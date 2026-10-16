"""Wykres przebiegu krystalizacji Monte Carlo: liczba ziaren i średnia wielkość ziarna vs MCS.

Czyta mc_stats.csv (mcs,grains,meanGrainSize,energy,acceptRate) z jednego lub kilku folderów
wyników i rysuje dwa panele obok siebie (wspólna oś MCS, osobne osie Y — dwie wielkości
o różnej skali nigdy nie dzielą jednej osi). Każdy folder to jedna seria; legenda z nazw
folderów (albo --labels).

Przykłady:
    python tools/plot_mc_stats.py results/mc_full_2d results/mc_full_3d
    python tools/plot_mc_stats.py results/lava_mc_2d results/lava_mc_2d_nomob \
        --labels "z mobilnością" "bez mobilności" --out docs/img/mc_mobilnosc.png
"""

import argparse
import csv
import math
import os
import sys

import matplotlib

matplotlib.use("Agg")  # bez okna — tylko zapis do pliku
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter  # noqa: E402

# Paleta referencyjna (sloty w stałej kolejności, walidowana pod kątem daltonizmu) i tusz.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
THIN_SPACE = " "  # wąska spacja — separator tysięcy na osi (np. 10 000)


def read_stats(folder):
    """Kolumny mc_stats.csv jako listy liczb."""
    path = os.path.join(folder, "mc_stats.csv")
    if not os.path.exists(path):
        sys.exit(f"Brak {path} (czy MC było włączone: mc.enabled = true?)")
    cols = {"mcs": [], "grains": [], "meanGrainSize": []}
    with open(path, encoding="ascii", newline="") as f:
        for row in csv.DictReader(f):
            for k in cols:
                cols[k].append(float(row[k]))
    if not cols["mcs"]:
        sys.exit(f"{path}: brak wierszy danych")
    return cols


def style_axes(ax, title, ylabel):
    """Recesywna oprawa: tylko poziome linie siatki, osie lewa i dolna, tekst w kolorach tuszu."""
    ax.set_facecolor(SURFACE)
    ax.set_title(title, color=INK, fontsize=10, loc="left")
    ax.set_xlabel("krok Monte Carlo (MCS)", color=INK_SECONDARY, fontsize=9)
    ax.set_ylabel(ylabel, color=INK_SECONDARY, fontsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.grid(axis="x", visible=False)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
    ax.tick_params(colors=MUTED, labelsize=8)


def direct_labels(ax, ends, log):
    """Podpisy przy końcach linii (dla <= 4 serii), rozsunięte w pionie, żeby się nie nakładały.
    ends: lista (x, y, tekst). Tekst w kolorze tuszu — kolor serii niesie sama linia."""
    if not ends:
        return
    y0, y1 = ax.get_ylim()
    to_axis = (lambda v: (math.log10(v) - math.log10(y0)) / (math.log10(y1) - math.log10(y0))) if log \
        else (lambda v: (v - y0) / (y1 - y0))
    placed = sorted(((to_axis(y), x, text) for x, y, text in ends), key=lambda e: e[0])
    min_gap = 0.06  # w jednostkach osi (0..1)
    pos = []
    for frac, x, text in placed:
        if pos and frac - pos[-1][0] < min_gap:
            frac = pos[-1][0] + min_gap
        pos.append((frac, x, text))
    for frac, x, text in pos:
        # x = koniec linii (serie mogą kończyć się na różnych MCS), y po rozsunięciu.
        ax.annotate(text, xy=(x, frac), xycoords=("data", "axes fraction"),
                    xytext=(6, 0), textcoords="offset points", va="center", ha="left",
                    fontsize=8, color=INK)


def main():
    parser = argparse.ArgumentParser(description="Liczba ziaren i średnia wielkość ziarna vs MCS -> PNG")
    parser.add_argument("folders", nargs="+", help="foldery wyników z mc_stats.csv (każdy = jedna seria)")
    parser.add_argument("--labels", nargs="+", default=None, help="nazwy serii (domyślnie nazwy folderów)")
    parser.add_argument("--title", default=None, help="tytuł całego rysunku")
    parser.add_argument("--linear", action="store_true", help="liczba ziaren w skali liniowej (domyślnie log.)")
    parser.add_argument("--out", default=None, help="plik PNG (domyślnie <pierwszy folder>/mc_stats.png)")
    args = parser.parse_args()

    if len(args.folders) > len(SERIES):
        sys.exit(f"Najwyżej {len(SERIES)} serii na jednym wykresie — podziel foldery na kilka wykresów")
    labels = args.labels or [os.path.basename(os.path.normpath(f)) for f in args.folders]
    if len(labels) != len(args.folders):
        sys.exit("--labels: liczba nazw musi być równa liczbie folderów")
    series = [(label, read_stats(folder)) for label, folder in zip(labels, args.folders)]

    fig, (ax_g, ax_s) = plt.subplots(1, 2, figsize=(11.5, 4.4), dpi=150, sharex=True)
    fig.patch.set_facecolor(SURFACE)
    log = not args.linear
    style_axes(ax_g, "Liczba ziaren" + (" (skala log.)" if log else ""), "ziarna")
    style_axes(ax_s, "Średnia wielkość ziarna", "komórki na ziarno")
    if log:
        ax_g.set_yscale("log")
        # Podziałka 1-2-5 jako zwykłe liczby (np. 200, 500, 1 000) zamiast samych potęg 10.
        ax_g.yaxis.set_major_locator(LogLocator(base=10, subs=(1.0, 2.0, 5.0)))
        ax_g.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", THIN_SPACE)))
        ax_g.yaxis.set_minor_formatter(NullFormatter())

    for i, (label, s) in enumerate(series):
        color = SERIES[i]  # stała kolejność slotów — kolor należy do serii, nie do jej pozycji w rankingu
        kw = dict(color=color, linewidth=1.6, marker="o", markersize=4, markeredgecolor=SURFACE,
                  markeredgewidth=0.8, label=label)
        ax_g.plot(s["mcs"], s["grains"], **kw)
        ax_s.plot(s["mcs"], s["meanGrainSize"], **kw)

    ax_s.set_ylim(bottom=0)
    if len(series) >= 2:
        # Legenda zawsze przy >= 2 seriach (tożsamość nie może zależeć tylko od koloru) ...
        fig.legend(*ax_g.get_legend_handles_labels(), loc="upper center", ncol=min(len(series), 4),
                   frameon=False, fontsize=9, labelcolor=INK, bbox_to_anchor=(0.5, 0.97 if args.title else 1.0))
        # ... a przy <= 4 seriach dodatkowo podpisy przy końcach linii — tylko gdy wszystkie
        # serie kończą się na tym samym MCS (podpis w środku wykresu nachodziłby na inne linie).
        same_end = len({s["mcs"][-1] for _, s in series}) == 1
        if len(series) <= 4 and same_end:
            fig.canvas.draw()  # ustala zakresy osi przed liczeniem pozycji podpisów
            direct_labels(ax_g, [(s["mcs"][-1], s["grains"][-1], lab) for lab, s in series], log)
            direct_labels(ax_s, [(s["mcs"][-1], s["meanGrainSize"][-1], lab) for lab, s in series], False)
    if args.title:
        fig.suptitle(args.title, color=INK, fontsize=11, x=0.01, ha="left", y=1.03)
    fig.tight_layout(rect=(0, 0, 1, 0.92 if len(series) >= 2 else 1))
    out_path = args.out or os.path.join(args.folders[0], "mc_stats.png")
    fig.savefig(out_path, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    print(f"Zapisano {out_path}")


if __name__ == "__main__":
    main()
