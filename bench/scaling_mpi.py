#!/usr/bin/env python3
"""Pomiar skalowania MPI (etap 10): przyspieszenie S(p) = T(1)/T(p), efektywność E(p) = S(p)/p, część szeregowa
z prawa Amdahla i udział komunikacji dla engine_mpi przy p procesach (domyślnie 1, 2, 3, 4, 6, 8 — tylko rdzenie P),
z wariantami hybrydowymi (procesy × wątki OpenMP), wariantem wymiany `mpi.exchange = changed` i — dla porównania przy
tej samej liczbie rdzeni — programem engine z wątkami OpenMP.

Warianty (--variants, po przecinku; pierwszy = odniesienie zgodności i T(1)):
  m<p>       engine_mpi na p procesach po 1 wątku                     (m1, m2, m3, m4, m6, m8)
  h<p>x<t>   engine_mpi na p procesach po t wątków (tryb hybrydowy)    (h2x4, h4x2)
  c<p>       engine_mpi na p procesach, mpi.exchange = changed         (c4, c8)
  o<t>       engine (OpenMP) na t wątkach                              (o1, o8)
  przyrostki wariantów MPI (etap 11, dowolne z d, s, i): d — mpi.pack = datatype, s — mpi.bcast = struct,
             i — mpi.io = mpiio, np. m8d, c8d, m4i, h2x4dsi (bez przyrostka — jak w etapie 10)
Każdy przebieg z `--high-priority` (mpiexec uruchamia procesy z priorytetem normalnym, a przy 8 zajętych rdzeniach P
proces wywłaszczony przez program w tle zatrzymuje pozostałe na wymianie / MPI_Allreduce) i przypięciem
`parallel.affinity = pcores`: proces r z t wątkami na rdzeniach P nr r·t … r·t + t − 1 (procesory logiczne 2, 4, …, 14,
0 — parallel/Affinity.hpp). Windows: `mpiexec -n p` (MS-MPI). WSL (--wsl): OpenMPI `mpiexec --allow-run-as-root
--use-hwthread-cpus --bind-to none -n p` — 8 miejsc na 8 procesorach wirtualnych (WSL zgłasza 4 rdzenie × 2 wątki SMT;
bez nadsubskrypcji, więc bez --oversubscribe), wiązanie robi sam program (te same zasady co na Windows; procesory
wirtualne bez gwarancji rdzeni fizycznych P), wariant o<t> jak w etapie 9 (libgomp OMP_PROC_BIND=close,
OMP_PLACES=cores).

Warianty idą naprzemiennie (kolejność odwracana co powtórzenie), powtórzenia ≥ 5, mediana [min–max]. Po każdym
powtórzeniu wyniki wszystkich wariantów są porównywane bitowo z pierwszym (bench/ab.py: compare_dirs). Tło CPU na
początku i końcu.

Miary z times.json: `total`, faza obliczeń (`caSim` / `mcSim`), z sekcji `mpi`: komunikacja w fazie (średnia i maks po
procesach: wymiana warstw brzegowych + MPI_Allreduce), obliczenia na proces (min / średnia / maks — nierównomierność
pasów = maks / średnia), bajty i komunikaty na wymianę, zebranie wyniku (MPI_Gatherv), statystyki MC (zebranie mapy
kryształów + union-find na procesie 0), rozsyłanie configu i terenu (MPI_Bcast), start MPI (MPI_Init_thread — wliczony
w total: OpenMPI w WSL ~0,3 s, MS-MPI kilkadziesiąt ms).

Wyniki (bench/results/mpi/<nazwa>*): _raw.csv (każdy przebieg), .csv (mediany, S, E), .md (tabela + Amdahl). Pomiar
dłuższy niż ~10 min dzielić na części (--cases) i scalać: --from-raw a_raw.csv,b_raw.csv --name <nazwa>.

    python bench/scaling_mpi.py --list
    python bench/scaling_mpi.py --wsl --cases lava_etna_real --reps 1 --variants m1,m3 --name proba
    python bench/scaling_mpi.py --wsl --cases lava_duza_3d_front,lava_duza_3d_full --name skalowanie_mpi_gcc_cz1
    python bench/scaling_mpi.py --wsl --variants m8,h2x4,h4x2,o8 --cases ... --name hybryda_gcc
    python bench/scaling_mpi.py --from-raw bench/results/mpi/a_raw.csv,bench/results/mpi/b_raw.csv --name skalowanie_mpi_gcc
"""

from __future__ import annotations

import argparse
import copy
import csv
import datetime as dt
import json
import os
import re
import shlex
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ab import ROOT, background_load, compare_dirs, fmt_ms, wsl_path  # noqa: E402
from scaling import amdahl_f, amdahl_s  # noqa: E402
from scaling import cases as omp_cases  # noqa: E402

IS_WINDOWS = os.name == "nt"
SECTIONS = ["readConfig", "readInput", "allocate", "terrain", "vents", "caSim", "caStats", "save", "mcInit", "mcSim",
            "mcStats", "mcSave", "total"]
DEFAULT_VARIANTS = "m1,m2,m3,m4,m6,m8"
# Miary z sekcji "mpi" w times.json (klucz w raw.csv -> ścieżka; stage = ca albo mc wg fazy przypadku).
MPI_FIELDS = {
    "commAvg": ("commMs", "avg"), "commMax": ("commMs", "max"), "haloAvg": ("haloMs", "avg"),
    "reduceAvg": ("reduceMs", "avg"), "computeMin": ("computeMs", "min"), "computeAvg": ("computeMs", "avg"),
    "computeMax": ("computeMs", "max"), "bytesPerExchange": ("bytesPerExchange",), "messagesPerExchange":
    ("messagesPerExchange",), "exchanges": ("exchanges",), "bytes": ("bytes",), "layersSkipped": ("layersSkipped",),
    "statsAvg": ("statsMs", "avg"), "statsGatherAvg": ("statsGatherMs", "avg"), "statsLabel": ("statsLabelMs",),
    "typesBuilt": ("typesBuilt",), "typeBuildAvg": ("typeBuildMs", "avg"),
}
# Etap 11: pliki wyników (sekcja files: rozmiar i czas zapisu na procesie 0; mpi.io.files: formatowanie i MPI-IO
# — maksimum po procesach) i rozsyłanie configu (mpi.bcast).
RESULT_FILES = {"ca_result.bin": "caBin", "ca_result.txt": "caTxt", "mc_result.bin": "mcBin", "mc_result.txt": "mcTxt"}
IO_FIELDS = [f"{s}{k}" for s in RESULT_FILES.values() for k in ("Ms", "Bytes", "FormatMax", "IoMax")] + \
    ["ioMode", "readIoMax", "readBytes", "scatterMax", "bcastMode", "bcastConfigMs", "bcastConfigBytes",
     "configPrepMs", "configBuildMax", "ventsMs", "ventsBytes", "peakRoot", "peakMax", "caPrepMax"]


def cases() -> list[dict]:
    """Przypadki skalowania z etapu 9 (bench/scaling.py), bez wariantu naiwnego MC (random — sekwencyjny, tylko 1
    proces). Harmonogram wątków (tryb hybrydowy) — jak w pomiarze OpenMP."""
    return [c for c in omp_cases() if not c["id"].startswith("mc_random")]


def parse_variant(spec: str) -> dict:
    """m3 / h2x4 / c8 / o8 (+ przyrostki etapu 11: d, s, i — np. m8d, h2x4dsi) -> opis wariantu."""
    m = re.fullmatch(r"([mhco])(\d+)(?:x(\d+))?([dsi]*)", spec.strip())
    if not m:
        raise ValueError(f"nieznany wariant {spec!r} (m<p>, h<p>x<t>, c<p>, o<t>; przyrostki d, s, i)")
    kind, a, b, flags = m.group(1), int(m.group(2)), m.group(3), m.group(4)
    if flags and kind == "o":
        raise ValueError(f"przyrostki d / s / i dotyczą tylko engine_mpi, podano {spec!r}")
    opts = {"pack": "datatype" if "d" in flags else "manual", "bcast": "struct" if "s" in flags else "json",
            "io": "mpiio" if "i" in flags else "gather"}
    if kind == "h":
        if b is None:
            raise ValueError(f"wariant hybrydowy wymaga postaci h<p>x<t>, podano {spec!r}")
        return {"label": spec, "kind": "mpi", "procs": a, "threads": int(b), "exchange": "always", "cores": a * int(b),
                **opts}
    if kind == "o":
        return {"label": spec, "kind": "omp", "procs": 1, "threads": a, "exchange": "always", "cores": a, **opts}
    return {"label": spec, "kind": "mpi", "procs": a, "threads": 1, "exchange": "changed" if kind == "c" else "always",
            "cores": a, **opts}


class Runner:
    def __init__(self, mpi_exe: str, omp_exe: str, tmp: Path, inside_wsl: bool, mpiexec: str):
        self.mpi_exe = mpi_exe
        self.omp_exe = omp_exe
        self.tmp = tmp
        self.inside_wsl = inside_wsl
        self.mpiexec = mpiexec
        self.flags = subprocess.HIGH_PRIORITY_CLASS if IS_WINDOWS else 0

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

    def command(self, v: dict, cfg: Path, out: Path, schedule: str, chunk: int,
                mc_from: Path | None = None) -> tuple[list[str], dict]:
        env = dict(os.environ)
        common = ["--config", str(cfg), "--out", str(out), "--threads", str(v["threads"]), "--high-priority",
                  "--set", f"parallel.schedule={schedule}", "--set", f"parallel.chunk={chunk}"]
        if mc_from is not None:
            common += ["--mc-from", str(mc_from)]
        if v["kind"] == "omp":
            # Jak w etapie 9: Windows — przypięcie przez program; WSL — libgomp (program bez przypinania).
            affinity = "pcores" if IS_WINDOWS else "none"
            if not IS_WINDOWS:
                env.update({"OMP_PROC_BIND": "close", "OMP_PLACES": "cores"})
            return [self.omp_exe, *common, "--set", f"parallel.affinity={affinity}"], env
        env.pop("OMP_PROC_BIND", None)
        env.pop("OMP_PLACES", None)
        # --mpiexec może mieć własne opcje (np. "mpiexec --mca io romio321" — implementacja MPI-IO w OpenMPI);
        # w Windows bez trybu POSIX, żeby ukośniki odwrotne ścieżki zostały.
        mpiexec = shlex.split(self.mpiexec, posix=not IS_WINDOWS)
        launch = [*mpiexec, "-n", str(v["procs"])]
        if not IS_WINDOWS:
            launch = [*mpiexec, "--allow-run-as-root", "--use-hwthread-cpus", "--bind-to", "none", "-n",
                      str(v["procs"])]
        return [*launch, self.mpi_exe, *common, "--set", "parallel.affinity=pcores",
                "--set", f"mpi.exchange={v['exchange']}", "--set", f"mpi.pack={v['pack']}",
                "--set", f"mpi.bcast={v['bcast']}", "--set", f"mpi.io={v['io']}"], env

    def run(self, v: dict, cfg: Path, out: Path, phase: str, schedule: str, chunk: int,
            mc_from: Path | None = None) -> dict:
        """Jeden przebieg; zwraca sekcje times.json, miary komunikacji (sekcja mpi) i czas procesu. mc_from — folder
        wyniku CA (engine --mc-from)."""
        shutil.rmtree(out, ignore_errors=True)
        cmd, env = self.command(v, cfg, out, schedule, chunk, mc_from)
        t0 = time.perf_counter()
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, creationflags=self.flags, env=env)
        wall = time.perf_counter() - t0
        if r.returncode != 0:
            raise RuntimeError(f"{' '.join(cmd[:8])} … zakończony kodem {r.returncode}: "
                               f"{r.stderr.decode('utf-8', 'replace')[-600:]}")
        with open(out / "times.json", encoding="utf-8") as f:
            times = json.load(f)
        row = {s: times[s] for s in SECTIONS if s in times}
        row["procWall"] = round(wall * 1000.0, 3)
        for name, short in RESULT_FILES.items():
            f = times.get("files", {}).get(name)
            if f:
                row[f"{short}Ms"] = f.get("writeMs")
                row[f"{short}Bytes"] = f.get("bytes")
        row["peakRoot"] = times.get("memory", {}).get("peakRssBytes")  # szczyt pamięci procesu 0
        mpi = times.get("mpi")
        if mpi:
            row["peakMax"] = mpi.get("peakRssBytes", {}).get("max")  # największy szczyt wśród procesów
            row["caPrepMax"] = mpi.get("ca", {}).get("gatherMs", {}).get("max")  # pas bez ramki (+ Gatherv)
            io = mpi.get("io", {})
            row["ioMode"] = io.get("mode", "gather")
            for f in io.get("files", []):
                short = RESULT_FILES.get(f.get("file"))
                if short:
                    row[f"{short}FormatMax"] = f.get("formatMs", {}).get("max")
                    row[f"{short}IoMax"] = f.get("ioMs", {}).get("max")
            if "read" in io:
                row["readIoMax"] = io["read"].get("ioMs", {}).get("max")
                row["readBytes"] = io["read"].get("bytes")
            if "scatter" in mpi:
                row["scatterMax"] = mpi["scatter"].get("ms", {}).get("max")
            bc = mpi.get("bcast", {})
            row["bcastMode"] = bc.get("mode", "json")
            row["bcastConfigMs"] = bc.get("configMs")
            row["bcastConfigBytes"] = bc.get("configBytes")
            row["configPrepMs"] = bc.get("configPrepMs")
            row["configBuildMax"] = bc.get("configBuildMs", {}).get("max")
            row["ventsMs"] = bc.get("ventsMs")
            row["ventsBytes"] = bc.get("ventsBytes")
            stage = mpi.get("ca" if phase == "caSim" else "mc", {})
            for key, path in MPI_FIELDS.items():
                val = stage
                for p in path:
                    val = val.get(p) if isinstance(val, dict) else None
                if val is not None:
                    row[key] = val
            row["gatherMax"] = mpi.get("gather", {}).get("ms", {}).get("max")
            row["initMax"] = mpi.get("initMs", {}).get("max")  # MPI_Init_thread (w total; WSL ~0,3 s)
            row["bcastMs"] = mpi.get("bcast", {}).get("configMs", 0) + mpi.get("bcast", {}).get("terrainMs", 0)
            row["bcastBytes"] = mpi.get("bcast", {}).get("configBytes", 0) + mpi.get("bcast", {}).get(
                "terrainBytes", 0)
            row["priority"] = " ".join(mpi.get("priority", []))
            row["cpus"] = " ".join("/".join(str(c) for c in cs) for cs in mpi.get("cpus", []))
            row["computePerRank"] = " ".join(str(x) for x in stage.get("perRank", {}).get("computeMs", []))
        else:
            row["cpus"] = " ".join(str(c) for c in times.get("cpus", []))
        return row


# ---------------------------------------------------------------------------
# Podsumowanie
# ---------------------------------------------------------------------------
def med(rows: list[dict], key: str) -> float | None:
    vals = [float(r[key]) for r in rows if r.get(key) not in (None, "")]
    return statistics.median(vals) if vals else None


def summarize(raw: list[dict], plan: list[dict], variants: list[dict]) -> tuple[list[dict], list[str]]:
    summary, md, amd = [], [], []
    md.append("| Przypadek | wariant | rdzenie | total [ms] | S | E | faza [ms] | S fazy | E fazy | komunikacja / faza "
              "| nierówność | B / wymianę | zgodne |")
    md.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    labels = [v["label"] for v in variants]
    by_label = {v["label"]: v for v in variants}
    for case in plan:
        rows = [r for r in raw if r["case"] == case["id"]]
        if not rows:
            continue
        phase = case["phase"]
        present = [l for l in labels if any(r["variant"] == l for r in rows)]
        present += [l for l in dict.fromkeys(r["variant"] for r in rows) if l not in present]
        ent = {}
        for l in present:
            rl = [r for r in rows if r["variant"] == l]
            v = by_label.get(l) or parse_variant(l)
            e = {"case": case["id"], "group": case["group"], "variant": l, "kind": v["kind"], "procs": v["procs"],
                 "threads": v["threads"], "cores": v["cores"], "exchange": v["exchange"], "phase": phase,
                 "n": len(rl)}
            for m in ["total", phase]:
                vals = [float(r[m]) for r in rl if r.get(m) not in (None, "")]
                e[f"{m}_med"] = statistics.median(vals)
                e[f"{m}_min"] = min(vals)
                e[f"{m}_max"] = max(vals)
            for k in [*SECTIONS, *MPI_FIELDS, "gatherMax", "initMax", "bcastMs", "bcastBytes", "procWall"]:
                if k not in ("total", phase):
                    x = med(rl, k)
                    if x is not None:
                        e[f"{k}_med"] = x
            if e.get("commAvg_med") is not None and e[f"{phase}_med"] > 0:
                e["comm_share"] = e["commAvg_med"] / e[f"{phase}_med"]
            if e.get("computeAvg_med"):
                e["imbalance"] = e["computeMax_med"] / e["computeAvg_med"]
            e["identical"] = all(str(r.get("identical")) in ("True", "true", "1") for r in rl)
            ent[l] = e
        ref = ent.get(present[0])
        base = None  # T(1): pierwszy wariant na 1 rdzeniu
        for l in present:
            if ent[l]["cores"] == 1:
                base = ent[l]
                break
        for l in present:
            e = ent[l]
            if base:
                e["S_total"] = base["total_med"] / e["total_med"]
                e["E_total"] = e["S_total"] / e["cores"]
                e["S_phase"] = base[f"{phase}_med"] / e[f"{phase}_med"]
                e["E_phase"] = e["S_phase"] / e["cores"]
            summary.append(e)
            f2 = lambda k: f"{e[k]:.2f}" if k in e else "—"  # noqa: E731
            share = f"{100 * e['comm_share']:.0f}%" if "comm_share" in e else "—"
            imb = f"×{e['imbalance']:.2f}" if "imbalance" in e else "—"
            bpe = fmt_ms(e["bytesPerExchange_med"]) if "bytesPerExchange_med" in e else "—"
            md.append(f"| {case['id']} | {l} | {e['cores']} | {fmt_ms(e['total_med'])} [{fmt_ms(e['total_min'])}–"
                      f"{fmt_ms(e['total_max'])}] | {f2('S_total')} | {f2('E_total')} | {fmt_ms(e[f'{phase}_med'])} "
                      f"[{fmt_ms(e[f'{phase}_min'])}–{fmt_ms(e[f'{phase}_max'])}] | {f2('S_phase')} | "
                      f"{f2('E_phase')} | {share} | {imb} | {bpe} | {'tak' if e['identical'] else '**NIE**'} |")
        # Amdahl dla czystego MPI (m<p>): S(p) całego przebiegu i fazy.
        pts = [(ent[l]["procs"], ent[l]) for l in present if l.startswith("m")]
        if base and len(pts) > 1 and ref is not None:
            f_tot = amdahl_f([(p, e["S_total"]) for p, e in pts])
            f_ph = amdahl_f([(p, e["S_phase"]) for p, e in pts])
            serial = (base["total_med"] - base[f"{phase}_med"]) / base["total_med"]
            if f_tot is not None and f_ph is not None:
                amd.append(f"| {case['id']} | {f_tot:.3f} | {f_ph:.3f} | {serial:.3f} | {amdahl_s(f_tot, 8):.2f} | "
                           f"{1 / f_tot if f_tot else float('inf'):.1f} |")
                for _, e in pts:
                    e["amdahl_f_total"] = f_tot
                    e["amdahl_f_phase"] = f_ph
                    e["serial_measured"] = serial
    md += ["", "Komunikacja / faza — średni po procesach czas wymiany warstw brzegowych i MPI_Allreduce w fazie "
           "obliczeń przez czas fazy (czekanie na wolniejszy pas wlicza się do MPI_Allreduce); nierówność — maks / "
           "średnia czasu obliczeń procesów; B / wymianę — bajty wszystkich komunikatów jednej wymiany."]
    if amd:
        md += ["", "Prawo Amdahla (warianty m<p>) — część szeregowa f (najmniejsze kwadraty na 1/S); „szeregowe "
               "z pomiaru” = (total − faza)/total przy 1 procesie; S(∞) = 1/f:", "",
               "| Przypadek | f (total) | f (faza) | szeregowe z pomiaru | S(8) z f | S(∞) |", "|---|---|---|---|---|---|"]
        md += amd
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
    """Tabela z zapisanych przebiegów (pomiar w częściach)."""
    srcs = [Path(p.strip()) for p in args.from_raw.split(",") if p.strip()]
    raw = []
    for s in srcs:
        with open(s, encoding="utf-8") as f:
            raw += list(csv.DictReader(f))
    ids = {c["id"] for c in plan}
    raw = [r for r in raw if r["case"] in ids]
    variants = [parse_variant(l) for l in dict.fromkeys(r["variant"] for r in raw)]
    summary, md = summarize(raw, plan, variants)
    notes = []
    for s in srcs:
        part_md = s.with_name(s.name.replace("_raw.csv", ".md"))
        if part_md.exists():
            for line in part_md.read_text(encoding="utf-8").splitlines():
                if line.startswith("- Tło") or line.startswith("- Czas pomiaru") or line.startswith("Tło"):
                    notes.append(f"- `{s.name}`: {line.lstrip('- ')}")
    header = [f"# Skalowanie MPI `{args.name}`", "",
              f"- Tabela z pomiaru w częściach: {', '.join(f'`{s.name}`' for s in srcs)}", *notes, ""]
    write_outputs(Path(args.out), args.name, summary, md, header)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bin", help="engine_mpi (domyślnie build/Release/engine_mpi.exe; z --wsl "
                                  "build-gcc-release/bin/engine_mpi)")
    ap.add_argument("--omp-bin", help="engine dla wariantów o<t> (domyślnie build/Release/engine.exe; z --wsl "
                                      "build-gcc-release/bin/engine)")
    ap.add_argument("--mpiexec", default="mpiexec", help="polecenie mpiexec (domyślnie z PATH)")
    ap.add_argument("--cases", help="tylko wybrane przypadki (id po przecinku)")
    ap.add_argument("--variants", default=DEFAULT_VARIANTS, help=f"warianty (domyślnie {DEFAULT_VARIANTS})")
    ap.add_argument("--reps", type=int, help="powtórzenia (domyślnie z tabeli przypadków)")
    ap.add_argument("--min-reps", type=int, default=5, help="minimalna liczba powtórzeń (domyślnie 5)")
    ap.add_argument("--name", help="nazwa zestawu wyników (domyślnie skalowanie_mpi_<data>_<godzina>)")
    ap.add_argument("--out", default=str(ROOT / "bench" / "results" / "mpi"), help="folder wyników")
    ap.add_argument("--note", default="", help="opis do nagłówka tabeli")
    ap.add_argument("--list", action="store_true", help="wypisz przypadki i zakończ")
    ap.add_argument("--wsl", action="store_true", help="pomiar w WSL (GCC + OpenMPI)")
    ap.add_argument("--inside-wsl", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--from-raw", metavar="PLIKI_RAW_CSV", help="bez pomiaru: tabela z zapisanych _raw.csv")
    args = ap.parse_args()
    linux = args.wsl or not IS_WINDOWS
    if not args.bin:
        args.bin = "build-gcc-release/bin/engine_mpi" if linux else "build/Release/engine_mpi.exe"
    if not args.omp_bin:
        args.omp_bin = "build-gcc-release/bin/engine" if linux else "build/Release/engine.exe"
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    plan = cases()
    if args.cases:
        wanted = [c.strip() for c in args.cases.split(",")]
        plan = [c for c in plan if c["id"] in wanted]
    variants = [parse_variant(s) for s in args.variants.split(",") if s.strip()]
    if args.list:
        for c in cases():
            print(f"{c['group']:10s} {c['id']:30s} reps {c['reps']:2d}  faza {c['phase']:6s} harmonogram "
                  f"{c['schedule'][0]},{c['schedule'][1]}")
        return 0
    if args.from_raw:
        if not args.name:
            ap.error("--from-raw wymaga --name")
        return from_raw(args, plan)
    too_many = [v["label"] for v in variants if v["cores"] > 8]
    if too_many:
        ap.error(f"tryb oszczędny: najwyżej 8 procesów × wątków (warianty {', '.join(too_many)})")
    name = args.name or "skalowanie_mpi_" + dt.datetime.now().strftime("%Y-%m-%d_%H%M")

    # --- tryb --wsl: ten sam skrypt w WSL; tło mierzone po stronie Windows ---
    if args.wsl and not args.inside_wsl:
        load_start = background_load()
        cmd = ["wsl", "-e", "env", "PYTHONIOENCODING=utf-8", "python3", wsl_path(Path(__file__)), "--inside-wsl",
               "--bin", wsl_path(ROOT / args.bin), "--omp-bin", wsl_path(ROOT / args.omp_bin),
               "--variants", args.variants, "--min-reps", str(args.min_reps), "--name", name,
               "--out", wsl_path(Path(args.out))]
        for flag, val in (("--cases", args.cases), ("--reps", args.reps), ("--note", args.note),
                          ("--mpiexec", args.mpiexec if args.mpiexec != "mpiexec" else None)):
            if val:
                cmd += [flag, str(val)]
        r = subprocess.run(cmd)
        load_end = background_load()
        md = Path(args.out) / f"{name}.md"
        if md.exists() and load_start:
            with open(md, "a", encoding="utf-8", newline="\n") as f:
                f.write(f"\nTło (Windows, poza WSL): start {load_start['totalPercent']:.0f}% "
                        f"({', '.join(load_start['top'][:3])}), koniec {load_end.get('totalPercent', 0):.0f}%.\n")
        return r.returncode

    mpi_exe = args.bin if Path(args.bin).is_absolute() else str(ROOT / args.bin)
    omp_exe = args.omp_bin if Path(args.omp_bin).is_absolute() else str(ROOT / args.omp_bin)
    if args.inside_wsl:
        tmp_root = Path("/tmp/volcano_scaling_mpi")
        shutil.rmtree(tmp_root / "run", ignore_errors=True)
        (tmp_root / "bin").mkdir(parents=True, exist_ok=True)
        # programy na ext4 maszyny WSL (start z dysku Windows /mnt/<dysk> przez 9P jest wolny)
        for src, dst_name in ((mpi_exe, "engine_mpi"), (omp_exe, "engine")):
            dst = tmp_root / "bin" / dst_name
            if Path(src).exists():
                shutil.copy(src, dst)
                os.chmod(dst, 0o755)
        mpi_exe = str(tmp_root / "bin" / "engine_mpi")
        omp_exe = str(tmp_root / "bin" / "engine")
        tmp = tmp_root / "run"
        tmp.mkdir(parents=True, exist_ok=True)
    else:
        tmp = Path(tempfile.mkdtemp(prefix="volcano_scaling_mpi_"))
    for exe, need in ((mpi_exe, any(v["kind"] == "mpi" for v in variants)),
                      (omp_exe, any(v["kind"] == "omp" for v in variants))):
        if need and not Path(exe).exists():
            print(f"Brak programu {exe}", file=sys.stderr)
            return 2
    runner = Runner(mpi_exe, omp_exe, tmp, args.inside_wsl, args.mpiexec)
    for c in plan:
        c["reps"] = max(args.min_reps, args.reps if args.reps else c["reps"])

    load_start = background_load()
    print(f"Skalowanie MPI {name}: {mpi_exe}; przypadków {len(plan)}, wariantów {len(variants)} "
          f"({', '.join(v['label'] for v in variants)}), przebiegów {sum(c['reps'] for c in plan) * len(variants)}")
    if load_start:
        print(f"Tło: {load_start['totalPercent']:.0f}% CPU ({', '.join(load_start['top'][:3])})", flush=True)
    cfgs = {c["id"]: runner.prepare_config(c) for c in plan}
    # Rozgrzewka: pliki programów w pamięci podręcznej systemu, start mpiexec.
    first = plan[0]
    for v in variants[:2]:
        runner.run(v, cfgs[first["id"]], tmp / "warm", first["phase"], *first["schedule"])

    raw: list[dict] = []
    failures = 0
    t_start = time.time()
    for rep in range(max(c["reps"] for c in plan)):
        for case in plan:
            if rep >= case["reps"]:
                continue
            order = variants if rep % 2 == 0 else list(reversed(variants))
            outs = {}
            for v in order:
                out = tmp / "out" / f"{case['id']}__{v['label']}__{rep}"
                row = runner.run(v, cfgs[case["id"]], out, case["phase"], *case["schedule"])
                row.update({"name": name, "case": case["id"], "group": case["group"], "variant": v["label"],
                            "kind": v["kind"], "procs": v["procs"], "threads": v["threads"], "cores": v["cores"],
                            "exchange": v["exchange"], "pack": v["pack"], "bcast": v["bcast"], "io": v["io"],
                            "schedule": case["schedule"][0], "chunk": case["schedule"][1],
                            "rep": rep, "timestamp": dt.datetime.now().isoformat(timespec="seconds")})
                outs[v["label"]] = (out, row)
                raw.append(row)
            ref_label = variants[0]["label"]
            outs[ref_label][1]["identical"] = True
            for label, (out, row) in outs.items():
                if label == ref_label:
                    continue
                diffs = compare_dirs(outs[ref_label][0], out)
                row["identical"] = not diffs
                if diffs:
                    failures += 1
                    print(f"!!! RÓŻNICA WYNIKÓW: {case['id']} rep {rep}: {label} vs {ref_label}: {'; '.join(diffs)}",
                          file=sys.stderr, flush=True)
            ph = case["phase"]
            print(f"[{rep + 1}/{case['reps']}] {case['id']:28s} " +
                  "  ".join(f"{v['label']} {outs[v['label']][1].get(ph, 0):8.1f}" for v in variants) + f"  ({ph})",
                  flush=True)
            for out, _ in outs.values():
                shutil.rmtree(out, ignore_errors=True)
    load_end = background_load()
    minutes = (time.time() - t_start) / 60

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    keys = ["name", "case", "group", "variant", "kind", "procs", "threads", "cores", "exchange", "pack", "bcast", "io",
            "schedule", "chunk", "rep", "timestamp", *SECTIONS, "procWall", *MPI_FIELDS, "gatherMax", "initMax",
            "bcastMs", "bcastBytes", *IO_FIELDS, "priority", "cpus", "computePerRank", "identical"]
    with open(out_dir / f"{name}_raw.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        w.writerows(raw)
    raw_s = [{k: ("" if v is None else v) for k, v in r.items()} for r in raw]
    summary, md = summarize(raw_s, plan, variants)
    header = [f"# Skalowanie MPI `{name}`", ""]
    if args.note:
        header += [args.note, ""]
    launch = ("MS-MPI `mpiexec -n p`" if IS_WINDOWS else
              "OpenMPI `mpiexec --allow-run-as-root --use-hwthread-cpus --bind-to none -n p` (WSL, procesory "
              "wirtualne)")
    header += [f"- Programy: `{Path(args.bin).name}` ({launch}), `{Path(args.omp_bin).name}` (warianty o<t>); "
               "`--high-priority`, przypięcie `parallel.affinity = pcores` (proces r z t wątkami na rdzeniach "
               "r·t … r·t + t − 1); warianty naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max] "
               "z n powtórzeń",
               f"- Czas pomiaru: {minutes:.1f} min, {dt.datetime.now().isoformat(timespec='minutes')}"]
    if load_start:
        header.append(f"- Tło: start {load_start['totalPercent']:.0f}% CPU ({', '.join(load_start['top'][:3])}), "
                      f"koniec {load_end.get('totalPercent', 0):.0f}%")
    header.append(f"- Zgodność wyników z `{variants[0]['label']}`: " +
                  ("wszystkie przebiegi bitowo zgodne" if failures == 0 else f"**{failures} różnic**"))
    header.append("")
    write_outputs(out_dir, name, summary, md, header)
    print(f"({minutes:.1f} min); różnic wyników: {failures}")
    if not args.inside_wsl:
        shutil.rmtree(tmp, ignore_errors=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
