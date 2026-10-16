"""Zrzuty ekranu GUI do raportu + scenariusz end-to-end w prawdziwej przeglądarce (Playwright, Chromium).

Uruchomienie (z katalogu volcano-ca-mc, po `pip install -r gui/requirements-dev.txt`
i `python -m playwright install chromium`):

    python gui/tests/screenshots.py            # zrzuty do docs/img/gui_*.png (scenariusze etapów 4–6)
    python gui/tests/screenshots.py --only-series   # tylko ekrany etapu 5 (seria, kolejka, porównanie, mapy wysokości)
    python gui/tests/screenshots.py --skip-series   # bez ekranów etapu 5
    python gui/tests/screenshots.py --only-real   # tylko etap 6: docs/img/real_*.png, replay_*.png (prawdziwe wulkany,
                                                  # odtwarzanie erupcji; brakujące wyniki liczy silnik)
    python gui/tests/screenshots.py --out X    # inny katalog
    python gui/tests/screenshots.py --theme light   # motyw jasny „popiół” (domyślnie ciemny „bazalt”, etap 7)

Skrypt sam uruchamia GUI (python -m gui na wolnym porcie), przechodzi scenariusz z docs/etap-4-gui.md:
preset test_3d -> zmiana nazwy i liczby kraterów -> Sprawdź -> Uruchom (+ lava_mc_3d i mc_full_2d w kolejce)
-> postęp w zakładce Zadania -> log -> Wyniki -> podgląd 2D (typ, flowId, kryształy) -> podgląd 3D (ściany,
powierzchnia, woksele) -> Czasy i statystyki -> duży wynik etna_3d. Zadania tworzą prawdziwe configi
w configs/gui/ i foldery w results/gui/ (nazwy demo_*).
Etap 5 (etap5()): preset heightmap_kaldera (panel mapy wysokości z miniaturą) -> import obrazu PNG mapy
(plik tymczasowy, usuwany na końcu) -> powierzchnia 3D wyniku heightmap_kaldera -> kolejka wstrzymana -> szablon
serii „Wpływ sąsiedztwa” -> Uruchom serię -> Zadania: grupa serii, zmiana kolejności, wznowienie, postęp i czas
do końca -> Porównanie (wykres słupkowy sąsiedztw) -> Porównanie najnowszej pełnej serii „CA vs MC” (wykres
log–log 2D/3D, tabela, galeria mikrostruktur). Zrzuty docs/img/gui_heightmap*.png, gui_seria*.png,
gui_zadania_seria*.png, gui_porownanie*.png.

Etap 6 (etap6()): presety etna_real / wezuwiusz_real — panel „Kratery na mapie” (mapa, kratery, szer./dł. pod kursorem),
powierzchnia 3D po erupcji (Etna szczytowa i boczna, Wezuwiusz), odtwarzanie erupcji Etny w 3D (klatki kroków 8, 60, 150,
230 + woksele), przekrój 2D Wezuwiusza w kilku krokach, krystalizacja MC z migawek. Zrzuty docs/img/real_*.png, replay_*.png.

Na końcu wypisuje błędy i ostrzeżenia z konsoli przeglądarki; kod wyjścia 1, gdy były błędy JS.
"""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Strona i tabele (od etapu 7 tabele mają własny obszar przewijania z przyklejonym nagłówkiem) na początek.
SCROLL_TOP = "window.scrollTo(0, 0); document.querySelectorAll('.table-scroll').forEach((e) => { e.scrollTop = 0; })"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def api(base: str, path: str):
    with urllib.request.urlopen(base + path, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def wait_jobs(base: str, ids: list[str], timeout: float = 300) -> list[dict]:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        jobs = {j["id"]: j for j in api(base, "/api/jobs")}
        if all(jobs[i]["status"] not in ("queued", "running") for i in ids):
            return [jobs[i] for i in ids]
        time.sleep(0.5)
    raise TimeoutError("zadania nie skończyły się w czasie")


def api_post(base: str, path: str, body: dict):
    req = urllib.request.Request(base + path, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def etap5(page, base, shot, element_shot, idle, select_result, errors, timings) -> None:
    """Ekrany etapu 5: mapa wysokości, seria z kolejką, porównanie (opis scenariusza w docstringu modułu)."""
    # ---- mapa wysokości: preset z terenem z pliku -> panel mapy z miniaturą
    page.goto(base + "/#form")
    page.wait_for_selector("#f-vents-count")
    page.select_option("#preset-select", "configs/heightmap_kaldera.json")
    page.wait_for_timeout(1000)
    element_shot("#hm-card", "heightmap")
    # import obrazu PNG (ten sam obraz mapy w skali szarości, który zapisuje tools/make_heightmaps.py)
    page.click("#hm-import-open")
    page.set_input_files("#hm-file", str(ROOT / "configs" / "heightmaps" / "kaldera_wylom.png"))
    for sel, val in (("#hm-name", "demo_kaldera_z_obrazu"), ("#hm-nx", "100"), ("#hm-ny", "100"), ("#hm-nz", "45"),
                     ("#hm-max", "35"), ("#hm-smooth", "1")):
        page.fill(sel, val)
    page.click("#hm-import-run")
    page.wait_for_selector("#hm-import-msg .notice.ok", timeout=30000)
    element_shot("#hm-card", "heightmap_import")
    for p in (ROOT / "configs" / "heightmaps").glob("demo_kaldera_z_obrazu*.csv"):
        p.unlink()  # zrzut zrobiony — import demonstracyjny nie zostaje w repozytorium
    if (ROOT / "results" / "heightmap_kaldera").is_dir():
        page.click(".tab[data-tab=view3d]")
        select_result("heightmap_kaldera", "#v3-loading")
        page.check("input[name=v3-mode][value=surface]")
        page.select_option("#v3-field", "crystal")
        idle("#v3-loading")
        page.wait_for_timeout(800)
        shot("heightmap_3d")

    # ---- seria z szablonu przy wstrzymanej kolejce: grupa, kolejność, potem postęp
    api_post(base, "/api/queue", {"paused": True})
    try:
        page.goto(base + "/#series")
        page.click("button[data-template=neighborhood]")
        page.wait_for_selector("#series-preview-table tbody tr")
        page.fill("#series-name", "demo_sasiedztwo")
        page.wait_for_timeout(1000)
        shot("seria", full=True)
        page.click("#series-run")
        page.wait_for_selector("#series-result .notice.ok", timeout=60000)
        element_shot("#tab-series .form-side .card", "seria_uruchomiono")
        sid = api(base, "/api/series")[0]["id"]
        page.goto(base + "/#jobs")
        page.wait_for_selector(f"tr[data-job='{sid}__08_hexagonal_MC']")
        page.click(f"tr[data-job='{sid}__08_hexagonal_MC'] button[data-act=up]")
        # Starsze serie zwinięte, widok od góry: pasek kolejki + grupa nowej serii.
        for other in [r.get_attribute("data-series") for r in page.locator("tr.group-row").all()]:
            if other != sid:  # lista jest renderowana od nowa po każdym kliknięciu — selektor za każdym razem świeży
                page.click(f"tr.group-row[data-series='{other}'] button[data-act=toggle]")
        page.evaluate(SCROLL_TOP)
        page.wait_for_timeout(1200)
        shot("zadania_seria_pauza")
        page.click("#queue-pause")  # wznowienie z GUI
        page.wait_for_timeout(2500)
        page.evaluate(SCROLL_TOP)
        shot("zadania_seria")
    finally:
        api_post(base, "/api/queue", {"paused": False})
    t0 = time.monotonic()
    while time.monotonic() - t0 < 300:
        c = next(s for s in api(base, "/api/series") if s["id"] == sid)["counts"]
        if c["queued"] + c["running"] == 0:
            break
        time.sleep(0.5)
    timings["seria sąsiedztwo (8 zadań)"] = time.monotonic() - t0
    if c["done"] != 8:
        errors.append(f"seria {sid}: {c}")

    # ---- porównanie: seria sąsiedztw (oś X kategoryczna -> słupki), potem pełna seria CA vs MC
    page.goto(base + "/#compare")
    page.select_option("#cmp-source", f"gui/series/{sid}")
    page.wait_for_function("() => document.querySelectorAll('#cmp-charts canvas').length > 0", timeout=30000)
    page.wait_for_timeout(1500)
    shot("porownanie_sasiedztwo", full=True)
    ca = next((s for s in api(base, "/api/compare/sources")
               if s.get("template") == "ca_vs_mc" and s["gui"] and s["jobs"] == 16 and s["done"] == 16), None)
    if ca:
        page.select_option("#cmp-source", ca["ref"])
        page.wait_for_function("() => document.querySelectorAll('#cmp-charts canvas').length === 2", timeout=30000)
        page.wait_for_function("() => [...document.querySelectorAll('#cmp-gallery figure')].length > 0", timeout=30000)
        page.wait_for_timeout(4000)  # miniatury galerii
        shot("porownanie", full=True)
        element_shot("#cmp-gallery", "porownanie_galeria")
        page.select_option("#cmp-y", "nsPerUnit")
        page.wait_for_timeout(800)
        element_shot("#tab-compare .card:nth-of-type(2)", "porownanie_koszt")
    else:
        errors.append("brak pełnej serii CA vs MC — uruchom najpierw python gui/tests/run_ca_vs_mc.py")


def ensure_result(rid: str, config: str, *overrides: str) -> None:
    """Wynik results/<rid> potrzebny do zrzutów — jeśli go nie ma, liczy go silnik (bez GUI)."""
    if (ROOT / "results" / rid / "ca_result.bin").is_file():
        return
    sys.path.insert(0, str(ROOT))
    from gui.settings import find_engine
    exe = find_engine(ROOT)
    args = [str(exe), "--config", f"configs/{config}.json", "--out", f"results/{rid}"]
    for o in overrides:
        args += ["--set", o]
    print(f"  liczę results/{rid} ({config}{' ' + ' '.join(overrides) if overrides else ''})…")
    subprocess.run(args, cwd=ROOT, check=True, capture_output=True)


def etap6(page, base, out, idle, select_result, errors, timings) -> None:
    """Ekrany etapu 6: prawdziwe wulkany (formularz z mapą i kraterami, powierzchnia 3D Etny i Wezuwiusza)
    i odtwarzanie erupcji krok po kroku (klatki 3D Etny, przekrój 2D Wezuwiusza, krystalizacja MC).
    Zrzuty docs/img/real_*.png i docs/img/replay_*.png."""
    def save(name: str, sel: str | None = None, full: bool = False):
        page.wait_for_timeout(400)
        path = out / f"{name}.png"
        (page.locator(sel).screenshot(path=str(path)) if sel else page.screenshot(path=str(path), full_page=full))
        print(f"  zapisano {path}")

    def set_step(prefix: str, k: int, loading: str):
        page.evaluate("([p, k]) => { const t = document.querySelector(`#${p}-replay-time`); t.value = k;"
                      " t.dispatchEvent(new Event('input')); }", [prefix, k])
        page.wait_for_timeout(300)
        idle(loading)
        page.wait_for_timeout(500)

    for rid in ("etna_real", "etna_real_boczna", "wezuwiusz_real"):
        ensure_result(rid, rid)
    ensure_result("replay_lava_mc_3d", "lava_mc_3d", "mc.snapshotsEvery=10", "output.snapshotsEvery=20")

    # ---- formularz: preset z prawdziwym terenem, panel „Kratery na mapie” (kursor nad kraterem — szer./dł.)
    page.goto(base + "/#form")
    page.wait_for_selector("#f-vents-count")
    for preset, name in (("etna_real", "real_formularz_kratery"), ("wezuwiusz_real", "real_formularz_wezuwiusz")):
        page.select_option("#preset-select", f"configs/{preset}.json")
        page.wait_for_selector("#vp-card:not([hidden])")
        page.wait_for_timeout(1200)
        cv = page.locator("#vp-canvas")
        cv.scroll_into_view_if_needed()
        box = cv.bounding_box()
        cv.hover(position={"x": box["width"] * 0.47, "y": box["height"] * 0.49})
        save(name, "#vp-card")
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_selector("#hm-card")
    save("real_mapa_wysokosci", "#hm-card")

    # ---- powierzchnia 3D po erupcji (kolor = krater)
    page.goto(base + "/#view3d")
    page.wait_for_selector("#result-select option", state="attached")
    page.check("input[name=v3-mode][value=surface]")
    for rid, name in (("etna_real", "real_etna_3d"), ("etna_real_boczna", "real_etna_boczna_3d"),
                      ("wezuwiusz_real", "real_wezuwiusz_3d")):
        t0 = time.monotonic()
        select_result(rid, "#v3-loading")
        page.select_option("#v3-field", "flowId")
        idle("#v3-loading")
        timings[f"{rid} 3D powierzchnia"] = time.monotonic() - t0
        save(name)

    # ---- odtwarzanie erupcji Etny w 3D (powierzchnia): początek, spływ, koniec erupcji, zastyganie
    select_result("etna_real", "#v3-loading")
    page.check("#v3-replay-on")
    page.wait_for_selector("#v3-replay-bar:not([hidden])")
    idle("#v3-loading")
    page.wait_for_function("() => document.querySelector('#v3-replay-label').textContent.includes('/')", timeout=60000)
    for k in (8, 60, 150, 230):
        set_step("v3", k, "#v3-loading")
        save(f"replay_etna_3d_{k:03d}")
    page.check("input[name=v3-mode][value=voxels]")
    idle("#v3-loading")
    set_step("v3", 120, "#v3-loading")
    save("replay_etna_3d_woksele")
    page.uncheck("#v3-replay-on")
    page.check("input[name=v3-mode][value=surface]")

    # ---- odtwarzanie w 2D: przekrój przez krater Wezuwiusza (y = 71)
    page.click(".tab[data-tab=view2d]")
    select_result("wezuwiusz_real", "#v2-loading")
    page.check("input[name=v2-axis][value=y]")
    page.fill("#v2-index-num", "71")
    page.press("#v2-index-num", "Enter")
    idle("#v2-loading")
    page.check("#v2-replay-on")
    page.wait_for_function("() => document.querySelector('#v2-replay-label').textContent.includes('/')", timeout=60000)
    idle("#v2-loading")
    for k in (6, 40, 128):
        set_step("v2", k, "#v2-loading")
        save(f"replay_wezuwiusz_2d_{k:03d}")

    # ---- krystalizacja MC z migawek (lava_mc_3d, mc.snapshotsEvery = 10)
    select_result("replay_lava_mc_3d", "#v2-loading")
    page.wait_for_timeout(500)
    if not page.is_checked("#v2-replay-on"):
        page.check("#v2-replay-on")
    page.select_option("#v2-replay-source", "mc")
    idle("#v2-loading")
    page.check("input[name=v2-axis][value=y]")
    page.fill("#v2-index-num", "40")
    page.press("#v2-index-num", "Enter")
    idle("#v2-loading")
    for k in (0, 2, 20):
        set_step("v2", k, "#v2-loading")
        save(f"replay_mc_2d_{k:02d}")
    page.uncheck("#v2-replay-on")
    label = page.inner_text("#v2-replay-label")
    if "MCS" not in label:
        errors.append(f"odtwarzanie MC: nieoczekiwana etykieta {label!r}")


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "docs" / "img"))
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--only-series", action="store_true", help="tylko ekrany etapu 5 (seria, kolejka, porównanie)")
    ap.add_argument("--skip-series", action="store_true", help="bez ekranów etapu 5")
    ap.add_argument("--only-real", action="store_true", help="tylko ekrany etapu 6 (prawdziwe wulkany, odtwarzanie)")
    ap.add_argument("--skip-real", action="store_true", help="bez ekranów etapu 6")
    ap.add_argument("--theme", choices=["dark", "light"], default="dark", help="motyw GUI (etap 7); dokumentacja: dark")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import sync_playwright

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    server = subprocess.Popen([sys.executable, "-m", "gui", "--no-browser", "--port", str(port)], cwd=ROOT)
    console: list[str] = []
    errors: list[str] = []
    timings: dict[str, float] = {}
    try:
        for _ in range(100):
            try:
                api(base, "/api/info")
                break
            except OSError:
                time.sleep(0.2)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            # Motyw przed wczytaniem strony: ustawienie systemu (prefers-color-scheme) + wybór zapamiętany w localStorage.
            ctx = browser.new_context(viewport={"width": args.width, "height": args.height}, device_scale_factor=1,
                                      color_scheme=args.theme)
            ctx.add_init_script(f"try {{ localStorage.setItem('volcano.theme', '{args.theme}'); }} catch (e) {{}}")
            page = ctx.new_page()

            def on_console(m):
                if m.type in ("error", "warning") and "GPU stall due to ReadPixels" not in m.text:
                    console.append(f"{m.type}: {m.text}")
                    if m.type == "error":
                        errors.append(m.text)

            page.on("console", on_console)
            page.on("pageerror", lambda e: (console.append(f"pageerror: {e}"), errors.append(str(e))))

            def shot(name: str, full: bool = False):
                page.wait_for_timeout(400)
                page.screenshot(path=str(out / f"gui_{name}.png"), full_page=full)
                print(f"  zapisano {out / f'gui_{name}.png'}")

            def element_shot(sel: str, name: str):
                page.wait_for_timeout(400)
                page.locator(sel).screenshot(path=str(out / f"gui_{name}.png"))
                print(f"  zapisano {out / f'gui_{name}.png'}")

            def idle(sel: str):
                page.wait_for_selector(sel, state="hidden", timeout=60000)
                page.wait_for_timeout(300)


            def select_result(rid: str, loading: str):
                """Wybór wyniku z listy nad podglądem; czeka na metadane (pasek wyniku) i na dane podglądu."""
                page.select_option("#result-select", rid)
                page.wait_for_function("(rid) => document.querySelector('#result-info').textContent.includes('results/' + rid)",
                                       arg=rid, timeout=60000)
                page.wait_for_timeout(300)
                idle(loading)

            if not args.only_series and not args.only_real:  # scenariusz etapu 4
                # ---- 1. Nowa symulacja: preset test_3d, zmiana nazwy i liczby kraterów, Sprawdź, Uruchom
                page.goto(base + "/#form")
                page.wait_for_selector("#f-vents-count")
                page.select_option("#preset-select", "configs/test_3d.json")
                page.fill("#job-name", "demo_test_3d_5_kraterow")
                page.fill("#f-vents-count", "5")
                page.click("#btn-validate")
                page.wait_for_selector("#validation .notice.ok")
                shot("formularz")
                # Błędny parametr -> czytelny błąd silnika w formularzu.
                page.fill("#f-space-nx", "-5")
                page.click("#btn-validate")
                page.wait_for_selector("#validation .notice.error")
                page.evaluate("window.scrollTo(0, 0)")
                shot("formularz_blad")
                page.fill("#f-space-nx", "64")
                page.click("#btn-run")
                page.wait_for_selector("#run-result .notice.ok")
                shot("formularz_uruchomiono")
                ids = [api(base, "/api/jobs")[0]["id"]]
                for preset, name in (("configs/lava_mc_3d.json", "demo_lava_mc_3d"), ("configs/mc_full_2d.json", "demo_mc_full_2d")):
                    page.select_option("#preset-select", preset)
                    page.fill("#job-name", name)
                    page.click("#btn-run")
                    page.wait_for_selector("#run-result .notice.ok")
                    ids.append(next(j["id"] for j in api(base, "/api/jobs") if j["name"] == name))

                # ---- 2. Zadania: kolejka i postęp, potem log
                page.goto(base + "/#jobs")
                page.wait_for_timeout(1500)
                shot("zadania_postep")
                jobs = wait_jobs(base, ids)
                for j in jobs:
                    print(f"  zadanie {j['id']}: {j['status']}, {j['durationS']} s")
                    if j["status"] != "done":
                        errors.append(f"zadanie {j['id']} zakończone statusem {j['status']}: {j.get('error')}")
                page.wait_for_timeout(1500)
                page.click(f"tr[data-job='{ids[1]}'] button[data-act=log]")
                page.wait_for_timeout(800)
                shot("zadania")

                # ---- 3. Wyniki
                page.goto(base + "/#results")
                page.wait_for_selector(f"tr[data-id='gui/{ids[0]}']")
                shot("wyniki")

                # ---- 4. Podgląd 2D: test_3d z GUI — typ i flowId (warstwa z z największą ilością lawy)
                rid = f"gui/{ids[0]}"
                page.click(f"tr[data-id='{rid}'] button[data-act='2d']")
                idle("#v2-loading")
                nz = api(base, f"/api/result?id={rid}")["dims"][2]
                best, best_z = -1, nz // 2
                for z in range(nz):
                    with urllib.request.urlopen(f"{base}/api/result/slice?id={rid}&field=type&axis=z&index={z}") as r:
                        data = r.read()
                    count = sum(1 for b in data if b in (2, 3))
                    if count > best:
                        best, best_z = count, z
                page.check("input[name=v2-axis][value=y]")
                idle("#v2-loading")
                shot("2d_typ")
                page.check("input[name=v2-axis][value=z]")
                page.fill("#v2-index-num", str(best_z))
                page.press("#v2-index-num", "Enter")
                page.select_option("#v2-field", "flowId")
                idle("#v2-loading")
                box = page.locator("#v2-canvas").bounding_box()
                page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                page.wait_for_timeout(600)
                shot("2d_flowid")

                # MC: kryształy lava_mc_3d (przekrój przez krater, powiększenie, granice ziaren) i mc_full_2d
                select_result(f"gui/{ids[1]}", "#v2-loading")
                page.select_option("#v2-field", "crystal")
                page.check("input[name=v2-axis][value=y]")
                page.fill("#v2-index-num", "40")
                page.press("#v2-index-num", "Enter")
                page.check("#v2-boundaries")
                idle("#v2-loading")
                # Powiększenie ×~2 wokół krateru (środek przekroju, górna część stożka) + podpowiedź nad bazaltem.
                box = page.locator("#v2-canvas").bounding_box()
                cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] * 0.45
                page.mouse.move(cx, cy)
                for _ in range(2):
                    page.mouse.wheel(0, -250)
                    page.wait_for_timeout(80)
                page.wait_for_timeout(300)
                shot("2d_krysztaly_lava")
                select_result(f"gui/{ids[2]}", "#v2-loading")
                page.select_option("#v2-field", "crystal")
                page.check("#v2-boundaries")
                idle("#v2-loading")
                shot("2d_krysztaly_mc_full")

                # ---- 5. Podgląd 3D: ściany zewnętrzne, powierzchnia, woksele
                select_result(rid, "#v2-loading")
                page.click(".tab[data-tab=view3d]")
                idle("#v3-loading")
                page.wait_for_timeout(800)
                shot("3d_sciany")
                page.uncheck("#v3-top-surface")
                idle("#v3-loading")
                shot("3d_sciany_warstwa")
                page.check("input[name=v3-mode][value=surface]")
                idle("#v3-loading")
                shot("3d_powierzchnia")
                page.check("input[name=v3-mode][value=voxels]")
                idle("#v3-loading")
                shot("3d_woksele")
                select_result(f"gui/{ids[1]}", "#v3-loading")
                page.check("input[name=v3-mode][value=surface]")
                page.select_option("#v3-field", "crystal")
                idle("#v3-loading")
                shot("3d_krysztaly_powierzchnia")
                select_result("mc_full_3d", "#v3-loading")
                page.check("input[name=v3-mode][value=faces]")
                idle("#v3-loading")
                page.wait_for_timeout(500)
                shot("3d_mc_full_sciany")

                # ---- 6. Czasy i statystyki (lava + MC)
                select_result(f"gui/{ids[1]}", "#v3-loading")
                page.click(".tab[data-tab=stats]")
                page.wait_for_selector("#ch-grains")
                page.wait_for_timeout(800)
                shot("czasy", full=True)

                # ---- 7. Duży wynik (etna_3d, 1,8 mln komórek) — przeglądarka się nie zawiesza
                if (ROOT / "results" / "etna_3d").is_dir():
                    t0 = time.monotonic()
                    page.click(".tab[data-tab=view2d]")
                    select_result("etna_3d", "#v2-loading")
                    timings["etna_3d 2D"] = time.monotonic() - t0
                    t0 = time.monotonic()
                    page.click(".tab[data-tab=view3d]")
                    page.check("input[name=v3-mode][value=surface]")
                    page.select_option("#v3-field", "flowId")
                    idle("#v3-loading")
                    timings["etna_3d 3D powierzchnia"] = time.monotonic() - t0
                    shot("3d_etna_powierzchnia")

            if not args.skip_series and not args.only_real:
                etap5(page, base, shot, element_shot, idle, select_result, errors, timings)
            if not args.skip_real:
                etap6(page, base, out, idle, select_result, errors, timings)
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=10)

    for k, v in timings.items():
        print(f"  czas: {k}: {v:.2f} s")
    print("Konsola przeglądarki:", "brak błędów i ostrzeżeń" if not console else "")
    for line in console:
        print("  " + line)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
