#!/usr/bin/env python3
"""Wykresy etapu 10 (MPI) -> docs/img/etap10_*.png z wyników bench/scaling_mpi.py (bench/results/mpi/).

Użycie (z katalogu volcano-ca-mc):
    python bench/plot_etap10.py
    python bench/plot_etap10.py --msvc skalowanie_mpi_msvc --gcc skalowanie_mpi_gcc --dir bench/results/mpi

Wykresy:
    etap10_podzial.png       schemat: pasy warstw między 3 procesy, okna procesów z warstwami brzegowymi (lawa 17 pod
                             pasem + 1 nad; classic i MC po 1) i komunikaty jednej wymiany
    etap10_skalowanie.png    przyspieszenie S(p) i efektywność E(p) fazy obliczeń (caSim / mcSim), p procesów, MSVC
    etap10_amdahl.png        S(p) całego przebiegu (total) i krzywe prawa Amdahla z dopasowaną częścią szeregową f
    etap10_mpi_omp.png       MPI (p procesów) vs OpenMP (p wątków) przy 4 i 8 rdzeniach P, MSVC i GCC; kontrolnie
                             OpenMP z etapu 9 (bench/results/omp/skalowanie_{msvc,gcc}.csv)
    etap10_hybryda.png       8 rdzeni: procesy × wątki (8 × 1, 4 × 2, 2 × 4, 1 × 8 = OpenMP), MSVC i GCC
    etap10_komunikacja.png   udział komunikacji w czasie fazy w funkcji p: wymiana warstw + MPI_Allreduce
    etap10_obciazenie.png    czas obliczeń każdego procesu (pasa) w lawie przy 4 i 8 procesach, dla porównania
                             classic 300³ (równa praca na pas — widać tylko wolniejszy procesor 0)
    etap10_wymiana.png       mpi.exchange: changed / always — bajty na wymianę i czas fazy przy 4 i 8 procesach
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from plot_etap9 import CASES, COLOR, GROUPS, LABEL, MARKER, MUTED, SHORT, comma  # noqa: E402
from plot_profile import C, INK, INK2, save, style  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PS = [1, 2, 3, 4, 6, 7, 8]  # liczby procesów m<p> w pomiarze MSVC (m7 — bez procesora 0)


def load(dir_: Path, name: str | None) -> pd.DataFrame | None:
    if not name:
        return None
    p = dir_ / f"{name}.csv"
    if not p.exists():
        print(f"  (brak {p} — pomijam)")
        return None
    df = pd.read_csv(p)
    df["phase_med"] = [r[f"{r['phase']}_med"] for _, r in df.iterrows()]
    return df


def load_raw(dir_: Path, name: str) -> pd.DataFrame | None:
    """Surowe przebiegi: <nazwa>_raw.csv albo części <nazwa>_cz*_raw.csv (pomiar w częściach, --from-raw)."""
    files = sorted(dir_.glob(f"{name}_raw.csv")) or sorted(dir_.glob(f"{name}_cz*_raw.csv"))
    return pd.concat([pd.read_csv(f) for f in files], ignore_index=True) if files else None


def get(df: pd.DataFrame, case: str, variant: str, col: str) -> float:
    r = df[(df["case"] == case) & (df["variant"] == variant)]
    return float(r.iloc[0][col]) if not r.empty and col in r.columns and pd.notna(r.iloc[0][col]) else np.nan


def present(df: pd.DataFrame) -> list[str]:
    have = set(df["case"])
    return [c for c, _ in CASES if c in have]


def group_cases(df: pd.DataFrame) -> list[tuple[str, list[str]]]:
    cases = present(df)
    grp = dict(zip(df["case"], df["group"]))
    return [(title, [c for c in cases if grp.get(c) == g]) for g, title in GROUPS
            if any(grp.get(c) == g for c in cases)]


def mpi_points(df: pd.DataFrame, case: str, col: str) -> tuple[list[int], list[float]]:
    """Punkty m<p> (czyste MPI, 1 wątek na proces) w kolejności p."""
    d = df[(df["case"] == case) & (df["variant"].str.fullmatch(r"m\d+"))].copy()
    d["p"] = d["procs"].astype(int)
    d = d.sort_values("p")
    return list(d["p"]), list(d[col])


def ideal_axes(ax: plt.Axes, kind: str) -> None:
    ps = np.arange(1, 9)
    if kind == "S":
        ax.plot(ps, ps, color=MUTED, linestyle="--", linewidth=1.2, label="idealnie (S = p)")
        ax.set_ylim(0, 8.5)
        ax.set_ylabel("przyspieszenie S(p) = T(1) / T(p)")
    else:
        ax.axhline(1.0, color=MUTED, linestyle="--", linewidth=1.2, label="idealnie (E = 1)")
        ax.set_ylim(0, 1.15)
        ax.set_ylabel("efektywność E(p) = S(p) / p")
    ax.set_xlim(0.7, 8.3)
    ax.set_xticks(PS)
    ax.set_xlabel("liczba procesów p (rdzenie P)")


# ---------------------------------------------------------------------------
# Schemat podziału
# ---------------------------------------------------------------------------
def plot_partition(out: Path) -> None:
    """Pasy warstw między 3 procesy (48 warstw jak test_3d, po 16 na proces) i okna procesów: warstwy własne
    + warstwy brzegowe. Lawa czyta do 17 warstw pod pasem (dropDepth do 16 poziomów + hasSupport), więc okno
    procesu 2 sięga przez cały pas procesu 1 aż do warstwy procesu 0; classic i MC — po 1 warstwie z każdej strony."""
    style()
    nz, p, below, above = 48, 3, 17, 1
    lo = [r * nz // p for r in range(p)]
    hi = [(r + 1) * nz // p for r in range(p)]
    owner = lambda z: next(r for r in range(p) if lo[r] <= z < hi[r])  # noqa: E731
    pcol = [C[0], C[2], C[6]]

    fig, axes = plt.subplots(1, 3, figsize=(15.5, 6.6), gridspec_kw={"width_ratios": [1.35, 1.0, 0.75]})

    # (a) przekrój x–z przestrzeni: teren, lawa, pasy procesów.
    ax = axes[0]
    nx = 56
    h = [max(2, int(34 - abs(x - 24) * 1.25)) for x in range(nx)]
    for x in (23, 24, 25):
        h[x] = 31
    for z in range(nz):
        ax.add_patch(plt.Rectangle((-0.5, z - 0.5), nx, 1, color=pcol[owner(z)], alpha=0.16, linewidth=0))
    for x in range(nx):
        ax.add_patch(plt.Rectangle((x - 0.5, -0.5), 1, h[x], facecolor="#9b9890", edgecolor="none"))
    for x in range(24, 46):  # lawa spływa po prawym zboczu (warstwa nad skałą)
        ax.add_patch(plt.Rectangle((x - 0.5, h[x] - 0.5), 1, 1, facecolor="#b33a10", edgecolor="none"))
    ax.add_patch(plt.Rectangle((22.5, 30.5), 3, 1, facecolor="#b33a10", edgecolor="none"))
    for r in range(1, p):
        ax.axhline(lo[r] - 0.5, color=INK, linewidth=1.3)
    for r in range(p):
        ax.text(nx + 0.3, (lo[r] + hi[r] - 1) / 2, f"proces {r}\nwarstwy {lo[r]}–{hi[r] - 1}", va="center",
                ha="left", fontsize=8.5, color=INK)
    ax.set_xlim(-0.5, nx + 9)
    ax.set_ylim(-0.5, nz - 0.5)
    ax.set_xticks([])
    ax.set_yticks([0, 16, 32, 47])
    ax.set_ylabel("warstwa z (globalnie)")
    ax.set_xlabel("x")
    ax.grid(False)
    ax.set_title("(a) przestrzeń: równe pasy warstw z (48 warstw, 3 procesy)", color=INK2)

    # (b), (c) okna procesów: warstwy własne i brzegowe, kolor = proces-właściciel warstwy.
    def window(ax: plt.Axes, nb: int, na: int, deep: bool, title: str) -> None:
        for r in range(p):
            x0 = r * 1.5
            zs = range(max(0, lo[r] - nb), min(nz, hi[r] + na))
            for z in zs:
                own = lo[r] <= z < hi[r]
                o = owner(z)
                if own:
                    ax.add_patch(plt.Rectangle((x0, z), 1, 1, facecolor=pcol[o], edgecolor="white", lw=0.5))
                else:
                    full = (z == lo[r] - 1) or (z >= hi[r]) or not deep
                    ax.add_patch(plt.Rectangle((x0, z), 1, 1, facecolor=pcol[o], alpha=0.55 if full else 0.22,
                                               edgecolor=INK if full else "white", lw=0.8 if full else 0.4,
                                               hatch="////" if full else "..."))
            ax.text(x0 + 0.5, -2.4, f"proces {r}", ha="center", fontsize=8.5, color=INK)
            n_ghost = len(zs) - (hi[r] - lo[r])
            ax.text(x0 + 0.5, min(nz, hi[r] + na) + 0.6, f"okno: {len(zs)}\n({n_ghost} brzeg.)", ha="center",
                    fontsize=7.5, color=INK2)
        ax.set_xlim(-0.4, p * 1.5 - 0.1)
        ax.set_ylim(-3.2, nz + 4.5)
        ax.set_xticks([])
        ax.set_yticks([0, 16, 32, 47])
        ax.grid(False)
        ax.set_title(title, color=INK2)

    window(axes[1], below, above, True, "(b) lawa: okna procesów — 17 warstw pod pasem, 1 nad")
    axes[1].annotate("17 pod pasem\nprocesu 2:\n16 od procesu 1\n+ 1 od procesu 0", xy=(3.5, 15.5), xytext=(3.0, 4.0),
                     fontsize=7.8, color=INK, arrowprops=dict(arrowstyle="->", color=INK, lw=0.9))
    window(axes[2], 1, 1, False, "(c) classic i MC: po 1 warstwie")
    handles = [plt.Rectangle((0, 0), 1, 1, facecolor=C[0]),
               plt.Rectangle((0, 0), 1, 1, facecolor=C[0], alpha=0.55, edgecolor=INK, hatch="////"),
               plt.Rectangle((0, 0), 1, 1, facecolor=C[0], alpha=0.22, edgecolor="white", hatch="...")]
    fig.legend(handles, ["warstwy własne (reguły liczą tylko je)",
                         "warstwa brzegowa — pełny stan (lawa: typ, flowId, temperatura — 9 B na komórkę)",
                         "głębsza warstwa brzegowa lawy — sam typ (1 B na komórkę; czyta ją tylko dropDepth)"],
               loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.06), fontsize=8.3)
    fig.suptitle("Podział na pasy z warstwami brzegowymi (ghost). Kolor = proces, którego warstwa jest kopiowana. "
                 "Lawa, 3 procesy: 5 komunikatów na krok (0→1, 1→2, 0→2 pod pasy; 1→0, 2→1 nad pasy)", y=1.0)
    fig.tight_layout()
    save(fig, out, "etap10_podzial.png")


# ---------------------------------------------------------------------------
# Skalowanie i Amdahl
# ---------------------------------------------------------------------------
def plot_scaling(df: pd.DataFrame, out: Path, compiler: str) -> None:
    style()
    groups = group_cases(df)
    fig, axes = plt.subplots(2, len(groups), figsize=(4.3 * len(groups), 7.4), squeeze=False)
    for j, (title, cases) in enumerate(groups):
        a1, a2 = axes[0][j], axes[1][j]
        for cid in cases:
            ps, s = mpi_points(df, cid, "S_phase")
            _, e = mpi_points(df, cid, "E_phase")
            kw = dict(color=COLOR[cid], marker=MARKER[cid], markersize=6, linewidth=2, label=LABEL[cid])
            a1.plot(ps, s, **kw)
            a2.plot(ps, e, **kw)
        ideal_axes(a1, "S")
        ideal_axes(a2, "E")
        a1.set_title(title, color=INK2)
        a1.legend(loc="upper left", fontsize=8)
        if j > 0:
            a1.set_ylabel("")
            a2.set_ylabel("")
    fig.suptitle(f"Skalowanie fazy obliczeń (caSim / mcSim), MPI {compiler}: S(p) i E(p) — mediana z ≥ 5 powtórzeń, "
                 "proces r na rdzeniu P (p = 7: bez procesora 0, p = 8: z nim)", y=1.0)
    fig.tight_layout()
    save(fig, out, "etap10_skalowanie.png")


def plot_amdahl(df: pd.DataFrame, out: Path, compiler: str) -> None:
    style()
    groups = group_cases(df)
    fig, axes = plt.subplots(1, len(groups), figsize=(4.3 * len(groups), 4.6), squeeze=False)
    pp = np.linspace(1, 8, 50)
    for j, (title, cases) in enumerate(groups):
        ax = axes[0][j]
        for cid in cases:
            ps, s = mpi_points(df, cid, "S_total")
            f = get(df, cid, "m1", "amdahl_f_total")
            pts = dict(color=COLOR[cid], marker=MARKER[cid], markersize=7, markeredgecolor="white",
                       markeredgewidth=1.2)
            if np.isfinite(f) and f < 0.999:
                ax.plot(pp, 1 / (f + (1 - f) / pp), color=COLOR[cid], linewidth=2,
                        label=f"{LABEL[cid]}: f = {comma(f, 3)}")
                ax.plot(ps, s, linestyle="none", **pts)
            else:  # S(p) < 1 — wersja rozproszona wolniejsza; prawo Amdahla (S ≥ 1) tego nie opisuje
                ax.plot(ps, s, linestyle=":", linewidth=1.3, label=f"{LABEL[cid]}: S < 1 (bez dopasowania)", **pts)
        ideal_axes(ax, "S")
        ax.set_title(title, color=INK2)
        ax.legend(loc="upper left", fontsize=8)
        if j > 0:
            ax.set_ylabel("")
    fig.suptitle(f"Cały przebieg (total), MPI {compiler}: zmierzone S(p) (punkty) i prawo Amdahla "
                 "S(p) = 1 / (f + (1 − f)/p) z dopasowaną częścią szeregową f (linia)", y=1.0)
    fig.tight_layout()
    save(fig, out, "etap10_amdahl.png")


# ---------------------------------------------------------------------------
# MPI vs OpenMP, hybryda
# ---------------------------------------------------------------------------
def plot_mpi_omp(msvc: pd.DataFrame, gcc: pd.DataFrame | None, omp9: dict, out: Path) -> None:
    """S fazy: p procesów MPI vs p wątków OpenMP w tym samym przebiegu; romb — OpenMP z etapu 9 (kontrola)."""
    style()
    panels = [(msvc, "MSVC / MS-MPI", 4, "msvc"), (msvc, "MSVC / MS-MPI", 8, "msvc")]
    if gcc is not None:
        panels.append((gcc, "GCC / OpenMPI (WSL)", 8, "gcc"))
    cases = present(msvc)
    fig, axes = plt.subplots(1, len(panels), figsize=(5.4 * len(panels), 4.6), sharey=True, squeeze=False)
    for ax, (df, name, p, comp) in zip(axes[0], panels):
        x = np.arange(len(cases))
        bars = [(f"m{p}", f"MPI: {p} procesów", C[0]), (f"o{p}", f"OpenMP: {p} wątków", C[1])]
        for i, (v, lab, color) in enumerate(bars):
            vals = [get(df, c, v, "S_phase") for c in cases]
            ax.bar(x + (i - 0.5) * 0.38, vals, width=0.36, color=color, label=lab)
            for xi, val in zip(x, vals):
                if np.isfinite(val):
                    ax.text(xi + (i - 0.5) * 0.38, val + 0.08, comma(val, 1), ha="center", fontsize=7.3, color=INK)
        ref = omp9.get(comp)
        if ref is not None:
            vals = [get_omp9(ref, c, p) for c in cases]
            ax.plot(x + 0.47, vals, linestyle="none", marker="D", markersize=5, color=INK, markerfacecolor="white",
                    label=f"OpenMP etap 9 ({p} wątków, binarka e9)")
        ax.axhline(p, color=MUTED, linestyle="--", linewidth=1.2, label=f"idealnie (S = {p})")
        ax.set_ylim(0, 10.2)
        ax.set_xticks(x)
        ax.set_xticklabels([SHORT.get(c, c) for c in cases], fontsize=7.5)
        ax.set_title(f"{name} — {p} rdzenie P" if p == 4 else f"{name} — {p} rdzeni P", color=INK2)
        ax.grid(axis="x", visible=False)
        ax.legend(loc="upper left", fontsize=7.5, ncol=2)
    axes[0][0].set_ylabel("przyspieszenie fazy S = T(1) / T")
    fig.suptitle("MPI (pamięć rozproszona, pasy stałe) vs OpenMP (pamięć wspólna, harmonogram etapu 9) przy tej samej "
                 "liczbie rdzeni — S fazy obliczeń od wspólnego T(1)", y=1.0)
    fig.tight_layout()
    save(fig, out, "etap10_mpi_omp.png")


def get_omp9(df: pd.DataFrame, case: str, threads: int) -> float:
    r = df[(df["case"] == case) & (df["threads"] == threads)]
    return float(r.iloc[0]["S_phase"]) if not r.empty else np.nan


def plot_hybrid(msvc: pd.DataFrame, gcc: pd.DataFrame | None, out: Path) -> None:
    """8 rdzeni: 8 procesów × 1 wątek … 1 proces × 8 wątków (engine z OpenMP)."""
    style()
    configs = [("m8", "8 × 1"), ("h4x2", "4 × 2"), ("h2x4", "2 × 4"), ("o8", "1 × 8\n(OpenMP)")]
    rows = [(msvc, "MSVC / MS-MPI")] + ([(gcc, "GCC / OpenMPI")] if gcc is not None else [])
    groups = group_cases(msvc)
    fig, axes = plt.subplots(len(rows), len(groups), figsize=(4.3 * len(groups), 3.7 * len(rows)), squeeze=False,
                             sharey=True)
    for i, (df, name) in enumerate(rows):
        for j, (title, cases) in enumerate(groups):
            ax = axes[i][j]
            for cid in cases:
                xs, ys = [], []
                for k, (v, _) in enumerate(configs):
                    val = get(df, cid, v, "S_phase")
                    if np.isfinite(val):
                        xs.append(k)
                        ys.append(val)
                ax.plot(xs, ys, color=COLOR[cid], marker=MARKER[cid], markersize=6, linewidth=2, label=LABEL[cid])
            ax.axhline(8, color=MUTED, linestyle="--", linewidth=1.2)
            ax.set_ylim(0, 8.5)
            ax.set_xticks(range(len(configs)))
            ax.set_xticklabels([c for _, c in configs], fontsize=8)
            ax.set_title(f"{title} — {name}", color=INK2, fontsize=9.5)
            if j == 0:
                ax.set_ylabel("S fazy przy 8 rdzeniach")
            if i == len(rows) - 1:
                ax.set_xlabel("procesy MPI × wątki OpenMP na proces")
            ax.legend(loc="upper left", bbox_to_anchor=(0.0, 0.93), fontsize=7.5)
    fig.suptitle("Tryb hybrydowy na 8 rdzeniach P: mniej pasów (mniej warstw brzegowych, mniejsza nierównomierność) "
                 "vs więcej wątków w procesie (GCC: bez 4 × 2)", y=1.0)
    fig.tight_layout()
    save(fig, out, "etap10_hybryda.png")


# ---------------------------------------------------------------------------
# Komunikacja, nierównomierność, wymiana always / changed
# ---------------------------------------------------------------------------
def plot_comm(df: pd.DataFrame, out: Path) -> None:
    style()
    groups = group_cases(df)
    fig, axes = plt.subplots(1, len(groups), figsize=(4.3 * len(groups), 4.3), squeeze=False, sharey=True)
    for j, (title, cases) in enumerate(groups):
        ax = axes[0][j]
        for cid in cases:
            ps, share = mpi_points(df, cid, "comm_share")
            _, halo = mpi_points(df, cid, "haloAvg_med")
            _, ph = mpi_points(df, cid, "phase_med")
            ps, share, halo, ph = ps[1:], share[1:], halo[1:], ph[1:]  # bez p = 1 (brak komunikacji)
            ax.plot(ps, [100 * s for s in share], color=COLOR[cid], marker=MARKER[cid], markersize=6, linewidth=2,
                    label=LABEL[cid])
            ax.plot(ps, [100 * h / t for h, t in zip(halo, ph)], color=COLOR[cid], linewidth=1.3, linestyle=":")
        ax.set_xticks(PS[1:])
        ax.set_xlim(1.6, 8.4)
        ax.set_ylim(0, 100)
        ax.set_xlabel("liczba procesów p")
        ax.set_title(title, color=INK2)
        ax.legend(loc="upper left", fontsize=8)
        if title.startswith("MC"):
            ax.text(0.03, 0.70, "MC nie ma MPI_Allreduce w MCS — czekanie na wolniejszy\npas wlicza się do wymiany "
                    "(MPI_Waitall po kolorze);\nlinie ciągła i kropkowana się pokrywają", transform=ax.transAxes,
                    fontsize=7.6, color=INK2, va="top")
    axes[0][0].set_ylabel("udział w czasie fazy [%] (średnia po procesach)")
    fig.suptitle("Komunikacja w fazie obliczeń: linia ciągła — wymiana warstw + MPI_Allreduce (z czekaniem na "
                 "najwolniejszy pas), kropkowana — sama wymiana warstw", y=1.0)
    fig.tight_layout()
    save(fig, out, "etap10_komunikacja.png")


def per_rank(raw: pd.DataFrame, case: str, variant: str) -> tuple[np.ndarray, list[str]]:
    rr = raw[(raw["case"] == case) & (raw["variant"] == variant)]
    if rr.empty:
        return np.array([]), []
    work = np.median(np.array([[float(x) for x in str(s).split()] for s in rr["computePerRank"]]), axis=0)
    cpus = str(rr.iloc[0]["cpus"]).split()
    return work, cpus


def plot_load(df: pd.DataFrame, raw: pd.DataFrame, out: Path) -> None:
    style()
    cases = [c for c in ("lava_etna_real", "lava_duza_3d_front", "lava_duza_3d_full", "classic_300x300x300_s100_vn")
             if c in set(raw["case"])]
    variants = ["m4", "m8"]
    fig, axes = plt.subplots(len(variants), len(cases), figsize=(4.1 * len(cases), 6.6), squeeze=False)
    for i, v in enumerate(variants):
        for j, cid in enumerate(cases):
            ax = axes[i][j]
            work, cpus = per_rank(raw, cid, v)
            if not len(work):
                ax.set_visible(False)
                continue
            phase = get(df, cid, v, "phase_med")
            colors = [C[3] if c == "0" else COLOR[cid] for c in cpus]
            bars = ax.bar(np.arange(len(work)), work, color=colors, width=0.7)
            for b, c in zip(bars, cpus):
                if c == "0":
                    b.set_hatch("///")  # drugie kodowanie (nie tylko kolor)
                    b.set_edgecolor("white")
            ax.axhline(phase, color=INK, linestyle="--", linewidth=1.1, label=f"czas fazy {comma(phase, 0)} ms")
            ax.set_xticks(np.arange(len(work)))
            ax.set_xticklabels([f"{r}\nCPU {c}" for r, c in enumerate(cpus)], fontsize=7)
            imb = get(df, cid, v, "imbalance")
            ax.set_title(f"{LABEL[cid]}, {v[1:]} procesy — nierówność ×{comma(imb)}" if v == "m4" else
                         f"{LABEL[cid]}, {v[1:]} procesów — ×{comma(imb)}", color=INK2, fontsize=8.8)
            ax.set_ylim(0, max(phase, work.max()) * 1.25)
            ax.legend(loc="upper right", fontsize=7.5)
            ax.grid(axis="x", visible=False)
            if j == 0:
                ax.set_ylabel("czas obliczeń procesu [ms]")
            if i == len(variants) - 1:
                ax.set_xlabel("proces (pas od dołu) i jego procesor")
    fig.suptitle("Nierównomierność obciążenia pasów (mediana z powtórzeń; nierówność = maks / średnia). Lawa spływa po "
                 "dolnych warstwach; żółty, kreskowany — proces na procesorze 0 (przerwania systemu)", y=1.0)
    fig.tight_layout()
    save(fig, out, "etap10_obciazenie.png")


def plot_exchange(df: pd.DataFrame, out: Path) -> None:
    style()
    cases = [c for c in present(df) if np.isfinite(get(df, c, "c4", "phase_med"))]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.4))
    x = np.arange(len(cases))
    for ax, (col, ylabel, title) in zip(axes, (
            ("bytesPerExchange_med", "bajty na wymianę: changed / always [%]", "bajty jednej wymiany"),
            ("phase_med", "czas fazy: changed / always [%]", "czas fazy obliczeń"))):
        for i, (p, color) in enumerate(((4, C[0]), (8, C[1]))):
            vals = [100 * get(df, c, f"c{p}", col) / get(df, c, f"m{p}", col) for c in cases]
            ax.bar(x + (i - 0.5) * 0.38, vals, width=0.36, color=color, label=f"{p} procesów")
            for xi, val in zip(x, vals):
                ax.text(xi + (i - 0.5) * 0.38, val + 1.5, comma(val, 0) + "%", ha="center", fontsize=7, color=INK)
        ax.axhline(100, color=MUTED, linestyle="--", linewidth=1.2, label="always (100%)")
        ax.set_ylim(0, 140)
        ax.set_yticks(range(0, 101, 20))
        ax.set_xticks(x)
        labels = [SHORT.get(c, c) for c in cases]
        if col == "bytesPerExchange_med":  # bajty always: 4 / 8 procesów
            labels = [f"{lab}\n4: {comma(get(df, c, 'm4', col) / 1e6)} MB\n8: {comma(get(df, c, 'm8', col) / 1e6)} MB"
                      for lab, c in zip(labels, cases)]
        ax.set_xticklabels(labels, fontsize=7.5)
        ax.set_ylabel(ylabel)
        ax.set_title(title + (" (pod nazwą: always przy 4 / 8 procesach)" if col == "bytesPerExchange_med" else ""),
                     color=INK2)
        ax.grid(axis="x", visible=False)
        ax.legend(loc="upper left", fontsize=7.8, ncol=3)
    fig.suptitle("mpi.exchange = changed (warstwa wysyłana tylko po zmianie) względem always — MSVC / MS-MPI", y=1.0)
    fig.tight_layout()
    save(fig, out, "etap10_wymiana.png")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dir", default=str(ROOT / "bench" / "results" / "mpi"), help="folder wyników scaling_mpi.py")
    ap.add_argument("--msvc", default="skalowanie_mpi_msvc", help="nazwa pomiaru MSVC (<nazwa>.csv)")
    ap.add_argument("--gcc", default="skalowanie_mpi_gcc", help="nazwa pomiaru GCC")
    ap.add_argument("--omp-dir", default=str(ROOT / "bench" / "results" / "omp"), help="wyniki OpenMP etapu 9")
    ap.add_argument("--out", default=str(ROOT / "docs" / "img"), help="folder wykresów")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    d, out = Path(args.dir), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    plot_partition(out)
    msvc, gcc = load(d, args.msvc), load(d, args.gcc)
    omp9 = {k: pd.read_csv(p) for k, p in (("msvc", Path(args.omp_dir) / "skalowanie_msvc.csv"),
                                            ("gcc", Path(args.omp_dir) / "skalowanie_gcc.csv")) if p.exists()}
    if msvc is not None:
        plot_scaling(msvc, out, "MSVC / MS-MPI")
        plot_amdahl(msvc, out, "MSVC / MS-MPI")
        plot_mpi_omp(msvc, gcc, omp9, out)
        plot_hybrid(msvc, gcc, out)
        plot_comm(msvc, out)
        plot_exchange(msvc, out)
        raw = load_raw(d, args.msvc)
        if raw is not None:
            plot_load(msvc, raw, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
