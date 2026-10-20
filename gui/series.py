"""Generator serii zadań (etap 5) — wspólny moduł zakładki „Seria” w GUI (gui/app.py, gui/jobs.py)
i skryptu tools/make_series.py. Tylko biblioteka standardowa (bez FastAPI).

Pojęcia:
  config bazowy  — config silnika, na który nakładane są parametry zmienne (pełny albo częściowy —
                   brakujące klucze silnik uzupełnia wartościami domyślnymi);
  oś serii       — lista kluczy configu (ścieżki z kropkami, np. "vents.count") i lista punktów;
                   punkt = wartość dla każdego klucza osi + etykieta (nazwy plików, legenda wykresu);
  parowanie      — kilka kluczy w jednej osi zmienia się razem (space.nx i space.ny przy siatkach
                   kwadratowych, mc.enabled i mc.domain przy wyborze algorytmu CA / MC);
  zadania serii  — iloczyn kartezjański punktów wszystkich osi (1–3 osie); pierwsza oś zmienia się
                   najwolniej, więc kolejność zadań jest jak w tabeli.

Zapis wartości osi (GUI i linia poleceń, parse_points):
  "100, 200, 500"         trzy punkty; przy kluczach sparowanych ta sama wartość trafia do wszystkich
  "100;100;1, 10;10;10"   krotki — kolejne wartości dla kolejnych kluczy osi
  "[CA] false;basalt"     etykieta punktu w nawiasie kwadratowym (domyślnie tworzona z wartości)
  true / false / null     wartości logiczne i null; liczby całkowite i rzeczywiste; reszta to tekst
  zakres (range_points)   od, do, krok     — 100, 1000, 300 -> 100, 400, 700, 1000
  potęgi (power_points)   od, do, mnożnik  — 1, 1000, 10    -> 1, 10, 100, 1000

Zapis serii (write_series) — „po wygenerowaniu kilku plików zlecenie obliczeń”: najpierw WSZYSTKIE configi
<configs>/<id>/NN_<opis>.json i series.json (opis serii), foldery wyników <results>/<id>/NN_<opis>/
(+ kopia series.json) — dopiero potem GUI dodaje zadania do kolejki (JobManager.create_series),
a make_series.py uruchamia `engine --batch <configs>/<id> --out <results>/<id>`.
"""

from __future__ import annotations

import copy
import itertools
import json
import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .names import safe_name, stamp

MAX_AXES = 3
MAX_POINTS = 200      # punktów na oś
MAX_JOBS = 1000       # twardy limit zadań w serii
WARN_JOBS = 50        # powyżej — ostrzeżenie w podglądzie


class SeriesError(Exception):
    """Błąd opisu serii; errors — lista komunikatów po polsku (do formularza)."""

    def __init__(self, message: str, errors: list[str] | None = None):
        super().__init__(message)
        self.errors = errors or [message]


@dataclass
class Point:
    """Punkt osi: wartości dla kolejnych kluczy osi + etykieta."""

    values: list
    label: str


@dataclass
class Axis:
    """Oś serii: klucze configu (sparowane, gdy jest ich kilka) i punkty."""

    name: str
    keys: list[str]
    points: list[Point]

    def to_json(self) -> dict:
        return {"name": self.name, "keys": list(self.keys),
                "points": [{"label": p.label, "values": list(p.values)} for p in self.points]}


@dataclass
class SeriesSpec:
    """Opis serii: nazwa, config bazowy, osie i domyślny widok wykresu w zakładce „Porównanie”."""

    name: str
    base: dict
    axes: list[Axis]
    description: str = ""
    template: str | None = None
    chart: dict = field(default_factory=dict)


@dataclass
class SeriesJob:
    """Jedno zadanie serii (config gotowy do zapisu)."""

    index: int               # 1..N
    name: str                # NN_<opis> — nazwa pliku configu i folderu wyników
    labels: dict             # nazwa osi -> etykieta punktu
    values: dict             # klucz configu -> wartość
    config: dict

    def to_json(self) -> dict:
        return {"index": self.index, "name": self.name, "labels": self.labels, "values": self.values,
                "config": self.config}


# ---------------------------------------------------------------------------- pomocnicze


def deep_merge(base: dict, patch: dict) -> dict:
    """Kopia base z nałożonym patch (sekcje scalane rekurencyjnie; jak scalanie configu w silniku)."""
    out = copy.deepcopy(base)
    for k, v in (patch or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def get_path(cfg: dict, key: str, default: Any = None) -> Any:
    node: Any = cfg
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


def set_path(cfg: dict, key: str, value: Any) -> None:
    """Ustawia wartość pod ścieżką z kropkami (brakujące sekcje są tworzone)."""
    parts = key.split(".")
    node = cfg
    for part in parts[:-1]:
        if not isinstance(node.get(part), dict):
            node[part] = {}
        node = node[part]
    node[parts[-1]] = value


def leaf_paths(cfg: dict, prefix: str = "") -> list[str]:
    """Wszystkie klucze-liście configu (np. z engine --print-defaults) w kolejności sekcji."""
    out = []
    for k, v in cfg.items():
        if k.startswith("_"):
            continue
        p = f"{prefix}.{k}" if prefix else k
        out.extend(leaf_paths(v, p) if isinstance(v, dict) else [p])
    return out


def parse_value(text: str) -> Any:
    """Tekst z pola „wartości” -> wartość JSON: true/false/null, liczba całkowita, rzeczywista albo tekst."""
    t = text.strip()
    if len(t) >= 2 and t[0] == t[-1] and t[0] in "\"'":
        return t[1:-1]
    low = t.lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "none"):
        return None
    try:
        return int(t)
    except ValueError:
        pass
    try:
        v = float(t)
        if math.isfinite(v):
            return v
    except ValueError:
        pass
    return t


def value_text(v: Any) -> str:
    """Wartość -> zapis w polu „wartości” (odwrotność parse_value)."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "null"
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def _num_text(v: Any) -> str:
    return f"{v:g}" if isinstance(v, float) else str(v)


def default_label(keys: list[str], values: list) -> str:
    """Etykieta punktu z wartości: nx100, moore, 100x100x1, enabled_tak_full…"""
    def one(key: str, v: Any) -> str:
        short = key.split(".")[-1]
        if isinstance(v, bool):
            return f"{short}_{'tak' if v else 'nie'}"
        if isinstance(v, (int, float)):
            return f"{short}{_num_text(v)}"
        if v is None:
            return f"{short}_null"
        return str(v)

    if len({json.dumps(v) for v in values}) == 1:
        return one(keys[0], values[0])
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
        return "x".join(_num_text(v) for v in values)
    return "_".join(one(k, v) for k, v in zip(keys, values))


# ---------------------------------------------------------------------------- punkty osi


def parse_points(keys: list[str], text: str) -> list[Point]:
    """Lista wartości z pola tekstowego (opis składni w docstringu modułu)."""
    points = []
    tokens = [t.strip() for t in text.replace("\n", ",").split(",")]
    for tok in tokens:
        if not tok:
            continue
        label = None
        if tok.startswith("["):
            end = tok.find("]")
            if end < 0:
                raise SeriesError(f"Brak zamykającego „]” w etykiecie: „{tok}”")
            label = tok[1:end].strip() or None
            tok = tok[end + 1:].strip()
            if not tok:
                raise SeriesError(f"Punkt „[{label}]” nie ma wartości")
        parts = [parse_value(p) for p in tok.split(";")]
        if len(parts) == 1 and len(keys) > 1:
            parts = parts * len(keys)   # sparowane klucze dostają tę samą wartość
        if len(parts) != len(keys):
            raise SeriesError(f"Punkt „{tok}” ma {len(parts)} wartości, a oś ma {len(keys)} "
                              f"{'klucz' if len(keys) == 1 else 'klucze'} ({', '.join(keys)}) — "
                              "podaj jedną wartość (dla wszystkich kluczy) albo krotkę a;b;c")
        points.append(Point(parts, label or default_label(keys, parts)))
    if not points:
        raise SeriesError(f"Oś ({', '.join(keys)}) nie ma żadnej wartości")
    return points


def _as_number(v: Any, what: str) -> float:
    if isinstance(v, bool) or v is None:
        raise SeriesError(f"{what} musi być liczbą, podano: {v!r}")
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise SeriesError(f"{what} musi być liczbą, podano: {v!r}") from None
    if not math.isfinite(x):
        raise SeriesError(f"{what} musi być liczbą skończoną")
    return x


def _maybe_int(values: list[float], ints: bool) -> list:
    return [int(round(v)) for v in values] if ints else [round(v, 12) for v in values]


def range_points(keys: list[str], start: Any, stop: Any, step: Any) -> list[Point]:
    """Zakres liniowy od–do z krokiem (koniec włącznie, jeśli trafia w krok)."""
    a, b, s = (_as_number(start, "„od”"), _as_number(stop, "„do”"), _as_number(step, "„krok”"))
    if s <= 0:
        raise SeriesError("„krok” zakresu musi być większy od 0")
    if b < a:
        raise SeriesError("„do” musi być nie mniejsze niż „od”")
    n = int(math.floor((b - a) / s + 1e-9)) + 1
    if n > MAX_POINTS:
        raise SeriesError(f"Zakres daje {n} wartości — maksimum to {MAX_POINTS} na oś")
    ints = all(float(x).is_integer() for x in (a, b, s))
    vals = _maybe_int([a + i * s for i in range(n)], ints)
    return [Point([v] * len(keys), default_label(keys, [v] * len(keys))) for v in vals]


def power_points(keys: list[str], start: Any, stop: Any, factor: Any) -> list[Point]:
    """Potęgi: od, od·m, od·m², … ≤ do (np. 1, 10, 100, 1000)."""
    a, b, f = (_as_number(start, "„od”"), _as_number(stop, "„do”"), _as_number(factor, "„mnożnik”"))
    if a <= 0:
        raise SeriesError("„od” w potęgach musi być większe od 0")
    if f <= 1:
        raise SeriesError("„mnożnik” musi być większy od 1")
    if b < a:
        raise SeriesError("„do” musi być nie mniejsze niż „od”")
    vals, v = [], a
    while v <= b * (1 + 1e-9):
        vals.append(v)
        if len(vals) > MAX_POINTS:
            raise SeriesError(f"Potęgi dają więcej niż {MAX_POINTS} wartości")
        v *= f
    ints = a.is_integer() and f.is_integer()
    vals = _maybe_int(vals, ints)
    return [Point([v] * len(keys), default_label(keys, [v] * len(keys))) for v in vals]


def points_text(axis: Axis) -> str:
    """Punkty osi jako tekst pola „wartości” (etykieta tylko wtedy, gdy różni się od domyślnej)."""
    out = []
    for p in axis.points:
        same = len({json.dumps(v) for v in p.values}) == 1
        vals = value_text(p.values[0]) if same else ";".join(value_text(v) for v in p.values)
        out.append(vals if p.label == default_label(axis.keys, p.values) else f"[{p.label}] {vals}")
    return ", ".join(out)


def _keys_of(d: dict) -> list[str]:
    keys = d.get("keys", [])
    if isinstance(keys, str):
        keys = [k.strip() for k in keys.split(",")]
    return [str(k).strip() for k in keys if str(k).strip()]


def axis_from_dict(d: dict, number: int = 1) -> Axis:
    """Oś z JSON (GUI / series.json / szablon). Tryby: points (lista punktów), list (tekst),
    range (od, do, krok), pow (od, do, mnożnik)."""
    keys = _keys_of(d)
    name = str(d.get("name") or "").strip() or f"oś {number}"
    if not keys:
        raise SeriesError(f"Oś „{name}”: wybierz co najmniej jeden parametr (klucz configu)")
    if len(set(keys)) != len(keys):
        raise SeriesError(f"Oś „{name}”: ten sam klucz wybrano dwa razy")
    mode = d.get("mode") or ("points" if "points" in d else "list")
    if mode == "points":
        pts = []
        for p in d.get("points", []):
            vals = list(p.get("values", []))
            if len(vals) == 1 and len(keys) > 1:
                vals = vals * len(keys)
            if len(vals) != len(keys):
                raise SeriesError(f"Oś „{name}”: punkt {p} ma {len(vals)} wartości, a oś {len(keys)} klucze")
            pts.append(Point(vals, str(p.get("label") or default_label(keys, vals))))
        if not pts:
            raise SeriesError(f"Oś „{name}” nie ma żadnej wartości")
    elif mode == "list":
        pts = parse_points(keys, str(d.get("text", "")))
    elif mode == "range":
        pts = range_points(keys, d.get("start"), d.get("stop"), d.get("step"))
    elif mode == "pow":
        pts = power_points(keys, d.get("start"), d.get("stop"), d.get("factor"))
    else:
        raise SeriesError(f"Oś „{name}”: nieznany tryb „{mode}” (list, range, pow, points)")
    if len(pts) > MAX_POINTS:
        raise SeriesError(f"Oś „{name}” ma {len(pts)} punktów — maksimum to {MAX_POINTS}")
    return Axis(name, keys, pts)


def spec_from_dict(d: dict) -> SeriesSpec:
    """Opis serii z JSON (body POST /api/series, plik --spec w make_series.py)."""
    if not isinstance(d, dict):
        raise SeriesError("Opis serii musi być obiektem JSON")
    base = d.get("base") or {}
    if not isinstance(base, dict):
        raise SeriesError("Config bazowy musi być obiektem JSON")
    axes_in = d.get("axes") or []
    errors, axes = [], []
    for i, a in enumerate(axes_in, 1):
        try:
            axes.append(axis_from_dict(a, i))
        except SeriesError as e:
            errors.extend(e.errors)
    if errors:
        raise SeriesError(errors[0], errors)
    return SeriesSpec(name=str(d.get("name") or "seria").strip() or "seria", base=base, axes=axes,
                      description=str(d.get("description") or ""), template=d.get("template"),
                      chart=d.get("chart") or {})


# ---------------------------------------------------------------------------- rozwinięcie serii


def expand(spec: SeriesSpec, allowed_keys: set[str] | None = None) -> list[SeriesJob]:
    """Zadania serii: iloczyn kartezjański punktów osi nałożony na config bazowy.

    allowed_keys — dozwolone klucze (np. z engine --print-defaults); nieznany klucz = czytelny błąd
    jeszcze przed walidacją silnikiem."""
    axes = spec.axes
    if not 1 <= len(axes) <= MAX_AXES:
        raise SeriesError(f"Seria musi mieć od 1 do {MAX_AXES} parametrów zmiennych (osi), jest {len(axes)}")
    seen: dict[str, str] = {}
    errors = []
    for a in axes:
        for k in a.keys:
            if k.startswith("_"):
                errors.append(f"Klucz „{k}” zaczyna się od „_” — silnik takie klucze pomija")
            elif allowed_keys is not None and k not in allowed_keys:
                errors.append(f"Nieznany parametr „{k}” (oś „{a.name}”) — dozwolone klucze: jak w engine --print-defaults")
            if k in seen and seen[k] != a.name:
                errors.append(f"Klucz „{k}” jest w dwóch osiach („{seen[k]}” i „{a.name}”) — połącz je w jedną oś")
            seen[k] = a.name
    names = [a.name for a in axes]
    if len(set(names)) != len(names):
        errors.append("Osie muszą mieć różne nazwy")
    total = math.prod(len(a.points) for a in axes)
    if total > MAX_JOBS:
        errors.append(f"Seria ma {total} zadań — maksimum to {MAX_JOBS}")
    if errors:
        raise SeriesError(errors[0], errors)

    width = max(2, len(str(total)))
    jobs = []
    for i, combo in enumerate(itertools.product(*[a.points for a in axes]), 1):
        cfg = copy.deepcopy(spec.base)
        cfg = {k: v for k, v in cfg.items() if not k.startswith("_")}
        labels, values = {}, {}
        for axis, point in zip(axes, combo):
            labels[axis.name] = point.label
            for k, v in zip(axis.keys, point.values):
                set_path(cfg, k, copy.deepcopy(v))
                values[k] = v
        name = f"{i:0{width}d}_{safe_name('_'.join(labels.values()), 60, fallback='zadanie')}"
        jobs.append(SeriesJob(i, name, labels, values, cfg))
    return jobs


def preview_warnings(jobs: list[SeriesJob]) -> list[str]:
    """Ostrzeżenia podglądu (liczba zadań)."""
    out = []
    if len(jobs) > WARN_JOBS:
        out.append(f"Seria ma {len(jobs)} zadań (> {WARN_JOBS}) — obliczenia mogą potrwać długo; "
                   "sprawdź szacowany czas.")
    return out


def new_series_id(name: str, taken=lambda sid: False) -> str:
    """Identyfikator serii: data-czas + bezpieczna nazwa (jak identyfikator zadania)."""
    base = f"{stamp()}_{safe_name(name, 40, fallback='seria')}"
    sid, n = base, 2
    while taken(sid):
        sid, n = f"{base}-{n}", n + 1
    return sid


def _rel(p: Path, root: Path | None) -> str:
    if root is not None:
        try:
            return p.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            pass
    return p.as_posix()


def write_series(spec: SeriesSpec, jobs: list[SeriesJob], configs_root: Path, results_root: Path, series_id: str,
                 root: Path | None = None, source: str = "gui", extra: dict | None = None) -> dict:
    """Zapis serii na dysk — WSZYSTKIE pliki i foldery przed uruchomieniem obliczeń.

    configs_root/<id>/NN_<opis>.json (z metadanymi w kluczu "_series" — silnik pomija klucze „_”),
    configs_root/<id>/series.json, results_root/<id>/NN_<opis>/ i results_root/<id>/series.json.
    Ścieżki w series.json są względne wobec root (katalog projektu), gdy się da. Zwraca opis serii."""
    cfg_dir = configs_root / series_id
    res_dir = results_root / series_id
    if cfg_dir.exists():
        raise SeriesError(f"Folder serii już istnieje: {cfg_dir}")
    cfg_dir.mkdir(parents=True)
    res_dir.mkdir(parents=True, exist_ok=True)
    created = datetime.now().isoformat(timespec="seconds")
    job_meta = []
    for job in jobs:
        cfg_path = cfg_dir / f"{job.name}.json"
        out_dir = res_dir / job.name
        stored = {"_series": {"id": series_id, "name": spec.name, "index": job.index, "job": job.name,
                              "labels": job.labels, "values": job.values}, **job.config}
        cfg_path.write_text(json.dumps(stored, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        out_dir.mkdir(exist_ok=True)
        job_meta.append({"index": job.index, "name": job.name, "labels": job.labels, "values": job.values,
                         "config": _rel(cfg_path, root), "outDir": _rel(out_dir, root)})
    meta = {
        "version": 1, "id": series_id, "name": spec.name, "description": spec.description,
        "template": spec.template, "created": created, "source": source,
        "axes": [a.to_json() for a in spec.axes], "chart": spec.chart,
        "configsDir": _rel(cfg_dir, root), "resultsDir": _rel(res_dir, root),
        **(extra or {}),
        "base": {k: v for k, v in spec.base.items() if not k.startswith("_")},
        "jobs": job_meta,
    }
    text = json.dumps(meta, ensure_ascii=False, indent=1) + "\n"
    (cfg_dir / "series.json").write_text(text, encoding="utf-8", newline="\n")
    (res_dir / "series.json").write_text(text, encoding="utf-8", newline="\n")
    return meta


# ---------------------------------------------------------------------------- szablony serii

# Punkty osi „algorytm”: klasyczny rozrost CA (mc wyłączone) albo MC na całej przestrzeni (bez CA).
_ALGORITHM = {"name": "algorytm", "keys": ["mc.enabled", "mc.domain"],
              "points": [{"label": "CA", "values": [False, "basalt"]}, {"label": "MC", "values": [True, "full"]}]}

# Wspólna baza porównań: rozrost klasyczny (CA) i MC full z tymi samymi parametrami co pomiary z etapu 3.
_CLASSIC_BASE = {
    "grid": "vector", "boundary": "periodic", "neighborhood": "von_neumann", "rngSeed": 42,
    "ca": {"mode": "classic"}, "vents": {"count": 100},
    "mc": {"enabled": False, "domain": "basalt", "Q": 50, "mcs": 100, "mobilityFromCooling": False},
    "output": {"format": "bin", "snapshotsEvery": 0},
}


def _size_point(nx: int, ny: int, nz: int) -> dict:
    d = "3D" if min(nx, ny, nz) > 1 else "2D"
    dims = f"{nx}x{ny}x{nz}" if d == "3D" else f"{nx}x{ny}"
    return {"label": f"{d}_{dims}", "values": [nx, ny, nz]}


TEMPLATES: list[dict] = [
    {
        "id": "ca_vs_mc", "name": "CA vs MC: rozmiar siatki",
        "description": "Porównanie czasu symulacji: klasyczny rozrost CA (100 zarodków, von Neumann, periodyczne) "
                       "i naiwny MC full (Q = 50, 100 MCS, von Neumann, periodyczne) na tych samych siatkach "
                       "2D {100², 200², 500², 1000²} i 3D {10³, 25³, 50³, 100³} — 16 zadań. Do pomiarów: 1 worker "
                       "i przypięcie do rdzenia P.",
        "basePreset": None, "basePatch": _CLASSIC_BASE, "measure": True,
        "axes": [
            {"name": "rozmiar", "keys": ["space.nx", "space.ny", "space.nz"],
             "points": [_size_point(n, n, 1) for n in (100, 200, 500, 1000)]
             + [_size_point(n, n, n) for n in (10, 25, 50, 100)]},
            _ALGORITHM,
        ],
        "chart": {"x": "cells", "y": "simMs", "series": "axis:algorytm", "panel": "dim", "logX": True, "logY": True},
    },
    {
        "id": "seeds", "name": "Wpływ liczby zarodków",
        "description": "Rozrost klasyczny CA (von Neumann, periodyczne) z 1, 10, 100 i 1000 zarodkami na siatkach "
                       "500² i 50³ — 8 zadań. Więcej zarodków = mniej kroków = krótszy czas.",
        "basePreset": None, "basePatch": _CLASSIC_BASE, "measure": True,
        "axes": [
            {"name": "rozmiar", "keys": ["space.nx", "space.ny", "space.nz"],
             "points": [_size_point(500, 500, 1), _size_point(50, 50, 50)]},
            {"name": "zarodki", "keys": ["vents.count"],
             "points": [{"label": "1_zarodek", "values": [1]}, {"label": "10_zarodkow", "values": [10]},
                        {"label": "100_zarodkow", "values": [100]}, {"label": "1000_zarodkow", "values": [1000]}]},
        ],
        "chart": {"x": "seeds", "y": "caSim", "series": "axis:rozmiar", "panel": "", "logX": True, "logY": True},
    },
    {
        "id": "neighborhood", "name": "Wpływ sąsiedztwa (2D)",
        "description": "Rozrost klasyczny CA (100 zarodków) i MC full (Q = 50, 100 MCS) na siatce 300×300, "
                       "brzeg periodyczny, dla sąsiedztw von Neumann, Moore, losowe pentagonalne i heksagonalne — "
                       "8 zadań (czas, liczba kroków, liczba ziaren po MC).",
        "basePreset": None, "basePatch": deep_merge(_CLASSIC_BASE, {"space": {"nx": 300, "ny": 300, "nz": 1}}),
        "measure": True,
        "axes": [
            {"name": "sąsiedztwo", "keys": ["neighborhood"],
             "points": [{"label": v, "values": [v]} for v in ("von_neumann", "moore", "pentagonal", "hexagonal")]},
            _ALGORITHM,
        ],
        "chart": {"x": "axis:sąsiedztwo", "y": "simMs", "series": "axis:algorytm", "panel": "", "logX": False,
                  "logY": False},
    },
    {
        "id": "lava_vents", "name": "Lawa: liczba kraterów",
        "description": "Preset test_3d (64×64×48, kratery na zboczu) z 1, 3, 5 i 8 kraterami — 4 zadania: "
                       "objętość lawy, zasięg, liczba kroków i czas CA.",
        "basePreset": "test_3d", "basePatch": {"output": {"format": "bin"}}, "measure": False,
        "axes": [
            {"name": "kratery", "keys": ["vents.count"],
             "points": [{"label": "1_krater", "values": [1]}, {"label": "3_kratery", "values": [3]},
                        {"label": "5_kraterow", "values": [5]}, {"label": "8_kraterow", "values": [8]}]},
        ],
        "chart": {"x": "seeds", "y": "caSim", "series": "", "panel": "", "logX": False, "logY": False},
    },
    {
        "id": "openmp_threads", "name": "OpenMP: liczba wątków",
        "description": "Etap 9: ten sam przypadek przy 1, 2, 4, 6 i 8 wątkach (rdzenie P, przypinanie pcores) — "
                       "lawa test_3d w pełnym przebiegu (ca.sweep = full, harmonogram guided) i MC szachownica "
                       "500² (100 MCS) — 10 zadań. Wynik każdego zadania jest ten sam dla każdej liczby wątków; czas "
                       "maleje. Do pomiarów: 1 worker (zadania nie mogą liczyć się równocześnie). Dokładny pomiar "
                       "przyspieszenia: bench/scaling.py (wysoki priorytet, powtórzenia).",
        "basePreset": "test_3d", "measure": True,
        "basePatch": {"ca": {"sweep": "full"}, "output": {"format": "bin"},
                      "mc": {"Q": 50, "mcs": 100, "kT": 0.0, "update": "checkerboard", "mobilityFromCooling": False,
                             "statsEvery": 50},
                      "parallel": {"schedule": "guided", "chunk": 0, "affinity": "pcores"}},
        "axes": [
            {"name": "algorytm", "keys": ["mc.enabled", "mc.domain", "space.nx", "space.ny", "space.nz",
                                          "boundary", "neighborhood"],
             "points": [{"label": "CA_lawa_full", "values": [False, "basalt", 64, 64, 48, "absorbing", "moore"]},
                        {"label": "MC_szachownica", "values": [True, "full", 500, 500, 1, "periodic", "von_neumann"]}]},
            {"name": "wątki", "keys": ["parallel.threads"],
             "points": [{"label": label, "values": [t]} for label, t in
                        (("1_watek", 1), ("2_watki", 2), ("4_watki", 4), ("6_watkow", 6), ("8_watkow", 8))]},
        ],
        "chart": {"x": "threads", "y": "simMs", "series": "axis:algorytm", "panel": "", "logX": False, "logY": True},
    },
]


def template(tid: str) -> dict:
    for t in TEMPLATES:
        if t["id"] == tid:
            return t
    raise SeriesError(f"Nieznany szablon serii „{tid}” (dostępne: {', '.join(t['id'] for t in TEMPLATES)})")


def template_base(t: dict, configs_dir: Path, defaults: dict | None = None) -> dict:
    """Config bazowy szablonu: (wartości domyślne silnika) ⊕ preset z configs/ ⊕ basePatch."""
    base = copy.deepcopy(defaults) if defaults else {}
    if t.get("basePreset"):
        preset = json.loads((configs_dir / f"{t['basePreset']}.json").read_text(encoding="utf-8"))
        base = deep_merge(base, {k: v for k, v in preset.items() if not k.startswith("_")})
    return deep_merge(base, t.get("basePatch") or {})


def template_spec(tid: str, configs_dir: Path, defaults: dict | None = None, name: str | None = None) -> SeriesSpec:
    """Gotowa seria z szablonu (make_series.py --template, testy)."""
    t = template(tid)
    return SeriesSpec(name=name or t["id"], base=template_base(t, configs_dir, defaults),
                      axes=[axis_from_dict(a, i) for i, a in enumerate(t["axes"], 1)],
                      description=t["description"], template=t["id"], chart=dict(t["chart"]))


def templates_for_gui(configs_dir: Path, defaults: dict | None) -> list[dict]:
    """Szablony dla zakładki „Seria”: osie w zapisie tekstowym (jak wpisuje użytkownik) + config bazowy."""
    out = []
    for t in TEMPLATES:
        if t.get("basePreset") and not (configs_dir / f"{t['basePreset']}.json").is_file():
            continue  # brak presetu bazowego w configs/ — szablon pomijamy zamiast psuć całą listę
        axes = [axis_from_dict(a, i) for i, a in enumerate(t["axes"], 1)]
        out.append({
            "id": t["id"], "name": t["name"], "description": t["description"], "measure": t.get("measure", False),
            "base": template_base(t, configs_dir, defaults), "chart": t["chart"],
            "axes": [{"name": a.name, "keys": a.keys, "mode": "list", "text": points_text(a)} for a in axes],
            "jobs": math.prod(len(a.points) for a in axes),
        })
    return out
