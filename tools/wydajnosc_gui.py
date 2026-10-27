#!/usr/bin/env python3
"""Dane zakładki „Wydajność” GUI (optymalizacja, OpenMP, MPI, typy MPI i MPI-IO, testy) -> gui/static/data/wydajnosc.json.

Czyta istniejące pliki pomiarów w bench/results/ (profil przed / po optymalizacji sekwencyjnej, testy A/B `ab/`,
skalowanie OpenMP `omp/`, MPI `mpi/`, typy pochodne i MPI-IO `mpi_io/`, testy wydajności `testy/`, tabele zgodności
`*/zgodnosc_*.md`) i zapisuje jeden plik JSON z gotowymi do narysowania wykresami: dla każdego wykresu tytuł, wniosek,
„Jak czytać”, warunki pomiaru słownie, pliki źródłowe („Skąd dane”), dokument PDF i widoki (kompilator × przełączniki)
z seriami danych. Bez nowych pomiarów. Zakładka (gui/static/js/perf.js) tylko to rysuje — żadna liczba nie jest
wpisana w JS.

Zasady porównywania jak w bench/zestawienie_e12.py (z niego pochodzi zestawienie S / E i łączne przyspieszenie):
S zawsze od T(1) tej samej sesji, kroki optymalizacji k1–k4 (taktowanie dynamiczne) i k5–k8 (taktowanie bazowe) tylko
jako stosunki z jednego testu A/B, czasy przed / po optymalizacji — z profilu przy taktowaniu bazowym.

Teksty widoczne w zakładce (tytuły, wnioski, „Jak czytać”, warunki, serie, osie, podpowiedzi): pełne zdania bez
długich pauz i bez wewnętrznych nazw (klucz techniczny najwyżej w podpowiedzi albo raz w nawiasie), mnożniki zysku
jako przyspieszenie > 1, liczby po polsku; nazwy plików tylko w polach `sources` („Skąd dane”). Sprawdza to
gui/tests/test_perf.py.

    python tools/wydajnosc_gui.py            # zapis gui/static/data/wydajnosc.json
    python tools/wydajnosc_gui.py --check    # tylko porównanie z plikiem w repozytorium (kod 1 — dane nieaktualne)

Format pliku (wersja FORMAT): {format, generated, generator, sources[], compilers{}, header{}, glossary[], conditions{},
summary{}, sections[]}; sekcja: {id, title, intro, doc, charts[]}; wykres: {id, title, kind (line | bar | hbar | scatter
| dots), wide?, selectors[], compilers[], views{klucz: widok}, lead, conclusion, howto[], steps?, conditions, sources[],
doc{pdf, title, section}}; klucz widoku = kompilator (gdy wykres ma dane kompilatorów) i wartości przełączników
połączone „|”; widok: {kind?, labels?, headers?, x{}, y{}, series[], hlines?, vlines?, xband?, connect?, rowText?,
rowNotes?, legend?, legendRows?, note?}; seria: {name, role (kolor z motywu GUI), marker?, dash?, outline?, data, lo?,
hi?, tips?, labels?, roles?, markers?, ptLabels?, band?}.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "bench" / "results"
OUT = ROOT / "gui" / "static" / "data" / "wydajnosc.json"
FORMAT = 2
sys.path.insert(0, str(ROOT / "bench"))

COMPILERS = {"msvc": "MSVC / MS-MPI", "gcc": "GCC / OpenMPI (WSL)"}
BUILD = {"msvc": "msvc-O2", "gcc": "gcc-O3"}
# Dokumenty (PDF w docs/pdf/, budowane z docs/<nazwa>.md przez tools/build_docs_pdf.py): nazwa pliku i tytuł.
DOCS = {"seq": ("optymalizacja-sekwencyjna", "Optymalizacja wersji sekwencyjnej"),
        "omp": ("openmp", "Zrównoleglenie OpenMP"), "mpi": ("mpi", "Wersja rozproszona MPI"),
        "mpiio": ("mpi-typy-i-zapis", "Typy pochodne MPI i równoległy zapis"),
        "tests": ("testy-wydajnosci", "Testy wydajności")}

CLOCK = "taktowanie bazowe (ok. 2,1 GHz)"
COND_PROFILE = (f"Proces przypięty do jednego rdzenia wydajnościowego (P), {CLOCK}, wysoki priorytet procesu; mediana "
                "z 3 powtórzeń")
COND_PAR = (f"Jeden wątek albo proces na rdzeń wydajnościowy (P), najwyżej 8; {CLOCK}; wysoki priorytet procesu; "
            "warianty mierzone na przemian, mediana z co najmniej 5 powtórzeń; każdy przebieg porównany bitowo "
            "z wariantem odniesienia")
COND_GCC = ("GCC działa w WSL 2 (Linux w maszynie wirtualnej): procesory są wirtualne i nie ma gwarancji, że to rdzenie "
            "wydajnościowe, więc wyniki GCC służą tylko do porównania")
NBSP = " "


# ---------------------------------------------------------------------------
# Odczyt plików (każdy przeczytany plik trafia na listę źródeł)
# ---------------------------------------------------------------------------
class Sources:
    """Zbiór plików, z których pochodzą dane (ścieżki względem katalogu projektu)."""

    def __init__(self) -> None:
        self.all: set[str] = set()

    def rel(self, path: Path) -> str:
        r = path.relative_to(ROOT).as_posix()
        self.all.add(r)
        return r


SRC = Sources()


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    SRC.rel(path)
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def num(v) -> float | None:
    try:
        return float(v) if v not in (None, "") else None
    except ValueError:
        return None


def r4(v: float | None) -> float | None:
    """Liczba do JSON: 4 cyfry znaczące (mały, stabilny plik; tyle mają mediany w tabelach pomiarów)."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return float(f"{v:.4g}") if v != 0 else 0.0


def parts(prefix: str, folder: Path) -> list[Path]:
    """Części pomiaru <prefix>_cz<N>[litera]_raw.csv — z każdej części ostatnia wersja (jak bench/plot_etap11.py)."""
    best: dict[int, Path] = {}
    for p in sorted(folder.glob(f"{prefix}_cz*_raw.csv")):
        m = re.search(r"_cz(\d+)([a-z]?)_raw\.csv$", p.name)
        if m and (int(m.group(1)) not in best or p.name > best[int(m.group(1))].name):
            best[int(m.group(1))] = p
    return [best[k] for k in sorted(best)]


# ---------------------------------------------------------------------------
# Liczby po polsku (podpowiedzi i etykiety są gotowym tekstem)
# ---------------------------------------------------------------------------
def pl(v: float, d: int = 2) -> str:
    s = f"{v:,.{d}f}".replace(",", " ").replace(".", ",")
    return s.replace(" ", NBSP)


def fnum(v: float | None) -> str:
    """Liczba z dokładnością jak w tabelach pomiarów (3 cyfry znaczące, tysiące ze spacją)."""
    if v is None:
        return "brak"
    a = abs(v)
    if a >= 100:
        return pl(v, 0)
    if a >= 10:
        return pl(v, 1)
    if a >= 1:
        return pl(v, 2)
    return pl(v, 3) if a >= 0.01 else pl(v, 4)


def fms(v: float | None) -> str:
    return "brak" if v is None else f"{fnum(v)}{NBSP}ms"


def fx(v: float) -> str:
    """Mnożnik > 1 bez znaku ×: 215, 3,7, 1,52."""
    return pl(v, 0) if v >= 10 else pl(v, 1) if v >= 2 else pl(v, 2)


def same(r: float) -> bool:
    """Stosunek, który po zaokrągleniu do mnożnika (×1,00) nie jest ani zyskiem, ani stratą."""
    return fx(r if r >= 1 else 1 / r) == fx(1.0)


def gain(before: float | None, after: float | None, more: str = "szybciej", less: str = "wolniej") -> str:
    """Zysk jako przyspieszenie > 1: „×215 szybciej”; strata: „×1,10 wolniej”; ×1,00: „bez zmian”."""
    if not before or not after:
        return ""
    r = before / after
    if same(r):
        return "bez zmian"
    return f"×{fx(r)} {more}" if r >= 1 else f"×{fx(1 / r)} {less}"


def gain_short(before: float | None, after: float | None) -> str:
    """Krótka etykieta słupka na osi przyspieszenia: „×36”; strata: „×1,10 wolniej”; ×1,00: „bez zmian”."""
    if not before or not after:
        return ""
    return fratio(before / after)


def fratio(r: float) -> str:
    """Stosunek czasów przed / po jako mnożnik > 1: „×1,22”, strata „×1,12 wolniej”, ×1,00: „bez zmian”."""
    if same(r):
        return "bez zmian"
    return f"×{fx(r)}" if r >= 1 else f"×{fx(1 / r)} wolniej"


def fs(s: float) -> str:
    """Przyspieszenie w podpowiedzi: „S = 4,99”; poniżej 1 z wyjaśnieniem (wolniej niż na jednym rdzeniu)."""
    return f"S = {pl(s)}" + (" (wolniej niż na 1 rdzeniu)" if s < 1 else "")


def fpct(v: float, d: int = 1) -> str:
    """Procent ze znakiem minus (−), nie dywizem: „−2,3%”."""
    return pl(v, d).replace("-", "−") + "%"


def plural(n: int, one: str, few: str, many: str) -> str:
    """Liczba z rzeczownikiem w poprawnej formie: 1 tabela, 24 tabele, 25 tabel (tysiące ze spacją)."""
    word = one if n == 1 else few if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else many
    return f"{pl(n, 0)} {word}"


def frange(lo: float | None, hi: float | None, f=fnum) -> str:
    return "" if lo is None or hi is None else f" [{f(lo)}–{f(hi)}]"


def reps(n) -> str:
    n = int(float(n))
    return f"{n} powtórzenie" if n == 1 else f"{n} powtórzenia" if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 \
        else f"{n} powtórzeń"


# ---------------------------------------------------------------------------
# Budowanie wykresów
# ---------------------------------------------------------------------------
def rr4(v):
    return [rr4(x) for x in v] if isinstance(v, list) else r4(v)


def series(name: str, role: str, data: list, **kw) -> dict:
    s = {"name": name, "role": role, "data": [rr4(v) for v in data]}
    for k, v in kw.items():
        if v is None:
            continue
        if k in ("lo", "hi"):
            v = [r4(x) for x in v]
        if k == "band":
            v = {"lo": [r4(x) for x in v["lo"]], "hi": [r4(x) for x in v["hi"]]}
        s[k] = v
    return s


def ideal_line(xs: list[float], kind: str) -> dict:
    return series("idealnie: S(p) = p" if kind == "S" else "idealnie: E(p) = 1", "ideal",
                  [[x, x if kind == "S" else 1.0] for x in xs], dash=True, marker="none")


def chart(cid: str, title: str, kind: str, sec: str, section: str, lead: str, conclusion: str, howto: list[str],
          conditions: str, selectors: list | None = None, compilers: list | None = None, sources=None,
          wide: bool = False) -> dict:
    name, dtitle = DOCS[sec]
    c = {"id": cid, "title": title, "kind": kind, "selectors": selectors or [], "compilers": compilers or [],
         "views": {}, "lead": lead, "conclusion": conclusion, "howto": howto, "conditions": conditions,
         "doc": {"pdf": f"{name}.pdf", "title": dtitle, "section": section}, "sources": sorted(set(sources or []))}
    if wide:
        c["wide"] = True
    return c


def sel(sid: str, label: str, options: list[tuple[str, str]]) -> dict:
    return {"id": sid, "label": label, "options": [{"id": a, "label": b} for a, b in options]}


def key(*parts_: str) -> str:
    return "|".join(parts_)


HOW_LOG = "równe odstępy na osi to równe mnożniki: od 1 do 10 jest tyle samo miejsca co od 10 do 100"
HOW_SE = ("S(p) = czas na 1 rdzeniu / czas na p rdzeniach („ile razy szybciej”); E(p) = S(p) / p („jaka część dodanych "
          "rdzeni pracuje użytecznie”, 1,0 = idealnie)")

# Przypadki pomiarów wersji równoległych (ta sama kolejność co bench/zestawienie_e12.py i wykresy w dokumentach).
CASES = [("lava_etna_real", "lawa: Etna, automat frontalny", "lawa"),
         ("lava_duza_3d_front", "lawa: teren testowy 128×128×64, automat frontalny", "lawa"),
         ("lava_duza_3d_full", "lawa: teren testowy 128×128×64, pełny przebieg", "lawa"),
         ("classic_2000x2000_s400_vn", "rozrost ziaren 2000×2000", "classic"),
         ("classic_300x300x300_s100_vn", "rozrost ziaren 300×300×300", "classic"),
         ("mc_cb_2d_1000", "Monte Carlo 1000×1000 (szachownica)", "mc"),
         ("mc_cb_3d_100", "Monte Carlo 100×100×100 (szachownica)", "mc")]
CASE_LABEL = {c: lbl for c, lbl, _ in CASES}
CASE_SHORT = {"lava_etna_real": "Etna", "lava_duza_3d_front": "lawa 3D, frontalny", "lava_duza_3d_full": "lawa 3D, pełny",
              "classic_2000x2000_s400_vn": "rozrost 2000×2000", "classic_300x300x300_s100_vn": "rozrost 300×300×300",
              "mc_cb_2d_1000": "Monte Carlo 1000×1000", "mc_cb_3d_100": "Monte Carlo 100×100×100"}
CASE_TILE = {"lava_etna_real": "Lawa: Etna", "classic_300x300x300_s100_vn": "Rozrost ziaren 300×300×300",
             "mc_cb_2d_1000": "Monte Carlo 1000×1000", "mc_cb_3d_100": "Monte Carlo 100×100×100"}
GROUPS = [("lawa", "lawa"), ("classic", "rozrost ziaren"), ("mc", "Monte Carlo")]
ROLES = ["s1", "s2", "s3"]
MARKERS = ["circle", "rect", "triangle"]
NEIGH = ("Rozrost ziaren i Monte Carlo 2D: sąsiedztwo von Neumanna (4 sąsiadów), Monte Carlo 3D: sąsiedztwo Moore'a "
         "(26 sąsiadów).")


def group_cases(g: str) -> list[str]:
    return [c for c, _, gg in CASES if gg == g]


def variant_name(v: str) -> str:
    """Nazwa wariantu z bench/zestawienie_e12.py po polsku, bez skrótów (np. „MPI 7, typy pochodne”)."""
    m = re.fullmatch(r"MPI (\d+) proces(?:y|ów)? \(bez procesora 0\)", v)
    if m:
        return f"MPI, {m.group(1)} procesów bez procesora 0"
    m = re.fullmatch(r"MPI (\d+), typy pochodne", v)
    if m:
        return f"MPI, {procs_word(int(m.group(1)))}, typ pochodny MPI"
    m = re.fullmatch(r"MPI (\d+), changed", v)
    if m:
        return f"MPI, {procs_word(int(m.group(1)))}, wymiana tylko zmienionych warstw"
    m = re.fullmatch(r"hybryda (\d+) × (\d+)", v)
    if m:
        return f"tryb hybrydowy: {procs_word(int(m.group(1)))} × {m.group(2)} wątki"
    m = re.fullmatch(r"MPI (\d+) proces\w*", v)
    if m:
        return f"MPI, {procs_word(int(m.group(1)))}"
    return v


def procs_word(p: int) -> str:
    return f"{p} proces" if p == 1 else f"{p} procesy" if 2 <= p <= 4 else f"{p} procesów"


def version_name(stage: str, variant: str) -> str:
    if "typ pochodny" in variant_name(variant) or stage == "11":
        return "wersja MPI (typy MPI)"
    return {"8": "optymalizacja sekwencyjna", "9": "wersja OpenMP", "10": "wersja MPI"}.get(stage, "")


# Krótkie nazwy przypadków do ciasnych miejsc (tabela, podpisy osi): 1000² = siatka 1000×1000, 300³ = 300×300×300
# (zapis wyjaśniony w „Pojęciach”).
CASE_TABLE = {"lava_etna_real": "lawa: Etna", "lava_duza_3d_front": "lawa 128²×64, frontalny",
              "lava_duza_3d_full": "lawa 128²×64, pełny przebieg", "classic_2000x2000_s400_vn": "rozrost ziaren 2000²",
              "classic_300x300x300_s100_vn": "rozrost ziaren 300³", "mc_cb_2d_1000": "Monte Carlo 1000²",
              "mc_cb_3d_100": "Monte Carlo 100³"}
CASE_AXIS = {"lava_etna_real": ["Etna"], "lava_duza_3d_front": ["lawa 3D,", "frontalny"],
             "lava_duza_3d_full": ["lawa 3D,", "pełny"], "classic_2000x2000_s400_vn": ["rozrost", "2000²"],
             "classic_300x300x300_s100_vn": ["rozrost", "300³"], "mc_cb_2d_1000": ["Monte Carlo", "1000²"],
             "mc_cb_3d_100": ["Monte Carlo", "100³"]}


# ---------------------------------------------------------------------------
# Nagłówek: zgodność bitowa (pliki zgodnosc_*.md i kolumna identical pomiarów)
# ---------------------------------------------------------------------------
def compat() -> dict:
    files = sorted(p for p in RES.glob("*/zgodnosc_*.md") if "_cz" not in p.name)
    configs_max, rows_ok, rows_all, cells_ok, cells_all = 0, 0, 0, 0, 0
    threads, procs, compilers = {1}, {1}, set()
    srcs = []
    for p in files:
        text = p.read_text(encoding="utf-8")
        srcs.append(SRC.rel(p))
        progs = {}
        line = next((ln for ln in text.splitlines() if ln.startswith("Programy:")), "")
        for m in re.finditer(r"`([\w.]+)` = (.*?)(?=, `[\w.]+` = |; nadpisania|$)", line):
            d = m.group(2)
            pm = re.search(r"mpiexec[^`]*?-n (\d+)", d)
            tm = re.search(r"--threads (\d+)", d)
            progs[m.group(1)] = {"gcc": "wsl:" in d, "procs": int(pm.group(1)) if pm else None,
                                 "threads": int(tm.group(1)) if tm else 1}
        lines = [ln for ln in text.splitlines() if ln.startswith("| ")]
        if not lines:
            continue
        head = [c.strip() for c in lines[0].strip("|").split("|")]
        body = [ln for ln in lines[1:] if ln.startswith("| `")]  # wiersze configów (separator „|---|” nie zaczyna się od „| ”)
        cols = [(i, h.split(" = ")[0]) for i, h in enumerate(head) if " = " in h]
        ok = 0
        for ln in body:
            cells = [c.strip() for c in ln.strip("|").split("|")]
            vals = [cells[i] for i, _ in cols]
            cells_all += len(vals)
            cells_ok += sum(v == "tak" for v in vals)
            ok += all(v == "tak" for v in vals)
        rows_all += len(body)
        rows_ok += ok
        configs_max = max(configs_max, len(body))
        for _, lbl in cols:
            pr = progs.get(lbl) or progs.get(lbl.split(" ")[0])
            if not pr:
                continue
            compilers.add("gcc" if pr["gcc"] else "msvc")
            threads.add(pr["threads"])
            if pr["procs"]:
                procs.add(pr["procs"])

    # Pomiary: każde powtórzenie porównane bitowo z wariantem odniesienia (kolumna identical, n — liczba powtórzeń).
    runs, bad = 0, 0
    meas = [RES / "omp" / f"skalowanie_{c}.csv" for c in COMPILERS] + \
           [RES / "omp" / f"harmonogramy_{c}.csv" for c in COMPILERS] + \
           [RES / "mpi" / f"skalowanie_mpi_{c}.csv" for c in COMPILERS]
    for p in meas:
        for r in read_csv(p):
            n = int(num(r.get("n")) or 0)
            runs += n
            bad += n if r.get("identical") != "True" else 0
            if r.get("threads"):
                threads.add(int(float(r["threads"])))
            if r.get("procs"):
                procs.add(int(float(r["procs"])))
    io_raw = sorted((RES / "mpi_io").glob("pomiar_*_cz*_raw.csv")) + sorted((RES / "mpi_io").glob("pomiar_*romio_raw.csv"))
    for p in io_raw:
        for r in read_csv(p):
            runs += 1
            bad += r.get("identical") != "True"
    srcs += [p.relative_to(ROOT).as_posix() for p in meas + io_raw if p.exists()]
    rng = lambda s: f"{min(s)}–{max(s)}"  # noqa: E731
    all_ok = rows_ok == rows_all and bad == 0
    return {
        "principle": "Wynik symulacji jest bitowo ten sam przy każdej liczbie wątków i procesów",
        "allOk": all_ok,
        "badges": [
            {"text": f"{configs_max if all_ok else rows_ok}/{configs_max} konfiguracji",
             "title": f"Każdy z {configs_max} przykładowych plików konfiguracji policzony każdą wersją programu "
                      f"(optymalizacje, OpenMP, MPI, typy MPI i MPI-IO) i porównany bajt po bajcie: "
                      f"{plural(len(files), 'tabela', 'tabele', 'tabel')} zgodności, {pl(cells_ok, 0)} z "
                      f"{pl(cells_all, 0)} porównań zgodnych"},
            {"text": f"{rng(threads)} wątków", "title": "Liczby wątków w porównaniach: " + ", ".join(map(str, sorted(threads)))},
            {"text": f"{rng(procs)} procesów", "title": "Liczby procesów MPI w porównaniach: " + ", ".join(map(str, sorted(procs)))},
            {"text": " i ".join({"msvc": "MSVC", "gcc": "GCC"}[c] for c in ("msvc", "gcc") if c in compilers),
             "title": "Te same pliki wynikowe z kompilatora MSVC (Windows) i GCC (Linux w WSL)"},
            {"text": f"{plural(runs, 'przebieg pomiarowy', 'przebiegi pomiarowe', 'przebiegów pomiarowych')}, "
                     f"{plural(bad, 'różnica', 'różnice', 'różnic')}",
             "title": "Każde powtórzenie pomiarów skalowania, harmonogramów, MPI i MPI-IO porównane bitowo z wynikiem "
                      "odniesienia"},
        ],
        "cells": {"ok": cells_ok, "all": cells_all}, "runs": runs, "runsDifferent": bad,
        "threads": sorted(threads), "procs": sorted(procs), "sources": sorted(set(srcs)),
    }


# ---------------------------------------------------------------------------
# Pojęcia (rozwijany słowniczek na górze zakładki)
# ---------------------------------------------------------------------------
GLOSSARY = [
    ("Przyspieszenie S(p)", "S(p) = T(1) / T(p): ile razy krócej trwa obliczenie na p rdzeniach niż na jednym. T(1) "
                            "zawsze z tej samej sesji pomiarowej co T(p)."),
    ("Efektywność E(p)", "E(p) = S(p) / p: jaka część dodanych rdzeni pracuje użytecznie. 1,0 = idealnie, 0,5 = połowa "
                         "mocy obliczeniowej się marnuje."),
    ("Skalowanie silne", "Ten sam problem liczony na coraz większej liczbie rdzeni. Ogranicza je część programu, która "
                         "zostaje sekwencyjna (prawo Amdahla: przy części sekwencyjnej f przyspieszenie nie przekroczy 1 / f)."),
    ("Skalowanie słabe, E_w(p)", "Problem rośnie razem z liczbą rdzeni (p razy większa siatka na p rdzeniach). "
                                 "E_w(p) = T(1) / T(p); 1,0 = czas się nie zmienia (prawo Gustafsona)."),
    ("Faza obliczeń, cały przebieg", "Faza obliczeń to czas samego automatu komórkowego albo samego Monte Carlo. Cały "
                                     "przebieg dodaje wczytanie danych, przygotowanie terenu, statystyki i zapis wyników."),
    ("Lawa, rozrost ziaren, Monte Carlo", "Trzy rodziny przypadków: automat komórkowy spływu lawy (teren testowy albo "
                                          "rzeczywisty teren Etny), klasyczny automat rozrostu ziaren z losowych "
                                          "zarodków i krystalizacja bazaltu metodą Monte Carlo (MC, model Pottsa). "
                                          "Rozmiar siatki: 1000² = 1000×1000 komórek, 300³ = 300×300×300."),
    ("Sąsiedztwo von Neumanna, Moore'a", "Komórki, które reguła bierze pod uwagę: von Neumann to sąsiedzi przez ścianę "
                                         "(4 w 2D, 6 w 3D), Moore także po przekątnej (8 w 2D, 26 w 3D)."),
    ("Automat frontalny", "Liczy w kroku tylko komórki przy granicy (lawa i jej sąsiedzi, brzegi rosnących ziaren). "
                          "Pełny przebieg sprawdza każdą komórkę siatki. Wynik obu trybów jest bitowo ten sam."),
    ("Szachownica (Monte Carlo)", "Komórki dzielone na kolory tak, że sąsiedzi mają różne kolory; najpierw próby we "
                                  "wszystkich komórkach jednego koloru, potem następnego. Komórki jednego koloru można "
                                  "liczyć równolegle. Losowa kolejność to wariant naiwny: próba po próbie w losowych miejscach."),
    ("Harmonogram OpenMP", "Sposób podziału warstw siatki między wątki: static (każdy wątek jeden ciągły pas), static,1 "
                           "(warstwy rozdawane na zmianę), dynamic (wątek bierze następną warstwę, gdy skończy), guided "
                           "(jak dynamic, z malejącymi porcjami). Liczba po przecinku to rozmiar porcji."),
    ("Pas, warstwy brzegowe", "W MPI każdy proces liczy pas kolejnych warstw siatki we własnej pamięci. Warstwy "
                              "brzegowe to kopie warstw sąsiedniego procesu potrzebne regułom na granicy pasa; procesy "
                              "wymieniają je w każdym kroku."),
    ("Tryb hybrydowy", "Procesy MPI, z których każdy ma kilka wątków OpenMP, np. 2 × 4 = 2 procesy po 4 wątki."),
    ("Typ pochodny MPI", "Opis układu danych w pamięci (MPI_Type_create_struct), dzięki któremu MPI wysyła warstwy wprost "
                         "z siatki. Alternatywa to ręczne pakowanie: kopiowanie pól do bufora przed wysłaniem."),
    ("MPI-IO", "Równoległy zapis i odczyt jednego pliku przez wszystkie procesy naraz. Bez MPI-IO proces 0 zbiera cały "
               "wynik i zapisuje go sam."),
    ("Procesor 0", "Procesor logiczny 0 obsługuje przerwania systemu, więc wątek albo proces na nim liczy wolniej. "
                   "Wariant „7 procesów bez procesora 0” omija go."),
    ("Pamięć podręczna D1, L2, L3, chybienie", "D1: pamięć danych 1. poziomu (48 KB na rdzeń), L2: 2 MB na rdzeń, L3: "
                                               "36 MB wspólne dla wszystkich rdzeni. Chybienie: danych nie ma na danym "
                                               "poziomie i trzeba je pobrać z wolniejszego (ostatecznie z pamięci RAM)."),
    ("Taktowanie bazowe i dynamiczne", "Taktowanie dynamiczne: procesor podnosi częstotliwość pod obciążeniem (Intel "
                                       "Turbo Boost, ok. 4,3 GHz na rdzeniu P). Taktowanie bazowe: podwyższanie "
                                       "wyłączone (ok. 2,1 GHz), czasy ok. 2,3× dłuższe, ale stabilniejsze. Przy "
                                       "taktowaniu dynamicznym mierzono tylko kroki k1–k4 optymalizacji sekwencyjnej."),
    ("Rdzenie P i E", "Procesor i9-13900HX ma 8 rdzeni wydajnościowych (P, po 2 procesory logiczne) i 16 "
                      "energooszczędnych (E). Pomiary równoległe używają tylko rdzeni P: jeden wątek albo proces na "
                      "rdzeń, najwyżej 8."),
    ("Mediana z powtórzeń, test A/B", "Każdy wariant mierzono kilka razy na przemian z innymi; mediana jest odporna na "
                                      "pojedyncze zakłócenia, a rozrzut [min–max] jest w podpowiedzi. Test A/B: stary "
                                      "i nowy program na przemian w tych samych warunkach."),
    ("Zgodność bitowa", "Pliki wyników identyczne bajt po bajcie: dowód, że optymalizacja albo zrównoleglenie nie "
                        "zmieniły wyniku symulacji."),
]


# ---------------------------------------------------------------------------
# Zestawienie S / E i łączne przyspieszenie — bench/zestawienie_e12.py
# ---------------------------------------------------------------------------
def zestawienie() -> tuple[dict, dict]:
    import zestawienie_e12 as z

    rows, chain = {}, {}
    for comp in COMPILERS:
        r, c = z.collect(comp)
        rows[comp], chain[comp] = r, c
    for p in [RES / "profile_2026-10-17_przed2.csv", RES / "profile_2026-10-17_po.csv"] + \
             [RES / "omp" / f"skalowanie_{c}.csv" for c in COMPILERS] + \
             [RES / "mpi" / f"skalowanie_mpi_{c}.csv" for c in COMPILERS]:
        SRC.rel(p)
    for c in COMPILERS:
        for p in sorted((RES / "mpi_io").glob(f"pomiar_{c}_cz*_raw.csv")):
            SRC.rel(p)
    return rows, chain


def summary(rows: dict, chain: dict) -> dict:
    srcs = ["bench/results/testy/zestawienie.md", "bench/results/profile_2026-10-17_przed2.csv",
            "bench/results/profile_2026-10-17_po.csv", "bench/results/omp/skalowanie_msvc.csv",
            "bench/results/mpi/skalowanie_mpi_msvc.csv", "bench/results/mpi_io/pomiar_msvc_cz1_raw.csv"]
    SRC.all.add("bench/results/testy/zestawienie.md")
    tiles, best, best_src = {}, {}, set()
    ch = chart("summary_lacznie", "Skąd bierze się łączne przyspieszenie fazy obliczeń", "hbar", "tests", "2.2",
               "W lawie prawie cały zysk dał algorytm, w Monte Carlo szachownica i równoległość.",
               "Automat frontalny liczy tylko brzeg potoku lawy; szachownica lepiej wykorzystuje pamięć podręczną, "
               "a 6–7 rdzeni dzieli pracę.",
               ["Każdy pasek to iloczyn trzech czynników, każdy zmierzony w jednej sesji: algorytm (optymalizacja wersji "
                "sekwencyjnej), szachownica Monte Carlo przy 1 wątku i najlepszy wariant równoległy (OpenMP albo MPI).",
                f"Skala logarytmiczna ({HOW_LOG}), dlatego odcinki czynników układają się jeden za drugim: długość "
                "całego paska odpowiada iloczynowi.",
                "Liczba na końcu paska: łączne przyspieszenie, czyli ile razy krócej trwa faza obliczeń niż w programie "
                "sprzed optymalizacji.",
                "Podpowiedź przy każdym odcinku: czasy przed i po; pod wykresem iloraz czasów wprost (programy mierzone "
                "w różne dni, dlatego trochę inny niż iloczyn)."],
               f"Faza obliczeń (sam automat albo samo Monte Carlo, bez przygotowania i zapisu); {CLOCK}; rdzenie "
               "wydajnościowe (P), najwyżej 8; każdy czynnik to iloraz median z jednej sesji pomiarowej",
               compilers=list(COMPILERS), sources=srcs)
    for comp in COMPILERS:
        cs = chain[comp]
        tiles[comp] = [{
            "label": CASE_TILE.get(c["case"], c["short"]), "value": f"×{pl(c['S_product'], 0)}",
            "parts": " · ".join(x for x in (
                f"algorytm ×{fx(c['S_alg'])}",
                f"szachownica ×{fx(c['S_checkerboard'])}" if c["S_checkerboard"] else "",
                f"{variant_name(c['best'])} ×{fx(c['S_par'])}") if x),
            "detail": f"{fms(c['T_przed'])} → {fms(c['T_best'])} (faza obliczeń, {COMPILERS[comp].split(' /')[0]})",
        } for c in cs]
        labels = [CASE_TILE.get(c["case"], c["short"]) for c in cs]
        lg = lambda v: math.log10(v) if v and v > 0 else 0.0  # noqa: E731
        sa = [lg(c["S_alg"]) for c in cs]
        sc = [lg(c["S_checkerboard"]) if c["S_checkerboard"] else 0.0 for c in cs]
        sp = [lg(c["S_par"]) for c in cs]
        ch["views"][comp] = {
            "labels": labels, "stacked": True,
            "x": {"title": "łączne przyspieszenie fazy obliczeń (skala log.)", "fmt": "pow10", "min": 0, "max": 4},
            "y": {"title": ""},
            "series": [
                series("algorytm (optymalizacja sekwencyjna)", "s1", sa, tips=[
                    f"algorytm ×{fx(c['S_alg'])}: {fms(c['T_przed'])} → {fms(c['T_po'])} (profil przed i po optymalizacji)"
                    for c in cs]),
                series("szachownica Monte Carlo (1 wątek)", "s3", sc, tips=[
                    (f"szachownica ×{fx(c['S_checkerboard'])} względem losowej kolejności prób"
                     + ("" if c["checkerboard_same_session"] else " (dwie sesje)")) if c["S_checkerboard"]
                    else "nie dotyczy" for c in cs]),
                series("równoległość (OpenMP albo MPI)", "s2", sp, tips=[
                    f"{variant_name(c['best'])} ({version_name(c['best_stage'], c['best'])}): ×{fx(c['S_par'])}, "
                    f"czas {fms(c['T_best'])}" for c in cs],
                    labels=[f"×{pl(c['S_product'], 0)}" for c in cs]),
            ],
            "valueFmt": "pow10",
            "foot": [f"{lbl} (iloczyn ×{pl(c['S_product'], 0)}, iloraz wprost ×{pl(c['S_direct'], 0)})"
                     for lbl, c in zip(labels, cs)],
        }
        # Najlepszy wariant dla każdego przypadku (bez kontrolnych przebiegów OpenMP w sesji pomiarów MPI).
        out = []
        for cid, lbl, _ in CASES:
            par = [r for r in rows[comp] if r["case"] == cid and r["stage"] in ("9", "10", "11") and r["S_phase"]
                   and r["cores"] > 1 and "kontrola" not in r["variant"] and "(etap 10)" not in r["variant"]]
            if not par:
                continue
            b = max(par, key=lambda r: r["S_phase"])
            best_src.update(s.strip() for s in b["source"].split(","))
            out.append({"case": CASE_TABLE[cid], "variant": variant_name(b["variant"]),
                        "version": version_name(b["stage"], b["variant"]),
                        "cores": b["cores"], "S": r4(b["S_phase"]), "E": r4(b["E_phase"]), "Stotal": r4(b["S_total"])})
        best[comp] = out
    name, dtitle = DOCS["tests"]
    return {"tiles": tiles, "best": best, "chart": ch,
            "tilesHowto": "Duża liczba: ile razy krócej trwa faza obliczeń niż w programie sprzed optymalizacji. Pod nią "
                          "rozbicie na czynniki (algorytm, szachownica Monte Carlo, najlepszy wariant równoległy); ich "
                          "iloczyn daje dużą liczbę. Najniżej czas przed i po.",
            "bestHowto": ["S fazy: przyspieszenie fazy obliczeń = czas na 1 rdzeniu / czas na p rdzeniach (ta sama sesja "
                          "pomiarowa); E: efektywność = S / liczba rdzeni (1,0 = idealnie).",
                          "S całego przebiegu obejmuje też części sekwencyjne (przygotowanie, statystyki, zapis), "
                          "dlatego jest mniejsze. Pod nazwą wariantu: sekcja zakładki z jego pomiarami.",
                          "Lawa 128²×64: teren testowy 128×128×64. " + NEIGH],
            "bestConditions": f"Faza obliczeń (sam automat albo samo Monte Carlo), najwyżej 8 rdzeni wydajnościowych (P), "
                              f"{CLOCK}",
            "bestSources": sorted(s for s in best_src if s.startswith("bench/results/")),
            "doc": {"pdf": f"{name}.pdf", "title": dtitle, "section": "2.1"}}


# ---------------------------------------------------------------------------
# Sekcja 1: optymalizacja sekwencyjna
# ---------------------------------------------------------------------------
PROFILE_CASES = [("etna_real", "lawa: Etna (rzeczywisty teren)"), ("test_3d", "lawa: teren testowy 3D"),
                 ("classic_1000x1000_s100_vn_per", "rozrost ziaren 1000×1000, von Neumann"),
                 ("classic_1000x1000_s100_moore_per", "rozrost ziaren 1000×1000, Moore"),
                 ("classic_300x300x300_s100_vn_per", "rozrost ziaren 300×300×300, von Neumann"),
                 ("mcfull_1000x1000_vn_mcs100", "Monte Carlo 1000×1000, von Neumann"),
                 ("mcfull_100x100x100_moore_mcs100", "Monte Carlo 100×100×100, Moore")]
AB = RES / "ab"
# Kroki: (krótka nazwa, opis, {kompilator: [(plik, kolumna po, kolumna przed)]}, rodziny, których krok dotyczy,
# miara „zmieniona część programu” dla CA i MC) — jak bench/plot_etap8.py, + k8.
STEPS = [
    ("k1: Monte Carlo bez skoków", "Monte Carlo bez skoku warunkowego: sąsiedzi liczeni sumą porównań zamiast "
     "instrukcji if, energia przed i po zmianie w jednym przejściu.",
     {"msvc": [("ab_k1_mc_msvc", "k1", "przed"), ("ab_k1_ca_msvc", "k1", "przed")],
      "gcc": [("ab_k1_mc_gcc", "k1", "przed"), ("ab_k1_ca_gcc", "k1", "przed")]}, ("mc",), ("caSim", "mcSim")),
    ("k2: ramka w używanych osiach", "Ramka siatki tylko w osiach, których używa sąsiedztwo: siatka 2D nie ma ramki "
     "w trzeciej osi (mniej pamięci, szybsze wypełnianie).",
     {"msvc": [("ab_k2_msvc", "k2", "k1")], "gcc": [("ab_k2_gcc", "k2", "k1")]}, ("ca_lava", "ca_classic", "mc"),
     ("caSim", "mcSim")),
    ("k3: przesunięcia sąsiadów", "Sąsiedzi w automacie przez stałe przesunięcia w tablicy, liczone raz, zamiast wzoru "
     "na indeks w każdej komórce.",
     {"msvc": [("ab_k3_msvc", "k3", "k2")], "gcc": [("ab_k3_gcc", "k3", "k2")]}, ("ca_lava", "ca_classic"),
     ("caSim", "mcSim")),
    ("k4: automat frontalny", "Automat frontalny: w kroku sprawdzane są tylko komórki przy granicy (lawa i jej "
     "sąsiedzi, brzegi ziaren), a nie cała siatka.",
     {"msvc": [("ab_k4_msvc", "k4", "k3")], "gcc": [("ab_k4_gcc", "k4", "k3")]}, ("ca_lava", "ca_classic"),
     ("caSim", "mcSim")),
    ("k5: tańsze statystyki", "Tańsze statystyki Monte Carlo: etykiety ziaren i energia całkowita bez zbędnych "
     "sprawdzeń.",
     {"msvc": [("ab_k5_msvc", "k5", "k4"), ("ab_k5_msvc_ca", "k5", "k4")],
      "gcc": [("ab_k5_gcc", "k5", "k4"), ("ab_k5_gcc_ca", "k5", "k4")]}, ("mc",), ("caSim", "mcStats")),
    ("k6: mniejsze typy danych", "Mniejsze typy danych w siatce: nie mierzono (brak czasu na pomiary).", {}, (), None),
    ("k7: zapis tekstu", "Szybszy zapis plików tekstowych z wynikami (własne formatowanie liczb do bufora).",
     {"msvc": [("ab_k7_msvc", "k7", "k5")], "gcc": [("ab_k7a_gcc", "k7a", "k5")]}, ("ca_lava", "ca_classic", "mc"),
     ("save", "mcSave")),
    ("k8: flagi kompilatora", "Flagi kompilatora pod konkretny procesor (AVX2, -march=native): bez zysku, zostały tylko "
     "jako ustawienia porównawcze.",
     {"msvc": [("ab_k8_msvc", "avx2", "k7")], "gcc": [("ab_k8_gcc", "native", "k7a")]}, ("ca_lava", "ca_classic", "mc"),
     ("caSim", "mcSim")),
]
AB_GROUPS = [("ca_lava", "lawa", "ca"), ("ca_classic", "rozrost ziaren", "camc"), ("mc", "Monte Carlo", "mc")]
AB_CASES = {"lava_etna_real": "Etna", "lava_test_3d": "lawa 3D", "lava_mc_2d_ca": "lawa + krystalizacja 2D",
            "classic_1000x1000_s100_vn": "1000×1000 von Neumann", "classic_1000x1000_s100_moore": "1000×1000 Moore",
            "classic_100x100x100_s10_vn": "100×100×100 von Neumann",
            "classic_100x100x100_s10_moore": "100×100×100 Moore",
            "classic_300x300x300_s100_vn": "300×300×300 von Neumann", "mc_full_2d_200": "200×200",
            "mc_full_2d_1000": "1000×1000", "mc_full_3d_50": "50×50×50", "mc_full_3d_100": "100×100×100",
            "lava_mc_3d": "lawa + krystalizacja 3D"}
FRONT_CASES = [("lava_etna_real", "lawa: Etna"), ("lava_test_3d", "lawa: teren testowy 3D"),
               ("lava_mc_2d_ca", "lawa + krystalizacja 2D (automat)"),
               ("classic_1000x1000_s100_vn", "rozrost ziaren 1000×1000, von Neumann"),
               ("classic_1000x1000_s100_moore", "rozrost ziaren 1000×1000, Moore"),
               ("classic_100x100x100_s10_vn", "rozrost ziaren 100×100×100, von Neumann"),
               ("classic_100x100x100_s10_moore", "rozrost ziaren 100×100×100, Moore"),
               ("classic_300x300x300_s100_vn", "rozrost ziaren 300×300×300, von Neumann")]
METRIC_WORD = {"caSim": "automat", "mcSim": "Monte Carlo", "mcStats": "statystyki Monte Carlo",
               "save": "zapis wyniku automatu", "mcSave": "zapis wyniku Monte Carlo", "total": "cały przebieg"}
# Ta sama miara w podpowiedzi kroku, gdzie przed nią stoi nazwa rodziny („Monte Carlo, faza Monte Carlo”).
STEP_METRIC = {**METRIC_WORD, "caSim": "faza automatu", "mcSim": "faza Monte Carlo"}


def ab_raw_median(name: str, case: str, metric: str, label: str) -> float | None:
    """Mediana z surowych przebiegów testu A/B, gdy tabela median nie ma danej miary dla przypadku (np. zapis lawy)."""
    vals = []
    for p in sorted(AB.glob(f"{name}_*raw.csv")) + sorted(AB.glob(f"{name}_raw.csv")):
        for r in read_csv(p):
            if r["case"] == case and r["label"] == label and num(r.get(metric)) is not None:
                vals.append(num(r[metric]))
    return statistics.median(vals) if vals else None


def section_seq() -> dict:
    charts = []
    # --- czas przed / po (profil) ---
    p_przed, p_po = RES / "profile_2026-10-17_przed2.csv", RES / "profile_2026-10-17_po.csv"
    przed, po = read_csv(p_przed), read_csv(p_po)
    c1 = chart("seq_przed_po", "Czas przed i po optymalizacji sekwencyjnej", "hbar", "seq", "4",
               "Automat frontalny skrócił lawę Etny z 32 s do 0,15 s, ponad 200 razy.",
               "Lawa zajmuje ułamek siatki, a pełny przebieg sprawdzał w każdym kroku wszystkie 1,8 mln komórek. "
               "Rozrost ziaren zyskał 7–17×, Monte Carlo 1,4–2×.",
               [f"Oś pozioma: czas w milisekundach, skala logarytmiczna ({HOW_LOG}); dzięki niej na jednym wykresie "
                "mieszczą się 0,1 s i 30 s.",
                "Szary pasek: program przed optymalizacją, pomarańczowy: po optymalizacji. Liczba przy pasku: ile razy "
                "szybciej działa program po optymalizacji.",
                "Wąsy: najkrótszy i najdłuższy z 3 powtórzeń.",
                "Przełącznik „miara”: cały przebieg programu albo sama faza obliczeń. Rozrost ziaren i Monte Carlo "
                "zapisują tu wynik także jako tekst, więc cały przebieg zawiera też zapis."],
               COND_PROFILE + "; oba programy (przed i po) zmierzone w tej samej sesji",
               [sel("measure", "miara", [("total", "cały przebieg"), ("phase", "faza obliczeń")])], list(COMPILERS),
               sources=[SRC.rel(p_przed), SRC.rel(p_po)])
    for comp in COMPILERS:
        for m in ("total", "phase"):
            labels, a, b, alo, ahi, blo, bhi, ta, tb, ratio = [], [], [], [], [], [], [], [], [], []
            for vid, lbl in PROFILE_CASES:
                ra = next((r for r in przed if r["variant"] == vid and r["build"] == BUILD[comp]), None)
                rb = next((r for r in po if r["variant"] == vid and r["build"] == BUILD[comp]), None)
                if not ra or not rb:
                    continue
                col = "total" if m == "total" else ("mcSim" if vid.startswith("mcfull") else "caSim")
                va, vb = num(ra[f"{col}_ms_med"]), num(rb[f"{col}_ms_med"])
                labels.append(lbl)
                a.append(va), b.append(vb)
                alo.append(num(ra[f"{col}_ms_min"])), ahi.append(num(ra[f"{col}_ms_max"]))
                blo.append(num(rb[f"{col}_ms_min"])), bhi.append(num(rb[f"{col}_ms_max"]))
                ta.append(f"{METRIC_WORD[col]} ({col}): mediana {fms(va)}{frange(alo[-1], ahi[-1])}, {reps(ra['repeats'])}")
                tb.append(f"{METRIC_WORD[col]} ({col}): mediana {fms(vb)}{frange(blo[-1], bhi[-1])}, "
                          f"{reps(rb['repeats'])}; {gain(va, vb)}")
                ratio.append(gain(va, vb))
            c1["views"][key(comp, m)] = {
                "labels": labels, "x": {"title": "czas [ms] (skala log.)", "log": True, "fmt": "ms"}, "y": {"title": ""},
                "series": [series("przed optymalizacją", "before", a, lo=alo, hi=ahi, tips=ta),
                           series("po optymalizacji", "after", b, lo=blo, hi=bhi, tips=tb, labels=ratio)]}
    charts.append(c1)

    # --- kroki k1–k8 (testy A/B: przyspieszenie kroku = czas przed / czas po) ---
    c2 = chart("seq_kroki", "Wpływ każdego kroku optymalizacji", "hbar", "seq", "2",
               "Najwięcej dał automat frontalny (k4): lawa liczy się od kilku do kilkuset razy szybciej.",
               "k1 przyspieszył Monte Carlo 2–4× (MSVC), k7 zapis tekstu 3,7–5,5×. k8 (flagi AVX2 i -march=native) nic "
               "nie dał i nie wszedł do domyślnych ustawień.",
               ["Wiersz = jeden krok optymalizacji. Długość paska = przyspieszenie kroku, czyli czas przed krokiem / "
                "czas po kroku: ×1 = bez zmian, w prawo = szybciej, w lewo = wolniej.",
                "Kolor: rodzina przypadków (lawa, rozrost ziaren, Monte Carlo); pasek to mediana przypadków rodziny, "
                "każdy przypadek osobno jest w podpowiedzi. Brak paska: krok tej rodziny nie dotyczy.",
                f"Skala logarytmiczna ({HOW_LOG}), bo zysk kroku k4 jest o rząd wielkości większy niż pozostałych "
                "kroków.",
                "Przełącznik „miara”: cały przebieg programu albo tylko część, którą zmienia krok (automat dla k2–k4, "
                "Monte Carlo dla k1, statystyki dla k5, zapis dla k7).",
                "Kroki k1–k4 mierzono przy taktowaniu dynamicznym, k5–k8 przy bazowym. Stosunki czasów można zestawiać, "
                "bo oba programy testu A/B działały w tych samych warunkach; czasów bezwzględnych z obu grup nie łączymy."],
               "Testy A/B: stary i nowy program na przemian, przypięte do jednego rdzenia wydajnościowego (P), mediana "
               "z 5–11 powtórzeń, zgodność bitowa po każdym powtórzeniu; kroki k1–k4 przy taktowaniu dynamicznym, "
               "k5–k8 przy bazowym", [sel("measure", "miara", [("total", "cały przebieg"),
                                                               ("part", "zmieniona część programu")])],
               list(COMPILERS), wide=True)
    c2["steps"] = [{"k": s[0].split(":")[0], "text": s[1]} for s in STEPS]
    labels = ["Kroki k1–k4, taktowanie dynamiczne"] + [s[0] for s in STEPS[:4]] + \
             ["Kroki k5–k8, taktowanie bazowe"] + [s[0] for s in STEPS[4:]]
    headers = [0, 5]
    for comp in COMPILERS:
        for m in ("total", "part"):
            vals = {g: [None] * len(labels) for g, _, _ in AB_GROUPS}
            tips = {g: [""] * len(labels) for g, _, _ in AB_GROUPS}
            labs = {g: [""] * len(labels) for g, _, _ in AB_GROUPS}
            notes = [None] * len(labels)
            for si, (short, _, files, groups, part) in enumerate(STEPS):
                row = si + 1 if si < 4 else si + 2
                if short.startswith("k6"):
                    notes[row] = "nie mierzono (brak czasu na pomiary)"
                    continue
                if short.startswith("k8"):
                    notes[row] = "bez zysku (×1,0), tylko ustawienia porównawcze"
                seen: dict[str, tuple] = {}
                for name, bcol, acol in files.get(comp, []):
                    path = AB / f"{name}.csv"
                    rows = read_csv(path)
                    for case in sorted({r["case"] for r in rows}):
                        grp = next(r["group"] for r in rows if r["case"] == case)
                        if case in seen or grp not in groups:
                            continue
                        metric = "total" if m == "total" else part[1 if grp == "mc" else 0]
                        r = next((x for x in rows if x["case"] == case and x["metric"] == metric), None)
                        va = num(r.get(f"{acol}_med")) if r else ab_raw_median(name, case, metric, acol)
                        vb = num(r.get(f"{bcol}_med")) if r else ab_raw_median(name, case, metric, bcol)
                        if va and vb:
                            seen[case] = (grp, va / vb, metric, name)
                for g, glbl, _ in AB_GROUPS:
                    rs = sorted((AB_CASES.get(c, c), v[1], v[2], v[3]) for c, v in seen.items() if v[0] == g)
                    if not rs:
                        continue
                    sp = [x[1] for x in rs]
                    med = statistics.median(sp)
                    vals[g][row] = med
                    labs[g][row] = ("" if short.startswith("k8") else "bez zmian" if 1 / 1.03 <= med <= 1.03
                                    else f"×{fx(med)}" if med >= 1 else f"×{fx(1 / med)} wolniej")
                    mets = sorted({STEP_METRIC[x[2]] for x in rs})
                    tips[g][row] = (f"{glbl}, {', '.join(mets)}: mediana {fratio(med)}, rozrzut przypadków od "
                                    f"{fratio(min(sp))} do {fratio(max(sp))}; "
                                    + "; ".join(f"{c} {fratio(v)}" for c, v, _, _ in rs))
                    c2["sources"].append(f"bench/results/ab/{rs[0][3]}.csv")
            c2["views"][key(comp, m)] = {
                "labels": labels, "headers": headers, "barThickness": 9,
                "x": {"title": "przyspieszenie kroku: czas przed / czas po (skala log.)", "log": True, "fmt": "times",
                      "min": 0.8, "max": 100, "base": 1},
                "y": {"title": ""},
                "series": [series(lbl, role, vals[g], tips=tips[g], labels=labs[g]) for g, lbl, role in AB_GROUPS],
                "hlines": [{"y": 1, "label": "×1 = bez zmian"}], "rowNotes": notes}
    c2["sources"] = sorted(set(c2["sources"]))
    charts.append(c2)

    # --- front vs pełny przebieg (k4) ---
    c3 = chart("seq_front_full", "Automat frontalny vs pełny przebieg (ten sam program)", "hbar", "seq", "3.4",
               "Automat frontalny liczy tylko komórki, które mogą się zmienić, a wynik jest bitowo ten sam co przy "
               "pełnym przebiegu.",
               "W lawie to ułamek procenta siatki (Etna ok. 250× szybciej); w rozroście ziaren automat frontalny "
               "obejmuje granice wszystkich rosnących ziaren, więc zysk jest mniejszy (3–10×).",
               [f"Oś pozioma: czas samego automatu w milisekundach, skala logarytmiczna ({HOW_LOG}).",
                "Szary pasek: pełny przebieg (każda komórka siatki w każdym kroku); pomarańczowy: automat frontalny "
                "(tylko komórki przy granicy lawy albo ziaren). Liczba: ile razy szybciej działa automat frontalny.",
                "Wąsy: najkrótszy i najdłuższy z 7–11 powtórzeń.",
                "Oba tryby to ten sam program przełączany jednym ustawieniem w pliku konfiguracji; pełny przebieg "
                "zostaje w kodzie jako wersja odniesienia."],
               "Test A/B przy taktowaniu dynamicznym: oba tryby na przemian w tym samym programie, proces przypięty do "
               "jednego rdzenia wydajnościowego (P), mediana z 7–11 powtórzeń; czas samego automatu",
               compilers=list(COMPILERS))
    for comp in COMPILERS:
        path = AB / f"ab_k4_{comp}_front_full.csv"
        rs = {r["case"]: r for r in read_csv(path) if r["metric"] == "caSim"}
        c3["sources"].append(SRC.rel(path))
        labels, f_, r_, flo, fhi, rlo, rhi, tf, tr, lab = ([] for _ in range(10))
        for cid, lbl in FRONT_CASES:
            r = rs.get(cid)
            if not r:
                continue
            labels.append(lbl)
            vf, vr = num(r["k4_full_med"]), num(r["k4_med"])
            f_.append(vf), r_.append(vr)
            flo.append(num(r["k4_full_min"])), fhi.append(num(r["k4_full_max"]))
            rlo.append(num(r["k4_min"])), rhi.append(num(r["k4_max"]))
            tf.append(f"automat (caSim): {fms(vf)}{frange(flo[-1], fhi[-1])}, {reps(r['k4_full_n'])}")
            tr.append(f"automat (caSim): {fms(vr)}{frange(rlo[-1], rhi[-1])}, {reps(r['k4_n'])}; {gain(vf, vr)}")
            lab.append(gain(vf, vr))
        c3["views"][comp] = {"labels": labels, "x": {"title": "czas samego automatu [ms] (skala log.)", "log": True,
                                                     "fmt": "ms"}, "y": {"title": ""},
                             "series": [series("pełny przebieg", "before", f_, lo=flo, hi=fhi, tips=tf),
                                        series("automat frontalny", "after", r_, lo=rlo, hi=rhi, tips=tr, labels=lab)]}
    charts.append(c3)
    # Szeroki wykres kroków na końcu: dwie zwykłe karty stoją wtedy obok siebie, bez pustej połowy wiersza.
    charts[1:] = [c3, c2]
    name, title = DOCS["seq"]
    return {"id": "seq", "title": "Optymalizacja sekwencyjna",
            "intro": "Ta sekcja pokazuje, ile dały zmiany algorytmu i kodu w wersji jednowątkowej, zanim pojawiła się "
                     "równoległość. Każdą zmianę sprawdzono testem A/B (stary i nowy program na przemian), a wynik "
                     "symulacji po każdej został bitowo ten sam.",
            "doc": {"pdf": f"{name}.pdf", "title": title, "section": ""}, "charts": charts}


# ---------------------------------------------------------------------------
# Sekcja 2: OpenMP
# ---------------------------------------------------------------------------
THREADS = [1, 2, 4, 6, 8]


def section_omp() -> dict:
    charts = []
    omp = {c: read_csv(RES / "omp" / f"skalowanie_{c}.csv") for c in COMPILERS}
    c1 = chart("omp_skalowanie", "Przyspieszenie S(p) i efektywność E(p): OpenMP", "line", "omp", "5",
               "Pełny przebieg lawy, rozrost ziaren 2000×2000 i Monte Carlo z szachownicą przyspieszają 6,1–6,7× na "
               "8 wątkach.",
               "Cały przebieg rośnie wolniej (prawo Amdahla): przygotowanie terenu, statystyki ziaren i zapis są "
               "sekwencyjne, w Etnie to ok. 40% czasu.",
               [f"Oś pozioma: liczba wątków p, każdy na osobnym rdzeniu wydajnościowym. Oś pionowa: {HOW_SE}.",
                "Szara linia przerywana: przyspieszenie idealne, S(p) = p (albo E(p) = 1).",
                "Kolor i kształt znacznika: przypadek z wybranej grupy.",
                "Czas „cały przebieg + Amdahl”: cienkie linie przerywane w kolorze przypadku to krzywe prawa Amdahla "
                "dopasowane do udziału części sekwencyjnej f; im większe f, tym niżej krzywa.",
                "Ósmy wątek pracuje na procesorze 0, który obsługuje też przerwania systemu, dlatego zysk z 6 do 8 "
                "wątków jest mniejszy."],
               COND_PAR + "; S = T(1) / T(p) z tej samej sesji",
               [sel("metric", "miara", [("S", "S(p)"), ("E", "E(p)")]), sel("group", "przypadki", GROUPS),
                sel("measure", "czas", [("phase", "faza obliczeń"), ("total", "cały przebieg + Amdahl")])],
               list(COMPILERS), sources=[f"bench/results/omp/skalowanie_{c}.csv" for c in COMPILERS])
    for comp in COMPILERS:
        for metric in ("S", "E"):
            for g, _ in GROUPS:
                for m in ("phase", "total"):
                    ss = []
                    for i, cid in enumerate(group_cases(g)):
                        d = sorted((r for r in omp[comp] if r["case"] == cid), key=lambda r: int(r["threads"]))
                        if not d:
                            continue
                        ph = d[0]["phase"] if m == "phase" else "total"
                        col = f"{metric}_{'phase' if m == 'phase' else 'total'}"
                        pts = [[int(r["threads"]), num(r[col])] for r in d]
                        tips = [f"T({r['threads']}) = {fms(num(r[f'{ph}_med']))}"
                                f"{frange(num(r.get(f'{ph}_min')), num(r.get(f'{ph}_max')))}, {reps(r['n'])}; "
                                f"S = {pl(num(r[col.replace('E_', 'S_')]))}, E = {pl(num(r[col.replace('S_', 'E_')]))}"
                                f"; harmonogram {r['schedule']}{',' + r['chunk'] if r['chunk'] not in ('0', '') else ''}"
                                for r in d]
                        ss.append(series(CASE_LABEL[cid], ROLES[i], pts, marker=MARKERS[i], tips=tips))
                        if m == "total" and metric == "S":
                            f = num(d[0]["amdahl_f_total"])
                            xs = [1 + k * 0.25 for k in range(29)]
                            ss.append(series(f"{CASE_SHORT[cid]}: prawo Amdahla, f = {pl(f, 3)}", ROLES[i],
                                             [[x, 1 / (f + (1 - f) / x)] for x in xs], dash=True, marker="none",
                                             thin=True))
                    ss.insert(0, ideal_line([1, 8], metric))
                    c1["views"][key(comp, metric, g, m)] = {
                        "x": {"title": "liczba wątków p (rdzenie P)", "ticks": THREADS, "min": 1, "max": 8, "fmt": "int"},
                        "y": {"title": "przyspieszenie S(p) = T(1) / T(p)" if metric == "S" else "efektywność E(p) = S(p) / p",
                              "min": 0, "max": 8.5 if metric == "S" else 1.15, "fmt": "num"},
                        "series": ss}
    charts.append(c1)

    # --- harmonogramy przy 8 wątkach ---
    sched = {c: read_csv(RES / "omp" / f"harmonogramy_{c}.csv") for c in COMPILERS}
    cases = [c for c, _, _ in CASES if any(r["case"] == c for r in sched["msvc"])]
    c2 = chart("omp_harmonogramy", "Harmonogramy OpenMP przy 8 wątkach", "hbar", "omp", "6",
               "Najlepszy harmonogram zależy od tego, jak praca rozkłada się po warstwach siatki.",
               "Automat frontalny lawy: static,1 (warstwy na zmianę, bo lawa jest w kilku warstwach); pełny przebieg: "
               "dynamic albo guided; rozrost ziaren 2D: static (dynamic w bibliotece OpenMP kompilatora MSVC 3,7× wolniejszy).",
               ["Pasek = czas fazy obliczeń przy 8 wątkach dla jednego harmonogramu (krócej = lepiej). Pomarańczowy: "
                "najlepszy harmonogram, szare: pozostałe.",
                "Liczba przy pasku: ile razy dłużej niż najlepszy harmonogram.",
                "Harmonogramy: static to jeden ciągły pas warstw na wątek, static,1 to warstwy rozdawane na zmianę, "
                "dynamic to następna warstwa dla wątku, który skończył, guided działa jak dynamic z malejącymi porcjami; "
                "liczba po przecinku to rozmiar porcji (np. dynamic,4 = po 4 warstwy).",
                "Wąsy: najkrótszy i najdłuższy z powtórzeń. GCC: porównanie harmonogramów tylko dla lawy."],
               COND_PAR + "; czas fazy obliczeń przy 8 wątkach",
               [sel("case", "przypadek", [(c, CASE_LABEL[c]) for c in cases])], list(COMPILERS),
               sources=[f"bench/results/omp/harmonogramy_{c}.csv" for c in COMPILERS])
    for comp in COMPILERS:
        for cid in cases:
            d = [r for r in sched[comp] if r["case"] == cid]
            if not d:
                continue
            best = min(num(r["phase_med"]) for r in d)
            c2["views"][key(comp, cid)] = {
                "labels": [r["variant"] for r in d],
                "x": {"title": "czas fazy obliczeń przy 8 wątkach [ms]", "fmt": "ms", "min": 0},
                "y": {"title": ""},
                "series": [series("czas fazy (mediana)", "muted", [num(r["phase_med"]) for r in d],
                                  lo=[num(r["phase_min"]) for r in d], hi=[num(r["phase_max"]) for r in d],
                                  roles=["after" if num(r["phase_med"]) == best else "muted" for r in d],
                                  labels=["najlepszy" if num(r["phase_med"]) == best else f"×{pl(num(r['rel_best']), 2)} dłużej"
                                          for r in d],
                                  tips=[f"mediana {fms(num(r['phase_med']))}{frange(num(r['phase_min']), num(r['phase_max']))}"
                                        f", {reps(r['n'])}; " + ("najlepszy" if num(r["phase_med"]) == best else
                                                                 f"×{pl(num(r['rel_best']), 2)} dłużej niż najlepszy")
                                        for r in d])],
                "legend": [{"role": "after", "label": "najlepszy harmonogram"},
                           {"role": "muted", "label": "pozostałe"}]}
    charts.append(c2)

    # --- praca wątków (lawa): static vs inny harmonogram ---
    c3 = chart("omp_watki", "Nierównomierność pracy wątków w lawie (8 wątków)", "bar", "omp", "6",
               "Przy równych pasach (static) środkowe wątki dostają całą pracę, bo lawa jest skupiona w kilku warstwach.",
               "W Etnie najwolniejszy wątek pracuje 3,2 razy dłużej niż przeciętny; przy przydziale na zmianę (static,1) "
               "praca rozkłada się prawie równo (1,2).",
               ["Para słupków = jeden wątek; pod nią numer wątku i procesor logiczny, na którym pracował.",
                "Wysokość: łączny czas pracy wątku w fazie (suma po krokach), bez czekania na pozostałe wątki.",
                "Niebieski: harmonogram static (równe ciągłe pasy), pomarańczowy: harmonogram wybrany przełącznikiem.",
                "Nierówność (w legendzie) = suma po krokach najdłuższego czasu wątku / suma średniego czasu; 1,0 = "
                "wszyscy pracują tyle samo, 3,2 = najwolniejszy pracuje ponad 3 razy dłużej, a reszta na niego czeka."],
               f"Osobny przebieg dla każdego harmonogramu z licznikami pracy wątków (poza pomiarem czasu); {CLOCK}; "
               "8 wątków na rdzeniach wydajnościowych (P)",
               [sel("case", "przypadek", [(c, CASE_LABEL[c]) for c in group_cases("lawa")]),
                sel("schedule", "porównaj ze static", [(s, s) for s in ("static,1", "dynamic", "guided", "dynamic,4", "guided,4")])],
               list(COMPILERS))
    for comp in COMPILERS:
        path = RES / "omp" / f"harmonogramy_{comp}_threads.json"
        if not path.exists():
            continue
        c3["sources"].append(SRC.rel(path))
        stats = json.loads(path.read_text(encoding="utf-8"))
        for cid in group_cases("lawa"):
            for s in ("static,1", "dynamic", "guided", "dynamic,4", "guided,4"):
                a, b = stats.get(f"{cid}|static"), stats.get(f"{cid}|{s}")
                if not a or not b:
                    continue
                ca, cb = a["stats"]["ca"], b["stats"]["ca"]
                cpus = ca.get("cpus") or [[]] * len(ca["threadWorkMs"])
                labels = [[f"wątek {t}", f"proc. {c[0]}"] if c else [f"wątek {t}"] for t, c in enumerate(cpus)]
                c3["views"][key(comp, cid, s)] = {
                    "labels": labels, "x": {"title": "wątek i procesor logiczny"},
                    "y": {"title": "czas pracy wątku [ms] (suma kroków)", "fmt": "ms", "min": 0},
                    "series": [series(f"static: nierówność {pl(ca['imbalance'])}", "s1", ca["threadWorkMs"],
                                      tips=[f"static: {fms(v)} pracy wątku" for v in ca["threadWorkMs"]]),
                               series(f"{s}: nierówność {pl(cb['imbalance'])}", "s2", cb["threadWorkMs"],
                                      tips=[f"{s}: {fms(v)} pracy wątku" for v in cb["threadWorkMs"]])],
                    "note": f"Czas fazy w tym przebiegu: static {fms(a['phaseMs'])}, {s} {fms(b['phaseMs'])}"}
    charts.append(c3)

    # --- walidacja szachownicy MC ---
    path = RES / "omp" / "mc_walidacja.csv"
    val = read_csv(path)
    vcases = [("2d_vn_kT0", "2D 200×200, von Neumann, kT = 0"),
              ("3d_moore_kT0", "3D 50×50×50, Moore, kT = 0"),
              ("2d_vn_kT03", "2D 200×200, von Neumann, kT = 0,3")]
    seeds = len({r["seed"] for r in val})
    c4 = chart("omp_walidacja", "Szachownica vs losowa kolejność prób Monte Carlo", "line", "omp", "3.2",
               "Szachownica daje inny przebieg losowy, ale ziarna rosną tak samo, więc wynik jest poprawny.",
               "W 2D tempo wzrostu ziaren (wykładnik) jest identyczne, a liczba ziaren różni się o 1–2%. Przy 1 wątku "
               "szachownica jest 3,3–4× szybsza, bo przechodzi komórki po kolei zamiast skakać po losowych adresach.",
               ["Oś pozioma: krok Monte Carlo (MCS: w jednym kroku każda komórka dostaje średnio jedną próbę zmiany). "
                "Oś pionowa: liczba ziaren (skala logarytmiczna) albo średnia wielkość ziarna w komórkach. kT w nazwie "
                "przypadku to temperatura modelu: przy kT = 0 przyjmowana jest tylko zmiana, która nie podnosi energii.",
                f"Linia ciągła: losowa kolejność prób (wariant naiwny); przerywana: szachownica. Linia to średnia z {seeds} "
                "przebiegów z różną wartością początkową generatora liczb losowych, jasne pasmo: najmniejsza i "
                "największa wartość.",
                "Dlaczego wynik się różni: to dwa różne procesy losowe. W losowej kolejności ok. 37% komórek nie dostaje "
                "w danym kroku żadnej próby, w szachownicy każda dostaje dokładnie jedną. Poprawność sprawdza się "
                "statystyką: tempo rozrostu ziaren jest to samo.",
                "Szachownica: komórki podzielone na kolory tak, że sąsiedzi mają różne kolory; wszystkie komórki jednego "
                "koloru można liczyć naraz, na wielu wątkach."],
               f"{seeds} przebiegów na tryb, każdy z inną wartością początkową generatora liczb losowych; 100 kroków "
               "Monte Carlo, kompilator MSVC, 1 wątek",
               [sel("case", "przypadek", vcases),
                sel("measure", "wielkość", [("grains", "liczba ziaren"), ("meanGrainSize", "średnia wielkość ziarna")])],
               sources=[SRC.rel(path), "bench/results/omp/mc_walidacja.md"])
    SRC.all.add("bench/results/omp/mc_walidacja.md")
    for cid, _ in vcases:
        for m in ("grains", "meanGrainSize"):
            ss = []
            for i, (mode, lbl) in enumerate((("random", "losowa kolejność prób"), ("checkerboard", "szachownica"))):
                d = [r for r in val if r["case"] == cid and r["mode"] == mode]
                mcs = sorted({int(r["mcs"]) for r in d})
                by = {k: [num(r[m]) for r in d if int(r["mcs"]) == k] for k in mcs}
                mean = [statistics.mean(by[k]) for k in mcs]
                ss.append(series(lbl, ROLES[i], [[k, v] for k, v in zip(mcs, mean)], marker="none", dash=i == 1,
                                 band={"lo": [min(by[k]) for k in mcs], "hi": [max(by[k]) for k in mcs]},
                                 tips=[f"średnia z {len(by[k])} przebiegów: {fnum(statistics.mean(by[k]))}"
                                       f"{frange(min(by[k]), max(by[k]))}" for k in mcs]))
            c4["views"][key(cid, m)] = {
                "x": {"title": "krok Monte Carlo (MCS)", "min": 0, "max": 100, "fmt": "int"},
                "y": {"title": "liczba ziaren (skala log.)" if m == "grains" else "średnia wielkość ziarna [komórki]",
                      "fmt": "num", "log": m == "grains"},
                "series": ss}
    charts.append(c4)
    name, title = DOCS["omp"]
    return {"id": "omp", "title": "OpenMP",
            "intro": "Ta sekcja pokazuje, jak wersja wielowątkowa (OpenMP: wątki dzielą jedną siatkę w pamięci) "
                     "przyspiesza na 1–8 rdzeniach wydajnościowych i od czego zależy zysk: od podziału pracy między wątki "
                     "(harmonogramu) i od kolejności prób Monte Carlo.",
            "doc": {"pdf": f"{name}.pdf", "title": title, "section": ""}, "charts": charts}


# ---------------------------------------------------------------------------
# Sekcja 3: MPI
# ---------------------------------------------------------------------------
def section_mpi(rows: dict) -> dict:
    charts = []
    mpi = {c: read_csv(RES / "mpi" / f"skalowanie_mpi_{c}.csv") for c in COMPILERS}
    srcs = [f"bench/results/omp/skalowanie_{c}.csv" for c in COMPILERS] + \
           [f"bench/results/mpi/skalowanie_mpi_{c}.csv" for c in COMPILERS]
    c1 = chart("mpi_skalowanie", "MPI vs OpenMP przy tej samej liczbie rdzeni", "line", "mpi", "9.5",
               "Siatki o równej pracy w każdej warstwie (rozrost ziaren 2D, Monte Carlo) skalują w MPI prawie liniowo.",
               "7 procesów bez procesora 0 daje 6,7× szybciej, więcej niż OpenMP na 8 wątkach. Lawę ogranicza nierówny "
               "podział pasów; Etna w MPI jest wolniejsza niż jeden proces, bo wymiana warstw trwa dłużej niż sam krok.",
               [f"Oś pozioma: liczba rdzeni (wątków OpenMP albo procesów MPI). Oś pionowa: {HOW_SE}.",
                "Linia przerywana: przyspieszenie idealne S(p) = p. Niebieskie koła: OpenMP; pomarańczowe kwadraty: MPI; "
                "pusty romb: MPI na 7 procesach z pominięciem procesora 0 (obsługuje przerwania systemu); zielony "
                "trójkąt i gwiazdka: tryb hybrydowy (procesy × wątki).",
                "S liczone od czasu jednego wątku albo procesu z tej samej sesji pomiarowej (OpenMP i MPI mierzono "
                "w różnych sesjach). GCC: MPI tylko na 1, 2, 3 i 8 procesach."],
               COND_PAR + "; faza obliczeń",
               [sel("metric", "miara", [("S", "S(p)"), ("E", "E(p)")]),
                sel("case", "przypadek", [(c, CASE_LABEL[c]) for c, _, _ in CASES])], list(COMPILERS), sources=srcs)
    for comp in COMPILERS:
        rr = rows[comp]
        for metric in ("S", "E"):
            col = f"{metric}_phase"
            for cid, _, _ in CASES:
                d = [r for r in rr if r["case"] == cid]
                omp_ = sorted((r for r in d if r["kind"] == "omp" and r["stage"] == "9"), key=lambda r: r["cores"])
                mpi_ = sorted((r for r in d if r["kind"] == "mpi" and r["stage"] == "10" and "changed" not in r["variant"]
                               and r["cores"] != 7), key=lambda r: r["cores"])
                m7 = [r for r in d if r["kind"] == "mpi" and r["stage"] == "10" and r["cores"] == 7]
                hyb = [r for r in d if r["kind"] == "hyb"]
                tip = lambda r: (f"{variant_name(r['variant'])}: czas {fms(r['T_phase'])}; {fs(r['S_phase'])}, "  # noqa: E731
                                 f"E = {pl(r['E_phase'])}")
                ss = [ideal_line([1, 8], metric)]
                if omp_:
                    ss.append(series("OpenMP (wątki)", "s1", [[r["cores"], r[col]] for r in omp_], marker="circle",
                                     tips=[tip(r) for r in omp_]))
                if mpi_:
                    ss.append(series("MPI (procesy)", "s2", [[r["cores"], r[col]] for r in mpi_], marker="rect",
                                     tips=[tip(r) for r in mpi_]))
                if m7:
                    ss.append(series("MPI, 7 procesów bez procesora 0", "s2", [[7, m7[0][col]]], marker="rectRot",
                                     outline=True, line=False, tips=[tip(m7[0])]))
                for h in hyb:
                    two = "2 × 4" in h["variant"]
                    ss.append(series(variant_name(h["variant"]), "s3", [[8, h[col]]], marker="triangle" if two else "star",
                                     line=False, tips=[tip(h)]))
                if len(ss) > 1:
                    c1["views"][key(comp, metric, cid)] = {
                        "x": {"title": "rdzenie P (wątki albo procesy)", "ticks": list(range(1, 9)), "min": 1, "max": 8,
                              "fmt": "int"},
                        "y": {"title": "przyspieszenie fazy S(p)" if metric == "S" else "efektywność fazy E(p)",
                              "min": 0, "max": 8.5 if metric == "S" else 1.15, "fmt": "num"},
                        "series": ss}
    charts.append(c1)

    # --- tryb hybrydowy ---
    configs = [("m8", ["8 × 1", "(samo MPI)"]), ("h4x2", ["4 × 2"]), ("h2x4", ["2 × 4"]), ("o8", ["1 × 8", "(samo OpenMP)"])]
    c2 = chart("mpi_hybryda", "Tryb hybrydowy na 8 rdzeniach: procesy × wątki", "line", "mpi", "9.6",
               "2 procesy po 4 wątki to najlepszy wariant MPI dla lawy i rozrostu ziaren 300×300×300.",
               "Mniej pasów to mniej warstw brzegowych i mniejsza nierównomierność. W rozroście ziaren 2D i Monte Carlo "
               "2D wygrywa samo MPI, w lawie samo OpenMP.",
               ["Oś pozioma: podział 8 rdzeni na procesy MPI × wątki OpenMP w każdym procesie, od samego MPI (8 × 1) "
                "do samego OpenMP (1 × 8). Oś pionowa: przyspieszenie fazy obliczeń S względem 1 procesu.",
                "Linia przerywana: idealnie, S = 8. Kolor i kształt: przypadek z grupy.",
                "GCC: bez wariantu 4 × 2."],
               COND_PAR + "; wszystkie warianty w jednej sesji, S od czasu 1 procesu",
               [sel("group", "przypadki", GROUPS)], list(COMPILERS), sources=srcs[2:])
    for comp in COMPILERS:
        for g, _ in GROUPS:
            ss = []
            for i, cid in enumerate(group_cases(g)):
                vals, tips = [], []
                for v, lbl in configs:
                    r = next((x for x in mpi[comp] if x["case"] == cid and x["variant"] == v), None)
                    vals.append(num(r["S_phase"]) if r else None)
                    tips.append(f"{' '.join(lbl)}: czas {fms(num(r[r['phase'] + '_med']))}, {fs(num(r['S_phase']))}"
                                if r else "brak pomiaru")
                ss.append(series(CASE_LABEL[cid], ROLES[i], vals, marker=MARKERS[i], tips=tips))
            c2["views"][key(comp, g)] = {
                "labels": [lbl for _, lbl in configs], "x": {"title": "procesy MPI × wątki OpenMP na proces"},
                "y": {"title": "przyspieszenie fazy S", "min": 0, "max": 8.5, "fmt": "num"},
                "series": ss, "hlines": [{"y": 8, "label": "idealnie: S = 8"}]}
    charts.append(c2)

    # --- komunikacja ---
    c3 = chart("mpi_komunikacja", "Udział komunikacji w czasie fazy obliczeń", "line", "mpi", "9.7",
               "Sama wymiana warstw brzegowych jest tania; większość czasu komunikacji to czekanie na najwolniejszy pas.",
               "Skok między 7 a 8 procesami to proces na procesorze 0 (przerwania systemu), a nie więcej przesyłanych "
               "bajtów.",
               ["Oś pozioma: liczba procesów. Oś pionowa: udział komunikacji w czasie fazy obliczeń w procentach "
                "(średnia po procesach).",
                "Linia ciągła ze znacznikami: cała komunikacja (wymiana warstw brzegowych i wspólne sumowanie liczników "
                "z czekaniem na pozostałe procesy). Cienka linia przerywana w tym samym kolorze: sama wymiana warstw.",
                "Różnica między liniami to czekanie: proces, który skończył krok, czeka na najwolniejszy pas.",
                "Na klastrze wymiana szłaby przez sieć, więc to dolna granica kosztu komunikacji."],
               COND_PAR + "; udział = (wymiana warstw + MPI_Allreduce z czekaniem) / czas fazy",
               [sel("group", "przypadki", GROUPS)], list(COMPILERS), sources=srcs[2:])
    for comp in COMPILERS:
        for g, _ in GROUPS:
            ss = []
            for i, cid in enumerate(group_cases(g)):
                d = sorted((r for r in mpi[comp] if r["case"] == cid and re.fullmatch(r"m\d+", r["variant"])
                            and int(r["procs"]) > 1), key=lambda r: int(r["procs"]))
                if not d:
                    continue
                ph = [num(r[r["phase"] + "_med"]) for r in d]
                share = [100 * num(r["comm_share"]) for r in d]
                halo = [100 * num(r["haloAvg_med"]) / p for r, p in zip(d, ph)]
                ss.append(series(CASE_LABEL[cid], ROLES[i], [[int(r["procs"]), v] for r, v in zip(d, share)],
                                 marker=MARKERS[i], tips=[f"komunikacja {pl(v, 0)}% fazy; wymiana warstw "
                                                          f"{fms(num(r['haloAvg_med']))} ({pl(h, 0)}%), faza {fms(p)}"
                                                          for r, v, h, p in zip(d, share, halo, ph)]))
                ss.append(series(f"{CASE_SHORT[cid]}: sama wymiana warstw", ROLES[i],
                                 [[int(r["procs"]), v] for r, v in zip(d, halo)], dash=True, marker="none", thin=True))
            c3["views"][key(comp, g)] = {
                "x": {"title": "liczba procesów p", "ticks": [2, 3, 4, 6, 7, 8], "min": 2, "max": 8, "fmt": "int"},
                "y": {"title": "udział w czasie fazy [%]", "min": 0, "max": 100, "fmt": "pct"}, "series": ss}
    charts.append(c3)

    # --- always vs changed ---
    c4 = chart("mpi_changed", "Wymiana warstw: tylko zmienione vs co krok", "bar", "mpi", "9.9",
               "W lawie warstwy brzegowe zmieniają się rzadko, więc wysyłanie tylko zmienionych warstw oszczędza bajty "
               "i czas.",
               "Wysyłane jest 20–57% bajtów, a faza obliczeń Etny jest krótsza o 22%. W rozroście ziaren i Monte Carlo 2D "
               "warstwy zmieniają się prawie w każdym kroku, więc zysku nie ma.",
               ["Wysokość słupka: wariant „tylko zmienione warstwy” jako procent wariantu „wymiana co krok” (100% = bez "
                "różnicy, mniej = oszczędność). Miara: bajty na jedną wymianę albo czas fazy obliczeń.",
                "Kolor: liczba procesów (4 albo 8).",
                "Wariant „tylko zmienione” wysyła warstwę brzegową tylko wtedy, gdy zmieniła się od poprzedniej "
                "wymiany; „wymiana co krok” wysyła wszystkie warstwy brzegowe w każdym kroku. Wynik obu jest bitowo ten "
                "sam.",
                "Pomiar tylko dla MSVC / MS-MPI."],
               COND_PAR + "; oba warianty w tej samej sesji", [sel("measure", "miara",
                                                                     [("bytes", "bajty na wymianę"),
                                                                      ("time", "czas fazy")])],
               ["msvc"], sources=["bench/results/mpi/skalowanie_mpi_msvc.csv"])
    for m in ("bytes", "time"):
        ss = []
        for i, p in enumerate((4, 8)):
            vals, tips = [], []
            for cid, _, _ in CASES:
                a = next((x for x in mpi["msvc"] if x["case"] == cid and x["variant"] == f"m{p}"), None)
                c = next((x for x in mpi["msvc"] if x["case"] == cid and x["variant"] == f"c{p}"), None)
                if not a or not c:
                    vals.append(None), tips.append("")
                    continue
                if m == "bytes":
                    va, vc = num(a["bytesPerExchange_med"]), num(c["bytesPerExchange_med"])
                    tips.append(f"co krok {pl(va / 1e6)} MB, tylko zmienione {pl(vc / 1e6)} MB na wymianę "
                                f"(pominięte warstwy: {pl(num(c['layersSkipped_med']), 0)})")
                else:
                    va, vc = num(a[a["phase"] + "_med"]), num(c[c["phase"] + "_med"])
                    tips.append(f"faza: co krok {fms(va)}, tylko zmienione {fms(vc)} ({gain(va, vc)})")
                vals.append(100 * vc / va)
            ss.append(series(procs_word(p), ROLES[i], vals, tips=tips))
        c4["views"][key("msvc", m)] = {
            "labels": [CASE_AXIS[c] for c, _, _ in CASES], "x": {"title": ""},
            "y": {"title": "tylko zmienione / co krok [%]", "min": 0, "max": 130, "fmt": "pct"}, "series": ss,
            "hlines": [{"y": 100, "label": "co krok = 100%"}]}
    charts.append(c4)

    # --- praca procesów (pasy) i procesor 0 ---
    c5 = chart("mpi_pasy", "Praca każdego procesu (pasa) i procesor 0", "bar", "mpi", "9.8",
               "Pasy MPI mają stałe granice, więc w lawie dolne pasy liczą prawie całą pracę, a krok czeka na "
               "najwolniejszy.",
               "Przy 8 procesach proces na procesorze 0 (przerwania systemu) liczy tę samą pracę o 13–30% dłużej, "
               "dlatego 7 procesów jest szybsze niż 8.",
               ["Słupek = jeden proces; procesy liczą kolejne pasy warstw od dołu siatki. Pod słupkiem: numer procesu "
                "i procesor logiczny, na którym działał.",
                "Wysokość: czas samych obliczeń procesu w fazie (bez wymiany i czekania). Linia przerywana: czas całej "
                "fazy, czyli ile trwało, zanim skończył najwolniejszy proces.",
                "Pomarańczowy słupek: proces na procesorze 0, który obsługuje też przerwania systemu.",
                "Nierówność pasów (pod wykresem) = najdłuższy czas procesu / średni; 1,0 = praca podzielona równo.",
                "GCC (WSL): procesy bez przypięcia do znanych procesorów, tylko 3 i 8 procesów."],
               COND_PAR + "; czas obliczeń procesu w fazie, mediana z powtórzeń",
               [sel("case", "przypadek", [(c, CASE_LABEL[c]) for c, _, _ in CASES]),
                sel("p", "procesy", [("4", "4"), ("7", "7"), ("8", "8")])], list(COMPILERS))
    for comp in COMPILERS:
        files = sorted((RES / "mpi").glob(f"skalowanie_mpi_{comp}_cz*_raw.csv"))
        raw = [r for f in files for r in read_csv(f)]
        c5["sources"] += [f.relative_to(ROOT).as_posix() for f in files]
        for cid, _, _ in CASES:
            for p in ("3", "4", "7", "8"):
                rr = [r for r in raw if r["case"] == cid and r["variant"] == f"m{p}" and r.get("computePerRank")]
                if not rr:
                    continue
                per = [[float(x) for x in str(r["computePerRank"]).split()] for r in rr]
                work = [statistics.median(col) for col in zip(*per)]
                cpus = str(rr[0].get("cpus") or "").split()
                summ = next((x for x in mpi[comp] if x["case"] == cid and x["variant"] == f"m{p}"), None)
                cpu_known = len(cpus) == len(work)
                labels = [[f"proces {k}", f"proc. {cpus[k]}"] if cpu_known else [f"proces {k}"] for k in range(len(work))]
                roles = ["s2" if cpu_known and cpus[k] == "0" else "s1" for k in range(len(work))]
                phase = num(summ[summ["phase"] + "_med"]) if summ else None
                view = {"labels": labels, "x": {"title": "proces (pas od dołu siatki) i jego procesor"},
                        "y": {"title": "czas obliczeń procesu [ms]", "fmt": "ms", "min": 0},
                        "series": [series("czas obliczeń procesu", "s1", work, roles=roles,
                                          tips=[f"{fms(v)} (mediana z {len(per)} przebiegów)" for v in work])],
                        "legend": [{"role": "s1", "label": "proces na rdzeniu P"},
                                   {"role": "s2", "label": "proces na procesorze 0 (przerwania systemu)"}]}
                if phase:
                    view["hlines"] = [{"y": phase, "label": f"czas fazy {fms(phase)}"}]
                if summ:
                    view["note"] = f"Nierówność pasów (najdłuższy / średni czas procesu): {pl(num(summ['imbalance']))}"
                if p == "3":
                    continue  # GCC ma tylko 3 i 8 procesów — w przełączniku 4 / 7 / 8
                c5["views"][key(comp, cid, p)] = view
    c5["sources"] = sorted(set(c5["sources"]))
    charts.append(c5)
    name, title = DOCS["mpi"]
    return {"id": "mpi", "title": "MPI",
            "intro": "Ta sekcja pokazuje wersję rozproszoną (MPI): siatka jest dzielona na pasy warstw, każdy proces ma "
                     "własną pamięć i wymienia z sąsiadami warstwy brzegowe. Porównanie z OpenMP przy tej samej liczbie "
                     "rdzeni, tryb hybrydowy i koszt komunikacji.",
            "doc": {"pdf": f"{name}.pdf", "title": title, "section": ""}, "charts": charts}


# ---------------------------------------------------------------------------
# Sekcja 4: typy pochodne i MPI-IO
# ---------------------------------------------------------------------------
PACK = [("pack_lava_3d_front", "lawa 128×128×64, automat frontalny"), ("pack_lava_3d_full", "lawa 128×128×64, pełny przebieg"),
        ("pack_classic_300", "rozrost ziaren 300×300×300"), ("pack_mc_cb_3d_100", "Monte Carlo 100×100×100 (szachownica)")]
IO = [("io_bin_classic_300", "rozrost ziaren 300×300×300, plik binarny"),
      ("io_txt_classic_300", "rozrost ziaren 300×300×300, plik tekstowy"),
      ("io_bin_classic_2000", "rozrost ziaren 2000×2000, plik binarny"),
      ("io_txt_classic_2000", "rozrost ziaren 2000×2000, plik tekstowy"),
      ("io_bin_lava_3d", "lawa 3D, plik binarny"), ("io_txt_lava_3d", "lawa 3D, plik tekstowy")]
READ = [("read_classic_300", "rozrost ziaren 300×300×300, plik binarny 351 MB"),
        ("read_lava_3d", "lawa 3D, plik binarny 14 MB")]
GATHER = "zebranie na procesie 0"
MPIIO = "równoległy zapis MPI-IO"


def io_med(raw: list[dict]) -> dict:
    groups: dict[tuple[str, str], list[dict]] = {}
    for r in raw:
        groups.setdefault((r["case"], r["variant"]), []).append(r)
    out = {}
    for k, rs in groups.items():
        e = {"n": len(rs)}
        for col in rs[0]:
            vals = [num(x.get(col)) for x in rs]
            vals = [v for v in vals if v is not None]
            if vals and col not in ("procs", "threads", "cores", "rep"):
                e[col] = statistics.median(vals)
                e[col + "_min"], e[col + "_max"] = min(vals), max(vals)
        out[k] = e
    return out


def section_mpiio() -> dict:
    charts = []
    d = RES / "mpi_io"
    raw = {"msvc": [r for f in parts("pomiar_msvc", d) for r in read_csv(f)],
           "gcc": [r for f in parts("pomiar_gcc", d) for r in read_csv(f)],
           "romio": read_csv(d / "pomiar_gcc_romio_raw.csv")}
    medv = {k: io_med(v) for k, v in raw.items()}
    srcs = [f.relative_to(ROOT).as_posix() for f in parts("pomiar_msvc", d) + parts("pomiar_gcc", d)]
    for f in ("pomiar_msvc.md", "pomiar_gcc.md", "pomiar_gcc_romio.md"):
        SRC.all.add(f"bench/results/mpi_io/{f}")

    def get(src, case, var, col):
        e = medv[src].get((case, var))
        return (e.get(col), e.get(col + "_min"), e.get(col + "_max"), e["n"]) if e and col in e else (None, None, None, 0)

    # --- wymiana: manual vs datatype ---
    c1 = chart("io_wymiana", "Wymiana warstw: ręczne pakowanie vs typ pochodny MPI", "bar", "mpiio", "8.2",
               "Typ pochodny opisuje warstwę wprost w siatce, bez kopii do bufora, więc sama wymiana jest krótsza "
               "o 25–50%.",
               "Cała faza zyskuje tylko 0–9%, bo wymiana to mały ułamek kroku; w Monte Carlo zysku nie ma (procesy i tak "
               "czekają na siebie po każdym kolorze szachownicy).",
               ["Oś pozioma: liczba procesów. Oś pionowa (przełącznik „miara”): czas samej wymiany warstw brzegowych "
                "w fazie albo czas całej fazy obliczeń.",
                "Niebieski: ręczne pakowanie (pola komórek kopiowane do bufora i wysyłane); pomarańczowy: typ pochodny "
                "MPI (wskazuje pola w siatce, bez kopii). Liczba nad słupkiem: ile razy szybciej z typem pochodnym.",
                "Wąsy: najkrótszy i najdłuższy przebieg z powtórzeń.",
                "Oba warianty wysyłają te same bajty w tych samych komunikatach. GCC: tylko 8 procesów, bez pełnego "
                "przebiegu lawy."],
               COND_PAR + "; oba warianty na przemian w jednej sesji",
               [sel("case", "przypadek", PACK), sel("measure", "miara", [("halo", "sama wymiana"), ("phase", "cała faza")])],
               list(COMPILERS), sources=srcs)
    for comp in COMPILERS:
        ps = [2, 4, 7, 8] if comp == "msvc" else [8]
        for cid, _ in PACK:
            for m in ("halo", "phase"):
                col = "haloAvg" if m == "halo" else ("mcSim" if "mc_" in cid else "caSim")
                a = [get(comp, cid, f"m{p}", col) for p in ps]
                b = [get(comp, cid, f"m{p}d", col) for p in ps]
                if not any(x[0] for x in a):
                    continue
                c1["views"][key(comp, cid, m)] = {
                    "labels": [procs_word(p) for p in ps], "x": {"title": "liczba procesów"},
                    "y": {"title": ("czas wymiany warstw w fazie [ms]" if m == "halo" else "czas fazy obliczeń [ms]"),
                          "fmt": "ms", "min": 0},
                    "series": [series("ręczne pakowanie", "s1", [x[0] for x in a],
                                      lo=[x[1] for x in a], hi=[x[2] for x in a],
                                      tips=[f"mediana {fms(x[0])}{frange(x[1], x[2])}, {reps(x[3])}" for x in a]),
                               series("typ pochodny MPI", "s2", [x[0] for x in b],
                                      lo=[x[1] for x in b], hi=[x[2] for x in b],
                                      labels=[gain_short(x[0], y[0]) for x, y in zip(a, b)],
                                      tips=[f"mediana {fms(y[0])}{frange(y[1], y[2])}, {reps(y[3])}; "
                                            f"{gain(x[0], y[0]) or 'brak porównania'}" for x, y in zip(a, b)])]}
    charts.append(c1)

    # --- zapis: gather vs MPI-IO ---
    c2 = chart("io_zapis", "Zapis wyniku: zebranie na procesie 0 vs MPI-IO", "bar", "mpiio", "8.4",
               "Zapis jednego pliku na jednym dysku sam się nie zrównolegla; MPI-IO zyskuje, bo znika zbieranie siatki "
               "na procesie 0, a tekst formatuje się równolegle.",
               "Plik tekstowy 300×300×300 przy 8 procesach: 1,8 s → 0,73 s. Małe pliki (do 52 MB) bez zysku.",
               ["Oś pozioma: liczba procesów. Oś pionowa (przełącznik „miara”): czas zapisu, przepustowość zapisu w MB/s "
                "(rozmiar pliku / czas zapisu) albo udział zapisu w czasie całego przebiegu.",
                f"Niebieski: {GATHER} i zapis przez ten proces; pomarańczowy: {MPIIO} (każdy proces pisze swój pas do "
                "wspólnego pliku). Liczba nad słupkiem: ile razy szybciej z MPI-IO.",
                "Czas zapisu liczony od końca obliczeń: kopia pasa bez ramki, przy zebraniu przesłanie do procesu 0, "
                "zapis do zamknięcia pliku.",
                "Wąsy: najkrótszy i najdłuższy przebieg. GCC: tylko 8 procesów, OpenMPI z domyślną implementacją OMPIO."],
               COND_PAR + "; dysk SSD NVMe, zapis do pamięci podręcznej systemu",
               [sel("case", "plik", IO), sel("measure", "miara", [("save", "czas zapisu"), ("mbs", "MB/s"),
                                                                 ("share", "udział w całym przebiegu")])],
               list(COMPILERS), sources=srcs)
    for comp in COMPILERS:
        ps = [1, 2, 4, 8] if comp == "msvc" else [8]
        for cid, lbl in IO:
            kind = "Bin" if "_bin_" in cid else "Txt"
            size = get("msvc", cid, "m1", f"ca{kind}Bytes")[0] or get(comp, cid, "m8", f"ca{kind}Bytes")[0]
            for m in ("save", "mbs", "share"):
                a = [get(comp, cid, f"m{p}", "save") for p in ps]
                b = [get(comp, cid, f"m{p}i", "save") for p in ps]
                if not any(x[0] for x in a):
                    continue
                ta = [get(comp, cid, f"m{p}", "total")[0] for p in ps]
                tb = [get(comp, cid, f"m{p}i", "total")[0] for p in ps]
                if m == "save":
                    va, vb, y = [x[0] for x in a], [x[0] for x in b], {"title": "czas zapisu [ms]", "fmt": "ms", "min": 0}
                elif m == "mbs":
                    va = [size / 1e3 / x[0] if x[0] and size else None for x in a]
                    vb = [size / 1e3 / x[0] if x[0] and size else None for x in b]
                    y = {"title": "przepustowość zapisu [MB/s] = rozmiar / czas", "fmt": "num", "min": 0}
                else:
                    va = [100 * x[0] / t if x[0] and t else None for x, t in zip(a, ta)]
                    vb = [100 * x[0] / t if x[0] and t else None for x, t in zip(b, tb)]
                    y = {"title": "zapis / cały przebieg [%]", "fmt": "pct", "min": 0, "max": 100}
                tip = lambda x, t: (f"zapis {fms(x[0])}{frange(x[1], x[2])}, cały przebieg {fms(t)}, {reps(x[3])}"  # noqa
                                    + (f", plik {pl(size / 1e6, 0)} MB" if size else ""))
                c2["views"][key(comp, cid, m)] = {
                    "labels": [procs_word(p) for p in ps], "x": {"title": "liczba procesów"}, "y": y,
                    "series": [series(GATHER, "s1", va, tips=[tip(x, t) for x, t in zip(a, ta)],
                                      lo=[x[1] for x in a] if m == "save" else None,
                                      hi=[x[2] for x in a] if m == "save" else None),
                               series(MPIIO, "s2", vb, tips=[tip(x, t) for x, t in zip(b, tb)],
                                      lo=[x[1] for x in b] if m == "save" else None,
                                      hi=[x[2] for x in b] if m == "save" else None,
                                      labels=[gain_short(x[0], y_[0]) if m == "save" else "" for x, y_ in zip(a, b)])]}
    charts.append(c2)

    # --- implementacje MPI-IO przy 8 procesach ---
    impls = [("msvc", "MS-MPI (NTFS)"), ("gcc", "OpenMPI OMPIO (ext4)"), ("romio", "OpenMPI ROMIO (ext4)")]
    c3 = chart("io_implementacje", "Implementacja MPI-IO przy 8 procesach", "bar", "mpiio", "8.4",
               "Wybór implementacji MPI-IO zmienia wynik bardziej niż liczba procesów.",
               "W OpenMPI domyślne OMPIO zapisywało tekst 300×300×300 dwa razy wolniej niż ROMIO, a mały plik binarny "
               "wolniej niż zebranie na procesie 0.",
               ["Grupy słupków: biblioteka MPI i system plików (MS-MPI w Windows na NTFS, OpenMPI w WSL na ext4 z jedną "
                "z dwóch implementacji MPI-IO: OMPIO albo ROMIO; ten sam dysk).",
                f"Niebieski: {GATHER}; pomarańczowy: {MPIIO}. Liczba nad słupkiem: ile razy szybciej z MPI-IO.",
                "Wąsy: najkrótszy i najdłuższy przebieg."],
               COND_PAR + "; MSVC / MS-MPI na NTFS, GCC / OpenMPI w WSL na ext4 (ten sam dysk)",
               [sel("case", "plik", IO[:4])], sources=srcs + ["bench/results/mpi_io/pomiar_gcc_romio_raw.csv"])
    SRC.rel(d / "pomiar_gcc_romio_raw.csv")
    for cid, _ in IO[:4]:
        a = [get(s, cid, "m8", "save") for s, _ in impls]
        b = [get(s, cid, "m8i", "save") for s, _ in impls]
        c3["views"][cid] = {
            "labels": [n for _, n in impls], "x": {"title": ""},
            "y": {"title": "czas zapisu przy 8 procesach [ms]", "fmt": "ms", "min": 0},
            "series": [series(GATHER, "s1", [x[0] for x in a], lo=[x[1] for x in a],
                              hi=[x[2] for x in a], tips=[f"zapis {fms(x[0])}{frange(x[1], x[2])}, {reps(x[3])}" for x in a]),
                       series(MPIIO, "s2", [x[0] for x in b], lo=[x[1] for x in b], hi=[x[2] for x in b],
                              labels=[gain_short(x[0], y[0]) for x, y in zip(a, b)],
                              tips=[f"zapis {fms(y[0])}{frange(y[1], y[2])}, {reps(y[3])}" for y in b])]}
    charts.append(c3)

    # --- pamięć procesu 0 ---
    c4 = chart("io_pamiec0", "Szczyt pamięci procesu 0: zebranie wyniku vs MPI-IO", "bar", "mpiio", "8.4",
               "Przy zebraniu proces 0 trzyma cały wynik obok swojego pasa; przy MPI-IO każdy proces pisze swój pas.",
               "Dlatego szczyt pamięci procesu 0 maleje z liczbą procesów: rozrost ziaren 300×300×300 przy 8 procesach "
               "469 MB → 118 MB.",
               ["Oś pionowa: największe zużycie pamięci przez proces 0 w trakcie przebiegu (szczyt zbioru roboczego), "
                "w MB.",
                f"Niebieski: {GATHER}; pomarańczowy: {MPIIO}. Liczba nad słupkiem: ile razy mniej pamięci zajmuje "
                "proces 0 przy MPI-IO.",
                "GCC: tylko 8 procesów."],
               COND_PAR + "; szczyt zbioru roboczego procesu 0 (Windows: PeakWorkingSetSize, Linux: ru_maxrss)",
               [sel("case", "plik", IO)], list(COMPILERS), sources=srcs)
    for comp in COMPILERS:
        ps = [1, 2, 4, 8] if comp == "msvc" else [8]
        for cid, _ in IO:
            a = [get(comp, cid, f"m{p}", "peakRoot") for p in ps]
            b = [get(comp, cid, f"m{p}i", "peakRoot") for p in ps]
            if not any(x[0] for x in a):
                continue
            mb = lambda x: x / 1e6 if x else None  # noqa: E731  (MB = 10⁶ B, jak w tabelach pomiarów MPI-IO)
            c4["views"][key(comp, cid)] = {
                "labels": [procs_word(p) for p in ps], "x": {"title": "liczba procesów"},
                "y": {"title": "szczyt pamięci procesu 0 [MB]", "fmt": "num", "min": 0},
                "series": [series(GATHER, "s1", [mb(x[0]) for x in a], tips=[f"{fnum(mb(x[0]))} MB" for x in a]),
                           series(MPIIO, "s2", [mb(x[0]) for x in b],
                                  labels=[gain(x[0], y[0], "mniej", "więcej") for x, y in zip(a, b)],
                                  tips=[f"{fnum(mb(y[0]))} MB" for y in b])]}
    charts.append(c4)

    # --- odczyt --mc-from ---
    cols = [("msvc", 1), ("msvc", 8), ("gcc", 1), ("gcc", 8)]
    c5 = chart("io_odczyt", "Odczyt wyniku automatu na wejściu Monte Carlo", "bar", "mpiio", "8.5",
               "Przy MPI-IO każdy proces czyta tylko swój pas i tylko 3 tablice potrzebne Monte Carlo (2,6× mniej danych).",
               "Nic nie przechodzi przez proces 0, więc w MSVC odczyt jest 12–27× szybszy.",
               ["Grupy słupków: kompilator i liczba procesów. Oś pionowa: czas odczytu wejścia w ms.",
                "Niebieski: proces 0 czyta cały plik i rozsyła pasy pozostałym (MPI_Scatterv); pomarańczowy: każdy "
                "proces czyta swój pas wprost z pliku (MPI_File_read_at_all). Liczba nad słupkiem: ile razy szybciej.",
                "Wejście to wynik automatu zapisany wcześniej w osobnym przebiegu: Monte Carlo liczy się na gotowym "
                "wyniku, bez ponownego liczenia automatu."],
               COND_PAR + "; plik wejściowy w pamięci podręcznej systemu", [sel("case", "wejście", READ)], sources=srcs)
    for cid, _ in READ:
        a = [get(s, cid, f"m{p}", "readInput") for s, p in cols]
        sc = [get(s, cid, f"m{p}", "scatterMax")[0] or 0.0 for s, p in cols]
        b = [get(s, cid, f"m{p}i", "readInput") for s, p in cols]
        va = [x[0] + s_ if x[0] is not None else None for x, s_ in zip(a, sc)]
        c5["views"][cid] = {
            "labels": [[f"{'MSVC' if s == 'msvc' else 'GCC'},", procs_word(p)] for s, p in cols], "x": {"title": ""},
            "y": {"title": "odczyt wejścia [ms]", "fmt": "ms", "min": 0},
            "series": [series("proces 0 czyta cały plik i rozsyła pasy", "s1", va,
                              tips=[f"odczyt {fms(x[0])} + rozesłanie {fms(s_)}, {reps(x[3])}" for x, s_ in zip(a, sc)]),
                       series("każdy proces czyta swój pas (MPI-IO)", "s2", [x[0] for x in b],
                              labels=[gain_short(v, y[0]) for v, y in zip(va, b)],
                              tips=[f"odczyt {fms(y[0])}{frange(y[1], y[2])}, {reps(y[3])}" for y in b])]}
    charts.append(c5)
    name, title = DOCS["mpiio"]
    return {"id": "mpiio", "title": "Typy MPI i MPI-IO",
            "intro": "Ta sekcja pokazuje dwie opcje wersji MPI: wymianę warstw typem pochodnym MPI zamiast ręcznego "
                     "pakowania oraz równoległy zapis i odczyt pliku (MPI-IO) zamiast zbierania wyniku na procesie 0. "
                     "Pliki wynikowe są bajt w bajt te same we wszystkich wariantach.",
            "doc": {"pdf": f"{name}.pdf", "title": title, "section": ""}, "charts": charts}


# ---------------------------------------------------------------------------
# Sekcja 5: testy wydajności
# ---------------------------------------------------------------------------
WEAK = [("weak_classic_2d", "rozrost ziaren 2000 × 2000·p", "classic_2000x2000_s400_vn"),
        ("weak_mc_cb_2d", "Monte Carlo (szachownica) 1000 × 1000·p", "mc_cb_2d_1000"),
        ("weak_lava_full", "lawa, pełny przebieg 128 × 128·p × 64", "lava_duza_3d_full"),
        ("weak_lava_front", "lawa, automat frontalny 128 × 128·p × 64", "lava_duza_3d_front")]
MEM_CASES = [("classic2d_1000", "1000×1000"), ("classic2d_2000", "2000×2000"), ("classic2d_4000", "4000×4000"),
             ("classic3d_100", "100×100×100"), ("classic3d_200", "200×200×200"), ("classic3d_300", "300×300×300"),
             ("lava3d_64", "64×64×64"), ("lava3d_128", "128×128×64"), ("lava3d_256", "256×256×64"),
             ("etna_real", "Etna (rzeczywisty teren)"), ("mc3d_50", "50×50×50"), ("mc3d_100", "100×100×100"),
             ("mc3d_200", "200×200×200")]
MEM_FAMILY = {"classic2d": ("rozrost ziaren 2D", "circle"), "classic3d": ("rozrost ziaren 3D", "rect"),
              "lava3d": ("lawa 3D", "triangle"), "mc3d": ("Monte Carlo 3D", "rectRot"), "etna": ("lawa: Etna", "star")}
MEM_GROUPS = [("Rozrost ziaren", ("classic2d", "classic3d")), ("Lawa", ("lava3d", "etna")), ("Monte Carlo", ("mc3d",))]
MEM_FAMILY_WORD = {"classic2d": "rozrost ziaren", "classic3d": "rozrost ziaren", "lava3d": "lawa", "etna": "lawa",
                   "mc3d": "Monte Carlo"}
# Pary porównań chybień: (nazwa wiersza, [(przypadek, krótka nazwa punktu)]).
CG_PAIRS = [("lawa, teren testowy 3D", [("lava_front", "frontalny"), ("lava_full", "pełny")]),
            ("Monte Carlo 1000×1000", [("mc_cb_2d", "szachownica"), ("mc_random_2d", "losowo")]),
            ("Monte Carlo 100×100×100", [("mc_cb_3d", "szachownica"), ("mc_random_3d", "losowo")]),
            ("rozrost ziaren 1000×1000", [("classic2d_vn", "von Neumann"), ("classic2d_moore", "Moore")]),
            ("rozrost ziaren 100×100×100", [("classic3d_vn", "von Neumann"), ("classic3d_moore", "Moore")]),
            ("rozrost 1000×1000, układ siatki", [("layout_vector", "wektor"), ("layout_matrix", "macierz")])]
CG_SETS = {
    "classic": ("rozmiar: rozrost ziaren", [("size_classic_256", "256×256 (1,7 MB, mieści się w L2)"),
                                            ("size_classic_1024", "1024×1024 (27 MB, w L3)"),
                                            ("size_classic_2896", "2896×2896 (218 MB, poza L3)")]),
    "mc": ("rozmiar: Monte Carlo losowo", [("size_mc_256", "256×256 (0,8 MB, mieści się w L2)"),
                                           ("size_mc_1024", "1024×1024 (13 MB, w L3)"),
                                           ("size_mc_4096", "4096×4096 (201 MB, poza L3)")]),
    "pas": ("pas MPI vs cała siatka", [("strip_mc_cb_1000x125", "pas 1000×125 przy 8 procesach (1,5 MB)"),
                                       ("strip_mc_cb_1000x1000", "cała siatka 1000×1000 (12 MB)")]),
}
CURVES = [("classic_full", "rozrost ziaren, pełny przebieg (po kolei, 26 B na komórkę)", "ca", 26),
          ("mc_random", "Monte Carlo losowo (12 B na komórkę)", "mc", 12),
          ("mc_cb", "Monte Carlo, szachownica (po kolei w kolorach)", "camc", 12)]
KERNELS = [("triad", "triad (a = b + s·c)", "s1"), ("copy", "copy (a = b)", "s2"), ("odczyt", "sam odczyt", "s3")]
DEMAND = [("weak_classic_2d", "classic2d_vn", "rozrost ziaren 2000 × 16 000 (frontalny)"),
          ("weak_mc_cb_2d", "mc_cb_2d", "Monte Carlo (szachownica) 1000 × 8000"),
          ("weak_lava_full", "lava_full", "lawa, pełny przebieg"), ("weak_lava_front", "lava_front", "lawa, automat frontalny")]
ZERO = 1e-5  # chybienia na komórkę i krok (próbę) poniżej tego progu = 0 (pierwsze dotknięcie pamięci jest poza jądrem)


def cache_sizes() -> dict:
    """L1d / L2 / L3 rdzenia P z bench/results/testy/procesor.md (odczyt z systemu)."""
    path = RES / "testy" / "procesor.md"
    text = path.read_text(encoding="utf-8")
    SRC.rel(path)
    out = {}
    for lvl, typ, size, unit, cores in re.findall(r"^\| (L\d) \| (\w+) \| (\d+) (KB|MB) \| \d+ \| \d+ \| ([\w/]+) \|",
                                                  text, re.M):
        if typ in ("Data", "Unified") and "P" in cores and lvl not in out:
            out[lvl] = int(size) * (1024 if unit == "KB" else 1024 ** 2)
    return out


def cg_per_unit(rows: list[dict]) -> dict[str, dict[str, float]]:
    """Chybienia jądra (funkcje kroku) na jednostkę pracy: CA — komórka × krok, MC — próba (jak bench/plot_etap12.py)."""
    res: dict[str, dict[str, float]] = {}
    for r in rows:
        mc = (num(r.get("mcs")) or 0) > 0
        units = num(r["domainCells"]) * num(r["mcs"]) if mc else num(r["cells"]) * num(r["steps"])
        e = res.setdefault(r["case"], {})
        e["D1"] = num(r["kD1"]) / units
        e[r["ll"]] = num(r["kDL"]) / units
        e["refs"] = num(r["kD"]) / units
        e["desc"] = r["desc"]
        e["unit"] = "na próbę" if mc else "na komórkę i krok"
    return res


def cg_tip(e: dict, v: float | None, name: str = "") -> str:
    """Podpowiedź punktu chybień: „szachownica: 0,034 chybienia na próbę (odwołań do danych: 4,7)”."""
    n = fmiss(v)
    return (f"{name + ': ' if name else ''}{n} {'chybień' if n == '0' else 'chybienia'} {e['unit']} "
            f"(odwołań do danych: {pl(e['refs'], 1)})")


def mem_base(med_: dict) -> tuple[float, dict[int, float]]:
    """Narzut stały procesu (rozrost ziaren 16³): engine z 1 wątkiem i engine_mpi na p procesach — jak bench/plot_etap12.py."""
    o1 = med_.get(("base_tiny", "o1"), {})
    end = num(o1.get("endRss"))
    base_omp = min(num(o1["peakRss"]), end) if end else num(o1.get("peakRss")) or 0.0
    base_mpi = {p: num(med_[("base_tiny", f"m{p}d")]["rssAvg"]) for p in range(1, 9) if ("base_tiny", f"m{p}d") in med_}
    return base_omp, base_mpi


def fmiss(v: float | None) -> str:
    if v is None or v < ZERO:
        return "0"
    return pl(v, 5) if v < 0.0001 else pl(v, 4) if v < 0.01 else pl(v, 3) if v < 1 else pl(v, 2)


def section_tests(rows: dict) -> dict:
    import memory

    charts = []
    T = RES / "testy"
    # --- skalowanie słabe ---
    c1 = chart("t_slabe", "Skalowanie słabe E_w(p) obok silnego E(p)", "line", "tests", "2.4",
               "Gdy siatka rośnie razem z liczbą rdzeni, Monte Carlo i lawa utrzymują efektywność 0,87–1,00, lepiej niż "
               "w skalowaniu silnym.",
               "Rozrost ziaren 2D spada do 0,49: ogranicza go przepustowość pamięci RAM, a nie część sekwencyjna.",
               ["Oś pozioma: liczba rdzeni p. Oś pionowa: efektywność; 1,0 = idealnie.",
                "Linie ze znacznikami: skalowanie słabe, E_w(p) = T(1) / T(p) przy p razy większej siatce (problem rośnie "
                "razem z liczbą rdzeni; 1,0 = czas się nie zmienia). Cienkie linie przerywane: skalowanie silne E(p) "
                "tego samego przypadku przy stałej siatce.",
                "Niebieski: OpenMP; pomarańczowy: MPI (z typami pochodnymi). Szara linia przerywana: idealnie, E = 1.",
                "Przełącznik „E_w z”: z czasu fazy albo z czasu na komórkę i krok. W rozroście ziaren liczba kroków "
                "rośnie z p (199 → 247), dlatego drugi wariant.",
                "MPI lawy: podział siatki w osi z, a siatka rośnie w osi y, więc warstwy brzegowe rosną z p."],
               COND_PAR + "; siatka p razy większa; silne E(p) z pomiarów OpenMP i MPI",
               [sel("case", "przypadek", [(w, lbl) for w, lbl, _ in WEAK]),
                sel("measure", "E_w z", [("phase", "czasu fazy"), ("norm", "czasu na komórkę i krok")])],
               list(COMPILERS), sources=[f"bench/results/testy/slabe_{k}_{c}.csv" for k in ("omp", "mpi") for c in COMPILERS])
    for comp in COMPILERS:
        weak = {k: read_csv(T / f"slabe_{k}_{comp}.csv") for k in ("omp", "mpi")}
        for wid, _, strong in WEAK:
            for m in ("phase", "norm"):
                col = "Ew_phase" if m == "phase" else "Ew_norm"
                ss = [ideal_line([1, 8], "E")]
                for k, lbl, role, mk in (("omp", "OpenMP: słabe E_w(p)", "s1", "circle"),
                                         ("mpi", "MPI: słabe E_w(p)", "s2", "rect")):
                    d = sorted((r for r in weak[k] if r["case"] == wid), key=lambda r: int(r["cores"]))
                    if d:
                        ph = d[0]["phase"]
                        ss.append(series(lbl, role, [[int(r["cores"]), num(r[col])] for r in d], marker=mk,
                                         tips=[f"p = {r['cores']}: {pl(num(r['cells']) / 1e6, 1)} mln komórek, czas "
                                               f"{fms(num(r[ph + '_med']))}{frange(num(r[ph + '_min']), num(r[ph + '_max']))}"
                                               f", {pl(num(r['ns_unit']), 2)} ns na komórkę i krok" for r in d]))
                zs = [r for r in rows[comp] if r["case"] == strong]
                for kind, stage, lbl, role in (("omp", "9", "OpenMP: silne E(p)", "s1"), ("mpi", "10", "MPI: silne E(p)", "s2")):
                    d = sorted((r for r in zs if r["kind"] == kind and r["stage"] == stage and "changed" not in r["variant"]
                                and r["cores"] != 7), key=lambda r: r["cores"])
                    if d:
                        ss.append(series(f"{lbl}, {CASE_SHORT[strong]}", role, [[r["cores"], r["E_phase"]] for r in d],
                                         dash=True, marker="none", thin=True,
                                         tips=[f"{variant_name(r['variant'])}: E = {pl(r['E_phase'])}" for r in d]))
                if len(ss) > 1:
                    c1["views"][key(comp, wid, m)] = {
                        "x": {"title": "rdzenie P (p)", "ticks": [1, 2, 4, 6, 7, 8], "min": 1, "max": 8, "fmt": "int"},
                        "y": {"title": "efektywność", "min": 0, "max": 1.25, "fmt": "num"}, "series": ss}
    charts.append(c1)

    # --- pamięć: wątki vs procesy ---
    medm = {c: memory.med_rows(read_csv(T / f"pamiec_{c}_raw.csv")) for c in COMPILERS}
    c2 = chart("t_pamiec_p", "Pamięć: wątki vs procesy MPI", "line", "tests", "3.3",
               "Wątki dzielą jedną siatkę, więc pamięć prawie się nie zmienia (8 wątków względem 1: 0,96–1,05).",
               "Procesy MPI mają własne kopie pasów z warstwami brzegowymi: rozrost ziaren +0–14%, lawa +71–84% przy "
               "8 procesach (17 warstw pod pasem).",
               ["Oś pozioma: liczba wątków albo procesów. Oś pionowa: pamięć względem 1 wątku albo 1 procesu "
                "(1,0 = bez zmian).",
                "Niebieski: szczyt pamięci procesu z p wątkami; pomarańczowy: suma pamięci danych wszystkich procesów "
                "MPI (bez stałej pamięci samego programu w każdym procesie).",
                "Podpowiedź przy MPI: jaka część pamięci procesów to warstwy brzegowe (kopie warstw sąsiednich pasów).",
                "GCC: 3 przypadki."],
               "Szczyt zbioru roboczego procesu, jeden przebieg na wariant (szczyt jest powtarzalny); dla procesów suma "
               "po procesach minus stała pamięć programu w każdym procesie (zmierzona na siatce 16×16×16); MPI z typami "
               "pochodnymi i zebraniem wyniku",
               [sel("case", "przypadek", [(c, f"{MEM_FAMILY_WORD[next(f for f in MEM_FAMILY if c.startswith(f))]} {lbl}"
                                           if not c.startswith("etna") else f"lawa: {lbl}") for c, lbl in MEM_CASES])],
               list(COMPILERS),
               sources=[f"bench/results/testy/pamiec_{c}_raw.csv" for c in COMPILERS] + ["bench/results/testy/pamiec_msvc.md"])
    SRC.all.add("bench/results/testy/pamiec_msvc.md")
    for comp in COMPILERS:
        med_ = medm[comp]
        if not med_:
            continue
        base_omp, base_mpi = mem_base(med_)
        for cid, lbl in MEM_CASES:
            one = med_.get((cid, "m1d"))
            o1 = med_.get((cid, "o1"))
            if not one or not o1:
                continue
            d1 = num(one["rssAvg"]) - base_mpi.get(1, 0.0)
            pts, tips = [], []
            for p in memory.MPI_PROCS:
                e = med_.get((cid, f"m{p}d"))
                if not e:
                    continue
                data = num(e["rssAvg"]) * p - p * base_mpi.get(p, 0.0)
                mm = memory.mpi_model(e)
                pts.append([p, data / d1])
                tips.append(f"dane {pl(data / 2**20, 0)} MB (suma po procesach)"
                            + (f"; warstwy brzegowe: {pl(100 * mm['haloShare'], 0)}% pamięci pasów" if mm else ""))
            tp, tt = [], []
            for p in (1, 2, 4, 8):
                e = med_.get((cid, f"o{p}"))
                if e:
                    tp.append([p, num(e["peakRss"]) / num(o1["peakRss"])])
                    tt.append(f"szczyt {pl(num(e['peakRss']) / 2**20, 0)} MB")
            c2["views"][key(comp, cid)] = {
                "x": {"title": "wątki albo procesy", "ticks": [1, 2, 3, 4, 8], "min": 1, "max": 8, "fmt": "int"},
                "y": {"title": "pamięć względem 1 wątku albo procesu", "min": 0.8, "fmt": "num"},
                "series": [series("wątki OpenMP: szczyt procesu", "s1", tp, marker="circle", tips=tt),
                           series("procesy MPI: suma danych", "s2", pts, marker="rect", tips=tips)],
                "hlines": [{"y": 1, "label": "bez zmian"}]}
    charts.append(c2)

    # --- model vs pomiar ---
    med_ = medm["msvc"]
    base_omp, base_mpi = mem_base(med_)
    c3 = chart("t_model", "Model pamięci z kodu vs pomiar", "dots", "tests", "3.5",
               "Model liczony z rozmiarów tablic w kodzie trafia w pomiar automatu na jednym wątku z dokładnością 0–6%, "
               "a w sumę po procesach MPI z zebraniem wyniku z dokładnością do 8%.",
               "Większe odchylenia mają znane przyczyny: bufory, których model nie zawiera (zbieranie mapy kryształów "
               "w Monte Carlo, wewnętrzne bufory zapisu MPI-IO; pomiar do 20–29% powyżej modelu, najbardziej w małych "
               "siatkach), oraz zarezerwowana, a nieużywana pamięć statystyk w Monte Carlo 200×200×200 (tu model "
               "zawyża: pomiar jest o 16% mniejszy).",
               ["Widok „błąd modelu w %”: (model − pomiar) / pomiar dla każdego przypadku; 0% = model idealny, wartość "
                "dodatnia = model zawyża. Szare pasmo: ±10%. Wiersze pogrupowane po rodzinie przypadków; w małych "
                "siatkach (kilka MB) już 1 MB różnicy to kilkanaście procent.",
                "Pełne koło: 1 wątek; puste kwadraty: suma po procesach MPI (1–8 procesów, zapis przez zebranie albo "
                "MPI-IO; każdy znacznik to jeden wariant, szczegóły w podpowiedzi).",
                f"Widok „model vs pomiar”: oś pozioma model, pionowa pomiar, obie w MB i w skali logarytmicznej ({HOW_LOG}). "
                "Linia przerywana: pomiar = model, pasmo wokół niej: ±10%. Kolor: tryb (1 wątek albo procesy MPI), "
                "kształt: rodzina przypadków.",
                f"Od pomiaru odjęto stałą pamięć samego programu, niezależną od rozmiaru siatki: {pl(base_omp / 2**20, 1)} MB "
                f"dla programu jednowątkowego i {pl(base_mpi.get(1, 0.0) / 2**20, 1)} MB na każdy proces MPI."],
               "Szczyt zbioru roboczego procesu minus stała pamięć programu; model: model pamięci silnika (1 wątek) "
               "rozszerzony na pasy procesów MPI; kompilator MSVC",
               [sel("view", "widok", [("err", "błąd modelu w %"), ("xy", "model vs pomiar")])], ["msvc"],
               sources=["bench/results/testy/pamiec_msvc_raw.csv"], wide=True)
    pts1, ptsm = {}, {}
    xs, mk, tt, xm, mm_, tm = [], [], [], [], [], []
    for cid, lbl in MEM_CASES:
        fam = next(f for f in MEM_FAMILY if cid.startswith(f))
        full = f"{MEM_FAMILY_WORD[fam]} {lbl}" if fam != "etna" else f"lawa: {lbl}"
        e = med_.get((cid, "o1"))
        if e:
            x, y = num(e["modelPeak"]) / 2**20, (num(e["peakRss"]) - base_omp) / 2**20
            xs.append([x, y]), mk.append(MEM_FAMILY[fam][1])
            tt.append(f"{full}, 1 wątek: model {pl(x, 0)} MB, pomiar {pl(y, 0)} MB")
            pts1[cid] = (100 * (x - y) / y, f"1 wątek: model {pl(x, 0)} MB, pomiar {pl(y, 0)} MB, błąd "
                                            f"{fpct(100 * (x - y) / y)}")
        for p in memory.MPI_PROCS:
            for io in ("d", "di"):
                e = med_.get((cid, f"m{p}{io}"))
                m = memory.mpi_model(e) if e else None
                if m:
                    x, y = m["modelSum"] / 2**20, (num(e["rssAvg"]) * p - p * base_mpi.get(p, 0.0)) / 2**20
                    xm.append([x, y]), mm_.append(MEM_FAMILY[fam][1])
                    how = "MPI-IO" if io == "di" else "zebranie"
                    tm.append(f"{full}, {procs_word(p)}, {how}: model {pl(x, 0)} MB, pomiar {pl(y, 0)} MB")
                    ptsm.setdefault(cid, []).append((100 * (x - y) / y, f"{procs_word(p)}, {how}: model {pl(x, 0)} MB, "
                                                                        f"pomiar {pl(y, 0)} MB, błąd {fpct(100 * (x - y) / y)}"))
    labels, headers, d1, t1, dm, tmm, rtext = [], [], [], [], [], [], []
    for gname, fams in MEM_GROUPS:
        headers.append(len(labels))
        labels.append(gname)
        d1.append(None), t1.append(""), dm.append(None), tmm.append(""), rtext.append("")
        for cid, lbl in MEM_CASES:
            if not cid.startswith(fams):
                continue
            labels.append(lbl)
            d1.append(pts1[cid][0] if cid in pts1 else None)
            t1.append(pts1[cid][1] if cid in pts1 else "")
            ms = ptsm.get(cid, [])
            dm.append([v for v, _ in ms] or None)
            tmm.append([t for _, t in ms] or "")
            rtext.append("model zawyża" if cid == "mc3d_200" else "")
    c3["views"]["msvc|err"] = {
        "kind": "dots", "labels": labels, "headers": headers,
        "x": {"title": "błąd modelu: (model − pomiar) / pomiar [%]", "fmt": "pct", "min": -30, "max": 30},
        "y": {"title": ""},
        "series": [series("1 wątek", "s1", d1, marker="circle", tips=t1),
                   series("suma po procesach MPI", "s2", dm, marker="rect", outline=True, tips=tmm)],
        "xband": {"from": -10, "to": 10, "label": "±10%"}, "vlines": [{"x": 0, "label": ""}], "rowText": rtext,
        "legendRows": [{"label": "znacznik", "items": [{"role": "s1", "label": "1 wątek", "marker": "circle"},
                                                       {"role": "s2", "label": "suma po procesach MPI (jeden wariant)",
                                                        "marker": "rect", "outline": True}]}]}
    c3["views"]["msvc|xy"] = {
        "kind": "scatter",
        "x": {"title": "model [MB] (skala log.)", "log": True, "fmt": "num", "min": 3, "max": 1500},
        "y": {"title": "pomiar bez stałej pamięci programu [MB] (skala log.)", "log": True, "fmt": "num", "min": 3, "max": 1500},
        "series": [series("pomiar = model", "ideal", [[3, 3], [1500, 1500]], dash=True, marker="none",
                          band={"lo": [2.7, 1350], "hi": [3.3, 1650]}),
                   series("1 wątek", "s1", xs, markers=mk, line=False, tips=tt),
                   series("suma po procesach MPI (1–8 procesów)", "s2", xm, markers=mm_, line=False, outline=True, tips=tm)],
        "legendRows": [{"label": "kolor", "items": [{"role": "s1", "label": "1 wątek", "marker": "circle"},
                                                    {"role": "s2", "label": "suma po procesach MPI", "marker": "rect",
                                                     "outline": True},
                                                    {"role": "ideal", "label": "pomiar = model (±10%)", "marker": "line"}]},
                       {"label": "kształt", "items": [{"label": name, "marker": mrk} for name, mrk in MEM_FAMILY.values()]}]}
    charts.append(c3)

    # --- cachegrind ---
    cg = cg_per_unit(read_csv(T / "cachegrind.csv"))
    c4 = chart("t_cachegrind", "Pamięć podręczna: chybienia D1, L2 i L3", "dots", "tests", "4.2",
               "Szachownica Monte Carlo ma 11–12× mniej chybień D1 niż losowa kolejność prób, dlatego już przy 1 wątku "
               "jest 3–4× szybsza.",
               "Automat frontalny lawy dotyka tylko brzegu potoku: 19× mniej chybień D1 niż pełny przebieg.",
               ["Zestaw „pary porównań”: wiersz = dwa warianty tego samego przypadku; kropki połączone kreską, przy "
                "kropce nazwa wariantu, z prawej: ile razy mniej chybień ma lepszy. Pomarańczowa kropka: mniej chybień, "
                "szara: więcej.",
                "Zestawy „rozmiar” i „pas MPI”: pasek = chybienia dla jednego rozmiaru siatki.",
                f"Oś pozioma: chybienia na komórkę i krok (automat) albo na próbę (Monte Carlo), skala logarytmiczna "
                f"({HOW_LOG}). Mniej = lepiej. „0 chybień”: zero, którego nie da się pokazać na tej skali.",
                "Poziomy: D1 = pamięć podręczna danych 1. poziomu (48 KB na rdzeń), L2 (2 MB na rdzeń), L3 (36 MB, "
                "wspólna). Chybienie = danych nie ma na tym poziomie i trzeba je pobrać z wolniejszego.",
                "Liczby pochodzą z symulacji (valgrind cachegrind), nie z liczników sprzętowych: w WSL nie ma narzędzia "
                "perf, a w Windows liczniki wymagają uprawnień administratora. Symulator nie ma pobierania z wyprzedzeniem, "
                "więc przy dostępie po kolei zawyża chybienia L3."],
               "Symulacja valgrind cachegrind w WSL, GCC -O3 z informacją dla debuggera (ten sam kod maszynowy), 1 wątek; "
               "parametry pamięci podręcznej rdzenia wydajnościowego (D1 48 KB, L2 2 MB, L3 36 MB); liczone tylko "
               "funkcje kroku, bez pierwszego dotknięcia pamięci przy przygotowaniu",
               [sel("view", "zestaw", [("pary", "pary porównań")] + [(k, v[0]) for k, v in CG_SETS.items()]),
                sel("level", "poziom", [("D1", "D1"), ("L2", "L2"), ("L3", "L3")])],
               sources=["bench/results/testy/cachegrind.csv", "bench/results/testy/cachegrind.md"])
    SRC.all.add("bench/results/testy/cachegrind.md")
    xmin, xmax = 1e-3, 100
    for lvl in ("D1", "L2", "L3"):
        # pary: kropki połączone kreską (A, B), lepszy wariant pomarańczowy
        rows_ = [(n, pts) for n, pts in CG_PAIRS if all(c in cg for c, _ in pts)]
        da, db, ra, rb, la, lb, ta, tb, rt, notes = ([] for _ in range(10))
        for n, ((ca, na), (cb, nb)) in rows_:
            va, vb = cg[ca].get(lvl), cg[cb].get(lvl)
            za, zb = va is None or va < ZERO, vb is None or vb < ZERO
            da.append(None if za else va), db.append(None if zb else vb)
            ra.append("after" if (not za and (zb or va <= vb)) else "muted")
            rb.append("after" if (not zb and (za or vb < va)) else "muted")
            la.append(na if not za else f"{na}: 0 chybień"), lb.append(nb if not zb else f"{nb}: 0 chybień")
            ta.append(cg_tip(cg[ca], va, na))
            tb.append(cg_tip(cg[cb], vb, nb))
            if za and zb:
                rt.append(""), notes.append("0 chybień w obu wariantach")
            elif za or zb:
                rt.append(f"{na if za else nb}: 0 chybień"), notes.append(None)
            else:
                hi_, lo_ = max(va, vb), min(va, vb)
                r = hi_ / lo_
                rt.append(f"×{fx(r)} mniej" if r >= 1.05 else "prawie tyle samo"), notes.append(None)
        c4["views"][key("pary", lvl)] = {
            "kind": "dots", "labels": [n for n, _ in rows_], "connect": True,
            "x": {"title": "chybienia na komórkę i krok albo na próbę (skala log.)", "log": True, "fmt": "num",
                  "min": xmin, "max": xmax},
            "y": {"title": ""},
            "series": [series("wariant A", "muted", da, roles=ra, ptLabels=la, tips=ta, marker="circle"),
                       series("wariant B", "muted", db, roles=rb, ptLabels=lb, tips=tb, marker="circle")],
            "rowText": rt, "rowNotes": notes,
            "legendRows": [{"label": "kolor", "items": [{"role": "after", "label": "mniej chybień", "marker": "circle"},
                                                        {"role": "muted", "label": "więcej chybień", "marker": "circle"}]}]}
        for vid, (_, items) in CG_SETS.items():
            items = [(c, lbl) for c, lbl in items if c in cg]
            vals = [cg[c].get(lvl) for c, _ in items]
            c4["views"][key(vid, lvl)] = {
                "kind": "hbar", "labels": [lbl for _, lbl in items],
                "x": {"title": "chybienia na komórkę i krok albo na próbę (skala log.)", "log": True, "fmt": "num",
                      "min": xmin, "max": xmax},
                "y": {"title": ""},
                "series": [series(f"chybienia {lvl}", {"D1": "seq1", "L2": "seq2", "L3": "seq3"}[lvl],
                                  [v if v and v >= ZERO else None for v in vals],
                                  labels=[fmiss(v) if v and v >= ZERO else "0 chybień" for v in vals],
                                  tips=[cg_tip(cg[c], v) for v, (c, _) in zip(vals, items)])]}
    charts.append(c4)

    # --- krzywa czasu na komórkę ---
    caches = cache_sizes()
    c5 = chart("t_krzywa", "Czas na komórkę a rozmiar siatki", "line", "tests", "4.3",
               "Monte Carlo z losową kolejnością zwalnia 4,6×, gdy siatka wychodzi z L2 do pamięci RAM.",
               "Próg wypada tam, gdzie przewiduje 12 B na komórkę. Rozrost ziaren i szachownica idą po kolei: procesor "
               "pobiera dane z wyprzedzeniem i ukrywa opóźnienie, więc progu nie ma.",
               ["Oś pozioma: liczba komórek siatki; oś pionowa: czas w nanosekundach na komórkę i krok (automat) albo na "
                f"próbę (Monte Carlo). Obie osie w skali logarytmicznej ({HOW_LOG}).",
                "Pionowe linie przerywane: rozmiar siatki, przy którym dane kroku przestają się mieścić w L2 (2 MB) albo "
                "L3 (36 MB); w nawiasie liczba bajtów dotykanych na komórkę (26 B rozrost ziaren, 12 B Monte Carlo).",
                "Wąsy: najkrótszy i najdłuższy z 5 powtórzeń."],
               f"1 wątek na rdzeniu wydajnościowym (P), {CLOCK}; siatki 2D o boku od 128 do 2896 co √2, ta sama gęstość "
               "zarodków i liczba kroków; mediana z 5 powtórzeń; progi = pojemność pamięci podręcznej / bajty dotykane "
               "na komórkę w kroku",
               compilers=list(COMPILERS), sources=[f"bench/results/testy/krzywa_{c}.csv" for c in COMPILERS])
    fits = {"L2": "L2", "L3": "L3", "RAM": "pamięci RAM", "DRAM": "pamięci RAM"}
    for comp in COMPILERS:
        d = read_csv(T / f"krzywa_{comp}.csv")
        if not d:
            continue
        ss = []
        for cv, lbl, role, _ in CURVES:
            dc = sorted((r for r in d if r["curve"] == cv), key=lambda r: num(r["cells"]))
            ss.append(series(lbl, role, [[num(r["cells"]), num(r["ns_med"])] for r in dc], marker="circle",
                             lo=[num(r["ns_min"]) for r in dc], hi=[num(r["ns_max"]) for r in dc],
                             tips=[f"{pl(num(r['cells']), 0)} komórek (bok {r['n']}), dane kroku "
                                   f"{pl(num(r['workingSet']) / 2**20, 1)} MB w {fits.get(r['fits'], r['fits'])}: "
                                   f"{pl(num(r['ns_med']), 1)} ns [{pl(num(r['ns_min']), 1)}–{pl(num(r['ns_max']), 1)}] "
                                   f"na {'próbę' if r['unit'] in ('próbę', 'probe', 'trial') else 'komórkę i krok'}"
                                   for r in dc]))
        vl = [{"x": caches[lv] / bpc, "label": f"{lv} ({bpc} B)"} for bpc in (26, 12) for lv in ("L2", "L3") if lv in caches]
        c5["views"][comp] = {"x": {"title": "komórki siatki (skala log.)", "log": True, "fmt": "num"},
                             "y": {"title": "ns na komórkę i krok albo na próbę (skala log.)", "log": True, "fmt": "num"},
                             "series": ss, "vlines": vl}
    charts.append(c5)

    # --- przepustowość ---
    c6 = chart("t_przepustowosc", "Przepustowość pamięci RAM: 1–8 wątków", "line", "tests", "4.4",
               "Pamięć RAM nasyca się przy 6 wątkach: ok. 48 GB/s przy zapisie i odczycie, ok. 59 GB/s przy samym odczycie.",
               "Jeden wątek wykorzystuje ok. 1/3 tej przepustowości, więc przypadek ograniczony pamięcią nie skorzysta "
               "z dalszych rdzeni.",
               ["Oś pozioma: liczba wątków na rdzeniach wydajnościowych; oś pionowa: przepustowość w GB/s (najlepszy "
                "z 20 powtórzeń).",
                "Kolor i kształt: rodzaj pętli testowej jak w teście STREAM: triad (a = b + s·c: dwa odczyty i zapis), "
                "copy (a = b), sam odczyt.",
                "Płaska linia od 6 wątków = pamięć nasycona: kolejne wątki tylko dzielą tę samą przepustowość."],
               f"Mikrotest przepustowości (pętle jak w STREAM), tablice 160 MB (ponad 4 razy więcej niż L3), wątki na "
               f"rdzeniach wydajnościowych (P), {CLOCK}; najlepszy z 20 powtórzeń", compilers=list(COMPILERS),
               sources=[f"bench/results/testy/przepustowosc_{c}.csv" for c in COMPILERS])
    for comp in COMPILERS:
        d = [r for r in read_csv(T / f"przepustowosc_{comp}.csv") if r["mode"] == "stream"]
        ss = []
        for i, (kname, lbl, role) in enumerate(KERNELS):
            dk = sorted((r for r in d if r["kernel"] == kname), key=lambda r: int(r["threads"]))
            ss.append(series(lbl, role, [[int(r["threads"]), num(r["best"]) / 1000] for r in dk], marker=MARKERS[i],
                             tips=[f"najlepszy {pl(num(r['best']) / 1000, 1)} GB/s, mediana {pl(num(r['median']) / 1000, 1)} GB/s"
                                   for r in dk]))
        c6["views"][comp] = {"x": {"title": "wątki (rdzenie P)", "ticks": THREADS, "min": 1, "max": 8, "fmt": "int"},
                             "y": {"title": "przepustowość [GB/s]", "min": 0, "fmt": "num"}, "series": ss}
    charts.append(c6)

    # --- zapotrzebowanie przy 8 wątkach ---
    weak = read_csv(T / "slabe_omp_msvc.csv")
    bw = [r for r in read_csv(T / "przepustowosc_msvc.csv") if r["mode"] == "stream" and r["kernel"] == "triad"]
    bw_max = max(num(r["best"]) for r in bw) / 1000 if bw else None
    c7 = chart("t_zapotrzebowanie", "Zapotrzebowanie na przepustowość przy 8 wątkach", "hbar", "tests", "4.4",
               "Kolejność zapotrzebowania na przepustowość pamięci jest dokładnie kolejnością efektywności w skalowaniu "
               "słabym.",
               "Rozrost ziaren potrzebuje co najmniej 16 GB/s ruchu spoza L2 (realnie do ok. 30 z 48 GB/s) i ma "
               "E_w(8) = 0,49; Monte Carlo i lawa używają najwyżej 15% przepustowości.",
               ["Długość paska: szacowany ruch danych spoza L2 (do L3 albo RAM) przy 8 wątkach, w GB/s. Linia "
                "przerywana: zmierzona maksymalna przepustowość RAM (pętla triad).",
                "Szacunek: komórki (albo próby) na sekundę ze skalowania słabego × chybienia L2 na komórkę z symulacji "
                "cachegrind × 64 B (linia pamięci). To dolna granica: bez zapisów zwrotnych i pobierania z wyprzedzeniem.",
                "W podpowiedzi efektywność E_w(8) tego przypadku."],
               "OpenMP, 8 wątków, kompilator MSVC; dane ze skalowania słabego, symulacji cachegrind i mikrotestu "
               "przepustowości", compilers=["msvc"],
               sources=["bench/results/testy/slabe_omp_msvc.csv", "bench/results/testy/cachegrind.csv",
                        "bench/results/testy/przepustowosc_msvc.csv"])
    vals, tips, labels = [], [], []
    for wid, cid, lbl in DEMAND:
        r = next((x for x in weak if x["case"] == wid and x["cores"] == "8"), None)
        if not r or cid not in cg:
            continue
        ph = "mcSim_med" if num(r.get("mcSim_med")) else "caSim_med"
        units_s = num(r["cells"]) * num(r["work"]) / (num(r[ph]) / 1000.0)
        gbs = units_s * cg[cid]["L2"] * 64 / 1e9
        labels.append(lbl)
        vals.append(gbs)
        tips.append(f"{pl(gbs, 1)} GB/s; E_w(8) OpenMP = {pl(num(r['Ew_phase']))}")
    c7["views"]["msvc"] = {"labels": labels, "x": {"title": "ruch spoza L2 [GB/s]", "fmt": "num", "min": 0,
                                                   "max": math.ceil((bw_max or 50) / 10) * 10},
                           "y": {"title": ""},
                           "series": [series("zapotrzebowanie przy 8 wątkach", "s1", vals, tips=tips,
                                             labels=[f"{pl(v, 1)} GB/s" for v in vals])],
                           "vlines": [{"x": bw_max, "label": f"maks. RAM (triad): {pl(bw_max, 1)} GB/s"}] if bw_max else []}
    charts.append(c7)
    name, title = DOCS["tests"]
    return {"id": "tests", "title": "Testy wydajności",
            "intro": "Ta sekcja zbiera testy całego systemu: skalowanie słabe (problem rośnie z liczbą rdzeni), pamięć "
                     "główną wątków i procesów, pamięć podręczną procesora i przepustowość pamięci RAM. Tłumaczy, skąd "
                     "biorą się wyniki z poprzednich sekcji.",
            "doc": {"pdf": f"{name}.pdf", "title": title, "section": ""}, "charts": charts}


# ---------------------------------------------------------------------------
# Zapis
# ---------------------------------------------------------------------------
def build() -> dict:
    SRC.all.clear()
    rows, chain = zestawienie()
    head = compat()
    data = {
        "format": FORMAT,
        "generated": dt.datetime.now().replace(microsecond=0).isoformat(),
        "generator": "tools/wydajnosc_gui.py",
        "compilers": COMPILERS,
        "header": head,
        "glossary": [{"term": t, "def": d} for t, d in GLOSSARY],
        "summary": summary(rows, chain),
        "sections": [section_seq(), section_omp(), section_mpi(rows), section_mpiio(), section_tests(rows)],
        "conditions": {"gcc": COND_GCC},
    }
    for s in data["sections"]:
        for c in s["charts"]:
            c["sources"] = sorted(set(c["sources"]))
            SRC.all.update(c["sources"])
            for v in c["views"].values():  # linie odniesienia — też 4 cyfry znaczące
                for ln in v.get("hlines", []) + v.get("vlines", []):
                    for k in ("x", "y"):
                        if k in ln:
                            ln[k] = r4(ln[k])
    data["summary"]["chart"]["sources"] = sorted(set(data["summary"]["chart"]["sources"]))
    data["sources"] = sorted(s for s in SRC.all if (ROOT / s).exists())
    return data


def dumps(obj, indent: int = 0) -> str:
    """JSON czytelny dla człowieka: obiekty wcięte, tablice liczb i krótkich tekstów w jednej linii."""
    pad, pad2 = " " * indent, " " * (indent + 1)
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        items = [f"{pad2}{json.dumps(k, ensure_ascii=False)}: {dumps(v, indent + 1)}" for k, v in obj.items()]
        return "{\n" + ",\n".join(items) + "\n" + pad + "}"
    if isinstance(obj, list):
        if all(not isinstance(v, (dict, list)) for v in obj) or all(
                isinstance(v, list) and all(not isinstance(x, (dict, list)) for x in v) for v in obj):
            return json.dumps(obj, ensure_ascii=False, separators=(", ", ": "))
        return "[\n" + ",\n".join(pad2 + dumps(v, indent + 1) for v in obj) + "\n" + pad + "]"
    return json.dumps(obj, ensure_ascii=False)


def strip_generated(d: dict) -> dict:
    return {k: v for k, v in d.items() if k != "generated"}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=str(OUT), help="plik JSON (domyślnie gui/static/data/wydajnosc.json)")
    ap.add_argument("--check", action="store_true", help="tylko sprawdź, czy plik jest aktualny (bez zapisu)")
    args = ap.parse_args()
    data = build()
    out = Path(args.out)
    if args.check:
        old = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
        same = strip_generated(old) == strip_generated(json.loads(dumps(data)))
        print(f"{out}: {'aktualny' if same else 'NIEAKTUALNY — uruchom python tools/wydajnosc_gui.py'}")
        return 0 if same else 1
    out.parent.mkdir(parents=True, exist_ok=True)
    text = dumps(data) + "\n"
    out.write_bytes(text.encode("utf-8"))
    n = sum(len(s["charts"]) for s in data["sections"]) + 1
    print(f"Zapisano {out.relative_to(ROOT).as_posix() if out.is_relative_to(ROOT) else out}: {n} wykresów, "
          f"{len(data['sources'])} plików źródłowych, {len(text.encode('utf-8')) / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
