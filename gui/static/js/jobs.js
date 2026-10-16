// Zakładka „Zadania” — kolejka zadań (etapy 4–5, „GUI — kolejkowanie zadań”):
//  - pauza / wznowienie kolejki, liczba równoległych workerów (ostrzeżenie: równoległe zadania zaburzają
//    pomiary czasu), przypięcie procesu silnika do rdzenia P + wysoki priorytet (jak pomiary z etapu 3),
//  - filtr statusu, grupowanie po serii: postęp „X z N”, czas, szacowany czas do końca, anulowanie serii,
//  - akcje zadania: log, anuluj, ▲/▼ (kolejność oczekujących), ponów (błąd / anulowane / przerwane), pokaż wynik.
// Lista odświeża się co 1 s, gdy coś jest w kolejce (inaczej co 5 s).

import { getJSON, getText, postJSON, url } from './api.js';
import { fmtInt, fmtTime } from './estimate.js';
import { $, esc, icon, notice, plural } from './util.js';

const STATUS_ICON = { queued: 'clock', running: 'run', done: 'check', error: 'x', cancelled: 'minus', interrupted: 'alert' };
const ACTIVE = new Set(['queued', 'running']);
const RETRYABLE = new Set(['error', 'cancelled', 'interrupted']);
const PROCESS_OVERHEAD_MS = 150;  // start procesu silnika, odczyt configu, zapis plików — poza szacunkiem obliczeń

function elapsed(job) {
  if (job.durationS != null) return job.durationS;
  if (job.status === 'running' && job.started) return (Date.now() - new Date(job.started).getTime()) / 1000;
  return null;
}

function progressHTML(job) {
  const p = job.progress || {};
  const mc = job.summary?.mcs != null && job.summary?.mode !== 'mc_full';
  if (job.status === 'done') return '<div class="progress done"><span style="width:100%"></span></div>';  // „gotowe” — w kolumnie Status
  if (job.status === 'queued') {
    return `<div class="progress"><span style="width:0"></span></div><span class="sub">w kolejce${job.queuePosition ? ` (#${job.queuePosition})` : ''}</span>`;
  }
  if (job.status !== 'running') {
    return `<div class="progress failed"><span style="width:100%"></span></div><span class="sub">${esc(job.error || job.statusLabel)}</span>`;
  }
  let frac = null, text = 'start…';
  if (p.stage === 'ca') {
    const classic = String(job.summary?.mode || '').startsWith('classic');
    const stage = mc ? 'etap 1/2 · ' : '';
    if (classic && job.cells) {
      frac = Math.min(1, (p.active || 0) / job.cells);
      text = `${stage}CA: krok ${fmtInt(p.done)} · wypełnienie ${(100 * frac).toFixed(0)}%`;
    } else {
      text = `${stage}CA: krok ${fmtInt(p.done)} (limit ${fmtInt(p.total)}) · płynna lawa ${fmtInt(p.active || 0)}`;
    }
  } else if (p.stage === 'mc') {
    frac = p.total ? p.done / p.total : 1;
    text = `${mc ? 'etap 2/2 · ' : ''}MC: ${fmtInt(p.done)} / ${fmtInt(p.total)} MCS`;
  } else if (p.stage === 'save') {
    text = 'zapis wyników…';
  }
  const cls = frac == null ? 'progress indeterminate' : 'progress';
  return `<div class="${cls}"><span style="width:${frac == null ? 30 : 100 * frac}%"></span></div><span class="sub">${text}</span>`;
}

/** Szacowany czas do końca serii [ms]: szacunki zadań (heurystyka etapu 3) skalowane współczynnikiem
 *  „czas rzeczywisty / szacunek” z już policzonych zadań; bez szacunków — średni czas zadania. */
export function seriesEta(jobs, workers) {
  const done = jobs.filter((j) => j.status === 'done' && j.durationS != null);
  const pending = jobs.filter((j) => ACTIVE.has(j.status));
  if (!pending.length) return 0;
  const withEst = done.filter((j) => j.estimateMs > 0);
  const ratio = withEst.length
    ? withEst.reduce((s, j) => s + j.durationS * 1000, 0) / withEst.reduce((s, j) => s + j.estimateMs + PROCESS_OVERHEAD_MS, 0)
    : 1;
  const avg = done.length ? (done.reduce((s, j) => s + j.durationS, 0) / done.length) * 1000 : null;
  let remaining = 0;
  for (const j of pending) {
    let ms = j.estimateMs > 0 ? (j.estimateMs + PROCESS_OVERHEAD_MS) * ratio : avg;
    if (ms == null) return null;
    if (j.status === 'running') ms -= (elapsed(j) || 0) * 1000;
    remaining += Math.max(ms, 0);
  }
  return remaining / Math.max(1, Math.min(workers, pending.length));
}

export class JobsView {
  /** hooks: showResult(resultId), openCompare(seriesRef), onJobsFinished(), onUpdate(jobs) */
  constructor(hooks) {
    this.hooks = hooks;
    this.jobs = [];
    this.queue = null;
    this.openLogs = new Set();
    this.logs = new Map();
    this.collapsed = new Set();
    this.timer = null;
    $('#jobs-table').addEventListener('click', (ev) => this.onClick(ev));
    $('#jobs-filter').addEventListener('change', () => this.render());
    $('#jobs-group').addEventListener('change', () => this.render());
    $('#queue-pause').addEventListener('click', () => this.updateQueue({ paused: !this.queue?.paused }));
    $('#queue-workers').addEventListener('change', (e) => this.updateQueue({ workers: Number(e.target.value) }));
    $('#queue-pin').addEventListener('change', (e) => this.updateQueue({ pin: { enabled: e.target.checked } }));
  }

  async updateQueue(body) {
    try {
      this.queue = await postJSON('/api/queue', body);
    } catch (err) {
      $('#queue-warning').innerHTML = notice('error', esc(err.message));
    }
    this.renderQueue();
    this.refresh();
  }

  async refresh() {
    clearTimeout(this.timer);
    try {
      const prev = new Map(this.jobs.map((j) => [j.id, j.status]));
      const [jobs, queue] = await Promise.all([getJSON('/api/jobs'), getJSON('/api/queue')]);
      this.jobs = jobs;
      this.queue = queue;
      // Zadanie właśnie się skończyło — odśwież listę wyników (nowy folder w results/gui/).
      if (this.jobs.some((j) => prev.get(j.id) === 'running' && j.status !== 'running')) this.hooks.onJobsFinished?.();
      if (this.openLogs.size) await this.refreshLogs();
      this.renderQueue();
      this.render();
      this.hooks.onUpdate?.(this.jobs, this.queue);
    } catch { /* serwer chwilowo niedostępny — spróbujemy znowu */ }
    const active = this.jobs.some((j) => ACTIVE.has(j.status));
    this.timer = setTimeout(() => this.refresh(), active ? 1000 : 5000);
  }

  async refreshLogs() {
    await Promise.all([...this.openLogs].map(async (id) => {
      try { this.logs.set(id, (await getText(url(`/api/jobs/${encodeURIComponent(id)}/log`, { tail: 300 }))) || '(log pusty)'); } catch { /* pomijamy */ }
    }));
  }

  renderQueue() {
    const q = this.queue;
    if (!q) return;
    const queued = this.jobs.filter((j) => j.status === 'queued').length;
    const running = this.jobs.filter((j) => j.status === 'running').length;
    const st = $('#queue-status');
    st.className = `queue-status ${q.paused ? 'paused' : 'running'}`;
    st.innerHTML = q.paused
      ? `<b>Kolejka wstrzymana</b> · ${queued} oczekuje${running ? ` · ${running} kończy się` : ''}`
      : `<b>Kolejka działa</b> · ${queued} oczekuje · ${running} działa`;
    $('#queue-pause').textContent = q.paused ? 'Wznów kolejkę' : 'Wstrzymaj kolejkę';
    const sel = $('#queue-workers');
    if (sel.options.length !== q.maxWorkers) {
      sel.innerHTML = Array.from({ length: q.maxWorkers }, (_, i) => `<option value="${i + 1}">${i + 1}${i === 0 ? ' (po kolei)' : ''}</option>`).join('');
    }
    sel.value = String(q.workers);
    $('#queue-pin').checked = !!q.pin?.enabled;
    const cpus = (q.pin?.cpus || []).slice(0, q.workers);
    $('#queue-pin-cpus').textContent = `procesor logiczny ${cpus.join(', ')}`;
    let warn = '';
    if (q.workers > 1) {
      warn += notice('warn', `${q.workers} równoległe workery: zadania liczą się jednocześnie i <b>zaburzają pomiary czasu</b> (wspólna
        pamięć podręczna L3, pasmo pamięci, limit mocy procesora). Do porównań czasów (np. CA vs MC) ustaw 1 worker.`);
    }
    if (q.pin?.enabled && q.platform !== 'win32') warn += notice('info', 'Na Linuksie przypięcie działa (sched_setaffinity), ale priorytet procesu się nie zmienia.');
    $('#queue-warning').innerHTML = warn;
  }

  jobRow(job, inGroup) {
    const s = job.summary || {};
    const t = elapsed(job);
    const mode = String(s.mode || '');
    const params = `${esc(mode)} · ${(s.space || []).join('×')}<br><span class="sub">${esc(s.neighborhood || '')}, ${esc(s.boundary || '')}`
      + `${s.vents && !mode.startsWith('mc_full') ? `, ${mode.startsWith('classic') ? plural(s.vents, 'ziarno', 'ziarna', 'ziaren') : plural(s.vents, 'krater', 'kratery', 'kraterów')}` : ''}`
      + `${s.mcs != null ? `, ${s.mcs} MCS` : ''}</span>`;
    const active = ACTIVE.has(job.status);
    const title = inGroup ? `<b>${esc(job.id.split('__').pop())}</b>` : `<b>${esc(job.name)}</b><br><span class="sub mono">${esc(job.id)}</span>`;
    const est = job.estimateMs != null && job.status !== 'done' ? `<br><span class="sub">szac. ~${fmtTime(job.estimateMs)}</span>` : '';
    return `<tr data-job="${esc(job.id)}" class="${inGroup ? 'in-group' : ''}">
      <td>${title}${job.pinnedCpu != null ? `<br><span class="sub">CPU ${job.pinnedCpu}</span>` : ''}</td>
      <td><span class="status ${job.status}"><span class="icon">${STATUS_ICON[job.status] ? icon(STATUS_ICON[job.status]) : ''}</span>${esc(job.statusLabel)}</span>
        ${job.exitCode != null && job.exitCode !== 0 ? `<br><span class="sub">kod ${job.exitCode}</span>` : ''}</td>
      <td>${progressHTML(job)}</td>
      <td class="num nowrap">${t != null ? fmtTime(t * 1000) : '—'}${est}</td>
      <td>${params}</td>
      <td><span class="sub mono">${inGroup
        ? `${esc(job.configPath.split('/').pop())}<br>${esc(job.outDir.split('/').pop())}/`
        : `${esc(job.configPath)}<br>${esc(job.outDir)}/`}</span></td>
      <td class="row-actions">
        ${job.status === 'queued' ? `<button class="btn btn-small" data-act="up" title="Wyżej w kolejce" aria-label="Wyżej w kolejce">${icon('up')}</button><button class="btn btn-small" data-act="down" title="Niżej w kolejce" aria-label="Niżej w kolejce">${icon('down')}</button>` : ''}
        <button class="btn btn-small" data-act="log">${this.openLogs.has(job.id) ? 'Ukryj log' : 'Log'}</button>
        ${active ? '<button class="btn btn-small btn-danger" data-act="cancel">Anuluj</button>' : ''}
        ${RETRYABLE.has(job.status) ? '<button class="btn btn-small" data-act="retry">Ponów</button>' : ''}
        ${job.status === 'done' ? '<button class="btn btn-small" data-act="show">Pokaż wynik</button>' : ''}
      </td></tr>
      ${this.openLogs.has(job.id) ? `<tr class="log-row" data-log="${esc(job.id)}"><td colspan="7"><pre>${esc(this.logs.get(job.id) ?? 'wczytywanie…')}</pre></td></tr>` : ''}`;
  }

  groupRow(sid, jobs) {
    const total = jobs.length;
    const c = (st) => jobs.filter((j) => j.status === st).length;
    const done = c('done'), running = c('running'), queued = c('queued'), failed = c('error') + c('interrupted'), cancelled = c('cancelled');
    const finished = done + failed + cancelled;
    const time = jobs.reduce((s, j) => s + (elapsed(j) || 0), 0);
    const eta = seriesEta(jobs, this.queue?.workers || 1);
    const parts = [`<b>${done} z ${total}</b> gotowe`];
    if (running) parts.push(`${running} działa`);
    if (queued) parts.push(`${queued} oczekuje`);
    if (failed) parts.push(`${failed} błąd`);
    if (cancelled) parts.push(`${cancelled} anulowane`);
    const etaText = queued + running === 0 ? 'zakończona' : eta == null ? 'do końca: —' : `do końca ~${fmtTime(eta)}`;
    const open = !this.collapsed.has(sid);
    const anyActive = queued + running > 0;
    return `<tr class="group-row" data-series="${esc(sid)}"><td colspan="7"><div class="group-head">
      <button class="btn btn-small btn-ghost toggle-btn${open ? ' open' : ''}" data-act="toggle" title="Zwiń / rozwiń" aria-label="Zwiń / rozwiń serię" aria-expanded="${open}">${icon('right')}</button>
      <span><b>Seria: ${esc(jobs[0].seriesName || sid)}</b><br><span class="sub mono" title="pliki configów i foldery wyników serii">
        ${esc(jobs[0].configPath.split('/').slice(0, -1).join('/'))}/ → ${esc(jobs[0].outDir.split('/').slice(0, -1).join('/'))}/</span></span>
      <span class="group-progress"><span class="progress ${finished === total && failed === 0 && cancelled === 0 ? 'done' : ''}"><span style="width:${(100 * finished) / total}%"></span></span></span>
      <span class="sub">${parts.join(' · ')} · czas ${fmtTime(time * 1000)} · ${etaText}</span>
      <span class="row-actions">
        <button class="btn btn-small" data-act="compare">Porównanie</button>
        ${anyActive ? '<button class="btn btn-small btn-danger" data-act="cancel-series">Anuluj serię</button>' : ''}
      </span></div></td></tr>`;
  }

  render() {
    const filter = $('#jobs-filter').value;
    const group = $('#jobs-group').checked;
    const pass = (j) => !filter || (filter === 'active' ? ACTIVE.has(j.status) : j.status === filter);
    const rows = [];
    const seen = new Set();
    for (const job of this.jobs) {
      if (group && job.seriesId) {
        if (seen.has(job.seriesId)) continue;
        seen.add(job.seriesId);
        const members = this.jobs.filter((j) => j.seriesId === job.seriesId).sort((a, b) => (a.seriesIndex || 0) - (b.seriesIndex || 0));
        const visible = members.filter(pass);
        if (!visible.length) continue;
        rows.push(this.groupRow(job.seriesId, members));
        if (!this.collapsed.has(job.seriesId)) visible.forEach((j) => rows.push(this.jobRow(j, true)));
      } else if (pass(job)) {
        rows.push(this.jobRow(job, false));
      }
    }
    $('#jobs-table tbody').innerHTML = rows.join('');
    $('#jobs-empty').hidden = rows.length > 0;
    const active = this.jobs.filter((j) => ACTIVE.has(j.status)).length;
    const badge = $('#jobs-badge');
    badge.hidden = active === 0;
    badge.textContent = active;
  }

  async onClick(ev) {
    const btn = ev.target.closest('button[data-act]');
    if (!btn) return;
    const act = btn.dataset.act;
    const groupRow = btn.closest('tr.group-row');
    if (groupRow) {
      const sid = groupRow.dataset.series;
      if (act === 'toggle') {
        if (this.collapsed.has(sid)) this.collapsed.delete(sid); else this.collapsed.add(sid);
        this.render();
      } else if (act === 'cancel-series') {
        if (!window.confirm('Anulować wszystkie oczekujące i działające zadania tej serii?')) return;
        await postJSON(`/api/series/${encodeURIComponent(sid)}/cancel`, {});
        this.refresh();
      } else if (act === 'compare') {
        this.hooks.openCompare?.(`gui/series/${sid}`);
      }
      return;
    }
    const id = btn.closest('tr').dataset.job;
    try {
      if (act === 'log') {
        if (this.openLogs.has(id)) this.openLogs.delete(id); else { this.openLogs.add(id); await this.refreshLogs(); }
        this.render();
        return;
      }
      if (act === 'cancel') await postJSON(`/api/jobs/${encodeURIComponent(id)}/cancel`, {});
      else if (act === 'retry') await postJSON(`/api/jobs/${encodeURIComponent(id)}/retry`, {});
      else if (act === 'up' || act === 'down') await postJSON(`/api/jobs/${encodeURIComponent(id)}/move`, { direction: act });
      else if (act === 'show') {
        const job = this.jobs.find((j) => j.id === id);
        await this.hooks.showResult?.(job.resultId);
        return;
      }
    } catch (err) {
      $('#queue-warning').innerHTML = notice('error', esc(err.message));
    }
    this.refresh();
  }
}
