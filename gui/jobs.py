"""Zadania (jobs) GUI i kolejka: config + folder wyników + podproces silnika + status + log.

Pojedyncze zadanie powstaje z formularza GUI (create):
  1. walidacja configu silnikiem (`engine --validate`) — błędy wracają do formularza, nic nie jest tworzone,
  2. zapis configu do configs/gui/<id>.json         („utworzenie pliku konfiguracyjnego”),
  3. utworzenie folderu results/gui/<id>/            („utworzenie folderu na wyniki”) + gui_job.json,
  4. kolejka -> worker uruchamia `engine --config ... --out ... --progress`, czyta linie PROGRESS,
     resztę wyjścia zapisuje do results/gui/<id>/engine.log.

Seria (create_series, etap 5): walidacja WSZYSTKICH configów serii, zapis wszystkich plików
configs/gui/series/<sid>/NN_<opis>.json + series.json i folderów results/gui/series/<sid>/NN_<opis>/
(gui/series.py: write_series) — dopiero potem wszystkie zadania trafiają do kolejki naraz.

Kolejka (etap 5, „GUI — kolejkowanie zadań”):
  - liczba równoległych workerów zmieniana w GUI (set_workers; 1 = zadania po kolei — zalecane przy
    pomiarach czasu, bo równoległe procesy dzielą pamięć podręczną L3, pasmo pamięci i limit mocy),
  - pauza / wznowienie (pause / resume — działające zadania kończą się normalnie, nowe nie startują),
  - anulowanie zadania i całej serii, zmiana kolejności oczekujących (move), ponowienie zadania
    z błędem / anulowanego / przerwanego (retry),
  - opcjonalne przypięcie procesu silnika do wybranego procesora logicznego (rdzeń P) i wysoki priorytet
    — tak jak pomiary z etapu 3 (bench/run_profile.py),
  - stan (zadania, kolejność kolejki, pauza, liczba workerów, przypięcie) w results/gui/jobs.json —
    przeżywa restart GUI; zadanie, które „działało” w chwili zamknięcia, dostaje status „przerwane”.

Statusy: queued (oczekuje), running (działa), done (gotowe), error (błąd), cancelled (anulowane),
interrupted (przerwane).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from .engine import CREATE_NO_WINDOW, EngineClient
from .names import safe_name, stamp
from .series import SeriesError, SeriesJob, SeriesSpec, deep_merge, new_series_id, write_series
from .settings import Settings

__all__ = ["Job", "JobError", "JobManager", "safe_name", "summarize_config", "merge_defaults"]

STATUS_LABELS = {
    "queued": "oczekuje",
    "running": "działa",
    "done": "gotowe",
    "error": "błąd",
    "cancelled": "anulowane",
    "interrupted": "przerwane",
}
ACTIVE = ("queued", "running")
RETRYABLE = ("error", "cancelled", "interrupted")
MAX_WORKERS = max(1, min(16, os.cpu_count() or 4))

PROGRESS_RE = re.compile(r"^PROGRESS (\w+) (\d+)/(\d+)(?: (\w+)=(\d+))?\s*$")
# Windows: HIGH_PRIORITY_CLASS przy przypięciu (jak bench/run_profile.py); na Linuksie nie zmieniamy priorytetu.
HIGH_PRIORITY = getattr(subprocess, "HIGH_PRIORITY_CLASS", 0) if sys.platform == "win32" else 0


class JobError(Exception):
    """Błąd tworzenia / obsługi zadania; errors — lista komunikatów dla formularza."""

    def __init__(self, message: str, errors: list[str] | None = None, warnings: list[str] | None = None,
                 status: int = 400):
        super().__init__(message)
        self.errors = errors or [message]
        self.warnings = warnings or []
        self.status = status


@dataclass
class Job:
    """Stan jednego zadania (zapisywany w jobs.json). Ścieżki względem katalogu projektu."""

    id: str
    name: str
    status: str = "queued"
    created: str = ""
    started: str | None = None
    finished: str | None = None
    durationS: float | None = None
    exitCode: int | None = None
    error: str | None = None
    configPath: str = ""
    outDir: str = ""
    resultId: str = ""                     # identyfikator wyniku w ResultStore (gui/<id>, gui/series/<sid>/<nn>)
    mcFrom: str | None = None              # folder wyniku CA dla --mc-from
    cells: int = 0
    summary: dict = field(default_factory=dict)   # tryb, wymiary, sąsiedztwo… (do listy)
    warnings: list = field(default_factory=list)
    progress: dict = field(default_factory=dict)  # ostatnia linia PROGRESS: stage, done, total, active
    command: list = field(default_factory=list)
    seriesId: str | None = None            # seria (etap 5): identyfikator, numer i etykiety punktów osi
    seriesName: str | None = None
    seriesIndex: int | None = None
    labels: dict = field(default_factory=dict)
    estimateMs: float | None = None        # szacunek czasu z GUI (heurystyka etapu 3) — do „czasu do końca”
    pinnedCpu: int | None = None           # procesor logiczny, do którego przypięto proces silnika

    def to_json(self) -> dict:
        d = asdict(self)
        d["statusLabel"] = STATUS_LABELS.get(self.status, self.status)
        return d


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def summarize_config(cfg: dict) -> dict:
    """Krótki opis configu do listy zadań (tryb, wymiary, sąsiedztwo, brzeg, MC)."""
    sp = cfg.get("space", {})
    mc = cfg.get("mc", {})
    ca = cfg.get("ca", {})
    full = bool(mc.get("enabled")) and mc.get("domain") == "full"
    mode = "mc_full" if full else (ca.get("mode", "lava") + (" + MC" if mc.get("enabled") else ""))
    return {
        "mode": mode,
        "space": [sp.get("nx"), sp.get("ny"), sp.get("nz")],
        "neighborhood": cfg.get("neighborhood"),
        "boundary": cfg.get("boundary"),
        "vents": cfg.get("vents", {}).get("count"),
        "mcs": mc.get("mcs") if mc.get("enabled") else None,
        "maxSteps": ca.get("maxSteps"),
    }


def merge_defaults(defaults: dict, cfg: dict) -> dict:
    """Config użytkownika nałożony na domyślny (jak w silniku) — do opisu i szacunków."""
    return deep_merge(defaults, cfg)


def _cells(cfg: dict) -> int:
    sp = cfg.get("space", {})
    return int(sp.get("nx", 1)) * int(sp.get("ny", 1)) * int(sp.get("nz", 1))


class JobManager:
    """Kolejka zadań z `workers` równoległymi wykonawcami (domyślnie 1), pauzą i kolejnością."""

    def __init__(self, settings: Settings, engine: EngineClient | None = None, workers: int | None = None,
                 start: bool = True):
        self.settings = settings
        self.engine = engine or EngineClient(settings)
        self.workers = max(1, settings.workers)
        self.paused = False
        self.pin = {"enabled": False, "cpus": list(settings.pin_cpus)}
        self._jobs: dict[str, Job] = {}
        self._queue: list[str] = []
        self._procs: dict[str, subprocess.Popen] = {}
        self._lock = threading.RLock()
        self._cv = threading.Condition(self._lock)
        self._stop = False
        self._threads: dict[int, threading.Thread] = {}
        self._started = False
        self._load()
        if workers is not None:
            self.workers = max(1, min(MAX_WORKERS, workers))
        if start:
            self.start()

    # ------------------------------------------------------------------ trwałość (jobs.json)

    def _load(self) -> None:
        path = self.settings.jobs_file
        if not path.is_file():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        known = set(Job.__dataclass_fields__)
        for d in data.get("jobs", []):
            job = Job(**{k: v for k, v in d.items() if k in known})
            if job.status == "running":
                # Proces silnika zginął razem z GUI (albo działa bez nadzoru) — wynik niepewny.
                job.status = "interrupted"
                job.error = "przerwane — GUI zostało zamknięte w trakcie obliczeń"
                job.finished = job.finished or _now()
            self._jobs[job.id] = job
        q = data.get("queue") or {}
        self.paused = bool(q.get("paused", False))
        if q.get("workers"):
            self.workers = max(1, min(MAX_WORKERS, int(q["workers"])))
        if isinstance(q.get("pin"), dict):
            self.pin = {"enabled": bool(q["pin"].get("enabled")), "cpus": list(q["pin"].get("cpus") or self.pin["cpus"])}
        # Oczekujące wracają do kolejki: najpierw w zapisanej kolejności, potem pozostałe wg utworzenia.
        order = [j for j in q.get("order", []) if j in self._jobs and self._jobs[j].status == "queued"]
        rest = [j.id for j in self._jobs.values() if j.status == "queued" and j.id not in order]
        self._queue = order + rest
        self._save()

    def _save(self) -> None:
        """Zapis atomowy (plik tymczasowy + zamiana) — przerwany zapis nie psuje listy zadań."""
        with self._lock:
            data = {"version": 2,
                    "queue": {"paused": self.paused, "workers": self.workers, "pin": self.pin, "order": list(self._queue)},
                    "jobs": [asdict(j) for j in self._jobs.values()]}
            path = self.settings.jobs_file
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
            os.replace(tmp, path)

    # ------------------------------------------------------------------ tworzenie zadań

    def _new_id(self, name: str) -> str:
        base = f"{stamp()}_{safe_name(name)}"
        job_id, n = base, 2
        while (job_id in self._jobs or (self.settings.gui_configs_dir / f"{job_id}.json").exists()
               or (self.settings.gui_results_dir / job_id).exists()):
            job_id, n = f"{base}-{n}", n + 1
        return job_id

    def _rel(self, p: Path) -> str:
        try:
            return p.resolve().relative_to(self.settings.root.resolve()).as_posix()
        except ValueError:
            return str(p)

    def _full(self, config: dict) -> dict:
        try:
            return merge_defaults(self.engine.defaults(), config)
        except Exception:  # noqa: BLE001 — opis zadania nie może zablokować uruchomienia
            return config

    def create(self, config: dict, name: str, mc_from: Path | None = None) -> Job:
        """Walidacja -> config w configs/gui/<id>.json -> folder results/gui/<id>/ -> kolejka.

        Rzuca JobError z listą błędów, gdy config nie przechodzi walidacji silnika."""
        if not isinstance(config, dict):
            raise JobError("Config musi być obiektem JSON")
        check = self.engine.validate(config, mc_from)
        if not check["ok"]:
            raise JobError("Config nie przeszedł walidacji", check["errors"], check["warnings"], status=422)

        with self._lock:
            job_id = self._new_id(name)
            cfg_path = self.settings.gui_configs_dir / f"{job_id}.json"
            out_dir = self.settings.gui_results_dir / job_id
            cfg_path.parent.mkdir(parents=True, exist_ok=True)
            out_dir.mkdir(parents=True, exist_ok=False)
            # Metadane GUI w kluczu "_gui" — silnik pomija klucze zaczynające się od "_".
            stored = {"_gui": {"id": job_id, "name": name, "created": _now()}, **config}
            cfg_path.write_text(json.dumps(stored, ensure_ascii=False, indent=2), encoding="utf-8")
            full = self._full(config)
            summary = summarize_config(full)
            cells = _cells(full)
            if mc_from is not None:
                # MC na gotowym wyniku CA: wymiary z nagłówka pliku, nie z configu.
                from .results import read_dims_header
                hdr = read_dims_header(mc_from)
                if hdr:
                    cells = hdr[0][0] * hdr[0][1] * hdr[0][2]
                    summary.update(space=list(hdr[0]), mode="mc_from", vents=None, mcs=full.get("mc", {}).get("mcs"))
            job = Job(
                id=job_id, name=name, created=_now(), configPath=self._rel(cfg_path), outDir=self._rel(out_dir),
                resultId=f"gui/{job_id}", mcFrom=str(mc_from) if mc_from else None, cells=cells,
                summary=summary, warnings=check["warnings"],
            )
            job.command = self.engine.run_command(cfg_path, out_dir, mc_from)
            self._write_job_file(out_dir, job)
            self._jobs[job_id] = job
            self.submit(job_id)
        return job

    def _write_job_file(self, out_dir: Path, job: Job) -> None:
        (out_dir / "gui_job.json").write_text(
            json.dumps({"id": job.id, "name": job.name, "created": job.created, "configPath": job.configPath,
                        "mcFrom": job.mcFrom, "seriesId": job.seriesId, "seriesIndex": job.seriesIndex,
                        "labels": job.labels}, ensure_ascii=False, indent=2), encoding="utf-8")

    def validate_series(self, jobs: list[SeriesJob]) -> None:
        """Walidacja wszystkich configów serii silnikiem (równolegle, po jednym procesie na config).
        Rzuca JobError (422) z błędami w postaci „NN_opis: komunikat” — wtedy nic nie jest zapisywane."""
        with ThreadPoolExecutor(max_workers=min(8, max(1, len(jobs)))) as pool:
            checks = list(pool.map(lambda j: self.engine.validate(j.config), jobs))
        errors, warnings = [], []
        for job, check in zip(jobs, checks):
            errors += [f"{job.name}: {e}" for e in check["errors"]]
            warnings += [f"{job.name}: {w}" for w in check["warnings"]]
        if errors:
            raise JobError(f"{len(errors)} config(ów) serii nie przeszło walidacji", errors, warnings, status=422)

    def create_series(self, spec: SeriesSpec, jobs: list[SeriesJob], estimates: dict | None = None) -> dict:
        """Seria: walidacja wszystkich configów -> zapis wszystkich plików i folderów -> kolejka.

        Zwraca opis serii (series.json) z identyfikatorami utworzonych zadań."""
        if not jobs:
            raise JobError("Seria nie ma zadań")
        self.validate_series(jobs)
        estimates = estimates or {}
        with self._lock:
            sid = new_series_id(spec.name, lambda s: (self.settings.series_configs_dir / s).exists()
                                or (self.settings.series_results_dir / s).exists())
            try:
                meta = write_series(spec, jobs, self.settings.series_configs_dir, self.settings.series_results_dir, sid,
                                    root=self.settings.root, source="gui")
            except SeriesError as e:
                raise JobError(str(e), e.errors) from e
            # Wszystkie pliki i foldery już są — teraz zadania, a na końcu jedno dodanie do kolejki.
            created = _now()
            new_ids = []
            for sj, jm in zip(jobs, meta["jobs"]):
                cfg_path = self.settings.root / jm["config"]
                out_dir = self.settings.root / jm["outDir"]
                full = self._full(sj.config)
                job = Job(
                    id=f"{sid}__{sj.name}", name=f"{spec.name} · {sj.name}", created=created,
                    configPath=jm["config"], outDir=jm["outDir"], resultId=f"gui/series/{sid}/{sj.name}",
                    cells=_cells(full), summary=summarize_config(full), seriesId=sid, seriesName=spec.name,
                    seriesIndex=sj.index, labels=sj.labels,
                    estimateMs=float(estimates[sj.name]) if isinstance(estimates.get(sj.name), (int, float)) else None,
                )
                job.command = self.engine.run_command(cfg_path, out_dir)
                self._write_job_file(out_dir, job)
                self._jobs[job.id] = job
                new_ids.append(job.id)
            self._queue.extend(new_ids)
            self._save()
            self._cv.notify_all()
        meta["jobIds"] = new_ids
        return meta

    def submit(self, job_id: str) -> None:
        """Dodaje zadanie na koniec kolejki."""
        with self._cv:
            self._jobs[job_id].status = "queued"
            if job_id not in self._queue:
                self._queue.append(job_id)
            self._save()
            self._cv.notify()

    # ------------------------------------------------------------------ odczyt

    def list(self) -> list[Job]:
        """Najnowsze pierwsze — w kolejności utworzenia (słownik zachowuje kolejność wstawiania, także po
        wczytaniu jobs.json); czas `created` ma dokładność sekundy, więc nie nadaje się do sortowania."""
        with self._lock:
            return list(reversed(self._jobs.values()))

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def queue_state(self) -> dict:
        """Stan kolejki do GUI: pauza, workery, przypięcie, kolejność oczekujących, działające."""
        with self._lock:
            running = [j.id for j in self._jobs.values() if j.status == "running"]
            return {"paused": self.paused, "workers": self.workers, "maxWorkers": MAX_WORKERS, "pin": dict(self.pin),
                    "cpuCount": os.cpu_count() or 1, "order": list(self._queue), "running": running,
                    "platform": sys.platform}

    def series_list(self) -> list[dict]:
        """Serie z GUI (grupy zadań o tym samym seriesId): liczby zadań w statusach, czasy, szacunki."""
        groups: dict[str, list[Job]] = {}
        with self._lock:
            for j in self._jobs.values():
                if j.seriesId:
                    groups.setdefault(j.seriesId, []).append(j)
        out = []
        for sid, jobs in groups.items():
            jobs.sort(key=lambda j: j.seriesIndex or 0)
            counts = {s: sum(1 for j in jobs if j.status == s) for s in STATUS_LABELS}
            out.append({
                "id": sid, "name": jobs[0].seriesName, "created": jobs[0].created, "total": len(jobs),
                "counts": counts, "ref": f"gui/series/{sid}",
                "configsDir": self._rel(self.settings.series_configs_dir / sid),
                "resultsDir": self._rel(self.settings.series_results_dir / sid),
                "durationS": round(sum(j.durationS or 0 for j in jobs), 3),
                "jobIds": [j.id for j in jobs],
            })
        out.sort(key=lambda s: s["created"], reverse=True)
        return out

    def log_path(self, job: Job) -> Path:
        return self.settings.root / job.outDir / "engine.log"

    def read_log(self, job_id: str, tail: int = 400) -> str:
        job = self.get(job_id)
        if job is None:
            raise JobError("Nie ma takiego zadania", status=404)
        path = self.log_path(job)
        if not path.is_file():
            return ""
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(lines[-tail:])

    # ------------------------------------------------------------------ sterowanie kolejką

    def _require(self, job_id: str) -> Job:
        job = self._jobs.get(job_id)
        if job is None:
            raise JobError("Nie ma takiego zadania", status=404)
        return job

    def cancel(self, job_id: str) -> Job:
        with self._cv:
            job = self._require(job_id)
            if job.status == "queued":
                if job_id in self._queue:
                    self._queue.remove(job_id)
                job.status, job.finished = "cancelled", _now()
                job.error = "anulowane przed startem"
                self._save()
            elif job.status == "running":
                job.status = "cancelled"  # worker zobaczy to po zakończeniu procesu
                proc = self._procs.get(job_id)
                if proc is not None and proc.poll() is None:
                    proc.terminate()
            return job

    def cancel_series(self, series_id: str) -> int:
        """Anuluje wszystkie oczekujące i działające zadania serii; zwraca ich liczbę."""
        with self._cv:
            ids = [j.id for j in self._jobs.values() if j.seriesId == series_id]
            if not ids:
                raise JobError("Nie ma takiej serii", status=404)
            active = [i for i in ids if self._jobs[i].status in ACTIVE]
            # Najpierw usuwamy oczekujące z kolejki — żaden worker nie weźmie ich w trakcie anulowania.
            for i in active:
                if self._jobs[i].status == "queued":
                    self.cancel(i)
            for i in active:
                if self._jobs[i].status == "running":
                    self.cancel(i)
            self._save()
            return len(active)

    def move(self, job_id: str, direction: str) -> list[str]:
        """Zmiana kolejności oczekującego zadania: up, down, top, bottom. Zwraca nową kolejność."""
        with self._cv:
            self._require(job_id)
            if job_id not in self._queue:
                raise JobError("Przesuwać można tylko zadania oczekujące w kolejce", status=409)
            i = self._queue.index(job_id)
            target = {"up": i - 1, "down": i + 1, "top": 0, "bottom": len(self._queue) - 1}.get(direction)
            if target is None:
                raise JobError("Kierunek: up, down, top albo bottom")
            target = max(0, min(len(self._queue) - 1, target))
            self._queue.insert(target, self._queue.pop(i))
            self._save()
            return list(self._queue)

    def retry(self, job_id: str) -> Job:
        """Ponowienie zadania z błędem / anulowanego / przerwanego: ten sam config i folder, koniec kolejki."""
        with self._cv:
            job = self._require(job_id)
            if job.status not in RETRYABLE:
                raise JobError(f"Ponowić można zadanie ze statusem: błąd, anulowane, przerwane (jest: "
                               f"{STATUS_LABELS.get(job.status, job.status)})", status=409)
            if not (self.settings.root / job.configPath).is_file():
                raise JobError(f"Brak pliku konfiguracyjnego {job.configPath}", status=409)
            job.started = job.finished = job.durationS = job.exitCode = job.error = None
            job.progress = {}
            self.submit(job_id)
            return job

    def pause(self) -> None:
        with self._cv:
            self.paused = True
            self._save()

    def resume(self) -> None:
        with self._cv:
            self.paused = False
            self._save()
            self._cv.notify_all()

    def set_workers(self, n: int) -> int:
        """Liczba równoległych workerów (1..MAX_WORKERS). Nadmiarowe kończą się po bieżącym zadaniu."""
        with self._cv:
            self.workers = max(1, min(MAX_WORKERS, int(n)))
            self._save()
            self._cv.notify_all()
        if self._started and not self._stop:
            self.start()
        return self.workers

    def set_pin(self, enabled: bool, cpus: list[int] | None = None) -> dict:
        """Przypięcie procesów silnika do procesorów logicznych (worker i -> cpus[i mod n]) + wysoki priorytet."""
        with self._cv:
            count = os.cpu_count() or 1
            if cpus is not None:
                bad = [c for c in cpus if not isinstance(c, int) or not 0 <= c < count]
                if bad or not cpus:
                    raise JobError(f"Procesory logiczne muszą być liczbami z zakresu 0..{count - 1}")
                self.pin["cpus"] = list(cpus)
            self.pin["enabled"] = bool(enabled)
            self._save()
            return dict(self.pin)

    def wait(self, job_id: str, timeout: float = 60.0) -> Job:
        """Czeka, aż zadanie przestanie być aktywne (testy, skrypty)."""
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            job = self.get(job_id)
            if job is not None and job.status not in ACTIVE:
                return job
            time.sleep(0.05)
        raise TimeoutError(f"Zadanie {job_id} nie skończyło się w {timeout} s")

    # ------------------------------------------------------------------ wykonanie

    def start(self) -> None:
        """Uruchamia brakujące wątki workerów 0..workers−1."""
        with self._lock:
            self._started = True
            for i in range(self.workers):
                t = self._threads.get(i)
                if t is None or not t.is_alive():
                    t = threading.Thread(target=self._worker, args=(i,), name=f"volcano-worker-{i}", daemon=True)
                    self._threads[i] = t
                    t.start()

    def shutdown(self, cancel_running: bool = True) -> None:
        with self._cv:
            self._stop = True
            if cancel_running:
                for proc in self._procs.values():
                    if proc.poll() is None:
                        proc.terminate()
            self._cv.notify_all()
            threads = list(self._threads.values())
        for t in threads:
            t.join(timeout=5)

    def _worker(self, index: int) -> None:
        while True:
            with self._cv:
                while not self._stop and (index >= self.workers or self.paused or not self._queue):
                    if index >= self.workers:
                        if self._threads.get(index) is threading.current_thread():
                            del self._threads[index]   # nadmiarowy worker kończy pracę
                        return
                    self._cv.wait()
                if self._stop:
                    return
                job_id = self._queue.pop(0)
                job = self._jobs[job_id]
                if job.status != "queued":
                    continue
                job.status, job.started, job.progress = "running", _now(), {}
                job.pinnedCpu = None
                self._save()
            self._run(job, index)

    def _pin_process(self, proc: subprocess.Popen, index: int) -> tuple[int | None, str]:
        """Przypina proces silnika do procesora logicznego (psutil, a bez niego WinAPI / sched_setaffinity)."""
        count = os.cpu_count() or 1
        cpus = [c for c in self.pin.get("cpus") or [] if 0 <= c < count] or [0]
        cpu = cpus[index % len(cpus)]
        try:
            try:
                import psutil
                psutil.Process(proc.pid).cpu_affinity([cpu])
            except ImportError:
                if sys.platform == "win32":
                    import ctypes
                    k32 = ctypes.windll.kernel32
                    k32.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
                    if not k32.SetProcessAffinityMask(ctypes.c_void_p(int(proc._handle)), ctypes.c_size_t(1 << cpu)):
                        raise OSError("SetProcessAffinityMask nie powiodło się") from None
                else:
                    os.sched_setaffinity(proc.pid, {cpu})
        except Exception as e:  # noqa: BLE001 — proces mógł się już zakończyć; zadanie liczy się dalej
            return None, f"# przypięcie nie powiodło się: {e}\n"
        prio = ", priorytet wysoki" if HIGH_PRIORITY else ""
        return cpu, f"# przypięto do procesora logicznego {cpu}{prio}\n"

    def _run(self, job: Job, index: int = 0) -> None:
        out_dir = self.settings.root / job.outDir
        out_dir.mkdir(parents=True, exist_ok=True)
        log = self.log_path(job)
        pin = bool(self.pin.get("enabled"))
        t0 = time.monotonic()
        exit_code: int | None = None
        error: str | None = None
        with open(log, "w", encoding="utf-8") as logf:
            logf.write(f"# {_now()} zadanie {job.id}\n# polecenie: {' '.join(job.command)}\n")
            logf.flush()
            try:
                proc = subprocess.Popen(job.command, cwd=self.settings.root, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                                        bufsize=1, creationflags=CREATE_NO_WINDOW | (HIGH_PRIORITY if pin else 0))
            except OSError as e:
                error = f"Nie można uruchomić silnika: {e}"
                logf.write(error + "\n")
            else:
                if pin:
                    cpu, note = self._pin_process(proc, index)
                    job.pinnedCpu = cpu
                    logf.write(note)
                    logf.flush()
                with self._lock:
                    self._procs[job.id] = proc
                    cancelled_early = job.status == "cancelled"
                if cancelled_early:
                    proc.terminate()
                assert proc.stdout is not None
                for line in proc.stdout:
                    m = PROGRESS_RE.match(line)
                    if m:
                        stage, done, total, key, value = m.groups()
                        prog = {"stage": stage, "done": int(done), "total": int(total)}
                        if key:
                            prog[key] = int(value)
                        with self._lock:
                            job.progress = prog
                        continue
                    logf.write(line)
                    logf.flush()
                exit_code = proc.wait()
                proc.stdout.close()
                with self._lock:
                    self._procs.pop(job.id, None)
            duration = time.monotonic() - t0
            logf.write(f"# koniec: kod wyjścia {exit_code}, czas {duration:.2f} s\n")

        with self._lock:
            job.exitCode, job.durationS, job.finished = exit_code, round(duration, 3), _now()
            if job.status == "cancelled":
                job.error = "anulowane przez użytkownika"
            elif error is not None:
                job.status, job.error = "error", error
            elif exit_code == 0:
                job.status = "done"
            else:
                job.status = "error"
                job.error = self._last_error_line(log) or f"silnik zakończył się kodem {exit_code}"
            self._save()

    @staticmethod
    def _last_error_line(log: Path) -> str | None:
        """Ostatni komunikat błędu silnika z logu (do listy zadań)."""
        try:
            lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return None
        for line in reversed(lines):
            if line.startswith(("Błąd", "Blad")):
                return line.strip()
        return None
