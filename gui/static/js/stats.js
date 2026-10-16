// Zakładka „Czasy i statystyki”: times.json (sekcje, pamięć, pliki), stats.json (CA i MC),
// mc_stats.csv (liczba ziaren i średnia wielkość ziarna vs MCS — Chart.js) i historia aktywnych komórek CA.
// Każdy wykres ma jedną serię i jedną oś Y (dwie wielkości o różnej skali = dwa wykresy).
// Kolory z motywu (theme.js): CA = lawa, MC = chłodny fiolet — te same co w Porównaniu; po zmianie motywu
// zakładka rysuje się od nowa z zapamiętanych danych.

import { fmtBytes, fmtInt } from './estimate.js';
import { onThemeChange, themeColors } from './theme.js';

const SECTION_NAMES = {
  readConfig: 'wczytanie configu', readInput: 'wczytanie wyniku CA (--mc-from)', allocate: 'alokacja siatki',
  terrain: 'teren', vents: 'kratery / zarodki', caSim: 'symulacja CA', snapshots: 'migawki', save: 'zapis wyników CA',
  mcInit: 'MC: przygotowanie', mcSim: 'symulacja MC', mcStats: 'MC: statystyki', mcSave: 'zapis wyników MC',
};
const INFO_NAMES = {
  cells: 'komórki', space: 'wymiary', mode: 'tryb', grid: 'siatka', neighborhood: 'sąsiedztwo', boundary: 'brzeg',
  steps: 'kroki CA', stopReason: 'koniec CA', mcDomain: 'domena MC', mcs: 'MCS', domainCells: 'komórki domeny MC',
  Q: 'Q', mcMobility: 'mobilność ze stygnięcia', mcFrom: 'wejście (--mc-from)', cpu: 'procesor', compiler: 'kompilator', build: 'build',
};
const charts = [];
let last = null;  // { root, d } — do ponownego narysowania po zmianie motywu
onThemeChange(() => { if (last && last.root.isConnected) renderStats(last.root, last.d); });

/** Rodzaj paska czasu etapu: obliczenia CA (lawa), MC (fiolet), reszta (wczytanie, alokacja, zapis) — neutralnie. */
const barKind = (k) => (k === 'caSim' ? '' : k === 'mcSim' ? ' mc' : ' other');

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const ms = (v) => (v >= 100 ? fmtInt(v) : v.toLocaleString('pl-PL', { maximumFractionDigits: 2 }));
const num = (v, d = 2) => (typeof v === 'number' ? v.toLocaleString('pl-PL', { maximumFractionDigits: d }) : esc(v ?? '—'));

function kv(pairs) {
  return `<dl class="kv">${pairs.filter(([, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `<dt>${esc(k)}</dt><dd>${v}</dd>`).join('')}</dl>`;
}

function timesCard(t) {
  const total = t.total || 0;
  const rows = Object.keys(SECTION_NAMES).filter((k) => typeof t[k] === 'number');
  const max = Math.max(...rows.map((k) => t[k]), 1);
  let html = `<div class="card"><h3>Czasy etapów (times.json)</h3><table class="table"><thead><tr><th>Etap</th>
    <th class="num">ms</th><th class="num">% całości</th><th></th></tr></thead><tbody>`;
  for (const k of rows) {
    html += `<tr><td>${SECTION_NAMES[k]} <span class="sub mono">${k}</span></td><td class="num">${ms(t[k])}</td>
      <td class="num">${total ? ((100 * t[k]) / total).toLocaleString('pl-PL', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) : '—'}</td>
      <td class="bar-cell"><div class="bar${barKind(k)}" style="width:${(100 * t[k]) / max}%"></div></td></tr>`;
  }
  html += `<tr><td><b>razem</b> <span class="sub mono">total</span></td><td class="num"><b>${ms(total)}</b></td><td class="num">100</td><td></td></tr>`;
  html += '</tbody></table>';
  if (t.detail) {
    html += `<p class="legend-title">Fazy (--timing-detail) [ms]</p>${kv(Object.entries(t.detail).map(([k, v]) => [k, ms(v)]))}`;
  }
  return `${html}</div>`;
}

function infoCard(t) {
  const pairs = Object.keys(INFO_NAMES).filter((k) => k in t).map((k) => {
    let v = t[k];
    if (Array.isArray(v)) v = v.join(' × ');
    else if (typeof v === 'number') v = fmtInt(v);
    else if (typeof v === 'boolean') v = v ? 'tak' : 'nie';
    return [INFO_NAMES[k], esc(v)];
  });
  return `<div class="card"><h3>Przebieg</h3>${kv(pairs)}</div>`;
}

function memoryCard(t) {
  const m = t.memory;
  if (!m) return '';
  const model = m.model || {};
  const b = (v) => (v != null ? fmtBytes(v) : null);
  const pairs = [
    ['szczyt pamięci procesu', b(m.peakRssBytes)],
    ['szczyt pamięci prywatnej', b(m.peakPrivateBytes)],
    ['pamięć na starcie / na końcu', m.startRssBytes != null ? `${fmtBytes(m.startRssBytes)} / ${fmtBytes(m.endRssBytes)}` : null],
    ['model teoretyczny (szczyt)', b(model.peakBytes)],
    ['model: bajtów na komórkę', model.peakBytesPerCell != null ? num(model.peakBytesPerCell, 1) : null],
    ['skład szczytu (model)', model.peakBlocks ? esc(Object.entries(model.peakBlocks).map(([k, v]) => `${k} ${fmtBytes(v)}`).join(', ')) : null],
  ];
  let html = `<div class="card"><h3>Pamięć i pliki</h3>${kv(pairs)}`;
  const files = t.files;
  if (files && typeof files === 'object') {
    const list = Array.isArray(files) ? files : Object.entries(files).map(([name, f]) => ({ name, ...f }));
    html += `<p class="legend-title">Pliki wynikowe</p><table class="table"><thead><tr><th>Plik</th><th class="num">rozmiar</th>
      <th class="num">zapis [ms]</th></tr></thead><tbody>`;
    for (const f of list) {
      const name = (f.name || f.path || '').split(/[\\/]/).pop();
      html += `<tr><td class="mono">${esc(name)}</td><td class="num">${f.bytes != null ? fmtBytes(f.bytes) : f.size != null ? fmtBytes(f.size) : '—'}</td>
        <td class="num">${f.ms != null ? ms(f.ms) : f.writeMs != null ? ms(f.writeMs) : '—'}</td></tr>`;
    }
    html += '</tbody></table>';
  }
  return `${html}</div>`;
}

function caStatsCard(s) {
  if (!s || !('steps' in s)) return '';
  let html = '<div class="card"><h3>Statystyki CA (stats.json)</h3>';
  if (s.mode === 'lava') {
    html += kv([['tryb', 'lava'], ['kroki', fmtInt(s.steps)], ['koniec', esc(s.stopReason)],
      ['objętość lawy (lawa + bazalt)', `${fmtInt(s.totalLavaVolume)} komórek`], ['płynna lawa na końcu', fmtInt(s.liquidLava)],
      ['zasięg maks.', `${num(s.maxReach, 1)} komórek`]]);
    const flows = (s.flows || []).slice(0, 12);
    if (flows.length) {
      html += `<table class="table"><thead><tr><th>Krater</th><th>Położenie</th><th class="num">Komórki</th><th class="num">Bazalt</th>
        <th class="num">Zasięg</th></tr></thead><tbody>${flows.map((f) => `<tr><td>${f.flowId}</td><td class="mono">${f.vent.join(', ')}</td>
        <td class="num">${fmtInt(f.cells)}</td><td class="num">${fmtInt(f.basalt ?? 0)}</td><td class="num">${num(f.maxReach, 1)}</td></tr>`).join('')}
        </tbody></table>`;
      if ((s.flows || []).length > flows.length) html += `<p class="hint">… i ${s.flows.length - flows.length} kolejnych</p>`;
    }
  } else {
    html += kv([['tryb', 'classic'], ['kroki', fmtInt(s.steps)], ['koniec', esc(s.stopReason)], ['ziarna', fmtInt(s.grains)],
      ['średnia wielkość ziarna', `${num(s.meanGrainSize, 1)} komórek`], ['najmniejsze / największe', `${fmtInt(s.minGrainSize)} / ${fmtInt(s.maxGrainSize)}`]]);
  }
  return `${html}</div>`;
}

function mcStatsCard(mc) {
  if (!mc) return '';
  let html = `<div class="card"><h3>Statystyki MC (stats.json)</h3>${kv([
    ['domena', `${esc(mc.domain)} — ${fmtInt(mc.domainCells)} komórek`], ['Q / MCS', `${mc.Q} / ${mc.mcs}`],
    ['J / kT', `${num(mc.J)} / ${num(mc.kT)}`], ['sąsiedztwo / brzeg', `${esc(mc.neighborhood)} / ${esc(mc.boundary)}`],
    ['mobilność', mc.mobility === 'cooling' ? `ze stygnięcia (min ${num(mc.mobilityMin)})` : 'wyłączona'],
    ['ziarna: start → koniec', `${fmtInt(mc.grainsStart)} → ${fmtInt(mc.grainsEnd)}`],
    ['średnia wielkość ziarna', `${num(mc.meanGrainSizeStart)} → ${num(mc.meanGrainSizeEnd)} komórek`],
    ['największe ziarno', fmtInt(mc.largestGrainEnd)], ['energia', `${fmtInt(mc.energyStart)} → ${fmtInt(mc.energyEnd)}`],
    ['akceptacja', mc.attempts ? `${num((100 * mc.accepted) / mc.attempts, 1)}% z ${fmtInt(mc.attempts)} prób` : '—'],
  ])}`;
  const bm = mc.byMobility;
  if (bm) {
    const row = (name, c) => `<tr><td>${name}</td><td class="num">${fmtInt(c.cells)}</td><td class="num">${fmtInt(c.grainsEnd)}</td>
      <td class="num">${num(c.meanGrainSizeEnd)}</td><td class="num">${fmtInt(c.largestGrainEnd)}</td></tr>`;
    html += `<p class="legend-title">Wg mobilności (próg ${num(bm.threshold)}) — efekt „chilled margin”</p>
      <table class="table"><thead><tr><th>Klasa</th><th class="num">komórki</th><th class="num">ziarna</th><th class="num">średnia</th>
      <th class="num">największe</th></tr></thead><tbody>${row('długo płynna (m ≥ 0,5)', bm.high)}${row('szybko zastygła (m < 0,5)', bm.low)}</tbody></table>`;
  }
  return `${html}</div>`;
}

function lineChart(canvas, xs, ys, xLabel, yLabel, color) {
  const C = window.Chart;
  if (!C) return;
  const th = themeColors(), grid = th.chartGrid, ink2 = th.ink2;
  charts.push(new C(canvas, {
    type: 'line',
    data: { labels: xs, datasets: [{ data: ys, borderColor: color, backgroundColor: color, borderWidth: 2, pointRadius: xs.length > 60 ? 0 : 3,
      pointBorderColor: th.panel, pointBorderWidth: 1.5, tension: 0 }] },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      interaction: { mode: 'index', intersect: false },
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => `${yLabel}: ${c.parsed.y.toLocaleString('pl-PL')}` } } },
      scales: {
        x: { type: 'linear', title: { display: true, text: xLabel, color: ink2 }, grid: { color: grid }, border: { color: th.chartAxis },
          ticks: { color: ink2 } },
        y: { title: { display: true, text: yLabel, color: ink2 }, grid: { color: grid }, border: { color: th.chartAxis },
          ticks: { color: ink2 }, beginAtZero: true },
      },
    },
  }));
}

/** Rysuje zakładkę dla szczegółów wyniku (odpowiedź /api/result/details). */
export function renderStats(root, d) {
  last = { root, d };
  charts.splice(0).forEach((c) => c.destroy());
  const th = themeColors();
  const t = d.times || {};
  const s = d.stats || {};
  let html = '';
  html += d.times ? timesCard(t) : '<div class="card"><h3>Czasy</h3><p class="empty">Brak times.json — wynik bez pomiaru czasu</p></div>';
  html += d.times ? infoCard(t) : '';
  html += memoryCard(t);
  html += caStatsCard(s);
  html += mcStatsCard(s.mc);
  if (d.mcStats) {
    html += `<div class="card wide"><h3>Monte Carlo vs MCS (mc_stats.csv)</h3><div class="chart-row">
      <div><p class="legend-title">Liczba ziaren</p><div class="chart-box"><canvas id="ch-grains"></canvas></div></div>
      <div><p class="legend-title">Średnia wielkość ziarna [komórki]</p><div class="chart-box"><canvas id="ch-mean"></canvas></div></div>
      </div></div>`;
  }
  if (Array.isArray(s.activeCells) && s.activeCells.length > 1) {
    html += `<div class="card wide"><h3>${s.mode === 'classic' ? 'Komórki należące do ziaren' : 'Płynna lawa'} po każdym kroku CA (stats.json)</h3>
      <div class="chart-box"><canvas id="ch-active"></canvas></div></div>`;
  }
  if (d.config) {
    html += `<div class="card wide"><details><summary>config_used.json</summary><pre>${esc(JSON.stringify(d.config, null, 2))}</pre></details></div>`;
  }
  root.innerHTML = html;
  if (d.mcStats) {
    lineChart(root.querySelector('#ch-grains'), d.mcStats.mcs, d.mcStats.grains, 'MCS', 'liczba ziaren', th.seriesMc);
    lineChart(root.querySelector('#ch-mean'), d.mcStats.mcs, d.mcStats.meanGrainSize, 'MCS', 'średnia wielkość ziarna', th.seriesMc);
  }
  if (root.querySelector('#ch-active')) {
    const step = s.activeCellsStep || 1;
    lineChart(root.querySelector('#ch-active'), s.activeCells.map((_, i) => (i + 1) * step), s.activeCells, 'krok CA',
      s.mode === 'classic' ? 'komórki ziaren' : 'komórki płynnej lawy', th.seriesCa);
  }
}
