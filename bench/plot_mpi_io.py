#!/usr/bin/env python3
"""Wykresy typów pochodnych MPI i MPI-IO -> docs/img/mpi_io_*.png z wyników bench/mpi_io.py
(bench/results/mpi_io/pomiar_*_raw.csv; z części pomiaru brana jest ostatnia powtórzona wersja, np. cz3b zamiast cz3).

Użycie (z katalogu volcano-ca-mc):
    python bench/plot_mpi_io.py
    python bench/plot_mpi_io.py --dir bench/results/mpi_io --out docs/img

Wykresy:
    mpi_io_schemat.png   schemat: typ struct warstwy z pól SoA (wymiana), widok subarray pasa w pliku .bin,
                         przesunięcia MPI_Exscan w pliku .txt
    mpi_io_wymiana.png   czas wymiany warstw: pakowanie (manual) vs typy pochodne (datatype), przypadki × p, MSVC;
                         GCC przy 8 procesach
    mpi_io_zapis.png     zapis wyników: czas save i MB/s, zebranie na proces 0 (gather) vs MPI-IO, .bin i .txt osobno,
                         p procesów (MSVC); przy 8 procesach MS-MPI, OpenMPI z OMPIO i z ROMIO
    mpi_io_udzial.png    udział zapisu (save) w czasie całego przebiegu (total): gather vs MPI-IO
    mpi_io_odczyt.png    odczyt --mc-from: proces 0 + MPI_Scatterv vs MPI_File_read_at_all (MSVC i GCC)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from plot_openmp import MUTED, comma  # noqa: E402
from plot_profile import C, INK, INK2, save, style  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BASE, ALT = C[0], C[1]  # dotychczasowa ścieżka (wersja MPI) / nowa (typy MPI, MPI-IO): niebieski / pomarańczowy
HATCH = "///"  # drugie kodowanie nowej ścieżki (nie tylko kolor)

PACK = [("pack_lava_3d_front", "lawa 128×128×64 (automat frontalny)"),
        ("pack_lava_3d_full", "lawa 128×128×64 (pełny przebieg)"),
        ("pack_classic_300", "rozrost ziaren 300×300×300"), ("pack_mc_cb_3d_100", "Monte Carlo 100×100×100 (szachownica)")]
PACK_SHORT = {"pack_lava_3d_front": "lawa 3D\nfrontalny", "pack_lava_3d_full": "lawa 3D\npełny",
              "pack_classic_300": "rozrost\nziaren 300³", "pack_mc_cb_3d_100": "Monte Carlo\n100³"}
# Zapis: (przypadek, nazwa siatki, rodzaj pliku, rozmiar pliku).
IO = [("io_bin_classic_300", "rozrost ziaren 300×300×300", "bin", "351 MB"),
      ("io_txt_classic_300", "rozrost ziaren 300×300×300", "txt", "562 MB"),
      ("io_bin_classic_2000", "rozrost ziaren 2000×2000", "bin", "52 MB"),
      ("io_txt_classic_2000", "rozrost ziaren 2000×2000", "txt", "86 MB"),
      ("io_bin_lava_3d", "lawa 128×128×64", "bin", "14 MB"), ("io_txt_lava_3d", "lawa 128×128×64", "txt", "19 MB")]
IO_INFO = {cid: (name, kind, size) for cid, name, kind, size in IO}
FILE_KIND = {"bin": "plik binarny", "txt": "plik tekstowy"}
READ = [("read_lava_3d", "wynik lawy 128×128×64 (plik binarny 14 MB)"),
        ("read_classic_300", "wynik rozrostu ziaren 300×300×300 (plik binarny 351 MB)")]


def load_parts(dir_: Path, prefix: str) -> pd.DataFrame | None:
    """Części <prefix>_cz<N>[litera]_raw.csv — z każdej części ostatnia wersja (cz3b zamiast cz3)."""
    best: dict[int, Path] = {}
    for p in sorted(dir_.glob(f"{prefix}_cz*_raw.csv")):
        m = re.search(r"_cz(\d+)([a-z]?)_raw\.csv$", p.name)
        if m:
            n = int(m.group(1))
            if n not in best or p.name > best[n].name:
                best[n] = p
    files = [best[n] for n in sorted(best)]
    single = dir_ / f"{prefix}_raw.csv"
    if not files and single.exists():
        files = [single]
    if not files:
        print(f"  (brak {prefix}_*_raw.csv, pomijam)")
        return None
    print(f"  {prefix}: " + ", ".join(p.name for p in files))
    return pd.concat([pd.read_csv(p) for p in files], ignore_index=True)


def med(df: pd.DataFrame | None, case: str, variant: str, col: str) -> float:
    if df is None:
        return np.nan
    r = df[(df["case"] == case) & (df["variant"] == variant)][col].dropna()
    return float(r.median()) if len(r) else np.nan


def bar_pair(ax: plt.Axes, x: np.ndarray, a: list[float], b: list[float], la: str, lb: str, w: float = 0.38,
             fmt=lambda v: comma(v, 0), ratio: bool = True) -> None:
    """Para słupków (dotychczas / nowe) z wartościami; nad parą zysk nowej ścieżki jako mnożnik > 1 („×2,5” = 2,5 razy
    szybciej, strata: „×1,10 wolniej”)."""
    ax.bar(x - w / 2, a, width=w * 0.95, color=BASE, label=la)
    ax.bar(x + w / 2, b, width=w * 0.95, color=ALT, hatch=HATCH, edgecolor="white", linewidth=0, label=lb)
    top = np.nanmax(np.array(a + b, dtype=float)) if len(a) else 1.0
    for xi, va, vb in zip(x, a, b):
        for dx, v in ((-w / 2, va), (w / 2, vb)):
            if np.isfinite(v):
                ax.text(xi + dx, v + top * 0.015, fmt(v), ha="center", va="bottom", fontsize=7, color=INK)
        if ratio and np.isfinite(va) and np.isfinite(vb) and va > 0:
            r = va / vb
            txt = "bez zmian" if abs(r - 1) < 0.005 else f"×{comma(r, 1 if r >= 10 else 2)}" if r > 1 else \
                f"×{comma(1 / r)} wolniej"
            ax.text(xi, max(va, vb) + top * 0.09, txt, ha="center", va="bottom", fontsize=7.6,
                    color=INK2, fontweight="bold")
    ax.set_ylim(0, top * 1.25)
    ax.grid(axis="x", visible=False)


# ---------------------------------------------------------------------------
# Schemat
# ---------------------------------------------------------------------------
def plot_scheme(out: Path) -> None:
    style()
    fig, axes = plt.subplots(3, 1, figsize=(13, 10.2), gridspec_kw={"height_ratios": [1.25, 1.0, 0.95]})
    box = dict(edgecolor="white", linewidth=0.8)

    # (a) typ komunikatu wymiany: bloki pól SoA (lawa, komunikat do procesu nad nadawcą).
    ax = axes[0]
    fields = [("type[] (uint8)", 17, C[0]), ("flowId[] (int32)", 1, C[2]), ("temp[] (float)", 1, C[6])]
    nl = 22  # warstwy okna pokazane w każdej tablicy (od lewej: niższe), pas nadawcy kończy się na k = 21
    entry_y = [2.45, 1.75, 1.05]  # wiersze opisu typu w ramce
    for i, (name, n, col) in enumerate(fields):
        y = 2.6 - i * 1.3
        ax.text(-0.4, y + 0.4, name, ha="right", va="center", fontsize=8.5, color=INK)
        for z in range(nl):
            sel = z >= nl - n
            ax.add_patch(plt.Rectangle((z, y), 1, 0.8, facecolor=col if sel else "#dcdbd6",
                                       alpha=1.0 if sel else 0.7, **box))
        ax.annotate("", xy=(nl - n - 0.05, y + 0.92), xytext=(nl + 0.05, y + 0.92),
                    arrowprops=dict(arrowstyle="<->", color=INK, lw=0.9))
        ax.text(nl - n / 2 if n > 1 else nl + 0.2, y + 0.98,
                f"blok {i + 1}: {n} warstw" if n > 1 else f"blok {i + 1}: 1 warstwa",
                ha="center" if n > 1 else "right", va="bottom", fontsize=7.6, color=INK)
        # strzałka do typu
        ax.annotate("", xy=(nl + 3.1, entry_y[i] + 0.17), xytext=(nl + 0.2, y + 0.4),
                    arrowprops=dict(arrowstyle="->", color=col, lw=1.4))
    ax.add_patch(plt.Rectangle((nl + 3.2, 0.2), 14.6, 3.05, facecolor="#f4f3ef", edgecolor=INK2, linewidth=1))
    ax.text(nl + 10.5, 2.95, "MPI_Type_create_struct (3 bloki)", ha="center", fontsize=8.8, color=INK, weight="bold")
    for i, (txt, col) in enumerate((("&type[k−16] × 17 · MPI_Type_contiguous(warstwa, MPI_UNSIGNED_CHAR)", C[0]),
                                    ("&flowId[k] × 1 · MPI_Type_contiguous(warstwa, MPI_INT)", C[2]),
                                    ("&temp[k] × 1 · MPI_Type_contiguous(warstwa, MPI_FLOAT)", C[6]))):
        ax.add_patch(plt.Rectangle((nl + 3.45, entry_y[i]), 0.35, 0.35, facecolor=col, linewidth=0))
        ax.text(nl + 3.95, entry_y[i] + 0.17, txt, va="center", fontsize=7.5, color=INK)
    ax.text(nl + 3.45, 0.45, "adresy: MPI_Get_address; MPI_Isend(MPI_BOTTOM, 1, typ), bez bufora i memcpy",
            fontsize=7.4, color=INK2)
    ax.text(0, -0.45, "okno nadawcy: warstwy z (w każdej tablicy ciągły fragment), k = najwyższa warstwa pasa",
            fontsize=7.8, color=INK2)
    ax.set_xlim(-7.5, nl + 18.3)
    ax.set_ylim(-0.7, 3.6)
    ax.axis("off")
    ax.set_title("(a) wymiana warstw, mpi.pack = datatype: typ komunikatu z warstw pól SoA (lawa → proces nad "
                 "nadawcą; zbudowany raz, dwa zestawy przy zamianie cur / next)", color=INK2, loc="left")

    # (b) widok pasa w pliku .bin: subarray każdej tablicy, struct z przesunięć tablic.
    ax = axes[1]
    arrays = [("type", 1), ("flowId", 4), ("temp", 4), ("solidStep", 2), ("arrivalStep", 2)]
    L, p = 12, 3
    lo = [r * L // p for r in range(p)]
    hi = [(r + 1) * L // p for r in range(p)]
    pc = [C[0], C[2], C[6]]
    x = 0.0
    ax.add_patch(plt.Rectangle((x, 0), 1.6, 1, facecolor="#9b9890", **box))
    ax.text(x + 0.8, 0.5, "nagł.\n20 B", ha="center", va="center", fontsize=7, color="white")
    ax.text(x + 0.8, -0.32, "proces 0:\nwrite_at", ha="center", va="top", fontsize=6.8, color=INK2)
    x += 1.7
    for name, b in arrays:
        w = 0.24 * b ** 0.5
        x0 = x
        for z in range(L):
            r = next(i for i in range(p) if lo[i] <= z < hi[i])
            ax.add_patch(plt.Rectangle((x, 0), w, 1, facecolor=pc[r], **box))
            x += w
        ax.text((x0 + x) / 2, 1.12, f"{name} ({b} B)", ha="center", va="bottom", fontsize=7.6, color=INK)
        x += 0.25
    for r in range(p):
        ax.add_patch(plt.Rectangle((x + 0.6, 0.72 - r * 0.33), 0.3, 0.24, facecolor=pc[r], linewidth=0))
        ax.text(x + 1.0, 0.84 - r * 0.33, f"proces {r}: warstwy [{lo[r]}, {hi[r]})", va="center", fontsize=7.6,
                color=INK)
    ax.text(1.7, -0.32, "widok procesu r (MPI_File_set_view): filetype = MPI_Type_create_struct( 5 × "
            "MPI_Type_create_subarray(L × bajty warstwy, wycinek [lo, hi)), przesunięcia = początki tablic )\n"
            "zapis: MPI_File_write_all(bufor, 1, typ pamięci), czyli jeden zapis zbiorowy pasa wszystkich tablic",
            va="top", fontsize=7.6, color=INK2)
    ax.set_xlim(-0.2, x + 6.2)
    ax.set_ylim(-1.1, 1.55)
    ax.axis("off")
    ax.set_title("(b) mpi.io = mpiio, plik ca_result.bin: pas procesu = wycinek każdej tablicy (L = 12 warstw, "
                 "3 procesy)", color=INK2, loc="left")

    # (c) plik tekstowy: długości bajtów, MPI_Exscan, przesunięcia.
    ax = axes[2]
    lens = [("nagłówek + wiersze 0", 9.5), ("wiersze 1", 7.2), ("wiersze 2", 8.4), ("wiersze 3", 6.1)]
    x = 0.0
    off = 0.0
    for r, (name, n) in enumerate(lens):
        col = C[[0, 2, 6, 3][r]]
        ax.add_patch(plt.Rectangle((x, 0), n, 1, facecolor=col, **box))
        ax.text(x + n / 2, 0.5, f"proces {r}: {name}\nn{r} B", ha="center", va="center", fontsize=7.6,
                color="white" if r != 3 else INK)
        lab = "0" if r == 0 else " + ".join(f"n{i}" for i in range(r))
        ax.annotate(f"przesunięcie = {lab}", xy=(x, 1.0), xytext=(x + 0.2, 1.55), fontsize=7.6, color=INK,
                    arrowprops=dict(arrowstyle="->", color=INK, lw=0.8))
        x += n
        off += n
    ax.text(0, -0.3, "każdy proces formatuje swoje wiersze do pamięci (ten sam kod co writeTxt) → MPI_Exscan(n, SUM) "
            "= przesunięcie, MPI_Allreduce = rozmiar pliku (MPI_File_set_size)\n→ MPI_File_write_at_all(przesunięcie, "
            "tekst) w porcjach < 2 GB; wiersze mają zmienną długość, więc przesunięcie nie wynika z numeru warstwy",
            va="top", fontsize=7.6, color=INK2)
    ax.set_xlim(-0.2, x + 0.5)
    ax.set_ylim(-1.0, 2.0)
    ax.axis("off")
    ax.set_title("(c) mpi.io = mpiio, plik ca_result.txt: przesunięcia pasów z MPI_Exscan (4 procesy)", color=INK2,
                 loc="left")
    fig.suptitle("Typy pochodne MPI w wymianie warstw i w widoku pliku, przesunięcia tekstu", y=0.995)
    fig.tight_layout()
    save(fig, out, "mpi_io_schemat.png")


# ---------------------------------------------------------------------------
# Wymiana warstw
# ---------------------------------------------------------------------------
def plot_pack(msvc: pd.DataFrame, gcc: pd.DataFrame | None, out: Path) -> None:
    style()
    ps = [2, 4, 7, 8]
    fig, axes = plt.subplots(1, 5, figsize=(19, 4.4), gridspec_kw={"width_ratios": [1, 1, 1, 1, 1.15]})
    for ax, (cid, title) in zip(axes, PACK):
        a = [med(msvc, cid, f"m{p}", "haloAvg") for p in ps]
        b = [med(msvc, cid, f"m{p}d", "haloAvg") for p in ps]
        bar_pair(ax, np.arange(len(ps)), a, b, "pakowanie do bufora", "typ pochodny MPI (bez bufora)",
                 fmt=lambda v: comma(v, 0) if v >= 100 else comma(v, 1))
        ax.set_xticks(np.arange(len(ps)))
        ax.set_xticklabels([f"p = {p}" for p in ps])
        ax.set_title(title, color=INK2)
    axes[0].set_ylabel("czas wymiany warstw w fazie [ms]\n(średnia po procesach, mediana powtórzeń)")
    axes[0].legend(loc="upper left", fontsize=7.8)
    ax = axes[4]
    cases = [c for c, _ in PACK if np.isfinite(med(gcc, c, "m8", "haloAvg"))] if gcc is not None else []
    if cases:
        a = [med(gcc, c, "m8", "haloAvg") for c in cases]
        b = [med(gcc, c, "m8d", "haloAvg") for c in cases]
        bar_pair(ax, np.arange(len(cases)), a, b, "pakowanie do bufora", "typ pochodny MPI (bez bufora)",
                 fmt=lambda v: comma(v, 0) if v >= 100 else comma(v, 1))
        ax.set_xticks(np.arange(len(cases)))
        ax.set_xticklabels([PACK_SHORT[c] for c in cases], fontsize=7.8)
    ax.set_title("GCC / OpenMPI (WSL), p = 8", color=INK2)
    fig.suptitle("Wymiana warstw brzegowych: pakowanie do bufora i typ pochodny MPI (te same bajty i komunikaty); "
                 "MSVC / MS-MPI (4 panele) i GCC / OpenMPI.\nNad parą: ile razy szybciej z typem pochodnym. Monte Carlo: "
                 "czas wymiany zawiera czekanie na wolniejszy pas", y=1.02)
    fig.tight_layout()
    save(fig, out, "mpi_io_wymiana.png")


# ---------------------------------------------------------------------------
# Zapis
# ---------------------------------------------------------------------------
def plot_io(msvc: pd.DataFrame, gcc: pd.DataFrame | None, romio: pd.DataFrame | None, out: Path) -> None:
    style()
    ps = [1, 2, 4, 8]
    fig, axes = plt.subplots(2, 3, figsize=(17, 8.4), gridspec_kw={"width_ratios": [1, 1, 1.1]})
    for j, (kind, key) in enumerate((("bin", "caBin"), ("txt", "caTxt"))):
        cid = f"io_{kind}_classic_300"
        ax = axes[0][j]
        a = [med(msvc, cid, f"m{p}", "save") for p in ps]
        b = [med(msvc, cid, f"m{p}i", "save") for p in ps]
        bar_pair(ax, np.arange(len(ps)), a, b, "zebranie na proces 0", "MPI-IO (każdy proces pisze swój pas)")
        ax.set_xticks(np.arange(len(ps)))
        ax.set_xticklabels([f"p = {p}" for p in ps])
        ax.set_title(f"rozrost ziaren 300³: ca_result.{kind} ({IO_INFO[cid][2]}), czas zapisu [ms]", color=INK2)
        ax.set_ylabel("czas zapisu [ms]: pas bez ramki\n+ (zebranie) przesłanie + plik" if j == 0 else "")
        ax.legend(loc="upper right", fontsize=7.8)
        # MB/s = rozmiar pliku / save, oba rozmiary
        ax = axes[1][j]
        for cid2, ls, mk in ((f"io_{kind}_classic_300", "-", "o"), (f"io_{kind}_classic_2000", "--", "s")):
            size = med(msvc, cid2, "m1", f"{key}Bytes")
            for suf, col, lab in (("", BASE, "zebranie"), ("i", ALT, "MPI-IO")):
                ys = [size / 1e3 / med(msvc, cid2, f"m{p}{suf}", "save") for p in ps]
                ax.plot(ps, ys, color=col, linestyle=ls, marker=mk, markersize=6,
                        label=f"{lab}, {IO_INFO[cid2][0].replace('300×300×300', '300³').replace('2000×2000', '2000²')}")
        ax.set_xticks(ps)
        ax.set_xlabel("liczba procesów p")
        ax.set_ylim(bottom=0)
        ax.set_ylabel("przepustowość zapisu [MB/s]\n= rozmiar / czas zapisu" if j == 0 else "")
        ax.set_title(f"{FILE_KIND[kind]}: MB/s (rozrost ziaren 300³ i 2000²)", color=INK2)
        ax.legend(loc="upper left", fontsize=7.6)
    # p = 8: implementacje MPI-IO
    impls = [(msvc, "MS-MPI\n(NTFS)"), (gcc, "OpenMPI OMPIO\n(ext4)"), (romio, "OpenMPI ROMIO\n(ext4)")]
    for i, kind in enumerate(("bin", "txt")):
        ax = axes[i][2]
        cid = f"io_{kind}_classic_300"
        a = [med(df, cid, "m8", "save") for df, _ in impls]
        b = [med(df, cid, "m8i", "save") for df, _ in impls]
        bar_pair(ax, np.arange(len(impls)), a, b, "zebranie", "MPI-IO")
        ax.set_xticks(np.arange(len(impls)))
        ax.set_xticklabels([n for _, n in impls], fontsize=8)
        ax.set_title(f"rozrost ziaren 300³, {FILE_KIND[kind]}, p = 8:\nczas zapisu [ms] wg implementacji", color=INK2)
    fig.suptitle("Zapis wyniku: zebranie pasów na proces 0 i MPI-IO (każdy proces pisze swój pas do wspólnego pliku; "
                 "jeden dysk SSD, czas do zamknięcia pliku).\nKolumny 1–2: MSVC / MS-MPI. Nad parą: ile razy szybciej "
                 "z MPI-IO", y=1.02)
    fig.tight_layout()
    save(fig, out, "mpi_io_zapis.png")


def plot_share(msvc: pd.DataFrame, out: Path) -> None:
    style()
    fig, axes = plt.subplots(2, 3, figsize=(15, 7.2), sharey=True)
    for ax, (cid, name, kind, size) in zip(axes.flat, IO):
        ps = [p for p in (1, 2, 4, 8) if np.isfinite(med(msvc, cid, f"m{p}", "save"))]
        a = [100 * med(msvc, cid, f"m{p}", "save") / med(msvc, cid, f"m{p}", "total") for p in ps]
        b = [100 * med(msvc, cid, f"m{p}i", "save") / med(msvc, cid, f"m{p}i", "total") for p in ps]
        bar_pair(ax, np.arange(len(ps)), a, b, "zebranie na proces 0", "MPI-IO", fmt=lambda v: comma(v, 0) + "%",
                 ratio=False)
        ax.set_ylim(0, 75)
        ax.set_xticks(np.arange(len(ps)))
        ax.set_xticklabels([f"p = {p}" for p in ps])
        ax.set_title(f"{name}: {FILE_KIND[kind]} {size}", color=INK2)
    axes[0][0].set_ylabel("zapis / cały przebieg [%]")
    axes[1][0].set_ylabel("zapis / cały przebieg [%]")
    axes[0][0].legend(loc="upper left", fontsize=8)
    fig.suptitle("Udział zapisu wyniku w czasie całego przebiegu: MSVC / MS-MPI, mediana z 5 powtórzeń. Faza obliczeń "
                 "maleje z p, zapis nie, więc udział rośnie", y=1.0)
    fig.tight_layout()
    save(fig, out, "mpi_io_udzial.png")


def plot_read(msvc: pd.DataFrame, gcc: pd.DataFrame | None, out: Path) -> None:
    style()
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.4))
    cols = [(msvc, "MSVC", 1), (msvc, "MSVC", 8), (gcc, "GCC", 1), (gcc, "GCC", 8)]
    for ax, (cid, title) in zip(axes, READ):
        a = [med(df, cid, f"m{p}", "readInput") + np.nan_to_num(med(df, cid, f"m{p}", "scatterMax")) for df, _, p in cols]
        b = [med(df, cid, f"m{p}i", "readInput") for df, _, p in cols]
        bar_pair(ax, np.arange(len(cols)), a, b, "proces 0 czyta cały plik (+ MPI_Scatterv)",
                 "MPI_File_read_at_all: każdy swój pas", fmt=lambda v: comma(v, 0) if v >= 10 else comma(v, 1))
        ax.set_ylim(0, ax.get_ylim()[1] * 1.25)  # miejsce na legendę nad słupkami
        ax.set_xticks(np.arange(len(cols)))
        ax.set_xticklabels([f"{n}\np = {p}" for _, n, p in cols])
        ax.set_title(title, color=INK2)
    axes[0].set_ylabel("odczyt wyniku automatu [ms]")
    axes[0].legend(loc="upper left", fontsize=7.8)
    fig.suptitle("Odczyt wyniku automatu na wejściu Monte Carlo: proces 0 i rozesłanie 5 tablic (13 B na komórkę) albo "
                 "MPI-IO pasów 3 tablic (5 B na komórkę);\nplik w pamięci podręcznej systemu. Nad parą: ile razy szybciej "
                 "z MPI-IO", y=1.02)
    fig.tight_layout()
    save(fig, out, "mpi_io_odczyt.png")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dir", default=str(ROOT / "bench" / "results" / "mpi_io"), help="folder wyników mpi_io.py")
    ap.add_argument("--out", default=str(ROOT / "docs" / "img"), help="folder wykresów")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    d, out = Path(args.dir), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    plot_scheme(out)
    msvc, gcc = load_parts(d, "pomiar_msvc"), load_parts(d, "pomiar_gcc")
    romio = load_parts(d, "pomiar_gcc_romio")
    if msvc is not None:
        plot_pack(msvc, gcc, out)
        plot_io(msvc, gcc, romio, out)
        plot_share(msvc, out)
        plot_read(msvc, gcc, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
