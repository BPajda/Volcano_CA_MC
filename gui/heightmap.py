"""Mapy wysokości terenu (terrain.type = "file") — import z GUI i z linii poleceń (etap 5).

Format CSV czytany przez silnik (engine/src/terrain/HeightmapLoader.cpp): ny wierszy × nx wartości,
wiersz k to y = k, kolumna i to x = i; wartość = wysokość terenu w komórkach (może być ułamkowa);
separatory: przecinek, średnik, spacja, tabulator; wiersze puste i zaczynające się od „#” są pomijane.
parse_csv sprawdza dokładnie te same reguły, ale z komunikatem od razu przy imporcie (zamiast błędu
dopiero przy uruchomieniu symulacji).

Obraz PNG/JPG w odcieniach szarości (image_to_heights): jasność -> wysokość
  h = podstawa + jasność · (wysokość maks. − podstawa)   (jasność 0..1; opcja „odwróć”: ciemne = wysoko),
obraz skalowany do nx × ny (Pillow, interpolacja dwuliniowa z wygładzeniem przy zmniejszaniu),
opcjonalnie wygładzony (3 przebiegi filtra pudełkowego o promieniu r ≈ filtr Gaussa) i przycięty do [0, nz].
Górny wiersz obrazu to północ — trafia na y = ny − 1, więc obraz wygląda tak samo jak rzut z góry
w podglądzie 2D (tam y rośnie do góry).
"""

from __future__ import annotations

import io
import json
import math
import re
from pathlib import Path

import numpy as np

from .names import safe_name

MAX_UPLOAD_BYTES = 40 * 1024 * 1024    # plik z przeglądarki
MAX_IMAGE_PIXELS = 25_000_000          # obraz wejściowy (np. 5000 × 5000)
MAX_MAP_CELLS = 4_000_000              # mapa wynikowa nx · ny (2000 × 2000)
_SPLIT = re.compile(r"[,; \t]+")


class HeightmapError(Exception):
    """Błąd pliku mapy wysokości — komunikat po polsku do formularza."""

    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.status = status


# ---------------------------------------------------------------------------- CSV


def parse_csv(text: str, name: str = "plik") -> np.ndarray:
    """Tekst CSV -> tablica (ny, nx) float64 (wiersz 0 = y = 0). Te same reguły co silnik."""
    rows: list[list[float]] = []
    first_line = 0
    for line_no, raw in enumerate(text.splitlines(), 1):
        fields = [f for f in _SPLIT.split(raw.strip()) if f]
        if not fields or fields[0].startswith("#"):
            continue
        vals = []
        for col, tok in enumerate(fields, 1):
            try:
                v = float(tok)
            except ValueError:
                raise HeightmapError(f"{name}, wiersz {line_no}, kolumna {col}: „{tok[:20]}” nie jest liczbą") from None
            if not math.isfinite(v):
                raise HeightmapError(f"{name}, wiersz {line_no}, kolumna {col}: wartość nieskończona")
            if v < 0:
                raise HeightmapError(f"{name}, wiersz {line_no}, kolumna {col}: wysokość ujemna ({tok})")
            vals.append(v)
        if rows and len(vals) != len(rows[0]):
            raise HeightmapError(f"{name}, wiersz {line_no}: {len(vals)} wartości, a wiersz {first_line} ma "
                                 f"{len(rows[0])}; mapa musi mieć tyle samo wartości w każdym wierszu (nx)")
        if not rows:
            first_line = line_no
        rows.append(vals)
        if len(rows) * len(vals) > MAX_MAP_CELLS:
            raise HeightmapError(f"{name}: mapa ma więcej niż {MAX_MAP_CELLS:,} komórek, zmniejsz rozdzielczość"
                                 .replace(",", " "))
    if not rows:
        raise HeightmapError(f"{name}: brak wierszy z liczbami (plik pusty albo same komentarze „#”)")
    return np.array(rows, dtype=np.float64)


def heights_to_csv(h: np.ndarray, comment: str = "") -> str:
    """Tablica (ny, nx) -> tekst CSV (wiersz y = 0 pierwszy), z komentarzem „#” na początku."""
    ny, nx = h.shape
    lines = [f"# Mapa wysokości terenu volcano-ca-mc (terrain.type = \"file\"): {ny} wierszy (y = 0..{ny - 1}) "
             f"× {nx} wartości (x = 0..{nx - 1}), wartości w komórkach"]
    if comment:
        lines += [f"# {c}" for c in comment.splitlines()]
    integral = bool(np.all(np.abs(h - np.round(h)) < 1e-9))
    for row in h:
        if integral:
            lines.append(",".join(str(int(round(v))) for v in row))
        else:
            lines.append(",".join(f"{v:.2f}".rstrip("0").rstrip(".") for v in row))
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------- przetwarzanie


def resize(arr: np.ndarray, nx: int, ny: int) -> np.ndarray:
    """Skalowanie mapy (ny0, nx0) -> (ny, nx): Pillow (dwuliniowo, z wygładzeniem przy zmniejszaniu),
    a bez Pillow — interpolacja dwuliniowa numpy."""
    if arr.shape == (ny, nx):
        return arr.astype(np.float64)
    try:
        from PIL import Image
        img = Image.fromarray(arr.astype(np.float32))  # tryb "F" (float32)
        return np.asarray(img.resize((nx, ny), Image.Resampling.BILINEAR), dtype=np.float64)
    except ImportError:
        ys = np.linspace(0, arr.shape[0] - 1, ny)
        xs = np.linspace(0, arr.shape[1] - 1, nx)
        tmp = np.array([np.interp(xs, np.arange(arr.shape[1]), r) for r in arr])
        return np.array([np.interp(ys, np.arange(arr.shape[0]), c) for c in tmp.T]).T


def smooth(arr: np.ndarray, radius: float) -> np.ndarray:
    """Wygładzenie: 3 przebiegi filtra pudełkowego (2r+1) — przybliżenie filtra Gaussa; brzegi powielane."""
    r = int(round(radius))
    if r <= 0:
        return arr
    out = arr.astype(np.float64)
    for _ in range(3):
        for axis in (0, 1):
            pad = [(0, 0), (0, 0)]
            pad[axis] = (r + 1, r)
            p = np.pad(out, pad, mode="edge")
            c = np.cumsum(p, axis=axis)
            hi = np.take(c, range(2 * r + 1, c.shape[axis]), axis=axis)
            lo = np.take(c, range(0, c.shape[axis] - 2 * r - 1), axis=axis)
            out = (hi - lo) / (2 * r + 1)
    return out


def image_to_heights(data: bytes, nx: int, ny: int, nz: int, max_height: float, base: float = 0.0,
                     smooth_radius: float = 0.0, invert: bool = False, normalize: bool = False,
                     name: str = "obraz") -> tuple[np.ndarray, dict]:
    """Obraz PNG/JPG (bajty) -> mapa (ny, nx) wysokości w komórkach + opis konwersji."""
    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError:
        raise HeightmapError("Import obrazów wymaga pakietu Pillow: python -m pip install --user pillow") from None
    if len(data) > MAX_UPLOAD_BYTES:
        raise HeightmapError(f"{name}: plik ma {len(data) / 2**20:.1f} MiB, a maksimum to {MAX_UPLOAD_BYTES // 2**20} MiB")
    _check_target(nx, ny, nz)
    if not 0 <= base <= max_height:
        raise HeightmapError("Wysokość podstawy musi być z zakresu 0..wysokość maks.")
    if max_height <= 0:
        raise HeightmapError("Wysokość maks. musi być większa od 0")
    try:
        img = Image.open(io.BytesIO(data))
        fmt = img.format
        w, h = img.size  # tylko nagłówek — zanim obraz trafi do pamięci
    except (UnidentifiedImageError, OSError):
        raise HeightmapError(f"{name}: to nie jest obraz PNG ani JPG (albo plik jest uszkodzony)") from None
    if fmt not in ("PNG", "JPEG", "BMP", "GIF", "WEBP", "TIFF"):
        raise HeightmapError(f"{name}: format {fmt} nie jest obsługiwany, użyj PNG albo JPG")
    if w * h > MAX_IMAGE_PIXELS:
        raise HeightmapError(f"{name}: obraz {w}×{h} = {w * h / 1e6:.1f} Mpx jest za duży "
                             f"(maksimum {MAX_IMAGE_PIXELS / 1e6:.0f} Mpx); zmniejsz go przed importem")
    try:
        if img.mode in ("I;16", "I;16B", "I;16L", "I"):
            gray = np.asarray(img.convert("I"), dtype=np.float64) / 65535.0   # PNG 16-bitowy
        else:
            gray = np.asarray(img.convert("L"), dtype=np.float64) / 255.0     # jasność (luminancja)
    except OSError as e:
        raise HeightmapError(f"{name}: nie można odczytać obrazu ({e})") from None
    gray = np.clip(gray, 0.0, 1.0)
    if normalize and gray.max() > gray.min():
        gray = (gray - gray.min()) / (gray.max() - gray.min())
    if invert:
        gray = 1.0 - gray
    gray = gray[::-1, :]                     # górny wiersz obrazu (północ) -> y = ny − 1
    heights = base + resize(gray, nx, ny) * (max_height - base)
    heights = smooth(heights, smooth_radius)
    heights = np.clip(np.round(heights, 2), 0.0, float(nz))
    info = {"source": name, "format": fmt, "imageSize": [w, h], "mode": img.mode, "maxHeight": max_height,
            "base": base, "smooth": smooth_radius, "invert": invert, "normalize": normalize}
    return heights, info


def _check_target(nx: int, ny: int, nz: int) -> None:
    if not (1 <= nx <= 100000 and 1 <= ny <= 100000 and 1 <= nz <= 100000):
        raise HeightmapError("Wymiary mapy nx, ny i wysokość nz muszą być z zakresu 1..100000")
    if nx * ny > MAX_MAP_CELLS:
        raise HeightmapError(f"Mapa {nx}×{ny} ma więcej niż {MAX_MAP_CELLS:,} komórek".replace(",", " "))


def csv_to_heights(text: str, name: str, nx: int | None = None, ny: int | None = None,
                   nz: int | None = None) -> tuple[np.ndarray, dict]:
    """CSV od użytkownika -> mapa; z nx, ny — przeskalowana do siatki; z nz — przycięta do [0, nz]."""
    h = parse_csv(text, name)
    info = {"source": name, "format": "CSV", "imageSize": [h.shape[1], h.shape[0]]}
    if nx and ny and (nx, ny) != (h.shape[1], h.shape[0]):
        _check_target(nx, ny, nz or 1)
        h = np.round(resize(h, nx, ny), 2)
        info["resized"] = True
    if nz:
        info["clipped"] = bool((h > nz).any())
        h = np.clip(h, 0.0, float(nz))
    return h, info


# ---------------------------------------------------------------------------- pliki configs/heightmaps/


def save_map(folder: Path, name: str, heights: np.ndarray, comment: str = "") -> Path:
    """Zapis do folder/<bezpieczna nazwa>.csv (istniejący plik nie jest nadpisywany: -2, -3…)."""
    folder.mkdir(parents=True, exist_ok=True)
    stem = safe_name(Path(name).stem, 40, fallback="mapa")
    path, n = folder / f"{stem}.csv", 2
    while path.exists():
        path, n = folder / f"{stem}-{n}.csv", n + 1
    path.write_text(heights_to_csv(heights, comment), encoding="utf-8", newline="\n")
    return path


_cache: dict[str, tuple[tuple, np.ndarray, str]] = {}


def load_map(path: Path) -> tuple[np.ndarray, str]:
    """Mapa z pliku CSV + pierwszy komentarz (pamiętane do zmiany pliku)."""
    st = path.stat()
    key = str(path.resolve())
    sig = (st.st_size, st.st_mtime_ns)
    hit = _cache.get(key)
    if hit and hit[0] == sig:
        return hit[1], hit[2]
    text = path.read_text(encoding="utf-8", errors="replace")
    comments = [ln[1:].strip() for ln in text.splitlines() if ln.startswith("#")]
    h = parse_csv(text, path.name)
    note = comments[1] if len(comments) > 1 else (comments[0] if comments else "")
    _cache[key] = (sig, h, note)
    return h, note


def list_maps(folder: Path, root: Path) -> list[dict]:
    """Mapy w folderze (configs/heightmaps/): plik względem katalogu projektu, wymiary, zakres wysokości."""
    out = []
    if not folder.is_dir():
        return out
    for p in sorted(folder.glob("*.csv")):
        try:
            h, note = load_map(p)
        except (HeightmapError, OSError) as e:
            out.append({"file": _rel(p, root), "name": p.stem, "error": str(e)})
            continue
        item = {"file": _rel(p, root), "name": p.stem, "nx": int(h.shape[1]), "ny": int(h.shape[0]),
                "min": float(h.min()), "max": float(h.max()), "note": note}
        geo = load_geo(p)
        if geo is not None:
            item["geo"] = geo
        out.append(item)
    return out


def load_geo(csv_path: Path) -> dict | None:
    """Metadane mapy z prawdziwego terenu (<nazwa>.json obok CSV, tools/fetch_dem.py): bbox, siatka, skala
    pozioma i pionowa, źródło — dla GUI (szer./dł. pod kursorem, wysokość w metrach). None, gdy brak pliku."""
    p = csv_path.with_suffix(".json")
    if not p.is_file():
        return None
    try:
        meta = json.loads(p.read_text(encoding="utf-8"))
        bbox, grid = meta["bbox"], meta["grid"]
        return {"bbox": {k: float(bbox[k]) for k in ("south", "west", "north", "east")},
                "nx": int(grid["nx"]), "ny": int(grid["ny"]), "nz": int(grid.get("nz", 0)),
                "metersPerCell": meta.get("horizontal", {}).get("metersPerCell"),
                "metersPerCellZ": meta.get("vertical", {}).get("metersPerCell"),
                "baseMeters": meta.get("vertical", {}).get("baseMeters", 0.0),
                "exaggeration": meta.get("horizontal", {}).get("verticalExaggeration"),
                "source": meta.get("source", {}).get("name"), "zoom": meta.get("source", {}).get("zoom"),
                "fetched": meta.get("fetched"), "attributionDoc": meta.get("source", {}).get("attributionDoc"),
                "description": meta.get("description", "")}
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _rel(p: Path, root: Path) -> str:
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return p.as_posix()
