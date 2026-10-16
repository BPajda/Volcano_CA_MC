"""Odtwarzanie erupcji krok po kroku (etap 6): stan w kroku k z arrivalStep / solidStep = migawka silnika
(output.snapshotsEvery), temperatura z parametrów stygnięcia, liczby komórek = activeCells silnika, endpointy
/api/result/replay*, pola appear / solidFrom / terrain, migawki MC (mcs=<k>), ta sama reguła w przeglądarce
(gui/static/js/replay.js uruchomiony przez node)."""

from __future__ import annotations

import json
import shutil
import struct
import subprocess
from pathlib import Path

import numpy as np
import pytest

from gui import replay
from gui.results import ResultStore

from .conftest import ROOT

AIR, ROCK, LAVA, BASALT = 0, 1, 2, 3
SMALL_3D = ["space.nx=36", "space.ny=36", "space.nz=28", "terrain.peakHeight=20", "terrain.baseRadius=18",
            "terrain.craterRadius=4", "terrain.craterDepth=2", "vents.count=3", "ca.coolingAmbient=2",
            "ca.coolingLateral=4", "ca.coolingFall=2", "vents.eruptionSteps=40"]
SMALL_2D = ["space.nx=100", "space.nz=50", "terrain.peakHeight=35", "terrain.baseRadius=45", "terrain.craterRadius=8",
            "terrain.craterDepth=4", "ca.coolingAmbient=2", "ca.coolingLateral=8", "ca.coolingFall=5",
            "vents.eruptionSteps=10"]
CASES = {
    "lava3d": SMALL_3D,
    "lava3d_positions": SMALL_3D + ["vents.placement=positions", "vents.count=2", "vents.positions=[[18,18],[26,12]]"],
    "lava2d": SMALL_2D,
    "classic": ["ca.mode=classic", "space.nx=40", "space.ny=40", "space.nz=1", "vents.count=12"],
}


def run_engine(engine: Path, out: Path, overrides: list[str]) -> Path:
    args = [str(engine), "--out", str(out)]
    for o in overrides + ["output.format=bin"]:
        args += ["--set", o]
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT)
    assert p.returncode == 0, p.stderr
    return out


def read_volc(path: Path) -> dict:
    raw = path.read_bytes()
    _, nx, ny, nz = struct.unpack("<4i", raw[4:20])
    n = nx * ny * nz
    shape = (nz, ny, nx)
    return {"type": np.frombuffer(raw, np.uint8, n, 20).reshape(shape),
            "flow": np.frombuffer(raw, "<i4", n, 20 + n).reshape(shape),
            "temp": np.frombuffer(raw, "<f4", n, 20 + 5 * n).reshape(shape)}


@pytest.fixture(scope="module")
def engine_runs(tmp_path_factory) -> dict:
    """Przebiegi silnika z migawkami co 7 kroków (+ MC z migawkami co 3 MCS)."""
    from gui.settings import find_engine
    exe = find_engine(ROOT)
    if exe is None:
        pytest.skip("brak zbudowanego silnika")
    base = tmp_path_factory.mktemp("replay") / "results"
    out = {name: run_engine(exe, base / name, ov + ["output.snapshotsEvery=7"]) for name, ov in CASES.items()}
    out["mc"] = run_engine(exe, base / "mc", SMALL_2D + ["mc.enabled=true", "mc.mcs=7", "mc.statsEvery=3",
                                                         "mc.snapshotsEvery=3"])
    return {"store": ResultStore(base), "dirs": out}


def test_rule_on_tiny_grid():
    t = np.array([ROCK, AIR, LAVA, BASALT, BASALT, LAVA], dtype=np.uint8)
    arrival = np.array([0, 0, 5, 0, 3, 0], dtype=np.uint16)
    solid = np.array([0, 0, 0, 10, 4, 0], dtype=np.uint16)
    vent = np.array([0, 0, 0, 1, 0, 0], dtype=bool)
    a = replay.appear_steps(t, arrival, vent)
    s = replay.solid_from(t, solid)
    assert a.tolist() == [replay.NEVER, replay.NEVER, 6, 0, 4, 1]   # krater (vent) w stanie 0, reszta arrival + 1
    assert replay.appear_steps(t, arrival).tolist() == [replay.NEVER, replay.NEVER, 6, 0, 4, 0]  # bez listy kraterów
    assert s.tolist() == [replay.NEVER, replay.NEVER, replay.NEVER, 11, 5, replay.NEVER]
    assert replay.state_at(t, a, s, 0).tolist() == [ROCK, AIR, AIR, LAVA, AIR, AIR]
    assert replay.state_at(t, a, s, 4).tolist() == [ROCK, AIR, AIR, LAVA, LAVA, LAVA]
    assert replay.state_at(t, a, s, 6).tolist() == [ROCK, AIR, LAVA, LAVA, BASALT, LAVA]
    assert replay.state_at(t, a, s, 11).tolist() == [ROCK, AIR, LAVA, BASALT, BASALT, LAVA]
    liquid, solid_n = replay.counts_per_step(a, s, 12)
    assert liquid[0] == 1 and liquid[4] == 3 and liquid[6] == 3 and liquid[11] == 2
    assert solid_n[4] == 0 and solid_n[5] == 1 and solid_n[12] == 2
    temp = np.array([0, 0, 900, 790, 795, 1000], dtype=np.float32)
    T = replay.temp_at(t, temp, s, 12, 8, cooling_ambient=3.0, erupt_temp=1200.0)
    assert T[2] == pytest.approx(900 + 3 * 4) and T[3] == pytest.approx(790 + 3 * 3)
    assert replay.temp_at(t, temp, s, 12, 0, 3.0, 800.0)[3] == 800.0   # krater w trakcie erupcji: eruptTemp


@pytest.mark.parametrize("name", list(CASES))
def test_replay_equals_engine_snapshots(engine_runs, name):
    d = engine_runs["store"].load(name)
    info = d.replay_info()
    snaps = d.snapshot_steps()
    assert snaps[0] == 0 and snaps[-1] == info["steps"] and len(snaps) >= 3
    assert info["ventsExact"]
    t, a = np.asarray(d.type), d.extract("appear", np.asarray)
    s = d.extract("solidFrom", np.asarray)
    cfg = json.loads((d.folder / "config_used.json").read_text(encoding="utf-8"))
    for k in snaps:
        snap = read_volc(d.folder / "snapshots" / f"step_{k:06d}.bin")
        state = replay.state_at(t, a, s, k)
        assert np.array_equal(state, snap["type"]), f"krok {k}"
        live = (state == LAVA) | (state == BASALT)
        assert np.array_equal(np.asarray(d.ca.flow)[live], snap["flow"][live])
        if cfg["ca"]["mode"] == "lava":
            liquid = state == LAVA
            T = replay.temp_at(t, np.asarray(d.ca.temp), s, info["steps"], k, cfg["ca"]["coolingAmbient"],
                               cfg["vents"]["eruptTemp"])
            assert np.abs(T[liquid] - snap["temp"][liquid]).max(initial=0) < 0.05
    # Liczba komórek płynnych w każdym kroku = activeCells silnika (stats.json).
    stats = json.loads((d.folder / "stats.json").read_text(encoding="utf-8"))
    total = [l + so for l, so in zip(info["liquid"], info["solid"])] if info["mode"] == "classic" else info["liquid"]
    assert total[1:] == stats["activeCells"]


def test_replay_without_vents_is_approximate(engine_runs, tmp_path):
    """Bez listy kraterów (brak stats.json) komórki z arrivalStep = 0 pojawiają się w stanie 0 — różnica tylko tam."""
    src = engine_runs["dirs"]["lava3d"]
    dst = tmp_path / "results" / "bez_stats"
    shutil.copytree(src, dst)
    (dst / "stats.json").unlink()
    d = ResultStore(tmp_path / "results").load("bez_stats")
    info = d.replay_info()
    assert info["vents"] is None and not info["ventsExact"]
    exact = engine_runs["store"].load("lava3d")
    a1, a0 = exact.extract("appear", np.asarray), d.extract("appear", np.asarray)
    diff = a1 != a0
    assert diff.any() and np.all(a1[diff] == 1) and np.all(a0[diff] == 0)


def test_replay_cells_package_and_sampling(engine_runs):
    d = engine_runs["store"].load("lava3d")
    c = d.replay_cells()
    n = int(np.count_nonzero((np.asarray(d.type) == LAVA) | (np.asarray(d.type) == BASALT)))
    assert c["appear"].size == n == c["total"] and c["step"] == 1
    x, y, z = c["xyz"].T.astype(int)
    assert np.array_equal(c["flowId"], np.asarray(d.ca.flow)[z, y, x])
    assert np.array_equal(c["appear"], d.extract("appear", np.asarray)[z, y, x])
    s = d.replay_cells(limit=max(1, n // 5))
    assert s["step"] >= 2 and s["appear"].size < n
    assert np.all(s["xyz"][:, 0] % s["step"] == 0) and np.all(s["xyz"][:, 1] % s["step"] == 0)


def test_api_replay_endpoints(engine_runs, settings):
    import warnings
    warnings.filterwarnings("ignore", message="Using `httpx` with `starlette.testclient`")
    from fastapi.testclient import TestClient
    from gui.app import create_app
    shutil.copytree(engine_runs["dirs"]["lava3d"], settings.results_dir / "lava3d")
    shutil.copytree(engine_runs["dirs"]["mc"], settings.results_dir / "mc")
    with TestClient(create_app(settings, start_workers=False)) as client:
        meta = client.get("/api/result", params={"id": "lava3d"}).json()
        assert meta["replay"] is True and meta["snapshots"][0] == 0 and meta["mcSnapshots"] == []
        info = client.get("/api/result/replay", params={"id": "lava3d"}).json()
        assert len(info["liquid"]) == info["steps"] + 1 and info["params"]["coolingAmbient"] == 2.0
        r = client.get("/api/result/replay/cells", params={"id": "lava3d"})
        m = json.loads(r.headers["X-Meta"])
        n = m["count"]
        assert len(r.content) == n * (4 * 4 + 6) and m["layout"][0] == "appear:int32"
        appear = np.frombuffer(r.content, "<i4", n, 0)
        assert appear.min() == 0 and appear.max() <= info["steps"]
        sl = client.get("/api/result/slice", params={"id": "lava3d", "field": "appear", "axis": "z", "index": 15})
        assert json.loads(sl.headers["X-Meta"])["dtype"] == "int32"
        terr = client.get("/api/result/surface", params={"id": "lava3d", "field": "terrain"})
        h = np.frombuffer(terr.content, "<u2").reshape(36, 36)
        top = np.frombuffer(client.get("/api/result/surface", params={"id": "lava3d", "field": "height"}).content,
                            "<u2").reshape(36, 36)
        assert np.all(top >= h) and np.any(top > h)   # lawa leży na terenie
        # Migawki MC: przekrój kryształów z migawki = plik migawki; brak migawki -> 404.
        mmeta = client.get("/api/result", params={"id": "mc"}).json()
        assert mmeta["mcSnapshots"] == [0, 3, 6, 7]
        sl = client.get("/api/result/slice", params={"id": "mc", "field": "crystal", "axis": "y", "index": 0, "mcs": 3})
        raw = (settings.results_dir / "mc" / "mc_snapshots" / "mcs_000003.bin").read_bytes()
        want = np.frombuffer(raw, "<i4", offset=16).reshape(50, 1, 100)[:, 0, :]
        assert np.array_equal(np.frombuffer(sl.content, "<i4").reshape(50, 100), want)
        assert client.get("/api/result/slice", params={"id": "mc", "field": "crystal", "axis": "y", "index": 0,
                                                       "mcs": 4}).status_code == 404
        assert client.get("/api/result/faces", params={"id": "mc", "field": "crystal", "mcs": 0}).status_code == 200


def test_js_replay_matches_python(engine_runs, tmp_path):
    """Ta sama reguła w przeglądarce: replay.js (node) liczy stany i liczby komórek jak gui/replay.py."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("brak node — test zgodności JS pominięty")
    d = engine_runs["store"].load("lava3d")
    info = d.replay_info()
    t = np.asarray(d.type).ravel()
    a = d.extract("appear", np.asarray).ravel()
    s = d.extract("solidFrom", np.asarray).ravel()
    temp = np.asarray(d.ca.temp).ravel()
    ks = [0, 3, info["steps"] // 2, info["steps"]]
    data = {"type": t.tolist(), "appear": a.tolist(), "solidFrom": s.tolist(), "temp": temp.tolist(), "ks": ks,
            "steps": info["steps"], "params": info["params"]}
    (tmp_path / "data.json").write_text(json.dumps(data), encoding="utf-8")
    js = (ROOT / "gui" / "static" / "js" / "replay.js").as_uri()
    script = tmp_path / "check.mjs"
    script.write_text(f"""
import {{ readFileSync }} from 'node:fs';
import {{ stateAt, tempAt }} from '{js}';
const d = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const out = {{}};
for (const k of d.ks) {{
  const st = d.type.map((t, i) => stateAt(k, t, d.appear[i], d.solidFrom[i]));
  const T = d.type.map((t, i) => st[i] === 2 ? tempAt(k, t, d.temp[i], d.solidFrom[i], d.steps, d.params) : 0);
  out[k] = {{ st, T }};
}}
console.log(JSON.stringify(out));
""", encoding="utf-8")
    p = subprocess.run([node, str(script), str(tmp_path / "data.json")], capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0, p.stderr
    res = json.loads(p.stdout)
    for k in ks:
        want = replay.state_at(t, a, s, k)
        assert res[str(k)]["st"] == want.tolist(), f"krok {k}"
        liquid = want == LAVA
        T = replay.temp_at(t, temp, s, info["steps"], k, info["params"]["coolingAmbient"], info["params"]["eruptTemp"])
        assert np.allclose(np.array(res[str(k)]["T"])[liquid], T[liquid])
