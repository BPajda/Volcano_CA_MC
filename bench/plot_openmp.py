#!/usr/bin/env python3
"""Wykresy wersji OpenMP -> docs/img/openmp_*.png z wyników bench/scaling.py (bench/results/omp/).

Użycie (z katalogu volcano-ca-mc):
    python bench/plot_openmp.py
    python bench/plot_openmp.py --msvc skalowanie_msvc --gcc skalowanie_gcc --sched harmonogramy_msvc --dir bench/results/omp

Wykresy:
    openmp_podzial.png       schemat: warstwy z między wątki (static vs static,1) z frontem lawy; kolory szachownicy
    openmp_skalowanie.png    przyspieszenie S(p) i efektywność E(p) fazy obliczeń (caSim / mcSim) z linią idealną, MSVC
    openmp_amdahl.png        S(p) całego przebiegu (total) i krzywe prawa Amdahla z dopasowaną częścią szeregową f
    openmp_harmonogramy.png  czas fazy przy 8 wątkach dla harmonogramów static / dynamic / guided (z porcjami)
    openmp_watki.png         czas pracy każdego wątku (--thread-stats) w lawie: równe pasy (static) vs na zmianę
                             (static,1) vs dynamic, czyli nierównomierność obciążenia
    openmp_szeregowe.png     udział faz w czasie całego przebiegu przy 1 i 8 wątkach (części szeregowe rosną)
    openmp_msvc_gcc.png      S(8) fazy i całości: MSVC (vcomp) vs GCC (libgomp, WSL)
Walidacja szachownicy MC (openmp_mc_walidacja.png) rysuje bench/mc_validation.py.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from plot_profile import C, GRID, INK, INK2, save, style  # noqa: E402  (paleta i styl wykresów projektu)

ROOT = Path(__file__).resolve().parent.parent
MUTED = "#898781"  # linia idealna / odniesienie — neutralna szarość

# Przypadki w stałej kolejności (kolor = przypadek, ten sam na wszystkich wykresach).
CASES = [
    ("lava_etna_real", "lawa: Etna (automat frontalny)"),
    ("lava_duza_3d_front", "lawa 128×128×64 (automat frontalny)"),
    ("lava_duza_3d_full", "lawa 128×128×64 (pełny przebieg)"),
    ("classic_2000x2000_s400_vn", "rozrost ziaren 2000×2000"),
    ("classic_300x300x300_s100_vn", "rozrost ziaren 300×300×300"),
    ("mc_cb_2d_1000", "Monte Carlo 1000×1000 (szachownica)"),
    ("mc_cb_3d_100", "Monte Carlo 100×100×100 (szachownica)"),
]
COLOR = {cid: C[i % len(C)] for i, (cid, _) in enumerate(CASES)}
LABEL = dict(CASES)
# Znacznik = drugie kodowanie przypadku (kolory 7 przypadków nie są rozróżnialne parami przy daltonizmie, więc
# wykresy linii są dzielone na grupy po ≤ 3 przypadki, a znacznik odróżnia przypadki także bez koloru).
MARKER = dict(zip((c for c, _ in CASES), ["o", "s", "^", "o", "s", "o", "s"]))
GROUPS = [("ca_lava", "lawa (automat komórkowy)"), ("ca_classic", "rozrost ziaren (automat komórkowy)"),
          ("mc", "Monte Carlo (szachownica)")]
# Faza obliczeń przypadku po polsku (kolumna phase w CSV: caSim / mcSim).
PHASE = {"caSim": "faza automatu", "mcSim": "faza Monte Carlo"}
# Krótkie podpisy osi X (wykres MSVC vs GCC).
SHORT = {"lava_etna_real": "lawa: Etna\nfrontalny", "lava_duza_3d_front": "lawa 3D\n128²×64\nfrontalny",
         "lava_duza_3d_full": "lawa 3D\n128²×64\npełny", "classic_2000x2000_s400_vn": "rozrost\nziaren\n2000²",
         "classic_300x300x300_s100_vn": "rozrost\nziaren\n300³", "mc_cb_2d_1000": "Monte\nCarlo\n1000²",
         "mc_cb_3d_100": "Monte\nCarlo\n100³"}
SECTIONS = ["readConfig", "allocate", "terrain", "vents", "caSim", "caStats", "save", "mcInit", "mcSim", "mcStats",
            "mcSave"]


def comma(v: float, digits: int = 2) -> str:
    return f"{v:.{digits}f}".replace(".", ",")


def load(dir_: Path, name: str | None) -> pd.DataFrame | None:
    if not name:
        return None
    p = dir_ / f"{name}.csv"
    if not p.exists():
        print(f"  (brak {p}, pomijam)")
        return None
    return pd.read_csv(p)


def present(df: pd.DataFrame) -> list[str]:
    """Przypadki z wieloma liczbami wątków, w stałej kolejności CASES."""
    have = {c for c, g in df.groupby("case") if g["threads"].nunique() > 1}
    return [c for c, _ in CASES if c in have]


def ideal_axes(ax: plt.Axes, pmax: int, kind: str) -> None:
    ps = np.arange(1, pmax + 1)
    if kind == "S":
        ax.plot(ps, ps, color=MUTED, linestyle="--", linewidth=1.2, label="idealnie (S = p)")
        ax.set_ylim(0, pmax + 0.5)
        ax.set_ylabel("przyspieszenie S(p) = T(1) / T(p)")
    else:
        ax.axhline(1.0, color=MUTED, linestyle="--", linewidth=1.2, label="idealnie (E = 1)")
        ax.set_ylim(0, 1.15)
        ax.set_ylabel("efektywność E(p) = S(p) / p")
    ax.set_xlim(0.7, pmax + 0.3)
    ax.set_xticks([1, 2, 4, 6, 8])
    ax.set_xlabel("liczba wątków p (rdzenie P)")


def group_cases(df: pd.DataFrame) -> list[tuple[str, list[str]]]:
    """Grupy (lawa / classic / MC) z przypadkami obecnymi w pomiarze — jeden panel na grupę."""
    cases = present(df)
    grp = dict(zip(df["case"], df["group"]))
    return [(title, [c for c in cases if grp.get(c) == g]) for g, title in GROUPS
            if any(grp.get(c) == g for c in cases)]


def plot_scaling(df: pd.DataFrame, out: Path, compiler: str) -> None:
    """S(p) (górny rząd) i E(p) (dolny rząd) fazy obliczeń; kolumna = grupa przypadków."""
    style()
    groups = group_cases(df)
    fig, axes = plt.subplots(2, len(groups), figsize=(4.3 * len(groups), 7.4), squeeze=False)
    for j, (title, cases) in enumerate(groups):
        a1, a2 = axes[0][j], axes[1][j]
        for cid in cases:
            d = df[df["case"] == cid].sort_values("threads")
            kw = dict(color=COLOR[cid], marker=MARKER[cid], markersize=6, linewidth=2, label=LABEL[cid])
            a1.plot(d["threads"], d["S_phase"], **kw)
            a2.plot(d["threads"], d["E_phase"], **kw)
        ideal_axes(a1, 8, "S")
        ideal_axes(a2, 8, "E")
        a1.set_title(title, color=INK2)
        a1.legend(loc="upper left", fontsize=8)
        if j > 0:
            a1.set_ylabel("")
            a2.set_ylabel("")
    fig.suptitle(f"Skalowanie fazy obliczeń (automat / Monte Carlo), {compiler}: przyspieszenie S(p) i efektywność "
                 "E(p); mediana z ≥ 5 powtórzeń, rdzenie P", y=1.0)
    fig.tight_layout()
    save(fig, out, "openmp_skalowanie.png")


def plot_amdahl(df: pd.DataFrame, out: Path, compiler: str) -> None:
    """S(p) całego przebiegu (punkty) i krzywa Amdahla z dopasowanym f (linia); panel = grupa przypadków."""
    style()
    groups = group_cases(df)
    fig, axes = plt.subplots(1, len(groups), figsize=(4.3 * len(groups), 4.6), squeeze=False)
    ps = np.linspace(1, 8, 50)
    for j, (title, cases) in enumerate(groups):
        ax = axes[0][j]
        for cid in cases:
            d = df[df["case"] == cid].sort_values("threads")
            f = float(d["amdahl_f_total"].iloc[0])
            ax.plot(ps, 1 / (f + (1 - f) / ps), color=COLOR[cid], linewidth=2,
                    label=f"{LABEL[cid]}: f = {comma(f, 3)}")
            ax.plot(d["threads"], d["S_total"], color=COLOR[cid], marker=MARKER[cid], markersize=7,
                    linestyle="none", markeredgecolor="white", markeredgewidth=1.2)
        ideal_axes(ax, 8, "S")
        ax.set_title(title, color=INK2)
        ax.legend(loc="upper left", fontsize=8)
        if j > 0:
            ax.set_ylabel("")
    fig.suptitle(f"Cały przebieg, {compiler}: zmierzone S(p) (punkty) i prawo Amdahla "
                 "S(p) = 1 / (f + (1 − f)/p) z dopasowaną częścią szeregową f (linia)", y=1.0)
    fig.tight_layout()
    save(fig, out, "openmp_amdahl.png")


def plot_schedules(df: pd.DataFrame, out: Path) -> None:
    style()
    cases = [c for c, _ in CASES if c in set(df["case"])]
    n = len(cases)
    cols = 2 if n > 1 else 1
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(6.0 * cols, 2.5 * rows), squeeze=False)
    for k, cid in enumerate(cases):
        ax = axes[k // cols][k % cols]
        d = df[df["case"] == cid].reset_index(drop=True)
        y = np.arange(len(d))[::-1]
        best = d["phase_med"].min()
        colors = [COLOR[cid] if v == best else "#b8b6af" for v in d["phase_med"]]
        ax.barh(y, d["phase_med"], color=colors, height=0.62)
        ax.errorbar(d["phase_med"], y, xerr=[d["phase_med"] - d["phase_min"], d["phase_max"] - d["phase_med"]],
                    fmt="none", ecolor=INK2, elinewidth=0.9, capsize=2)
        for yi, v, r in zip(y, d["phase_max"], d["rel_best"]):
            ax.text(v * 1.02, yi, "×" + comma(r), va="center", fontsize=8, color=INK)
        ax.set_yticks(y)
        ax.set_yticklabels(d["variant"])
        ax.set_xlim(0, d["phase_max"].max() * 1.22)
        phase = PHASE.get(d["phase"].iloc[0], d["phase"].iloc[0])
        ax.set_title(f"{LABEL.get(cid, cid)}: {phase}, {int(d['threads'].iloc[0])} wątków", color=INK2, fontsize=9.5)
        ax.set_xlabel("czas fazy [ms] (mediana, min–max)")
        ax.grid(axis="y", visible=False)
    for k in range(n, rows * cols):
        axes[k // cols][k % cols].set_visible(False)
    fig.suptitle("Harmonogramy OpenMP: najlepszy w kolorze przypadku, ×k = ile razy dłużej niż najlepszy", y=1.0)
    fig.tight_layout()
    save(fig, out, "openmp_harmonogramy.png")


def plot_threads(stats: dict, out: Path) -> None:
    """Czas pracy wątków (suma po krokach) przy 8 wątkach dla wybranych harmonogramów lawy."""
    style()
    cases = [c for c in ("lava_etna_real", "lava_duza_3d_front", "lava_duza_3d_full")
             if any(k.startswith(c + "|") for k in stats)]
    if not cases:
        return
    variants = [("static", C[0]), ("static,1", C[1]), ("dynamic", C[2]), ("guided", C[3])]
    fig, axes = plt.subplots(1, len(cases), figsize=(5.2 * len(cases), 4.0), squeeze=False)
    for j, cid in enumerate(cases):
        ax = axes[0][j]
        vs = [(v, c) for v, c in variants if f"{cid}|{v}" in stats]
        width = 0.8 / max(1, len(vs))
        cpus = None
        for i, (v, color) in enumerate(vs):
            ca = stats[f"{cid}|{v}"]["stats"]["ca"]
            work = np.array(ca["threadWorkMs"])
            x = np.arange(len(work))
            ax.bar(x + (i - (len(vs) - 1) / 2) * width, work, width=width * 0.92, color=color,
                   label=f"{v}: ×{comma(ca['imbalance'])}")
            cpus = ca.get("cpus")
        ax.set_xticks(np.arange(len(work)))
        ax.set_xticklabels([f"{t}\nCPU {c[0]}" if c else str(t) for t, c in enumerate(cpus or [[]] * len(work))],
                           fontsize=7.5)
        ax.set_xlabel("wątek (procesor logiczny)")
        ax.set_ylabel("czas pracy wątku [ms] (suma kroków)")
        ax.set_title(LABEL.get(cid, cid), color=INK2)
        ax.set_ylim(0, ax.get_ylim()[1] * 1.45)  # miejsce na legendę nad słupkami
        ax.legend(fontsize=8, loc="upper center", ncol=2)
    fig.suptitle("Praca wątków przy 8 wątkach; w legendzie nierównomierność obciążenia = Σ maks / Σ średnia czasu "
                 "wątku w kroku",
                 y=1.02)
    fig.tight_layout()
    save(fig, out, "openmp_watki.png")


def plot_serial(df: pd.DataFrame, raw: pd.DataFrame | None, out: Path) -> None:
    """Udział faz w czasie całego przebiegu (100%) przy 1 i 8 wątkach.

    Z surowych przebiegów (raw): części (także reszta = total − sekcje) liczone w każdym przebiegu osobno, potem
    mediana każdej części — mediany sekcji z tabeli nie sumują się do mediany total (rozkłady skośne), więc „reszta”
    liczona z median byłaby zawyżona (classic 2000², p = 8: 30 ms zamiast 11–15 ms)."""
    style()
    cases = present(df)
    parts = [("faza obliczeń (równoległa)", C[0]),
             ("przygotowanie (config, alokacja, teren, kratery, start Monte Carlo)", C[3]),
             ("statystyki (automat: równolegle; Monte Carlo: etykiety ziaren, szeregowo)", C[4]),
             ("zapis wyników", C[2]), ("reszta poza sekcjami (m.in. zwolnienie pamięci automatu)", "#b8b6af")]

    def split(get, phase: str) -> list[float]:
        ph = get(phase)
        prep = sum(get(k) for k in ("readConfig", "allocate", "terrain", "vents", "mcInit"))
        stats = get("mcStats") + get("caStats")
        savet = get("save") + get("mcSave")
        return [ph, prep, stats, savet, max(0.0, get("total") - ph - prep - stats - savet)]

    rows, labels = [], []
    for cid in cases:
        phase = df[df["case"] == cid]["phase"].iloc[0]
        for p in (1, 8):
            if raw is not None:
                rr = raw[(raw["case"] == cid) & (raw["threads"] == p)]
                if rr.empty:
                    continue
                per_run = np.array([split(lambda k: float(r[k]) if k in r and pd.notna(r[k]) else 0.0, phase)
                                    for _, r in rr.iterrows()])
                vals = list(np.median(per_run, axis=0))
                total = float(rr["total"].median())
            else:
                r = df[(df["case"] == cid) & (df["threads"] == p)]
                if r.empty:
                    continue
                r = r.iloc[0]
                vals = split(lambda k: float(r[k + "_med"]) if k + "_med" in r and pd.notna(r[k + "_med"]) else 0.0,
                             phase)
                total = float(r["total_med"])
            rows.append(vals)
            labels.append(f"{LABEL[cid]}, p = {p}  ({total / 1000:.2f} s)".replace(".", ","))
    if not rows:
        return
    a = np.array(rows)
    a = a / a.sum(axis=1, keepdims=True) * 100
    fig, ax = plt.subplots(figsize=(10, 0.42 * len(rows) + 1.6))
    y = np.arange(len(rows))[::-1]
    left = np.zeros(len(rows))
    for k, (name, color) in enumerate(parts):
        ax.barh(y, a[:, k], left=left, color=color, height=0.7, label=name, edgecolor="white", linewidth=1)
        left += a[:, k]
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8.5)
    ax.set_xlim(0, 100)
    ax.set_xlabel("udział w czasie całego przebiegu [%]")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.07 - 0.9 / len(rows)), ncol=2, fontsize=8)
    ax.set_title("Części szeregowe (prawo Amdahla): udział faz w czasie całego przebiegu przy 1 i 8 wątkach "
                 "(mediany części z powtórzeń)", color=INK2)
    fig.tight_layout()
    save(fig, out, "openmp_szeregowe.png")


def plot_compilers(msvc: pd.DataFrame, gcc: pd.DataFrame, out: Path) -> None:
    style()
    cases = [c for c in present(msvc) if c in set(gcc["case"])]
    if not cases:
        return
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for ax, col, title in ((axes[0], "S_phase", "faza obliczeń"), (axes[1], "S_total", "cały przebieg")):
        x = np.arange(len(cases))
        for i, (df, name, color) in enumerate(((msvc, "MSVC (vcomp, OpenMP 2.0)", C[0]),
                                               (gcc, "GCC (libgomp, WSL)", C[1]))):
            vals = [float(df[(df["case"] == c) & (df["threads"] == 8)][col].iloc[0])
                    if not df[(df["case"] == c) & (df["threads"] == 8)].empty else np.nan for c in cases]
            ax.bar(x + (i - 0.5) * 0.38, vals, width=0.36, color=color, label=name)
            for xi, v in zip(x, vals):
                if not np.isnan(v):
                    ax.text(xi + (i - 0.5) * 0.38, v + 0.08, comma(v, 1), ha="center", fontsize=7.5, color=INK)
        ax.axhline(8, color=MUTED, linestyle="--", linewidth=1.2, label="idealnie (S = 8)")
        ax.set_ylim(0, 9.6)
        ax.set_xticks(x)
        ax.set_xticklabels([SHORT.get(c, c) for c in cases], fontsize=7.8)
        ax.set_title(f"S(8): {title}", color=INK2)
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("przyspieszenie S(8) = T(1) / T(8)")
    axes[0].legend(loc="upper center", fontsize=8, ncol=3)
    fig.suptitle("8 wątków: MSVC (Windows, przypięcie do rdzeni P, wysoki priorytet) i GCC (WSL, 8 procesorów "
                 "wirtualnych, wiązanie libgomp)", y=1.0)
    fig.tight_layout()
    save(fig, out, "openmp_msvc_gcc.png")


def plot_partition(out: Path) -> None:
    """Schemat podziału przestrzeni (bez danych pomiarowych): warstwy z dzielone między 4 wątki — static (równe pasy)
    i static,1 (cyklicznie) — z lawą i jej frontem na przekroju x–z oraz kolory szachownicy MC (Moore 2D)."""
    style()
    nx, nz, nt = 30, 16, 4
    tcol = [C[0], C[6], C[2], C[3]]  # kolor wątku (pasy w tle)
    rock_c, lava_c, cand_c = "#9b9890", "#b33a10", "#ffffff"
    # Teren: stożek z kraterem; lawa w kraterze i na prawym zboczu (warstwa nad skałą).
    h = [max(1, int(13 - abs(x - 12) * 0.95)) for x in range(nx)]
    for x in (11, 12, 13):
        h[x] = 10
    cell = np.zeros((nz, nx), dtype=int)  # 0 powietrze, 1 skała, 2 lawa, 3 kandydat frontu
    for x in range(nx):
        cell[:h[x], x] = 1
    for x in range(11, 23):
        cell[h[x], x] = 2
    cell[11, 11:14] = 2
    for z in range(nz):
        for x in range(nx):
            if cell[z, x] == 0 and any(0 <= z + dz < nz and 0 <= x + dx < nx and cell[z + dz, x + dx] == 2
                                       for dz in (-1, 0, 1) for dx in (-1, 0, 1)):
                cell[z, x] = 3

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.9), gridspec_kw={"width_ratios": [1.15, 1.15, 0.8]})
    for ax, (name, owner) in zip(axes[:2], (("static: równe pasy warstw", lambda z: z * nt // nz),
                                             ("static,1: warstwy na zmianę", lambda z: z % nt))):
        work = [0] * nt
        for z in range(nz):
            t = owner(z)
            ax.add_patch(plt.Rectangle((-0.5, z - 0.5), nx, 1, color=tcol[t], alpha=0.22, linewidth=0))
            work[t] += int(((cell[z] == 2) | (cell[z] == 3)).sum())
            ax.text(nx - 0.2, z, f"w{t}", va="center", ha="left", fontsize=7.5, color=INK2)
        for z in range(nz):
            for x in range(nx):
                c = cell[z, x]
                if c == 1:
                    ax.add_patch(plt.Rectangle((x - 0.5, z - 0.5), 1, 1, facecolor=rock_c, edgecolor="white", lw=0.4))
                elif c == 2:
                    ax.add_patch(plt.Rectangle((x - 0.5, z - 0.5), 1, 1, facecolor=lava_c, edgecolor="white", lw=0.4))
                elif c == 3:
                    ax.add_patch(plt.Rectangle((x - 0.36, z - 0.36), 0.72, 0.72, facecolor=cand_c, edgecolor=INK,
                                               lw=0.8))
        ax.set_xlim(-0.5, nx + 1.2)
        ax.set_ylim(-0.5, nz - 0.5)
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([0, nz // 2, nz - 1])
        ax.set_ylabel("warstwa z")
        ax.grid(False)
        ax.set_title(name, color=INK2)
        ax.set_xlabel("komórki frontu (lawa + kandydaci) na wątek: " + " / ".join(map(str, work)), fontsize=8.5)
    # Szachownica Moore 2D: kolor = (x mod 2) + 2·(y mod 2); komórka i 8 sąsiadów — zawsze inne kolory.
    ax = axes[2]
    n = 8
    ccol = [C[0], C[1], C[2], C[3]]
    for y in range(n):
        for x in range(n):
            k = (x % 2) + 2 * (y % 2)
            ax.add_patch(plt.Rectangle((x - 0.5, y - 0.5), 1, 1, facecolor=ccol[k], alpha=0.45, edgecolor="white",
                                       lw=1))
            ax.text(x, y, str(k), ha="center", va="center", fontsize=8, color=INK)
    cx, cy = 4, 3
    ax.add_patch(plt.Rectangle((cx - 1.5, cy - 1.5), 3, 3, fill=False, edgecolor=INK, lw=1.2, linestyle="--"))
    ax.add_patch(plt.Rectangle((cx - 0.5, cy - 0.5), 1, 1, fill=False, edgecolor=INK, lw=2.2))
    ax.set_xlim(-0.5, n - 0.5)
    ax.set_ylim(-0.5, n - 0.5)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(False)
    ax.set_title("szachownica Monte Carlo (Moore 2D, 4 kolory)", color=INK2)
    ax.set_xlabel("komórka (ramka) i jej 8 sąsiadów (przerywana):\nzawsze inne kolory; von Neumann: 2 kolory, "
                  "Moore 3D: 8", fontsize=8.5)
    handles = [plt.Rectangle((0, 0), 1, 1, facecolor=rock_c), plt.Rectangle((0, 0), 1, 1, facecolor=lava_c),
               plt.Rectangle((0, 0), 1, 1, facecolor=cand_c, edgecolor=INK)]
    fig.legend(handles, ["skała", "lawa", "kandydat frontu (powietrze obok lawy)"], loc="lower center",
               ncol=3, bbox_to_anchor=(0.36, -0.04), fontsize=8.5)
    fig.suptitle("Podział przestrzeni między wątki: iteracja pętli równoległej = jedna warstwa z (w 2D: wiersz y); "
                 "w0–w3 = wątek, któremu przypadła warstwa", y=1.0)
    fig.tight_layout()
    save(fig, out, "openmp_podzial.png")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dir", default=str(ROOT / "bench" / "results" / "omp"), help="folder wyników scaling.py")
    ap.add_argument("--msvc", default="skalowanie_msvc", help="nazwa pomiaru skalowania MSVC (<nazwa>.csv)")
    ap.add_argument("--gcc", default="skalowanie_gcc", help="nazwa pomiaru skalowania GCC")
    ap.add_argument("--sched", default="harmonogramy_msvc", help="nazwa porównania harmonogramów (MSVC)")
    ap.add_argument("--out", default=str(ROOT / "docs" / "img"), help="folder wykresów")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # zawsze: na Windows NUL udaje terminal (isatty) i ma kodowanie cp1250
    d, out = Path(args.dir), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    msvc, gcc, sched = load(d, args.msvc), load(d, args.gcc), load(d, args.sched)
    plot_partition(out)
    if msvc is not None:
        plot_scaling(msvc, out, "MSVC")
        plot_amdahl(msvc, out, "MSVC")
        # Surowe przebiegi: <nazwa>_raw.csv albo części <nazwa>_cz*_raw.csv (pomiar w częściach, --from-raw).
        raw_files = sorted(d.glob(f"{args.msvc}_raw.csv")) or sorted(d.glob(f"{args.msvc}_cz*_raw.csv"))
        raw = pd.concat([pd.read_csv(f) for f in raw_files], ignore_index=True) if raw_files else None
        plot_serial(msvc, raw, out)
        if gcc is not None:
            plot_compilers(msvc, gcc, out)
    if sched is not None:
        plot_schedules(sched, out)
        tj = d / f"{args.sched}_threads.json"
        if tj.exists():
            plot_threads(json.loads(tj.read_text(encoding="utf-8")), out)
    # Walidacja szachownicy MC: wykres z zapisanego CSV (bez ponownego pomiaru) — bench/mc_validation.py --from-csv.
    val = d / "mc_walidacja.csv"
    if val.exists():
        subprocess.run([sys.executable, str(Path(__file__).with_name("mc_validation.py")), "--from-csv", str(val),
                        "--img", str(out)], check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
