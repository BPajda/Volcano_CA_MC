"""Odtwarzanie erupcji krok po kroku z wyniku końcowego (etap 6) — czyste funkcje numpy.

ca_result.bin v2 zapisuje dla każdej komórki arrivalStep (numer kroku t, w którym komórka stała się lawą)
i solidStep (numer kroku, w którym zastygła). Krok t silnika czyta stan t i zapisuje stan t + 1
(LavaCA::updateLava, znacznik = steps_ przed zwiększeniem), więc stan po k krokach (k = 0 … steps) to:
  skała                                  -> skała,
  na końcu AIR (nigdy nie była lawą)     -> powietrze,
  k < pojawienie                         -> powietrze,   pojawienie = 0 dla krateru, arrivalStep + 1 dla reszty,
  k >= solidStep + 1 (tylko bazalt)      -> bazalt,
  w pozostałych przypadkach              -> płynna lawa (także lawa płynna do końca — jej solidStep = 0).
Kratery mają arrivalStep = 0 tak jak komórki zalane w kroku 0, dlatego rozpoznajemy je po położeniu
(stats.json -> flows[].vent); bez listy kraterów komórki z arrivalStep = 0 pojawiają się już w stanie 0
(różnica najwyżej 1 kroku dla kilku komórek; w opisie odtwarzania ventsExact = false).
Klasyczny rozrost ziaren (ca.mode = classic) odtwarza się tak samo (zarodki = „kratery”).

Temperatura: po przybyciu płynna lawa traci dokładnie coolingAmbient na krok, a krater w trakcie erupcji ma
stałą eruptTemp (CaRules.hpp, reguła 2) — temperaturę w stanie k liczymy wstecz od temperatury końcowej:
  bazalt:          T_k = T_końc + c·(solidStep + 1 − k),   lawa płynna na końcu: T_k = T_końc + c·(steps − k),
  ograniczone z góry przez eruptTemp (krater w trakcie erupcji).
Zgodność z prawdziwym stanem automatu sprawdzają testy (engine/tests/test_replay.cpp, gui/tests/test_replay.py);
ten sam algorytm liczy przeglądarka (gui/static/js/replay.js) — z tablic pobranych raz, bez backendu na klatkę.
"""

from __future__ import annotations

import numpy as np

AIR, ROCK, LAVA, BASALT = 0, 1, 2, 3
NEVER = np.int32(2**31 - 1)     # „nigdy” dla pojawienia / zastygnięcia (int32 — bezpiecznie dla JS)


def appear_steps(cell_type: np.ndarray, arrival: np.ndarray, vent_mask: np.ndarray | None = None) -> np.ndarray:
    """Stan, w którym komórka staje się lawą (int32): 0 dla kraterów, arrivalStep + 1 dla pozostałej lawy
    i bazaltu, NEVER dla skały i powietrza. vent_mask — True w komórkach kraterów (te same wymiary); None —
    kratery nieznane: wszystkie komórki z arrivalStep = 0 traktowane jak kratery (stan 0)."""
    t = np.asarray(cell_type)
    arr = np.asarray(arrival).astype(np.int32)
    live = (t == LAVA) | (t == BASALT)
    out = np.where(live, arr + 1, NEVER).astype(np.int32)
    vents = np.asarray(vent_mask, dtype=bool) if vent_mask is not None else (arr == 0)
    return np.where(live & vents, 0, out).astype(np.int32)


def solid_from(cell_type: np.ndarray, solid: np.ndarray) -> np.ndarray:
    """Stan, od którego komórka jest bazaltem (int32): solidStep + 1 dla bazaltu, NEVER dla reszty."""
    t = np.asarray(cell_type)
    return np.where(t == BASALT, np.asarray(solid).astype(np.int32) + 1, NEVER).astype(np.int32)


def state_at(cell_type: np.ndarray, appear: np.ndarray, solid_start: np.ndarray, k: int) -> np.ndarray:
    """Typ komórek w stanie k (uint8) z typu końcowego i tablic appear_steps / solid_from."""
    t = np.asarray(cell_type)
    live = (t == LAVA) | (t == BASALT)
    out = np.where(live, AIR, t).astype(np.uint8)
    out = np.where(live & (appear <= k), LAVA, out)
    out = np.where(live & (solid_start <= k), BASALT, out)
    return out.astype(np.uint8)


def temp_at(cell_type: np.ndarray, temp: np.ndarray, solid_start: np.ndarray, steps: int, k: int,
            cooling_ambient: float, erupt_temp: float) -> np.ndarray:
    """Temperatura płynnej lawy w stanie k (float64; dla pozostałych komórek bez znaczenia)."""
    end = np.where(np.asarray(cell_type) == BASALT, solid_start, steps).astype(np.float64)
    return np.minimum(erupt_temp, np.asarray(temp, dtype=np.float64) + cooling_ambient * (end - k))


def counts_per_step(appear: np.ndarray, solid_start: np.ndarray, steps: int) -> tuple[np.ndarray, np.ndarray]:
    """Liczba komórek płynnych i zastygłych w każdym stanie k = 0 … steps (dla podanych komórek lawy)."""
    a = np.asarray(appear).ravel()
    s = np.asarray(solid_start).ravel()
    a = a[a != NEVER]
    s = s[s != NEVER]
    n = steps + 1
    started = np.cumsum(np.bincount(np.clip(a, 0, n), minlength=n + 1)[:n])
    solid = np.cumsum(np.bincount(np.clip(s, 0, n), minlength=n + 1)[:n])
    return (started - solid).astype(np.int64), solid.astype(np.int64)


def vent_mask(shape: tuple[int, int, int], vents: list[list[int]] | None) -> np.ndarray | None:
    """Maska kraterów (nz, ny, nx) z listy [x, y, z]; None, gdy lista nieznana."""
    if vents is None:
        return None
    m = np.zeros(shape, dtype=bool)
    nz, ny, nx = shape
    for v in vents:
        x, y, z = (int(c) for c in v[:3])
        if 0 <= x < nx and 0 <= y < ny and 0 <= z < nz:
            m[z, y, x] = True
    return m
