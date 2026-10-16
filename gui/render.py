"""Wycinanie danych do wizualizacji z tablic 3D (nz, ny, nx) — czyste funkcje numpy.

Przeglądarka nigdy nie dostaje całego bloku: tylko przekrój (2D), 6 ścian zewnętrznych, mapę
powierzchni albo ograniczoną liczbę wokseli. Tablice mogą być np.memmap — wycinek czyta z dysku
tylko potrzebne strony.

Orientacja zwracanych płaszczyzn: wiersz 0 = najmniejsza współrzędna osi pionowej obrazu
(przeglądarka rysuje go na dole), kolumna 0 = najmniejsza współrzędna osi poziomej:
  oś x (przekrój x = i): wiersze z, kolumny y
  oś y (przekrój y = i): wiersze z, kolumny x
  oś z (warstwa z = i):  wiersze y, kolumny x
"""

from __future__ import annotations

import math

import numpy as np

AIR, ROCK, LAVA, BASALT = 0, 1, 2, 3
MAX_PLANE_CELLS = 4_000_000  # większe płaszczyzny są próbkowane co `step` komórek w obu osiach

PLANE_AXES = {"x": ("y", "z"), "y": ("x", "z"), "z": ("x", "y")}  # oś -> (poziomo, pionowo)


def sampling_step(height: int, width: int, max_cells: int | None = None) -> int:
    """Krok próbkowania płaszczyzny: najmniejsze s, przy którym (h/s)·(w/s) <= max_cells
    (domyślnie MAX_PLANE_CELLS, czytane przy wywołaniu)."""
    max_cells = max_cells or MAX_PLANE_CELLS
    cells = height * width
    if cells <= max_cells:
        return 1
    return int(math.ceil(math.sqrt(cells / max_cells)))


def plane(arr, axis: str, index: int) -> np.ndarray:
    """Płaszczyzna prostopadła do osi `axis` na pozycji `index` (bez próbkowania)."""
    nz, ny, nx = arr.shape
    size = {"x": nx, "y": ny, "z": nz}[axis]
    if not 0 <= index < size:
        raise IndexError(f"indeks {index} poza zakresem 0..{size - 1} dla osi {axis}")
    if axis == "x":
        return arr[:, :, index]
    if axis == "y":
        return arr[:, index, :]
    return arr[index, :, :]


def slice_plane(arr, axis: str, index: int, max_cells: int | None = None) -> tuple[np.ndarray, int]:
    """Przekrój z próbkowaniem dużych płaszczyzn. Zwraca (ciągła tablica 2D, krok próbkowania)."""
    p = plane(arr, axis, index)
    step = sampling_step(p.shape[0], p.shape[1], max_cells)
    if step > 1:
        p = p[::step, ::step]
    return np.ascontiguousarray(p), step


def top_index(cell_type, value: int | None = None) -> np.ndarray:
    """Dla każdej kolumny (y, x): indeks z najwyższej niepustej komórki (typ != AIR), -1 gdy pusta;
    z value — najwyższej komórki tego typu (np. ROCK: teren bez lawy). Liczone warstwami od góry —
    pamięć pomocnicza to jedna warstwa, nie cały blok."""
    nz, ny, nx = cell_type.shape
    top = np.full((ny, nx), -1, dtype=np.int32)
    todo = np.ones((ny, nx), dtype=bool)
    for z in range(nz - 1, -1, -1):
        layer = np.asarray(cell_type[z])
        hit = todo & ((layer != AIR) if value is None else (layer == value))
        top[hit] = z
        todo &= ~hit
        if not todo.any():
            break
    return top


def surface_values(arr, top: np.ndarray) -> np.ndarray:
    """Wartość pola na wysokości `top` w każdej kolumnie (0 dla pustych kolumn)."""
    ny, nx = top.shape
    yy, xx = np.indices((ny, nx))
    zz = np.maximum(top, 0)
    vals = np.asarray(arr[zz, yy, xx])
    return np.where(top >= 0, vals, np.zeros((), dtype=vals.dtype)).astype(vals.dtype, copy=False)


FACE_ORDER = ("x0", "x1", "y0", "y1", "z0", "z1")


def face(arr, name: str) -> np.ndarray:
    """Ściana zewnętrzna bloku: x0 (x = 0), x1 (x = nx−1), y0, y1, z0 (spód), z1 (góra).
    Orientacja jak w plane(): x — wiersze z, kolumny y; y — wiersze z, kolumny x; z — wiersze y, kolumny x."""
    nz, ny, nx = arr.shape
    axis, last = name[0], name[1] == "1"
    index = {"x": nx, "y": ny, "z": nz}[axis] - 1 if last else 0
    return np.ascontiguousarray(plane(arr, axis, index))


def voxel_indices(cell_type, limit: int, crystal=None) -> tuple[np.ndarray, int, int]:
    """Indeksy płaskie wokseli lawy/bazaltu (albo domeny MC, gdy crystal podany i brak CA).
    Gdy jest ich więcej niż limit — co k-ty (deterministycznie). Zwraca (indeksy, wszystkie, krok)."""
    nz = cell_type.shape[0]
    chunks = []
    plane_cells = cell_type.shape[1] * cell_type.shape[2]
    for z in range(nz):  # warstwami — bez pełnej maski bloku w pamięci
        t = np.asarray(cell_type[z]).ravel()
        mask = (t == LAVA) | (t == BASALT)
        if crystal is not None:
            mask |= np.asarray(crystal[z]).ravel() > 0
        idx = np.flatnonzero(mask)
        if idx.size:
            chunks.append(idx + z * plane_cells)
    all_idx = np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.int64)
    total = int(all_idx.size)
    step = max(1, int(math.ceil(total / limit))) if limit > 0 else 1
    return all_idx[::step], total, step
