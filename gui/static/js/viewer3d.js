// Podgląd 3D (three.js + OrbitControls):
//  - ściany zewnętrzne (wymagany „rzut ścian zewnętrznych”): prostopadłościan nx × ny × nz, każda z 6 ścian
//    oteksturowana wartościami wybranego pola (te same kolory i legenda co w 2D). Opcja: górna ściana jako
//    rzut z góry (najwyższa niepusta komórka kolumny) — warstwa z = nz−1 wulkanu to prawie samo powietrze;
//  - powierzchnia: siatka wysokości (najwyższa niepusta komórka w kolumnie) pokolorowana polem na tej
//    wysokości — dla trybu lava zbocze wulkanu z jęzorami lawy;
//  - woksele lawy/bazaltu (InstancedMesh, limit liczby wokseli).
// Układ: oś x symulacji -> X sceny, z (pionowa) -> Y sceny, y -> −Z sceny (układ prawoskrętny, bez odbicia).
// Etap 6 — odtwarzanie erupcji (replay.js): komórki lawy wyniku końcowego (pojawienie, zastygnięcie, temperatura,
// flowId) i wysokość terenu pobierane RAZ (/api/result/replay/cells, surface?field=terrain); każda klatka liczy
// w przeglądarce powierzchnię w kroku k (najwyższa niepusta komórka kolumny), kolory ścian albo widoczne woksele.
// Krystalizacja MC: ściany / powierzchnia z kryształami z migawki (mcs=<k>).
// Etap 7 (wygląd): tło = gradient nieba z motywu (CSS pod przezroczystym canvasem), światło półkuli + kierunkowe
// „słońce” (cieniowanie zbocza), płynna lawa w odtwarzaniu z lekką emisją (atrybut aGlow — świeci też w cieniu),
// ramka i podpisy osi w kolorach motywu. Logika odtwarzania i próbkowania danych bez zmian.

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/OrbitControls.js';
import { getBinary, getJSON, typed, url } from './api.js';
import { AIR, BASALT, LAVA, ROCK, TYPE_RGB, colorize, drawLegend, legendFor, rockShade, showLegend, FIELD_LABELS } from './palette.js';
import {
  ReplayBar, colorizeReplay, exportFrames, flowCountOf, frameTitle, recordWebM, replayColor, replayLegend, stateAt, tempAt,
} from './replay.js';
import { onThemeChange, skyGradient, themeColors } from './theme.js';
import { setText } from './util.js';
import { download } from './viewer2d.js';

const VOXEL_LIMIT = 150000;
const SURFACE_MAX_VERTICES = 360000;

export class Viewer3D {
  constructor(el) {
    this.el = el;  // { wrap, loading, legend, status, field, modeRadios, topSurface, topGroup, exag, exagGroup, exagVal, reset, png }
    this.meta = null;
    this.mode = 'faces';
    this.field = 'type';
    this.cache = new Map();
    this.inited = false;
    this.rd = null;      // dane odtwarzania wyniku (info, komórki lawy, teren)
    this.rv = null;      // obiekty sceny aktualizowane co klatkę odtwarzania
    this.mcsParam = undefined;  // MCS migawki kryształów (odtwarzanie MC)
    this.replay = new ReplayBar(el.replay, {
      onFrame: (k) => this.drawReplay(k),
      onToggle: () => { this.mcsParam = undefined; this.load(); },
      onSource: () => { this.replay.syncRange(); this.mcsParam = undefined; this.load(); },
    });
    el.replay.frames.addEventListener('click', () => this.exportReplay('frames'));
    el.replay.webm.addEventListener('click', () => this.exportReplay('webm'));
    this.bind();
    onThemeChange(() => {
      if (!this.inited) return;
      this.applyThemeLights();
      if (this.meta) this.load(); else this.render();
    });
  }

  bind() {
    const e = this.el;
    e.modeRadios.forEach((r) => r.addEventListener('change', () => { if (r.checked) { this.mode = r.value; this.sync(); this.load(); } }));
    e.field.addEventListener('change', () => { this.field = e.field.value; this.load(); });
    e.topSurface.addEventListener('change', () => this.load());
    e.exag.addEventListener('input', () => { e.exagVal.textContent = `×${e.exag.value}`; this.load(); });
    e.reset.addEventListener('click', () => this.resetCamera());
    e.png.addEventListener('click', () => this.exportPNG());
  }

  init() {
    if (this.inited) return;
    this.inited = true;
    const wrap = this.el.wrap;
    // Przezroczysty canvas: tło (gradient nieba) rysuje CSS pod sceną (.canvas-wrap.sky) — zmienia się z motywem.
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
    this.renderer.setPixelRatio(window.devicePixelRatio || 1);
    this.renderer.setClearColor(0x000000, 0);
    wrap.appendChild(this.renderer.domElement);
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(35, 1, 0.1, 10000);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.addEventListener('change', () => this.render());
    // Światło półkuli (niebo / grunt) + kierunkowe „słońce” z NW nad wulkanem — zbocza od słońca ciemniejsze.
    this.hemi = new THREE.HemisphereLight(0xffffff, 0x6a5a4a, 1.6);
    this.sun = new THREE.DirectionalLight(0xffffff, 2.3);
    this.sun.position.set(-0.6, 1, 0.8);
    this.scene.add(this.hemi, this.sun);
    this.applyThemeLights();
    this.group = new THREE.Group();
    this.scene.add(this.group);
    new ResizeObserver(() => this.resize()).observe(wrap);
    this.resize();
  }

  /** Kolory świateł z motywu (CSS: --hemi-sky, --hemi-ground, --sun). */
  applyThemeLights() {
    const c = themeColors();
    this.hemi.color.setStyle(c.hemiSky, THREE.SRGBColorSpace);
    this.hemi.groundColor.setStyle(c.hemiGround, THREE.SRGBColorSpace);
    this.sun.color.setStyle(c.sun, THREE.SRGBColorSpace);
  }

  resize() {
    if (!this.inited) return;
    const r = this.el.wrap.getBoundingClientRect();
    if (r.width < 10 || r.height < 10) return;
    this.renderer.setSize(r.width, r.height, false);
    this.renderer.domElement.style.width = '100%';
    this.renderer.domElement.style.height = '100%';
    this.camera.aspect = r.width / r.height;
    this.camera.updateProjectionMatrix();
    this.render();
  }

  render() { if (this.inited) this.renderer.render(this.scene, this.camera); }

  setResult(meta) {
    const newResult = this.meta?.id !== meta.id;
    this.meta = meta;
    if (newResult) {
      this.cache.clear();
      this.rd = null;
      this.mcsParam = undefined;
      this.replay.setResult(meta);
      this.field = meta.mode === 'mc_full' && meta.fields.includes('crystal') ? 'crystal' : (meta.fields.includes('flowId') ? 'flowId' : 'type');
      this.el.topSurface.checked = meta.mode === 'lava';  // u wulkanu warstwa z = nz−1 to prawie samo powietrze
    }
    if (!meta.fields.includes(this.field)) this.field = 'type';
    const f = this.el.field;
    f.innerHTML = '';
    for (const name of meta.fields) f.add(new Option(FIELD_LABELS[name], name));
    f.value = this.field;
    this.sync();
    return this.load(newResult);
  }

  sync() {
    this.el.topGroup.hidden = this.mode !== 'faces';
    this.el.exagGroup.hidden = this.mode !== 'surface';
    this.el.field.disabled = this.replay.on;  // w odtwarzaniu kolor wybiera pasek odtwarzania
    if ([...this.el.field.options].some((o) => o.value === this.field)) this.el.field.value = this.field;
  }

  async fetch(path, params) {
    // Odtwarzanie MC: kryształy z migawki (parametr mcs) — klucz pamięci podręcznej rozróżnia migawki.
    if (this.mcsParam !== undefined && params.field === 'crystal' && path !== '/api/result/voxels') params = { ...params, mcs: this.mcsParam };
    const key = `${path}|${JSON.stringify(params)}`;
    if (this.cache.has(key)) return this.cache.get(key);
    const r = await getBinary(url(path, { id: this.meta.id, ...params }));
    this.cache.set(key, r);
    if (this.cache.size > 24) this.cache.delete(this.cache.keys().next().value);
    return r;
  }

  async load(resetCam = false) {
    if (!this.meta) return;
    this.init();
    const token = (this.token = (this.token || 0) + 1);
    const slow = setTimeout(() => { this.el.loading.hidden = false; }, 150);
    this.sync();
    try {
      let objects;
      const replayCa = this.replay.on && this.replay.source === 'ca';
      if (this.replay.on && this.replay.source === 'mc' && this.mcsParam === undefined) {
        this.replay.syncRange();
        this.mcsParam = this.replay.mcs[this.replay.k];
        this.field = 'crystal';
      }
      if (replayCa) objects = await this.buildReplay();
      else if (this.mode === 'faces') objects = await this.buildFaces();
      else if (this.mode === 'surface') objects = await this.buildSurface();
      else objects = await this.buildVoxels();
      if (token !== this.token) { disposeAll(objects); return; }
      this.rv = objects.rv || null;  // dopiero po sprawdzeniu tokenu — spóźniona budowa nie podmieni obiektów
      this.clear();
      objects.forEach((o) => this.group.add(o));
      this.group.add(...this.buildFrame());
      showLegend(this.el.legend, this.legend);
      if (resetCam || !this.camSet) this.resetCamera();
      if (replayCa && this.rv) this.updateReplay(this.replay.k);
      else if (this.replay.on && this.mcsParam !== undefined) this.mcStatus();
      this.render();
    } catch (err) {
      this.el.status.textContent = `Błąd: ${err.message}`;
    } finally {
      clearTimeout(slow);
      if (token === this.token) this.el.loading.hidden = true;
    }
  }

  clear() {
    disposeAll([...this.group.children]);
    this.group.clear();
  }

  ctx() { return { ranges: this.meta.ranges }; }

  /** Pozycja sceny dla współrzędnych bloku (x, y, z) — środek bloku w (0, 0, 0). */
  pos(x, y, z) {
    const [nx, ny, nz] = this.meta.dims;
    return [x - nx / 2, z - nz / 2, -(y - ny / 2)];
  }

  async buildFaces() {
    const top = this.el.topSurface.checked ? 'surface' : 'layer';
    const reqs = [this.fetch('/api/result/faces', { field: 'type', top })];
    if (this.field !== 'type') reqs.push(this.fetch('/api/result/faces', { field: this.field, top }));
    if (top === 'surface') reqs.push(this.fetch('/api/result/surface', { field: 'height' }));
    const [t, v0, hgt] = await Promise.all(reqs);
    const v = this.field === 'type' ? null : v0;
    const heightsTop = top === 'surface' ? typed('uint16', (this.field === 'type' ? v0 : hgt).buffer) : null;
    const [nx, ny, nz] = this.meta.dims;
    const present = new Set();
    const meshes = [];
    const place = facePlacement(nx, ny, nz);
    for (const f of t.meta.faces) {
      const n = f.width * f.height;
      const tArr = typed('uint8', t.buffer, f.offset, n);
      tArr.forEach((x) => present.add(x));
      const vArr = v ? typed(v.meta.dtype, v.buffer, v.meta.faces.find((g) => g.name === f.name).offset, n) : null;
      const ctx = this.ctx();
      if (f.name === 'z1' && heightsTop) ctx.heights = heightsTop;  // skała w rzucie z góry cieniowana wysokością
      let rgba = colorize(f.width, f.height, tArr, vArr, this.field, ctx, false);
      const pl = place[f.name];
      if (pl.flipCols || pl.flipRows) rgba = flip(rgba, f.width, f.height, pl.flipCols, pl.flipRows);
      const tex = new THREE.DataTexture(new Uint8Array(rgba.buffer), f.width, f.height, THREE.RGBAFormat);
      tex.colorSpace = THREE.SRGBColorSpace;
      tex.magFilter = THREE.NearestFilter;
      tex.minFilter = THREE.LinearMipmapLinearFilter;
      tex.generateMipmaps = true;
      tex.needsUpdate = true;
      // polygonOffset: krawędzie bloku rysowane na ścianach nie migoczą (z-fighting).
      const mat = new THREE.MeshBasicMaterial({ map: tex, polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1 });
      const mesh = new THREE.Mesh(new THREE.PlaneGeometry(pl.size[0], pl.size[1]), mat);
      mesh.position.set(...pl.p);
      mesh.rotation.set(...pl.rot);
      meshes.push(mesh);
    }
    this.legend = legendFor(this.field, this.meta, present);
    this.el.status.textContent = `Ściany zewnętrzne bloku ${nx}×${ny}×${nz} (proporcje jak nx:ny:nz)`
      + (top === 'surface' ? ' · górna ściana: rzut z góry (najwyższa niepusta komórka kolumny)' : ' · górna ściana: warstwa z = nz−1')
      + ' · lewy przycisk: obrót, prawy: przesuwanie, kółko: powiększenie';
    return meshes;
  }

  async buildSurface() {
    const reqs = [this.fetch('/api/result/surface', { field: 'height' }), this.fetch('/api/result/surface', { field: 'type' })];
    if (this.field !== 'type') reqs.push(this.fetch('/api/result/surface', { field: this.field }));
    const [hR, tR, vR] = await Promise.all(reqs);
    const [nx, ny, nz] = this.meta.dims;
    const w = hR.meta.width, h = hR.meta.height;  // kolumny x, wiersze y
    const heights = typed('uint16', hR.buffer), types = typed('uint8', tR.buffer);
    const vals = vR ? typed(vR.meta.dtype, vR.buffer) : null;
    const rgba = colorize(w, h, types, vals, this.field, this.ctx(), false);
    const s = Math.max(1, Math.ceil(Math.sqrt((w * h) / SURFACE_MAX_VERTICES)));
    const sx = Math.ceil(w / s), sy = Math.ceil(h / s);
    const exag = Number(this.el.exag.value);
    const posArr = new Float32Array(sx * sy * 3), colArr = new Float32Array(sx * sy * 3);
    const c = new THREE.Color();
    for (let gy = 0; gy < sy; gy++) {
      for (let gx = 0; gx < sx; gx++) {
        const x = Math.min(w - 1, gx * s), y = Math.min(h - 1, gy * s), i = y * w + x, k = gy * sx + gx;
        const [X, , Z] = this.pos(x + 0.5, y + 0.5, 0);
        posArr.set([X, heights[i] * exag - nz / 2, Z], 3 * k);
        c.setRGB(rgba[4 * i] / 255, rgba[4 * i + 1] / 255, rgba[4 * i + 2] / 255, THREE.SRGBColorSpace);
        colArr.set([c.r, c.g, c.b], 3 * k);
      }
    }
    const index = [];
    for (let gy = 0; gy < sy - 1; gy++) {
      for (let gx = 0; gx < sx - 1; gx++) {
        const a = gy * sx + gx, b = a + 1, cc = a + sx, d = cc + 1;
        index.push(a, b, d, a, d, cc);
      }
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(posArr, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(colArr, 3));
    geo.setIndex(index);
    geo.computeVertexNormals();
    const mesh = new THREE.Mesh(geo, new THREE.MeshLambertMaterial({ vertexColors: true, side: THREE.DoubleSide }));
    this.legend = legendFor(this.field, this.meta, new Set(types));
    this.el.status.textContent = `Powierzchnia: najwyższa niepusta komórka w każdej z ${w}×${h} kolumn, kolor = pole na tej wysokości`
      + (s > 1 ? ` · co ${s}. kolumna` : '') + (exag !== 1 ? ` · przewyższenie ×${exag}` : '');
    return [mesh];
  }

  async buildVoxels() {
    const reqs = [this.fetch('/api/result/voxels', { field: 'type', limit: VOXEL_LIMIT })];
    if (this.field !== 'type') reqs.push(this.fetch('/api/result/voxels', { field: this.field, limit: VOXEL_LIMIT }));
    const [tR, vR] = await Promise.all(reqs);
    const n = tR.meta.count;
    const xyz = typed('uint16', tR.buffer, 0, 3 * n);
    const types = typed('uint8', tR.buffer, 6 * n, n);
    const vals = vR ? typed(vR.meta.dtype, vR.buffer, 6 * n, n) : null;
    const rgba = colorize(n, 1, types, vals, this.field, this.ctx(), false);
    const mesh = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshLambertMaterial(), Math.max(n, 1));
    const m = new THREE.Matrix4(), c = new THREE.Color();
    for (let k = 0; k < n; k++) {
      m.makeTranslation(...this.pos(xyz[3 * k] + 0.5, xyz[3 * k + 1] + 0.5, xyz[3 * k + 2] + 0.5));
      mesh.setMatrixAt(k, m);
      mesh.setColorAt(k, c.setRGB(rgba[4 * k] / 255, rgba[4 * k + 1] / 255, rgba[4 * k + 2] / 255, THREE.SRGBColorSpace));
    }
    mesh.count = n;
    this.legend = legendFor(this.field, this.meta, new Set(types));
    this.el.status.textContent = `Woksele lawy i bazaltu${this.meta.mode === 'mc_full' ? ' (domena MC)' : ''}: ${n.toLocaleString('pl-PL')}`
      + (tR.meta.step > 1 ? ` z ${tR.meta.total.toLocaleString('pl-PL')} (co ${tR.meta.step}., limit ${VOXEL_LIMIT.toLocaleString('pl-PL')})` : '');
    return n ? [mesh] : [];
  }

  // ------------------------------------------------------------ odtwarzanie erupcji (etap 6)

  /** Dane odtwarzania (raz na wynik): opis z /api/result/replay, komórki lawy posortowane wg pojawienia, teren. */
  async replayData() {
    if (this.rd && this.rd.id === this.meta.id) return this.rd;
    const id = this.meta.id;
    const [info, cells, terr] = await Promise.all([
      getJSON(url('/api/result/replay', { id })),
      getBinary(url('/api/result/replay/cells', { id })),
      getBinary(url('/api/result/surface', { id, field: 'terrain' })),
    ]);
    info.flowCount = flowCountOf(info);
    const n = cells.meta.count, b = cells.buffer;
    const appear = typed('int32', b, 0, n), solidFrom = typed('int32', b, 4 * n, n);
    const temp = typed('float32', b, 8 * n, n), flowId = typed('int32', b, 12 * n, n);
    const xyz = typed('uint16', b, 16 * n, 3 * n);
    // Kolejność wg kroku pojawienia: w kroku k widoczne są komórki 0 … upto(k) − 1.
    const order = Array.from({ length: n }, (_, i) => i).sort((p, q) => appear[p] - appear[q]);
    const pick = (src, T) => { const o = new T(n); for (let i = 0; i < n; i++) o[i] = src[order[i]]; return o; };
    const sx = new Uint16Array(n), sy = new Uint16Array(n), sz = new Uint16Array(n);
    for (let i = 0; i < n; i++) { const j = order[i]; sx[i] = xyz[3 * j]; sy[i] = xyz[3 * j + 1]; sz[i] = xyz[3 * j + 2]; }
    this.rd = { id, info, n, step: cells.meta.step, total: cells.meta.total, x: sx, y: sy, z: sz,
      appear: pick(appear, Int32Array), solidFrom: pick(solidFrom, Int32Array), temp: pick(temp, Float32Array),
      flowId: pick(flowId, Int32Array), terrain: typed('uint16', terr.buffer), tw: terr.meta.width, th: terr.meta.height };
    this.replay.setInfo(info);
    return this.rd;
  }

  /** Liczba komórek pojawionych do kroku k (wyszukiwanie binarne w tablicy posortowanej wg pojawienia). */
  upto(k) {
    const a = this.rd.appear;
    let lo = 0, hi = this.rd.n;
    while (lo < hi) { const mid = (lo + hi) >> 1; if (a[mid] <= k) lo = mid + 1; else hi = mid; }
    return lo;
  }

  /** Powierzchnia w kroku k: wysokość najwyższej niepustej komórki kolumny i indeks komórki lawy na wierzchu (−1: teren). */
  surfaceAt(k) {
    const d = this.rd, w = d.tw, h = d.th;
    const height = new Uint16Array(d.terrain), topCell = new Int32Array(w * h).fill(-1);
    const m = this.upto(k);
    for (let i = 0; i < m; i++) {
      const c = d.y[i] * w + d.x[i];
      if (d.z[i] + 1 > height[c]) { height[c] = d.z[i] + 1; topCell[c] = i; }
    }
    return { height, topCell, w, h };
  }

  /** Stan komórki odtwarzania i (indeks w danych posortowanych) w kroku k: AIR / LAVA / BASALT. */
  cellState(i, k) {
    const d = this.rd;
    const t = d.solidFrom[i] === 2147483647 ? LAVA : BASALT;  // typ końcowy: bazalt ma zastygnięcie
    return stateAt(k, t, d.appear[i], d.solidFrom[i]);
  }

  /** Kolor komórki odtwarzania i w kroku k (st — stan z cellState, jeśli już policzony). */
  cellColor(i, k, st = this.cellState(i, k)) {
    const d = this.rd, info = d.info;
    const t = d.solidFrom[i] === 2147483647 ? LAVA : BASALT;
    return replayColor(st, tempAt(k, t, d.temp[i], d.solidFrom[i], info.steps, info.params), d.flowId[i], this.replay.mode, info, info.flowCount);
  }

  /** Rzut z góry w kroku k jako RGBA (wiersz 0 = y = 0): lawa wg odtwarzania, teren cieniowany wysokością;
   *  glow (opcjonalnie) — 1 dla kolumn z płynną lawą na wierzchu (emisja „żaru”). */
  topColors(sf, k, glow = null) {
    const { height, topCell, w, h } = sf, d = this.rd;
    let lo = Infinity, hi = -Infinity;
    for (let i = 0; i < d.terrain.length; i++) if (d.terrain[i] > 0) { lo = Math.min(lo, d.terrain[i]); hi = Math.max(hi, d.terrain[i]); }
    const out = new Uint8ClampedArray(w * h * 4);
    for (let c = 0; c < w * h; c++) {
      let col, g = 0;
      if (topCell[c] >= 0) {
        const st = this.cellState(topCell[c], k);
        col = this.cellColor(topCell[c], k, st);
        if (st === LAVA) g = 1;
      } else if (height[c] > 0) col = rockShade(hi > lo ? (height[c] - lo) / (hi - lo) : 1);
      else col = TYPE_RGB[AIR];
      out[4 * c] = col[0]; out[4 * c + 1] = col[1]; out[4 * c + 2] = col[2]; out[4 * c + 3] = 255;
      if (glow) glow[c] = g;
    }
    return out;
  }

  /** Obiekty sceny odtwarzania dla bieżącego widoku; klatki aktualizuje updateReplay(k). */
  async buildReplay() {
    const d = await this.replayData();
    const [nx, ny, nz] = this.meta.dims;
    this.legend = replayLegend(d.info, this.replay.mode);
    if (this.mode === 'surface') {
      const w = d.tw, h = d.th;
      let s = Math.max(1, Math.ceil(Math.sqrt((w * h) / SURFACE_MAX_VERTICES)));
      if (d.step > 1) s = Math.ceil(s / d.step) * d.step;  // próbkowane kolumny pakietu
      const sx = Math.ceil(w / s), sy = Math.ceil(h / s);
      const posArr = new Float32Array(sx * sy * 3), colArr = new Float32Array(sx * sy * 3);
      for (let gy = 0; gy < sy; gy++) {
        for (let gx = 0; gx < sx; gx++) {
          const [X, , Z] = this.pos(Math.min(w - 1, gx * s) + 0.5, Math.min(h - 1, gy * s) + 0.5, 0);
          posArr.set([X, 0, Z], 3 * (gy * sx + gx));
        }
      }
      const index = [];
      for (let gy = 0; gy < sy - 1; gy++) {
        for (let gx = 0; gx < sx - 1; gx++) { const a = gy * sx + gx, b = a + 1, c2 = a + sx, e = c2 + 1; index.push(a, b, e, a, e, c2); }
      }
      const glowArr = new Float32Array(sx * sy);
      const geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.BufferAttribute(posArr, 3));
      geo.setAttribute('color', new THREE.BufferAttribute(colArr, 3));
      geo.setAttribute('aGlow', new THREE.BufferAttribute(glowArr, 1));
      geo.setIndex(index);
      const mesh = new THREE.Mesh(geo, glowMaterial({ vertexColors: true, side: THREE.DoubleSide }));
      return withRv([mesh], { kind: 'surface', geo, posArr, colArr, glowArr, s, sx, sy, w, h });
    }
    if (this.mode === 'voxels') {
      const step = Math.max(1, Math.ceil(d.n / VOXEL_LIMIT));
      const idx = [];
      for (let i = 0; i < d.n; i += step) idx.push(i);
      const box = new THREE.BoxGeometry(1, 1, 1);
      const glowArr = new Float32Array(Math.max(idx.length, 1));
      box.setAttribute('aGlow', new THREE.InstancedBufferAttribute(glowArr, 1));
      const mesh = new THREE.InstancedMesh(box, glowMaterial(), Math.max(idx.length, 1));
      const m = new THREE.Matrix4(), c = new THREE.Color(1, 1, 1);
      idx.forEach((i, j) => {
        m.makeTranslation(...this.pos(d.x[i] + 0.5, d.y[i] + 0.5, d.z[i] + 0.5));
        mesh.setMatrixAt(j, m);
        mesh.setColorAt(j, c);
      });
      // Wierzchnia warstwa terenu (powierzchnia skały) dla orientacji — półprzezroczysta szarość.
      const terrain = this.terrainMesh();
      return withRv([terrain, mesh], { kind: 'voxels', mesh, idx, step, glowArr, glowAttr: box.attributes.aGlow });
    }
    // Ściany: side faces z pól odtwarzania (przekroje brzegowe), górna — rzut z góry w kroku k albo warstwa nz−1.
    const top = this.el.topSurface.checked ? 'surface' : 'layer';
    const fields = ['type', 'appear', 'solidFrom', 'temp', 'flowId'];
    const res = await Promise.all(fields.map((f) => this.fetch('/api/result/faces', { field: f, top: 'layer' })));
    const faces = [], meshes = [];
    const place = facePlacement(nx, ny, nz);
    for (const f of res[0].meta.faces) {
      const n = f.width * f.height;
      const arr = {};
      fields.forEach((name, j) => {
        const r = res[j];
        arr[name === 'type' ? 'type' : name] = typed(r.meta.dtype, r.buffer, r.meta.faces.find((g) => g.name === f.name).offset, n);
      });
      const tex = new THREE.DataTexture(new Uint8Array(n * 4), f.width, f.height, THREE.RGBAFormat);
      tex.colorSpace = THREE.SRGBColorSpace;
      tex.magFilter = THREE.NearestFilter;
      tex.minFilter = THREE.LinearFilter;
      const mat = new THREE.MeshBasicMaterial({ map: tex, polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1 });
      const pl = place[f.name];
      const mesh = new THREE.Mesh(new THREE.PlaneGeometry(pl.size[0], pl.size[1]), mat);
      mesh.position.set(...pl.p);
      mesh.rotation.set(...pl.rot);
      meshes.push(mesh);
      faces.push({ name: f.name, w: f.width, h: f.height, arr, tex, pl, topSurface: f.name === 'z1' && top === 'surface' });
    }
    return withRv(meshes, { kind: 'faces', faces });
  }

  /** Powierzchnia terenu (skała) — tło dla wokseli w odtwarzaniu. */
  terrainMesh() {
    const d = this.rd, w = d.tw, h = d.th, [, , nz] = this.meta.dims;
    const s = Math.max(1, Math.ceil(Math.sqrt((w * h) / SURFACE_MAX_VERTICES)));
    const sx = Math.ceil(w / s), sy = Math.ceil(h / s);
    const pos = new Float32Array(sx * sy * 3);
    for (let gy = 0; gy < sy; gy++) {
      for (let gx = 0; gx < sx; gx++) {
        const x = Math.min(w - 1, gx * s), y = Math.min(h - 1, gy * s);
        const [X, , Z] = this.pos(x + 0.5, y + 0.5, 0);
        pos.set([X, d.terrain[y * w + x] - nz / 2, Z], 3 * (gy * sx + gx));
      }
    }
    const index = [];
    for (let gy = 0; gy < sy - 1; gy++) {
      for (let gx = 0; gx < sx - 1; gx++) { const a = gy * sx + gx, b = a + 1, c = a + sx, e = c + 1; index.push(a, b, e, a, e, c); }
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    geo.setIndex(index);
    geo.computeVertexNormals();
    const rock = new THREE.Color().setRGB(TYPE_RGB[ROCK][0] / 255, TYPE_RGB[ROCK][1] / 255, TYPE_RGB[ROCK][2] / 255, THREE.SRGBColorSpace);
    return new THREE.Mesh(geo, new THREE.MeshLambertMaterial({ color: rock, side: THREE.DoubleSide }));
  }

  /** Klatka odtwarzania: CA — aktualizacja obiektów sceny; MC — ściany / powierzchnia z migawki MCS. */
  async drawReplay(k) {
    if (!this.meta || !this.replay.on) return;
    if (this.replay.source === 'mc') {
      this.mcsParam = this.replay.mcs[k];
      await this.load();
      return;
    }
    if (!this.rv) return;
    this.updateReplay(k);
    this.render();
  }

  updateReplay(k) {
    const rv = this.rv, d = this.rd, [nx, ny, nz] = this.meta.dims;
    if (rv.kind === 'surface') {
      const sf = this.surfaceAt(k);
      const glow = rv.glowCols || (rv.glowCols = new Float32Array(sf.w * sf.h));
      const rgba = this.topColors(sf, k, glow);
      const exag = Number(this.el.exag.value), c = new THREE.Color();
      for (let gy = 0; gy < rv.sy; gy++) {
        for (let gx = 0; gx < rv.sx; gx++) {
          const x = Math.min(rv.w - 1, gx * rv.s), y = Math.min(rv.h - 1, gy * rv.s), i = y * rv.w + x, q = gy * rv.sx + gx;
          rv.posArr[3 * q + 1] = sf.height[i] * exag - nz / 2;
          c.setRGB(rgba[4 * i] / 255, rgba[4 * i + 1] / 255, rgba[4 * i + 2] / 255, THREE.SRGBColorSpace);
          rv.colArr[3 * q] = c.r; rv.colArr[3 * q + 1] = c.g; rv.colArr[3 * q + 2] = c.b;
          rv.glowArr[q] = glow[i];
        }
      }
      rv.geo.attributes.position.needsUpdate = true;
      rv.geo.attributes.color.needsUpdate = true;
      rv.geo.attributes.aGlow.needsUpdate = true;
      rv.geo.computeVertexNormals();
      rv.geo.computeBoundingSphere();
    } else if (rv.kind === 'voxels') {
      const m = this.upto(k);
      let count = 0;
      const c = new THREE.Color();
      for (const i of rv.idx) {
        if (i >= m) break;
        const st = this.cellState(i, k);
        const col = this.cellColor(i, k, st);
        rv.mesh.setColorAt(count, c.setRGB(col[0] / 255, col[1] / 255, col[2] / 255, THREE.SRGBColorSpace));
        rv.glowArr[count] = st === LAVA ? 1 : 0;
        // Macierz instancji count = komórka i (kolejność wg pojawienia, co step-ta komórka).
        count++;
      }
      rv.mesh.count = count;
      if (rv.mesh.instanceColor) rv.mesh.instanceColor.needsUpdate = true;
      rv.glowAttr.needsUpdate = true;
    } else {
      const sf = this.rv.faces.some((f) => f.topSurface) ? this.surfaceAt(k) : null;
      for (const f of rv.faces) {
        let rgba = f.topSurface ? this.topColors(sf, k)
          : colorizeReplay(f.w, f.h, f.arr, k, d.info, this.replay.mode, false).rgba;
        if (f.pl.flipCols || f.pl.flipRows) rgba = flip(rgba, f.w, f.h, f.pl.flipCols, f.pl.flipRows);
        f.tex.image.data.set(rgba);
        f.tex.needsUpdate = true;
      }
    }
    const info = d.info;
    this.legend = replayLegend(info, this.replay.mode);
    showLegend(this.el.legend, this.legend);
    const sampled = d.step > 1 ? ` · kolumny co ${d.step} (${d.n.toLocaleString('pl-PL')} z ${d.total.toLocaleString('pl-PL')} komórek lawy)` : '';
    const vox = rv.kind === 'voxels' && rv.step > 1 ? ` · woksele co ${rv.step}.` : '';
    const names = { surface: 'powierzchnia (najwyższa niepusta komórka kolumny w tym kroku)', voxels: 'woksele lawy i bazaltu', faces: 'ściany zewnętrzne' };
    setText(this.el.status, `Odtwarzanie erupcji: ${names[rv.kind]} · ${nx}×${ny}×${nz}${sampled}${vox}`
      + (info.ventsExact ? '' : ' · kratery nieznane (stats.json): komórki z arrivalStep = 0 już w kroku 0'));
  }

  mcStatus() {
    const [nx, ny, nz] = this.meta.dims;
    this.el.status.textContent = `Odtwarzanie krystalizacji MC: migawka MCS ${this.mcsParam} · ${nx}×${ny}×${nz}`
      + (this.mode === 'voxels' ? ' · woksele pokazują stan końcowy (migawki tylko dla ścian i powierzchni)' : '');
    if (this.legend) this.legend.title = `Kryształ (MC), MCS ${this.mcsParam}`;
    showLegend(this.el.legend, this.legend);
  }

  /** Eksport odtwarzania (klatki PNG w ZIP albo WebM): obraz sceny + tytuł z krokiem + legenda. */
  async exportReplay(kind) {
    if (!this.inited || !this.meta || !this.replay.on) return;
    const bar = this.replay;
    const src = this.renderer.domElement;
    const r = this.el.wrap.getBoundingClientRect();
    const legendW = 240, head = 34, scale = src.width / r.width;
    const out = document.createElement('canvas');
    out.width = Math.round((r.width + legendW) * scale);
    out.height = Math.round((r.height + head) * scale);
    const names = { faces: 'ściany', surface: 'powierzchnia', voxels: 'woksele' };
    const draw = async (k, canvas) => {
      await this.drawReplay(k);
      this.render();
      const g = canvas.getContext('2d');
      g.setTransform(scale, 0, 0, scale, 0, 0);
      g.fillStyle = themeColors().panel; g.fillRect(0, 0, r.width + legendW, r.height + head);
      g.fillStyle = skyGradient(g, 0, head, r.width, r.height); g.fillRect(0, head, r.width, r.height);
      const label = bar.source === 'ca' ? `krok ${k} / ${bar.info.steps}` : `MCS ${bar.mcs[k]}`;
      frameTitle(g, `${this.meta.name}: 3D, ${names[this.mode]}, ${label}`);
      g.drawImage(src, 0, head, r.width, r.height);
      drawLegend(g, this.legend, r.width + 16, head + 8, legendW - 28);
    };
    const base = `${this.meta.name}_3d_${this.mode}_${bar.source === 'ca' ? 'erupcja' : 'mc'}`.replace(/[^\w.-]+/g, '_');
    const k0 = bar.k;
    try {
      if (kind === 'frames') await exportFrames(bar, out, draw, base);
      else await recordWebM(bar, out, draw, base);
    } finally {
      await bar.go(k0);
    }
  }

  /** Krawędzie bloku, strzałki osi i podpisy. */
  buildFrame() {
    const [nx, ny, nz] = this.meta.dims;
    const out = [];
    const th = themeColors();
    const frame = new THREE.Color().setStyle(th.frame3d, THREE.SRGBColorSpace);
    const edges = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(nx, nz, ny)),
      new THREE.LineBasicMaterial({ color: frame, transparent: true, opacity: 0.85 }));
    out.push(edges);
    const D = Math.max(nx, ny, nz), len = Math.max(4, D * 0.18);
    const o = new THREE.Vector3(...this.pos(0, 0, 0)).add(new THREE.Vector3(-0.02 * D, -0.02 * D, 0.02 * D));
    const axes = [['x', [1, 0, 0], nx], ['y', [0, 0, -1], ny], ['z', [0, 1, 0], nz]];
    for (const [name, dir, n] of axes) {
      const d = new THREE.Vector3(...dir);
      out.push(new THREE.ArrowHelper(d, o, len, new THREE.Color().setStyle(th.accentText, THREE.SRGBColorSpace), len * 0.18, len * 0.09));
      const label = textSprite(`${name}${name === 'z' ? ' (pion)' : ''}  0…${n - 1}`, D * 0.045, th);
      label.position.copy(o.clone().add(d.multiplyScalar(len * 1.25)));
      out.push(label);
    }
    return out;
  }

  resetCamera() {
    if (!this.meta || !this.inited) return;
    const [nx, ny, nz] = this.meta.dims;
    const D = Math.max(nx, ny, nz);
    let p;
    if (ny === 1) p = [0.35 * D, 0.45 * D, 1.9 * D];        // przekrój x–z: widok z przodu
    else if (nz === 1) p = [0.2 * D, 1.95 * D, 0.6 * D];    // płaszczyzna x–y: widok z góry
    else p = [1.45 * D, 1.25 * D, 1.85 * D];
    this.camera.position.set(...p);
    this.camera.near = D / 500; this.camera.far = D * 20;
    this.camera.updateProjectionMatrix();
    this.controls.target.set(0, 0, 0);
    this.controls.update();
    this.camSet = true;
    this.render();
  }

  exportPNG() {
    if (!this.inited || !this.meta) return;
    this.render();
    const src = this.renderer.domElement;
    const r = this.el.wrap.getBoundingClientRect();
    const legendW = 240, head = 34, scale = src.width / r.width;
    const W = Math.round(r.width) + legendW, H = Math.round(r.height) + head;
    const out = document.createElement('canvas');
    out.width = W * scale; out.height = H * scale;
    const g = out.getContext('2d'), th = themeColors();
    g.scale(scale, scale);
    g.fillStyle = th.panel; g.fillRect(0, 0, W, H);  // eksport w kolorach bieżącego motywu (jasny — do druku)
    g.fillStyle = skyGradient(g, 0, head, r.width, r.height); g.fillRect(0, head, r.width, r.height);
    g.fillStyle = th.ink; g.font = `600 14px ${th.font}`; g.textBaseline = 'top';
    const names = { faces: 'ściany zewnętrzne', surface: 'powierzchnia', voxels: 'woksele lawy' };
    const [nx, ny, nz] = this.meta.dims;
    g.fillText(`${this.meta.name}: 3D, ${names[this.mode]} (${nx}×${ny}×${nz}), kolor: ${FIELD_LABELS[this.field]}`, 12, 10);
    g.drawImage(src, 0, head, r.width, r.height);
    drawLegend(g, this.legend, r.width + 16, head + 8, legendW - 28);
    download(out, `${this.meta.name}_3d_${this.mode}_${this.field}.png`);
  }
}

/** Lista obiektów sceny z dołączonym opisem obiektów aktualizowanych co klatkę odtwarzania. */
function withRv(objects, rv) {
  objects.rv = rv;
  return objects;
}

/** Położenie i obrót płaszczyzny każdej ściany (PlaneGeometry leży w XY, normalna +Z) oraz odbicia tekstury,
 *  tak żeby wiersz/kolumna danych trafiły na właściwą komórkę ściany (opis w docs/interfejs-graficzny.md). */
function facePlacement(nx, ny, nz) {
  return {
    x0: { size: [ny, nz], p: [-nx / 2, 0, 0], rot: [0, -Math.PI / 2, 0], flipCols: true },
    x1: { size: [ny, nz], p: [nx / 2, 0, 0], rot: [0, Math.PI / 2, 0] },
    y0: { size: [nx, nz], p: [0, 0, ny / 2], rot: [0, 0, 0] },
    y1: { size: [nx, nz], p: [0, 0, -ny / 2], rot: [0, Math.PI, 0], flipCols: true },
    z0: { size: [nx, ny], p: [0, -nz / 2, 0], rot: [Math.PI / 2, 0, 0], flipRows: true },
    z1: { size: [nx, ny], p: [0, nz / 2, 0], rot: [-Math.PI / 2, 0, 0] },
  };
}

/** Odbicie obrazu RGBA w poziomie i/lub pionie. */
function flip(rgba, w, h, cols, rows) {
  const out = new Uint8ClampedArray(rgba.length);
  for (let r = 0; r < h; r++) {
    const sr = rows ? h - 1 - r : r;
    for (let c = 0; c < w; c++) {
      const sc = cols ? w - 1 - c : c;
      const s = (sr * w + sc) * 4, d = (r * w + c) * 4;
      out[d] = rgba[s]; out[d + 1] = rgba[s + 1]; out[d + 2] = rgba[s + 2]; out[d + 3] = rgba[s + 3];
    }
  }
  return out;
}

/** Lambert z „żarem”: atrybut aGlow (0…1, na wierzchołek albo instancję) dodaje emisję w kolorze komórki —
 *  płynna lawa w odtwarzaniu świeci także na zboczu odwróconym od słońca. Bez atrybutu aGlow = 0 (brak emisji). */
function glowMaterial(params = {}) {
  const m = new THREE.MeshLambertMaterial(params);
  m.onBeforeCompile = (sh) => {
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nattribute float aGlow;\nvarying float vGlow;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvGlow = aGlow;');
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', '#include <common>\nvarying float vGlow;')
      .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\ntotalEmissiveRadiance += vColor.rgb * vGlow * 0.75;');
  };
  m.customProgramCacheKey = () => 'lava-glow';
  return m;
}

function textSprite(text, height, th) {
  const c = document.createElement('canvas');
  const g = c.getContext('2d');
  const fs = 48;
  g.font = `600 ${fs}px ${th.font}`;
  c.width = Math.ceil(g.measureText(text).width) + 16; c.height = fs + 16;
  g.font = `600 ${fs}px ${th.font}`;
  g.fillStyle = th.ink; g.textBaseline = 'middle';
  g.fillText(text, 8, c.height / 2);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false, transparent: true }));
  sp.scale.set((height * c.width) / c.height, height, 1);
  sp.renderOrder = 10;
  return sp;
}

function disposeAll(objects) {
  for (const o of objects) {
    o.traverse?.((x) => {
      x.geometry?.dispose();
      const mats = Array.isArray(x.material) ? x.material : x.material ? [x.material] : [];
      for (const m of mats) { m.map?.dispose(); m.dispose(); }
    });
  }
}
