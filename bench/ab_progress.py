"""Test A/B narzutu opcji --progress: stary program, nowy bez flagi, nowy z --progress.

Każdy przypadek uruchamiany przemiennie (A, B, C, potem C, B, A …), proces przypięty do procesora
logicznego 2 (rdzeń P, jak w run_profile.py), priorytet wysoki, output.format = none. Wynik: mediana
[min–max] czasu symulacji z times.json oraz mediana stosunku parami „z --progress / bez” (ten sam przebieg r).

    python bench/ab_progress.py --old <stary_engine.exe> [--new build/Release/engine.exe] [--reps 11]
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES = {
    "test_3d (CA lava)": ("configs/test_3d.json", "caSim"),
    "classic_ref (CA classic 100^3)": ("configs/classic_ref.json", "caSim"),
    "mc_full_3d (MC 50^3 Moore)": ("configs/mc_full_3d.json", "mcSim"),
    "lava_mc_3d (CA + MC)": ("configs/lava_mc_3d.json", "caSim"),
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--old", required=True, help="program sprzed zmiany (punkt odniesienia)")
    ap.add_argument("--new", default=str(ROOT / "build" / "Release" / ("engine.exe" if os.name == "nt" else "engine")))
    ap.add_argument("--reps", type=int, default=11)
    ap.add_argument("--cpu", type=int, default=2, help="procesor logiczny do przypięcia (rdzeń P)")
    args = ap.parse_args()
    try:
        import psutil
        psutil.Process().cpu_affinity([args.cpu])  # procesy potomne dziedziczą powinowactwo
    except (ImportError, AttributeError):
        print("Uwaga: brak psutil — pomiar bez przypięcia do rdzenia", file=sys.stderr)
    flags = getattr(subprocess, "HIGH_PRIORITY_CLASS", 0)
    variants = {"old": (args.old, []), "new": (args.new, []), "new+progress": (args.new, ["--progress"])}
    tmp = tempfile.mkdtemp(prefix="ab_progress_")
    res = {c: {v: [] for v in variants} for c in CASES}
    for r in range(args.reps):
        for case, (cfg, key) in CASES.items():
            order = list(variants.items())
            if r % 2:
                order.reverse()
            for v, (exe, extra) in order:
                out = os.path.join(tmp, f"{v}_{r}")
                p = subprocess.run([exe, "--config", str(ROOT / cfg), "--out", out, "--set", "output.format=none", *extra],
                                   capture_output=True, text=True, encoding="utf-8", creationflags=flags)
                if p.returncode != 0:
                    print(p.stderr, file=sys.stderr)
                    return 1
                with open(os.path.join(out, "times.json"), encoding="utf-8") as f:
                    res[case][v].append(json.load(f)[key])
    for case in CASES:
        base = statistics.median(res[case]["old"])
        row = [f"{v}: {statistics.median(x):8.1f} ms [{min(x):.1f}-{max(x):.1f}] x{statistics.median(x) / base:.3f}"
               for v, x in res[case].items()]
        print(f"{case:32s} | " + " | ".join(row))
    print("Stosunek parami (ten sam przebieg r): mediana new+progress / new [min-max]")
    for case in CASES:
        ratios = [p / n for p, n in zip(res[case]["new+progress"], res[case]["new"])]
        print(f"{case:32s} | x{statistics.median(ratios):.3f} [{min(ratios):.3f}-{max(ratios):.3f}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
