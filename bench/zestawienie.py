#!/usr/bin/env python3
"""Zestawienie przyspieszenia i efektywności z istniejących pomiarów (etap 12) — bez nowych przebiegów.

Czyta CSV etapów 8–11 i składa jedną tabelę przypadek × wariant: program sekwencyjny przed etapem 8 i po nim (profil
`profile_2026-10-17_przed2` / `_po`), OpenMP (etap 9, `bench/results/omp/skalowanie_*.csv`), MPI, hybryda i OpenMP
kontrolnie (etap 10, `bench/results/mpi/skalowanie_mpi_*.csv`), typy pochodne w wymianie (etap 11,
`bench/results/mpi_io/pomiar_*_raw.csv`) — z T, S, E i częścią szeregową f (prawo Amdahla), osobno faza obliczeń
(`caSim` / `mcSim`) i cały przebieg (`total`), MSVC i GCC, z kolumnami „źródło” (plik, etap) i „warunki”.

Zasady porównywania (dokładniej w docs/testy-wydajnosci.md, punkt 1):
- S i E wariantu równoległego liczone od T(1) **z tej samej sesji pomiarowej** (etap 9: p = 1, etap 10: m1); wartości
  z różnych dni nie są mieszane w jednym ilorazie — poza „łącznym przyspieszeniem”, które jest iloczynem ilorazów
  z sesji (algorytm × równoległość) i dla kontroli także ilorazem wprost.
- Etap 11 nie ma m1 w grupie „pack” — S z typami pochodnymi = S(m<p>) z etapu 10 × (faza m / faza d w jednej sesji
  etapu 11). Surowe czasy m8 z etapów 10 i 11 różnią się o kilkanaście–kilkadziesiąt procent (inna sesja).
- Profil przed / po etapie 8 był z formatem wyjścia `both` (txt + bin) w classic i MC, a pomiary etapów 9–11 —
  z `bin`: tam porównywalna jest tylko faza obliczeń (`total` zawiera inny zapis). Etna — `bin` w obu, więc też total.
- Warunki: wszystkie zestawione pomiary bez turbo (tryb oszczędny); etap 8 kroki k1–k4 (testy A/B) były z turbo —
  ich ilorazy są porównywalne, czasy nie, więc do łańcucha przed → po służy profil `_przed2` / `_po` (bez turbo).

Wyniki: bench/results/testy/zestawienie.md (tabele), zestawienie.csv (postać długa: przypadek × kompilator × wariant),
zestawienie_lacznie.csv (łączne przyspieszenie, dane wykresu „schodki”). Wykresy: python bench/plot_testy.py.

    python bench/zestawienie.py
"""

from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "bench" / "results"
OUT = RES / "testy"

# Przypadki pomiarów skalowania (etapy 9–11) i ich odpowiedniki w profilu przed / po etapie 8.
CASES = [
    {"id": "lava_etna_real", "label": "lawa `etna_real`, front", "short": "Etna", "group": "lawa",
     "profile": "etna_real", "total_ok": True, "pack": None},
    {"id": "lava_duza_3d_front", "label": "lawa 3D 128² × 64, front", "short": "lawa front", "group": "lawa",
     "profile": None, "pack": "pack_lava_3d_front"},
    {"id": "lava_duza_3d_full", "label": "lawa 3D 128² × 64, full", "short": "lawa full", "group": "lawa",
     "profile": None, "pack": "pack_lava_3d_full"},
    {"id": "classic_2000x2000_s400_vn", "label": "classic 2000², VN", "short": "classic 2000²", "group": "classic",
     "profile": None, "pack": None},
    {"id": "classic_300x300x300_s100_vn", "label": "classic 300³, VN", "short": "classic 300³", "group": "classic",
     "profile": "classic_300x300x300_s100_vn_per", "total_ok": False, "pack": "pack_classic_300"},
    {"id": "mc_cb_2d_1000", "label": "MC szachownica 1000², VN", "short": "MC 1000²", "group": "mc",
     "profile": "mcfull_1000x1000_vn_mcs100", "total_ok": False, "random": "mc_random_2d_1000", "pack": None},
    {"id": "mc_cb_3d_100", "label": "MC szachownica 100³, Moore", "short": "MC 100³", "group": "mc",
     "profile": "mcfull_100x100x100_moore_mcs100", "total_ok": False, "random": "mc_random_3d_100",
     "pack": "pack_mc_cb_3d_100"},
]
COMPILERS = {"msvc": {"build": "msvc-O2", "name": "MSVC / MS-MPI"}, "gcc": {"build": "gcc-O3", "name": "GCC / OpenMPI"}}
COND = "bez turbo, rdzenie P, wysoki priorytet"


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def num(v) -> float | None:
    try:
        return float(v) if v not in (None, "") else None
    except ValueError:
        return None


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def raw_medians(paths: list[Path]) -> dict[tuple[str, str], dict]:
    """Mediany przebiegów (przypadek, wariant) z plików _raw.csv etapu 11."""
    groups: dict[tuple[str, str], list[dict]] = {}
    for p in paths:
        for r in read_csv(p):
            groups.setdefault((r["case"], r["variant"]), []).append(r)
    out = {}
    for key, rows in groups.items():
        e = {"n": len(rows)}
        for k in ("caSim", "mcSim", "total", "haloAvg"):
            vals = [num(r.get(k)) for r in rows if num(r.get(k)) is not None]
            if vals:
                e[k] = statistics.median(vals)
        out[key] = e
    return out


def collect(comp: str) -> tuple[list[dict], list[dict]]:
    """Wiersze tabeli (postać długa) i łączne przyspieszenie dla jednego kompilatora."""
    build = COMPILERS[comp]["build"]
    p_przed = RES / "profile_2026-10-17_przed2.csv"
    p_po = RES / "profile_2026-10-17_po.csv"
    p_omp = RES / "omp" / f"skalowanie_{comp}.csv"
    p_mpi = RES / "mpi" / f"skalowanie_mpi_{comp}.csv"
    przed = {r["variant"]: r for r in read_csv(p_przed) if r["build"] == build}
    po = {r["variant"]: r for r in read_csv(p_po) if r["build"] == build}
    omp = read_csv(p_omp)
    mpi = read_csv(p_mpi)
    e11_files = sorted((RES / "mpi_io").glob(f"pomiar_{comp}_cz*_raw.csv"))
    e11 = raw_medians(e11_files)
    rows, chain = [], []

    for case in CASES:
        cid, ph = case["id"], ("mcSim" if case["group"] == "mc" else "caSim")

        def add(variant: str, stage: str, cores: int, t_ph, t_tot, s_ph=None, s_tot=None, f_ph=None, f_tot=None,
                src: str = "", cond: str = COND, note: str = "", kind: str = "") -> dict:
            r = {"case": cid, "label": case["label"], "group": case["group"], "compiler": comp, "variant": variant,
                 "kind": kind, "stage": stage, "cores": cores, "phase": ph, "T_phase": t_ph, "T_total": t_tot,
                 "S_phase": s_ph, "E_phase": s_ph / cores if s_ph and cores else None, "S_total": s_tot,
                 "E_total": s_tot / cores if s_tot and cores else None, "f_phase": f_ph, "f_total": f_tot,
                 "source": src, "conditions": cond, "note": note}
            rows.append(r)
            return r

        # --- etap 8: profil przed / po (sekwencyjnie, 1 rdzeń P) ---
        pv = case.get("profile")
        r_przed = r_po = None
        if pv and pv in przed and pv in po:
            key = f"{ph}_ms_med"
            tp, tq = num(przed[pv][key]), num(po[pv][key])
            totp = num(przed[pv]["total_ms_med"]) if case.get("total_ok") else None
            totq = num(po[pv]["total_ms_med"]) if case.get("total_ok") else None
            fmt_note = "" if case.get("total_ok") else "profil z zapisem txt + bin — total nieporównywalny z etapami 9–11"
            r_przed = add("przed etapem 8", "8", 1, tp, totp, src=rel(p_przed),
                          cond="bez turbo, 1 rdzeń P (proces przypięty)", note=fmt_note, kind="seq")
            r_po = add("po etapie 8", "8", 1, tq, totq, s_ph=tp / tq, s_tot=(totp / totq if totp else None),
                       src=rel(p_po), cond="bez turbo, 1 rdzeń P (proces przypięty)",
                       note="S = przed / po (zysk z algorytmu)" + ("; " + fmt_note if fmt_note else ""), kind="seq")

        # --- etap 9: OpenMP (T(1) z tej samej sesji) ---
        o = {int(r["threads"]): r for r in omp if r["case"] == cid}
        rnd = None
        if case.get("random"):
            rr = [r for r in omp if r["case"] == case["random"] and r["threads"] == "1"]
            if rr:
                rnd = add("MC random, 1 wątek", "9", 1, num(rr[0][f"{ph}_med"]), num(rr[0]["total_med"]),
                          src=rel(p_omp), note="wariant naiwny (sekwencyjny z definicji)", kind="seq")
        if 1 in o:
            t1 = o[1]
            r_o1 = add("OpenMP 1 wątek", "9", 1, num(t1[f"{ph}_med"]), num(t1["total_med"]), s_ph=1.0, s_tot=1.0,
                       src=rel(p_omp), kind="omp")
            if rnd:
                r_o1["note"] = (f"szachownica przy 1 wątku: ×{rnd['T_phase'] / r_o1['T_phase']:.2f} względem "
                                "wariantu random (kolejność komórek zamiast losowych adresów)")
            for p in (2, 4, 6, 8):
                if p in o:
                    e = o[p]
                    add(f"OpenMP {p} wątków" if p > 4 else f"OpenMP {p} wątki", "9", p, num(e[f"{ph}_med"]),
                        num(e["total_med"]), num(e["S_phase"]), num(e["S_total"]), num(e.get("amdahl_f_phase")),
                        num(e.get("amdahl_f_total")), src=rel(p_omp), kind="omp")

        # --- etap 10: MPI, hybryda, OpenMP kontrolnie (T(1) = m1 tej sesji) ---
        m = {r["variant"]: r for r in mpi if r["case"] == cid}
        names = {"m1": "MPI 1 proces", "m2": "MPI 2 procesy", "m3": "MPI 3 procesy", "m4": "MPI 4 procesy",
                 "m6": "MPI 6 procesów", "m7": "MPI 7 procesów (bez procesora 0)", "m8": "MPI 8 procesów",
                 "h2x4": "hybryda 2 × 4", "h4x2": "hybryda 4 × 2", "c4": "MPI 4, changed", "c8": "MPI 8, changed",
                 "o4": "OpenMP 4 (etap 10)", "o8": "OpenMP 8 (etap 10, kontrola)"}
        for v, nm in names.items():
            if v in m:
                e = m[v]
                add(nm, "10", int(e["cores"]), num(e[f"{ph}_med"]), num(e["total_med"]), num(e["S_phase"]),
                    num(e["S_total"]), num(e.get("amdahl_f_phase")) if v.startswith("m") else None,
                    num(e.get("amdahl_f_total")) if v.startswith("m") else None, src=rel(p_mpi),
                    kind="hyb" if v.startswith("h") else ("omp" if v.startswith("o") else "mpi"),
                    note=("total zawiera MPI_Init" if v.startswith(("m", "h", "c")) else ""))

        # --- etap 11: typy pochodne w wymianie (stosunek d / m z jednej sesji × S etapu 10) ---
        if case.get("pack"):
            for p in (2, 4, 7, 8):
                em, ed = e11.get((case["pack"], f"m{p}")), e11.get((case["pack"], f"m{p}d"))
                base = m.get(f"m{p}")
                if em and ed and base and ph in em and ph in ed:
                    ratio = em[ph] / ed[ph]
                    s_ph = num(base["S_phase"]) * ratio
                    add(f"MPI {p}, typy pochodne", "11", p, ed[ph], None, s_ph, None,
                        src=", ".join(rel(f) for f in e11_files), kind="mpi",
                        note=(f"S = S(m{p}) etapu 10 × faza m / d etapu 11 (×{ratio:.3f}); faza m{p} w etapie 11: "
                              f"{em[ph]:.0f} ms, w etapie 10: {num(base[f'{ph}_med']):.0f} ms"))

        # --- łączne przyspieszenie: przed etapem 8 → najlepszy wariant równoległy na ≤ 8 rdzeniach ---
        if r_przed and r_po:
            par = [r for r in rows if r["case"] == cid and r["compiler"] == comp and r["stage"] in ("9", "10", "11")
                   and r["S_phase"] and r["cores"] > 1 and "kontrola" not in r["variant"] and "(etap 10)" not in
                   r["variant"]]
            best = max(par, key=lambda r: r["S_phase"]) if par else None
            base1 = next((r for r in rows if r["case"] == cid and r["compiler"] == comp and r["variant"] ==
                          ("OpenMP 1 wątek" if best and best["stage"] == "9" else "MPI 1 proces")), None)
            if best and base1:
                alg = r_przed["T_phase"] / r_po["T_phase"]
                # MC: szachownica to inny (równoważny statystycznie) proces — zysk przy 1 wątku liczony osobno.
                # Bez wariantu random w sesji (GCC) — szachownica wprost: po etapie 8 (profil) / szachownica 1 wątek
                # (etap 9), czyli czasy z dwóch sesji.
                cb1 = next(r for r in rows if r["case"] == cid and r["compiler"] == comp and
                           r["variant"] == "OpenMP 1 wątek")["T_phase"]
                cb = (rnd["T_phase"] / cb1 if rnd else r_po["T_phase"] / cb1) if case["group"] == "mc" else None
                drift = (r_po["T_phase"] / rnd["T_phase"]) if rnd else r_po["T_phase"] / base1["T_phase"]
                chain.append({
                    "case": cid, "label": case["label"], "short": case["short"], "compiler": comp,
                    "T_przed": r_przed["T_phase"], "T_po": r_po["T_phase"], "S_alg": alg,
                    "T_random1": rnd["T_phase"] if rnd else None, "S_checkerboard": cb,
                    "checkerboard_same_session": bool(rnd),
                    "T_par1": base1["T_phase"], "best": best["variant"], "best_stage": best["stage"],
                    "T_best": best["T_phase"], "S_par": best["S_phase"], "cores": best["cores"],
                    "S_product": alg * (cb or 1.0) * best["S_phase"],
                    "S_direct": r_przed["T_phase"] / best["T_phase"], "session_ratio": drift,
                    "T_omp8": next((r["T_phase"] for r in rows if r["case"] == cid and r["compiler"] == comp and
                                    r["variant"] == "OpenMP 8 wątków"), None)})
    return rows, chain


# ---------------------------------------------------------------------------
# Tabele Markdown
# ---------------------------------------------------------------------------
def f2(v, d: int = 2) -> str:
    return "—" if v is None else f"{v:.{d}f}".replace(".", ",")


def fms(v) -> str:
    if v is None:
        return "—"
    if v >= 1000:
        return f"{v:,.0f}".replace(",", " ")
    if v >= 100:
        return f"{v:.0f}"
    if v >= 10:
        return f"{v:.1f}".replace(".", ",")
    return f"{v:.2f}".replace(".", ",")


def pick(rows: list[dict], case: str, comp: str, variant: str) -> dict | None:
    return next((r for r in rows if r["case"] == case and r["compiler"] == comp and r["variant"] == variant), None)


def summary_table(rows: list[dict], comp: str) -> list[str]:
    """Jedna linia na przypadek: T(1) i S / E fazy przy 8 rdzeniach w każdym wariancie, najlepszy wariant."""
    cols = [("OpenMP 8 wątków", "OpenMP 8"), ("MPI 7 procesów (bez procesora 0)", "MPI 7"), ("MPI 8 procesów", "MPI 8"),
            ("hybryda 2 × 4", "2 × 4"), ("hybryda 4 × 2", "4 × 2"), ("MPI 8, typy pochodne", "MPI 8 + typy")]
    present = [c for c in cols if any(pick(rows, k["id"], comp, c[0]) for k in CASES)]
    md = ["| Przypadek | T(1) faza [ms] (etap 9 / 10) | " + " | ".join(f"{c[1]}: S / E" for c in present) +
          " | najlepszy (S fazy) | S całego przebiegu najlepszego |",
          "|---|---|" + "---|" * len(present) + "---|---|"]
    for k in CASES:
        o1, m1 = pick(rows, k["id"], comp, "OpenMP 1 wątek"), pick(rows, k["id"], comp, "MPI 1 proces")
        if not (o1 or m1):
            continue
        cells = []
        for v, _ in present:
            r = pick(rows, k["id"], comp, v)
            cells.append(f"{f2(r['S_phase'])} / {f2(r['E_phase'])}" if r and r["S_phase"] else "—")
        par = [r for r in rows if r["case"] == k["id"] and r["compiler"] == comp and r["cores"] > 1 and r["S_phase"]
               and r["stage"] in ("9", "10", "11")]
        best = max(par, key=lambda r: r["S_phase"])
        md.append(f"| {k['label']} | {fms(o1['T_phase'] if o1 else None)} / {fms(m1['T_phase'] if m1 else None)} | "
                  + " | ".join(cells) + f" | {best['variant']} (etap {best['stage']}): **{f2(best['S_phase'])}** | "
                  f"{f2(best['S_total'])} |")
    return md


def long_table(rows: list[dict], comp: str) -> list[str]:
    md = ["| Przypadek | Wariant | Etap | Rdzenie | T faza [ms] | T total [ms] | S faza | E faza | S total | E total | "
          "f faza | f total | Źródło | Uwagi |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if r["compiler"] != comp:
            continue
        src = r["source"].replace("bench/results/", "")
        if len(src) > 60:
            src = src.split(",")[0] + " …"
        md.append(f"| {r['label']} | {r['variant']} | {r['stage']} | {r['cores']} | {fms(r['T_phase'])} | "
                  f"{fms(r['T_total'])} | {f2(r['S_phase'])} | {f2(r['E_phase'])} | {f2(r['S_total'])} | "
                  f"{f2(r['E_total'])} | {f2(r['f_phase'], 3)} | {f2(r['f_total'], 3)} | `{src}` | {r['note']} |")
    return md


def cb_txt(c: dict) -> str:
    if not c["S_checkerboard"]:
        return "—"
    return f"×{f2(c['S_checkerboard'])}" + ("" if c["checkerboard_same_session"] else "¹")


def chain_table(chain: list[dict]) -> list[str]:
    md = ["| Przypadek | Kompilator | przed etapem 8 [ms] | po etapie 8 [ms] | zysk z algorytmu (etap 8) | "
          "szachownica przy 1 wątku (etap 9) | najlepszy wariant równoległy | jego T [ms] | zysk z równoległości | "
          "**łącznie** (iloczyn) | wprost: przed / najlepszy |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in chain:
        md.append(f"| {c['label']} | {COMPILERS[c['compiler']]['name'].split(' /')[0]} | {fms(c['T_przed'])} | "
                  f"{fms(c['T_po'])} | ×{f2(c['S_alg'], 1)} | "
                  f"{cb_txt(c)} | {c['best']} (etap "
                  f"{c['best_stage']}) | {fms(c['T_best'])} | ×{f2(c['S_par'])} | **×{f2(c['S_product'], 0)}** | "
                  f"×{f2(c['S_direct'], 0)} |")
    return md


def superlinear(rows: list[dict]) -> list[str]:
    """Każdy wariant równoległy z E > 1 (faza albo cały przebieg)."""
    hits = [r for r in rows if r["cores"] > 1 and r["stage"] in ("9", "10", "11") and
            ((r["E_phase"] or 0) > 1.0 or (r["E_total"] or 0) > 1.0)]
    if not hits:
        return ["Brak wariantu z E > 1."]
    md = ["| Przypadek | Kompilator | Wariant | Etap | S faza | E faza | S total | E total |",
          "|---|---|---|---|---|---|---|---|"]
    for r in hits:
        md.append(f"| {r['label']} | {r['compiler']} | {r['variant']} | {r['stage']} | {f2(r['S_phase'])} | "
                  f"{f2(r['E_phase'], 3)} | {f2(r['S_total'])} | {f2(r['E_total'], 3)} |")
    return md


def io_table() -> list[str]:
    """Cały przebieg z zapisem wyniku (etap 11, grupa io): S(8) przy zebraniu na proces 0 i przy MPI-IO."""
    md = ["| Przypadek (zapis) | Kompilator | T(1) total, gather [ms] | S(8) total, gather | S(8) total, MPI-IO | "
          "S(8) faza | udział zapisu w total przy 8 procesach: gather / MPI-IO |", "|---|---|---|---|---|---|---|"]
    for comp in COMPILERS:
        files = sorted((RES / "mpi_io").glob(f"pomiar_{comp}*_raw.csv"))
        groups: dict[tuple[str, str], list[dict]] = {}
        for p in files:
            if comp == "gcc" and "romio" in p.name:
                continue
            for r in read_csv(p):
                if r["case"].startswith("io_"):
                    groups.setdefault((r["case"], r["variant"]), []).append(r)
        for cid in ("io_bin_classic_300", "io_txt_classic_300", "io_bin_classic_2000", "io_txt_classic_2000"):
            med = {}
            for v in ("m1", "m8", "m8i"):
                rs = groups.get((cid, v), [])
                if rs:
                    med[v] = {k: statistics.median([float(r[k]) for r in rs if r.get(k)]) for k in
                              ("total", "caSim", "save")}
            t1 = med.get("m1")
            if "m8" not in med or "m8i" not in med or t1 is None:
                continue
            lbl = cid.replace("io_", "").replace("_classic_", " classic ").replace("300", "300³").replace("2000",
                                                                                                          "2000²")
            s_g = t1["total"] / med["m8"]["total"]
            s_i = t1["total"] / med["m8i"]["total"]
            s_ph = t1["caSim"] / med["m8"]["caSim"]
            md.append(f"| {lbl} | {comp} | {fms(t1['total'])} | {f2(s_g)} | {f2(s_i)} | {f2(s_ph)} | "
                      f"{100 * med['m8']['save'] / med['m8']['total']:.0f}% / "
                      f"{100 * med['m8i']['save'] / med['m8i']['total']:.0f}% |")
    return md


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    rows, chain = [], []
    for comp in COMPILERS:
        r, c = collect(comp)
        rows += r
        chain += c
    OUT.mkdir(parents=True, exist_ok=True)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(OUT / "zestawienie.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    with open(OUT / "zestawienie_lacznie.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(chain[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(chain)

    md = ["# Zestawienie przyspieszenia i efektywności (etapy 8–11)", "",
          "Bez nowych przebiegów — `python bench/zestawienie.py` czyta CSV etapów 8–11. S = T(1)/T(p), E = S/p, "
          "f — część szeregowa z dopasowania prawa Amdahla (z tabel etapów 9 i 10, warianty jednego rodzaju); "
          "„faza” = `caSim` / `mcSim`, „total” = cały przebieg. T(1) i T(p) zawsze z tej samej sesji pomiarowej. "
          f"Warunki wszystkich wierszy: {COND} (etap 8 — 1 rdzeń P); każdy przebieg etapów 9–11 bitowo zgodny "
          "z wariantem odniesienia.", ""]
    for comp, cdef in COMPILERS.items():
        md += [f"## {cdef['name']} — S / E fazy obliczeń przy 7–8 rdzeniach", ""]
        md += summary_table(rows, comp) + [""]
    md += ["## Łączne przyspieszenie od programu sprzed optymalizacji (faza obliczeń)", "",
           "Iloczyn ilorazów z sesji: algorytm (etap 8: profil `_przed2` / `_po`, ta sama sesja) × szachownica przy "
           "1 wątku (MC, etap 9: random / szachownica, ta sama sesja) × równoległość (T(1) / T(p) w sesji najlepszego "
           "wariantu). Kolumna „wprost” dzieli czasy z różnych dni — kontrola.", ""]
    md += chain_table(chain) + ["", "¹ GCC nie mierzył wariantu random w sesji etapu 9 — szachownica wprost: po etapie 8 "
                                "(profil `_po`, wariant random) / szachownica przy 1 wątku (etap 9), dwie sesje.", ""]
    md += ["## Cały przebieg z zapisem wyniku (etap 11)", "",
           "Grupa `io` etapu 11, MSVC / MS-MPI (T(1) = m1 gather tej samej sesji; GCC mierzono tylko przy 8 procesach "
           "— `bench/results/mpi_io/pomiar_gcc*.md`):", ""]
    md += io_table() + [""]
    md += ["## Przyspieszenie ponadliniowe (E > 1)", ""]
    md += superlinear(rows) + [""]
    for comp, cdef in COMPILERS.items():
        md += [f"## Wszystkie warianty — {cdef['name']}", ""]
        md += long_table(rows, comp) + [""]
    with open(OUT / "zestawienie.md", "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(md) + "\n")
    print("\n".join(md[:60]))
    print(f"Zapisano {rel(OUT / 'zestawienie.md')}, zestawienie.csv ({len(rows)} wierszy), zestawienie_lacznie.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
