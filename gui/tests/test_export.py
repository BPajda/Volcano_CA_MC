"""Eksport wyników (gui/export.py): plik VTK ImageData (.vti) — sprawdzany zwykłym parserem XML (dekodowanie base64,
nagłówki UInt64, bloki zlib) i porównany z tablicami źródłowymi; ZIP folderu wyniku; to samo przez HTTP.
Do tego agregacja wyników do tabeli porównania (gui/compare.py) bez silnika."""

from __future__ import annotations

import base64
import io
import json
import math
import xml.etree.ElementTree as ET
import zipfile
import zlib

import numpy as np
import pytest

from gui import compare
from gui.export import write_vti, zip_result
from gui.results import ResultStore

from .conftest import BASALT, LAVA, make_grid, write_ca_bin, write_mc

VTK_DTYPES = {"UInt8": "<u1", "UInt16": "<u2", "Int32": "<i4", "Float32": "<f4"}


def _b64_prefix(text: str, nbytes: int) -> tuple[bytes, str]:
    """Pierwsze nbytes bajtów zakodowanych osobno (nagłówek VTK) i reszta tekstu."""
    chars = 4 * math.ceil(nbytes / 3)
    return base64.b64decode(text[:chars])[:nbytes], text[chars:]


def read_vti(path) -> tuple[dict, dict[str, np.ndarray]]:
    """Niezależny czytnik plików .vti (XML) — taki, jak opisuje format VTK."""
    root = ET.parse(path).getroot()
    assert root.tag == "VTKFile" and root.get("type") == "ImageData" and root.get("byte_order") == "LittleEndian"
    img = root.find("ImageData")
    info = {"extent": [int(v) for v in img.get("WholeExtent").split()], "compressor": root.get("compressor"),
            "scalars": img.find("Piece/CellData").get("Scalars")}
    arrays = {}
    for da in img.iter("DataArray"):
        dt, text = VTK_DTYPES[da.get("type")], (da.text or "").strip()
        if da.get("format") == "ascii":
            arrays[da.get("Name")] = np.array(text.split(), dtype=np.float64).astype(dt)
            continue
        if info["compressor"]:
            head, _ = _b64_prefix(text, 8)
            nblocks = int(np.frombuffer(head, "<u8")[0])
            head, rest = _b64_prefix(text, 8 * (3 + nblocks))
            h = np.frombuffer(head, "<u8")
            data, raw, pos = b"", base64.b64decode(rest), 0
            for size in h[3:]:
                data += zlib.decompress(raw[pos:pos + int(size)])
                pos += int(size)
            assert len(data) == (h[0] - 1) * h[1] + h[2]
        else:
            head, rest = _b64_prefix(text, 8)
            data = base64.b64decode(rest)
            assert len(data) == int(np.frombuffer(head, "<u8")[0])
        arrays[da.get("Name")] = np.frombuffer(data, dt)
    return info, arrays


@pytest.fixture
def result_store(tmp_path):
    g = make_grid(9, 6, 7, seed=3)
    folder = tmp_path / "results" / "r"
    folder.mkdir(parents=True)
    write_ca_bin(folder, g)
    write_mc(folder, g)
    (folder / "times.json").write_text("{}", encoding="utf-8")
    (folder / "snapshots").mkdir()
    (folder / "snapshots" / "step_000001.bin").write_bytes(b"x" * 10)
    return ResultStore(tmp_path / "results"), g


@pytest.mark.parametrize("fmt", ["zlib", "binary", "ascii"])
def test_vti_matches_source_arrays(tmp_path, result_store, fmt):
    store, g = result_store
    d = store.load("r")
    path = write_vti(d, tmp_path / f"r_{fmt}.vti", fmt)
    info, arr = read_vti(path)
    assert info["extent"] == [0, 9, 0, 6, 0, 7] and info["scalars"] == "crystal"
    assert (info["compressor"] == "vtkZLibDataCompressor") == (fmt == "zlib")
    assert list(arr) == ["type", "flowId", "temp", "solidStep", "arrivalStep", "cooling", "crystal"]
    # Kolejność komórek VTK (x najszybciej, potem y, z) = kolejność w plikach .bin = ravel tablicy (nz, ny, nx).
    assert np.array_equal(arr["type"], g["type"].ravel())
    assert np.array_equal(arr["flowId"], g["flow"].ravel())
    assert np.array_equal(arr["temp"], g["temp"].ravel())   # ascii z %.9g — float32 bez strat
    assert np.array_equal(arr["arrivalStep"], g["arrival"].ravel())
    assert np.array_equal(arr["crystal"], g["crystal"].ravel())
    cooling = d.extract("cooling", lambda a: np.asarray(a))
    assert np.array_equal(arr["cooling"], cooling.ravel())


def test_vti_mc_full_without_ca(tmp_path):
    g = make_grid(5, 4, 1)
    folder = tmp_path / "results" / "mc"
    folder.mkdir(parents=True)
    write_mc(folder, g)
    info, arr = read_vti(write_vti(ResultStore(tmp_path / "results").load("mc"), tmp_path / "mc.vti"))
    assert list(arr) == ["type", "crystal"] and info["extent"] == [0, 5, 0, 4, 0, 1]
    assert np.array_equal(arr["type"], np.where(g["crystal"].ravel() > 0, BASALT, 0))


def test_zip_contains_whole_folder(result_store):
    store, _ = result_store
    folder = store.resolve("r")
    path = zip_result(folder, "wynik_r")
    try:
        with zipfile.ZipFile(path) as z:
            names = sorted(z.namelist())
            assert names == ["wynik_r/ca_result.bin", "wynik_r/mc_result.bin", "wynik_r/snapshots/step_000001.bin",
                             "wynik_r/times.json"]
            assert z.read("wynik_r/ca_result.bin") == (folder / "ca_result.bin").read_bytes()
            assert z.testzip() is None
    finally:
        path.unlink()


def test_api_zip_and_vtk(client, settings):
    g = make_grid(6, 5, 4)
    folder = settings.results_dir / "r"
    folder.mkdir()
    write_ca_bin(folder, g)
    (folder / "engine.log").write_text("log\n", encoding="utf-8")
    r = client.get("/api/result/zip", params={"id": "r"})
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    assert 'filename="r.zip"' in r.headers["content-disposition"]
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        assert sorted(z.namelist()) == ["r/ca_result.bin", "r/engine.log"]
    r = client.get("/api/result/vtk", params={"id": "r", "format": "binary"})
    assert r.status_code == 200 and 'filename="r.vti"' in r.headers["content-disposition"]
    p = settings.root / "pobrany.vti"
    p.write_bytes(r.content)
    _, arr = read_vti(p)
    assert np.array_equal(arr["flowId"], g["flow"].ravel())
    assert client.get("/api/result/vtk", params={"id": "r", "format": "xml"}).status_code == 422
    assert client.get("/api/result/zip", params={"id": "..\\..\\configs"}).status_code == 400


# ---------------------------------------------------------------- tabela porównania (bez silnika)


def fake_result(folder, mode, cells, **times):
    folder.mkdir(parents=True)
    t = {"mode": mode, "cells": cells, "space": [int(cells ** 0.5), int(cells ** 0.5), 1],
         "neighborhood": "von_neumann", "boundary": "periodic", "total": 10.0,
         "memory": {"peakRssBytes": 3 * 1024 * 1024, "model": {"peakBytes": 1024 * 1024, "peakBytesPerCell": 40.0}},
         "files": {"ca_result.bin": {"bytes": 1024 * 1024}}, **times}
    (folder / "times.json").write_text(json.dumps(t), encoding="utf-8")
    (folder / "config_used.json").write_text(json.dumps({"vents": {"count": 7}, "rngSeed": cells}), encoding="utf-8")
    (folder / "stats.json").write_text(json.dumps({"grains": 7, "mc": {"grainsEnd": 5, "meanGrainSizeEnd": 2.5}}),
                                       encoding="utf-8")


def test_compare_rows_series_and_csv(tmp_path):
    res = tmp_path / "results"
    batch = res / "seria_cli"
    fake_result(batch / "01_ca", "classic", 100, caSim=2.0, steps=10)
    fake_result(batch / "02_mc", "mc_full", 100, mcSim=8.0, mcs=20, domainCells=100)
    (batch / "03_blad").mkdir()
    (batch / "batch_summary.csv").write_text("name,status\n", encoding="utf-8")
    src = compare.find_series(res)
    assert [s["ref"] for s in src] == ["seria_cli"] and src[0]["jobs"] == 3 and src[0]["done"] == 2
    t = compare.series_table(res, "seria_cli")
    rows = {r["name"]: r for r in t["rows"]}
    ca, mc = rows["01_ca"], rows["02_mc"]
    assert ca["algorithm"] == "CA" and ca["simMs"] == 2.0 and ca["nsPerCellStep"] == pytest.approx(2000.0)
    assert ca["seeds"] == 7 and ca["peakRssMiB"] == 3.0 and ca["outputMiB"] == 1.0 and ca["dim"] == "2D"
    assert mc["algorithm"] == "MC" and mc["simMs"] == 8.0 and mc["nsPerTrial"] == pytest.approx(4000.0) and mc["seeds"] is None
    assert mc["mcGrainsEnd"] == 5 and rows["03_blad"]["status"] == "brak wyniku"
    # Bez series.json parametry zmienne wykrywane z config_used.json (tu: rngSeed takie samo — brak różnic).
    assert ca["values"] == {} and ca["id"] == "seria_cli/01_ca"
    text = compare.table_csv(t)
    lines = text.splitlines()
    assert lines[0].startswith("index,name,status,algorithm") and len(lines) == 4 and "01_ca" in lines[1]
    sel = compare.results_table(res, ["seria_cli/01_ca", "seria_cli/02_mc"])
    assert [r["algorithm"] for r in sel["rows"]] == ["CA", "MC"]
    with pytest.raises(compare.CompareError):
        compare.series_table(res, "../x")
    with pytest.raises(compare.CompareError):
        compare.results_table(res, [])
    assert LAVA == 2
