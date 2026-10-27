#!/usr/bin/env python3
"""Symulacja pamięci podręcznej: valgrind --tool=cachegrind na programie GCC (`build-gcc-release-g` — kod jak
Release -O3, z -g), 1 wątek, w WSL. Liczniki sprzętowe nie są dostępne (WSL: brak perf, Windows: liczniki PMU
wymagają uprawnień administratora — bench/results/testy/POSTEP.md), więc chybienia liczy symulator.

Cachegrind symuluje dwa poziomy danych: D1 i ostatni poziom (LL). Procesor (bench/results/testy/procesor.md): rdzeń P
— L1d 48 KB 12-drożna, L2 2 MB 16-drożna (na rdzeń), L3 36 MB 12-drożna (wspólna), linia 64 B. Dlatego każdy przypadek
liczony jest dwa razy: LL = L2 (chybienia L2 = odwołania do L3) i LL = L3 (chybienia L3 = odwołania do pamięci RAM).
L3 36 MB ma 49 152 zbiory przy 12 drogach, a cachegrind wymaga liczby zbiorów będącej potęgą 2 — symulujemy 36 MB
z 18 drogami (32 768 zbiorów; ten sam rozmiar, inna asocjacyjność — chybienia z konfliktów nieco inne niż w procesorze).
Symulator nie modeluje prefetchera sprzętowego, wspólnej L3 z innymi rdzeniami ani zasady inkluzji — liczby są
porównawcze (front vs full, random vs szachownica, rozmiar siatki), nie bezwzględne.

Cachegrind 3.18 nie ma włączania / wyłączania zbierania w trakcie programu, więc liczy cały przebieg (przygotowanie,
statystyki, zapis — `output.format = none`); dlatego obok sum całego programu tabela podaje funkcje z największą
liczbą chybień (jak cg_annotate) i ich udział.

Wyniki: bench/results/testy/<nazwa>.csv (wiersz na przebieg; skrypt dopisuje i pomija przebiegi już zapisane —
wznowienie), <nazwa>.md (tabele), bench/profiles/cachegrind/<przypadek>_<LL>.txt (cg_annotate: funkcje, ścieżki
zastąpione <repo>). Uruchamianie (z katalogu projektu, Windows):

    wsl -e python3 bench/cachegrind.py --list
    wsl -e python3 bench/cachegrind.py --cases lava_front,lava_full --ll L2,L3
    wsl -e python3 bench/cachegrind.py --report        # same tabele z zapisanego CSV
"""

from __future__ import annotations

import argparse
import copy
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ab import ROOT, classic, deep_update, from_file  # noqa: E402

D1 = "49152,12,64"
I1 = "32768,8,64"
LL = {"L2": ("2097152,16,64", "L2 rdzenia P: 2 MB, 16-drożna"),
      "L3": ("37748736,18,64", "L3: 36 MB (18 dróg zamiast 12 — wymóg potęgi 2 zbiorów)")}
EVENTS = ["Ir", "I1mr", "ILmr", "Dr", "D1mr", "DLmr", "Dw", "D1mw", "DLmw"]
# Funkcje kroku („jądro”) — miary bez przygotowania, statystyk i pierwszego dotknięcia pamięci przy alokacji
# (te w małych przypadkach dają większość chybień LL: _M_fill_assign, memset, memcpy, PottsMC::initialize).
KERNEL_CA = re.compile(r"^(LavaCA::(?!initFront|applyTerrain|placeSeeds|setStrip|LavaCA$)|Boundary::|"
                       r"Neighborhood::variantFromPrefix$|std::vector::emplace_back$)")
KERNEL_MC = re.compile(r"^PottsMC::(sweepTrials|colorTrials|syncFrame|sweep)$")
# Pliki robocze na ext4 w katalogu domowym WSL — /tmp czyści WSL przy wyłączeniu bezczynnej maszyny wirtualnej.
TMP = Path.home() / ".cache" / "volcano_cg"


def lava(sweep: str, steps: int = 150, grid: str = "vector") -> dict:
    """test_3d (64 × 64 × 48, 196 608 komórek): pierwsze `steps` kroków (erupcja trwa 150)."""
    return from_file("test_3d", {"grid": grid, "ca": {"sweep": sweep, "maxSteps": steps},
                                 "output": {"format": "none"}})


def cls(n: tuple[int, int, int], seeds: int, nb: str, sweep: str = "front", steps: int = 65535,
        grid: str = "vector") -> dict:
    return deep_update(classic(n, seeds, nb, fmt="none"), {"grid": grid, "ca": {"sweep": sweep, "maxSteps": steps}})


def mc(name: str, n: tuple[int, int, int], mcs: int, update: str) -> dict:
    """MC na całej przestrzeni (mc_full_2d / mc_full_3d): mcs prób na komórkę, statystyki tylko na końcu."""
    return from_file(name, {"space": {"nx": n[0], "ny": n[1], "nz": n[2]},
                            "mc": {"mcs": mcs, "statsEvery": mcs, "update": update}, "output": {"format": "none"}})


def cases() -> list[dict]:
    """Przypadki: id, grupa porównania, config, opis. Rozmiary dobrane tak, by przebieg pod cachegrind trwał ≤ ~5 min."""
    return [
        # CA lawa: automat frontalny (lista kandydatów — rozproszony dostęp) vs pełny przebieg (sekwencyjnie po siatce).
        {"id": "lava_front", "group": "lava", "config": lava("front"), "desc": "lawa test_3d, front, 150 kroków"},
        {"id": "lava_full", "group": "lava", "config": lava("full"), "desc": "lawa test_3d, full, 150 kroków"},
        # CA classic: sąsiedztwo von Neumanna (6 / 4 sąsiadów) vs Moore'a (26 / 8).
        {"id": "classic2d_vn", "group": "classic", "config": cls((1000, 1000, 1), 100, "von_neumann"),
         "desc": "classic 1000², VN, front"},
        {"id": "classic2d_moore", "group": "classic", "config": cls((1000, 1000, 1), 100, "moore"),
         "desc": "classic 1000², Moore, front"},
        {"id": "classic3d_vn", "group": "classic", "config": cls((100, 100, 100), 100, "von_neumann"),
         "desc": "classic 100³, VN, front"},
        {"id": "classic3d_moore", "group": "classic", "config": cls((100, 100, 100), 100, "moore"),
         "desc": "classic 100³, Moore, front"},
        # Układ danych: SoA w jednym wektorze na pole (VectorStorage, domyślny) vs macierz (MatrixStorage, etap 1).
        {"id": "layout_vector", "group": "layout", "config": cls((1000, 1000, 1), 100, "von_neumann", "full", 40),
         "desc": "classic 1000², VN, full, 40 kroków, vector"},
        {"id": "layout_matrix", "group": "layout",
         "config": cls((1000, 1000, 1), 100, "von_neumann", "full", 40, grid="matrix"),
         "desc": "classic 1000², VN, full, 40 kroków, matrix"},
        # MC: losowe próby (losowy adres w każdej próbie) vs szachownica (komórki po kolei, co druga / co ósma).
        {"id": "mc_random_2d", "group": "mc", "config": mc("mc_full_2d", (1000, 1000, 1), 3, "random"),
         "desc": "MC 1000², VN, random, 3 MCS"},
        {"id": "mc_cb_2d", "group": "mc", "config": mc("mc_full_2d", (1000, 1000, 1), 3, "checkerboard"),
         "desc": "MC 1000², VN, szachownica, 3 MCS"},
        {"id": "mc_random_3d", "group": "mc", "config": mc("mc_full_3d", (100, 100, 100), 2, "random"),
         "desc": "MC 100³, Moore, random, 2 MCS"},
        {"id": "mc_cb_3d", "group": "mc", "config": mc("mc_full_3d", (100, 100, 100), 2, "checkerboard"),
         "desc": "MC 100³, Moore, szachownica, 2 MCS"},
        # Rozmiar siatki względem pamięci podręcznej: mieści się w L2 / w L3 / większa niż L3.
        {"id": "size_classic_256", "group": "size_classic", "config": cls((256, 256, 1), 7, "von_neumann", "full", 40),
         "desc": "classic 256², VN, full, 40 kroków (siatka ~1,7 MB — L2)"},
        {"id": "size_classic_1024", "group": "size_classic",
         "config": cls((1024, 1024, 1), 100, "von_neumann", "full", 10),
         "desc": "classic 1024², VN, full, 10 kroków (~27 MB — L3)"},
        {"id": "size_classic_2896", "group": "size_classic",
         "config": cls((2896, 2896, 1), 800, "von_neumann", "full", 3),
         "desc": "classic 2896², VN, full, 3 kroki (~218 MB — RAM)"},
        {"id": "size_mc_256", "group": "size_mc", "config": mc("mc_full_2d", (256, 256, 1), 20, "random"),
         "desc": "MC 256², random, 20 MCS (~0,3 MB — L2)"},
        {"id": "size_mc_1024", "group": "size_mc", "config": mc("mc_full_2d", (1024, 1024, 1), 2, "random"),
         "desc": "MC 1024², random, 2 MCS (~5 MB — L3)"},
        {"id": "size_mc_4096", "group": "size_mc", "config": mc("mc_full_2d", (4096, 4096, 1), 1, "random"),
         "desc": "MC 4096², random, 1 MCS (~84 MB — RAM)"},
        # Przyspieszenie ponadliniowe: pas MC 1000² przy 8 procesach (1000 × 125) vs cała siatka — czy pas mieści się w L2.
        {"id": "strip_mc_cb_1000x125", "group": "strip", "config": mc("mc_full_2d", (1000, 125, 1), 24, "checkerboard"),
         "desc": "MC szachownica 1000 × 125 (pas przy 8 procesach), 24 MCS"},
        {"id": "strip_mc_cb_1000x1000", "group": "strip", "config": mc("mc_full_2d", (1000, 1000, 1), 3,
                                                                          "checkerboard"),
         "desc": "MC szachownica 1000², 3 MCS (ta sama liczba prób)"},
    ]


# ---------------------------------------------------------------------------
# Przebieg i odczyt pliku cachegrind.out
# ---------------------------------------------------------------------------
def parse_out(path: Path) -> tuple[dict, dict[str, list[int]]]:
    """Suma programu (summary) i sumy na funkcję (fn=) z pliku cachegrind.out."""
    events, fn, per_fn, summary = EVENTS, None, {}, {}
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("events:"):
                events = line.split()[1:]
            elif line.startswith("fn="):
                fn = line[3:].strip()
                per_fn.setdefault(fn, [0] * len(events))
            elif line.startswith("summary:"):
                vals = [int(x) for x in line.split()[1:]]
                summary = dict(zip(events, vals + [0] * (len(events) - len(vals))))
            elif fn and line[:1].isdigit():
                parts = line.split()
                acc = per_fn[fn]
                for i, v in enumerate(parts[1:]):
                    acc[i] += int(v)
    named = {k: dict(zip(events, v)) for k, v in per_fn.items()}
    return summary, named


def short_fn(name: str) -> str:
    """Nazwa funkcji do tabel: bez argumentów, szablonów, typu zwracanego, przestrzeni nazw i przyrostka [clone …]."""
    s = re.sub(r"\s*\[clone[^\]]*\]", "", name).replace("volcano::", "")
    while "<" in s:
        s2 = re.sub(r"<[^<>]*>", "", s)
        if s2 == s:
            break
        s = s2
    s = s.split("(")[0].strip()
    return s.split(" ")[-1]


def sanitize(text: str) -> str:
    """Ścieżki bezwzględne -> <repo> / <tmp> (raporty trafiają do repozytorium)."""
    text = text.replace(str(ROOT), "<repo>")
    return re.sub(re.escape(str(TMP)) + r"[^\s]*", "<tmp>", text)


def run_case(case: dict, ll: str, exe: str) -> dict:
    cfg = copy.deepcopy(case["config"])
    terrain = cfg.get("terrain", {})
    if terrain.get("type") == "file" and terrain.get("file"):
        terrain["file"] = str(ROOT / terrain["file"])
    cdir = TMP / "configs"
    cdir.mkdir(parents=True, exist_ok=True)
    cpath = cdir / f"{case['id']}.json"
    with open(cpath, "w", encoding="utf-8", newline="\n") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    out = TMP / "out" / f"{case['id']}_{ll}"
    shutil.rmtree(out, ignore_errors=True)
    cg = TMP / "cg" / f"{case['id']}_{ll}.out"
    cg.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["valgrind", "--tool=cachegrind", "--cache-sim=yes", f"--I1={I1}", f"--D1={D1}", f"--LL={LL[ll][0]}",
           f"--cachegrind-out-file={cg}", exe, "--config", str(cpath), "--out", str(out), "--threads", "1"]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    wall = time.time() - t0
    if r.returncode != 0:
        raise RuntimeError(f"cachegrind {case['id']} {ll}: kod {r.returncode}\n{r.stderr[-1500:]}")
    with open(out / "times.json", encoding="utf-8") as f:
        times = json.load(f)
    summary, per_fn = parse_out(cg)
    row = {"case": case["id"], "group": case["group"], "ll": ll, "desc": case["desc"], "wallSec": round(wall, 1),
           "cells": times.get("cells"), "steps": times.get("steps"), "mcs": times.get("mcs"),
           "domainCells": times.get("domainCells"), "simMs": times.get("caSim") or times.get("mcSim"),
           **{k: summary.get(k, 0) for k in EVENTS}}
    # Funkcje z największą liczbą chybień D1 i LL (zapis + odczyt) — 6 pierwszych; instancje szablonu tej samej funkcji
    # (np. std::vector<…>::_M_fill_assign dla kilku typów) sumowane pod skróconą nazwą.
    merged: dict[str, dict] = {}
    for n, v in per_fn.items():
        acc = merged.setdefault(short_fn(n), {k: 0 for k in EVENTS})
        for k in EVENTS:
            acc[k] += v.get(k, 0)

    def top(key: str) -> str:
        items = sorted(merged.items(), key=lambda kv: -(kv[1][f"{key}mr"] + kv[1][f"{key}mw"]))
        return json.dumps([[n, v["Dr"] + v["Dw"], v[f"{key}mr"] + v[f"{key}mw"]] for n, v in items[:6]],
                          ensure_ascii=False)
    row["topD1"] = top("D1")
    row["topDL"] = top("DL")
    # Sumy funkcji kroku (jądro): odwołania do danych i chybienia D1 / LL.
    pat = KERNEL_MC if case["group"] in ("mc", "size_mc", "strip") else KERNEL_CA
    kern = {n: v for n, v in per_fn.items() if pat.search(short_fn(n))}
    row["kD"] = sum(v.get("Dr", 0) + v.get("Dw", 0) for v in kern.values())
    row["kD1"] = sum(v.get("D1mr", 0) + v.get("D1mw", 0) for v in kern.values())
    row["kDL"] = sum(v.get("DLmr", 0) + v.get("DLmw", 0) for v in kern.values())
    row["kernelFns"] = " ".join(sorted({short_fn(n) for n in kern}))
    # cg_annotate (bez źródeł) do bench/profiles/cachegrind/.
    ann = subprocess.run(["cg_annotate", "--show=Dr,D1mr,DLmr,Dw,D1mw,DLmw", "--sort=D1mr,DLmr", "--auto=no",
                          str(cg)], capture_output=True, text=True)
    pdir = ROOT / "bench" / "profiles" / "cachegrind"
    pdir.mkdir(parents=True, exist_ok=True)
    lines = sanitize(ann.stdout).splitlines()
    with open(pdir / f"{case['id']}_{ll}.txt", "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines[:80]) + "\n")
    return row


# ---------------------------------------------------------------------------
# Tabele
# ---------------------------------------------------------------------------
def unit_of(r: dict) -> tuple[float, str]:
    """Jednostka pracy: komórka × krok (CA) albo próba MC (MCS × komórki domeny)."""
    if r.get("mcs") not in (None, "", "None", "0", 0):
        return float(r["mcs"]) * float(r["domainCells"] or r["cells"]), "próbę MC"
    return float(r["cells"]) * float(r["steps"] or 1), "komórkę × krok"


def pct(a: float, b: float) -> str:
    return f"{100 * a / b:.2f}%".replace(".", ",") if b else "—"


def num(v: float, d: int = 2) -> str:
    return f"{v:.{d}f}".replace(".", ",")


def miss_table(by: dict, plan: list[dict], kernel: bool) -> list[str]:
    """Odwołania i chybienia na jednostkę pracy: jądro (funkcje kroku) albo cały program."""
    kd, k1, kl = ("kD", "kD1", "kDL") if kernel else (None, None, None)
    md = ["| Przypadek | D odwołania / jedn. | D1: chybienia / jedn. | D1 miss rate | L2: chybienia / jedn. | "
          "L2 miss rate | L3: chybienia / jedn. | L3 miss rate | jednostka |", "|---|---|---|---|---|---|---|---|---|"]
    for c in plan:
        r2, r3 = by.get((c["id"], "L2")), by.get((c["id"], "L3"))
        r = r2 or r3
        if not r:
            continue
        u, uname = unit_of(r)
        if kernel:
            d, d1 = int(r[kd]), int(r[k1])
            l2 = int(r2[kl]) if r2 else None
            l3 = int(r3[kl]) if r3 else None
        else:
            d = int(r["Dr"]) + int(r["Dw"])
            d1 = int(r["D1mr"]) + int(r["D1mw"])
            l2 = int(r2["DLmr"]) + int(r2["DLmw"]) if r2 else None
            l3 = int(r3["DLmr"]) + int(r3["DLmw"]) if r3 else None
        md.append(f"| {c['desc']} | {num(d / u, 1)} | {num(d1 / u, 3)} | {pct(d1, d)} | "
                  f"{num(l2 / u, 3) if l2 is not None else '—'} | {pct(l2, d) if l2 is not None else '—'} | "
                  f"{num(l3 / u, 4) if l3 is not None else '—'} | {pct(l3, d) if l3 is not None else '—'} | {uname} |")
    return md


def report(rows: list[dict], plan: list[dict]) -> list[str]:
    by = {(r["case"], r["ll"]): r for r in rows}
    md = ["Jądro — funkcje kroku (CA: `LavaCA::` poza przygotowaniem, `Boundary::`, wybór wariantu sąsiedztwa, "
          "`push_back` list frontu; MC: `PottsMC::sweepTrials` / `colorTrials` / `syncFrame`); miss rate = chybienia / "
          "odwołania do danych jądra:", ""]
    md += miss_table(by, plan, kernel=True)
    md += ["", "Cały program (z przygotowaniem, statystykami i pierwszym dotknięciem pamięci przy alokacji):", ""]
    md += miss_table(by, plan, kernel=False)
    md += ["", "Funkcje z największą liczbą chybień (LL = L3; udział w chybieniach D1 / L3 całego programu):", "",
           "| Przypadek | funkcja: udział w chybieniach D1 | funkcja: udział w chybieniach L3 |", "|---|---|---|"]
    for c in plan:
        r = by.get((c["id"], "L3")) or by.get((c["id"], "L2"))
        if not r:
            continue
        d1 = int(r["D1mr"]) + int(r["D1mw"])
        dl = int(r["DLmr"]) + int(r["DLmw"])
        t1 = "; ".join(f"`{n}` {pct(m, d1)}" for n, _, m in json.loads(r["topD1"])[:3] if m)
        tl = "; ".join(f"`{n}` {pct(m, dl)}" for n, _, m in json.loads(r["topDL"])[:3] if m)
        md.append(f"| {c['desc']} | {t1} | {tl} |")
    return md


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cases", help="przypadki (id po przecinku; domyślnie wszystkie)")
    ap.add_argument("--ll", default="L2,L3", help="poziomy LL do symulacji (L2, L3)")
    ap.add_argument("--bin", default="build-gcc-release-g/bin/engine", help="program (GCC Release z -g)")
    ap.add_argument("--name", default="cachegrind", help="nazwa wyników w bench/results/testy/")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--report", action="store_true", help="bez przebiegów: tabele z zapisanego CSV")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    plan = cases()
    if args.list:
        for c in plan:
            print(f"{c['group']:13s} {c['id']:24s} {c['desc']}")
        return 0
    if args.cases:
        wanted = [x.strip() for x in args.cases.split(",")]
        plan_run = [c for c in plan if c["id"] in wanted]
    else:
        plan_run = plan
    out_dir = ROOT / "bench" / "results" / "testy"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"{args.name}.csv"
    rows = []
    if csv_path.exists():
        with open(csv_path, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    if not args.report:
        if os.name == "nt":
            print("Uruchom w WSL: wsl -e python3 bench/cachegrind.py …", file=sys.stderr)
            return 2
        exe_src = ROOT / args.bin
        (TMP / "bin").mkdir(parents=True, exist_ok=True)
        exe = TMP / "bin" / "engine"
        shutil.copy(exe_src, exe)
        os.chmod(exe, 0o755)
        done = {(r["case"], r["ll"]) for r in rows}
        for c in plan_run:
            for ll in args.ll.split(","):
                if (c["id"], ll) in done:
                    print(f"pominięty (zapisany): {c['id']} {ll}")
                    continue
                print(f"cachegrind {c['id']} LL={ll} …", flush=True)
                row = run_case(c, ll, str(exe))
                rows.append({k: ("" if v is None else str(v)) for k, v in row.items()})
                keys = list(dict.fromkeys(k for r in rows for k in r))
                with open(csv_path, "w", encoding="utf-8", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=keys, lineterminator="\n")
                    w.writeheader()
                    w.writerows(rows)
                d = int(row["Dr"]) + int(row["Dw"])
                print(f"  {row['wallSec']} s; D {d:,}, D1 miss {100 * (int(row['D1mr']) + int(row['D1mw'])) / d:.2f}%, "
                      f"LL miss {100 * (int(row['DLmr']) + int(row['DLmw'])) / d:.3f}%", flush=True)
    md = [f"# Symulacja pamięci podręcznej `{args.name}` (cachegrind)", "",
          f"- Program: `{args.bin}` (GCC 11.4 -O3, -falign-functions=64, -g), 1 wątek, WSL 2; valgrind cachegrind, "
          f"I1 {I1}, D1 {D1} (rozmiar, drogi, linia), LL = L2 {LL['L2'][0]} albo L3 {LL['L3'][0]}.",
          "- Liczby z całego przebiegu programu (przygotowanie, kroki, statystyki; bez zapisu wyników). „Jedn.” — "
          "komórka × krok (CA) albo próba MC. Miss rate = chybienia / wszystkie odwołania do danych (odczyt + zapis).",
          ""]
    md += report(rows, plan)
    with open(out_dir / f"{args.name}.md", "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(md) + "\n")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    sys.exit(main())
