"""Zestawienie wyników — liczy przykładowe przypadki (presety z configs/) i zapisuje raport docs/wyniki.md.

Uruchomienie (z folderu volcano-ca-mc):
    python tools\\zestaw_wynikow.py            # wszystko (~1 min + benchmark ~10 s)
    python tools\\zestaw_wynikow.py --bez-liczenia   # tylko raport z wyników, które już są w results\\

Każdy punkt raportu: co sprawdzamy, jakim poleceniem, wynik (liczby z times.json / stats.json silnika)
i status polecenia. Wyniki trafiają do results\\<nazwa>\\ — te same foldery pokazuje GUI (lista „Wyniki”).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "docs" / "wyniki.md"


def find_engine() -> Path:
    for rel in ("build/Release/engine.exe", "build/engine.exe", "build-gcc-release/engine", "build/engine"):
        p = ROOT / rel
        if p.exists():
            return p
    sys.exit("Nie znaleziono silnika (build\\Release\\engine.exe) — najpierw zbuduj projekt (docs\\uruchamianie.md, pkt 2).")


# ---------------------------------------------------------------- formatowanie liczb po polsku

def num(v, dec: int = 0) -> str:
    if v is None:
        return "—"
    s = f"{v:,.{dec}f}".replace(",", " ").replace(".", ",")
    return s


def ms(v) -> str:
    if v is None:
        return "—"
    return f"{num(v / 1000, 2)} s" if v >= 1000 else f"{num(v, 1)} ms"


def mib(b) -> str:
    return "—" if b is None else f"{num(b / 2**20, 1)} MiB"


# ---------------------------------------------------------------- przypadki

CASES = [
    dict(name="etna_real", title="Etna — spływ lawy na prawdziwym terenie (CA, 3D)",
         check="Rozrost CA (lawa = ziarna z 3 kraterów szczytowych) na mapie wysokości z AWS Terrain Tiles; "
               "kratery w zadanych kolumnach (`vents.positions`).",
         args=["--config", "configs/etna_real.json", "--out", "results/etna_real"]),
    dict(name="wezuwiusz_real", title="Wezuwiusz — wypełnienie krateru i przelew (CA, 3D)",
         check="Wypełnianie zagłębienia (priority-flood) i przelew przez najniższe miejsce krawędzi; "
               "Monte Somma zatrzymuje lawę.",
         args=["--config", "configs/wezuwiusz_real.json", "--out", "results/wezuwiusz_real"]),
    dict(name="test_2d", title="Przekrój 2D — reguły automatu",
         check="Podstawowe reguły lawy w przekroju x–z: spadek, rozlewanie z podparciem, kierunek największego "
               "spadku, stygnięcie i zastyganie w bazalt.",
         args=["--config", "configs/test_2d.json", "--out", "results/test_2d"]),
    dict(name="classic_ref", title="Klasyczny rozrost ziaren CA (100³, 10 ziaren)",
         check="Czysty rozrost ziaren CA (tryb `classic`, von Neumann, brzeg periodyczny) — "
               "przypadek referencyjny do porównań wydajności.",
         args=["--config", "configs/classic_ref.json", "--out", "results/classic_ref"]),
    dict(name="lava_mc_2d_migawki", title="Lawa 2D + krystalizacja bazaltu MC (z migawkami MC)",
         check="CA → bazalt → Monte Carlo (Potts, Metropolis) z mobilnością ze stygnięcia: duże kryształy "
               "w jeziorze lawy, drobne na szybko zastygłych jęzorach; migawki MC do odtwarzania wzrostu ziaren.",
         args=["--config", "configs/lava_mc_2d.json", "--out", "results/lava_mc_2d_migawki",
               "--set", "mc.snapshotsEvery=10"]),
    dict(name="lava_mc_3d", title="Lawa 3D + krystalizacja bazaltu MC",
         check="To samo co wyżej w 3D (80×80×50, sąsiedztwo Moore'a).",
         args=["--config", "configs/lava_mc_3d.json", "--out", "results/lava_mc_3d"]),
    dict(name="mc_full_2d", title="Klasyczny naiwny Monte Carlo (200×200, Q = 50)",
         check="Kroki 1–5 naiwnego algorytmu Monte Carlo na całej przestrzeni, bez CA — zgrubianie ziaren w czasie (MCS).",
         args=["--config", "configs/mc_full_2d.json", "--out", "results/mc_full_2d"]),
    dict(name="heightmap_kaldera", title="Teren z pliku — kaldera z wyłomem",
         check="Dane wejściowe z pliku (mapa wysokości CSV): lawa wypływa tylko przez wyłom w ścianie kaldery.",
         args=["--config", "configs/heightmap_kaldera.json", "--out", "results/heightmap_kaldera"]),
]


def run(engine: Path, args: list[str]) -> tuple[int, float, str]:
    t0 = time.perf_counter()
    p = subprocess.run([str(engine), *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return p.returncode, time.perf_counter() - t0, (p.stdout or "") + (p.stderr or "")


def load(folder: Path, name: str) -> dict | None:
    f = folder / name
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def meters_per_cell(cfg: dict | None) -> float | None:
    """Skala pozioma z metadanych mapy (tylko prawdziwy teren: configs/heightmaps/<nazwa>.json)."""
    try:
        meta = load(ROOT / Path(cfg["terrain"]["file"]).parent, Path(cfg["terrain"]["file"]).stem + ".json")
        return meta["horizontal"]["metersPerCell"] if meta else None
    except (KeyError, TypeError):
        return None


def result_rows(folder: Path) -> list[tuple[str, str]]:
    t, s, cfg = load(folder, "times.json"), load(folder, "stats.json"), load(folder, "config_used.json")
    if not t:
        return [("wynik", "brak `times.json` — symulacja nie została policzona")]
    rows: list[tuple[str, str]] = []
    sp = t.get("space") or [None] * 3
    rows.append(("siatka", f"{sp[0]} × {sp[1]} × {sp[2]} = {num(t.get('cells'))} komórek, "
                           f"sąsiedztwo {t.get('neighborhood')}, brzeg {t.get('boundary')}"))
    mode = t.get("mode")
    if mode in ("lava", "classic") and s:
        rows.append(("kroki CA / koniec", f"{t.get('steps')} kroków — {t.get('stopReason')}"))
        if mode == "lava":
            mpc = meters_per_cell(cfg)
            reach = s.get("maxReach")
            reach_txt = f"{num(reach, 1)} komórek" + (f" ≈ {num(reach * mpc / 1000, 1)} km" if mpc and reach else "")
            rows.append(("objętość lawy", f"{num(s.get('totalLavaVolume'))} komórek (płynnej na końcu: "
                                           f"{num(s.get('liquidLava'))}), największy zasięg od krateru: {reach_txt}"))
            flows = s.get("flows") or []
            if len(flows) > 1:
                rows.append(("lawa z kraterów", "; ".join(
                    f"krater {f['flowId']}: {num(f['cells'])} kom., zasięg {num(f.get('maxReach'), 1)}"
                    for f in flows)))
        else:
            rows.append(("ziarna", f"{s.get('grains')} ziaren, średnio {num(s.get('meanGrainSize'))} komórek "
                                   f"(najmniejsze {num(s.get('minGrainSize'))}, największe {num(s.get('maxGrainSize'))})"))
        rows.append(("czas CA (`caSim`)", f"{ms(t.get('caSim'))} — {num(t['caSim'] * 1e6 / (t['cells'] * max(t['steps'], 1)), 1)} "
                                          f"ns na komórkę i krok" if t.get("caSim") and t.get("steps") else ms(t.get("caSim"))))
    mc = (s or {}).get("mc")
    if mc:
        acc = 100 * mc["accepted"] / mc["attempts"] if mc.get("attempts") else None
        rows.append(("MC: domena", f"{mc.get('domain')} — {num(mc.get('domainCells'))} komórek, Q = {mc.get('Q')}, "
                                   f"{mc.get('mcs')} MCS, kT = {mc.get('kT')}, mobilność: {mc.get('mobility')}"))
        rows.append(("MC: ziarna", f"{num(mc.get('grainsStart'))} → {num(mc.get('grainsEnd'))}; średnie ziarno "
                                   f"{num(mc.get('meanGrainSizeStart'), 2)} → {num(mc.get('meanGrainSizeEnd'), 2)} kom., "
                                   f"największe {num(mc.get('largestGrainEnd'))}"))
        rows.append(("MC: energia / akceptacja", f"{num(mc.get('energyStart'))} → {num(mc.get('energyEnd'))}; "
                                                 f"zaakceptowano {num(acc, 1)} % z {num(mc.get('attempts'))} prób"))
        bm = mc.get("byMobility")
        if bm:
            hi, lo = bm["high"], bm["low"]
            ratio = hi["meanGrainSizeEnd"] / lo["meanGrainSizeEnd"] if lo.get("meanGrainSizeEnd") else None
            rows.append(("MC: efekt stygnięcia", f"wolno stygnące (mobilność ≥ {bm['threshold']}): średnie ziarno "
                                                 f"{num(hi['meanGrainSizeEnd'], 1)} kom.; szybko stygnące: "
                                                 f"{num(lo['meanGrainSizeEnd'], 1)} kom. → **×{num(ratio, 1)}**"))
        if t.get("mcSim"):
            per = t["mcSim"] * 1e6 / mc["attempts"] if mc.get("attempts") else None
            rows.append(("czas MC (`mcSim`)", f"{ms(t['mcSim'])} — {num(per, 1)} ns na próbę"))
    mem = t.get("memory") or {}
    if mem.get("peakRssBytes"):
        model = (mem.get("model") or {})
        rows.append(("pamięć (szczyt)", f"{mib(mem['peakRssBytes'])} zmierzone, model z kodu {mib(model.get('peakBytes'))} "
                                        f"({num(model.get('peakBytesPerCell'), 1)} B/komórkę)"))
    files = t.get("files") or {}
    if files:
        rows.append(("pliki", ", ".join(f"`{k}` {mib(v['bytes']) if v['bytes'] > 2**20 else num(v['bytes'] / 1024, 1) + ' KiB'}"
                                         for k, v in files.items())))
    rows.append(("czas całkowity (`total`)", ms(t.get("total"))))
    return rows


def section(i: int, c: dict, code: int | None, wall: float | None, log: str) -> str:
    folder = ROOT / "results" / c["name"]
    cmd = ".\\build\\Release\\engine.exe " + " ".join(a.replace("/", "\\") if not a.startswith("mc.") else a
                                                      for a in c["args"])
    if code is None:
        status = "policzone wcześniej" if (folder / "times.json").exists() else "❌ brak wyniku"
    else:
        status = f"✅ OK (kod 0, {num(wall, 1)} s z uruchomieniem procesu)" if code == 0 else f"❌ błąd — kod wyjścia {code}"
    out = [f"## {i}. {c['title']}", "", f"**Co sprawdzamy:** {c['check']}", "",
           f"**Polecenie:** (podgląd w GUI: wynik `{c['name']}`)", "",
           "```powershell", cmd, "```", "", f"**Status:** {status}", "", "| | Wynik |", "|---|---|"]
    out += [f"| {k} | {v} |" for k, v in result_rows(folder)]
    if code not in (None, 0):
        out += ["", "<details><summary>wyjście programu</summary>", "", "```", log[-3000:], "```", "", "</details>"]
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bez-liczenia", action="store_true", help="nie uruchamiaj silnika, tylko zbuduj raport")
    opt = ap.parse_args()
    engine = find_engine()

    parts: list[str] = []
    ok = 0
    for i, c in enumerate(CASES, 1):
        code = wall = None
        log = ""
        if not opt.bez_liczenia:
            print(f"[{i}/{len(CASES) + 2}] {c['name']} …", flush=True)
            code, wall, log = run(engine, c["args"])
            print(f"      {'OK' if code == 0 else 'BŁĄD ' + str(code)} ({wall:.1f} s)", flush=True)
        ok += code == 0
        parts.append(section(i, c, code, wall, log))

    # Walidacja configu — błąd po polsku zamiast awarii
    n = len(CASES) + 1
    vargs = ["--validate", "--config", "configs/test_3d.json", "--set", "space.nx=-5"]
    print(f"[{n}/{len(CASES) + 2}] walidacja …", flush=True)
    vcode, _, vout = run(engine, vargs)
    parts.append("\n".join([
        f"## {n}. Walidacja configu (błędne dane wejściowe)", "",
        "**Co sprawdzamy:** silnik sprawdza config przed liczeniem i zwraca błędy po polsku (tego samego używa "
        "formularz GUI — przycisk **Sprawdź**).", "",
        "**Polecenie:**", "", "```powershell",
        ".\\build\\Release\\engine.exe " + " ".join(a.replace("/", "\\") for a in vargs), "```", "",
        f"**Status:** {'✅ błąd wykryty (kod 1 = błąd configu)' if vcode == 1 else f'⚠️ nieoczekiwany kod {vcode}'}", "",
        "```json", vout.strip()[:2000], "```", ""]))

    # Benchmark vector vs macierz
    n += 1
    print(f"[{n}/{len(CASES) + 2}] benchmark vector vs macierz (~10 s) …", flush=True)
    bcode, bwall, bout = run(engine, ["--benchmark", "--quick"])
    parts.append("\n".join([
        f"## {n}. Benchmark: płaska tablica (vector) vs `vector<vector<vector>>` (macierz)", "",
        "**Co sprawdzamy:** te same przypadki na obu reprezentacjach siatki — czas samego automatu (mediana) i czy "
        "wyniki są identyczne komórka po komórce (kolumna „zgodne”).", "",
        "**Polecenie:**", "", "```powershell", ".\\build\\Release\\engine.exe --benchmark --quick",
        "```", "",
        f"**Status:** {'✅ wszystkie wyniki zgodne (kod 0)' if bcode == 0 else ('❌ niezgodne wyniki (kod 4)' if bcode == 4 else f'❌ kod {bcode}')}"
        f" — {num(bwall, 1)} s", "", "```", bout.strip()[-6000:], "```", ""]))

    t0 = load(ROOT / "results" / "etna_real", "times.json") or {}
    head = [
        "# Zestawienie wyników — przykładowe przypadki (wulkan: CA + MC)", "",
        f"Wygenerowane: {dt.datetime.now():%d.%m.%Y %H:%M} skryptem `tools/zestaw_wynikow.py` · "
        f"procesor: {t0.get('cpu', '—')} · kompilator: {t0.get('compiler', '—')} {t0.get('build', '')}", "",
        "Każdy punkt: co sprawdzamy, polecenie (z folderu `volcano-ca-mc`), wynik odczytany z plików silnika "
        "(`times.json`, `stats.json`). Wyniki są w `results\\<nazwa>\\` i można je obejrzeć w GUI "
        "(Podgląd 2D / 3D, Czasy i statystyki).", "",
        "> Czasy pochodzą z jednego uruchomienia (MSVC Release) i służą orientacji. Pomiary do profilu (3 powtórzenia, "
        "przypięcie do rdzenia P) są w `docs/etap-3-profilowanie.md`, porównanie CA vs MC — w `docs/etap-5-kolejka-serie-dane.md`.", "",
        "| # | Przypadek | Status |", "|---|---|---|"]
    for i, (c, p) in enumerate(zip(CASES, parts), 1):
        st = p.split("**Status:** ", 1)[1].split("\n", 1)[0]
        head.append(f"| {i} | {c['title']} | {st} |")
    head.append(f"| {len(CASES) + 1} | Walidacja configu | {'✅' if vcode == 1 else '⚠️'} |")
    head.append(f"| {len(CASES) + 2} | Benchmark vector vs macierz | {'✅' if bcode == 0 else '❌'} |")
    REPORT.write_text("\n".join(head) + "\n\n" + "\n".join(parts), encoding="utf-8", newline="\n")
    print(f"\nRaport: {REPORT.relative_to(ROOT)}")
    if not opt.bez_liczenia and ok != len(CASES):
        print(f"UWAGA: {len(CASES) - ok} przypadków z błędem — szczegóły w raporcie.")


if __name__ == "__main__":
    main()
