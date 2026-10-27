#!/usr/bin/env python3
"""Wykresy optymalizacji wersji sekwencyjnej -> docs/img/optymalizacja_*.png.

Użycie (z katalogu volcano-ca-mc):
    python bench/plot_optymalizacja.py
    python bench/plot_optymalizacja.py --przed bench/results/profile_2026-10-17_przed2.csv \\
                                       --po bench/results/profile_2026-10-17_po.csv --out docs/img

Wykresy:
    optymalizacja_przed_po.png     czas całego przebiegu (total z times.json) przed i po optymalizacji: skrócony
                                   profil _przed2 / _po (te same warunki: taktowanie bazowe, przypięcie do rdzenia P),
                                   MSVC i GCC
    optymalizacja_kroki.png        przyspieszenie każdego kroku względem poprzedniego przyjętego (testy A/B
                                   bench/results/ab/ab_k*.csv): total przed krokiem / total po kroku, każdy przypadek
    optymalizacja_front_full.png   automat frontalny vs pełny przebieg (ten sam program k4, ca.sweep = front / full): caSim

Zysk jako mnożnik > 1 („×215” = 215 razy szybciej), skala logarytmiczna: zyski sięgają ×300, a straty kilku procent
też muszą być widoczne. Linia ×1 = bez zmian.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from plot_profile import C, GRID, INK, INK2, save, style  # noqa: E402  (ta sama paleta i styl co profil)

ROOT = Path(__file__).resolve().parent.parent
AB = ROOT / "bench" / "results" / "ab"
MUTED = "#898781"  # stan „przed” / wersja odniesienia — neutralna szarość, nie kolor kategorii

# Przypadki skróconego profilu: id wariantu run_profile.py -> etykieta (nazwy jak w zakładce „Wydajność”).
PROFILE_CASES = [
    ("etna_real", "lawa: Etna (rzeczywisty teren, 1,8 mln komórek)"),
    ("test_3d", "lawa: teren testowy 3D"),
    ("classic_1000x1000_s100_vn_per", "rozrost ziaren 1000×1000, von Neumann"),
    ("classic_1000x1000_s100_moore_per", "rozrost ziaren 1000×1000, Moore"),
    ("classic_300x300x300_s100_vn_per", "rozrost ziaren 300×300×300, von Neumann"),
    ("mcfull_1000x1000_vn_mcs100", "Monte Carlo 1000×1000, von Neumann"),
    ("mcfull_100x100x100_moore_mcs100", "Monte Carlo 100×100×100, Moore"),
]
BUILDS = [("msvc-O2", "MSVC /O2"), ("gcc-O3", "GCC -O3")]

# Kroki optymalizacji: (etykieta, {kompilator: [(plik CSV, kolumna B, kolumna A), ...]}) — A/B = czas przed / po kroku.
STEPS = [
    ("k1\nMonte Carlo\nbez skoków", {"msvc": [("ab_k1_mc_msvc", "k1", "przed"), ("ab_k1_ca_msvc", "k1", "przed")],
                                     "gcc": [("ab_k1_mc_gcc", "k1", "przed"), ("ab_k1_ca_gcc", "k1", "przed")]}),
    ("k2\nramka\nw osiach", {"msvc": [("ab_k2_msvc", "k2", "k1")], "gcc": [("ab_k2_gcc", "k2", "k1")]}),
    ("k3\nprzesunięcia\nsąsiadów", {"msvc": [("ab_k3_msvc", "k3", "k2")], "gcc": [("ab_k3_gcc", "k3", "k2")]}),
    ("k4\nautomat\nfrontalny", {"msvc": [("ab_k4_msvc", "k4", "k3")], "gcc": [("ab_k4_gcc", "k4", "k3")]}),
    ("k5\ntańsze\nstatystyki", {"msvc": [("ab_k5_msvc", "k5", "k4"), ("ab_k5_msvc_ca", "k5", "k4")],
                                "gcc": [("ab_k5_gcc", "k5", "k4"), ("ab_k5_gcc_ca", "k5", "k4")]}),
    ("k7\nzapis\ntekstu", {"msvc": [("ab_k7_msvc", "k7", "k5")], "gcc": [("ab_k7a_gcc", "k7a", "k5")]}),
]
GROUPS = [("ca_lava", "lawa", C[0], "o"), ("ca_classic", "rozrost ziaren", C[1], "s"), ("mc", "Monte Carlo", C[2], "^")]


def times_fmt(v: float, _pos=None) -> str:
    """Oś mnożnika: ×1, ×3, ×10 (przecinek dziesiętny)."""
    return "×" + f"{v:g}".replace(".", ",")


def ms_fmt(v: float, _pos=None) -> str:
    return f"{v / 1000:g} s".replace(".", ",") if v >= 1000 else f"{v:g} ms".replace(".", ",")


def gain_text(before: float, after: float) -> str:
    """Zysk jako mnożnik > 1: „×215”, „×1,7”; strata: „×1,10 wolniej”."""
    r = before / after
    if r < 1:
        return f"×{1 / r:.2f} wolniej".replace(".", ",")
    s = f"{r:.0f}" if r >= 20 else f"{r:.1f}"
    return "×" + s.replace(".", ",")


def plot_przed_po(przed: pd.DataFrame, po: pd.DataFrame, out: Path) -> None:
    """Dwa punkty na przypadek (przed, po) połączone odcinkiem, oś czasu logarytmiczna; zysk przy punkcie."""
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.3), sharey=True)
    y = np.arange(len(PROFILE_CASES))[::-1]
    for ax, (build, title) in zip(axes, BUILDS):
        for yi, (vid, _) in zip(y, PROFILE_CASES):
            a = przed[(przed.variant == vid) & (przed.build == build)]
            b = po[(po.variant == vid) & (po.build == build)]
            if a.empty or b.empty:
                continue
            ta, tb = float(a.iloc[0]["total_ms_med"]), float(b.iloc[0]["total_ms_med"])
            ax.plot([tb, ta], [yi, yi], color=GRID, lw=2.0, zorder=1, solid_capstyle="round")
            ax.scatter([ta], [yi], s=46, color=MUTED, zorder=3, edgecolor="white", linewidth=1.2)
            ax.scatter([tb], [yi], s=46, color=C[0], zorder=3, edgecolor="white", linewidth=1.2)
            ax.text(tb / 1.35, yi, gain_text(ta, tb), va="center", ha="right", fontsize=8, color=INK2)
        ax.set_xscale("log")
        ax.set_xlim(12, 1.6e5)
        ax.xaxis.set_major_formatter(FuncFormatter(ms_fmt))
        ax.set_title(title, color=INK, loc="left")
        ax.set_xlabel("czas całego przebiegu, mediana z 3 [skala log.]")
        ax.grid(axis="y", visible=False)
    axes[0].set_yticks(y, [label for _, label in PROFILE_CASES])
    axes[0].scatter([], [], s=46, color=MUTED, label="przed optymalizacją")
    axes[0].scatter([], [], s=46, color=C[0], label="po optymalizacji (obok: ile razy szybciej)")
    fig.legend(loc="lower center", ncol=2, bbox_to_anchor=(0.55, -0.04))
    fig.suptitle("Czas przed i po optymalizacji sekwencyjnej (profil skrócony, ten sam komputer, taktowanie bazowe)",
                 x=0.02, ha="left", color=INK, fontsize=10.5)
    fig.tight_layout(rect=(0, 0.05, 1, 0.96))
    save(fig, out, "optymalizacja_przed_po.png")


def step_gains(spec: list[tuple[str, str, str]]) -> pd.DataFrame:
    """Przyspieszenie kroku = mediana total przed / po dla każdego przypadku z plików kroku (bez powtórzeń)."""
    rows = []
    for name, b, a in spec:
        path = AB / f"{name}.csv"
        if not path.exists():
            print(f"  (brak {path.name}, pomijam)", file=sys.stderr)
            continue
        df = pd.read_csv(path)
        df = df[df.metric == "total"]
        for _, r in df.iterrows():
            rows.append({"case": r["case"], "group": r["group"], "gain": r[f"{a}_med"] / r[f"{b}_med"]})
    out = pd.DataFrame(rows)
    return out.drop_duplicates("case") if not out.empty else out


def plot_kroki(out: Path) -> None:
    """Punkt = przypadek zestawu A/B (kolor i kształt = rodzina), oś Y = total przed krokiem / total po kroku."""
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.6), sharey=True)
    offsets = {"ca_lava": -0.18, "ca_classic": 0.0, "mc": 0.18}
    for ax, comp, title in zip(axes, ("msvc", "gcc"), ("MSVC /O2", "GCC -O3")):
        ax.axhline(1.0, color=INK2, lw=1.0, ls=(0, (3, 3)), zorder=1)
        for k, (label, files) in enumerate(STEPS):
            r = step_gains(files[comp])
            for g, _, color, marker in GROUPS:
                v = r[r.group == g]["gain"] if not r.empty else []
                xs = k + offsets[g] + np.linspace(-0.05, 0.05, len(v)) if len(v) > 1 else [k + offsets[g]] * len(v)
                ax.scatter(xs, v, s=40, color=color, marker=marker, edgecolor="white", linewidth=1.0, zorder=3)
        ax.set_yscale("log")
        ax.set_ylim(0.5, 500)
        ax.yaxis.set_major_locator(FixedLocator([1.0, 3.0, 10.0, 30.0, 100.0, 300.0]))
        ax.yaxis.set_minor_locator(NullLocator())
        ax.yaxis.set_major_formatter(FuncFormatter(times_fmt))
        ax.set_xticks(range(len(STEPS)), [s[0] for s in STEPS], fontsize=7.5)
        ax.set_xlim(-0.6, len(STEPS) - 0.4)
        ax.grid(axis="x", visible=False)
        ax.set_title(title, color=INK, loc="left")
    axes[0].set_ylabel("przyspieszenie kroku: czas przed / po\n(cały przebieg) [skala log.; > ×1 = szybciej]")
    for g, name, color, marker in GROUPS:
        axes[0].scatter([], [], s=40, color=color, marker=marker, label=name)
    fig.legend(loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.03))
    fig.suptitle("Przyspieszenie każdego kroku optymalizacji względem poprzedniego (testy A/B, mediany)",
                 x=0.02, y=0.995, ha="left", color=INK, fontsize=10.5)
    fig.text(0.02, 0.935, "k1–k4 mierzone przy taktowaniu dynamicznym, k5 i k7 przy bazowym (stosunki czasów są "
             "porównywalne)", ha="left", color=INK2, fontsize=8.5)
    fig.tight_layout(rect=(0, 0.05, 1, 0.93))
    save(fig, out, "optymalizacja_kroki.png")


CA_CASES = [
    ("lava_etna_real", "lawa: Etna"),
    ("lava_test_3d", "lawa: teren testowy 3D"),
    ("lava_mc_2d_ca", "lawa + krystalizacja 2D (automat)"),
    ("classic_1000x1000_s100_vn", "rozrost ziaren 1000×1000, von Neumann"),
    ("classic_1000x1000_s100_moore", "rozrost ziaren 1000×1000, Moore"),
    ("classic_100x100x100_s10_vn", "rozrost ziaren 100×100×100, von Neumann"),
    ("classic_100x100x100_s10_moore", "rozrost ziaren 100×100×100, Moore"),
    ("classic_300x300x300_s100_vn", "rozrost ziaren 300×300×300, von Neumann"),
]


def plot_front_full(out: Path) -> None:
    """caSim pełnego przebiegu i automatu frontalnego tego samego programu (k4), oś log."""
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.3), sharey=True)
    y = np.arange(len(CA_CASES))[::-1]
    for ax, comp, title in zip(axes, ("msvc", "gcc"), ("MSVC /O2", "GCC -O3")):
        df = pd.read_csv(AB / f"ab_k4_{comp}_front_full.csv")
        df = df[df.metric == "caSim"]
        for yi, (cid, _) in zip(y, CA_CASES):
            r = df[df["case"] == cid]
            if r.empty:
                continue
            tf, tr = float(r.iloc[0]["k4_full_med"]), float(r.iloc[0]["k4_med"])
            ax.plot([tr, tf], [yi, yi], color=GRID, lw=2.0, zorder=1, solid_capstyle="round")
            ax.scatter([tf], [yi], s=46, color=MUTED, zorder=3, edgecolor="white", linewidth=1.2)
            ax.scatter([tr], [yi], s=46, color=C[0], zorder=3, edgecolor="white", linewidth=1.2)
            ax.text(tr / 1.35, yi, gain_text(tf, tr), va="center", ha="right", fontsize=8, color=INK2)
        ax.set_xscale("log")
        ax.set_xlim(0.4, 4e4)
        ax.xaxis.set_major_formatter(FuncFormatter(ms_fmt))
        ax.set_title(title, color=INK, loc="left")
        ax.set_xlabel("czas fazy automatu, mediana [skala log.]")
        ax.grid(axis="y", visible=False)
    axes[0].set_yticks(y, [label for _, label in CA_CASES])
    axes[0].scatter([], [], s=46, color=MUTED, label="pełny przebieg (wersja referencyjna)")
    axes[0].scatter([], [], s=46, color=C[0], label="automat frontalny (obok: ile razy szybciej)")
    fig.legend(loc="lower center", ncol=2, bbox_to_anchor=(0.55, -0.04))
    fig.suptitle("Automat frontalny i pełny przebieg: ten sam program (krok k4), wyniki bitowo identyczne",
                 x=0.02, ha="left", color=INK, fontsize=10.5)
    fig.tight_layout(rect=(0, 0.05, 1, 0.96))
    save(fig, out, "optymalizacja_front_full.png")


def main() -> int:
    ap = argparse.ArgumentParser(description="Wykresy optymalizacji sekwencyjnej (przed/po, kroki, front vs full)")
    ap.add_argument("--przed", default=str(ROOT / "bench" / "results" / "profile_2026-10-17_przed2.csv"))
    ap.add_argument("--po", default=str(ROOT / "bench" / "results" / "profile_2026-10-17_po.csv"))
    ap.add_argument("--out", default=str(ROOT / "docs" / "img"), help="folder na PNG")
    args = ap.parse_args()
    style()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    plot_przed_po(pd.read_csv(args.przed), pd.read_csv(args.po), out)
    plot_kroki(out)
    plot_front_full(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
