"""(szerokość, długość geograficzna) -> kolumna (x, y) siatki mapy z prawdziwego terenu (tools/fetch_dem.py).

Używa metadanych configs/heightmaps/<name>.json (bbox i wymiary siatki). Dla każdego punktu wypisuje kolumnę,
wysokość terenu (komórki i metry) oraz okno wysokości wokół niej — do sprawdzenia, czy podane współrzędne
krateru trafiają w krater na mapie (krater = lokalne zagłębienie albo najwyższe miejsce stożka w okolicy).
Wynik [x, y] wpisuje się do configu: "vents": {"placement": "positions", "positions": [[x, y], ...]}.

Użycie (z katalogu volcano-ca-mc):
    python tools/latlon_to_grid.py etna 37.751 14.993 37.747 15.000      # pary SZER DŁ
    python tools/latlon_to_grid.py wezuwiusz 40.821 14.426 --window 3
    python tools/latlon_to_grid.py etna --cell 74 80                      # odwrotnie: komórka -> (szer., dł.)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gui.heightmap import parse_csv  # noqa: E402
from tools.fetch_dem import DemError, grid_to_latlon, latlon_to_grid, load_meta  # noqa: E402


def describe_point(h: np.ndarray, meta: dict, lat: float, lon: float, window: int) -> list[str]:
    """Opis punktu: kolumna, wysokość, okno wysokości [m] (północ u góry), lokalne ekstrema w oknie."""
    x, y, fx, fy = latlon_to_grid(meta, lat, lon)
    mz, base = meta["vertical"]["metersPerCell"], meta["vertical"]["baseMeters"]
    ny, nx = h.shape
    lines = [f"{lat:.5f} N, {lon:.5f} E -> x = {x}, y = {y} (ułamkowo {fx:.2f}, {fy:.2f}); "
             f"teren {h[y, x]:.2f} komórki = {h[y, x] * mz + base:.0f} m"]
    y0, y1, x0, x1 = max(0, y - window), min(ny - 1, y + window), max(0, x - window), min(nx - 1, x + window)
    win = h[y0:y1 + 1, x0:x1 + 1] * mz + base
    lines.append(f"  okno {2 * window + 1}×{2 * window + 1} [m], północ u góry, (*) = ta kolumna:")
    lines.append("        " + "".join(f"{xx:>7d}" for xx in range(x0, x1 + 1)))
    for yy in range(y1, y0 - 1, -1):
        row = "".join(f"{win[yy - y0, xx - x0]:>6.0f}{'*' if (xx, yy) == (x, y) else ' '}" for xx in range(x0, x1 + 1))
        lines.append(f"  y={yy:>3d} {row}")
    jmax = np.unravel_index(int(np.argmax(win)), win.shape)
    jmin = np.unravel_index(int(np.argmin(win)), win.shape)
    lines.append(f"  najwyżej w oknie: x = {x0 + jmax[1]}, y = {y0 + jmax[0]} ({win.max():.0f} m); "
                 f"najniżej: x = {x0 + jmin[1]}, y = {y0 + jmin[0]} ({win.min():.0f} m)")
    # Zagłębienie: kolumna niższa od wszystkich 8 sąsiadów (dno krateru w tej rozdzielczości).
    pits = [(xx, yy) for yy in range(max(1, y0), min(ny - 1, y1 + 1)) for xx in range(max(1, x0), min(nx - 1, x1 + 1))
            if h[yy, xx] < h[yy - 1:yy + 2, xx - 1:xx + 2].reshape(-1)[[0, 1, 2, 3, 5, 6, 7, 8]].min()]
    if pits:
        lines.append("  lokalne zagłębienia (niższe od 8 sąsiadów): " +
                     ", ".join(f"[{px}, {py}] {h[py, px] * mz + base:.0f} m" for px, py in pits))
    return lines


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description="(szer., dł.) -> (x, y) siatki mapy z tools/fetch_dem.py")
    ap.add_argument("name", help="nazwa mapy (configs/heightmaps/<name>.json) albo ścieżka do .json/.csv")
    ap.add_argument("coords", nargs="*", type=float, help="pary SZER DŁ [°]")
    ap.add_argument("--window", type=int, default=2, help="promień okna wysokości (komórki)")
    ap.add_argument("--cell", nargs=2, type=int, metavar=("X", "Y"), help="odwrotnie: komórka -> (szer., dł.)")
    args = ap.parse_args(argv)
    try:
        meta = load_meta(args.name)
        csv = Path(args.name).with_suffix(".csv") if args.name.endswith((".json", ".csv")) else \
            ROOT / "configs" / "heightmaps" / f"{args.name}.csv"
        h = parse_csv(csv.read_text(encoding="utf-8"), csv.name)
        if args.cell:
            lat, lon = grid_to_latlon(meta, *args.cell)
            print(f"komórka x = {args.cell[0]}, y = {args.cell[1]} -> środek {lat:.5f} N, {lon:.5f} E")
        if len(args.coords) % 2:
            raise DemError("współrzędne podaje się parami: SZER DŁ")
        for i in range(0, len(args.coords), 2):
            print("\n".join(describe_point(h, meta, args.coords[i], args.coords[i + 1], args.window)))
    except (DemError, OSError) as e:
        print(f"Błąd: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
