"""Eksport wyniku symulacji do VTK ImageData (.vti) — format wymiany z ParaView / VisIt / VTK (etap 5).

Ten sam kod co przycisk „VTK” w GUI (gui/export.py: write_vti; odczyt wyników — gui/results.py):
siatka nx × ny × nz wokseli, pola komórek type, flowId, temp, solidStep, arrivalStep, cooling (z ca_result.*)
i crystal (z mc_result.*). Wynik MC z --mc-from bierze typy komórek z folderu wejściowego (jak GUI).

Użycie (z katalogu volcano-ca-mc):
    python tools/export_vtk.py results/lava_mc_3d                      # -> results/lava_mc_3d/lava_mc_3d.vti (zlib)
    python tools/export_vtk.py results/test_2d --format ascii --out test_2d.vti
ParaView: File -> Open -> plik .vti -> Apply; kolorowanie wg pola (np. crystal), filtr Threshold (type >= 2)
pokazuje samą lawę i bazalt.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gui.export import FORMATS, vti_fields, write_vti  # noqa: E402
from gui.results import ResultData, ResultError  # noqa: E402


def main() -> int:
    # Konsola Windows bez UTF-8 (np. potok w Git Bash, cp1250) — znaki spoza strony kodowej jako „?”.
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description="Wynik symulacji -> VTK ImageData (.vti) dla ParaView")
    ap.add_argument("folder", help="folder wyniku (ca_result.* i/lub mc_result.*)")
    ap.add_argument("--out", help="plik .vti (domyślnie <folder>/<nazwa folderu>.vti)")
    ap.add_argument("--format", choices=FORMATS, default="zlib",
                    help="zlib — base64 + kompresja (domyślnie), binary — base64 bez kompresji, ascii — tekst")
    args = ap.parse_args()
    folder = Path(args.folder)
    try:
        data = ResultData(folder.name, folder)
    except ResultError as e:
        print(f"Błąd: {e}", file=sys.stderr)
        return 1
    out = Path(args.out) if args.out else folder / f"{folder.resolve().name}.vti"
    write_vti(data, out, args.format)
    nx, ny, nz = data.dims
    names = ", ".join(n for n, _ in vti_fields(data))
    print(f"{out}: {nx}×{ny}×{nz} komórek, pola: {names}, format {args.format}, {out.stat().st_size / 2**20:.2f} MiB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
