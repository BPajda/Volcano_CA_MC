"""Odczyt wyników i dane do wizualizacji: bin v1/v2, txt, mc_result.*, przekroje, ściany, powierzchnia,
próbkowanie, memmap, wynik MC z --mc-from, bezpieczeństwo identyfikatorów wyników."""

from __future__ import annotations

import json

import numpy as np
import pytest

from gui import render, results
from gui.results import ResultError, ResultStore

from .conftest import BASALT, LAVA, make_grid, write_ca_bin, write_ca_txt, write_mc


def store_with(tmp_path, name, g, ca="bin2", mc=None) -> ResultStore:
    folder = tmp_path / "results" / name
    folder.mkdir(parents=True)
    if ca == "bin2":
        write_ca_bin(folder, g, 2)
    elif ca == "bin1":
        write_ca_bin(folder, g, 1)
    elif ca == "txt":
        write_ca_txt(folder, g)
    if mc:
        write_mc(folder, g, mc)
    return ResultStore(tmp_path / "results")


def expected_cooling(g):
    end = int(max(g["solid"].max(), g["arrival"].max()))
    s, a = g["solid"].astype(np.int64), g["arrival"].astype(np.int64)
    c = np.where(g["type"] == BASALT, s - a, np.where(g["type"] == LAVA, end - a, 0))
    return np.clip(c, 0, 65535).astype(np.uint16)


@pytest.mark.parametrize("ca", ["bin2", "bin1", "txt"])
def test_read_ca_formats(tmp_path, grid, ca):
    d = store_with(tmp_path, "r", grid, ca).load("r")
    assert d.dims == (7, 5, 6)
    assert np.array_equal(d.type, grid["type"])
    assert np.array_equal(d.ca.flow, grid["flow"])
    if ca == "txt":
        assert np.allclose(d.ca.temp, np.round(grid["temp"], 1), atol=0.051)
        assert "cooling" not in d.fields()   # txt nie ma solidStep/arrivalStep
    else:
        assert np.array_equal(d.ca.temp, grid["temp"])
        assert np.array_equal(d.ca.solid, grid["solid"])
    if ca == "bin2":
        assert np.array_equal(d.ca.arrival, grid["arrival"])
        assert "cooling" in d.fields()
        full = d.extract("cooling", lambda a: np.asarray(a))
        assert np.array_equal(full, expected_cooling(grid))
    if ca == "bin1":
        assert d.ca.arrival is None and "cooling" not in d.fields()


@pytest.mark.parametrize("fmt", ["bin", "txt"])
def test_read_mc(tmp_path, grid, fmt):
    d = store_with(tmp_path, "r", grid, "bin2", mc=fmt).load("r")
    assert "crystal" in d.fields()
    assert np.array_equal(d.mc.crystal, grid["crystal"])
    assert d.ranges()["crystal"] == [0, int(grid["crystal"].max())]


def test_mc_full_without_ca(tmp_path, grid):
    """Tryb MC full: brak ca_result — typ komórki z domeny MC (kryształ > 0 -> bazalt)."""
    d = store_with(tmp_path, "r", grid, ca=None, mc="bin").load("r")
    assert d.fields() == ["type", "crystal"]
    assert np.array_equal(d.type, np.where(grid["crystal"] > 0, BASALT, 0))


def test_mc_from_uses_input_folder(tmp_path, grid):
    """Wynik `engine --mc-from`: typy komórek z folderu wejściowego (_mcFrom w config_used.json)."""
    root = tmp_path / "results"
    (root / "ca").mkdir(parents=True)
    write_ca_bin(root / "ca", grid)
    (root / "mc").mkdir()
    write_mc(root / "mc", grid)
    (root / "mc" / "config_used.json").write_text(json.dumps({"_mcFrom": str(root / "ca")}), encoding="utf-8")
    d = ResultStore(root).load("mc")
    assert d.ca_folder == root / "ca"
    assert np.array_equal(d.type, grid["type"])
    assert set(d.fields()) == {"type", "flowId", "temp", "crystal", "cooling"}


@pytest.mark.parametrize("axis", ["x", "y", "z"])
@pytest.mark.parametrize("field", ["type", "flowId", "temp", "crystal", "cooling"])
def test_slice_matches_numpy(tmp_path, grid, axis, field):
    d = store_with(tmp_path, "r", grid, "bin2", mc="bin").load("r")
    src = {"type": grid["type"], "flowId": grid["flow"], "temp": grid["temp"], "crystal": grid["crystal"],
           "cooling": expected_cooling(grid)}[field]
    n = {"x": 7, "y": 5, "z": 6}[axis]
    for index in (0, n // 2, n - 1):
        arr, step = d.slice(field, axis, index)
        exp = src[:, :, index] if axis == "x" else src[:, index, :] if axis == "y" else src[index]
        assert step == 1
        assert arr.shape == exp.shape and np.array_equal(arr, exp)
    with pytest.raises(ResultError):
        d.slice(field, axis, n)


def test_slice_sampling(tmp_path, monkeypatch):
    """Przekrój większy niż limit komórek jest próbkowany co `step` w obu osiach."""
    g = make_grid(40, 3, 30)
    d = store_with(tmp_path, "r", g).load("r")
    monkeypatch.setattr(render, "MAX_PLANE_CELLS", 100)
    arr, step = d.slice("type", "y", 1)  # 30 × 40 = 1200 komórek > 100
    assert step == render.sampling_step(30, 40, 100) == 4
    assert np.array_equal(arr, g["type"][:, 1, :][::4, ::4])


def test_faces_match_numpy(tmp_path, grid):
    d = store_with(tmp_path, "r", grid).load("r")
    faces = dict(d.faces("flowId", top_surface=False))
    f = grid["flow"]
    expected = {"x0": f[:, :, 0], "x1": f[:, :, -1], "y0": f[:, 0, :], "y1": f[:, -1, :], "z0": f[0], "z1": f[-1]}
    assert list(faces) == list(render.FACE_ORDER)
    for name, exp in expected.items():
        assert np.array_equal(faces[name], exp), name


def brute_top(t):
    nz, ny, nx = t.shape
    top = np.full((ny, nx), -1)
    for y in range(ny):
        for x in range(nx):
            for z in range(nz - 1, -1, -1):
                if t[z, y, x] != 0:
                    top[y, x] = z
                    break
    return top


def test_surface_map(tmp_path, grid):
    """Mapa powierzchni: najwyższa niepusta komórka kolumny + wartość pola na tej wysokości."""
    grid["type"][:, 0, 0] = 0  # pusta kolumna
    d = store_with(tmp_path, "r", grid).load("r")
    top = brute_top(grid["type"])
    assert np.array_equal(d.top(), top)
    assert np.array_equal(d.surface("height"), (top + 1).astype(np.uint16))
    temps = d.surface("temp")
    for y in range(5):
        for x in range(7):
            exp = grid["temp"][top[y, x], y, x] if top[y, x] >= 0 else 0
            assert temps[y, x] == exp
    # Górna ściana jako rzut z góry = mapa powierzchni.
    faces = dict(d.faces("type", top_surface=True))
    assert np.array_equal(faces["z1"], d.surface("type"))


def test_voxels_and_cell(tmp_path, grid):
    d = store_with(tmp_path, "r", grid, mc="bin").load("r")
    xyz, vals, total, step = d.voxels("flowId", limit=10**6)
    live = (grid["type"] == LAVA) | (grid["type"] == BASALT)
    assert total == int(live.sum()) and step == 1
    for (x, y, z), v in zip(xyz, vals):
        assert live[z, y, x] and v == grid["flow"][z, y, x]
    xyz2, _, total2, step2 = d.voxels("type", limit=5)
    assert total2 == total and len(xyz2) <= 5 and step2 > 1
    c = d.cell(3, 2, 1)
    assert c["type"] == grid["type"][1, 2, 3] and c["crystal"] == grid["crystal"][1, 2, 3]
    with pytest.raises(ResultError):
        d.cell(7, 0, 0)


def test_memmap_large_files(tmp_path, grid, monkeypatch):
    """Duże pliki bin są mapowane w pamięć (np.memmap) — wycinki takie same jak przy wczytaniu do RAM."""
    monkeypatch.setattr(results, "MEMMAP_MIN_BYTES", 0)
    d = store_with(tmp_path, "r", grid, mc="bin").load("r")
    assert isinstance(d.type, np.memmap) and isinstance(d.mc.crystal, np.memmap)
    assert "memmap" in d.ca.source
    arr, _ = d.slice("cooling", "y", 2)
    assert np.array_equal(arr, expected_cooling(grid)[:, 2, :])
    del d  # zwolnienie mapowania (Windows nie usunie zmapowanego pliku)


def test_truncated_and_bad_files(tmp_path, grid):
    folder = tmp_path / "results" / "bad"
    folder.mkdir(parents=True)
    write_ca_bin(folder, grid)
    data = (folder / "ca_result.bin").read_bytes()
    (folder / "ca_result.bin").write_bytes(data[:-10])
    with pytest.raises(ResultError, match="obcięty"):
        ResultStore(tmp_path / "results").load("bad")
    (folder / "ca_result.bin").write_bytes(b"XXXX" + data[4:])
    with pytest.raises(ResultError, match="VOLC"):
        ResultStore(tmp_path / "results").load("bad")


@pytest.mark.parametrize("rid", ["..", "../x", "..\\x", "a/../../x", "C:\\Windows", "/etc", "gui/../../x", "a/b/c", "", "a:b"])
def test_result_id_cannot_escape_results(tmp_path, grid, rid):
    store = store_with(tmp_path, "ok", grid)
    with pytest.raises(ResultError) as e:
        store.resolve(rid)
    assert e.value.status in (400, 404)


def test_listing(tmp_path, grid):
    root = tmp_path / "results"
    store = store_with(tmp_path, "cli_run", grid, mc="bin")
    (root / "gui" / "20261009-120000_x").mkdir(parents=True)
    write_ca_bin(root / "gui" / "20261009-120000_x", grid)
    (root / "gui" / "20261009-120000_x" / "gui_job.json").write_text(json.dumps({"name": "moje zadanie"}), encoding="utf-8")
    (root / "benchmark_x").mkdir()  # bez wyników — pomijany
    (root / "benchmark_x" / "benchmark.csv").write_text("a\n", encoding="utf-8")
    items = {r["id"]: r for r in store.list()}
    assert set(items) == {"cli_run", "gui/20261009-120000_x"}
    assert items["gui/20261009-120000_x"]["name"] == "moje zadanie" and items["gui/20261009-120000_x"]["gui"]
    assert items["cli_run"]["dims"] == [7, 5, 6] and items["cli_run"]["hasMc"]
    assert items["cli_run"]["format"] == "bin v2"


# ---------------------------------------------------------------- przez HTTP


def test_api_slice_faces_surface(client, settings, grid):
    folder = settings.results_dir / "r"
    folder.mkdir()
    write_ca_bin(folder, grid)
    write_mc(folder, grid)
    meta = client.get("/api/result", params={"id": "r"}).json()
    assert meta["dims"] == [7, 5, 6] and "crystal" in meta["fields"] and meta["planeAxis"] is None

    r = client.get("/api/result/slice", params={"id": "r", "field": "temp", "axis": "x", "index": 3})
    assert r.headers["content-type"] == "application/octet-stream"
    m = json.loads(r.headers["X-Meta"])
    arr = np.frombuffer(r.content, dtype=m["dtype"]).reshape(m["height"], m["width"])
    assert (m["hAxis"], m["vAxis"]) == ("y", "z")
    assert np.array_equal(arr, grid["temp"][:, :, 3])

    r = client.get("/api/result/faces", params={"id": "r", "field": "crystal"})
    m = json.loads(r.headers["X-Meta"])
    y1 = next(f for f in m["faces"] if f["name"] == "y1")
    arr = np.frombuffer(r.content, dtype="<i4", count=y1["width"] * y1["height"], offset=y1["offset"])
    assert np.array_equal(arr.reshape(y1["height"], y1["width"]), grid["crystal"][:, -1, :])

    r = client.get("/api/result/surface", params={"id": "r", "field": "height"})
    m = json.loads(r.headers["X-Meta"])
    h = np.frombuffer(r.content, dtype=m["dtype"]).reshape(m["height"], m["width"])
    assert np.array_equal(h, brute_top(grid["type"]) + 1)

    assert client.get("/api/result/cell", params={"id": "r", "x": 1, "y": 2, "z": 3}).json()["flowId"] == grid["flow"][3, 2, 1]
    assert client.get("/api/result/slice", params={"id": "r", "field": "type", "axis": "q", "index": 0}).status_code == 422
    assert client.get("/api/result/slice", params={"id": "r", "field": "type", "axis": "z", "index": 99}).status_code == 400
    assert client.get("/api/result", params={"id": "..\\..\\configs"}).status_code == 400
    assert client.get("/api/result", params={"id": "nie_ma"}).status_code == 404
