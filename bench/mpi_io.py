#!/usr/bin/env python3
"""Pomiar etapu 11 (typy pochodne MPI i MPI-IO): porównanie wariantów engine_mpi w tych samych warunkach co pomiar
skalowania z etapu 10 (bench/scaling_mpi.py: `--high-priority`, `parallel.affinity = pcores`, warianty naprzemiennie,
kolejność odwracana co powtórzenie, ≥ 5 powtórzeń, mediana [min–max]; wyniki każdego przebiegu porównywane bitowo
z pierwszym wariantem przypadku).

Grupy przypadków (warianty jak w scaling_mpi.py: m<p> — p procesów, przyrostki d / s / i — mpi.pack = datatype,
mpi.bcast = struct, mpi.io = mpiio):
  pack  — wymiana warstw brzegowych: pakowanie do bufora (m<p>) vs typy pochodne (m<p>d): czas wymiany (średnia po
          procesach), na jedną wymianę, cała faza obliczeń, bajty i komunikaty na wymianę, budowa typów;
  bcast — rozsyłanie configu: JSON (m<p>) vs blok struktury i kratery jako tablica struktur (m<p>s): MPI_Bcast, budowa
          Config na procesach ≠ 0 (parsowanie i walidacja / przepisanie pól), kratery / zarodki;
  io    — zapis wyników: zebranie na proces 0 (m<p>) vs MPI-IO (m<p>i), plik .bin i .txt osobno: czas zapisu (sekcja
          save / mcSave procesu 0 i czas pliku), MB/s, udział w total, formatowanie i samo MPI-IO (maks. po procesach),
          zebranie (MPI_Gatherv);
  read  — odczyt --mc-from: proces 0 czyta cały ca_result.bin i rozdziela pasy (MPI_Scatterv) vs każdy proces czyta swój
          pas (MPI_File_read_at_all). Wejście przygotowuje raz program engine (jeden wątek) przed pomiarem.

Wyniki (bench/results/mpi_io/<nazwa>*): _raw.csv (każdy przebieg) i .md (tabele grup). Pomiar dłuższy niż ~10 min
dzielić na części (--cases) i scalać: --from-raw a_raw.csv,b_raw.csv --name <nazwa>. WSL (--wsl): skrypt uruchamiany
w WSL (GCC + OpenMPI, `mpiexec --allow-run-as-root --use-hwthread-cpus --bind-to none`), programy i wszystkie wyniki
na ext4 (/tmp/volcano_mpi_io) — MPI-IO w WSL tylko tam; tło mierzone po stronie Windows. Windows: wyniki w folderze
tymczasowym systemu (NTFS).
Pamięć podręczna systemu plików: każdy przebieg pisze nowy plik (folder wyniku usuwany przed przebiegiem, wynik
porównany i usunięty zaraz po nim), a czas zapisu kończy się na zamknięciu pliku (bez wymuszania zapisu na dysk) —
w obu trybach tak samo. Plik wejściowy grupy read jest po zapisie przez engine w pamięci podręcznej, więc wszystkie
odczyty są „ciepłe”. Rozgrzewka: jeden przebieg pierwszego wariantu pierwszego przypadku przed pomiarem.

    python bench/mpi_io.py --list
    python bench/mpi_io.py --cases pack_lava_3d_front --variants m2,m2d,m8,m8d --reps 1 --min-reps 1 --name proba
    python bench/mpi_io.py --wsl --cases io_bin_classic_300 --variants m1,m1i,m8,m8i --name io_gcc_cz1
    python bench/mpi_io.py --wsl --mpiexec "mpiexec --mca io romio321" --cases io_txt_classic_2000 --variants m8,m8i
    python bench/mpi_io.py --from-raw bench/results/mpi_io/a_raw.csv,bench/results/mpi_io/b_raw.csv --name mpi_io_msvc
"""

from __future__ import annotations

import argparse
import copy
import csv
import datetime as dt
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ab import ROOT, background_load, classic, compare_dirs, deep_update, fmt_ms, from_file, wsl_path  # noqa: E402
from scaling import lava_big  # noqa: E402
from scaling_mpi import IO_FIELDS, MPI_FIELDS, SECTIONS, Runner, parse_variant  # noqa: E402

IS_WINDOWS = os.name == "nt"
OUT_DIR = ROOT / "bench" / "results" / "mpi_io"
PACK_VARIANTS = "m2,m2d,m4,m4d,m7,m7d,m8,m8d"
BCAST_VARIANTS = "m3,m3s,m8,m8s"
IO_VARIANTS = "m1,m1i,m2,m2i,m4,m4i,m8,m8i"
IO_SMALL_VARIANTS = "m1,m1i,m8,m8i"  # mały plik (lawa 3D, 14–19 MB)
READ_VARIANTS = "m1,m1i,m8,m8i"


def cases() -> list[dict]:
    """Przypadki: id, grupa, config, faza, harmonogram (jak w etapach 9–10), powtórzenia, warianty domyślne; read —
    config MC i config wyniku CA, który przed pomiarem liczy program engine (produce)."""
    mc_from = {"neighborhood": "moore", "boundary": "absorbing", "rngSeed": 42,
               "mc": {"enabled": True, "domain": "basalt", "update": "checkerboard", "Q": 50, "mcs": 0,
                      "mobilityFromCooling": True, "statsEvery": 10},
               "output": {"format": "bin"}}
    c300 = classic((300, 300, 300), 100, "von_neumann", fmt="bin")
    c2000 = classic((2000, 2000, 1), 400, "von_neumann", fmt="bin")
    mc100 = from_file("mc_full_3d", {"space": {"nx": 100, "ny": 100, "nz": 100}, "mc": {"mcs": 100, "statsEvery": 10,
                                                                                         "update": "checkerboard"},
                                     "output": {"format": "bin"}})
    fmt = lambda cfg, f: deep_update(copy.deepcopy(cfg), {"output": {"format": f}})  # noqa: E731
    return [
        {"id": "pack_lava_3d_front", "group": "pack", "phase": "caSim", "schedule": ("static", 1), "reps": 7,
         "variants": PACK_VARIANTS, "config": lava_big("front")},
        {"id": "pack_lava_3d_full", "group": "pack", "phase": "caSim", "schedule": ("guided", 0), "reps": 5,
         "variants": PACK_VARIANTS, "config": lava_big("full")},
        {"id": "pack_classic_300", "group": "pack", "phase": "caSim", "schedule": ("dynamic", 4), "reps": 5,
         "variants": PACK_VARIANTS, "config": fmt(c300, "none")},
        {"id": "pack_mc_cb_3d_100", "group": "pack", "phase": "mcSim", "schedule": ("dynamic", 0), "reps": 5,
         "variants": PACK_VARIANTS, "config": mc100},
        {"id": "bcast_etna_real", "group": "bcast", "phase": "caSim", "schedule": ("static", 1), "reps": 5,
         "variants": BCAST_VARIANTS, "config": from_file("etna_real")},
        {"id": "bcast_classic_2000", "group": "bcast", "phase": "caSim", "schedule": ("static", 0), "reps": 5,
         "variants": BCAST_VARIANTS, "config": fmt(c2000, "none")},
        {"id": "io_bin_classic_300", "group": "io", "phase": "caSim", "schedule": ("dynamic", 4), "reps": 5,
         "variants": IO_VARIANTS, "config": fmt(c300, "bin")},
        {"id": "io_txt_classic_300", "group": "io", "phase": "caSim", "schedule": ("dynamic", 4), "reps": 5,
         "variants": IO_VARIANTS, "config": fmt(c300, "txt")},
        {"id": "io_bin_classic_2000", "group": "io", "phase": "caSim", "schedule": ("static", 0), "reps": 5,
         "variants": IO_VARIANTS, "config": fmt(c2000, "bin")},
        {"id": "io_txt_classic_2000", "group": "io", "phase": "caSim", "schedule": ("static", 0), "reps": 5,
         "variants": IO_VARIANTS, "config": fmt(c2000, "txt")},
        {"id": "io_bin_lava_3d", "group": "io", "phase": "caSim", "schedule": ("static", 1), "reps": 5,
         "variants": IO_SMALL_VARIANTS, "config": fmt(lava_big("front"), "bin")},
        {"id": "io_txt_lava_3d", "group": "io", "phase": "caSim", "schedule": ("static", 1), "reps": 5,
         "variants": IO_SMALL_VARIANTS, "config": fmt(lava_big("front"), "txt")},
        {"id": "read_lava_3d", "group": "read", "phase": "mcSim", "schedule": ("static", 0), "reps": 7,
         "variants": READ_VARIANTS, "config": mc_from, "produce": fmt(lava_big("front"), "bin")},
        {"id": "read_classic_300", "group": "read", "phase": "mcSim", "schedule": ("static", 0), "reps": 5,
         "variants": READ_VARIANTS, "config": mc_from, "produce": fmt(c300, "bin")},
    ]


# ---------------------------------------------------------------------------
# Tabele
# ---------------------------------------------------------------------------
def med(rows: list[dict], key: str) -> float | None:
    vals = [float(r[key]) for r in rows if r.get(key) not in (None, "")]
    return statistics.median(vals) if vals else None


def span(rows: list[dict], key: str) -> str:
    """mediana [min–max]"""
    vals = [float(r[key]) for r in rows if r.get(key) not in (None, "")]
    if not vals:
        return "—"
    return f"{fmt_ms(statistics.median(vals))} [{fmt_ms(min(vals))}–{fmt_ms(max(vals))}]"


def f(v: float | None, fmt: str = "{:.2f}") -> str:
    return "—" if v is None else fmt.format(v)


def mb(v: float | None) -> str:
    return "—" if v is None else f"{v / 1e6:.2f} MB"


def ratio(num: float | None, den: float | None, fmt: str = "×{:.3f}") -> str:
    """num / den albo „—” (brak wartości, np. wymiana przy 1 procesie)."""
    return "—" if num is None or not den else fmt.format(num / den)


def pairs(rows: list[dict], flag: str) -> list[tuple[int, list[dict], list[dict]]]:
    """Pary (p, wiersze bez przyrostka, wiersze z przyrostkiem flag) wg liczby procesów."""
    out = []
    for p in sorted({int(r["procs"]) for r in rows}):
        base = [r for r in rows if int(r["procs"]) == p and r["variant"] == f"m{p}"]
        alt = [r for r in rows if int(r["procs"]) == p and r["variant"] == f"m{p}{flag}"]
        if base and alt:
            out.append((p, base, alt))
    return out


def table_pack(case: dict, rows: list[dict]) -> list[str]:
    ph = case["phase"]
    md = [f"### `{case['id']}` — wymiana warstw: pakowanie (m) vs typy pochodne (d)", "",
          "| p | faza m [ms] | faza d [ms] | d/m faza | wymiana m [ms] | wymiana d [ms] | d/m wymiana | na wymianę m / d "
          "[ms] | B / wymianę m / d | komunikaty / wymianę | typy (suma) | budowa typów [ms] | zgodne |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for p, a, b in pairs(rows, "d"):
        ex = med(a, "exchanges")
        pa, pb, ha, hb = med(a, ph), med(b, ph), med(a, "haloAvg"), med(b, "haloAvg")
        ok = all(str(r.get("identical")) in ("True", "true", "1") for r in a + b)
        md.append(f"| {p} | {span(a, ph)} | {span(b, ph)} | {ratio(pb, pa)} | {span(a, 'haloAvg')} | "
                  f"{span(b, 'haloAvg')} | {ratio(hb, ha)} | {ratio(ha, ex, '{:.3f}')} / {ratio(hb, ex, '{:.3f}')} | "
                  f"{mb(med(a, 'bytesPerExchange'))} / "
                  f"{mb(med(b, 'bytesPerExchange'))} | {f(med(a, 'messagesPerExchange'), '{:.1f}')} / "
                  f"{f(med(b, 'messagesPerExchange'), '{:.1f}')} | {f(med(b, 'typesBuilt'), '{:.0f}')} | "
                  f"{f(med(b, 'typeBuildAvg'), '{:.3f}')} | {'tak' if ok else '**NIE**'} |")
    return md + [""]


def table_bcast(case: dict, rows: list[dict]) -> list[str]:
    md = [f"### `{case['id']}` — rozsyłanie: JSON (m) vs struktury (s)", "",
          "| wariant | MPI_Bcast configu [ms] | config [B] | przygotowanie (proces 0) [ms] | budowa Config (maks.) [ms] "
          "| kratery [ms] | kratery [B] | razem [ms] | zgodne |", "|---|---|---|---|---|---|---|---|---|"]
    for v in dict.fromkeys(r["variant"] for r in rows):
        rv = [r for r in rows if r["variant"] == v]
        tot = [sum(float(r.get(k) or 0) for k in ("bcastConfigMs", "configPrepMs", "configBuildMax", "ventsMs"))
               for r in rv]
        ok = all(str(r.get("identical")) in ("True", "true", "1") for r in rv)
        md.append(f"| {v} | {span(rv, 'bcastConfigMs')} | {f(med(rv, 'bcastConfigBytes'), '{:.0f}')} | "
                  f"{span(rv, 'configPrepMs')} | {span(rv, 'configBuildMax')} | {span(rv, 'ventsMs')} | "
                  f"{f(med(rv, 'ventsBytes'), '{:.0f}')} | {fmt_ms(statistics.median(tot))} | "
                  f"{'tak' if ok else '**NIE**'} |")
    return md + [""]


def table_io(case: dict, rows: list[dict]) -> list[str]:
    key = "caTxt" if "_txt_" in case["id"] else "caBin"
    md = [f"### `{case['id']}` — zapis: zebranie na proces 0 (m) vs MPI-IO (i)", "",
          "| p | save m [ms] | save i [ms] | i/m | plik m [ms] | plik i [ms] | MB/s m / i | udział w total m / i | "
          "zebranie m (maks.) [ms] | formatowanie i (maks.) [ms] | MPI-IO i (maks.) [ms] | pamięć procesu 0 m / i "
          "[MB] | zgodne |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for p, a, b in pairs(rows, "i"):
        size = med(a, f"{key}Bytes") or 0
        fa, fb = med(a, f"{key}Ms"), med(b, f"{key}Ms")
        sa, sb = med(a, "save"), med(b, "save")
        ta, tb = med(a, "total"), med(b, "total")
        ok = all(str(r.get("identical")) in ("True", "true", "1") for r in a + b)
        md.append(f"| {p} | {span(a, 'save')} | {span(b, 'save')} | {ratio(sb, sa)} | {span(a, f'{key}Ms')} | "
                  f"{span(b, f'{key}Ms')} | {ratio(size / 1e3, fa, '{:.0f}')} / {ratio(size / 1e3, fb, '{:.0f}')} | "
                  f"{ratio(100 * sa, ta, '{:.1f}%')} / {ratio(100 * sb, tb, '{:.1f}%')} | "
                  f"{f(med(a, 'gatherMax'), '{:.1f}')} | "
                  f"{f(med(b, f'{key}FormatMax'), '{:.1f}')} | {f(med(b, f'{key}IoMax'), '{:.1f}')} | "
                  f"{ratio(med(a, 'peakRoot'), 1e6, '{:.0f}')} / {ratio(med(b, 'peakRoot'), 1e6, '{:.0f}')} | "
                  f"{'tak' if ok else '**NIE**'} |")
    size = med(rows, f"{key}Bytes")
    return md + [f"Plik: {mb(size)}. save — od końca fazy CA: pas bez ramki, (m) zebranie na proces 0, zapis pliku.",
                 ""]


def table_read(case: dict, rows: list[dict]) -> list[str]:
    md = [f"### `{case['id']}` — odczyt --mc-from: proces 0 + MPI_Scatterv (m) vs MPI_File_read_at_all (i)", "",
          "| p | readInput m [ms] | rozdział m (maks.) [ms] | odczyt i [ms] | MPI-IO i (maks.) [ms] | i / m (odczyt + "
          "rozdział) | total m / i [ms] | zgodne |", "|---|---|---|---|---|---|---|---|"]
    for p, a, b in pairs(rows, "i"):
        ra = (med(a, "readInput") or 0) + (med(a, "scatterMax") or 0)
        rb = med(b, "readInput") or 0
        ok = all(str(r.get("identical")) in ("True", "true", "1") for r in a + b)
        md.append(f"| {p} | {span(a, 'readInput')} | {f(med(a, 'scatterMax'), '{:.1f}')} | {span(b, 'readInput')} | "
                  f"{f(med(b, 'readIoMax'), '{:.1f}')} | {ratio(rb, ra)} | {fmt_ms(med(a, 'total'))} / "
                  f"{fmt_ms(med(b, 'total'))} | {'tak' if ok else '**NIE**'} |")
    by = med(rows, "readBytes")
    return md + [f"Przeczytane pasy (MPI-IO): {mb(by)} (type, solidStep, arrivalStep).", ""]


TABLES = {"pack": table_pack, "bcast": table_bcast, "io": table_io, "read": table_read}


def summarize(raw: list[dict], plan: list[dict]) -> list[str]:
    md = []
    for case in plan:
        rows = [r for r in raw if r["case"] == case["id"]]
        if rows:
            md += TABLES[case["group"]](case, rows)
    return md


def write_md(out_dir: Path, name: str, header: list[str], md: list[str]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / f"{name}.md", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(header + md) + "\n")
    print("\n".join(md))
    print(f"Zapisano {out_dir / (name + '.md')}")


# ---------------------------------------------------------------------------
# Pomiar
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bin", help="engine_mpi (domyślnie build/Release/engine_mpi.exe; z --wsl "
                                  "build-gcc-release/bin/engine_mpi)")
    ap.add_argument("--omp-bin", help="engine — przygotowanie wejścia grupy read (domyślnie build/Release/engine.exe; "
                                      "z --wsl build-gcc-release/bin/engine)")
    ap.add_argument("--mpiexec", default="mpiexec", help="polecenie mpiexec z ewentualnymi opcjami (domyślnie "
                                                         "mpiexec z PATH; np. \"mpiexec --mca io romio321\" — ROMIO "
                                                         "zamiast OMPIO w OpenMPI)")
    ap.add_argument("--cases", help="tylko wybrane przypadki (id po przecinku)")
    ap.add_argument("--variants", help="warianty dla wszystkich wybranych przypadków (domyślnie z tabeli przypadków)")
    ap.add_argument("--reps", type=int, help="powtórzenia (domyślnie z tabeli przypadków)")
    ap.add_argument("--min-reps", type=int, default=5, help="minimalna liczba powtórzeń (domyślnie 5)")
    ap.add_argument("--name", help="nazwa zestawu wyników (domyślnie mpi_io_<data>_<godzina>)")
    ap.add_argument("--out", default=str(OUT_DIR), help="folder wyników")
    ap.add_argument("--list", action="store_true", help="wypisz przypadki i zakończ")
    ap.add_argument("--wsl", action="store_true", help="pomiar w WSL (GCC + OpenMPI, wyniki na ext4)")
    ap.add_argument("--inside-wsl", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--from-raw", metavar="PLIKI_RAW_CSV", help="bez pomiaru: tabele z zapisanych _raw.csv")
    args = ap.parse_args()
    linux = args.wsl or not IS_WINDOWS
    args.bin = args.bin or ("build-gcc-release/bin/engine_mpi" if linux else "build/Release/engine_mpi.exe")
    args.omp_bin = args.omp_bin or ("build-gcc-release/bin/engine" if linux else "build/Release/engine.exe")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    plan = cases()
    if args.list:
        for c in plan:
            print(f"{c['group']:6s} {c['id']:24s} reps {c['reps']:2d}  warianty {c['variants']}")
        return 0
    if args.cases:
        wanted = [c.strip() for c in args.cases.split(",")]
        plan = [c for c in plan if c["id"] in wanted]
    if args.from_raw:
        if not args.name:
            ap.error("--from-raw wymaga --name")
        raw, notes = [], []
        for src in (Path(p.strip()) for p in args.from_raw.split(",") if p.strip()):
            with open(src, encoding="utf-8") as fh:
                raw += list(csv.DictReader(fh))
            part = src.with_name(src.name.replace("_raw.csv", ".md"))
            if part.exists():
                notes += [f"- `{src.name}`: {line.lstrip('- ')}" for line in part.read_text(encoding="utf-8").splitlines()
                          if line.startswith("- Tło") or line.startswith("- Czas pomiaru") or line.startswith("Tło")]
        header = [f"# Typy MPI i MPI-IO `{args.name}`", "", f"- Tabele z pomiaru w częściach: {args.from_raw}", *notes, ""]
        write_md(Path(args.out), args.name, header, summarize(raw, plan))
        return 0
    for c in plan:
        c["variant_list"] = [parse_variant(s) for s in (args.variants or c["variants"]).split(",") if s.strip()]
        c["reps"] = max(args.min_reps, args.reps if args.reps else c["reps"])
        too_many = [v["label"] for v in c["variant_list"] if v["cores"] > 8]
        if too_many:
            ap.error(f"tryb oszczędny: najwyżej 8 procesów × wątków (warianty {', '.join(too_many)})")
    name = args.name or "mpi_io_" + dt.datetime.now().strftime("%Y-%m-%d_%H%M")

    if args.wsl and not args.inside_wsl:
        load_start = background_load()
        cmd = ["wsl", "-e", "env", "PYTHONIOENCODING=utf-8", "python3", wsl_path(Path(__file__)), "--inside-wsl",
               "--bin", wsl_path(ROOT / args.bin), "--omp-bin", wsl_path(ROOT / args.omp_bin),
               "--min-reps", str(args.min_reps), "--name", name, "--out", wsl_path(Path(args.out))]
        for flag, val in (("--cases", args.cases), ("--variants", args.variants), ("--reps", args.reps),
                          ("--mpiexec", args.mpiexec if args.mpiexec != "mpiexec" else None)):
            if val:
                cmd += [flag, str(val)]
        r = subprocess.run(cmd)
        load_end = background_load()
        md = Path(args.out) / f"{name}.md"
        if md.exists() and load_start:
            with open(md, "a", encoding="utf-8", newline="\n") as fh:
                fh.write(f"\nTło (Windows, poza WSL): start {load_start['totalPercent']:.0f}% "
                         f"({', '.join(load_start['top'][:3])}), koniec {load_end.get('totalPercent', 0):.0f}%.\n")
        return r.returncode

    mpi_exe = args.bin if Path(args.bin).is_absolute() else str(ROOT / args.bin)
    omp_exe = args.omp_bin if Path(args.omp_bin).is_absolute() else str(ROOT / args.omp_bin)
    if args.inside_wsl:
        tmp_root = Path("/tmp/volcano_mpi_io")
        shutil.rmtree(tmp_root, ignore_errors=True)
        (tmp_root / "bin").mkdir(parents=True, exist_ok=True)
        for src, dst_name in ((mpi_exe, "engine_mpi"), (omp_exe, "engine")):
            dst = tmp_root / "bin" / dst_name
            shutil.copy(src, dst)
            os.chmod(dst, 0o755)
        mpi_exe, omp_exe = str(tmp_root / "bin" / "engine_mpi"), str(tmp_root / "bin" / "engine")
        tmp = tmp_root / "run"
        tmp.mkdir(parents=True, exist_ok=True)
    else:
        tmp = Path(tempfile.mkdtemp(prefix="volcano_mpi_io_"))
    runner = Runner(mpi_exe, omp_exe, tmp, args.inside_wsl, args.mpiexec)
    cfgs = {c["id"]: runner.prepare_config(c) for c in plan}

    # Wejście grupy read: wynik CA policzony raz programem engine (jeden wątek) — ten sam plik dla wszystkich wariantów.
    inputs = {}
    for c in plan:
        if "produce" in c:
            src_cfg = runner.prepare_config({"id": c["id"] + "_input", "config": c["produce"]})
            inputs[c["id"]] = tmp / "inputs" / c["id"]
            subprocess.run([omp_exe, "--config", str(src_cfg), "--out", str(inputs[c["id"]])], check=True,
                           stdout=subprocess.DEVNULL)

    load_start = background_load()
    total_runs = sum(c["reps"] * len(c["variant_list"]) for c in plan)
    print(f"Typy MPI i MPI-IO {name}: {mpi_exe}; przypadków {len(plan)}, przebiegów {total_runs}")
    if load_start:
        print(f"Tło: {load_start['totalPercent']:.0f}% CPU ({', '.join(load_start['top'][:3])})", flush=True)
    first = plan[0]  # rozgrzewka: pliki programu w pamięci podręcznej, start mpiexec
    runner.run(first["variant_list"][0], cfgs[first["id"]], tmp / "warm", first["phase"], *first["schedule"],
               inputs.get(first["id"]))
    shutil.rmtree(tmp / "warm", ignore_errors=True)

    raw: list[dict] = []
    failures = 0
    t_start = time.time()
    for rep in range(max(c["reps"] for c in plan)):
        for case in plan:
            if rep >= case["reps"]:
                continue
            variants = case["variant_list"]
            order = variants if rep % 2 == 0 else list(reversed(variants))
            ref_out = None
            line = []
            for v in order:
                out = tmp / "out" / f"{case['id']}__{v['label']}"
                row = runner.run(v, cfgs[case["id"]], out, case["phase"], *case["schedule"], inputs.get(case["id"]))
                row.update({"name": name, "case": case["id"], "group": case["group"], "variant": v["label"],
                            "kind": v["kind"], "procs": v["procs"], "threads": v["threads"], "cores": v["cores"],
                            "exchange": v["exchange"], "pack": v["pack"], "bcast": v["bcast"], "io": v["io"],
                            "schedule": case["schedule"][0], "chunk": case["schedule"][1], "rep": rep,
                            "timestamp": dt.datetime.now().isoformat(timespec="seconds")})
                # Zgodność z pierwszym wariantem kolejności tego powtórzenia; wynik usuwany od razu (pliki txt
                # classic 300³ mają ~0,6 GB — na dysku najwyżej dwa naraz).
                if ref_out is None:
                    ref_out = out
                    row["identical"] = True
                else:
                    diffs = compare_dirs(ref_out, out)
                    row["identical"] = not diffs
                    if diffs:
                        failures += 1
                        print(f"!!! RÓŻNICA WYNIKÓW: {case['id']} rep {rep}: {v['label']}: {'; '.join(diffs)}",
                              file=sys.stderr, flush=True)
                    shutil.rmtree(out, ignore_errors=True)
                raw.append(row)
                key = {"pack": case["phase"], "bcast": "bcastConfigMs", "io": "save", "read": "readInput"}[case["group"]]
                line.append(f"{v['label']} {float(row.get(key) or 0):8.2f}")
            shutil.rmtree(ref_out, ignore_errors=True)
            print(f"[{rep + 1}/{case['reps']}] {case['id']:22s} " + "  ".join(line), flush=True)
    load_end = background_load()
    minutes = (time.time() - t_start) / 60

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    keys = ["name", "case", "group", "variant", "kind", "procs", "threads", "cores", "exchange", "pack", "bcast", "io",
            "schedule", "chunk", "rep", "timestamp", *SECTIONS, "procWall", *MPI_FIELDS, "gatherMax", "initMax",
            "bcastMs", "bcastBytes", *IO_FIELDS, "priority", "cpus", "computePerRank", "identical"]
    with open(out_dir / f"{name}_raw.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        w.writerows(raw)
    raw_s = [{k: ("" if val is None else val) for k, val in r.items()} for r in raw]
    launch = (f"MS-MPI `{args.mpiexec} -n p`" if IS_WINDOWS else
              f"OpenMPI `{args.mpiexec} --allow-run-as-root --use-hwthread-cpus --bind-to none -n p` (WSL, wyniki na "
              "ext4)")
    header = [f"# Typy MPI i MPI-IO `{name}`", "",
              f"- Program: `{Path(args.bin).name}` ({launch}); `--high-priority`, `parallel.affinity = pcores`; warianty "
              "naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max]",
              f"- Czas pomiaru: {minutes:.1f} min, {dt.datetime.now().isoformat(timespec='minutes')}"]
    if load_start:
        header.append(f"- Tło: start {load_start['totalPercent']:.0f}% CPU ({', '.join(load_start['top'][:3])}), "
                      f"koniec {load_end.get('totalPercent', 0):.0f}%")
    header += ["- Zgodność wyników w przypadku: " + ("wszystkie przebiegi bitowo zgodne" if failures == 0
                                                     else f"**{failures} różnic**"), ""]
    write_md(out_dir, name, header, summarize(raw_s, plan))
    print(f"({minutes:.1f} min); różnic wyników: {failures}")
    shutil.rmtree(tmp, ignore_errors=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
