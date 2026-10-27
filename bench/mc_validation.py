#!/usr/bin/env python3
"""Walidacja statystyczna szachownicy MC: mc.update = checkerboard vs random (wariant naiwny).

Szachownica to inny proces losowy niż wariant naiwny (inny porządek prób: kolor po kolorze, każda komórka raz na MCS,
zamiast N prób w losowych komórkach ze zwracaniem), więc wyniki nie są bitowo te same — porównujemy rozkłady. Dla każdego
przypadku i ≥ 10 ziaren generatora (rngSeed) oba warianty liczą ten sam układ, a skrypt porównuje:
  * liczbę ziaren i średnią wielkość ziarna po N MCS (średnia, odchylenie, przedział ufności 95%, różnica względna,
    statystyka t Welcha),
  * kinetykę: wykładnik wzrostu n z dopasowania średniej wielkości ziarna ~ MCS^n (MCS 20..N, każde ziarno osobno),
  * krzywe liczby ziaren i średniej wielkości vs MCS (średnia i min–max po ziarnach) -> docs/img/openmp_mc_walidacja.png.

Przypadki: configs/mc_full_2d.json (200², von Neumann, Q = 50) i configs/mc_full_3d.json (50³, Moore, Q = 50) z kT jak
w configach (0) i 100 MCS, oraz 2D z kT = 0,3 (czy zgodność trzyma się także przy akceptacji ruchów pod górę; poniżej
temperatury przejścia modelu Pottsa 2D dla Q = 50: kT_c = 1/ln(1 + √50) ≈ 0,48 — wyżej ziarna nie rosną).
Szachownica liczona w 8 wątkach (wynik nie zależy od liczby wątków), random — w jednym.

    python bench/mc_validation.py                      # pomiar + tabela + wykres
    python bench/mc_validation.py --seeds 20
    python bench/mc_validation.py --from-csv bench/results/omp/mc_walidacja.csv   # tylko tabela i wykres
Wyniki: bench/results/omp/mc_walidacja.csv (każdy wiersz mc_stats.csv), mc_walidacja.md (tabela).
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from plot_profile import C, INK2, save, style  # noqa: E402  (paleta i styl wykresów projektu)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "bench" / "results" / "omp"
MODES = [("random", "losowa kolejność (wariant naiwny)", C[0]), ("checkerboard", "szachownica", C[1])]
CASES = [
    ("2d_vn_kT0", "2D 200², von Neumann, kT = 0", "mc_full_2d", {"mc": {"mcs": 100, "statsEvery": 5}}),
    ("3d_moore_kT0", "3D 50³, Moore, kT = 0", "mc_full_3d", {"mc": {"mcs": 100, "statsEvery": 5}}),
    ("2d_vn_kT03", "2D 200², von Neumann, kT = 0,3", "mc_full_2d", {"mc": {"mcs": 100, "statsEvery": 5, "kT": 0.3}}),
]
# Nazwy przypadków na wykresie (tabela mc_walidacja.md zostaje z krótkimi nazwami z CASES).
PLOT_LABEL = {"2d_vn_kT0": "Monte Carlo 200×200, von Neumann, kT = 0",
              "3d_moore_kT0": "Monte Carlo 50×50×50, Moore, kT = 0",
              "2d_vn_kT03": "Monte Carlo 200×200, von Neumann, kT = 0,3"}


def run_all(exe: str, seeds: list[int]) -> pd.DataFrame:
    """Wszystkie przebiegi; zwraca wiersze mc_stats.csv z kolumnami case, mode, seed."""
    tmp = Path(tempfile.mkdtemp(prefix="volcano_mcval_"))
    frames = []
    try:
        for cid, _, cfg, patch in CASES:
            for seed in seeds:
                for mode, _, _ in MODES:
                    out = tmp / f"{cid}_{mode}_{seed}"
                    sets = ["--set", f"rngSeed={seed}", "--set", f"mc.update={mode}", "--set", "output.format=none"]
                    for sec, vals in patch.items():
                        for k, v in vals.items():
                            sets += ["--set", f"{sec}.{k}={json.dumps(v)}"]
                    threads = "8" if mode == "checkerboard" else "1"
                    r = subprocess.run([exe, "--config", f"configs/{cfg}.json", "--out", str(out), "--threads", threads,
                                        *sets], cwd=ROOT, capture_output=True)
                    if r.returncode != 0:
                        raise RuntimeError(r.stderr.decode("utf-8", "replace")[-400:])
                    df = pd.read_csv(out / "mc_stats.csv")
                    df["case"], df["mode"], df["seed"] = cid, mode, seed
                    frames.append(df)
                    shutil.rmtree(out, ignore_errors=True)
                print(f"{cid}: ziarno {seed} gotowe", flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return pd.concat(frames, ignore_index=True)


def growth_exponent(g: pd.DataFrame) -> float:
    """Wykładnik n z dopasowania meanGrainSize ~ MCS^n (MCS >= 20) w skali log-log."""
    g = g[g["mcs"] >= 20]
    x, y = np.log(g["mcs"].to_numpy(float)), np.log(g["meanGrainSize"].to_numpy(float))
    return float(np.polyfit(x, y, 1)[0])


def mean_ci(v: list[float]) -> tuple[float, float, float]:
    """Średnia, odchylenie standardowe i połowa przedziału ufności 95% (kwantyl rozkładu t ≈ 2,2 dla n ≈ 12)."""
    m = statistics.mean(v)
    s = statistics.stdev(v) if len(v) > 1 else 0.0
    t = {10: 2.262, 11: 2.228, 12: 2.201, 15: 2.145, 20: 2.093}.get(len(v), 2.0)
    return m, s, t * s / math.sqrt(len(v))


def num(v: float) -> str:
    """Liczba do tabeli: od 100 — całkowita ze spacją tysięcy, od 10 — 1 cyfra po kropce, mniejsze — 3 cyfry."""
    if abs(v) >= 100:
        return f"{v:,.0f}".replace(",", " ")
    return f"{v:.1f}" if abs(v) >= 10 else f"{v:.3f}"


def plain(v: float, _pos=None) -> str:
    """Opis osi logarytmicznej zwykłą liczbą (spacja tysięcy, przecinek dziesiętny)."""
    return f"{v:,.0f}".replace(",", " ") if v >= 100 else f"{v:g}".replace(".", ",")


def welch_t(a: list[float], b: list[float]) -> float:
    va, vb = statistics.variance(a) / len(a), statistics.variance(b) / len(b)
    return (statistics.mean(b) - statistics.mean(a)) / math.sqrt(va + vb) if va + vb > 0 else 0.0


def table(df: pd.DataFrame) -> list[str]:
    seeds = sorted(df["seed"].unique())
    md = [f"Ziarna generatora: {len(seeds)} ({seeds[0]}–{seeds[-1]}); wartości po ostatnim MCS: średnia ± odchylenie "
          "(przedział ufności 95% średniej); różnica = szachownica / random − 1; |t| Welcha < 2 — różnica nieistotna "
          "na poziomie ~5%. Wykładnik n: średnia wielkość ziarna ~ MCS^n (MCS 20–100).", "",
          "| Przypadek | wielkość | random | szachownica | różnica | t Welcha |", "|---|---|---|---|---|---|"]
    for cid, label, _, _ in CASES:
        d = df[df["case"] == cid]
        if d.empty:
            continue
        last = d["mcs"].max()
        for col, name in (("grains", "liczba ziaren"), ("meanGrainSize", "średnia wielkość ziarna"),
                          ("energy", "energia")):
            vals = {m: d[(d["mode"] == m) & (d["mcs"] == last)].sort_values("seed")[col].tolist() for m, _, _ in MODES}
            (ma, sa, ca), (mb, sb, cb) = mean_ci(vals["random"]), mean_ci(vals["checkerboard"])
            md.append(f"| {label} (MCS {last}) | {name} | {num(ma)} ± {num(sa)} (±{num(ca)}) | "
                      f"{num(mb)} ± {num(sb)} (±{num(cb)}) | {mb / ma - 1:+.1%} | "
                      f"{welch_t(vals['random'], vals['checkerboard']):+.2f} |")
        ex = {m: [growth_exponent(g) for _, g in d[d["mode"] == m].groupby("seed")] for m, _, _ in MODES}
        (ma, sa, _), (mb, sb, _) = mean_ci(ex["random"]), mean_ci(ex["checkerboard"])
        md.append(f"| {label} | wykładnik wzrostu n | {ma:.3f} ± {sa:.3f} | {mb:.3f} ± {sb:.3f} | {mb / ma - 1:+.1%} | "
                  f"{welch_t(ex['random'], ex['checkerboard']):+.2f} |")
        acc = {m: d[(d["mode"] == m) & (d["mcs"] > 0)]["acceptRate"].mean() for m, _, _ in MODES}
        md.append(f"| {label} | średni współczynnik akceptacji | {acc['random']:.3f} | {acc['checkerboard']:.3f} | "
                  f"{acc['checkerboard'] / acc['random'] - 1:+.1%} | — |")
    return md


def plot(df: pd.DataFrame, out: Path) -> None:
    """Krzywe liczby ziaren i średniej wielkości ziarna vs MCS: średnia po ziarnach generatora (linia) i min–max (pasmo)."""
    style()
    cases = [c for c in CASES if not df[df["case"] == c[0]].empty]
    fig, axes = plt.subplots(2, len(cases), figsize=(4.3 * len(cases), 6.6), squeeze=False)
    for j, (cid, label, _, _) in enumerate(cases):
        d = df[(df["case"] == cid) & (df["mcs"] > 0)]
        for i, (col, ylab) in enumerate((("grains", "liczba ziaren"), ("meanGrainSize", "średnia wielkość ziarna [kom.]"))):
            ax = axes[i][j]
            for mode, mlabel, color in MODES:
                g = d[d["mode"] == mode].groupby("mcs")[col]
                x = g.mean().index.to_numpy()
                ax.fill_between(x, g.min().to_numpy(), g.max().to_numpy(), color=color, alpha=0.18, linewidth=0)
                ax.plot(x, g.mean().to_numpy(), color=color, label=mlabel)
            ax.set_xscale("log")
            ax.set_yscale("log")
            for axis in (ax.xaxis, ax.yaxis):
                axis.set_major_locator(LogLocator(base=10, subs=(1.0, 2.0, 5.0)))
                axis.set_major_formatter(FuncFormatter(plain))
                axis.set_minor_formatter(NullFormatter())
            ax.set_xlabel("MCS")
            ax.set_ylabel(ylab)
            if i == 0:
                ax.set_title(PLOT_LABEL.get(cid, label), color=INK2)
    axes[0][0].legend(loc="lower left")
    seeds = df["seed"].nunique()
    fig.suptitle(f"Szachownica i wariant naiwny Monte Carlo: średnia i min–max z {seeds} ziaren generatora", y=1.0)
    fig.tight_layout()
    save(fig, out, "openmp_mc_walidacja.png")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--bin", default="build/Release/engine.exe", help="program silnika")
    ap.add_argument("--seeds", type=int, default=12, help="liczba ziaren generatora (domyślnie 12, min. 10)")
    ap.add_argument("--from-csv", help="bez pomiaru: tabela i wykres z zapisanego CSV")
    ap.add_argument("--img", default=str(ROOT / "docs" / "img"), help="folder wykresu")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # zawsze: na Windows NUL udaje terminal (isatty) i ma kodowanie cp1250
    if args.from_csv:
        df = pd.read_csv(args.from_csv)
    else:
        exe = str(ROOT / args.bin) if not Path(args.bin).is_absolute() else args.bin
        df = run_all(exe, list(range(1, max(10, args.seeds) + 1)))
        OUT.mkdir(parents=True, exist_ok=True)
        df.to_csv(OUT / "mc_walidacja.csv", index=False, lineterminator="\n")
    md = ["# Walidacja statystyczna szachownicy MC (`bench/mc_validation.py`)", ""] + table(df)
    with open(OUT / "mc_walidacja.md", "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(md) + "\n")
    print("\n".join(md))
    plot(df, Path(args.img))
    return 0


if __name__ == "__main__":
    sys.exit(main())
