#!/usr/bin/env python3
"""Wykresy do raportów (docs/raport-1.md, docs/raport-2.md) — jasna paleta do druku, rysunki o szerokości strony
(6,7 cala ≈ 17 cm, czcionka 7,5 pt), kolory jak w GUI (etap 7): CA = lawa #e8682a, MC = chłodny fiolet #7d68dd (para
sprawdzona walidatorem palety, docs/wyglad-interfejsu.md); w raporcie 2 rozrost ziaren #2a78d6, a OpenMP / MPI /
hybryda jak w bench/plot_testy.py (paleta bench/plot_profile.py, dobrana pod daltonizm).

    python tools/raport_wykresy.py            # oba raporty
    python tools/raport_wykresy.py 1          # -> docs/img/raport/ca_vs_mc.png, docs/img/raport/profil.png
    python tools/raport_wykresy.py 2          # -> docs/img/raport-2/*.png

Dane (bez nowych pomiarów — tylko odczyt plików z repozytorium):
  raport 1:
  ca_vs_mc.png  docs/data/ca_vs_mc.csv — seria „CA vs MC — rozmiar siatki” policzona przez GUI 10.10.2026
                (1 worker, przypięcie do CPU 2; docs/kolejka-serie-dane.md, punkt 4.2): caSim / mcSim vs liczba komórek.
  profil.png    bench/results/profile_2026-10-09.csv — pomiar z 9.10.2026 (MSVC /O2, mediana z 3 powtórzeń):
                (a) koszt jednostkowy CA classic (10 zarodków) i MC full (Q = 50, 100 MCS) vs liczba komórek,
                (b) fazy kroku CA z --timing-detail (docs/profilowanie.md, punkty 3.2, 3.3, 3.6).
  raport 2 (docs/img/raport-2/; wszystkie liczby z bench/results/, MSVC, taktowanie bazowe, rdzenie P):
  podzial.svg        schemat (bez danych): warstwy między wątki, okno procesu MPI w lawie, kolory szachownicy MC.
  optymalizacja.png  (a) cały przebieg przed / po optymalizacji sekwencyjnej (profile_2026-10-17_przed2 / _po),
                     (b) automat frontalny vs pełny przebieg w tym samym programie (ab/ab_k4_msvc_front_full.csv).
  openmp.png         S(p) i E(p) fazy obliczeń, 1–8 wątków (omp/skalowanie_msvc.csv).
  mpi.png            (a) S fazy przy 7–8 rdzeniach: OpenMP, MPI 7 i 8 procesów, hybryda (testy/zestawienie.csv),
                     (b) udział komunikacji w fazie vs liczba procesów (mpi/skalowanie_mpi_msvc.csv).
  testy.png          (a) skalowanie słabe E_w(8) obok silnego E (testy/slabe_*_msvc.csv, testy/zestawienie.csv),
                     (b) przepustowość RAM vs wątki i zapotrzebowanie przy 8 wątkach (testy/przepustowosc_msvc.csv,
                         slabe_omp_msvc.csv, cachegrind.csv — ten sam rachunek co bench/plot_testy.py).
  pamiec.png         (a) chybienia D1 na jednostkę pracy, pary porównań (testy/cachegrind.csv),
                     (b) czas na jednostkę pracy vs rozmiar siatki z progami L2 / L3 (testy/krzywa_msvc.csv).
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from matplotlib.ticker import FixedLocator, FuncFormatter, LogLocator, NullFormatter, NullLocator  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "img" / "raport"
OUT2 = ROOT / "docs" / "img" / "raport-2"
RES = ROOT / "bench" / "results"
CA, MC = "#e8682a", "#7d68dd"
CL = "#2a78d6"  # rozrost ziaren (classic) w raporcie 2 — rodziny przypadków: lawa CA, rozrost CL, Monte Carlo MC
# Warianty równoległe (raport 2): inne odcienie niż rodziny przypadków, bo na jednym rysunku występują oba podziały.
OMP_V, MPI_V, MPI8_V, HYB_V, MUTED = "#1baf7a", "#eda100", "#f6d58c", "#e87ba4", "#898781"
# Fazy kroku CA: paleta referencyjna GUI (--series-*); kontrast < 3:1 dla dwóch kolorów — stąd etykiety wartości.
PHASES = [("ramka (brzegi)", "#2a78d6"), ("D(n)", "#eda100"), ("reguły + zapis next", "#1baf7a")]
INK, INK2, GRID = "#231b14", "#5e554b", "#e6e1da"


def style() -> None:
    plt.rcParams.update({
        "font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 7.5, "axes.titlesize": 8, "axes.titleweight": "bold",
        "axes.titlelocation": "left", "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
        "ytick.color": INK2, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.5, "axes.axisbelow": True,
        "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False, "lines.linewidth": 1.6,
        "lines.markersize": 4.5, "figure.facecolor": "white", "savefig.dpi": 300, "axes.linewidth": 0.6,
        "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    })


def pl_num(v: float, _pos=None) -> str:
    """Podpis osi log: 1, 2, 5 × 10^k po polsku (spacja tysięcy, przecinek dziesiętny)."""
    if v >= 1:
        return f"{v:,.0f}".replace(",", " ")
    return f"{v:g}".replace(".", ",")


def log_axis(ax, which: str) -> None:
    """Oś log: X — tylko potęgi 10 (10³ … 10⁶), Y — 1, 2, 5 × 10^k."""
    axis = ax.xaxis if which == "x" else ax.yaxis
    if which == "x":
        axis.set_major_locator(LogLocator(base=10, subs=(1.0,)))
        axis.set_major_formatter(FuncFormatter(lambda v, _p: f"10$^{{{round(math.log10(v))}}}$"))
    else:
        axis.set_major_locator(LogLocator(base=10, subs=(1.0, 2.0, 5.0)))
        axis.set_major_formatter(FuncFormatter(pl_num))
    axis.set_minor_formatter(NullFormatter())


def ca_vs_mc() -> Path:
    d = pd.read_csv(ROOT / "docs" / "data" / "ca_vs_mc.csv")
    fig, axes = plt.subplots(1, 2, figsize=(6.7, 2.25), constrained_layout=True)
    for ax, dim in zip(axes, ("2D", "3D")):
        s = d[d["dim"] == dim].sort_values("cells")
        ca = s[s["algorithm"] == "CA"].set_index("cells")["caSim"]
        mc = s[s["algorithm"] == "MC"].set_index("cells")["mcSim"]
        ax.plot(ca.index, ca.values, "-o", color=CA, markeredgecolor="white", markeredgewidth=0.8, label="CA (caSim)")
        ax.plot(mc.index, mc.values, "-o", color=MC, markeredgecolor="white", markeredgewidth=0.8, label="MC (mcSim, 100 MCS)")
        ax.set_xscale("log")
        ax.set_yscale("log")
        log_axis(ax, "x")
        log_axis(ax, "y")
        for n in ca.index:  # stosunek MC / CA przy każdym rozmiarze
            r = mc[n] / ca[n]
            txt = f"×{r:.0f}" if r >= 10 else f"×{r:.1f}".replace(".", ",")
            if mc[n] < 5:  # oba czasy < 5 ms — zaszumione (docs/kolejka-serie-dane.md: wartość w nawiasie)
                txt = f"({txt})"
            ax.annotate(txt, (n, (mc[n] * ca[n]) ** 0.5),
                        ha="center", va="center", fontsize=6.5, color=INK2,
                        bbox={"boxstyle": "round,pad=0.15", "fc": "white", "ec": "none"})
        ax.set_title("2D: siatki 100² … 1000²" if dim == "2D" else "3D: siatki 10³ … 100³")
        ax.set_xlabel("liczba komórek")
        ax.set_ylabel("czas symulacji [ms]")
        ax.text(ca.index[-1] * 1.12, ca.values[-1], "CA", color=INK, fontsize=7, va="center", fontweight="bold")
        ax.text(mc.index[-1] * 1.12, mc.values[-1], "MC", color=INK, fontsize=7, va="center", fontweight="bold")
        ax.set_xlim(ca.index[0] / 1.6, ca.index[-1] * 2.2)
    axes[0].legend(loc="upper left", fontsize=6.5, handlelength=1.6)
    path = OUT / "ca_vs_mc.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def profil() -> Path:
    d = pd.read_csv(ROOT / "bench" / "results" / "profile_2026-10-09.csv")
    m = d[d["build"] == "msvc-O2"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(6.7, 2.3), constrained_layout=True, gridspec_kw={"width_ratios": [1, 1.15]})

    # (a) koszt jednostkowy: CA classic (10 zarodków, periodyczne, von Neumann) i MC full (von Neumann)
    def series(df, kind):
        out = {}
        for dim in ("2D", "3D"):
            s = df[df["dim"] == dim].sort_values("cells")
            if kind == "CA":
                y = s["caSim_ms_med"] * 1e6 / (s["cells"] * s["steps"])
            else:
                y = s["mcSim_ms_med"] * 1e6 / (s["cells"] * s["mcs"])
            out[dim] = (s["cells"].to_numpy(), y.to_numpy())
        return out

    cl = m[(m["group"] == "classic") & (m["seeds"] == 10) & (m["neighborhood"] == "von_neumann") & (m["boundary"] == "periodic")]
    mc = m[(m["group"] == "mc") & (m["neighborhood"] == "von_neumann")]
    for kind, df, color in (("CA", cl, CA), ("MC", mc, MC)):
        for dim, (x, y) in series(df, kind).items():
            ls = "-" if dim == "2D" else "--"
            a.plot(x, y, ls, marker="o" if dim == "2D" else "s", color=color, markeredgecolor="white", markeredgewidth=0.8)
            dy = {("CA", "2D"): 4, ("CA", "3D"): -4, ("MC", "2D"): -5, ("MC", "3D"): 5}[(kind, dim)]
            a.text(x[-1] * 1.35, y[-1] + dy, f"{kind} {dim}", color=INK, fontsize=6.5, va="center")
    a.set_xscale("log")
    log_axis(a, "x")
    a.set_xlim(600, 1e6 * 8)
    a.set_ylim(0, None)
    a.set_title("(a) koszt jednostkowy, von Neumann")
    a.set_xlabel("liczba komórek")
    a.set_ylabel("CA: ns/(komórka·krok)\nMC: ns/próbę")

    # (b) fazy kroku CA (--timing-detail): udział w caSim
    cases = [("classic_100x100x100_s10_vn_per_detail", "classic 100³ VN"),
             ("classic_1000x1000_s100_vn_per_detail", "classic 1000² VN"),
             ("test_3d_detail", "lawa test_3d"), ("etna_3d_detail", "lawa etna_3d")]
    rows = []
    for v, label in cases:
        r = m[m["variant"] == v].iloc[0]
        parts = [r["detail_caFrame_ms_med"], r.get("detail_caDescent_ms_med", 0) or 0, r["detail_caRules_ms_med"]]
        parts = [0.0 if pd.isna(p) else float(p) for p in parts]
        total = r["caSim_ms_med"]
        rows.append((label, [100 * p / total for p in parts], total))
    for i, (label, pct, total) in enumerate(reversed(rows)):
        left = 0.0
        for (name, color), p in zip(PHASES, pct):
            b.barh(i, p, left=left, color=color, height=0.62, edgecolor="white", linewidth=1.0)
            if p >= 4:
                b.text(left + p / 2, i, f"{p:.0f}%", ha="center", va="center", fontsize=6.3,
                       color="white" if color == "#2a78d6" else INK)
            left += p
        b.text(101, i, f"{total / 1000:.2f} s".replace(".", ",") if total >= 1000 else f"{total:.0f} ms",
               va="center", fontsize=6.3, color=INK2)
    b.set_yticks(range(len(rows)), [r[0] for r in reversed(rows)])
    b.set_xlim(0, 112)
    b.set_xticks([0, 25, 50, 75, 100])
    b.grid(axis="y", visible=False)
    b.set_title("(b) fazy kroku CA (udział w caSim)")
    b.set_xlabel("udział w czasie symulacji CA [%]   (z prawej: caSim)")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for _, c in PHASES]
    b.legend(handles, [n for n, _ in PHASES], loc="upper center", bbox_to_anchor=(0.45, -0.32), ncol=3, fontsize=6.3,
             handlelength=1.0, columnspacing=1.0)
    path = OUT / "profil.png"
    fig.savefig(path)
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------------------------------- raport 2

# Przypadki pomiarów równoległych: id w CSV -> (etykieta jak w zakładce „Wydajność”, rodzina: kolor, styl linii, znacznik)
CASES2 = [("lava_etna_real", "lawa: Etna", CA, "-", "o"),
          ("lava_duza_3d_front", "lawa 128²×64, frontalny", CA, "--", "s"),
          ("lava_duza_3d_full", "lawa 128²×64, pełny przebieg", CA, ":", "^"),
          ("classic_2000x2000_s400_vn", "rozrost ziaren 2000²", CL, "-", "o"),
          ("classic_300x300x300_s100_vn", "rozrost ziaren 300³", CL, "--", "s"),
          ("mc_cb_2d_1000", "Monte Carlo 1000²", MC, "-", "o"),
          ("mc_cb_3d_100", "Monte Carlo 100³", MC, "--", "s")]


def comma(v: float, digits: int = 2) -> str:
    return f"{v:.{digits}f}".replace(".", ",")


def gain(before: float, after: float) -> str:
    """Zysk jako mnożnik > 1 (×375, ×4,8)."""
    r = before / after
    return "×" + (f"{r:,.0f}".replace(",", " ") if r >= 20 else comma(r, 1))


def ms_label(v: float, _pos=None) -> str:
    return f"{v / 1000:g} s".replace(".", ",") if v >= 1000 else f"{v:g} ms".replace(".", ",")


def spread(vals: list[float], gap: float) -> list[float]:
    """Położenia etykiet: wartości rozsunięte co najmniej o gap (kolejność zachowana, środek bez zmian)."""
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    ys = [vals[i] for i in order]
    for k in range(1, len(ys)):
        ys[k] = max(ys[k], ys[k - 1] + gap)
    shift = (sum(vals) - sum(ys)) / len(ys) if ys else 0.0
    out = [0.0] * len(vals)
    for k, i in enumerate(order):
        out[i] = ys[k] + shift
    return out


def dumbbell(ax, rows: list[tuple[str, float, float]], before_label: str, after_label: str) -> None:
    """Para punktów na wiersz (przed szary, po kolorowy) na osi log., zysk z lewej strony punktu „po”."""
    y = np.arange(len(rows))[::-1]
    for yi, (_, a, b) in zip(y, rows):
        ax.plot([b, a], [yi, yi], color=GRID, lw=1.8, zorder=1, solid_capstyle="round")
        ax.scatter([a], [yi], s=22, color=MUTED, zorder=3, edgecolor="white", linewidth=0.8)
        ax.scatter([b], [yi], s=22, color=CA, zorder=3, edgecolor="white", linewidth=0.8)
        ax.text(b / 1.4, yi, gain(a, b), va="center", ha="right", fontsize=6.6, color=INK)
    ax.set_yticks(y, [r[0] for r in rows])
    ax.set_xscale("log")
    ax.xaxis.set_major_formatter(FuncFormatter(ms_label))
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.grid(axis="y", visible=False)
    ax.scatter([], [], s=22, color=MUTED, label=before_label)
    ax.scatter([], [], s=22, color=CA, label=after_label)
    ax.legend(loc="upper center", bbox_to_anchor=(0.45, -0.24), ncol=2, fontsize=6.4, handletextpad=0.3,
              columnspacing=1.0)


def r2_optymalizacja() -> Path:
    przed = pd.read_csv(RES / "profile_2026-10-17_przed2.csv")
    po = pd.read_csv(RES / "profile_2026-10-17_po.csv")
    cases = [("etna_real", "lawa: Etna"), ("test_3d", "lawa: teren testowy 3D"),
             ("classic_1000x1000_s100_vn_per", "rozrost ziaren 1000²"),
             ("classic_300x300x300_s100_vn_per", "rozrost ziaren 300³"),
             ("mcfull_1000x1000_vn_mcs100", "Monte Carlo 1000²"), ("mcfull_100x100x100_moore_mcs100", "Monte Carlo 100³")]

    def total(df, v):
        return float(df[(df.variant == v) & (df.build == "msvc-O2")].iloc[0]["total_ms_med"])

    rows_a = [(lab, total(przed, v), total(po, v)) for v, lab in cases]
    ff = pd.read_csv(RES / "ab" / "ab_k4_msvc_front_full.csv")
    ff = ff[ff.metric == "caSim"].set_index("case")
    cases_b = [("lava_etna_real", "lawa: Etna"), ("lava_test_3d", "lawa: teren testowy 3D"),
               ("classic_1000x1000_s100_vn", "rozrost ziaren 1000²"), ("classic_100x100x100_s10_vn", "rozrost ziaren 100³"),
               ("classic_300x300x300_s100_vn", "rozrost ziaren 300³")]
    rows_b = [(lab, float(ff.loc[c, "k4_full_med"]), float(ff.loc[c, "k4_med"])) for c, lab in cases_b]
    fig, (a, b) = plt.subplots(1, 2, figsize=(6.7, 2.05), constrained_layout=True)
    dumbbell(a, rows_a, "przed optymalizacją", "po optymalizacji")
    a.set_xlim(40, 1.2e5)
    a.set_title("(a) cały przebieg przed → po, taktowanie bazowe")
    a.set_xlabel("czas całego przebiegu, mediana [skala log.]")
    dumbbell(b, rows_b, "pełny przebieg (referencyjny)", "automat frontalny")
    b.set_xlim(10, 3e4)
    b.set_title("(b) faza automatu: frontalny vs pełny")
    b.set_xlabel("czas fazy automatu, mediana [skala log.]")
    return save2(fig, "optymalizacja.png")


def r2_openmp() -> Path:
    d = pd.read_csv(RES / "omp" / "skalowanie_msvc.csv")
    fig, (a, b) = plt.subplots(1, 2, figsize=(6.7, 2.3), constrained_layout=True)
    ps = np.array([1, 2, 4, 6, 8])
    a.plot([1, 8], [1, 8], ls="--", color=MUTED, lw=1.0)
    b.axhline(1.0, ls="--", color=MUTED, lw=1.0)
    s8, labels = [], []
    for cid, lab, col, ls, mk in CASES2:
        dc = d[d["case"] == cid].sort_values("threads")
        a.plot(dc["threads"], dc["S_phase"], ls=ls, marker=mk, color=col, mec="white", mew=0.6, lw=1.3, ms=3.6)
        b.plot(dc["threads"], dc["E_phase"], ls=ls, marker=mk, color=col, mec="white", mew=0.6, lw=1.3, ms=3.6)
        s8.append(float(dc[dc["threads"] == 8]["S_phase"].iloc[0]))
        labels.append((lab, col))
    for (lab, col), v, yl in zip(labels, s8, spread(s8, 0.36)):
        a.text(8.25, yl, f"{comma(v)}  {lab}", fontsize=6.0, va="center", color=INK)
    a.set_xlim(0.7, 14.6)
    a.set_ylim(0.8, 8.2)
    a.spines["bottom"].set_bounds(1, 8)
    for ax in (a, b):
        ax.set_xticks(ps)
        ax.set_xlabel("wątki p (rdzenie P)")
    a.set_ylabel("S(p) = T(1) / T(p)")
    a.text(6.1, 7.55, "idealne", fontsize=6.2, color=MUTED, rotation=33)
    a.set_title("(a) przyspieszenie fazy obliczeń")
    b.set_ylim(0, 1.12)
    b.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: comma(v, 1)))
    b.set_ylabel("E(p) = S(p) / p")
    b.set_title("(b) efektywność")
    return save2(fig, "openmp.png")


def r2_mpi() -> Path:
    z = pd.read_csv(RES / "testy" / "zestawienie.csv")
    z = z[z["compiler"] == "msvc"]
    m = pd.read_csv(RES / "mpi" / "skalowanie_mpi_msvc.csv")
    fig, (a, b) = plt.subplots(1, 2, figsize=(6.7, 2.4), constrained_layout=True, gridspec_kw={"width_ratios": [1.25, 1]})
    variants = [("OpenMP 8 wątków", lambda r: (r["kind"] == "omp") & (r["stage"] == 9) & (r["cores"] == 8), OMP_V),
                ("MPI 7 procesów (bez procesora 0)",
                 lambda r: (r["kind"] == "mpi") & (r["stage"] == 10) & (r["cores"] == 7), MPI_V),
                ("MPI 8 procesów", lambda r: (r["kind"] == "mpi") & (r["stage"] == 10) & (r["cores"] == 8)
                 & ~r["variant"].str.contains("changed"), MPI8_V),
                ("hybryda 2 procesy × 4 wątki", lambda r: (r["kind"] == "hyb") & r["variant"].str.contains("2 × 4"), HYB_V)]
    marks = ["o", "D", "s", "^"]
    y = np.arange(len(CASES2))[::-1]
    for yi, (cid, *_rest) in zip(y, CASES2):  # wiersz = przypadek, punkt = wariant; kreska od najgorszego do najlepszego
        r = z[(z["case"] == cid)]
        vals = [float(r[sel(r)]["S_phase"].iloc[0]) for _, sel, _ in variants]
        a.plot([min(vals), max(vals)], [yi, yi], color=GRID, lw=1.8, zorder=1, solid_capstyle="round")
        best = int(np.argmax(vals))
        a.text(max(vals) + 0.22, yi, comma(vals[best]), fontsize=6.2, va="center", color=INK, fontweight="bold")
        for (vlab, _sel, col), mk, v in zip(variants, marks, vals):
            a.scatter([v], [yi], s=24 if mk != "D" else 18, marker=mk, color=col, zorder=3,
                      edgecolor=MPI_V if col == MPI8_V else "white", linewidth=0.7)
    for (vlab, _sel, col), mk in zip(variants, marks):
        a.scatter([], [], s=24, marker=mk, color=col, edgecolor=MPI_V if col == MPI8_V else "white", linewidth=0.7,
                  label=vlab)
    a.set_yticks(y, [c[1] for c in CASES2])
    a.set_xlim(0, 8)
    a.axvline(8, color=MUTED, ls="--", lw=0.8)
    a.grid(axis="y", visible=False)
    a.set_xlabel("S fazy obliczeń przy 7–8 rdzeniach P (liczba: najlepszy wariant)")
    a.set_title("(a) OpenMP, MPI i hybryda (T(1) z sesji wariantu)")
    a.legend(loc="upper center", bbox_to_anchor=(0.32, -0.2), ncol=2, fontsize=6.0, handlelength=1.0,
             columnspacing=0.8)
    ends = []
    for cid, lab, col, ls, mk in CASES2:
        dc = m[(m["case"] == cid) & m["variant"].isin(["m2", "m3", "m4", "m6", "m7", "m8"])].sort_values("procs")
        b.plot(dc["procs"], 100 * dc["comm_share"], ls=ls, marker=mk, color=col, mec="white", mew=0.6, lw=1.3, ms=3.4)
        ends.append((lab, col, 100 * float(dc[dc["procs"] == 8]["comm_share"].iloc[0])))
    for (lab, col, v), yl in zip(ends, spread([e[2] for e in ends], 6.2)):
        b.text(8.25, yl, f"{v:.0f}%", fontsize=6.0, va="center", color=col, fontweight="bold")
    b.set_xticks([2, 3, 4, 6, 7, 8])
    b.set_xlim(1.7, 9.2)
    b.spines["bottom"].set_bounds(2, 8)
    b.set_ylim(0, 100)
    b.set_xlabel("procesy MPI p")
    b.set_ylabel("komunikacja / faza [%]")
    b.set_title("(b) udział komunikacji w fazie")
    handles = [Line2D([], [], color=c, lw=1.6, label=t) for t, c in (("lawa", CA), ("rozrost ziaren", CL),
                                                                    ("Monte Carlo", MC))]
    b.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3, fontsize=6.0, handlelength=1.4)
    return save2(fig, "mpi.png")


WEAK2 = [("weak_classic_2d", "rozrost ziaren\n2000 × 2000·p", "classic_2000x2000_s400_vn", "classic2d_vn"),
         ("weak_mc_cb_2d", "Monte Carlo\n1000 × 1000·p", "mc_cb_2d_1000", "mc_cb_2d"),
         ("weak_lava_full", "lawa pełny\n128 × 128·p × 64", "lava_duza_3d_full", "lava_full"),
         ("weak_lava_front", "lawa frontalny\n128 × 128·p × 64", "lava_duza_3d_front", "lava_front")]


def cg_per_unit(cg: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Chybienia jądra (funkcje kroku) na jednostkę pracy: CA — komórka × krok, MC — próba (jak bench/plot_testy.py)."""
    res: dict[str, dict[str, float]] = {}
    for case, g in cg.groupby("case"):
        res[case] = {}
        for _, r in g.iterrows():
            mc = pd.notna(r.get("mcs")) and float(r.get("mcs") or 0) > 0
            units = float(r["domainCells"]) * float(r["mcs"]) if mc else float(r["cells"]) * float(r["steps"])
            res[case]["D1"] = float(r["kD1"]) / units
            res[case][r["ll"]] = float(r["kDL"]) / units
    return res


def r2_testy() -> Path:
    wo = pd.read_csv(RES / "testy" / "slabe_omp_msvc.csv")
    wm = pd.read_csv(RES / "testy" / "slabe_mpi_msvc.csv")
    z = pd.read_csv(RES / "testy" / "zestawienie.csv")
    z = z[z["compiler"] == "msvc"]
    bw = pd.read_csv(RES / "testy" / "przepustowosc_msvc.csv")
    per = cg_per_unit(pd.read_csv(RES / "testy" / "cachegrind.csv"))
    fig, (a, b) = plt.subplots(1, 2, figsize=(6.7, 2.4), constrained_layout=True, gridspec_kw={"width_ratios": [1.2, 1]})
    bars = [("słabe E_w, OpenMP 8", OMP_V, None), ("słabe E_w, MPI 7", MPI_V, None),
            ("silne E, OpenMP 8", "white", OMP_V), ("silne E, MPI 7", "white", MPI_V)]
    w = 0.19
    x = np.arange(len(WEAK2))
    for i, (wid, lab, strong, _cg) in enumerate(WEAK2):
        zs = z[z["case"] == strong]
        vals = [float(wo[(wo["case"] == wid) & (wo["cores"] == 8)]["Ew_phase"].iloc[0]),
                float(wm[(wm["case"] == wid) & (wm["cores"] == 7)]["Ew_phase"].iloc[0]),
                float(zs[(zs["kind"] == "omp") & (zs["stage"] == 9) & (zs["cores"] == 8)]["E_phase"].iloc[0]),
                float(zs[(zs["kind"] == "mpi") & (zs["stage"] == 10) & (zs["cores"] == 7)]["E_phase"].iloc[0])]
        for k, ((_, fc, ec), v) in enumerate(zip(bars, vals)):
            xx = i + (k - 1.5) * w
            a.bar(xx, v, width=w * 0.9, color=fc, edgecolor=ec or "none", linewidth=1.0, hatch="////" if ec else None)
            a.text(xx, v + 0.03, comma(v), fontsize=5.2, ha="center", va="bottom", color=INK2, rotation=90)
    handles = [Patch(facecolor=fc, edgecolor=ec or fc, hatch="////" if ec else None, label=lab) for lab, fc, ec in bars]
    a.axhline(1.0, color=MUTED, ls="--", lw=0.8)
    a.set_xticks(x, [w_[1] for w_ in WEAK2], fontsize=6.3)
    a.set_ylim(0, 1.35)
    a.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: comma(v, 1)))
    a.set_ylabel("efektywność (faza obliczeń)")
    a.grid(axis="x", visible=False)
    a.set_title("(a) skalowanie słabe obok silnego, 7–8 rdzeni")
    a.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, fontsize=6.0, handlelength=1.4,
             columnspacing=1.0)
    s = bw[bw["mode"] == "stream"]
    for kern, lab, col in (("triad", "triad", "#104281"), ("odczyt", "sam odczyt", "#86b6ef")):
        dk = s[s["kernel"] == kern].sort_values("threads")
        b.plot(dk["threads"], dk["best"] / 1000, "-o", color=col, mec="white", mew=0.6, ms=3.6, lw=1.4, label=lab)
    dem = []
    for wid, lab, _strong, cid in WEAK2:  # zapotrzebowanie przy 8 wątkach: jednostki / s × chybienia L2 × 64 B
        r = wo[(wo["case"] == wid) & (wo["cores"] == 8)].iloc[0]
        phase = "mcSim_med" if pd.notna(r.get("mcSim_med")) else "caSim_med"
        units_s = float(r["cells"]) * float(r["work"]) / (float(r[phase]) / 1000.0)
        dem.append((lab.split("\n")[0], units_s * per[cid]["L2"] * 64 / 1e9))
    for (lab, v), yl in zip(dem, spread([d_[1] for d_ in dem], 4.2)):
        b.plot([8.45], [v], marker="_", ms=9, mew=1.8, color=INK2)
        b.text(8.85, yl, f"{lab}: {comma(v, 1)}", fontsize=5.9, va="center", color=INK)
    b.set_xlim(0.6, 13.6)
    b.set_xticks([1, 2, 4, 6, 8])
    b.spines["bottom"].set_bounds(1, 8)
    b.set_ylim(0, 65)
    b.set_xlabel("wątki (rdzenie P)")
    b.set_ylabel("GB/s")
    b.set_title("(b) przepustowość RAM; kreski: potrzeby przy 8")
    b.text(8.85, max(spread([d_[1] for d_ in dem], 4.2)) + 4.6, "GB/s spoza L2:", fontsize=5.9, color=INK2)
    b.legend(loc="upper left", fontsize=6.0, handlelength=1.4)
    return save2(fig, "testy.png")


def r2_pamiec() -> Path:
    per = cg_per_unit(pd.read_csv(RES / "testy" / "cachegrind.csv"))
    k = pd.read_csv(RES / "testy" / "krzywa_msvc.csv")
    fig, (a, b) = plt.subplots(1, 2, figsize=(6.7, 2.3), constrained_layout=True, gridspec_kw={"width_ratios": [1.15, 1]})
    pairs = [("lawa 3D: frontalny / pełny", "lava_front", "lava_full"),
             ("rozrost 100³: VN / Moore", "classic3d_vn", "classic3d_moore"),
             ("MC 1000²: szachownica / losowo", "mc_cb_2d", "mc_random_2d"),
             ("MC 100³: szachownica / losowo", "mc_cb_3d", "mc_random_3d")]
    y = np.arange(len(pairs))[::-1]
    for yi, (lab, c1, c2) in zip(y, pairs):
        v1, v2 = per[c1]["D1"], per[c2]["D1"]
        a.plot([v1, v2], [yi, yi], color=GRID, lw=1.8, zorder=1)
        a.scatter([v2], [yi], s=22, color=MUTED, zorder=3, edgecolor="white", linewidth=0.8)
        a.scatter([v1], [yi], s=22, color=CA if "lawa" in lab else CL if "rozrost" in lab else MC, zorder=3,
                  edgecolor="white", linewidth=0.8)
        r = v2 / v1
        a.text(max(v1, v2) * 1.5, yi, f"×{comma(r, 1) if r < 10 else f'{r:.0f}'} mniej" if r >= 1.05 else "×1,0",
               fontsize=6.4, va="center", color=INK)
        a.text(min(v1, v2) / 1.5, yi, comma(min(v1, v2), 3 if min(v1, v2) < 0.1 else 2), fontsize=5.6, va="center",
               ha="right", color=INK2)
    a.set_yticks(y, [p[0] for p in pairs])
    a.set_xscale("log")
    a.set_xlim(0.006, 300)
    a.xaxis.set_major_formatter(FuncFormatter(lambda v, _p: comma(v, 0) if v >= 1 else f"{v:g}".replace(".", ",")))
    a.grid(axis="y", visible=False)
    a.set_xlabel("chybienia D1 na komórkę × krok / próbę MC [log.]")
    a.set_title("(a) symulacja cachegrind: pierwszy / drugi wariant")
    curves = [("mc_random", "Monte Carlo, losowo (12 B/kom.)", MC, "-"),
              ("mc_cb", "Monte Carlo, szachownica", MC, "--"),
              ("classic_full", "rozrost, pełny przebieg (26 B/kom.)", CL, "-")]
    for cname, lab, col, ls in curves:
        dc = k[k["curve"] == cname].sort_values("cells")
        b.plot(dc["cells"], dc["ns_med"], ls=ls, marker="o", color=col, mec="white", mew=0.6, ms=3.2, lw=1.3, label=lab)
    for nbytes, col in ((12, MC), (26, CL)):  # progi: pojemność L2 / L3 przez bajty dotykane na komórkę w kroku
        for cap, txt in ((2 * 2**20, "L2"), (36 * 2**20, "L3")):
            b.axvline(cap / nbytes, color=col, ls=":", lw=0.9)
            b.text(cap / nbytes * 1.08, 16 if nbytes == 12 else 13, f"{txt} {nbytes} B", fontsize=5.5, color=col,
                   va="center")
    b.set_xscale("log")
    b.set_yscale("log")
    log_axis(b, "x")
    b.yaxis.set_major_locator(FixedLocator([5, 10, 20, 50, 100, 200]))
    b.yaxis.set_major_formatter(FuncFormatter(pl_num))
    b.yaxis.set_minor_locator(NullLocator())
    b.set_ylim(5, 260)
    b.set_xlabel("komórki siatki 2D (1 wątek)")
    b.set_ylabel("ns na komórkę × krok / próbę")
    b.set_title("(b) czas na jednostkę pracy vs rozmiar")
    b.legend(loc="upper center", bbox_to_anchor=(0.45, -0.24), ncol=2, fontsize=5.9, handlelength=1.6,
             columnspacing=0.8)
    return save2(fig, "pamiec.png")


def r2_podzial() -> Path:
    """Schemat podziału przestrzeni (SVG, bez danych pomiarowych): (a) warstwy z między wątki OpenMP przy `static`
    i `static,1`, (b) okno procesu MPI w lawie (pas + 1 warstwa brzegowa nad, 17 pod), (c) kolory szachownicy MC 2D."""
    T = [CL, "#1baf7a", "#eda100", "#e87ba4"]  # wątki 0..3
    INK2 = "#554b42"
    out: list[str] = []
    a = out.append
    a('<svg viewBox="0 0 700 158" width="100%" xmlns="http://www.w3.org/2000/svg" font-family="Inter, Segoe UI, sans-serif" font-size="9" fill="#1f1a16">')
    a('<defs><pattern id="hz" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
      '<rect width="4" height="4" fill="#cfe0f5"/><line x1="0" y1="0" x2="0" y2="4" stroke="#2a78d6" stroke-width="1.6"/></pattern>'
      '<marker id="ar2" viewBox="0 0 8 8" refX="7.5" refY="4" markerWidth="5" markerHeight="5" orient="auto">'
      '<path d="M0,0 L8,4 L0,8 z" fill="#7a6d60"/></marker></defs>')
    # (a) OpenMP
    a('<text x="2" y="11" font-weight="650">(a) OpenMP: warstwa z = iteracja</text>')
    base, h = 140, 6.6
    for col, (x, name) in enumerate(((40, "static"), (96, "static,1"))):
        for k in range(16):
            t = k // 4 if col == 0 else k % 4
            y = base - (k + 1) * h
            a(f'<rect x="{x}" y="{y:.1f}" width="36" height="{h - 1:.1f}" fill="{T[t]}"/>')
        a(f'<text x="{x + 18}" y="{base + 11}" text-anchor="middle" font-size="8.6" fill="{INK2}">{name}</text>')
    y_lo, y_hi = base - 6 * h, base - 2 * h
    a(f'<path d="M34 {y_hi:.1f} H30 V{y_lo:.1f} H34" stroke="#e8682a" stroke-width="1.6" fill="none"/>')
    a(f'<text x="27" y="{(y_lo + y_hi) / 2 + 3:.1f}" text-anchor="end" font-size="8.4" fill="#b93c0b">lawa</text>')
    a(f'<text x="2" y="{base - 15 * h:.1f}" font-size="8" fill="{INK2}">z</text>')
    a(f'<path d="M6 {base - 1:.1f} V{base - 15.5 * h:.1f}" stroke="{INK2}" stroke-width="0.9" marker-end="url(#ar2)"/>')
    for t in range(4):
        yy = 30 + t * 13
        a(f'<rect x="150" y="{yy - 7}" width="9" height="9" fill="{T[t]}"/><text x="163" y="{yy + 1}" font-size="8.4">wątek {t}</text>')
    a(f'<text x="150" y="98" font-size="8" fill="{INK2}">static: lawa u wątku 0</text>')
    a(f'<text x="150" y="110" font-size="8" fill="{INK2}">static,1: u każdego</text>')
    a(f'<text x="150" y="122" font-size="8" fill="{INK2}">bariera między fazami,</text>')
    a(f'<text x="150" y="134" font-size="8" fill="{INK2}">liczniki: reduction(+)</text>')
    # (b) MPI
    a('<text x="246" y="11" font-weight="650">(b) MPI: okno procesu r (lawa)</text>')
    x, w, lh = 316, 40, 4.1
    y0 = 146
    ytype = y0 - 16 * lh
    a(f'<rect x="{x}" y="{ytype:.1f}" width="{w}" height="{16 * lh:.1f}" fill="#e3edf9" stroke="#b9cde8" stroke-width="0.6"/>')
    for k in range(1, 16):
        yy = y0 - k * lh
        a(f'<line x1="{x}" y1="{yy:.1f}" x2="{x + w}" y2="{yy:.1f}" stroke="#c6d8ef" stroke-width="0.5"/>')
    yfull_lo = ytype - lh
    a(f'<rect x="{x}" y="{yfull_lo:.1f}" width="{w}" height="{lh:.1f}" fill="url(#hz)" stroke="#2a78d6" stroke-width="0.6"/>')
    yown = yfull_lo - 8 * lh
    a(f'<rect x="{x}" y="{yown:.1f}" width="{w}" height="{8 * lh:.1f}" fill="#2a78d6"/>')
    for k in range(1, 8):
        yy = yfull_lo - k * lh
        a(f'<line x1="{x}" y1="{yy:.1f}" x2="{x + w}" y2="{yy:.1f}" stroke="#ffffff" stroke-width="0.5"/>')
    ytop = yown - lh
    a(f'<rect x="{x}" y="{ytop:.1f}" width="{w}" height="{lh:.1f}" fill="url(#hz)" stroke="#2a78d6" stroke-width="0.6"/>')
    lx = x + w + 8
    a(f'<text x="{lx}" y="{ytop + 3.5:.1f}" font-size="8.4">1 nad pasem: pełny stan (9 B/kom.)</text>')
    a(f'<text x="{lx}" y="{(yown + yfull_lo) / 2 + 3:.1f}" font-size="8.4" font-weight="600">pas własny: reguły liczą tylko go</text>')
    a(f'<text x="{lx}" y="{yfull_lo + 3.5:.1f}" font-size="8.4">1 tuż pod pasem: pełny stan</text>')
    a(f'<text x="{lx}" y="{(ytype + y0) / 2:.1f}" font-size="8.4">16 głębiej: sam typ (1 B/kom.),</text>')
    a(f'<text x="{lx}" y="{(ytype + y0) / 2 + 11:.1f}" font-size="8.4">od 1–3 procesów niżej</text>')
    for yy, txt in ((ytop + lh / 2, "od r+1"), ((yfull_lo + y0) / 2, "od r−1, r−2…")):
        a(f'<text x="{x - 30}" y="{yy + 3:.1f}" text-anchor="end" font-size="8.2" fill="{INK2}">{txt}</text>')
        a(f'<path d="M{x - 27} {yy:.1f} H{x - 3}" stroke="#7a6d60" stroke-width="1" marker-end="url(#ar2)"/>')
    a(f'<text x="{x - 30}" y="{yown + 20:.1f}" text-anchor="end" font-size="8.2" fill="{INK2}">Isend / Irecv</text>')
    a(f'<text x="{x - 30}" y="{yown + 30:.1f}" text-anchor="end" font-size="8.2" fill="{INK2}">+ Waitall</text>')
    # (c) szachownica
    a('<text x="532" y="11" font-weight="650">(c) szachownica MC (2D)</text>')
    vn = ["#7d68dd", "#d9d2f6"]
    mo = ["#7d68dd", "#b3a8e6", "#e0a07c", "#f6d9c7"]
    c = 10.5
    for gx, colors, fn in ((536, vn, lambda i, j: (i + j) % 2), (620, mo, lambda i, j: (i % 2) + 2 * (j % 2))):
        for j in range(6):
            for i in range(6):
                a(f'<rect x="{gx + i * c:.1f}" y="{24 + j * c:.1f}" width="{c - 0.8:.1f}" height="{c - 0.8:.1f}" fill="{colors[fn(i, j)]}"/>')
    a(f'<text x="536" y="100" font-size="8.4">von Neumann:</text><text x="536" y="110" font-size="8.4">2 kolory</text>')
    a(f'<text x="620" y="100" font-size="8.4">Moore: 4 kolory</text><text x="620" y="110" font-size="8.4">(w 3D: 8)</text>')
    a(f'<text x="532" y="128" font-size="8" fill="{INK2}">jeden kolor = komórki bez wspólnych</text>')
    a(f'<text x="532" y="139" font-size="8" fill="{INK2}">sąsiadów: kolor po kolorze, w kolorze</text>')
    a(f'<text x="532" y="150" font-size="8" fill="{INK2}">równolegle (wątki albo pasy MPI)</text>')
    a('</svg>')
    path = OUT2 / "podzial.svg"
    path.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    return path

def save2(fig, name: str) -> Path:
    path = OUT2 / name
    fig.savefig(path)
    plt.close(fig)
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description="Wykresy raportów (docs/img/raport/, docs/img/raport-2/)")
    ap.add_argument("raport", nargs="?", choices=["1", "2"], help="numer raportu (domyślnie oba)")
    args = ap.parse_args()
    style()
    paths = []
    if args.raport in (None, "1"):
        OUT.mkdir(parents=True, exist_ok=True)
        paths += [ca_vs_mc(), profil()]
    if args.raport in (None, "2"):
        OUT2.mkdir(parents=True, exist_ok=True)
        paths += [r2_podzial(), r2_optymalizacja(), r2_openmp(), r2_mpi(), r2_testy(), r2_pamiec()]
    for p in paths:
        print(f"zapisano {p.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    sys.exit(main())
