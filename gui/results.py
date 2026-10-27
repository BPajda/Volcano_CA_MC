"""Odczyt wyników symulacji dla GUI: lista wyników, dane do wizualizacji, czasy i statystyki.

Formaty (docs/uruchamianie.md, „Pliki wynikowe”):
  ca_result.bin  "VOLC", uint32 wersja (1|2), int32 nx ny nz, uint8 type[N], int32 flowId[N],
                 float temp[N], uint16 solidStep[N], (v2) uint16 arrivalStep[N]; indeks x + nx·(y + ny·z)
  ca_result.txt  "nx ny nz", nagłówek kolumn, wiersze "x y z type flowId temp"
  mc_result.bin  "VMC1", int32 nx ny nz, int32 crystal[N] (0 poza domeną)
  mc_result.txt  "nx ny nz", nagłówek, wiersze "x y z crystal"
  times.json, stats.json, mc_stats.csv (mcs,grains,meanGrainSize,energy,acceptRate), config_used.json

Duże pliki bin (> MEMMAP_MIN_BYTES) są mapowane w pamięć (np.memmap) — przekrój czyta z dysku tylko
potrzebne strony. Mniejsze są wczytywane do RAM: zmapowanego pliku Windows nie pozwala nadpisać, a wyniki
w results/ bywają nadpisywane z linii poleceń. Pliki txt (starsze uruchomienia) są parsowane w całości —
wolniej, ale wynik trafia do pamięci podręcznej (LRU, kilka ostatnio oglądanych wyników).
"""

from __future__ import annotations

import csv
import json
import struct
import threading
from collections import OrderedDict
from pathlib import Path

import numpy as np

from . import render, replay
from .render import AIR, BASALT, LAVA, ROCK

MEMMAP_MIN_BYTES = 128 * 1024 * 1024
TXT_MAX_CELLS = 30_000_000  # ~1,5 GB tymczasowo przy parsowaniu; większe wyniki tylko z .bin
MAX_ID_PARTS = 4            # gui/series/<seria>/<zadanie> — najgłębszy identyfikator wyniku
VENT_MASK_MAX_CELLS = 64_000_000   # maska kraterów (1 B/komórkę) do odtwarzania — powyżej kratery przybliżone
REPLAY_CELLS_LIMIT = 2_000_000     # komórek lawy w pakiecie odtwarzania 3D (22 B/komórkę); powyżej — próbkowanie kolumn

FIELDS = ("type", "flowId", "temp", "crystal", "cooling")
# Pola pochodne odtwarzania erupcji (etap 6, gui/replay.py): stan pojawienia się lawy i zastygnięcia — tylko do
# przekrojów/ścian/powierzchni dla przeglądarki, nie pojawiają się na liście pól podglądu.
REPLAY_FIELDS = ("appear", "solidFrom")
FIELD_DTYPES = {"type": "uint8", "flowId": "int32", "temp": "float32", "crystal": "int32", "cooling": "uint16",
                "height": "uint16", "terrain": "uint16", "appear": "int32", "solidFrom": "int32"}
RESULT_FILES = ("ca_result.bin", "ca_result.txt", "mc_result.bin", "mc_result.txt")


class ResultError(Exception):
    """Błąd odczytu / złe żądanie; status — kod HTTP."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


# ---------------------------------------------------------------------------- odczyt plików


def read_dims_header(folder: Path) -> tuple[tuple[int, int, int], str] | None:
    """Wymiary z nagłówka pierwszego pliku wyników (bez czytania danych) i opis formatu."""
    p = folder / "ca_result.bin"
    if p.is_file():
        with open(p, "rb") as f:
            hdr = f.read(20)
        if len(hdr) == 20 and hdr[:4] == b"VOLC":
            version, nx, ny, nz = struct.unpack("<4i", hdr[4:20])
            return (nx, ny, nz), f"bin v{version}"
    has_ca_txt = (folder / "ca_result.txt").is_file()
    p = folder / "mc_result.bin"
    if p.is_file() and not has_ca_txt:
        with open(p, "rb") as f:
            hdr = f.read(16)
        if len(hdr) == 16 and hdr[:4] == b"VMC1":
            return struct.unpack("<3i", hdr[4:16]), "bin"  # type: ignore[return-value]
    for name in ("ca_result.txt", "mc_result.txt"):
        p = folder / name
        if p.is_file():
            with open(p, "rb") as f:
                parts = f.readline().split()
            if len(parts) == 3:
                return tuple(int(v) for v in parts), "txt"  # type: ignore[return-value]
    return None


def _raw(path: Path, dtype: str, offset: int, shape: tuple[int, int, int], use_memmap: bool) -> np.ndarray:
    """Tablica z pliku binarnego: memmap (duże pliki) albo wczytana do RAM."""
    count = shape[0] * shape[1] * shape[2]
    if use_memmap:
        return np.memmap(path, dtype=dtype, mode="r", offset=offset, shape=shape)
    with open(path, "rb") as f:
        f.seek(offset)
        return np.fromfile(f, dtype=dtype, count=count).reshape(shape)


def _parse_txt(path: Path, columns: int) -> tuple[tuple[int, int, int], np.ndarray]:
    """Plik tekstowy wyników: (nx, ny, nz), tablica wierszy (n, columns) jako float64."""
    with open(path, "rb") as f:
        dims = tuple(int(v) for v in f.readline().split())
        if len(dims) != 3:
            raise ResultError(f"{path.name}: nieprawidłowy nagłówek wymiarów", 422)
        if dims[0] * dims[1] * dims[2] > TXT_MAX_CELLS:
            raise ResultError(f"{path.name}: {dims[0] * dims[1] * dims[2]:,} komórek, za dużo dla pliku txt; "
                              "uruchom symulację z output.format = bin", 422)
    # np.loadtxt (parser w C od numpy 1.23): ~0,6 s na 1 mln wierszy; np.fromfile(sep=" ") — ~16 s.
    try:
        data = np.loadtxt(path, skiprows=2, ndmin=2, dtype=np.float64)
    except ValueError as e:
        raise ResultError(f"{path.name}: błąd formatu danych: {e}", 422) from e
    if data.size and data.shape[1] != columns:
        raise ResultError(f"{path.name}: oczekiwano {columns} kolumn, jest {data.shape[1]}", 422)
    return dims, data.reshape(-1, columns)  # type: ignore[return-value]


def _txt_to_grid(dims, rows: np.ndarray, col: int, dtype) -> np.ndarray:
    nx, ny, nz = dims
    out = np.zeros(nx * ny * nz, dtype=dtype)
    idx = (rows[:, 0] + nx * (rows[:, 1] + ny * rows[:, 2])).astype(np.int64)
    if idx.size and (idx.min() < 0 or idx.max() >= out.size):
        raise ResultError("współrzędne w pliku txt poza przestrzenią", 422)
    out[idx] = rows[:, col]
    return out.reshape(nz, ny, nx)


class CaData:
    """Wynik CA: tablice (nz, ny, nx) type, flowId, temp, solidStep, arrivalStep (v2)."""

    def __init__(self, folder: Path):
        bin_path, txt_path = folder / "ca_result.bin", folder / "ca_result.txt"
        self.solid = self.arrival = None
        if bin_path.is_file():
            with open(bin_path, "rb") as f:
                hdr = f.read(20)
            if len(hdr) < 20 or hdr[:4] != b"VOLC":
                raise ResultError(f"{bin_path}: to nie jest plik wyników VOLC", 422)
            version, nx, ny, nz = struct.unpack("<4i", hdr[4:20])
            if version not in (1, 2):
                raise ResultError(f"{bin_path}: nieobsługiwana wersja {version}", 422)
            n = nx * ny * nz
            need = 20 + n * (11 + (2 if version >= 2 else 0))
            size = bin_path.stat().st_size
            if size < need:
                raise ResultError(f"{bin_path}: plik obcięty ({size} B, potrzeba {need} B)", 422)
            shape = (nz, ny, nx)
            mm = size > MEMMAP_MIN_BYTES
            self.type = _raw(bin_path, "u1", 20, shape, mm)
            self.flow = _raw(bin_path, "<i4", 20 + n, shape, mm)
            self.temp = _raw(bin_path, "<f4", 20 + 5 * n, shape, mm)
            self.solid = _raw(bin_path, "<u2", 20 + 9 * n, shape, mm)
            if version >= 2:
                self.arrival = _raw(bin_path, "<u2", 20 + 11 * n, shape, mm)
            self.source = f"ca_result.bin v{version}" + (" (memmap)" if mm else "")
            self.dims = (nx, ny, nz)
        elif txt_path.is_file():
            dims, rows = _parse_txt(txt_path, 6)
            self.type = _txt_to_grid(dims, rows, 3, np.uint8)
            self.flow = _txt_to_grid(dims, rows, 4, np.int32)
            self.temp = _txt_to_grid(dims, rows, 5, np.float32)
            self.source = "ca_result.txt"
            self.dims = dims
        else:
            raise ResultError(f"Brak ca_result.bin ani ca_result.txt w {folder}", 404)
        self.folder = folder


class McData:
    """Wynik MC: mapa kryształów (nz, ny, nx), 0 poza domeną."""

    def __init__(self, folder: Path):
        bin_path, txt_path = folder / "mc_result.bin", folder / "mc_result.txt"
        if bin_path.is_file():
            with open(bin_path, "rb") as f:
                hdr = f.read(16)
            if len(hdr) < 16 or hdr[:4] != b"VMC1":
                raise ResultError(f"{bin_path}: to nie jest plik kryształów VMC1", 422)
            nx, ny, nz = struct.unpack("<3i", hdr[4:16])
            size = bin_path.stat().st_size
            if size < 16 + 4 * nx * ny * nz:
                raise ResultError(f"{bin_path}: plik obcięty", 422)
            mm = size > MEMMAP_MIN_BYTES
            self.crystal = _raw(bin_path, "<i4", 16, (nz, ny, nx), mm)
            self.source = "mc_result.bin" + (" (memmap)" if mm else "")
            self.dims = (nx, ny, nz)
        elif txt_path.is_file():
            dims, rows = _parse_txt(txt_path, 4)
            self.crystal = _txt_to_grid(dims, rows, 3, np.int32)
            self.source = "mc_result.txt"
            self.dims = dims
        else:
            raise ResultError(f"Brak mc_result.bin ani mc_result.txt w {folder}", 404)


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def _numbered(folder: Path, prefix: str) -> list[int]:
    """Numery plików <prefix><numer>.bin w folderze (migawki), rosnąco."""
    out = []
    if folder.is_dir():
        for p in folder.glob(f"{prefix}*.bin"):
            tail = p.stem[len(prefix):]
            if tail.isdigit():
                out.append(int(tail))
    return sorted(out)


def read_mc_stats(path: Path) -> dict | None:
    """mc_stats.csv -> {"mcs": [...], "grains": [...], ...} (kolumny jako listy liczb)."""
    if not path.is_file():
        return None
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return None
    return {k: [float(r[k]) if "." in r[k] or "e" in r[k].lower() else int(r[k]) for r in rows] for k in rows[0]}


# ---------------------------------------------------------------------------- jeden wynik


class ResultData:
    """Wczytany wynik: CA (z tego folderu albo z folderu wejściowego MC — _mcFrom) i/lub MC."""

    def __init__(self, rid: str, folder: Path):
        self.rid, self.folder = rid, folder
        self.ca: CaData | None = None
        self.mc: McData | None = None
        self.ca_folder: Path | None = None
        if any((folder / n).is_file() for n in ("ca_result.bin", "ca_result.txt")):
            self.ca, self.ca_folder = CaData(folder), folder
        if any((folder / n).is_file() for n in ("mc_result.bin", "mc_result.txt")):
            self.mc = McData(folder)
            if self.ca is None:
                # MC uruchomione z --mc-from: typy komórek z folderu wejściowego (jak plot_slice.py).
                cfg = _read_json(folder / "config_used.json") or {}
                src = cfg.get("_mcFrom")
                if src and Path(src).is_dir():
                    try:
                        ca = CaData(Path(src))
                        if ca.dims == self.mc.dims:
                            self.ca, self.ca_folder = ca, Path(src)
                    except ResultError:
                        pass
        if self.ca is None and self.mc is None:
            raise ResultError(f"W folderze {folder.name} nie ma wyników (ca_result.* / mc_result.*)", 404)
        self.dims = self.ca.dims if self.ca is not None else self.mc.dims  # type: ignore[union-attr]
        if self.ca is not None:
            self.type = self.ca.type
        else:
            # Tryb MC full: cała domena jako „bazalt”, reszta powietrze.
            self.type = np.where(np.asarray(self.mc.crystal) > 0, BASALT, AIR).astype(np.uint8)  # type: ignore
        self._top: np.ndarray | None = None
        self._ranges: dict | None = None
        self._cooling_end: int | None = None
        self._vents: list | None = None
        self._vents_read = False
        self._vent_mask: np.ndarray | None = None
        self._replay_info: dict | None = None
        self._mc_snaps: OrderedDict[int, np.ndarray] = OrderedDict()
        self._lock = threading.Lock()

    # --- pola

    def fields(self) -> list[str]:
        out = ["type"]
        if self.ca is not None:
            out += ["flowId", "temp"]
        if self.mc is not None:
            out.append("crystal")
        if self.ca is not None and self.ca.arrival is not None:
            out.append("cooling")
        return out

    def _array(self, field: str, mcs: int | None = None):
        if field == "type":
            return self.type
        if field == "flowId" and self.ca is not None:
            return self.ca.flow
        if field == "temp" and self.ca is not None:
            return self.ca.temp
        if field == "crystal" and self.mc is not None:
            return self.mc.crystal if mcs is None else self.mc_snapshot(mcs)
        raise ResultError(f"Pole „{field}” nie jest dostępne w tym wyniku (dostępne: {', '.join(self.fields())})")

    def cooling_end(self) -> int:
        """Ostatni krok CA — czas płynięcia lawy, która nie zastygła, liczony do niego (jak w MC)."""
        if self._cooling_end is None:
            ca = self.ca
            assert ca is not None and ca.solid is not None and ca.arrival is not None
            self._cooling_end = int(max(np.max(ca.solid), np.max(ca.arrival)))
        return self._cooling_end

    def extract(self, field: str, fn, mcs: int | None = None) -> np.ndarray:
        """Wycinek pola: fn(tablica 3D) -> tablica. Pole cooling = solidStep − arrivalStep (bazalt),
        koniec CA − arrivalStep (płynna lawa), 0 poza lawą — liczone tylko dla wycinka. Pola odtwarzania
        appear / solidFrom (gui/replay.py) też liczone tylko dla wycinka. mcs — kryształy z migawki MC."""
        if field == "cooling":
            if "cooling" not in self.fields():
                raise ResultError("Czas stygnięcia wymaga ca_result.bin w wersji 2 (z arrivalStep)")
            ca = self.ca
            t = np.asarray(fn(self.type))
            s = np.asarray(fn(ca.solid)).astype(np.int32)  # type: ignore[union-attr]
            a = np.asarray(fn(ca.arrival)).astype(np.int32)  # type: ignore[union-attr]
            c = np.where(t == BASALT, s - a, np.where(t == LAVA, self.cooling_end() - a, 0))
            return np.clip(c, 0, 65535).astype(np.uint16)
        if field in REPLAY_FIELDS:
            self._require_replay()
            ca = self.ca
            t = np.asarray(fn(self.type))
            if field == "solidFrom":
                return replay.solid_from(t, np.asarray(fn(ca.solid)))  # type: ignore[union-attr]
            vm = self.vent_mask()
            return replay.appear_steps(t, np.asarray(fn(ca.arrival)),  # type: ignore[union-attr]
                                       np.asarray(fn(vm)) if vm is not None else None)
        return np.asarray(fn(self._array(field, mcs)))

    # --- odtwarzanie erupcji krok po kroku (etap 6)

    def _require_replay(self) -> None:
        if self.ca is None or self.ca.arrival is None:
            raise ResultError("Odtwarzanie erupcji wymaga ca_result.bin w wersji 2 (z arrivalStep i solidStep); "
                              "uruchom symulację z output.format = bin")

    def vents(self) -> list | None:
        """Kratery / zarodki [[x, y, z], ...] ze stats.json (flows[].vent); None, gdy lista nieznana albo obcięta."""
        if not self._vents_read:
            stats = _read_json((self.ca_folder or self.folder) / "stats.json") or {}
            flows = stats.get("flows")
            if isinstance(flows, list) and flows and not stats.get("flowsTruncated"):
                try:
                    self._vents = [[int(c) for c in f["vent"][:3]] for f in flows]
                except (KeyError, TypeError, ValueError):
                    self._vents = None
            self._vents_read = True
        return self._vents

    def vent_mask(self) -> np.ndarray | None:
        """Maska kraterów (nz, ny, nx) — kratery pojawiają się w stanie 0 (gui/replay.py). None: lista kraterów
        nieznana albo wynik za duży (> VENT_MASK_MAX_CELLS) — wtedy komórki z arrivalStep = 0 też w stanie 0."""
        nx, ny, nz = self.dims
        if self._vent_mask is None and nx * ny * nz <= VENT_MASK_MAX_CELLS:
            self._vent_mask = replay.vent_mask((nz, ny, nx), self.vents())
        return self._vent_mask

    def replay_steps(self) -> int:
        """Liczba kroków CA (stan końcowy = stan po tylu krokach): stats.json / times.json albo z tablic."""
        folder = self.ca_folder or self.folder
        for name in ("stats.json", "times.json"):
            v = (_read_json(folder / name) or {}).get("steps")
            if isinstance(v, int) and v >= 0:
                return v
        return int(self.cooling_end()) + 1

    def replay_info(self) -> dict:
        """Opis odtwarzania: kroki, parametry stygnięcia, liczba komórek płynnych/zastygłych w każdym stanie,
        kratery, dostępne migawki CA i MC. Liczone warstwami (memmap nie trafia cały do RAM), pamiętane."""
        self._require_replay()
        with self._lock:
            if self._replay_info is not None:
                return self._replay_info
        steps = self.replay_steps()
        cfg = _read_json((self.ca_folder or self.folder) / "config_used.json") or {}
        ca_cfg, vents_cfg = cfg.get("ca", {}) or {}, cfg.get("vents", {}) or {}
        vm = self.vent_mask()
        liquid = np.zeros(steps + 1, dtype=np.int64)
        solid = np.zeros(steps + 1, dtype=np.int64)
        live_cells = 0
        ca = self.ca
        for z in range(self.dims[2]):
            t = np.asarray(self.type[z])
            live = (t == LAVA) | (t == BASALT)
            if not live.any():
                continue
            live_cells += int(live.sum())
            a = replay.appear_steps(t, np.asarray(ca.arrival[z]), vm[z] if vm is not None else None)  # type: ignore
            s = replay.solid_from(t, np.asarray(ca.solid[z]))  # type: ignore[union-attr]
            lq, sd = replay.counts_per_step(a, s, steps)
            liquid += lq
            solid += sd
        info = {
            "id": self.rid, "mode": cfg.get("ca", {}).get("mode", "lava"), "steps": steps,
            "dims": list(self.dims), "liveCells": live_cells,
            "params": {"coolingAmbient": float(ca_cfg.get("coolingAmbient", 0.3)),
                       "eruptTemp": float(vents_cfg.get("eruptTemp", 1200)),
                       "eruptionSteps": int(vents_cfg.get("eruptionSteps", 300)),
                       "solidusTemp": float(ca_cfg.get("solidusTemp", 800))},
            "vents": self.vents(), "ventsExact": vm is not None and self.vents() is not None,
            "liquid": liquid.tolist(), "solid": solid.tolist(),
            "snapshots": self.snapshot_steps(), "mcSnapshots": self.mc_snapshot_steps(),
            "replayCellsLimit": REPLAY_CELLS_LIMIT,
        }
        with self._lock:
            self._replay_info = info
        return info

    def replay_cells(self, limit: int = REPLAY_CELLS_LIMIT) -> dict:
        """Wszystkie komórki lawy/bazaltu wyniku końcowego do odtwarzania 3D: xyz, pojawienie, zastygnięcie,
        temperatura końcowa, flowId. Gdy jest ich więcej niż limit — tylko kolumny co `step` w x i y
        (próbkowanie kolumn zachowuje całe kolumny, więc powierzchnia w kroku k jest poprawna w próbkach)."""
        self._require_replay()
        nx, ny, nz = self.dims
        total = self.replay_info()["liveCells"]
        step = max(1, int(np.ceil(np.sqrt(total / limit)))) if limit > 0 and total > limit else 1
        vm = self.vent_mask()
        ca = self.ca
        parts: dict[str, list] = {k: [] for k in ("x", "y", "z", "appear", "solidFrom", "temp", "flow")}
        yy, xx = np.indices((ny, nx))
        keep = (xx % step == 0) & (yy % step == 0)
        for z in range(nz):
            t = np.asarray(self.type[z])
            live = ((t == LAVA) | (t == BASALT)) & keep
            if not live.any():
                continue
            ys, xs = np.nonzero(live)
            a = replay.appear_steps(t, np.asarray(ca.arrival[z]), vm[z] if vm is not None else None)  # type: ignore
            s = replay.solid_from(t, np.asarray(ca.solid[z]))  # type: ignore[union-attr]
            parts["x"].append(xs)
            parts["y"].append(ys)
            parts["z"].append(np.full(xs.size, z))
            parts["appear"].append(a[live])
            parts["solidFrom"].append(s[live])
            parts["temp"].append(np.asarray(ca.temp[z])[live])  # type: ignore[union-attr]
            parts["flow"].append(np.asarray(ca.flow[z])[live])  # type: ignore[union-attr]

        def cat(key, dtype):
            return np.concatenate(parts[key]).astype(dtype) if parts[key] else np.zeros(0, dtype=dtype)

        xyz = np.stack([cat("x", np.uint16), cat("y", np.uint16), cat("z", np.uint16)], axis=1)
        return {"xyz": np.ascontiguousarray(xyz), "appear": cat("appear", np.int32), "solidFrom": cat("solidFrom", np.int32),
                "temp": cat("temp", np.float32), "flowId": cat("flow", np.int32), "total": total, "step": step}

    def snapshot_steps(self) -> list[int]:
        """Kroki migawek CA (snapshots/step_<k>.bin, output.snapshotsEvery)."""
        return _numbered((self.ca_folder or self.folder) / "snapshots", "step_")

    def mc_snapshot_steps(self) -> list[int]:
        """Kroki MCS migawek kryształów (mc_snapshots/mcs_<k>.bin, mc.snapshotsEvery)."""
        return _numbered(self.folder / "mc_snapshots", "mcs_") if self.mc is not None else []

    def mc_snapshot(self, mcs: int) -> np.ndarray:
        """Mapa kryształów (nz, ny, nx) z migawki MCS — kilka ostatnich w pamięci."""
        with self._lock:
            hit = self._mc_snaps.get(mcs)
            if hit is not None:
                self._mc_snaps.move_to_end(mcs)
                return hit
        path = self.folder / "mc_snapshots" / f"mcs_{mcs:06d}.bin"
        if not path.is_file():
            raise ResultError(f"Brak migawki MC dla MCS {mcs} (mc_snapshots/{path.name})", 404)
        with open(path, "rb") as f:
            hdr = f.read(16)
        nx, ny, nz = self.dims
        if len(hdr) < 16 or hdr[:4] != b"VMC1" or struct.unpack("<3i", hdr[4:16]) != (nx, ny, nz):
            raise ResultError(f"{path.name}: to nie jest migawka kryształów tego wyniku", 422)
        arr = _raw(path, "<i4", 16, (nz, ny, nx), path.stat().st_size > MEMMAP_MIN_BYTES)
        with self._lock:
            self._mc_snaps[mcs] = arr
            while len(self._mc_snaps) > 8:
                self._mc_snaps.popitem(last=False)
        return arr

    # --- wycinki do wizualizacji

    def slice(self, field: str, axis: str, index: int, max_side: int | None = None,
              mcs: int | None = None) -> tuple[np.ndarray, int]:
        """Przekrój pola; max_side — miniatura: próbkowanie tak, by dłuższy bok miał ≤ max_side komórek;
        mcs — kryształy z migawki MC (odtwarzanie wzrostu ziaren)."""
        if axis not in ("x", "y", "z"):
            raise ResultError("oś musi być x, y albo z")
        try:
            plane = render.plane(self.type, axis, index)  # sprawdzenie zakresu indeksu
        except IndexError as e:
            raise ResultError(str(e)) from e
        step_box: list[int] = []
        thumb_step = max(1, -(-max(plane.shape) // max_side)) if max_side else 1

        def fn(arr):
            if thumb_step > render.sampling_step(*plane.shape):
                p, step = np.ascontiguousarray(render.plane(arr, axis, index)[::thumb_step, ::thumb_step]), thumb_step
            else:
                p, step = render.slice_plane(arr, axis, index)
            step_box.append(step)
            return p

        data = self.extract(field, fn, mcs)
        return np.ascontiguousarray(data), step_box[0]

    def top(self) -> np.ndarray:
        """Indeks z najwyższej niepustej komórki w każdej kolumnie (pamiętany)."""
        with self._lock:
            if self._top is None:
                self._top = render.top_index(self.type)
            return self._top

    def surface(self, field: str, mcs: int | None = None) -> np.ndarray:
        """Mapa powierzchni: height — wysokość najwyższej niepustej komórki (+1), terrain — wysokość samej
        skały (teren bez lawy, do odtwarzania erupcji), inne pola — wartość w najwyższej niepustej komórce."""
        if field == "terrain":
            return (render.top_index(self.type, ROCK) + 1).astype(np.uint16)
        top = self.top()
        if field == "height":
            return (top + 1).astype(np.uint16)
        return self.extract(field, lambda arr: render.surface_values(arr, top), mcs)

    def faces(self, field: str, top_surface: bool, mcs: int | None = None) -> list[tuple[str, np.ndarray]]:
        """6 ścian zewnętrznych (render.FACE_ORDER). top_surface — zamiast warstwy z = nz−1 (u wulkanu
        prawie samo powietrze) rzut z góry: pole w najwyższej niepustej komórce każdej kolumny."""
        out = []
        for name in render.FACE_ORDER:
            if name == "z1" and top_surface:
                topi = self.top()
                p = self.extract(field, lambda arr: render.surface_values(arr, topi), mcs)
            else:
                p = self.extract(field, lambda arr, n=name: render.face(arr, n), mcs)
            out.append((name, np.ascontiguousarray(p)))
        return out

    def voxels(self, field: str, limit: int) -> tuple[np.ndarray, np.ndarray, int, int]:
        """Woksele lawy/bazaltu (albo domeny MC): (xyz uint16 [k,3], wartości pola, wszystkie, krok)."""
        crystal = self.mc.crystal if (self.ca is None and self.mc is not None) else None
        idx, total, step = render.voxel_indices(self.type, limit, crystal)
        nx, ny, _ = self.dims
        xyz = np.stack([idx % nx, (idx // nx) % ny, idx // (nx * ny)], axis=1).astype(np.uint16)
        vals = self.extract(field, lambda arr: np.asarray(arr).reshape(-1)[idx])
        return np.ascontiguousarray(xyz), np.ascontiguousarray(vals), total, step

    def cell(self, x: int, y: int, z: int) -> dict:
        nx, ny, nz = self.dims
        if not (0 <= x < nx and 0 <= y < ny and 0 <= z < nz):
            raise ResultError(f"komórka ({x}, {y}, {z}) poza przestrzenią {nx}×{ny}×{nz}")
        out: dict = {"x": x, "y": y, "z": z}
        for f in self.fields():
            v = self.extract(f, lambda arr: np.asarray(arr[z, y, x]))
            out[f] = v.item()
        return out

    # --- zakresy wartości (stałe skale kolorów dla wszystkich przekrojów)

    def ranges(self) -> dict:
        with self._lock:
            if self._ranges is not None:
                return self._ranges
            r: dict = {}
            nz = self.dims[2]
            if self.ca is not None:
                lo, hi, fmax = np.inf, -np.inf, 0
                for z in range(nz):  # warstwami — memmap nie trafia cały do RAM
                    t = np.asarray(self.type[z])
                    live = (t == LAVA) | (t == BASALT)
                    fmax = max(fmax, int(np.asarray(self.ca.flow[z]).max(initial=0)))
                    if live.any():
                        tv = np.asarray(self.ca.temp[z])[live]
                        lo, hi = min(lo, float(tv.min())), max(hi, float(tv.max()))
                r["temp"] = [lo, hi] if np.isfinite(lo) else [0.0, 0.0]
                r["flowId"] = [0, fmax]
            if self.mc is not None:
                r["crystal"] = [0, int(np.asarray(self.mc.crystal).max(initial=0))]
            if "cooling" in self.fields():
                lo, hi = np.inf, -np.inf
                for z in range(nz):
                    c = self.extract("cooling", lambda arr, z=z: arr[z])
                    t = np.asarray(self.type[z])
                    live = (t == LAVA) | (t == BASALT)
                    if live.any():
                        lo, hi = min(lo, int(c[live].min())), max(hi, int(c[live].max()))
                r["cooling"] = [int(lo), int(hi)] if np.isfinite(lo) else [0, 0]
            self._ranges = r
            return r


# ---------------------------------------------------------------------------- magazyn wyników


def _signature(folder: Path) -> tuple:
    """Rozmiary i czasy modyfikacji plików wyników — zmiana = wynik trzeba wczytać od nowa."""
    sig = []
    for name in RESULT_FILES + ("times.json", "config_used.json"):
        p = folder / name
        if p.is_file():
            st = p.stat()
            sig.append((name, st.st_size, st.st_mtime_ns))
    return tuple(sig)


def _has_results(folder: Path) -> bool:
    return any((folder / n).is_file() for n in RESULT_FILES)


class ResultStore:
    """Lista wyników w results/ (także results/gui/*) i pamięć podręczna wczytanych wyników (LRU)."""

    def __init__(self, results_dir: Path, cache_size: int = 4):
        self.results_dir = results_dir
        self.cache_size = cache_size
        self._cache: OrderedDict[str, tuple[tuple, ResultData]] = OrderedDict()
        self._summaries: dict[str, tuple[tuple, dict]] = {}
        self._lock = threading.Lock()

    def resolve(self, rid: str) -> Path:
        """Identyfikator wyniku (np. "test_3d", "gui/20261009-120000_test", "gui/series/<seria>/01_x"
        albo "series/<seria>/01_x" po engine --batch) -> folder. Najwyżej MAX_ID_PARTS członów.
        Nie pozwala wyjść poza results/ (.., ścieżki bezwzględne, dyski, dowiązania)."""
        if not rid or len(rid) > 300:
            raise ResultError("Brak identyfikatora wyniku")
        parts = rid.replace("\\", "/").split("/")
        if any(p in ("", ".", "..") or ":" in p for p in parts) or len(parts) > MAX_ID_PARTS:
            raise ResultError(f"Nieprawidłowy identyfikator wyniku: {rid}")
        base = self.results_dir.resolve()
        folder = (base / Path(*parts)).resolve()
        try:
            folder.relative_to(base)
        except ValueError:
            raise ResultError(f"Nieprawidłowy identyfikator wyniku: {rid}") from None
        if not folder.is_dir() or not _has_results(folder):
            raise ResultError(f"Nie ma wyniku {rid}", 404)
        return folder

    def load(self, rid: str) -> ResultData:
        folder = self.resolve(rid)
        sig = _signature(folder)
        with self._lock:
            hit = self._cache.get(rid)
            if hit is not None and hit[0] == sig:
                self._cache.move_to_end(rid)
                return hit[1]
            data = ResultData(rid, folder)
            self._cache[rid] = (sig, data)
            self._cache.move_to_end(rid)
            while len(self._cache) > self.cache_size:
                self._cache.popitem(last=False)
            return data

    def _candidates(self) -> list[tuple[str, Path]]:
        """Foldery z wynikami do MAX_ID_PARTS poziomów w głąb: results/<x>, results/gui/<id>,
        results/gui/series/<seria>/<zadanie>, results/<seria z --batch>/<config>… Folder z wynikiem
        nie jest przeszukiwany dalej (np. snapshots/)."""
        out: list[tuple[str, Path]] = []

        def visit(d: Path, parts: list[str]) -> None:
            for sub in sorted(d.iterdir()):
                if not sub.is_dir():
                    continue
                if _has_results(sub):
                    out.append(("/".join(parts + [sub.name]), sub))
                elif len(parts) + 1 < MAX_ID_PARTS:
                    visit(sub, parts + [sub.name])

        if self.results_dir.is_dir():
            visit(self.results_dir, [])
        return out

    def list(self) -> list[dict]:
        items = []
        for rid, folder in self._candidates():
            sig = _signature(folder)
            cached = self._summaries.get(rid)
            if cached is None or cached[0] != sig:
                try:
                    cached = (sig, self.summarize(rid, folder))
                except (OSError, ResultError, ValueError) as e:
                    cached = (sig, {"id": rid, "name": folder.name, "error": str(e)})
                self._summaries[rid] = cached
            items.append(cached[1])
        return items

    def summarize(self, rid: str, folder: Path) -> dict:
        """Opis wyniku do listy — tylko małe pliki i nagłówki (bez wczytywania danych)."""
        times = _read_json(folder / "times.json") or {}
        cfg = _read_json(folder / "config_used.json") or {}
        job = _read_json(folder / "gui_job.json") or {}
        hdr = read_dims_header(folder)
        dims = list(hdr[0]) if hdr else times.get("space")
        files = []
        mtime = 0.0
        for p in sorted(folder.iterdir()):
            if p.is_file():
                st = p.stat()
                files.append({"name": p.name, "size": st.st_size})
                if p.name in RESULT_FILES:
                    mtime = max(mtime, st.st_mtime)
        mode = times.get("mode")
        if mode is None and cfg:
            mc = cfg.get("mc", {})
            mode = "mc_full" if mc.get("enabled") and mc.get("domain") == "full" else cfg.get("ca", {}).get("mode")
        has_mc = (folder / "mc_result.bin").is_file() or (folder / "mc_result.txt").is_file()
        # Wynik należący do serii (etap 5): folder nadrzędny ma series.json albo batch_summary.csv.
        parent = folder.parent
        series = None
        if "/" in rid and ((parent / "series.json").is_file() or (parent / "batch_summary.csv").is_file()):
            series = rid.rsplit("/", 1)[0]
        return {
            "id": rid,
            "name": job.get("name") or (f"{parent.name} / {folder.name}" if series else folder.name),
            "gui": rid.startswith("gui/"),
            "series": series,
            "dims": dims,
            "cells": (dims[0] * dims[1] * dims[2]) if dims else None,
            "mode": mode,
            "hasCa": (folder / "ca_result.bin").is_file() or (folder / "ca_result.txt").is_file(),
            "hasMc": has_mc,
            "format": hdr[1] if hdr else None,
            "neighborhood": times.get("neighborhood", cfg.get("neighborhood")),
            "boundary": times.get("boundary", cfg.get("boundary")),
            "vents": cfg.get("vents", {}).get("count") if cfg else None,
            "steps": times.get("steps"),
            "mcs": times.get("mcs"),
            "times": {k: times.get(k) for k in ("caSim", "mcSim", "total") if k in times},
            "files": files,
            "size": sum(f["size"] for f in files),
            "modified": mtime,
        }

    def details(self, rid: str) -> dict:
        """Czasy, statystyki i config wyniku (zakładka „Czasy i statystyki”)."""
        folder = self.resolve(rid)
        stats = _read_json(folder / "stats.json")
        if isinstance(stats, dict):
            # Historia aktywnych komórek bywa długa (do 65535 kroków) — do GUI wystarczy co n-ta wartość.
            for key in ("activeCells", "changedCells"):
                seq = stats.get(key)
                if isinstance(seq, list) and len(seq) > 2000:
                    step = -(-len(seq) // 2000)
                    stats[key] = seq[::step]
                    stats[key + "Step"] = step
        return {
            "id": rid,
            "times": _read_json(folder / "times.json"),
            "stats": stats,
            "mcStats": read_mc_stats(folder / "mc_stats.csv"),
            "config": _read_json(folder / "config_used.json"),
            "job": _read_json(folder / "gui_job.json"),
            "summary": self.summarize(rid, folder),
        }
