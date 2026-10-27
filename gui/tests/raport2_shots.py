"""Zrzut GUI do raportu 2 (docs/raport-2.md): zakładka „Wydajność” — nagłówek z plakietkami zgodności i jedna karta
wykresu z wnioskiem i blokiem „Jak czytać”. Zapis do docs/img/raport-2/gui_wydajnosc.png (motyw jasny — raport jest
drukowany na białym tle; okno 1600×900, deviceScaleFactor 2, jak gui/tests/raport_shots.py).

    python gui/tests/raport2_shots.py                       # sekcja OpenMP, karta omp_skalowanie (domyślnie)
    python gui/tests/raport2_shots.py --section mpi --card mpi_skalowanie
    python gui/tests/raport2_shots.py --full results\\wydajnosc_cala.png   # dodatkowo cała strona (do wyboru kadru)

Kadr: nagłówek zakładki (zasada zgodności, „Pojęcia”, plakietki) zwężony do szerokości kolumny karty — plakietki
przechodzą do drugiego wiersza, jak w węższym oknie — a pod nim wybrana karta od tytułu do końca bloku „Jak czytać”
(dwa pasy sklejone na tle strony; przełącznik sekcji, „Warunki”, „Skąd dane” i link PDF karty są poza kadrem).
Liczby na wykresie pochodzą z gui/static/data/wydajnosc.json, więc zrzut nie wymaga pomiarów ani zadań.

Skrypt sam uruchamia GUI (python -m gui na wolnym porcie) i niczego nie zostawia w results/gui: zakładka nie tworzy
zadań, a gdyby backend przy starcie albo zamknięciu przepisał results/gui/jobs.json, plik wraca do treści sprzed
skryptu. Na końcu wypisuje błędy konsoli JS; kod wyjścia 1, gdy były błędy.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from screenshots import ROOT, api, free_port  # noqa: E402

GUI_RESULTS = ROOT / "results" / "gui"
JOBS_FILE = GUI_RESULTS / "jobs.json"
GAP = 14  # odstęp między sklejanymi pasami [px CSS]


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def snapshot() -> tuple[set[str], bytes | None]:
    """Stan results/gui przed skryptem: lista plików i treść jobs.json (do porównania i odtworzenia)."""
    files = {p.relative_to(GUI_RESULTS).as_posix() for p in GUI_RESULTS.rglob("*")} if GUI_RESULTS.is_dir() else set()
    return files, JOBS_FILE.read_bytes() if JOBS_FILE.is_file() else None


def restore(before: tuple[set[str], bytes | None]) -> None:
    files, jobs = before
    if jobs is not None and JOBS_FILE.read_bytes() != jobs:
        JOBS_FILE.write_bytes(jobs)
        print("  results/gui/jobs.json przywrócony do stanu sprzed skryptu")
    now, _ = snapshot()
    extra = sorted(now - files)
    if extra:
        print("  UWAGA: nowe pliki w results/gui:", ", ".join(extra))


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "docs" / "img" / "raport-2" / "gui_wydajnosc.png"))
    ap.add_argument("--section", default="omp", help="sekcja zakładki (summary, seq, omp, mpi, mpiio, tests)")
    ap.add_argument("--card", default="omp_skalowanie", help="id karty wykresu (wydajnosc.json, charts[].id)")
    ap.add_argument("--full", default=None, help="dodatkowo zrzut całej strony do tego pliku (wybór kadru)")
    ap.add_argument("--dpr", type=float, default=2.0)
    args = ap.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    before = snapshot()

    from playwright.sync_api import sync_playwright

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    server = subprocess.Popen([sys.executable, "-m", "gui", "--no-browser", "--port", str(port)], cwd=ROOT)
    console: list[str] = []
    errors: list[str] = []
    try:
        for _ in range(100):
            try:
                api(base, "/api/info")
                break
            except OSError:
                time.sleep(0.2)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(viewport={"width": 1600, "height": 900}, device_scale_factor=args.dpr,
                                      color_scheme="light")
            ctx.add_init_script("try { localStorage.setItem('volcano.theme', 'light'); "
                                f"localStorage.setItem('volcano.perf.section', '{args.section}'); "
                                "localStorage.setItem('volcano.perf.compiler', 'msvc'); } catch (e) {}")
            page = ctx.new_page()

            def on_console(m):
                if m.type in ("error", "warning"):
                    console.append(f"{m.type}: {m.text}")
                    if m.type == "error":
                        errors.append(m.text)

            page.on("console", on_console)
            page.on("pageerror", lambda e: (console.append(f"pageerror: {e}"), errors.append(str(e))))
            page.goto(base + "/#perf")
            card = f"#perf-{args.card}"
            page.wait_for_selector(f"{card} canvas", timeout=30000)
            page.wait_for_selector(".perf-head .perf-badge", timeout=30000)
            page.wait_for_timeout(1500)  # animacje Chart.js
            if args.full:
                page.screenshot(path=args.full, full_page=True)
                print(f"  zapisano {rel(Path(args.full))}")
            shoot(page, card, out, args.dpr)
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=10)
        restore(before)

    print("Konsola przeglądarki:", "brak błędów i ostrzeżeń" if not console else "")
    for line in console:
        print("  " + line)
    return 1 if errors else 0


def rect(page, sel: str) -> dict:
    """Prostokąt elementu względem początku strony [px CSS]."""
    return page.evaluate("""(sel) => { const r = document.querySelector(sel).getBoundingClientRect();
        return { x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height }; }""", sel)


def shoot(page, card: str, out: Path, dpr: float) -> None:
    """Dwa pasy sklejone jeden pod drugim na tle strony: (1) nagłówek zakładki zwężony do szerokości kolumny karty
    (plakietki zgodności przechodzą do drugiego wiersza, jak w węższym oknie), (2) karta od tytułu do końca bloku
    „Jak czytać”."""
    from PIL import Image

    c = rect(page, card)
    page.add_style_tag(content=f".perf-head {{ max-width: {c['w']:.0f}px; }}")
    page.wait_for_timeout(800)
    head, c = rect(page, ".perf-head"), rect(page, card)
    howto = page.evaluate("""(sel) => { const box = document.querySelector(sel + ' .perf-howto');
        return box ? box.getBoundingClientRect().bottom + scrollY : null; }""", card)
    tmp = out.with_suffix(".tmp.png")
    page.screenshot(path=str(tmp), full_page=True)
    d = dpr
    with Image.open(tmp) as im:
        bg = im.getpixel((int(4 * d), int((head["y"] + head["h"] + 4) * d)))[:3]
        m = 2  # margines wokół kart (cień i zaokrąglone rogi)
        parts = [im.crop(tuple(round(v * d) for v in (head["x"] - m, head["y"] - m, head["x"] + head["w"] + m,
                                                      head["y"] + head["h"] + m))),
                 im.crop(tuple(round(v * d) for v in (c["x"] - m, c["y"] - m, c["x"] + c["w"] + m,
                                                      (howto + 5) if howto else c["y"] + c["h"] + m)))]
        gap = round(GAP * d)
        canvas = Image.new("RGB", (max(q.width for q in parts), sum(q.height for q in parts) + gap), bg)
        canvas.paste(parts[0], (0, 0))
        canvas.paste(parts[1], (0, parts[0].height + gap))
        canvas.save(out, optimize=True)
    tmp.unlink()
    print(f"  zapisano {rel(out)} ({canvas.width}×{canvas.height} px)")


if __name__ == "__main__":
    sys.exit(main())
