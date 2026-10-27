"""Generator serii (gui/series.py — wspólny dla GUI i tools/make_series.py): iloczyn kartezjański, parowanie
kluczy, zakresy, potęgi, nazwy plików; zapis serii (wszystkie configi i foldery PRZED startem zadań); kolejka:
kolejność, pauza, anulowanie serii, ponowienie, wiele workerów, trwałość stanu; API serii i kolejki."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from gui import series as S
from gui.jobs import HIGH_PRIORITY, JobError, JobManager, launch_mode

from .conftest import ROOT, preset

# ---------------------------------------------------------------- generator (bez silnika)


def spec(axes, base=None, name="test"):
    return S.SeriesSpec(name=name, base=base or {"space": {"nx": 10, "ny": 10, "nz": 1}}, axes=axes)


def test_parse_points_lists_tuples_labels():
    pts = S.parse_points(["vents.count"], "1, 10,100")
    assert [p.values for p in pts] == [[1], [10], [100]] and [p.label for p in pts] == ["count1", "count10", "count100"]
    # Klucze sparowane: jedna wartość trafia do wszystkich, krotka — po kolei; etykieta w nawiasie.
    pts = S.parse_points(["space.nx", "space.ny", "space.nz"], "100, [płyta] 200;300;1\n10")
    assert [p.values for p in pts] == [[100, 100, 100], [200, 300, 1], [10, 10, 10]]
    assert [p.label for p in pts] == ["nx100", "płyta", "nx10"]
    pts = S.parse_points(["mc.enabled", "mc.domain"], "[CA] false;basalt, [MC] true;full")
    assert pts[1].values == [True, "full"] and pts[0].label == "CA"
    assert S.parse_points(["neighborhood"], "moore, von_neumann")[1].values == ["von_neumann"]
    assert S.parse_points(["mc.kT"], "0.5, 1e-3, null")[1].values == [0.001]
    with pytest.raises(S.SeriesError, match="ma 2 wartości, a oś ma 3"):
        S.parse_points(["space.nx", "space.ny", "space.nz"], "1;2")
    with pytest.raises(S.SeriesError, match="nie ma żadnej wartości"):
        S.parse_points(["a"], " , ")


def test_ranges_and_powers():
    assert [p.values[0] for p in S.range_points(["a"], 100, 1000, 300)] == [100, 400, 700, 1000]
    assert [p.values[0] for p in S.range_points(["a"], 100, 950, 300)] == [100, 400, 700]
    vals = [p.values[0] for p in S.range_points(["a"], 0.1, 0.5, 0.1)]
    assert vals == pytest.approx([0.1, 0.2, 0.3, 0.4, 0.5]) and len(vals) == 5
    assert [p.values[0] for p in S.power_points(["a"], 1, 1000, 10)] == [1, 10, 100, 1000]
    assert [p.values[0] for p in S.power_points(["a"], 10, 100, 2)] == [10, 20, 40, 80]
    two = S.range_points(["space.nx", "space.ny"], 10, 30, 10)
    assert [p.values for p in two] == [[10, 10], [20, 20], [30, 30]]
    for bad in (lambda: S.range_points(["a"], 1, 10, 0), lambda: S.range_points(["a"], 10, 1, 1),
                lambda: S.power_points(["a"], 0, 10, 2), lambda: S.power_points(["a"], 1, 10, 1),
                lambda: S.range_points(["a"], 1, 10_000, 1), lambda: S.range_points(["a"], "x", 2, 1)):
        with pytest.raises(S.SeriesError):
            bad()


def test_cartesian_product_pairing_and_names():
    sp = spec([S.axis_from_dict({"name": "rozmiar", "keys": "space.nx, space.ny", "mode": "list", "text": "10, 20"}),
               S.axis_from_dict({"name": "zarodki", "keys": ["vents.count"], "mode": "pow", "start": 1, "stop": 100, "factor": 10}),
               S.axis_from_dict({"name": "sąsiedztwo", "keys": ["neighborhood"], "mode": "list", "text": "moore, von_neumann"})])
    jobs = S.expand(sp)
    assert len(jobs) == 2 * 3 * 2
    # Pierwsza oś zmienia się najwolniej; nazwy NN_<etykiety> z bezpiecznych znaków.
    assert [j.name for j in jobs[:3]] == ["01_nx10_count1_moore", "02_nx10_count1_von_neumann", "03_nx10_count10_moore"]
    assert jobs[-1].name == "12_nx20_count100_von_neumann"
    j = jobs[8]  # nx 20, count 10, moore
    assert j.config["space"] == {"nx": 20, "ny": 20, "nz": 1}
    assert j.config["vents"]["count"] == 10 and j.config["neighborhood"] == "moore"
    assert j.labels == {"rozmiar": "nx20", "zarodki": "count10", "sąsiedztwo": "moore"}
    assert j.values == {"space.nx": 20, "space.ny": 20, "vents.count": 10, "neighborhood": "moore"}
    # Config bazowy nie jest modyfikowany, klucze "_" nie trafiają do zadań.
    sp.base["_opis"] = "x"
    assert "_opis" not in S.expand(sp)[0].config and sp.base["space"]["nx"] == 10
    assert len({j.name for j in jobs}) == len(jobs)


def test_expand_errors():
    a = S.axis_from_dict({"keys": ["vents.count"], "text": "1, 2"})
    with pytest.raises(S.SeriesError, match="od 1 do 3"):
        S.expand(spec([]))
    with pytest.raises(S.SeriesError, match="od 1 do 3"):
        S.expand(spec([a, a, a, a]))
    dup = S.axis_from_dict({"name": "b", "keys": ["vents.count", "rngSeed"], "text": "1"})
    with pytest.raises(S.SeriesError, match="w dwóch osiach"):
        S.expand(spec([a, dup]))
    with pytest.raises(S.SeriesError, match="Nieznany parametr „vent.count”"):
        S.expand(spec([S.axis_from_dict({"keys": ["vent.count"], "text": "1"})]), allowed_keys={"vents.count"})
    with pytest.raises(S.SeriesError, match="maksimum"):
        S.expand(spec([S.axis_from_dict({"name": f"o{i}", "keys": [f"k{i}"], "mode": "range", "start": 1, "stop": 11,
                                         "step": 1}) for i in range(3)]))
    with pytest.raises(S.SeriesError, match="co najmniej jeden parametr"):
        S.axis_from_dict({"name": "x", "keys": [], "text": "1"})


def test_templates_round_trip():
    """Szablony: osie w zapisie tekstowym (jak w GUI) dają te same zadania co osie z punktów."""
    for t in S.TEMPLATES:
        direct = S.expand(S.template_spec(t["id"], ROOT / "configs"))
        gui = next(g for g in S.templates_for_gui(ROOT / "configs", None) if g["id"] == t["id"])
        parsed = S.expand(S.spec_from_dict({"name": t["id"], "base": gui["base"], "axes": gui["axes"]}))
        assert [j.config for j in direct] == [j.config for j in parsed]
        assert [j.name for j in direct] == [j.name for j in parsed] and gui["jobs"] == len(direct)
    ca = S.expand(S.template_spec("ca_vs_mc", ROOT / "configs"))
    assert len(ca) == 16 and ca[0].name == "01_2D_100x100_CA" and ca[-1].name == "16_3D_100x100x100_MC"
    assert ca[1].config["mc"]["enabled"] is True and ca[1].config["mc"]["domain"] == "full"
    assert ca[0].config["ca"]["mode"] == "classic" and ca[0].config["vents"]["count"] == 100
    assert ca[0].config["boundary"] == "periodic" and ca[0].config["neighborhood"] == "von_neumann"
    lava = S.template_spec("lava_vents", ROOT / "configs")
    assert lava.base["space"] == {"nx": 64, "ny": 64, "nz": 48}  # z presetu test_3d


def test_write_series_creates_everything(tmp_path):
    sp = spec([S.axis_from_dict({"name": "zarodki", "keys": ["vents.count"], "text": "1, 2, 3"})])
    jobs = S.expand(sp)
    meta = S.write_series(sp, jobs, tmp_path / "configs", tmp_path / "results", "sid", root=tmp_path)
    for j in jobs:
        cfg = json.loads((tmp_path / "configs" / "sid" / f"{j.name}.json").read_text(encoding="utf-8"))
        assert cfg["_series"]["index"] == j.index and cfg["vents"]["count"] == j.values["vents.count"]
        assert (tmp_path / "results" / "sid" / j.name).is_dir()
    for folder in ("configs", "results"):
        m = json.loads((tmp_path / folder / "sid" / "series.json").read_text(encoding="utf-8"))
        assert m["id"] == "sid" and [x["name"] for x in m["jobs"]] == [j.name for j in jobs]
        assert m["jobs"][0]["config"] == "configs/sid/01_count1.json" and m["axes"][0]["keys"] == ["vents.count"]
    assert meta["resultsDir"] == "results/sid"
    with pytest.raises(S.SeriesError, match="już istnieje"):
        S.write_series(sp, jobs, tmp_path / "configs", tmp_path / "results", "sid")


# ---------------------------------------------------------------- seria i kolejka z prawdziwym silnikiem


def small_series(n=3, name="mala", mcs=None):
    """Seria n szybkich zadań: rozrost klasyczny 30×30, różne liczby zarodków."""
    base = preset("test_2d", **{"space.nx": 30, "space.ny": 30, "space.nz": 1, "ca.mode": "classic",
                                "output.format": "bin"})
    axes = [S.axis_from_dict({"name": "zarodki", "keys": ["vents.count"], "text": ", ".join(str(i + 1) for i in range(n))})]
    sp = S.SeriesSpec(name=name, base=base, axes=axes)
    return sp, S.expand(sp)


def long_config(n=100):
    """Klasyczny rozrost n³ z 1 zarodkiem — zadanie na ~0,5–2 s (kolejka, wiele workerów)."""
    return preset("test_2d", **{"space.nx": n, "space.ny": n, "space.nz": n, "ca.mode": "classic",
                                "vents.count": 1, "output.format": "none"})


def wait_until(cond, timeout=60.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.05)
    return False


def test_series_files_exist_before_start(settings):
    """Najpierw wszystkie configi + series.json i foldery wyników, potem kolejka; nic nie wystartowało."""
    jm = JobManager(settings, start=False)
    sp, jobs = small_series(3)
    meta = jm.create_series(sp, jobs, {"01_count1": 5.0})
    sid = meta["id"]
    cdir, rdir = settings.series_configs_dir / sid, settings.series_results_dir / sid
    assert sorted(p.name for p in cdir.iterdir()) == ["01_count1.json", "02_count2.json", "03_count3.json", "series.json"]
    assert sorted(p.name for p in rdir.iterdir() if p.is_dir()) == ["01_count1", "02_count2", "03_count3"]
    assert (rdir / "series.json").is_file() and (rdir / "01_count1" / "gui_job.json").is_file()
    listed = [j for j in jm.list() if j.seriesId == sid]
    assert len(listed) == 3 and all(j.status == "queued" and j.started is None for j in listed)
    assert jm.queue_state()["order"] == meta["jobIds"]
    first = jm.get(meta["jobIds"][0])
    assert first.estimateMs == 5.0 and first.resultId == f"gui/series/{sid}/01_count1" and first.labels == {"zarodki": "count1"}
    assert first.configPath == f"configs/gui/series/{sid}/01_count1.json"
    # Po starcie workerów: wszystkie gotowe, wyniki w zapowiedzianych folderach.
    jm.start()
    try:
        for jid in meta["jobIds"]:
            assert jm.wait(jid, 60).status == "done"
        assert (rdir / "03_count3" / "ca_result.bin").is_file()
        s = jm.series_list()[0]
        assert s["id"] == sid and s["counts"]["done"] == 3 and s["total"] == 3
    finally:
        jm.shutdown()


def test_series_validation_creates_nothing(settings):
    jm = JobManager(settings, start=False)
    base = preset("test_2d", **{"space.nx": 30, "ca.mode": "classic"})
    sp = S.SeriesSpec(name="zla", base=base, axes=[S.axis_from_dict({"keys": ["neighborhood"], "text": "moore, octagonal"})])
    with pytest.raises(JobError) as e:
        jm.create_series(sp, S.expand(sp))
    assert e.value.status == 422 and any(m.startswith("02_octagonal:") and "neighborhood" in m for m in e.value.errors)
    assert not settings.series_configs_dir.exists() or not any(settings.series_configs_dir.iterdir())
    assert jm.list() == []


def test_queue_order_move_pause_persistence(settings):
    jm = JobManager(settings, start=False)
    a = jm.create(preset("test_2d", **{"ca.maxSteps": 20}), "a")
    b = jm.create(preset("test_2d", **{"ca.maxSteps": 20}), "b")
    c = jm.create(preset("test_2d", **{"ca.maxSteps": 20}), "c")
    assert jm.move(c.id, "up") == [a.id, c.id, b.id]
    assert jm.move(c.id, "top") == [c.id, a.id, b.id]
    assert jm.move(a.id, "bottom") == [c.id, b.id, a.id]
    jm.pause()
    jm.set_workers(2)
    # Stan kolejki przeżywa restart: kolejność, pauza, liczba workerów.
    jm2 = JobManager(settings, start=False)
    q = jm2.queue_state()
    assert q["order"] == [c.id, b.id, a.id] and q["paused"] and q["workers"] == 2
    jm2.set_workers(1)
    order = []
    run = jm2._run
    jm2._run = lambda job, index=0: (order.append(job.id), run(job, index))[1]
    jm2.start()
    try:
        time.sleep(0.8)
        assert all(jm2.get(j).status == "queued" for j in (a.id, b.id, c.id))  # wstrzymana — nic nie startuje
        jm2.resume()
        for j in (a.id, b.id, c.id):
            assert jm2.wait(j, 60).status == "done"
        assert order == [c.id, b.id, a.id]  # kolejność wykonania = kolejność kolejki po przesunięciach (1 worker)
        with pytest.raises(JobError, match="oczekujące"):
            jm2.move(a.id, "up")
    finally:
        jm2.shutdown()


def test_cancel_series_and_retry(settings):
    jm = JobManager(settings, start=False)
    sp, jobs = small_series(3, "do_anulowania")
    meta = jm.create_series(sp, jobs)
    assert jm.cancel_series(meta["id"]) == 3
    assert all(jm.get(j).status == "cancelled" for j in meta["jobIds"]) and jm.queue_state()["order"] == []
    with pytest.raises(JobError):
        jm.cancel_series("nie_ma")
    # Ponowienie: anulowane / z błędem wraca na koniec kolejki z wyczyszczonym stanem.
    again = jm.retry(meta["jobIds"][1])
    assert again.status == "queued" and again.error is None and jm.queue_state()["order"] == [meta["jobIds"][1]]
    broken = jm.get(meta["jobIds"][2])
    broken.status, broken.error, broken.exitCode = "error", "Błąd: x", 3
    jm.retry(broken.id)
    with pytest.raises(JobError, match="Ponowić"):
        jm.retry(meta["jobIds"][1])  # już oczekuje
    jm.start()
    try:
        assert jm.wait(meta["jobIds"][1], 60).status == "done"
        assert jm.wait(meta["jobIds"][2], 60).status == "done" and jm.get(meta["jobIds"][2]).exitCode == 0
        assert jm.get(meta["jobIds"][0]).status == "cancelled"
    finally:
        jm.shutdown()


def test_multiple_workers_run_in_parallel(settings):
    """Dwa workery liczą dwa zadania jednocześnie; zmiana liczby workerów działa w trakcie pracy kolejki."""
    jm = JobManager(settings, workers=1)
    try:
        ids = [jm.create(long_config(), f"dlugie{i}").id for i in range(3)]
        assert wait_until(lambda: jm.get(ids[0]).status == "running", 30)
        assert jm.get(ids[1]).status == "queued"   # 1 worker — drugie czeka
        assert jm.set_workers(2) == 2
        assert wait_until(lambda: sum(jm.get(i).status == "running" for i in ids) == 2, 30), "nie widać 2 zadań naraz"
        for i in ids:
            assert jm.wait(i, 120).status == "done"
    finally:
        jm.shutdown()


def test_pinning_to_cpu(settings):
    jm = JobManager(settings, workers=1)
    try:
        jm.set_pin(True, [0])
        with pytest.raises(JobError):
            jm.set_pin(True, [10_000])
        # zadanie na ~0,5 s: krótsze (30 kroków test_2d) kończyło się czasem przed przypięciem (PID not found)
        job = jm.wait(jm.create(long_config(), "przypiete").id, 60)
        assert job.status == "done" and job.pinnedCpu == 0
        assert "przypięto do procesora logicznego 0" in jm.read_log(job.id)
    finally:
        jm.shutdown()


def test_launch_mode_threads():
    # 1 wątek: przypięcie i wysoki priorytet razem (pomiar jak w etapie 3); bez przypinania — priorytet normalny.
    assert launch_mode(True, 1) == (True, HIGH_PRIORITY)
    assert launch_mode(False, 1) == (False, 0)
    # Wiele wątków (etap 9): zawsze wysoki priorytet, nigdy przypięcie całego procesu do jednego procesora.
    assert launch_mode(True, 8) == (False, HIGH_PRIORITY)
    assert launch_mode(False, 2) == (False, HIGH_PRIORITY)
    # threads = 0 (wszystkie procesory logiczne): bez przypięcia, priorytet normalny.
    assert launch_mode(True, 0) == (False, 0)
    if sys.platform == "win32":
        assert HIGH_PRIORITY == subprocess.HIGH_PRIORITY_CLASS


def test_multithreaded_job_not_pinned_to_one_cpu(settings):
    jm = JobManager(settings, workers=1)
    try:
        jm.set_pin(True, [0])   # przypinanie włączone — zadanie wielowątkowe i tak nie trafia na jeden procesor
        job = jm.wait(jm.create(preset("test_2d", **{"ca.maxSteps": 30, "parallel.threads": 2}), "watki").id, 60)
        assert job.status == "done" and job.pinnedCpu is None
        log = jm.read_log(job.id)
        assert "wątki OpenMP: 2" in log and "bez przypięcia" in log and "przypięto" not in log
        if sys.platform == "win32":
            assert "priorytet wysoki" in log
        times = json.loads((settings.root / job.outDir / "times.json").read_text(encoding="utf-8"))
        assert times["threads"] == 2
    finally:
        jm.shutdown()


# ---------------------------------------------------------------- przez HTTP


def test_api_series_queue_and_compare(client, settings):
    t = {x["id"]: x for x in client.get("/api/series/templates").json()}
    assert set(t) == {"ca_vs_mc", "seeds", "neighborhood", "lava_vents", "openmp_threads"} and t["ca_vs_mc"]["jobs"] == 16
    pv = client.post("/api/series/preview", json={"spec": {"name": "ca_vs_mc", "base": t["ca_vs_mc"]["base"],
                                                           "axes": t["ca_vs_mc"]["axes"]}}).json()
    assert pv["count"] == 16 and pv["jobs"][0]["config"]["grid"] == "vector"  # config scalony z domyślnymi
    bad = client.post("/api/series/preview", json={"spec": {"base": {}, "axes": [{"keys": ["vent.count"], "text": "1"}]}})
    assert bad.status_code == 422 and "Nieznany parametr" in bad.json()["errors"][0]

    client.post("/api/queue", json={"paused": True})
    sp = {"name": "api", "base": preset("test_2d", **{"space.nx": 30, "space.ny": 30, "space.nz": 1, "ca.mode": "classic",
                                                     "output.format": "bin"}),
          "axes": [{"name": "zarodki", "keys": ["vents.count"], "mode": "list", "text": "1, 4"},
                   {"name": "algorytm", "keys": ["mc.enabled", "mc.domain"], "mode": "list",
                    "text": "[CA] false;basalt, [MC] true;full"}]}
    sp["base"]["mc"]["mcs"] = 5
    sp["base"]["mc"]["mobilityFromCooling"] = False
    res = client.post("/api/series", json={"spec": sp, "estimates": {"01_count1_CA": 1}})
    assert res.status_code == 201, res.json()
    meta = res.json()
    sid = meta["id"]
    assert len(meta["jobs"]) == 4 and (settings.root / meta["configsDir"] / "series.json").is_file()
    jobs = {j["id"]: j for j in client.get("/api/jobs").json()}
    first = jobs[meta["jobIds"][0]]
    assert first["status"] == "queued" and first["queuePosition"] == 1 and first["estimateMs"] == 1
    assert client.post(f"/api/jobs/{meta['jobIds'][3]}/move", json={"direction": "top"}).json()["order"][0] == meta["jobIds"][3]
    assert client.post(f"/api/jobs/{meta['jobIds'][0]}/move", json={"direction": "sideways"}).status_code == 422
    q = client.post("/api/queue", json={"paused": False, "workers": 1}).json()
    assert not q["paused"] and q["workers"] == 1
    jm = client.app.state.jobs
    for jid in meta["jobIds"]:
        assert jm.wait(jid, 60).status == "done"
    assert client.get("/api/series").json()[0]["counts"]["done"] == 4

    # Wyniki serii: lista wyników (identyfikatory 4-członowe), porównanie, CSV.
    ids = {r["id"]: r for r in client.get("/api/results").json()}
    rid = f"gui/series/{sid}/02_count1_MC"
    assert rid in ids and ids[rid]["series"] == f"gui/series/{sid}"
    assert client.get("/api/result", params={"id": rid}).json()["fields"] == ["type", "crystal"]
    src = client.get("/api/compare/sources").json()
    assert src[0]["ref"] == f"gui/series/{sid}" and src[0]["done"] == 4
    table = client.get("/api/compare", params={"series": f"gui/series/{sid}"}).json()
    rows = {r["name"]: r for r in table["rows"]}
    assert rows["01_count1_CA"]["algorithm"] == "CA" and rows["01_count1_CA"]["caSim"] > 0
    assert rows["02_count1_MC"]["algorithm"] == "MC" and rows["02_count1_MC"]["mcs"] == 5
    assert rows["02_count1_MC"]["simMs"] == rows["02_count1_MC"]["mcSim"] and rows["02_count1_MC"]["nsPerTrial"] > 0
    assert rows["03_count4_CA"]["labels"] == {"zarodki": "count4", "algorytm": "CA"} and rows["03_count4_CA"]["seeds"] == 4
    csv_text = client.get("/api/compare/csv", params={"series": f"gui/series/{sid}"}).text
    header = csv_text.splitlines()[0].split(",")
    assert header[:4] == ["index", "name", "zarodki", "algorytm"] and "caSim" in header and len(csv_text.splitlines()) == 5
    sel = client.post("/api/compare", json={"ids": [rid, f"gui/series/{sid}/04_count4_MC"]}).json()
    assert [r["values"] for r in sel["rows"]] == [{"vents.count": 1}, {"vents.count": 4}]  # klucze, które się różnią
    assert client.get("/api/compare", params={"series": "../../x"}).status_code == 400
    assert client.post(f"/api/series/{sid}/cancel", json={}).json()["cancelled"] == 0
