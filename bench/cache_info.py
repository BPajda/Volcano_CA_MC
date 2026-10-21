#!/usr/bin/env python3
"""Parametry pamięci podręcznej procesora (etap 12): poziomy, rozmiary, asocjacyjność, długość linii i które procesory
logiczne dzielą każdą pamięć podręczną — z systemu, bez zgadywania z nazwy procesora.

Windows: GetLogicalProcessorInformationEx (RelationCache + RelationProcessorCore — klasa wydajności rdzenia, czyli
P / E w procesorze hybrydowym). Linux / WSL: /sys/devices/system/cpu/cpu*/cache/index*/ (w WSL 2 to opis procesorów
wirtualnych podany przez hiperwizor). Wynik: tabela Markdown na stdout albo do pliku (--out).

    python bench/cache_info.py --out bench/results/testy/procesor.md
    wsl -e python3 bench/cache_info.py
"""

from __future__ import annotations

import argparse
import ctypes
import os
import platform
import sys
from pathlib import Path

IS_WINDOWS = os.name == "nt"
CACHE_TYPES = {0: "Unified", 1: "Instruction", 2: "Data", 3: "Trace"}


def mask_cpus(mask: int) -> list[int]:
    """Numery procesorów logicznych z maski (grupa 0 — komputer ma < 64 procesory logiczne)."""
    return [i for i in range(64) if mask >> i & 1]


def windows_info() -> tuple[list[dict], dict[int, int]]:
    """Pamięci podręczne i klasa wydajności każdego procesora logicznego (GetLogicalProcessorInformationEx)."""
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    relation_all = 0xFFFF
    size = ctypes.c_uint32(0)
    k32.GetLogicalProcessorInformationEx(relation_all, None, ctypes.byref(size))
    buf = ctypes.create_string_buffer(size.value)
    if not k32.GetLogicalProcessorInformationEx(relation_all, buf, ctypes.byref(size)):
        raise OSError(ctypes.get_last_error(), "GetLogicalProcessorInformationEx")
    raw = buf.raw
    caches, eff = [], {}
    off = 0
    while off < size.value:
        rel = int.from_bytes(raw[off:off + 4], "little")
        rec = int.from_bytes(raw[off + 4:off + 8], "little")
        body = raw[off + 8:off + rec]
        if rel == 0:  # RelationProcessorCore: Flags, EfficiencyClass, Reserved[20], GroupCount, GROUP_AFFINITY[]
            cls = body[1]
            mask = int.from_bytes(body[24:32], "little")
            for c in mask_cpus(mask):
                eff[c] = cls
        elif rel == 2:  # RelationCache: Level, Associativity, LineSize, CacheSize, Type, Reserved[18], GroupCount, GROUP_AFFINITY
            caches.append({"level": body[0], "assoc": body[1], "line": int.from_bytes(body[2:4], "little"),
                           "size": int.from_bytes(body[4:8], "little"),
                           "type": CACHE_TYPES.get(int.from_bytes(body[8:12], "little"), "?"),
                           "cpus": mask_cpus(int.from_bytes(body[32:40], "little"))})
        off += rec
    return caches, eff


def linux_info() -> tuple[list[dict], dict[int, int]]:
    """Pamięci podręczne z /sys (każda raz — po liście procesorów, które ją dzielą)."""
    seen, caches = set(), []
    base = Path("/sys/devices/system/cpu")
    for cpu in sorted(base.glob("cpu[0-9]*"), key=lambda p: int(p.name[3:])):
        for idx in sorted((cpu / "cache").glob("index*")):
            rd = lambda n: (idx / n).read_text().strip() if (idx / n).exists() else ""  # noqa: E731
            shared = rd("shared_cpu_list")
            key = (rd("level"), rd("type"), shared)
            if key in seen:
                continue
            seen.add(key)
            cpus = []
            for part in shared.split(","):
                a, _, b = part.partition("-")
                cpus += list(range(int(a), int(b or a) + 1)) if a else []
            size = rd("size")
            mult = {"K": 1024, "M": 1024 * 1024}.get(size[-1:], 1)
            caches.append({"level": int(rd("level") or 0), "assoc": int(rd("ways_of_associativity") or 0),
                           "line": int(rd("coherency_line_size") or 0),
                           "size": int(size.rstrip("KM") or 0) * mult, "type": rd("type"), "cpus": cpus})
    return caches, {}


def fmt_size(b: int) -> str:
    return f"{b // (1024 * 1024)} MB" if b >= 1024 * 1024 and b % (1024 * 1024) == 0 else f"{b // 1024} KB"


def cpu_list(cpus: list[int]) -> str:
    """0,1,2,3 -> 0–3; listy nieciągłe po przecinku."""
    out, i = [], 0
    while i < len(cpus):
        j = i
        while j + 1 < len(cpus) and cpus[j + 1] == cpus[j] + 1:
            j += 1
        out.append(f"{cpus[i]}–{cpus[j]}" if j > i else str(cpus[i]))
        i = j + 1
    return ", ".join(out)


def table(caches: list[dict], eff: dict[int, int]) -> list[str]:
    """Jeden wiersz na rodzaj pamięci podręcznej (poziom, typ, rozmiar, klasa rdzeni) z liczbą egzemplarzy."""
    classes = sorted(set(eff.values()))
    name = {c: ("P" if c == max(classes) else "E") for c in classes} if len(classes) > 1 else {}
    groups: dict[tuple, list[dict]] = {}
    for c in caches:
        cls = sorted({name.get(eff.get(p), "") for p in c["cpus"]}) if name else []
        key = (c["level"], c["type"], c["size"], c["assoc"], c["line"], "/".join(cls), len(c["cpus"]))
        groups.setdefault(key, []).append(c)
    md = ["| Poziom | Typ | Rozmiar | Asocjacyjność | Linia [B] | Rdzenie | Procesory logiczne na egzemplarz | "
          "Egzemplarze (procesory) |", "|---|---|---|---|---|---|---|---|"]
    for key in sorted(groups, key=lambda k: (k[0], k[1] != "Data", k[5] != "P", -k[2])):
        lvl, typ, size, assoc, line, cls, n = key
        inst = groups[key]
        md.append(f"| L{lvl} | {typ} | {fmt_size(size)} | {assoc} | {line} | {cls or '—'} | {n} | {len(inst)} "
                  f"({'; '.join(cpu_list(c['cpus']) for c in inst[:4])}{'; …' if len(inst) > 4 else ''}) |")
    return md


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", help="plik Markdown (domyślnie stdout)")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    caches, eff = windows_info() if IS_WINDOWS else linux_info()
    src = ("Windows `GetLogicalProcessorInformationEx` (RelationCache, RelationProcessorCore — klasa wydajności)"
           if IS_WINDOWS else "Linux `/sys/devices/system/cpu/cpu*/cache` (w WSL 2 — procesory wirtualne)")
    lines = [f"Źródło: {src}; procesor: {platform.processor() or platform.machine()}; procesorów logicznych: "
             f"{os.cpu_count()}.", ""]
    if eff:
        by = {}
        for cpu, cls in sorted(eff.items()):
            by.setdefault(cls, []).append(cpu)
        lines += ["Klasy wydajności rdzeni: " + "; ".join(f"klasa {c} — procesory {cpu_list(v)}" for c, v in
                                                       sorted(by.items(), reverse=True)), ""]
    lines += table(caches, eff)
    text = "\n".join(lines) + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
