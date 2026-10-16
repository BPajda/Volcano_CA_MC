"""Wspólne elementy testów backendu GUI: sztuczne wyniki zapisane wg formatu z docs/uruchamianie.md
(niezależnie od czytnika), ustawienia z katalogami tymczasowymi i klient HTTP aplikacji."""

from __future__ import annotations

import json
import shutil
import struct
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gui.settings import Settings, find_engine  # noqa: E402

AIR, ROCK, LAVA, BASALT = 0, 1, 2, 3


def make_grid(nx: int, ny: int, nz: int, seed: int = 1) -> dict:
    """Mały „wulkan”: skała do wysokości h(x, y), nad nią warstwa lawy/bazaltu, reszta powietrze.
    Tablice w układzie (nz, ny, nx), jak w plikach (indeks x + nx·(y + ny·z))."""
    rng = np.random.default_rng(seed)
    t = np.zeros((nz, ny, nx), np.uint8)
    h = rng.integers(0, max(1, nz - 2), size=(ny, nx))
    for y in range(ny):
        for x in range(nx):
            t[: h[y, x], y, x] = ROCK
            if h[y, x] < nz and rng.random() < 0.5:
                t[h[y, x], y, x] = LAVA if rng.random() < 0.3 else BASALT
    live = (t == LAVA) | (t == BASALT)
    flow = np.where(live, rng.integers(1, 4, size=t.shape), 0).astype(np.int32)
    temp = np.where(live, rng.uniform(790, 1200, size=t.shape), 0).astype(np.float32)
    arrival = np.where(live, rng.integers(0, 50, size=t.shape), 0).astype(np.uint16)
    solid = np.where(t == BASALT, arrival + rng.integers(1, 30, size=t.shape), 0).astype(np.uint16)
    crystal = np.where(live, rng.integers(1, 20, size=t.shape), 0).astype(np.int32)
    return {"type": t, "flow": flow, "temp": temp, "solid": solid, "arrival": arrival, "crystal": crystal}


def write_ca_bin(folder: Path, g: dict, version: int = 2) -> None:
    nz, ny, nx = g["type"].shape
    with open(folder / "ca_result.bin", "wb") as f:
        f.write(b"VOLC" + struct.pack("<4i", version, nx, ny, nz))
        f.write(g["type"].tobytes())
        f.write(g["flow"].astype("<i4").tobytes())
        f.write(g["temp"].astype("<f4").tobytes())
        f.write(g["solid"].astype("<u2").tobytes())
        if version >= 2:
            f.write(g["arrival"].astype("<u2").tobytes())


def write_ca_txt(folder: Path, g: dict) -> None:
    nz, ny, nx = g["type"].shape
    lines = [f"{nx} {ny} {nz}", "x y z type flowId temp"]
    for z in range(nz):
        for y in range(ny):
            for x in range(nx):
                lines.append(f"{x} {y} {z} {g['type'][z, y, x]} {g['flow'][z, y, x]} {g['temp'][z, y, x]:.1f}")
    (folder / "ca_result.txt").write_text("\n".join(lines) + "\n", encoding="ascii")


def write_mc(folder: Path, g: dict, fmt: str = "bin") -> None:
    nz, ny, nx = g["crystal"].shape
    if fmt == "bin":
        with open(folder / "mc_result.bin", "wb") as f:
            f.write(b"VMC1" + struct.pack("<3i", nx, ny, nz) + g["crystal"].astype("<i4").tobytes())
    else:
        lines = [f"{nx} {ny} {nz}", "x y z crystal"]
        for z in range(nz):
            for y in range(ny):
                for x in range(nx):
                    lines.append(f"{x} {y} {z} {g['crystal'][z, y, x]}")
        (folder / "mc_result.txt").write_text("\n".join(lines) + "\n", encoding="ascii")


@pytest.fixture
def grid() -> dict:
    return make_grid(7, 5, 6)


@pytest.fixture
def engine_path() -> Path:
    exe = find_engine(ROOT)
    if exe is None:
        pytest.skip("brak zbudowanego silnika (cmake --build --preset msvc-release)")
    return exe


@pytest.fixture
def settings(tmp_path: Path, engine_path: Path) -> Settings:
    """Projekt w katalogu tymczasowym: configs/ (kopie kilku presetów) i pusty results/."""
    (tmp_path / "configs").mkdir()
    (tmp_path / "results").mkdir()
    for name in ("test_2d", "test_3d", "lava_mc_2d", "mc_full_2d"):
        shutil.copy(ROOT / "configs" / f"{name}.json", tmp_path / "configs")
    return Settings(root=tmp_path, engine=engine_path, engine_source="test", configs_dir=tmp_path / "configs",
                    results_dir=tmp_path / "results")


@pytest.fixture
def client(settings: Settings):
    import warnings

    # Starlette ostrzega o przyszłej zmianie klienta testowego (httpx) — nie dotyczy działania GUI.
    warnings.filterwarnings("ignore", message="Using `httpx` with `starlette.testclient`")
    from fastapi.testclient import TestClient

    from gui.app import create_app

    with TestClient(create_app(settings)) as c:
        yield c


def preset(name: str, **overrides) -> dict:
    """Config z configs/<name>.json z nadpisaniami w postaci {'ca.maxSteps': 50}."""
    cfg = json.loads((ROOT / "configs" / f"{name}.json").read_text(encoding="utf-8"))
    for path, value in overrides.items():
        node = cfg
        *parents, last = path.split(".")
        for p in parents:
            node = node.setdefault(p, {})
        node[last] = value
    return cfg
