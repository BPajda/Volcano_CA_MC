// Odtwarzanie erupcji krok po kroku (etap 6) — wspólne dla podglądu 2D i 3D.
//
// Stan komórki w kroku k (k = 0 … steps; stan k = po k krokach CA) liczy przeglądarka z tablic pobranych raz
// (bez zapytania do backendu na klatkę) — ta sama reguła co gui/replay.py i test engine/tests/test_replay.cpp:
//   skała -> skała; komórka, która nigdy nie była lawą -> powietrze;
//   k < appear -> powietrze (appear = 0 dla krateru, arrivalStep + 1 dla reszty);
//   k >= solidFrom -> bazalt (solidFrom = solidStep + 1); inaczej płynna lawa.
// Temperatura płynnej lawy w kroku k: po przybyciu lawa traci dokładnie coolingAmbient na krok (krater w trakcie
// erupcji ma stałe eruptTemp), więc liczymy ją wstecz od temperatury końcowej (dokładnie, z błędem zaokrągleń):
//   T_k = min(eruptTemp, T_końc + coolingAmbient · (koniec − k)), koniec = solidFrom (bazalt) albo steps (lawa).
// Paleta „żar” (palette.js, GLOW): świeża lawa jasnożółta → pomarańcz → ciemniejąca czerwień przy temperaturze
// zastygania; bazalt — grafit jak w widoku „typ komórki”. Tryb „krater”: kolor flowId (rozrost ziaren w trybie classic).
// Odtwarzanie krystalizacji MC: suwak po migawkach mc_snapshots/mcs_<k>.bin (kryształy z backendu).
// Eksport: sekwencja klatek PNG w pliku ZIP (bez kompresji — PNG i tak jest skompresowany) albo film WebM
// (MediaRecorder na canvasie).

import { AIR, BASALT, GLOW, LAVA, ROCK, TYPE_RGB, flowColor, ramp, rockShade } from './palette.js';
import { themeColors } from './theme.js';
import { downloadBlob, icon, rangeFill } from './util.js';

export const NEVER = 2147483647;

/** Kolor żaru dla temperatury T (solidus -> ciemna czerwień, eruptTemp -> jasnożółty). */
export function glowColor(T, params) {
  const lo = params.solidusTemp, hi = params.eruptTemp;
  return ramp(GLOW, hi > lo ? (T - lo) / (hi - lo) : 1);
}

/** Typ komórki w kroku k (typ końcowy + pojawienie + zastygnięcie). */
export function stateAt(k, t, appear, solidFrom) {
  if (t !== LAVA && t !== BASALT) return t;
  if (k < appear) return AIR;
  return k >= solidFrom ? BASALT : LAVA;
}

/** Temperatura płynnej lawy w kroku k (z temperatury końcowej i parametrów stygnięcia). */
export function tempAt(k, t, tempFinal, solidFrom, steps, params) {
  const end = t === BASALT ? solidFrom : steps;
  return Math.min(params.eruptTemp, tempFinal + params.coolingAmbient * (end - k));
}

/** Kolor komórki w stanie s (po odtworzeniu) — wspólny dla 2D, ścian, powierzchni i wokseli. */
export function replayColor(s, T, flow, mode, info, flowCount) {
  if (s === LAVA) return mode === 'flow' ? flowColor(flow, flowCount) : glowColor(T, info.params);
  if (s === BASALT) {
    if (mode !== 'flow') return TYPE_RGB[BASALT];
    const c = flowColor(flow, flowCount);
    return [c[0] * 0.55, c[1] * 0.55, c[2] * 0.55];
  }
  return TYPE_RGB[s] || TYPE_RGB[AIR];
}

/**
 * Płaszczyzna w×h (przekrój albo ściana) w kroku k -> RGBA; zlicza też komórki płynne i zastygłe płaszczyzny.
 * d: { type, appear, solidFrom, temp, flowId } (tablice typowane, wiersz 0 = dół), flipY jak palette.colorize;
 * heights — wysokości kolumn (cieniowanie skały w rzucie z góry), states — opcjonalnie wyjście: typ w kroku k.
 */
export function colorizeReplay(w, h, d, k, info, mode, flipY = true, heights = null, states = null) {
  const out = new Uint8ClampedArray(w * h * 4);
  const flowCount = info.flowCount;
  let hlo = Infinity, hhi = -Infinity;
  if (heights) {
    for (let i = 0; i < heights.length; i++) if (heights[i] > 0) { hlo = Math.min(hlo, heights[i]); hhi = Math.max(hhi, heights[i]); }
  }
  let liquid = 0, solid = 0;
  for (let row = 0; row < h; row++) {
    const dst = flipY ? h - 1 - row : row;
    for (let col = 0; col < w; col++) {
      const i = row * w + col;
      const t = d.type[i];
      const s = stateAt(k, t, d.appear[i], d.solidFrom[i]);
      if (states) states[i] = s;
      let c;
      if (s === LAVA || s === BASALT) {
        c = replayColor(s, tempAt(k, t, d.temp[i], d.solidFrom[i], info.steps, info.params), d.flowId[i], mode, info, flowCount);
        if (s === LAVA) liquid++; else solid++;
      } else if (s === ROCK && heights && hhi > hlo) {
        c = rockShade((heights[i] - hlo) / (hhi - hlo));  // rzut z góry: skała cieniowana wysokością
      } else c = TYPE_RGB[s] || TYPE_RGB[AIR];
      const o = (dst * w + col) * 4;
      out[o] = c[0]; out[o + 1] = c[1]; out[o + 2] = c[2]; out[o + 3] = 255;
    }
  }
  return { rgba: out, liquid, solid };
}

/** Legenda odtwarzania (format palette.legendFor). */
export function replayLegend(info, mode, mcs = false) {
  if (mcs) return null;
  const L = { title: mode === 'flow' ? 'Odtwarzanie: krater / ziarno' : 'Odtwarzanie: żar lawy', items: [], notes: [] };
  if (mode === 'flow') {
    L.notes.push('płynna lawa — kolor krateru (flowId), zastygła — ten sam kolor przyciemniony');
  } else {
    const p = info.params;
    L.gradient = { stops: [0, 0.2, 0.4, 0.6, 0.8, 1].map((t) => glowColor(p.solidusTemp + t * (p.eruptTemp - p.solidusTemp), p)),
      min: p.solidusTemp, max: p.eruptTemp, unit: '°C' };
    L.notes.push('płynna lawa: temperatura w tym kroku (z temperatury końcowej i stygnięcia coolingAmbient na krok) — '
      + 'jasnożółta świeża, ciemnoczerwona tuż przed zastygnięciem');
    L.items.push({ rgb: TYPE_RGB[BASALT], label: 'bazalt (zastygła lawa)' });
  }
  L.items.push({ rgb: TYPE_RGB[ROCK], label: 'skała' }, { rgb: TYPE_RGB[AIR], label: 'powietrze' });
  return L;
}

/** Liczba kraterów do kolorowania flowId (sloty palety dla ≤ 8). */
export function flowCountOf(info) {
  return info.vents ? info.vents.length : 0;
}

// ------------------------------------------------------------------ pasek odtwarzania (suwak, Odtwórz, prędkość)

const SPEEDS = [1, 2, 5, 10, 20, 50, 100, 200, 500];

/**
 * Pasek odtwarzania: el = { bar, on, source, play, time, label, speed, counts, color, frames, webm, msg }.
 * hooks.onFrame(k) — narysuj krok k (indeks suwaka); hooks.onToggle(on); hooks.onSource(source).
 * Kroki: CA — 0 … steps; MC — indeksy listy migawek (etykieta = MCS).
 */
export class ReplayBar {
  constructor(el, hooks) {
    this.el = el;
    this.hooks = hooks;
    this.info = null;
    this.source = 'ca';
    this.k = 0;
    this.playing = false;
    this.busy = false;
    el.on.addEventListener('change', () => this.toggle(el.on.checked));
    el.play.addEventListener('click', () => (this.playing ? this.pause() : this.play()));
    el.time.addEventListener('input', () => { this.pause(); this.go(Number(el.time.value)); });
    el.speed.addEventListener('change', () => { this.lastT = null; });
    el.source.addEventListener('change', () => { this.pause(); this.source = el.source.value; this.hooks.onSource?.(this.source); });
    el.color.addEventListener('change', () => this.hooks.onFrame(this.k));
    // Spacja: Odtwórz / Pauza, gdy pasek jest widoczny (zakładka podglądu otwarta, odtwarzanie włączone),
    // a fokus nie jest w polu tekstowym, liście ani na przycisku (przycisk sam reaguje na spację).
    document.addEventListener('keydown', (e) => {
      if (e.code !== 'Space' || e.repeat || el.bar.hidden || !el.bar.offsetParent) return;
      const t = e.target;
      if (t !== el.time && t.closest?.('input, select, textarea, button, a, [contenteditable]')) return;
      e.preventDefault();
      if (this.playing) this.pause(); else this.play();
    });
  }

  get on() { return this.el.on.checked; }
  get mode() { return this.el.color.value; }

  /** Nowy wynik: meta z /api/result (replay, mcSnapshots). */
  setResult(meta) {
    this.pause();
    this.info = null;
    this.mcs = meta.mcSnapshots || [];
    const can = !!meta.replay || this.mcs.length > 0;
    this.el.on.disabled = !can;
    this.el.on.parentElement.title = can ? 'Odtwarzanie erupcji krok po kroku (suwak czasu)'
      : 'Odtwarzanie wymaga ca_result.bin w wersji 2 (output.format = bin) albo migawek MC';
    if (!can && this.el.on.checked) this.el.on.checked = false;
    const src = this.el.source;
    src.innerHTML = '';
    if (meta.replay) src.add(new Option('erupcja (CA)', 'ca'));
    if (this.mcs.length) src.add(new Option(`krystalizacja (MC, ${this.mcs.length} migawek)`, 'mc'));
    this.source = src.options.length ? src.options[0].value : 'ca';
    src.value = this.source;
    src.hidden = src.options.length < 2;
    this.el.color.value = meta.mode === 'classic' ? 'flow' : 'glow';
    this.el.bar.hidden = !this.on;
  }

  /** Dane odtwarzania CA (z /api/result/replay) — ustala zakres suwaka i domyślną prędkość. */
  setInfo(info) {
    this.info = info;
    this.syncRange();
  }

  last() { return this.source === 'mc' ? Math.max(0, this.mcs.length - 1) : (this.info ? this.info.steps : 0); }

  syncRange() {
    const last = this.last();
    this.el.color.parentElement.hidden = this.source === 'mc';  // kryształy MC mają własne kolory (hash ID)
    this.el.time.max = last;
    if (this.k > last) this.k = last;
    this.el.time.value = this.k;
    rangeFill(this.el.time);
    // Domyślnie całe odtwarzanie ~10 s.
    const want = this.source === 'mc' ? 2 : Math.max(1, last / 10);
    this.el.speed.innerHTML = SPEEDS.map((v) => `<option value="${v}">${v} ${this.source === 'mc' ? 'migawek' : 'kroków'}/s</option>`).join('');
    this.el.speed.value = String(SPEEDS.reduce((a, b) => (Math.abs(b - want) < Math.abs(a - want) ? b : a)));
    this.label();
  }

  /** Etykieta kroku + liczba komórek płynnych / zastygłych w całej objętości. */
  label(extra = '') {
    const k = this.k;
    if (this.source === 'mc') {
      this.el.label.textContent = `MCS ${this.mcs[k] ?? 0} (${k + 1}/${this.mcs.length})`;
      this.el.counts.textContent = extra;
      return;
    }
    const info = this.info;
    this.el.label.textContent = info ? `krok ${k} / ${info.steps}` : 'krok —';
    if (!info) { this.el.counts.textContent = ''; return; }
    const fmt = (v) => v.toLocaleString('pl-PL');
    const classic = info.mode === 'classic';
    this.el.counts.innerHTML = classic
      ? `komórki ziaren: <b>${fmt(info.liquid[k] + info.solid[k])}</b>${extra}`
      : `płynna: <b>${fmt(info.liquid[k])}</b> · zastygła: <b>${fmt(info.solid[k])}</b> komórek${extra}`;
  }

  toggle(on) {
    this.pause();
    this.el.bar.hidden = !on;
    this.hooks.onToggle?.(on);
  }

  /** Przejście do kroku k (indeks suwaka). */
  go(k) {
    this.k = Math.max(0, Math.min(this.last(), k));
    this.el.time.value = this.k;
    rangeFill(this.el.time);
    this.label();
    return this.hooks.onFrame(this.k);
  }

  play() {
    if (this.k >= this.last()) this.go(0);
    this.playing = true;
    this.playLabel(true);
    this.lastT = null;
    this.acc = 0;
    const tick = async (now) => {
      if (!this.playing) return;
      if (this.lastT == null) this.lastT = now;
      this.acc += ((now - this.lastT) / 1000) * Number(this.el.speed.value);
      this.lastT = now;
      if (this.acc >= 1 && !this.busy) {
        const n = Math.floor(this.acc);
        this.acc -= n;
        this.busy = true;
        try { await this.go(this.k + n); } finally { this.busy = false; }
        if (this.k >= this.last()) { this.pause(); return; }
      }
      this.raf = requestAnimationFrame(tick);
    };
    this.raf = requestAnimationFrame(tick);
  }

  pause() {
    this.playing = false;
    cancelAnimationFrame(this.raf);
    this.playLabel(false);
  }

  /** Napis i ikona przycisku Odtwórz / Pauza — podmieniane tylko przy zmianie stanu (pause() woła każdy ruch suwaka,
   *  a nowy element SVG w każdej klatce kosztował ~30% przepustowości odtwarzania w 3D). */
  playLabel(playing) {
    if (this.shownPlaying === playing) return;
    this.shownPlaying = playing;
    this.el.play.innerHTML = playing ? `${icon('pause')}Pauza` : `${icon('play')}Odtwórz`;
  }

  /** Lista kroków do eksportu: najwyżej maxFrames, równomiernie, zawsze z pierwszym i ostatnim. */
  frameList(maxFrames = 200) {
    const last = this.last();
    if (last + 1 <= maxFrames) return Array.from({ length: last + 1 }, (_, i) => i);
    const out = [];
    for (let i = 0; i < maxFrames; i++) out.push(Math.round((i * last) / (maxFrames - 1)));
    return [...new Set(out)];
  }

  message(text) { this.el.msg.textContent = text; }
}

// ------------------------------------------------------------------ eksport: ZIP z klatkami PNG, film WebM

const CRC_TABLE = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();

function crc32(bytes) {
  let c = 0xFFFFFFFF;
  for (let i = 0; i < bytes.length; i++) c = CRC_TABLE[(c ^ bytes[i]) & 0xFF] ^ (c >>> 8);
  return (c ^ 0xFFFFFFFF) >>> 0;
}

/** Archiwum ZIP bez kompresji (metoda 0 „stored”) z listy { name, data: Uint8Array } -> Blob. */
export function makeZip(files) {
  const parts = [];
  const central = [];
  let offset = 0;
  const enc = new TextEncoder();
  const now = new Date();  // data i czas modyfikacji w formacie DOS (dla wszystkich plików)
  const dosTime = (now.getHours() << 11) | (now.getMinutes() << 5) | (now.getSeconds() >> 1);
  const dosDate = ((now.getFullYear() - 1980) << 9) | ((now.getMonth() + 1) << 5) | now.getDate();
  for (const f of files) {
    const name = enc.encode(f.name);
    const crc = crc32(f.data);
    const head = new DataView(new ArrayBuffer(30));
    head.setUint32(0, 0x04034b50, true); head.setUint16(4, 20, true); head.setUint16(6, 0x0800, true);  // UTF-8
    head.setUint16(8, 0, true); head.setUint16(10, dosTime, true); head.setUint16(12, dosDate, true); head.setUint32(14, crc, true);
    head.setUint32(18, f.data.length, true); head.setUint32(22, f.data.length, true); head.setUint16(26, name.length, true);
    parts.push(head, name, f.data);
    const cen = new DataView(new ArrayBuffer(46));
    cen.setUint32(0, 0x02014b50, true); cen.setUint16(4, 20, true); cen.setUint16(6, 20, true); cen.setUint16(8, 0x0800, true);
    cen.setUint16(12, dosTime, true); cen.setUint16(14, dosDate, true);
    cen.setUint32(16, crc, true); cen.setUint32(20, f.data.length, true); cen.setUint32(24, f.data.length, true);
    cen.setUint16(28, name.length, true); cen.setUint32(42, offset, true);
    central.push(cen, name);
    offset += 30 + name.length + f.data.length;
  }
  const size = central.reduce((s, p) => s + p.byteLength, 0);
  const end = new DataView(new ArrayBuffer(22));
  end.setUint32(0, 0x06054b50, true); end.setUint16(8, files.length, true); end.setUint16(10, files.length, true);
  end.setUint32(12, size, true); end.setUint32(16, offset, true);
  return new Blob([...parts, ...central, end], { type: 'application/zip' });
}

const canvasPng = (canvas) => new Promise((resolve) => canvas.toBlob(async (b) => resolve(new Uint8Array(await b.arrayBuffer())), 'image/png'));

/**
 * Eksport sekwencji klatek PNG (ZIP). draw(k, canvas) rysuje klatkę kroku k na canvasie wyjściowym.
 */
export async function exportFrames(bar, canvas, draw, baseName) {
  const ks = bar.frameList();
  bar.pause();
  const files = [];
  for (let i = 0; i < ks.length; i++) {
    bar.message(`klatka ${i + 1}/${ks.length}…`);
    await draw(ks[i], canvas);
    files.push({ name: `${baseName}_${String(i).padStart(4, '0')}.png`, data: await canvasPng(canvas) });
  }
  downloadBlob(makeZip(files), `${baseName}_klatki.zip`);
  bar.message(`zapisano ${ks.length} klatek PNG (ZIP)`);
}

/**
 * Film WebM z canvasu (MediaRecorder): klatki kroków z bar.frameList(), fps klatek na sekundę.
 */
export async function recordWebM(bar, canvas, draw, baseName, fps = 25) {
  if (typeof MediaRecorder === 'undefined' || !canvas.captureStream) {
    bar.message('ta przeglądarka nie nagrywa canvasu (MediaRecorder) — użyj klatek PNG');
    return;
  }
  const type = ['video/webm;codecs=vp9', 'video/webm;codecs=vp8', 'video/webm'].find((t) => MediaRecorder.isTypeSupported(t));
  if (!type) { bar.message('brak obsługi WebM w tej przeglądarce — użyj klatek PNG'); return; }
  bar.pause();
  const ks = bar.frameList(300);
  const stream = canvas.captureStream(0);
  const track = stream.getVideoTracks()[0];
  const rec = new MediaRecorder(stream, { mimeType: type, videoBitsPerSecond: 8_000_000 });
  const chunks = [];
  rec.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
  const done = new Promise((resolve) => { rec.onstop = resolve; });
  rec.start();
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  for (let i = 0; i < ks.length; i++) {
    bar.message(`nagrywanie: klatka ${i + 1}/${ks.length}…`);
    const t0 = performance.now();
    await draw(ks[i], canvas);
    track.requestFrame?.();
    await wait(Math.max(0, 1000 / fps - (performance.now() - t0)));
  }
  await wait(200);
  rec.stop();
  await done;
  downloadBlob(new Blob(chunks, { type: 'video/webm' }), `${baseName}.webm`);
  bar.message(`zapisano film WebM (${ks.length} klatek, ${fps} kl./s)`);
}

/** Nagłówek klatki eksportu: tytuł + krok (kolor i krój z motywu). */
export function frameTitle(g, text, x = 12, y = 10) {
  const th = themeColors();
  g.fillStyle = th.ink;
  g.font = `600 14px ${th.font}`;
  g.textBaseline = 'top';
  g.fillText(text, x, y);
}
