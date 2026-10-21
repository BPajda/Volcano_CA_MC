#!/usr/bin/env python3
"""Krzywa „czas na komórkę i krok” w funkcji rozmiaru siatki (etap 12): empiryczne progi pamięci podręcznej L2 / L3 /
RAM. Jeden wątek na rdzeniu P (engine `--threads 1 --set parallel.affinity=pcores`, wątek na procesorze logicznym 2,
priorytet wysoki — jak bench/scaling.py), siatki 2D o boku rosnącym co √2 (128 … 2896), ta sama gęstość zarodków
i ta sama liczba kroków / MCS dla każdego rozmiaru — praca na komórkę jest porównywalna, zmienia się tylko rozmiar
danych względem pamięci podręcznej.

Rodziny przypadków (CURVES):
  classic_full  classic VN, pełny przebieg (`ca.sweep = full`), 1 zarodek na 10 000 komórek, 40 kroków — dostęp po
                kolei (prefetcher sprzętowy pomaga); miara: faza caSim / (komórki × kroki)
  mc_random     MC VN na całej przestrzeni, `mc.update = random`, 3 MCS — dostęp losowy; miara: mcSim / próby
  mc_cb         to samo w szachownicy (`checkerboard`) — dostęp po kolei w kolorach
Zapis wyników wyłączony (`output.format = none`). Zbiór roboczy kroku = bajty dotykane na komórkę × komórki z ramką
(TOUCHED): classic `full` przechodzi co krok oba bufory automatu (2 × 13 B — w cachegrind 0,41 linii 64 B na komórkę
× krok), próba MC czyta listę domeny (`domainFrame`, 8 B, losowo w trybie random) i orientacje (`spin`, 4 B) — maska
(1 B) tylko przy ścianach. Obok rozmiar z modelu pamięci silnika (`memory.model.peakBlocks`: caGrid, mcGrid — z
tablicami, których krok nie dotyka). Progi w procesorze (rdzeń P): L1d 48 KB, L2 2 MB, L3 36 MB (wspólna) —
bench/results/testy/procesor.md; symulacja tych samych progów (cachegrind): bench/results/testy/cachegrind.md.

Rozmiary idą naprzemiennie (rosnąco w parzystych powtórzeniach, malejąco w nieparzystych), ≥ 5 powtórzeń, mediana
i [min–max]; tło CPU na początku i końcu. Pomiar czasu — wymaga wolnego komputera (część 2 etapu 12, PLAN_POMIARU.md).

Wyniki: bench/results/testy/<nazwa>_raw.csv (przebiegi), <nazwa>.csv (mediany), <nazwa>.md (tabela).

    python bench/cell_time.py --list
    python bench/cell_time.py --curves classic_full,mc_random --name krzywa_msvc_cz1
    python bench/cell_time.py --curves mc_cb --sizes 256,1024 --reps 1 --name proba   # sprawdzenie
    python bench/cell_time.py --wsl --name krzywa_gcc
    python bench/cell_time.py --from-raw bench/results/testy/a_raw.csv,bench/results/testy/b_raw.csv --name krzywa_msvc
"""

from __future__ import annotations

import argparse
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
from ab import ROOT, background_load, classic, deep_update, fmt_ms, from_file, wsl_path  # noqa: E402
from scaling import Runner  # noqa: E402

IS_WINDOWS = os.name == "nt"
SIZES = [128, 181, 256, 362, 512, 724, 1024, 1448, 2048, 2896]  # bok siatki 2D, co √2 (2896² — poza L3 we wszystkich)
CACHE = {"L1d": 48 * 1024, "L2": 2 * 1024 * 1024, "L3": 36 * 1024 * 1024}  # rdzeń P i9-13900HX (procesor.md)
MB = 1024.0 * 1024.0


def classic_full(n: int) -> dict:
    seeds = max(1, round(n * n / 10000))
    return deep_update(classic((n, n, 1), seeds, "von_neumann", fmt="none"), {"ca": {"sweep": "full", "maxSteps": 40}})


def mc_2d(update: str):
    def make(n: int) -> dict:
        return from_file("mc_full_2d", {"space": {"nx": n, "ny": n, "nz": 1},
                                        "mc": {"mcs": 3, "statsEvery": 3, "update": update},
                                        "output": {"format": "none"}})
    return make


# touched — bajty na komórkę z ramką dotykane w kroku / próbie (zbiór roboczy; opis w nagłówku pliku).
CURVES = {
    "classic_full": {"phase": "caSim", "grid": "caGrid", "touched": 26, "unit": "komórkę × krok", "config": classic_full,
                     "schedule": ("static", 0), "desc": "classic 2D VN, pełny przebieg, 1 zarodek / 10⁴ komórek, 40 kroków"},
    "mc_random": {"phase": "mcSim", "grid": "mcGrid", "touched": 12, "unit": "próbę MC", "config": mc_2d("random"),
                  "schedule": ("static", 0), "desc": "MC 2D VN, random, 3 MCS"},
    "mc_cb": {"phase": "mcSim", "grid": "mcGrid", "touched": 12, "unit": "próbę MC", "config": mc_2d("checkerboard"),
              "schedule": ("guided", 4), "desc": "MC 2D VN, szachownica, 3 MCS"},
}


def framed_cells(n: int) -> int:
    return (n + 2) * (n + 2)  # siatka 2D z ramką 1 komórki w x i y


def run_one(runner: Runner, curve: str, n: int, cfg: Path, out: Path) -> dict:
    c = CURVES[curve]
    row = runner.run(cfg, out, 1, *c["schedule"])
    with open(out / "times.json", encoding="utf-8") as f:
        t = json.load(f)
    blocks = t.get("memory", {}).get("model", {}).get("peakBlocks", {})
    work = (t.get("cells") or 0) * ((t.get("mcs") if c["phase"] == "mcSim" else t.get("steps")) or 0)
    shutil.rmtree(out, ignore_errors=True)
    return {"curve": curve, "n": n, "cells": t.get("cells"), "steps": t.get("steps"), "mcs": t.get("mcs"),
            "work": work, "phaseMs": row.get(c["phase"]), "total": row.get("total"),
            "nsPerUnit": round(row.get(c["phase"], 0) * 1e6 / work, 4) if work else None,
            "gridBytes": blocks.get(c["grid"]), "modelPeak": t.get("memory", {}).get("model", {}).get("peakBytes"),
            "cpus": row.get("cpus")}


def summarize(raw: list[dict]) -> tuple[list[dict], list[str]]:
    summary = []
    md = ["| Krzywa | bok n | komórki | zbiór roboczy kroku [MB] | mieści się w | model: siatka [MB] | ns / jedn. — "
          "mediana [min–max] | względem najmniejszej | n powt. |", "|---|---|---|---|---|---|---|---|---|"]
    for curve in CURVES:
        rows = [r for r in raw if r["curve"] == curve]
        if not rows:
            continue
        first = None
        for n in sorted({int(r["n"]) for r in rows}):
            rn = [r for r in rows if int(r["n"]) == n]
            vals = [float(r["nsPerUnit"]) for r in rn if r.get("nsPerUnit") not in (None, "")]
            grid = float(rn[0]["gridBytes"] or 0)
            ws = CURVES[curve]["touched"] * framed_cells(n)
            where = next((k for k, v in CACHE.items() if ws <= v), "RAM")
            e = {"curve": curve, "n": n, "cells": int(float(rn[0]["cells"])), "workingSet": ws, "fits": where,
                 "gridBytes": grid, "ns_med": statistics.median(vals), "ns_min": min(vals), "ns_max": max(vals),
                 "reps": len(vals), "unit": CURVES[curve]["unit"]}
            first = first or e["ns_med"]
            e["rel"] = e["ns_med"] / first
            summary.append(e)
            md.append(f"| {curve} | {n} | {e['cells']:,}".replace(",", " ") +
                      f" | {ws / MB:.2f} | {where} | {grid / MB:.2f}".replace(".", ",") +
                      f" | {e['ns_med']:.2f} [{e['ns_min']:.2f}–{e['ns_max']:.2f}]".replace(".", ",") +
                      f" | {e['rel']:.2f}".replace(".", ",") + f" | {e['reps']} |")
    md += ["", "Jednostka: classic — komórka × krok (faza caSim), MC — próba (faza mcSim). Zbiór roboczy kroku = bajty "
           "dotykane na komórkę × komórki z ramką (classic `full` 26 B — oba bufory automatu; MC 12 B — lista domeny "
           "i orientacje); model: siatka = caGrid / mcGrid z modelu pamięci silnika (z tablicami, których krok nie "
           "dotyka). Progi rdzenia P: L1d 48 KB, L2 2 MB, L3 36 MB (L3 wspólna dla wszystkich rdzeni)."]
    return summary, md


def write(out_dir: Path, name: str, raw: list[dict], header: list[str]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    keys = list(dict.fromkeys(k for r in raw for k in r))
    with open(out_dir / f"{name}_raw.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, lineterminator="\n")
        w.writeheader()
        w.writerows([{k: ("" if r.get(k) is None else r.get(k)) for k in keys} for r in raw])
    summary, md = summarize(raw)
    if summary:
        with open(out_dir / f"{name}.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(summary[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(summary)
    with open(out_dir / f"{name}.md", "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(header + md) + "\n")
    print("\n".join(md))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bin", help="program (domyślnie build/Release/engine.exe; --wsl: build-gcc-release/bin/engine)")
    ap.add_argument("--curves", default=",".join(CURVES), help=f"krzywe (domyślnie wszystkie: {', '.join(CURVES)})")
    ap.add_argument("--sizes", default=",".join(map(str, SIZES)), help="boki siatki n (n × n)")
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--name", help="nazwa zestawu (domyślnie krzywa_<data>_<godzina>)")
    ap.add_argument("--out", default=str(ROOT / "bench" / "results" / "testy"))
    ap.add_argument("--note", help="uwaga do nagłówka tabeli")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--wsl", action="store_true", help="program GCC w WSL (dane na ext4, wątek wiąże libgomp)")
    ap.add_argument("--inside-wsl", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--from-raw", metavar="PLIKI_RAW_CSV")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    linux = args.wsl or not IS_WINDOWS
    args.bin = args.bin or ("build-gcc-release/bin/engine" if linux else "build/Release/engine.exe")
    curves = [c.strip() for c in args.curves.split(",") if c.strip()]
    sizes = [int(s) for s in args.sizes.split(",") if s.strip()]
    for c in curves:
        if c not in CURVES:
            ap.error(f"nieznana krzywa {c!r} (są: {', '.join(CURVES)})")
    if args.list:
        for c, d in CURVES.items():
            print(f"{c:13s} {d['desc']}; boki {', '.join(map(str, SIZES))}")
        return 0
    name = args.name or "krzywa_" + dt.datetime.now().strftime("%Y-%m-%d_%H%M")
    if args.from_raw:
        raw = []
        for s in args.from_raw.split(","):
            with open(s.strip(), encoding="utf-8") as f:
                raw += list(csv.DictReader(f))
        write(Path(args.out), name, raw, [f"# Czas na komórkę vs rozmiar siatki `{name}`", "",
                                          *[f"- Z `{Path(s.strip()).name}`" for s in args.from_raw.split(",")], ""])
        return 0

    if args.wsl and not args.inside_wsl:  # ten sam skrypt w WSL; tło mierzone po stronie Windows
        load_start = background_load()
        cmd = ["wsl", "-e", "env", "PYTHONIOENCODING=utf-8", "python3", wsl_path(Path(__file__)), "--inside-wsl",
               "--bin", wsl_path(ROOT / args.bin), "--curves", args.curves, "--sizes", args.sizes,
               "--reps", str(args.reps), "--name", name, "--out", wsl_path(Path(args.out))]
        if args.note:
            cmd += ["--note", args.note]
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
        tmp_root = Path.home() / ".cache" / "volcano_celltime"  # ext4; /tmp czyści WSL przy wyłączeniu maszyny
        shutil.rmtree(tmp_root, ignore_errors=True)
        (tmp_root / "bin").mkdir(parents=True, exist_ok=True)
        dst = tmp_root / "bin" / "engine"
        shutil.copy(exe, dst)
        os.chmod(dst, 0o755)
        exe, tmp = str(dst), tmp_root / "run"
        tmp.mkdir(parents=True, exist_ok=True)
    else:
        tmp = Path(tempfile.mkdtemp(prefix="volcano_celltime_"))
    runner = Runner(exe, tmp, args.inside_wsl)
    cfgs = {(c, n): runner.prepare_config({"id": f"{c}_{n}", "config": CURVES[c]["config"](n)})
            for c in curves for n in sizes}
    load_start = background_load()
    print(f"Krzywa {name}: {exe}; krzywe {', '.join(curves)}, boki {', '.join(map(str, sizes))}, "
          f"powtórzeń {args.reps}", flush=True)
    if load_start:
        print(f"Tło: {load_start['totalPercent']:.0f}% CPU ({', '.join(load_start['top'][:3])})", flush=True)
    runner.run(cfgs[(curves[0], sizes[0])], tmp / "warm", 1, "static", 0)  # rozgrzewka: program w pamięci systemu
    raw, t0 = [], time.time()
    for rep in range(args.reps):
        order = sizes if rep % 2 == 0 else sizes[::-1]
        for c in curves:
            for n in order:
                row = run_one(runner, c, n, cfgs[(c, n)], tmp / "out" / f"{c}_{n}")
                row.update({"name": name, "rep": rep, "timestamp": dt.datetime.now().isoformat(timespec="seconds")})
                raw.append(row)
                print(f"  {rep} {c:13s} n = {n:5d}  {fmt_ms(row['phaseMs'])} ms  {row['nsPerUnit']:.2f} ns / jedn.  "
                      f"siatka {float(row['gridBytes'] or 0) / MB:.2f} MB", flush=True)
    load_end = background_load()
    minutes = (time.time() - t0) / 60
    header = [f"# Czas na komórkę vs rozmiar siatki `{name}`", ""]
    if args.note:
        header += [args.note, ""]
    exe = Path(args.bin).resolve()  # w nagłówku ścieżka względem projektu (bez ścieżki prywatnej)
    exe = exe.relative_to(ROOT).as_posix() if exe.is_relative_to(ROOT) else exe.name
    header += [f"- Program: `{exe}`, 1 wątek (`parallel.affinity = "
               f"{'none' if args.inside_wsl else 'pcores'}`" + (", libgomp OMP_PROC_BIND=close" if args.inside_wsl
                                                                else ", priorytet wysoki") + ")",
               f"- {dt.datetime.now().isoformat(timespec='minutes')}, {minutes:.1f} min, powtórzeń {args.reps} "
               "(rozmiary naprzemiennie rosnąco / malejąco)"]
    if load_start:
        header.append(f"- Tło: start {load_start['totalPercent']:.0f}% CPU ({', '.join(load_start['top'][:3])}), "
                      f"koniec {load_end.get('totalPercent', 0):.0f}%")
    header.append("")
    write(Path(args.out), name, raw, header)
    if not args.inside_wsl:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"({minutes:.1f} min)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
