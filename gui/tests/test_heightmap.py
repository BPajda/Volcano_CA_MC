"""Mapy wysokości (gui/heightmap.py): walidacja CSV z komunikatami po polsku, konwersja obrazu PNG/JPG -> CSV
(jasność -> wysokość, skalowanie, wygładzanie, orientacja północ = y max), import przez API do configs/heightmaps/,
lista i dane mapy, a na końcu — silnik przyjmuje zapisany plik (walidacja i krótka symulacja)."""

from __future__ import annotations

import base64
import io
import json
import subprocess

import numpy as np
import pytest
from PIL import Image

from gui import heightmap as H

from .conftest import preset


def png_bytes(arr: np.ndarray, mode: str = "L", fmt: str = "PNG") -> bytes:
    buf = io.BytesIO()
    Image.fromarray(arr, mode=mode if mode != "L" else None).save(buf, format=fmt)
    return buf.getvalue()


def test_parse_csv_like_engine():
    h = H.parse_csv("# komentarz\n1, 2;3\n\n4\t5 6.5\n")
    assert h.shape == (2, 3) and h[1, 2] == 6.5
    for text, msg in (("1,2\n3,x\n", "wiersz 2, kolumna 2: „x” nie jest liczbą"),
                      ("1,2\n3\n", "wiersz 2: 1 wartości, a wiersz 1 ma 2"),
                      ("1,-2\n", "wysokość ujemna"),
                      ("# tylko komentarz\n\n", "brak wierszy z liczbami"),
                      ("1,inf\n", "nieskończona")):
        with pytest.raises(H.HeightmapError) as e:
            H.parse_csv(text, "mapa.csv")
        assert msg in str(e.value) and str(e.value).startswith("mapa.csv")


def test_csv_round_trip_and_resize():
    h = np.array([[0, 1.25, 2], [3, 4, 5.5]])
    text = H.heights_to_csv(h, "opis")
    assert text.splitlines()[1] == "# opis" and np.array_equal(H.parse_csv(text), h)
    assert H.heights_to_csv(np.array([[1.0, 2.0]])).splitlines()[-1] == "1,2"  # całkowite bez „.0”
    big, info = H.csv_to_heights("0,10\n0,10\n", "x", nx=5, ny=3, nz=8)
    assert big.shape == (3, 5) and info["resized"] and info["clipped"] and big.max() == 8.0
    assert np.allclose(big[:, 0], 0)


def test_image_to_heights_gradient_orientation_smoothing():
    # Górna połowa obrazu biała (północ = wysoko), dolna czarna.
    img = np.zeros((40, 60), np.uint8)
    img[:20, :] = 255
    h, info = H.image_to_heights(png_bytes(img), nx=30, ny=20, nz=50, max_height=40, base=2)
    assert h.shape == (20, 30) and info["format"] == "PNG" and info["imageSize"] == [60, 40]
    assert h[-1].mean() == pytest.approx(40, abs=0.5) and h[0].mean() == pytest.approx(2, abs=0.5)  # y max = góra obrazu
    inv, _ = H.image_to_heights(png_bytes(img), nx=30, ny=20, nz=50, max_height=40, invert=True)
    assert inv[0].mean() == pytest.approx(40, abs=0.5)
    sm, _ = H.image_to_heights(png_bytes(img), nx=30, ny=20, nz=50, max_height=40, smooth_radius=3)
    assert np.abs(np.diff(sm[:, 5])).max() < np.abs(np.diff(h[:, 5])).max()   # wygładzenie łagodzi skok
    clipped, _ = H.image_to_heights(png_bytes(img), nx=30, ny=20, nz=10, max_height=40)
    assert clipped.max() == 10
    # JPG, RGB (jasność z luminancji) i PNG 16-bitowy.
    rgb = np.zeros((10, 10, 3), np.uint8)
    rgb[..., 1] = 255
    hj, info = H.image_to_heights(png_bytes(rgb, "RGB", "JPEG"), nx=10, ny=10, nz=100, max_height=100)
    assert info["format"] == "JPEG" and 50 < hj.mean() < 70   # zielony ≈ 59% jasności
    g16 = (np.linspace(0, 65535, 16).reshape(4, 4)).astype(np.uint16)
    h16, _ = H.image_to_heights(png_bytes(g16, "I;16"), nx=4, ny=4, nz=100, max_height=100)
    assert h16.max() == pytest.approx(100, abs=0.5) and h16.min() == pytest.approx(0, abs=0.5)


def test_image_errors(monkeypatch):
    with pytest.raises(H.HeightmapError, match="to nie jest obraz"):
        H.image_to_heights(b"x,y\n1,2\n", 10, 10, 10, 5)
    monkeypatch.setattr(H, "MAX_IMAGE_PIXELS", 100)
    with pytest.raises(H.HeightmapError, match="za duży"):
        H.image_to_heights(png_bytes(np.zeros((20, 20), np.uint8)), 10, 10, 10, 5)
    with pytest.raises(H.HeightmapError, match="więcej niż"):
        H.image_to_heights(png_bytes(np.zeros((5, 5), np.uint8)), 3000, 3000, 10, 5)
    with pytest.raises(H.HeightmapError, match="podstawy"):
        H.image_to_heights(png_bytes(np.zeros((5, 5), np.uint8)), 5, 5, 10, 5, base=9)


def test_api_import_list_data_and_engine_accepts(client, settings, engine_path):
    img = np.tile(np.linspace(0, 255, 64).astype(np.uint8), (48, 1))   # jasność rośnie na wschód
    body = {"name": "Moja kaldera ąę", "kind": "image", "data": base64.b64encode(png_bytes(img)).decode(),
            "nx": 40, "ny": 30, "nz": 30, "maxHeight": 20, "base": 1, "smooth": 1}
    r = client.post("/api/heightmaps", json=body)
    assert r.status_code == 201, r.json()
    res = r.json()
    assert res["file"] == "configs/heightmaps/Moja_kaldera_ae.csv" and (res["nx"], res["ny"]) == (40, 30)
    path = settings.root / res["file"]
    h = H.parse_csv(path.read_text(encoding="utf-8"))
    assert h.shape == (30, 40) and h[:, -1].mean() > h[:, 0].mean() + 15
    # Ta sama nazwa drugi raz — nowy plik z przyrostkiem, stary nienadpisany.
    assert client.post("/api/heightmaps", json=body).json()["file"].endswith("Moja_kaldera_ae-2.csv")
    maps = {m["name"]: m for m in client.get("/api/heightmaps").json()}
    assert maps["Moja_kaldera_ae"]["nx"] == 40 and maps["Moja_kaldera_ae"]["max"] <= 20
    d = client.get("/api/heightmaps/data", params={"file": res["file"]})
    meta = json.loads(d.headers["X-Meta"])
    assert np.allclose(np.frombuffer(d.content, "<f4").reshape(meta["height"], meta["width"]), h, atol=1e-4)
    for bad in ("../configs/test_2d.json", "configs/heightmaps/../test_2d.json", "configs/heightmaps/nie_ma.csv"):
        assert client.get("/api/heightmaps/data", params={"file": bad}).status_code == 404

    # Błędne pliki — czytelne komunikaty, nic nie jest zapisywane.
    before = len(list(settings.heightmaps_dir.glob("*.csv")))
    err = client.post("/api/heightmaps", json={"name": "zly", "kind": "csv", "data": "1,2\n3\n"})
    assert err.status_code == 422 and "wiersz 2" in err.json()["detail"]
    err = client.post("/api/heightmaps", json={"name": "zly", "kind": "image", "data": "%%%", "nx": 5, "ny": 5, "nz": 5})
    assert err.status_code == 422 and "base64" in err.json()["detail"]
    assert len(list(settings.heightmaps_dir.glob("*.csv"))) == before
    csv_ok = client.post("/api/heightmaps", json={"name": "z_csv", "kind": "csv", "data": "0,1,2\n1,2,3\n", "nz": 10}).json()
    assert (csv_ok["nx"], csv_ok["ny"]) == (3, 2)

    # Silnik przyjmuje zapisany plik: walidacja i krótka symulacja lawy na tej mapie.
    cfg = preset("test_3d", **{"space.nx": 40, "space.ny": 30, "space.nz": 30, "terrain.type": "file",
                               "terrain.file": res["file"], "vents.count": 1, "vents.placement": "random",
                               "ca.maxSteps": 20, "output.format": "bin"})
    assert client.post("/api/validate", json={"config": cfg}).json()["ok"]
    wrong = dict(cfg, space={"nx": 41, "ny": 30, "nz": 30})
    v = client.post("/api/validate", json={"config": wrong}).json()
    assert not v["ok"] and "oczekiwano nx = 41" in v["errors"][0]
    cfg_path = settings.root / "cfg.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
    p = subprocess.run([str(engine_path), "--config", str(cfg_path), "--out", str(settings.root / "out")], cwd=settings.root,
                       capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0, p.stderr
