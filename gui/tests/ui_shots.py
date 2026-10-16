"""Zrzuty wyglądu GUI (etap 7: „przed / po”, motywy, rozdzielczości) i pomiar płynności odtwarzania 3D.

W odróżnieniu od screenshots.py ten skrypt NICZEGO nie tworzy (bez zadań, serii i importów) — tylko ogląda
istniejące wyniki, więc nie zostawia śladów w configs/gui/ ani results/gui/. Nie nadpisuje docs/img/gui_*.png.

    python gui/tests/ui_shots.py --prefix ui_przed                      # 8 zakładek -> docs/img/ui_przed_<zakładka>.png
    python gui/tests/ui_shots.py --prefix ui_po --theme dark
    python gui/tests/ui_shots.py --prefix ui_jasny --theme light --tabs form,view3d,compare
    python gui/tests/ui_shots.py --prefix x --size 1280x720 --out <katalog>   # kontrola układu przy małym ekranie
    python gui/tests/ui_shots.py --size 1024x576 --dpr 1.25 …          # 1280×720 przy skalowaniu Windows 125%
    python gui/tests/ui_shots.py --fps                                  # FPS odtwarzania etna_real (powierzchnia, woksele)

--theme ustawia motyw przed wczytaniem strony (prefers-color-scheme + localStorage „volcano.theme”); bez --theme
przeglądarka zgłasza jasny schemat systemu. Na końcu wypisuje błędy konsoli JS i poziome przewijanie strony
(szerokość dokumentu > okno); kod wyjścia 1, gdy były błędy JS.
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from screenshots import ROOT, api, free_port  # noqa: E402

TABS = ["form", "series", "jobs", "results", "compare", "view2d", "view3d", "stats"]
# Dodatkowe stany (--tabs …): odtwarzanie erupcji w 3D (Etna, powierzchnia i woksele) i 2D (Wezuwiusz), pole temperatury,
# formularz z błędem walidacji przy polu.
EXTRA = ["replay3d", "replay3d_vox", "replay2d", "temp2d", "form_error"]
NAMES = {"form": "nowa_symulacja", "series": "seria", "jobs": "zadania", "results": "wyniki", "compare": "porownanie",
         "view2d": "podglad_2d", "view3d": "podglad_3d", "stats": "czasy", "replay3d": "odtwarzanie_3d",
         "replay3d_vox": "odtwarzanie_3d_woksele", "replay2d": "odtwarzanie_2d", "temp2d": "temperatura_2d",
         "form_error": "formularz_blad"}
CA_VS_MC = "gui/series/20261010-212000_ca_vs_mc"   # pełna seria CA vs MC (pomiar z etapu 5)


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="ui")
    ap.add_argument("--out", default=str(ROOT / "docs" / "img"))
    ap.add_argument("--size", default="1440x900", help="okno przeglądarki w pikselach CSS, np. 1280x720")
    ap.add_argument("--dpr", type=float, default=1.0, help="device pixel ratio (1.25 = skalowanie Windows 125%%)")
    ap.add_argument("--theme", choices=["dark", "light"], default=None)
    ap.add_argument("--tabs", default=",".join(TABS))
    ap.add_argument("--full", action="store_true", help="zrzut całej strony (nie tylko okna)")
    ap.add_argument("--fps", action="store_true", help="pomiar płynności odtwarzania etna_real zamiast zrzutów")
    ap.add_argument("--headed", action="store_true", help="okno przeglądarki (GPU) zamiast trybu headless")
    ap.add_argument("--uncapped", action="store_true",
                    help="bez synchronizacji z odświeżaniem ekranu (FPS powyżej 60 — przepustowość klatek z GPU)")
    args = ap.parse_args()
    width, height = (int(v) for v in args.size.lower().split("x"))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import sync_playwright

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    server = subprocess.Popen([sys.executable, "-m", "gui", "--no-browser", "--port", str(port)], cwd=ROOT)
    console: list[str] = []
    errors: list[str] = []
    overflow: list[str] = []
    try:
        for _ in range(100):
            try:
                api(base, "/api/info")
                break
            except OSError:
                time.sleep(0.2)
        with sync_playwright() as p:
            flags = ["--use-angle=d3d11", "--ignore-gpu-blocklist"]
            if args.uncapped:
                flags += ["--disable-gpu-vsync", "--disable-frame-rate-limit"]
            browser = p.chromium.launch(headless=not args.headed, args=flags)
            ctx = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=args.dpr,
                                      color_scheme=args.theme or "light")
            if args.theme:
                ctx.add_init_script(f"try {{ localStorage.setItem('volcano.theme', '{args.theme}'); }} catch (e) {{}}")
            page = ctx.new_page()

            def on_console(m):
                if m.type in ("error", "warning") and "GPU stall due to ReadPixels" not in m.text:
                    console.append(f"{m.type}: {m.text}")
                    if m.type == "error":
                        errors.append(m.text)

            page.on("console", on_console)
            page.on("pageerror", lambda e: (console.append(f"pageerror: {e}"), errors.append(str(e))))

            def idle(sel: str):
                page.wait_for_selector(sel, state="hidden", timeout=60000)
                page.wait_for_timeout(300)

            def select_result(rid: str, loading: str):
                page.select_option("#result-select", rid)
                page.wait_for_function("(rid) => document.querySelector('#result-info').textContent.includes('results/' + rid)",
                                       arg=rid, timeout=60000)
                page.wait_for_timeout(300)
                idle(loading)

            def check_overflow(tab: str):
                sw = page.evaluate("() => [document.documentElement.scrollWidth, window.innerWidth]")
                if sw[0] > sw[1] + 1:
                    overflow.append(f"{tab}: szerokość dokumentu {sw[0]} px > okno {sw[1]} px")

            def shot(tab: str):
                if tab != "form_error":  # błąd przy polu — widok przewinięty do pola
                    page.evaluate("window.scrollTo(0, 0)")
                page.wait_for_timeout(500)
                check_overflow(tab)
                path = out / f"{args.prefix}_{NAMES[tab]}.png"
                page.screenshot(path=str(path), full_page=args.full)
                print(f"  zapisano {path}")

            if args.fps:
                measure_fps(page, base, idle, select_result)
            else:
                page.goto(base + "/#form")
                page.wait_for_selector("#f-vents-count")
                for tab in args.tabs.split(","):
                    show_tab(page, base, tab, idle, select_result)
                    shot(tab)
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=10)

    for line in overflow:
        print("  POZIOME PRZEWIJANIE:", line)
    print("Konsola przeglądarki:", "brak błędów i ostrzeżeń" if not console else "")
    for line in console:
        print("  " + line)
    return 1 if errors else 0


def show_tab(page, base, tab, idle, select_result) -> None:
    """Ustawia zakładkę w stanie do zrzutu (tylko oglądanie istniejących wyników)."""
    if tab == "form":
        page.goto(base + "/#form")
        page.wait_for_selector("#f-vents-count")
        page.select_option("#preset-select", "configs/etna_real.json")
        page.wait_for_selector("#vp-card:not([hidden])")
        page.wait_for_timeout(1200)
    elif tab == "series":
        page.goto(base + "/#series")
        page.click("button[data-template=ca_vs_mc]")
        page.wait_for_selector("#series-preview-table tbody tr")
        page.wait_for_timeout(800)
    elif tab == "jobs":
        page.goto(base + "/#jobs")
        page.wait_for_selector("#jobs-table tbody tr")
        page.wait_for_timeout(800)
    elif tab == "results":
        page.goto(base + "/#results")
        page.wait_for_selector("#results-table tbody tr")
        page.wait_for_timeout(500)
    elif tab == "compare":
        page.goto(base + "/#compare")
        page.wait_for_selector(f"#cmp-source option[value='{CA_VS_MC}']", state="attached", timeout=30000)
        page.select_option("#cmp-source", CA_VS_MC)
        page.wait_for_function("() => document.querySelectorAll('#cmp-charts canvas').length === 2", timeout=30000)
        page.wait_for_function("() => document.querySelectorAll('#cmp-gallery figure').length > 0", timeout=30000)
        page.wait_for_timeout(3000)
    elif tab == "view2d":
        page.goto(base + "/#view2d")
        page.wait_for_selector("#result-select option", state="attached")
        select_result("wezuwiusz_real", "#v2-loading")
        page.check("input[name=v2-axis][value=y]")
        page.fill("#v2-index-num", "71")
        page.press("#v2-index-num", "Enter")
        page.select_option("#v2-field", "flowId")
        idle("#v2-loading")
        box = page.locator("#v2-canvas").bounding_box()
        page.mouse.move(box["x"] + box["width"] * 0.5, box["y"] + box["height"] * 0.42)
        page.wait_for_timeout(600)
    elif tab == "view3d":
        page.goto(base + "/#view3d")
        page.wait_for_selector("#result-select option", state="attached")
        select_result("etna_real", "#v3-loading")
        page.check("input[name=v3-mode][value=surface]")
        idle("#v3-loading")
        page.select_option("#v3-field", "type")
        idle("#v3-loading")
        page.wait_for_timeout(800)
    elif tab == "stats":
        page.goto(base + "/#stats")
        page.wait_for_selector("#result-select option", state="attached")
        page.select_option("#result-select", "lava_mc_3d")
        page.wait_for_selector("#ch-grains", timeout=30000)
        page.wait_for_timeout(800)
    elif tab in ("replay3d", "replay3d_vox"):
        page.goto(base + "/#view3d")
        page.wait_for_selector("#result-select option", state="attached")
        select_result("etna_real", "#v3-loading")
        page.check(f"input[name=v3-mode][value={'surface' if tab == 'replay3d' else 'voxels'}]")
        idle("#v3-loading")
        if not page.is_checked("#v3-replay-on"):
            page.check("#v3-replay-on")
        page.wait_for_function("() => document.querySelector('#v3-replay-label').textContent.includes('/')", timeout=60000)
        idle("#v3-loading")
        set_step(page, "v3", 60 if tab == "replay3d" else 120, idle, "#v3-loading")
    elif tab == "replay2d":
        page.goto(base + "/#view2d")
        page.wait_for_selector("#result-select option", state="attached")
        select_result("wezuwiusz_real", "#v2-loading")
        page.check("input[name=v2-axis][value=y]")
        page.fill("#v2-index-num", "71")
        page.press("#v2-index-num", "Enter")
        idle("#v2-loading")
        if not page.is_checked("#v2-replay-on"):
            page.check("#v2-replay-on")
        page.wait_for_function("() => document.querySelector('#v2-replay-label').textContent.includes('/')", timeout=60000)
        idle("#v2-loading")
        set_step(page, "v2", 40, idle, "#v2-loading")
    elif tab == "temp2d":
        page.goto(base + "/#view2d")
        page.wait_for_selector("#result-select option", state="attached")
        select_result("test_2d", "#v2-loading")
        if page.is_checked("#v2-replay-on"):
            page.uncheck("#v2-replay-on")
            idle("#v2-loading")
        page.select_option("#v2-field", "temp")
        idle("#v2-loading")
    elif tab == "form_error":
        page.goto(base + "/#form")
        page.wait_for_selector("#f-vents-count")
        page.select_option("#preset-select", "configs/test_3d.json")
        page.fill("#f-space-nx", "-5")
        page.click("#btn-validate")
        page.wait_for_selector("#validation .notice.error")
        page.locator("#f-space-nx").scroll_into_view_if_needed()
        page.wait_for_timeout(400)


def set_step(page, prefix: str, k: int, idle, loading: str) -> None:
    """Suwak odtwarzania na krok k (zdarzenie input — jak przeciągnięcie)."""
    page.evaluate("([p, k]) => { const t = document.querySelector(`#${p}-replay-time`); t.value = k;"
                  " t.dispatchEvent(new Event('input')); }", [prefix, k])
    page.wait_for_timeout(300)
    idle(loading)
    page.wait_for_timeout(500)


def measure_fps(page, base, idle, select_result) -> None:
    """Płynność odtwarzania erupcji etna_real w 3D: każdy krok CA jako osobna klatka (suwak -> zdarzenie input),
    z czekaniem na requestAnimationFrame między klatkami (FPS = klatki / czas) oraz sam czas klatki w JS
    (updateReplay + render, bez czekania na ekran). 3 przebiegi, mediana."""
    page.goto(base + "/#view3d")
    page.wait_for_selector("#result-select option", state="attached")
    select_result("etna_real", "#v3-loading")
    gpu = page.evaluate("""() => { const c = document.createElement('canvas').getContext('webgl2');
        const d = c && c.getExtension('WEBGL_debug_renderer_info');
        return d ? c.getParameter(d.UNMASKED_RENDERER_WEBGL) : 'nieznany'; }""")
    print(f"  WebGL: {gpu}")
    page.check("#v3-replay-on")
    page.wait_for_selector("#v3-replay-bar:not([hidden])")
    for mode in ("surface", "voxels"):
        page.check(f"input[name=v3-mode][value={mode}]")
        idle("#v3-loading")
        page.wait_for_function("() => document.querySelector('#v3-replay-label').textContent.includes('/')", timeout=60000)
        fps, cpu = [], []
        for _ in range(3):
            r = page.evaluate("""async () => {
                const t = document.querySelector('#v3-replay-time');
                const last = Number(t.max);
                const raf = () => new Promise((res) => requestAnimationFrame(res));
                let cpu = 0;
                await raf();
                const t0 = performance.now();
                for (let k = 0; k <= last; k++) {
                  const a = performance.now();
                  t.value = k; t.dispatchEvent(new Event('input'));
                  cpu += performance.now() - a;
                  await raf();
                }
                const el = performance.now() - t0;
                return { frames: last + 1, ms: el, cpu: cpu / (last + 1) };
            }""")
            fps.append(r["frames"] / (r["ms"] / 1000))
            cpu.append(r["cpu"])
        print(f"  {mode}: {r['frames']} klatek, FPS (z czekaniem na klatkę ekranu) mediana {statistics.median(fps):.1f}"
              f" [{', '.join(f'{v:.1f}' for v in fps)}], czas klatki JS mediana {statistics.median(cpu):.2f} ms"
              f" [{', '.join(f'{v:.2f}' for v in cpu)}]")
        print("  JSON " + json.dumps({"mode": mode, "fps": fps, "cpuMs": cpu, "gpu": gpu}))


if __name__ == "__main__":
    sys.exit(main())
