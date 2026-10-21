#!/usr/bin/env python3
"""Pomiar skalowania OpenMP (etap 9): przyspieszenie S(p) = T(1)/T(p), efektywność E(p) = S(p)/p i część szeregowa
z prawa Amdahla dla wybranych przypadków CA i MC przy p wątkach (domyślnie 1, 2, 4, 6, 8 — tylko rdzenie P).

Każdy przebieg: silnik z `--threads p --set parallel.affinity=pcores` (jeden wątek na rdzeń fizyczny P, wątek 0 na
procesorze logicznym 2 — parallel/Affinity.hpp; w WSL wiąże libgomp — niżej), na Windows z priorytetem HIGH_PRIORITY_CLASS (bez niego wątki przy
8 zajętych rdzeniach P są wywłaszczane przez programy w tle na cały kwant czasu, a pozostałe czekają na barierze).
Liczby wątków idą naprzemiennie (rosnąco w parzystych powtórzeniach, malejąco w nieparzystych), powtórzenia ≥ 5,
mediana i [min–max]. Po każdym powtórzeniu wyniki dla wszystkich p są porównywane bitowo z wynikiem p = 1
(bench/ab.py: compare_dirs — wynik nie może zależeć od liczby wątków). Tło CPU na początku i na końcu pomiaru.

Miary: `total` (cały przebieg, z częściami szeregowymi: wczytanie, teren, przygotowanie, statystyki MC, zapis) i faza
obliczeń (`caSim` albo `mcSim`). Część szeregowa f z prawa Amdahla S(p) = 1 / (f + (1 − f)/p): metoda najmniejszych
kwadratów na 1/S (1/S − 1/p = f·(1 − 1/p) — liniowe w f). Dla porównania „szeregowe z pomiaru” = (total − faza)/total
przy p = 1 (części poza fazą obliczeń — górne oszacowanie f całości, gdy faza skaluje się idealnie).

Tryb harmonogramów (--schedules): te same przypadki przy jednej liczbie wątków (--sched-threads, domyślnie 8)
i harmonogramach static / dynamic / guided z porcjami (lista HARMONOGRAMY), naprzemiennie.

Wyniki (bench/results/omp/<nazwa>*): <nazwa>_raw.csv (każdy przebieg), <nazwa>.csv (mediany, S, E), <nazwa>.md (tabela
+ Amdahl), <nazwa>_threads.json (--thread-stats: czas pracy wątków; jeden dodatkowy przebieg na wariant, poza pomiarem).
Pomiar dłuższy niż ~10 min dzielić na części (--cases) i scalać: --from-raw a_raw.csv,b_raw.csv --name <nazwa>.

    python bench/scaling.py --list
    python bench/scaling.py --cases lava_etna_real,mc_cb_2d_1000 --reps 5 --name skalowanie_msvc_cz1
    python bench/scaling.py --schedules --cases lava_duza_3d_front,lava_duza_3d_full --name harmonogramy_msvc
    python bench/scaling.py --wsl --bin build-gcc-release/bin/engine --cases ... --name skalowanie_gcc_cz1
    python bench/scaling.py --from-raw bench/results/omp/a_raw.csv,bench/results/omp/b_raw.csv --name skalowanie_msvc

--wsl: skrypt uruchamiany w WSL (python3), program GCC i dane na ext4 maszyny WSL, wątki wiąże libgomp
(OMP_PROC_BIND=close, OMP_PLACES=cores; program z parallel.affinity = none), priorytet domyślny; tło mierzone po
stronie Windows. W WSL 2 procesory są wirtualne — maszyna
wirtualna nie mówi, na których rdzeniach fizycznych (P czy E) pracują (ograniczenie opisane w docs/etap-9-openmp.md).
"""

from __future__ import annotations

import argparse
import copy
import csv
import datetime as dt
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ab import (ROOT, background_load, classic, compare_dirs, deep_update, fmt_ms,  # noqa: E402
                from_file, wsl_path)

IS_WINDOWS = os.name == "nt"
SECTIONS = ["readConfig", "allocate", "terrain", "vents", "caSim", "caStats", "save", "mcInit", "mcSim", "mcStats",
            "mcSave",
            "total"]
THREADS = [1, 2, 4, 6, 8]
# Harmonogramy porównywane w trybie --schedules: (etykieta, schedule, chunk).
HARMONOGRAMY = [("static", "static", 0), ("static,1", "static", 1), ("dynamic", "dynamic", 0),
                ("dynamic,4", "dynamic", 4), ("guided", "guided", 0), ("guided,4", "guided", 4)]


# ---------------------------------------------------------------------------
# Przypadki. phase = miara fazy obliczeń; schedule/chunk = harmonogram pomiaru skalowania — najlepszy przy 8 wątkach
# we wstępnym porównaniu harmonogramów (dziennik bench/results/omp/POSTEP.md); reps = powtórzenia (krótkie — więcej).
# ---------------------------------------------------------------------------
def lava_big(sweep: str) -> dict:
    """Duży przypadek lawy 3D: test_3d powiększony do 128 × 128 × 64 z 24 kraterami na zboczach."""
    return from_file("test_3d", {"space": {"nx": 128, "ny": 128, "nz": 64},
                                 "terrain": {"peakHeight": 48, "baseRadius": 60, "craterRadius": 6},
                                 "vents": {"count": 24, "eruptionSteps": 400},
                                 "ca": {"coolingLateral": 20, "coolingFall": 15, "sweep": sweep},
                                 "output": {"format": "bin"}})


def cases() -> list[dict]:
    """Przypadki pomiaru skalowania (id, grupa, config, miara fazy, harmonogram, powtórzenia)."""
    mc_cb = {"mc": {"update": "checkerboard"}, "output": {"format": "bin"}}
    return [
        {"id": "lava_etna_real", "group": "ca_lava", "phase": "caSim", "reps": 11,
         "schedule": ("static", 1), "config": from_file("etna_real")},
        {"id": "lava_duza_3d_front", "group": "ca_lava", "phase": "caSim", "reps": 7,
         "schedule": ("static", 1), "config": lava_big("front")},
        {"id": "lava_duza_3d_full", "group": "ca_lava", "phase": "caSim", "reps": 5,
         "schedule": ("guided", 0), "config": lava_big("full")},
        {"id": "classic_2000x2000_s400_vn", "group": "ca_classic", "phase": "caSim", "reps": 7,
         "schedule": ("static", 0), "config": classic((2000, 2000, 1), 400, "von_neumann", fmt="bin")},
        {"id": "classic_300x300x300_s100_vn", "group": "ca_classic", "phase": "caSim", "reps": 5,
         "schedule": ("dynamic", 4), "config": classic((300, 300, 300), 100, "von_neumann", fmt="bin")},
        {"id": "mc_cb_2d_1000", "group": "mc", "phase": "mcSim", "reps": 5, "schedule": ("guided", 4),
         "config": from_file("mc_full_2d", deep_update({"space": {"nx": 1000, "ny": 1000, "nz": 1}}, mc_cb))},
        {"id": "mc_cb_3d_100", "group": "mc", "phase": "mcSim", "reps": 5, "schedule": ("dynamic", 0),
         "config": from_file("mc_full_3d", deep_update({"space": {"nx": 100, "ny": 100, "nz": 100},
                                                        "mc": {"mcs": 100, "statsEvery": 10}}, mc_cb))},
        # Odniesienie: wariant naiwny (random) — sekwencyjny, tylko p = 1.
        {"id": "mc_random_2d_1000", "group": "mc", "phase": "mcSim", "reps": 3, "schedule": ("static", 0),
         "threads": [1], "config": from_file("mc_full_2d", {"space": {"nx": 1000, "ny": 1000, "nz": 1},
                                                             "output": {"format": "bin"}})},
        {"id": "mc_random_3d_100", "group": "mc", "phase": "mcSim", "reps": 3, "schedule": ("static", 0),
         "threads": [1], "config": from_file("mc_full_3d", {"space": {"nx": 100, "ny": 100, "nz": 100},
                                                             "mc": {"mcs": 100, "statsEvery": 10},
                                                             "output": {"format": "bin"}})},
    ]


# ---------------------------------------------------------------------------
# Skalowanie słabe (etap 12, --weak): rozmiar przestrzeni rośnie z liczbą rdzeni p (prawo Gustafsona), praca na rdzeń
# stała; E_w(p) = T(1) / T(p). Rozmiar rośnie w osi warstw podziału (2D — y; lawa 3D — powierzchnia x–y, bo warstwy
# to z), więc każdy wątek / proces dostaje tyle samo warstw co przy p = 1 (2D) albo warstwy p razy większe (lawa).
# Zapis wyników wyłączony (output.format = none — zapis zestawiony osobno w etapie 11).
# ---------------------------------------------------------------------------
WEAK_TILE = 128  # bok kafla terenu lawy (jak lava_big z etapów 9–11)


def lava_tile_heightmap(tiles: int, path: Path) -> list[list[int]]:
    """Mapa wysokości lawy: `tiles` takich samych kafli 128 × 128 (stożek jak lava_big: wysokość 48, promień 60, krater
    o promieniu 6 i głębokości 3, deterministyczne nierówności) wzdłuż y; zwraca położenia kraterów — 24 na kafel na
    zboczu (pierścień o promieniu 26). Każda warstwa z ma więc ten sam skład skała / powietrze przy każdym p."""
    import math
    n = WEAK_TILE
    c = (n - 1) / 2.0
    tile = []
    for y in range(n):
        row = []
        for x in range(n):
            d = math.hypot(x - c, y - c)
            h = max(0.0, 48.0 * (1.0 - d / 60.0))
            if d < 6.0:
                h -= 3.0 * (1.0 - d / 6.0)
            h += 1.5 * math.sin(0.37 * x + 0.11 * y) * math.cos(0.23 * y - 0.05 * x)  # nierówności (bez losowania)
            row.append(max(0.0, h))
        tile.append(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"# kafel lawy {n} × {n} × {tiles} wzdłuż y (bench/scaling.py --weak)\n")
        for t in range(tiles):
            for row in tile:
                f.write(",".join(f"{v:.2f}" for v in row) + "\n")
    vents = []
    for t in range(tiles):
        for k in range(24):
            a = 2.0 * math.pi * (k + 0.5) / 24.0
            vents.append([round(c + 26.0 * math.cos(a)), round(c + 26.0 * math.sin(a)) + t * n])
    return vents


def weak_cases() -> list[dict]:
    """Przypadki skalowania słabego; size(p, tmp) -> config przestrzeni p razy większej niż przy p = 1."""
    def classic_w(p: int, tmp: Path) -> dict:
        return classic((2000, 2000 * p, 1), 400 * p, "von_neumann", fmt="none")

    def mc_w(p: int, tmp: Path) -> dict:
        return from_file("mc_full_2d", {"space": {"nx": 1000, "ny": 1000 * p, "nz": 1},
                                        "mc": {"update": "checkerboard", "mcs": 30, "statsEvery": 30},
                                        "output": {"format": "none"}})

    def lava_w(sweep: str, steps: int):
        def make(p: int, tmp: Path) -> dict:
            hm = tmp / "heightmaps" / f"weak_tile_{p}.csv"
            vents = lava_tile_heightmap(p, hm)
            cfg = from_file("test_3d", {"space": {"nx": WEAK_TILE, "ny": WEAK_TILE * p, "nz": 64},
                                        "terrain": {"type": "file", "file": str(hm)},
                                        "vents": {"count": len(vents), "placement": "positions", "eruptionSteps": 400},
                                        "ca": {"coolingLateral": 20, "coolingFall": 15, "sweep": sweep,
                                               "maxSteps": steps},
                                        "output": {"format": "none"}})
            cfg["vents"]["positions"] = vents
            return cfg
        return make

    return [
        {"id": "weak_classic_2d", "group": "ca_classic", "phase": "caSim", "reps": 5, "schedule": ("static", 0),
         "size": classic_w, "desc": "classic 2000 × 2000·p, 400·p zarodków, VN"},
        {"id": "weak_mc_cb_2d", "group": "mc", "phase": "mcSim", "reps": 5, "schedule": ("guided", 4),
         "size": mc_w, "desc": "MC szachownica 1000 × 1000·p, VN, 30 MCS"},
        {"id": "weak_lava_full", "group": "ca_lava", "phase": "caSim", "reps": 5, "schedule": ("guided", 0),
         "size": lava_w("full", 20), "desc": "lawa full 128 × 128·p × 64, 24·p kraterów, 20 kroków"},
        {"id": "weak_lava_front", "group": "ca_lava", "phase": "caSim", "reps": 5, "schedule": ("static", 1),
         "size": lava_w("front", 5000), "desc": "lawa front 128 × 128·p × 64, 24·p kraterów"},
    ]


def summarize_weak(raw: list[dict], plan: list[dict], cores_key: str = "threads") -> tuple[list[dict], list[str]]:
    """Skalowanie słabe: mediana [min–max] T(p), E_w = T(1)/T(p) fazy i całości, czas na komórkę × krok (CA) albo na
    próbę MC (normalizacja — liczba kroków classic zależy od położenia zarodków i może się zmieniać z p)."""
    summary = []
    md = ["| Przypadek | wariant | p | komórki | kroki / MCS | faza [ms] | E_w fazy | total [ms] | E_w total | "
          "ns rdzenia / (komórka × krok) albo / próbę | E_w znormalizowana |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for case in plan:
        rows = [r for r in raw if r["case"] == case["id"]]
        if not rows:
            continue
        ph = case["phase"]
        labels = list(dict.fromkeys(r["variant"] for r in rows))
        ent = []
        for l in labels:
            rl = [r for r in rows if r["variant"] == l]
            e = {"case": case["id"], "group": case["group"], "variant": l, "cores": int(rl[0][cores_key]),
                 "phase": ph, "n": len(rl), "cells": int(float(rl[0]["cells"])),
                 "work": float(rl[0].get("mcs") or rl[0].get("steps") or 1)}
            for m in ("total", ph):
                vals = [float(r[m]) for r in rl if r.get(m) not in (None, "")]
                e[f"{m}_med"] = statistics.median(vals)
                e[f"{m}_min"] = min(vals)
                e[f"{m}_max"] = max(vals)
            # czas rdzenia na jednostkę pracy: faza × p / (komórki × kroki albo MCS)
            e["ns_unit"] = e[f"{ph}_med"] * 1e6 * e["cores"] / (e["cells"] * e["work"])
            ent.append(e)
        base = next((e for e in ent if e["cores"] == 1), None)
        for e in ent:
            if base:
                e["Ew_phase"] = base[f"{ph}_med"] / e[f"{ph}_med"]
                e["Ew_total"] = base["total_med"] / e["total_med"]
                e["Ew_norm"] = base["ns_unit"] / e["ns_unit"]
            summary.append(e)
            g = lambda k: f"{e[k]:.2f}" if k in e else "—"  # noqa: E731
            md.append(f"| {case['id']} | {e['variant']} | {e['cores']} | {e['cells']:,}".replace(",", " ") +
                      f" | {e['work']:.0f} | {fmt_ms(e[f'{ph}_med'])} [{fmt_ms(e[f'{ph}_min'])}–"
                      f"{fmt_ms(e[f'{ph}_max'])}] | {g('Ew_phase')} | {fmt_ms(e['total_med'])} | {g('Ew_total')} | "
                      f"{e['ns_unit']:.2f} | {g('Ew_norm')} |")
    md += ["", "E_w = T(1) / T(p) przy przestrzeni p razy większej (ideał 1); znormalizowana — z czasu na (komórkę × "
           "krok / p), gdy liczba kroków albo MCS zmienia się z p (classic: największa luka między zarodkami)."]
    return summary, md


# ---------------------------------------------------------------------------
# Uruchomienie
# ---------------------------------------------------------------------------
class Runner:
    def __init__(self, exe: str, tmp: Path, inside_wsl: bool):
        self.exe = exe
        self.tmp = tmp
        self.flags = subprocess.HIGH_PRIORITY_CLASS if IS_WINDOWS else 0
        self.env = dict(os.environ)
        # Windows: program przypina wątki sam (pcores). WSL: wiąże libgomp (OMP_PROC_BIND=close, OMP_PLACES=cores),
        # a program nie przypina (affinity none) — podwójne przypinanie (libgomp przy zmianie zespołu wątków + program)
        # dawało w mikroteście bench/micro/omp_overhead.cpp regiony po kilkadziesiąt ms.
        self.affinity = "pcores" if IS_WINDOWS else "none"
        if not IS_WINDOWS:
            self.env.update({"OMP_PROC_BIND": "close", "OMP_PLACES": "cores"})

    def prepare_config(self, case: dict) -> Path:
        """Config przypadku w folderze tymczasowym; mapa wysokości kopiowana obok (ścieżka bezwzględna)."""
        cfg = copy.deepcopy(case["config"])
        terrain = cfg.get("terrain", {})
        if terrain.get("type") == "file" and terrain.get("file"):
            src = ROOT / terrain["file"]
            dst = self.tmp / "heightmaps" / src.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists():
                shutil.copy(src, dst)
            terrain["file"] = str(dst)
        path = self.tmp / "configs" / f"{case['id']}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return path

    def run(self, cfg: Path, out: Path, threads: int, schedule: str, chunk: int, stats: bool = False) -> dict:
        """Jeden przebieg; zwraca sekcje times.json, czas procesu i (stats) sekcję threadStats."""
        shutil.rmtree(out, ignore_errors=True)
        cmd = [self.exe, "--config", str(cfg), "--out", str(out), "--threads", str(threads),
               "--set", f"parallel.affinity={self.affinity}", "--set", f"parallel.schedule={schedule}",
               "--set", f"parallel.chunk={chunk}"]
        if stats:
            cmd.append("--thread-stats")
        t0 = time.perf_counter()
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, creationflags=self.flags, env=self.env)
        wall = time.perf_counter() - t0
        if r.returncode != 0:
            raise RuntimeError(f"{self.exe} zakończony kodem {r.returncode}: "
                               f"{r.stderr.decode('utf-8', 'replace')[-500:]}")
        with open(out / "times.json", encoding="utf-8") as f:
            times = json.load(f)
        row = {s: times[s] for s in SECTIONS if s in times}
        row["procWall"] = round(wall * 1000.0, 3)
        row["threadsUsed"] = times.get("threads")
        row["cpus"] = " ".join(str(c) for c in times.get("cpus", []))
        for k in ("cells", "steps", "mcs"):  # rozmiar i liczba kroków (skalowanie słabe — normalizacja)
            row[k] = times.get(k)
        if stats:
            row["threadStats"] = times.get("threadStats")
        return row


# ---------------------------------------------------------------------------
# Podsumowanie
# ---------------------------------------------------------------------------
def amdahl_f(points: list[tuple[int, float]]) -> float | None:
    """Część szeregowa f z dopasowania S(p) = 1/(f + (1−f)/p): najmniejsze kwadraty na 1/S (liniowe w f)."""
    xs = [(1 - 1 / p, 1 / s - 1 / p) for p, s in points if p > 1 and s > 0]
    den = sum(x * x for x, _ in xs)
    if den <= 0:
        return None
    return max(0.0, min(1.0, sum(x * y for x, y in xs) / den))


def amdahl_s(f: float, p: int) -> float:
    return 1.0 / (f + (1.0 - f) / p)


def summarize_scaling(raw: list[dict], plan: list[dict]) -> tuple[list[dict], list[str]]:
    """Mediana [min–max] T(p), S(p), E(p) dla total i fazy obliczeń; dopasowanie Amdahla; tabela Markdown."""
    summary, md = [], []
    md.append("| Przypadek | p | total [ms] | S | E | faza [ms] | S fazy | E fazy | zgodne |")
    md.append("|---|---|---|---|---|---|---|---|---|")
    amd = []
    for case in plan:
        rows = [r for r in raw if r["case"] == case["id"]]
        if not rows:
            continue
        phase = case["phase"]
        ps = sorted({int(r["threads"]) for r in rows})
        med = {}
        for p in ps:
            rp = [r for r in rows if int(r["threads"]) == p]
            entry = {"case": case["id"], "group": case["group"], "threads": p, "phase": phase, "n": len(rp),
                     "schedule": rp[0]["schedule"], "chunk": rp[0]["chunk"]}
            for m in ["total", phase]:
                vals = [float(r[m]) for r in rp if r.get(m) not in (None, "")]
                entry[f"{m}_med"] = statistics.median(vals)
                entry[f"{m}_min"] = min(vals)
                entry[f"{m}_max"] = max(vals)
            for s in SECTIONS:
                vals = [float(r[s]) for r in rp if r.get(s) not in (None, "")]
                if vals and s not in ("total", phase):
                    entry[f"{s}_med"] = statistics.median(vals)
            entry["identical"] = all(str(r.get("identical")) in ("True", "true", "1") for r in rp)
            med[p] = entry
        t1 = med.get(1)
        for p in ps:
            e = med[p]
            if t1:
                e["S_total"] = t1["total_med"] / e["total_med"]
                e["E_total"] = e["S_total"] / p
                e["S_phase"] = t1[f"{phase}_med"] / e[f"{phase}_med"]
                e["E_phase"] = e["S_phase"] / p
            summary.append(e)
            s_txt = lambda k: f"{e[k]:.2f}" if k in e else "—"  # noqa: E731
            md.append(f"| {case['id']} | {p} | {fmt_ms(e['total_med'])} [{fmt_ms(e['total_min'])}–"
                      f"{fmt_ms(e['total_max'])}] | {s_txt('S_total')} | {s_txt('E_total')} | "
                      f"{fmt_ms(e[f'{phase}_med'])} [{fmt_ms(e[f'{phase}_min'])}–{fmt_ms(e[f'{phase}_max'])}] | "
                      f"{s_txt('S_phase')} | {s_txt('E_phase')} | {'tak' if e['identical'] else '**NIE**'} |")
        if t1 and len(ps) > 1:
            f_tot = amdahl_f([(p, med[p]["S_total"]) for p in ps])
            f_ph = amdahl_f([(p, med[p]["S_phase"]) for p in ps])
            serial = (t1["total_med"] - t1[f"{phase}_med"]) / t1["total_med"]
            amd.append(f"| {case['id']} | {f_tot:.3f} | {f_ph:.3f} | {serial:.3f} | "
                       f"{amdahl_s(f_tot, 8):.2f} | {1 / f_tot if f_tot else float('inf'):.1f} |")
            for e in (med[p] for p in ps):
                e["amdahl_f_total"] = f_tot
                e["amdahl_f_phase"] = f_ph
                e["serial_measured"] = serial
    if amd:
        md += ["", "Prawo Amdahla — część szeregowa f (dopasowanie do mediany S(p), najmniejsze kwadraty na 1/S); "
               "„szeregowe z pomiaru” = (total − faza)/total przy p = 1; S(∞) = 1/f:", "",
               "| Przypadek | f (total) | f (faza) | szeregowe z pomiaru | S(8) z f | S(∞) |", "|---|---|---|---|---|---|"]
        md += amd
    return summary, md


def summarize_schedules(raw: list[dict], plan: list[dict]) -> tuple[list[dict], list[str]]:
    """Czas fazy i całości dla każdego harmonogramu (jedna liczba wątków), względem najlepszego."""
    summary, md = [], []
    md.append("| Przypadek | harmonogram | p | faza [ms] | total [ms] | faza / najlepszy | zgodne |")
    md.append("|---|---|---|---|---|---|---|")
    for case in plan:
        rows = [r for r in raw if r["case"] == case["id"]]
        if not rows:
            continue
        phase = case["phase"]
        labels = list(dict.fromkeys(r["variant"] for r in rows))
        ent = []
        for l in labels:
            rl = [r for r in rows if r["variant"] == l]
            ph = [float(r[phase]) for r in rl]
            tot = [float(r["total"]) for r in rl]
            ent.append({"case": case["id"], "variant": l, "threads": int(rl[0]["threads"]), "phase": phase,
                        "phase_med": statistics.median(ph), "phase_min": min(ph), "phase_max": max(ph),
                        "total_med": statistics.median(tot), "n": len(rl),
                        "identical": all(str(r.get("identical")) in ("True", "true", "1") for r in rl)})
        best = min(e["phase_med"] for e in ent)
        for e in ent:
            e["rel_best"] = e["phase_med"] / best
            summary.append(e)
            md.append(f"| {case['id']} | {e['variant']} | {e['threads']} | {fmt_ms(e['phase_med'])} "
                      f"[{fmt_ms(e['phase_min'])}–{fmt_ms(e['phase_max'])}] | {fmt_ms(e['total_med'])} | "
                      f"×{e['rel_best']:.2f} | {'tak' if e['identical'] else '**NIE**'} |")
    return summary, md


def write_outputs(out_dir: Path, name: str, summary: list[dict], md: list[str], header: list[str]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    if summary:
        keys = list(dict.fromkeys(k for s in summary for k in s))
        with open(out_dir / f"{name}.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys, lineterminator="\n")
            w.writeheader()
            w.writerows(summary)
    with open(out_dir / f"{name}.md", "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(header + md) + "\n")
    print("\n".join(md))
    print(f"Zapisano {out_dir / (name + '.md')}")


def from_raw(args: argparse.Namespace, plan: list[dict]) -> int:
    """Tabela z zapisanych przebiegów (pomiar w częściach: kilka plików _raw.csv po przecinku)."""
    srcs = [Path(p.strip()) for p in args.from_raw.split(",") if p.strip()]
    raw = []
    for s in srcs:
        with open(s, encoding="utf-8") as f:
            raw += list(csv.DictReader(f))
    ids = {c["id"] for c in plan}
    raw = [r for r in raw if r["case"] in ids]
    mode = raw[0].get("mode", "scaling") if raw else "scaling"
    if mode == "weak":
        ids = {r["case"] for r in raw}
        summary, md = summarize_weak(raw, [c for c in weak_cases() if c["id"] in ids])
    else:
        summary, md = (summarize_schedules if mode == "schedules" else summarize_scaling)(raw, plan)
    notes = []
    for s in srcs:
        part_md = s.with_name(s.name.replace("_raw.csv", ".md"))
        if part_md.exists():
            for line in part_md.read_text(encoding="utf-8").splitlines():
                if line.startswith("- Tło") or line.startswith("- Czas pomiaru") or line.startswith("Tło"):
                    notes.append(f"- `{s.name}`: {line.lstrip('- ')}")
    header = [f"# Skalowanie OpenMP `{args.name}`", "",
              f"- Tabela z pomiaru w częściach: {', '.join(f'`{s.name}`' for s in srcs)}", *notes, ""]
    write_outputs(Path(args.out), args.name, summary, md, header)
    # Statystyki wątków z części — jeden plik.
    merged = {}
    for s in srcs:
        tj = s.with_name(s.name.replace("_raw.csv", "_threads.json"))
        if tj.exists():
            merged.update(json.loads(tj.read_text(encoding="utf-8")))
    if merged:
        with open(Path(args.out) / f"{args.name}_threads.json", "w", encoding="utf-8", newline="\n") as f:
            json.dump(merged, f, indent=1, ensure_ascii=False)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bin", help="program silnika (domyślnie build/Release/engine.exe; z --wsl i w Linuksie "
                                  "build-gcc-release/bin/engine)")
    ap.add_argument("--cases", help="tylko wybrane przypadki (id po przecinku)")
    ap.add_argument("--threads", default=",".join(map(str, THREADS)), help="liczby wątków (domyślnie 1,2,4,6,8)")
    ap.add_argument("--reps", type=int, help="powtórzenia (domyślnie z tabeli przypadków)")
    ap.add_argument("--min-reps", type=int, default=5, help="minimalna liczba powtórzeń (domyślnie 5)")
    ap.add_argument("--schedules", action="store_true", help="porównanie harmonogramów przy --sched-threads wątkach")
    ap.add_argument("--weak", action="store_true", help="skalowanie słabe (etap 12): przestrzeń p razy większa przy p "
                                                         "wątkach, przypadki weak_cases()")
    ap.add_argument("--sched-threads", type=int, default=8, help="liczba wątków w trybie --schedules (domyślnie 8)")
    ap.add_argument("--no-stats", action="store_true", help="bez przebiegów --thread-stats (czas pracy wątków)")
    ap.add_argument("--name", help="nazwa zestawu wyników (domyślnie skalowanie_<data>_<godzina>)")
    ap.add_argument("--out", default=str(ROOT / "bench" / "results" / "omp"), help="folder wyników")
    ap.add_argument("--note", default="", help="opis do nagłówka tabeli")
    ap.add_argument("--list", action="store_true", help="wypisz przypadki i zakończ")
    ap.add_argument("--wsl", action="store_true", help="pomiar w WSL (program GCC)")
    ap.add_argument("--inside-wsl", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--from-raw", metavar="PLIKI_RAW_CSV", help="bez pomiaru: tabela z zapisanych _raw.csv")
    args = ap.parse_args()
    # Bez --bin z --wsl program Windows (engine.exe) uruchomiłby się w WSL przez interop jako proces Windows,
    # który nie widzi /tmp maszyny WSL („nie można otworzyć pliku konfiguracyjnego”).
    if not args.bin:
        args.bin = "build/Release/engine.exe" if IS_WINDOWS and not args.wsl else "build-gcc-release/bin/engine"
    # Zawsze UTF-8: na Windows wyjście przekierowane do NUL udaje terminal (isatty) i ma kodowanie cp1250.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    plan = weak_cases() if args.weak else cases()
    if args.cases:
        wanted = [c.strip() for c in args.cases.split(",")]
        plan = [c for c in plan if c["id"] in wanted]
    if args.list:
        for c in plan if args.weak else cases():
            print(f"{c['group']:10s} {c['id']:30s} reps {c['reps']:2d}  faza {c['phase']:6s} harmonogram "
                  f"{c['schedule'][0]},{c['schedule'][1]}  wątki {c.get('threads', THREADS)}"
                  + (f"  {c['desc']}" if args.weak else ""))
        return 0
    if args.from_raw:
        if not args.name:
            ap.error("--from-raw wymaga --name")
        return from_raw(args, plan)
    name = args.name or "skalowanie_" + dt.datetime.now().strftime("%Y-%m-%d_%H%M")

    # --- tryb --wsl: ten sam skrypt w WSL; tło mierzone po stronie Windows ---
    if args.wsl and not args.inside_wsl:
        load_start = background_load()
        cmd = ["wsl", "-e", "env", "PYTHONIOENCODING=utf-8", "python3", wsl_path(Path(__file__)), "--inside-wsl",
               "--bin", wsl_path(ROOT / args.bin), "--threads", args.threads, "--min-reps", str(args.min_reps),
               "--sched-threads", str(args.sched_threads), "--name", name, "--out", wsl_path(Path(args.out))]
        for flag, val in (("--cases", args.cases), ("--reps", args.reps), ("--note", args.note)):
            if val:
                cmd += [flag, str(val)]
        if args.schedules:
            cmd.append("--schedules")
        if args.weak:
            cmd.append("--weak")
        if args.no_stats:
            cmd.append("--no-stats")
        r = subprocess.run(cmd)
        load_end = background_load()
        md = Path(args.out) / f"{name}.md"
        if md.exists() and load_start:
            with open(md, "a", encoding="utf-8", newline="\n") as f:
                f.write(f"\nTło (Windows, poza WSL): start {load_start['totalPercent']:.0f}% "
                        f"({', '.join(load_start['top'][:3])}), koniec {load_end.get('totalPercent', 0):.0f}%.\n")
        return r.returncode

    exe = args.bin if Path(args.bin).is_absolute() else str(ROOT / args.bin)
    if args.inside_wsl:
        tmp_root = Path("/tmp/volcano_scaling")
        shutil.rmtree(tmp_root / "run", ignore_errors=True)
        (tmp_root / "bin").mkdir(parents=True, exist_ok=True)
        dst = tmp_root / "bin" / "engine"  # program na ext4 maszyny WSL (start z /mnt/d przez 9P jest wolny)
        shutil.copy(exe, dst)
        os.chmod(dst, 0o755)
        exe = str(dst)
        tmp = tmp_root / "run"
        tmp.mkdir(parents=True, exist_ok=True)
    else:
        tmp = Path(tempfile.mkdtemp(prefix="volcano_scaling_"))
    if not Path(exe).exists():
        print(f"Brak programu {exe}", file=sys.stderr)
        return 2
    runner = Runner(exe, tmp, args.inside_wsl)
    threads = [int(t) for t in args.threads.split(",")]

    # Warianty przebiegów: (przypadek, etykieta, p, harmonogram, chunk).
    variants = []
    for c in plan:
        c["reps"] = max(args.min_reps, args.reps if args.reps else c["reps"])
        if args.schedules:
            for label, sch, ch in HARMONOGRAMY:
                variants.append((c, label, args.sched_threads, sch, ch))
        else:
            for p in c.get("threads", threads):
                variants.append((c, f"p{p}", p, c["schedule"][0], c["schedule"][1]))

    load_start = background_load()
    print(f"Skalowanie {name}: {exe}; przypadków {len(plan)}, wariantów {len(variants)}, "
          f"przebiegów {sum(c['reps'] for c, *_ in variants)}")
    if load_start:
        print(f"Tło: {load_start['totalPercent']:.0f}% CPU ({', '.join(load_start['top'][:3])})", flush=True)
    if args.weak:
        # Skalowanie słabe: osobny config dla każdego p (przestrzeń p razy większa).
        cfgs = {(c["id"], p): runner.prepare_config({"id": f"{c['id']}_p{p}", "config": c["size"](p, tmp)})
                for c in plan for p in threads}
    else:
        cfgs = {c["id"]: runner.prepare_config(c) for c in plan}
    cfg_of = (lambda cid, p: cfgs[(cid, p)]) if args.weak else (lambda cid, p: cfgs[cid])  # noqa: E731
    # Rozgrzewka: plik programu w pamięci podręcznej systemu, start puli wątków.
    runner.run(cfg_of(plan[0]["id"], threads[0]), tmp / "warm", 2, "static", 0)

    raw: list[dict] = []
    failures = 0
    t_start = time.time()
    for rep in range(max(c["reps"] for c in plan)):
        for case in plan:
            if rep >= case["reps"]:
                continue
            vs = [v for v in variants if v[0] is case]
            order = vs if rep % 2 == 0 else list(reversed(vs))
            outs = {}
            for c, label, p, sch, ch in order:
                out = tmp / "out" / f"{case['id']}__{label}__{rep}"
                row = runner.run(cfg_of(case["id"], p), out, p, sch, ch)
                mode = "weak" if args.weak else ("schedules" if args.schedules else "scaling")
                row.update({"name": name, "mode": mode, "case": case["id"],
                            "group": case["group"], "variant": label, "threads": p, "schedule": sch, "chunk": ch,
                            "rep": rep, "timestamp": dt.datetime.now().isoformat(timespec="seconds")})
                outs[label] = (out, row)
                raw.append(row)
            ref_label = vs[0][1]
            outs[ref_label][1]["identical"] = True
            for label, (out, row) in outs.items():
                if label == ref_label:
                    continue
                if args.weak:  # inne rozmiary — porównanie bitowe nie ma sensu (zgodność: etapy 9–10, ctest)
                    row["identical"] = ""
                    continue
                diffs = compare_dirs(outs[ref_label][0], out)
                row["identical"] = not diffs
                if diffs:
                    failures += 1
                    print(f"!!! RÓŻNICA WYNIKÓW: {case['id']} rep {rep}: {label} vs {ref_label}: {'; '.join(diffs)}",
                          file=sys.stderr, flush=True)
            ph = case["phase"]
            print(f"[{rep + 1}/{case['reps']}] {case['id']:28s} " +
                  "  ".join(f"{l} {outs[l][1].get(ph, 0):8.1f}" for l in (v[1] for v in vs)) + f"  ({ph})",
                  flush=True)
            for out, _ in outs.values():
                shutil.rmtree(out, ignore_errors=True)

    # Czas pracy wątków (--thread-stats): jeden przebieg na wariant z p > 1, poza pomiarem czasu.
    thread_stats = {}
    if not args.no_stats and not args.weak:  # skalowanie słabe — bez przebiegów --thread-stats
        for c, label, p, sch, ch in variants:
            if p > 1:
                row = runner.run(cfg_of(c["id"], p), tmp / "stats", p, sch, ch, stats=True)
                thread_stats[f"{c['id']}|{label}"] = {"threads": p, "schedule": sch, "chunk": ch,
                                                      "phaseMs": row.get(c["phase"]), "stats": row["threadStats"]}
    load_end = background_load()
    minutes = (time.time() - t_start) / 60

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    keys = ["name", "mode", "case", "group", "variant", "threads", "schedule", "chunk", "rep", "timestamp", *SECTIONS,
            "procWall", "threadsUsed", "cpus", "cells", "steps", "mcs", "identical"]
    with open(out_dir / f"{name}_raw.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        w.writerows(raw)
    if thread_stats:
        with open(out_dir / f"{name}_threads.json", "w", encoding="utf-8", newline="\n") as f:
            json.dump(thread_stats, f, indent=1, ensure_ascii=False)
    raw_s = [{k: ("" if v is None else v) for k, v in r.items()} for r in raw]
    if args.weak:
        summary, md = summarize_weak(raw_s, plan)
    else:
        summary, md = (summarize_schedules if args.schedules else summarize_scaling)(raw_s, plan)
    header = [f"# Skalowanie OpenMP `{name}`", ""]
    if args.note:
        header += [args.note, ""]
    bind = ("przypięcie `parallel.affinity = pcores` (jeden wątek na rdzeń fizyczny P); priorytet HIGH_PRIORITY_CLASS"
            if IS_WINDOWS else "wiązanie libgomp OMP_PROC_BIND=close, OMP_PLACES=cores (`parallel.affinity = none`); "
            "priorytet domyślny")
    header += [f"- Program: `{Path(args.bin).name}`; {bind}; "
               "warianty naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max] z n powtórzeń",
               f"- Czas pomiaru: {minutes:.1f} min, {dt.datetime.now().isoformat(timespec='minutes')}"]
    if load_start:
        header.append(f"- Tło: start {load_start['totalPercent']:.0f}% CPU ({', '.join(load_start['top'][:3])}), "
                      f"koniec {load_end.get('totalPercent', 0):.0f}%")
    if args.weak:
        header.append("- Skalowanie słabe: przestrzeń p razy większa przy p wątkach, `output.format = none`; wyników "
                      "różnych rozmiarów nie porównuje się bitowo (zgodność wątków — etapy 9–10)")
    else:
        header.append("- Zgodność wyników z p = 1 (albo z pierwszym harmonogramem): " +
                      ("wszystkie przebiegi bitowo zgodne" if failures == 0 else f"**{failures} różnic**"))
    header.append("")
    write_outputs(out_dir, name, summary, md, header)
    print(f"({minutes:.1f} min); różnic wyników: {failures}")
    if not args.inside_wsl:
        shutil.rmtree(tmp, ignore_errors=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
