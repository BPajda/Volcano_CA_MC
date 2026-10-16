// Podgląd 2D: przekrój wyniku (oś x / y / z, suwak warstwy) na canvasie.
// Dane: dwa przekroje z backendu jako surowe bajty — typ komórki i wybrane pole; kolorowanie tutaj.
// Zoom kółkiem wokół kursora, przesuwanie przeciąganiem, piksele ostre (bez wygładzania).
// Granice ziaren (flowId, crystal): przy dużym powiększeniu linie między komórkami, przy małym —
// przyciemnione komórki graniczne (linie byłyby gęstsze niż piksele ekranu).
// Etap 6: odtwarzanie erupcji (suwak czasu nad przekrojem, replay.js) — przekroje typ / pojawienie / zastygnięcie /
// temperatura / flowId pobierane raz na płaszczyznę, stan w kroku k liczony w przeglądarce; krystalizacja MC —
// przekroje kryształów z migawek (mcs=<k>).
// Etap 7: tło, ramka, granice ziaren, podpisy osi i eksport biorą kolory z motywu (theme.js); po zmianie motywu
// przekrój jest kolorowany od nowa (powietrze i skała mają wariant ciemny / jasny — palette.js).

import { getBinary, getJSON, typed, url } from './api.js';
import {
  AIR, BASALT, LAVA, TYPE_NAMES, TYPE_RGB, colorize, drawLegend, hasGrains, legendFor, showLegend, toHex, FIELD_LABELS,
} from './palette.js';
import {
  ReplayBar, colorizeReplay, exportFrames, flowCountOf, frameTitle, recordWebM, replayLegend, tempAt,
} from './replay.js';
import { onThemeChange, themeColors } from './theme.js';
import { rangeFill, setText } from './util.js';

const LINE_ZOOM = 5;  // od tylu pikseli ekranu na komórkę granice ziaren są liniami

export class Viewer2D {
  constructor(el) {
    this.el = el;  // { wrap, canvas, tooltip, loading, legend, status, field, axisRadios, index, indexNum, indexMax, boundaries, fit, png }
    this.meta = null;
    this.field = 'type';
    this.axis = 'y';
    this.index = 0;
    this.cache = new Map();
    this.view = { scale: 1, ox: 0, oy: 0 };
    this.img = null;  // { w, h, type, values, canvas, canvasDark, axis, index, step }
    this.cellReq = 0;
    this.rp = null;   // dane odtwarzania bieżącej płaszczyzny
    this.replay = new ReplayBar(el.replay, {
      onFrame: (k) => this.drawReplay(k),
      onToggle: () => this.load(),
      onSource: () => { this.replay.syncRange(); this.load(); },
    });
    el.replay.frames.addEventListener('click', () => this.exportReplay('frames'));
    el.replay.webm.addEventListener('click', () => this.exportReplay('webm'));
    this.bind();
    new ResizeObserver(() => this.render()).observe(el.wrap);
    onThemeChange(() => { if (this.meta) this.load(); else this.render(); });
  }

  bind() {
    const e = this.el;
    e.field.addEventListener('change', () => { this.field = e.field.value; this.syncControls(); this.load(); });
    e.axisRadios.forEach((r) => r.addEventListener('change', () => {
      if (!r.checked) return;
      this.axis = r.value;
      this.index = Math.floor((this.axisSize() - 1) / 2);
      this.syncControls(); this.load(true);
    }));
    const setIndex = (v) => {
      this.index = Math.max(0, Math.min(this.axisSize() - 1, Number(v) || 0));
      e.index.value = this.index; e.indexNum.value = this.index;
      rangeFill(e.index);
      this.load();
    };
    e.index.addEventListener('input', () => setIndex(e.index.value));
    e.indexNum.addEventListener('change', () => setIndex(e.indexNum.value));
    e.boundaries.addEventListener('change', () => this.render());
    e.fit.addEventListener('click', () => { this.fit(); this.render(); });
    e.png.addEventListener('click', () => this.exportPNG());

    const c = e.canvas;
    c.addEventListener('wheel', (ev) => {
      ev.preventDefault();
      if (!this.img) return;
      const { x, y } = this.mouse(ev);
      const f = Math.exp(-ev.deltaY * 0.0015);
      const s = Math.min(200, Math.max(0.05, this.view.scale * f));
      this.view.ox = x - (x - this.view.ox) * (s / this.view.scale);
      this.view.oy = y - (y - this.view.oy) * (s / this.view.scale);
      this.view.scale = s;
      this.render();
    }, { passive: false });
    let drag = null;
    c.addEventListener('mousedown', (ev) => { drag = { ...this.mouse(ev), ox: this.view.ox, oy: this.view.oy }; e.wrap.classList.add('panning'); });
    window.addEventListener('mouseup', () => { drag = null; e.wrap.classList.remove('panning'); });
    c.addEventListener('mousemove', (ev) => {
      const m = this.mouse(ev);
      if (drag) {
        this.view.ox = drag.ox + m.x - drag.x; this.view.oy = drag.oy + m.y - drag.y;
        this.render(); e.tooltip.hidden = true; return;
      }
      this.hover(m);
    });
    c.addEventListener('mouseleave', () => { e.tooltip.hidden = true; });
    c.addEventListener('dblclick', () => { this.fit(); this.render(); });
  }

  mouse(ev) {
    const r = this.el.canvas.getBoundingClientRect();
    return { x: ev.clientX - r.left, y: ev.clientY - r.top };
  }

  axisSize() {
    const [nx, ny, nz] = this.meta.dims;
    return { x: nx, y: ny, z: nz }[this.axis];
  }

  /** Nowy wynik: domyślna płaszczyzna (2D — jedyna sensowna), środek osi, pole „typ”. */
  setResult(meta) {
    const keepField = this.meta && meta.fields.includes(this.field) && this.meta.id === meta.id;
    const prevId = this.meta?.id;
    this.meta = meta;
    if (!keepField) this.field = meta.fields.includes('crystal') && meta.mode === 'mc_full' ? 'crystal' : 'type';
    if (prevId !== meta.id) {
      this.axis = meta.planeAxis || 'y';
      this.index = meta.planeAxis ? 0 : Math.floor((this.axisSize() - 1) / 2);
      this.cache.clear();
      this.img = null;
      // Podpowiedź opisuje komórkę poprzedniego wyniku — chowamy ją i unieważniamy spóźnione /api/result/cell.
      this.el.tooltip.hidden = true;
      this.cellReq++;
    }
    const f = this.el.field;
    f.innerHTML = '';
    for (const name of meta.fields) f.add(new Option(FIELD_LABELS[name], name));
    f.value = this.field;
    if (prevId !== meta.id) { this.replay.setResult(meta); this.rp = null; }
    this.syncControls();
    return this.load(prevId !== meta.id);
  }

  syncControls() {
    const e = this.el, m = this.meta;
    e.axisRadios.forEach((r) => {
      r.checked = r.value === this.axis;
      r.disabled = !!m.planeAxis;  // 2D: przekrój tylko w płaszczyźnie siatki
    });
    const max = this.axisSize() - 1;
    e.index.max = max; e.indexNum.max = max;
    e.index.value = this.index; e.indexNum.value = this.index;
    rangeFill(e.index);
    e.index.disabled = e.indexNum.disabled = max === 0;
    e.indexMax.textContent = `/ ${max}`;
    e.boundaries.disabled = !hasGrains(this.field) || this.replay.on;
    e.field.disabled = this.replay.on;  // w odtwarzaniu kolor wybiera pasek odtwarzania (żar / krater / kryształy)
  }

  async fetchSlice(field, mcs = undefined) {
    const key = `${this.meta.id}|${field}|${this.axis}|${this.index}|${mcs ?? ''}`;
    if (this.cache.has(key)) return this.cache.get(key);
    const { meta, buffer } = await getBinary(url('/api/result/slice', { id: this.meta.id, field, axis: this.axis, index: this.index, mcs }));
    const data = { meta, arr: typed(meta.dtype, buffer) };
    this.cache.set(key, data);
    if (this.cache.size > 40) this.cache.delete(this.cache.keys().next().value);
    return data;
  }

  async load(refit = false) {
    if (!this.meta) return;
    const token = (this.loadToken = (this.loadToken || 0) + 1);
    const slow = setTimeout(() => { this.el.loading.hidden = false; }, 150);
    this.syncControls();
    try {
      if (this.replay.on) {
        await this.loadReplay(token, refit);
        return;
      }
      const [t, v] = await Promise.all([this.fetchSlice('type'), this.field === 'type' ? null : this.fetchSlice(this.field)]);
      if (token !== this.loadToken) return;  // w międzyczasie przesunięto suwak
      const { width: w, height: h, step } = t.meta;
      const ctx = { ranges: this.meta.ranges };
      const rgba = colorize(w, h, t.arr, v ? v.arr : null, this.field, ctx);
      const prev = this.img;
      this.img = { w, h, step, type: t.arr, values: v ? v.arr : null, field: this.field, axis: this.axis, index: this.index,
        hAxis: t.meta.hAxis, vAxis: t.meta.vAxis, canvas: toCanvas(rgba, w, h), canvasDark: null };
      if (hasGrains(this.field)) this.img.canvasDark = toCanvas(darkenBoundaries(rgba, w, h, v.arr), w, h);
      if (refit || !prev || prev.w !== w || prev.h !== h) this.fit();
      this.updateLegend();
      this.render();
      const [nx, ny, nz] = this.meta.dims;
      this.el.status.textContent = `${this.planeName()} · oś pozioma ${this.img.hAxis}, pionowa ${this.img.vAxis}`
        + (step > 1 ? ` · próbkowanie co ${step} komórek (przekrój > 4 mln komórek)` : '')
        + ` · blok ${nx}×${ny}×${nz} · kółko — powiększenie, przeciąganie — przesuwanie, dwuklik — dopasuj`;
    } catch (err) {
      this.el.status.textContent = `Błąd: ${err.message}`;
    } finally {
      clearTimeout(slow);
      if (token === this.loadToken) this.el.loading.hidden = true;
    }
  }

  planeName() {
    return this.axis === 'z' ? `warstwa z = ${this.index}` : `przekrój ${this.axis} = ${this.index}`;
  }

  // ------------------------------------------------------------ odtwarzanie erupcji (etap 6)

  /** Dane odtwarzania bieżącej płaszczyzny (CA: 5 przekrojów pobranych raz; MC: kryształy z migawek). */
  async loadReplay(token, refit) {
    const bar = this.replay;
    if (bar.source === 'ca') {
      if (!bar.info || bar.info.id !== this.meta.id) {
        const info = await getJSON(url('/api/result/replay', { id: this.meta.id }));
        if (token !== this.loadToken) return;
        info.flowCount = flowCountOf(info);
        bar.setInfo(info);
      }
      const parts = await Promise.all(['type', 'appear', 'solidFrom', 'temp', 'flowId'].map((f) => this.fetchSlice(f)));
      if (token !== this.loadToken) return;
      const [t, a, s, tp, f] = parts;
      this.rp = { w: t.meta.width, h: t.meta.height, step: t.meta.step, hAxis: t.meta.hAxis, vAxis: t.meta.vAxis,
        type: t.arr, appear: a.arr, solidFrom: s.arr, temp: tp.arr, flowId: f.arr };
    } else {
      bar.syncRange();
      this.rp = null;
    }
    await this.drawReplay(bar.k, refit);
  }

  /** Klatka odtwarzania: krok k (CA) albo indeks migawki k (MC). */
  async drawReplay(k, refit = false) {
    if (!this.meta || !this.replay.on) return;
    const bar = this.replay;
    const prev = this.img;
    let rgba, w, h, step, hAxis, vAxis, states, values = null, field;
    if (bar.source === 'ca') {
      const d = this.rp;
      if (!d || !bar.info) return;
      ({ w, h, step, hAxis, vAxis } = d);
      states = new Uint8Array(w * h);
      const r = colorizeReplay(w, h, d, k, bar.info, bar.mode, true, null, states);
      rgba = r.rgba;
      field = 'replay';
      this.legend = replayLegend(bar.info, bar.mode);
      bar.label(` · w przekroju: ${r.liquid.toLocaleString('pl-PL')} / ${r.solid.toLocaleString('pl-PL')}`);
    } else {
      const mcs = bar.mcs[k];
      const [t, c] = await Promise.all([this.fetchSlice('type'), this.fetchSlice('crystal', mcs)]);
      if (!this.replay.on || bar.source !== 'mc') return;
      ({ width: w, height: h, step, hAxis, vAxis } = t.meta);
      rgba = colorize(w, h, t.arr, c.arr, 'crystal', { ranges: this.meta.ranges });
      states = t.arr;
      values = c.arr;
      field = 'crystal';
      this.legend = legendFor('crystal', this.meta, new Set(t.arr));
      this.legend.title = `Kryształ (MC) — MCS ${mcs}`;
    }
    this.img = { w, h, step, type: states, values, field, axis: this.axis, index: this.index, hAxis, vAxis,
      canvas: toCanvas(rgba, w, h), canvasDark: null, replayK: k };
    if (refit || !prev || prev.w !== w || prev.h !== h) this.fit();
    showLegend(this.el.legend, this.legend);
    this.render();
    const [nx, ny, nz] = this.meta.dims;
    setText(this.el.status, `Odtwarzanie ${bar.source === 'ca' ? 'erupcji' : 'krystalizacji MC'} · ${this.planeName()}`
      + ` · oś pozioma ${hAxis}, pionowa ${vAxis}` + (step > 1 ? ` · próbkowanie co ${step}` : '')
      + ` · blok ${nx}×${ny}×${nz}` + (bar.source === 'ca' && bar.info && !bar.info.ventsExact
        ? ' · kratery nieznane (stats.json) — komórki z arrivalStep = 0 już w kroku 0' : ''));
  }

  /** Eksport odtwarzania: klatki PNG (ZIP) albo film WebM — kadr jak w „Eksport PNG” (widok + legenda). */
  async exportReplay(kind) {
    if (!this.img || !this.replay.on) return;
    const bar = this.replay;
    const r = this.el.wrap.getBoundingClientRect();
    const legendW = 240, head = 34;
    const out = document.createElement('canvas');
    out.width = Math.round(r.width) + legendW;
    out.height = Math.max(Math.round(r.height), 300) + head;
    const view = { ...this.view };
    const draw = async (k, canvas) => {
      await this.drawReplay(k);
      const g = canvas.getContext('2d'), th = themeColors();
      g.fillStyle = th.panel; g.fillRect(0, 0, canvas.width, canvas.height);
      const label = bar.source === 'ca' ? `krok ${k} / ${bar.info.steps}` : `MCS ${bar.mcs[k]}`;
      frameTitle(g, `${this.meta.name}: ${this.planeName()} — ${label}`);
      g.save();
      g.translate(0, head);
      g.beginPath(); g.rect(0, 0, r.width, r.height); g.clip();
      g.fillStyle = th.viewBg; g.fillRect(0, 0, r.width, r.height);
      this.draw(g, view, r.width, r.height);
      g.restore();
      drawLegend(g, this.legend, r.width + 16, head + 8, legendW - 28);
    };
    const base = `${this.meta.name}_${this.axis}${this.index}_${bar.source === 'ca' ? 'erupcja' : 'mc'}`.replace(/[^\w.-]+/g, '_');
    const k0 = bar.k;
    try {
      if (kind === 'frames') await exportFrames(bar, out, draw, base);
      else await recordWebM(bar, out, draw, base);
    } finally {
      await bar.go(k0);
    }
  }

  updateLegend() {
    const present = new Set(this.img.type);
    this.legend = legendFor(this.field, this.meta, present);
    showLegend(this.el.legend, this.legend);
  }

  fit() {
    if (!this.img) return;
    const r = this.el.wrap.getBoundingClientRect();
    const pad = 16;
    const s = Math.min((r.width - 2 * pad) / this.img.w, (r.height - 2 * pad) / this.img.h);
    this.view.scale = Math.max(0.05, s);
    this.view.ox = (r.width - this.img.w * this.view.scale) / 2;
    this.view.oy = (r.height - this.img.h * this.view.scale) / 2;
  }

  render() {
    const c = this.el.canvas, r = this.el.wrap.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    if (c.width !== Math.round(r.width * dpr) || c.height !== Math.round(r.height * dpr)) {
      c.width = Math.round(r.width * dpr); c.height = Math.round(r.height * dpr);
    }
    const g = c.getContext('2d');
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.fillStyle = themeColors().viewBg;
    g.fillRect(0, 0, r.width, r.height);
    if (!this.img) return;
    this.draw(g, this.view, r.width, r.height);
  }

  /** Rysuje przekrój z transformacją view; używane też przy eksporcie PNG. */
  draw(g, view, width, height) {
    const { img } = this;
    const { scale, ox, oy } = view;
    const lines = this.el.boundaries.checked && hasGrains(img.field) && img.replayK === undefined;
    g.imageSmoothingEnabled = false;
    const src = lines && scale < LINE_ZOOM && img.canvasDark ? img.canvasDark : img.canvas;
    g.drawImage(src, ox, oy, img.w * scale, img.h * scale);
    g.strokeStyle = themeColors().viewFrame;
    g.lineWidth = 1;
    g.strokeRect(Math.round(ox) - 0.5, Math.round(oy) - 0.5, Math.round(img.w * scale) + 1, Math.round(img.h * scale) + 1);
    if (lines && scale >= LINE_ZOOM) this.drawBoundaries(g, view, width, height);
    this.drawAxes(g, view, height);
  }

  drawBoundaries(g, { scale, ox, oy }, width, height) {
    const { w, h, values: v } = this.img;
    const c0 = Math.max(0, Math.floor(-ox / scale)), c1 = Math.min(w - 1, Math.ceil((width - ox) / scale));
    const rTop = Math.max(0, Math.floor(-oy / scale)), rBot = Math.min(h - 1, Math.ceil((height - oy) / scale));
    g.beginPath();
    for (let ri = rTop; ri <= rBot; ri++) {
      const row = h - 1 - ri;  // wiersz danych (0 = dół)
      for (let col = c0; col <= c1; col++) {
        const a = v[row * w + col];
        if (col + 1 < w) {
          const b = v[row * w + col + 1];
          if (a !== b && (a > 0 || b > 0)) { const x = ox + (col + 1) * scale; g.moveTo(x, oy + ri * scale); g.lineTo(x, oy + (ri + 1) * scale); }
        }
        if (row + 1 < h) {
          const b = v[(row + 1) * w + col];
          if (a !== b && (a > 0 || b > 0)) { const y = oy + ri * scale; g.moveTo(ox + col * scale, y); g.lineTo(ox + (col + 1) * scale, y); }
        }
      }
    }
    g.strokeStyle = themeColors().grainLine;
    g.lineWidth = Math.min(2, Math.max(1, scale / 12));
    g.stroke();
  }

  drawAxes(g, { scale, ox, oy }, height) {
    const { w, h, hAxis, vAxis, step } = this.img;
    const th = themeColors();
    g.font = `12px ${th.font}`;
    g.fillStyle = th.viewInk;
    const bottom = Math.min(height - 4, oy + h * scale + 16);
    g.textBaseline = 'alphabetic';
    g.fillText(`${hAxis} → (0…${(w - 1) * step})`, Math.max(4, ox), bottom);
    g.save();
    g.translate(Math.max(14, ox - 6), oy + h * scale);
    g.rotate(-Math.PI / 2);
    g.fillText(`${vAxis} → (0…${(h - 1) * step})`, 0, 0);
    g.restore();
  }

  /** Komórka pod kursorem -> współrzędne (x, y, z) bloku. */
  cellAt(m) {
    const { img, view } = this;
    if (!img) return null;
    const col = Math.floor((m.x - view.ox) / view.scale), ri = Math.floor((m.y - view.oy) / view.scale);
    if (col < 0 || col >= img.w || ri < 0 || ri >= img.h) return null;
    const row = img.h - 1 - ri;
    const a = col * img.step, b = row * img.step;
    const xyz = img.axis === 'x' ? [img.index, a, b] : img.axis === 'y' ? [a, img.index, b] : [a, b, img.index];
    return { col, row, xyz, i: row * img.w + col };
  }

  hover(m) {
    const tt = this.el.tooltip, cell = this.cellAt(m);
    if (!cell) { tt.hidden = true; return; }
    const { img } = this;
    const [x, y, z] = cell.xyz;
    if (img.replayK !== undefined && this.replay.source === 'ca' && this.rp) {
      this.hoverReplay(tt, m, cell, x, y, z);
      return;
    }
    const t = img.type[cell.i];
    let rows = `<tr><td>typ</td><td>${typeLabel(t)}</td></tr>`;
    if (img.values) rows += `<tr><td>${FIELD_LABELS[img.field].toLowerCase()}</td><td>${fmtVal(img.field, img.values[cell.i])}</td></tr>`;
    tt.innerHTML = `<div class="tt-head">x ${x} · y ${y} · z ${z}</div><table>${rows}</table>`;
    this.placeTooltip(tt, m);
    // Pozostałe pola komórki (flowId, temp, kryształ…) z backendu, z opóźnieniem — bez zalewania serwera.
    const req = ++this.cellReq;
    clearTimeout(this.cellTimer);
    this.cellTimer = setTimeout(async () => {
      try {
        const c = await getJSON(url('/api/result/cell', { id: this.meta.id, x, y, z }));
        if (req !== this.cellReq || tt.hidden) return;
        let html = `<div class="tt-head">x ${x} · y ${y} · z ${z}</div><table>`;
        html += `<tr><td>typ</td><td>${typeLabel(c.type)}</td></tr>`;
        if ('flowId' in c) html += `<tr><td>flowId</td><td>${c.flowId || '—'}</td></tr>`;
        if ('temp' in c) html += `<tr><td>temp</td><td>${c.type === LAVA || c.type === BASALT ? `${c.temp.toFixed(1)} °C` : '—'}</td></tr>`;
        if ('crystal' in c) html += `<tr><td>kryształ</td><td>${c.crystal || '—'}</td></tr>`;
        if ('cooling' in c) html += `<tr><td>czas stygnięcia</td><td>${c.type === LAVA || c.type === BASALT ? `${c.cooling} kroków` : '—'}</td></tr>`;
        tt.innerHTML = `${html}</table>`;
      } catch { /* podpowiedź jest pomocnicza — błąd pomijamy */ }
    }, 90);
  }

  /** Podpowiedź w odtwarzaniu: stan komórki w kroku k (bez zapytania do backendu). */
  hoverReplay(tt, m, cell, x, y, z) {
    const d = this.rp, i = cell.i, k = this.img.replayK, info = this.replay.info;
    const s = this.img.type[i], t = d.type[i];
    let rows = `<tr><td>krok ${k}</td><td>${typeLabel(s)}</td></tr>`;
    if (s === LAVA) rows += `<tr><td>temp</td><td>${tempAt(k, t, d.temp[i], d.solidFrom[i], info.steps, info.params).toFixed(0)} °C</td></tr>`;
    if (t === LAVA || t === BASALT) {
      rows += `<tr><td>lawa od kroku</td><td>${d.appear[i]}</td></tr>`;
      rows += `<tr><td>zastygła w kroku</td><td>${t === BASALT ? d.solidFrom[i] : '— (płynna do końca)'}</td></tr>`;
      if (s !== AIR) rows += `<tr><td>flowId</td><td>${d.flowId[i]}</td></tr>`;
    }
    tt.innerHTML = `<div class="tt-head">x ${x} · y ${y} · z ${z}</div><table>${rows}</table>`;
    this.placeTooltip(tt, m);
  }

  placeTooltip(tt, m) {
    tt.hidden = false;
    const r = this.el.wrap.getBoundingClientRect();
    const x = m.x + 16 + tt.offsetWidth > r.width ? m.x - 12 - tt.offsetWidth : m.x + 16;
    const y = m.y + 16 + tt.offsetHeight > r.height ? m.y - 12 - tt.offsetHeight : m.y + 16;
    tt.style.left = `${x}px`; tt.style.top = `${y}px`;
  }

  /** Eksport aktualnego widoku (z powiększeniem i przesunięciem) + tytuł + legenda do PNG. */
  exportPNG() {
    if (!this.img) return;
    const r = this.el.wrap.getBoundingClientRect();
    const scale = 2, legendW = 240, head = 34;
    const W = Math.round(r.width) + legendW, H = Math.max(Math.round(r.height), 300) + head;
    const out = document.createElement('canvas');
    out.width = W * scale; out.height = H * scale;
    const g = out.getContext('2d'), th = themeColors();
    g.scale(scale, scale);
    g.fillStyle = th.panel; g.fillRect(0, 0, W, H);  // eksport w kolorach bieżącego motywu (jasny — do druku)
    g.fillStyle = th.ink; g.font = `600 14px ${th.font}`; g.textBaseline = 'top';
    const [nx, ny, nz] = this.meta.dims;
    g.fillText(`${this.meta.name}: ${this.planeName()} (${nx}×${ny}×${nz}), kolor: ${FIELD_LABELS[this.field]}`, 12, 10);
    g.save();
    g.translate(0, head);
    g.beginPath(); g.rect(0, 0, r.width, r.height); g.clip();
    g.fillStyle = th.viewBg; g.fillRect(0, 0, r.width, r.height);
    this.draw(g, this.view, r.width, r.height);
    g.restore();
    drawLegend(g, this.legend, r.width + 16, head + 8, legendW - 28);
    download(out, `${this.meta.name}_${this.axis}${this.index}_${this.field}.png`);
  }
}

/** Typ komórki w podpowiedzi: próbka koloru z palety + nazwa. */
function typeLabel(t) {
  const rgb = TYPE_RGB[t];
  return `${rgb ? `<span class="sw" style="background:${toHex(rgb)}"></span>` : ''}${TYPE_NAMES[t] ?? t}`;
}

function fmtVal(field, v) {
  if (field === 'temp') return `${v.toFixed(1)} °C`;
  if (field === 'cooling') return `${v} kroków`;
  return v === 0 ? '—' : String(v);
}

function toCanvas(rgba, w, h) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  c.getContext('2d').putImageData(new ImageData(rgba, w, h), 0, 0);
  return c;
}

/** Kopia obrazu z przyciemnionymi komórkami na granicy ziaren (sąsiad w prawo / w górę ma inne ID). */
function darkenBoundaries(rgba, w, h, v) {
  const out = new Uint8ClampedArray(rgba);
  const mark = (row, col) => {
    const o = ((h - 1 - row) * w + col) * 4;
    out[o] *= 0.45; out[o + 1] *= 0.45; out[o + 2] *= 0.45;
  };
  for (let row = 0; row < h; row++) {
    for (let col = 0; col < w; col++) {
      const a = v[row * w + col];
      if (col + 1 < w) { const b = v[row * w + col + 1]; if (a !== b && a > 0 && b > 0) mark(row, col); }
      if (row + 1 < h) { const b = v[(row + 1) * w + col]; if (a !== b && a > 0 && b > 0) mark(row, col); }
    }
  }
  return out;
}

export function download(canvas, name) {
  const a = document.createElement('a');
  a.download = name.replace(/[^\w.-]+/g, '_');
  a.href = canvas.toDataURL('image/png');
  a.click();
}

