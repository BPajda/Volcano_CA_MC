"""Przykładowe mapy wysokości terenu (etap 5) -> configs/heightmaps/*.csv (+ podgląd PNG w skali szarości).

Mapy pokazują, co daje teren z pliku (terrain.type = "file") w porównaniu ze stożkiem z generatora:
  kaldera_wylom     — szeroka kaldera z wyłomem w krawędzi i doliną poniżej: lawa wypełnia kalderę i wypływa
                      tylko przez wyłom (rozwiązuje znany problem „krater szczytowy przelewa się równo na wszystkie
                      strony” — docs/etap-1-automat-komorkowy.md, punkt 6),
  kanion            — stożek z małym kraterem i krętym kanionem wciętym w zbocze i równinę: lawa płynie kanionem,
  podwojny_wulkan   — główny stożek i niższy, starszy stożek obok; krater ma obniżenie krawędzi w stronę drugiego
                      stożka — lawa spływa na przełęcz i rozdziela się na boki starszego stożka.
Mapy są deterministyczne (stały seed szumu). Wysokości w komórkach; wiersz CSV y = 0..ny−1, kolumna x.

Użycie (z katalogu volcano-ca-mc):
    python tools/make_heightmaps.py                 # configs/heightmaps/*.csv + *.png (skala szarości)
    python tools/make_heightmaps.py --out X --no-png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gui.heightmap import heights_to_csv, smooth  # noqa: E402  (ten sam zapis CSV co import z GUI)

N = 100        # mapy 100 × 100 kolumn (nz w configach: 45)
APRON = 8.0    # łagodny spadek całej mapy ku brzegom (bez płaskiej równiny, na której lawa rozlewa się wszędzie)


def grid(n: int = N):
    y, x = np.mgrid[0:n, 0:n].astype(np.float64)
    c = (n - 1) / 2
    return x - c, y - c


def noise(n: int, seed: int, amp: float, radius: float = 4) -> np.ndarray:
    """Gładki szum: losowe wartości wygładzone filtrem — nierówności bez dołków, w których lawa by grzęzła."""
    rng = np.random.default_rng(seed)
    return amp * smooth(rng.uniform(-1, 1, (n, n)), radius) * 3.0


def cone(dx, dy, peak: float, base: float) -> np.ndarray:
    return peak * np.clip(1 - np.hypot(dx, dy) / base, 0, None)


def apron(dx, dy) -> np.ndarray:
    """Podnóże: od APRON w środku do ~0 w narożnikach mapy."""
    return APRON * np.clip(1 - np.hypot(dx, dy) / (0.75 * N), 0, None)


def angle_to(ang, toward: float) -> np.ndarray:
    """Różnica kątów w (−π, π]."""
    return np.angle(np.exp(1j * (ang - toward)))


def kaldera_wylom() -> tuple[np.ndarray, str]:
    dx, dy = grid()
    r = np.hypot(dx, dy)
    ang = np.arctan2(dy, dx)                      # 0 = wschód (+x)
    peak, base, R, depth = 34.0, 46.0, 9.0, 6.0
    h = apron(dx, dy) + cone(dx, dy, peak, base) + noise(N, 11, 0.5)
    rim = APRON * (1 - R / (0.75 * N)) + peak * (1 - R / base)
    floor = rim - depth
    h = np.where(r < R, floor, h)
    # Wyłom: na kierunku wschodnim krawędź obniżona do floor + 2 (poziom przelewu kaldery).
    breach = (np.abs(ang) < np.radians(18)) & (r >= R - 1) & (r < R + 4)
    h = np.where(breach, np.minimum(h, floor + 2 + 0.3 * np.clip(r - R, 0, None)), h)
    # Dolina poniżej wyłomu: rynna o głębokości 4 komórek (strome ściany) wzdłuż promienia na wschód.
    across = np.abs(dy)
    valley = (dx > R) & (across < 4)
    h = np.where(valley, h - 4.0 * np.clip(1.6 - across / 2.5, 0, 1), h)
    return np.clip(h, 0, None), f"kaldera (promień {R:g}, głębokość {depth:g}) z wyłomem na wschód i doliną poniżej"


def kanion() -> tuple[np.ndarray, str]:
    dx, dy = grid()
    r = np.hypot(dx, dy)
    peak, base, R, depth = 32.0, 42.0, 4.0, 3.0
    h = apron(dx, dy) + cone(dx, dy, peak, base) + noise(N, 23, 0.4)
    rim = APRON * (1 - R / (0.75 * N)) + peak * (1 - R / base)
    h = np.where(r < R, rim - depth, h)
    # Kręty kanion od krawędzi krateru na południowy wschód: oś kanionu = kąt zmieniający się z promieniem.
    ang = np.arctan2(dy, dx)
    axis = np.radians(-40) + 0.45 * np.sin(r / 6.0)
    across = np.abs(angle_to(ang, axis)) * np.maximum(r, 1)   # odległość od osi kanionu (po łuku)
    inside = (across < 2.2) & (r >= R - 1)
    bottom = np.minimum(h - 5.0, rim - depth + 1)    # dno 5 komórek pod zboczem; u góry = przelew krateru
    h = np.where(inside, np.maximum(bottom, 0.0), h)
    return np.clip(h, 0, None), f"stożek z kraterem (promień {R:g}) i krętym kanionem (głębokość 5) na południowy wschód"


def podwojny_wulkan() -> tuple[np.ndarray, str]:
    dx, dy = grid()
    r = np.hypot(dx, dy)
    ox, oy = 26.0, 20.0                               # starszy stożek na północnym wschodzie
    main = cone(dx, dy, 30.0, 40.0)
    second = cone(dx - ox, dy - oy, 20.0, 24.0)
    h = apron(dx, dy) + np.maximum(main, second) + noise(N, 37, 0.5)
    R, depth = 5.0, 3.0
    rim = APRON * (1 - R / (0.75 * N)) + 30.0 * (1 - R / 40.0)
    h = np.where(r < R, rim - depth, h)
    # Obniżenie krawędzi krateru w stronę drugiego stożka — tamtędy lawa wypływa na przełęcz.
    ang = np.arctan2(dy, dx)
    toward = np.arctan2(oy, ox)
    notch = (np.abs(angle_to(ang, toward)) < np.radians(20)) & (r >= R - 1) & (r < R + 3)
    h = np.where(notch, np.minimum(h, rim - depth + 1.5), h)
    # Płytka rynna od obniżenia krawędzi do przełęczy (głęb. 3) — lawa spływa w stronę starszego stożka.
    along = dx * np.cos(toward) + dy * np.sin(toward)
    across = np.abs(-dx * np.sin(toward) + dy * np.cos(toward))
    trough = (along > R) & (along < np.hypot(ox, oy) - 12) & (across < 3)
    h = np.where(trough, h - 3.0 * np.clip(1.5 - across / 2, 0, 1), h)
    return np.clip(h, 0, None), (f"główny stożek z kraterem (promień {R:g}) i niższy stożek na północnym wschodzie; "
                                 "krawędź krateru obniżona w stronę przełęczy")


MAPS = {"kaldera_wylom": kaldera_wylom, "kanion": kanion, "podwojny_wulkan": podwojny_wulkan}


def save_png(h: np.ndarray, path: Path) -> None:
    """Mapa jako obraz PNG w skali szarości (biel = najwyżej, północ u góry) — podgląd i przykład do importu
    obrazu w GUI („Importuj mapę”: wysokość maks. = najwyższy punkt mapy)."""
    from PIL import Image
    g = np.round(255 * (h - h.min()) / max(h.max() - h.min(), 1e-9)).astype(np.uint8)
    Image.fromarray(g[::-1, :]).save(path)


def main() -> int:
    # Konsola Windows bez UTF-8 (np. potok w Git Bash, cp1250) — znaki spoza strony kodowej jako „?”.
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=str(ROOT / "configs" / "heightmaps"))
    ap.add_argument("--no-png", action="store_true", help="bez obrazów PNG w skali szarości")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, fn in MAPS.items():
        h, desc = fn()
        h = np.round(h, 1)
        (out / f"{name}.csv").write_text(heights_to_csv(h, f"{desc} (tools/make_heightmaps.py)"), encoding="utf-8",
                                         newline="\n")
        if not args.no_png:
            save_png(h, out / f"{name}.png")
        print(f"{out / name}.csv: {h.shape[1]}×{h.shape[0]}, wysokość {h.min():.1f}–{h.max():.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
