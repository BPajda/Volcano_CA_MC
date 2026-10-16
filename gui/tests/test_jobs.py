"""Zadania i API z prawdziwym silnikiem: domyślny config, walidacja, utworzenie configu i folderu wyników,
uruchomienie (status gotowe, wynik da się wczytać), kolejka FIFO, anulowanie, trwałość jobs.json,
bezpieczne nazwy zadań. Wymaga zbudowanego silnika (inaczej testy są pomijane)."""

from __future__ import annotations

import json
import subprocess
import time

import numpy as np
import pytest

from gui.jobs import JobError, JobManager, safe_name
from gui.results import ResultStore

from .conftest import preset


@pytest.mark.parametrize("name, expected", [
    ("Etna 5 kraterów", "Etna_5_kraterow"),
    ("..\\..\\evil", "evil"),
    ("../../../etc/passwd", "etc_passwd"),
    ("C:\\Windows\\System32", "C_Windows_System32"),
    ("łódź żółw", "lodz_zolw"),
    ("....", "zadanie"),
    ("", "zadanie"),
    ("a" * 100, "a" * 40),
])
def test_safe_name(name, expected):
    assert safe_name(name) == expected


def test_defaults_from_engine(client, engine_path):
    d = client.get("/api/defaults").json()
    out = subprocess.run([str(engine_path), "--print-defaults"], capture_output=True, text=True, encoding="utf-8")
    assert d == json.loads(out.stdout)
    assert set(d) >= {"space", "terrain", "vents", "ca", "mc", "output"}


def test_validate_errors_in_polish(client):
    ok = client.post("/api/validate", json={"config": preset("test_2d")}).json()
    assert ok == {"ok": True, "errors": [], "warnings": []}
    bad = client.post("/api/validate", json={"config": preset("test_2d", **{"space.nx": -5})}).json()
    assert not bad["ok"] and "space.nx" in bad["errors"][0] and "zakresu" in bad["errors"][0]
    unknown = client.post("/api/validate", json={"config": {"neighbourhood": "moore"}}).json()
    assert not unknown["ok"] and "Nieznany parametr" in unknown["errors"][0]
    warn = client.post("/api/validate", json={"config": preset("mc_full_2d", **{"mc.mobilityFromCooling": True})}).json()
    assert warn["ok"] and len(warn["warnings"]) == 1


def test_invalid_job_creates_nothing(client, settings):
    r = client.post("/api/jobs", json={"name": "zly", "config": preset("test_2d", neighborhood="octagonal")})
    assert r.status_code == 422
    assert any("neighborhood" in e for e in r.json()["errors"])
    assert not settings.gui_configs_dir.exists() or not any(settings.gui_configs_dir.iterdir())
    assert not any(p.is_dir() for p in settings.gui_results_dir.glob("*")) if settings.gui_results_dir.exists() else True


def test_job_end_to_end(client, settings):
    """Formularz -> config w configs/gui/<id>.json -> folder results/gui/<id>/ -> silnik -> wynik w GUI."""
    cfg = preset("lava_mc_2d", **{"mc.mcs": 20})
    job = client.post("/api/jobs", json={"name": "Test lawy + MC", "config": cfg}).json()
    jid = job["id"]
    assert jid.endswith("_Test_lawy_MC")
    cfg_path = settings.root / job["configPath"]
    out_dir = settings.root / job["outDir"]
    assert cfg_path.parent == settings.gui_configs_dir and cfg_path.is_file()
    assert out_dir.parent == settings.gui_results_dir and out_dir.is_dir()
    stored = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert stored["_gui"]["name"] == "Test lawy + MC" and stored["mc"]["mcs"] == 20

    end = time.monotonic() + 120
    while (st := client.get(f"/api/jobs/{jid}").json())["status"] in ("queued", "running"):
        assert time.monotonic() < end
        time.sleep(0.1)
    assert st["status"] == "done", st
    assert st["exitCode"] == 0 and st["durationS"] > 0
    assert st["progress"]["stage"] == "save"  # ostatnia linia PROGRESS
    for name in ("config_used.json", "ca_result.bin", "mc_result.bin", "mc_stats.csv", "times.json", "engine.log",
                 "gui_job.json"):
        assert (out_dir / name).is_file(), name
    log = client.get(f"/api/jobs/{jid}/log").text
    assert "Symulacja zakończona" in log and "PROGRESS" not in log

    # Wynik widoczny w liście i możliwy do wczytania.
    ids = [r["id"] for r in client.get("/api/results").json()]
    assert f"gui/{jid}" in ids
    meta = client.get("/api/result", params={"id": f"gui/{jid}"}).json()
    assert meta["dims"] == [240, 1, 80] and meta["planeAxis"] == "y" and "crystal" in meta["fields"]
    det = client.get("/api/result/details", params={"id": f"gui/{jid}"}).json()
    assert det["times"]["mcs"] == 20 and det["mcStats"]["mcs"][-1] == 20
    data = ResultStore(settings.results_dir).load(f"gui/{jid}")
    assert int(np.count_nonzero(np.asarray(data.mc.crystal))) == det["stats"]["mc"]["domainCells"]


def test_fifo_and_persistence(settings):
    """Kilka zadań naraz przy 1 workerze wykonuje się po kolei; stan przeżywa restart managera."""
    jm = JobManager(settings, workers=1)
    try:
        a = jm.create(preset("test_2d", **{"ca.maxSteps": 80}), "pierwsze")
        b = jm.create(preset("mc_full_2d", **{"mc.mcs": 5}), "drugie")
        ja, jb = jm.wait(a.id), jm.wait(b.id)
        assert ja.status == jb.status == "done"
        assert jb.started >= ja.finished  # drugie zaczęło się po pierwszym
        assert [j.id for j in jm.list()] == [b.id, a.id]  # najnowsze pierwsze
    finally:
        jm.shutdown()
    data = json.loads(settings.jobs_file.read_text(encoding="utf-8"))
    assert [j["id"] for j in data["jobs"]] == [a.id, b.id]

    # Restart: zadanie „działa” z poprzedniej sesji -> przerwane; oczekujące wraca do kolejki.
    data["jobs"][0]["status"] = "running"
    settings.jobs_file.write_text(json.dumps(data), encoding="utf-8")
    jm2 = JobManager(settings, start=False)
    assert jm2.get(a.id).status == "interrupted" and "przerwane" in jm2.get(a.id).error
    assert jm2.get(b.id).status == "done"


def test_cancel_queued_and_running(settings):
    jm = JobManager(settings, workers=1)
    try:
        # Długie zadanie: klasyczny rozrost 160³ z 1 zarodkiem (kilka sekund) — anulowane w trakcie.
        long = jm.create(preset("test_2d", **{"space.nx": 160, "space.ny": 160, "space.nz": 160, "ca.mode": "classic",
                                              "vents.count": 1, "output.format": "none"}), "dlugie")
        queued = jm.create(preset("test_2d"), "w_kolejce")
        end = time.monotonic() + 30
        while jm.get(long.id).progress.get("stage") != "ca":
            assert time.monotonic() < end
            time.sleep(0.05)
        assert jm.cancel(queued.id).status == "cancelled"
        jm.cancel(long.id)
        j = jm.wait(long.id, 30)
        assert j.status == "cancelled" and j.exitCode != 0
        time.sleep(0.3)
        assert jm.get(queued.id).status == "cancelled" and jm.get(queued.id).started is None
    finally:
        jm.shutdown()


def test_job_name_cannot_escape(client, settings):
    """Nazwa zadania z „..\\” nie wychodzi poza configs/gui ani results/gui."""
    job = client.post("/api/jobs", json={"name": "..\\..\\..\\evil", "config": preset("test_2d", **{"ca.maxSteps": 5})}).json()
    cfg_path = (settings.root / job["configPath"]).resolve()
    out_dir = (settings.root / job["outDir"]).resolve()
    assert cfg_path.parent == settings.gui_configs_dir.resolve()
    assert out_dir.parent == settings.gui_results_dir.resolve()
    assert ".." not in job["id"] and "\\" not in job["id"] and "/" not in job["id"]
    assert client.get("/api/jobs/..%5C..%5Cevil").status_code == 404


def test_request_guards(client):
    """POST tylko z Content-Type JSON (ochrona przed formularzem z innej strony), Host tylko localhost."""
    r = client.post("/api/validate", content=b'{"config": {}}', headers={"Content-Type": "text/plain"})
    assert r.status_code == 415
    assert client.get("/api/info", headers={"Host": "evil.example"}).status_code == 400
    assert client.get("/api/info").json()["host"] == "127.0.0.1"


def test_presets_and_static(client):
    presets = {p["name"]: p for p in client.get("/api/presets").json()}
    assert {"test_2d", "lava_mc_2d", "mc_full_2d"} <= set(presets)
    assert presets["test_2d"]["description"] and "_opis" not in presets["test_2d"]["config"]
    page = client.get("/")
    assert page.status_code == 200 and "Nowa symulacja" in page.text
    for path in ("/js/main.js", "/vendor/three/three.module.min.js", "/vendor/chartjs/chart.umd.js"):
        assert client.get(path).status_code == 200, path


def test_engine_missing(tmp_path):
    from gui.settings import Settings
    s = Settings(root=tmp_path, engine=None, configs_dir=tmp_path / "configs", results_dir=tmp_path / "results")
    jm = JobManager(s, start=False)
    with pytest.raises(Exception) as e:
        jm.create({"space": {"nx": 10}}, "x")
    assert "engine" in str(e.value).lower()
    assert not isinstance(e.value, JobError) or e.value.status != 200


def test_mc_from_job(client, settings):
    """MC na gotowym wyniku CA (pole „Źródło danych” = engine --mc-from): wynik CA z zadania GUI,
    potem samo MC; typy komórek w podglądzie pochodzą z folderu wejściowego."""
    jm = client.app.state.jobs
    ca = client.post("/api/jobs", json={"name": "ca", "config": preset("lava_mc_2d", **{"mc.enabled": False})}).json()
    cfg = preset("lava_mc_2d", **{"mc.mcs": 15})
    del cfg["space"]  # GUI nie wysyła wymiarów — pochodzą z pliku wyniku CA
    # Zanim CA się policzy, folder nie ma wyniku — MC na nim nie da się zlecić.
    early = client.post("/api/jobs", json={"name": "mc", "config": cfg, "mcFrom": f"gui/{ca['id']}"})
    assert early.status_code in (201, 404)
    if early.status_code == 201:  # CA zdążyło się skończyć (szybki komputer)
        jm.wait(early.json()["id"])
    assert jm.wait(ca["id"]).status == "done"
    mc = client.post("/api/jobs", json={"name": "mc", "config": cfg, "mcFrom": f"gui/{ca['id']}"}).json()
    assert "--mc-from" in mc["command"] and mc["warnings"] == []
    assert mc["summary"]["mode"] == "mc_from" and mc["summary"]["space"] == [240, 1, 80]
    job = jm.wait(mc["id"])
    assert job.status == "done", job.error
    meta = client.get("/api/result", params={"id": f"gui/{mc['id']}"}).json()
    assert meta["sources"]["caFolder"].endswith(ca["id"]) and "crystal" in meta["fields"] and "flowId" in meta["fields"]
    det = client.get("/api/result/details", params={"id": f"gui/{mc['id']}"}).json()
    assert det["times"]["mode"] == "mc_from" and det["mcStats"]["mcs"][-1] == 15
    # mcFrom spoza results/ jest odrzucane.
    bad = client.post("/api/jobs", json={"name": "x", "config": cfg, "mcFrom": r"..\..\configs"})
    assert bad.status_code == 400
