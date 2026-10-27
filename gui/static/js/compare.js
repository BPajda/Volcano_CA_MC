// Zakładka „Porównanie” (etap 5): wyniki serii w jednej tabeli i na wykresie — m.in. wykres
// czasów symulacji CA i MC w funkcji liczby komórek (szablon „CA vs MC: rozmiar siatki”: log–log, osobno 2D i 3D).
//  - źródło: seria z GUI (results/gui/series/<id>/), seria z linii poleceń (folder z series.json albo
//    batch_summary.csv po engine --batch) albo dowolne zaznaczone wyniki,
//  - tabela (gui/compare.py: times.json, stats.json, config_used.json każdego wyniku): parametry zmienne,
//    czasy, kroki, koszt jednostkowy, pamięć, pliki; sortowanie; eksport CSV,
//  - wykres Chart.js: oś X, oś Y (jedna miara — nigdy dwie osie Y), serie (kolor = ta sama wartość
//    w każdym panelu), osobne wykresy (np. 2D i 3D), skala liniowa / logarytmiczna, eksport PNG,
//  - galeria: miniatury przekrojów 2D wszystkich wyników („wizualizacja przykładowych mikrostruktur”).
// Kolory serii (etap 7, theme.js): algorytm ma stałe kolory — CA = lawa, MC = chłodny fiolet, CA+MC = turkus
// (wszystkie pary rozróżnialne także przy daltonizmie, w obu motywach); inne podziały — paleta kategoryczna motywu
// (--series-1…8, sprawdzona walidatorem dla tła karty; identyfikację wspiera legenda i tabela). Kolor należy do wartości
// serii, nie do jej pozycji. Po zmianie motywu wykresy i galeria rysują się od nowa.

import { getBinary, getJSON, postJSON, typed, url } from './api.js';
import { fmtInt } from './estimate.js';
import { colorize } from './palette.js';
import { algorithmColor, onThemeChange, themeColors } from './theme.js';
import { $, $$, downloadBlob, esc, notice } from './util.js';

// Miary do wyboru na osi Y (liczbowe) i dodatkowe osie X; etykiety i jednostki z kolumn backendu.
const Y_KEYS = ['simMs', 'caSim', 'mcSim', 'total', 'save', 'mcSave', 'nsPerUnit', 'nsPerCellStep', 'nsPerTrial', 'steps',
  'mcs', 'peakRssMiB', 'modelMiB', 'bytesPerCell', 'outputMiB', 'totalLavaVolume', 'maxReach', 'grains', 'mcGrainsEnd',
  'mcMeanGrainSizeEnd'];
const X_KEYS = ['cells', 'nx', 'seeds', 'steps', 'mcs', 'domainCells', 'threads', 'neighborhood', 'algorithm', 'dim', 'mode', 'schedule'];
const GROUP_KEYS = ['algorithm', 'dim', 'neighborhood', 'mode', 'boundary'];
const COL_SETS = {
  times: ['status', 'algorithm', 'dim', 'cells', 'threads', 'steps', 'mcs', 'caSim', 'mcSim', 'simMs', 'nsPerUnit', 'total'],
  resources: ['status', 'algorithm', 'cells', 'peakRssMiB', 'modelMiB', 'bytesPerCell', 'outputMiB', 'save', 'mcSave', 'total'],
  stats: ['status', 'mode', 'neighborhood', 'seeds', 'steps', 'mcs', 'grains', 'totalLavaVolume', 'maxReach', 'mcGrainsEnd',
    'mcMeanGrainSizeEnd'],
};

function fmtNum(v, unit) {
  if (v == null || v === '') return '—';
  if (typeof v !== 'number') return esc(v);
  if (Number.isInteger(v) && Math.abs(v) >= 100) return fmtInt(v);
  const a = Math.abs(v);
  const d = unit === 'ms' || unit === 'ns' ? (a < 10 ? 2 : a < 100 ? 1 : 0) : (a < 1 ? 3 : a < 100 ? 2 : 1);
  return v.toLocaleString('pl-PL', { maximumFractionDigits: d, minimumFractionDigits: 0 });
}

export class CompareView {
  /** hooks: results() — lista wyników, openResult(id, tab) */
  constructor(hooks) {
    this.hooks = hooks;
    this.sources = [];
    this.table = null;
    this.ref = null;
    this.ids = null;
    this.charts = [];
    this.sort = { key: 'index', dir: 1 };
    this.timer = null;
    this.active = false;
    $('#cmp-source').addEventListener('change', () => this.load($('#cmp-source').value));
    $('#cmp-refresh').addEventListener('click', () => this.refreshSources(true));
    ['#cmp-x', '#cmp-y', '#cmp-series', '#cmp-panel', '#cmp-logx', '#cmp-logy'].forEach((s) => $(s).addEventListener('change', () => this.renderCharts()));
    $('#cmp-default').addEventListener('click', () => { this.applyDefaultView(); this.renderCharts(); });
    $('#cmp-png').addEventListener('click', () => this.exportPng());
    $('#cmp-csv').addEventListener('click', () => this.exportCsv());
    $('#cmp-cols').addEventListener('change', () => this.renderTable());
    $('#cmp-gal-field').addEventListener('change', () => this.renderGallery());
    $('#cmp-table thead').addEventListener('click', (ev) => {
      const th = ev.target.closest('th[data-sort]');
      if (!th) return;
      const key = th.dataset.sort;
      this.sort = { key, dir: this.sort.key === key ? -this.sort.dir : 1 };
      this.renderTable();
    });
    $('#cmp-gallery').addEventListener('click', (ev) => {
      const fig = ev.target.closest('figure[data-id]');
      if (fig) this.hooks.openResult(fig.dataset.id, ev.target.closest('[data-act=v3]') ? 'view3d' : 'view2d');
    });
    $('#cmp-pick-filter').addEventListener('input', () => this.renderPickList());
    $('#cmp-pick').addEventListener('toggle', () => { if ($('#cmp-pick').open) this.renderPickList(); });
    $('#cmp-pick-apply').addEventListener('click', () => {
      const ids = $$('#cmp-pick-list input:checked').map((c) => c.value);
      if (ids.length) this.loadIds(ids);
    });
    onThemeChange(() => { if (this.table) { this.renderCharts(); this.renderGallery(); } });
  }

  /** Zakładka pokazana / ukryta (automatyczne odświeżanie tylko na widocznej zakładce). */
  setActive(on) {
    this.active = on;
    if (on) this.refreshSources(false);
    else clearTimeout(this.timer);
  }

  async refreshSources(reload) {
    try {
      this.sources = await getJSON('/api/compare/sources');
    } catch (err) {
      $('#cmp-info').innerHTML = notice('error', esc(err.message));
      return;
    }
    const sel = $('#cmp-source');
    sel.innerHTML = (this.ids ? '<option value="">— zaznaczone wyniki —</option>' : '')
      + this.sources.map((s) => `<option value="${esc(s.ref)}">${esc(s.name)} · ${s.done}/${s.jobs} · ${esc(s.gui ? 'GUI' : s.source)} · results/${esc(s.ref)}</option>`).join('');
    if (!this.sources.length && !this.ids) sel.innerHTML = '<option value="">— brak serii —</option>';
    const want = this.ids ? '' : (this.ref && this.sources.some((s) => s.ref === this.ref) ? this.ref : this.sources[0]?.ref);
    if (want !== undefined) sel.value = want ?? '';
    if (this.ids) return reload ? this.loadIds(this.ids) : undefined;
    if (want && (reload || want !== this.ref || !this.table)) await this.load(want);
    else if (!want) this.showEmpty();
  }

  /** Otwiera konkretną serię (np. z zakładki „Zadania” albo „Seria”). */
  async open(ref) {
    this.ids = null;
    this.ref = null;
    await this.refreshSources(false);
    if (this.sources.some((s) => s.ref === ref)) {
      $('#cmp-source').value = ref;
      await this.load(ref);
    }
  }

  async load(ref) {
    if (!ref) return;
    this.ids = null;
    const first = this.ref !== ref;
    this.ref = ref;
    try {
      this.table = await getJSON(url('/api/compare', { series: ref }));
    } catch (err) {
      $('#cmp-info').innerHTML = notice('error', esc(err.message));
      return;
    }
    this.afterLoad(first);
  }

  async loadIds(ids) {
    this.ids = ids;
    this.ref = null;
    try {
      this.table = await postJSON('/api/compare', { ids });
    } catch (err) {
      $('#cmp-info').innerHTML = notice('error', esc(err.message));
      return;
    }
    await this.refreshSources(false);
    $('#cmp-source').value = '';
    this.afterLoad(true);
  }

  afterLoad(first) {
    const t = this.table;
    const ok = t.rows.filter((r) => r.status === 'ok').length;
    const s = t.series || {};
    $('#cmp-info').innerHTML = `${esc(s.name || '')}${s.template ? ` (szablon ${esc(s.template)})` : ''} · ${ok} z ${t.rows.length} wyników gotowych`
      + (s.created ? ` · utworzona ${esc(s.created.replace('T', ' '))}` : '');
    this.fillSelects(first);
    this.renderCharts();
    this.renderTable();
    if (first || this.galleryFor !== this.galleryKey()) this.renderGallery();
    clearTimeout(this.timer);
    if (this.active && t.rows.some((r) => r.status !== 'ok' && r.status !== 'błąd' && r.status !== 'anulowane' && r.status !== 'brak wyniku')) {
      this.timer = setTimeout(() => (this.ids ? this.loadIds(this.ids) : this.load(this.ref)), 3000);
    }
  }

  showEmpty() {
    this.table = null;
    $('#cmp-info').textContent = '';
    $('#cmp-empty').hidden = false;
    $('#cmp-table thead').innerHTML = $('#cmp-table tbody').innerHTML = '';
    $('#cmp-charts').innerHTML = '<p class="empty">Brak danych do wykresu.</p>';
    $('#cmp-gallery').innerHTML = '';
  }

  // ------------------------------------------------------------ wybór osi wykresu

  col(key) {
    if (key.startsWith('axis:')) return { key, label: key.slice(5), kind: 'cat' };
    if (key.startsWith('value:')) return { key, label: key.slice(6), kind: 'num' };
    return this.table.columns.find((c) => c.key === key) || { key, label: key };
  }

  value(row, key) {
    if (!key) return null;
    if (key.startsWith('axis:')) return row.labels?.[key.slice(5)] ?? null;
    if (key.startsWith('value:')) return row.values?.[key.slice(6)] ?? null;
    return row[key] ?? null;
  }

  label(key) {
    const c = this.col(key);
    return c.unit ? `${c.label} [${c.unit}]` : c.label;
  }

  fillSelects(first) {
    const t = this.table;
    const axes = (t.axes || []).map((a) => `axis:${a.name}`);
    const valueKeys = [];
    for (const r of t.rows) for (const k of Object.keys(r.values || {})) if (!valueKeys.includes(k)) valueKeys.push(k);
    const numericValues = valueKeys.filter((k) => t.rows.every((r) => r.values?.[k] == null || typeof r.values[k] === 'number'));
    const opts = (keys, none) => (none ? '<option value="">— brak —</option>' : '') + keys.map((k) => `<option value="${esc(k)}">${esc(this.label(k))}</option>`).join('');
    const keep = (sel, html) => { const cur = $(sel).value; $(sel).innerHTML = html; if ([...$(sel).options].some((o) => o.value === cur)) $(sel).value = cur; };
    keep('#cmp-x', opts([...X_KEYS, ...axes, ...numericValues.map((k) => `value:${k}`)]));
    keep('#cmp-y', opts(Y_KEYS));
    keep('#cmp-series', opts([...axes, ...GROUP_KEYS], true));
    keep('#cmp-panel', opts([...axes, ...GROUP_KEYS], true));
    if (first) this.applyDefaultView();
  }

  applyDefaultView() {
    const c = this.table?.series?.chart || {};
    const has = (sel, v) => [...$(sel).options].some((o) => o.value === v);
    const set = (sel, v, fallback) => { $(sel).value = has(sel, v) ? v : fallback; };
    set('#cmp-x', c.x, 'cells');
    set('#cmp-y', c.y, 'simMs');
    set('#cmp-series', c.series ?? '', has('#cmp-series', 'algorithm') ? 'algorithm' : '');
    set('#cmp-panel', c.panel ?? '', '');
    $('#cmp-logx').checked = c.logX ?? false;
    $('#cmp-logy').checked = c.logY ?? false;
  }

  // ------------------------------------------------------------ wykres

  renderCharts() {
    this.charts.splice(0).forEach((ch) => ch.destroy());
    const box = $('#cmp-charts');
    const t = this.table;
    if (!t || !window.Chart) {
      box.innerHTML = '<p class="empty">Brak danych do wykresu.</p>';
      return;
    }
    const xKey = $('#cmp-x').value, yKey = $('#cmp-y').value, sKey = $('#cmp-series').value, pKey = $('#cmp-panel').value;
    const logX = $('#cmp-logx').checked, logY = $('#cmp-logy').checked;
    const rows = t.rows.filter((r) => {
      const y = this.value(r, yKey), x = this.value(r, xKey);
      return r.status === 'ok' && typeof y === 'number' && x != null && (!logY || y > 0) && (!logX || typeof x !== 'number' || x > 0);
    });
    const categorical = rows.some((r) => typeof this.value(r, xKey) !== 'number');
    const th = themeColors();
    const INK = th.ink, INK2 = th.ink2, GRID = th.chartGrid;
    // Kolor należy do wartości serii (nie do jej pozycji w panelu) — ta sama seria ma ten sam kolor wszędzie;
    // algorytm CA / MC / CA+MC ma kolor stały (ten sam co w zakładce „Czasy i statystyki”).
    const seriesNames = [];
    for (const r of rows) { const s = String(this.value(r, sKey) ?? 'wszystkie'); if (!seriesNames.includes(s)) seriesNames.push(s); }
    const color = (s) => algorithmColor(s) || th.series[seriesNames.indexOf(s)] || th.muted;
    const panels = [];
    for (const r of rows) { const p = pKey ? String(this.value(r, pKey) ?? '—') : ''; if (!panels.includes(p)) panels.push(p); }
    panels.sort();
    box.innerHTML = panels.length ? panels.map((p, i) => `<div class="cmp-chart"><p class="legend-title">${esc(p ? `${this.col(pKey).label}: ${p}` : '')}</p>
      <div class="chart-box"><canvas id="cmp-chart-${i}" role="img" aria-label="${esc(`${this.label(yKey)} vs ${this.label(xKey)} ${p}`)}"></canvas></div></div>`).join('')
      : '<p class="empty">Brak gotowych wyników z tą miarą. Poczekaj na koniec zadań albo wybierz inną miarę.</p>';
    box.classList.toggle('two', panels.length > 1);
    const xLabels = [];
    if (categorical) for (const r of rows) { const x = String(this.value(r, xKey)); if (!xLabels.includes(x)) xLabels.push(x); }

    panels.forEach((p, i) => {
      const pr = rows.filter((r) => (pKey ? String(this.value(r, pKey) ?? '—') : '') === p);
      const names = seriesNames.filter((s) => pr.some((r) => String(this.value(r, sKey) ?? 'wszystkie') === s));
      const datasets = names.map((s) => {
        const sr = pr.filter((r) => String(this.value(r, sKey) ?? 'wszystkie') === s);
        const data = categorical
          ? xLabels.map((x) => { const r = sr.find((q) => String(this.value(q, xKey)) === x); return r ? { x, y: this.value(r, yKey), row: r } : null; }).filter(Boolean)
          : sr.map((r) => ({ x: this.value(r, xKey), y: this.value(r, yKey), row: r })).sort((a, b) => a.x - b.x);
        const c = color(s);
        return categorical
          ? { label: s, data, backgroundColor: c, borderColor: c, borderWidth: 0, borderRadius: 4, borderSkipped: 'bottom', barPercentage: 0.85, categoryPercentage: 0.8 }
          : { label: s, data, borderColor: c, backgroundColor: c, borderWidth: 2, pointRadius: 4, pointHoverRadius: 6, pointHitRadius: 12,
            pointBorderColor: th.panel, pointBorderWidth: 1.5, tension: 0 };
      });
      const axisTitle = (text) => ({ display: true, text, color: INK2 });
      // Oś logarytmiczna: podpisy tylko przy 1, 2 i 5 × 10^k (siatka zostaje) — bez tłoku etykiet 20 000, 30 000…
      const ticksFor = (log) => ({
        color: INK2, maxRotation: 0, autoSkip: !log,
        callback(v) {
          if (typeof v !== 'number') return this.getLabelForValue(v);
          if (log && v > 0) {
            const m = v / 10 ** Math.floor(Math.log10(v) + 1e-9);
            if (![1, 2, 5].some((k) => Math.abs(m - k) < 1e-6)) return '';
          }
          return fmtNum(v);
        },
      });
      const cfg = {
        type: categorical ? 'bar' : 'line',
        data: categorical ? { labels: xLabels.filter((x) => pr.some((r) => String(this.value(r, xKey)) === x)), datasets } : { datasets },
        options: {
          responsive: true, maintainAspectRatio: false, animation: false,
          interaction: categorical ? { mode: 'index', intersect: false } : { mode: 'x', intersect: false },
          plugins: {
            // Klucz legendy odwzorowuje znacznik: kreska dla linii, prostokąt dla słupków.
            legend: { display: names.length > 1,
              labels: categorical ? { color: INK, boxWidth: 12, boxHeight: 12 }
                : {
                  color: INK, usePointStyle: true, pointStyleWidth: 22,
                  // Kolor kreski = kolor linii serii (domyślnie Chart.js bierze obwódkę punktu — tu jasną).
                  generateLabels: (chart) => chart.data.datasets.map((ds, di) => ({
                    text: ds.label, strokeStyle: ds.borderColor, fillStyle: ds.borderColor, lineWidth: 3, pointStyle: 'line',
                    fontColor: INK, hidden: !chart.isDatasetVisible(di), datasetIndex: di,
                  })),
                } },
            tooltip: {
              callbacks: {
                title: (items) => (items[0] ? `${this.label(xKey)}: ${categorical ? items[0].label : fmtNum(items[0].parsed.x)}` : ''),
                label: (c) => `${fmtNum(c.parsed.y, this.col(yKey).unit)} ${this.col(yKey).unit || ''}: ${c.dataset.label} (${c.raw.row?.name || ''})`,
              },
            },
          },
          scales: {
            x: categorical
              ? { type: 'category', title: axisTitle(this.label(xKey)), grid: { color: GRID }, border: { color: th.chartAxis }, ticks: { color: INK2 } }
              : { type: logX ? 'logarithmic' : 'linear', title: axisTitle(this.label(xKey)), grid: { color: GRID }, border: { color: th.chartAxis },
                ticks: ticksFor(logX) },
            y: { type: logY ? 'logarithmic' : 'linear', title: axisTitle(this.label(yKey)), grid: { color: GRID }, border: { color: th.chartAxis },
              ticks: ticksFor(logY), beginAtZero: !logY },
          },
        },
      };
      this.charts.push(new window.Chart($(`#cmp-chart-${i}`), cfg));
    });
    const skipped = t.rows.filter((r) => r.status === 'ok').length - rows.length;
    let note = `${rows.length} punktów`;
    if (yKey === 'simMs') note += ' · czas symulacji = caSim dla CA, mcSim dla MC (bez wczytania, alokacji i zapisu)';
    if (yKey === 'nsPerUnit') note += ' · CA: ns na komórkę i krok, MC: ns na próbę (1 MCS = tyle prób, ile komórek domeny)';
    if (skipped > 0) note += ` · pominięto ${skipped} bez tej miary${logY || logX ? ' (albo ≤ 0 na skali log)' : ''}`;
    if (seriesNames.length > th.series.length) note += ' · więcej serii niż kolorów palety, wybierz inny podział';
    $('#cmp-chart-note').textContent = note;
    $('#cmp-chart-title').textContent = `${this.col(yKey).label} vs ${this.col(xKey).label}`;
  }

  exportPng() {
    if (!this.charts.length) return;
    const canvases = this.charts.map((c) => c.canvas);
    const titles = $$('#cmp-charts .cmp-chart .legend-title').map((p) => p.textContent);
    // Płótna wykresów mają rozdzielczość × devicePixelRatio — tytuły i marginesy w tej samej skali.
    const k = window.devicePixelRatio || 1;
    const pad = 16 * k, head = 44 * k, sub = titles.some(Boolean) ? 24 * k : 0;
    const w = canvases.reduce((s, c) => s + c.width, 0) + pad * (canvases.length + 1);
    const h = Math.max(...canvases.map((c) => c.height)) + head + sub + pad;
    const out = document.createElement('canvas');
    out.width = w;
    out.height = h;
    const ctx = out.getContext('2d'), th = themeColors();
    ctx.fillStyle = th.panel;  // tło karty bieżącego motywu (jak na ekranie; jasny motyw — do druku)
    ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = th.ink;
    ctx.font = `600 ${18 * k}px ${th.font}`;
    ctx.fillText(`${$('#cmp-chart-title').textContent}: ${this.table?.series?.name || ''}`, pad, 28 * k);
    let x = pad;
    canvases.forEach((c, i) => {
      if (titles[i]) {
        ctx.font = `600 ${14 * k}px ${th.font}`;
        ctx.fillStyle = th.ink2;
        ctx.fillText(titles[i], x, head + 14 * k);
      }
      ctx.drawImage(c, x, head + sub);
      x += c.width + pad;
    });
    out.toBlob((blob) => downloadBlob(blob, `${this.fileStem()}.png`), 'image/png');
  }

  fileStem() {
    return `porownanie_${(this.table?.series?.id || 'wybrane').replace(/[^A-Za-z0-9_-]+/g, '_')}`;
  }

  async exportCsv() {
    if (!this.table) return;
    const resp = this.ids
      ? await fetch('/api/compare/csv', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ids: this.ids }) })
      : await fetch(url('/api/compare/csv', { series: this.ref }));
    if (!resp.ok) return;
    downloadBlob(await resp.blob(), `${this.fileStem()}.csv`);
  }

  // ------------------------------------------------------------ tabela

  renderTable() {
    const t = this.table;
    $('#cmp-empty').hidden = !!t;
    if (!t) return;
    const set = $('#cmp-cols').value;
    const axes = (t.axes || []).map((a) => `axis:${a.name}`);
    const axisNames = (t.axes || []).map((a) => a.name);
    // Kolumna miary o tej samej nazwie co oś serii (np. „algorytm”) byłaby powtórzeniem — pomijamy ją.
    const metric = (set === 'all' ? t.columns.map((c) => c.key).filter((k) => k !== 'index' && k !== 'name') : COL_SETS[set])
      .filter((k) => !axisNames.includes(this.col(k).label));
    const keys = ['index', 'name', ...axes, ...metric];
    const { key, dir } = this.sort;
    const rows = [...t.rows].sort((a, b) => {
      const x = this.value(a, key), y = this.value(b, key);
      if (x == null && y == null) return 0;
      if (x == null) return 1;
      if (y == null) return -1;
      return (x < y ? -1 : x > y ? 1 : 0) * dir;
    });
    $('#cmp-table thead').innerHTML = `<tr>${keys.map((k) => {
      const c = this.col(k);
      const cls = [c.kind === 'num' ? 'num' : '', k === key ? (dir > 0 ? 'sorted-asc' : 'sorted-desc') : ''].filter(Boolean).join(' ');
      return `<th data-sort="${esc(k)}" class="${cls}" title="${esc(k)}">${esc(c.label)}${c.unit ? ` <span class="sub">[${esc(c.unit)}]</span>` : ''}</th>`;
    }).join('')}</tr>`;
    $('#cmp-table tbody').innerHTML = rows.map((r) => `<tr class="${r.status === 'ok' ? '' : 'pending'}">${keys.map((k) => {
      const c = this.col(k);
      const v = this.value(r, k);
      if (k === 'name') return `<td class="mono">${esc(v)}</td>`;
      if (k === 'status') return `<td><span class="status ${v === 'ok' ? 'done' : v === 'działa' ? 'running' : v === 'błąd' ? 'error' : 'queued'}">${esc(v === 'ok' ? 'gotowe' : v)}</span></td>`;
      return c.kind === 'num' ? `<td class="num">${fmtNum(v, c.unit)}</td>` : `<td>${esc(v ?? '—')}</td>`;
    }).join('')}</tr>`).join('');
  }

  // ------------------------------------------------------------ galeria mikrostruktur

  galleryKey() {
    return `${this.ref || this.ids?.join(',')}|${$('#cmp-gal-field').value}|${this.table?.rows.filter((r) => r.status === 'ok').length}`;
  }

  async renderGallery() {
    const t = this.table;
    const box = $('#cmp-gallery');
    if (!t) { box.innerHTML = ''; return; }
    this.galleryFor = this.galleryKey();
    const token = (this.galleryToken = (this.galleryToken || 0) + 1);
    const rows = t.rows.filter((r) => r.status === 'ok');
    box.innerHTML = rows.length ? rows.map((r) => `<figure data-id="${esc(r.id)}" title="Otwórz podgląd 2D: ${esc(r.id)}">
      <canvas width="160" height="160"></canvas>
      <figcaption><b>${r.index}.</b> ${esc(Object.values(r.labels || {}).join(' · ') || r.name)}<br>
      <span class="sub">${esc([r.nx, r.ny, r.nz].join('×'))} · ${esc(r.algorithm || '')}</span>
      <button class="btn btn-small btn-ghost" data-act="v3" title="Otwórz w podglądzie 3D">widok 3D</button></figcaption></figure>`).join('')
      : '<p class="empty">Brak gotowych wyników. Poczekaj na koniec zadań serii (zakładka „Zadania”).</p>';
    const figs = $$('figure[data-id]', box);
    let next = 0;
    const work = async () => {
      while (next < figs.length && token === this.galleryToken) {
        const fig = figs[next++];
        try { await this.thumb(fig); } catch { fig.classList.add('failed'); }
      }
    };
    await Promise.all([work(), work(), work()]);
  }

  async thumb(fig) {
    const id = fig.dataset.id;
    const meta = await getJSON(url('/api/result', { id }));
    const want = $('#cmp-gal-field').value;
    const field = want !== 'auto' ? (meta.fields.includes(want) ? want : 'type')
      : meta.fields.includes('crystal') ? 'crystal' : meta.fields.includes('flowId') ? 'flowId' : 'type';
    const [, ny, nz] = meta.dims;
    // 2D: płaszczyzna siatki; 3D lawa: przekrój pionowy przez środek wulkanu; 3D classic / MC: środkowa warstwa z.
    const axis = meta.planeAxis || (meta.mode === 'lava' ? 'y' : 'z');
    const index = meta.planeAxis ? 0 : axis === 'y' ? Math.floor(ny / 2) : Math.floor(nz / 2);
    const q = { id, axis, index, maxSide: 160 };
    const types = await getBinary(url('/api/result/slice', { ...q, field: 'type' }));
    const vals = field === 'type' ? types : await getBinary(url('/api/result/slice', { ...q, field }));
    const w = types.meta.width, h = types.meta.height;
    const rgba = colorize(w, h, typed('uint8', types.buffer), field === 'type' ? null : typed(vals.meta.dtype, vals.buffer), field,
      { ranges: meta.ranges }, true);
    const canvas = fig.querySelector('canvas');
    const scale = Math.min(canvas.width / w, canvas.height / h);
    const tmp = document.createElement('canvas');
    tmp.width = w;
    tmp.height = h;
    tmp.getContext('2d').putImageData(new ImageData(rgba, w, h), 0, 0);
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = themeColors().viewBg;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(tmp, (canvas.width - w * scale) / 2, (canvas.height - h * scale) / 2, w * scale, h * scale);
    fig.title = `${id}: ${field}, przekrój ⟂ ${axis} = ${index}${types.meta.step > 1 ? ` (co ${types.meta.step}. komórka)` : ''}; kliknij: podgląd 2D`;
  }

  // ------------------------------------------------------------ dowolne wyniki

  renderPickList() {
    const q = $('#cmp-pick-filter').value.trim().toLowerCase();
    const items = this.hooks.results().filter((r) => !q || r.id.toLowerCase().includes(q) || r.name.toLowerCase().includes(q)).slice(0, 300);
    const checked = new Set(this.ids || []);
    $('#cmp-pick-list').innerHTML = items.map((r) => `<label class="pick"><input type="checkbox" value="${esc(r.id)}" ${checked.has(r.id) ? 'checked' : ''}>
      <span>${esc(r.name)} <span class="sub mono">${esc(r.id)}</span></span></label>`).join('') || '<p class="empty">Brak wyników.</p>';
  }
}
