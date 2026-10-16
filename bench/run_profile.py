#!/usr/bin/env python3
"""Profil aplikacji (etap 3): automatyczna macierz pomiarów silnika volcano-ca-mc.

Skrypt generuje configi do folderu tymczasowego, uruchamia program engine dla każdego
wariantu (domyślnie 3 powtórzenia), zbiera times.json (czasy etapów, szczytowa pamięć
procesu + model teoretyczny, rozmiary i czasy zapisu plików) i zapisuje:

    bench/results/<nazwa>.csv        — jeden wiersz na wariant × build: mediana, min, max,
                                       odchylenie standardowe każdej miary (+ parametry wariantu),
    bench/results/<nazwa>_raw.csv    — każde powtórzenie osobno,
    bench/results/<nazwa>_raw.jsonl  — to samo przyrostowo (wznawianie przerwanego pomiaru),
    bench/results/<nazwa>_meta.json  — sprzęt, system, kompilatory, flagi, przypięcie do rdzenia,
    bench/results/<nazwa>_benchmark.csv — tabela vector vs macierz (engine --benchmark).

Domyślna nazwa: profile_<RRRR-MM-DD> (z --quick: profile_<data>_quick). Wyniki z etapu 3 są
punktem odniesienia dla dalszej optymalizacji — nie nadpisujemy ich: ponowne uruchomienie z tą samą nazwą
DOPISUJE brakujące pomiary (wznowienie), a nowy pomiar innego dnia dostaje nową datę.

Przypięcie do rdzenia: na Windows proces skryptu ustawia sobie maskę powinowactwa (psutil,
a bez niego SetProcessAffinityMask przez ctypes) — procesy potomne ją dziedziczą, co działa
jak `start /affinity` z benchmarku etapu 1, ale bez pośrednictwa cmd (cytowanie ścieżek ze
spacjami, kod wyjścia, stderr). Domyślnie procesor logiczny 2: rdzeń wydajnościowy (P) i8-13900HX
to procesory 0–15, a procesor 0 obsługuje najwięcej przerwań. Silnik dostaje też priorytet
HIGH_PRIORITY_CLASS. W WSL: `taskset -c <cpu>` (uwaga: to wirtualny procesor maszyny WSL2 —
host może go planować na dowolnym rdzeniu fizycznym).

Użycie (z katalogu volcano-ca-mc):
    python bench/run_profile.py --quick                 # szybkie sprawdzenie (~1 min)
    python bench/run_profile.py --full --gcc            # pełna macierz MSVC + GCC/WSL
    python bench/run_profile.py --full --groups classic,mc --repeats 5
    python bench/run_profile.py --full --dry-run        # sam plan pomiarów

Zależności: tylko biblioteka standardowa + pandas (CSV); psutil opcjonalnie.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

try:
    import psutil  # opcjonalnie: przypięcie procesu, informacje o RAM/CPU
except ImportError:  # pragma: no cover
    psutil = None

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CONFIGS = ROOT / "configs"
IS_WINDOWS = os.name == "nt"

# ---------------------------------------------------------------------------
# Buildy: etykieta -> ścieżka, gdzie uruchamiać, flagi (do meta.json i raportu).
# ---------------------------------------------------------------------------
BUILDS = {
    "msvc-O2": {"path": "build/Release/engine.exe", "runner": "win",
                "flags": "/O2 /Ob2 /DNDEBUG (CMake Release) /W4 /permissive- /utf-8"},
    "msvc-O1": {"path": "build-msvc-o1/Release/engine.exe", "runner": "win",
                "flags": "/O1 /DNDEBUG (preset msvc-o1)"},
    "msvc-Debug": {"path": "build/Debug/engine.exe", "runner": "win",
                   "flags": "/Od /Ob0 /RTC1 /Zi /MDd (CMake Debug, asercje)"},
    "gcc-O3": {"path": "build-gcc-release/bin/engine", "runner": "wsl",
               "flags": "-O3 -DNDEBUG -Wall -Wextra (preset gcc-release)"},
    "gcc-O2": {"path": "build-gcc-o2/bin/engine", "runner": "wsl",
               "flags": "-O2 -g -DNDEBUG (preset gcc-o2; -g nie zmienia kodu)"},
    "gcc-O0": {"path": "build-gcc-o0/bin/engine", "runner": "wsl",
               "flags": "-O0 -DNDEBUG (preset gcc-o0)"},
    "gcc-Debug": {"path": "build-gcc-debug/bin/engine", "runner": "wsl",
                  "flags": "-g, bez optymalizacji, asercje (preset gcc-debug)"},
}
MSVC_COMPILER_BUILDS = ["msvc-O2", "msvc-O1", "msvc-Debug"]
GCC_COMPILER_BUILDS = ["gcc-O3", "gcc-O2", "gcc-O0", "gcc-Debug"]

# Sekcje czasu z times.json (kolejność = kolejność etapów programu).
SECTIONS = ["readConfig", "readInput", "allocate", "terrain", "vents", "caSim", "snapshots", "save",
            "mcInit", "mcSim", "mcStats", "mcSave", "total"]


# ---------------------------------------------------------------------------
# Warianty
# ---------------------------------------------------------------------------
def deep_update(base: dict, patch: dict) -> dict:
    """Scala słownik patch z base (rekurencyjnie) i zwraca base."""
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            deep_update(base[k], v)
        else:
            base[k] = copy.deepcopy(v)
    return base


def load_config(name: str) -> dict:
    """Config z folderu configs/ (komentarze // nie są używane w naszych plikach)."""
    with open(CONFIGS / f"{name}.json", encoding="utf-8") as f:
        return json.load(f)


def dims_label(nx: int, ny: int, nz: int) -> str:
    return f"{nx}x{ny}" if nz == 1 else f"{nx}x{ny}x{nz}"


NB_SHORT = {"von_neumann": "vn", "moore": "moore"}


def classic_variant(group: str, nx: int, ny: int, nz: int, seeds: int, nb: str, bc: str,
                    fmt: str = "both") -> dict:
    """Klasyczny rozrost ziaren CA (tryb classic) — jak w tabeli benchmarku vector vs macierz."""
    cfg = {"space": {"nx": nx, "ny": ny, "nz": nz}, "grid": "vector", "boundary": bc, "neighborhood": nb,
           "rngSeed": 42, "vents": {"count": seeds}, "ca": {"mode": "classic", "maxSteps": 65535},
           "mc": {"enabled": False}, "output": {"format": fmt}}
    vid = f"classic_{dims_label(nx, ny, nz)}_s{seeds}_{NB_SHORT[nb]}_{bc[:3]}"
    return {"id": vid, "group": group, "config": cfg, "kind": "classic"}


def mc_variant(group: str, nx: int, ny: int, nz: int, nb: str, mcs: int, fmt: str = "both",
               stats_every: int = 10) -> dict:
    """Naiwny rozrost MC na całej przestrzeni (mc.domain = full), Q = 50, periodyczne."""
    cfg = {"space": {"nx": nx, "ny": ny, "nz": nz}, "boundary": "periodic", "neighborhood": nb, "rngSeed": 42,
           "mc": {"enabled": True, "domain": "full", "Q": 50, "mcs": mcs, "J": 1.0, "kT": 0.0,
                  "mobilityFromCooling": False, "statsEvery": stats_every},
           "output": {"format": fmt}}
    vid = f"mcfull_{dims_label(nx, ny, nz)}_{NB_SHORT[nb]}_mcs{mcs}"
    return {"id": vid, "group": group, "config": cfg, "kind": "mc_full"}


def file_variant(group: str, name: str, overrides: dict | None = None, suffix: str = "") -> dict:
    """Istniejący config z configs/ (lava, CA + MC), opcjonalnie z nadpisaniami."""
    cfg = deep_update(load_config(name), overrides or {})
    return {"id": f"{name}{suffix}", "group": group, "config": cfg, "kind": "config:" + name}


SIZES_FULL = [(100, 100, 1), (1000, 1000, 1), (10, 10, 10), (100, 100, 100)]
SIZES_QUICK = [(100, 100, 1), (10, 10, 10)]


def build_plan(quick: bool, groups: list[str], use_gcc: bool, main_label: str, gcc_label: str) -> list[dict]:
    """Lista wariantów; każdy ma listę buildów, na których ma być zmierzony."""
    main_builds = [main_label] + ([gcc_label] if use_gcc else [])
    plan: list[dict] = []

    def add(v: dict, builds: list[str], flags: list[str] | None = None) -> None:
        # Identyfikator jest kluczem configu, wznowienia i podsumowania — musi być unikalny
        # (ten sam przypadek w grupie compilers ma inny format wyjścia niż w grupie classic).
        if v["group"] == "compilers":
            v["id"] = "cmp_" + v["id"]
        assert all(p["id"] != v["id"] for p in plan), f"powtórzony wariant {v['id']}"
        v["builds"] = builds
        v["flags"] = flags or []
        plan.append(v)

    sizes = SIZES_QUICK if quick else SIZES_FULL
    seeds_list = [1, 10] if quick else [1, 10, 100]
    if "classic" in groups:
        for (nx, ny, nz) in sizes:
            for seeds in seeds_list:
                if seeds > nx * ny * nz // 4:
                    continue  # bez sensu: zarodki zajęłyby > 25% przestrzeni
                for nb in ("von_neumann", "moore"):
                    add(classic_variant("classic", nx, ny, nz, seeds, nb, "periodic"), main_builds)
        # Porównanie brzegów: absorbujący dla 1000x1000 i 100x100x100.
        for (nx, ny, nz) in ([] if quick else [(1000, 1000, 1), (100, 100, 100)]):
            for seeds in seeds_list:
                for nb in ("von_neumann", "moore"):
                    add(classic_variant("classic", nx, ny, nz, seeds, nb, "absorbing"), main_builds)
    if "mc" in groups:
        for (nx, ny, nz) in sizes:
            for nb in ("von_neumann", "moore"):
                add(mc_variant("mc", nx, ny, nz, nb, 10 if quick else 100), main_builds)
    if "lava" in groups:
        names = ["test_2d"] if quick else ["test_2d", "test_3d", "etna_3d", "lava_mc_2d", "lava_mc_3d"]
        for name in names:
            add(file_variant("lava", name), main_builds)
    if "big" in groups and not quick:
        add(classic_variant("big", 300, 300, 300, 100, "von_neumann", "periodic"), main_builds)
    if "compilers" in groups:
        # Reprezentatywne warianty dla porównania kompilatorów i poziomów optymalizacji.
        # Debug jest bardzo wolny — warianty dobrane tak, żeby Debug trwał co najwyżej ~1 min.
        comp_builds = list(MSVC_COMPILER_BUILDS) + (list(GCC_COMPILER_BUILDS) if use_gcc else [])
        if quick:
            add(classic_variant("compilers", 10, 10, 10, 10, "von_neumann", "periodic", fmt="bin"),
                ["msvc-O2", "msvc-Debug"] + (["gcc-O3", "gcc-O0"] if use_gcc else []))
        else:
            add(classic_variant("compilers", 100, 100, 100, 10, "von_neumann", "periodic", fmt="bin"), comp_builds)
            add(mc_variant("compilers", 100, 100, 100, "moore", 10, fmt="bin"), comp_builds)
            add(mc_variant("compilers", 200, 200, 1, "von_neumann", 100, fmt="bin"), comp_builds)
            add(file_variant("compilers", "test_3d", {"output": {"format": "bin"}}), comp_builds)
    if "detail" in groups:
        # Szczegółowe fazy wewnątrz CA i MC (--timing-detail) — osobne przebiegi.
        if quick:
            add(file_variant("detail", "test_2d", suffix="_detail"), [main_label], ["--timing-detail"])
        else:
            for v in (classic_variant("detail", 100, 100, 100, 10, "von_neumann", "periodic", fmt="none"),
                      classic_variant("detail", 1000, 1000, 1, 100, "von_neumann", "periodic", fmt="none"),
                      mc_variant("detail", 100, 100, 100, "moore", 20, fmt="none"),
                      mc_variant("detail", 1000, 1000, 1, "von_neumann", 20, fmt="none"),
                      file_variant("detail", "test_3d", {"output": {"format": "none"}}),
                      file_variant("detail", "etna_3d", {"output": {"format": "none"}}),
                      file_variant("detail", "lava_mc_3d", {"output": {"format": "none"}})):
                v["id"] += "_detail"
                add(v, main_builds, ["--timing-detail"])
    return plan


# ---------------------------------------------------------------------------
# Środowisko: przypięcie, priorytet, informacje o sprzęcie
# ---------------------------------------------------------------------------
def pin_self(cpu: int) -> str:
    """Przypina proces skryptu (i dziedziczące procesy potomne) do jednego procesora logicznego."""
    if psutil is not None:
        psutil.Process().cpu_affinity([cpu])
        return f"psutil.cpu_affinity([{cpu}]) procesu skryptu, dziedziczone przez engine"
    if IS_WINDOWS:
        import ctypes
        k32 = ctypes.windll.kernel32
        if not k32.SetProcessAffinityMask(k32.GetCurrentProcess(), ctypes.c_size_t(1 << cpu)):
            raise OSError("SetProcessAffinityMask nie powiodło się")
        return f"SetProcessAffinityMask(1 << {cpu}) procesu skryptu, dziedziczone przez engine"
    os.sched_setaffinity(0, {cpu})
    return f"sched_setaffinity({{{cpu}}})"


def windows_cpu_sets() -> list[dict]:
    """Procesory logiczne z klasą wydajności (Windows: 1 = rdzeń P, 0 = rdzeń E)."""
    if not IS_WINDOWS:
        return []
    import ctypes
    import ctypes.wintypes as wt
    k32 = ctypes.windll.kernel32
    need = wt.ULONG(0)
    k32.GetSystemCpuSetInformation(None, 0, ctypes.byref(need), None, 0)
    buf = ctypes.create_string_buffer(need.value)
    if not k32.GetSystemCpuSetInformation(buf, need, ctypes.byref(need), None, 0):
        return []
    out, off, raw = [], 0, buf.raw
    while off < need.value:
        size = int.from_bytes(raw[off:off + 4], "little")
        # SYSTEM_CPU_SET_INFORMATION: Size, Type, Id, Group(2), LogicalProcessorIndex(1), CoreIndex(1),
        # LastLevelCacheIndex(1), NumaNodeIndex(1), EfficiencyClass(1)
        out.append({"logical": raw[off + 14], "core": raw[off + 15], "efficiencyClass": raw[off + 18]})
        off += size
    return out


def background_load(seconds: float = 2.0) -> dict:
    """Obciążenie procesora przez inne programy (całkowite [%] i 5 największych procesów) —
    zapisywane w meta, bo tło wpływa na pomiar (pamięć podręczna L3, częstotliwość turbo)."""
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
    return {"totalPercent": total,
            "topProcesses": [{"name": n, "percentOfOneCpu": round(c, 1)} for c, n in top[:5]]}


def run_capture(cmd: list[str]) -> str:
    """Wyjście polecenia jako tekst (UTF-8, a gdy się nie da — strona kodowa systemu)."""
    try:
        out = subprocess.run(cmd, capture_output=True, timeout=60).stdout
    except Exception as e:  # pragma: no cover
        return f"? ({e})"
    for enc in ("utf-8", "oem" if IS_WINDOWS else "latin-1"):
        try:
            return out.decode(enc).strip()
        except (UnicodeDecodeError, LookupError):
            continue
    return out.decode("latin-1", "replace").strip()


def windows_cpu_name() -> str:
    if not IS_WINDOWS:
        return platform.processor()
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as k:
            return winreg.QueryValueEx(k, "ProcessorNameString")[0].strip()
    except OSError:
        return platform.processor()


def host_info(cpu: int) -> dict:
    sets = windows_cpu_sets()
    info = {
        "os": platform.platform(),
        "python": platform.python_version(),
        "cpu": windows_cpu_name(),
        "logicalCpus": os.cpu_count(),
    }
    if psutil is not None:
        info["physicalCores"] = psutil.cpu_count(logical=False)
        info["ramBytes"] = psutil.virtual_memory().total
        freq = psutil.cpu_freq()
        if freq is not None:
            info["cpuFreqMHz"] = {"current": freq.current, "max": freq.max}
        battery = psutil.sensors_battery() if hasattr(psutil, "sensors_battery") else None
        if battery is not None:
            info["powerPlugged"] = battery.power_plugged  # laptop: zasilanie sieciowe czy bateria
    if sets:
        p = sorted(s["logical"] for s in sets if s["efficiencyClass"] > 0)
        e = sorted(s["logical"] for s in sets if s["efficiencyClass"] == 0)
        info["pCoreLogicalCpus"] = p
        info["eCoreLogicalCpus"] = e
        info["pinnedCpuEfficiencyClass"] = next((s["efficiencyClass"] for s in sets if s["logical"] == cpu), None)
    if IS_WINDOWS:
        ram = run_capture(["powershell", "-NoProfile", "-Command",
                           "(Get-CimInstance Win32_PhysicalMemory | ForEach-Object { \"$($_.Capacity/1GB) GB "
                           "$($_.ConfiguredClockSpeed) MT/s\" }) -join '; '"])
        info["ramModules"] = ram
        info["computer"] = run_capture(["powershell", "-NoProfile", "-Command",
                                        "$c = Get-CimInstance Win32_ComputerSystem; \"$($c.Manufacturer) $($c.Model)\""])
        info["powerScheme"] = run_capture(["powercfg", "/getactivescheme"])
    return info


# ---------------------------------------------------------------------------
# Uruchamianie
# ---------------------------------------------------------------------------
def wsl_path(p: Path) -> str:
    """C:\\a\\b -> /mnt/c/a/b"""
    s = str(Path(p).resolve())
    return f"/mnt/{s[0].lower()}{s[2:]}".replace("\\", "/")


def sh_quote(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


class Runner:
    """Uruchamia engine dla jednego wariantu i zwraca słownik z times.json."""

    def __init__(self, args: argparse.Namespace, tmp: Path):
        self.args = args
        self.tmp = tmp
        self.keepalive: subprocess.Popen | None = None

    def run(self, build: str, variant: dict, rep: int) -> tuple[dict | None, str]:
        cfg_path = self.tmp / "configs" / f"{variant['id']}.json"
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        if not cfg_path.exists():
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(variant["config"], f, indent=2, ensure_ascii=False)
        spec = BUILDS[build]
        if spec["runner"] == "win":
            return self._run_win(spec, cfg_path, variant, rep, build)
        return self._run_wsl(spec, cfg_path, variant, rep, build)

    def _run_win(self, spec: dict, cfg: Path, variant: dict, rep: int, build: str) -> tuple[dict | None, str]:
        exe = self.args.engine if build == self.args.engine_label else ROOT / spec["path"]
        out = self.tmp / "out" / f"{variant['id']}__{build}__{rep}"
        shutil.rmtree(out, ignore_errors=True)
        cmd = [str(exe), "--config", str(cfg), "--out", str(out)] + variant["flags"]
        flags = 0
        if IS_WINDOWS and self.args.priority == "high":
            flags = subprocess.HIGH_PRIORITY_CLASS
        proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                creationflags=flags)
        pin_note = ""
        if psutil is not None and not self.args.no_pin:
            try:  # kontrola dziedziczenia maski (i korekta, gdyby system jej nie przekazał)
                child = psutil.Process(proc.pid)
                if child.cpu_affinity() != [self.args.cpu]:
                    child.cpu_affinity([self.args.cpu])
                    pin_note = "affinity set after start"
            except psutil.Error:
                pass
        _, err = proc.communicate()
        if proc.returncode != 0:
            return None, f"kod {proc.returncode}: {err.decode('utf-8', 'replace')[-400:]}"
        with open(out / "times.json", encoding="utf-8") as f:
            data = json.load(f)
        if not self.args.keep:
            shutil.rmtree(out, ignore_errors=True)
        return data, pin_note

    def keep_wsl_alive(self) -> None:
        """WSL2 wyłącza maszynę wirtualną po kilku sekundach bez procesów (a start systemu czyści /tmp).
        Proces `sleep` w tle podtrzymuje ją przez cały pomiar — stałe środowisko i brak restartów."""
        if self.keepalive is None:
            self.keepalive = subprocess.Popen(["wsl", "-e", "sleep", "infinity"],
                                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2)

    def close(self) -> None:
        if self.keepalive is not None:
            self.keepalive.terminate()
            self.keepalive = None

    def _run_wsl(self, spec: dict, cfg: Path, variant: dict, rep: int, build: str) -> tuple[dict | None, str]:
        exe = Path(self.args.gcc_engine) if build == self.args.gcc_label else ROOT / spec["path"]
        base = "/tmp/volcano_profile"
        self.keep_wsl_alive()
        dest = self.tmp / "out" / f"{variant['id']}__{build}__{rep}.times.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        pin = "" if self.args.no_pin else f"taskset -c {self.args.cpu} "
        flags = " ".join(variant["flags"])
        # Program i config na ext4 maszyny WSL (start i odczyt z /mnt/d przez 9P są wolne), wyniki też
        # na ext4 — czasy zapisu bez narzutu 9P. Program kopiowany, gdy go brak (np. po restarcie WSL).
        script = "\n".join([
            "set -e",
            f"mkdir -p {base}/bin {base}/run",
            f"[ -x {base}/bin/{build} ] || {{ cp {sh_quote(wsl_path(exe))} {base}/bin/{build}; "
            f"chmod +x {base}/bin/{build}; }}",
            f"cp {sh_quote(wsl_path(cfg))} {base}/run/config.json",
            f"rm -rf {base}/run/out",
            f"{pin}{base}/bin/{build} --config {base}/run/config.json --out {base}/run/out {flags} > /dev/null",
            f"cp {base}/run/out/times.json {sh_quote(wsl_path(dest))}",
            f"rm -rf {base}/run/out",
        ])
        sh = self.tmp / "run_wsl.sh"
        with open(sh, "w", encoding="utf-8", newline="\n") as f:
            f.write(script + "\n")
        r = subprocess.run(["wsl", "-e", "bash", wsl_path(sh)], capture_output=True, text=True)
        if r.returncode != 0 or not dest.exists():
            return None, f"WSL kod {r.returncode}: {r.stderr[-400:]}"
        with open(dest, encoding="utf-8") as f:
            data = json.load(f)
        dest.unlink()
        return data, ""


# ---------------------------------------------------------------------------
# Spłaszczenie times.json i podsumowanie
# ---------------------------------------------------------------------------
def variant_params(v: dict) -> dict:
    c = v["config"]
    sp = c.get("space", {})
    nx, ny, nz = sp.get("nx", 200), sp.get("ny", 1), sp.get("nz", 100)
    mc = c.get("mc", {})
    mode = "mc_full" if (mc.get("enabled") and mc.get("domain") == "full") else c.get("ca", {}).get("mode", "lava")
    return {
        "variant": v["id"], "group": v["group"], "kind": v["kind"], "mode": mode,
        "nx": nx, "ny": ny, "nz": nz, "dim": "2D" if 1 in (nx, ny, nz) else "3D",
        "seeds": c.get("vents", {}).get("count", 1) if mode != "mc_full" else None,
        "neighborhood": c.get("neighborhood", "moore"), "boundary": c.get("boundary", "absorbing"),
        "mcEnabled": bool(mc.get("enabled")), "mcsCfg": mc.get("mcs") if mc.get("enabled") else None,
        "outputFormat": c.get("output", {}).get("format", "txt"), "flags": " ".join(v["flags"]),
    }


def flatten(times: dict) -> dict:
    """Miary liczbowe z times.json w płaskim słowniku (kolumny CSV)."""
    row: dict = {}
    for s in SECTIONS:
        if s in times:
            row[f"{s}_ms"] = times[s]
    for k in ("cells", "steps", "domainCells", "mcs", "Q"):
        if k in times:
            row[k] = times[k]
    for k in ("stopReason", "compiler", "build", "cpu"):
        if k in times:
            row[k] = times[k]
    mem = times.get("memory", {})
    for k in ("startRssBytes", "peakRssBytes", "peakPrivateBytes", "endRssBytes"):
        if k in mem:
            row[f"mem_{k}"] = mem[k]
    model = mem.get("model", {})
    if "peakBytes" in model:
        row["mem_modelPeakBytes"] = model["peakBytes"]
        row["mem_modelPeakBytesPerCell"] = model["peakBytesPerCell"]
        for name, b in model.get("blocks", {}).items():
            row[f"mem_block_{name}_bytes"] = b["bytes"]
    for name, f in times.get("files", {}).items():
        key = name.replace(".", "_")
        row[f"file_{key}_bytes"] = f["bytes"]
        row[f"file_{key}_ms"] = f["writeMs"]
    for k, v in times.get("detail", {}).items():
        if k != "unit":
            row[f"detail_{k}_ms"] = v
    return row


def summarize(raw: pd.DataFrame) -> pd.DataFrame:
    """Mediana, min, max, odchylenie standardowe każdej miary dla wariantu × build."""
    keys = ["variant", "build"]
    param_cols = ["group", "kind", "mode", "nx", "ny", "nz", "dim", "seeds", "neighborhood", "boundary",
                  "mcEnabled", "mcsCfg", "outputFormat", "flags", "compiler", "buildType", "cpu",
                  "cells", "steps", "domainCells", "mcs", "Q", "stopReason"]
    metric_cols = [c for c in raw.columns if c not in keys + param_cols + ["rep", "timestamp", "note"]
                   and pd.api.types.is_numeric_dtype(raw[c])]
    rows = []
    for (variant, build), g in raw.groupby(keys, sort=False):
        r = {"variant": variant, "build": build, "repeats": len(g)}
        for c in param_cols:
            if c in g.columns:
                vals = g[c].dropna().unique()
                r[c] = vals[0] if len(vals) else None
        for c in metric_cols:
            vals = g[c].dropna().astype(float).tolist()
            if not vals:
                continue
            r[f"{c}_med"] = statistics.median(vals)
            r[f"{c}_min"] = min(vals)
            r[f"{c}_max"] = max(vals)
            r[f"{c}_std"] = statistics.stdev(vals) if len(vals) > 1 else 0.0
        rows.append(r)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Główna pętla
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--quick", action="store_true", help="mała macierz do szybkiego sprawdzenia")
    mode.add_argument("--full", action="store_true", help="pełna macierz (domyślnie)")
    ap.add_argument("--repeats", type=int, default=3, help="powtórzenia każdego wariantu (domyślnie 3)")
    ap.add_argument("--engine", default=str(ROOT / BUILDS["msvc-O2"]["path"]),
                    help="program engine dla głównego przebiegu (domyślnie MSVC Release)")
    ap.add_argument("--engine-label", default="msvc-O2", help="etykieta buildu głównego przebiegu")
    ap.add_argument("--gcc", action="store_true", help="drugi przebieg: GCC przez WSL (+ buildy GCC w grupie compilers)")
    ap.add_argument("--gcc-engine", default=str(ROOT / BUILDS["gcc-O3"]["path"]), help="program GCC (Linux) dla --gcc")
    ap.add_argument("--gcc-label", default="gcc-O3", help="etykieta buildu GCC")
    ap.add_argument("--groups", default="classic,mc,lava,big,compilers,detail,benchmark",
                    help="grupy: classic, mc, lava, big, compilers, detail, benchmark")
    ap.add_argument("--cpu", type=int, default=2, help="procesor logiczny do przypięcia (domyślnie 2 — rdzeń P)")
    ap.add_argument("--no-pin", action="store_true", help="bez przypinania do rdzenia")
    ap.add_argument("--priority", choices=["high", "normal"], default="high", help="priorytet procesu engine (Windows)")
    ap.add_argument("--name", help="nazwa zestawu (domyślnie profile_<data>[_quick])")
    ap.add_argument("--out", default=str(ROOT / "bench" / "results"), help="folder wyników")
    ap.add_argument("--tmp", help="folder tymczasowy na configi i wyniki przebiegów")
    ap.add_argument("--keep", action="store_true", help="nie usuwaj folderów wyników przebiegów")
    ap.add_argument("--dry-run", action="store_true", help="wypisz plan i zakończ")
    args = ap.parse_args()
    if not sys.stdout.isatty():  # przekierowanie do pliku/potoku: polskie znaki w UTF-8
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    quick = args.quick
    groups = [g.strip() for g in args.groups.split(",") if g.strip()]
    BUILDS[args.engine_label] = dict(BUILDS.get(args.engine_label, {"runner": "win", "flags": "?"}),
                                     path=str(args.engine))
    if args.gcc:
        BUILDS[args.gcc_label] = dict(BUILDS.get(args.gcc_label, {"runner": "wsl", "flags": "?"}),
                                      path=str(args.gcc_engine))

    plan = build_plan(quick, groups, args.gcc, args.engine_label, args.gcc_label)
    # Pomijamy buildy, których programu brak (np. nie zbudowano gcc-o0) — z ostrzeżeniem.
    missing = sorted({b for v in plan for b in v["builds"] if not (ROOT / BUILDS[b]["path"]).exists()
                      and not Path(BUILDS[b]["path"]).exists()})
    for b in missing:
        print(f"UWAGA: brak programu dla buildu {b} ({BUILDS[b]['path']}) — pomijam", file=sys.stderr)
    for v in plan:
        v["builds"] = [b for b in v["builds"] if b not in missing]
    runs = [(v, b, r) for v in plan for r in range(args.repeats) for b in v["builds"]]
    if args.dry_run:
        for v in plan:
            print(f"{v['group']:10s} {v['id']:42s} {','.join(v['builds'])} {' '.join(v['flags'])}")
        print(f"Wariantów: {len(plan)}, przebiegów: {len(runs)} (+ benchmark: {'benchmark' in groups})")
        return 0

    today = dt.date.today().isoformat()
    name = args.name or (f"profile_{today}" + ("_quick" if quick else ""))
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl = out_dir / f"{name}_raw.jsonl"
    done: set[tuple[str, str, int]] = set()
    if jsonl.exists():
        with open(jsonl, encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                done.add((r["variant"], r["build"], r["rep"]))
        print(f"Wznawiam {name}: {len(done)} przebiegów już zmierzonych")

    pin_method = "brak (--no-pin)"
    if not args.no_pin:
        pin_method = pin_self(args.cpu) if IS_WINDOWS else f"taskset/sched_setaffinity {args.cpu}"
    tmp = Path(args.tmp) if args.tmp else Path(tempfile.mkdtemp(prefix="volcano_profile_"))
    tmp.mkdir(parents=True, exist_ok=True)
    runner = Runner(args, tmp)
    load_start = background_load()
    if load_start:
        print(f"Obciążenie CPU przez inne programy: {load_start['totalPercent']:.0f}% "
              f"({', '.join(p['name'] for p in load_start['topProcesses'][:3])})")
    print(f"Zestaw {name}: {len(plan)} wariantów, {len(runs)} przebiegów, folder tymczasowy {tmp}")

    builds_seen: dict[str, dict] = {}
    t_start = time.time()
    failures = 0
    for k, (v, build, rep) in enumerate(runs, 1):
        if (v["id"], build, rep) in done:
            continue
        t0 = time.time()
        data, note = runner.run(build, v, rep)
        wall = time.time() - t0
        if data is None:
            failures += 1
            print(f"[{k}/{len(runs)}] {v['id']} {build} #{rep}: BŁĄD {note}", file=sys.stderr)
            continue
        row = variant_params(v)
        row.update({"build": build, "rep": rep, "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
                    "wallSeconds": round(wall, 3), "note": note})
        flat = flatten(data)
        flat["buildType"] = flat.pop("build", None)
        row.update(flat)
        builds_seen.setdefault(build, {"compiler": data.get("compiler"), "buildType": data.get("build")})
        with open(jsonl, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        main_t = data.get("caSim", data.get("mcSim", 0.0))
        print(f"[{k}/{len(runs)}] {v['id']:40s} {build:10s} #{rep}  sim {main_t:10.1f} ms  "
              f"total {data.get('total', 0):10.1f} ms  ({wall:.1f} s)", flush=True)

    runner.close()

    # Benchmark vector vs macierz (engine --benchmark), pomiar jednorazowy z medianą z 5 powtórzeń.
    bench_csv = out_dir / f"{name}_benchmark.csv"
    if "benchmark" in groups and not bench_csv.exists():
        bdir = tmp / "benchmark"
        cmd = [str(args.engine), "--benchmark", "--repeats", "3" if quick else "5", "--out", str(bdir)]
        if quick:
            cmd.append("--quick")
        print("Benchmark vector vs macierz: " + " ".join(cmd[1:]), flush=True)
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                           creationflags=subprocess.HIGH_PRIORITY_CLASS if IS_WINDOWS and args.priority == "high" else 0)
        if r.returncode == 0 and (bdir / "benchmark.csv").exists():
            shutil.copy(bdir / "benchmark.csv", bench_csv)
            print(r.stdout)
        else:
            failures += 1
            print("Benchmark: błąd\n" + r.stdout[-500:] + r.stderr[-500:], file=sys.stderr)

    # CSV: surowe przebiegi i podsumowanie (z całego pliku jsonl — także z wcześniejszych wywołań).
    if jsonl.exists():
        with open(jsonl, encoding="utf-8") as f:
            raw = pd.DataFrame([json.loads(line) for line in f])
        raw.to_csv(out_dir / f"{name}_raw.csv", index=False)
        summary = summarize(raw)
        summary.to_csv(out_dir / f"{name}.csv", index=False)
        print(f"Zapisano {out_dir / (name + '.csv')} ({len(summary)} wierszy) i {name}_raw.csv ({len(raw)})")

    # Metadane: sprzęt, system, buildy, przypięcie, powtórzenia.
    meta_path = out_dir / f"{name}_meta.json"
    meta = {}
    if meta_path.exists():
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
    passes = meta.get("passes", [])
    passes.append({"started": dt.datetime.fromtimestamp(t_start).isoformat(timespec="seconds"),
                   "durationMinutes": round((time.time() - t_start) / 60, 1),
                   "command": " ".join(sys.argv), "groups": groups, "repeats": args.repeats,
                   "mode": "quick" if quick else "full", "failures": failures,
                   "backgroundLoad": {"start": load_start, "end": background_load()}})
    builds_meta = meta.get("builds", {})
    for b, info in builds_seen.items():
        builds_meta[b] = {"path": BUILDS[b]["path"], "runner": BUILDS[b]["runner"],
                          "flags": BUILDS[b]["flags"], **info}
    meta.update({
        "name": name,
        "host": host_info(args.cpu),
        "pinning": {"cpu": None if args.no_pin else args.cpu, "method": pin_method,
                    "wsl": None if args.no_pin else f"taskset -c {args.cpu} (wirtualny procesor WSL2)"},
        "priority": "HIGH_PRIORITY_CLASS" if args.priority == "high" else "NORMAL",
        "builds": builds_meta,
        "passes": passes,
        "notes": [
            "Czasy etapów z times.json (steady_clock w programie) — bez czasu startu procesu.",
            "W wierszach CSV: <miara>_med/_min/_max/_std z powtórzeń; pomiary < 5 ms są zaszumione.",
            "WSL: config i wyniki na ext4 maszyny wirtualnej (/tmp), nie na /mnt/d.",
        ],
    })
    if args.gcc:
        meta["wsl"] = {
            "uname": run_capture(["wsl", "-e", "uname", "-srm"]),
            "distro": run_capture(["wsl", "-e", "bash", "-c", "grep PRETTY_NAME /etc/os-release | cut -d= -f2"]),
            "gcc": run_capture(["wsl", "-e", "bash", "-c", "g++ --version | head -1"]),
            "nproc": run_capture(["wsl", "-e", "nproc"]),
            "memTotal": run_capture(["wsl", "-e", "bash", "-c", "grep MemTotal /proc/meminfo"]),
        }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"Metadane: {meta_path}. Błędów: {failures}. Czas: {(time.time() - t_start) / 60:.1f} min")
    if not args.keep and not args.tmp:
        shutil.rmtree(tmp, ignore_errors=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
