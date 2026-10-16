"""Rysuje przekrój (lub widok z góry) wyniku symulacji do pliku PNG.

Narzędzie do obejrzenia wyniku przed powstaniem GUI (etapy 4–5).
Czyta ca_result.bin (szybciej) albo ca_result.txt z folderu wyników, a w trybie
--color crystal także mapę kryształów Monte Carlo mc_result.bin / mc_result.txt.

Przykłady:
    python tools/plot_slice.py results/test_2d
    python tools/plot_slice.py results/test_3d --axis y --index 32 --color flow
    python tools/plot_slice.py results/test_3d --axis top --color type
    python tools/plot_slice.py results/test_2d --color temp --out docs/img/test_2d_temp.png
    python tools/plot_slice.py results/mc_full_2d --color crystal --boundaries
    python tools/plot_slice.py results/lava_mc_2d --color crystal --crop --boundaries
    python tools/plot_slice.py results/lava_mc_2d --color cooling --window 95 145 40 56

Osie: x, y, z — przekrój płaszczyzną prostopadłą do osi (z = pionowa, więc --axis z
to poziomy plaster na wysokości --index); top — widok z góry: najwyższa niepusta
komórka w każdej kolumnie (skała cieniowana wysokością terenu). Bez --axis dla
przestrzeni 2D wybierana jest płaszczyzna siatki (oś o rozmiarze 1), dla 3D — y.

Tryb cooling: czas w stanie płynnym solidStep − arrivalStep (ca_result.bin w wersji 2) —
z niego MC liczy mobilność (długo płynna lawa -> duże kryształy).

Tryb crystal: każdy kryształ (orientacja 1..Q z MC) ma stały pseudolosowy kolor,
skała jest szara, powietrze białe. Gdy w folderze nie ma ca_result.* (MC uruchomione
z --mc-from albo tryb full), typy komórek są brane z folderu wejściowego zapisanego
w config_used.json (_mcFrom), a w trybie full cała przestrzeń jest domeną.
"""

import argparse
import json
import os
import sys

import numpy as np

import matplotlib

matplotlib.use("Agg")  # bez okna — tylko zapis do pliku
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.colors import ListedColormap, hsv_to_rgb  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

AIR, ROCK, LAVA, BASALT = 0, 1, 2, 3

# Kolory (paleta referencyjna z walidacją CVD): lawa = pomarańcz (gorąca),
# bazalt = niebieski (zimny), skała = szary kontekst, powietrze = tło.
SURFACE = "#fcfcfb"
TYPE_COLORS = {AIR: SURFACE, ROCK: "#c3c2b7", LAVA: "#eb6834", BASALT: "#2a78d6"}
TYPE_NAMES = {AIR: "powietrze", ROCK: "skała", LAVA: "lawa", BASALT: "bazalt"}
# Kolejne kratery — stała kolejność slotów palety (nigdy nie zapętlamy).
FLOW_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"


def read_result(folder, required=True):
    """Zwraca słownik tablic (nz, ny, nx): type, flow, temp, a z .bin także solid (solidStep)
    i arrival (arrivalStep; w wersji 1 zera) — z .bin (wersja 1 lub 2) albo .txt.
    Gdy brak plików: kończy program (required) albo zwraca None."""
    bin_path = os.path.join(folder, "ca_result.bin")
    txt_path = os.path.join(folder, "ca_result.txt")
    if os.path.exists(bin_path):
        with open(bin_path, "rb") as f:
            raw = f.read()
        if raw[:4] != b"VOLC":
            sys.exit(f"{bin_path}: to nie jest plik wyników VOLC")
        version, nx, ny, nz = np.frombuffer(raw, dtype="<i4", count=4, offset=4)
        if version not in (1, 2):
            sys.exit(f"{bin_path}: nieobsługiwana wersja {version}")
        # Wersja 2 dopisuje arrivalStep na końcu — początek pliku jest taki sam jak w wersji 1.
        n = int(nx) * int(ny) * int(nz)
        off = 20
        cell_type = np.frombuffer(raw, dtype=np.uint8, count=n, offset=off)
        off += n
        flow = np.frombuffer(raw, dtype="<i4", count=n, offset=off)
        off += 4 * n
        temp = np.frombuffer(raw, dtype="<f4", count=n, offset=off)
        off += 4 * n
        solid = np.frombuffer(raw, dtype="<u2", count=n, offset=off)
        off += 2 * n
        arrival = np.frombuffer(raw, dtype="<u2", count=n, offset=off) if version >= 2 else np.zeros(n, np.uint16)
    elif os.path.exists(txt_path):
        with open(txt_path, encoding="ascii") as f:
            nx, ny, nz = (int(v) for v in f.readline().split())
        data = np.loadtxt(txt_path, skiprows=2, ndmin=2)
        # Plik ma kolejność x najszybciej, potem y, potem z — taką samą jak .bin,
        # ale ustawiamy wartości po współrzędnych, żeby nie zależeć od kolejności wierszy.
        idx = (data[:, 0] + nx * (data[:, 1] + ny * data[:, 2])).astype(np.int64)
        n = nx * ny * nz
        cell_type = np.zeros(n, np.uint8)
        flow = np.zeros(n, np.int32)
        temp = np.zeros(n, np.float32)
        cell_type[idx] = data[:, 3]
        flow[idx] = data[:, 4]
        temp[idx] = data[:, 5]
        solid = arrival = None  # txt nie zawiera pól czasu
    elif required:
        sys.exit(f"Brak ca_result.bin ani ca_result.txt w {folder}")
    else:
        return None
    shape = (int(nz), int(ny), int(nx))
    grid = {
        "type": cell_type.reshape(shape),
        "flow": flow.reshape(shape),
        "temp": temp.reshape(shape),
    }
    if solid is not None:
        grid["solid"] = solid.reshape(shape)
        grid["arrival"] = arrival.reshape(shape)
    return grid


def read_crystals(folder):
    """Mapa kryształów MC (nz, ny, nx) z mc_result.bin ("VMC1") albo mc_result.txt."""
    bin_path = os.path.join(folder, "mc_result.bin")
    txt_path = os.path.join(folder, "mc_result.txt")
    if os.path.exists(bin_path):
        with open(bin_path, "rb") as f:
            raw = f.read()
        if raw[:4] != b"VMC1":
            sys.exit(f"{bin_path}: to nie jest plik kryształów VMC1")
        nx, ny, nz = (int(v) for v in np.frombuffer(raw, dtype="<i4", count=3, offset=4))
        crystal = np.frombuffer(raw, dtype="<i4", count=nx * ny * nz, offset=16)
    elif os.path.exists(txt_path):
        with open(txt_path, encoding="ascii") as f:
            nx, ny, nz = (int(v) for v in f.readline().split())
        data = np.loadtxt(txt_path, skiprows=2, dtype=np.int64, ndmin=2)
        idx = data[:, 0] + nx * (data[:, 1] + ny * data[:, 2])
        crystal = np.zeros(nx * ny * nz, np.int32)
        crystal[idx] = data[:, 3]
    else:
        sys.exit(f"Brak mc_result.bin ani mc_result.txt w {folder} (MC wyłączone? mc.enabled = true)")
    return crystal.reshape((nz, ny, nx))


def ca_folder_for(folder, ca_override):
    """Folder z ca_result.* dla wyników MC: --ca, ten sam folder albo _mcFrom z config_used.json."""
    if ca_override:
        return ca_override
    if any(os.path.exists(os.path.join(folder, n)) for n in ("ca_result.bin", "ca_result.txt")):
        return folder
    cfg_path = os.path.join(folder, "config_used.json")
    if os.path.exists(cfg_path):
        with open(cfg_path, encoding="utf-8") as f:
            source = json.load(f).get("_mcFrom")
        if source and os.path.isdir(source):
            return source
    return None


def take_slice(grid, axis, index):
    """Wycina płaszczyznę 2D. Zwraca (tablice 2D, opis, etykieta osi poziomej, pionowej)."""
    nz, ny, nx = grid["type"].shape
    if axis == "top":
        # Najwyższa niepusta komórka w każdej kolumnie (x, y).
        solid = grid["type"] != AIR
        has = solid.any(axis=0)
        top = nz - 1 - np.argmax(solid[::-1], axis=0)  # indeks z najwyższej niepustej
        top = np.where(has, top, 0)
        yy, xx = np.indices((ny, nx))
        planes = {k: v[top, yy, xx] for k, v in grid.items()}
        planes["type"] = np.where(has, planes["type"], AIR)
        planes["height"] = np.where(has, top + 1, 0)
        return planes, "widok z góry", "x", "y"
    size = {"x": nx, "y": ny, "z": nz}[axis]
    if index is None:
        index = 0 if size == 1 else size // 2
    if not 0 <= index < size:
        sys.exit(f"--index {index} poza zakresem 0..{size - 1} dla osi {axis}")
    if axis == "y":
        planes = {k: v[:, index, :] for k, v in grid.items()}
        return planes, f"przekrój y = {index}", "x", "z (wysokość)"
    if axis == "x":
        planes = {k: v[:, :, index] for k, v in grid.items()}
        return planes, f"przekrój x = {index}", "y", "z (wysokość)"
    planes = {k: v[index, :, :] for k, v in grid.items()}
    return planes, f"warstwa z = {index}", "x", "y"


def default_axis(shape):
    """Płaszczyzna siatki 2D (oś o rozmiarze 1); dla 3D przekrój y."""
    nz, ny, nx = shape
    if ny == 1:
        return "y"
    if nz == 1:
        return "z"
    if nx == 1:
        return "x"
    return "y"


def flow_colors(count):
    """Kolory ziaren: do 8 — sloty palety w stałej kolejności; więcej (rozrost classic,
    setki ziaren) — deterministyczne kolory pseudolosowe, jak w obrazach mikrostruktur."""
    if count <= len(FLOW_COLORS):
        return FLOW_COLORS[:count]
    rng = np.random.default_rng(12345)
    hues = rng.permutation(count) / count
    cmap = plt.get_cmap("hsv")
    lightness = 0.75 + 0.25 * rng.random(count)
    return [tuple(c * l for c in cmap(h)[:3]) for h, l in zip(hues, lightness)]


def crystal_rgb(ids):
    """Stały pseudolosowy kolor dla ID kryształu: ten sam ID ma ten sam kolor na każdym
    obrazku (hash mnożeniem Knutha). Nasycenie >= 0.45 i jasność <= 0.92 — kryształ nie
    zlewa się z szarą skałą ani białym powietrzem."""
    h = (ids.astype(np.uint64) * np.uint64(2654435761)) % np.uint64(2 ** 32)
    hue = (h & np.uint64(0xFFFF)).astype(float) / 65536.0
    sat = 0.45 + 0.40 * ((h >> np.uint64(16)) & np.uint64(0xFF)).astype(float) / 255.0
    val = 0.62 + 0.30 * ((h >> np.uint64(24)) & np.uint64(0xFF)).astype(float) / 255.0
    return hsv_to_rgb(np.stack([hue, sat, val], axis=-1))


def boundary_segments(crystal):
    """Odcinki granic między komórkami o różnych kryształach (co najmniej jedna w domenie)
    — także granica bazaltu ze skałą/powietrzem. Współrzędne jak w imshow (środki komórek
    w liczbach całkowitych)."""
    segs = []
    inside = crystal > 0
    # Granice pionowe: między kolumnami j i j+1.
    diff = (crystal[:, :-1] != crystal[:, 1:]) & (inside[:, :-1] | inside[:, 1:])
    for i, j in zip(*np.nonzero(diff)):
        segs.append([(j + 0.5, i - 0.5), (j + 0.5, i + 0.5)])
    # Granice poziome: między wierszami i i i+1.
    diff = (crystal[:-1, :] != crystal[1:, :]) & (inside[:-1, :] | inside[1:, :])
    for i, j in zip(*np.nonzero(diff)):
        segs.append([(j - 0.5, i + 0.5), (j + 0.5, i + 0.5)])
    return segs


def crop_box(planes, margin=3):
    """Prostokąt obejmujący lawę/bazalt (lub domenę MC) z marginesem; None, gdy brak."""
    mask = (planes["type"] == LAVA) | (planes["type"] == BASALT)
    if "crystal" in planes:
        mask |= planes["crystal"] > 0
    if not mask.any():
        return None
    rows = np.nonzero(mask.any(axis=1))[0]
    cols = np.nonzero(mask.any(axis=0))[0]
    h, w = mask.shape
    return (max(rows[0] - margin, 0), min(rows[-1] + margin + 1, h),
            max(cols[0] - margin, 0), min(cols[-1] + margin + 1, w))


def render(planes, mode, title, xlabel, ylabel, out_path, is_top, flow_count, boundaries, offset):
    cell_type = planes["type"]
    h, w = cell_type.shape
    # Rozmiar rysunku proporcjonalny do przekroju (komórki kwadratowe).
    scale = 9.0 / max(w, h)
    fig_w = max(5.0, w * scale + 2.5)
    fig_h = max(3.0, h * scale + 1.2)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    rgb = np.zeros((h, w, 3))

    def paint(mask, color):
        rgb[mask] = matplotlib.colors.to_rgb(color)

    paint(cell_type == AIR, TYPE_COLORS[AIR])
    rock = cell_type == ROCK
    if is_top and rock.any():
        # Teren cieniowany wysokością — widać stożek wulkanu.
        height = planes["height"].astype(float)
        hmin, hmax = height[rock].min(), height[rock].max()
        t = (height - hmin) / max(hmax - hmin, 1.0)
        shade = 0.45 + 0.35 * t  # 0.45..0.80 — najwyższa skała nadal wyraźnie ciemniejsza od tła
        rgb[rock] = np.stack([shade, shade, shade * 0.97], axis=-1)[rock]
    else:
        paint(rock, TYPE_COLORS[ROCK])

    handles = []
    lava_like = (cell_type == LAVA) | (cell_type == BASALT)
    colorbar_source = None
    colorbar_label = "temperatura [°C]"
    if mode == "type":
        paint(cell_type == LAVA, TYPE_COLORS[LAVA])
        paint(cell_type == BASALT, TYPE_COLORS[BASALT])
        present = sorted(set(np.unique(cell_type).tolist()))
        handles = [Patch(facecolor=TYPE_COLORS[t], edgecolor=INK_SECONDARY, linewidth=0.5, label=TYPE_NAMES[t])
                   for t in present if t in TYPE_NAMES]
    elif mode == "flow":
        flows = planes["flow"]
        count = flow_count  # z całej siatki — te same kolory na każdym przekroju
        colors = flow_colors(max(count, 1))
        for f in range(1, count + 1):
            paint(lava_like & (flows == f), colors[f - 1])
        if count <= len(FLOW_COLORS):
            handles = [Patch(facecolor=colors[f - 1], label=f"krater {f}") for f in range(1, count + 1)]
            handles.append(Patch(facecolor=TYPE_COLORS[ROCK], edgecolor=INK_SECONDARY, linewidth=0.5, label="skała"))
        else:
            handles = [Patch(facecolor="none", edgecolor="none", label=f"{count} ziaren (kolory losowe)")]
    elif mode == "crystal":
        crystal = planes["crystal"]
        inside = crystal > 0
        paint(lava_like & ~inside, TYPE_COLORS[BASALT])  # nie powinno wystąpić — bazalt bez kryształu
        rgb[inside] = crystal_rgb(crystal[inside])
        count = len(np.unique(crystal[inside]))
        handles = [Patch(facecolor="none", edgecolor="none", label=f"{count} orientacji w przekroju\n(kolory losowe)")]
        if rock.any():
            handles.append(Patch(facecolor=TYPE_COLORS[ROCK], edgecolor=INK_SECONDARY, linewidth=0.5, label="skała"))
    elif mode == "cooling":
        # Czas w stanie płynnym (wejście mobilności MC); sekwencyjna skala jednej barwy:
        # jasny = krótko płynna (szybko zastygła), ciemny = długo płynna.
        live = lava_like
        if live.any():
            time = planes["solid"].astype(float) - planes["arrival"].astype(float)
            liquid = planes["type"] == LAVA
            if liquid.any():
                # Lawa jeszcze płynna: jak w MC — zastygła w ostatnim kroku CA.
                end = max(float(planes["solid"].max()), float(planes["arrival"].max()))
                time = np.where(liquid, end - planes["arrival"], time)
            time = np.maximum(time, 0.0)
            lo, hi = float(time[live].min()), float(time[live].max())
            norm = matplotlib.colors.Normalize(vmin=lo, vmax=max(hi, lo + 1e-3))
            cmap = ListedColormap(["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"])
            smooth = matplotlib.colors.LinearSegmentedColormap.from_list("czas", cmap.colors)
            rgb[live] = smooth(norm(time[live]))[:, :3]
            colorbar_source = matplotlib.cm.ScalarMappable(norm=norm, cmap=smooth)
            colorbar_label = "czas w stanie płynnym [kroki CA]"
        handles = [Patch(facecolor=TYPE_COLORS[ROCK], edgecolor=INK_SECONDARY, linewidth=0.5, label="skała")]
    else:  # temp
        temps = planes["temp"]
        if lava_like.any():
            lo, hi = float(temps[lava_like].min()), float(temps[lava_like].max())
            norm = matplotlib.colors.Normalize(vmin=lo, vmax=max(hi, lo + 1e-3))
            cmap = plt.get_cmap("Oranges")  # jedna barwa: jasny = chłodniej, ciemny = goręcej
            rgb[lava_like] = cmap(0.25 + 0.75 * norm(temps[lava_like]))[:, :3]
            colorbar_source = matplotlib.cm.ScalarMappable(
                norm=norm, cmap=ListedColormap(cmap(np.linspace(0.25, 1.0, 256))))
        handles = [Patch(facecolor=TYPE_COLORS[ROCK], edgecolor=INK_SECONDARY, linewidth=0.5, label="skała")]

    # Współrzędne osi uwzględniają przycięcie (--crop): piksel (0,0) to komórka offset.
    row0, col0 = offset
    extent = (col0 - 0.5, col0 + w - 0.5, row0 - 0.5, row0 + h - 0.5)
    ax.imshow(rgb, origin="lower", interpolation="nearest", aspect="equal", extent=extent)
    if mode == "crystal" and boundaries:
        segs = boundary_segments(planes["crystal"])
        if segs:
            segs = np.asarray(segs) + np.array([col0, row0])
            # Cienka linia w kolorze tuszu — granice ziaren; grubość zależna od skali rysunku.
            lw = max(0.25, min(1.0, 120.0 / max(w, h)))
            ax.add_collection(LineCollection(segs, colors=INK, linewidths=lw, alpha=0.55))
    ax.set_title(title, color=INK, fontsize=10, loc="left")
    ax.set_xlabel(xlabel, color=INK_SECONDARY, fontsize=9)
    ax.set_ylabel(ylabel, color=INK_SECONDARY, fontsize=9)
    ax.tick_params(colors=INK_SECONDARY, labelsize=8)
    for spine in ax.spines.values():
        spine.set_color("#c3c2b7")
    if colorbar_source is not None:
        cb = fig.colorbar(colorbar_source, ax=ax, fraction=0.04, pad=0.02)
        cb.set_label(colorbar_label, color=INK_SECONDARY, fontsize=9)
        cb.ax.tick_params(colors=INK_SECONDARY, labelsize=8)
    if handles:
        if colorbar_source is not None:
            # Po prawej jest pasek barw — legenda pod wykresem, żeby się nie nakładały.
            ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.0, -0.12), frameon=False,
                      fontsize=8, labelcolor=INK, ncol=len(handles))
        else:
            ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False,
                      fontsize=8, labelcolor=INK)
    fig.tight_layout()
    fig.savefig(out_path, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Przekrój wyniku symulacji -> PNG")
    parser.add_argument("folder", help="folder wyników (z ca_result.* i/lub mc_result.*)")
    parser.add_argument("--axis", choices=["x", "y", "z", "top"], default=None,
                        help="oś prostopadła do przekroju albo 'top' (widok z góry); domyślnie "
                             "płaszczyzna siatki 2D, a dla 3D — y")
    parser.add_argument("--index", type=int, default=None,
                        help="numer warstwy (domyślnie środek, a dla wymiaru 1 — zero)")
    parser.add_argument("--color", choices=["type", "flow", "temp", "cooling", "crystal"], default="type",
                        help="kolorowanie: typ komórki, krater (flowId), temperatura, czas w stanie "
                             "płynnym (cooling) albo kryształ MC")
    parser.add_argument("--boundaries", action="store_true",
                        help="tryb crystal: rysuj granice ziaren cienką linią")
    parser.add_argument("--crop", action="store_true",
                        help="przytnij obraz do obszaru lawy/bazaltu (z marginesem 3 komórek)")
    parser.add_argument("--window", type=int, nargs=4, default=None, metavar=("H0", "H1", "V0", "V1"),
                        help="wycinek przekroju: zakres osi poziomej [H0, H1) i pionowej [V0, V1) w komórkach")
    parser.add_argument("--ca", default=None,
                        help="tryb crystal: folder z ca_result.* (gdy wyniki MC są w innym folderze)")
    parser.add_argument("--title", default=None, help="własny tytuł rysunku")
    parser.add_argument("--out", default=None, help="plik PNG (domyślnie <folder>/slice.png)")
    args = parser.parse_args()

    if args.color == "crystal":
        crystal = read_crystals(args.folder)
        ca_dir = ca_folder_for(args.folder, args.ca)
        grid = read_result(ca_dir) if ca_dir else None
        if grid is None:
            # Tryb full (albo brak wyniku CA): cała domena MC jako „bazalt”, reszta powietrze.
            cell_type = np.where(crystal > 0, BASALT, AIR).astype(np.uint8)
            zeros = np.zeros(crystal.shape, np.int32)
            grid = {"type": cell_type, "flow": zeros, "temp": zeros.astype(np.float32)}
        if grid["type"].shape != crystal.shape:
            sys.exit(f"Wymiary mc_result {crystal.shape} różnią się od ca_result {grid['type'].shape}")
        grid["crystal"] = crystal
    else:
        grid = read_result(args.folder)
    if args.color == "cooling" and "solid" not in grid:
        sys.exit("Tryb cooling wymaga ca_result.bin (txt nie zawiera solidStep/arrivalStep)")

    axis = args.axis or default_axis(grid["type"].shape)
    planes, what, xlabel, ylabel = take_slice(grid, axis, args.index)
    offset = (0, 0)
    if args.crop:
        box = crop_box(planes)
        if box is not None:
            r0, r1, c0, c1 = box
            planes = {k: v[r0:r1, c0:c1] for k, v in planes.items()}
            offset = (r0, c0)
    if args.window:
        h0, h1, v0, v1 = args.window
        r0, c0 = offset
        h, w = planes["type"].shape
        rs, re_ = max(v0 - r0, 0), min(v1 - r0, h)
        cs, ce = max(h0 - c0, 0), min(h1 - c0, w)
        if rs >= re_ or cs >= ce:
            sys.exit("--window: wycinek poza przekrojem")
        planes = {k: v[rs:re_, cs:ce] for k, v in planes.items()}
        offset = (r0 + rs, c0 + cs)
    nz, ny, nx = grid["type"].shape
    name = os.path.basename(os.path.normpath(args.folder))
    title = args.title or f"{name}: {what} ({nx}×{ny}×{nz}), kolor: {args.color}"
    out_path = args.out or os.path.join(args.folder, "slice.png")
    flow_count = int(grid["flow"].max())
    render(planes, args.color, title, xlabel, ylabel, out_path, axis == "top", flow_count, args.boundaries, offset)
    print(f"Zapisano {out_path}")


if __name__ == "__main__":
    main()
