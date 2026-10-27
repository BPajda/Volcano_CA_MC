"""Kontrola palety GUI (etap 7): kontrast tekstu WCAG w obu motywach i rozróżnialność kolorów komórek przy daltonizmie.

    python gui/tests/palette_check.py            # tabele na wyjściu + docs/img/ui_paleta_daltonizm.png
    python gui/tests/palette_check.py --wykresy  # kolory wykresów zakładki „Wydajność” (tylko tabele, bez plików)

Kolory czyta z plików (jedno źródło prawdy): zmienne motywów z gui/static/css/style.css, kolory komórek z
gui/static/js/palette.js. Daltonizm: Chromium (Playwright) rysuje próbki z emulacją DevTools
Emulation.setEmulatedVisionDeficiency (protanopia, deuteranopia, tritanopia, achromatopsia), kolory odczytujemy
ze zrzutu i liczymy odległość ΔE w przestrzeni OKLab (×100; ≥ 8 — dobrze rozróżnialne, 6–8 — na granicy,
< 6 — wymagają drugiego kodu: legenda z numerem, podpowiedź, granice ziaren).
"""

from __future__ import annotations

import io
import math
import re
import sys
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSS = ROOT / "gui" / "static" / "css" / "style.css"
PALETTE = ROOT / "gui" / "static" / "js" / "palette.js"
DEFICIENCIES = ["none", "protanopia", "deuteranopia", "tritanopia", "achromatopsia"]
NAMES_PL = {"none": "normalne widzenie", "protanopia": "protanopia", "deuteranopia": "deuteranopia",
            "tritanopia": "tritanopia", "achromatopsia": "achromatopsja"}


# ------------------------------------------------------------------ kolory z plików

def css_theme(block_selector: str) -> dict[str, str]:
    """Zmienne kolorów (#rrggbb) z bloku CSS motywu."""
    text = CSS.read_text(encoding="utf-8")
    start = text.index(block_selector + " {")
    body = text[start:text.index("\n}", start)]
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})\b", body))


def themes() -> dict[str, dict[str, str]]:
    dark = css_theme(":root")
    light = {**dark, **css_theme(':root[data-theme="light"]')}
    return {"ciemny": dark, "jasny": light}


def palette_colors() -> dict:
    """Kolory komórek z palette.js: powietrze / skała w obu motywach, lawa, bazalt, kratery."""
    js = PALETTE.read_text(encoding="utf-8")
    out = {"themes": {}}
    for name, air, rock in re.findall(r"(dark|light): \{ air: '(#\w{6})', rock: '(#\w{6})' \}", js):
        out["themes"]["ciemny" if name == "dark" else "jasny"] = {"powietrze": air, "skała": rock}
    out["lava"] = re.search(r"LAVA_HEX = '(#\w{6})'", js).group(1)
    out["basalt"] = re.search(r"BASALT_HEX = '(#\w{6})'", js).group(1)
    slots = re.search(r"FLOW_SLOTS = \[([^\]]+)\]", js, re.S).group(1)
    out["flow"] = re.findall(r"'(#\w{6})'", slots)
    return out


# ------------------------------------------------------------------ kontrast WCAG i OKLab

def _lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgb(h: str) -> tuple[int, int, int]:
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def luminance(c) -> float:
    r, g, b = (_lin(v / 255) for v in (rgb(c) if isinstance(c, str) else c))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def oklab(c) -> tuple[float, float, float]:
    r, g, b = (_lin(v / 255) for v in (rgb(c) if isinstance(c, str) else c))
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
            1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
            0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_)


def delta_e(a, b) -> float:
    return 100 * math.dist(oklab(a), oklab(b))


TEXT_PAIRS = [  # (opis, kolor tekstu, tło, wymagany kontrast)
    ("tekst główny / karta", "ink", "panel", 4.5), ("tekst główny / tło strony", "ink", "bg", 4.5),
    ("tekst drugorzędny / karta", "ink-2", "panel", 4.5), ("tekst drugorzędny / przycisk", "ink-2", "raised", 4.5),
    ("tekst wyciszony / karta", "muted", "panel", 4.5), ("akcent (lawa) / karta", "accent-text", "panel", 4.5),
    ("tekst na przycisku lawy (początek gradientu)", "on-lava", "lava", 4.5),
    ("tekst na przycisku lawy (koniec gradientu)", "on-lava", "lava-2", 4.5),
    ("OK / karta", "good", "panel", 4.5), ("ostrzeżenie / karta", "warn", "panel", 4.5),
    ("błąd / karta", "crit", "panel", 4.5), ("informacja / karta", "info", "panel", 4.5),
    ("podpisy osi 2D / tło podglądu", "view-ink", "view-bg", 4.5),
    ("obrys fokusu / karta (element interfejsu, 3:1)", "focus", "panel", 3.0),
    ("obrys fokusu / przycisk (element interfejsu, 3:1)", "focus", "raised", 3.0),
]


def contrast_report(th: dict[str, dict[str, str]]) -> list[str]:
    lines = ["| para | motyw ciemny | motyw jasny |", "|---|---|---|"]
    for label, fg, bg, need in TEXT_PAIRS:
        cells = []
        for name in ("ciemny", "jasny"):
            t = th[name]
            r = contrast(t[fg], t[bg])
            cells.append(f"{r:.1f}:1 {'✓' if r >= need else '✗'}")
        lines.append(f"| {label} | {' | '.join(cells)} |")
    return lines


# ------------------------------------------------------------------ daltonizm (emulacja Chromium)

def swatch_page(groups: list[tuple[str, list[tuple[str, str]]]], bg: str) -> str:
    rows = []
    for title, items in groups:
        sw = "".join(f'<div class="s" style="background:{c}"><span>{n}</span></div>' for n, c in items)
        rows.append(f'<div class="g"><div class="t">{title}</div><div class="r">{sw}</div></div>')
    return f"""<!doctype html><meta charset="utf-8"><style>
      body {{ margin: 0; padding: 14px; background: {bg}; font: 600 12px system-ui, sans-serif; color: #111; }}
      .g {{ margin-bottom: 10px; }} .t {{ margin: 0 0 4px; }} .r {{ display: flex; gap: 6px; flex-wrap: wrap; }}
      .s {{ width: 64px; height: 40px; border-radius: 4px; position: relative; }}
      .s span {{ position: absolute; left: 0; right: 0; top: 42px; text-align: center; font-size: 10px; }}
      .r {{ padding-bottom: 14px; }}
    </style>{''.join(rows)}"""


# ------------------------------------------------------------------ kolory wykresów (zakładka „Wydajność”)

# Zestawy kolorów rysowane razem na jednym wykresie (role serii z gui/static/js/perf.js → zmienne CSS motywu).
CHART_SETS = [
    ("metody / przypadki (s1–s3)", ["series-1", "series-2", "series-3"], "categorical"),
    ("algorytmy CA / MC / CA+MC", ["series-ca", "series-mc", "series-camc"], "categorical"),
    ("przed / po, najlepszy / pozostałe", ["muted", "series-ca"], "categorical"),
    ("poziomy pamięci podręcznej D1 / L2 / L3", ["seq-1", "seq-2", "seq-3"], "ordinal"),
]


def chart_check() -> int:
    """Kontrast kolorów wykresów z tłem karty (element graficzny ≥ 3:1) i najmniejsza ΔE par w zestawie przy normalnym
    widzeniu i daltonizmie (emulacja Chromium, jak dla palety komórek)."""
    from PIL import Image
    from playwright.sync_api import sync_playwright

    th = themes()
    groups, keys = [], []
    for name in ("ciemny", "jasny"):
        for title, vars_, _ in CHART_SETS:
            groups.append((f"{title} — {name}", [(v, th[name][v]) for v in vars_]))
            keys.append((name, title, vars_))
    pages = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 760, "height": 300}, device_scale_factor=1)
        cdp = page.context.new_cdp_session(page)
        for name in ("ciemny", "jasny"):
            idx = [i for i, k in enumerate(keys) if k[0] == name]
            page.set_content(swatch_page([groups[i] for i in idx], th[name]["panel"]))
            boxes = page.evaluate("""() => [...document.querySelectorAll('.g')].map((g) => [...g.querySelectorAll('.s')].map((s) => {
                const r = s.getBoundingClientRect(); return [s.textContent, Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)]; }))""")
            for d in DEFICIENCIES:
                cdp.send("Emulation.setEmulatedVisionDeficiency", {"type": d})
                page.wait_for_timeout(120)
                img = Image.open(io.BytesIO(page.screenshot(full_page=True))).convert("RGB")
                for gi, g in zip(idx, boxes):
                    pages[(gi, d)] = {label: img.getpixel((x, y)) for label, x, y in g}
        browser.close()
    print("## Kolory wykresów: kontrast z kartą (≥ 3:1) i najmniejsza ΔE pary w zestawie (OKLab ×100)\n")
    print("| zestaw | motyw | kontrast z kartą | normalne | protanopia | deuteranopia | tritanopia |")
    print("|---|---|---|---|---|---|---|")
    for gi, (name, title, vars_) in enumerate(keys):
        t = th[name]
        con = " / ".join(f"{contrast(t[v], t['panel']):.1f}" for v in vars_)
        cells = []
        for d in ("none", "protanopia", "deuteranopia", "tritanopia"):
            s = pages[(gi, d)]
            worst = min(delta_e(s[a], s[b]) for a, b in combinations(vars_, 2))
            cells.append(f"{worst:.1f}")
        print(f"| {title} | {name} | {con} | " + " | ".join(cells) + " |")
    print("\nΔE ≥ 8 — rozróżnialne, 6–8 — na granicy (wymaga drugiego kodu: znacznik, etykieta, tabela). Rampa D1 / L2 / L3"
          " ma jeden odcień — rozróżnia ją jasność.")
    return 0


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    if "--wykresy" in sys.argv[1:]:
        return chart_check()
    th = themes()
    pal = palette_colors()
    print("## Kontrast tekstu (WCAG 2.1, AA = 4,5:1)\n")
    print("\n".join(contrast_report(th)))

    from PIL import Image
    from playwright.sync_api import sync_playwright

    flow = pal["flow"]
    groups = []
    for name in ("ciemny", "jasny"):
        tc = pal["themes"][name]
        groups.append((f"typ komórki — motyw {name}", [("powietrze", tc["powietrze"]), ("skała", tc["skała"]),
                                                       ("lawa", pal["lava"]), ("bazalt", pal["basalt"])]))
    groups.append(("kratery / ziarna (flowId) 1–10", [(str(i + 1), c) for i, c in enumerate(flow)]))
    html = swatch_page(groups, "#7f7f7f")
    sampled: dict[str, dict[str, tuple[int, int, int]]] = {}
    shots = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 760, "height": 300}, device_scale_factor=1)
        cdp = page.context.new_cdp_session(page)
        page.set_content(html)
        boxes = page.evaluate("""() => [...document.querySelectorAll('.g')].map((g) => [...g.querySelectorAll('.s')].map((s) => {
            const r = s.getBoundingClientRect(); return [s.textContent, Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)]; }))""")
        for d in DEFICIENCIES:
            cdp.send("Emulation.setEmulatedVisionDeficiency", {"type": d})
            page.wait_for_timeout(150)
            png = page.screenshot(full_page=True)
            img = Image.open(io.BytesIO(png)).convert("RGB")
            shots.append((d, img))
            sampled[d] = {}
            for gi, g in enumerate(boxes):
                for label, x, y in g:
                    sampled[d][f"{gi}:{label}"] = img.getpixel((x, y))
        browser.close()

    print("\n## Rozróżnialność kolorów komórek (ΔE OKLab ×100 ze zrzutu Chromium; ≥ 8 dobrze, 6–8 granica)\n")
    print("| widzenie | typ: min. para (ciemny) | typ: min. para (jasny) | kratery 1–3 | 1–5 | 1–7 | 1–10 | krater vs skała / bazalt (min.) |")
    print("|---|---|---|---|---|---|---|---|")
    for d in DEFICIENCIES:
        s = sampled[d]

        def worst(keys):
            best = None
            for a, b in combinations(keys, 2):
                v = delta_e(s[a], s[b])
                if best is None or v < best[0]:
                    best = (v, a.split(":")[1], b.split(":")[1])
            return best

        cells = []
        for gi in (0, 1):
            w = worst([f"{gi}:{n}" for n in ("powietrze", "skała", "lawa", "bazalt")])
            cells.append(f"{w[0]:.1f} ({w[1]}–{w[2]})")
        for k in (3, 5, 7, 10):
            w = worst([f"2:{i + 1}" for i in range(k)])
            cells.append(f"{w[0]:.1f} ({w[1]}–{w[2]})")
        vs = min(delta_e(s[f"2:{i + 1}"], s[f"{gi}:{n}"]) for i in range(len(flow)) for gi in (0, 1) for n in ("skała", "bazalt"))
        cells.append(f"{vs:.1f}")
        print(f"| {NAMES_PL[d]} | " + " | ".join(cells) + " |")

    # Zestawienie zrzutów: wiersz = rodzaj widzenia.
    w = max(im.width for _, im in shots)
    h = sum(im.height + 22 for _, im in shots)
    out = Image.new("RGB", (w, h), (127, 127, 127))
    from PIL import ImageDraw
    dr = ImageDraw.Draw(out)
    y = 0
    for d, im in shots:
        dr.text((14, y + 5), NAMES_PL[d], fill=(20, 20, 20))
        out.paste(im, (0, y + 22))
        y += im.height + 22
    path = ROOT / "docs" / "img" / "ui_paleta_daltonizm.png"
    out.save(path)
    print(f"\nzapisano {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
