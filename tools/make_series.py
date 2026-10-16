"""Seria zadań bez GUI (etap 5): config bazowy + parametry zmienne -> folder configów -> engine --batch.

Ten sam generator co zakładka „Seria” w GUI (moduł gui/series.py — bez FastAPI): iloczyn kartezjański osi,
parowanie kluczy, zakresy, potęgi, nazwy NN_<opis>.json, series.json. Najpierw zapisuje WSZYSTKIE configi
(<configs-out>/<id>/) i foldery wyników (<results-out>/<id>/), a z --run od razu zleca obliczenia:
`engine --batch <configs-out>/<id> --out <results-out>/<id>` (każdy config w osobnym procesie silnika,
na końcu batch_summary.csv) i wypisuje tabelę porównania (gui/compare.py).

Przykłady (z katalogu volcano-ca-mc):
    # gotowy szablon (lista: --list-templates), od razu z obliczeniami, proces przypięty do rdzenia P
    python tools/make_series.py --template ca_vs_mc --run --cpu 2
    # mniejsza wersja szablonu: oś „rozmiar” zastąpiona krótszą listą
    python tools/make_series.py --template ca_vs_mc --name ca_vs_mc_mala --run ^
        --vary "rozmiar:space.nx,space.ny,space.nz=[2D_100x100] 100;100;1, [2D_200x200] 200;200;1, [3D_10x10x10] 10, [3D_25x25x25] 25"
    # własna seria: config bazowy z pliku, dwa parametry (sparowane nx+ny), potęgi liczby zarodków
    python tools/make_series.py --base configs/classic_ref.json --set space.nz=1 ^
        --vary "space.nx,space.ny=100, 200, 400" --pow "vents.count=1:1000:10" --run
    python tools/make_series.py --spec moja_seria.json --dry-run      # opis serii z pliku JSON (jak body POST /api/series)

Składnia parametru: [nazwa_osi:]klucz[,klucz2...]=wartości
    --vary   lista: "100, 200, 500"; krotki dla kluczy sparowanych "100;100;1"; etykiety "[CA] false;basalt"
    --range  od:do:krok        (np. "mc.mcs=20:100:20")
    --pow    od:do:mnożnik     (np. "vents.count=1:1000:10")
Nazwa osi równa nazwie osi szablonu zastępuje tę oś (np. „rozmiar”); inna — dodaje nową oś (razem 1–3 osie).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gui import compare, series  # noqa: E402
from gui.settings import find_engine  # noqa: E402


def parse_param(text: str, mode: str, number: int) -> dict:
    """„[nazwa:]klucze=wartości” -> opis osi dla gui/series.axis_from_dict."""
    if "=" not in text:
        raise series.SeriesError(f"Parametr „{text}” — oczekiwano postaci [nazwa:]klucz=wartości")
    left, values = text.split("=", 1)
    name, keys = (left.split(":", 1) if ":" in left else ("", left))
    axis = {"name": name.strip() or keys.split(",")[0].strip().split(".")[-1], "keys": keys, "mode": mode}
    if mode == "list":
        axis["text"] = values
    else:
        parts = [p.strip() for p in re.split(r"[:;]", values)]
        if len(parts) != 3:
            raise series.SeriesError(f"Parametr „{text}” — zakres/potęgi to od:do:{'krok' if mode == 'range' else 'mnożnik'}")
        axis.update(start=parts[0], stop=parts[1], **({"step": parts[2]} if mode == "range" else {"factor": parts[2]}))
    return axis


def engine_defaults(engine: Path | None) -> dict | None:
    """Pełny domyślny config silnika (engine --print-defaults) — do sprawdzenia kluczy i opisu bazy."""
    if engine is None:
        return None
    p = subprocess.run([str(engine), "--print-defaults"], capture_output=True, text=True, encoding="utf-8")
    return json.loads(p.stdout) if p.returncode == 0 else None


def pin_self(cpu: int) -> str:
    """Przypięcie procesu skryptu do procesora logicznego cpu — engine i jego przebiegi dziedziczą maskę."""
    try:
        import psutil
        psutil.Process().cpu_affinity([cpu])
        if sys.platform == "win32":
            psutil.Process().nice(psutil.HIGH_PRIORITY_CLASS)
        return f"psutil: procesor logiczny {cpu}" + (", priorytet wysoki" if sys.platform == "win32" else "")
    except ImportError:
        if sys.platform == "win32":
            import ctypes
            k32 = ctypes.windll.kernel32
            k32.SetProcessAffinityMask(k32.GetCurrentProcess(), ctypes.c_size_t(1 << cpu))
            return f"SetProcessAffinityMask: procesor logiczny {cpu}"
        os.sched_setaffinity(0, {cpu})
        return f"sched_setaffinity: procesor logiczny {cpu}"


def main() -> int:
    # Konsola Windows bez UTF-8 (np. potok w Git Bash, cp1250) — znaki spoza strony kodowej jako „?”.
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description="Seria zadań bez GUI: configi + engine --batch (etap 5)",
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 2)[2])
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--template", help="gotowy szablon serii (jak w GUI), np. ca_vs_mc")
    src.add_argument("--base", help="config bazowy (plik JSON); bez --template i --base — wartości domyślne silnika")
    src.add_argument("--spec", help="pełny opis serii w JSON: {name, base, axes: [...], chart}")
    ap.add_argument("--list-templates", action="store_true", help="wypisz szablony i zakończ")
    ap.add_argument("--name", help="nazwa serii (domyślnie: szablon albo „seria”)")
    ap.add_argument("--set", action="append", default=[], metavar="KLUCZ=WARTOŚĆ", help="zmiana configu bazowego (wiele razy)")
    ap.add_argument("--vary", action="append", default=[], metavar="[OŚ:]KLUCZE=LISTA", help="oś: lista wartości")
    ap.add_argument("--range", action="append", default=[], metavar="[OŚ:]KLUCZE=OD:DO:KROK", help="oś: zakres liniowy")
    ap.add_argument("--pow", action="append", default=[], metavar="[OŚ:]KLUCZE=OD:DO:MNOŻNIK", help="oś: potęgi")
    ap.add_argument("--configs-out", default=str(ROOT / "configs" / "series"), help="folder na foldery configów serii")
    ap.add_argument("--results-out", default=str(ROOT / "results" / "series"), help="folder na foldery wyników serii")
    ap.add_argument("--engine", help="program silnika (domyślnie wykrywany jak w GUI: build/Release/engine.exe …)")
    ap.add_argument("--run", action="store_true", help="po zapisaniu plików uruchom engine --batch")
    ap.add_argument("--cpu", type=int, help="przypnij obliczenia do procesora logicznego (np. 2 — rdzeń P)")
    ap.add_argument("--dry-run", action="store_true", help="tylko pokaż zadania (bez zapisu plików)")
    args = ap.parse_args()

    if args.list_templates:
        for t in series.TEMPLATES:
            n = 1
            for a in t["axes"]:
                n *= len(a["points"])
            print(f"{t['id']:14s} {t['name']} — {n} zadań\n{'':15s}{t['description']}")
        return 0

    engine = Path(args.engine) if args.engine else find_engine(ROOT)
    defaults = engine_defaults(engine)
    try:
        if args.spec:
            spec = series.spec_from_dict(json.loads(Path(args.spec).read_text(encoding="utf-8")))
        elif args.template:
            spec = series.template_spec(args.template, ROOT / "configs", defaults)
        else:
            base = {}
            if args.base:
                base = {k: v for k, v in json.loads(Path(args.base).read_text(encoding="utf-8")).items() if not k.startswith("_")}
            spec = series.SeriesSpec(name="seria", base=series.deep_merge(defaults or {}, base), axes=[])
        if args.name:
            spec.name = args.name
        for kv in args.set:
            key, _, value = kv.partition("=")
            series.set_path(spec.base, key.strip(), series.parse_value(value))
        # Osie z linii poleceń: ta sama nazwa co oś szablonu — zastępuje ją, inna — dodaje nową oś.
        params = [(t, "list") for t in args.vary] + [(t, "range") for t in args.range] + [(t, "pow") for t in args.pow]
        for i, (text, mode) in enumerate(params, len(spec.axes) + 1):
            axis = series.axis_from_dict(parse_param(text, mode, i), i)
            names = [a.name for a in spec.axes]
            if axis.name in names:
                spec.axes[names.index(axis.name)] = axis
            else:
                spec.axes.append(axis)
        allowed = set(series.leaf_paths(defaults)) if defaults else None
        jobs = series.expand(spec, allowed)
    except (series.SeriesError, OSError, json.JSONDecodeError) as e:
        for msg in getattr(e, "errors", [str(e)]):
            print(f"Błąd: {msg}", file=sys.stderr)
        return 1

    print(f"Seria „{spec.name}”: {len(jobs)} zadań = {' × '.join(f'{len(a.points)} ({a.name})' for a in spec.axes)}")
    for w in series.preview_warnings(jobs):
        print(f"Ostrzeżenie: {w}")
    for j in jobs:
        print(f"  {j.name:36s} " + ", ".join(f"{k}={json.dumps(v, ensure_ascii=False)}" for k, v in j.values.items()))
    if args.dry_run:
        return 0

    cfg_root, res_root = Path(args.configs_out), Path(args.results_out)
    sid = series.new_series_id(spec.name, lambda s: (cfg_root / s).exists() or (res_root / s).exists())
    meta = series.write_series(spec, jobs, cfg_root, res_root, sid, root=ROOT, source="tools/make_series.py")
    print(f"Zapisano {len(jobs)} configów + series.json: {meta['configsDir']}/")
    print(f"Foldery wyników: {meta['resultsDir']}/")
    if not args.run:
        print(f"Obliczenia: {engine or 'engine'} --batch {meta['configsDir']} --out {meta['resultsDir']}")
        return 0
    if engine is None:
        print("Błąd: nie znaleziono programu engine — zbuduj silnik albo podaj --engine", file=sys.stderr)
        return 1
    if args.cpu is not None:
        print(f"Przypięcie: {pin_self(args.cpu)}")
    cmd = [str(engine), "--batch", str(cfg_root / sid), "--out", str(res_root / sid)]
    print("Polecenie:", " ".join(f'"{c}"' if " " in c else c for c in cmd), flush=True)
    code = subprocess.run(cmd, cwd=ROOT).returncode
    table = compare.series_table(res_root, sid)
    print(f"\n{'zadanie':36s} {'status':6s} {'kroki':>6s} {'MCS':>5s} {'caSim [ms]':>11s} {'mcSim [ms]':>11s} {'ns/jedn.':>9s}")
    for r in table["rows"]:
        f = lambda v, d=1: "—" if v is None else (f"{v:.{d}f}" if isinstance(v, float) else str(v))  # noqa: E731
        print(f"{r['name']:36s} {r['status'][:6]:6s} {f(r['steps']):>6s} {f(r['mcs']):>5s} {f(r['caSim']):>11s} "
              f"{f(r['mcSim']):>11s} {f(r['nsPerUnit']):>9s}")
    csv_path = res_root / sid / "porownanie.csv"
    csv_path.write_text(compare.table_csv(table), encoding="utf-8", newline="")
    print(f"\nTabela porównania: {csv_path} (oraz batch_summary.csv z engine --batch)")
    return code


if __name__ == "__main__":
    sys.exit(main())
