// Motyw GUI (etap 7): ciemny „bazalt” (domyślny) i jasny „popiół” — jedno źródło kolorów dla canvasu 2D, three.js
// i Chart.js. Kolory interfejsu są zmiennymi CSS (css/style.css: :root + [data-theme="light"]); ten moduł je czyta
// (themeColors), więc JS nie wpisuje kolorów interfejsu na sztywno. Kolory komórek (powietrze, skała, lawa…) są
// w palette.js — palette.js słucha zmiany motywu (powietrze i skała mają wariant jasny i ciemny).
//  - wybór: zapamiętany w localStorage („volcano.theme”, w try/catch — tryb prywatny), inaczej prefers-color-scheme
//    (i jego zmiana w systemie, dopóki użytkownik nie wybrał sam); atrybut ustawia już skrypt w <head> (bez mignięcia),
//  - przełącznik w nagłówku (#theme-toggle), zdarzenie zmiany: onThemeChange(fn),
//  - wysokość nagłówka i paska wyniku → zmienne CSS --header-h, --resultbar-h (podgląd 2D/3D na całą wysokość okna).

import { rangeFill, store } from './util.js';

const KEY = 'volcano.theme';
const listeners = [];
let cache = null;

/** Bieżący motyw: 'dark' albo 'light' (bez przeglądarki — np. test replay.js w node — ciemny). */
export const currentTheme = () => (typeof document !== 'undefined'
  && document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark');

/** Funkcja wołana po każdej zmianie motywu (argument: nazwa motywu); kolejność = kolejność rejestracji. */
export function onThemeChange(fn) { listeners.push(fn); }

/** Ustawia motyw; remember = false — zmiana z ustawień systemu (bez zapisu wyboru). */
export function setTheme(name, remember = true) {
  const t = name === 'light' ? 'light' : 'dark';
  if (remember) store.set(KEY, t);
  if (t === currentTheme() && cache) return;
  document.documentElement.setAttribute('data-theme', t);
  cache = null;
  syncToggle();
  applyChartTheme();
  for (const fn of listeners) {
    try { fn(t); } catch (err) { console.error(err); }
  }
}

const css = (s, name) => s.getPropertyValue(name).trim();

/** Kolory motywu odczytane z CSS (pamięć podręczna do zmiany motywu). */
export function themeColors() {
  if (cache) return cache;
  const s = getComputedStyle(document.documentElement);
  cache = {
    name: currentTheme(),
    bg: css(s, '--bg'), panel: css(s, '--panel'), raised: css(s, '--raised'), line: css(s, '--line-2'),
    ink: css(s, '--ink'), ink2: css(s, '--ink-2'), muted: css(s, '--muted'),
    lava: css(s, '--lava'), lava2: css(s, '--lava-2'), accentText: css(s, '--accent-text'), onLava: css(s, '--on-lava'),
    viewBg: css(s, '--view-bg'), viewFrame: css(s, '--view-frame'), viewInk: css(s, '--view-ink'), grainLine: css(s, '--grain-line'),
    skyTop: css(s, '--sky-top'), skyMid: css(s, '--sky-mid'), skyBottom: css(s, '--sky-bottom'),
    hemiSky: css(s, '--hemi-sky'), hemiGround: css(s, '--hemi-ground'), sun: css(s, '--sun'), frame3d: css(s, '--frame-3d'),
    chartGrid: css(s, '--chart-grid'), chartAxis: css(s, '--chart-axis'),
    seriesCa: css(s, '--series-ca'), seriesMc: css(s, '--series-mc'), seriesCaMc: css(s, '--series-camc'),
    series: [1, 2, 3, 4, 5, 6, 7, 8].map((k) => css(s, `--series-${k}`)),
    font: '"Inter", system-ui, "Segoe UI", sans-serif',
    mono: '"JetBrains Mono", ui-monospace, Consolas, monospace',
  };
  return cache;
}

/** Kolor serii wykresu wg nazwy algorytmu (CA = lawa, MC = chłodny fiolet, CA+MC = turkus) albo null. */
export function algorithmColor(name) {
  const c = themeColors();
  return { CA: c.seriesCa, MC: c.seriesMc, 'CA+MC': c.seriesCaMc }[name] || null;
}

/** Tło eksportu PNG/WebM jako gradient nieba 3D (te same kolory co tło podglądu w CSS). */
export function skyGradient(g, x, y, w, h) {
  const c = themeColors();
  const grad = g.createLinearGradient(0, y, 0, y + h);
  grad.addColorStop(0, c.skyTop); grad.addColorStop(0.58, c.skyMid); grad.addColorStop(1, c.skyBottom);
  return grad;
}

/** Domyślne kolory i krój Chart.js z motywu (osie, legenda, podpowiedź); wykresy rysowane od nowa po zmianie motywu. */
function applyChartTheme() {
  const C = typeof window !== 'undefined' ? window.Chart : null;
  if (!C) return;
  const c = themeColors();
  C.defaults.color = c.ink2;
  C.defaults.borderColor = c.chartGrid;
  C.defaults.font.family = c.font;
  const tt = C.defaults.plugins.tooltip;
  Object.assign(tt, { backgroundColor: c.panel, titleColor: c.ink, bodyColor: c.ink, borderColor: c.line, borderWidth: 1,
    padding: 9, cornerRadius: 8, boxPadding: 4 });
}

function syncToggle() {
  const b = document.getElementById('theme-toggle');
  if (!b) return;
  const dark = currentTheme() === 'dark';
  const label = dark ? 'Motyw ciemny — przełącz na jasny' : 'Motyw jasny — przełącz na ciemny';
  b.setAttribute('aria-label', label);
  b.title = label;
}

/** Wysokość nagłówka i paska wyniku → zmienne CSS (układ podglądów na całą wysokość okna). */
function observeChrome() {
  const root = document.documentElement.style;
  const head = document.querySelector('.topbar');
  const bar = document.getElementById('result-bar');
  const update = () => {
    if (head) root.setProperty('--header-h', `${Math.round(head.getBoundingClientRect().height)}px`);
    if (bar) root.setProperty('--resultbar-h', bar.hidden ? '0px' : `${Math.round(bar.getBoundingClientRect().height) + 14}px`);
  };
  const ro = new ResizeObserver(update);
  if (head) ro.observe(head);
  if (bar) {
    ro.observe(bar);
    new MutationObserver(update).observe(bar, { attributes: true, attributeFilter: ['hidden'] });
  }
  update();
}

/** Start: przełącznik, reakcja na zmianę ustawień systemu, obserwacja wysokości nagłówka. */
export function initTheme() {
  const saved = store.get(KEY);
  setTheme(saved === 'light' || saved === 'dark' ? saved : currentTheme(), false);
  document.getElementById('theme-toggle')?.addEventListener('click', () => setTheme(currentTheme() === 'dark' ? 'light' : 'dark'));
  const mq = window.matchMedia?.('(prefers-color-scheme: light)');
  mq?.addEventListener?.('change', (e) => {
    const s = store.get(KEY);
    if (s !== 'light' && s !== 'dark') setTheme(e.matches ? 'light' : 'dark', false);
  });
  syncToggle();
  observeChrome();
  // Suwaki: wypełnienie toru przy przeciąganiu (zmiany z kodu — rangeFill w replay.js i viewer2d.js).
  document.addEventListener('input', (e) => { if (e.target.type === 'range') rangeFill(e.target); });
  document.querySelectorAll('input[type=range]').forEach(rangeFill);
}
