#!/usr/bin/env python3
"""Pamięć główna wersji równoległych: szczyt pamięci procesu (RSS) i model pamięci (`MemoryModel`)
dla engine z p wątkami OpenMP i engine_mpi z p procesami (zebranie wyniku na proces 0 albo MPI-IO), kilka rozmiarów
siatki. Pamięć nie zależy od tła ani od turbo, więc pomiar nie wymaga wolnego komputera (krótkie przebiegi, 1 powtórzenie
— szczyt pamięci jest powtarzalny; sprawdzane --reps 2).

Co raportuje silnik (bez zmian w kodzie): `times.json` → `memory` (proces 0: startRssBytes, peakRssBytes,
peakPrivateBytes — Windows, model.peakBytes i skład szczytu peakBlocks), w engine_mpi dodatkowo `mpi.peakRssBytes`
(min / średnia / maks po procesach — suma = średnia × p), `mpi.split` (granice pasów) i `mpi.ca.ghostLayersBelow /
Above`. Model w silniku liczy tylko proces 0, więc model pozostałych procesów rozszerza ten skrypt: okno procesu r =
pas własny + warstwy brzegowe (lawa: do 17 pod pasem i 1 nad, classic / MC: po 1, periodycznie — pierścień), bajty na
komórkę okna z modelu procesu 0 (siatka z ramką, tablice pomocnicze, listy frontu — w proporcji do warstw własnych),
+ kopia pasu bez ramki do zapisu (13 B na komórkę pasa — `ownLayers`, nie rejestrowana w MemoryModel), + na procesie 0
w trybie gather wynik całej przestrzeni (`caResult`, rejestrowany). Typy pochodne (`mpi.pack = datatype`, ustawienie
pomiarów etapu 12) nie mają buforów pakowania; bufory biblioteki MPI (pamięć współdzielona między procesami) wchodzą
w narzut stały procesu, mierzony osobno na bardzo małej siatce (grupa base). Zapis MPI-IO przy p > 1 jest zbiorowy
i dwufazowy: proces 0 (jedyny agregator na jednym komputerze) zbiera dane innych procesów w buforze ≤ 16 MB (ROMIO,
`cb_buffer_size`; MS-MPI ma MPI-IO z ROMIO) — model procesu 0 = max(kroki, zapis: pas + min(16 MB, plik)).

Warianty jak w scaling_mpi.py: o<p> — engine na p wątkach; m<p>d — engine_mpi na p procesach, typy pochodne, gather;
m<p>di — to samo z MPI-IO. Wszystkie z `--high-priority` i `parallel.affinity = pcores` (≤ 8 rdzeni P), zapis `bin`.

Wyniki: bench/results/testy/<nazwa>_raw.csv (przebieg), <nazwa>.md (tabele). --from-raw — same tabele.

    python bench/memory.py --list
    python bench/memory.py --groups base,omp,mpi --name pamiec_msvc
    python bench/memory.py --wsl --cases classic2d_2000,lava3d_128,mc3d_100 --name pamiec_gcc
    python bench/memory.py --from-raw bench/results/testy/pamiec_msvc_raw.csv --name pamiec_msvc
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
from ab import ROOT, background_load, classic, deep_update, from_file, wsl_path  # noqa: E402
from scaling_mpi import Runner, parse_variant  # noqa: E402

IS_WINDOWS = os.name == "nt"
MB = 1024.0 * 1024.0
OMP_VARIANTS = ["o1", "o2", "o4", "o8"]
MPI_PROCS = [1, 2, 3, 4, 8]
CELL_RESULT = 13  # B na komórkę wyniku CA (Microstructure: typ 1 + flowId 4 + temp 4 + solidStep 2 + arrivalStep 2)
CB_BUFFER = 16 * 1024 * 1024  # bufor agregatora zapisu zbiorowego MPI-IO (ROMIO, wskazówka cb_buffer_size: 16 MB)


def lava_size(n: int) -> dict:
    """Lawa 3D n × n × 64 (jak lava_big z etapów 9–11 dla n = 128): stożek proporcjonalny do boku, 24 kratery."""
    return from_file("test_3d", {"space": {"nx": n, "ny": n, "nz": 64},
                                 "terrain": {"peakHeight": 48, "baseRadius": round(60 * n / 128), "craterRadius": 6},
                                 "vents": {"count": 24, "eruptionSteps": 400},
                                 "ca": {"coolingLateral": 20, "coolingFall": 15, "sweep": "front"},
                                 "output": {"format": "bin"}})


def mc3d(n: int) -> dict:
    return from_file("mc_full_3d", {"space": {"nx": n, "ny": n, "nz": n},
                                    "mc": {"mcs": 2, "statsEvery": 2, "update": "checkerboard"},
                                    "output": {"format": "bin"}})


def cases() -> list[dict]:
    """Przypadki: kilka rozmiarów classic 2D i 3D, lawy 3D, MC 3D (szachownica) i Etna; base — narzut stały procesu."""
    c = []
    for n, s in ((1000, 100), (2000, 400), (4000, 1600)):
        c.append({"id": f"classic2d_{n}", "group": "classic2d", "phase": "caSim",
                  "config": classic((n, n, 1), s, "von_neumann", fmt="bin"), "desc": f"classic {n}², VN"})
    for n in (100, 200, 300):
        c.append({"id": f"classic3d_{n}", "group": "classic3d", "phase": "caSim",
                  "config": classic((n, n, n), 100, "von_neumann", fmt="bin"), "desc": f"classic {n}³, VN"})
    for n in (64, 128, 256):
        c.append({"id": f"lava3d_{n}", "group": "lava3d", "phase": "caSim", "config": lava_size(n),
                  "desc": f"lawa {n}² × 64, front"})
    for n in (50, 100, 200):
        c.append({"id": f"mc3d_{n}", "group": "mc3d", "phase": "mcSim", "config": mc3d(n),
                  "desc": f"MC {n}³, Moore, szachownica"})
    c.append({"id": "etna_real", "group": "lava3d", "phase": "caSim", "config": from_file("etna_real"),
              "desc": "lawa `etna_real` (160 × 160 × 70)"})
    c.append({"id": "base_tiny", "group": "base", "phase": "caSim",
              "config": classic((16, 16, 16), 4, "von_neumann", fmt="bin"), "desc": "classic 16³ (narzut stały)"})
    for cc in c:
        cc["schedule"] = ("static", 0)
    return c


# ---------------------------------------------------------------------------
# Pomiar
# ---------------------------------------------------------------------------
def run_one(runner: Runner, v: dict, cfg: Path, out: Path) -> dict:
    shutil.rmtree(out, ignore_errors=True)
    cmd, env = runner.command(v, cfg, out, "static", 0)
    t0 = time.perf_counter()
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, creationflags=runner.flags, env=env)
    wall = time.perf_counter() - t0
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(map(str, cmd[:6]))} …: kod {r.returncode}: {r.stderr.decode('utf-8', 'replace')[-600:]}")
    with open(out / "times.json", encoding="utf-8") as f:
        t = json.load(f)
    mem = t.get("memory", {})
    model = mem.get("model", {})
    row = {"wallMs": round(wall * 1000, 1), "cells": t.get("cells"), "steps": t.get("steps"),
           "total": t.get("total"), "startRss": mem.get("startRssBytes"), "peakRss": mem.get("peakRssBytes"),
           "endRss": mem.get("endRssBytes"),
           "peakPrivate": mem.get("peakPrivateBytes"), "modelPeak": model.get("peakBytes"),
           "modelBlocks": json.dumps(model.get("peakBlocks", {})), "space": " ".join(map(str, t.get("space", [])))}
    # rozmiar plików wyniku binarnego (MPI-IO: bufor zapisu zbiorowego agregatora rośnie z plikiem do cb_buffer_size)
    row["resultBytes"] = sum(int(f.get("bytes") or 0) for n, f in t.get("files", {}).items()
                             if n in ("ca_result.bin", "mc_result.bin"))
    m = t.get("mpi")
    if m:
        pk = m.get("peakRssBytes", {})
        stage = m.get("ca") or m.get("mc") or {}
        row.update({"rssMin": pk.get("min"), "rssAvg": pk.get("avg"), "rssMax": pk.get("max"),
                    "axis": m.get("axis"), "layers": m.get("layers"), "split": " ".join(map(str, m.get("split", []))),
                    "ghostBelow": stage.get("ghostLayersBelow"), "ghostAbove": stage.get("ghostLayersAbove"),
                    "io": m.get("io", {}).get("mode"), "pack": m.get("pack")})
    shutil.rmtree(out, ignore_errors=True)
    return row


def measure(args, plan: list[dict], name: str) -> int:
    if args.inside_wsl:
        tmp = Path.home() / ".cache" / "volcano_mem"  # ext4 (MPI-IO w WSL tylko na ext4; /tmp czyści WSL)
        shutil.rmtree(tmp, ignore_errors=True)
        (tmp / "bin").mkdir(parents=True, exist_ok=True)
        exes = []
        for src, dst in ((args.bin, "engine_mpi"), (args.omp_bin, "engine")):
            d = tmp / "bin" / dst
            shutil.copy(ROOT / src, d)
            os.chmod(d, 0o755)
            exes.append(str(d))
        mpi_exe, omp_exe = exes
        mpiexec = "mpiexec --mca io romio321"  # ROMIO w WSL (decyzja po etapie 11)
    else:
        tmp = Path(tempfile.mkdtemp(prefix="volcano_mem_"))
        mpi_exe, omp_exe, mpiexec = str(ROOT / args.bin), str(ROOT / args.omp_bin), args.mpiexec
    runner = Runner(mpi_exe, omp_exe, tmp, args.inside_wsl, mpiexec)
    groups = args.groups.split(",")
    variants = []
    if "omp" in groups:
        variants += OMP_VARIANTS
    if "mpi" in groups:
        variants += [f"m{p}d" for p in MPI_PROCS] + [f"m{p}di" for p in MPI_PROCS]
    load_start = background_load()
    raw, t0 = [], time.time()
    for case in plan:
        cfg = runner.prepare_config(case)
        vs = variants if case["group"] != "base" else ["o1", "o8"] + [f"m{p}d" for p in range(1, 9)]
        if case["group"] == "base" and "base" not in groups:
            continue
        for rep in range(args.reps):
            for label in vs:
                v = parse_variant(label)
                row = run_one(runner, v, cfg, tmp / "out" / f"{case['id']}_{label}")
                row.update({"name": name, "case": case["id"], "group": case["group"], "variant": label,
                            "kind": v["kind"], "procs": v["procs"], "threads": v["threads"], "rep": rep,
                            "timestamp": dt.datetime.now().isoformat(timespec="seconds")})
                raw.append(row)
                print(f"{case['id']:16s} {label:6s} szczyt {float(row['peakRss'] or 0) / MB:8.1f} MB"
                      + (f", maks {float(row['rssMax']) / MB:8.1f}, suma {float(row['rssAvg']) * v['procs'] / MB:8.1f}"
                         if row.get("rssAvg") else "") + f", model p0 {float(row['modelPeak'] or 0) / MB:8.1f} MB",
                      flush=True)
    load_end = background_load()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    keys = list(dict.fromkeys(k for r in raw for k in r))
    with open(out_dir / f"{name}_raw.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, lineterminator="\n")
        w.writeheader()
        w.writerows([{k: ("" if r.get(k) is None else r.get(k)) for k in keys} for r in raw])
    minutes = (time.time() - t0) / 60
    note = [f"- Czas pomiaru: {minutes:.1f} min, {dt.datetime.now().isoformat(timespec='minutes')}"]
    if load_start:
        note.append(f"- Tło: start {load_start['totalPercent']:.0f}% CPU, koniec {load_end.get('totalPercent', 0):.0f}% "
                    "(pamięć nie zależy od tła)")
    write_report(raw, plan, out_dir, name, note)
    if not args.inside_wsl:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


# ---------------------------------------------------------------------------
# Model rozszerzony na procesy MPI
# ---------------------------------------------------------------------------
def window_layers(split: list[int], r: int, below: int, above: int, periodic: bool) -> int:
    """Warstwy okna procesu r: własne + brzegowe pod (≤ below) i nad (≤ above); periodycznie — zawsze pełne."""
    own = split[r + 1] - split[r]
    if periodic:
        return own + below + above
    return own + min(below, split[r]) + min(above, split[-1] - split[r + 1])


def framed(space: list[int], axis: str, lw: int) -> tuple[int, int]:
    """Komórki okna o lw warstwach: bez ramki i z ramką 1 komórki w osiach o rozmiarze > 1 (etap 8, k2)."""
    nx, ny, nz = space
    dims = [nx, lw, 1] if axis == "y" else [nx, ny, lw]
    cells = dims[0] * dims[1] * dims[2]
    fr = 1
    for d in dims:
        fr *= d + 2 if d > 1 else d
    return cells, fr


def mpi_model(row: dict) -> dict | None:
    """Model każdego procesu z modelu procesu 0 (bajty na komórkę okna) — suma i maksimum po procesach oraz narzut
    warstw brzegowych (siatka okna poza pasem własnym)."""
    if not row.get("split"):
        return None
    split = [int(x) for x in row["split"].split()]
    p = len(split) - 1
    space = [int(x) for x in row["space"].split()]
    axis = row["axis"]
    below, above = int(row.get("ghostBelow") or 1), int(row.get("ghostAbove") or 1)
    periodic = row["group"] in ("classic2d", "classic3d", "mc3d", "base")  # brzeg periodyczny w tych przypadkach
    blocks = json.loads(row["modelBlocks"] or "{}")
    lw0 = window_layers(split, 0, below, above, periodic)
    own0 = split[1] - split[0]
    c0, f0 = framed(space, axis, lw0)
    plane = c0 // lw0
    grid_key = "mcGrid" if "mcGrid" in blocks else "caGrid"
    b_grid = blocks.get(grid_key, 0) / f0           # B na komórkę okna z ramką
    b_aux = blocks.get("caAux", 0) / c0             # B na komórkę okna (D(n), znaczniki, mapa wysokości)
    b_front = blocks.get("caFront", 0) / (own0 * plane)  # listy frontu — w proporcji do warstw własnych (przybliżenie)
    root_only = sum(v for k, v in blocks.items() if k not in (grid_key, "caAux", "caFront"))  # caResult, statystyki MC
    per = []
    halo = 0.0
    for r in range(p):
        lw = window_layers(split, r, below, above, periodic)
        own = split[r + 1] - split[r]
        c, f = framed(space, axis, lw)
        mr = b_grid * f + b_aux * c + b_front * own * plane
        slab = CELL_RESULT * own * plane if grid_key == "caGrid" else 0.0
        mr += slab  # kopia pasa bez ramki do zapisu (r.slab)
        if r == 0:
            mr += root_only
            if row.get("io") == "mpiio" and p > 1 and grid_key == "caGrid":
                # Zapis zbiorowy (dwufazowy): proces 0 jest agregatorem i zbiera dane innych w buforze
                # ≤ cb_buffer_size; siatka okna jest już zwolniona, więc szczyt = max(kroki, zapis).
                mr = max(mr, slab + root_only + min(CB_BUFFER, float(row.get("resultBytes") or 0)))
        per.append(mr)
        halo += b_grid * (f - framed(space, axis, own)[1])
    grid_total = sum(b_grid * framed(space, axis, window_layers(split, r, below, above, periodic))[1] for r in range(p))
    return {"modelSum": sum(per), "modelMax": max(per), "modelMin": min(per), "haloBytes": halo,
            "haloShare": halo / grid_total if grid_total else 0.0, "gridOwnTotal": grid_total - halo}


# ---------------------------------------------------------------------------
# Tabele
# ---------------------------------------------------------------------------
def fmb(v) -> str:
    if v in (None, ""):
        return "—"
    v = float(v) / MB
    return f"{v:,.0f}".replace(",", " ") if v >= 100 else f"{v:.1f}".replace(".", ",")


def f2(v, d: int = 2) -> str:
    return "—" if v is None else f"{v:.{d}f}".replace(".", ",")


def med_rows(raw: list[dict]) -> dict[tuple[str, str], dict]:
    """Mediana powtórzeń (pola liczbowe) dla każdej pary (przypadek, wariant)."""
    groups: dict[tuple[str, str], list[dict]] = {}
    for r in raw:
        groups.setdefault((r["case"], r["variant"]), []).append(r)
    out = {}
    for key, rs in groups.items():
        e = dict(rs[0])
        for k in ("peakRss", "startRss", "endRss", "peakPrivate", "modelPeak", "rssMin", "rssAvg", "rssMax", "wallMs",
                  "total"):
            vals = [float(x[k]) for x in rs if x.get(k) not in (None, "")]
            if vals:
                e[k] = statistics.median(vals)
        e["n"] = len(rs)
        e["spread"] = (max(float(x["peakRss"]) for x in rs) - min(float(x["peakRss"]) for x in rs)) if rs else 0.0
        out[key] = e
    return out


def write_report(raw: list[dict], plan: list[dict], out_dir: Path, name: str, note: list[str]) -> None:
    med = med_rows(raw)
    by_case = {c["id"]: c for c in plan}
    md = [f"# Pamięć główna `{name}`", "",
          "- Szczyt pamięci procesu: Windows `PeakWorkingSetSize`, Linux `ru_maxrss` (proces 0 — `memory.peakRssBytes`; "
          "MPI: `mpi.peakRssBytes` min / średnia / maks po procesach, suma = średnia × p). Model: `MemoryModel` "
          "(duże tablice × `sizeof`; proces 0 — z silnika, pozostałe procesy — rozszerzenie w skrypcie). MB = 2²⁰ B.",
          *note, ""]
    # Narzut stały procesu (base).
    base = {k[1]: v for k, v in med.items() if k[0] == "base_tiny"}
    base_mpi = {}
    if base:
        md += ["## Narzut stały procesu (classic 16³ — dane < 0,1 MB)", "",
               "| Wariant | szczyt procesu 0 [MB] | na starcie (proces 0) [MB] | na końcu (proces 0) [MB] | "
               "średnio na proces [MB] | maks [MB] |",
               "|---|---|---|---|---|---|"]
        for lab in sorted(base, key=lambda l: (l[0] != "o", parse_variant(l)["cores"])):
            e = base[lab]
            md.append(f"| {lab} | {fmb(e['peakRss'])} | {fmb(e.get('startRss'))} | {fmb(e.get('endRss'))} | "
                      f"{fmb(e.get('rssAvg') or e['peakRss'])} | {fmb(e.get('rssMax') or e['peakRss'])} |")
            if lab.startswith("m"):
                base_mpi[parse_variant(lab)["procs"]] = float(e["rssAvg"])
        md.append("")
    base_omp = None
    if "o1" in base:
        # Linux: ru_maxrss dziedziczy szczyt procesu rodzica przez fork / exec (Python ~17 MB), więc szczyt bardzo
        # małego przypadku to RSS rodzica — narzut stały z RSS na końcu przebiegu (/proc/self/statm), jeśli jest.
        b = base["o1"]
        base_omp = min(float(b["peakRss"]), float(b["endRss"])) if b.get("endRss") not in (None, "") else \
            float(b["peakRss"])

    # OpenMP: pamięć vs liczba wątków.
    omp_cases = [c for c in plan if c["group"] != "base" and any(k == (c["id"], "o1") for k in med)]
    if omp_cases:
        md += ["## OpenMP — szczyt pamięci w funkcji liczby wątków", "",
               "| Przypadek | komórki | 1 wątek [MB] | 2 | 4 | 8 | 8 / 1 | model [MB] | (szczyt − narzut) / model | "
               "B / komórkę: pomiar / model |", "|---|---|---|---|---|---|---|---|---|---|"]
        for c in omp_cases:
            e = {lab: med.get((c["id"], lab)) for lab in OMP_VARIANTS}
            if not e["o1"]:
                continue
            cells = float(e["o1"]["cells"])
            data = float(e["o1"]["peakRss"]) - (base_omp or float(e["o1"]["startRss"]))
            model = float(e["o1"]["modelPeak"])
            cells_txt = f"{cells:,.0f}".replace(",", " ")
            md.append(f"| {c['desc']} | {cells_txt} | {fmb(e['o1']['peakRss'])} | " + " | ".join(fmb(e[l]['peakRss']) if e[l] else "—"
                                                                       for l in ('o2', 'o4', 'o8')) +
                      f" | {f2(float(e['o8']['peakRss']) / float(e['o1']['peakRss']), 3) if e['o8'] else '—'} | "
                      f"{fmb(model)} | {f2(data / model, 3)} | {f2(data / cells, 1)} / {f2(model / cells, 1)} |")
        md += ["", f"Narzut stały = szczyt classic 16³ przy 1 wątku ({fmb(base_omp)} MB; w Linuksie RSS na końcu "
               "przebiegu — `ru_maxrss` bardzo małego procesu pokazuje szczyt procesu, który go uruchomił).", ""]

    # MPI: suma, maksimum, model, warstwy brzegowe.
    mpi_cases = [c for c in plan if c["group"] != "base" and any(k == (c["id"], "m1d") for k in med)]
    if mpi_cases:
        md += ["## MPI — pamięć wszystkich procesów i procesu 0", "",
               "Suma = średnia × p; „dane” = pomiar − p × narzut stały procesu MPI (grupa base, ta sama liczba "
               "procesów). Model: suma / maksimum po procesach (rozszerzenie modelu procesu 0; MPI-IO przy p > 1 — "
               "proces 0 z buforem agregatora zapisu zbiorowego ≤ 16 MB); warstwy brzegowe = siatka okien poza pasami "
               "własnymi (udział w siatce wszystkich okien).", "",
               "| Przypadek | p | zapis | suma [MB] | dane: suma [MB] | model: suma [MB] | dane / model | maks [MB] | "
               "proces 0 [MB] | model: maks [MB] | min [MB] | warstwy brzegowe [MB] (udział) | suma / 1 proces |",
               "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for c in mpi_cases:
            one = med.get((c["id"], "m1d"))
            one_data = float(one["rssAvg"]) - base_mpi.get(1, 0.0)
            for io in ("d", "di"):
                for p in MPI_PROCS:
                    e = med.get((c["id"], f"m{p}{io}"))
                    if not e or not e.get("rssAvg"):
                        continue
                    mm = mpi_model(e) or {}
                    tot = float(e["rssAvg"]) * p
                    data = tot - p * base_mpi.get(p, 0.0)
                    md.append(f"| {c['desc']} | {p} | {'MPI-IO' if io == 'di' else 'gather'} | {fmb(tot)} | {fmb(data)} | "
                              f"{fmb(mm.get('modelSum'))} | {f2(data / mm['modelSum'], 3) if mm else '—'} | "
                              f"{fmb(e['rssMax'])} | {fmb(e['peakRss'])} | {fmb(mm.get('modelMax'))} | {fmb(e['rssMin'])} "
                              f"| {fmb(mm.get('haloBytes'))} ({100 * mm.get('haloShare', 0):.0f}%) | "
                              f"{f2(data / one_data, 2) if one_data > 0 else '—'} |")
        md.append("")
    with open(out_dir / f"{name}.md", "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(md) + "\n")
    print("\n".join(md))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bin", help="engine_mpi (domyślnie build/Release/engine_mpi.exe; WSL build-gcc-release/bin/engine_mpi)")
    ap.add_argument("--omp-bin", help="engine (domyślnie build/Release/engine.exe; WSL build-gcc-release/bin/engine)")
    ap.add_argument("--mpiexec", default="mpiexec")
    ap.add_argument("--cases", help="przypadki (id po przecinku)")
    ap.add_argument("--groups", default="base,omp,mpi", help="base (narzut stały), omp, mpi")
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--name", default="pamiec")
    ap.add_argument("--out", default=str(ROOT / "bench" / "results" / "testy"))
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--wsl", action="store_true")
    ap.add_argument("--inside-wsl", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--from-raw", metavar="PLIKI_RAW_CSV")
    args = ap.parse_args()
    linux = args.wsl or not IS_WINDOWS
    args.bin = args.bin or ("build-gcc-release/bin/engine_mpi" if linux else "build/Release/engine_mpi.exe")
    args.omp_bin = args.omp_bin or ("build-gcc-release/bin/engine" if linux else "build/Release/engine.exe")
    sys.stdout.reconfigure(encoding="utf-8")
    plan = cases()
    if args.list:
        for c in plan:
            print(f"{c['group']:10s} {c['id']:16s} {c['desc']}")
        return 0
    if args.cases:
        wanted = [x.strip() for x in args.cases.split(",")]
        plan = [c for c in plan if c["id"] in wanted or (c["group"] == "base" and "base" in args.groups)]
    if args.from_raw:
        raw = []
        for s in args.from_raw.split(","):
            with open(s.strip(), encoding="utf-8") as f:
                raw += list(csv.DictReader(f))
        note = [f"- Tabela z `{Path(s.strip()).name}`" for s in args.from_raw.split(",")]
        old = Path(args.out) / f"{args.name}.md"
        if old.exists():  # czas pomiaru i tło z poprzedniej wersji tabeli
            note += [l for l in old.read_text(encoding="utf-8").splitlines() if l.startswith(("- Czas pomiaru", "- Tło"))]
        write_report(raw, plan, Path(args.out), args.name, note)
        return 0
    if args.wsl and not args.inside_wsl:
        cmd = ["wsl", "-e", "env", "PYTHONIOENCODING=utf-8", "python3", wsl_path(Path(__file__)), "--inside-wsl",
               "--bin", args.bin, "--omp-bin", args.omp_bin, "--groups", args.groups, "--reps", str(args.reps),
               "--name", args.name, "--out", wsl_path(Path(args.out))]
        if args.cases:
            cmd += ["--cases", args.cases]
        return subprocess.run(cmd).returncode
    return measure(args, plan, args.name)


if __name__ == "__main__":
    sys.exit(main())
