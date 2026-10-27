"""Pomiar „CA vs MC: rozmiar siatki” przez GUI (etap 5): te same kliknięcia co ręcznie, w Chromium (Playwright).

Scenariusz: start GUI (python -m gui na wolnym porcie) -> zakładka „Seria” -> szablon „CA vs MC: rozmiar siatki”
-> „Ustaw 1 worker + przypięcie” (proces silnika na rdzeniu P, wysoki priorytet — jak pomiary z etapu 3)
-> „Uruchom serię” (16 configów + series.json w configs/gui/series/<id>/, foldery w results/gui/series/<id>/,
potem kolejka) -> czekanie na koniec -> zakładka „Porównanie” -> widok domyślny (czas symulacji CA i MC vs liczba
komórek, log–log, osobno 2D i 3D) -> „Eksport PNG” i „Eksport CSV” -> docs/img/ca_vs_mc.png, docs/data/ca_vs_mc.csv.

Uruchomienie (z katalogu volcano-ca-mc; w czasie pomiaru nie obciążaj komputera):
    python gui/tests/run_ca_vs_mc.py
    python gui/tests/run_ca_vs_mc.py --template seeds --png X.png --csv X.csv   # inny szablon
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


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def api(base: str, path: str):
    with urllib.request.urlopen(base + path, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def background_load(seconds: float = 2.0) -> dict:
    """Obciążenie komputera przez inne programy (psutil, opcjonalnie): całe CPU [%] i 5 najbardziej zajętych procesów
    — zapisywane obok wyników, bo tło zmienia czasy (wspólne L3, limit mocy; docs/profilowanie.md, punkt 1.3)."""
    try:
        import psutil
    except ImportError:
        return {"available": False}
    procs = list(psutil.process_iter(["name"]))
    for pr in procs:
        try:
            pr.cpu_percent(None)
        except psutil.Error:
            pass
    total = psutil.cpu_percent(interval=seconds)
    top = []
    for pr in procs:
        try:
            if pr.info["name"] not in ("System Idle Process", "Idle"):
                top.append((pr.cpu_percent(None), pr.info["name"]))
        except psutil.Error:
            pass
    top.sort(reverse=True)
    return {"available": True, "cpuPercentAll": total, "logicalCpus": psutil.cpu_count(),
            "top": [{"name": n, "cpuPercentOfOneCpu": round(c, 1)} for c, n in top[:5]]}


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", default="ca_vs_mc")
    ap.add_argument("--png", default=str(ROOT / "docs" / "img" / "ca_vs_mc.png"))
    ap.add_argument("--csv", default=str(ROOT / "docs" / "data" / "ca_vs_mc.csv"))
    ap.add_argument("--meta", default=str(ROOT / "docs" / "data" / "ca_vs_mc_meta.json"))
    ap.add_argument("--series", help="bez liczenia: tylko eksport wykresu i CSV z istniejącej serii GUI (identyfikator)")
    ap.add_argument("--timeout", type=float, default=1800)
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    server = subprocess.Popen([sys.executable, "-m", "gui", "--no-browser", "--port", str(port)], cwd=ROOT)
    errors: list[str] = []
    try:
        for _ in range(100):
            try:
                api(base, "/api/info")
                break
            except OSError:
                time.sleep(0.2)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=2, accept_downloads=True)
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)

            before = api(base, "/api/queue")  # przywracany na końcu — pomiar nie zmienia ustawień kolejki na stałe
            meta: dict = {}
            if args.series:
                sid = args.series
            else:
                meta["backgroundBefore"] = background_load()
                print(f"Tło przed pomiarem: {meta['backgroundBefore']}")
                page.goto(base + "/#series")
                page.click(f"button[data-template={args.template}]")
                page.wait_for_selector("#series-preview-table tbody tr")
                setup = page.locator("#series-measure-setup")
                if setup.count():
                    setup.click()
                    page.wait_for_timeout(500)
                q = api(base, "/api/queue")
                print(f"Kolejka: {q['workers']} worker, przypięcie {q['pin']}")
                page.click("#series-run")
                page.wait_for_selector("#series-result .notice.ok", timeout=60000)
                sid = api(base, "/api/series")[0]["id"]
                print(f"Seria {sid}: {page.locator('#series-result').inner_text()}")
                t0 = time.monotonic()
                while time.monotonic() - t0 < args.timeout:
                    s = next(x for x in api(base, "/api/series") if x["id"] == sid)
                    c = s["counts"]
                    if c["queued"] + c["running"] == 0:
                        break
                    time.sleep(1.0)
                duration = time.monotonic() - t0
                print(f"Koniec serii po {duration:.1f} s: {c}")
                meta.update(series=sid, template=args.template, date=time.strftime("%Y-%m-%d %H:%M:%S"),
                            durationS=round(duration, 1), counts=c, queue={"workers": q["workers"], "pin": q["pin"]},
                            backgroundAfter=background_load())
                Path(args.meta).parent.mkdir(parents=True, exist_ok=True)
                Path(args.meta).write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8",
                                           newline="\n")
                print(f"zapisano {args.meta}")

            page.goto(base + "/#compare")
            page.select_option("#cmp-source", f"gui/series/{sid}")
            page.wait_for_function("() => document.querySelectorAll('#cmp-charts canvas').length > 0", timeout=30000)
            page.click("#cmp-default")
            page.wait_for_timeout(1000)
            for button, target in (("#cmp-png", args.png), ("#cmp-csv", args.csv)):
                Path(target).parent.mkdir(parents=True, exist_ok=True)
                with page.expect_download() as dl:
                    page.click(button)
                dl.value.save_as(target)
                print(f"zapisano {target}")
            if not args.series:
                page.evaluate("(b) => fetch('/api/queue', {method: 'POST', headers: {'Content-Type': 'application/json'}, "
                              "body: JSON.stringify(b)})",
                              {"workers": before["workers"], "pin": {"enabled": before["pin"]["enabled"]}})
            browser.close()
        table = api(base, f"/api/compare?series=gui/series/{sid}")
        print(f"\n{'zadanie':22s} {'komórki':>9s} {'kroki':>6s} {'caSim [ms]':>11s} {'mcSim [ms]':>11s} {'ns/jedn.':>9s} {'RSS [MiB]':>9s}")
        for r in table["rows"]:
            f = lambda v, d=1: "—" if v is None else f"{v:.{d}f}" if isinstance(v, float) else str(v)  # noqa: E731
            print(f"{r['name']:22s} {f(r['cells']):>9s} {f(r['steps']):>6s} {f(r['caSim']):>11s} {f(r['mcSim']):>11s} "
                  f"{f(r['nsPerUnit']):>9s} {f(r['peakRssMiB']):>9s}")
    finally:
        server.terminate()
        server.wait(timeout=10)
    if errors:
        print("Błędy JS:", *errors, sep="\n  ")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
