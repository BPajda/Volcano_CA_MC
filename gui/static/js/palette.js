// Paleta naukowa GUI — JEDYNE miejsce z kolorami danych: przekroje 2D, ściany / powierzchnia / woksele 3D, legendy,
// galeria Porównania, eksporty PNG i WebM, odtwarzanie erupcji (motyw „Bazalt i lawa”, uzasadnienie i pomiary
// kontrastu / daltonizmu: docs/wyglad-interfejsu.md):
//  - typ komórki: powietrze = tło podglądu (wariant ciemny / jasny motywu), skała = ciepła szarość-brąz (ciemniejsza
//    w motywie ciemnym), lawa = pomarańcz-żar, bazalt = grafit (ten sam w obu motywach — odróżnia się od tła i skały);
//  - krater / ziarno (flowId): 10 kolorów kategorycznych bez szarości i brązów (nie mylą się ze skałą), w kolejności
//    od najbardziej odległych (także przy proto- i deuteranopii); krater 1 = pomarańcz lawy; więcej kraterów /
//    ziaren (rozrost classic) — kolor z hasha ID, ten sam na każdym przekroju, ścianie 3D i w każdej sesji;
//  - kryształ MC: hash Knutha z ID, dokładnie jak crystal_rgb() w tools/plot_slice.py (jedyna część wspólna
//    z obrazkami ze skryptów — plot_slice.py ma starą paletę: szara skała, niebieski bazalt);
//  - temperatura: skala „żar” (ciemna czerwień → pomarańcz → jasnożółty) — ta sama co odtwarzanie erupcji;
//  - czas stygnięcia: chłodna skala granat → turkus (jasny turkus = długo płynna lawa → duże kryształy MC).
// Kolory powietrza i skały zależą od motywu: TYPE_RGB jest zmieniane w miejscu po zmianie motywu (theme.js),
// więc moduły, które je zaimportowały, widzą bieżące wartości.

import { currentTheme, onThemeChange, themeColors } from './theme.js';

export const AIR = 0, ROCK = 1, LAVA = 2, BASALT = 3;
export const TYPE_NAMES = { 0: 'powietrze', 1: 'skała', 2: 'lawa', 3: 'bazalt' };

const hex = (h) => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
export const toHex = (rgb) => '#' + rgb.map((v) => Math.round(v).toString(16).padStart(2, '0')).join('');

/** Powietrze i skała w obu motywach (reszta palety jest wspólna). */
const THEME_CELLS = {
  dark: { air: '#1a1613', rock: '#8a7f72' },
  light: { air: '#f7f3ed', rock: '#c8bdae' },
};
export const LAVA_HEX = '#ff6a1f';
export const BASALT_HEX = '#464a55';
export const TYPE_RGB = { 0: hex(THEME_CELLS.dark.air), 1: hex(THEME_CELLS.dark.rock), 2: hex(LAVA_HEX), 3: hex(BASALT_HEX) };

// Kratery / ziarna: kolejność wg największej minimalnej odległości OKLab (normalne widzenie i symulacja protanopii /
// deuteranopii, Machado 2009) — pierwszych 5 kolorów rozróżnialnych parami (ΔE ≥ 13), szczegóły w docs/wyglad-interfejsu.md.
export const FLOW_SLOTS = ['#ee7733', '#2f5fd0', '#66ccee', '#f0e442', '#9085e9', '#ccbb44', '#e8402f', '#3d7fc4', '#c39bf0',
  '#5b6ee1'].map(hex);
// Żar: temperatura i płynna lawa w odtwarzaniu (zastyganie → erupcja).
export const GLOW = ['#6e1410', '#a81d14', '#d6361c', '#f0641e', '#ff9a1f', '#ffc93c', '#fff1b0'].map(hex);
// Czas stygnięcia: granat (krótko płynna) → turkus (długo płynna).
const COOL = ['#1b2a5c', '#1f4a8a', '#1f73a6', '#239db2', '#4cc6bc', '#9ce9d6'].map(hex);
// Panel „Kratery na mapie”: mapa hipsometryczna (niziny zielone → skały brązowe → szczyty jasne), morze, poziomice
// i znacznik krateru (lawa z ciemnym i jasnym obrysem, numer z obwódką — czytelne na każdym kolorze mapy).
export const HYPSO = ['#4f8a52', '#8fb36b', '#d9cf8e', '#c49a62', '#9c7452', '#cfc6bd', '#f6f4f0'].map(hex);
export const SEA_RGB = hex('#b0cde2');
export const CONTOUR = 'rgba(40, 30, 20, 0.45)';
export const VENT_MARKER = { fill: LAVA_HEX, halo: 'rgba(255, 106, 31, 0.28)', ring: '#1b0e06', outer: 'rgba(255, 255, 255, 0.85)',
  text: '#fff4e8', textHalo: 'rgba(20, 14, 10, 0.85)' };

export const FIELD_LABELS = {
  type: 'Typ komórki',
  flowId: 'Krater / ziarno (flowId)',
  temp: 'Temperatura',
  crystal: 'Kryształ (MC)',
  cooling: 'Czas stygnięcia',
};

/** Powietrze i skała dla motywu (wołane przy starcie i po każdej zmianie motywu). */
export function setPaletteTheme(name) {
  const t = THEME_CELLS[name] || THEME_CELLS.dark;
  TYPE_RGB[AIR] = hex(t.air);
  TYPE_RGB[ROCK] = hex(t.rock);
}
setPaletteTheme(currentTheme());
onThemeChange(setPaletteTheme);

function hsvToRgb(h, s, v) {
  const i = Math.floor(h * 6), f = h * 6 - i;
  const p = v * (1 - s), q = v * (1 - f * s), t = v * (1 - (1 - f) * s);
  const [r, g, b] = [[v, t, p], [q, v, p], [p, v, t], [p, q, v], [t, p, v], [v, p, q]][i % 6];
  return [r * 255, g * 255, b * 255];
}

const hashCache = new Map();
/** Stały kolor z ID (hash mnożeniem Knutha) — identyczny wzór jak crystal_rgb() w plot_slice.py. */
export function hashColor(id) {
  let c = hashCache.get(id);
  if (c) return c;
  const h = Math.imul(id, 0x9E3779B1) >>> 0;  // (id · 2654435761) mod 2^32
  const hue = (h & 0xFFFF) / 65536;
  const sat = 0.45 + 0.40 * ((h >>> 16) & 0xFF) / 255;
  const val = 0.62 + 0.30 * ((h >>> 24) & 0xFF) / 255;
  c = hsvToRgb(hue, sat, val);
  if (hashCache.size > 100000) hashCache.clear();
  hashCache.set(id, c);
  return c;
}

/** Kolor krateru/ziarna: sloty palety dla ≤ 10, inaczej hash z ID. */
export function flowColor(id, count) {
  if (count <= FLOW_SLOTS.length && id >= 1 && id <= FLOW_SLOTS.length) return FLOW_SLOTS[id - 1];
  return hashColor(id);
}

export function ramp(stops, t) {
  t = Math.min(1, Math.max(0, t));
  const x = t * (stops.length - 1), i = Math.min(stops.length - 2, Math.floor(x)), f = x - i;
  const a = stops[i], b = stops[i + 1];
  return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f];
}
const norm = (v, lo, hi) => (hi > lo ? (v - lo) / (hi - lo) : 1);
export const tempColor = (v, lo, hi) => ramp(GLOW, norm(v, lo, hi));
export const coolingColor = (v, lo, hi) => ramp(COOL, norm(v, lo, hi));

/** Skała w rzucie z góry cieniowana wysokością (t = 0 najniżej … 1 najwyżej) — kolor skały motywu, ciemniej / jaśniej. */
export function rockShade(t) {
  const r = TYPE_RGB[ROCK], k = 0.62 + 0.5 * Math.min(1, Math.max(0, t));
  return [Math.min(255, r[0] * k), Math.min(255, r[1] * k), Math.min(255, r[2] * k)];
}

/**
 * Kolory RGBA dla płaszczyzny w×h (wiersz 0 = dół płaszczyzny).
 * typeArr — typy komórek, valArr — wartości pola (dla field = 'type' może być null).
 * ctx: { ranges, flowCount, heights? (wysokość kolumny — cieniowanie skały w rzucie z góry) }.
 * flipY = true — wiersz 0 trafia na dół obrazu (canvas rysuje od góry); false — kolejność wierszy bez zmian
 * (tekstury three.js: wiersz 0 = v = 0 = dół).
 */
export function colorize(w, h, typeArr, valArr, field, ctx, flipY = true) {
  const out = new Uint8ClampedArray(w * h * 4);
  const r = ctx.ranges || {};
  const [tlo, thi] = r.temp || [0, 1];
  const [clo, chi] = r.cooling || [0, 1];
  const flowCount = ctx.flowCount ?? (r.flowId ? r.flowId[1] : 0);
  let hlo = 0, hhi = 1;
  const heights = ctx.heights;
  if (heights) {
    hlo = Infinity; hhi = -Infinity;
    for (let i = 0; i < heights.length; i++) if (heights[i] > 0 && typeArr[i] === ROCK) { hlo = Math.min(hlo, heights[i]); hhi = Math.max(hhi, heights[i]); }
    if (!isFinite(hlo)) { hlo = 0; hhi = 1; }
  }
  for (let row = 0; row < h; row++) {
    const dstRow = flipY ? h - 1 - row : row;
    for (let col = 0; col < w; col++) {
      const i = row * w + col;
      const t = typeArr[i];
      let c;
      if (field === 'type' || t === AIR || t === ROCK) {
        c = TYPE_RGB[t] || TYPE_RGB[BASALT];
        if (t === ROCK && heights) c = rockShade(norm(heights[i], hlo, hhi));
      } else {
        const v = valArr[i];
        if (field === 'flowId') c = v > 0 ? flowColor(v, flowCount) : TYPE_RGB[BASALT];
        else if (field === 'temp') c = tempColor(v, tlo, thi);
        else if (field === 'cooling') c = coolingColor(v, clo, chi);
        else if (field === 'crystal') c = v > 0 ? hashColor(v) : TYPE_RGB[t];
        else c = TYPE_RGB[t];
      }
      const o = (dstRow * w + col) * 4;
      out[o] = c[0]; out[o + 1] = c[1]; out[o + 2] = c[2]; out[o + 3] = 255;
    }
  }
  return out;
}

/** Czy pole ma „ziarna”, których granice można rysować. */
export const hasGrains = (field) => field === 'flowId' || field === 'crystal';

/**
 * Opis legendy (dane — rysowany jako HTML w panelu i na canvasie przy eksporcie PNG):
 * { title, items: [{rgb, label}], gradient?: {stops, min, max, unit}, notes: [], swatches?: [rgb] }
 */
export function legendFor(field, meta, presentTypes) {
  const r = meta.ranges || {};
  const classic = meta.mode === 'classic';
  const typesShown = [AIR, ROCK, LAVA, BASALT].filter((t) => !presentTypes || presentTypes.has(t));
  const rockAir = typesShown.filter((t) => t === AIR || t === ROCK)
    .map((t) => ({ rgb: TYPE_RGB[t], label: TYPE_NAMES[t] }));
  const L = { title: FIELD_LABELS[field], items: [], notes: [] };
  if (field === 'type') {
    L.items = typesShown.map((t) => ({
      rgb: TYPE_RGB[t],
      label: classic && t === LAVA ? 'ziarno (rozrost CA)' : meta.mode === 'mc_full' && t === BASALT ? 'domena MC' : TYPE_NAMES[t],
    }));
  } else if (field === 'flowId') {
    const n = r.flowId ? r.flowId[1] : 0;
    if (n <= FLOW_SLOTS.length) {
      L.items = Array.from({ length: n }, (_, k) => ({ rgb: flowColor(k + 1, n), label: `${classic ? 'ziarno' : 'krater'} ${k + 1}` }));
    } else {
      L.notes.push(`${n} ${classic ? 'ziaren' : 'kraterów'}: kolor stały, wyliczany z ID (ten sam na każdym przekroju)`);
      L.swatches = Array.from({ length: 24 }, (_, k) => hashColor(k + 1));
    }
    L.items.push(...rockAir);
  } else if (field === 'crystal') {
    const q = r.crystal ? r.crystal[1] : 0;
    L.notes.push(`orientacje 1…${q}: kolor stały z ID kryształu (jak plot_slice.py --color crystal)`);
    L.swatches = Array.from({ length: Math.min(q, 24) }, (_, k) => hashColor(k + 1));
    L.items.push(...rockAir);
  } else if (field === 'temp') {
    const [lo, hi] = r.temp || [0, 0];
    L.gradient = { stops: [0, 0.2, 0.4, 0.6, 0.8, 1].map((t) => tempColor(lo + (hi - lo) * t, lo, hi)), min: lo, max: hi, unit: '°C' };
    L.notes.push('lawa i bazalt: ciemnoczerwony = chłodniej, jasnożółty = goręcej (skala „żar”)');
    L.items.push(...rockAir);
  } else if (field === 'cooling') {
    const [lo, hi] = r.cooling || [0, 0];
    L.gradient = { stops: [0, 0.2, 0.4, 0.6, 0.8, 1].map((t) => coolingColor(lo + (hi - lo) * t, lo, hi)), min: lo, max: hi, unit: 'kroków CA' };
    L.notes.push('czas w stanie płynnym (solidStep − arrivalStep): granat = krótko, jasny turkus = długo płynna → duże kryształy MC');
    L.items.push(...rockAir);
  }
  return L;
}

const fmt = (v) => (Math.abs(v) >= 100 || Number.isInteger(v) ? Math.round(v).toLocaleString('pl-PL') : v.toFixed(1));

/** Legenda jako HTML (panel boczny). */
export function legendHTML(L) {
  let html = `<div class="legend-title">${L.title}</div>`;
  if (L.gradient) {
    const g = L.gradient;
    html += `<div class="legend-gradient" style="background:linear-gradient(to right, ${g.stops.map(toHex).join(', ')})"></div>`
      + `<div class="legend-scale"><span>${fmt(g.min)}</span><span>${fmt(g.max)} ${g.unit}</span></div>`;
  }
  if (L.swatches) html += `<div class="legend-swatches">${L.swatches.map((c) => `<span style="background:${toHex(c)}"></span>`).join('')}</div>`;
  for (const n of L.notes) html += `<p class="legend-note">${n}</p>`;
  for (const it of L.items) html += `<div class="legend-item"><span class="sw" style="background:${toHex(it.rgb)}"></span>${it.label}</div>`;
  return html;
}

const shownLegend = new WeakMap();
/** Wstawia legendę do panelu tylko, gdy się zmieniła — w odtwarzaniu legenda jest liczona co klatkę, a ponowne
 *  budowanie DOM i przemalowanie panelu w każdej klatce zmniejszało płynność odtwarzania 3D (pomiar: docs/wyglad-interfejsu.md). */
export function showLegend(el, L) {
  const html = legendHTML(L);
  if (shownLegend.get(el) === html && el.innerHTML) return;
  shownLegend.set(el, html);
  el.innerHTML = html;
}

/** Legenda narysowana na canvasie (eksport PNG) w prostokącie od (x, y), szerokość w. Zwraca wysokość. */
export function drawLegend(ctx, L, x, y, w) {
  const th = themeColors();
  let cy = y;
  ctx.font = `600 13px ${th.font}`; ctx.fillStyle = th.ink; ctx.textBaseline = 'top';
  ctx.fillText(L.title, x, cy); cy += 22;
  ctx.font = `12px ${th.font}`;
  if (L.gradient) {
    const g = L.gradient, grad = ctx.createLinearGradient(x, 0, x + w, 0);
    g.stops.forEach((c, k) => grad.addColorStop(k / (g.stops.length - 1), toHex(c)));
    ctx.fillStyle = grad; ctx.fillRect(x, cy, w, 12); cy += 16;
    ctx.fillStyle = th.ink2; ctx.fillText(fmt(g.min), x, cy);
    const right = `${fmt(g.max)} ${g.unit}`; ctx.fillText(right, x + w - ctx.measureText(right).width, cy); cy += 20;
  }
  if (L.swatches) {
    L.swatches.forEach((c, k) => { ctx.fillStyle = toHex(c); ctx.fillRect(x + (k % 12) * 15, cy + Math.floor(k / 12) * 15, 12, 12); });
    cy += Math.ceil(L.swatches.length / 12) * 15 + 6;
  }
  ctx.fillStyle = th.ink2;
  for (const n of L.notes) { cy = wrapText(ctx, n, x, cy, w, 16) + 4; }
  for (const it of L.items) {
    ctx.fillStyle = toHex(it.rgb); ctx.fillRect(x, cy, 14, 14);
    ctx.strokeStyle = th.viewFrame; ctx.strokeRect(x + 0.5, cy + 0.5, 13, 13);
    ctx.fillStyle = th.ink; ctx.fillText(it.label, x + 22, cy + 1); cy += 20;
  }
  return cy - y;
}

function wrapText(ctx, text, x, y, w, lh) {
  let line = '';
  for (const word of text.split(' ')) {
    const test = line ? `${line} ${word}` : word;
    if (ctx.measureText(test).width > w && line) { ctx.fillText(line, x, y); y += lh; line = word; } else line = test;
  }
  if (line) { ctx.fillText(line, x, y); y += lh; }
  return y;
}
