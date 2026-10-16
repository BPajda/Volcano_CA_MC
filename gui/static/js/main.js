// Główny moduł GUI: zakładki, formularz nowej symulacji (z mapą wysokości), lista wyników (ZIP, VTK, MC na
// wyniku CA), wybór wyniku do podglądu 2D / 3D / czasów. Zakładki „Seria”, „Zadania” i „Porównanie” mają
// własne moduły (series.js, jobs.js, compare.js). Cała logika obliczeń jest w silniku C++ — tu tylko
// zbieranie parametrów, wywołania API i wizualizacja. Wygląd (etap 7): motyw ciemny / jasny — theme.js, kolory
// danych — palette.js.

import { getJSON, postJSON, url } from './api.js';
import { ConfigForm } from './form.js';
import { estimate, fmtBytes, fmtInt, fmtTime } from './estimate.js';
import { Viewer2D } from './viewer2d.js';
import { Viewer3D } from './viewer3d.js';
import { renderStats } from './stats.js';
import { JobsView } from './jobs.js';
import { SeriesView } from './series.js';
import { CompareView } from './compare.js';
import { HeightmapPanel } from './heightmap.js';
import { VentPicker } from './ventpicker.js';
import { initTheme } from './theme.js';
import { $, $$, downloadBlob, esc, notice, store } from './util.js';

const state = {
  info: null, defaults: null, presets: [], results: [],
  selected: null, meta: null, tab: 'form',
  sort: { key: 'modified', dir: -1 },
};
let form, viewer2d, viewer3d, jobsView, seriesView, compareView, heightmapPanel, ventPicker;

// ---------------------------------------------------------------- zakładki

const TABS = ['form', 'series', 'jobs', 'results', 'compare', 'view2d', 'view3d', 'stats'];

function showTab(name) {
  if (!TABS.includes(name)) name = 'form';
  state.tab = name;
  $$('.tab').forEach((b) => b.classList.toggle('active', b.dataset.tab === name));
  $$('.tab-panel').forEach((p) => { p.hidden = p.id !== `tab-${name}`; });
  $('#result-bar').hidden = !['view2d', 'view3d', 'stats'].includes(name);
  if (location.hash !== `#${name}`) history.replaceState(null, '', `#${name}`);
  compareView?.setActive(name === 'compare');
  if (name === 'jobs') jobsView.refresh();
  if (name === 'series') seriesView.onShow();
  if (name === 'results') refreshResults();
  if (['view2d', 'view3d', 'stats'].includes(name)) ensureSelection().then(() => showSelected());
}

// ---------------------------------------------------------------- formularz

function slug(name) {
  const t = name.replace(/ł/g, 'l').replace(/Ł/g, 'L').normalize('NFKD').replace(/[̀-ͯ]/g, '')
    .replace(/[^A-Za-z0-9_-]+/g, '_').replace(/_+/g, '_').replace(/^[_-]+|[_-]+$/g, '').slice(0, 40);
  return t || 'zadanie';
}

function updateIdPreview() {
  const d = new Date(), p = (n) => String(n).padStart(2, '0');
  const stamp = `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
  const id = `${stamp}_${slug($('#job-name').value || 'zadanie')}`;
  $('#job-id-preview').textContent = `configs/gui/${id}.json → results/gui/${id}/`;
}

/** Config do wysłania: przy MC na gotowym wyniku CA bez sekcji space — wymiary pochodzą z pliku
 *  (inaczej silnik ostrzega o konflikcie wymiarów podanych przez użytkownika). */
function configToSend(cfg = form.get()) {
  if ($('#mc-from-select').value) delete cfg.space;
  return cfg;
}

function mcFromResult() {
  const id = $('#mc-from-select').value;
  return id ? state.results.find((r) => r.id === id) || { id } : null;
}

function onFormChange(cfg) {
  const mcFrom = mcFromResult();
  const e = estimate(cfg, mcFrom);
  const kind = e.full ? 'Monte Carlo na całej przestrzeni' : mcFrom ? `MC na wyniku ${esc(mcFrom.name || mcFrom.id)}`
    : `${e.classic ? 'rozrost klasyczny CA' : 'lawa (CA)'}${e.mcOn ? ' + krystalizacja MC' : ''}`;
  let html = `<table class="estimate-table">
    <tr><td>Przestrzeń</td><td>${e.dims.join(' × ')} (${e.d}D)</td></tr>
    <tr><td>Komórki</td><td>${fmtInt(e.cells)}</td></tr>
    <tr><td>Przebieg</td><td>${kind}</td></tr>
    <tr><td>Pamięć (szacunek)</td><td>~${fmtBytes(e.bytes)}</td></tr>
    <tr><td>Czas (szacunek)</td><td>~${fmtTime(e.ms)}${e.steps ? ` <span class="hint">(~${fmtInt(e.steps)} kroków CA)</span>` : ''}</td></tr>
    <tr><td>Pliki wyników</td><td>~${fmtBytes(e.fileBytes)}</td></tr></table>
    <p class="hint">Heurystyka z pomiarów profilu (B/komórkę, ns/komórkę·krok, ns/próbę MC) — rząd wielkości.</p>`;
  for (const w of e.warnings) html += notice(w.level === 'error' ? 'error' : w.level === 'info' ? 'info' : 'warn', esc(w.text));
  $('#estimate').innerHTML = html;
  // cfg z argumentu — onFormChange jest wołane już z konstruktora formularza, zanim `form` jest przypisany.
  $('#config-preview').textContent = JSON.stringify(configToSend(JSON.parse(JSON.stringify(cfg))), null, 2);
  heightmapPanel?.sync(cfg);
  ventPicker?.sync(cfg);
}

function showValidation(res, title) {
  const box = $('#validation');
  let html = '';
  if (res.ok) html += notice('ok', title || 'Config poprawny — silnik przyjmie te parametry.');
  for (const e of res.errors || []) html += notice('error', esc(e));
  for (const w of res.warnings || []) html += notice('warn', `Ostrzeżenie: ${esc(w)}`);
  box.innerHTML = html;
  form.markErrors(res.errors);
}

async function validate() {
  $('#run-result').innerHTML = '';
  $('#validation').innerHTML = notice('info', 'Sprawdzanie (engine --validate)…');
  try {
    const res = await postJSON('/api/validate', { config: configToSend(), mcFrom: $('#mc-from-select').value || null });
    showValidation(res);
    return res;
  } catch (err) {
    showValidation({ ok: false, errors: err.errors });
    return null;
  }
}

async function run() {
  const btn = $('#btn-run');
  btn.disabled = true;
  $('#validation').innerHTML = notice('info', 'Walidacja i tworzenie zadania…');
  $('#run-result').innerHTML = '';
  try {
    const job = await postJSON('/api/jobs', {
      name: $('#job-name').value.trim() || 'zadanie', config: configToSend(), mcFrom: $('#mc-from-select').value || null,
    });
    showValidation({ ok: true, warnings: job.warnings }, 'Config poprawny — zadanie dodane do kolejki.');
    $('#run-result').innerHTML = notice('ok', `Utworzono plik konfiguracyjny <code>${esc(job.configPath)}</code><br>
      i folder wyników <code>${esc(job.outDir)}/</code>.<br>
      <button class="btn btn-small" id="goto-jobs">Pokaż w zakładce Zadania</button>`);
    $('#goto-jobs').addEventListener('click', () => showTab('jobs'));
    jobsView.refresh();
  } catch (err) {
    showValidation({ ok: false, errors: err.errors, warnings: err.warnings });
  } finally {
    btn.disabled = false;
    updateIdPreview();
  }
}

function fillPresets() {
  const sel = $('#preset-select');
  sel.innerHTML = '<option value="">— wybierz preset —</option>';
  const groups = { configs: 'configs/ — przykładowe configi', gui: 'configs/gui/ — configi zadań z GUI' };
  for (const [g, label] of Object.entries(groups)) {
    const items = state.presets.filter((p) => p.group === g);
    if (!items.length) continue;
    const og = document.createElement('optgroup');
    og.label = label;
    (g === 'gui' ? [...items].reverse() : items).forEach((p) => og.appendChild(new Option(g === 'gui' ? `${p.label} (${p.name})` : p.name, p.file)));
    sel.appendChild(og);
  }
}

function loadPreset() {
  const p = state.presets.find((x) => x.file === $('#preset-select').value);
  if (!p) return;
  form.set(p.config);
  $('#job-name').value = p.group === 'gui' ? p.label : p.name;
  if (!p.mcFromOnly) { $('#mc-from-select').value = ''; form.setMcFrom(false); }
  let desc = `<b>${esc(p.file)}</b>${p.description ? ` — ${esc(p.description)}` : ''}${p.note ? `<br>${esc(p.note)}` : ''}`;
  if (p.mcFromOnly) desc += '<br>Ten preset zawiera tylko parametry MC — wybierz wynik CA w polu „Źródło danych”.';
  $('#preset-description').innerHTML = desc;
  $('#validation').innerHTML = '';
  $('#run-result').innerHTML = '';
  updateIdPreview();
}

function importFile(file) {
  const reader = new FileReader();
  reader.onload = () => {
    try {
      // Silnik dopuszcza komentarze // i /* */ — usuwamy je przed JSON.parse.
      const text = String(reader.result).replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
      const cfg = JSON.parse(text);
      if (typeof cfg !== 'object' || Array.isArray(cfg)) throw new Error('plik musi zawierać obiekt JSON { … }');
      form.set(cfg);
      $('#job-name').value = file.name.replace(/\.json$/i, '');
      $('#preset-description').innerHTML = `Zaimportowano <b>${esc(file.name)}</b>${cfg._opis ? ` — ${esc(cfg._opis)}` : ''}`;
      updateIdPreview();
      validate();
    } catch (err) {
      $('#validation').innerHTML = notice('error', `Nie można wczytać ${esc(file.name)}: ${esc(err.message)}`);
    }
  };
  reader.readAsText(file, 'utf-8');
}

function exportFile() {
  const name = slug($('#job-name').value || 'config');
  downloadBlob(new Blob([JSON.stringify(form.get(), null, 2) + '\n'], { type: 'application/json' }), `${name}.json`);
}

function fillMcFrom() {
  const sel = $('#mc-from-select'), cur = sel.value;
  sel.innerHTML = '<option value="">nowa symulacja (teren → CA → opcjonalnie MC)</option>';
  for (const r of state.results.filter((x) => x.hasCa && x.mode === 'lava')) {
    sel.add(new Option(`MC na wyniku CA: ${r.name} (${(r.dims || []).join('×')})`, r.id));
  }
  sel.value = [...sel.options].some((o) => o.value === cur) ? cur : '';
}

/** MC na wybranym wyniku CA: zakładka „Nowa symulacja” z presetem mc_basalt i polem „Źródło danych”. */
function mcFromResultId(id) {
  showTab('form');
  const p = state.presets.find((x) => x.mcFromOnly);
  if (p) { $('#preset-select').value = p.file; loadPreset(); }
  $('#mc-from-select').value = id;
  form.setMcFrom(true);
  $('#job-name').value = `mc_na_${slug(id.split('/').pop())}`.slice(0, 40);
  updateIdPreview();
  $('#validation').innerHTML = notice('info', `Samo Monte Carlo na wyniku CA <code>${esc(id)}</code> (<code>engine --mc-from</code>) — sprawdź parametry MC i kliknij Uruchom.`);
}

// ---------------------------------------------------------------- wyniki

const sortValue = {
  name: (r) => r.name.toLowerCase(), dims: (r) => r.cells || 0, mode: (r) => r.mode || '', neighborhood: (r) => r.neighborhood || '',
  steps: (r) => r.steps ?? r.mcs ?? -1, caSim: (r) => r.times?.caSim ?? -1, mcSim: (r) => r.times?.mcSim ?? -1,
  size: (r) => r.size || 0, modified: (r) => r.modified || 0,
};

function renderResults() {
  const q = $('#results-filter').value.trim().toLowerCase();
  const mode = $('#results-mode').value, src = $('#results-source').value;
  const srcOk = (r) => !src || (src === 'series' ? !!r.series : src === 'gui' ? r.gui && !r.series : !r.gui && !r.series);
  let rows = state.results.filter((r) => (!q || r.name.toLowerCase().includes(q) || r.id.toLowerCase().includes(q))
    && (!mode || (mode === 'mc' ? r.hasMc : r.mode === mode)) && srcOk(r));
  const { key, dir } = state.sort;
  rows = rows.sort((a, b) => { const x = sortValue[key](a), y = sortValue[key](b); return (x < y ? -1 : x > y ? 1 : 0) * dir; });
  $$('#results-table th[data-sort]').forEach((th) => {
    th.classList.toggle('sorted-asc', th.dataset.sort === key && dir > 0);
    th.classList.toggle('sorted-desc', th.dataset.sort === key && dir < 0);
  });
  const ms = (v) => (v == null ? '—' : fmtInt(v));
  $('#results-table tbody').innerHTML = rows.map((r) => `<tr data-id="${esc(r.id)}" class="${r.id === state.selected ? 'selected' : ''}">
    <td><b>${esc(r.name)}</b><br><span class="sub mono">results/${esc(r.id)}</span></td>
    <td>${r.dims ? r.dims.join('×') : '—'}<br><span class="sub">${r.cells ? fmtInt(r.cells) : ''}</span></td>
    <td>${esc(r.mode || '—')}${r.hasMc && r.mode !== 'mc_full' && r.mode !== 'mc_from' ? ' + MC' : ''}<br><span class="sub">${esc(r.format || '')}</span></td>
    <td>${esc(r.neighborhood || '—')}<br><span class="sub">${esc(r.boundary || '')}</span></td>
    <td class="num">${r.steps != null ? fmtInt(r.steps) : '—'}${r.mcs != null ? `<br><span class="sub">${fmtInt(r.mcs)} MCS</span>` : ''}</td>
    <td class="num">${ms(r.times?.caSim)}</td><td class="num">${ms(r.times?.mcSim)}</td>
    <td class="num">${fmtBytes(r.size || 0)}<br><span class="sub">${r.files?.length || 0} plików</span></td>
    <td>${r.modified ? new Date(r.modified * 1000).toLocaleString('pl-PL', { dateStyle: 'short', timeStyle: 'short' }) : '—'}</td>
    <td class="row-actions"><span class="btn-group"><button class="btn btn-small" data-act="2d" title="Podgląd 2D">2D</button><button
        class="btn btn-small" data-act="3d" title="Podgląd 3D">3D</button><button class="btn btn-small" data-act="stats" title="Czasy i statystyki">Czasy</button></span><br>
      <span class="btn-group"><a class="btn btn-small" href="${esc(url('/api/result/zip', { id: r.id }))}" download title="Folder wyniku jako ZIP">ZIP</a><a class="btn btn-small"
        href="${esc(url('/api/result/vtk', { id: r.id }))}" download title="VTK ImageData (.vti) dla ParaView">VTK</a>${r.hasCa && r.mode === 'lava'
        ? '<button class="btn btn-small" data-act="mcfrom" title="Samo Monte Carlo na tym wyniku CA (--mc-from)">MC</button>' : ''}</span></td></tr>`).join('');
  $('#results-empty').hidden = rows.length > 0;
}

async function refreshResults() {
  try {
    state.results = await getJSON('/api/results');
  } catch { return; }
  renderResults();
  fillResultSelect();
  fillMcFrom();
}

function fillResultSelect() {
  const sel = $('#result-select');
  const sorted = [...state.results].sort((a, b) => (b.modified || 0) - (a.modified || 0));
  sel.innerHTML = sorted.map((r) => `<option value="${esc(r.id)}">${esc(r.name)} — ${(r.dims || []).join('×')} ${esc(r.mode || '')}${r.gui ? ' (GUI)' : ''}</option>`).join('');
  if (state.selected) sel.value = state.selected;
}

async function ensureSelection() {
  if (state.selected) return;
  if (!state.results.length) await refreshResults();
  const saved = store.get('volcano.result');
  const pick = state.results.find((r) => r.id === saved) || [...state.results].sort((a, b) => (b.modified || 0) - (a.modified || 0))[0];
  if (pick) await selectResult(pick.id, false);
}

let selectSeq = 0;  // numer ostatniego wyboru — odpowiedź na starszy wybór (szybkie przełączanie) jest pomijana

async function selectResult(id, show = true) {
  const seq = ++selectSeq;
  state.selected = id;
  store.set('volcano.result', id);
  if (![...$('#result-select').options].some((o) => o.value === id)) await refreshResults();
  if (seq !== selectSeq) return;
  $('#result-select').value = id;
  $('#result-info').textContent = 'wczytywanie…';
  $('#result-zip').href = url('/api/result/zip', { id });
  $('#result-vtk').href = url('/api/result/vtk', { id });
  try {
    const meta = await getJSON(url('/api/result', { id }));
    if (seq !== selectSeq) return;
    state.meta = meta;
    const m = state.meta;
    $('#result-info').textContent = `${m.dims.join(' × ')} (${m.is2D ? '2D' : '3D'}) · tryb ${m.mode || '—'} · pola: ${m.fields.length}`
      + ` · ${[m.sources.ca, m.sources.mc].filter(Boolean).join(' + ')} · ${m.folder}`;
  } catch (err) {
    state.meta = null;
    $('#result-info').textContent = `Błąd: ${err.message}`;
  }
  renderResults();
  if (show) showSelected();
}

let statsFor = null;
async function showSelected() {
  if (!state.meta) return;
  if (state.tab === 'view2d') viewer2d.setResult(state.meta);
  else if (state.tab === 'view3d') viewer3d.setResult(state.meta);
  else if (state.tab === 'stats' && statsFor !== state.meta.id) {
    statsFor = state.meta.id;
    $('#stats-content').innerHTML = '<div class="card wide"><p class="empty">wczytywanie czasów i statystyk…</p></div>';
    try {
      renderStats($('#stats-content'), await getJSON(url('/api/result/details', { id: state.meta.id })));
    } catch (err) {
      $('#stats-content').innerHTML = `<div class="card">${notice('error', esc(err.message))}</div>`;
      statsFor = null;
    }
  }
}

/** Otwiera wynik w podglądzie (z zakładek „Zadania” i „Porównanie”). */
async function openResult(id, tab = 'view2d') {
  await selectResult(id, false);
  showTab(tab);
}

// ---------------------------------------------------------------- start

async function init() {
  initTheme();  // przełącznik motywu, wysokość nagłówka; kolory Chart.js — przed pierwszym wykresem
  $$('.tab').forEach((b) => b.addEventListener('click', () => showTab(b.dataset.tab)));
  window.addEventListener('hashchange', () => showTab(location.hash.slice(1)));

  state.info = await getJSON('/api/info');
  // Status silnika jako „pigułka”: kropka + krótki tekst; pełna ścieżka i katalogi w podpowiedzi.
  const es = $('#engine-status');
  es.className = `engine-status ${state.info.engine ? 'ok' : 'missing'}`;
  es.innerHTML = state.info.engine ? '<span class="dot"></span>silnik gotowy' : '<span class="dot"></span>silnik nie znaleziony';
  es.title = `Silnik: ${state.info.engine || 'brak'} (${state.info.engineSource})\nconfigi: ${state.info.guiConfigsDir}\nwyniki: ${state.info.guiResultsDir}`;
  if (state.info.warnings.length) {
    const w = $('#app-warnings');
    w.hidden = false;
    w.innerHTML = state.info.warnings.map(esc).join('<br>');
  }

  jobsView = new JobsView({
    showResult: (rid) => openResult(rid, 'view2d'),
    openCompare: (ref) => { showTab('compare'); compareView.open(ref); },
    onJobsFinished: () => refreshResults(),
    onUpdate: () => { if (state.tab === 'series') seriesView.renderQueueNote(); },
  });
  heightmapPanel = new HeightmapPanel({ form: () => form });
  ventPicker = new VentPicker({ form: () => form, maps: () => heightmapPanel.maps });

  try {
    state.defaults = await getJSON('/api/defaults');
  } catch (err) {
    $('#config-form').innerHTML = notice('error', `Nie można pobrać domyślnego configu z silnika: ${esc(err.message)}`);
    state.defaults = null;
  }
  if (state.defaults) {
    await heightmapPanel.refresh();
    form = new ConfigForm($('#config-form'), state.defaults, onFormChange);
    state.presets = await getJSON('/api/presets');
    fillPresets();
  } else {
    $('#btn-validate').disabled = $('#btn-run').disabled = true;
  }

  $('#btn-preset-load').addEventListener('click', loadPreset);
  $('#preset-select').addEventListener('change', loadPreset);
  $('#btn-import').addEventListener('click', () => $('#import-file').click());
  $('#import-file').addEventListener('change', (e) => { if (e.target.files[0]) importFile(e.target.files[0]); e.target.value = ''; });
  $('#btn-export').addEventListener('click', exportFile);
  $('#btn-defaults').addEventListener('click', () => {
    form.set({}); $('#preset-select').value = ''; $('#preset-description').textContent = 'Wartości domyślne silnika (engine --print-defaults).';
  });
  $('#btn-validate').addEventListener('click', validate);
  $('#btn-run').addEventListener('click', run);
  $('#job-name').addEventListener('input', updateIdPreview);
  $('#mc-from-select').addEventListener('change', () => form?.setMcFrom(!!$('#mc-from-select').value));
  setInterval(updateIdPreview, 1000);
  updateIdPreview();

  $('#results-table tbody').addEventListener('click', async (ev) => {
    const tr = ev.target.closest('tr[data-id]');
    if (!tr || ev.target.closest('a')) return;
    const act = ev.target.closest('button')?.dataset.act;
    if (act === 'mcfrom') { mcFromResultId(tr.dataset.id); return; }
    await selectResult(tr.dataset.id, false);
    if (act) showTab({ '2d': 'view2d', '3d': 'view3d', stats: 'stats' }[act]);
  });
  $('#results-table thead').addEventListener('click', (ev) => {
    const th = ev.target.closest('th[data-sort]');
    if (!th) return;
    const key = th.dataset.sort;
    state.sort = { key, dir: state.sort.key === key ? -state.sort.dir : (key === 'name' || key === 'mode' ? 1 : -1) };
    renderResults();
  });
  ['#results-filter', '#results-mode', '#results-source'].forEach((s) => $(s).addEventListener('input', renderResults));
  $('#btn-results-refresh').addEventListener('click', refreshResults);
  $('#result-select').addEventListener('change', (e) => selectResult(e.target.value));

  // Pasek odtwarzania erupcji (etap 6) — te same elementy w 2D (v2-) i 3D (v3-).
  const replayEls = (p) => Object.fromEntries(['bar', 'on', 'source', 'play', 'time', 'label', 'speed', 'counts', 'color',
    'frames', 'webm', 'msg'].map((k) => [k, $(`#${p}-replay-${k}`)]));
  viewer2d = new Viewer2D({
    wrap: $('#v2-wrap'), canvas: $('#v2-canvas'), tooltip: $('#v2-tooltip'), loading: $('#v2-loading'), legend: $('#v2-legend'),
    status: $('#v2-status'), field: $('#v2-field'), axisRadios: $$('input[name=v2-axis]'), index: $('#v2-index'),
    indexNum: $('#v2-index-num'), indexMax: $('#v2-index-max'), boundaries: $('#v2-boundaries'), fit: $('#v2-fit'), png: $('#v2-png'),
    replay: replayEls('v2'),
  });
  viewer3d = new Viewer3D({
    wrap: $('#v3-wrap'), loading: $('#v3-loading'), legend: $('#v3-legend'), status: $('#v3-status'), field: $('#v3-field'),
    modeRadios: $$('input[name=v3-mode]'), topSurface: $('#v3-top-surface'), topGroup: $('#v3-top-group'), exag: $('#v3-exag'),
    exagGroup: $('#v3-exag-group'), exagVal: $('#v3-exag-val'), reset: $('#v3-reset'), png: $('#v3-png'),
    replay: replayEls('v3'),
  });

  compareView = new CompareView({ results: () => state.results, openResult });
  seriesView = new SeriesView({
    defaults: () => state.defaults || {},
    presets: () => state.presets,
    formConfig: () => (form ? form.get() : state.defaults || {}),
    queue: () => jobsView.queue,
    showJobs: (switchTab = true) => { if (switchTab) showTab('jobs'); else jobsView.refresh(); },
    openCompare: (ref) => { showTab('compare'); compareView.open(ref); },
    setQueue: (body) => jobsView.updateQueue(body),
  });

  await refreshResults();
  await jobsView.refresh();
  if (state.defaults) await seriesView.init();
  showTab(location.hash.slice(1) || 'form');
}

init().catch((err) => {
  document.querySelector('main').insertAdjacentHTML('afterbegin', notice('error', `Błąd startu GUI: ${esc(err.message)}`));
});
