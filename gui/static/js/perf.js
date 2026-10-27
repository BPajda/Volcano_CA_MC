// Zakładka „Wydajność”: wyniki optymalizacji i zrównoleglenia w jednym miejscu — nagłówek z zasadą zgodności bitowej
// i panelem „Pojęcia”, „Podsumowanie” i pięć sekcji (Optymalizacja sekwencyjna, OpenMP, MPI, Typy MPI i MPI-IO, Testy
// wydajności) jako zakładki wewnętrzne.
//  - dane: jeden plik statyczny /data/wydajnosc.json (gui/static/data/, generuje tools/wydajnosc_gui.py z plików
//    bench/results/) — ładowany raz, przy pierwszym wejściu w zakładkę; ten moduł niczego nie liczy i nie ma w nim
//    żadnej liczby z pomiarów: wykres = widok z pliku (serie, osie, podpowiedzi, wnioski, „Jak czytać”, warunki, źródła),
//  - wykresy Chart.js tworzone przy pierwszym wejściu w sekcję; po zmianie motywu albo kompilatora — od nowa,
//  - widok wykresu wybierają: przełącznik MSVC / GCC (dla wykresów z danymi obu kompilatorów) i przełączniki wykresu
//    (przypadek, miara…); brak pomiaru dla wyboru — najbliższy dostępny widok z adnotacją,
//  - karta wykresu: tytuł → wykres → wniosek → „Jak czytać” → warunki → „Skąd dane” (zwinięte) → „Pobierz PDF”
//    (dokument z docs/pdf/ przez /api/doc/pdf), do tego widok tabeli i eksport PNG,
//  - rodzaje wykresów: line, scatter, bar, hbar (z wierszami-nagłówkami i notatkami wierszy) i dots (wiersze z punktami,
//    np. wykres hantlowy: dwa punkty połączone kreską, etykiety punktów i tekst z prawej strony wiersza).
// Kolory tylko z motywu (theme.js: --series-*, --seq-*, CA / MC / CA+MC); rola serii w pliku danych wybiera kolor.

import { getJSON } from './api.js';
import { onThemeChange, themeColors } from './theme.js';
import { $, $$, downloadBlob, esc, icon, notice, store } from './util.js';

const DATA_URL = '/data/wydajnosc.json';
const KEY_SECTION = 'volcano.perf.section';
const KEY_COMPILER = 'volcano.perf.compiler';
const NONE = 'brak';

// ---------------------------------------------------------------- liczby po polsku

const NF = {};
const nf = (d) => (NF[d] ||= new Intl.NumberFormat('pl-PL', { minimumFractionDigits: d, maximumFractionDigits: d }));
function digits(v) {
  const a = Math.abs(v);
  return a >= 100 ? 0 : a >= 10 ? 1 : a >= 1 ? 2 : a >= 0.01 ? 3 : 4;
}
const dec = (v, d = digits(v)) => nf(d).format(v);
const CLEAN = new Intl.NumberFormat('pl-PL', { maximumFractionDigits: 4 });

/** Wartość z jednostką osi (fmt z pliku danych: ms, times, pct, int, pow10, num). */
function fmtValue(v, fmt) {
  if (v == null || Number.isNaN(v)) return NONE;
  switch (fmt) {
    case 'ms': return v >= 1000 ? `${dec(v / 1000)} s` : `${dec(v)} ms`;
    case 'times': return `×${v < 0.1 ? nf(3).format(v) : nf(2).format(v)}`;
    case 'pow10': return `×${dec(10 ** v, 10 ** v >= 100 ? 0 : 2)}`;
    case 'pct': return `${nf(v !== 0 && Math.abs(v) < 10 ? 1 : 0).format(v)}%`;
    case 'int': return nf(0).format(v);
    default: return dec(v);
  }
}

/** Podpis podziałki: na osi log. tylko 1, 2 i 5 × 10^k — mniej, gdy na dekadę przypada mało miejsca (1 i 3 albo
 *  same potęgi 10; siatka zostaje), pow10 — tylko całkowite potęgi. */
function tickLabel(v, fmt, log, scale) {
  if (typeof v !== 'number') return v;
  if (log && v > 0) {
    const decades = scale ? Math.log10(scale.max / scale.min) : 1;
    const px = scale ? (scale.isHorizontal() ? scale.width : scale.height) / Math.max(decades, 0.1) : 999;
    const keep = px >= (scale?.isHorizontal() ? 230 : 120) ? [1, 2, 5] : px >= (scale?.isHorizontal() ? 120 : 60) ? [1, 3] : [1];
    const m = v / 10 ** Math.floor(Math.log10(v) + 1e-9);
    if (!keep.some((k) => Math.abs(m - k) < 1e-6)) return '';
  }
  if (fmt === 'pow10') return Number.isInteger(Math.round(v * 1e6) / 1e6) ? `×${nf(0).format(10 ** v)}` : '';
  if (fmt === 'ms') return v >= 1000 ? `${CLEAN.format(v / 1000)} s` : `${CLEAN.format(v)} ms`;
  if (fmt === 'times') return `×${CLEAN.format(v)}`;
  if (fmt === 'pct') return `${nf(0).format(v)}%`;
  return CLEAN.format(v);
}

const labelText = (l) => (Array.isArray(l) ? l.join(' ') : String(l ?? ''));
/** Długi podpis kategorii słupków poziomych w dwóch wierszach (podział po przecinku) — bez ucinania przy osi. */
const wrapLabel = (l) => {
  if (Array.isArray(l) || String(l).length <= 30) return l;
  const i = String(l).lastIndexOf(', ');
  return i > 0 ? [l.slice(0, i + 1), l.slice(i + 2)] : l;
};

// ---------------------------------------------------------------- kolory z motywu

/** Kolor roli serii (plik danych mówi, co seria znaczy; motyw — jaki to kolor). */
function roleColor(role, th) {
  switch (role) {
    case 's1': return th.series[0];
    case 's2': return th.series[1];
    case 's3': return th.series[2];
    case 'ca': case 'after': return th.seriesCa;
    case 'mc': return th.seriesMc;
    case 'camc': return th.seriesCaMc;
    case 'seq1': return th.seq[0];
    case 'seq2': return th.seq[1];
    case 'seq3': return th.seq[2];
    default: return th.muted;  // before, muted, ideal
  }
}

/** #rrggbb + przezroczystość → rgba() (wypełnienia pasm i słupków „obrysowych”). */
function alpha(hex, a) {
  const m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(hex || '');
  return m ? `rgba(${parseInt(m[1], 16)}, ${parseInt(m[2], 16)}, ${parseInt(m[3], 16)}, ${a})` : hex;
}

/** Mały znacznik SVG do legendy HTML (kształty jak pointStyle Chart.js). */
function markerSvg(marker, color, outline, panel) {
  const fill = outline ? panel : color;
  const attrs = `fill="${esc(fill)}" stroke="${esc(color)}" stroke-width="1.6"`;
  const shapes = {
    circle: `<circle cx="7" cy="7" r="4.6" ${attrs}/>`,
    rect: `<rect x="2.6" y="2.6" width="8.8" height="8.8" ${attrs}/>`,
    triangle: `<path d="M7 2 L12 11.5 L2 11.5 Z" ${attrs}/>`,
    rectRot: `<path d="M7 1.6 L12.4 7 L7 12.4 L1.6 7 Z" ${attrs}/>`,
    star: `<path d="M7 1.5 L8.6 5.3 L12.7 5.6 L9.6 8.3 L10.5 12.3 L7 10.2 L3.5 12.3 L4.4 8.3 L1.3 5.6 L5.4 5.3 Z" ${attrs}/>`,
    line: `<line x1="1" y1="7" x2="13" y2="7" stroke="${esc(color)}" stroke-width="2" stroke-dasharray="3 2"/>`,
  };
  return `<svg class="perf-mk" width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">${shapes[marker] || shapes.circle}</svg>`;
}

// ---------------------------------------------------------------- wtyczki Chart.js (wąsy, etykiety, linie odniesienia)

const viewOf = (chart) => chart.options.plugins.perfRefLines?.view || {};

/** Wąsy min–max (rozrzut powtórzeń): zbiory danych z tablicami _lo / _hi. */
const whiskers = {
  id: 'perfWhiskers',
  afterDatasetsDraw(chart) {
    const { ctx } = chart;
    const horiz = chart.options.indexAxis === 'y';
    const vs = horiz ? chart.scales.x : chart.scales.y;
    chart.data.datasets.forEach((ds, di) => {
      if (!ds._lo || !chart.isDatasetVisible(di)) return;
      ctx.save();
      ctx.strokeStyle = ds._whisker;
      ctx.lineWidth = 1.2;
      chart.getDatasetMeta(di).data.forEach((el, i) => {
        const lo = ds._lo[i], hi = ds._hi[i];
        if (lo == null || hi == null || el.skip) return;
        const a = vs.getPixelForValue(lo), b = vs.getPixelForValue(hi), cap = 3;
        ctx.beginPath();
        if (horiz) {
          ctx.moveTo(a, el.y); ctx.lineTo(b, el.y);
          ctx.moveTo(a, el.y - cap); ctx.lineTo(a, el.y + cap); ctx.moveTo(b, el.y - cap); ctx.lineTo(b, el.y + cap);
        } else {
          ctx.moveTo(el.x, a); ctx.lineTo(el.x, b);
          ctx.moveTo(el.x - cap, a); ctx.lineTo(el.x + cap, a); ctx.moveTo(el.x - cap, b); ctx.lineTo(el.x + cap, b);
        }
        ctx.stroke();
      });
      ctx.restore();
    });
  },
};

/** Etykiety przy końcu słupka (np. „×36”, „0 chybień” zamiast niewidocznego zera) i notatki wierszy słupków poziomych
 *  (np. „nie mierzono”) — kolor tekstu, nie serii. */
const valueLabels = {
  id: 'perfLabels',
  afterDatasetsDraw(chart) {
    if (chart.config.type === 'scatter') return;
    const { ctx, chartArea: area } = chart;
    const horiz = chart.options.indexAxis === 'y';
    const th = themeColors();
    const view = viewOf(chart);
    chart.data.datasets.forEach((ds, di) => {
      if (!ds._labels || !chart.isDatasetVisible(di)) return;
      ctx.save();
      ctx.fillStyle = th.ink;
      ctx.font = `600 11px ${th.font}`;
      chart.getDatasetMeta(di).data.forEach((el, i) => {
        const t = ds._labels[i];
        if (!t) return;
        if (ds.data[i] == null) {  // zero na skali log. albo brak słupka z opisem: tekst przy początku osi
          if (!horiz) return;
          ctx.fillStyle = th.ink2;
          ctx.textAlign = 'left';
          ctx.textBaseline = 'middle';
          ctx.fillText(t, area.left + 6, chart.scales.y.getPixelForValue(i));
          ctx.fillStyle = th.ink;
          return;
        }
        if (el.skip) return;
        if (horiz) {
          const left = el.x < el.base - 0.5;  // słupek w lewo od podstawy (krok wolniejszy niż ×1): tekst za podstawą
          const hi = ds._hi?.[i] != null ? chart.scales.x.getPixelForValue(ds._hi[i]) : el.x;
          ctx.textBaseline = 'middle';
          ctx.textAlign = 'left';
          if (left) {
            ctx.fillText(t, el.base + 5, el.y);
          } else {
            ctx.fillText(t, Math.min(Math.max(el.x, hi) + 5, chart.width - ctx.measureText(t).width - 2), el.y);
          }
        } else {
          const hi = ds._hi?.[i] != null ? chart.scales.y.getPixelForValue(ds._hi[i]) : el.y;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'bottom';
          ctx.fillText(t, el.x, Math.min(el.y, hi) - 4);
        }
      });
      ctx.restore();
    });
    if (horiz && view.rowNotes) {
      ctx.save();
      ctx.fillStyle = th.ink2;
      ctx.font = `italic 11.5px ${th.font}`;
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      const x0 = chart.scales.x.getPixelForValue(view.x?.base ?? view.x?.min ?? 0);
      view.rowNotes.forEach((n, i) => {
        if (n) ctx.fillText(n, Math.max(x0, area.left) + 8, chart.scales.y.getPixelForValue(i));
      });
      ctx.restore();
    }
  },
};

/** Linie i pasma odniesienia z widoku (np. „×1 = bez zmian”, idealnie S = 8, progi L2 / L3, pasmo ±10%) — pod danymi. */
const refLines = {
  id: 'perfRefLines',
  beforeDatasetsDraw(chart) {
    const view = viewOf(chart);
    const { ctx, chartArea: a } = chart;
    const th = themeColors();
    const horiz = chart.options.indexAxis === 'y';
    ctx.save();
    if (view.xband) {
      const sx = chart.scales.x;
      const x0 = Math.max(sx.getPixelForValue(view.xband.from), a.left), x1 = Math.min(sx.getPixelForValue(view.xband.to), a.right);
      ctx.fillStyle = alpha(th.ink, th.name === 'dark' ? 0.08 : 0.06);
      ctx.fillRect(x0, a.top, x1 - x0, a.bottom - a.top);
      ctx.fillStyle = th.ink2;
      ctx.font = `600 11px ${th.font}`;
      ctx.textAlign = 'right';
      ctx.textBaseline = 'top';
      ctx.fillText(view.xband.label || '', x1 - 4, a.top + 3);
    }
    ctx.strokeStyle = th.muted;
    ctx.fillStyle = th.ink2;
    ctx.lineWidth = 1.2;
    ctx.setLineDash([5, 4]);
    ctx.font = `11px ${th.font}`;
    for (const h of view.hlines || []) {
      const sc = horiz ? chart.scales.x : chart.scales.y;
      const p = sc.getPixelForValue(h.y);
      if (!Number.isFinite(p)) continue;
      ctx.beginPath();
      if (horiz) { ctx.moveTo(p, a.top); ctx.lineTo(p, a.bottom); } else { ctx.moveTo(a.left, p); ctx.lineTo(a.right, p); }
      ctx.stroke();
      ctx.textBaseline = 'bottom';
      if (horiz) {
        ctx.textAlign = 'left';
        ctx.fillText(h.label || '', p + 4, a.top + 12);
      } else {
        ctx.textAlign = 'right';
        ctx.fillText(h.label || '', a.right - 4, p - 3);
      }
    }
    for (const v of view.vlines || []) {
      const p = chart.scales.x.getPixelForValue(v.x);
      if (!Number.isFinite(p) || p < a.left || p > a.right) continue;
      ctx.beginPath();
      ctx.moveTo(p, a.top);
      ctx.lineTo(p, a.bottom);
      ctx.stroke();
      if (!v.label) continue;
      ctx.save();
      ctx.translate(p - 4, a.top + 6);
      ctx.rotate(-Math.PI / 2);
      ctx.textAlign = 'right';
      ctx.textBaseline = 'bottom';
      ctx.fillText(v.label, 0, 0);
      ctx.restore();
    }
    ctx.restore();
  },
};

/** Wykres „dots”: kreski łączące punkty wiersza (wykres hantlowy), etykiety punktów, tekst z prawej strony wiersza
 *  (np. „×19 mniej”) i notatki wierszy bez punktów (np. „0 chybień w obu wariantach”). */
const dotsDecor = {
  id: 'perfDots',
  beforeDatasetsDraw(chart) {
    const view = viewOf(chart);
    if (view.kind !== 'dots' || !view.connect) return;
    const { ctx } = chart;
    const th = themeColors();
    const sx = chart.scales.x, sy = chart.scales.y;
    ctx.save();
    ctx.strokeStyle = th.muted;
    ctx.lineWidth = 2.4;
    view.labels.forEach((_, i) => {
      const xs = view.series.flatMap((s) => [s.data[i]].flat()).filter((v) => v != null && (!view.x.log || v > 0));
      if (xs.length < 2) return;
      const y = sy.getPixelForValue(i);
      ctx.beginPath();
      ctx.moveTo(sx.getPixelForValue(Math.min(...xs)), y);
      ctx.lineTo(sx.getPixelForValue(Math.max(...xs)), y);
      ctx.stroke();
    });
    ctx.restore();
  },
  afterDatasetsDraw(chart) {
    const view = viewOf(chart);
    if (view.kind !== 'dots') return;
    const { ctx, chartArea: a } = chart;
    const th = themeColors();
    const sx = chart.scales.x, sy = chart.scales.y;
    ctx.save();
    ctx.textBaseline = 'middle';
    view.labels.forEach((_, i) => {
      const y = sy.getPixelForValue(i);
      // etykiety punktów: lewy punkt wiersza — tekst na lewo, prawy — na prawo (bliskie punkty się nie zasłaniają)
      const pts = view.series.map((s) => ({ v: s.data[i], t: s.ptLabels?.[i] })).filter((p) => p.t);
      const vals = pts.filter((p) => p.v != null && !Array.isArray(p.v)).map((p) => p.v);
      ctx.font = `11px ${th.font}`;
      ctx.fillStyle = th.ink2;
      for (const p of pts) {
        if (p.v == null) {  // zero na skali log.: opis przy początku osi
          ctx.textAlign = 'left';
          ctx.fillText(p.t, a.left + 4, y);
          continue;
        }
        const px = sx.getPixelForValue(p.v);
        const isLeft = vals.length > 1 && p.v === Math.min(...vals);
        ctx.textAlign = isLeft ? 'right' : 'left';
        ctx.fillText(p.t, isLeft ? px - 9 : px + 9, y);
      }
      const rt = view.rowText?.[i];
      if (rt) {
        ctx.font = `600 11px ${th.font}`;
        ctx.fillStyle = th.ink;
        ctx.textAlign = 'left';
        ctx.fillText(rt, a.right + 8, y);
      }
      const note = view.rowNotes?.[i];
      if (note) {
        ctx.font = `italic 11.5px ${th.font}`;
        ctx.fillStyle = th.ink2;
        ctx.textAlign = 'left';
        ctx.fillText(note, a.left + 6, y);
      }
    });
    ctx.restore();
  },
};

// ---------------------------------------------------------------- wykres z widoku

const kindOf = (spec, view) => view?.kind || spec.kind;
const isLineKind = (kind) => kind === 'line' || kind === 'scatter';
/** Oś x liczbowa (punkty [x, y]) — linie bez etykiet kategorii; linia z etykietami (np. procesy × wątki) ma oś kategorii. */
const numericX = (kind, view) => isLineKind(kind) && !view.labels;

/** Zbiory danych Chart.js z serii widoku (kolory z ról, znaczniki, pasma, wąsy, podpowiedzi). */
function datasets(kind, view, th) {
  const out = [];
  const line = isLineKind(kind);
  for (const s of view.series) {
    const c = roleColor(s.role, th);
    const quiet = s.role === 'ideal' || (!s.tips && s.marker === 'none');
    if (kind === 'dots') {  // wiersz i = współrzędna y; wartość albo lista wartości (kilka punktów w wierszu)
      const pts = [], tips = [], cols = [];
      s.data.forEach((v, i) => {
        [v].flat().forEach((x, j) => {
          if (x == null || (view.x.log && x <= 0)) return;
          pts.push({ x, y: i });
          tips.push(Array.isArray(s.tips?.[i]) ? s.tips[i][j] : s.tips?.[i] || '');
          cols.push(roleColor(s.roles?.[i] || s.role, th));
        });
      });
      out.push({ label: s.name, data: pts, _tips: tips, _role: s.role, pointStyle: s.marker || 'circle',
        pointRadius: 5.5, pointHoverRadius: 7.5, pointHitRadius: 8, pointBorderWidth: 2,
        pointBackgroundColor: s.outline ? th.panel : cols, pointBorderColor: s.outline ? cols : th.panel,
        backgroundColor: c, borderColor: c, showLine: false });
      continue;
    }
    const pts = numericX(kind, view) ? s.data.map((p) => (p == null ? null : { x: p[0], y: p[1] })) : s.data;
    if (s.band && numericX(kind, view)) {
      const xs = s.data.map((p) => p?.[0]);
      out.push({ label: '', data: s.band.lo.map((y, i) => ({ x: xs[i], y })), borderWidth: 0, pointRadius: 0,
        pointHitRadius: 0, fill: false, _aux: true });
      out.push({ label: '', data: s.band.hi.map((y, i) => ({ x: xs[i], y })), borderWidth: 0, pointRadius: 0,
        pointHitRadius: 0, fill: '-1', backgroundColor: alpha(c, th.name === 'dark' ? 0.16 : 0.12), _aux: true });
    }
    const ds = { label: s.name, data: pts, _tips: s.tips, _lo: s.lo, _hi: s.hi, _labels: s.labels, _quiet: quiet,
      _role: s.role, _marker: s.marker, _whisker: alpha(th.ink2, 0.85) };
    if (line) {
      const none = s.marker === 'none';
      const markers = s.markers || null;
      Object.assign(ds, {
        type: 'line', borderColor: s.role === 'ideal' ? th.muted : c, backgroundColor: c,
        borderWidth: s.thin ? 1.4 : 2, borderDash: s.dash ? [6, 4] : [], showLine: s.line !== false && kind !== 'scatter',
        pointStyle: markers || (none ? false : s.marker || 'circle'),
        pointRadius: none ? 0 : 4.5, pointHoverRadius: none ? 0 : 6.5, pointHitRadius: none ? 0 : 10,
        pointBorderWidth: 2, pointBorderColor: s.outline ? c : th.panel, pointBackgroundColor: s.outline ? th.panel : c,
        tension: 0, spanGaps: true, fill: false, borderCapStyle: 'round', borderJoinStyle: 'round',
      });
      if (s.role === 'ideal' && kind === 'scatter') ds.showLine = true;
    } else {
      const fills = s.roles ? s.roles.map((r) => roleColor(r, th)) : c;
      const thick = view.barThickness || (kind === 'hbar' ? 18 : 24);
      Object.assign(ds, {
        backgroundColor: s.outline ? alpha(c, 0.16) : fills, borderColor: s.outline ? c : th.panel,
        borderWidth: view.stacked ? { right: 2 } : (s.outline ? 1.5 : 0), borderRadius: view.stacked ? 0 : 3,
        borderSkipped: 'start', maxBarThickness: thick, categoryPercentage: 0.82, barPercentage: 0.9,
      });
      const base = (kind === 'hbar' ? view.x : view.y)?.base;
      if (base != null) ds.base = base;
    }
    out.push(ds);
  }
  return out;
}

/** Elementy legendy: kreska dla linii bez znaczników, znacznik dla punktów, prostokąt dla słupków. */
function legendLabels(chart, kind, view, th) {
  if (view.legend) {
    return view.legend.map((l) => ({
      text: l.label, fillStyle: l.outline ? th.panel : roleColor(l.role, th), strokeStyle: roleColor(l.role, th),
      lineWidth: l.outline ? 2 : 0, pointStyle: l.marker || (isLineKind(kind) ? 'circle' : 'rect'), fontColor: th.ink,
      hidden: false,
    }));
  }
  return chart.data.datasets.map((ds, i) => {
    if (ds._aux) return null;
    const lineOnly = isLineKind(kind) && (ds.pointStyle === false || Array.isArray(ds.pointStyle));
    return {
      text: ds.label, datasetIndex: i, hidden: !chart.isDatasetVisible(i), fontColor: th.ink,
      fillStyle: isLineKind(kind) ? ds.pointBackgroundColor || ds.borderColor : (Array.isArray(ds.backgroundColor)
        ? ds.backgroundColor[0] : ds.backgroundColor),
      strokeStyle: ds.borderColor, lineWidth: isLineKind(kind) ? 2 : 0, lineDash: ds.borderDash,
      pointStyle: lineOnly && !Array.isArray(ds.pointStyle) ? 'line' : isLineKind(kind)
        ? (Array.isArray(ds.pointStyle) ? 'circle' : ds.pointStyle) : 'rect',
    };
  }).filter(Boolean);
}

function axisSpec(ax, th, { category = false, stacked = false, headers = [] } = {}) {
  ax = ax || {};
  const title = ax.title ? { display: true, text: ax.title, color: th.ink2 } : { display: false };
  if (category) {
    return { type: 'category', title, stacked, grid: { display: false }, border: { color: th.chartAxis },
      ticks: { autoSkip: false, maxRotation: 0,
        color: (ctx) => (headers.includes(ctx.index) ? th.ink : th.ink2),
        font: (ctx) => (headers.includes(ctx.index) ? { weight: '700' } : undefined) } };
  }
  const s = {
    type: ax.log ? 'logarithmic' : 'linear', title, stacked, min: ax.min, max: ax.max,
    grid: { color: th.chartGrid }, border: { color: th.chartAxis },
    ticks: { color: th.ink2, maxRotation: 0, autoSkip: !ax.log, callback(v) { return tickLabel(v, ax.fmt, ax.log, this); } },
  };
  if (ax.ticks) s.afterBuildTicks = (scale) => { scale.ticks = ax.ticks.map((value) => ({ value })); };
  if (ax.fmt === 'pow10') s.ticks.stepSize = 1;
  return s;
}

/** Oś wierszy wykresu „dots”: liczby 0…n−1 od góry, podpisy z etykiet widoku, wiersze-nagłówki pogrubione. */
function rowAxis(view, th) {
  const n = view.labels.length, headers = view.headers || [];
  return {
    type: 'linear', reverse: true, min: -0.6, max: n - 0.4, grid: { display: false }, border: { color: th.chartAxis },
    afterBuildTicks: (scale) => { scale.ticks = view.labels.map((_, value) => ({ value })); },
    ticks: { autoSkip: false, callback: (v) => labelText(view.labels[v]),
      color: (ctx) => (headers.includes(ctx.tick?.value) ? th.ink : th.ink2),
      font: (ctx) => (headers.includes(ctx.tick?.value) ? { weight: '700' } : undefined) },
  };
}

/** Konfiguracja Chart.js dla widoku wykresu. */
function chartConfig(spec, view) {
  const th = themeColors();
  const kind = kindOf(spec, view);
  const dots = kind === 'dots';
  const horiz = kind === 'hbar';
  const line = isLineKind(kind);
  const numX = numericX(kind, view);
  const valueAx = horiz || dots ? view.x : view.y;
  const valueFmt = view.valueFmt || valueAx?.fmt;
  const hasLabels = view.series.some((s) => s.labels);
  const headers = view.headers || [];
  const scales = dots
    ? { x: axisSpec(view.x, th), y: rowAxis(view, th) }
    : line
      ? { x: axisSpec(view.x, th, { category: !numX }), y: axisSpec(view.y, th) }
      : horiz
        ? { x: axisSpec(view.x, th, { stacked: view.stacked }), y: axisSpec(view.y, th, { category: true, stacked: view.stacked, headers }) }
        : { x: axisSpec(view.x, th, { category: true, stacked: view.stacked }), y: axisSpec(view.y, th, { stacked: view.stacked }) };
  if (!dots) {
    // Zakres osi wartości obejmuje wąsy (min–max) i linie odniesienia — Chart.js liczy go tylko z median.
    const vk = horiz ? 'x' : 'y', vs = scales[vk];
    const extra = [...view.series.flatMap((s) => [...(s.lo || []), ...(s.hi || [])]),
      ...(view.hlines || []).map((h) => h.y)].filter((v) => v != null && (!valueAx?.log || v > 0));
    if (extra.length && valueAx?.max == null) vs.suggestedMax = Math.max(...extra);
    if (extra.length && valueAx?.min == null && (valueAx?.log || line)) vs.suggestedMin = Math.min(...extra);  // słupki liniowe — od 0
    if (numX && view.vlines?.length && view.x.max == null) scales.x.suggestedMax = Math.max(...view.vlines.map((v) => v.x));
    if (hasLabels && !valueAx?.log && valueAx?.max == null) vs.grace = '8%';
  }
  const rowTextW = dots && view.rowText?.some(Boolean) ? 118 : 0;
  const cfg = {
    type: dots ? 'scatter' : line ? 'line' : 'bar',
    data: dots || numX ? { datasets: datasets(kind, view, th) }
      : { labels: horiz ? view.labels.map(wrapLabel) : view.labels, datasets: datasets(kind, view, th) },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false, indexAxis: horiz ? 'y' : 'x',
      layout: { padding: { right: rowTextW || (horiz && hasLabels ? 64 : 8), top: !horiz && hasLabels ? 18 : 4 } },
      interaction: dots ? { mode: 'nearest', intersect: true }
        : line ? { mode: 'nearest', intersect: false } : { mode: 'index', intersect: false, axis: horiz ? 'y' : 'x' },
      plugins: {
        perfRefLines: { view },
        legend: {
          display: !view.legendRows && !dots && (view.series.filter((s) => s.role !== 'ideal').length > 1 || !!view.legend),
          position: 'bottom',
          labels: { color: th.ink, usePointStyle: true, pointStyleWidth: 18, boxHeight: 9, padding: 12,
            generateLabels: (chart) => legendLabels(chart, kind, view, th) },
          onClick: view.legend ? () => {} : undefined,
        },
        tooltip: {
          filter: (it) => !it.dataset._aux && !it.dataset._quiet,
          callbacks: {
            title: (items) => {
              const it = items[0];
              if (!it) return '';
              if (dots) return labelText(view.labels[it.raw.y]);
              if (!numX) return labelText(view.labels[it.dataIndex]);
              return `${view.x.title || 'x'}: ${fmtValue(it.parsed.x, view.x.fmt)}`;
            },
            label: (it) => `${it.dataset.label}: ${fmtValue(horiz || dots ? it.parsed.x : it.parsed.y, valueFmt)}`,
            afterLabel: (it) => it.dataset._tips?.[it.dataIndex] || '',
          },
        },
      },
      scales,
    },
    plugins: [refLines, dotsDecor, whiskers, valueLabels],
  };
  return cfg;
}

/** Wysokość płótna: słupki poziome i wiersze „dots” rosną z liczbą wierszy (i serii), reszta — stała. */
function chartHeight(spec, view) {
  const kind = kindOf(spec, view);
  if (kind === 'dots') return Math.max(200, view.labels.length * 27 + 76);
  if (kind !== 'hbar') return 300;
  const n = view.labels.length, k = view.stacked ? 1 : view.series.length;
  const bar = view.barThickness ? view.barThickness + 2 : 10;
  return Math.max(220, Math.round(n * (12 + bar * k) + 90));
}

// ---------------------------------------------------------------- tabela (każdy wykres ma widok tabeli)

function tableHtml(spec, view) {
  const kind = kindOf(spec, view);
  const ser = view.series.filter((s) => s.role !== 'ideal' && !(s.marker === 'none' && !s.tips));
  const valueAx = kind === 'hbar' || kind === 'dots' ? view.x : view.y;
  const vf = view.valueFmt || valueAx?.fmt;
  const numX = numericX(kind, view);
  const cell = (s, i) => {
    const v = numX ? s.data[i]?.[1] : s.data[i];
    if (v == null) return `<td class="num">${esc(s.labels?.[i] || NONE)}</td>`;
    if (Array.isArray(v)) {
      const lo = Math.min(...v), hi = Math.max(...v);
      return `<td class="num">${esc(fmtValue(lo, vf))}${v.length > 1 ? ` … ${esc(fmtValue(hi, vf))}` : ''}</td>`;
    }
    const range = s.lo?.[i] != null && s.hi?.[i] != null ? ` <span class="sub">[${fmtValue(s.lo[i], vf)}–${fmtValue(s.hi[i], vf)}]</span>` : '';
    return `<td class="num">${esc(fmtValue(v, vf))}${range}</td>`;
  };
  let head, rows;
  if (numX) {
    const xs = [...new Set(ser.flatMap((s) => s.data.filter(Boolean).map((p) => p[0])))].sort((a, b) => a - b);
    head = `<th>${esc(view.x.title || 'x')}</th>`;
    rows = xs.map((x) => `<tr><td class="num">${esc(fmtValue(x, view.x.fmt))}</td>${ser.map((s) => {
      const i = s.data.findIndex((p) => p && p[0] === x);
      return i < 0 ? `<td class="num">${NONE}</td>` : cell(s, i);
    }).join('')}</tr>`);
  } else {
    head = '<th></th>';
    const headers = view.headers || [];
    rows = view.labels.map((l, i) => (headers.includes(i)
      ? `<tr><th colspan="${ser.length + 1}">${esc(labelText(l))}</th></tr>`
      : `<tr><td>${esc(labelText(l))}</td>${ser.map((s) => cell(s, i)).join('')}</tr>`));
  }
  return `<div class="table-scroll"><table class="table perf-data"><thead><tr>${head}${ser.map((s) => `<th class="num">${esc(s.name)}</th>`).join('')}</tr></thead>
    <tbody>${rows.join('')}</tbody></table></div>`;
}

/** Pliki źródłowe pogrupowane po folderach: „folder/ plik1, plik2; folder2/ …”. */
function sourcesHtml(paths) {
  const by = new Map();
  for (const p of paths) {
    const i = p.lastIndexOf('/');
    const dir = p.slice(0, i + 1), name = p.slice(i + 1);
    if (!by.has(dir)) by.set(dir, []);
    by.get(dir).push(name);
  }
  return [...by].map(([dir, names]) => `<code>${esc(dir)}</code> ${names.map(esc).join(', ')}`).join('; ');
}

/** Blok „Jak czytać” (punkty) z opcjonalną listą kroków (np. k1…k8). */
function howtoHtml(points, steps) {
  if (!points?.length && !steps?.length) return '';
  const st = steps?.length ? `<p class="perf-howto-sub">Kroki optymalizacji:</p><ul class="perf-steps">${steps.map((s) =>
    `<li><b>${esc(s.k)}</b> ${esc(s.text)}</li>`).join('')}</ul>` : '';
  return `<div class="perf-howto"><p class="perf-howto-title">${icon('info')}Jak czytać</p>
    <ul>${(points || []).map((p) => `<li>${esc(p)}</li>`).join('')}</ul>${st}</div>`;
}

const sourcesBlock = (paths) => (paths?.length
  ? `<details class="perf-src"><summary>Skąd dane</summary><p>${sourcesHtml(paths)}.</p></details>` : '');

// ---------------------------------------------------------------- zakładka

export class PerfView {
  constructor(root) {
    this.root = root;
    this.data = null;
    this.loading = null;
    this.pdfs = new Set();  // dokumenty PDF dostępne w tej kopii projektu (/api/doc/list)
    this.cards = new Map();  // id wykresu → { spec, state, chart, el, section, dirty }
    this.built = new Set();  // sekcje z kartami w DOM
    this.section = store.get(KEY_SECTION) || 'summary';
    this.compiler = store.get(KEY_COMPILER) === 'gcc' ? 'gcc' : 'msvc';
    onThemeChange(() => this.refresh());
  }

  /** Wejście w zakładkę: dane raz, potem bieżąca sekcja. */
  async show() {
    if (!this.data) {
      this.loading ||= this.load();
      await this.loading;
    }
    if (this.data) this.showSection(this.section);
  }

  async load() {
    this.root.innerHTML = '<div class="card"><p class="empty">wczytywanie wyników pomiarów…</p></div>';
    try {
      this.data = await getJSON(DATA_URL);
    } catch (err) {
      this.root.innerHTML = `<div class="card">${notice('error', `Nie można wczytać danych zakładki
        (<code>gui/static/data/wydajnosc.json</code>): ${esc(err.message)}. Dane tworzy
        <code>python tools/wydajnosc_gui.py</code>.`)}</div>`;
      this.loading = null;
      return;
    }
    try {
      this.pdfs = new Set((await getJSON('/api/doc/list')).pdf || []);
    } catch {
      this.pdfs = new Set();
    }
    this.buildFrame();
  }

  // ------------------------------------------------------------ szkielet: nagłówek, pojęcia, nawigacja, sekcje

  buildFrame() {
    const d = this.data, h = d.header;
    const sections = [{ id: 'summary', title: 'Podsumowanie' }, ...d.sections.map((s) => ({ id: s.id, title: s.title }))];
    if (!sections.some((s) => s.id === this.section)) this.section = 'summary';
    this.root.innerHTML = `
      <div class="card perf-head">
        <p class="perf-principle"><span class="perf-ok">${icon(h.allOk ? 'check' : 'alert')}</span><b>${esc(h.principle)}</b></p>
        <button type="button" class="btn btn-small btn-ghost perf-gloss-btn" aria-expanded="false" aria-controls="perf-gloss">${icon('info')}Pojęcia</button>
        <div class="perf-badges">${h.badges.map((b) => `<span class="perf-badge" title="${esc(b.title)}">${esc(b.text)}</span>`).join('')}</div>
        <div class="perf-gloss" id="perf-gloss" hidden>
          <dl>${d.glossary.map((g) => `<div><dt>${esc(g.term)}</dt><dd>${esc(g.def)}</dd></div>`).join('')}</dl>
          ${sourcesBlock(h.sources)}
        </div>
      </div>
      <div class="perf-nav">
        <div class="perf-tabs" role="tablist" aria-label="Sekcje wyników">${sections.map((s, i) => `<button type="button" role="tab"
          class="perf-tab" data-perf-section="${esc(s.id)}">${i ? `<span class="perf-no">${i}</span>` : ''}${esc(s.title)}</button>`).join('')}</div>
        <span class="field-inline perf-compiler" title="Kompilator i biblioteka MPI: dla wykresów z danymi obu">Kompilator
          <span class="seg">${Object.entries(d.compilers).map(([k, name]) => `<label title="${esc(name)}"><input type="radio"
            name="perf-compiler" value="${esc(k)}"${k === this.compiler ? ' checked' : ''}><span>${esc(name.split(' /')[0])}</span></label>`).join('')}</span>
        </span>
      </div>
      ${sections.map((s) => `<div class="perf-section" data-section="${esc(s.id)}" hidden></div>`).join('')}`;
    $$('.perf-tab', this.root).forEach((b) => b.addEventListener('click', () => this.showSection(b.dataset.perfSection)));
    $$('input[name=perf-compiler]', this.root).forEach((r) => r.addEventListener('change', () => {
      this.compiler = r.value;
      store.set(KEY_COMPILER, r.value);
      this.refresh();
    }));
    const gb = $('.perf-gloss-btn', this.root), gp = $('#perf-gloss', this.root);
    gb.addEventListener('click', () => {
      gp.hidden = !gp.hidden;
      gb.setAttribute('aria-expanded', gp.hidden ? 'false' : 'true');
    });
  }

  showSection(id) {
    if (!$(`.perf-section[data-section="${id}"]`, this.root)) id = 'summary';
    this.section = id;
    store.set(KEY_SECTION, id);
    $$('.perf-tab', this.root).forEach((b) => {
      const on = b.dataset.perfSection === id;
      b.classList.toggle('active', on);
      b.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    $$('.perf-section', this.root).forEach((s) => { s.hidden = s.dataset.section !== id; });
    if (!this.built.has(id)) this.buildSection(id);
    for (const c of this.cards.values()) if (c.section === id && (!c.chart || c.dirty)) this.render(c);
  }

  /** Motyw albo kompilator: wykresy bieżącej sekcji od nowa, pozostałe — przy następnym wejściu. */
  refresh() {
    if (!this.data) return;
    if (this.built.has('summary')) this.renderSummaryText();
    for (const c of this.cards.values()) {
      if (c.section === this.section) this.render(c);
      else c.dirty = true;
    }
  }

  /** „Pobierz PDF: Tytuł (rozdz. X.Y)” + „otwórz w przeglądarce”; bez PDF w tej kopii — sam opis dokumentu. */
  pdfLink(doc) {
    if (!doc?.pdf) return '';
    const where = doc.section ? ` (rozdz. ${esc(doc.section)})` : '';
    const url = `/api/doc/pdf?name=${encodeURIComponent(doc.pdf)}`;
    if (this.pdfs.has(doc.pdf)) {
      return `<span class="perf-pdf"><a href="${url}" download data-pdf="${esc(doc.pdf)}">${icon('download')}Pobierz PDF: ${esc(doc.title)}${where}</a>
        <a class="perf-pdf-open" href="${url}&amp;inline=1" target="_blank" rel="noopener">otwórz w przeglądarce</a></span>`;
    }
    return `<span class="perf-pdf missing">Dokument „${esc(doc.title)}”${where} jest w pełnym repozytorium projektu.</span>`;
  }

  buildSection(id) {
    const box = $(`.perf-section[data-section="${id}"]`, this.root);
    this.built.add(id);
    if (id === 'summary') {
      this.buildSummary(box);
      return;
    }
    const sec = this.data.sections.find((s) => s.id === id);
    box.innerHTML = `<div class="perf-intro"><p>${esc(sec.intro)}</p><p class="perf-intro-pdf">${this.pdfLink(sec.doc)}</p></div>
      <div class="perf-grid">${sec.charts.map((c) => `<article class="card perf-card${c.wide ? ' wide' : ''}" id="perf-${esc(c.id)}"></article>`).join('')}</div>`;
    for (const spec of sec.charts) this.addCard(spec, $(`#perf-${spec.id}`, box), id);
  }

  buildSummary(box) {
    const s = this.data.summary;
    box.innerHTML = `<div class="perf-tiles" id="perf-tiles"></div>
      <p class="hint perf-tiles-howto"><b>Jak czytać:</b> ${esc(s.tilesHowto)}</p>
      <div class="perf-grid">
        <article class="card perf-card" id="perf-${esc(s.chart.id)}"></article>
        <article class="card perf-card"><div class="card-head"><h3>Najlepszy wariant dla każdego przypadku</h3>
          <span class="perf-chip" id="perf-best-chip"></span></div>
          <div class="table-scroll"><table class="table perf-best" id="perf-best"></table></div>
          ${howtoHtml(s.bestHowto)}
          <p class="perf-cond"><b>Warunki:</b> ${esc(s.bestConditions)}.</p>
          ${sourcesBlock(s.bestSources)}
          <p class="perf-pdfline">${this.pdfLink(s.doc)}</p></article>
      </div>`;
    this.addCard(s.chart, $(`#perf-${s.chart.id}`, box), 'summary');
    this.renderSummaryText();
  }

  renderSummaryText() {
    const s = this.data.summary, comp = s.tiles[this.compiler] ? this.compiler : 'msvc';
    const tiles = $('#perf-tiles', this.root), best = $('#perf-best', this.root);
    if (!tiles || !best) return;
    tiles.innerHTML = s.tiles[comp].map((t) => `<div class="perf-tile">
      <span class="perf-tile-label">${esc(t.label)}</span>
      <span class="perf-tile-value" title="tyle razy szybciej niż program sprzed optymalizacji (faza obliczeń)">${esc(t.value)}<small class="perf-tile-unit">szybciej</small></span>
      <span class="perf-tile-parts">${esc(t.parts)}</span>
      <span class="perf-tile-detail">${esc(t.detail)}</span></div>`).join('');
    $('#perf-best-chip', this.root).textContent = this.data.compilers[comp];
    best.innerHTML = `<thead><tr><th>Przypadek</th><th>Najlepszy wariant</th><th class="num">S fazy</th>
      <th class="num">E</th><th class="num">S całego przebiegu</th></tr></thead><tbody>${s.best[comp].map((r) => `<tr><td>${esc(r.case)}</td>
      <td>${esc(r.variant)}<br><span class="sub">${esc(r.version)}</span></td>
      <td class="num"><b>${esc(fmtValue(r.S, 'num'))}</b></td><td class="num">${esc(fmtValue(r.E, 'num'))}</td>
      <td class="num">${esc(fmtValue(r.Stotal, 'num'))}</td></tr>`).join('')}</tbody>`;
  }

  // ------------------------------------------------------------ karta wykresu

  addCard(spec, el, section) {
    const state = {};
    for (const s of spec.selectors) state[s.id] = s.options[0].id;
    const c = { spec, state, el, section, chart: null, dirty: false, table: false };
    this.cards.set(spec.id, c);
    const tools = spec.selectors.map((s) => {
      const seg = s.options.length <= 4 && s.options.reduce((n, o) => n + o.label.length, 0) <= 44;
      const name = `perf-${spec.id}-${s.id}`;
      const ctl = seg
        ? `<span class="seg">${s.options.map((o, i) => `<label><input type="radio" name="${esc(name)}" value="${esc(o.id)}"
            data-sel="${esc(s.id)}"${i ? '' : ' checked'}><span>${esc(o.label)}</span></label>`).join('')}</span>`
        : `<select data-sel="${esc(s.id)}" aria-label="${esc(s.label)}">${s.options.map((o) => `<option value="${esc(o.id)}">${esc(o.label)}</option>`).join('')}</select>`;
      return `<span class="field-inline">${esc(s.label)} ${ctl}</span>`;
    }).join('');
    el.innerHTML = `<div class="card-head"><h3>${esc(spec.title)}</h3><span class="perf-chip" data-role="chip"></span></div>
      <div class="toolbar perf-tools">${tools}<span class="toolbar-end">
        <button type="button" class="btn btn-small btn-ghost" data-act="table" aria-pressed="false">${icon('table')}Tabela</button>
        <button type="button" class="btn btn-small" data-act="png">${icon('image')}Eksport PNG</button></span></div>
      <div class="chart-box perf-box"><canvas role="img" aria-label="${esc(spec.title)}"></canvas></div>
      <div class="perf-legend" data-role="legend" hidden></div>
      <p class="hint perf-note" data-role="note"></p>
      <div class="perf-table" hidden></div>
      <p class="perf-concl"><b>${esc(spec.lead)}</b> ${esc(spec.conclusion)}</p>
      ${howtoHtml(spec.howto, spec.steps)}
      <p class="perf-cond"><b>Warunki:</b> ${esc(spec.conditions)}.</p>
      ${sourcesBlock(spec.sources)}
      <p class="perf-pdfline">${this.pdfLink(spec.doc)}</p>`;
    $$('[data-sel]', el).forEach((inp) => inp.addEventListener('change', () => {
      c.state[inp.dataset.sel] = inp.value;
      this.render(c);
    }));
    $('[data-act=table]', el).addEventListener('click', (ev) => {
      c.table = !c.table;
      ev.currentTarget.setAttribute('aria-pressed', c.table ? 'true' : 'false');
      this.renderTable(c);
    });
    $('[data-act=png]', el).addEventListener('click', () => this.exportPng(c));
  }

  /** Widok dla bieżącego kompilatora i przełączników; brak — najbliższy (najwięcej zgodnych przełączników). */
  resolve(c) {
    const { spec, state } = c;
    const comps = spec.compilers;
    const comp = comps.length ? (comps.includes(this.compiler) ? this.compiler : comps[0]) : null;
    const want = spec.selectors.map((s) => state[s.id]);
    const keyOf = (vals) => [comp, ...vals].filter((x) => x != null).join('|');
    let key = keyOf(want);
    const subst = [];
    if (!spec.views[key]) {
      const prefix = comp ? `${comp}|` : '';
      let best = null, bestScore = -1;
      for (const k of Object.keys(spec.views)) {
        if (comp && k !== comp && !k.startsWith(prefix)) continue;
        const vals = (comp ? k.slice(prefix.length) : k).split('|');
        const score = vals.reduce((sum, v, i) => sum + (v === want[i] ? 2 ** (vals.length - i) : 0), 0);
        if (score > bestScore) { best = vals; bestScore = score; }
      }
      if (best) {
        spec.selectors.forEach((s, i) => {
          if (best[i] !== want[i]) {
            subst.push(`${s.label}: ${s.options.find((o) => o.id === want[i])?.label} → ${s.options.find((o) => o.id === best[i])?.label}`);
            state[s.id] = best[i];
          }
        });
        key = keyOf(best);
      }
    }
    return { comp, key, view: spec.views[key], subst };
  }

  /** Opcje przełączników bez danych dla bieżącego kompilatora i pozostałych wyborów — wyłączone. */
  syncControls(c, comp) {
    const { spec, state, el } = c;
    spec.selectors.forEach((s, si) => {
      for (const o of s.options) {
        const vals = spec.selectors.map((x, i) => (i === si ? o.id : state[x.id]));
        const k = [comp, ...vals].filter((x) => x != null).join('|');
        const ok = !!spec.views[k];
        const inp = $(`input[data-sel="${s.id}"][value="${CSS.escape(o.id)}"]`, el);
        if (inp) { inp.disabled = !ok; inp.checked = state[s.id] === o.id; }
        const opt = $(`select[data-sel="${s.id}"] option[value="${CSS.escape(o.id)}"]`, el);
        if (opt) opt.disabled = !ok;
      }
      const select = $(`select[data-sel="${s.id}"]`, el);
      if (select) select.value = state[s.id];
    });
  }

  /** Legenda HTML w podpisanych rzędach (np. „kolor: …”, „kształt: …”) — gdy wykres ma dwa kodowania naraz. */
  renderLegend(c, view) {
    const box = $('[data-role=legend]', c.el);
    if (!view?.legendRows) {
      box.hidden = true;
      box.innerHTML = '';
      return;
    }
    const th = themeColors();
    box.innerHTML = view.legendRows.map((r) => `<div class="perf-legend-row"><span class="perf-legend-key">${esc(r.label)}:</span>
      ${r.items.map((it) => `<span class="perf-legend-item">${markerSvg(it.marker, it.role ? roleColor(it.role, th) : th.ink2,
        !!it.outline, th.panel)}${esc(it.label)}</span>`).join('')}</div>`).join('');
    box.hidden = false;
  }

  render(c) {
    const { comp, view, subst } = this.resolve(c);
    c.dirty = false;
    c.chart?.destroy();
    c.chart = null;
    const chip = $('[data-role=chip]', c.el);
    const notes = [];
    if (comp) {
      chip.textContent = this.data.compilers[comp];
      chip.hidden = false;
      if (comp !== this.compiler) notes.push(`Brak danych ${this.data.compilers[this.compiler]}, pokazano ${this.data.compilers[comp]}.`);
      if (comp === 'gcc') notes.push(this.data.conditions.gcc);
    } else {
      chip.hidden = true;
    }
    if (subst.length) notes.push(`Brak pomiaru dla tego wyboru, pokazano najbliższy (${subst.join('; ')}).`);
    if (view?.note) notes.push(view.note);
    if (view?.foot) notes.push(view.foot.join(' · '));
    $('[data-role=note]', c.el).textContent = notes.map((n) => (/[.!?)]$/.test(n) ? n : `${n}.`)).join(' ');
    this.syncControls(c, comp);
    this.renderLegend(c, view);
    const box = $('.perf-box', c.el);
    if (!view || !window.Chart) {
      box.innerHTML = '<p class="empty">Brak danych dla tego wykresu.</p>';
      return;
    }
    box.style.height = `${chartHeight(c.spec, view)}px`;
    if (!$('canvas', box)) box.innerHTML = `<canvas role="img" aria-label="${esc(c.spec.title)}"></canvas>`;
    c.view = view;
    c.chart = new window.Chart($('canvas', box), chartConfig(c.spec, view));
    this.renderTable(c);
  }

  renderTable(c) {
    const t = $('.perf-table', c.el);
    t.hidden = !c.table;
    if (c.table && c.view) t.innerHTML = tableHtml(c.spec, c.view);
  }

  /** PNG: tytuł, wykres i przypis (warunki, źródło) w kolorach bieżącego motywu. */
  exportPng(c) {
    if (!c.chart) return;
    const src = c.chart.canvas;
    const k = window.devicePixelRatio || 1, th = themeColors();
    const pad = 16 * k, w = src.width + 2 * pad;
    const ctx0 = document.createElement('canvas').getContext('2d');
    ctx0.font = `${12 * k}px ${th.font}`;
    const wrap = (text) => {
      const words = text.split(' '), lines = [];
      let cur = '';
      for (const wd of words) {
        const t = cur ? `${cur} ${wd}` : wd;
        if (ctx0.measureText(t).width > w - 2 * pad && cur) { lines.push(cur); cur = wd; } else cur = t;
      }
      if (cur) lines.push(cur);
      return lines;
    };
    const comp = this.resolve(c).comp;
    const foot = [...wrap(`Warunki: ${c.spec.conditions}.`), ...wrap(`Dane: ${c.spec.sources.join(', ')}.`)];
    const head = 40 * k, footH = foot.length * 16 * k + pad;
    const out = document.createElement('canvas');
    out.width = w;
    out.height = head + src.height + footH;
    const ctx = out.getContext('2d');
    ctx.fillStyle = th.panel;
    ctx.fillRect(0, 0, out.width, out.height);
    ctx.fillStyle = th.ink;
    ctx.font = `600 ${16 * k}px ${th.font}`;
    ctx.fillText(`${c.spec.title}${comp ? ` (${this.data.compilers[comp]})` : ''}`, pad, 26 * k);
    ctx.drawImage(src, pad, head);
    ctx.fillStyle = th.ink2;
    ctx.font = `${12 * k}px ${th.font}`;
    foot.forEach((ln, i) => ctx.fillText(ln, pad, head + src.height + (i + 1) * 16 * k));
    const stem = [c.spec.id, comp, ...c.spec.selectors.map((s) => c.state[s.id])].filter(Boolean).join('_')
      .replace(/[^A-Za-z0-9_-]+/g, '_');
    out.toBlob((blob) => downloadBlob(blob, `wydajnosc_${stem}.png`), 'image/png');
  }
}
