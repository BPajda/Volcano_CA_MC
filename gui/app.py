"""Backend GUI (FastAPI): formularz -> config -> zadanie -> silnik -> wyniki -> wizualizacja.

Endpointy (wszystkie pod /api, opis w docs/etap-4-gui.md i docs/etap-5-kolejka-serie-dane.md; dokumentacja interaktywna: /api/docs):
  GET  /api/info                     ustawienia: program silnika, katalogi, liczba workerów, ostrzeżenia
  GET  /api/defaults                 pełny domyślny config (engine --print-defaults)
  GET  /api/presets                  presety: configs/*.json (+ configi zadań z configs/gui/)
  POST /api/validate                 {config, mcFrom?} -> {ok, errors, warnings} (engine --validate)
  POST /api/jobs                     {name, config, mcFrom?} -> zadanie (config + folder wyników + kolejka)
  GET  /api/jobs, /api/jobs/{id}     lista zadań / jedno zadanie (status, postęp, czas, miejsce w kolejce)
  GET  /api/jobs/{id}/log            log silnika (engine.log)
  POST /api/jobs/{id}/cancel         anulowanie (usunięcie z kolejki / zabicie procesu)
  POST /api/jobs/{id}/move           {direction: up|down|top|bottom} — kolejność oczekujących (etap 5)
  POST /api/jobs/{id}/retry          ponowienie zadania z błędem / anulowanego / przerwanego
  GET  /api/queue, POST /api/queue   stan kolejki; {paused?, workers?, pin?: {enabled, cpus}}
  GET  /api/series/templates         gotowe szablony serii (gui/series.py)
  POST /api/series/preview           {spec} -> lista zadań serii (bez zapisu)
  POST /api/series                   {spec, estimates?} -> wszystkie configi + foldery, potem kolejka
  GET  /api/series                   serie z GUI i ich postęp; POST /api/series/{id}/cancel — anulowanie serii
  GET  /api/compare/sources          serie do porównania (results/gui/series/*, foldery po engine --batch)
  GET  /api/compare?series=          tabela wyników serii; POST /api/compare {ids} — dowolne wyniki
  GET  /api/compare/csv?series=      to samo jako CSV; POST /api/compare/csv {ids}
  GET  /api/heightmaps               mapy wysokości w configs/heightmaps/; GET /api/heightmaps/data?file= — wartości
  POST /api/heightmaps               import mapy: CSV albo obraz PNG/JPG (base64) -> configs/heightmaps/<nazwa>.csv
  GET  /api/results                  lista wyników (results/*, results/gui/*, results/gui/series/*/*, serie --batch)
  GET  /api/result?id=               metadane wyniku: wymiary, pola, zakresy wartości
  GET  /api/result/details?id=       times.json, stats.json, mc_stats.csv, config_used.json
  GET  /api/result/slice?id&field&axis&index[&maxSide]  przekrój (maxSide — miniatura) — surowe bajty
  GET  /api/result/faces?id&field&top=layer|surface 6 ścian zewnętrznych — surowe bajty
  GET  /api/result/surface?id&field                 mapa powierzchni (height = wysokość) — surowe bajty
  GET  /api/result/voxels?id&field&limit            woksele lawy/bazaltu — surowe bajty
  GET  /api/result/cell?id&x&y&z                    wszystkie pola jednej komórki (podpowiedź)
  GET  /api/result/replay?id=                       odtwarzanie erupcji (etap 6): kroki, parametry stygnięcia, liczba
                                                    komórek płynnych/zastygłych w każdym kroku, kratery, migawki CA i MC
  GET  /api/result/replay/cells?id&limit            komórki lawy do odtwarzania 3D (pojawienie, zastygnięcie, temp.) — bajty
  (slice/faces/surface: pola appear, solidFrom — odtwarzanie; mcs=<k> — kryształy z migawki MC mc_snapshots/)
  GET  /api/result/zip?id=                          folder wyniku jako ZIP (etap 5)
  GET  /api/result/vtk?id=&format=zlib|binary|ascii plik VTK ImageData (.vti) dla ParaView (etap 5)

Dane tablicowe idą jako application/octet-stream (little-endian, wiersz po wierszu), a opis
(typ tablicy, wymiary, krok próbkowania) w nagłówku X-Meta (JSON). Kolorowanie robi przeglądarka.

Bezpieczeństwo: serwer słucha tylko na 127.0.0.1; nagłówek Host musi wskazywać localhost (ochrona przed
DNS rebinding), a żądania POST muszą mieć Content-Type: application/json (strona z innej domeny nie wyśle
takiego żądania bez zgody CORS — której nie dajemy). Identyfikatory wyników i serie nie mogą wyjść poza
results/, mapy wysokości — poza configs/heightmaps/.
"""

from __future__ import annotations

import base64
import binascii
import json
import mimetypes
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
from fastapi import FastAPI, Query, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from . import compare, export, heightmap, series
from .engine import EngineClient, EngineMissing
from .jobs import STATUS_LABELS, JobError, JobManager
from .names import safe_name
from .results import FIELD_DTYPES, REPLAY_CELLS_LIMIT, ResultError, ResultStore
from .settings import Settings, load_settings

STATIC_DIR = Path(__file__).resolve().parent / "static"
# Fonty GUI (static/vendor/fonts, etap 7): Python na Windows nie zna typu .woff2 — bez tego plik szedłby jako text/plain.
mimetypes.add_type("font/woff2", ".woff2")
FIELD_PATTERN = "^(type|flowId|temp|crystal|cooling|appear|solidFrom)$"   # appear, solidFrom — odtwarzanie (etap 6)


class ValidateBody(BaseModel):
    config: dict
    mcFrom: str | None = None  # identyfikator wyniku CA (MC na gotowym wyniku, --mc-from)


class JobBody(BaseModel):
    name: str = Field(default="zadanie", max_length=80)
    config: dict
    mcFrom: str | None = None


class MoveBody(BaseModel):
    direction: str = Field(pattern="^(up|down|top|bottom)$")


class QueueBody(BaseModel):
    paused: bool | None = None
    workers: int | None = Field(default=None, ge=1, le=64)
    pin: dict | None = None    # {"enabled": bool, "cpus": [int, ...]}


class SeriesBody(BaseModel):
    spec: dict
    estimates: dict | None = None   # nazwa zadania -> szacowany czas [ms] (heurystyka z GUI)


class CompareBody(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=500)


class HeightmapBody(BaseModel):
    name: str = Field(max_length=80)
    kind: str = Field(pattern="^(csv|image)$")
    data: str                        # tekst CSV albo obraz zakodowany base64
    nx: int | None = Field(default=None, ge=1, le=100000)
    ny: int | None = Field(default=None, ge=1, le=100000)
    nz: int | None = Field(default=None, ge=1, le=100000)
    maxHeight: float = 60.0
    base: float = 0.0
    smooth: float = Field(default=0.0, ge=0, le=50)
    invert: bool = False
    normalize: bool = False
    resize: bool = False             # CSV: przeskaluj do nx × ny


def _binary(arr: np.ndarray, meta: dict) -> Response:
    """Tablica jako surowe bajty little-endian + opis w nagłówku X-Meta."""
    arr = np.ascontiguousarray(arr, dtype=arr.dtype.newbyteorder("<"))
    meta = {"dtype": arr.dtype.name, **meta}
    return Response(content=arr.tobytes(), media_type="application/octet-stream",
                    headers={"X-Meta": json.dumps(meta), "Cache-Control": "no-store"})


def _attachment(name: str) -> dict:
    return {"Content-Disposition": f'attachment; filename="{name}"', "Cache-Control": "no-store"}


def _unlink(path: Path) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


def create_app(settings: Settings | None = None, start_workers: bool = True) -> FastAPI:
    """Aplikacja z własnymi ustawieniami (testy podają katalogi tymczasowe)."""
    settings = settings or load_settings()
    engine = EngineClient(settings)
    jobs = JobManager(settings, engine, start=start_workers)
    store = ResultStore(settings.results_dir)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield
        jobs.shutdown(cancel_running=True)

    app = FastAPI(title="Wulkan: CA + MC — GUI", docs_url="/api/docs", redoc_url=None, openapi_url="/api/openapi.json",
                  lifespan=lifespan)
    app.state.settings, app.state.jobs, app.state.store, app.state.engine = settings, jobs, store, engine
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])

    @app.middleware("http")
    async def require_json_post(request: Request, call_next):
        if request.method == "POST" and request.url.path.startswith("/api/"):
            ctype = request.headers.get("content-type", "")
            if not ctype.startswith("application/json"):
                return JSONResponse({"detail": "Wymagany nagłówek Content-Type: application/json"}, status_code=415)
        return await call_next(request)

    @app.middleware("http")
    async def revalidate_static(request: Request, call_next):
        # Pliki frontendu (HTML/JS/CSS) przeglądarka ma zawsze sprawdzać u serwera (ETag → 304, bez ponownego
        # pobierania, gdy plik się nie zmienił). Bez tego po zmianie GUI Chrome potrafił wziąć z pamięci podręcznej
        # stary moduł JS obok nowego („module './util.js' does not provide an export named …”) i strona była pusta.
        response = await call_next(request)
        if request.method == "GET" and not request.url.path.startswith("/api/") \
                and "cache-control" not in response.headers:
            response.headers["Cache-Control"] = "no-cache"
        return response

    @app.exception_handler(ResultError)
    async def _result_error(_req, e: ResultError):
        return JSONResponse({"detail": str(e)}, status_code=e.status)

    @app.exception_handler(JobError)
    async def _job_error(_req, e: JobError):
        return JSONResponse({"detail": str(e), "errors": e.errors, "warnings": e.warnings}, status_code=e.status)

    @app.exception_handler(series.SeriesError)
    async def _series_error(_req, e: series.SeriesError):
        return JSONResponse({"detail": str(e), "errors": e.errors}, status_code=422)

    @app.exception_handler(compare.CompareError)
    async def _compare_error(_req, e: compare.CompareError):
        return JSONResponse({"detail": str(e)}, status_code=e.status)

    @app.exception_handler(heightmap.HeightmapError)
    async def _heightmap_error(_req, e: heightmap.HeightmapError):
        return JSONResponse({"detail": str(e), "errors": [str(e)]}, status_code=e.status)

    @app.exception_handler(EngineMissing)
    async def _engine_missing(_req, e: EngineMissing):
        return JSONResponse({"detail": str(e), "errors": [str(e)]}, status_code=503)

    def rel(p: Path) -> str:
        try:
            return p.resolve().relative_to(settings.root.resolve()).as_posix()
        except ValueError:
            return str(p)

    # ------------------------------------------------------------------ ustawienia, formularz

    @app.get("/api/info")
    def info():
        return {
            "engine": str(settings.engine) if settings.engine else None,
            "engineSource": settings.engine_source,
            "root": str(settings.root),
            "configsDir": rel(settings.configs_dir),
            "resultsDir": rel(settings.results_dir),
            "guiConfigsDir": rel(settings.gui_configs_dir),
            "guiResultsDir": rel(settings.gui_results_dir),
            "seriesConfigsDir": rel(settings.series_configs_dir),
            "seriesResultsDir": rel(settings.series_results_dir),
            "heightmapsDir": rel(settings.heightmaps_dir),
            "workers": jobs.workers,
            "host": settings.host,
            "port": settings.port,
            "warnings": settings.warnings,
        }

    @app.get("/api/defaults")
    def defaults():
        return engine.defaults()

    @app.get("/api/presets")
    def presets():
        out = []
        for group, folder in (("configs", settings.configs_dir), ("gui", settings.gui_configs_dir)):
            if not folder.is_dir():
                continue
            files = sorted(folder.glob("*.json"))
            if group == "gui":
                files = files[-30:]  # ostatnie configi zadań z GUI
            for p in files:
                try:
                    cfg = json.loads(p.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                    continue
                if not isinstance(cfg, dict):
                    continue
                gui = cfg.get("_gui", {}) if isinstance(cfg.get("_gui"), dict) else {}
                out.append({
                    "name": p.stem, "group": group, "file": rel(p),
                    "label": gui.get("name") or p.stem,
                    "description": cfg.get("_opis", ""), "note": cfg.get("_uwaga", ""),
                    # Preset bez przestrzeni i z samym MC na bazalcie służy do --mc-from (np. mc_basalt.json).
                    "mcFromOnly": "space" not in cfg and cfg.get("mc", {}).get("domain") == "basalt",
                    "config": {k: v for k, v in cfg.items() if not k.startswith("_")},
                })
        return out

    def mc_from_path(mc_from: str | None) -> Path | None:
        return store.resolve(mc_from) if mc_from else None

    @app.post("/api/validate")
    def validate(body: ValidateBody):
        return engine.validate(body.config, mc_from_path(body.mcFrom))

    # ------------------------------------------------------------------ zadania i kolejka

    def job_json(job, order: dict[str, int]) -> dict:
        d = job.to_json()
        d["queuePosition"] = order.get(job.id)
        return d

    def order_map() -> dict[str, int]:
        return {jid: i + 1 for i, jid in enumerate(jobs.queue_state()["order"])}

    @app.post("/api/jobs", status_code=201)
    def create_job(body: JobBody):
        job = jobs.create(body.config, body.name.strip() or "zadanie", mc_from_path(body.mcFrom))
        return job_json(job, order_map())

    @app.get("/api/jobs")
    def list_jobs():
        order = order_map()
        return [job_json(j, order) for j in jobs.list()]

    def get_job(job_id: str):
        job = jobs.get(job_id)
        if job is None:
            raise JobError("Nie ma takiego zadania", status=404)
        return job

    @app.get("/api/jobs/{job_id}")
    def job_detail(job_id: str):
        return job_json(get_job(job_id), order_map())

    @app.get("/api/jobs/{job_id}/log", response_class=PlainTextResponse)
    def job_log(job_id: str, tail: int = Query(400, ge=1, le=100000)):
        return jobs.read_log(job_id, tail)

    @app.post("/api/jobs/{job_id}/cancel")
    def cancel_job(job_id: str):
        return job_json(jobs.cancel(job_id), order_map())

    @app.post("/api/jobs/{job_id}/move")
    def move_job(job_id: str, body: MoveBody):
        return {"order": jobs.move(job_id, body.direction)}

    @app.post("/api/jobs/{job_id}/retry")
    def retry_job(job_id: str):
        return job_json(jobs.retry(job_id), order_map())

    @app.get("/api/queue")
    def queue_state():
        return jobs.queue_state()

    @app.post("/api/queue")
    def queue_update(body: QueueBody):
        if body.workers is not None:
            jobs.set_workers(body.workers)
        if body.pin is not None:
            cpus = body.pin.get("cpus")
            jobs.set_pin(bool(body.pin.get("enabled")), list(cpus) if isinstance(cpus, list) else None)
        if body.paused is True:
            jobs.pause()
        elif body.paused is False:
            jobs.resume()
        return jobs.queue_state()

    # ------------------------------------------------------------------ serie (etap 5)

    def allowed_keys() -> set[str]:
        return set(series.leaf_paths(engine.defaults()))

    @app.get("/api/series/templates")
    def series_templates():
        return series.templates_for_gui(settings.configs_dir, engine.defaults())

    @app.post("/api/series/preview")
    def series_preview(body: SeriesBody):
        spec = series.spec_from_dict(body.spec)
        expanded = series.expand(spec, allowed_keys())
        defaults_cfg = engine.defaults()
        return {
            "count": len(expanded), "warnings": series.preview_warnings(expanded),
            "axes": [a.to_json() for a in spec.axes],
            "jobs": [{**j.to_json(), "config": series.deep_merge(defaults_cfg, j.config)} for j in expanded],
            "configsDir": rel(settings.series_configs_dir) + "/<id>/",
            "resultsDir": rel(settings.series_results_dir) + "/<id>/",
        }

    @app.post("/api/series", status_code=201)
    def series_create(body: SeriesBody):
        spec = series.spec_from_dict(body.spec)
        expanded = series.expand(spec, allowed_keys())
        meta = jobs.create_series(spec, expanded, body.estimates)
        return {k: v for k, v in meta.items() if k != "base"}

    @app.get("/api/series")
    def series_list():
        return jobs.series_list()

    @app.post("/api/series/{series_id}/cancel")
    def series_cancel(series_id: str):
        return {"cancelled": jobs.cancel_series(series_id)}

    # ------------------------------------------------------------------ porównanie wyników (etap 5)

    def with_job_status(table: dict) -> dict:
        """Wiersze serii z GUI dostają status zadania z kolejki (oczekuje, działa, błąd…)."""
        by_result = {j.resultId: j for j in jobs.list() if j.seriesId}
        for row in table["rows"]:
            job = by_result.get(row["id"])   # id wiersza = gui/series/<seria>/<zadanie> = Job.resultId
            if job is not None:
                row["jobId"] = job.id
                if job.status != "done":
                    row["status"] = STATUS_LABELS.get(job.status, job.status)
        return table

    @app.get("/api/compare/sources")
    def compare_sources():
        return compare.find_series(settings.results_dir)

    @app.get("/api/compare")
    def compare_series(series_ref: str = Query(..., alias="series")):
        return with_job_status(compare.series_table(settings.results_dir, series_ref))

    @app.post("/api/compare")
    def compare_results(body: CompareBody):
        return compare.results_table(settings.results_dir, body.ids)

    def csv_response(table: dict, name: str) -> Response:
        return Response(content=compare.table_csv(table), media_type="text/csv; charset=utf-8",
                        headers=_attachment(f"{safe_name(name, 60, fallback='porownanie')}.csv"))

    @app.get("/api/compare/csv")
    def compare_series_csv(series_ref: str = Query(..., alias="series")):
        table = compare.series_table(settings.results_dir, series_ref)
        return csv_response(table, table["series"].get("id") or series_ref.rsplit("/", 1)[-1])

    @app.post("/api/compare/csv")
    def compare_results_csv(body: CompareBody):
        return csv_response(compare.results_table(settings.results_dir, body.ids), "wybrane_wyniki")

    # ------------------------------------------------------------------ mapy wysokości (etap 5)

    def heightmap_path(file: str) -> Path:
        p = (settings.root / file).resolve()
        folder = settings.heightmaps_dir.resolve()
        if p.parent != folder or p.suffix.lower() != ".csv" or not p.is_file():
            raise heightmap.HeightmapError(f"Nie ma mapy wysokości {file} w {rel(settings.heightmaps_dir)}/", 404)
        return p

    @app.get("/api/heightmaps")
    def heightmaps_list():
        return heightmap.list_maps(settings.heightmaps_dir, settings.root)

    @app.get("/api/heightmaps/data")
    def heightmap_data(file: str):
        h, note = heightmap.load_map(heightmap_path(file))
        return _binary(h.astype(np.float32), {"height": int(h.shape[0]), "width": int(h.shape[1]),
                                              "min": float(h.min()), "max": float(h.max()), "file": file})

    @app.post("/api/heightmaps", status_code=201)
    def heightmap_import(body: HeightmapBody):
        if body.kind == "image":
            if not (body.nx and body.ny and body.nz):
                raise heightmap.HeightmapError("Podaj wymiary mapy nx, ny i wysokość przestrzeni nz")
            try:
                raw = base64.b64decode(body.data, validate=True)
            except (binascii.Error, ValueError):
                raise heightmap.HeightmapError("Uszkodzone dane obrazu (base64)") from None
            h, info_ = heightmap.image_to_heights(raw, body.nx, body.ny, body.nz, body.maxHeight, body.base,
                                                  body.smooth, body.invert, body.normalize, body.name)
            comment = (f"Źródło: obraz {body.name} ({info_['imageSize'][0]}×{info_['imageSize'][1]}, {info_['mode']}), "
                       f"jasność -> wysokość {body.base:g}–{body.maxHeight:g} komórek, wygładzanie {body.smooth:g}"
                       f"{', odwrócone' if body.invert else ''}{', rozciągnięty kontrast' if body.normalize else ''}")
        else:
            if len(body.data) > heightmap.MAX_UPLOAD_BYTES:
                raise heightmap.HeightmapError("Plik CSV jest za duży (maks. 40 MiB)")
            h, info_ = heightmap.csv_to_heights(body.data, body.name, body.nx if body.resize else None,
                                                body.ny if body.resize else None, body.nz)
            comment = f"Źródło: plik CSV {body.name}" + (" (przeskalowany)" if info_.get("resized") else "")
        path = heightmap.save_map(settings.heightmaps_dir, body.name, h, comment)
        warnings = []
        if body.nz and float(h.max()) > body.nz - 5:
            warnings.append(f"Najwyższy punkt mapy ({h.max():.1f}) jest blisko nz = {body.nz} — nad terenem zostaje "
                            "mało miejsca na lawę; zwiększ nz.")
        if info_.get("clipped"):
            warnings.append(f"Część wysokości przekraczała nz = {body.nz} i została przycięta.")
        return {"file": rel(path), "name": path.stem, "nx": int(h.shape[1]), "ny": int(h.shape[0]),
                "min": float(h.min()), "max": float(h.max()), "info": info_, "warnings": warnings}

    # ------------------------------------------------------------------ wyniki

    @app.get("/api/results")
    def list_results():
        return store.list()

    @app.get("/api/result")
    def result_meta(id: str):
        d = store.load(id)
        nx, ny, nz = d.dims
        flat = "y" if ny == 1 else ("z" if nz == 1 else ("x" if nx == 1 else None))
        summary = store.summarize(id, d.folder)
        return {
            "id": id, "name": summary["name"], "dims": list(d.dims), "is2D": flat is not None,
            "planeAxis": flat, "mode": summary["mode"], "fields": d.fields(),
            "dtypes": {f: FIELD_DTYPES[f] for f in d.fields()}, "ranges": d.ranges(),
            "sources": {"ca": d.ca.source if d.ca else None, "mc": d.mc.source if d.mc else None,
                        "caFolder": rel(d.ca_folder) if d.ca_folder else None},
            "folder": rel(d.folder),
            # Odtwarzanie erupcji (etap 6): wymaga ca_result.bin v2 (arrivalStep); migawki CA i MC, jeśli zapisane.
            "replay": d.ca is not None and d.ca.arrival is not None,
            "snapshots": d.snapshot_steps() if d.ca is not None else [], "mcSnapshots": d.mc_snapshot_steps(),
        }

    @app.get("/api/result/details")
    def result_details(id: str):
        return store.details(id)

    @app.get("/api/result/slice")
    def result_slice(id: str, field: str = Query(..., pattern=FIELD_PATTERN), axis: str = Query(..., pattern="^[xyz]$"),
                     index: int = Query(..., ge=0), maxSide: int | None = Query(None, ge=8, le=4096),
                     mcs: int | None = Query(None, ge=0)):
        d = store.load(id)
        arr, step = d.slice(field, axis, index, maxSide, mcs)
        h_axis, v_axis = {"x": ("y", "z"), "y": ("x", "z"), "z": ("x", "y")}[axis]
        return _binary(arr, {"field": field, "axis": axis, "index": index, "height": arr.shape[0],
                             "width": arr.shape[1], "step": step, "hAxis": h_axis, "vAxis": v_axis})

    @app.get("/api/result/faces")
    def result_faces(id: str, field: str = Query(..., pattern=FIELD_PATTERN),
                     top: str = Query("layer", pattern="^(layer|surface)$"), mcs: int | None = Query(None, ge=0)):
        d = store.load(id)
        parts, faces, offset = [], [], 0
        for name, arr in d.faces(field, top == "surface", mcs):
            arr = np.ascontiguousarray(arr, dtype=arr.dtype.newbyteorder("<"))
            faces.append({"name": name, "height": arr.shape[0], "width": arr.shape[1], "offset": offset})
            parts.append(arr.tobytes())
            offset += arr.nbytes
        dtype = FIELD_DTYPES[field]
        meta = {"dtype": dtype, "field": field, "top": top, "dims": list(d.dims), "faces": faces}
        return Response(content=b"".join(parts), media_type="application/octet-stream",
                        headers={"X-Meta": json.dumps(meta), "Cache-Control": "no-store"})

    @app.get("/api/result/surface")
    def result_surface(id: str, field: str = Query(..., pattern="^(height|terrain|type|flowId|temp|crystal|cooling)$"),
                       mcs: int | None = Query(None, ge=0)):
        d = store.load(id)
        arr = d.surface(field, mcs)
        return _binary(arr, {"field": field, "height": arr.shape[0], "width": arr.shape[1], "dims": list(d.dims)})

    @app.get("/api/result/voxels")
    def result_voxels(id: str, field: str = Query(..., pattern=FIELD_PATTERN),
                      limit: int = Query(150_000, ge=1, le=1_000_000)):
        d = store.load(id)
        xyz, vals, total, step = d.voxels(field, limit)
        vals = np.ascontiguousarray(vals, dtype=vals.dtype.newbyteorder("<"))
        meta = {"field": field, "dtype": vals.dtype.name, "count": int(xyz.shape[0]), "total": total, "step": step,
                "dims": list(d.dims)}
        return Response(content=xyz.astype("<u2").tobytes() + vals.tobytes(), media_type="application/octet-stream",
                        headers={"X-Meta": json.dumps(meta), "Cache-Control": "no-store"})

    @app.get("/api/result/cell")
    def result_cell(id: str, x: int, y: int, z: int):
        return store.load(id).cell(x, y, z)

    # ------------------------------------------------------------------ odtwarzanie erupcji (etap 6)

    @app.get("/api/result/replay")
    def result_replay(id: str):
        return store.load(id).replay_info()

    @app.get("/api/result/replay/cells")
    def result_replay_cells(id: str, limit: int = Query(REPLAY_CELLS_LIMIT, ge=1, le=REPLAY_CELLS_LIMIT)):
        """Komórki lawy wyniku końcowego: int32 appear[n], int32 solidFrom[n], float32 temp[n], int32 flowId[n],
        uint16 xyz[n·3] (w tej kolejności — tablice 4-bajtowe najpierw, wyrównane)."""
        d = store.load(id)
        c = d.replay_cells(limit)
        n = int(c["appear"].size)
        body = b"".join(np.ascontiguousarray(c[k], dtype=c[k].dtype.newbyteorder("<")).tobytes()
                        for k in ("appear", "solidFrom", "temp", "flowId", "xyz"))
        meta = {"count": n, "total": c["total"], "step": c["step"], "dims": list(d.dims),
                "layout": ["appear:int32", "solidFrom:int32", "temp:float32", "flowId:int32", "xyz:uint16x3"]}
        return Response(content=body, media_type="application/octet-stream",
                        headers={"X-Meta": json.dumps(meta), "Cache-Control": "no-store"})

    def download_name(rid: str) -> str:
        return safe_name(rid.replace("/", "_"), 100, fallback="wynik")

    @app.get("/api/result/zip")
    def result_zip(id: str):
        folder = store.resolve(id)
        name = download_name(id)
        tmp = export.zip_result(folder, name)
        return FileResponse(tmp, media_type="application/zip", filename=f"{name}.zip",
                            headers={"Cache-Control": "no-store"}, background=BackgroundTask(_unlink, tmp))

    @app.get("/api/result/vtk")
    def result_vtk(id: str, format: str = Query("zlib", pattern="^(zlib|binary|ascii)$")):
        d = store.load(id)
        if format == "ascii" and d.dims[0] * d.dims[1] * d.dims[2] > 2_000_000:
            raise ResultError("Format ascii tylko dla wyników do 2 mln komórek — wybierz zlib albo binary")
        name = download_name(id)
        fd, tmp = tempfile.mkstemp(prefix="volcano_", suffix=".vti")
        os.close(fd)
        try:
            export.write_vti(d, Path(tmp), format)
        except BaseException:
            _unlink(Path(tmp))
            raise
        return FileResponse(tmp, media_type="application/xml", filename=f"{name}.vti",
                            headers={"Cache-Control": "no-store"}, background=BackgroundTask(_unlink, Path(tmp)))

    # ------------------------------------------------------------------ frontend (bez kroku budowania)

    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    return app


def __getattr__(name: str):
    """`uvicorn gui.app:app` (plan projektu §8.1): aplikacja tworzona dopiero przy pierwszym odwołaniu —
    sam import modułu (np. w testach) nie uruchamia workerów ani nie czyta ustawień."""
    if name == "app":
        globals()["app"] = create_app()
        return globals()["app"]
    raise AttributeError(name)
