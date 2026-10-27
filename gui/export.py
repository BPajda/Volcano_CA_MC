"""Eksport wyników (etap 5): ZIP folderu wyniku i plik VTK ImageData (.vti) dla ParaView.

ZIP (zip_result): wszystkie pliki folderu wyniku — config_used.json, ca_result.*, mc_result.*, times.json,
stats.json, mc_stats.csv, engine.log, gui_job.json (i migawki snapshots/, jeśli są) — kompresja deflate.

VTK (write_vti): format wymiany z zewnętrznymi narzędziami wizualizacji (ParaView, VisIt, VTK).
Wynik CA/MC to regularna siatka wokseli, więc pasuje do niej typ ImageData: Extent 0..nx × 0..ny × 0..nz
(punkty), a wartości są polami KOMÓREK (CellData) — każda komórka symulacji to jeden woksel o boku 1.
Kolejność komórek w VTK (x najszybciej, potem y, potem z) jest taka sama jak w plikach .bin
(indeks x + nx·(y + ny·z)), więc tablice zapisujemy bez przestawiania.
Pola: type (UInt8), flowId (Int32), temp (Float32), solidStep, arrivalStep (UInt16, z ca_result.bin),
cooling (UInt16, czas w stanie płynnym — jak w GUI), crystal (Int32, z mc_result.*).
Kodowanie (fmt):
  zlib   — (domyślne) base64 wewnątrz XML, dane skompresowane zlib w blokach po 64 KiB
           (compressor="vtkZLibDataCompressor"); nagłówek UInt64: liczba bloków, rozmiar bloku, rozmiar
           ostatniego bloku, rozmiary bloków po kompresji. Wyniki to głównie zera (powietrze, brak kryształu),
           więc plik jest wielokrotnie mniejszy;
  binary — base64 bez kompresji; przed danymi nagłówek UInt64 z liczbą bajtów;
  ascii  — liczby tekstem (czytelne, ale duże; dla małych siatek).
W obu wariantach base64 nagłówek i dane są kodowane OSOBNO (tak zapisuje sam VTK i meshio) — czytnik
VTK najpierw dekoduje nagłówek (znana liczba bajtów), a potem od nowa dane.
Plik jest poprawnym XML-em, więc test sprawdza go zwykłym parserem (xml.etree) i porównuje tablice
z danymi źródłowymi; dodatkowo sprawdziłem go czytnikiem VTK z ParaView (pvpython, docs/kolejka-serie-dane.md).
"""

from __future__ import annotations

import base64
import os
import tempfile
import zipfile
import zlib
from pathlib import Path

import numpy as np

from .results import ResultData

VTK_TYPES = {"uint8": "UInt8", "uint16": "UInt16", "int32": "Int32", "float32": "Float32"}
_CHUNK = 3 * 1024 * 1024  # wielokrotność 3 B — kolejne fragmenty base64 łączą się bez znaków „=”
_BLOCK = 64 * 1024       # rozmiar bloku przed kompresją (fmt = zlib)
FORMATS = ("zlib", "binary", "ascii")


def vti_fields(data: ResultData) -> list[tuple[str, np.ndarray]]:
    """Pola do zapisu: (nazwa, tablica (nz, ny, nx)) — tylko dostępne w wyniku."""
    out: list[tuple[str, np.ndarray]] = [("type", data.type)]
    if data.ca is not None:
        out += [("flowId", data.ca.flow), ("temp", data.ca.temp)]
        if data.ca.solid is not None:
            out.append(("solidStep", data.ca.solid))
        if data.ca.arrival is not None:
            out.append(("arrivalStep", data.ca.arrival))
    if "cooling" in data.fields():
        out.append(("cooling", None))  # liczone warstwami przy zapisie (bez całego bloku w pamięci)
    if data.mc is not None:
        out.append(("crystal", data.mc.crystal))
    return out


def _layers(data: ResultData, name: str, arr):
    """Kolejne warstwy z pola (z = 0..nz−1) jako tablice little-endian."""
    nz = data.dims[2]
    for z in range(nz):
        if name == "cooling":
            layer = data.extract("cooling", lambda a, z=z: a[z])
        else:
            layer = np.asarray(arr[z])
        yield np.ascontiguousarray(layer, dtype=layer.dtype.newbyteorder("<"))


def _write_base64(f, chunks) -> None:
    """Strumień bajtów -> base64 w fragmentach (wielokrotności 3 B, więc bez „=” w środku)."""
    pending = bytearray()
    for chunk in chunks:
        pending += chunk
        cut = len(pending) - len(pending) % 3
        if cut >= _CHUNK:
            f.write(base64.b64encode(pending[:cut]).decode("ascii"))
            del pending[:cut]
    f.write(base64.b64encode(bytes(pending)).decode("ascii"))


def _blocks(layers, size: int):
    """Warstwy -> kolejne bloki po `size` bajtów (ostatni krótszy)."""
    pending = bytearray()
    for layer in layers:
        pending += layer.tobytes()
        while len(pending) >= size:
            yield bytes(pending[:size])
            del pending[:size]
    if pending:
        yield bytes(pending)


def write_vti(data: ResultData, path: Path, fmt: str = "zlib") -> Path:
    """Zapis wyniku do pliku .vti (ImageData, CellData). fmt: zlib (domyślnie), binary albo ascii."""
    if fmt not in FORMATS:
        raise ValueError(f"format VTK: {', '.join(FORMATS)}")
    nx, ny, nz = data.dims
    fields = vti_fields(data)
    scalars = "crystal" if data.mc is not None else "type"
    compressor = ' compressor="vtkZLibDataCompressor"' if fmt == "zlib" else ""
    with open(path, "w", encoding="ascii", newline="\n") as f:
        f.write('<?xml version="1.0"?>\n')
        f.write('<VTKFile type="ImageData" version="1.0" byte_order="LittleEndian" header_type="UInt64"'
                f'{compressor}>\n')
        f.write(f'  <ImageData WholeExtent="0 {nx} 0 {ny} 0 {nz}" Origin="0 0 0" Spacing="1 1 1">\n')
        f.write(f'    <Piece Extent="0 {nx} 0 {ny} 0 {nz}">\n')
        f.write(f'      <CellData Scalars="{scalars}">\n')
        for name, arr in fields:
            dtype = np.dtype(np.uint16 if name == "cooling" else np.asarray(arr[0:1]).dtype)
            vtype = VTK_TYPES[dtype.name]
            encoding = "ascii" if fmt == "ascii" else "binary"
            f.write(f'        <DataArray type="{vtype}" Name="{name}" format="{encoding}">\n')
            if fmt == "zlib":
                comp = [zlib.compress(b, 6) for b in _blocks(_layers(data, name, arr), _BLOCK)]
                total = nx * ny * nz * dtype.itemsize
                last = total - (len(comp) - 1) * _BLOCK if comp else 0
                header = np.array([len(comp), _BLOCK, last, *[len(c) for c in comp]], dtype="<u8")
                f.write(base64.b64encode(header.tobytes()).decode("ascii"))
                _write_base64(f, comp)
                f.write("\n")
            elif fmt == "binary":
                f.write(base64.b64encode(np.uint64(nx * ny * nz * dtype.itemsize).tobytes()).decode("ascii"))
                _write_base64(f, (layer.tobytes() for layer in _layers(data, name, arr)))
                f.write("\n")
            else:
                spec = "%.9g" if vtype == "Float32" else "%d"   # %.9g — float32 bez utraty dokładności
                for layer in _layers(data, name, arr):
                    np.savetxt(f, layer.reshape(-1, nx), fmt=spec, delimiter=" ")
            f.write("        </DataArray>\n")
        f.write("      </CellData>\n    </Piece>\n  </ImageData>\n</VTKFile>\n")
    return path


def zip_result(folder: Path, arcname: str) -> Path:
    """ZIP wszystkich plików folderu wyniku (rekurencyjnie) w pliku tymczasowym — do pobrania z GUI.
    Wywołujący usuwa plik po wysłaniu."""
    fd, tmp = tempfile.mkstemp(prefix="volcano_", suffix=".zip")
    os.close(fd)
    try:
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for p in sorted(folder.rglob("*")):
                if p.is_file():
                    z.write(p, f"{arcname}/{p.relative_to(folder).as_posix()}")
    except BaseException:
        os.unlink(tmp)
        raise
    return Path(tmp)
