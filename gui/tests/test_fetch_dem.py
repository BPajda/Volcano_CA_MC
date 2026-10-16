"""tools/fetch_dem.py i tools/latlon_to_grid.py (etap 6) — BEZ internetu: kafelki Terrarium są tworzone
sztucznie w tymczasowym cache (znana funkcja wysokości), a fetch() działa z offline=True (--from-cache).
Sprawdzane: dekodowanie Terrarium, bbox -> kafelki, przepróbkowanie (orientacja północ = y max, skala pionowa,
poziom morza), metadane, lat/lon -> siatka, czytelne błędy po polsku."""

from __future__ import annotations

import json
import math

import numpy as np
import pytest

from gui.heightmap import load_geo, parse_csv
from tools import fetch_dem, latlon_to_grid as l2g
from tools.fetch_dem import DemError

BBOX = (37.60, 14.90, 37.70, 15.05)   # mały obszar (S, W, N, E) — przy zoomie 10 mieści się w 2×2 kafelkach
ZOOM = 10


def pixel_to_latlon(px: float, py: float, zoom: int) -> tuple[float, float]:
    """Odwrotność Web Mercator (globalne współrzędne piksela -> stopnie) — niezależna od testowanego kodu."""
    n = 256 * 2 ** zoom
    lon = px / n * 360.0 - 180.0
    lat = np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * np.asarray(py) / n))))
    return lat, lon


def write_tiles(cache, elevation, bbox=BBOX, zoom=ZOOM):
    """Sztuczne kafelki Terrarium (PNG) w cache dla funkcji elevation(lat, lon) [m]."""
    from PIL import Image
    x0, x1, y0, y1 = fetch_dem.tile_range(bbox, zoom)
    for tx in range(x0, x1 + 1):
        for ty in range(y0, y1 + 1):
            ii, jj = np.meshgrid(np.arange(256) + 0.5, np.arange(256) + 0.5)
            lat, lon = pixel_to_latlon(tx * 256 + ii, ty * 256 + jj, zoom)
            path = fetch_dem.tile_path(cache, zoom, tx, ty)
            path.parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(fetch_dem.encode_terrarium(elevation(lat, lon))).save(path)
    return (x1 - x0 + 1) * (y1 - y0 + 1)


def north_ramp(lat, lon):
    """Wysokość rosnąca liniowo na północ, z „morzem” (−20 m) na południowym skraju."""
    s, _, n, _ = BBOX
    return np.where(lat < s + 0.01, -20.0, 100.0 + 2000.0 * (lat - s) / (n - s))


def cone(lat, lon):
    """Stożek 3000 m w środku bbox (promień 0,04°)."""
    s, w, n, e = BBOX
    d = np.hypot(lat - (s + n) / 2, (lon - (w + e) / 2) * math.cos(math.radians(37.65)))
    return 200.0 + 2800.0 * np.clip(1 - d / 0.04, 0, None)


def test_terrarium_decode_encode():
    # Przykład z dokumentacji Terrain Tiles (tilezen/joerd, docs/formats.md): 2523,266 m <-> rgb(137, 219, 68).
    rgb = fetch_dem.encode_terrarium(np.array([[2523.266]]))
    assert rgb[0, 0].tolist() == [137, 219, 68]
    assert fetch_dem.decode_terrarium(rgb)[0, 0] == pytest.approx(2523.265625)
    vals = np.array([[-11000.0, -0.5, 0.0, 1.0 / 256, 8848.0]])
    assert np.allclose(fetch_dem.decode_terrarium(fetch_dem.encode_terrarium(vals)), vals, atol=1 / 256)
    with pytest.raises(DemError):
        fetch_dem.decode_terrarium(np.zeros((4, 4)))


def test_tile_range_and_pixels():
    # Wzór „slippy map” niezależnie: x = floor((lon + 180)/360 · 2^z), y = floor((1 − ln(tan φ + sec φ)/π)/2 · 2^z).
    def tile(lat, lon, z):
        n = 2 ** z
        phi = math.radians(lat)
        return int((lon + 180) / 360 * n), int((1 - math.log(math.tan(phi) + 1 / math.cos(phi)) / math.pi) / 2 * n)
    bbox = (37.58, 14.80, 37.92, 15.22)   # Etna z configs/heightmaps/etna.json
    x0, x1, y0, y1 = fetch_dem.tile_range(bbox, 11)
    nw, se = tile(37.92, 14.80, 11), tile(37.58, 15.22, 11)
    # Zakres obejmuje kafelki narożników; margines 2 pikseli (interpolacja przy brzegu) może dodać 1 kafelek.
    assert 0 <= nw[0] - x0 <= 1 and 0 <= nw[1] - y0 <= 1 and 0 <= x1 - se[0] <= 1 and 0 <= y1 - se[1] <= 1
    assert (x0, x1, y0, y1) == (1108, 1110, 790, 793)   # 37,58° N leży 1 piksel od granicy kafelków
    assert fetch_dem.tile_range((-1, -1, 1, 1), 0) == (0, 0, 0, 0)
    px, py = fetch_dem.latlon_to_pixel(0.0, 0.0, 1)
    assert (px, py) == pytest.approx((256.0, 256.0))
    assert fetch_dem.ground_resolution(0.0, 10) == pytest.approx(152.874, rel=1e-3)   # tabela z docs/data-sources.md
    m_lat, m_lon = fetch_dem.meters_per_degree(45.0)
    assert m_lat == pytest.approx(111132.0, rel=1e-3) and m_lon == pytest.approx(78847.0, rel=1e-3)


def test_bilinear():
    img = np.arange(12, dtype=float).reshape(3, 4)   # wartość = 4·wiersz + kolumna — funkcja liniowa
    u = np.array([0.0, 1.5, 3.0, 2.25])
    v = np.array([0.0, 0.5, 2.0, 1.75])
    assert np.allclose(fetch_dem.bilinear(img, u, v), 4 * v + u)
    assert fetch_dem.bilinear(img, np.array([-5.0]), np.array([9.0]))[0] == img[2, 0]   # poza obrazem — brzeg


def test_fetch_offline_orientation_scale_and_files(tmp_path):
    cache, out = tmp_path / "cache", tmp_path / "maps"
    tiles = write_tiles(cache, north_ramp)
    meta = fetch_dem.fetch("rampa", BBOX, ZOOM, 30, 20, 40, out, cache, offline=True, peak=0.85, log=lambda *_: None)
    h = parse_csv((out / "rampa.csv").read_text(encoding="utf-8"))
    assert h.shape == (20, 30)                       # ny wierszy × nx wartości (format silnika)
    rows = h.mean(axis=1)
    assert np.all(np.diff(rows[2:]) > 0)             # wiersz y rośnie na północ (y = ny − 1 = północ)
    assert h.max() == pytest.approx(0.85 * 40, abs=0.01)
    assert h[0].max() == 0.0                         # pas „morza” na południu -> 0 (poziom morza = podstawa)
    assert meta["vertical"]["baseMeters"] == 0.0
    assert meta["source"]["tiles"] == tiles and meta["source"]["zoom"] == ZOOM
    assert meta["grid"] == {**meta["grid"], "nx": 30, "ny": 20, "nz": 40}
    mpz = meta["vertical"]["metersPerCell"]
    assert mpz == pytest.approx(meta["vertical"]["peakMeters"] / (0.85 * 40), rel=1e-3)
    assert meta["horizontal"]["verticalExaggeration"] == pytest.approx(meta["horizontal"]["metersPerCell"] / mpz, rel=1e-2)
    assert "SRTM" in " ".join(meta["source"]["attribution"])
    # Wysokość w środku komórki ~ funkcja (interpolacja dwuliniowa, na liniowej rampie prawie dokładna).
    lats, _ = fetch_dem.cell_centers(BBOX, 30, 20)
    expect = (100 + 2000 * (lats[5:] - BBOX[0]) / (BBOX[2] - BBOX[0])) / mpz
    assert np.allclose(rows[5:], expect, atol=0.05)
    # Pliki: PNG (północ u góry obrazu) i metadane czytane przez GUI.
    from PIL import Image
    png = np.asarray(Image.open(out / "rampa.png"))
    assert png.shape == (20, 30) and png[0].mean() > png[-1].mean()
    geo = load_geo(out / "rampa.csv")
    assert geo["nx"] == 30 and geo["bbox"]["north"] == BBOX[2] and geo["metersPerCellZ"] == mpz
    assert json.loads((out / "rampa.json").read_text(encoding="utf-8"))["tool"] == "tools/fetch_dem.py"


def test_fetch_cone_peak_and_antialias(tmp_path):
    cache, out = tmp_path / "cache", tmp_path / "maps"
    write_tiles(cache, cone)
    meta = fetch_dem.fetch("stozek", BBOX, ZOOM, 24, 24, 50, out, cache, offline=True, log=lambda *_: None)
    h = parse_csv((out / "stozek.csv").read_text(encoding="utf-8"))
    jy, jx = np.unravel_index(np.argmax(h), h.shape)
    assert abs(jx - 11.5) <= 1 and abs(jy - 11.5) <= 1          # szczyt w środku kadru
    assert abs(meta["elevation"]["maxAt"]["x"] - jx) <= 1 and abs(meta["elevation"]["maxAt"]["y"] - jy) <= 1
    assert meta["vertical"]["baseMeters"] == pytest.approx(200.0, abs=1)  # bez morza: podstawa = minimum obszaru
    assert h.min() == pytest.approx(0.0, abs=0.01)


def test_latlon_to_grid_round_trip(tmp_path):
    meta = {"name": "m", "bbox": {"south": 10.0, "west": 20.0, "north": 11.0, "east": 22.0},
            "grid": {"nx": 200, "ny": 100}}
    assert fetch_dem.latlon_to_grid(meta, 10.0, 20.0)[:2] == (0, 0)
    assert fetch_dem.latlon_to_grid(meta, 10.999, 21.999)[:2] == (199, 99)
    assert fetch_dem.latlon_to_grid(meta, 10.6, 20.3)[:2] == (30, 60)   # granica komórek (błąd float) -> komórka na E/N
    x, y, fx, fy = fetch_dem.latlon_to_grid(meta, 10.5, 21.0)
    assert (x, y) == (100, 50) and (fx, fy) == pytest.approx((100.0, 50.0))
    lat, lon = fetch_dem.grid_to_latlon(meta, 37, 81)
    assert fetch_dem.latlon_to_grid(meta, lat, lon)[:2] == (37, 81)
    for lat, lon in ((9.9, 21.0), (10.5, 22.0), (11.0, 21.0)):
        with pytest.raises(DemError, match="poza obszarem"):
            fetch_dem.latlon_to_grid(meta, lat, lon)


def test_offline_missing_tile_and_cli(tmp_path, capsys):
    with pytest.raises(DemError, match="brak kafelka.*--from-cache"):
        fetch_dem.fetch("x", BBOX, ZOOM, 10, 10, 10, tmp_path / "o", tmp_path / "pusty_cache", offline=True,
                        log=lambda *_: None)
    args = ["--name", "cli", "--bbox", *map(str, BBOX), "--zoom", str(ZOOM), "--nx", "16", "--ny", "12", "--nz", "30",
            "--out", str(tmp_path / "o"), "--cache", str(tmp_path / "cache"), "--from-cache"]
    assert fetch_dem.main(args) == 1
    assert "Błąd: brak kafelka" in capsys.readouterr().err
    write_tiles(tmp_path / "cache", cone)
    assert fetch_dem.main(args) == 0
    assert (tmp_path / "o" / "cli.csv").is_file()
    with pytest.raises(DemError, match="bbox"):
        fetch_dem.fetch("x", (38, 15, 37, 16), ZOOM, 10, 10, 10, tmp_path, tmp_path, offline=True)
    # latlon_to_grid.py: kolumna, wysokość, okno, zagłębienia
    capsys.readouterr()
    assert l2g.main([str(tmp_path / "o" / "cli.json"), "37.655", "14.98", "--window", "1"]) == 0
    text = capsys.readouterr().out
    assert "x = 8, y = 6" in text and "okno 3×3" in text
    assert l2g.main([str(tmp_path / "o" / "cli.json"), "--cell", "8", "6"]) == 0
    assert "komórka x = 8, y = 6" in capsys.readouterr().out
    assert l2g.main([str(tmp_path / "o" / "cli.json"), "50", "15"]) == 1
