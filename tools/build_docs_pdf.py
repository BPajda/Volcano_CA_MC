#!/usr/bin/env python3
"""PDF dokumentów: docs/<nazwa>.md -> docs/pdf/<nazwa>.pdf (Chromium przez Playwright, styl jak raport
tools/build_report.py). Bez raportów raport-1.md i raport-2.md (własny skrypt) i bez spisu docs/README.md.

    python tools/build_docs_pdf.py                    # wszystkie dokumenty + docs/pdf/index.json (tytuły, strony)
    python tools/build_docs_pdf.py openmp mpi         # wybrane dokumenty (nazwy bez .md)
    python tools/build_docs_pdf.py --png DIR          # dodatkowo pierwsze strony jako PNG (do obejrzenia)

Układ: A4, tekst ~11 pt, pierwsza strona z tytułem, podtytułem „volcano-ca-mc: dokumentacja techniczna”, autorem
i datą wygenerowania; u góry każdej strony tytuł dokumentu, na dole numer strony. Rozdziały mają numerację z samego
dokumentu (bez liczników CSS raportu). Obrazki z docs/img/, tabele i listingi zawijane (nic nie wychodzi poza stronę).
Odnośniki do innych dokumentów stają się tekstem „(zob. dokument „Tytuł”)”, odnośniki do plików kodu i wyników —
samą ścieżką. Skrypt sprawdza po wyrenderowaniu: wczytane obrazki, elementy szersze niż strona, liczbę stron.
Obrazki trafiają do PDF w rozdzielczości druku (najwyżej ~300 dpi w ramce 174 × 120 mm): zrzuty ekranu jako JPEG,
wykresy bez zmian albo pomniejszone PNG (kopie w katalogu tymczasowym; pliki w docs/img/ bez zmian).
Wymaga: pip install --user markdown pygments pypdf playwright pillow (+ pymupdf dla --png).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_report as br  # noqa: E402  (wspólny styl i licznik stron z raportem)

ROOT = br.ROOT
DOCS = br.DOCS
OUT = DOCS / "pdf"
SKIP = {"raport-1.md", "raport-2.md", "README.md"}  # raporty mają własny skrypt (build_report.py)
AUTHOR = "Bartosz Pajda"
SUBTITLE = "volcano-ca-mc: dokumentacja techniczna"

# Różnice względem raportu: numeracja rozdziałów z treści dokumentu, szersze tabele z zawijaniem, strona tytułowa.
CSS_DOCS = r"""
body { counter-reset: none; font-size: 11pt; }
h2::before, h3::before { content: none; }
h2 { font-size: 14pt; margin: 13pt 0 4pt; }
h3 { font-size: 11.5pt; margin: 9pt 0 3pt; }
h4 { font-size: 10.5pt; margin: 7pt 0 2pt; font-weight: 650; }
p, li { text-align: left; }
img { max-width: 100%; height: auto; }
p > img { display: block; margin: 6pt auto 2pt; max-height: 120mm; object-fit: contain; }
table { margin: 4pt 0 8pt; table-layout: auto; }
th, td { overflow-wrap: break-word; hyphens: auto; }
td code, th code { white-space: normal; overflow-wrap: anywhere; }
.codehilite pre, pre { white-space: pre-wrap; overflow-wrap: anywhere; }
pre code { white-space: pre-wrap; }
blockquote { margin: 4pt 0 6pt; padding-left: 8pt; border-left: 2pt solid var(--rule); color: var(--ink2); }
.title-page { padding-top: 70mm; }
.title-page h1 { font-size: 24pt; margin: 0 0 8pt; }
.title-page .tp-kind { margin: 0 0 10pt; }
.title-page .tp-author { margin: 16pt 0 2pt; }
.pagebreak { break-after: page; }
"""

MD_LINK = re.compile(r"(!?)\[([^\]\n]*)\]\(([^)\s]+)\)")


def doc_titles() -> dict[str, str]:
    """Tytuł każdego dokumentu = pierwszy nagłówek „# …”."""
    out = {}
    for p in sorted(DOCS.glob("*.md")):
        first = p.read_text(encoding="utf-8").split("\n", 1)[0]
        if first.startswith("# "):
            out[p.name] = first[2:].strip()
    return out


def rewrite_links(text: str, titles: dict[str, str]) -> str:
    """Odnośniki Markdown na tekst do druku: dokumenty → „(zob. dokument „Tytuł”)”, pliki → ścieżka w `…`."""

    def repl(m: re.Match) -> str:
        bang, label, link = m.groups()
        if bang:  # obrazek zostaje (img/… względem docs/)
            return m.group(0)
        if re.match(r"^[a-z][a-z0-9+.-]*:", link, re.I) or link.startswith("#"):
            return m.group(0)  # adres URL i kotwica w tym samym dokumencie
        path = link.split("#", 1)[0]
        name = Path(path).name
        plain = label.strip("`")
        if "/" not in path.rstrip("/") and name in titles:
            ref = f"dokument „{titles[name]}”"
            if plain in (name, f"docs/{name}") or plain.lower() == titles[name].lower():
                return ref
            return f"{label} (zob. {ref})"
        rel = os.path.normpath(os.path.join("docs", path)).replace("\\", "/")
        if path.endswith("/"):
            rel += "/"
        if plain.rstrip("/") in (rel.rstrip("/"), path.rstrip("/"), name.rstrip("/")):
            return f"`{rel}`"
        return f"{label} (`{rel}`)"

    return MD_LINK.sub(repl, text)


def build_html(md_path: Path, titles: dict[str, str], date: str) -> tuple[str, str]:
    import markdown

    text = md_path.read_text(encoding="utf-8")
    first, body = text.split("\n", 1) if text.startswith("# ") else ("", text)
    title = first[2:].strip() if first else md_path.stem
    body = rewrite_links(body, titles)
    html = markdown.markdown(body, extensions=["tables", "fenced_code", "codehilite", "attr_list", "md_in_html",
                                               "sane_lists"],
                             extension_configs={"codehilite": {"guess_lang": False, "css_class": "codehilite"}},
                             output_format="html5")
    page = (f'<div class="title-page"><p class="tp-kind">{SUBTITLE}</p><h1>{title}</h1>'
            f'<p class="tp-author">{AUTHOR}</p><p class="tp-sub">Wygenerowano: {date}</p></div>'
            f'<div class="pagebreak"></div>')
    doc = ("<!doctype html>\n<html lang=\"pl\"><head><meta charset=\"utf-8\">\n"
           f"<title>{title}</title>\n<style>{br.CSS}{CSS_DOCS}</style></head>\n<body>\n{page}\n{html}\n</body></html>\n")
    return title, doc


# Obrazki do druku: ramka obrazka w PDF to szerokość tekstu (174 mm) i max-height 120 mm (CSS_DOCS), więc większa
# rozdzielczość niż ~300 dpi w tej ramce nic nie daje, a pełne zrzuty stron GUI (1280 × 3700 px) ważą po kilkaset KB.
PRINT_DPI = 300
PRINT_BOX_PX = (round(174 / 25.4 * PRINT_DPI), round(120 / 25.4 * PRINT_DPI))
SCREENSHOT = re.compile(r"^img/(gui_|ui_|real_|replay_|raport/gui_|raport-2/gui_|readme/)")  # zrzuty ekranu (JPEG); reszta — wykresy
IMG_SRC = re.compile(r'(<img\b[^>]*\bsrc=")(img/[^"]+)(")')


def print_image(rel: str, tmp: Path, cache: dict[str, str]) -> str:
    """Kopia obrazka docs/<rel> do druku (adres file:// w katalogu tymczasowym); oryginał, gdy kopia nie jest mniejsza."""
    if rel in cache:
        return cache[rel]
    from PIL import Image

    src = DOCS / rel
    shot = bool(SCREENSHOT.match(rel))
    im = Image.open(src)
    w, h = im.size
    s = min(1.0, PRINT_BOX_PX[0] / w, PRINT_BOX_PX[1] / h)
    if not shot and s == 1.0:  # wykres w rozdzielczości druku: bez zmian (Chromium i tak zapisuje go bezstratnie)
        cache[rel] = rel
        return rel
    im = im.convert("RGB")
    if s < 1:
        im = im.resize((round(w * s), round(h * s)), Image.LANCZOS)
    dst = tmp / (rel.replace("/", "_").rsplit(".", 1)[0] + (".jpg" if shot else ".png"))
    if shot:  # zrzut ekranu: JPEG (Chromium osadza go bez ponownego kodowania)
        im.save(dst, "JPEG", quality=88, optimize=True)
    else:
        im.save(dst, "PNG", optimize=True)
    cache[rel] = dst.resolve().as_uri() if dst.stat().st_size < src.stat().st_size else rel
    return cache[rel]


def header(title: str) -> str:
    return ('<div style="width:100%; font-family: Inter, Segoe UI, sans-serif; font-size:7.5pt; color:#776d63; '
            f'padding: 0 18mm; display:flex; justify-content:space-between;"><span>volcano-ca-mc</span>'
            f'<span>{title}</span></div>')


FOOTER = ('<div style="width:100%; font-family: Inter, Segoe UI, sans-serif; font-size:7.5pt; color:#776d63; '
          'padding: 0 18mm; display:flex; justify-content:flex-end;">'
          '<span>str. <span class="pageNumber"></span> / <span class="totalPages"></span></span></div>')

# Kontrola po wyrenderowaniu (w przeglądarce): obrazki niewczytane i elementy szersze niż obszar tekstu.
CHECK_JS = """() => {
  const width = document.body.clientWidth;
  const bad = [];
  for (const img of document.images) if (!img.complete || img.naturalWidth === 0) bad.push('obrazek: ' + img.getAttribute('src'));
  for (const el of document.querySelectorAll('table, pre, img, svg, figure')) {
    const r = el.getBoundingClientRect();
    if (r.right > width + 2 || el.scrollWidth > el.clientWidth + 2)
      bad.push('za szeroki ' + el.tagName.toLowerCase() + ': ' + (el.textContent || el.getAttribute('src') || '').trim().slice(0, 60));
  }
  return { bad, images: document.images.length, tables: document.querySelectorAll('table').length };
}"""


def render(page, html_path: Path, pdf_path: Path, title: str) -> dict:
    page.goto(html_path.resolve().as_uri(), wait_until="load")
    page.evaluate("() => document.fonts.ready")
    page.wait_for_timeout(200)
    page.emulate_media(media="print")
    info = page.evaluate(CHECK_JS)
    page.pdf(path=str(pdf_path), format="A4", print_background=True, display_header_footer=True,
             header_template=header(title), footer_template=FOOTER,
             margin={"top": "17mm", "bottom": "17mm", "left": "18mm", "right": "18mm"})
    return info


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("names", nargs="*", help="dokumenty (nazwy plików bez .md); domyślnie wszystkie")
    ap.add_argument("--png", default=None, help="katalog na PNG pierwszych stron")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    titles = doc_titles()
    docs = [p for p in sorted(DOCS.glob("*.md")) if p.name not in SKIP]
    if args.names:
        docs = [p for p in docs if p.stem in args.names]
    OUT.mkdir(exist_ok=True)
    index_path = OUT / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
    index.setdefault("titles", {})
    index.setdefault("pages", {})
    date = dt.date.today().strftime("%d.%m.%Y")
    problems = 0
    img_tmp = Path(tempfile.mkdtemp(prefix="volcano_pdf_img_"))
    img_cache: dict[str, str] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        for md in docs:
            title, html = build_html(md, titles, date)
            html = IMG_SRC.sub(lambda m: m.group(1) + print_image(m.group(2), img_tmp, img_cache) + m.group(3), html)
            tmp = DOCS / f".pdf_{md.stem}.html"  # obok dokumentu: względne img/ i ../gui/static/vendor/fonts/ działają
            pdf = OUT / f"{md.stem}.pdf"
            try:
                tmp.write_text(html, encoding="utf-8", newline="\n")
                info = render(page, tmp, pdf, title)
            finally:
                tmp.unlink(missing_ok=True)
            n = br.page_count(pdf)
            index["titles"][pdf.name] = title
            index["pages"][pdf.name] = n
            problems += len(info["bad"])
            print(f"docs/pdf/{pdf.name}: {n} stron, obrazków {info['images']}, tabel {info['tables']}"
                  + ("" if not info["bad"] else f", PROBLEMY: {len(info['bad'])}"))
            for b in info["bad"]:
                print("   ", b)
            if args.png:
                import pymupdf as fitz

                out = Path(args.png)
                out.mkdir(parents=True, exist_ok=True)
                with fitz.open(pdf) as d:
                    for i in range(min(3, len(d))):
                        d[i].get_pixmap(dpi=70).save(str(out / f"{md.stem}_{i + 1}.png"))
        browser.close()
    shutil.rmtree(img_tmp, ignore_errors=True)
    index["generated"] = dt.date.today().isoformat()
    index["titles"] = dict(sorted(index["titles"].items()))
    index["pages"] = dict(sorted(index["pages"].items()))
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"docs/pdf/index.json: {len(index['titles'])} dokumentów; problemów: {problems}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
