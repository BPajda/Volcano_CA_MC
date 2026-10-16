"""Wyniki serii w jednej tabeli — zakładka „Porównanie”, eksport CSV (np. docs/data/ca_vs_mc.csv).

Źródła:
  - seria z series.json (GUI: results/gui/series/<id>/, tools/make_series.py: results/series/<id>/) —
    parametry zmienne (osie) i kolejność zadań z opisu serii;
  - folder po `engine --batch` bez series.json (tylko batch_summary.csv + podfoldery wyników);
  - dowolny zbiór wyników (wybrane identyfikatory) — parametry zmienne wykrywane z config_used.json
    (klucze, których wartości się różnią).
Dla każdego wyniku czytane są tylko małe pliki: times.json, stats.json, config_used.json — bez danych
mikrostruktury. Moduł bez FastAPI (używa go też tools/make_series.py do tabeli po serii).
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

from .series import leaf_paths, get_path

MiB = 1024 * 1024

# Kolumny tabeli porównania: klucz, etykieta, jednostka, rodzaj (num — liczba, cat — kategoria, text).
COLUMNS: list[dict] = [
    {"key": "index", "label": "nr", "kind": "num"},
    {"key": "name", "label": "zadanie", "kind": "text"},
    {"key": "status", "label": "status", "kind": "cat"},
    {"key": "algorithm", "label": "algorytm", "kind": "cat"},
    {"key": "mode", "label": "tryb", "kind": "cat"},
    {"key": "dim", "label": "wymiar", "kind": "cat"},
    {"key": "nx", "label": "nx", "kind": "num"},
    {"key": "ny", "label": "ny", "kind": "num"},
    {"key": "nz", "label": "nz", "kind": "num"},
    {"key": "cells", "label": "liczba komórek", "kind": "num"},
    {"key": "neighborhood", "label": "sąsiedztwo", "kind": "cat"},
    {"key": "boundary", "label": "brzeg", "kind": "cat"},
    {"key": "seeds", "label": "zarodki / kratery", "kind": "num"},
    {"key": "steps", "label": "kroki CA", "kind": "num"},
    {"key": "mcs", "label": "kroki MC (MCS)", "kind": "num"},
    {"key": "domainCells", "label": "komórki domeny MC", "kind": "num"},
    {"key": "caSim", "label": "czas CA (caSim)", "unit": "ms", "kind": "num"},
    {"key": "mcSim", "label": "czas MC (mcSim)", "unit": "ms", "kind": "num"},
    {"key": "simMs", "label": "czas symulacji (CA: caSim, MC: mcSim)", "unit": "ms", "kind": "num"},
    {"key": "save", "label": "zapis CA", "unit": "ms", "kind": "num"},
    {"key": "mcSave", "label": "zapis MC", "unit": "ms", "kind": "num"},
    {"key": "total", "label": "czas całkowity", "unit": "ms", "kind": "num"},
    {"key": "nsPerCellStep", "label": "CA: czas na komórkę i krok", "unit": "ns", "kind": "num"},
    {"key": "nsPerTrial", "label": "MC: czas na próbę", "unit": "ns", "kind": "num"},
    {"key": "nsPerUnit", "label": "koszt jednostkowy (CA: ns/kom./krok, MC: ns/próbę)", "unit": "ns", "kind": "num"},
    {"key": "peakRssMiB", "label": "szczyt pamięci procesu", "unit": "MiB", "kind": "num"},
    {"key": "modelMiB", "label": "pamięć — model teoretyczny", "unit": "MiB", "kind": "num"},
    {"key": "bytesPerCell", "label": "pamięć na komórkę (model)", "unit": "B", "kind": "num"},
    {"key": "outputMiB", "label": "pliki wyników", "unit": "MiB", "kind": "num"},
    {"key": "totalLavaVolume", "label": "objętość lawy", "unit": "komórek", "kind": "num"},
    {"key": "maxReach", "label": "zasięg lawy", "unit": "komórek", "kind": "num"},
    {"key": "grains", "label": "ziarna CA", "kind": "num"},
    {"key": "mcGrainsEnd", "label": "ziarna po MC", "kind": "num"},
    {"key": "mcMeanGrainSizeEnd", "label": "średnie ziarno po MC", "unit": "komórek", "kind": "num"},
]
COLUMN_KEYS = [c["key"] for c in COLUMNS]


class CompareError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _num(d: dict | None, key: str) -> float | None:
    v = (d or {}).get(key)
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _round(v: float | None, digits: int = 3) -> float | None:
    return None if v is None else round(v, digits)


# ---------------------------------------------------------------------------- jeden wynik


def result_row(folder: Path) -> dict:
    """Wiersz tabeli dla folderu wyników (wartości None, gdy wyniku jeszcze nie ma)."""
    times = _read_json(folder / "times.json") or {}
    cfg = _read_json(folder / "config_used.json") or {}
    stats = _read_json(folder / "stats.json") or {}
    row: dict[str, Any] = {k: None for k in COLUMN_KEYS}
    row["status"] = "ok" if times else "brak wyniku"
    if not times:
        return row
    space = times.get("space") or [get_path(cfg, "space.nx"), get_path(cfg, "space.ny"), get_path(cfg, "space.nz")]
    nx, ny, nz = (space + [None, None, None])[:3]
    mode = times.get("mode")
    cells = _num(times, "cells")
    steps, mcs, domain = _num(times, "steps"), _num(times, "mcs"), _num(times, "domainCells")
    ca_sim, mc_sim = _num(times, "caSim"), _num(times, "mcSim")
    if mode in ("mc_full", "mc_from"):
        algorithm = "MC"
    elif mcs is not None:
        algorithm = "CA+MC"
    else:
        algorithm = "CA"
    row.update(
        mode=mode, algorithm=algorithm, nx=nx, ny=ny, nz=nz, cells=cells,
        dim=("3D" if all(isinstance(v, int) and v > 1 for v in (nx, ny, nz)) else "2D") if nx else None,
        neighborhood=times.get("neighborhood"), boundary=times.get("boundary"),
        seeds=get_path(cfg, "vents.count") if mode in ("lava", "classic") else None,
        steps=steps, mcs=mcs, domainCells=domain, caSim=ca_sim, mcSim=mc_sim,
        save=_num(times, "save"), mcSave=_num(times, "mcSave"), total=_num(times, "total"),
    )
    row["simMs"] = {"CA": ca_sim, "MC": mc_sim}.get(algorithm, (ca_sim or 0) + (mc_sim or 0))
    if ca_sim is not None and cells and steps:
        row["nsPerCellStep"] = _round(ca_sim * 1e6 / (cells * steps))
    if mc_sim is not None and domain and mcs:
        row["nsPerTrial"] = _round(mc_sim * 1e6 / (domain * mcs))
    row["nsPerUnit"] = {"CA": row["nsPerCellStep"], "MC": row["nsPerTrial"]}.get(algorithm)
    mem = times.get("memory") or {}
    model = mem.get("model") or {}
    if _num(mem, "peakRssBytes") is not None:
        row["peakRssMiB"] = _round(mem["peakRssBytes"] / MiB)
    if _num(model, "peakBytes") is not None:
        row["modelMiB"] = _round(model["peakBytes"] / MiB)
        row["bytesPerCell"] = _num(model, "peakBytesPerCell")
    files = times.get("files") or {}
    if isinstance(files, dict) and files:
        row["outputMiB"] = _round(sum((f or {}).get("bytes", 0) for f in files.values()) / MiB, 4)
    if isinstance(stats, dict):
        row["totalLavaVolume"] = _num(stats, "totalLavaVolume")
        row["maxReach"] = _num(stats, "maxReach")
        row["grains"] = _num(stats, "grains")
        mc = stats.get("mc") if isinstance(stats.get("mc"), dict) else {}
        row["mcGrainsEnd"] = _num(mc, "grainsEnd")
        row["mcMeanGrainSizeEnd"] = _num(mc, "meanGrainSizeEnd")
    return row


def _flat_config(folder: Path) -> dict:
    cfg = _read_json(folder / "config_used.json") or {}
    return {k: get_path(cfg, k) for k in leaf_paths(cfg)}


def varying_values(folders: list[Path]) -> list[dict]:
    """Dla zbioru wyników bez opisu serii: klucze configu, które się różnią -> {klucz: wartość} na wynik."""
    flats = [_flat_config(f) for f in folders]
    present = [f for f in flats if f]   # wyniki bez config_used.json (np. przerwane) nie biorą udziału w porównaniu
    keys: list[str] = []
    for f in present:
        keys += [k for k in f if k not in keys]
    varying = [k for k in keys if len({json.dumps(f.get(k)) for f in present}) > 1]
    return [{k: f.get(k) for k in varying} if f else {} for f in flats]


# ---------------------------------------------------------------------------- serie


def resolve_dir(results_dir: Path, ref: str, max_parts: int = 4) -> Path:
    """Identyfikator folderu względem results/ (np. "gui/series/<id>") -> folder; nie wychodzi poza results/."""
    if not ref or len(ref) > 300:
        raise CompareError("Brak identyfikatora serii")
    parts = ref.replace("\\", "/").split("/")
    if any(p in ("", ".", "..") or ":" in p for p in parts) or len(parts) > max_parts:
        raise CompareError(f"Nieprawidłowy identyfikator: {ref}")
    base = results_dir.resolve()
    folder = (base / Path(*parts)).resolve()
    try:
        folder.relative_to(base)
    except ValueError:
        raise CompareError(f"Nieprawidłowy identyfikator: {ref}") from None
    if not folder.is_dir():
        raise CompareError(f"Nie ma folderu {ref}", 404)
    return folder


def _is_series_dir(d: Path) -> bool:
    return (d / "series.json").is_file() or (d / "batch_summary.csv").is_file()


def find_series(results_dir: Path) -> list[dict]:
    """Serie w results/ (do 3 poziomów): foldery z series.json albo batch_summary.csv. Najnowsze pierwsze."""
    found: list[dict] = []

    def visit(d: Path, depth: int) -> None:
        if _is_series_dir(d):
            meta = _read_json(d / "series.json") or {}
            ref = d.relative_to(results_dir).as_posix()
            jobs = meta.get("jobs") or [{"name": p.name} for p in sorted(d.iterdir()) if p.is_dir()]
            done = sum(1 for j in jobs if (d / j["name"] / "times.json").is_file())
            found.append({"ref": ref, "name": meta.get("name") or d.name, "id": meta.get("id") or d.name,
                          "template": meta.get("template"), "source": meta.get("source") or "engine --batch",
                          "created": meta.get("created") or "", "jobs": len(jobs), "done": done,
                          "chart": meta.get("chart") or {}, "gui": ref.startswith("gui/")})
            return
        if depth >= 3:
            return
        for sub in sorted(d.iterdir()):
            if sub.is_dir() and sub.name not in ("snapshots", "vs_profiler"):
                visit(sub, depth + 1)

    if results_dir.is_dir():
        for sub in sorted(results_dir.iterdir()):
            if sub.is_dir():
                visit(sub, 1)
    found.sort(key=lambda s: s["created"] or s["ref"], reverse=True)
    return found


def series_table(results_dir: Path, ref: str) -> dict:
    """Tabela serii: opis (series.json), osie, kolumny i wiersze (jeden na zadanie, w kolejności serii)."""
    folder = resolve_dir(results_dir, ref)
    meta = _read_json(folder / "series.json")
    if meta is None and not (folder / "batch_summary.csv").is_file():
        raise CompareError(f"W folderze {ref} nie ma series.json ani batch_summary.csv", 404)
    meta = meta or {"name": folder.name, "id": folder.name, "axes": [], "chart": {}, "source": "engine --batch",
                    "jobs": [{"index": i, "name": p.name, "labels": {}, "values": None}
                             for i, p in enumerate(sorted(p for p in folder.iterdir() if p.is_dir()), 1)]}
    jobs = meta.get("jobs") or []
    folders = [folder / j["name"] for j in jobs]
    detected = varying_values(folders) if any(j.get("values") is None for j in jobs) else None
    rows = []
    for i, (job, f) in enumerate(zip(jobs, folders)):
        row = result_row(f)
        row.update(index=job.get("index", i + 1), name=job["name"], id=f"{ref}/{job['name']}",
                   labels=job.get("labels") or {}, values=job.get("values") if detected is None else detected[i])
        rows.append(row)
    return {"series": {k: v for k, v in meta.items() if k not in ("jobs", "base")}, "ref": ref,
            "axes": meta.get("axes") or [], "columns": COLUMNS, "rows": rows}


def results_table(results_dir: Path, ids: list[str]) -> dict:
    """Tabela dla dowolnego zbioru wyników (identyfikatory jak w /api/results)."""
    if not ids:
        raise CompareError("Wybierz co najmniej jeden wynik")
    folders = [resolve_dir(results_dir, rid) for rid in ids]
    values = varying_values(folders)
    rows = []
    for i, (rid, f, vals) in enumerate(zip(ids, folders, values), 1):
        row = result_row(f)
        row.update(index=i, name=rid, id=rid, labels={}, values=vals)
        rows.append(row)
    return {"series": {"name": "wybrane wyniki", "chart": {}}, "ref": None, "axes": [], "columns": COLUMNS,
            "rows": rows}


def table_csv(table: dict) -> str:
    """CSV tabeli: nr, zadanie, osie serii (etykiety), parametry zmienne (wartości), potem wszystkie miary."""
    rows = table["rows"]
    axes = [a["name"] for a in table.get("axes") or []]
    value_keys: list[str] = []
    for r in rows:
        value_keys += [k for k in (r.get("values") or {}) if k not in value_keys]
    metric_keys = [k for k in COLUMN_KEYS if k not in ("index", "name")]
    header = ["index", "name"] + axes + value_keys + metric_keys + ["id"]
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(header)
    for r in rows:
        vals = r.get("values") or {}
        w.writerow([r.get("index"), r.get("name")] + [(r.get("labels") or {}).get(a, "") for a in axes]
                   + [_csv_value(vals.get(k)) for k in value_keys] + [_csv_value(r.get(k)) for k in metric_keys]
                   + [r.get("id") or ""])
    return out.getvalue()


def _csv_value(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)
