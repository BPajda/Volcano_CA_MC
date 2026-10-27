// Zakładka „Seria” (etap 5): generator serii zadań = config bazowy + 1–3 parametry zmienne (osie).
//  - config bazowy: aktualny formularz „Nowa symulacja”, preset z configs/, plik JSON albo szablon,
//  - oś: klucz(e) configu (lista z engine --print-defaults; kilka kluczy = parametry sparowane, zmieniają się
//    razem) i wartości: lista, zakres (od, do, krok) albo potęgi (od, do, mnożnik),
//  - zadania = iloczyn kartezjański osi — rozwija je backend (gui/series.py, ten sam moduł co
//    tools/make_series.py), tu tylko podgląd z szacunkiem czasu i pamięci (heurystyka etapu 3, estimate.js),
//  - „Uruchom serię”: backend zapisuje WSZYSTKIE configi i foldery, dopiero potem dodaje zadania do kolejki.

import { getJSON, postJSON } from './api.js';
import { estimate, fmtBytes, fmtInt, fmtTime } from './estimate.js';
import { fieldGroup, fieldLabel, leafPaths, mergeConfig } from './form.js';
import { $, $$, debounce, esc, notice, plural } from './util.js';

const MAX_AXES = 3;
const PROCESS_OVERHEAD_MS = 150;

/** Krótki opis configu: tryb, wymiary, sąsiedztwo, brzeg, zarodki/kratery, MC. */
export function describeConfig(cfg) {
  const sp = cfg.space || {};
  const mc = cfg.mc || {};
  const full = mc.enabled && mc.domain === 'full';
  const classic = cfg.ca?.mode === 'classic';
  const parts = [full ? 'MC full (bez CA)' : classic ? 'CA classic' : 'CA lava', `${sp.nx}×${sp.ny}×${sp.nz}`,
    cfg.neighborhood, cfg.boundary];
  if (!full) parts.push(classic ? plural(cfg.vents?.count ?? 1, 'zarodek', 'zarodki', 'zarodków') : plural(cfg.vents?.count ?? 1, 'krater', 'kratery', 'kraterów'));
  if (mc.enabled) parts.push(`MC Q = ${mc.Q}, ${mc.mcs} MCS`);
  parts.push(`wyjście ${cfg.output?.format}`);
  return parts.filter(Boolean).join(' · ');
}

function stripComments(text) {
  return String(text).replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
}

export class SeriesView {
  /** hooks: defaults(), presets(), formConfig(), queue(), showJobs(), openCompare(ref), setQueue(body) */
  constructor(hooks) {
    this.hooks = hooks;
    this.templates = [];
    this.base = null;            // { source, config, label }
    this.axes = [];
    this.template = null;        // wybrany szablon (id, chart, measure)
    this.preview = null;
    this.previewSeq = 0;
    this.schedulePreview = debounce(() => this.runPreview(), 350);

    $('#series-add-axis').addEventListener('click', () => this.addAxis());
    $('#series-run').addEventListener('click', () => this.run());
    $('#series-name').addEventListener('input', () => this.schedulePreview());
    $$('input[name=series-base]').forEach((r) => r.addEventListener('change', () => this.setBaseSource(r.value)));
    $('#series-preset').addEventListener('change', () => { $('input[name=series-base][value=preset]').checked = true; this.setBaseSource('preset'); });
    $('#series-import').addEventListener('click', () => $('#series-import-file').click());
    $('#series-import-file').addEventListener('change', (e) => { if (e.target.files[0]) this.importBase(e.target.files[0]); e.target.value = ''; });
    $('#series-axes').addEventListener('input', (ev) => this.onAxisInput(ev));
    $('#series-axes').addEventListener('change', (ev) => this.onAxisChange(ev));
    $('#series-axes').addEventListener('click', (ev) => this.onAxisClick(ev));
    $('#series-templates').addEventListener('click', (ev) => {
      const b = ev.target.closest('button[data-template]');
      if (b) this.applyTemplate(b.dataset.template);
    });
  }

  async init() {
    try {
      this.templates = await getJSON('/api/series/templates');
    } catch (err) {
      $('#series-templates').innerHTML = notice('error', esc(err.message));
    }
    $('#series-templates').innerHTML = this.templates.map((t) => `<button class="template" data-template="${esc(t.id)}">
      <b>${esc(t.name)}</b><span class="sub">${plural(t.jobs, 'zadanie', 'zadania', 'zadań')}${t.measure ? ' · pomiar czasu' : ''}</span>
      <span class="template-desc">${esc(t.description)}</span></button>`).join('');
    const sel = $('#series-preset');
    sel.innerHTML = this.hooks.presets().filter((p) => p.group === 'configs' && !p.mcFromOnly)
      .map((p) => `<option value="${esc(p.file)}">${esc(p.name)}</option>`).join('');
    if (!this.base) {
      $('input[name=series-base][value=form]').checked = true;
      this.setBaseSource('form');
    }
    if (!this.axes.length) this.addAxis(false);
    this.renderAxes();
  }

  /** Zakładka pokazana: config z formularza mógł się zmienić. */
  onShow() {
    if (this.base?.source === 'form') this.setBaseSource('form');
    this.renderQueueNote();
  }

  // ------------------------------------------------------------ config bazowy

  setBaseSource(source) {
    const defaults = this.hooks.defaults();
    if (source === 'form') {
      this.base = { source, config: this.hooks.formConfig(), label: 'aktualny formularz „Nowa symulacja”' };
    } else if (source === 'preset') {
      const p = this.hooks.presets().find((x) => x.file === $('#series-preset').value);
      if (!p) return;
      this.base = { source, config: mergeConfig(defaults, p.config), label: `preset ${p.file}` };
    } else if (source === 'template' && this.template) {
      this.base = { source, config: mergeConfig(defaults, this.template.base), label: `szablon „${this.template.name}”` };
    } else {
      return;  // „plik” — config ustawia importBase()
    }
    this.renderBase();
    this.schedulePreview();
  }

  importBase(file) {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const cfg = JSON.parse(stripComments(reader.result));
        if (typeof cfg !== 'object' || Array.isArray(cfg)) throw new Error('plik musi zawierać obiekt JSON { … }');
        this.base = { source: 'file', config: mergeConfig(this.hooks.defaults(), cfg), label: `plik ${file.name}` };
        $('input[name=series-base][value=file]').checked = true;
        this.renderBase();
        this.schedulePreview();
      } catch (err) {
        $('#series-base-summary').innerHTML = notice('error', `Nie można wczytać ${esc(file.name)}: ${esc(err.message)}`);
      }
    };
    reader.readAsText(file, 'utf-8');
  }

  renderBase() {
    if (!this.base) return;
    $('#series-base-summary').innerHTML = `<b>${esc(this.base.label)}</b>: ${esc(describeConfig(this.base.config))}`;
    $('#series-base-json').textContent = JSON.stringify(this.base.config, null, 2);
  }

  // ------------------------------------------------------------ szablony

  applyTemplate(id) {
    const t = this.templates.find((x) => x.id === id);
    if (!t) return;
    this.template = t;
    this.axes = t.axes.map((a) => ({ name: a.name, keys: [...a.keys], mode: 'list', text: a.text, start: '', stop: '', step: '', factor: '' }));
    $('#series-name').value = t.id;
    const radio = $('input[name=series-base][value=template]');
    radio.disabled = false;
    radio.checked = true;
    this.setBaseSource('template');
    $$('#series-templates .template').forEach((b) => b.classList.toggle('active', b.dataset.template === id));
    this.renderAxes();
    this.renderQueueNote();
    $('#series-result').innerHTML = '';
  }

  // ------------------------------------------------------------ osie (parametry zmienne)

  addAxis(render = true) {
    if (this.axes.length >= MAX_AXES) return;
    this.axes.push({ name: `parametr ${this.axes.length + 1}`, keys: [], mode: 'list', text: '', start: '', stop: '', step: '', factor: '' });
    if (render) {
      this.renderAxes();
      this.schedulePreview();
    }
  }

  keyOptions(exclude) {
    const groups = new Map();
    for (const p of leafPaths(this.hooks.defaults())) {
      if (exclude.has(p)) continue;
      const g = fieldGroup(p);
      if (!groups.has(g)) groups.set(g, []);
      groups.get(g).push(p);
    }
    let html = '<option value="">+ dodaj klucz…</option>';
    for (const [g, keys] of groups) {
      html += `<optgroup label="${esc(g)}">${keys.map((k) => `<option value="${esc(k)}">${esc(fieldLabel(k))} (${esc(k)})</option>`).join('')}</optgroup>`;
    }
    return html;
  }

  renderAxes() {
    const used = new Set(this.axes.flatMap((a) => a.keys));
    $('#series-axes').innerHTML = this.axes.map((a, i) => {
      const pointsInfo = this.preview?.axes?.[i]
        ? `→ ${plural(this.preview.axes[i].points.length, 'wartość', 'wartości', 'wartości')}: ${this.preview.axes[i].points.map((p) => esc(p.label)).join(', ')}`
        : '';
      const chips = a.keys.map((k) => `<span class="chip" title="${esc(fieldLabel(k))}"><code>${esc(k)}</code>
        <button class="chip-x" data-act="remove-key" data-key="${esc(k)}" title="Usuń klucz">×</button></span>`).join('');
      const modeRadio = (m, label) => `<label><input type="radio" name="axis-mode-${i}" value="${m}" data-field="mode" ${a.mode === m ? 'checked' : ''}> ${label}</label>`;
      const num = (f, label) => `<label class="field-inline">${label} <input type="text" class="num-small" data-field="${f}" value="${esc(a[f] ?? '')}"></label>`;
      return `<div class="axis" data-i="${i}">
        <div class="axis-head"><b>Parametr ${i + 1}</b>
          <label class="field-inline">nazwa osi <input type="text" class="axis-name" data-field="name" value="${esc(a.name)}" maxlength="30"></label>
          ${a.keys.length > 1 ? '<span class="badge-soft">sparowane: zmieniają się razem</span>' : ''}
          <button class="btn btn-small btn-ghost axis-remove" data-act="remove-axis">Usuń parametr</button></div>
        <div class="axis-keys">klucze: ${chips || '<span class="sub">wybierz klucz configu →</span>'}
          <select data-act="add-key" class="axis-key-add">${this.keyOptions(used)}</select>
          ${a.keys.length ? '<span class="hint">(kolejny klucz = sparowanie)</span>' : ''}</div>
        <div class="axis-mode">wartości: ${modeRadio('list', 'lista')} ${modeRadio('range', 'zakres')} ${modeRadio('pow', 'potęgi')}</div>
        <div class="axis-values">${a.mode === 'list'
          ? `<textarea rows="2" data-field="text" placeholder="np. 100, 200, 500  albo  [CA] false;basalt, [MC] true;full">${esc(a.text)}</textarea>`
          : a.mode === 'range' ? `${num('start', 'od')} ${num('stop', 'do')} ${num('step', 'krok')}`
            : `${num('start', 'od')} ${num('stop', 'do')} ${num('factor', 'mnożnik')}`}</div>
        <div class="axis-points hint">${pointsInfo}</div>
      </div>`;
    }).join('') || '<p class="empty">Brak parametrów zmiennych. Dodaj co najmniej jeden.</p>';
    $('#series-add-axis').disabled = this.axes.length >= MAX_AXES;
  }

  axisAt(ev) {
    const el = ev.target.closest('.axis');
    return el ? this.axes[Number(el.dataset.i)] : null;
  }

  onAxisInput(ev) {
    const a = this.axisAt(ev);
    const f = ev.target.dataset.field;
    if (!a || !f || f === 'mode') return;
    a[f] = ev.target.value;
    this.schedulePreview();
  }

  onAxisChange(ev) {
    const a = this.axisAt(ev);
    if (!a) return;
    if (ev.target.dataset.field === 'mode') {
      a.mode = ev.target.value;
      this.renderAxes();
      this.schedulePreview();
    } else if (ev.target.dataset.act === 'add-key' && ev.target.value) {
      a.keys.push(ev.target.value);
      if (a.name.startsWith('parametr ') && a.keys.length === 1) a.name = ev.target.value.split('.').pop();
      this.renderAxes();
      this.schedulePreview();
    }
  }

  onAxisClick(ev) {
    const btn = ev.target.closest('button[data-act]');
    const a = this.axisAt(ev);
    if (!btn || !a) return;
    if (btn.dataset.act === 'remove-key') a.keys = a.keys.filter((k) => k !== btn.dataset.key);
    else if (btn.dataset.act === 'remove-axis') this.axes.splice(this.axes.indexOf(a), 1);
    this.renderAxes();
    this.schedulePreview();
  }

  // ------------------------------------------------------------ podgląd i uruchomienie

  spec() {
    return {
      name: $('#series-name').value.trim() || this.template?.id || 'seria',
      description: this.template?.description || '',
      template: this.base?.source === 'template' ? this.template?.id : null,
      chart: this.base?.source === 'template' ? this.template?.chart : {},
      base: this.base?.config || {},
      axes: this.axes.map((a) => ({
        name: a.name, keys: a.keys, mode: a.mode, text: a.text,
        start: a.start === '' ? null : Number(String(a.start).replace(',', '.')),
        stop: a.stop === '' ? null : Number(String(a.stop).replace(',', '.')),
        step: a.step === '' ? null : Number(String(a.step).replace(',', '.')),
        factor: a.factor === '' ? null : Number(String(a.factor).replace(',', '.')),
      })),
    };
  }

  async runPreview() {
    const seq = ++this.previewSeq;
    const msg = $('#series-messages');
    if (!this.axes.length || this.axes.some((a) => !a.keys.length)) {
      this.preview = null;
      this.renderPreview();
      msg.innerHTML = this.axes.length ? notice('info', 'Wybierz klucz configu dla każdego parametru zmiennego.') : '';
      return;
    }
    try {
      const res = await postJSON('/api/series/preview', { spec: this.spec() });
      if (seq !== this.previewSeq) return;  // w międzyczasie przyszła nowsza zmiana
      this.preview = res;
      msg.innerHTML = res.warnings.map((w) => notice('warn', esc(w))).join('');
    } catch (err) {
      if (seq !== this.previewSeq) return;
      this.preview = null;
      msg.innerHTML = (err.errors || [err.message]).map((e) => notice('error', esc(e))).join('');
    }
    this.renderAxesPoints();
    this.renderPreview();
  }

  renderAxesPoints() {
    $$('#series-axes .axis').forEach((el, i) => {
      const ax = this.preview?.axes?.[i];
      el.querySelector('.axis-points').innerHTML = ax
        ? `→ ${plural(ax.points.length, 'wartość', 'wartości', 'wartości')}: ${ax.points.map((p) => esc(p.label)).join(', ')}` : '';
    });
  }

  renderPreview() {
    const p = this.preview;
    const thead = $('#series-preview-table thead'), tbody = $('#series-preview-table tbody');
    $('#series-preview-empty').hidden = !!p;
    if (!p) {
      thead.innerHTML = tbody.innerHTML = '';
      $('#series-count').textContent = '';
      $('#series-estimate').innerHTML = '';
      $('#series-run').disabled = true;
      return;
    }
    const axes = p.axes.map((a) => a.name);
    let total = 0, maxBytes = 0, files = 0;
    const warns = new Map();
    this.estimates = {};
    const rows = p.jobs.map((j) => {
      const e = estimate(j.config);
      this.estimates[j.name] = Math.round(e.ms);
      total += e.ms + PROCESS_OVERHEAD_MS;
      maxBytes = Math.max(maxBytes, e.bytes);
      files += e.fileBytes;
      e.warnings.filter((w) => w.level !== 'info').forEach((w) => warns.set(w.text, w.level));
      return `<tr><td class="num">${j.index}</td><td class="mono">${esc(j.name)}</td>
        ${axes.map((a) => `<td>${esc(j.labels[a])}</td>`).join('')}
        <td>${esc(describeConfig(j.config).split(' · ').slice(0, 2).join(' · '))}</td>
        <td class="num">${e.steps ? fmtInt(e.steps) : '—'}</td><td class="num">~${fmtTime(e.ms)}</td><td class="num">~${fmtBytes(e.bytes)}</td></tr>`;
    });
    thead.innerHTML = `<tr><th class="num">nr</th><th>plik / folder</th>${axes.map((a) => `<th>${esc(a)}</th>`).join('')}
      <th>tryb, wymiary</th><th class="num">kroki CA (szac.)</th><th class="num">czas (szac.)</th><th class="num">pamięć (szac.)</th></tr>`;
    tbody.innerHTML = rows.join('');
    $('#series-count').textContent = plural(p.count, 'zadanie', 'zadania', 'zadań');
    $('#series-paths').textContent = `${p.configsDir}NN_….json + series.json → ${p.resultsDir}NN_…/`;
    const workers = this.hooks.queue()?.workers || 1;
    let html = `<table class="estimate-table">
      <tr><td>Zadania</td><td><b>${fmtInt(p.count)}</b> (${p.axes.map((a) => a.points.length).join(' × ')})</td></tr>
      <tr><td>Łączny czas (szacunek)</td><td>~${fmtTime(total)}${workers > 1 ? ` <span class="hint">(${workers} workery: ~${fmtTime(total / workers)})</span>` : ''}</td></tr>
      <tr><td>Największa pamięć</td><td>~${fmtBytes(maxBytes)}</td></tr>
      <tr><td>Pliki wyników</td><td>~${fmtBytes(files)}</td></tr></table>
      <p class="hint">Heurystyka z pomiarów profilu, rząd wielkości (czas: obliczenia + ~${PROCESS_OVERHEAD_MS} ms na proces).</p>`;
    for (const [text, level] of warns) html += notice(level === 'error' ? 'error' : 'warn', esc(text));
    $('#series-estimate').innerHTML = html;
    $('#series-run').disabled = false;
  }

  renderQueueNote() {
    const q = this.hooks.queue();
    if (!q) return;
    const pin = q.pin?.enabled ? `przypięcie do CPU ${q.pin.cpus.slice(0, q.workers).join(', ')}` : 'bez przypięcia';
    let html = `<p class="hint">Kolejka: ${q.workers === 1 ? '1 worker (zadania po kolei)' : `${q.workers} workery równolegle`}, ${pin}${q.paused ? ', <b>wstrzymana</b>' : ''}.</p>`;
    if (this.template?.measure && (q.workers > 1 || !q.pin?.enabled)) {
      html += notice('warn', `Ten szablon mierzy czasy: zalecany <b>1 worker</b> i <b>przypięcie do rdzenia P</b> (jak w pomiarach profilu).
        <br><button class="btn btn-small" id="series-measure-setup">Ustaw 1 worker + przypięcie</button>`);
    }
    $('#series-queue-note').innerHTML = html;
    $('#series-measure-setup')?.addEventListener('click', async () => {
      await this.hooks.setQueue({ workers: 1, pin: { enabled: true } });
      this.renderQueueNote();
    });
  }

  async run() {
    const btn = $('#series-run');
    btn.disabled = true;
    $('#series-result').innerHTML = notice('info', 'Walidacja wszystkich configów (engine --validate) i zapis plików serii…');
    try {
      await this.runPreview();
      if (!this.preview) throw Object.assign(new Error('Popraw błędy w opisie serii'), { errors: [] });
      const res = await postJSON('/api/series', { spec: this.spec(), estimates: this.estimates });
      const n = res.jobs.length;
      $('#series-result').innerHTML = notice('ok', `Seria <b>${esc(res.name)}</b> (<code>${esc(res.id)}</code>):<br>
        utworzono ${plural(n, 'plik konfiguracyjny', 'pliki konfiguracyjne', 'plików konfiguracyjnych')} + <code>series.json</code> w
        <code>${esc(res.configsDir)}/</code> i ${plural(n, 'folder', 'foldery', 'folderów')} wyników w <code>${esc(res.resultsDir)}/</code>;
        dopiero potem ${plural(n, 'zadanie trafiło', 'zadania trafiły', 'zadań trafiło')} do kolejki.<br>
        <button class="btn btn-small" id="series-goto-jobs">Pokaż w zakładce Zadania</button>
        <button class="btn btn-small" id="series-goto-compare">Porównanie</button>`);
      $('#series-goto-jobs').addEventListener('click', () => this.hooks.showJobs());
      $('#series-goto-compare').addEventListener('click', () => this.hooks.openCompare(`gui/series/${res.id}`));
      this.hooks.showJobs(false);
    } catch (err) {
      const errors = err.errors?.length ? err.errors : [err.message];
      $('#series-result').innerHTML = errors.slice(0, 12).map((e) => notice('error', esc(e))).join('')
        + (errors.length > 12 ? `<p class="hint">… i ${errors.length - 12} kolejnych</p>` : '');
    } finally {
      btn.disabled = false;
    }
  }
}
