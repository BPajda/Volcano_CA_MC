#!/usr/bin/env python3
"""Test A/B: porównanie czasu i wyników dwóch lub więcej programów engine na stałym zestawie przypadków.

Każdy przypadek jest uruchamiany NAPRZEMIENNIE wszystkimi programami (A B, potem B A, A B …: kolejność odwracana
co powtórzenie, żeby dryf temperatury i turbo rozkładał się równo), proces przypięty do jednego procesora logicznego
(domyślnie 2 — rdzeń P i9-13900HX, jak bench/run_profile.py), na Windows z priorytetem HIGH_PRIORITY_CLASS.
Czas: sekcje z times.json (caSim, mcSim, mcStats, save, total, …) oraz czas procesu (zegar ścienny od startu do
końca procesu i czas procesora). Po każdym powtórzeniu wyniki każdego programu są porównywane BITOWO z wynikiem
pierwszego programu (wszystkie pliki folderu wyników poza times.json i config_used.json; stats.json przy różnicy
bajtowej — jeszcze raz jako JSON bez pól z czasem). Różnica jest zgłaszana głośno i zaznaczana w tabeli.

Wyniki (bench/results/ab/<nazwa>*): <nazwa>_raw.csv (każdy przebieg), <nazwa>.csv (mediana, min, max na przypadek
i program), <nazwa>.md (tabela: przypadek, mediana [min–max] każdego programu, stosunki, zgodność).

Przykłady (z katalogu projektu):
    python bench/ab.py --bin przed=bench/baseline/engine_przed_msvc.exe --bin nowy=build/Release/engine.exe
    python bench/ab.py --bin przed=... --bin krok3=... --bin krok4=... --groups ca_lava,ca_classic
    python bench/ab.py --bin full=build/Release/engine.exe --bin front=build/Release/engine.exe \\
                       --args "full=--set ca.sweep=full" --groups ca_lava
    python bench/ab.py --wsl --bin przed=bench/baseline/engine_przed_gcc --bin nowy=build-gcc-release/bin/engine

--wsl: ten sam skrypt uruchamiany w WSL (python3), programy GCC kopiowane do /tmp (ext4), configi, mapy wysokości
i wyniki przebiegów też na /tmp — bez narzutu 9P; tabela i CSV zapisywane w bench/results/ab/. Przypięcie:
sched_setaffinity (wirtualny procesor WSL2), bez zmiany priorytetu.

Zależności: biblioteka standardowa; psutil opcjonalnie (Windows: przypięcie, kontrola dziedziczenia, obciążenie tła).
"""

from __future__ import annotations

import argparse
import copy
import csv
import datetime as dt
import filecmp
import json
import os
import shlex
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

try:
    import psutil  # opcjonalnie
except ImportError:  # pragma: no cover
    psutil = None
if os.name != "nt":
    import resource  # czas procesora procesów potomnych (Linux/WSL)

ROOT = Path(__file__).resolve().parent.parent
CONFIGS = ROOT / "configs"
IS_WINDOWS = os.name == "nt"
SECTIONS = ["readConfig", "allocate", "terrain", "vents", "caSim", "caStats", "save", "mcInit", "mcSim", "mcStats",
            "mcSave",
            "total"]
SKIP_FILES = {"times.json", "config_used.json"}  # czas przebiegu; config zawiera nowe klucze nowszego programu
# Klucze stats.json opisujące sposób liczenia, nie wynik (etap 9): liczba wątków, harmonogram, przypięcie (sekcja
# "parallel") i wariant MC (mc.update — pole dopisane w etapie 9). Pomijane przy porównaniu z programem sprzed etapu 9
# i między liczbami wątków; różne warianty MC (random / checkerboard) różnią się i tak całą resztą wyników.
RUN_KEYS = ("parallel", "update")


# ---------------------------------------------------------------------------
# Zestaw przypadków — STAŁY przez cały etap 8 (porównywalność tabel). reps = liczba powtórzeń (szybkie: więcej).
# ---------------------------------------------------------------------------
def deep_update(base: dict, patch: dict) -> dict:
    """Scala słownik patch z base (rekurencyjnie) i zwraca base."""
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            deep_update(base[k], v)
        else:
            base[k] = copy.deepcopy(v)
    return base


def from_file(name: str, patch: dict | None = None) -> dict:
    """Config z configs/<name>.json z nadpisaniami."""
    with open(CONFIGS / f"{name}.json", encoding="utf-8") as f:
        return deep_update(json.load(f), patch or {})


def classic(n: tuple[int, int, int], seeds: int, nb: str, fmt: str = "both") -> dict:
    """Klasyczny rozrost ziaren CA, brzeg periodyczny (jak w profilu z etapu 3)."""
    return {"space": {"nx": n[0], "ny": n[1], "nz": n[2]}, "grid": "vector", "boundary": "periodic",
            "neighborhood": nb, "rngSeed": 42, "vents": {"count": seeds}, "ca": {"mode": "classic", "maxSteps": 65535},
            "mc": {"enabled": False}, "output": {"format": fmt}}


def cases() -> list[dict]:
    """Lista przypadków: id, grupa, config, miary główne, liczba powtórzeń."""
    mc3 = {"mc": {"mcs": 100}}
    return [
        {"id": "lava_test_3d", "group": "ca_lava", "config": from_file("test_3d"), "metrics": ["caSim"], "reps": 7},
        {"id": "lava_etna_real", "group": "ca_lava", "config": from_file("etna_real"), "metrics": ["caSim"],
         "reps": 5},
        {"id": "lava_mc_2d_ca", "group": "ca_lava", "config": from_file("lava_mc_2d", {"mc": {"enabled": False}}),
         "metrics": ["caSim"], "reps": 11},
        {"id": "classic_1000x1000_s100_vn", "group": "ca_classic",
         "config": classic((1000, 1000, 1), 100, "von_neumann"), "metrics": ["caSim", "save"], "reps": 7},
        {"id": "classic_1000x1000_s100_moore", "group": "ca_classic",
         "config": classic((1000, 1000, 1), 100, "moore"), "metrics": ["caSim"], "reps": 7},
        {"id": "classic_100x100x100_s10_vn", "group": "ca_classic",
         "config": classic((100, 100, 100), 10, "von_neumann"), "metrics": ["caSim", "save"], "reps": 9},
        {"id": "classic_100x100x100_s10_moore", "group": "ca_classic",
         "config": classic((100, 100, 100), 10, "moore"), "metrics": ["caSim"], "reps": 9},
        {"id": "classic_300x300x300_s100_vn", "group": "ca_classic",
         "config": classic((300, 300, 300), 100, "von_neumann", fmt="bin"), "metrics": ["caSim", "save"], "reps": 5},
        {"id": "mc_full_2d_200", "group": "mc", "config": from_file("mc_full_2d"), "metrics": ["mcSim", "mcStats"],
         "reps": 11},
        {"id": "mc_full_2d_1000", "group": "mc",
         "config": from_file("mc_full_2d", {"space": {"nx": 1000, "ny": 1000, "nz": 1}}),
         "metrics": ["mcSim", "mcStats", "mcSave"], "reps": 5},
        {"id": "mc_full_3d_50", "group": "mc", "config": from_file("mc_full_3d", mc3), "metrics": ["mcSim", "mcStats"],
         "reps": 7},
        {"id": "mc_full_3d_100", "group": "mc",
         "config": from_file("mc_full_3d", {"space": {"nx": 100, "ny": 100, "nz": 100},
                                            "mc": {"mcs": 100, "statsEvery": 10}}),
         "metrics": ["mcSim", "mcStats", "mcSave"], "reps": 5},
        {"id": "lava_mc_3d", "group": "mc", "config": from_file("lava_mc_3d"), "metrics": ["mcSim", "caSim"],
         "reps": 7},
    ]


# ---------------------------------------------------------------------------
# Środowisko: przypięcie, tło, czas procesu
# ---------------------------------------------------------------------------
def pin_self(cpu: int) -> str:
    """Przypina proces skryptu do procesora logicznego cpu; procesy potomne dziedziczą maskę."""
    if IS_WINDOWS:
        if psutil is not None:
            psutil.Process().cpu_affinity([cpu])
            return f"psutil.cpu_affinity([{cpu}])"
        import ctypes
        k32 = ctypes.windll.kernel32
        if not k32.SetProcessAffinityMask(k32.GetCurrentProcess(), ctypes.c_size_t(1 << cpu)):
            raise OSError("SetProcessAffinityMask nie powiodło się")
        return f"SetProcessAffinityMask(1 << {cpu})"
    os.sched_setaffinity(0, {cpu})
    return f"sched_setaffinity({{{cpu}}}) (WSL2: procesor wirtualny)"


# Procesy, których nazwy zapisujemy w wynikach (system, narzędzia programistyczne); każda inna nazwa trafia do
# plików jako „inny program” — wyniki są w repozytorium publicznym, a lista programów użytkownika do nich nie należy.
PUBLIC_PROCESSES = {
    "python.exe", "python3", "svchost.exe", "wmiprvse.exe", "msmpeng.exe", "system", "registry", "vmmem",
    "vmmemwsl", "wslservice.exe", "wsl.exe", "explorer.exe", "dwm.exe", "searchindexer.exe", "searchprotocolhost.exe",
    "compattelrunner.exe", "backgrounddownload.exe", "tiworker.exe", "trustedinstaller.exe", "audiodg.exe",
    "csrss.exe", "conhost.exe", "powershell.exe", "cmd.exe", "bash.exe", "code.exe", "msbuild.exe", "cl.exe",
    "engine.exe", "memory compression", "system idle process",
}


def public_name(name: str) -> str:
    """Nazwa procesu do zapisu w wynikach: z listy PUBLIC_PROCESSES albo „inny program”."""
    return name if (name or "").lower() in PUBLIC_PROCESSES else "inny program"


def background_load(seconds: float = 2.0) -> dict:
    """Obciążenie CPU przez inne programy [% całego CPU] i 5 największych procesów (Windows, psutil;
    nazwy spoza PUBLIC_PROCESSES jako „inny program”)."""
    if psutil is None:
        return {}
    procs = list(psutil.process_iter(["name"]))
    for p in procs:
        try:
            p.cpu_percent(None)
        except psutil.Error:
            pass
    total = psutil.cpu_percent(interval=seconds)
    top = []
    for p in procs:
        try:
            if p.pid != 0:
                top.append((p.cpu_percent(None), p.info["name"]))
        except psutil.Error:
            pass
    top.sort(reverse=True)
    return {"totalPercent": total, "top": [f"{public_name(n)} {c:.0f}%" for c, n in top[:5]]}


def process_cpu_seconds(proc: subprocess.Popen) -> float | None:
    """Czas procesora (użytkownik + system) zakończonego procesu potomnego [s] — Windows: GetProcessTimes."""
    if not IS_WINDOWS:
        return None
    import ctypes
    import ctypes.wintypes as wt
    c, e, k, u = wt.FILETIME(), wt.FILETIME(), wt.FILETIME(), wt.FILETIME()
    handle = int(proc._handle)  # uchwyt trzymany przez Popen do zamknięcia obiektu
    if not ctypes.windll.kernel32.GetProcessTimes(wt.HANDLE(handle), ctypes.byref(c), ctypes.byref(e),
                                                  ctypes.byref(k), ctypes.byref(u)):
        return None
    to_s = lambda ft: ((ft.dwHighDateTime << 32) | ft.dwLowDateTime) / 1e7  # noqa: E731 (jednostki 100 ns)
    return to_s(k) + to_s(u)


def wsl_path(p: Path) -> str:
    """C:\\a\\b -> /mnt/c/a/b"""
    s = str(Path(p).resolve())
    return f"/mnt/{s[0].lower()}{s[2:]}".replace("\\", "/")


# ---------------------------------------------------------------------------
# Porównanie wyników
# ---------------------------------------------------------------------------
def strip_times(obj, ignore: tuple[str, ...] = ()):
    """JSON bez pól z czasem (nazwy kończące się na Ms/ms, zawierające time/seconds) i bez kluczy ignore."""
    if isinstance(obj, dict):
        return {k: strip_times(v, ignore) for k, v in obj.items()
                if not (k.lower().endswith("ms") or "time" in k.lower() or "seconds" in k.lower() or k in ignore)}
    if isinstance(obj, list):
        return [strip_times(v, ignore) for v in obj]
    return obj


def compare_dirs(ref: Path, other: Path, eol: bool = False, ignore_keys: tuple[str, ...] = ()) -> list[str]:
    """Różnice folderu wyników other względem ref (pusta lista = bitowo zgodne).
    eol=True: pliki tekstowe porównywane bez różnicy CRLF/LF (MSVC na Windows zapisuje txt/csv w trybie tekstowym,
    GCC na Linuksie — LF); ignore_keys: klucze JSON pomijane w stats.json (np. ścieżka folderu wejściowego) — zawsze
    także RUN_KEYS (opis liczenia: wątki, harmonogram, wariant MC)."""
    ignore_keys = tuple(ignore_keys) + RUN_KEYS
    diffs = []
    files_ref = {p.relative_to(ref) for p in ref.rglob("*") if p.is_file() and p.name not in SKIP_FILES}
    files_oth = {p.relative_to(other) for p in other.rglob("*") if p.is_file() and p.name not in SKIP_FILES}
    for f in sorted(files_ref ^ files_oth):
        diffs.append(f"brak pliku {f} w {'B' if f in files_ref else 'A'}")
    for f in sorted(files_ref & files_oth):
        a, b = ref / f, other / f
        if filecmp.cmp(a, b, shallow=False):
            continue
        if f.suffix == ".json":
            with open(a, encoding="utf-8") as fa, open(b, encoding="utf-8") as fb:
                if strip_times(json.load(fa), ignore_keys) == strip_times(json.load(fb), ignore_keys):
                    continue  # różnią się tylko pola z czasem / pominięte klucze
        if eol and f.suffix in (".txt", ".csv"):
            if a.read_bytes().replace(b"\r\n", b"\n") == b.read_bytes().replace(b"\r\n", b"\n"):
                continue
        diffs.append(f"różny plik {f}")
    return diffs


# ---------------------------------------------------------------------------
# Pomiar
# ---------------------------------------------------------------------------
class Bench:
    def __init__(self, args: argparse.Namespace, tmp: Path):
        self.args = args
        self.tmp = tmp
        self.flags = subprocess.HIGH_PRIORITY_CLASS if IS_WINDOWS else 0
        self.pin_note_shown = False

    def prepare_config(self, case: dict) -> Path:
        """Config przypadku w folderze tymczasowym; mapa wysokości kopiowana obok (ścieżka bezwzględna)."""
        cfg = copy.deepcopy(case["config"])
        terrain = cfg.get("terrain", {})
        if terrain.get("type") == "file" and terrain.get("file"):
            src = ROOT / terrain["file"]
            dst = self.tmp / "heightmaps" / src.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists():
                shutil.copy(src, dst)
            terrain["file"] = str(dst)
        path = self.tmp / "configs" / f"{case['id']}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return path

    def run(self, exe: str, extra: list[str], cfg: Path, out: Path) -> dict:
        """Jeden przebieg programu; zwraca miary (times.json + czas procesu)."""
        shutil.rmtree(out, ignore_errors=True)
        cmd = [exe, "--config", str(cfg), "--out", str(out)] + self.args.set_args + extra
        ru0 = None if IS_WINDOWS else resource.getrusage(resource.RUSAGE_CHILDREN)
        t0 = time.perf_counter()
        proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                creationflags=self.flags)
        if IS_WINDOWS and psutil is not None and not self.pin_note_shown:
            try:  # kontrola dziedziczenia maski powinowactwa (raz)
                aff = psutil.Process(proc.pid).cpu_affinity()
                if aff != [self.args.cpu]:
                    print(f"UWAGA: proces potomny ma maskę {aff}, ustawiam [{self.args.cpu}]", file=sys.stderr)
                    psutil.Process(proc.pid).cpu_affinity([self.args.cpu])
                self.pin_note_shown = True
            except psutil.Error:
                pass
        _, err = proc.communicate()
        wall = time.perf_counter() - t0
        if IS_WINDOWS:
            cpu_s = process_cpu_seconds(proc)
        else:
            ru1 = resource.getrusage(resource.RUSAGE_CHILDREN)
            cpu_s = (ru1.ru_utime - ru0.ru_utime) + (ru1.ru_stime - ru0.ru_stime)
        if proc.returncode != 0:
            raise RuntimeError(f"{exe} zakończony kodem {proc.returncode}: {err.decode('utf-8', 'replace')[-500:]}")
        with open(out / "times.json", encoding="utf-8") as f:
            times = json.load(f)
        row = {s: times[s] for s in SECTIONS if s in times}
        row["steps"] = times.get("steps")
        row["procWall"] = round(wall * 1000.0, 3)
        row["procCpu"] = round(cpu_s * 1000.0, 3) if cpu_s is not None else None
        return row


def fmt_ms(v: float) -> str:
    """Czas [ms] do tabeli: 3 cyfry znaczące dla małych, bez miejsc po przecinku dla dużych."""
    if v >= 1000:
        return f"{v:,.0f}".replace(",", " ")
    if v >= 100:
        return f"{v:.0f}"
    if v >= 10:
        return f"{v:.1f}"
    return f"{v:.2f}"


def summarize(raw: list[dict], labels: list[str], plan: list[dict]) -> tuple[list[dict], list[str]]:
    """Mediana/min/max każdej miary na przypadek × program, stosunki i tabela Markdown."""
    summary = []
    md = []
    head = "| Przypadek | miara | " + " | ".join(f"{l} [ms]" for l in labels)
    ratio_cols = [f"{l}/{labels[0]}" for l in labels[1:]]
    if len(labels) > 2:
        ratio_cols += [f"{labels[i]}/{labels[i - 1]}" for i in range(2, len(labels))]
    head += " | " + " | ".join(ratio_cols) + " | zgodne |"
    md.append(head)
    md.append("|" + "---|" * (2 + len(labels) + len(ratio_cols) + 1))
    for case in plan:
        rows = [r for r in raw if r["case"] == case["id"]]
        if not rows:
            continue
        same = all(r["identical"] for r in rows if r["label"] != labels[0])
        for metric in case["metrics"] + ["total", "procWall"]:
            stats = {}
            for l in labels:
                vals = [r[metric] for r in rows if r["label"] == l and r.get(metric) is not None]
                if vals:
                    stats[l] = (statistics.median(vals), min(vals), max(vals), len(vals))
            if len(stats) != len(labels):
                continue
            entry = {"case": case["id"], "group": case["group"], "metric": metric}
            for l, (med, lo, hi, n) in stats.items():
                entry.update({f"{l}_med": med, f"{l}_min": lo, f"{l}_max": hi, f"{l}_n": n})
            cells = [f"{fmt_ms(stats[l][0])} [{fmt_ms(stats[l][1])}–{fmt_ms(stats[l][2])}]" for l in labels]
            ratios = []
            pairs = [(l, labels[0]) for l in labels[1:]]
            if len(labels) > 2:
                pairs += [(labels[i], labels[i - 1]) for i in range(2, len(labels))]
            for num, den in pairs:
                r = stats[num][0] / stats[den][0] if stats[den][0] > 0 else float("nan")
                entry[f"{num}/{den}"] = r
                ratios.append(f"×{r:.3f}")
            summary.append(entry)
            md.append(f"| {case['id']} | {metric} | " + " | ".join(cells) + " | " + " | ".join(ratios) +
                      f" | {'tak' if same else '**NIE**'} |")
    return summary, md


def resummarize(args: argparse.Namespace, plan: list[dict]) -> int:
    """Tabela z już zapisanego pomiaru: podzbiór programów i przypadków jednego przebiegu naprzemiennego
    (np. z porównania przed / k1 / k2 tylko przed / k1 dla grup CA). Zgodność = zgodność wybranych programów
    z pierwszym z nich (w surowym pliku jest zgodność z pierwszym programem pomiaru — dla A = ten sam program
    wystarcza; inaczej wymagamy zgodności obu z odniesieniem pomiaru). Kilka plików po przecinku: jedna tabela
    z pomiaru podzielonego na części (np. osobno grupy ca_lava, ca_classic, mc — każda część to pełny przebieg
    naprzemienny tych samych programów)."""
    srcs = [Path(p.strip()) for p in args.from_raw.split(",") if p.strip()]
    src = srcs[0]
    rows = []
    for s in srcs:
        with open(s, encoding="utf-8") as f:
            rows += list(csv.DictReader(f))
    labels = [l.strip() for l in (args.labels or "").split(",") if l.strip()]
    if len(labels) < 2:
        print("--from-raw wymaga --labels z co najmniej dwiema etykietami", file=sys.stderr)
        return 2
    ids = {c["id"] for c in plan}
    raw = []
    for r in rows:
        if r["label"] not in labels or r["case"] not in ids:
            continue
        conv = dict(r)
        for k in [*SECTIONS, "steps", "procWall", "procCpu"]:
            conv[k] = float(r[k]) if r.get(k) not in (None, "") else None
        conv["identical"] = r.get("identical") in ("True", "true", "1")
        raw.append(conv)
    summary, md = summarize(raw, labels, plan)
    name = args.name or src.stem.replace("_raw", "") + "_" + "_".join(labels)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    if summary:
        skeys = list(dict.fromkeys(k for s in summary for k in s))
        with open(out_dir / f"{name}.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=skeys, lineterminator="\n")
            w.writeheader()
            w.writerows(summary)
    header = [f"# Test A/B `{name}`", ""]
    if args.note:
        header += [args.note, ""]
    raw_names = ", ".join(f"`{s.name}`" for s in srcs)
    md_names = ", ".join("`" + s.stem.replace("_raw", "") + ".md`" for s in srcs)
    header += [f"- Tabela z pomiaru {raw_names} (te same przebiegi naprzemienne; programy {', '.join(labels)}; "
               f"warunki pomiaru i tło — w nagłówku {md_names})", ""]
    with open(out_dir / f"{name}.md", "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(header + md) + "\n")
    print("\n".join(md))
    print(f"Zapisano {out_dir / (name + '.md')}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bin", action="append", default=[], metavar="ETYKIETA=ŚCIEŻKA",
                    help="program do porównania (pierwszy = odniesienie A); można podać wiele")
    ap.add_argument("--args", action="append", default=[], metavar="ETYKIETA=ARGUMENTY",
                    help='dodatkowe argumenty jednego programu, np. "full=--set ca.sweep=full"')
    ap.add_argument("--set", dest="set_values", action="append", default=[], metavar="KLUCZ=WARTOŚĆ",
                    help="nadpisanie configu dla wszystkich programów (--set silnika)")
    ap.add_argument("--groups", default="ca_lava,ca_classic,mc", help="grupy: ca_lava, ca_classic, mc")
    ap.add_argument("--cases", help="tylko wybrane przypadki (id po przecinku)")
    ap.add_argument("--reps", type=int, help="powtórzenia każdego przypadku (domyślnie z tabeli, min. 5)")
    ap.add_argument("--min-reps", type=int, default=5, help="minimalna liczba powtórzeń (domyślnie 5)")
    ap.add_argument("--cpu", type=int, default=2, help="procesor logiczny do przypięcia (domyślnie 2 — rdzeń P)")
    ap.add_argument("--name", help="nazwa zestawu wyników (domyślnie ab_<data>_<godzina>)")
    ap.add_argument("--out", default=str(ROOT / "bench" / "results" / "ab"), help="folder wyników")
    ap.add_argument("--note", default="", help="opis porównania do nagłówka tabeli")
    ap.add_argument("--keep", action="store_true", help="zostaw foldery wyników przebiegów")
    ap.add_argument("--list", action="store_true", help="wypisz przypadki i zakończ")
    ap.add_argument("--wsl", action="store_true", help="uruchom pomiar w WSL (programy GCC)")
    ap.add_argument("--inside-wsl", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--from-raw", metavar="PLIK_RAW_CSV",
                    help="bez pomiaru: nowa tabela z istniejącego <nazwa>_raw.csv (wybrane --labels, --groups); "
                         "kilka plików po przecinku — jedna tabela z pomiaru podzielonego na części")
    ap.add_argument("--labels", help="z --from-raw: programy do tabeli (etykiety po przecinku, pierwszy = A)")
    args = ap.parse_args()
    if not sys.stdout.isatty():
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    groups = {g.strip() for g in args.groups.split(",") if g.strip()}
    plan = [c for c in cases() if c["group"] in groups]
    if args.cases:
        wanted = [c.strip() for c in args.cases.split(",")]
        plan = [c for c in cases() if c["id"] in wanted]
    if args.list:
        for c in cases():
            print(f"{c['group']:10s} {c['id']:32s} reps {c['reps']:2d}  miary {', '.join(c['metrics'])}")
        return 0
    if args.from_raw:
        return resummarize(args, plan)
    if len(args.bin) < 2:
        ap.error("podaj co najmniej dwa programy --bin (pierwszy = odniesienie)")
    for c in plan:
        c["reps"] = max(args.min_reps, args.reps if args.reps else c["reps"])
    name = args.name or "ab_" + dt.datetime.now().strftime("%Y-%m-%d_%H%M")

    # --- tryb --wsl: ten sam skrypt w WSL, ścieżki przetłumaczone, tło mierzone po stronie Windows ---
    if args.wsl and not args.inside_wsl:
        load_start = background_load()
        conv = []
        for b in args.bin:
            label, path = b.split("=", 1)
            conv += ["--bin", f"{label}={wsl_path(ROOT / path if not Path(path).is_absolute() else Path(path))}"]
        rest = []
        for a in args.args:
            rest += ["--args", a]
        for s in args.set_values:
            rest += ["--set", s]
        if args.cases:
            rest += ["--cases", args.cases]
        if args.reps:
            rest += ["--reps", str(args.reps)]
        if args.keep:
            rest.append("--keep")
        cmd = ["wsl", "-e", "env", "PYTHONIOENCODING=utf-8", "python3", wsl_path(Path(__file__)), "--inside-wsl",
               *conv, *rest, "--groups", args.groups, "--min-reps", str(args.min_reps), "--cpu", str(args.cpu),
               "--name", name, "--out", wsl_path(Path(args.out))]
        if args.note:  # pusty argument wsl.exe odrzuca (Wsl/Service/E_INVALIDARG)
            cmd += ["--note", args.note]
        r = subprocess.run(cmd)
        load_end = background_load()
        md = Path(args.out) / f"{name}.md"
        if md.exists() and load_start:
            with open(md, "a", encoding="utf-8", newline="\n") as f:
                f.write(f"\nTło (Windows, poza WSL): start {load_start['totalPercent']:.0f}% "
                        f"({', '.join(load_start['top'][:3])}), koniec {load_end.get('totalPercent', 0):.0f}%.\n")
        return r.returncode

    labels, exes = [], {}
    for b in args.bin:
        label, path = b.split("=", 1)
        p = Path(path)
        exes[label] = str(p if p.is_absolute() else (ROOT / p))
        labels.append(label)
    extra = {l: [] for l in labels}
    for a in args.args:
        label, rest = a.split("=", 1)
        extra[label] = shlex.split(rest)
    args.set_args = [x for s in args.set_values for x in ("--set", s)]

    if args.inside_wsl:
        tmp = Path("/tmp/volcano_ab")
        shutil.rmtree(tmp / "run", ignore_errors=True)
        (tmp / "bin").mkdir(parents=True, exist_ok=True)
        for l in labels:  # program na ext4 maszyny WSL (start z /mnt/d przez 9P jest wolny)
            dst = tmp / "bin" / f"engine_{l}"
            shutil.copy(exes[l], dst)
            os.chmod(dst, 0o755)
            exes[l] = str(dst)
        tmp = tmp / "run"
        tmp.mkdir(parents=True, exist_ok=True)
    else:
        tmp = Path(tempfile.mkdtemp(prefix="volcano_ab_"))
    for l in labels:
        if not Path(exes[l]).exists():
            print(f"Brak programu {exes[l]}", file=sys.stderr)
            return 2

    pin = pin_self(args.cpu)
    load_start = background_load()
    bench = Bench(args, tmp)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"A/B {name}: {', '.join(f'{l}={exes[l]}' for l in labels)}")
    print(f"Przypięcie: {pin}; przypadków {len(plan)}, przebiegów {sum(c['reps'] for c in plan) * len(labels)}")
    if load_start:
        print(f"Tło: {load_start['totalPercent']:.0f}% CPU ({', '.join(load_start['top'][:3])})")

    # Rozgrzewka: każdy program raz na małym przypadku (plik programu w pamięci podręcznej systemu).
    warm = {"id": "_rozgrzewka", "config": classic((60, 60, 1), 5, "von_neumann", fmt="bin")}
    wcfg = bench.prepare_config(warm)
    for l in labels:
        bench.run(exes[l], extra[l], wcfg, tmp / "out" / f"warm_{l}")

    cfgs = {c["id"]: bench.prepare_config(c) for c in plan}
    raw: list[dict] = []
    failures = 0
    t_start = time.time()
    max_reps = max(c["reps"] for c in plan)
    for rep in range(max_reps):
        for case in plan:
            if rep >= case["reps"]:
                continue
            order = labels if rep % 2 == 0 else list(reversed(labels))
            outs = {}
            for pos, l in enumerate(order):
                out = tmp / "out" / f"{case['id']}__{l}__{rep}"
                row = bench.run(exes[l], extra[l], cfgs[case["id"]], out)
                row.update({"name": name, "case": case["id"], "group": case["group"], "label": l, "rep": rep,
                            "position": pos, "timestamp": dt.datetime.now().isoformat(timespec="seconds")})
                outs[l] = (out, row)
                raw.append(row)
            ref_out = outs[labels[0]][0]
            outs[labels[0]][1]["identical"] = True
            for l in labels[1:]:
                diffs = compare_dirs(ref_out, outs[l][0])
                outs[l][1]["identical"] = not diffs
                outs[l][1]["diffs"] = "; ".join(diffs)
                if diffs:
                    failures += 1
                    print(f"!!! RÓŻNICA WYNIKÓW: {case['id']} rep {rep}: {l} vs {labels[0]}: {'; '.join(diffs)}",
                          file=sys.stderr, flush=True)
            main_metric = case["metrics"][0]
            print(f"[{rep + 1}/{case['reps']}] {case['id']:32s} " +
                  "  ".join(f"{l} {outs[l][1].get(main_metric, 0):9.1f}" for l in labels) + f"  ({main_metric})",
                  flush=True)
            if not args.keep:
                for out, _ in outs.values():
                    shutil.rmtree(out, ignore_errors=True)
    load_end = background_load()
    minutes = (time.time() - t_start) / 60

    # --- zapis: surowe przebiegi, podsumowanie, tabela Markdown ---
    keys = ["name", "case", "group", "label", "rep", "position", "timestamp", *SECTIONS, "steps", "procWall",
            "procCpu", "identical", "diffs"]
    with open(out_dir / f"{name}_raw.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        w.writerows(raw)
    summary, md = summarize(raw, labels, plan)
    if summary:
        skeys = list(dict.fromkeys(k for s in summary for k in s))
        with open(out_dir / f"{name}.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=skeys, lineterminator="\n")
            w.writeheader()
            w.writerows(summary)
    header = [f"# Test A/B `{name}`", ""]
    if args.note:
        header += [args.note, ""]
    header += [f"- Programy: " + ", ".join(f"`{l}` = `{Path(exes[l]).name}`" +
                                          (f" `{' '.join(extra[l])}`" if extra[l] else "") for l in labels),
               f"- Przypięcie: {pin}; priorytet: {'HIGH_PRIORITY_CLASS' if IS_WINDOWS else 'domyślny'}; "
               f"kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń",
               f"- Czas pomiaru: {minutes:.1f} min, {dt.datetime.now().isoformat(timespec='minutes')}"]
    if args.set_values:
        header.append(f"- Nadpisania configu (wszystkie programy): {', '.join(args.set_values)}")
    if load_start:
        header.append(f"- Tło: start {load_start['totalPercent']:.0f}% CPU ({', '.join(load_start['top'][:3])}), "
                      f"koniec {load_end.get('totalPercent', 0):.0f}%")
    header.append(f"- Zgodność wyników z `{labels[0]}`: " +
                  ("wszystkie przebiegi bitowo zgodne" if failures == 0 else f"**{failures} różnic**"))
    header.append("")
    with open(out_dir / f"{name}.md", "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(header + md) + "\n")
    print("\n".join(md))
    print(f"Zapisano {out_dir / (name + '.md')} ({minutes:.1f} min); różnic wyników: {failures}")
    if not args.keep and not args.inside_wsl:
        shutil.rmtree(tmp, ignore_errors=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
