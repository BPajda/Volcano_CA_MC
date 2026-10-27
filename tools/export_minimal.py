#!/usr/bin/env python3
"""Eksport wersji minimalnej projektu: kod, README, raport PDF i PDF-y dokumentacji, do osobnego folderu (repozytorium).

    python tools/export_minimal.py                          # domyślnie ../volcano-ca-mc-minimal
    python tools/export_minimal.py ..\\volcano-ca-mc-minimal
    python tools/export_minimal.py --sprawdz                # tylko kontrola istniejącego eksportu (bez kopiowania)

Co robi:
  1. Czyści folder docelowy Z WYJĄTKIEM `.git/` — folder można trzymać jako osobne repozytorium i aktualizować jedną
     komendą po kolejnych zmianach (eksport → commit w folderze minimalnym → push).
  2. Kopiuje pliki z listy „kopiuj” (COPY niżej — lista dozwolonych, nie lista pomijanych): silnik z testami, GUI
     z testami pytest, narzędzia potrzebne do działania, configi i mapy wysokości, skrypty pomiarów z danymi cytowanymi
     w raporcie, pliki CMake, `.gitignore`, `docs/raport.pdf` → `raport.pdf`, PDF-y dokumentów `docs/pdf/` (link
     „Pobierz PDF” zakładki „Wydajność” działa także tutaj), szablon `tools/export_minimal/README.md` → `README.md`
     i obrazki, których ten README używa.
  3. W skopiowanych plikach Markdown odnośniki do dokumentacji z `docs/` (której w tej wersji nie ma) zamienia na
     odnośniki do PDF-u tego dokumentu z `docs/pdf/`, a gdy go nie ma — do `raport.pdf`.
  4. Sprawdza wynik: (a) odnośniki i obrazki we wszystkich plikach .md wskazują istniejące pliki, (b) ścieżki do
     `docs/` w kodzie — błąd poza komentarzami i opisami (w GUI to byłyby martwe linki), w komentarzach tylko
     informacja, (c) słownictwo spoza projektu — 0 trafień wzorców z lokalnego pliku `tools/export_minimal/slownictwo.txt`
     (w .gitignore; bez niego ta kontrola jest pomijana z ostrzeżeniem), także w tekście PDF-ów dokumentacji (pypdf).
     Kod wyjścia 1, gdy kontrola wykryła błędy.

Folder docelowy nie może być katalogiem projektu ani go zawierać; niepusty folder bez śladów poprzedniego eksportu
(README.md + raport.pdf + engine/) wymaga opcji --force.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import shutil
import sys
import tokenize
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "tools" / "export_minimal" / "README.md"

# ---------------------------------------------------------------- lista „kopiuj” (ścieżki względem katalogu projektu)
# (źródło, cel) — źródło może być katalogiem (kopiowany rekurencyjnie, z regułami EXCLUDE) albo wzorcem glob.
COPY: list[tuple[str, str]] = [
    ("engine", "engine"),                       # silnik C++17: src/, tests/ (doctest), third_party/
    ("gui", "gui"),                             # backend + frontend + testy pytest (bez skryptów zrzutów, EXCLUDE)
    ("tools/make_series.py", "tools/make_series.py"),
    ("tools/make_heightmaps.py", "tools/make_heightmaps.py"),
    ("tools/plot_slice.py", "tools/plot_slice.py"),
    ("tools/plot_mc_stats.py", "tools/plot_mc_stats.py"),
    ("tools/export_vtk.py", "tools/export_vtk.py"),
    ("tools/latlon_to_grid.py", "tools/latlon_to_grid.py"),
    ("tools/fetch_dem.py", "tools/fetch_dem.py"),
    ("configs/*.json", "configs"),
    ("configs/heightmaps", "configs/heightmaps"),
    ("bench/*.py", "bench"),
    ("bench/*.sh", "bench"),
    ("bench/README.md", "bench/README.md"),
    ("bench/micro", "bench/micro"),             # mc_kernels.cpp, omp_overhead.cpp, bandwidth.cpp — cele CMake o tych nazwach
    ("bench/results/*.csv", "bench/results"),   # dane pomiarowe cytowane w raporcie (bez bench/profiles/)
    ("CMakeLists.txt", "CMakeLists.txt"),
    ("CMakePresets.json", "CMakePresets.json"),
    (".gitignore", ".gitignore"),
    ("docs/raport.pdf", "raport.pdf"),
    ("docs/pdf", "docs/pdf"),                   # PDF-y dokumentów + index.json (tytuły) dla /api/doc/pdf zakładki „Wydajność”
]
# Obrazki używane przez README wersji minimalnej (sprawdzane z szablonem — każdy musi być na tej liście).
README_IMAGES = ["docs/img/readme/gui_3_erupcja_3d.png"]

# Wykluczenia przy kopiowaniu katalogów (wzorce ścieżek względem katalogu projektu).
EXCLUDE = [
    "*/__pycache__/*", "*/.pytest_cache/*", "*.pyc",
    "gui/settings.json",
    # skrypty zrzutów ekranu i pomiarów przez przeglądarkę (piszą do docs/) — zostają testy pytest i conftest.py
    "gui/tests/screenshots.py", "gui/tests/ui_shots.py", "gui/tests/raport_shots.py", "gui/tests/palette_check.py",
    "gui/tests/run_ca_vs_mc.py",
]
# W .gitignore wersji minimalnej pomijamy blok konwencji pracy lokalnej (od tej linii do końca pliku).
GITIGNORE_CUT = "# Konwencje pracy lokalnej"

TEXT_EXT = {".md", ".txt", ".py", ".js", ".html", ".css", ".json", ".cpp", ".hpp", ".h", ".sh", ".bat", ".ps1",
            ".cmake", ".csv"}
THIRD_PARTY = ["engine/third_party/*", "gui/static/vendor/three/*", "gui/static/vendor/chartjs/*.js"]

# Słownictwo, które nie może się pojawić w eksporcie (poza bibliotekami zewnętrznymi — THIRD_PARTY): wzorce wyrażeń
# regularnych, po jednym w linii, z lokalnego pliku poza repozytorium (w .gitignore) — inaczej sama lista dawałaby trafienia.
VOCAB_FILE = ROOT / "tools" / "export_minimal" / "slownictwo.txt"


def load_vocab(path: Path) -> re.Pattern | None:
    if not path.is_file():
        return None
    pats = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]
    return re.compile("|".join(f"(?:{p})" for p in pats), re.IGNORECASE) if pats else None

MD_LINK = re.compile(r"(!?)\[([^\]\n]*)\]\(([^)\s]+)\)")
DOCS_REF = re.compile(r"(?<![\w/.\-])((?:\.\./)*docs[/\\][\w.\-/\\*{}<>]*[\w*}>])")


def rel(p: Path, base: Path) -> str:
    return p.relative_to(base).as_posix()


def matches(relpath: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(relpath, pat) or fnmatch.fnmatch("./" + relpath, pat) for pat in patterns)


# ---------------------------------------------------------------- czyszczenie i kopiowanie

def check_target(dest: Path, force: bool) -> None:
    root = ROOT.resolve()
    d = dest.resolve()
    if d == root or root in d.parents or d in root.parents:
        sys.exit(f"Folder docelowy {d} nie może być katalogiem projektu, jego podkatalogiem ani katalogiem nadrzędnym.")
    if d.exists() and not d.is_dir():
        sys.exit(f"{d} istnieje i nie jest folderem.")
    if d.exists() and not force:
        content = [p for p in d.iterdir() if p.name != ".git"]
        looks_like_export = (d / "README.md").is_file() and (d / "raport.pdf").is_file() and (d / "engine").is_dir()
        if content and not looks_like_export:
            sys.exit(f"{d} nie jest pusty i nie wygląda na poprzedni eksport (README.md, raport.pdf, engine/) — "
                     f"wybierz inny folder albo użyj --force.")


def clean(dest: Path) -> int:
    """Usuwa zawartość folderu docelowego poza `.git/` (to wygenerowana kopia — źródłem jest repozytorium główne)."""
    n = 0
    if not dest.exists():
        dest.mkdir(parents=True)
        return 0
    for p in dest.iterdir():
        if p.name == ".git":
            continue
        if p.is_dir() and not p.is_symlink():
            shutil.rmtree(p)
        else:
            p.unlink()
        n += 1
    return n


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def copy_all(dest: Path) -> list[str]:
    copied: list[str] = []
    for src_rel, dst_rel in COPY:
        sources = sorted(ROOT.glob(src_rel)) if any(c in src_rel for c in "*?[") else [ROOT / src_rel]
        if not sources or not all(s.exists() for s in sources):
            sys.exit(f"Brak źródła z listy „kopiuj”: {src_rel}")
        for src in sources:
            if src.is_dir():
                for f in sorted(src.rglob("*")):
                    r = rel(f, ROOT)
                    if f.is_dir() or matches(r, EXCLUDE):
                        continue
                    target = dest / dst_rel / rel(f, src)
                    copy_file(f, target)
                    copied.append(rel(target, dest))
            else:
                r = rel(src, ROOT)
                if matches(r, EXCLUDE):
                    continue
                is_glob = any(c in src_rel for c in "*?[")
                target = dest / dst_rel / src.name if is_glob else dest / dst_rel
                copy_file(src, target)
                copied.append(rel(target, dest))
    for img in README_IMAGES:
        copy_file(ROOT / img, dest / img)
        copied.append(img)
    readme = TEMPLATE.read_text(encoding="utf-8")
    if readme.startswith("<!--"):  # komentarz dla czytelników szablonu — nie trafia do eksportu
        readme = readme.split("-->", 1)[1].lstrip("\n")
    (dest / "README.md").write_text(readme, encoding="utf-8", newline="\n")
    copied.append("README.md")
    # .gitignore bez bloku konwencji pracy lokalnej
    gi = dest / ".gitignore"
    text = gi.read_text(encoding="utf-8")
    if GITIGNORE_CUT in text:
        gi.write_text(text.split(GITIGNORE_CUT)[0].rstrip("\n") + "\n", encoding="utf-8", newline="\n")
    return copied


# ---------------------------------------------------------------- odnośniki do docs/ w plikach Markdown

def target_of(md: Path, link: str, dest: Path) -> Path | None:
    """Plik, na który wskazuje odnośnik względny (None dla adresów URL i kotwic w tym samym pliku)."""
    if re.match(r"^[a-z][a-z0-9+.-]*:", link, re.I) or link.startswith("#"):
        return None
    path = link.split("#", 1)[0]
    if not path:
        return None
    return (dest / path.lstrip("/")) if path.startswith("/") else (md.parent / path)


def rewrite_markdown(dest: Path) -> int:
    """Odnośniki do nieistniejących plików z docs/ → PDF tego dokumentu z docs/pdf/ (jeśli jest w eksporcie), inaczej
    raport.pdf (w każdym pliku .md poza README.md w katalogu głównym)."""
    changed = 0
    for md in sorted(dest.rglob("*.md")):
        if md == dest / "README.md" or ".git" in md.relative_to(dest).parts:
            continue
        text = md.read_text(encoding="utf-8")
        to_pdf = os.path.relpath(dest / "raport.pdf", md.parent).replace(os.sep, "/")

        def doc_pdf(stem: str) -> Path | None:
            p = dest / "docs" / "pdf" / f"{stem}.pdf"
            return p if p.is_file() else None

        def repl_link(m: re.Match) -> str:
            bang, label, link = m.groups()
            t = target_of(md, link, dest)
            if t is None or t.exists() or "docs" not in Path(os.path.relpath(t, dest)).parts[:1]:
                return m.group(0)
            pdf = doc_pdf(t.stem) if t.suffix == ".md" else None
            if pdf:  # kotwica rozdziału nie przechodzi do PDF — odnośnik do całego dokumentu
                rel_pdf = os.path.relpath(pdf, md.parent).replace(os.sep, "/")
                new_label = f"`docs/pdf/{pdf.name}`" if ("docs/" in label or label.strip("`").endswith(".md")) else label
                return f"{bang}[{new_label}]({rel_pdf})"
            new_label = "raport.pdf" if ("docs/" in label or label.strip("`").endswith(".md")) else label
            return f"{bang}[{new_label}]({to_pdf})"

        new = MD_LINK.sub(repl_link, text)
        # Kilka odnośników do raportu z rzędu (po zamianie) → jeden.
        pdf_link = re.escape(f"[raport.pdf]({to_pdf})")
        new = re.sub(rf"{pdf_link}(?:(?:,\s*|\s+i\s+){pdf_link})+", f"[raport.pdf]({to_pdf})", new)

        # Wzmianki `docs/<plik>.md` (bez odnośnika) → `raport.pdf`.
        def repl_tick(m: re.Match) -> str:
            path = m.group(1)
            t = (md.parent / path) if path.startswith("../") else (dest / path)
            if t.exists():
                return m.group(0)
            return f"`docs/pdf/{t.stem}.pdf`" if doc_pdf(t.stem) else "`raport.pdf`"

        new = re.sub(r"`((?:\.\./)*docs/[\w.\-/]+\.md)`", repl_tick, new)
        new = re.sub(r"`raport\.pdf`(?:(?:,\s*|\s+i\s+)`raport\.pdf`)+", "`raport.pdf`", new)
        if new != text:
            md.write_text(new, encoding="utf-8", newline="\n")
            changed += 1
    return changed


# ---------------------------------------------------------------- kontrola

def is_third_party(r: str) -> bool:
    return matches(r, THIRD_PARTY)


def text_files(dest: Path) -> list[Path]:
    out = []
    for f in sorted(dest.rglob("*")):
        if f.is_file() and ".git" not in f.relative_to(dest).parts and (f.suffix.lower() in TEXT_EXT
                                                                       or f.name in ("CMakeLists.txt", ".gitignore")):
            out.append(f)
    return out


def python_comment_lines(path: Path) -> set[int]:
    """Numery linii komentarzy i napisów wielowierszowych (docstringów) w pliku Pythona."""
    lines: set[int] = set()
    try:
        with open(path, "rb") as fh:
            for tok in tokenize.tokenize(fh.readline):
                if tok.type == tokenize.COMMENT:
                    lines.add(tok.start[0])
                elif tok.type == tokenize.STRING and tok.string.lstrip("rbuRBU").startswith(('"""', "'''")):
                    lines.update(range(tok.start[0], tok.end[0] + 1))
    except (tokenize.TokenError, SyntaxError):
        pass
    return lines


def block_comment_lines(text: str, ext: str) -> set[int]:
    """Numery linii leżących w komentarzach blokowych /* … */ (C++, JS, CSS) i <!-- … --> (HTML)."""
    pairs = [("/*", "*/")] if ext in (".cpp", ".hpp", ".h", ".js", ".css") else []
    if ext == ".html":
        pairs += [("<!--", "-->"), ("/*", "*/")]
    lines: set[int] = set()
    for start, end in pairs:
        pos = 0
        while (a := text.find(start, pos)) != -1:
            b = text.find(end, a + len(start))
            b = len(text) if b == -1 else b
            lines.update(range(text.count("\n", 0, a) + 1, text.count("\n", 0, b) + 2))
            pos = b + len(end)
    return lines


def in_comment(path: Path, line: str, lineno: int, col: int, comment_lines: set[int]) -> bool:
    ext = path.suffix.lower()
    s = line.lstrip()
    if lineno in comment_lines:
        return True
    if ext == ".py":
        return False
    if ext == ".md":
        return True  # wzmianka w tekście dokumentu (odnośniki sprawdza check_links)
    if ext == ".json":
        return s.startswith('"_')  # klucze „_…” to komentarze configu
    if s.startswith(("*", "/*", "<!--", "#")):
        return True
    before = line[:col]
    return "//" in before or "/*" in before or "<!--" in before or (ext in (".sh", ".txt", ".cmake") and "#" in before)


def check_links(dest: Path) -> list[str]:
    errors = []
    for md in sorted(dest.rglob("*.md")):
        if ".git" in md.relative_to(dest).parts or is_third_party(rel(md, dest)):
            continue
        for i, line in enumerate(md.read_text(encoding="utf-8").splitlines(), 1):
            for m in MD_LINK.finditer(line):
                t = target_of(md, m.group(3), dest)
                if t is not None and not t.exists():
                    errors.append(f"{rel(md, dest)}:{i}: odnośnik do nieistniejącego pliku: {m.group(3)}")
    return errors


def check_docs_refs(dest: Path) -> tuple[list[str], list[str]]:
    errors, infos = [], []
    for f in text_files(dest):
        r = rel(f, dest)
        if is_third_party(r) or f.suffix.lower() == ".csv":
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        ext = f.suffix.lower()
        comment_lines = python_comment_lines(f) if ext == ".py" else block_comment_lines(text, ext)
        for i, line in enumerate(text.splitlines(), 1):
            for m in DOCS_REF.finditer(line):
                ref = m.group(1).replace("\\", "/")
                rest = ref.split("docs/", 1)[1]
                wildcard = any(c in rest for c in "*{}<>")
                # Tylko dokumentacja tego repozytorium: ścieżka musi istnieć w docs/ repozytorium głównego
                # (pomija np. docs/attribution.md projektu tilezen/joerd i przykładowe nazwy plików wyjściowych).
                in_main = any((ROOT / "docs").glob(rest)) if wildcard and "{" not in rest else (ROOT / "docs" / rest).exists()
                if not in_main:
                    continue
                exported = any((dest / "docs").glob(rest)) if wildcard else (dest / "docs" / rest).exists()
                if exported:
                    continue
                msg = f"{r}:{i}: {ref}"
                (infos if in_comment(f, line, i, m.start(), comment_lines) else errors).append(msg)
    return errors, infos


def check_vocab(dest: Path, rx: re.Pattern) -> list[str]:
    hits = []
    for f in text_files(dest):
        r = rel(f, dest)
        if is_third_party(r):
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for m in rx.finditer(line):
                hits.append(f"{r}:{i}: „{m.group(0)}” — {line.strip()[:120]}")
    return hits + check_vocab_pdf(dest, rx)


def check_vocab_pdf(dest: Path, rx: re.Pattern) -> list[str]:
    """Słownictwo w tekście PDF-ów dokumentacji (docs/pdf/*.pdf); raport ma własną kontrolę przy budowaniu."""
    pdfs = sorted((dest / "docs" / "pdf").glob("*.pdf"))
    if not pdfs:
        return []
    try:
        from pypdf import PdfReader
    except ImportError:
        print("  UWAGA: brak pypdf — słownictwo w PDF-ach dokumentacji niesprawdzone (pip install --user pypdf)")
        return []
    hits = []
    for f in pdfs:
        for n, page in enumerate(PdfReader(str(f)).pages, 1):
            # tekst z PDF bywa łamany w środku słowa („wydajno ś ci”) — sklejamy spacje przed polskimi znakami
            # i normalizujemy znaki złożone (z + kropka → ż), żeby słowo z „ż” rozbite na „z” + kropkę nie dawało
            # fałszywego trafienia wzorca bez polskiej litery
            text = unicodedata.normalize("NFC", page.extract_text() or "")
            text = re.sub(r" (?=[ąćęłńóśźż])|(?<=[ąćęłńóśźż]) ", "", text)
            for line in text.splitlines():
                for m in rx.finditer(line):
                    hits.append(f"{rel(f, dest)}, str. {n}: „{m.group(0)}” — {line.strip()[:120]}")
    return hits


def check(dest: Path, verbose: bool, vocab_file: Path) -> int:
    link_err = check_links(dest)
    ref_err, ref_info = check_docs_refs(dest)
    rx = load_vocab(vocab_file)
    vocab = check_vocab(dest, rx) if rx else []
    missing_imgs = [img for img in README_IMAGES if not (dest / img).exists()]
    print("\nKontrola wersji minimalnej:")
    print(f"  odnośniki w plikach .md do nieistniejących plików: {len(link_err)}")
    for e in link_err:
        print("    BŁĄD", e)
    print(f"  ścieżki do docs/ w kodzie poza komentarzami: {len(ref_err)}")
    for e in ref_err:
        print("    BŁĄD", e)
    print(f"  ścieżki do docs/ w komentarzach i opisach (informacyjnie — dokumentacja pełnego repozytorium): {len(ref_info)}")
    for e in ref_info if verbose else []:
        print("    info", e)
    if rx:
        print(f"  słownictwo spoza projektu: {len(vocab)} trafień")
    else:
        print(f"  słownictwo spoza projektu: POMINIĘTE — brak listy wzorców {vocab_file}")
    for e in vocab:
        print("    BŁĄD", e)
    for img in missing_imgs:
        print("    BŁĄD brak obrazka README:", img)
    bad = len(link_err) + len(ref_err) + len(vocab) + len(missing_imgs)
    print("  wynik:", "OK" if not bad else f"{bad} problemów")
    return 1 if bad else 0


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dest", nargs="?", default=str(ROOT.parent / "volcano-ca-mc-minimal"),
                    help="folder docelowy (domyślnie ../volcano-ca-mc-minimal)")
    ap.add_argument("--sprawdz", action="store_true", help="tylko kontrola istniejącego eksportu")
    ap.add_argument("--force", action="store_true", help="pozwól wyczyścić niepusty folder, który nie jest eksportem")
    ap.add_argument("-v", "--verbose", action="store_true", help="wypisz też informacyjne odwołania do docs/")
    ap.add_argument("--slownictwo", default=str(VOCAB_FILE), help="plik z wzorcami słownictwa do kontroli")
    args = ap.parse_args()
    dest = Path(args.dest).resolve()
    vocab_file = Path(args.slownictwo)

    if args.sprawdz:
        if not dest.is_dir():
            sys.exit(f"Brak folderu {dest}")
        return check(dest, args.verbose, vocab_file)

    check_target(dest, args.force)
    # README szablonu nie może używać obrazków spoza README_IMAGES
    for m in MD_LINK.finditer(TEMPLATE.read_text(encoding="utf-8")):
        if m.group(1) and m.group(3) not in README_IMAGES:
            sys.exit(f"Szablon README używa obrazka spoza README_IMAGES: {m.group(3)}")
    removed = clean(dest)
    copied = copy_all(dest)
    rewritten = rewrite_markdown(dest)
    size = sum((dest / c).stat().st_size for c in copied)
    print(f"Wersja minimalna: {dest}")
    print(f"  usunięto poprzednią zawartość: {removed} elementów (bez .git/)")
    print(f"  skopiowano: {len(copied)} plików, {size / 2**20:.1f} MB")
    print(f"  pliki .md z odnośnikami do docs/ zamienionymi na PDF (docs/pdf/ albo raport.pdf): {rewritten}")
    return check(dest, args.verbose, vocab_file)


if __name__ == "__main__":
    sys.exit(main())
