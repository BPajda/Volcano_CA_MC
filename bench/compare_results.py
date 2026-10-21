#!/usr/bin/env python3
"""Bitowa zgodność wyników (etap 8): te same configi z configs/*.json uruchomione kilkoma programami engine.

Każdy config (w wariancie domyślnym — tak jak leży w configs/) jest liczony każdym programem, a folder wyników
porównywany bajt po bajcie z wynikiem pierwszego programu (wszystkie pliki poza times.json i config_used.json;
stats.json przy różnicy bajtowej — jeszcze raz jako JSON bez pól z czasem). configs/mc_basalt.json jest liczony
w trybie --mc-from na wyniku lava_mc_2d danego programu. Programy z przedrostkiem „wsl:” (build GCC) są
uruchamiane w WSL z katalogu projektu — dzięki temu ta sama tabela sprawdza zgodność MSVC ↔ GCC. Programy WSL piszą
wyniki na ext4 (/tmp/volcano_cmp — etap 11: MPI-IO w WSL tylko tam, dysk Windows przez 9p jest wielokrotnie wolniejszy),
a do porównania trafia ich kopia; folder wejściowy --mc-from jest przed przebiegiem kopiowany na ext4.

    python bench/compare_results.py --bin przed=bench/baseline/engine_przed_msvc.exe \\
        --bin msvc=build/Release/engine.exe --bin gcc=wsl:build-gcc-release/bin/engine --name zgodnosc_po
    python bench/compare_results.py ... --set ca.sweep=full      # nadpisanie dla wszystkich programów
    python bench/compare_results.py --bin e9=wsl:bench/baseline/engine_e9_gcc \\
        --bin m3=wsl:build-gcc-release/bin/engine_mpi \\
        --launch "m3=mpiexec -n 3 --allow-run-as-root --oversubscribe --bind-to none" --name zgodnosc_mpi   # etap 10

Wynik: tabela Markdown na ekranie i w bench/results/ab/<nazwa>.md; kod wyjścia 1 przy jakiejkolwiek różnicy.
"""

from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ab import compare_dirs, wsl_path  # noqa: E402  (ta sama definicja zgodności co test A/B)

ROOT = Path(__file__).resolve().parent.parent
MC_FROM = ("mc_basalt", "lava_mc_2d")  # config samego MC i wynik CA, na którym go liczymy
WSL_TMP = "/tmp/volcano_cmp"  # wyniki programów WSL (ext4), kopiowane potem do folderu porównania


def shown(exe: str) -> str:
    """Ścieżka programu do tabeli: względem katalogu projektu (bez ścieżki bezwzględnej komputera)."""
    for root in (wsl_path(ROOT), str(ROOT)):
        if root in exe:
            return exe.replace(root + ("/" if root.startswith("/") else "\\"), "").replace("\\", "/")
    return exe


def run(exe: str, args: list[str], out: Path, launch: list[str] | None = None) -> tuple[bool, str, float]:
    """Jeden przebieg (Windows albo WSL); zwraca (ok, komunikat błędu, czas [s]). launch — polecenie uruchamiające
    program (etap 10: mpiexec -n N …) wstawiane przed ścieżkę programu. WSL: wyniki na ext4, potem kopia do out."""
    shutil.rmtree(out, ignore_errors=True)
    t0 = time.perf_counter()
    launch = launch or []
    if exe.startswith("wsl:"):
        conv, pre, post = [], [], []
        for a in args:
            if Path(a).is_absolute() and Path(a).drive:  # folder Windows (--mc-from) -> kopia na ext4
                dst = f"{WSL_TMP}/in_{Path(a).name}"
                pre.append(f"rm -rf {shlex.quote(dst)} && cp -r {shlex.quote(wsl_path(Path(a)))} {shlex.quote(dst)}")
                post.append(f"rm -rf {shlex.quote(dst)}")
                conv.append(dst)
            else:
                conv.append(a)
        tmp_out = f"{WSL_TMP}/{out.name}"
        program = " ".join(shlex.quote(c) for c in [*launch, exe[4:], *conv, "--out", tmp_out])
        win_out = shlex.quote(wsl_path(out))
        script = " && ".join([f"mkdir -p {WSL_TMP}", f"rm -rf {shlex.quote(tmp_out)}", *pre, program]) + \
            f"; rc=$?; mkdir -p {win_out} && cp -r {shlex.quote(tmp_out)}/. {win_out}/; " + \
            "; ".join([f"rm -rf {shlex.quote(tmp_out)}", *post]) + "; exit $rc"
        cmd = ["wsl", "-e", "bash", "-c", script]
    else:
        cmd = [*launch, exe, *args, "--out", str(out)]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode == 0, r.stderr[-300:], time.perf_counter() - t0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bin", action="append", required=True, metavar="ETYKIETA=ŚCIEŻKA",
                    help="program (pierwszy = odniesienie); przedrostek wsl: — program Linux uruchamiany w WSL")
    ap.add_argument("--set", dest="set_values", action="append", default=[], metavar="KLUCZ=WARTOŚĆ",
                    help="nadpisanie configu dla wszystkich programów")
    ap.add_argument("--args", action="append", default=[], metavar="ETYKIETA=ARGUMENTY",
                    help='dodatkowe argumenty jednego programu, np. "full=--set ca.sweep=full"')
    ap.add_argument("--launch", action="append", default=[], metavar="ETYKIETA=POLECENIE",
                    help='polecenie uruchamiające program (etap 10, MPI), np. "m3=mpiexec -n 3"')
    ap.add_argument("--configs", help="tylko wybrane configi (nazwy bez .json, po przecinku)")
    ap.add_argument("--name", default="zgodnosc", help="nazwa pliku wyniku (<nazwa>.md)")
    ap.add_argument("--out", default=str(ROOT / "bench" / "results" / "ab"), help="folder wyniku (domyślnie bench/results/ab)")
    args = ap.parse_args()
    if not sys.stdout.isatty():
        sys.stdout.reconfigure(encoding="utf-8")

    labels, exes = [], {}
    for b in args.bin:
        label, path = b.split("=", 1)
        if path.startswith("wsl:"):
            exes[label] = "wsl:" + wsl_path(ROOT / path[4:])
        else:
            exes[label] = str(Path(path) if Path(path).is_absolute() else ROOT / path)
        labels.append(label)
    extra = {l: [] for l in labels}
    for a in args.args:
        label, rest = a.split("=", 1)
        extra[label] = rest.split()
    launch = {l: [] for l in labels}
    for a in args.launch:
        label, rest = a.split("=", 1)
        launch[label] = rest.split()
    sets = [x for s in args.set_values for x in ("--set", s)]
    names = sorted(p.stem for p in (ROOT / "configs").glob("*.json"))
    if args.configs:
        names = [n for n in names if n in args.configs.split(",")]
    tmp = Path(tempfile.mkdtemp(prefix="volcano_cmp_"))
    rows = []
    failures = 0
    for name in names:
        if name == MC_FROM[0]:
            continue  # liczony niżej, po lava_mc_2d
        outs = {}
        for l in labels:
            out = tmp / f"{name}__{l}"
            ok, err, sec = run(exes[l], ["--config", f"configs/{name}.json", *sets, *extra[l]], out, launch[l])
            if not ok:
                print(f"BŁĄD {name} {l}: {err}", file=sys.stderr)
                failures += 1
            outs[l] = out
        if name == MC_FROM[1]:  # MC z pliku na wyniku CA tego samego programu
            mc_outs = {}
            for l in labels:
                out = tmp / f"{MC_FROM[0]}__{l}"
                ok, err, _ = run(exes[l], ["--mc-from", str(outs[l]), "--config", f"configs/{MC_FROM[0]}.json",
                                           *sets, *extra[l]], out, launch[l])
                if not ok:
                    print(f"BŁĄD {MC_FROM[0]} {l}: {err}", file=sys.stderr)
                    failures += 1
                mc_outs[l] = out
            pending = [(name, outs), (f"{MC_FROM[0]} (--mc-from)", mc_outs)]
        else:
            pending = [(name, outs)]
        for case, o in pending:
            ref = o[labels[0]]
            files = sorted(p.name for p in ref.rglob("*") if p.is_file() and p.name not in ("times.json", "config_used.json"))
            cells = []
            for l in labels[1:]:
                # MSVC ↔ GCC: pliki tekstowe bez różnicy końców linii; MC z pliku: bez ścieżki folderu wejściowego
                cross = exes[l].startswith("wsl:") != exes[labels[0]].startswith("wsl:")
                diffs = compare_dirs(ref, o[l], eol=cross, ignore_keys=("folder", "file"))
                failures += 1 if diffs else 0
                cells.append("tak" if not diffs else "**NIE**: " + "; ".join(diffs))
            rows.append(f"| `{case}` | {', '.join(files)} | " + " | ".join(cells) + " |")
            print(rows[-1], flush=True)
    head = [f"# Zgodność wyników `{args.name}`", "",
            "Programy: " + ", ".join(f"`{l}` = " + (f"`{' '.join(launch[l])}` " if launch[l] else "") +
                                     f"`{shown(exes[l])}`" + (f" `{' '.join(extra[l])}`" if extra[l] else "")
                                     for l in labels) + (f"; nadpisania: {', '.join(args.set_values)}" if sets else ""),
            f"Porównanie bajt po bajcie z `{labels[0]}` (bez times.json i config_used.json; stats.json bez ścieżki "
            "folderu wejściowego --mc-from; MSVC ↔ GCC: txt/csv bez różnicy końców linii CRLF/LF; programy WSL piszą "
            "na ext4).", "",
            "| Config | pliki | " + " | ".join(f"{l} = {labels[0]}" for l in labels[1:]) + " |",
            "|---|---|" + "---|" * (len(labels) - 1)]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / f"{args.name}.md", "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(head + rows) + "\n")
    print(f"Zapisano {out_dir / (args.name + '.md')}; różnic / błędów: {failures}")
    shutil.rmtree(tmp, ignore_errors=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
