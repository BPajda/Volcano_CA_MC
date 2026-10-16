"""Prawdziwy teren (DEM) -> mapa wysokości silnika: pobranie kafelków wysokości, mozaika, wycinek, przepróbkowanie.

Źródło: AWS Terrain Tiles (Tilezen / Mapzen „Terrain Tiles”, publiczny zasób S3 — bez klucza i logowania),
kafelki Terrarium PNG 256×256 w odwzorowaniu Web Mercator (schemat kafelków „slippy map”):
    https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png
    wysokość [m] = R·256 + G + B/256 − 32768
Dane kafelków pochodzą m.in. z SRTM, GMTED2010, ETOPO1 i EU-DEM — wymagane przypisanie (ATTRIBUTION niżej,
pełny tekst: github.com/tilezen/joerd, docs/attribution.md) jest w configs/heightmaps/README.md, README.md
i w metadanych <name>.json.

Kroki (python tools/fetch_dem.py --name etna --bbox 37.58 14.80 37.92 15.22 --zoom 11 --nx 160 --ny 160 --nz 70):
 1. bbox (S, W, N, E) + zoom -> zakres kafelków; pobranie (cache tools/.dem_cache/terrarium/z/x/y.png — poza
    repozytorium), dekodowanie Terrarium i mozaika,
 2. siatka nx × ny: środek komórki (x, y) -> (szer., dł.) liniowo w bbox (x = 0 zachód, y = 0 POŁUDNIE,
    y = ny − 1 północ — ta sama konwencja co import obrazów w gui/heightmap.py i rzut z góry w podglądzie 2D)
    -> piksel mozaiki (Web Mercator) -> interpolacja dwuliniowa; gdy na komórkę przypada > 1,5 piksela,
    mozaika jest najpierw wygładzana (3 przebiegi filtra pudełkowego ≈ filtr Gaussa o szerokości ~ komórki),
    żeby komórka niosła średnią swojego terenu, a nie przypadkowy piksel (aliasing),
 3. wysokość [m] -> liczba komórek pionowych: poziom odniesienia = max(0, minimum obszaru) (poziom morza,
    gdy w kadrze jest morze; dno morza -> 0) -> 0, najwyższy punkt -> peak·nz (domyślnie 0,85·nz),
 4. zapis do configs/heightmaps/: <name>.csv (format silnika, wysokości w komórkach), <name>.png (podgląd
    w odcieniach szarości, północ u góry), <name>.json (bbox, zoom, źródło, data pobrania, rozdzielczość
    pozioma [m/komórkę], skala pionowa, przewyższenie, min/max wysokości w metrach).

Opcje: --from-cache (bez internetu, tylko kafelki z cache), --peak 0.85, --out, --cache.
Przeliczenie (szer., dł.) -> (x, y) siatki: latlon_to_grid() / python tools/latlon_to_grid.py <name> SZER DŁ.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gui.heightmap import heights_to_csv, smooth  # noqa: E402  (ten sam zapis CSV co import w GUI)

TILE = 256
URL_TEMPLATE = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
SOURCE_NAME = "AWS Terrain Tiles (Tilezen/Mapzen Terrain Tiles), format Terrarium PNG"
ATTRIBUTION_DOC = "https://github.com/tilezen/joerd/blob/master/docs/attribution.md"
# Przypisanie wymagane przez dostawców danych (tilezen/joerd, docs/attribution.md) — skrót do metadanych.
ATTRIBUTION = [
    "ArcticDEM terrain data DEM(s) were created from DigitalGlobe, Inc., imagery and funded under National "
    "Science Foundation awards 1043681, 1559691, and 1542736",
    "Australia terrain data © Commonwealth of Australia (Geoscience Australia) 2017",
    "Austria terrain data © offene Daten Österreichs – Digitales Geländemodell (DGM) Österreich",
    "Canada terrain data contains information licensed under the Open Government Licence – Canada",
    "Europe terrain data produced using Copernicus data and information funded by the European Union - EU-DEM layers",
    "Global ETOPO1 terrain data U.S. National Oceanic and Atmospheric Administration",
    "Mexico terrain data source: INEGI, Continental relief, 2016",
    "New Zealand terrain data Copyright 2011 Crown copyright (c) Land Information New Zealand and the New Zealand "
    "Government (All rights reserved)",
    "Norway terrain data © Kartverket",
    "United Kingdom terrain data © Environment Agency copyright and/or database right 2015. All rights reserved",
    "United States 3DEP (formerly NED) and global GMTED2010 and SRTM terrain data courtesy of the U.S. Geological Survey",
]
EARTH_RADIUS = 6378137.0                         # WGS84 — promień równikowy (Web Mercator)
MAX_LAT = 85.05112878                            # granica Web Mercator


class DemError(Exception):
    """Błąd pobierania / parametrów — komunikat po polsku dla użytkownika."""


# ---------------------------------------------------------------------------- geometria kafelków


def latlon_to_pixel(lat: float, lon: float, zoom: int) -> tuple[float, float]:
    """(szer., dł.) [°] -> globalne współrzędne piksela Web Mercator przy danym zoomie (ułamkowe; piksel i
    zajmuje przedział [i, i + 1), środek w i + 0,5). y rośnie na południe."""
    n = TILE * 2 ** zoom
    x = (lon + 180.0) / 360.0 * n
    s = math.sin(math.radians(lat))
    y = (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * n
    return x, y


def tile_range(bbox: tuple[float, float, float, float], zoom: int) -> tuple[int, int, int, int]:
    """Kafelki pokrywające bbox (S, W, N, E): (x0, x1, y0, y1) włącznie; y0 to kafelek najbardziej na północ.
    Margines 1 piksela — interpolacja dwuliniowa przy brzegu bbox sięga do sąsiedniego piksela."""
    s, w, n, e = bbox
    px0, py0 = latlon_to_pixel(n, w, zoom)
    px1, py1 = latlon_to_pixel(s, e, zoom)
    last = 2 ** zoom - 1
    x0 = max(0, int(math.floor((px0 - 2) / TILE)))
    x1 = min(last, int(math.floor((px1 + 2) / TILE)))
    y0 = max(0, int(math.floor((py0 - 2) / TILE)))
    y1 = min(last, int(math.floor((py1 + 2) / TILE)))
    return x0, x1, y0, y1


def ground_resolution(lat: float, zoom: int) -> float:
    """Rozdzielczość piksela kafelka [m] na danej szerokości (wzór z docs/data-sources.md Terrain Tiles)."""
    return math.cos(math.radians(lat)) * 2 * math.pi * EARTH_RADIUS / (TILE * 2 ** zoom)


def meters_per_degree(lat: float) -> tuple[float, float]:
    """Długość 1° szerokości i 1° długości geograficznej [m] na szerokości lat (elipsoida WGS84,
    rozwinięcie w szereg — dokładność ~1 cm)."""
    p = math.radians(lat)
    m_lat = 111132.954 - 559.822 * math.cos(2 * p) + 1.175 * math.cos(4 * p)
    m_lon = 111412.84 * math.cos(p) - 93.5 * math.cos(3 * p) + 0.118 * math.cos(5 * p)
    return m_lat, m_lon


# ---------------------------------------------------------------------------- Terrarium


def decode_terrarium(rgb: np.ndarray) -> np.ndarray:
    """Obraz Terrarium (h, w, 3+) uint8 -> wysokość [m] float64: R·256 + G + B/256 − 32768."""
    a = np.asarray(rgb)
    if a.ndim != 3 or a.shape[2] < 3:
        raise DemError("kafelek Terrarium musi być obrazem RGB")
    r, g, b = (a[..., i].astype(np.float64) for i in range(3))
    return r * 256.0 + g + b / 256.0 - 32768.0


def encode_terrarium(elev: np.ndarray) -> np.ndarray:
    """Wysokość [m] -> obraz Terrarium uint8 (h, w, 3) — odwrotność decode_terrarium (testy, sztuczne kafelki)."""
    v = np.asarray(elev, dtype=np.float64) + 32768.0
    r = np.floor(v / 256.0)
    g = np.floor(v - r * 256.0)
    b = np.floor((v - np.floor(v)) * 256.0)
    return np.stack([r, g, b], axis=-1).clip(0, 255).astype(np.uint8)


def read_tile(data: bytes) -> np.ndarray:
    """Bajty PNG kafelka -> wysokości (256, 256) [m]."""
    try:
        from PIL import Image
    except ImportError:
        raise DemError("Dekodowanie kafelków wymaga pakietu Pillow: python -m pip install --user pillow") from None
    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
    except OSError as e:
        raise DemError(f"uszkodzony kafelek PNG ({e})") from None
    h = decode_terrarium(np.asarray(img))
    if h.shape != (TILE, TILE):
        raise DemError(f"kafelek ma rozmiar {h.shape[1]}×{h.shape[0]}, oczekiwano {TILE}×{TILE}")
    return h


def tile_path(cache: Path, z: int, x: int, y: int) -> Path:
    return cache / "terrarium" / str(z) / str(x) / f"{y}.png"


def fetch_tile(z: int, x: int, y: int, cache: Path, offline: bool, url_template: str = URL_TEMPLATE,
               retries: int = 3) -> bytes:
    """Kafelek z cache albo z sieci (zapis do cache). offline=True — tylko cache."""
    path = tile_path(cache, z, x, y)
    if path.is_file() and path.stat().st_size > 0:
        return path.read_bytes()
    if offline:
        raise DemError(f"brak kafelka {z}/{x}/{y} w cache ({path}) — uruchom bez --from-cache (z internetem)")
    url = url_template.format(z=z, x=x, y=y)
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "volcano-ca-mc/1.0 (projekt studencki, fetch_dem.py)"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            return data
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code} {e.reason}"
            if e.code in (403, 404):
                break
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = str(getattr(e, "reason", e))
        time.sleep(1.0 + attempt)
    raise DemError(f"nie udało się pobrać kafelka {url}: {last}. Sprawdź połączenie z internetem "
                   "albo użyj --from-cache, jeśli kafelki były już pobrane")


def build_mosaic(bbox, zoom: int, cache: Path, offline: bool, url_template: str = URL_TEMPLATE,
                 log=print) -> tuple[np.ndarray, int, int, list[list[int]]]:
    """Mozaika kafelków pokrywających bbox: (wysokości [m], piksel x lewego brzegu, piksel y górnego brzegu, lista
    kafelków [z, x, y])."""
    x0, x1, y0, y1 = tile_range(bbox, zoom)
    count = (x1 - x0 + 1) * (y1 - y0 + 1)
    if count > 400:
        raise DemError(f"bbox przy zoomie {zoom} wymaga {count} kafelków (maks. 400) — zmniejsz zoom albo obszar")
    mosaic = np.zeros(((y1 - y0 + 1) * TILE, (x1 - x0 + 1) * TILE), dtype=np.float64)
    tiles = []
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            data = fetch_tile(zoom, tx, ty, cache, offline, url_template)
            mosaic[(ty - y0) * TILE:(ty - y0 + 1) * TILE, (tx - x0) * TILE:(tx - x0 + 1) * TILE] = read_tile(data)
            tiles.append([zoom, tx, ty])
    log(f"  mozaika: {count} kafelków z={zoom} x {x0}..{x1}, y {y0}..{y1} ({mosaic.shape[1]}×{mosaic.shape[0]} px)")
    return mosaic, x0 * TILE, y0 * TILE, tiles


# ---------------------------------------------------------------------------- siatka symulacji


def cell_centers(bbox, nx: int, ny: int) -> tuple[np.ndarray, np.ndarray]:
    """Środki komórek: szerokości (ny,) od południa (y = 0) i długości (nx,) od zachodu (x = 0)."""
    s, w, n, e = bbox
    lats = s + (np.arange(ny) + 0.5) / ny * (n - s)
    lons = w + (np.arange(nx) + 0.5) / nx * (e - w)
    return lats, lons


def bilinear(img: np.ndarray, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Interpolacja dwuliniowa obrazu img (wiersze v, kolumny u) w punktach o ułamkowych indeksach
    (środek piksela i ma indeks i); poza obrazem — wartość brzegowa."""
    h, w = img.shape
    u = np.clip(u, 0, w - 1)
    v = np.clip(v, 0, h - 1)
    i0 = np.clip(np.floor(u).astype(np.int64), 0, max(w - 2, 0))
    j0 = np.clip(np.floor(v).astype(np.int64), 0, max(h - 2, 0))
    fu = u - i0
    fv = v - j0
    i1 = np.minimum(i0 + 1, w - 1)
    j1 = np.minimum(j0 + 1, h - 1)
    top = img[j0, i0] * (1 - fu) + img[j0, i1] * fu
    bot = img[j1, i0] * (1 - fu) + img[j1, i1] * fu
    return top * (1 - fv) + bot * fv


def resample(mosaic: np.ndarray, origin_px: tuple[int, int], zoom: int, bbox, nx: int, ny: int,
             antialias: bool = True) -> tuple[np.ndarray, float]:
    """Mozaika (wiersz 0 = północ) -> wysokości (ny, nx) w środkach komórek, wiersz 0 = POŁUDNIE (y = 0).
    Zwraca też liczbę pikseli mozaiki na komórkę (w poziomie)."""
    lats, lons = cell_centers(bbox, nx, ny)
    px = np.array([latlon_to_pixel(lats[0], lon, zoom)[0] for lon in lons]) - origin_px[0] - 0.5
    py = np.array([latlon_to_pixel(lat, lons[0], zoom)[1] for lat in lats]) - origin_px[1] - 0.5
    per_cell = abs(px[-1] - px[0]) / max(nx - 1, 1)
    src = mosaic
    if antialias and per_cell > 1.5:
        # Filtr pudełkowy (3 przebiegi ≈ Gauss) o promieniu ~ pół komórki: komórka = średnia „swojego” terenu.
        src = smooth(mosaic, max(1.0, per_cell / 2.0 / math.sqrt(3.0)))
    uu, vv = np.meshgrid(px, py)
    return bilinear(src, uu, vv), per_cell


def to_cells(elev: np.ndarray, nz: int, peak: float = 0.85) -> tuple[np.ndarray, dict]:
    """Wysokości [m] -> liczba komórek pionowych: max(0, min obszaru) -> 0, najwyższy punkt -> peak·nz."""
    if not 0.05 <= peak <= 1.0:
        raise DemError("--peak musi być z zakresu 0,05..1 (część nz zajęta przez najwyższy punkt)")
    lo = float(elev.min())
    hi = float(elev.max())
    base = max(0.0, lo)
    if hi <= base:
        raise DemError(f"obszar jest płaski albo pod wodą (min {lo:.1f} m, max {hi:.1f} m) — wybierz inny bbox")
    peak_cells = peak * nz
    m_per_cell = (hi - base) / peak_cells
    cells = np.clip((elev - base) / m_per_cell, 0.0, float(nz))
    cells = np.round(cells, 2)
    return cells, {"baseMeters": round(base, 2), "peakMeters": round(hi, 2), "metersPerCell": round(m_per_cell, 3),
                   "peakCells": round(peak_cells, 2), "minMeters": round(lo, 2)}


def grid_meta(bbox, nx: int, ny: int, nz: int, zoom: int, vertical: dict, per_cell_px: float) -> dict:
    """Skala siatki: metry na komórkę w poziomie (osobno x i y, średnio) i w pionie, przewyższenie."""
    s, w, n, e = bbox
    mid = (s + n) / 2
    m_lat, m_lon = meters_per_degree(mid)
    mx = (e - w) / nx * m_lon
    my = (n - s) / ny * m_lat
    mh = (mx + my) / 2
    return {
        "metersPerCellX": round(mx, 2), "metersPerCellY": round(my, 2), "metersPerCell": round(mh, 2),
        "metersPerCellZ": vertical["metersPerCell"],
        "verticalExaggeration": round(mh / vertical["metersPerCell"], 3),
        "tilePixelMeters": round(ground_resolution(mid, zoom), 2), "tilePixelsPerCell": round(per_cell_px, 2),
        "widthKm": round(mx * nx / 1000, 3), "heightKm": round(my * ny / 1000, 3),
    }


def latlon_to_grid(meta: dict, lat: float, lon: float) -> tuple[int, int, float, float]:
    """(szer., dł.) -> kolumna siatki (x, y) wg metadanych <name>.json (+ współrzędne ułamkowe, środek komórki
    x ma wartość x + 0,5). Rzuca DemError, gdy punkt leży poza bbox."""
    b = meta["bbox"]
    nx, ny = meta["grid"]["nx"], meta["grid"]["ny"]
    fx = (lon - b["west"]) / (b["east"] - b["west"]) * nx
    fy = (lat - b["south"]) / (b["north"] - b["south"]) * ny
    # Punkt na granicy komórek należy do komórki na wschodzie / północy (tolerancja na błąd zaokrągleń float).
    fx, fy = fx + 1e-9, fy + 1e-9
    if not (0 <= fx < nx and 0 <= fy < ny):
        raise DemError(f"punkt {lat:.5f} N, {lon:.5f} E leży poza obszarem mapy {meta.get('name', '')} "
                       f"({b['south']}–{b['north']} N, {b['west']}–{b['east']} E)")
    return int(math.floor(fx)), int(math.floor(fy)), fx, fy


def grid_to_latlon(meta: dict, x: float, y: float) -> tuple[float, float]:
    """Środek komórki (x, y) -> (szer., dł.)."""
    b = meta["bbox"]
    nx, ny = meta["grid"]["nx"], meta["grid"]["ny"]
    return (b["south"] + (y + 0.5) / ny * (b["north"] - b["south"]),
            b["west"] + (x + 0.5) / nx * (b["east"] - b["west"]))


def load_meta(name_or_path: str, folder: Path | None = None) -> dict:
    """Metadane mapy: nazwa (configs/heightmaps/<name>.json) albo ścieżka do .json / .csv."""
    p = Path(name_or_path)
    if p.suffix.lower() == ".csv":
        p = p.with_suffix(".json")
    if p.suffix.lower() != ".json":
        p = (folder or ROOT / "configs" / "heightmaps") / f"{name_or_path}.json"
    if not p.is_file():
        raise DemError(f"brak metadanych mapy {p} — mapę z prawdziwego terenu tworzy tools/fetch_dem.py")
    return json.loads(p.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------- zapis


def save_preview_png(cells: np.ndarray, path: Path) -> None:
    """Podgląd w odcieniach szarości (biel = najwyżej), północ (y = ny − 1) u góry obrazu."""
    from PIL import Image
    g = np.round(255 * (cells - cells.min()) / max(float(cells.max() - cells.min()), 1e-9)).astype(np.uint8)
    Image.fromarray(g[::-1, :]).save(path)


def fetch(name: str, bbox, zoom: int, nx: int, ny: int, nz: int, out: Path, cache: Path, offline: bool = False,
          peak: float = 0.85, description: str = "", url_template: str = URL_TEMPLATE, log=print) -> dict:
    """Cały proces dla jednej mapy; zwraca metadane (zapisane też jako <name>.json)."""
    s, w, n, e = bbox
    if not (-MAX_LAT < s < n < MAX_LAT and -180 <= w < e <= 180):
        raise DemError("bbox musi mieć postać S W N E z S < N, W < E (stopnie; szerokość w granicach ±85°)")
    if not 0 <= zoom <= 15:
        raise DemError("zoom musi być z zakresu 0..15")
    if nx < 2 or ny < 2 or nz < 2 or nx * ny > 4_000_000:
        raise DemError("nx, ny, nz muszą być >= 2, a nx·ny <= 4 000 000")
    log(f"{name}: bbox {s}–{n} N, {w}–{e} E, zoom {zoom}, siatka {nx}×{ny}×{nz}")
    mosaic, ox, oy, tiles = build_mosaic(bbox, zoom, cache, offline, url_template, log)
    elev, per_cell = resample(mosaic, (ox, oy), zoom, bbox, nx, ny)
    cells, vertical = to_cells(elev, nz, peak)
    meta_grid = grid_meta(bbox, nx, ny, nz, zoom, vertical, per_cell)
    jy, jx = np.unravel_index(int(np.argmax(elev)), elev.shape)
    lat_max, lon_max = cell_centers(bbox, nx, ny)[0][jy], cell_centers(bbox, nx, ny)[1][jx]
    meta = {
        "name": name,
        "description": description,
        "source": {"name": SOURCE_NAME, "urlTemplate": url_template, "zoom": zoom, "tiles": len(tiles),
                   "tileRange": {"x": [tiles[0][1], tiles[-1][1]], "y": [tiles[0][2], tiles[-1][2]]},
                   "decoding": "R*256 + G + B/256 - 32768 [m]", "attributionDoc": ATTRIBUTION_DOC,
                   "attribution": ATTRIBUTION},
        "fetched": date.today().isoformat(),
        "tool": "tools/fetch_dem.py",
        "bbox": {"south": s, "west": w, "north": n, "east": e},
        "grid": {"nx": nx, "ny": ny, "nz": nz, "x": "x = 0 zachód (W) … nx − 1 wschód (E)",
                 "y": "y = 0 południe (S) … ny − 1 północ (N)",
                 "cellToLatLon": "lat = S + (y + 0.5)/ny·(N − S), lon = W + (x + 0.5)/nx·(E − W)"},
        "horizontal": meta_grid,
        "vertical": {"baseMeters": vertical["baseMeters"], "peakMeters": vertical["peakMeters"],
                     "metersPerCell": vertical["metersPerCell"], "peakCells": vertical["peakCells"],
                     "rule": "komórki = (wysokość − baseMeters) / metersPerCell, przycięte do [0, nz]; "
                             "baseMeters = max(0, minimum obszaru)"},
        "elevation": {"minMeters": vertical["minMeters"], "maxMeters": vertical["peakMeters"],
                      "meanMeters": round(float(elev.mean()), 2),
                      "maxAt": {"x": int(jx), "y": int(jy), "lat": round(float(lat_max), 5), "lon": round(float(lon_max), 5)},
                      "belowBase": int((elev < vertical["baseMeters"]).sum())},
    }
    out.mkdir(parents=True, exist_ok=True)
    comment = (f"{description + ' — ' if description else ''}prawdziwy teren: {SOURCE_NAME}, zoom {zoom}, "
               f"bbox {s}–{n} N, {w}–{e} E; {meta_grid['metersPerCell']:.0f} m/komórkę w poziomie, "
               f"{vertical['metersPerCell']:.1f} m/komórkę w pionie (przewyższenie ×{meta_grid['verticalExaggeration']:.2f}); "
               f"pobrano {meta['fetched']} (tools/fetch_dem.py); przypisanie danych: configs/heightmaps/README.md")
    (out / f"{name}.csv").write_text(heights_to_csv(cells, comment), encoding="utf-8", newline="\n")
    save_preview_png(cells, out / f"{name}.png")
    (out / f"{name}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
                                      newline="\n")
    log(f"  wysokość {vertical['minMeters']:.0f}–{vertical['peakMeters']:.0f} m (szczyt w x={jx}, y={jy}: "
        f"{lat_max:.4f} N, {lon_max:.4f} E) -> 0–{cells.max():.1f} komórek z {nz}")
    log(f"  skala: {meta_grid['metersPerCellX']:.1f} × {meta_grid['metersPerCellY']:.1f} m/komórkę w poziomie "
        f"({meta_grid['widthKm']:.1f} × {meta_grid['heightKm']:.1f} km), {vertical['metersPerCell']:.1f} m/komórkę "
        f"w pionie, przewyższenie ×{meta_grid['verticalExaggeration']:.2f}, piksel kafelka {meta_grid['tilePixelMeters']:.0f} m "
        f"({meta_grid['tilePixelsPerCell']:.1f} px/komórkę)")
    for ext in ("csv", "png", "json"):
        log(f"  zapisano {out / f'{name}.{ext}'}")
    return meta


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description="Prawdziwy teren (AWS Terrain Tiles, Terrarium) -> configs/heightmaps/<name>.csv/.png/.json")
    ap.add_argument("--name", required=True, help="nazwa mapy (plik configs/heightmaps/<name>.*)")
    ap.add_argument("--bbox", nargs=4, type=float, required=True, metavar=("S", "W", "N", "E"),
                    help="obszar: szerokość południowa, długość zachodnia, szerokość północna, długość wschodnia [°]")
    ap.add_argument("--zoom", type=int, required=True, help="poziom kafelków (10–13 dla wulkanów)")
    ap.add_argument("--nx", type=int, required=True)
    ap.add_argument("--ny", type=int, required=True)
    ap.add_argument("--nz", type=int, required=True, help="wysokość przestrzeni symulacji [komórki]")
    ap.add_argument("--peak", type=float, default=0.85, help="najwyższy punkt = peak·nz komórek (domyślnie 0,85)")
    ap.add_argument("--description", default="", help="opis do komentarza CSV i metadanych")
    ap.add_argument("--from-cache", action="store_true", help="bez internetu — tylko kafelki z cache")
    ap.add_argument("--out", default=str(ROOT / "configs" / "heightmaps"))
    ap.add_argument("--cache", default=str(ROOT / "tools" / ".dem_cache"))
    args = ap.parse_args(argv)
    try:
        fetch(args.name, tuple(args.bbox), args.zoom, args.nx, args.ny, args.nz, Path(args.out), Path(args.cache),
              args.from_cache, args.peak, args.description)
    except DemError as e:
        print(f"Błąd: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
