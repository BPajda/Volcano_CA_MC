#!/usr/bin/env python3
"""Profil CPU wersji MSVC (etap 3) z linii poleceń — kolektor profilera Visual Studio + xperf.

1. VSDiagnostics.exe (kolektor „CPU Usage” profilera Visual Studio, AgentConfigs/CpuUsageHigh.json)
   uruchamia engine z buildu z symbolami (preset msvc-profile: ten sam kod co Release + PDB)
   i próbkuje stos co ~1 ms -> plik .diagsession (archiwum z śladem ETW .etl).
2. xperf.exe (Windows Performance Toolkit) czyta ślad: `-a profile -detail` z symbolami z PDB
   daje liczbę próbek (wagę) na funkcję — profil płaski „self”, jak gprof -p.
3. Skrypt zostawia tylko wiersze procesu engine.exe i zapisuje top funkcji z udziałem procentowym
   do bench/profiles/msvc_<build>_<wariant>.txt. Plik .diagsession (tylko z --keep-diagsession,
   do results/vs_profiler/ — folder poza repozytorium, pliki mają 10–100 MB) można otworzyć
   w Visual Studio (Plik -> Otwórz) i zrobić zrzut „Hot Path”.

Wymaga: Visual Studio 2022 (Team Tools/DiagnosticsHub/Collector/VSDiagnostics.exe) i Windows
Performance Toolkit (xperf.exe; instaluje się z Windows SDK). Uprawnienia administratora nie są
potrzebne (kolektor działa jako usługa VS Standard Collector).

Użycie (z katalogu volcano-ca-mc, po zbudowaniu presetów msvc-profile i msvc-profile-noinline):
    python bench/profile_msvc.py
    python bench/profile_msvc.py --builds msvc-profile --cases ca_lava_etna3d --keep-diagsession
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parent.parent
VS = Path(r"C:\Program Files\Microsoft Visual Studio\2022\Community")
VSDIAG = VS / "Team Tools/DiagnosticsHub/Collector/VSDiagnostics.exe"
AGENT_CFG = VS / "Team Tools/DiagnosticsHub/Collector/AgentConfigs/CpuUsageHigh.json"
XPERF = Path(r"C:\Program Files (x86)\Windows Kits\10\Windows Performance Toolkit\xperf.exe")

# Te same warianty co w bench/profile_gcc.sh (gprof).
CASES = {
    "ca_lava_test3d": ["--config", "configs/test_3d.json", "--set", "output.format=none"],
    "ca_lava_etna3d": ["--config", "configs/etna_3d.json", "--set", "output.format=none"],
    "ca_classic_100c": ["--config", "configs/classic_ref.json", "--set", "output.format=none"],
    "mc_full_3d": ["--config", "configs/mc_full_3d.json", "--set", "output.format=none", "--set", "mc.mcs=300"],
}


def profile_case(build: str, case: str, tmp: Path, session: int, keep: bool) -> str:
    exe = ROOT / f"build-{build}" / "Release" / "engine.exe"
    if not exe.exists():
        sys.exit(f"Brak {exe} — zbuduj preset {build}")
    out_dir = tmp / f"out_{build}_{case}"
    args = [str(ROOT / a) if a.startswith("configs/") else a for a in CASES[case]] + ["--out", str(out_dir)]
    launch_args = subprocess.list2cmdline(args)
    diag = tmp / f"{build}_{case}.diagsession"
    subprocess.run([str(VSDIAG), "start", str(session), f"/launch:{exe}", f"/launchArgs:{launch_args}",
                    f"/loadConfig:{AGENT_CFG}"], check=True, capture_output=True)
    # Czekamy na pojawienie się i zakończenie procesu engine z tego buildu.
    t0 = time.time()
    seen = False
    while time.time() - t0 < 600:
        running = [p for p in psutil.process_iter(["exe"]) if p.info["exe"] and Path(p.info["exe"]) == exe]
        if running:
            seen = True
        elif seen or time.time() - t0 > 20:
            break
        time.sleep(0.5)
    subprocess.run([str(VSDIAG), "stop", str(session), f"/output:{diag}"], check=True, capture_output=True)
    # .diagsession to archiwum ZIP (OPC) — ślad ETW w pliku *.etl.
    xdir = tmp / f"x_{build}_{case}"
    with zipfile.ZipFile(diag) as z:
        z.extractall(xdir)
    etl = max(xdir.rglob("*.etl"), key=lambda p: p.stat().st_size)
    report = tmp / f"xperf_{build}_{case}.txt"
    env = dict(os.environ, _NT_SYMBOL_PATH=str(exe.parent))
    subprocess.run([str(XPERF), "-i", str(etl), "-o", str(report), "-symbols", "-a", "profile", "-detail"],
                   check=True, capture_output=True, env=env)
    if keep:
        dst = ROOT / "results" / "vs_profiler" / diag.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(diag, dst)
    return report.read_text(encoding="utf-8", errors="replace")


def parse(report: str) -> list[tuple[str, int]]:
    """Wiersze procesu engine.exe: (moduł!funkcja, waga) — suma po funkcjach."""
    rows: dict[str, int] = {}
    for line in report.splitlines():
        m = re.match(r'\s*engine\.exe \(\s*\d+\),\s*(\d+),\s*[\d.]+,\s*(.+)$', line)
        if m:
            name = m.group(2).strip()
            rows[name] = rows.get(name, 0) + int(m.group(1))
    return sorted(rows.items(), key=lambda kv: -kv[1])


def main() -> int:
    ap = argparse.ArgumentParser(description="Profil CPU MSVC: VSDiagnostics + xperf -> bench/profiles/")
    ap.add_argument("--builds", default="msvc-profile,msvc-profile-noinline")
    ap.add_argument("--cases", default=",".join(CASES))
    ap.add_argument("--keep-diagsession", action="store_true", help="kopiuj .diagsession do results/vs_profiler/")
    args = ap.parse_args()
    for tool in (VSDIAG, XPERF):
        if not tool.exists():
            sys.exit(f"Brak {tool}")
    out = ROOT / "bench" / "profiles"
    out.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="volcano_vsprof_"))
    session = 21
    for build in args.builds.split(","):
        for case in args.cases.split(","):
            session += 1
            report = profile_case(build, case, tmp, session, args.keep_diagsession)
            rows = parse(report)
            total = sum(w for _, w in rows) or 1
            lines = [f"# Profil CPU MSVC (VSDiagnostics CpuUsageHigh + xperf -a profile), build {build}, wariant {case}",
                     f"# argumenty: {' '.join(CASES[case])}",
                     "# udział = próbki funkcji / wszystkie próbki procesu engine.exe (czas „self”, bez wywoływanych)",
                     f"{'udział %':>9}  {'waga':>10}  funkcja"]
            for name, w in rows[:25]:
                lines.append(f"{100.0 * w / total:9.2f}  {w:10d}  {name}")
            (out / f"msvc_{build.replace('msvc-', '')}_{case}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
            top = ", ".join(f"{n.split('!')[-1]} {100.0 * w / total:.1f}%" for n, w in rows[:3])
            print(f"{build} {case}: {top}", flush=True)
    shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
