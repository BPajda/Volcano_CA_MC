#!/usr/bin/env python3
"""Raport techniczny: docs/raport.md -> docs/raport.html -> docs/raport.pdf (Chromium przez Playwright,
bez LaTeX-a). Wymaga: pip install --user markdown pygments pypdf (+ pymupdf dla --png).

    python tools/build_report.py                 # HTML + PDF, liczba stron (kod wyjścia 1, gdy > --max-pages)
    python tools/build_report.py --png DIR       # dodatkowo każda strona PDF jako PNG (do obejrzenia)
    python tools/build_report.py --check         # tylko kontrola: nazwy funkcji i ścieżki z `…` istnieją w repozytorium

Układ: A4, marginesy 18 mm (dół 20 mm — stopka „str. X / Y”), tekst Cambria 10,5 pt (interlinia 1,3), nagłówki Inter,
kod JetBrains Mono 8,5 pt (fonty GUI z gui/static/vendor/fonts/), nagłówki numerowane licznikami CSS, rysunki, tabele
i listingi bez dzielenia między strony (break-inside: avoid).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SRC = DOCS / "raport.md"
HTML = DOCS / "raport.html"
PDF = DOCS / "raport.pdf"

CSS = r"""
@font-face { font-family: "Inter"; font-weight: 100 900; src: url("../gui/static/vendor/fonts/inter-latin-ext-wght-normal.woff2") format("woff2"); unicode-range: U+0100-024F, U+1E00-1EFF, U+2020, U+20A0-20AB, U+20AD-20CF, U+2113, U+2C60-2C7F, U+A720-A7FF; }
@font-face { font-family: "Inter"; font-weight: 100 900; src: url("../gui/static/vendor/fonts/inter-latin-wght-normal.woff2") format("woff2"); unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+2000-206F, U+2074, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD; }
@font-face { font-family: "JetBrains Mono"; font-weight: 100 800; src: url("../gui/static/vendor/fonts/jetbrains-mono-latin-ext-wght-normal.woff2") format("woff2"); unicode-range: U+0100-024F, U+1E00-1EFF, U+20A0-20AB, U+20AD-20CF, U+2113, U+2C60-2C7F, U+A720-A7FF; }
@font-face { font-family: "JetBrains Mono"; font-weight: 100 800; src: url("../gui/static/vendor/fonts/jetbrains-mono-latin-wght-normal.woff2") format("woff2"); unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+2000-206F, U+2074, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD; }
:root { --ink: #1f1a16; --ink2: #554b42; --rule: #d9d0c5; --tint: #f4f0ea; --accent: #b93c0b; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: Cambria, Caladea, Georgia, "Times New Roman", serif; font-size: 11.5pt; line-height: 1.32; color: var(--ink);
       margin: 0; counter-reset: sec fig tab lst; }
p { margin: 0 0 4.5pt; text-align: left; }
ul, ol { margin: 0 0 5pt; padding-left: 15pt; }
li { margin: 0 0 1.5pt; text-align: left; }
li > p { margin: 0; }
h1, h2, h3, h4 { font-family: Inter, "Segoe UI", sans-serif; color: var(--ink); break-after: avoid; }
h2 { font-size: 13.7pt; font-weight: 700; margin: 11pt 0 4pt; counter-increment: sec; counter-reset: sub; }
h2::before { content: counter(sec) ".\2002"; color: var(--accent); }
h3 { font-size: 11.5pt; font-weight: 650; margin: 7pt 0 2.5pt; counter-increment: sub; }
h3::before { content: counter(sec) "." counter(sub) "\2002"; color: var(--accent); }
h2.nonum::before, h3.nonum::before { content: none; }
strong { font-weight: 700; }
sub, sup { line-height: 0; font-size: 72%; }
a { color: inherit; text-decoration: none; }
code, pre { font-variant-ligatures: none; font-feature-settings: "liga" 0, "calt" 0; }
code { font-family: "JetBrains Mono", Consolas, monospace; font-size: 9.0pt; background: var(--tint); padding: 0 1.5pt;
       border-radius: 2pt; }
/* listingi */
.listing { break-inside: avoid; margin: 5pt 0 7pt; }
.listing .lst-head { font-family: Inter, "Segoe UI", sans-serif; font-size: 8.8pt; color: var(--ink2); margin: 0 0 1.5pt;
                     text-align: left; }
.listing .lst-head b { color: var(--ink); font-weight: 650; }
.listing .lst-head code { font-size: 8.1pt; }
.codehilite { margin: 0; }
.codehilite pre { font-family: "JetBrains Mono", Consolas, monospace; font-size: 8.6pt; line-height: 1.22; margin: 0;
                  background: #f8f6f2; border-left: 2.2pt solid #d8c9b6; padding: 3pt 6pt; white-space: pre-wrap; overflow: hidden; }
.codehilite pre code { background: none; padding: 0; font-size: inherit; white-space: pre-wrap; }
.codehilite .c, .codehilite .c1, .codehilite .cm, .codehilite .cs { color: #6f675e; font-style: italic; }
.codehilite .cp, .codehilite .cpf { color: #6f675e; }
.codehilite .k, .codehilite .kd, .codehilite .kn, .codehilite .kr, .codehilite .kc, .codehilite .ow { color: #24427a; font-weight: 600; }
.codehilite .kt { color: #24427a; }
.codehilite .s, .codehilite .s1, .codehilite .s2, .codehilite .sa, .codehilite .se { color: #3c6a2f; }
.codehilite .mi, .codehilite .mf, .codehilite .mh, .codehilite .il, .codehilite .m { color: #8a4a12; }
.codehilite .nf, .codehilite .fm { color: #5b2f7a; }
.codehilite .o, .codehilite .p { color: #3a332d; }
/* rysunki i tabele */
figure { break-inside: avoid; margin: 6pt 0 7pt; text-align: center; }
figure img { max-width: 100%; display: block; margin: 0 auto; }
figure svg { display: block; margin: 0 auto; }
figcaption, .caption { font-family: Inter, "Segoe UI", sans-serif; font-size: 8.8pt; line-height: 1.3; color: var(--ink2);
                       text-align: left; margin: 3pt 0 0; }
figcaption b, .caption b { color: var(--ink); font-weight: 650; }
figcaption code, .caption code { font-size: 8.1pt; }
.tab { break-inside: avoid; margin: 5pt 0 7pt; }
.tab .caption { margin: 0 0 2.5pt; }
table { border-collapse: collapse; width: 100%; font-family: Inter, "Segoe UI", sans-serif; font-size: 8.0pt; line-height: 1.25;
        font-variant-numeric: tabular-nums; }
th, td { border-bottom: 0.5pt solid var(--rule); padding: 1.6pt 3.5pt; vertical-align: top; text-align: left; }
th { font-weight: 650; background: #efe9e1; border-bottom: 0.8pt solid #b9ac9c; }
td code, th code { font-size: 7.5pt; white-space: nowrap; }
.nw td, .nw th { white-space: normal; }
.nw td.wr { white-space: normal; }
.t4 td:last-child { white-space: normal; }
td.r, th.r, .num td:not(:first-child), .num th:not(:first-child) { text-align: right; }
.tab.t3 td:nth-child(2), .tab.t3 th:nth-child(2) { text-align: left; }
.formula { text-align: center; margin: 2pt 0 4pt; white-space: pre-wrap; }
.note { font-family: Inter, "Segoe UI", sans-serif; font-size: 8.8pt; color: var(--ink2); }
/* strona tytułowa */
.title-page { text-align: left; }
.tp-subject { font-family: Inter, "Segoe UI", sans-serif; font-size: 10pt; color: var(--ink2); margin: 0 0 2pt; text-align: left; }
.tp-kind { font-family: Inter, "Segoe UI", sans-serif; font-size: 9pt; letter-spacing: .08em; text-transform: uppercase;
           color: var(--accent); margin: 14pt 0 5pt; font-weight: 650; text-align: left; }
.title-page h1 { font-size: 21pt; line-height: 1.15; margin: 0 0 6pt; font-weight: 750; }
.tp-sub { font-family: Inter, "Segoe UI", sans-serif; font-size: 11pt; color: var(--ink2); margin: 0 0 6pt; text-align: left; }
.tp-author { font-family: Inter, "Segoe UI", sans-serif; font-size: 11.5pt; font-weight: 600; margin: 0 0 12pt; text-align: left; }
.tp-meta { width: auto; font-size: 9.5pt; margin: 0 0 12pt; }
.tp-meta td { border: none; padding: 1.8pt 14pt 1.8pt 0; }
.tp-meta td:first-child { color: var(--ink2); }
.tp-rule { border: none; border-top: 0.8pt solid var(--rule); margin: 0 0 12pt; }
.intro { font-size: 11.5pt; line-height: 1.35; margin-bottom: 4pt; }
.pagebreak { break-after: page; }
.cols2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10pt; }
"""

FOOTER = ('<div style="width:100%; font-family: Inter, Segoe UI, sans-serif; font-size:7.5pt; color:#776d63; '
          'padding: 0 18mm; display:flex; justify-content:space-between;">'
          '<span>Erupcja wulkanu: CA + MC · Bartosz Pajda</span>'
          '<span>str. <span class="pageNumber"></span> / <span class="totalPages"></span></span></div>')


def build_html() -> str:
    import markdown

    text = SRC.read_text(encoding="utf-8")
    body = markdown.markdown(text, extensions=["tables", "fenced_code", "codehilite", "attr_list", "md_in_html", "sane_lists"],
                             extension_configs={"codehilite": {"guess_lang": False, "css_class": "codehilite"}},
                             output_format="html5")
    return ("<!doctype html>\n<html lang=\"pl\"><head><meta charset=\"utf-8\">\n"
            "<title>Erupcja wulkanu: spływ lawy (CA) i krystalizacja bazaltu (MC)</title>\n"
            f"<style>{CSS}</style></head>\n<body>\n{body}\n</body></html>\n")


def render_pdf(html_path: Path, pdf_path: Path) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(html_path.resolve().as_uri(), wait_until="load")
        page.evaluate("() => document.fonts.ready")
        page.wait_for_timeout(300)
        page.pdf(path=str(pdf_path), format="A4", print_background=True, display_header_footer=True,
                 header_template="<span></span>", footer_template=FOOTER,
                 margin={"top": "17mm", "bottom": "19mm", "left": "18mm", "right": "18mm"})
        browser.close()


def page_count(pdf_path: Path) -> int:
    from pypdf import PdfReader
    return len(PdfReader(str(pdf_path)).pages)


def render_png(pdf_path: Path, out: Path, dpi: int) -> None:
    import fitz  # PyMuPDF

    out.mkdir(parents=True, exist_ok=True)
    with fitz.open(pdf_path) as doc:
        for i, pg in enumerate(doc, start=1):
            pg.get_pixmap(dpi=dpi).save(str(out / f"strona_{i:02d}.png"))
    print(f"strony PNG ({dpi} dpi): {out}")


def check_names() -> int:
    """Każda nazwa funkcji / klasy (`Klasa::metoda()`, `funkcja()`) i ścieżka pliku z `…` w raporcie musi istnieć."""
    text = SRC.read_text(encoding="utf-8")
    spans = set(re.findall(r"`([^`\n]+)`", text))
    code = {}
    for base in ("engine/src", "gui", "tools", "bench"):
        for f in (ROOT / base).rglob("*"):
            if f.suffix in (".cpp", ".hpp", ".py", ".js", ".sh") and "vendor" not in f.parts:
                code[f] = f.read_text(encoding="utf-8", errors="replace")
    blob = "\n".join(code.values())
    problems = []
    for s in sorted(spans):
        for name in re.findall(r"([A-Za-z_][A-Za-z0-9_]*(?:::[A-Za-z_~][A-Za-z0-9_]*)*)(?:<[^>]*>)?\(\)", s):
            parts = name.split("::")
            if not re.search(r"\b" + re.escape(parts[-1]) + r"\s*\(", blob):
                problems.append(f"funkcja {name}: brak w kodzie")
            if len(parts) > 1 and not re.search(r"\b(class|struct)\s+" + re.escape(parts[0]) + r"\b", blob):
                if not re.search(r"\b" + re.escape(parts[0]) + r"::", blob):
                    problems.append(f"klasa {parts[0]} ({name}): brak w kodzie")
        if re.fullmatch(r"[\w.\-/<>*{}]+/[\w.\-<>*{}]+\.(?:cpp|hpp|py|js|json|md|csv|bin|png|sh|txt)", s) and not any(c in s for c in "<>*{}"):
            if not ((ROOT / s).exists() or (DOCS / s).exists()):
                problems.append(f"ścieżka {s}: nie istnieje")
    for p in problems:
        print("  BŁĄD:", p)
    print(f"kontrola nazw: {len(spans)} fragmentów `…`, problemów: {len(problems)}")
    return len(problems)


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--png", default=None, help="katalog na PNG stron")
    ap.add_argument("--dpi", type=int, default=110)
    ap.add_argument("--max-pages", type=int, default=10)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.check:
        return 1 if check_names() else 0
    HTML.write_text(build_html(), encoding="utf-8", newline="\n")
    render_pdf(HTML, PDF)
    n = page_count(PDF)
    print(f"zapisano {PDF.relative_to(ROOT).as_posix()} — {n} stron (limit {args.max_pages})")
    if args.png:
        render_png(PDF, Path(args.png), args.dpi)
    bad = check_names()
    return 1 if n > args.max_pages or bad else 0


if __name__ == "__main__":
    sys.exit(main())
