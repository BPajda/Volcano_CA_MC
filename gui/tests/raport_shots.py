"""Zrzuty GUI do raportu 1 (docs/raport-1.md) — cztery ekrany jednej historii: konfiguracja → kolejka → erupcja 3D →
krystalizacja MC. Zapis do docs/img/raport/gui_1_konfiguracja.png, gui_2_kolejka.png, gui_3_erupcja_3d.png,
gui_4_krystalizacja_mc.png (domyślnie motyw jasny — raport jest drukowany na białym tle; --theme dark — ciemny;
okno 1600×900, deviceScaleFactor 2).

    python gui/tests/raport_shots.py                 # wszystkie 4 zrzuty (tworzy i na końcu usuwa zadanie Etny + serię)
    python gui/tests/raport_shots.py --shots 3,4 --etna etna_real   # tylko podglądy, na istniejącym wyniku (nic nie tworzy)
    python gui/tests/raport_shots.py --keep          # nie usuwaj utworzonych zadań (do obejrzenia w GUI)

Chronologia (te same dane w zrzutach 1→2→3):
  1. Nowa symulacja → preset etna_real (preset, nazwa zadania, „Podsumowanie i szacunek”, „Kratery na mapie” z kursorem
     nad szczytem). Karta mapy wysokości leży między nazwą zadania a mapą kraterów — w zrzucie jest wycięta (lewa
     kolumna sklejona z dwóch pasów, cięcie zaznaczone przerywaną linią), żeby zrzut zmieścił się w raporcie.
  2. Uruchom → zadanie Etny liczy się (przypięte, 1 worker), seria z szablonu „Lawa: liczba kraterów” (4 zadania) czeka za nim;
     kolejka wstrzymana (działające zadanie liczy się dalej), filtr „aktywne”.
  3. Podgląd 3D wyniku tego zadania → powierzchnia → odtwarzanie erupcji, krok 60, paleta „żar”.
  4. Podgląd 2D → lava_mc_2d_migawki → kryształ (MC) + granice ziaren, przybliżenie na krater i zbocze.

Skrypt sam uruchamia GUI (python -m gui na wolnym porcie). Utworzone zadanie i seria są po zrzutach anulowane / dokończone,
a na końcu usuwane: wpisy w results/gui/jobs.json, configs/gui/<id>.json, results/gui/<id>/, configs/gui/series/<id>/,
results/gui/series/<id>/ (tylko identyfikatory, których nie było przed startem skryptu). Stan kolejki (pauza, workery,
przypięcie) wraca do stanu sprzed skryptu. Na końcu wypisuje błędy konsoli JS; kod wyjścia 1, gdy były błędy.
"""

from __future__ import annotations

import argparse
import math
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from screenshots import ROOT, SCROLL_TOP, api, api_post, free_port  # noqa: E402

JOBS_FILE = ROOT / "results" / "gui" / "jobs.json"
ETNA_SUMMIT = (74, 82)       # najwyższa komórka mapy Etny (Krater Płn.-Wsch., docs/prawdziwe-wulkany.md)
REPLAY_STEP = 60
MC_RESULT = "lava_mc_2d_migawki"
# Okno przekroju 2D (komórki x, z): krater z jeziorem lawy (x ≈ 104–136) i prawe zbocze.
MC_WINDOW = (92, 196, 22, 62)
# Kamera 3D po „Reset kamery”: obrót (przeciągnięcie lewym [px CSS]), przybliżenie (odległość od celu × 0,95^zoom),
# przesunięcie kadru (przeciągnięcie prawym [px CSS]).
CAMERA_3D = {"rotate": (0, 0), "zoom": 13, "pan": (0, 85)}


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_jobs_file() -> dict:
    try:
        return json.loads(JOBS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 2, "queue": {}, "jobs": []}


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "docs" / "img" / "raport"))
    ap.add_argument("--shots", default="1,2,3,4")
    ap.add_argument("--etna", default=None, help="wynik do zrzutu 3, gdy zrzut 2 jest pominięty (np. etna_real)")
    ap.add_argument("--keep", action="store_true", help="nie usuwaj zadań utworzonych przez skrypt")
    ap.add_argument("--dpr", type=float, default=2.0)
    ap.add_argument("--theme", choices=["light", "dark"], default="light",
                    help="motyw GUI (raport: light — druk na białym tle; dark — np. zrzuty do README)")
    args = ap.parse_args()
    shots = {int(s) for s in args.shots.split(",")}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    before = read_jobs_file()
    known_jobs = {j["id"] for j in before.get("jobs", [])}
    queue_before = dict(before.get("queue") or {})

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
            browser = p.chromium.launch(headless=True, args=["--use-angle=d3d11", "--ignore-gpu-blocklist"])
            ctx = browser.new_context(viewport={"width": 1600, "height": 900}, device_scale_factor=args.dpr,
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
            shooter = Shooter(page, base, out, args.dpr)

            etna = args.etna or "etna_real"
            if 1 in shots or 2 in shots:
                shooter.configure_etna(save=1 in shots)
            if 2 in shots:
                etna = shooter.queue_shot()
            if 3 in shots:
                shooter.eruption_shot(etna)
            if 4 in shots:
                shooter.crystal_shot()
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=10)
        cleanup(known_jobs, queue_before, keep=args.keep)

    print("Konsola przeglądarki:", "brak błędów i ostrzeżeń" if not console else "")
    for line in console:
        print("  " + line)
    return 1 if errors else 0


class Shooter:
    """Kroki scenariusza; współrzędne elementów w pikselach CSS, obrazy w pikselach urządzenia (× dpr)."""

    def __init__(self, page, base: str, out: Path, dpr: float):
        self.page, self.base, self.out, self.dpr = page, base, out, dpr
        self.etna_job: str | None = None

    # ---------------------------------------------------------------- pomocnicze

    def idle(self, sel: str) -> None:
        self.page.wait_for_selector(sel, state="hidden", timeout=60000)
        self.page.wait_for_timeout(300)

    def select_result(self, rid: str, loading: str) -> None:
        page = self.page
        page.wait_for_selector(f"#result-select option[value='{rid}']", state="attached", timeout=30000)
        page.select_option("#result-select", rid)
        page.wait_for_function("(rid) => document.querySelector('#result-info').textContent.includes('results/' + rid)",
                               arg=rid, timeout=60000)
        page.wait_for_timeout(300)
        self.idle(loading)

    def rect(self, sel: str) -> dict:
        """Prostokąt elementu względem początku strony [px CSS]."""
        return self.page.evaluate("""(sel) => { const r = document.querySelector(sel).getBoundingClientRect();
            return { x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height }; }""", sel)

    def crop(self, src: Path, dst: Path, box: tuple[float, float, float, float]) -> None:
        from PIL import Image
        d = self.dpr
        with Image.open(src) as im:
            im.crop(tuple(round(v * d) for v in box)).save(dst, optimize=True)
        src.unlink()
        print(f"  zapisano {rel(dst)}")

    # ---------------------------------------------------------------- 1. konfiguracja

    def configure_etna(self, save: bool) -> None:
        page = self.page
        page.goto(self.base + "/#form")
        page.wait_for_selector("#f-vents-count")
        page.select_option("#preset-select", "configs/etna_real.json")
        page.wait_for_selector("#vp-card:not([hidden])")
        page.wait_for_timeout(1200)
        page.fill("#job-name", "etna_real")
        page.wait_for_timeout(300)
        if not save:
            return
        # Okno wysokie na cały górny fragment formularza (jak zrzut całej strony) — bez przewijania kursor zostaje
        # nad mapą, a przyklejony panel „Podsumowanie i szacunek” stoi na swoim miejscu.
        vp, hm, side = self.rect("#vp-card"), self.rect("#hm-card"), self.rect(".form-side")
        page.set_viewport_size({"width": 1600, "height": int(vp["y"] + vp["h"] + 20)})
        page.wait_for_timeout(600)
        vp, hm, side = self.rect("#vp-card"), self.rect("#hm-card"), self.rect(".form-side")
        cv = page.locator("#vp-canvas")
        box = cv.bounding_box()
        nx = ny = 160
        sc = box["width"] / nx
        x, y = ETNA_SUMMIT
        cv.hover(position={"x": (x + 0.5) * sc, "y": (ny - 1 - y + 0.5) * sc})
        page.wait_for_timeout(500)
        tmp = self.out / "_tmp_form.png"
        page.screenshot(path=str(tmp))
        page.set_viewport_size({"width": 1600, "height": 900})
        dst = self.out / "gui_1_konfiguracja.png"
        stitch_form(tmp, dst, self.dpr, split_x=side["x"] - 8, cut_from=hm["y"] - 8, cut_to=vp["y"] - 8,
                    bottom=vp["y"] + vp["h"] + 14)
        print(f"  zapisano {rel(dst)}")

    # ---------------------------------------------------------------- 2. kolejka

    def queue_shot(self) -> str:
        page, base = self.page, self.base
        api_post(base, "/api/queue", {"paused": False, "workers": 1, "pin": {"enabled": True}})
        page.goto(base + "/#form")  # formularz z kroku 1 jest już wypełniony (ta sama strona)
        page.wait_for_selector("#f-vents-count")
        if page.input_value("#preset-select") != "configs/etna_real.json":
            self.configure_etna(save=False)
        page.click("#btn-run")
        page.wait_for_selector("#run-result .notice.ok", timeout=60000)
        job = next(j for j in api(base, "/api/jobs") if j["name"] == "etna_real" and j["status"] in ("queued", "running"))
        self.etna_job = job["id"]
        # Kolejka wstrzymana zaraz po starcie Etny: zadanie działające liczy się dalej, nowe czekają.
        api_post(base, "/api/queue", {"paused": True})
        page.goto(base + "/#series")
        page.click("button[data-template=lava_vents]")
        page.wait_for_selector("#series-preview-table tbody tr")
        page.fill("#series-name", "lawa_kratery")
        page.wait_for_timeout(800)
        page.click("#series-run")
        page.wait_for_selector("#series-result .notice.ok", timeout=60000)
        sid = next(s["id"] for s in api(base, "/api/series") if s["id"].endswith("_lawa_kratery"))
        page.goto(base + "/#jobs")
        page.select_option("#jobs-filter", "active")
        page.wait_for_selector(f"tr[data-job='{self.etna_job}']")
        page.wait_for_selector(f"tr.group-row[data-series='{sid}']")
        # Postęp CA (krok / aktywne komórki) — czekamy, aż Etna przejdzie kilkadziesiąt kroków.
        page.wait_for_function("""(id) => { const r = document.querySelector(`tr[data-job='${id}']`);
            const m = r && r.textContent.match(/krok\\s*(\\d+)/); return m && Number(m[1]) >= 40; }""",
                               arg=self.etna_job, timeout=60000)
        page.evaluate(SCROLL_TOP)
        page.mouse.move(5, 5)  # kursor poza tabelą (bez podświetlenia wiersza)
        page.wait_for_timeout(700)
        tab = self.rect("#tab-jobs")
        last = page.evaluate("""() => { const rows = [...document.querySelectorAll('#jobs-table tbody tr')];
            const r = rows[rows.length - 1].getBoundingClientRect(); return r.bottom + scrollY; }""")
        tmp = self.out / "_tmp_jobs.png"
        page.screenshot(path=str(tmp), full_page=True)
        self.crop(tmp, self.out / "gui_2_kolejka.png", (tab["x"], tab["y"], tab["x"] + tab["w"], last + 16))
        # Seria była tylko tłem zrzutu — anulowana; Etna kończy się normalnie (wynik do zrzutu 3).
        api_post(base, f"/api/series/{sid}/cancel", {})
        end = time.monotonic() + 180
        while time.monotonic() < end:
            st = api(base, f"/api/jobs/{self.etna_job}")["status"]
            if st not in ("queued", "running"):
                break
            time.sleep(0.5)
        if st != "done":
            raise RuntimeError(f"zadanie {self.etna_job}: {st}")
        api_post(base, "/api/queue", {"paused": False})
        return f"gui/{self.etna_job}"

    # ---------------------------------------------------------------- 3. erupcja 3D

    def eruption_shot(self, rid: str) -> None:
        page = self.page
        page.goto(self.base + "/#view3d")
        page.wait_for_selector("#result-select option", state="attached")
        self.select_result(rid, "#v3-loading")
        page.check("input[name=v3-mode][value=surface]")
        self.idle("#v3-loading")
        if not page.is_checked("#v3-replay-on"):
            page.check("#v3-replay-on")
        page.wait_for_function("() => document.querySelector('#v3-replay-label').textContent.includes('/')", timeout=60000)
        self.idle("#v3-loading")
        page.select_option("#v3-replay-color", "glow")
        page.evaluate("(k) => { const t = document.querySelector('#v3-replay-time'); t.value = k;"
                      " t.dispatchEvent(new Event('input')); }", REPLAY_STEP)
        page.wait_for_timeout(400)
        self.idle("#v3-loading")
        # Kamera (OrbitControls): przybliżenie na stożek szczytowy, lekki obrót i przesunięcie kadru w górę.
        wrap = page.locator("#v3-wrap").bounding_box()
        cx, cy = wrap["x"] + wrap["width"] / 2, wrap["y"] + wrap["height"] / 2
        page.mouse.move(cx, cy)
        cam = CAMERA_3D
        page.click("#v3-reset")
        page.wait_for_timeout(300)
        if cam["rotate"] != (0, 0):
            page.mouse.down()
            page.mouse.move(cx + cam["rotate"][0], cy + cam["rotate"][1], steps=12)
            page.mouse.up()
        # OrbitControls (vendor/three/OrbitControls.js, getZoomScale): odległość × 0,95^(|deltaY| / (100 · DPR))
        # na zdarzenie; Chromium skaluje deltaY z page.mouse.wheel przez DPR — liczba zdarzeń z odczytanego deltaY.
        page.evaluate("() => { window.__wheel3 = []; document.querySelector('#v3-wrap').addEventListener('wheel',"
                      " (e) => window.__wheel3.push(e.deltaY), { capture: true }); }")
        page.mouse.move(cx, cy)
        page.mouse.wheel(0, -100)
        page.wait_for_timeout(100)
        real = abs(page.evaluate("() => window.__wheel3[0]"))
        per_event = real / (100 * max(1, int(self.dpr)))
        for _ in range(max(0, round(cam["zoom"] / per_event) - 1)):
            page.mouse.wheel(0, -100)
            page.wait_for_timeout(30)
        if cam["pan"] != (0, 0):
            page.mouse.move(cx, cy)
            page.mouse.down(button="right")
            page.mouse.move(cx + cam["pan"][0], cy + cam["pan"][1], steps=12)
            page.mouse.up(button="right")
        page.mouse.move(wrap["x"] + 5, wrap["y"] + wrap["height"] + 40)  # kursor poza sceną
        page.wait_for_timeout(1200)
        bar, card = self.rect("#result-bar"), self.rect("#tab-view3d")
        tmp = self.out / "_tmp_3d.png"
        page.screenshot(path=str(tmp))
        self.crop(tmp, self.out / "gui_3_erupcja_3d.png", (bar["x"], bar["y"], card["x"] + card["w"], card["y"] + card["h"]))

    # ---------------------------------------------------------------- 4. krystalizacja MC

    def crystal_shot(self) -> None:
        page = self.page
        page.goto(self.base + "/#view2d")
        page.wait_for_selector("#result-select option", state="attached")
        self.select_result(MC_RESULT, "#v2-loading")
        if page.is_checked("#v2-replay-on"):
            page.uncheck("#v2-replay-on")
            self.idle("#v2-loading")
        page.select_option("#v2-field", "crystal")
        self.idle("#v2-loading")
        if not page.is_checked("#v2-boundaries"):
            page.check("#v2-boundaries")
        page.wait_for_timeout(400)
        # Przybliżenie: okno MC_WINDOW wypełnia płótno (kółko myszy wokół środka okna, potem przeciągnięcie na środek).
        cv = page.locator("#v2-canvas").bounding_box()
        nx, nz = 240, 80
        fit = min(cv["width"] / nx, cv["height"] / nz)
        ox = cv["x"] + (cv["width"] - nx * fit) / 2
        oy = cv["y"] + (cv["height"] - nz * fit) / 2
        x0, x1, z0, z1 = MC_WINDOW
        tx, tz = (x0 + x1) / 2, (z0 + z1) / 2
        px, py = ox + tx * fit, oy + (nz - tz) * fit
        target = min(cv["width"] / (x1 - x0), cv["height"] / (z1 - z0))
        # viewer2d.js: skala × exp(−deltaY · 0.0015) na zdarzenie. Chromium skaluje deltaY z page.mouse.wheel,
        # więc najpierw odczyt rzeczywistego deltaY jednego zdarzenia, potem tyle małych zdarzeń, ile trzeba.
        page.evaluate("() => { window.__wheel = []; document.querySelector('#v2-canvas').addEventListener('wheel',"
                      " (e) => window.__wheel.push(e.deltaY)); }")
        page.mouse.move(px, py)
        page.mouse.wheel(0, -100)
        page.wait_for_timeout(200)
        real = page.evaluate("() => window.__wheel[0]")
        zoom = fit * math.exp(-real * 0.0015)
        steps = max(0, round(math.log(target / zoom) / (-real * 0.0015)))
        for _ in range(steps):
            page.mouse.wheel(0, -100)
            page.wait_for_timeout(60)
        page.wait_for_timeout(300)
        cx, cy = cv["x"] + cv["width"] / 2, cv["y"] + cv["height"] / 2
        page.mouse.down()
        page.mouse.move(cx, cy, steps=10)
        page.mouse.up()
        page.mouse.move(cv["x"] + cv["width"] + 60, cv["y"] - 30)  # kursor poza płótnem (bez podpowiedzi)
        page.wait_for_timeout(800)
        bar, card = self.rect("#result-bar"), self.rect("#tab-view2d")
        tmp = self.out / "_tmp_2d.png"
        page.screenshot(path=str(tmp))
        self.crop(tmp, self.out / "gui_4_krystalizacja_mc.png", (bar["x"], bar["y"], card["x"] + card["w"], card["y"] + card["h"]))


def stitch_form(src: Path, dst: Path, dpr: float, split_x: float, cut_from: float, cut_to: float, bottom: float) -> None:
    """Zrzut formularza bez karty mapy wysokości: lewa kolumna = pas [0, cut_from) + pas [cut_to, bottom),
    prawa kolumna (przyklejony panel szacunku) bez cięcia. Miejsce cięcia — przerywana linia."""
    from PIL import Image, ImageDraw
    d = dpr
    with Image.open(src) as im:
        im = im.convert("RGB")
        w = im.width
        sx, a, b, c = (round(v * d) for v in (split_x, cut_from, cut_to, bottom))
        h = a + (c - b)
        outimg = Image.new("RGB", (w, h), im.getpixel((5, h - 5 if h < im.height else im.height - 5)))
        outimg.paste(im.crop((0, 0, sx, a)), (0, 0))
        outimg.paste(im.crop((0, b, sx, c)), (0, a))
        outimg.paste(im.crop((sx, 0, w, h)), (sx, 0))
        g = ImageDraw.Draw(outimg)
        y = a - round(4 * d)
        dash, gap = round(8 * d), round(5 * d)
        for x in range(round(20 * d), sx - round(8 * d), dash + gap):
            g.line([(x, y), (min(x + dash, sx - round(8 * d)), y)], fill=(150, 138, 124), width=max(1, round(1.2 * d)))
        outimg.save(dst, optimize=True)
    src.unlink()


def cleanup(known_jobs: set[str], queue_before: dict, keep: bool) -> None:
    """Usuwa zadania i serie utworzone przez skrypt (wpisy w jobs.json, configi, foldery wyników); przywraca kolejkę."""
    data = read_jobs_file()
    jobs = data.get("jobs", [])
    new = [j for j in jobs if j["id"] not in known_jobs]
    if queue_before:
        q = data.setdefault("queue", {})
        for key in ("paused", "workers", "pin"):
            if key in queue_before:
                q[key] = queue_before[key]
    if not keep:
        series = {j["seriesId"] for j in new if j.get("seriesId")}
        for j in new:
            for rel in (j.get("configPath"), j.get("outDir")):
                if not rel:
                    continue
                path = ROOT / rel
                if path.is_dir():
                    shutil.rmtree(path)
                elif path.is_file():
                    path.unlink()
        for sid in series:
            for d in (ROOT / "configs" / "gui" / "series" / sid, ROOT / "results" / "gui" / "series" / sid):
                if d.is_dir():
                    shutil.rmtree(d)
        data["jobs"] = [j for j in jobs if j["id"] in known_jobs]
        q = data.setdefault("queue", {})
        q["order"] = [i for i in q.get("order", []) if i in known_jobs]
        print(f"  usunięto {len(new)} zadań utworzonych przez skrypt ({len(series)} seria/serie)")
    tmp = JOBS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(JOBS_FILE)


if __name__ == "__main__":
    sys.exit(main())
