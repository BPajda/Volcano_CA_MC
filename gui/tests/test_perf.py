"""Zakładka „Wydajność”: dane gui/static/data/wydajnosc.json (tools/wydajnosc_gui.py), teksty zakładki i dokumenty
(/api/doc, /api/doc/pdf).

- schemat pliku: wersja formatu, nagłówek, „Pojęcia”, pięć sekcji o stałych nazwach (odwołują się do nich dokumentacja
  i opisy obsługi), każdy wykres z wnioskiem, „Jak czytać”, warunkami, źródłami („Skąd dane”) i dokumentem PDF, spójne
  widoki (długości serii, klucze widoków = kompilator + opcje przełączników),
- zasady redakcji widocznych tekstów (plik danych i napisy w perf.js): bez długich pauz, bez „etapów”, „turbo” tylko
  w opisie taktowania, warunki bez nazw plików i ścieżek,
- wartości kontrolne porównane z plikami pomiarów czytanymi tutaj niezależnie (CSV / tabele Markdown),
- plik w repozytorium = świeżo wygenerowany („dane aktualne”),
- endpointy /api/doc/list, /api/doc (tylko .md z folderu dokumentacji), /api/doc/pdf (tylko PDF z docs/pdf/) i plik
  statyczny /data/wydajnosc.json.

Testy wymagające danych pomiarów (bench/results/*/) albo skryptu są pomijane w kopii projektu bez nich.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "gui" / "static" / "data" / "wydajnosc.json"
PERF_JS = ROOT / "gui" / "static" / "js" / "perf.js"
PDF_DIR = ROOT / "docs" / "pdf"
RES = ROOT / "bench" / "results"
TOOL = ROOT / "tools" / "wydajnosc_gui.py"
SECTIONS = ["Optymalizacja sekwencyjna", "OpenMP", "MPI", "Typy MPI i MPI-IO", "Testy wydajności"]
ROLES = {"s1", "s2", "s3", "ca", "mc", "camc", "seq1", "seq2", "seq3", "before", "after", "muted", "ideal"}
KINDS = {"line", "bar", "hbar", "scatter", "dots"}
FMTS = {None, "ms", "times", "pct", "int", "pow10", "num"}
# Pola, które nie są widocznym tekstem (identyfikatory, role kolorów, ścieżki „Skąd dane”, nazwy plików PDF).
NOT_TEXT = {"sources", "bestSources", "id", "role", "roles", "marker", "markers", "kind", "fmt", "generator", "generated",
            "pdf", "format"}

needs_results = pytest.mark.skipif(not (RES / "omp").is_dir() or not (RES / "testy").is_dir(),
                                   reason="brak danych pomiarów bench/results/*/ w tej kopii projektu")


@pytest.fixture(scope="module")
def data() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def charts(d: dict) -> dict[str, dict]:
    out = {c["id"]: c for s in d["sections"] for c in s["charts"]}
    out[d["summary"]["chart"]["id"]] = d["summary"]["chart"]
    return out


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def series(view: dict, name: str) -> dict:
    return next(s for s in view["series"] if s["name"] == name)


def at_x(s: dict, x: float) -> float:
    return next(p[1] for p in s["data"] if p and p[0] == x)


def texts(obj, path: str = ""):
    """Wszystkie widoczne teksty pliku danych: (ścieżka w JSON, tekst)."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k not in NOT_TEXT:
                yield from texts(v, f"{path}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from texts(v, f"{path}/{i}")
    elif isinstance(obj, str):
        yield path, obj


def js_strings(src: str) -> list[str]:
    """Napisy z kodu JS ('…', "…", `…`) bez komentarzy — to, co może trafić na ekran. W szablonie `…${wyr}…` tekst
    szablonu jest jednym napisem (wyrażenie zastępuje znak \\0), a napisy z wyrażenia — osobnymi (także zagnieżdżone)."""
    out, n = [], len(src)

    def code(i: int, in_expr: bool) -> int:
        depth = 0
        while i < n:
            c = src[i]
            if src.startswith("//", i):
                i = src.find("\n", i)
                i = n if i < 0 else i
            elif src.startswith("/*", i):
                j = src.find("*/", i + 2)
                i = n if j < 0 else j + 2
            elif c in "'\"":
                j, buf = i + 1, []
                while j < n and src[j] != c:
                    buf.append(src[j:j + 2] if src[j] == "\\" else src[j])
                    j += 2 if src[j] == "\\" else 1
                out.append("".join(buf))
                i = j + 1
            elif c == "`":
                i = template(i + 1)
            elif c == "/" and re.search(r"(^|[(,=:\[!&|?{};]|return)\s*$", src[max(0, i - 12):i]):
                j, cls = i + 1, False  # wyrażenie regularne /…/ (może zawierać cudzysłowy, np. /[&<>"']/g)
                while j < n and src[j] != "\n" and (cls or src[j] != "/"):
                    cls = (cls or src[j] == "[") and src[j] != "]"
                    j += 2 if src[j] == "\\" else 1
                i = j + 1
            elif in_expr and c == "{":
                depth += 1
                i += 1
            elif in_expr and c == "}":
                if depth == 0:
                    return i + 1
                depth -= 1
                i += 1
            else:
                i += 1
        return i

    def template(i: int) -> int:
        buf = []
        while i < n and src[i] != "`":
            if src[i] == "\\":
                buf.append(src[i:i + 2])
                i += 2
            elif src.startswith("${", i):
                buf.append("\0")
                i = code(i + 2, True)
            else:
                buf.append(src[i])
                i += 1
        out.append("".join(buf))
        return i + 1

    code(0, False)
    return out


# ---------------------------------------------------------------------------- schemat


def test_schema_top_level(data):
    assert data["format"] == 2
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d", data["generated"])
    assert data["generator"] == "tools/wydajnosc_gui.py"
    assert set(data["compilers"]) == {"msvc", "gcc"}
    assert [s["title"] for s in data["sections"]] == SECTIONS
    assert len({s["id"] for s in data["sections"]}) == 5
    h = data["header"]
    assert h["principle"].startswith("Wynik symulacji jest bitowo ten sam")
    assert h["allOk"] is True and h["runsDifferent"] == 0
    badges = [b["text"] for b in h["badges"]]
    assert "15/15 konfiguracji" in badges and "1–8 wątków" in badges and "1–8 procesów" in badges and "MSVC i GCC" in badges
    assert data["sources"] == sorted(set(data["sources"])) and len(data["sources"]) > 20
    if (RES / "omp").is_dir():
        assert all((ROOT / p).is_file() for p in data["sources"] + h["sources"])
    terms = [g["term"] for g in data["glossary"]]
    assert len(terms) >= 15 and all(g["def"] for g in data["glossary"])
    for t in ("Przyspieszenie S(p)", "Efektywność E(p)", "Automat frontalny", "Szachownica (Monte Carlo)", "MPI-IO",
              "Typ pochodny MPI", "Taktowanie bazowe i dynamiczne", "Rdzenie P i E"):
        assert t in terms, t
    for s in data["sections"]:
        assert len(s["intro"]) > 40 and s["doc"]["pdf"].endswith(".pdf") and s["doc"]["title"]


def test_schema_charts(data):
    all_charts = charts(data)
    assert len(all_charts) == 25
    for cid, c in all_charts.items():
        assert c["kind"] in KINDS, cid
        for k in ("title", "lead", "conclusion", "conditions"):
            assert isinstance(c[k], str) and len(c[k]) > 10, (cid, k)
        assert 2 <= len(c["howto"]) <= 6 and all(len(h) > 10 for h in c["howto"]), cid
        assert c["sources"] and all(p.startswith("bench/results/") for p in c["sources"]), cid
        assert set(c["sources"]) <= set(data["sources"]), cid
        assert c["doc"]["pdf"].endswith(".pdf") and c["doc"]["title"] and "section" in c["doc"], cid
        assert set(c["compilers"]) <= {"msvc", "gcc"}, cid
        assert c["views"], cid
        options = [{o["id"] for o in s["options"]} for s in c["selectors"]]
        for key, v in c["views"].items():
            parts = key.split("|")
            if c["compilers"]:
                assert parts[0] in c["compilers"], (cid, key)
                parts = parts[1:]
            assert len(parts) == len(options) or (not options and parts in ([], [""])), (cid, key)
            for p, opts in zip(parts, options):
                assert p in opts, (cid, key, p)
            check_view(cid, c, key, v)


def check_view(cid: str, c: dict, key: str, v: dict) -> None:
    kind = v.get("kind", c["kind"])
    assert kind in KINDS, (cid, key)
    numeric = kind in ("line", "scatter") and "labels" not in v
    assert v["series"], (cid, key)
    for ax in ("x", "y"):
        assert v[ax].get("fmt") in FMTS, (cid, key, ax)
    n_rows = len(v.get("labels", []))
    for s in v["series"]:
        assert s["role"] in ROLES, (cid, key, s["name"])
        n = len(s["data"])
        if numeric:
            assert all(p is None or (len(p) == 2 and all(isinstance(x, (int, float)) for x in p)) for p in s["data"])
        elif kind == "dots":  # wartość albo lista wartości (kilka punktów w wierszu)
            assert n == n_rows, (cid, key, s["name"])
            assert all(x is None or isinstance(x, (int, float)) or (isinstance(x, list) and x) for x in s["data"])
        else:
            assert n == n_rows, (cid, key, s["name"])
            assert all(x is None or isinstance(x, (int, float)) for x in s["data"])
        for k in ("tips", "lo", "hi", "labels", "roles", "markers", "ptLabels"):
            if k in s:
                assert len(s[k]) == n, (cid, key, s["name"], k)
        if "band" in s:
            assert len(s["band"]["lo"]) == len(s["band"]["hi"]) == n
    for k in ("rowText", "rowNotes"):
        if k in v:
            assert len(v[k]) == n_rows, (cid, key, k)
    assert all(0 <= i < n_rows for i in v.get("headers", [])), (cid, key)
    for row in v.get("legendRows", []):
        assert row["label"] and row["items"] and all(it["label"] for it in row["items"]), (cid, key)
    # widok ma dane albo opisane zera (np. „0 chybień” na skali log., gdzie zera nie da się narysować)
    assert any(any(x is not None for x in s["data"]) or any(s.get("labels") or [])
               for s in v["series"] if s["role"] != "ideal"), (cid, key)


def test_rebuilt_charts(data):
    """Przebudowane wykresy: kroki optymalizacji (wiersz na krok, grupy taktowania), chybienia (przełącznik poziomu,
    pary jako wykres hantlowy) i model pamięci (błąd % domyślnie, drugi widok z linią y = x)."""
    ch = charts(data)
    k = ch["seq_kroki"]
    v = k["views"]["msvc|total"]
    assert v["labels"][0].startswith("Kroki k1–k4") and v["labels"][5].startswith("Kroki k5–k8")
    assert v["headers"] == [0, 5] and v["x"]["log"] and v["x"]["base"] == 1
    assert "nie mierzono" in v["rowNotes"][v["labels"].index("k6: mniejsze typy danych")]
    assert [s["k"] for s in k["steps"]] == [f"k{i}" for i in range(1, 9)]
    k4 = v["labels"].index("k4: automat frontalny")
    assert series(v, "lawa")["data"][k4] > 5 and series(v, "Monte Carlo")["data"][k4] is None  # k4 nie dotyczy MC
    cg = ch["t_cachegrind"]
    assert [s["id"] for s in cg["selectors"]] == ["view", "level"]
    assert [o["id"] for o in cg["selectors"][1]["options"]] == ["D1", "L2", "L3"]
    pary = cg["views"]["pary|D1"]
    assert pary["kind"] == "dots" and pary["connect"] and any("mniej" in t for t in pary["rowText"])
    assert any("0 chybień" in (n or "") or any("0 chybień" in t for t in s["ptLabels"])
               for s in cg["views"]["pary|L3"]["series"] for n in cg["views"]["pary|L3"]["rowNotes"])
    m = ch["t_model"]
    assert [o["id"] for o in m["selectors"][0]["options"]] == ["err", "xy"]
    assert m["views"]["msvc|err"]["kind"] == "dots" and m["views"]["msvc|err"]["xband"] == {"from": -10, "to": 10,
                                                                                         "label": "±10%"}
    xy = m["views"]["msvc|xy"]
    assert series(xy, "pomiar = model")["band"] and [r["label"] for r in xy["legendRows"]] == ["kolor", "kształt"]


def test_summary(data):
    s = data["summary"]
    for comp in ("msvc", "gcc"):
        assert len(s["tiles"][comp]) == 4
        assert len(s["best"][comp]) == 7
        for r in s["best"][comp]:
            assert 0 < r["S"] <= r["cores"] * 1.1 and abs(r["E"] - r["S"] / r["cores"]) < 0.002
            assert r["version"].startswith("wersja")
    assert s["tilesHowto"] and s["bestHowto"] and s["bestConditions"] and s["doc"]["pdf"].endswith(".pdf")


# ---------------------------------------------------------------------------- zasady redakcji tekstów


def test_texts_rules(data):
    bad = []
    for path, t in texts(data):
        if "—" in t:
            bad.append(("długa pauza", path, t))
        if re.search("etap", t, re.I):
            bad.append(("etap", path, t))
        if re.search("turbo", t, re.I) and not path.startswith("/glossary"):
            bad.append(("turbo", path, t))
        if re.search(r"tryb\w* oszczędn", t, re.I):
            bad.append(("tryb oszczędny", path, t))
        if re.search(r"×0,\d", t):  # zysk i strata jako mnożnik > 1 („×1,10 wolniej”), także w podpowiedziach
            bad.append(("mnożnik < 1", path, t))
        if re.search(r"ca\.sweep|mpi\.(exchange|pack|bcast|io)\b|--mc-from|\bVN\b", t):
            bad.append(("klucz configu albo skrót", path, t))
    assert not bad, bad[:10]
    # „turbo” tylko raz, w opisie taktowania („Pojęcia”)
    assert [g["term"] for g in data["glossary"] if "turbo" in g["def"].lower()] == ["Taktowanie bazowe i dynamiczne"]


def test_conditions_without_files(data):
    conds = [c["conditions"] for c in charts(data).values()] + [data["summary"]["bestConditions"],
                                                                data["conditions"]["gcc"]]
    for t in conds:
        assert not re.search(r"\.(csv|md|json|py)\b|bench/|docs/|results/", t), t


def test_every_card_has_parts(data):
    for cid, c in charts(data).items():
        assert c["lead"] and c["conclusion"] and c["howto"] and c["conditions"] and c["sources"], cid


def test_gain_labels_above_one(data):
    """Mnożniki zysku w etykietach słupków jako przyspieszenie > 1 (np. „×215 szybciej”, nie „×0,005”)."""
    for cid, c in charts(data).items():
        for v in c["views"].values():
            for s in v["series"]:
                for lbl in s.get("labels", []) or []:
                    m = re.match(r"×(\d+(?:\u00a0\d{3})*(?:,\d+)?)", lbl or "")
                    if m:
                        assert float(m.group(1).replace("\u00a0", "").replace(",", ".")) >= 1, (cid, lbl)


def test_perf_js_texts():
    bad = [s for s in js_strings(PERF_JS.read_text(encoding="utf-8"))
           if "—" in s or re.search("etap|turbo", s, re.I)]
    assert not bad, bad


def prose_dash(s: str) -> bool:
    """Długa pauza w prozie: „—” poza znakiem pustej wartości ('—', „krok —”, „do końca: —”) i poza pustą pozycją
    listy wyboru („— wybierz preset —”)."""
    if s.strip() == "—":
        return False
    s = re.sub(r"(['\"])—\1", "", s)
    s = re.sub(r"— [^—<>'\"]+ —", "", s)
    s = re.sub(r"(krok|do końca:) —", "", s)
    return "—" in s


def test_gui_texts_without_dash():
    """Teksty wszystkich zakładek (index.html bez komentarzy, napisy z js/*.js) bez długich pauz w prozie."""
    static = ROOT / "gui" / "static"
    html = re.sub(r"<!--.*?-->|/\*.*?\*/", "", (static / "index.html").read_text(encoding="utf-8"), flags=re.S)
    bad = [ln.strip() for ln in html.splitlines() if prose_dash(ln)]
    for js in sorted((static / "js").glob("*.js")):
        bad += [f"{js.name}: {s[:80]}" for s in js_strings(js.read_text(encoding="utf-8")) if prose_dash(s)]
    assert not bad, bad


def test_app_title():
    html = (ROOT / "gui" / "static" / "index.html").read_text(encoding="utf-8")
    title = "Wulkan: spływ lawy (CA) i krystalizacja bazaltu (MC)"
    assert f"<title>{title}</title>" in html and f'<span class="brand-title">{title}</span>' in html


def test_pdf_links_exist(data):
    docs = {c["doc"]["pdf"] for c in charts(data).values()} | {s["doc"]["pdf"] for s in data["sections"]} | \
           {data["summary"]["doc"]["pdf"]}
    assert docs
    for name in docs:
        assert (PDF_DIR / name).is_file(), f"brak docs/pdf/{name} — python tools/build_docs_pdf.py"
    index = json.loads((PDF_DIR / "index.json").read_text(encoding="utf-8"))["titles"]
    for c in charts(data).values():
        assert index[c["doc"]["pdf"]] == c["doc"]["title"], c["id"]


# ---------------------------------------------------------------------------- wartości kontrolne


def profile_value(name: str, variant: str, col: str) -> float:
    r = next(x for x in read_csv(RES / name) if x["variant"] == variant and x["build"] == "msvc-O2")
    return float(r[col])


@needs_results
def test_control_etna_before_after(data):
    v = charts(data)["seq_przed_po"]["views"]["msvc|total"]
    i = v["labels"].index("lawa: Etna (rzeczywisty teren)")
    before = profile_value("profile_2026-10-17_przed2.csv", "etna_real", "total_ms_med")
    after = profile_value("profile_2026-10-17_po.csv", "etna_real", "total_ms_med")
    assert series(v, "przed optymalizacją")["data"][i] == pytest.approx(before, rel=1e-3)
    assert series(v, "po optymalizacji")["data"][i] == pytest.approx(after, rel=1e-3)
    assert 32_000 < before < 33_000 and 140 < after < 160  # 32,3 s → 0,15 s
    assert series(v, "po optymalizacji")["labels"][i] == "×215 szybciej"


@needs_results
def test_control_openmp_s8_lava_full(data):
    r = next(x for x in read_csv(RES / "omp" / "skalowanie_msvc.csv")
             if x["case"] == "lava_duza_3d_full" and x["threads"] == "8")
    v = charts(data)["omp_skalowanie"]["views"]["msvc|S|lawa|phase"]
    assert at_x(series(v, "lawa: teren testowy 128×128×64, pełny przebieg"), 8) == pytest.approx(float(r["S_phase"]), rel=1e-3)
    assert round(float(r["S_phase"]), 2) == 6.34


@needs_results
def test_control_mpi7_mc1000(data):
    r = next(x for x in read_csv(RES / "mpi" / "skalowanie_mpi_msvc.csv")
             if x["case"] == "mc_cb_2d_1000" and x["variant"] == "m7")
    v = charts(data)["mpi_skalowanie"]["views"]["msvc|S|mc_cb_2d_1000"]
    assert at_x(series(v, "MPI, 7 procesów bez procesora 0"), 7) == pytest.approx(float(r["S_phase"]), rel=1e-3)
    assert round(float(r["S_phase"]), 2) == 6.72


def md_save_row(case: str, p: int) -> tuple[float, float]:
    """Wiersz tabeli zapisu z pomiar_msvc.md: save gather (m) i MPI-IO (i) dla p procesów."""
    text = (RES / "mpi_io" / "pomiar_msvc.md").read_text(encoding="utf-8")
    block = text.split(f"### `{case}`", 1)[1].split("###", 1)[0]
    row = next(ln for ln in block.splitlines() if ln.startswith(f"| {p} |"))
    cells = [c.strip() for c in row.strip("|").split("|")]
    num = lambda c: float(c.split("[")[0].replace(" ", "").replace(",", "."))  # noqa: E731
    return num(cells[1]), num(cells[2])


@needs_results
@pytest.mark.parametrize("case", ["io_bin_classic_300", "io_txt_classic_300"])
def test_control_write_gather_vs_mpiio(data, case):
    m, i = md_save_row(case, 8)
    v = charts(data)["io_zapis"]["views"][f"msvc|{case}|save"]
    k = v["labels"].index("8 procesów")
    assert series(v, "zebranie na procesie 0")["data"][k] == pytest.approx(m, abs=0.6)
    assert series(v, "równoległy zapis MPI-IO")["data"][k] == pytest.approx(i, abs=0.6)


@needs_results
def test_control_weak_scaling_e8(data):
    r = next(x for x in read_csv(RES / "testy" / "slabe_omp_msvc.csv")
             if x["case"] == "weak_classic_2d" and x["cores"] == "8")
    v = charts(data)["t_slabe"]["views"]["msvc|weak_classic_2d|phase"]
    assert at_x(series(v, "OpenMP: słabe E_w(p)"), 8) == pytest.approx(float(r["Ew_phase"]), rel=1e-3)
    assert round(float(r["Ew_phase"]), 2) == 0.49


@needs_results
def test_control_total_speedup_etna(data):
    text = (RES / "testy" / "zestawienie.md").read_text(encoding="utf-8")
    row = next(ln for ln in text.splitlines() if ln.startswith("| lawa `etna_real`, front | MSVC |"))
    total = re.search(r"\*\*×(\d+)\*\*", row).group(1)
    tile = next(t for t in data["summary"]["tiles"]["msvc"] if t["label"] == "Lawa: Etna")
    assert tile["value"].replace("\u00a0", "") == f"×{total}"


# ---------------------------------------------------------------------------- dane aktualne


@needs_results
def test_json_is_fresh(data):
    if not TOOL.is_file():
        pytest.skip("brak tools/wydajnosc_gui.py")
    pytest.importorskip("psutil")  # bench/memory.py → bench/ab.py
    spec = importlib.util.spec_from_file_location("wydajnosc_gui", TOOL)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["wydajnosc_gui"] = mod
    spec.loader.exec_module(mod)
    fresh = json.loads(mod.dumps(mod.build()))
    assert mod.strip_generated(fresh) == mod.strip_generated(data), \
        "gui/static/data/wydajnosc.json nieaktualny — uruchom python tools/wydajnosc_gui.py"


# ---------------------------------------------------------------------------- backend: dokumenty i plik danych


def make_client(root: Path):
    import warnings

    warnings.filterwarnings("ignore", message="Using `httpx` with `starlette.testclient`")
    from fastapi.testclient import TestClient

    from gui.app import create_app
    from gui.settings import Settings

    s = Settings(root=root, engine=None, engine_source="test", configs_dir=root / "configs", results_dir=root / "results")
    return TestClient(create_app(s, start_workers=False))


@pytest.fixture
def docs_client(tmp_path: Path):
    (tmp_path / "docs" / "pdf").mkdir(parents=True)
    (tmp_path / "docs" / "openmp.md").write_text("# Zrównoleglenie OpenMP\n\nżółć\n", encoding="utf-8")
    (tmp_path / "docs" / "notatka.txt").write_text("nie Markdown", encoding="utf-8")
    (tmp_path / "docs" / "pdf" / "openmp.pdf").write_bytes(b"%PDF-1.4\n% test\n")
    (tmp_path / "docs" / "pdf" / "index.json").write_text(
        json.dumps({"titles": {"openmp.pdf": "Zrównoleglenie OpenMP"}}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "docs" / "tajny.pdf").write_bytes(b"%PDF-1.4\n% poza folderem pdf\n")
    (tmp_path / "tajny.md").write_text("poza folderem dokumentacji", encoding="utf-8")
    for d in ("configs", "results"):
        (tmp_path / d).mkdir()
    with make_client(tmp_path) as c:
        yield c


def test_doc_list_and_text(docs_client):
    assert docs_client.get("/api/doc/list").json() == {"docs": ["openmp.md"], "pdf": ["openmp.pdf"]}
    r = docs_client.get("/api/doc", params={"name": "openmp.md"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain") and "charset=utf-8" in r.headers["content-type"]
    assert r.text == "# Zrównoleglenie OpenMP\n\nżółć\n"


@pytest.mark.parametrize("name", ["../tajny.md", "..\\tajny.md", "notatka.txt", "openmp", "/etc/passwd",
                                  "C:\\Windows\\win.ini", "sub/openmp.md", "brak.md", ""])
def test_doc_rejects_paths(docs_client, name):
    r = docs_client.get("/api/doc", params={"name": name})
    assert r.status_code in (404, 422), name
    assert "poza folderem" not in r.text and "nie Markdown" not in r.text


def test_doc_pdf_download(docs_client):
    r = docs_client.get("/api/doc/pdf", params={"name": "openmp.pdf"})
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
    cd = r.headers["content-disposition"]
    assert cd.startswith('attachment; filename="volcano-ca-mc - Zrownoleglenie OpenMP.pdf"')
    assert "filename*=UTF-8''volcano-ca-mc%20-%20Zr%C3%B3wnoleglenie%20OpenMP.pdf" in cd
    r = docs_client.get("/api/doc/pdf", params={"name": "openmp.pdf", "inline": 1})
    assert r.status_code == 200 and r.headers["content-disposition"].startswith("inline;")


@pytest.mark.parametrize("name", ["../tajny.pdf", "..\\tajny.pdf", "..", "../pdf/openmp.pdf", "pdf/openmp.pdf",
                                  "/etc/passwd", "C:\\Windows\\win.ini", "index.json", "openmp.md", "brak.pdf",
                                  "tajny.pdf", ""])
def test_doc_pdf_rejects_names(docs_client, name):
    r = docs_client.get("/api/doc/pdf", params={"name": name})
    assert r.status_code in (404, 422), name
    assert b"poza folderem" not in r.content


def test_doc_pdf_for_every_chart_document(data):
    """Każdy dokument z pliku danych zakładki da się pobrać z prawdziwego folderu docs/pdf/ tej kopii projektu."""
    names = {c["doc"]["pdf"] for c in charts(data).values()} | {s["doc"]["pdf"] for s in data["sections"]}
    with make_client(ROOT) as c:
        listed = set(c.get("/api/doc/list").json()["pdf"])
        for name in sorted(names):
            assert name in listed, name
            r = c.get("/api/doc/pdf", params={"name": name})
            assert r.status_code == 200 and r.content.startswith(b"%PDF"), name
            assert r.headers["content-disposition"].startswith('attachment; filename="volcano-ca-mc - ')


def test_doc_list_without_docs_folder(tmp_path: Path):
    for d in ("configs", "results"):
        (tmp_path / d).mkdir()
    with make_client(tmp_path) as c:
        assert c.get("/api/doc/list").json() == {"docs": [], "pdf": []}
        assert c.get("/api/doc", params={"name": "openmp.md"}).status_code == 404
        assert c.get("/api/doc/pdf", params={"name": "openmp.pdf"}).status_code == 404


def test_static_data_file(docs_client, data):
    r = docs_client.get("/data/wydajnosc.json")
    assert r.status_code == 200 and r.json()["format"] == data["format"]
