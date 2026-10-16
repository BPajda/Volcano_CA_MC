#!/usr/bin/env python3
"""Wykresy do raportu (docs/raport.md) — jasna paleta do druku, kolory jak w GUI (etap 7):
CA = lawa #e8682a, MC = chłodny fiolet #7d68dd (para sprawdzona walidatorem palety, docs/etap-7-wyglad-gui.md).

    python tools/raport_wykresy.py            # -> docs/img/raport/ca_vs_mc.png, docs/img/raport/profil.png

Dane (bez nowych pomiarów — tylko odczyt plików z repozytorium):
  ca_vs_mc.png  docs/data/ca_vs_mc.csv — seria „CA vs MC — rozmiar siatki” policzona przez GUI 10.10.2026
                (1 worker, przypięcie do CPU 2; docs/etap-5-kolejka-serie-dane.md, punkt 4.2): caSim / mcSim vs liczba komórek.
  profil.png    bench/results/profile_2026-10-09.csv — pomiar z 9.10.2026 (MSVC /O2, mediana z 3 powtórzeń):
                (a) koszt jednostkowy CA classic (10 zarodków) i MC full (Q = 50, 100 MCS) vs liczba komórek,
                (b) fazy kroku CA z --timing-detail (docs/etap-3-profilowanie.md, punkty 3.2, 3.3, 3.6).
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "img" / "raport"
CA, MC = "#e8682a", "#7d68dd"
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
            if mc[n] < 5:  # oba czasy < 5 ms — zaszumione (docs/etap-5-kolejka-serie-dane.md: wartość w nawiasie)
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


def main() -> None:
    style()
    OUT.mkdir(parents=True, exist_ok=True)
    for p in (ca_vs_mc(), profil()):
        print(f"zapisano {p.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
