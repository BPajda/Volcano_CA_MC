// Kratery na mapie (etap 6) — panel w zakładce „Nowa symulacja”, widoczny przy vents.placement = "positions":
//  - podgląd mapy wysokości: kolory hipsometryczne + cieniowanie (światło z NW) + poziomice; północ (y = ny − 1) u góry,
//  - kliknięcie dodaje krater w kolumnie (x, y), kliknięcie na znaczniku go usuwa; lista [[x, y], …] trafia do pola
//    vents.positions formularza, a vents.count = liczba kraterów (silnik wymaga zgodności obu pól),
//  - pod kursorem: kolumna, wysokość terenu w komórkach, a dla map z metadanymi (configs/heightmaps/<nazwa>.json,
//    tools/fetch_dem.py) także wysokość w metrach i szerokość / długość geograficzna.
// Teren ze stożka (terrain.type = cone) jest pokazany w przybliżeniu — ten sam wzór co TerrainGenerator::cone,
// ale bez szumu. Przekrój 2D (ny = 1) — profil terenu, kliknięcie wybiera x.
// Etap 7: znaczniki kraterów w kolorze lawy z obrysem i numerem w kółku (czytelne na mapie hipsometrycznej),
// tło i profil w kolorach motywu / palety (skała); mapa przerysowywana po zmianie motywu.

import { getBinary, typed, url } from './api.js';
import { CONTOUR, HYPSO, ROCK, SEA_RGB, TYPE_RGB, VENT_MARKER, ramp, toHex } from './palette.js';
import { onThemeChange, themeColors } from './theme.js';
import { $, esc } from './util.js';

const SIZE = 520;   // dłuższy bok podglądu [px]

const hypso = (t) => ramp(HYPSO, t);

/** „Ładny” krok poziomic: 1, 2, 2,5 albo 5 × 10^n, ok. `count` poziomic na zakres. */
function niceStep(range, count = 10) {
  const raw = range / count, p = 10 ** Math.floor(Math.log10(raw)), m = raw / p;
  return (m < 1.5 ? 1 : m < 2.25 ? 2 : m < 3.5 ? 2.5 : m < 7.5 ? 5 : 10) * p;
}

export class VentPicker {
  /** hooks: form() — ConfigForm, maps() — lista map z /api/heightmaps (z metadanymi geo). */
  constructor(hooks) {
    this.hooks = hooks;
    this.card = $('#vp-card');
    this.canvas = $('#vp-canvas');
    this.info = $('#vp-info');
    this.list = $('#vp-list');
    this.hover = $('#vp-hover');
    this.key = null;        // klucz bieżącego terenu (plik albo parametry stożka)
    this.heights = null;    // Float32Array ny·nx (wiersz 0 = y = 0)
    this.positions = [];
    this.canvas.addEventListener('click', (e) => this.onClick(e));
    this.canvas.addEventListener('mousemove', (e) => this.onMove(e));
    this.canvas.addEventListener('mouseleave', () => { this.hover.innerHTML = '&nbsp;'; });
    $('#vp-clear').addEventListener('click', () => this.setPositions([]));
    $('#vp-undo').addEventListener('click', () => this.setPositions(this.positions.slice(0, -1)));
    onThemeChange(() => { if (!this.card.hidden && this.nx) { this.base = null; this.draw(); } });
  }

  /** Formularz się zmienił: panel tylko dla lawy z placement = positions; teren z pliku albo stożek. */
  async sync(cfg) {
    const lava = cfg.ca?.mode !== 'classic' && !(cfg.mc?.enabled && cfg.mc?.domain === 'full');
    const show = lava && cfg.vents?.placement === 'positions';
    this.card.hidden = !show;
    if (!show) return;
    const sp = cfg.space || {};
    this.nx = Math.max(1, sp.nx | 0);
    this.ny = Math.max(1, sp.ny | 0);
    this.nz = Math.max(1, sp.nz | 0);
    this.positions = Array.isArray(cfg.vents?.positions) ? cfg.vents.positions.filter((p) => Array.isArray(p) && p.length === 2) : [];
    const t = cfg.terrain || {};
    const file = t.type === 'file' ? t.file || '' : '';
    const map = file ? (this.hooks.maps() || []).find((m) => m.file === file) : null;
    this.geo = map?.geo && map.geo.nx === this.nx && map.geo.ny === this.ny ? map.geo : null;
    const key = file ? `file|${file}|${this.nx}|${this.ny}|${this.nz}` : `cone|${this.nx}|${this.ny}|${this.nz}|${t.peakHeight}|${t.baseRadius}|${t.craterRadius}|${t.craterDepth}`;
    if (key !== this.key) {
      this.key = key;
      this.hover.innerHTML = '&nbsp;';
      this.heights = null;
      this.note = '';
      if (file && map && map.nx === this.nx && map.ny === this.ny) {
        try {
          const { buffer } = await getBinary(url('/api/heightmaps/data', { file }));
          if (this.key !== key) return;
          this.heights = typed('float32', buffer);
        } catch (err) { this.note = `nie można wczytać mapy: ${err.message}`; }
      } else if (file) {
        this.note = map ? `mapa ${map.nx}×${map.ny} nie pasuje do siatki ${this.nx}×${this.ny}` : 'mapa spoza configs/heightmaps/, bez podglądu wysokości';
      } else {
        this.heights = coneHeights(t, this.nx, this.ny);
        this.note = 'teren ze stożka, podgląd bez szumu (terrain.noise)';
      }
      this.base = null;
    }
    this.draw();
  }

  setPositions(list) {
    const form = this.hooks.form();
    this.positions = list;
    form.setValues({ 'vents.positions': list, 'vents.count': Math.max(1, list.length) });
  }

  /** Geometria podglądu: skala [px/komórkę], przesunięcie; profil dla ny = 1. */
  layout() {
    const profile = this.ny === 1;
    const sc = profile ? Math.max(1, Math.floor(SIZE / this.nx)) : Math.max(1, Math.floor(SIZE / Math.max(this.nx, this.ny)));
    const w = this.nx * sc, h = profile ? Math.min(260, Math.max(120, this.nz * 3)) : this.ny * sc;
    return { profile, sc, w, h };
  }

  /** Tło (teren) liczone raz na teren; znaczniki rysowane na nim przy każdej zmianie listy. */
  renderBase() {
    const { profile, sc, w, h } = this.layout();
    const c = document.createElement('canvas');
    c.width = w; c.height = h;
    const g = c.getContext('2d'), th = themeColors();
    g.fillStyle = th.viewBg;
    g.fillRect(0, 0, w, h);
    const H = this.heights, nx = this.nx, ny = this.ny;
    if (!H) {
      g.strokeStyle = th.line;
      for (let x = 0; x <= nx; x += Math.max(1, Math.round(nx / 20))) { g.beginPath(); g.moveTo(x * sc, 0); g.lineTo(x * sc, h); g.stroke(); }
      return c;
    }
    let lo = Infinity, hi = -Infinity;
    for (const v of H) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
    this.range = [lo, hi];
    if (profile) {
      const zs = h / this.nz;
      g.fillStyle = toHex(TYPE_RGB[ROCK]);
      for (let x = 0; x < nx; x++) { const hh = Math.min(this.nz, H[x]) * zs; g.fillRect(x * sc, h - hh, sc, hh); }
      return c;
    }
    // Kolory hipsometryczne + cieniowanie (normalna z różnic wysokości, światło z północnego zachodu).
    const img = g.createImageData(nx, ny);
    const at = (x, y) => H[Math.min(ny - 1, Math.max(0, y)) * nx + Math.min(nx - 1, Math.max(0, x))];
    const zScale = 1.5;
    for (let y = 0; y < ny; y++) {
      for (let x = 0; x < nx; x++) {
        const v = at(x, y);
        const dx = (at(x + 1, y) - at(x - 1, y)) * zScale / 2, dy = (at(x, y + 1) - at(x, y - 1)) * zScale / 2;
        // światło: z kierunku (−1, +1, 1.2) (NW, y rośnie na północ)
        const nlen = Math.hypot(dx, dy, 1);
        const shade = Math.max(0, (dx * 0.577 - dy * 0.577 + 0.577 * 1.2) / nlen / 1.04);
        const col = v <= 0 ? SEA_RGB : hypso(hi > lo ? (v - lo) / (hi - lo) : 0.5);
        const f = 0.55 + 0.6 * shade;
        const o = ((ny - 1 - y) * nx + x) * 4;
        img.data[o] = Math.min(255, col[0] * f); img.data[o + 1] = Math.min(255, col[1] * f); img.data[o + 2] = Math.min(255, col[2] * f);
        img.data[o + 3] = 255;
      }
    }
    const tmp = document.createElement('canvas');
    tmp.width = nx; tmp.height = ny;
    tmp.getContext('2d').putImageData(img, 0, 0);
    g.imageSmoothingEnabled = false;
    g.drawImage(tmp, 0, 0, w, h);
    // Poziomice: granice między przedziałami wysokości (w metrach, gdy są metadane).
    const toM = (v) => (this.geo ? v * this.geo.metersPerCellZ + this.geo.baseMeters : v);
    const step = niceStep(toM(hi) - toM(lo), 10);
    this.contourStep = step;
    const lev = (x, y) => Math.floor(toM(H[y * nx + x]) / step);
    g.beginPath();
    for (let y = 0; y < ny; y++) {
      for (let x = 0; x < nx; x++) {
        const a = lev(x, y), py = (ny - 1 - y) * sc;
        if (x + 1 < nx && lev(x + 1, y) !== a) { g.moveTo((x + 1) * sc, py); g.lineTo((x + 1) * sc, py + sc); }
        if (y + 1 < ny && lev(x, y + 1) !== a) { g.moveTo(x * sc, py); g.lineTo((x + 1) * sc, py); }
      }
    }
    g.strokeStyle = CONTOUR;
    g.lineWidth = 1;
    g.stroke();
    return c;
  }

  draw() {
    const { profile, sc, w, h } = this.layout();
    if (!this.base) this.base = this.renderBase();
    const c = this.canvas;
    c.width = w; c.height = h;
    c.style.width = `${w}px`; c.style.height = `${h}px`;
    const g = c.getContext('2d');
    g.drawImage(this.base, 0, 0);
    const r = Math.max(6, Math.min(9, sc * 1.6));
    const th = themeColors();
    g.textAlign = 'center'; g.textBaseline = 'middle';
    this.positions.forEach(([x, y], i) => {
      const [px, py] = this.toPx(x, y);
      // Znacznik: poświata + kółko w kolorze lawy z ciemnym i jasnym obrysem (widoczny na każdym kolorze mapy).
      g.beginPath(); g.arc(px, py, r + 3, 0, 2 * Math.PI);
      g.fillStyle = VENT_MARKER.halo; g.fill();
      g.beginPath(); g.arc(px, py, r, 0, 2 * Math.PI);
      g.fillStyle = VENT_MARKER.fill; g.fill();
      g.lineWidth = 2; g.strokeStyle = VENT_MARKER.ring; g.stroke();
      g.lineWidth = 1; g.strokeStyle = VENT_MARKER.outer;
      g.beginPath(); g.arc(px, py, r + 1.5, 0, 2 * Math.PI); g.stroke();
      // Numer krateru nad znacznikiem: tekst z obwódką (czytelny na jasnym i ciemnym terenie).
      g.font = `700 11px ${th.font}`;
      g.lineWidth = 3; g.strokeStyle = VENT_MARKER.textHalo; g.strokeText(String(i + 1), px, py - r - 8);
      g.fillStyle = VENT_MARKER.text; g.fillText(String(i + 1), px, py - r - 8);
    });
    this.markR = r;
    this.renderList(profile);
  }

  /** Środek kolumny (x, y) na canvasie. */
  toPx(x, y) {
    const { profile, sc, h } = this.layout();
    if (profile) {
      const zs = h / this.nz, hh = this.heights ? Math.min(this.nz, this.heights[x]) * zs : h / 2;
      return [(x + 0.5) * sc, h - hh];
    }
    return [(x + 0.5) * sc, (this.ny - 1 - y + 0.5) * sc];
  }

  cellAt(e) {
    const rect = this.canvas.getBoundingClientRect();
    const { profile, sc } = this.layout();
    const x = Math.floor((e.clientX - rect.left) / sc);
    const y = profile ? 0 : this.ny - 1 - Math.floor((e.clientY - rect.top) / sc);
    if (x < 0 || x >= this.nx || y < 0 || y >= this.ny) return null;
    return { x, y, px: e.clientX - rect.left, py: e.clientY - rect.top };
  }

  onClick(e) {
    const cell = this.cellAt(e);
    if (!cell) return;
    // Kliknięcie na znaczniku (w promieniu znacznika) usuwa krater, w innym miejscu — dodaje.
    const hit = this.positions.findIndex(([x, y]) => {
      const [px, py] = this.toPx(x, y);
      return Math.hypot(px - cell.px, py - cell.py) <= this.markR + 2;
    });
    if (hit >= 0) this.setPositions(this.positions.filter((_, i) => i !== hit));
    else if (!this.positions.some(([x, y]) => x === cell.x && y === cell.y)) this.setPositions([...this.positions, [cell.x, cell.y]]);
  }

  onMove(e) {
    const cell = this.cellAt(e);
    if (!cell) { this.hover.innerHTML = '&nbsp;'; return; }
    this.hover.innerHTML = this.describe(cell.x, cell.y);
  }

  /** Opis kolumny: x, y, wysokość terenu (komórki, metry), szer./dł. geograficzna. */
  describe(x, y, withXY = true) {
    let s = withXY ? `x <b>${x}</b>, y <b>${y}</b>` : '';
    if (this.heights) {
      const v = this.heights[y * this.nx + x];
      s += `${s ? ' · ' : ''}teren ${v.toFixed(1)} kom.`;
      if (this.geo) s += ` ≈ ${Math.round(v * this.geo.metersPerCellZ + this.geo.baseMeters)} m n.p.m.`;
    }
    if (this.geo) {
      const b = this.geo.bbox;
      const lat = b.south + ((y + 0.5) / this.ny) * (b.north - b.south);
      const lon = b.west + ((x + 0.5) / this.nx) * (b.east - b.west);
      s += ` · ${lat.toFixed(4)}° N, ${lon.toFixed(4)}° E`;
    }
    return s;
  }

  renderList(profile) {
    const g = this.geo;
    let head = `Siatka ${this.nx}×${this.ny}${profile ? ' (przekrój 2D: kliknij na profilu, y = 0)' : ''}`;
    if (g) head += ` · ${g.metersPerCell?.toFixed(0)} m/komórkę w poziomie, ${g.metersPerCellZ?.toFixed(1)} m w pionie (przewyższenie ×${g.exaggeration?.toFixed(1)})`;
    if (this.contourStep && !profile) head += ` · poziomice co ${this.contourStep.toLocaleString('pl-PL')} ${g ? 'm' : 'kom.'}`;
    if (this.note) head += ` · ${this.note}`;
    if (g?.source) head += `<br>Teren: ${esc(g.source)}, zoom ${g.zoom}, pobrano ${esc(g.fetched || '?')}; przypisanie danych: <code>configs/heightmaps/README.md</code>`;
    this.info.innerHTML = head;
    this.list.innerHTML = this.positions.length
      ? this.positions.map(([x, y]) => `<li><b>[${x}, ${y}]</b> <span class="hint">${this.describe(x, y, false)}</span></li>`).join('')
      : '<li class="hint vp-empty">brak kraterów, kliknij na mapie</li>';
  }
}

/** Wysokości stożka z generatora bez szumu (TerrainGenerator::cone): płaskie dno krateru poniżej krawędzi. */
function coneHeights(t, nx, ny) {
  const out = new Float32Array(nx * ny);
  const cx = (nx - 1) / 2, cy = (ny - 1) / 2;
  const cone = (r) => t.peakHeight * Math.max(0, 1 - r / t.baseRadius);
  const floor = cone(t.craterRadius) - t.craterDepth;
  for (let y = 0; y < ny; y++) {
    for (let x = 0; x < nx; x++) {
      const r = Math.hypot(x - cx, y - cy);
      out[y * nx + x] = Math.max(0, r < t.craterRadius ? floor : cone(r));
    }
  }
  return out;
}
