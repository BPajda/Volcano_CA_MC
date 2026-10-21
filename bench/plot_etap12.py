#!/usr/bin/env python3
"""Wykresy etapu 12 (testy wydajności) -> docs/img/etap12_*.png z wyników w bench/results/testy/.

Użycie (z katalogu volcano-ca-mc):
    python bench/plot_etap12.py
    python bench/plot_etap12.py --only skalowanie,pamiec
    python bench/plot_etap12.py --dir bench/results/testy --out docs/img

Wykresy z danych części 1 (zestawienie istniejących pomiarów, pamięć, cachegrind — bez nowych pomiarów czasu):
    etap12_skalowanie_{lawa,classic,mc}.png  S(p) i E(p) fazy obliczeń: OpenMP (etap 9) vs MPI (etap 10) vs hybryda
    etap12_schodki.png         łączne przyspieszenie od programu sprzed etapu 8: algorytm → szachownica → równoległość
    etap12_cachegrind.png      chybienia D1 / L2 / L3 na jednostkę pracy: pary porównań, rozmiar siatki, pas MPI
    etap12_pamiec_p.png        pamięć MPI vs liczba procesów: suma danych, proces 0 przy zbieraniu i MPI-IO
    etap12_pamiec_rozmiar.png  szczyt pamięci vs rozmiar siatki (pomiar i model) oraz model vs pomiar
Wykresy z danych części 2 (bench/results/testy/PLAN_POMIARU.md; pomijane, gdy brak plików):
    etap12_slabe.png           skalowanie słabe E_w(p) OpenMP vs MPI obok silnego E(p)
    etap12_krzywa.png          czas na komórkę × krok / na próbę MC vs zbiór roboczy kroku, progi L1d / L2 / L3
    etap12_przepustowosc.png   przepustowość pamięci vs wątki i vs zbiór roboczy + zapotrzebowanie CA / MC (8 wątków)
    etap12_falszywe.png        fałszywe współdzielenie: licznik co 8 B vs co 64 B, nagłówki list warstw
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from memory import med_rows, mpi_model  # noqa: E402
from plot_etap9 import MUTED, comma  # noqa: E402
from plot_profile import C, INK, INK2, save, style  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MB = 1024.0 * 1024.0
OMP_C, MPI_C, HYB_C = C[0], C[1], C[2]  # OpenMP / MPI / hybryda — ten sam kolor na wszystkich wykresach
LEVELS = [("D1", "#86b6ef"), ("L2", "#2a78d6"), ("L3", "#104281")]  # rampa porządkowa jednego odcienia (jasny → ciemny)
CACHE_LINES = [(48 * 1024, "L1d 48 KB"), (2 * MB, "L2 2 MB"), (36 * MB, "L3 36 MB")]

GROUPS = {
    "lawa": [("lava_etna_real", "lawa etna_real (front)"), ("lava_duza_3d_front", "lawa 3D 128²×64 (front)"),
             ("lava_duza_3d_full", "lawa 3D 128²×64 (full)")],
    "classic": [("classic_2000x2000_s400_vn", "classic 2000² (VN)"), ("classic_300x300x300_s100_vn", "classic 300³ (VN)")],
    "mc": [("mc_cb_2d_1000", "MC szachownica 1000² (VN)"), ("mc_cb_3d_100", "MC szachownica 100³ (Moore)")],
}
GROUP_TITLE = {"lawa": "lawa (CA)", "classic": "classic (CA, rozrost ziaren)", "mc": "Monte Carlo (szachownica)"}


def load(dir_: Path, name: str) -> pd.DataFrame | None:
    p = dir_ / name
    if not p.exists():
        print(f"  (brak {p.name} — pomijam)")
        return None
    return pd.read_csv(p)


def spread(vals: list[float], gap: float) -> list[float]:
    """Położenia etykiet: wartości rozsunięte tak, by sąsiednie były co najmniej o gap od siebie (środek zostaje)."""
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    ys = [vals[i] for i in order]
    for k in range(1, len(ys)):
        ys[k] = max(ys[k], ys[k - 1] + gap)
    shift = (sum(vals) - sum(ys)) / len(ys) if ys else 0.0
    out = [0.0] * len(vals)
    for k, i in enumerate(order):
        out[i] = ys[k] + shift
    return out


def top_legend(fig: plt.Figure, handles: list, ncol: int, y: float = 1.0) -> None:
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, y), ncol=ncol, fontsize=8.6,
               handlelength=2.2, columnspacing=1.4)


# ---------------------------------------------------------------------------
# Część 1: zestawienie S / E i łączne przyspieszenie
# ---------------------------------------------------------------------------
def plot_scaling(dir_: Path, out: Path) -> None:
    z = load(dir_, "zestawienie.csv")
    if z is None:
        return
    d = z[z["compiler"] == "msvc"]
    for g, cases in GROUPS.items():
        style()
        n = len(cases)
        fig, axes = plt.subplots(2, n, figsize=(4.4 * n, 7.0), squeeze=False)
        for j, (cid, title) in enumerate(cases):
            dc = d[d["case"] == cid]
            omp = dc[(dc["kind"] == "omp") & (dc["stage"] == 9)].sort_values("cores")
            mpi_all = dc[(dc["kind"] == "mpi") & (dc["stage"] == 10) & ~dc["variant"].str.contains("changed")]
            mpi = mpi_all[mpi_all["cores"] != 7].sort_values("cores")
            m7 = mpi_all[mpi_all["cores"] == 7]
            hyb = dc[dc["kind"] == "hyb"]
            for row, (col, ideal, lab) in enumerate((("S_phase", lambda p: p, "przyspieszenie S(p)"),
                                                     ("E_phase", lambda p: np.ones_like(p), "efektywność E(p)"))):
                ax = axes[row][j]
                ps = np.array([1.0, 8.0])
                ax.plot(ps, ideal(ps), ls="--", color=MUTED, lw=1.2)
                ax.plot(omp["cores"], omp[col], "-o", color=OMP_C, mec="white", mew=1.0)
                ax.plot(mpi["cores"], mpi[col], "-s", color=MPI_C, mec="white", mew=1.0)
                ax.plot(m7["cores"], m7[col], "D", mfc="white", mec=MPI_C, mew=1.8, ms=7)
                for _, r in hyb.iterrows():
                    mk = "^" if "2 × 4" in r["variant"] else "v"
                    ax.plot([r["cores"] + 0.3], [r[col]], mk, color=HYB_C, mec="white", mew=1.0, ms=8)
                if row == 0:  # wybrane etykiety: wartości przy 8 (OpenMP, MPI) i 7 procesach
                    v8 = [float(df[df["cores"] == 8][col].iloc[0]) for df in (omp, mpi) if len(df[df["cores"] == 8])]
                    for v, yl in zip(v8, spread(v8, 0.45)):
                        ax.text(8.6, yl, comma(v), fontsize=7.6, color=INK, va="center")
                    if len(m7):
                        v = float(m7[col].iloc[0])
                        ax.text(7, v + 0.35, comma(v), fontsize=7.6, color=INK, ha="center")
                    ax.set_ylim(0, 8.6)
                    ax.set_title(title, fontsize=10)
                else:
                    ax.set_ylim(0, 1.15)
                    ax.set_xlabel("rdzenie P (wątki / procesy)")
                ax.set_xlim(0.6, 9.6)
                ax.set_xticks([1, 2, 3, 4, 5, 6, 7, 8])
                ax.spines["bottom"].set_bounds(1, 8)
                if j == 0:
                    ax.set_ylabel(lab)
        handles = [Line2D([], [], ls="--", color=MUTED, label="idealnie"),
                   Line2D([], [], marker="o", color=OMP_C, label="OpenMP (etap 9)"),
                   Line2D([], [], marker="s", color=MPI_C, label="MPI (etap 10)"),
                   Line2D([], [], marker="D", ls="", mfc="white", mec=MPI_C, mew=1.8, label="MPI 7 (bez procesora 0)"),
                   Line2D([], [], marker="^", ls="", color=HYB_C, ms=8, label="hybryda 2 × 4"),
                   Line2D([], [], marker="v", ls="", color=HYB_C, ms=8, label="hybryda 4 × 2")]
        fig.tight_layout(rect=(0, 0, 1, 0.9))
        top_legend(fig, handles, 6, 0.91)
        fig.suptitle(f"Faza obliczeń — {GROUP_TITLE[g]}: przyspieszenie i efektywność (MSVC / MS-MPI, dane etapów "
                     "9–10, bez turbo)", y=0.985, fontsize=11)
        save(fig, out, f"etap12_skalowanie_{g}.png")


def plot_steps(dir_: Path, out: Path) -> None:
    lac = load(dir_, "zestawienie_lacznie.csv")
    if lac is None:
        return
    style()
    fig, ax = plt.subplots(figsize=(10.5, 5.6))
    d = lac[lac["compiler"] == "msvc"].reset_index(drop=True)
    gcc = lac[lac["compiler"] == "gcc"].set_index("case")
    xs = np.arange(4)
    ends = []
    for i, r in d.iterrows():
        cb = r["S_checkerboard"] if np.isfinite(r["S_checkerboard"]) else 1.0
        y = [1.0, r["S_alg"], r["S_alg"] * cb, r["S_product"]]
        ax.plot(xs, y, "-o", color=C[i], mec="white", mew=1.0, zorder=3)
        g = gcc.loc[r["case"], "S_product"] if r["case"] in gcc.index else np.nan
        best = str(r["best"]).replace(" (bez procesora 0)", "").replace("wątków", "wątk.")
        factors = f"×{comma(r['S_alg'], 0 if r['S_alg'] >= 10 else 2)} alg." + \
                  (f" · ×{comma(cb)} szach." if cb > 1.001 else "") + f" · ×{comma(r['S_par'])} {best}"
        thousands = lambda v: f"{v:,.0f}".replace(",", " ")  # noqa: E731
        ends.append([r["S_product"], f"{r['short']}: ×{thousands(r['S_product'])}  = {factors};  GCC ×{thousands(g)}",
                     C[i]])
    # Etykiety końcowe rozsunięte w skali log. (co najmniej ×1,45 między sąsiednimi), z kreską do punktu.
    ends.sort(key=lambda e: e[0])
    ys = [e[0] for e in ends]
    for k in range(1, len(ys)):
        ys[k] = max(ys[k], ys[k - 1] * 1.45)
    for (v, text, col), yl in zip(ends, ys):
        ax.plot([3.05, 3.22], [v, yl], color=col, lw=1.0)
        ax.text(3.26, yl, text, fontsize=8.2, color=INK, va="center")
    ax.set_yscale("log")
    ax.set_xticks(xs)
    ax.set_xticklabels(["program\nsprzed\netapu 8", "po etapie 8\n(algorytm)", "szachownica\nMC przy\n1 wątku",
                        "najlepszy\nwariant\nrównoległy"], fontsize=8.6)
    ax.set_xlim(-0.2, 6.9)
    ax.set_ylabel("łączne przyspieszenie fazy obliczeń (skala log.)")
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"×{v:,.0f}".replace(",", " ")))
    ax.grid(axis="x", visible=False)
    ax.spines["bottom"].set_bounds(0, 3)
    ax.set_title("„Schodki” przyspieszenia fazy obliczeń od programu sprzed optymalizacji (MSVC; iloczyn ilorazów "
                 "z sesji)", fontsize=10)
    fig.tight_layout()
    save(fig, out, "etap12_schodki.png")


# ---------------------------------------------------------------------------
# Część 1: cachegrind
# ---------------------------------------------------------------------------
CG_PAIRS = [("lava_front", "lawa test_3d: front"), ("lava_full", "lawa test_3d: full"),
            ("classic2d_vn", "classic 1000²: VN"), ("classic2d_moore", "classic 1000²: Moore"),
            ("classic3d_vn", "classic 100³: VN"), ("classic3d_moore", "classic 100³: Moore"),
            ("layout_vector", "classic 1000² full: vector"), ("layout_matrix", "classic 1000² full: macierz"),
            ("mc_random_2d", "MC 1000²: random"), ("mc_cb_2d", "MC 1000²: szachownica"),
            ("mc_random_3d", "MC 100³: random"), ("mc_cb_3d", "MC 100³: szachownica")]
CG_SIZES = {"classic `full` (dostęp po kolei)": [("size_classic_256", "256²\n1,7 MB"),
                                                 ("size_classic_1024", "1 024²\n27 MB"),
                                                 ("size_classic_2896", "2 896²\n218 MB")],
            "MC random (dostęp losowy)": [("size_mc_256", "256²\n0,8 MB"), ("size_mc_1024", "1 024²\n13 MB"),
                                          ("size_mc_4096", "4 096²\n201 MB")],
            "MC szachownica: pas 1 z 8 procesów vs cała siatka": [("strip_mc_cb_1000x125", "pas 1000 × 125\n1,5 MB"),
                                                                  ("strip_mc_cb_1000x1000", "1000²\n12 MB")]}


def cg_per_unit(cg: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Chybienia jądra (funkcje kroku) na jednostkę pracy: CA — komórka × krok, MC — próba (komórki domeny × MCS)."""
    res: dict[str, dict[str, float]] = {}
    for case, g in cg.groupby("case"):
        res[case] = {}
        for _, r in g.iterrows():
            mc = pd.notna(r.get("mcs")) and float(r.get("mcs") or 0) > 0
            units = float(r["domainCells"]) * float(r["mcs"]) if mc else float(r["cells"]) * float(r["steps"])
            res[case]["D1"] = float(r["kD1"]) / units
            res[case][r["ll"]] = float(r["kDL"]) / units
    return res


def bars_levels(ax: plt.Axes, pos: np.ndarray, vals: list[dict[str, float]], horizontal: bool, w: float = 0.26,
                floor: float = 1e-4) -> None:
    """Grupy słupków D1 / L2 / L3 (rampa jednego odcienia) w skali log.; zero — napis „0” zamiast słupka."""
    for k, (lvl, col) in enumerate(LEVELS):
        off = (1 - k) * w if horizontal else (k - 1) * w  # D1 u góry grupy (poziomo) / z lewej (pionowo)
        for p, v in zip(pos, vals):
            x = v.get(lvl, np.nan)
            if not np.isfinite(x):
                continue
            txt = "0" if x < floor else comma(x, 4 if x < 0.001 else 3 if x < 0.1 else 2)
            if horizontal:
                if x >= floor:
                    ax.barh(p + off, x - floor * 0.5, left=floor * 0.5, height=w * 0.9, color=col)
                ax.text(max(x, floor) * 1.15, p + off, txt, fontsize=6.6, va="center", color=INK2)
            else:
                if x >= floor:
                    ax.bar(p + off, x - floor * 0.5, bottom=floor * 0.5, width=w * 0.9, color=col)
                ax.text(p + off, max(x, floor) * 1.2, txt, fontsize=6.6, ha="center", color=INK2,
                        rotation=90 if x >= floor else 0, va="bottom")


def plot_cachegrind(dir_: Path, out: Path) -> None:
    cg = load(dir_, "cachegrind.csv")
    if cg is None:
        return
    per = cg_per_unit(cg)
    style()
    fig = plt.figure(figsize=(14, 8.2))
    gs = fig.add_gridspec(3, 2, width_ratios=[1.25, 1.0], hspace=0.75, wspace=0.28)
    ax = fig.add_subplot(gs[:, 0])
    pos, vals, labels = [], [], []
    y = 0.0
    for i, (cid, lab) in enumerate(CG_PAIRS):
        if cid not in per:
            continue
        pos.append(y)
        vals.append(per[cid])
        labels.append(lab)
        y += 1.0 if i % 2 == 0 else 1.55  # odstęp między parami porównań
    pos_a = -np.array(pos)
    bars_levels(ax, pos_a, vals, horizontal=True)
    ax.set_yticks(pos_a)
    ax.set_yticklabels(labels, fontsize=8.6)
    ax.set_xscale("log")
    ax.set_xlim(5e-5, 60)
    ax.set_xlabel("chybienia na jednostkę pracy (skala log.; CA — komórka × krok, MC — próba)")
    ax.grid(axis="y", visible=False)
    ax.set_title("Pary porównań (jądro: funkcje kroku, 1 wątek, GCC -O3)", fontsize=10)
    for k, (title, items) in enumerate(CG_SIZES.items()):
        a = fig.add_subplot(gs[k, 1])
        items = [(c, l) for c, l in items if c in per]
        p = np.arange(len(items))
        bars_levels(a, p, [per[c] for c, _ in items], horizontal=False)
        a.set_yscale("log")
        a.set_ylim(5e-5, 80)
        a.set_xticks(p)
        a.set_xticklabels([l for _, l in items], fontsize=8)
        a.set_title(title, fontsize=9.5)
        a.grid(axis="x", visible=False)
        a.set_ylabel("chybienia / jedn.", fontsize=8.5)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c, label=f"chybienia {l}") for l, c in LEVELS]
    top_legend(fig, handles, 3, 0.94)
    fig.suptitle("Symulacja pamięci podręcznej (valgrind cachegrind): D1 48 KB, L2 2 MB, L3 36 MB rdzenia P — "
                 "zbiór roboczy w opisach rozmiaru", y=0.99, fontsize=11)
    save(fig, out, "etap12_cachegrind.png")


# ---------------------------------------------------------------------------
# Część 1: pamięć główna
# ---------------------------------------------------------------------------
MEM_FAMILY = [("classic2d", "classic 2D", ["classic2d_1000", "classic2d_2000", "classic2d_4000"]),
              ("classic3d", "classic 3D", ["classic3d_100", "classic3d_200", "classic3d_300"]),
              ("lava3d", "lawa 3D (front)", ["lava3d_64", "lava3d_128", "lava3d_256"]),
              ("mc3d", "MC 3D (szachownica)", ["mc3d_50", "mc3d_100", "mc3d_200"])]
MEM_P = [("classic2d_4000", "classic 4000²", C[0]), ("classic3d_300", "classic 300³", C[1]),
         ("lava3d_256", "lawa 256² × 64", C[2]), ("mc3d_200", "MC 200³", C[3])]
PROCS = [1, 2, 3, 4, 8]


def mem_load(dir_: Path, name: str) -> dict | None:
    p = dir_ / name
    if not p.exists():
        print(f"  (brak {p.name} — pomijam)")
        return None
    with open(p, encoding="utf-8") as f:
        return med_rows(list(csv.DictReader(f)))


def mem_base(med: dict) -> tuple[float, dict[int, float]]:
    """Narzut stały procesu: engine (1 wątek) i engine_mpi na p procesach (średnia na proces) — classic 16³."""
    o1 = med.get(("base_tiny", "o1"), {})
    base_omp = min(float(o1["peakRss"]), float(o1["endRss"])) if o1.get("endRss") not in (None, "") else \
        float(o1.get("peakRss", 0.0))
    base_mpi = {p: float(med[("base_tiny", f"m{p}d")]["rssAvg"]) for p in range(1, 9) if ("base_tiny", f"m{p}d") in med}
    return base_omp, base_mpi


def plot_memory_p(dir_: Path, out: Path) -> None:
    med = mem_load(dir_, "pamiec_msvc_raw.csv")
    if med is None:
        return
    _, base_mpi = mem_base(med)
    style()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5.0), gridspec_kw={"width_ratios": [1.0, 1.15]})
    for cid, lab, col in MEM_P:
        rel, ps = [], []
        one = med.get((cid, "m1d"))
        if not one:
            continue
        d1 = float(one["rssAvg"]) - base_mpi.get(1, 0.0)
        for p in PROCS:
            e = med.get((cid, f"m{p}d"))
            if e:
                ps.append(p)
                rel.append((float(e["rssAvg"]) * p - p * base_mpi.get(p, 0.0)) / d1)
        a1.plot(ps, rel, "-o", color=col, mec="white", mew=1.0)
        e8 = med.get((cid, "m8d"))
        halo = mpi_model(e8) if e8 else None
        txt = f"{lab}: ×{comma(rel[-1])}" + (f" (warstwy brzegowe {100 * halo['haloShare']:.0f}% siatki)"
                                              if halo and halo["haloShare"] > 0.03 else "")
        a1.text(8.2, rel[-1], txt, fontsize=8, va="center", color=INK)
    a1.plot([1, 8], [1, 1], color=MUTED, ls="--", lw=1.1, zorder=1)
    a1.set_xlim(0.7, 15.5)
    a1.set_xticks(PROCS)
    a1.spines["bottom"].set_bounds(1, 8)
    a1.set_xlabel("procesy MPI (p)")
    a1.set_ylabel("suma danych wszystkich procesów / 1 proces")
    a1.set_title("Suma pamięci danych (pomiar − p × narzut stały procesu), zebranie na proces 0", fontsize=9.5)
    a1.grid(axis="x", visible=False)

    # (b) przy 8 procesach: proces 0 przy zbieraniu, proces 0 przy MPI-IO, najmniejszy proces. Kolor = przypadek
    # (jak w panelu a), rodzaj słupka = wypełnienie: pełny / kreskowany / sam obrys.
    x = np.arange(len(MEM_P))
    w = 0.26
    series = [("proces 0 — zebranie wyniku (gather)", "m8d", "rssMax", {}),
              ("proces 0 — MPI-IO", "m8di", "rssMax", {"hatch": "////", "edgecolor": "white", "alpha": 0.75}),
              ("najmniejszy proces (gather)", "m8d", "rssMin", {"fill": False, "linewidth": 1.6})]
    for k, (lab, var, key, kw) in enumerate(series):
        for xi, (cid, _, col) in zip(x, MEM_P):
            e = med.get((cid, var))
            if not e:
                continue
            v = float(e[key]) / MB
            opts = dict(kw)
            if opts.get("fill") is False:
                opts["edgecolor"] = col
            else:
                opts["facecolor"] = col
            a2.bar(xi + (k - 1) * w, v, width=w * 0.92, **opts)
            a2.text(xi + (k - 1) * w, v + 8, f"{v:.0f}", ha="center", fontsize=7.4, color=INK)
    a2.set_xticks(x)
    a2.set_xticklabels([l for _, l, _ in MEM_P])
    a2.set_ylabel("szczyt pamięci procesu [MB]")
    a2.set_title("8 procesów: proces 0 przy zebraniu wyniku i przy MPI-IO vs najmniejszy proces", fontsize=9.5)
    legend = [plt.Rectangle((0, 0), 1, 1, facecolor=INK2, label=series[0][0]),
              plt.Rectangle((0, 0), 1, 1, facecolor=INK2, hatch="////", edgecolor="white", alpha=0.75,
                            label=series[1][0]),
              plt.Rectangle((0, 0), 1, 1, fill=False, edgecolor=INK2, linewidth=1.6, label=series[2][0])]
    a2.legend(handles=legend, fontsize=8.2, loc="upper right")
    a2.grid(axis="x", visible=False)
    fig.suptitle("Pamięć główna wersji MPI (MSVC / MS-MPI, typy pochodne, szczyt zbioru roboczego procesu)", y=1.02,
                 fontsize=11)
    fig.tight_layout()
    save(fig, out, "etap12_pamiec_p.png")


def plot_memory_size(dir_: Path, out: Path) -> None:
    med = mem_load(dir_, "pamiec_msvc_raw.csv")
    if med is None:
        return
    base_omp, base_mpi = mem_base(med)
    style()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5.2))
    for i, (_, lab, ids) in enumerate(MEM_FAMILY):
        cells, meas, model = [], [], []
        for cid in ids:
            e = med.get((cid, "o1"))
            if e:
                cells.append(float(e["cells"]))
                meas.append(float(e["peakRss"]) / MB)
                model.append((float(e["modelPeak"]) + base_omp) / MB)
        a1.plot(cells, meas, "o", color=C[i], mec="white", mew=1.0, ms=8, label=f"{lab}: pomiar")
        a1.plot(cells, model, "--", color=C[i], lw=1.4)
        if cells:
            bpc = (meas[-1] * MB - base_omp) / cells[-1]
            a1.text(cells[-1] * 1.25, meas[-1], f"{lab}\n{comma(bpc, 1)} B / komórkę", fontsize=7.8, va="center",
                    color=INK)
    a1.set_xscale("log")
    a1.set_yscale("log")
    a1.set_xlim(8e4, 2.5e8)
    a1.set_xlabel("komórki siatki (skala log.)")
    a1.set_ylabel("szczyt pamięci procesu [MB] (skala log.)")
    a1.set_title("1 wątek: pomiar (punkty) i model + narzut stały (linia przerywana)", fontsize=9.5)

    # (b) model vs pomiar: OpenMP 1 wątek i suma MPI (gather i MPI-IO), dane = pomiar − narzut stały.
    for i, (fam, lab, ids) in enumerate(MEM_FAMILY):
        xs, ys, xm, ym = [], [], [], []
        for cid in ids:
            e = med.get((cid, "o1"))
            if e:
                xs.append(float(e["modelPeak"]) / MB)
                ys.append((float(e["peakRss"]) - base_omp) / MB)
            for p in PROCS:
                for io in ("d", "di"):
                    e = med.get((cid, f"m{p}{io}"))
                    mm = mpi_model(e) if e else None
                    if mm:
                        xm.append(mm["modelSum"] / MB)
                        ym.append((float(e["rssAvg"]) * p - p * base_mpi.get(p, 0.0)) / MB)
        a2.plot(xs, ys, "o", color=C[i], mec="white", mew=1.0, ms=8)
        a2.plot(xm, ym, "s", mfc="none", mec=C[i], mew=1.3, ms=6)
    lim = np.array([3, 1500])
    a2.plot(lim, lim, color=MUTED, lw=1.1)
    a2.fill_between(lim, lim * 0.9, lim * 1.1, color=MUTED, alpha=0.12, lw=0)
    a2.set_xscale("log")
    a2.set_yscale("log")
    a2.set_xlim(*lim)
    a2.set_ylim(*lim)
    a2.set_xlabel("model pamięci [MB] (MemoryModel; MPI — rozszerzenie na procesy)")
    a2.set_ylabel("pomiar − narzut stały [MB]")
    a2.set_title("Model vs pomiar (pas ±10%): ● 1 wątek, □ suma po procesach MPI (p = 1–8)", fontsize=9.5)
    handles = [Line2D([], [], marker="o", ls="", color=C[i], ms=8, label=lab) for i, (_, lab, _) in
               enumerate(MEM_FAMILY)]
    a2.legend(handles=handles, fontsize=8.2, loc="upper left")
    fig.suptitle("Pamięć główna vs rozmiar siatki i model pamięci (MSVC)", y=1.02, fontsize=11)
    fig.tight_layout()
    save(fig, out, "etap12_pamiec_rozmiar.png")


# ---------------------------------------------------------------------------
# Część 2: skalowanie słabe, krzywa czasu na komórkę, przepustowość, fałszywe współdzielenie
# ---------------------------------------------------------------------------
WEAK = [("weak_classic_2d", "classic 2000 × 2000·p", "classic_2000x2000_s400_vn"),
        ("weak_mc_cb_2d", "MC szachownica 1000 × 1000·p", "mc_cb_2d_1000"),
        ("weak_lava_full", "lawa full 128 × 128·p × 64", "lava_duza_3d_full"),
        ("weak_lava_front", "lawa front 128 × 128·p × 64", "lava_duza_3d_front")]


def plot_weak(dir_: Path, out: Path) -> None:
    runs = {k: load(dir_, f"slabe_{k}.csv") for k in ("omp_msvc", "mpi_msvc", "omp_gcc", "mpi_gcc")}
    if runs["omp_msvc"] is None and runs["mpi_msvc"] is None:
        return
    z = load(dir_, "zestawienie.csv")
    style()
    fig, axes = plt.subplots(1, 4, figsize=(16, 4.6), sharey=True)
    for ax, (wid, title, strong) in zip(axes, WEAK):
        v8 = []
        for key, col, mk, ls, mfc in (("omp_msvc", OMP_C, "o", "-", None), ("mpi_msvc", MPI_C, "s", "-", None),
                                      ("omp_gcc", OMP_C, "o", "--", "white"), ("mpi_gcc", MPI_C, "s", "--", "white")):
            df = runs[key]
            if df is None:
                continue
            d = df[df["case"] == wid].sort_values("cores")
            ax.plot(d["cores"], d["Ew_norm"], ls=ls, marker=mk, color=col, mfc=mfc or col, mec=col if mfc else "white",
                    mew=1.2, lw=2.0 if ls == "-" else 1.3)
            r8 = d[d["cores"] == 8]
            if len(r8) and ls == "-":
                v8.append(float(r8["Ew_norm"].iloc[0]))
        for v, yl in zip(v8, spread(v8, 0.06)):  # etykiety przy 8 (MSVC), rozsunięte
            ax.text(8.25, yl, comma(v), fontsize=7.6, va="center", color=INK)
        if z is not None:  # silne skalowanie podobnego przypadku (etapy 9–10): E(p) fazy
            zs = z[(z["compiler"] == "msvc") & (z["case"] == strong)]
            for kind, stage, col in (("omp", 9, OMP_C), ("mpi", 10, MPI_C)):
                d = zs[(zs["kind"] == kind) & (zs["stage"] == stage) & ~zs["variant"].str.contains("changed") &
                       (zs["cores"] != 7)].sort_values("cores")
                ax.plot(d["cores"], d["E_phase"], ls=":", color=col, lw=1.4, alpha=0.9)
        ax.axhline(1.0, color=MUTED, ls="--", lw=1.1)
        ax.set_title(title, fontsize=9.5)
        ax.set_xticks([1, 2, 4, 6, 8])
        ax.set_xlim(0.6, 9.3)
        ax.set_ylim(0, 1.2)
        ax.set_xlabel("rdzenie P (p)")
    axes[0].set_ylabel("efektywność")
    handles = [Line2D([], [], marker="o", color=OMP_C, label="OpenMP, słabe E_w (MSVC)"),
               Line2D([], [], marker="s", color=MPI_C, label="MPI (typy pochodne), słabe E_w (MSVC)"),
               Line2D([], [], marker="o", ls="--", color=OMP_C, mfc="white", label="OpenMP, GCC"),
               Line2D([], [], marker="s", ls="--", color=MPI_C, mfc="white", label="MPI, GCC"),
               Line2D([], [], ls=":", color=INK2, label="silne E(p) podobnego przypadku (etapy 9–10)")]
    top_legend(fig, handles, 5, 1.0)
    fig.suptitle("Skalowanie słabe (Gustafson): przestrzeń p razy większa, E_w = T(1) / T(p) z czasu na komórkę × krok",
                 y=1.1, fontsize=11)
    fig.tight_layout()
    save(fig, out, "etap12_slabe.png")


CURVE_LABEL = {"classic_full": ("classic `full` (po kolei, 26 B / komórkę)", C[0]),
               "mc_random": ("MC random (losowo, 12 B / komórkę)", C[1]),
               "mc_cb": ("MC szachownica (po kolei w kolorach)", C[2])}


def plot_curve(dir_: Path, out: Path) -> None:
    runs = [(lab, load(dir_, f"krzywa_{k}.csv")) for k, lab in (("msvc", "MSVC"), ("gcc", "GCC (WSL)"))]
    runs = [(lab, d) for lab, d in runs if d is not None]
    if not runs:
        return
    style()
    fig, axes = plt.subplots(1, len(runs), figsize=(6.6 * len(runs), 5.0), sharey=True, squeeze=False)
    for ax, (lab, d) in zip(axes[0], runs):
        for curve, (cl, col) in CURVE_LABEL.items():
            dc = d[d["curve"] == curve].sort_values("cells")
            if not len(dc):
                continue
            ax.errorbar(dc["cells"], dc["ns_med"], yerr=[dc["ns_med"] - dc["ns_min"], dc["ns_max"] - dc["ns_med"]],
                        fmt="-o", color=col, mec="white", mew=1.0, capsize=2, lw=2.0, label=cl)
        # progi w liczbie komórek: pojemność L2 / L3 / bajty dotykane na komórkę w kroku (classic 26 B, MC 12 B)
        for bpc, col, yt in ((26, C[0], 0.97), (12, C[1], 0.90)):
            for b, t in CACHE_LINES[1:]:
                ax.axvline(b / bpc, color=col, ls="--", lw=1.0, alpha=0.8)
                ax.text(b / bpc * 1.08, yt, f"{t.split()[0]} ({bpc} B)", transform=ax.get_xaxis_transform(),
                        fontsize=7.6, color=INK2, va="top")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_ylim(0.6 * float(d["ns_min"].min()), 1.6 * float(d["ns_max"].max()))
        ax.set_xlabel("komórki siatki (skala log.)")
        ax.set_title(lab, fontsize=10)
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: comma(v, 0 if v >= 10 else 1)))
    axes[0][0].set_ylabel("ns na komórkę × krok albo na próbę MC (skala log.)")
    top_legend(fig, axes[0][0].get_legend_handles_labels()[0], 3, 1.0)
    fig.suptitle("Czas na jednostkę pracy vs rozmiar siatki (1 wątek, rdzeń P; mediana [min–max]); progi L2 2 MB / L3 36 MB"
                 " przeliczone na komórki", y=1.08, fontsize=11)
    fig.tight_layout()
    save(fig, out, "etap12_krzywa.png")


# Zapotrzebowanie na przepustowość przy 8 wątkach: przypadek skalowania słabego (jednostki / s przy p = 8) × bajty na
# jednostkę spoza L2 z cachegrind (chybienia L2 jądra × 64 B — górna granica ruchu z L3 / RAM dla siatki większej niż L3).
DEMAND = [("weak_classic_2d", "classic2d_vn", "classic (front)"), ("weak_mc_cb_2d", "mc_cb_2d", "MC szachownica"),
          ("weak_lava_full", "lava_full", "lawa full"), ("weak_lava_front", "lava_front", "lawa front")]


def plot_bandwidth(dir_: Path, out: Path) -> None:
    runs = [(lab, ls, load(dir_, f"przepustowosc_{k}.csv")) for k, lab, ls in (("msvc", "MSVC", "-"),
                                                                                ("gcc", "GCC (WSL)", "--"))]
    runs = [r for r in runs if r[2] is not None]
    if not runs:
        return
    style()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 5.2), gridspec_kw={"width_ratios": [1.0, 1.1]})
    kern = [("triad", C[0]), ("odczyt", C[1]), ("copy", C[2])]
    for lab, ls, d in runs:
        s = d[d["mode"] == "stream"]
        for k, col in kern:
            dk = s[s["kernel"] == k].sort_values("threads")
            a1.plot(dk["threads"], dk["best"] / 1000, ls=ls, marker="o", color=col, mec="white" if ls == "-" else col,
                    mfc=col if ls == "-" else "white", mew=1.0, lw=2.0 if ls == "-" else 1.3)
    weak = load(dir_, "slabe_omp_msvc.csv")
    cg = load(dir_, "cachegrind.csv")
    if weak is not None and cg is not None:
        per = cg_per_unit(cg)
        for i, (wid, cid, lab) in enumerate(DEMAND):
            r = weak[(weak["case"] == wid) & (weak["cores"] == 8)]
            if not len(r) or cid not in per:
                continue
            r = r.iloc[0]
            phase = "mcSim_med" if "mcSim_med" in r and pd.notna(r.get("mcSim_med")) else "caSim_med"
            units_s = float(r["cells"]) * float(r["work"]) / (float(r[phase]) / 1000.0)
            gbs = units_s * per[cid]["L2"] * 64 / 1e9
            a1.plot([8.35], [gbs], marker="_", ms=22, mew=2.5, color=INK2)
            a1.text(8.7, gbs, f"{lab}: {comma(gbs, 1)} GB/s", fontsize=7.8, va="center", color=INK)
    a1.set_xlim(0.6, 11.5)
    a1.set_xticks([1, 2, 4, 6, 8])
    a1.spines["bottom"].set_bounds(1, 8)
    a1.set_ylim(bottom=0)
    a1.set_xlabel("wątki (rdzenie P)")
    a1.set_ylabel("przepustowość [GB/s] (najlepsza z powtórzeń)")
    a1.set_title("STREAM, tablice 160 MB (RAM); kreski przy 8 — zapotrzebowanie CA / MC przy 8 wątkach", fontsize=9.5)
    handles = [Line2D([], [], color=c, marker="o", label=k) for k, c in kern] + \
              [Line2D([], [], color=INK2, ls=ls, label=lab) for lab, ls, _ in runs]
    a1.legend(handles=handles, fontsize=8.2, loc="upper left")
    lab, ls, d = runs[0]
    sz = d[d["mode"] == "sizes"]
    for (p, col) in ((1, C[0]), (8, C[1])):
        for k, mk in (("odczyt", "o"), ("triad", "s")):
            dk = sz[(sz["kernel"] == k) & (sz["threads"] == p)].sort_values("workingSetBytes")
            if len(dk):
                a2.plot(dk["workingSetBytes"] / MB, dk["best"] / 1000, marker=mk, ms=4.5, color=col,
                        ls="-" if k == "odczyt" else "--", lw=1.6, label=f"{k}, {p} {'wątek' if p == 1 else 'wątków'}")
    for b, t in CACHE_LINES:
        a2.axvline(b / MB, color=MUTED, ls="--", lw=1.0)
        a2.text(b / MB * 1.08, 0.97, t, transform=a2.get_xaxis_transform(), fontsize=7.8, color=INK2, va="top")
    a2.set_xscale("log")
    a2.set_xlabel("zbiór roboczy [MB] (skala log.)")
    a2.set_ylabel("przepustowość [GB/s]")
    a2.set_title(f"Przepustowość vs zbiór roboczy ({lab})", fontsize=9.5)
    a2.legend(fontsize=8.0, loc="center right")
    fig.suptitle("Przepustowość pamięci (mikrotest bandwidth, tryb oszczędny bez turbo) i zapotrzebowanie CA / MC",
                 y=1.02, fontsize=11)
    fig.tight_layout()
    save(fig, out, "etap12_przepustowosc.png")


def plot_false_sharing(dir_: Path, out: Path) -> None:
    runs = [(lab, ls, load(dir_, f"przepustowosc_{k}.csv")) for k, lab, ls in (("msvc", "MSVC", "-"),
                                                                                ("gcc", "GCC (WSL)", "--"))]
    runs = [r for r in runs if r[2] is not None]
    if not runs:
        return
    style()
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
    panels = [("licznik atomowy (fetch_add)", "licznik atomowy co 8 B", "licznik atomowy co 64 B"),
              ("licznik zapisywany w każdej iteracji", "licznik (zapis) co 8 B", "licznik (zapis) co 64 B"),
              ("listy warstw (push_back, static,1)", "listy warstw: nagłówki 96 B", "listy warstw: nagłówki co 128 B")]
    for ax, (title, bad, good) in zip(axes, panels):
        for lab, ls, d in runs:
            f = d[d["mode"] == "false"]
            for k, col, name in ((bad, MPI_C, "sąsiednie (jedna linia 64 B)"), (good, OMP_C, "osobne linie")):
                dk = f[f["kernel"] == k].sort_values("threads")
                ax.plot(dk["threads"], dk["median"], ls=ls, marker="o", color=col, mfc=col if ls == "-" else "white",
                        mec="white" if ls == "-" else col, lw=2.0 if ls == "-" else 1.3)
        ax.set_title(title, fontsize=9.5)
        ax.set_xticks([1, 2, 4, 6, 8])
        ax.set_xlabel("wątki")
        ax.set_ylim(bottom=0)
    axes[0].set_ylabel("ns na operację (mediana)")
    handles = [Line2D([], [], color=MPI_C, marker="o", label="dane wątków w jednej linii (co 8 B / nagłówki 96 B)"),
               Line2D([], [], color=OMP_C, marker="o", label="dane wątków w osobnych liniach (co 64 B / 128 B)")] + \
              [Line2D([], [], color=INK2, ls=ls, label=lab) for lab, ls, _ in runs]
    top_legend(fig, handles, 4, 1.0)
    fig.suptitle("Fałszywe współdzielenie (mikrotest bandwidth --mode false)", y=1.1, fontsize=11)
    fig.tight_layout()
    save(fig, out, "etap12_falszywe.png")


PLOTS = {"skalowanie": plot_scaling, "schodki": plot_steps, "cachegrind": plot_cachegrind,
         "pamiec": lambda d, o: (plot_memory_p(d, o), plot_memory_size(d, o)), "slabe": plot_weak,
         "krzywa": plot_curve, "przepustowosc": plot_bandwidth, "falszywe": plot_false_sharing}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=str(ROOT / "bench" / "results" / "testy"))
    ap.add_argument("--out", default=str(ROOT / "docs" / "img"))
    ap.add_argument("--only", help=f"wybrane wykresy po przecinku ({', '.join(PLOTS)})")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    dir_, out = Path(args.dir), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name in (args.only.split(",") if args.only else PLOTS):
        print(name)
        PLOTS[name.strip()](dir_, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
