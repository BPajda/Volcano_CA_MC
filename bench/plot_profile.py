#!/usr/bin/env python3
"""Wykresy profilu aplikacji (etap 3) z wyników bench/run_profile.py -> docs/img/profile_*.png.

Użycie (z katalogu volcano-ca-mc):
    python bench/plot_profile.py                         # najnowszy pełny zestaw bench/results/profile_*.csv
    python bench/plot_profile.py --csv bench/results/profile_2026-10-09.csv --out docs/img

Wykresy:
    profile_time_vs_cells.png  czas symulacji vs liczba komórek (log–log): CA classic i MC full, VN/Moore, 2D/3D
    profile_ns_per_cell.png    koszt jednostkowy: ns na komórkę i krok (CA) / na próbę (MC)
    profile_time_vs_seeds.png  CA classic: czas i liczba kroków vs liczba zarodków (1/10/100)
    profile_phases.png         udział faz programu w czasie całkowitym (odczyt, alokacja, teren, CA, MC, zapis)
    profile_memory.png         pamięć zmierzona vs model teoretyczny vs liczba komórek
    profile_output.png         rozmiar plików txt vs bin i czas zapisu
    profile_compilers.png      MSVC /O2, /O1, Debug i GCC -O3/-O2/-O0/Debug (czas względem MSVC /O2)
    profile_gcc_vs_msvc.png    przyspieszenie GCC -O3 względem MSVC /O2 w całej macierzy
    profile_detail.png         fazy wewnątrz kroku CA i składniki statystyk MC (--timing-detail)

Słupki błędów = min–max z powtórzeń (liczba powtórzeń w CSV, kolumna repeats).
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

ROOT = Path(__file__).resolve().parent.parent

# Paleta kategorii (stała kolejność, sprawdzona pod kątem daltonizmu) i kolory tekstu/siatki.
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e3e2de"
NB_PL = {"von_neumann": "von Neumann", "moore": "Moore"}
MB = 1024.0 ** 2


def style() -> None:
    plt.rcParams.update({
        "figure.dpi": 110, "savefig.dpi": 150, "font.size": 9.5, "axes.titlesize": 10.5,
        "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
        "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
        "lines.linewidth": 2.0, "lines.markersize": 6.5, "figure.facecolor": "white",
    })


def latest_csv() -> Path:
    files = sorted(p for p in (ROOT / "bench" / "results").glob("profile_*.csv")
                   if not p.stem.endswith(("_raw", "_benchmark", "_quick")))
    if not files:
        sys.exit("Brak bench/results/profile_*.csv — najpierw uruchom bench/run_profile.py")
    return files[-1]


def val(df: pd.DataFrame, variant: str, build: str, col: str, stat: str = "med") -> float:
    """Wartość statystyki miary dla wariantu i buildu (NaN, gdy brak)."""
    r = df[(df.variant == variant) & (df.build == build)]
    key = f"{col}_{stat}" if stat else col
    if r.empty or key not in r.columns:
        return float("nan")
    return float(r.iloc[0][key])


def err(df: pd.DataFrame, variant: str, build: str, col: str) -> tuple[float, float, float]:
    """Mediana i odległości do min/max (słupki błędów)."""
    m = val(df, variant, build, col)
    return m, m - val(df, variant, build, col, "min"), val(df, variant, build, col, "max") - m


def dims(nx: int, ny: int, nz: int) -> str:
    return f"{nx}×{ny}" if nz == 1 else f"{nx}×{ny}×{nz}"


def save(fig: plt.Figure, out: Path, name: str) -> None:
    fig.savefig(out / name, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  {out / name}")


SIZES = [(100, 100, 1), (1000, 1000, 1), (10, 10, 10), (100, 100, 100)]


def classic_id(nx, ny, nz, seeds, nb, bc="per"):
    d = f"{nx}x{ny}" if nz == 1 else f"{nx}x{ny}x{nz}"
    return f"classic_{d}_s{seeds}_{'vn' if nb == 'von_neumann' else 'moore'}_{bc}"


def mc_id(nx, ny, nz, nb, mcs=100):
    d = f"{nx}x{ny}" if nz == 1 else f"{nx}x{ny}x{nz}"
    return f"mcfull_{d}_{'vn' if nb == 'von_neumann' else 'moore'}_mcs{mcs}"


# ---------------------------------------------------------------------------
def plot_time_vs_cells(df, build, out):
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    series = [("CA classic, von Neumann", "ca", "von_neumann", C[0]), ("CA classic, Moore", "ca", "moore", C[1]),
              ("MC full, von Neumann", "mc", "von_neumann", C[2]), ("MC full, Moore", "mc", "moore", C[6])]
    for label, kind, nb, color in series:
        for dim, marker, ls in (("2D", "o", "-"), ("3D", "s", "--")):
            xs, ys, lo, hi = [], [], [], []
            for (nx, ny, nz) in SIZES:
                if (nz == 1) != (dim == "2D"):
                    continue
                vid = classic_id(nx, ny, nz, 10, nb) if kind == "ca" else mc_id(nx, ny, nz, nb)
                col = "caSim_ms" if kind == "ca" else "mcSim_ms"
                m, a, b = err(df, vid, build, col)
                if np.isnan(m):
                    continue
                xs.append(nx * ny * nz)
                ys.append(m / 1000)
                lo.append(a / 1000)
                hi.append(b / 1000)
            if xs:
                ax.errorbar(xs, ys, yerr=[lo, hi], color=color, marker=marker, ls=ls, capsize=2,
                            label=f"{label} ({dim})", markeredgecolor="white", markeredgewidth=0.8)
    # Prosta odniesienia: czas ~ liczba komórek (nachylenie 1).
    x = np.array([1e3, 1e6])
    ax.plot(x, 2e-5 * x / 1e3, color=INK2, lw=1, ls=":", label="nachylenie 1 (t ~ N)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("liczba komórek N")
    ax.set_ylabel("czas symulacji [s] (caSim / mcSim)")
    ax.set_title("Czas symulacji vs rozmiar przestrzeni\nCA classic: 10 zarodków, periodyczne; MC full: Q = 50, 100 MCS")
    ax.legend(fontsize=8, ncol=2, loc="upper left")
    save(fig, out, "profile_time_vs_cells.png")


def plot_ns_per_cell(df, build, out):
    """Koszt jednostkowy: CA — ns na komórkę i krok, MC — ns na próbę."""
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.9))
    labels = [dims(*s) for s in SIZES]
    xx = np.arange(len(SIZES))
    w = 0.38
    for ax, kind in zip(axes, ("ca", "mc")):
        for k, nb in enumerate(("von_neumann", "moore")):
            vals = []
            for (nx, ny, nz) in SIZES:
                n = nx * ny * nz
                if kind == "ca":
                    vid = classic_id(nx, ny, nz, 10, nb)
                    t, steps = val(df, vid, build, "caSim_ms"), val(df, vid, build, "steps", "")
                    vals.append(t * 1e6 / (n * steps) if steps else np.nan)
                else:
                    vid = mc_id(nx, ny, nz, nb)
                    t, mcs = val(df, vid, build, "mcSim_ms"), val(df, vid, build, "mcs", "")
                    vals.append(t * 1e6 / (n * mcs) if mcs else np.nan)
            bars = ax.bar(xx + (k - 0.5) * w, vals, w * 0.94, color=C[k], label=NB_PL[nb])
            for b, v in zip(bars, vals):
                if not np.isnan(v):
                    ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.0f}", ha="center", va="bottom",
                            fontsize=8, color=INK2)
        ax.set_xticks(xx, labels)
        ax.set_xlabel("przestrzeń")
        ax.set_ylabel("ns na komórkę i krok" if kind == "ca" else "ns na próbę MC")
        ax.set_title("CA classic (10 zarodków)" if kind == "ca" else "MC full (Q = 50, 100 MCS)")
        ax.legend(fontsize=8)
    fig.suptitle(f"Koszt jednostkowy ({build}) — mediana", y=1.02)
    fig.tight_layout()
    save(fig, out, "profile_ns_per_cell.png")


def plot_time_vs_seeds(df, build, out):
    fig, axes = plt.subplots(2, 2, figsize=(9.6, 6.4), sharex=True)
    for col, nb in enumerate(("von_neumann", "moore")):
        for k, (nx, ny, nz) in enumerate(SIZES):
            seeds, ts, lo, hi, steps = [], [], [], [], []
            for s in (1, 10, 100):
                vid = classic_id(nx, ny, nz, s, nb)
                m, a, b = err(df, vid, build, "caSim_ms")
                if np.isnan(m):
                    continue
                seeds.append(s)
                ts.append(m)
                lo.append(a)
                hi.append(b)
                steps.append(val(df, vid, build, "steps", ""))
            axes[0, col].errorbar(seeds, ts, yerr=[lo, hi], color=C[k], marker="o", capsize=2,
                                  label=dims(nx, ny, nz), markeredgecolor="white")
            axes[1, col].plot(seeds, steps, color=C[k], marker="o", label=dims(nx, ny, nz), markeredgecolor="white")
        axes[0, col].set_title(f"{NB_PL[nb]}, brzeg periodyczny")
        axes[0, col].set_yscale("log")
        axes[1, col].set_yscale("log")
        axes[1, col].set_xscale("log")
        axes[1, col].set_xticks([1, 10, 100], ["1", "10", "100"])
        axes[1, col].set_xlabel("liczba zarodków")
    axes[0, 0].set_ylabel("czas CA (caSim) [ms]")
    axes[1, 0].set_ylabel("liczba kroków CA")
    axes[0, 0].legend(fontsize=8, title="przestrzeń", title_fontsize=8)
    fig.suptitle(f"CA classic: czas i liczba kroków vs liczba zarodków ({build})", y=1.0)
    fig.tight_layout()
    save(fig, out, "profile_time_vs_seeds.png")


PHASES = [("odczyt configu", ["readConfig_ms"]), ("alokacja", ["allocate_ms"]),
          ("teren + kratery", ["terrain_ms", "vents_ms"]), ("symulacja CA", ["caSim_ms"]),
          ("MC: przygotowanie + kroki", ["mcInit_ms", "mcSim_ms"]), ("MC: statystyki", ["mcStats_ms"]),
          ("zapis wyników", ["save_ms", "mcSave_ms"])]


def phase_variants(df):
    cand = [("classic 100×100", classic_id(100, 100, 1, 10, "von_neumann")),
            ("classic 1000×1000", classic_id(1000, 1000, 1, 10, "von_neumann")),
            ("classic 10×10×10", classic_id(10, 10, 10, 10, "von_neumann")),
            ("classic 100×100×100", classic_id(100, 100, 100, 10, "von_neumann")),
            ("classic 300×300×300 (100 z.)", classic_id(300, 300, 300, 100, "von_neumann")),
            ("MC full 1000×1000 VN", mc_id(1000, 1000, 1, "von_neumann")),
            ("MC full 100×100×100 Moore", mc_id(100, 100, 100, "moore")),
            ("lava test_2d", "test_2d"), ("lava test_3d", "test_3d"), ("lava etna_3d", "etna_3d"),
            ("CA + MC lava_mc_3d", "lava_mc_3d")]
    return [(lbl, v) for lbl, v in cand if v in set(df.variant)]


def plot_phases(df, build, out):
    rows = phase_variants(df)
    fig, ax = plt.subplots(figsize=(9.6, 0.42 * len(rows) + 1.6))
    y = np.arange(len(rows))[::-1]
    left = np.zeros(len(rows))
    totals = np.array([val(df, v, build, "total_ms") for _, v in rows])
    for k, (name, cols) in enumerate(PHASES):
        part = np.array([sum(np.nan_to_num(val(df, v, build, c)) for c in cols) for _, v in rows])
        share = 100 * part / totals
        ax.barh(y, share, left=left, color=C[k], label=name, edgecolor="white", linewidth=1.2, height=0.7)
        left += share
    # Reszta czasu total poza sekcjami: start programu, folder wyników, config_used.json, podsumowanie.
    ax.barh(y, np.clip(100 - left, 0, None), left=left, color="#c9c8c2", label="pozostałe (start, folder, config_used)",
            edgecolor="white", linewidth=1.2, height=0.7)
    for yi, t in zip(y, totals):
        ax.text(101, yi, f"{t / 1000:.2f} s" if t >= 1000 else f"{t:.1f} ms", va="center", fontsize=8, color=INK2)
    ax.set_yticks(y, [lbl for lbl, _ in rows])
    ax.set_xlim(0, 112)
    ax.set_xticks([0, 20, 40, 60, 80, 100])
    ax.set_xlabel("udział w czasie całkowitym (total) [%]   (z prawej: total)")
    ax.set_title(f"Udział faz programu w czasie całkowitym ({build}, mediany)")
    ax.legend(fontsize=8, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.14))
    ax.grid(axis="y", visible=False)
    save(fig, out, "profile_phases.png")


def plot_memory(df, build, out):
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.4), gridspec_kw={"width_ratios": [1, 1.15]})
    # Lewy panel: szczyt procesu vs N; osobne serie 2D i 3D (te same N = 10^6 mają inny narzut ramki).
    series = [("CA classic 2D", [(100, 100, 1), (1000, 1000, 1)], "ca", C[0], "o", "-"),
              ("CA classic 3D", [(10, 10, 10), (100, 100, 100), (300, 300, 300)], "ca", C[0], "s", "--"),
              ("MC full 2D", [(100, 100, 1), (1000, 1000, 1)], "mc", C[2], "o", "-"),
              ("MC full 3D", [(10, 10, 10), (100, 100, 100)], "mc", C[2], "s", "--")]
    for label, sizes, kind, color, marker, ls in series:
        xs, meas, model, start = [], [], [], []
        for s in sizes:
            if kind == "ca":
                vid = classic_id(*s, 100 if s == (300, 300, 300) else 10, "von_neumann")
            else:
                vid = mc_id(*s, "von_neumann")
            p = val(df, vid, build, "mem_peakRssBytes")
            if np.isnan(p):
                continue
            xs.append(s[0] * s[1] * s[2])
            meas.append(p)
            start.append(val(df, vid, build, "mem_startRssBytes"))
            model.append(val(df, vid, build, "mem_modelPeakBytes"))
        xs, meas, model, start = (np.array(a) for a in (xs, meas, model, start))
        axes[0].plot(xs, meas / MB, marker=marker, ls=ls, color=color, label=f"{label}: zmierzony szczyt",
                     markeredgecolor="white")
        axes[0].plot(xs, (model + start) / MB, ls=":", color=color, lw=1.4)
    axes[0].plot([], [], ls=":", color=INK2, lw=1.4, label="model + pamięć na starcie (kropki)")
    axes[0].set_xscale("log")
    axes[0].set_yscale("log")
    axes[0].set_xlabel("liczba komórek N")
    axes[0].set_ylabel("szczytowa pamięć procesu [MiB]")
    axes[0].set_title("Szczyt zbioru roboczego procesu")
    axes[0].legend(fontsize=7.5)
    # Prawy panel: bajty na komórkę dla dużych przypadków — zmierzone (szczyt − start) vs model.
    cases = [("CA 2D\n1000²", classic_id(1000, 1000, 1, 10, "von_neumann")),
             ("CA 3D\n100³", classic_id(100, 100, 100, 10, "von_neumann")),
             ("CA 3D\n300³", classic_id(300, 300, 300, 100, "von_neumann")),
             ("MC 2D\n1000²", mc_id(1000, 1000, 1, "von_neumann")),
             ("MC 3D\n100³", mc_id(100, 100, 100, "von_neumann")),
             ("lava\netna_3d", "etna_3d"), ("CA+MC\nlava_mc_3d", "lava_mc_3d")]
    cases = [(l, v) for l, v in cases if v in set(df.variant)]
    xx = np.arange(len(cases))
    meas = [(val(df, v, build, "mem_peakRssBytes") - val(df, v, build, "mem_startRssBytes"))
            / val(df, v, build, "cells", "") for _, v in cases]
    model = [val(df, v, build, "mem_modelPeakBytes") / val(df, v, build, "cells", "") for _, v in cases]
    w = 0.38
    b1 = axes[1].bar(xx - w / 2, meas, w * 0.94, color=C[0], label="zmierzone: (szczyt − start) / N")
    b2 = axes[1].bar(xx + w / 2, model, w * 0.94, color=C[3], label="model: tablice × sizeof / N")
    for bars in (b1, b2):
        for b in bars:
            axes[1].text(b.get_x() + b.get_width() / 2, b.get_height(), f"{b.get_height():.0f}", ha="center",
                         va="bottom", fontsize=7.5, color=INK2)
    axes[1].set_xticks(xx, [l for l, _ in cases], fontsize=8)
    axes[1].set_ylabel("bajty na komórkę")
    axes[1].set_title("Pamięć danych na komórkę (duże przypadki)")
    axes[1].legend(fontsize=7.5, loc="upper right")
    axes[1].grid(axis="x", visible=False)
    fig.suptitle(f"Zapotrzebowanie na pamięć: pomiar vs model ({build})", y=1.02)
    fig.tight_layout()
    save(fig, out, "profile_memory.png")


def plot_output(df, build, out):
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.1))
    sizes = SIZES + [(300, 300, 300)]
    files = [("ca_result.txt", "ca_result_txt", "classic", C[0], "o", "-"),
             ("ca_result.bin", "ca_result_bin", "classic", C[0], "s", "--"),
             ("mc_result.txt", "mc_result_txt", "mc", C[2], "o", "-"),
             ("mc_result.bin", "mc_result_bin", "mc", C[2], "s", "--")]
    for label, key, kind, color, marker, ls in files:
        xs, b, t = [], [], []
        for s in sizes:
            if s == (300, 300, 300):
                if kind != "classic":
                    continue
                vid = classic_id(300, 300, 300, 100, "von_neumann")
            else:
                vid = classic_id(*s, 10, "von_neumann") if kind == "classic" else mc_id(*s, "von_neumann")
            v = val(df, vid, build, f"file_{key}_bytes")
            if np.isnan(v):
                continue
            xs.append(s[0] * s[1] * s[2])
            b.append(v)
            t.append(val(df, vid, build, f"file_{key}_ms"))
        o = np.argsort(xs)
        xs, b, t = (np.array(a)[o] for a in (xs, b, t))
        axes[0].plot(xs, b / MB, marker=marker, ls=ls, color=color, label=label, markeredgecolor="white")
        axes[1].plot(xs, t, marker=marker, ls=ls, color=color, label=label, markeredgecolor="white")
    for ax in axes:
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("liczba komórek N")
        ax.legend(fontsize=8)
    axes[0].set_ylabel("rozmiar pliku [MiB]")
    axes[0].set_title("Ile zajmują mikrostruktury")
    axes[1].set_ylabel("czas zapisu pliku [ms]")
    axes[1].set_title("Czas zapisu (pomiary < 5 ms zaszumione)")
    fig.suptitle(f"Wyjście: txt vs bin ({build})", y=1.02)
    fig.tight_layout()
    save(fig, out, "profile_output.png")


COMP_BUILDS = ["msvc-O2", "msvc-O1", "msvc-Debug", "gcc-O3", "gcc-O2", "gcc-O0", "gcc-Debug"]
COMP_LABELS = {"msvc-O2": "MSVC /O2 (Release)", "msvc-O1": "MSVC /O1", "msvc-Debug": "MSVC Debug",
               "gcc-O3": "GCC -O3 (Release)", "gcc-O2": "GCC -O2", "gcc-O0": "GCC -O0", "gcc-Debug": "GCC Debug"}


def plot_compilers(df, out):
    variants = [("CA classic 100³, VN, 10 z.", "cmp_" + classic_id(100, 100, 100, 10, "von_neumann"), "caSim_ms"),
                ("CA lava test_3d", "cmp_test_3d", "caSim_ms"),
                ("MC full 100³, Moore, 10 MCS", "cmp_" + mc_id(100, 100, 100, "moore", 10), "mcSim_ms"),
                ("MC full 200², VN, 100 MCS", "cmp_" + mc_id(200, 200, 1, "von_neumann", 100), "mcSim_ms")]
    builds = [b for b in COMP_BUILDS if b in set(df.build)]
    fig, ax = plt.subplots(figsize=(10.4, 4.4))
    xx = np.arange(len(variants))
    w = 0.8 / max(1, len(builds))
    for k, b in enumerate(builds):
        rel = []
        for _, vid, col in variants:
            rel.append(val(df, vid, b, col) / val(df, vid, "msvc-O2", col))
        bars = ax.bar(xx + (k - (len(builds) - 1) / 2) * w, rel, w * 0.92, color=C[k], label=COMP_LABELS.get(b, b))
        for bar, r in zip(bars, rel):
            if not np.isnan(r):
                ax.text(bar.get_x() + bar.get_width() / 2, r * 1.04, f"{r:.2f}" if r < 10 else f"{r:.0f}",
                        ha="center", va="bottom", fontsize=6.5, color=INK2, rotation=90)
    ax.axhline(1, color=INK2, lw=1)
    ax.set_yscale("log")
    ax.set_ylim(0.3, 20)
    ax.set_xticks(xx, [v[0] for v in variants])
    ax.set_ylabel("czas symulacji względem MSVC /O2 (×)")
    ax.set_title("Kompilatory i poziomy optymalizacji — czas samej symulacji (mediana), mniej = lepiej")
    ax.legend(fontsize=8, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.1))
    save(fig, out, "profile_compilers.png")


def plot_gcc_vs_msvc(df, out, main="msvc-O2", gcc="gcc-O3"):
    if gcc not in set(df.build):
        return
    rows = []
    for vid in df[df.build == main].variant:
        r = df[(df.variant == vid) & (df.build == main)].iloc[0]
        if r["group"] not in ("classic", "mc", "lava", "big"):
            continue
        col = "mcSim_ms" if r["mode"] == "mc_full" else "caSim_ms"
        a, b = val(df, vid, main, col), val(df, vid, gcc, col)
        if np.isnan(a) or np.isnan(b) or a < 5:
            continue  # < 5 ms — zaszumione
        rows.append((vid, r["mode"], a / b))
    if not rows:
        return
    rows.sort(key=lambda r: (r[1], r[2]))
    fig, ax = plt.subplots(figsize=(8.4, 0.2 * len(rows) + 1.4))
    colors = {"classic": C[0], "mc_full": C[2], "lava": C[1]}
    y = np.arange(len(rows))
    ax.barh(y, [r[2] for r in rows], color=[colors.get(r[1], C[4]) for r in rows], height=0.72)
    ax.axvline(1, color=INK2, lw=1)
    ax.set_yticks(y, [r[0] for r in rows], fontsize=6.5)
    ax.set_xlabel("czas MSVC /O2 / czas GCC -O3  (> 1: GCC szybszy)")
    ax.set_title("GCC -O3 (WSL) vs MSVC /O2 (Windows) — czas symulacji, warianty ≥ 5 ms")
    handles = [plt.Rectangle((0, 0), 1, 1, color=colors[k]) for k in ("classic", "mc_full", "lava")]
    ax.legend(handles, ["CA classic", "MC full", "lava (CA, CA + MC)"], fontsize=8, loc="lower right")
    ax.grid(axis="y", visible=False)
    save(fig, out, "profile_gcc_vs_msvc.png")


def plot_detail(df, build, out):
    ca = [("classic 100³ VN", classic_id(100, 100, 100, 10, "von_neumann") + "_detail"),
          ("classic 1000² VN", classic_id(1000, 1000, 1, 100, "von_neumann") + "_detail"),
          ("lava test_3d", "test_3d_detail"), ("lava etna_3d", "etna_3d_detail"),
          ("lava lava_mc_3d", "lava_mc_3d_detail")]
    ca = [(l, v) for l, v in ca if v in set(df.variant)]
    if not ca:
        return
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 3.8), gridspec_kw={"width_ratios": [1.3, 1]})
    parts = [("ramka (warunki brzegowe)", "detail_caFrame_ms"), ("D(n) — największy spadek", "detail_caDescent_ms"),
             ("reguły + zapis next", "detail_caRules_ms"), ("zamiana buforów, historia", "detail_caFinish_ms")]
    y = np.arange(len(ca))[::-1]
    left = np.zeros(len(ca))
    for k, (name, col) in enumerate(parts):
        v = np.array([np.nan_to_num(val(df, vid, build, col)) for _, vid in ca])
        tot = np.array([sum(np.nan_to_num(val(df, vid, build, c)) for _, c in parts) for _, vid in ca])
        share = 100 * v / tot
        axes[0].barh(y, share, left=left, color=C[k], label=name, edgecolor="white", linewidth=1.2, height=0.7)
        left += share
    axes[0].set_yticks(y, [l for l, _ in ca])
    axes[0].set_xlabel("udział w czasie kroku CA [%]")
    axes[0].set_title("Fazy kroku CA")
    axes[0].legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2)
    axes[0].grid(axis="y", visible=False)
    mc = [("MC 100³ Moore", mc_id(100, 100, 100, "moore", 20) + "_detail"),
          ("MC 1000² VN", mc_id(1000, 1000, 1, "von_neumann", 20) + "_detail"),
          ("lava_mc_3d", "lava_mc_3d_detail")]
    mc = [(l, v) for l, v in mc if v in set(df.variant)]
    parts = [("kroki MCS (mcSim)", "mcSim_ms"), ("statystyki: kopia mapy", "detail_mcStatsCrystals_ms"),
             ("statystyki: union-find", "detail_mcStatsGrains_ms"), ("statystyki: energia", "detail_mcStatsEnergy_ms")]
    y = np.arange(len(mc))[::-1]
    left = np.zeros(len(mc))
    for k, (name, col) in enumerate(parts):
        v = np.array([np.nan_to_num(val(df, vid, build, col)) for _, vid in mc])
        tot = np.array([sum(np.nan_to_num(val(df, vid, build, c)) for _, c in parts) for _, vid in mc])
        share = 100 * v / tot
        axes[1].barh(y, share, left=left, color=C[k + 4], label=name, edgecolor="white", linewidth=1.2, height=0.7)
        left += share
    axes[1].set_yticks(y, [l for l, _ in mc])
    axes[1].set_xlabel("udział w czasie MC [%]")
    axes[1].set_title("MC: kroki vs statystyki (co 10 MCS)")
    axes[1].legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2)
    axes[1].grid(axis="y", visible=False)
    fig.suptitle(f"Szczegółowe fazy (--timing-detail, {build})", y=1.02)
    fig.tight_layout()
    save(fig, out, "profile_detail.png")


def main() -> int:
    ap = argparse.ArgumentParser(description="Wykresy profilu aplikacji")
    ap.add_argument("--csv", help="podsumowanie z run_profile.py (domyślnie najnowszy pełny zestaw)")
    ap.add_argument("--build", default="msvc-O2", help="build głównych wykresów (domyślnie msvc-O2)")
    ap.add_argument("--out", default=str(ROOT / "docs" / "img"), help="folder na PNG")
    args = ap.parse_args()
    csv = Path(args.csv) if args.csv else latest_csv()
    df = pd.read_csv(csv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    style()
    print(f"Dane: {csv} ({len(df)} wierszy), build {args.build}")
    plot_time_vs_cells(df, args.build, out)
    plot_ns_per_cell(df, args.build, out)
    plot_time_vs_seeds(df, args.build, out)
    plot_phases(df, args.build, out)
    plot_memory(df, args.build, out)
    plot_output(df, args.build, out)
    plot_compilers(df, out)
    plot_gcc_vs_msvc(df, out, main=args.build)
    plot_detail(df, args.build, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
