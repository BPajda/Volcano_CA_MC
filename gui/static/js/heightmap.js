// Mapa wysokości terenu w zakładce „Nowa symulacja” (etap 5 — mechanizmy danych wejściowych):
//  - wybór mapy z configs/heightmaps/ ustawia terrain.type = "file", terrain.file i wymiary space.nx × ny
//    z mapy (nz — z zapasem nad najwyższym punktem), wybór „stożek” wraca do terrain.type = "cone",
//  - miniatura mapy (jasne = wyżej, północ u góry — jak rzut z góry w podglądzie 2D),
//  - import pliku CSV (sprawdzenie formatu, opcjonalnie przeskalowanie do nx × ny) albo obrazu PNG / JPG
//    w odcieniach szarości (backend: jasność -> wysokość, skalowanie, wygładzanie; gui/heightmap.py).

import { getBinary, getJSON, postJSON, typed, url } from './api.js';
import { onThemeChange, themeColors } from './theme.js';
import { $, esc, notice } from './util.js';

const HEADROOM = 15;  // tyle komórek nad najwyższym punktem mapy zostawiamy na lawę, gdy nz jest za małe

export class HeightmapPanel {
  /** hooks: form() — ConfigForm z zakładki „Nowa symulacja”. */
  constructor(hooks) {
    this.hooks = hooks;
    this.maps = [];
    this.thumbFor = undefined;  // undefined = nic nie narysowano (null = stożek z generatora)
    this.file = null;
    $('#hm-select').addEventListener('change', () => this.onSelect());
    $('#hm-import-open').addEventListener('click', () => this.openImport(true));
    $('#hm-import-cancel').addEventListener('click', () => this.openImport(false));
    $('#hm-file').addEventListener('change', (e) => this.onFile(e.target.files[0]));
    $('#hm-import-run').addEventListener('click', () => this.runImport());
    onThemeChange(() => { const f = this.thumbFor; this.thumbFor = undefined; this.drawThumb(f); });
  }

  async refresh() {
    try {
      this.maps = await getJSON('/api/heightmaps');
    } catch {
      this.maps = [];
    }
    const sel = $('#hm-select');
    const cur = sel.value;
    sel.innerHTML = '<option value="">— stożek z generatora (terrain.type = cone) —</option>'
      + this.maps.filter((m) => !m.error).map((m) => `<option value="${esc(m.file)}">${esc(m.name)} (${m.nx}×${m.ny}, wys. do ${m.max.toFixed(0)})</option>`).join('');
    sel.value = [...sel.options].some((o) => o.value === cur) ? cur : '';
  }

  /** Formularz się zmienił — lista i miniatura pokazują mapę z terrain.file (gdy terrain.type = file). */
  sync(cfg) {
    const file = cfg.terrain?.type === 'file' ? cfg.terrain?.file || '' : '';
    const known = this.maps.find((m) => m.file === file);
    const sel = $('#hm-select');
    sel.value = known ? file : '';
    const classic = cfg.ca?.mode === 'classic' || (cfg.mc?.enabled && cfg.mc?.domain === 'full');
    const info = $('#hm-info');
    if (known) {
      const sp = cfg.space || {};
      let text = `<code>${esc(known.file)}</code> — ${known.nx}×${known.ny} kolumn, wysokość ${known.min.toFixed(1)}–${known.max.toFixed(1)} komórek`;
      if (known.note) text += `<br>${esc(known.note)}`;
      if (known.geo) {
        const g = known.geo, b = g.bbox;
        text += `<br>Prawdziwy teren: ${b.south}–${b.north}° N, ${b.west}–${b.east}° E · ${g.metersPerCell?.toFixed(0)} m/komórkę`
          + ` w poziomie, ${g.metersPerCellZ?.toFixed(1)} m w pionie (przewyższenie ×${g.exaggeration?.toFixed(1)}) · ${esc(g.source || '')}`
          + ` (przypisanie danych: <code>configs/heightmaps/README.md</code>)`;
      }
      if (sp.nx !== known.nx || sp.ny !== known.ny) text += `<br>${notice('error', `Wymiary siatki ${sp.nx}×${sp.ny} nie pasują do mapy ${known.nx}×${known.ny} — wybierz mapę ponownie albo popraw space.nx / space.ny.`)}`;
      if (classic) text += `<br>${notice('info', 'W trybie classic / MC full teren jest pomijany.')}`;
      info.innerHTML = text;
    } else if (file) {
      info.innerHTML = `terrain.file = <code>${esc(file)}</code> (plik spoza configs/heightmaps/ — bez podglądu)`;
    } else {
      info.textContent = 'Teren ze stożka wulkanu (parametry w sekcji „Teren”). Mapa z pliku daje dowolny kształt: kalderę z wyłomem, kanion, dwa wulkany.';
    }
    this.drawThumb(known ? known.file : null);
  }

  onSelect() {
    const form = this.hooks.form();
    const file = $('#hm-select').value;
    if (!file) {
      form.setValues({ 'terrain.type': 'cone' });
      return;
    }
    const m = this.maps.find((x) => x.file === file);
    const cfg = form.get();
    // Mapa z prawdziwego terenu (tools/fetch_dem.py) ma skalę pionową wyliczoną dla swojego nz — bierzemy je z metadanych.
    const nz = m.geo?.nz ? m.geo.nz : Math.max(cfg.space?.nz || 1, Math.ceil(m.max) + HEADROOM);
    form.setValues({ 'terrain.type': 'file', 'terrain.file': m.file, 'space.nx': m.nx, 'space.ny': m.ny, 'space.nz': nz });
  }

  async drawThumb(file) {
    const canvas = $('#hm-thumb');
    const ctx = canvas.getContext('2d');
    if (file === this.thumbFor) return;
    this.thumbFor = file;
    const th = themeColors();
    ctx.fillStyle = th.viewBg;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    if (!file) {
      ctx.fillStyle = th.muted;
      ctx.font = `12px ${th.font}`;
      ctx.textAlign = 'center';
      ctx.fillText('stożek z generatora', canvas.width / 2, canvas.height / 2);
      return;
    }
    try {
      const { meta, buffer } = await getBinary(url('/api/heightmaps/data', { file }));
      if (this.thumbFor !== file) return;
      drawHeights(canvas, typed('float32', buffer), meta.width, meta.height, meta.min, meta.max);
    } catch { /* brak podglądu — lista i tak działa */ }
  }

  // ------------------------------------------------------------ import

  openImport(on) {
    $('#hm-import').hidden = !on;
    if (on) {
      const cfg = this.hooks.form().get();
      const sp = cfg.space || {};
      $('#hm-nx').value = sp.nx > 1 ? sp.nx : 120;
      $('#hm-ny').value = sp.ny > 1 ? sp.ny : 120;
      $('#hm-nz').value = sp.nz || 80;
      $('#hm-import-msg').innerHTML = '';
    }
  }

  onFile(file) {
    this.file = file || null;
    const img = $('#hm-src-preview');
    img.hidden = true;
    $('#hm-image-opts').hidden = $('#hm-csv-opts').hidden = true;
    if (!file) return;
    const isImage = /\.(png|jpe?g)$/i.test(file.name) || file.type.startsWith('image/');
    this.kind = isImage ? 'image' : 'csv';
    $('#hm-image-opts').hidden = !isImage;
    $('#hm-csv-opts').hidden = isImage;
    if (!$('#hm-name').value) $('#hm-name').value = file.name.replace(/\.[^.]+$/, '');
    if (isImage) {
      img.src = URL.createObjectURL(file);
      img.hidden = false;
      img.onload = () => {
        // Proporcje obrazu: ny dopasowane do nx, jeśli użytkownik nie zmienił ny ręcznie.
        const nx = Number($('#hm-nx').value) || 120;
        $('#hm-ny').value = Math.max(1, Math.round((nx * img.naturalHeight) / img.naturalWidth));
      };
    }
  }

  async runImport() {
    const msg = $('#hm-import-msg');
    if (!this.file) {
      msg.innerHTML = notice('error', 'Wybierz plik CSV, PNG albo JPG.');
      return;
    }
    const cfg = this.hooks.form().get();
    const body = { name: $('#hm-name').value.trim() || this.file.name, kind: this.kind };
    msg.innerHTML = notice('info', 'Import…');
    try {
      if (this.kind === 'image') {
        body.data = await readBase64(this.file);
        Object.assign(body, {
          nx: Number($('#hm-nx').value), ny: Number($('#hm-ny').value), nz: Number($('#hm-nz').value),
          maxHeight: Number($('#hm-max').value), base: Number($('#hm-base').value), smooth: Number($('#hm-smooth').value),
          invert: $('#hm-invert').checked, normalize: $('#hm-normalize').checked,
        });
      } else {
        body.data = await this.file.text();
        Object.assign(body, { nx: cfg.space?.nx, ny: cfg.space?.ny, nz: cfg.space?.nz, resize: $('#hm-resize').checked });
      }
      const res = await postJSON('/api/heightmaps', body);
      await this.refresh();
      $('#hm-select').value = res.file;
      this.onSelect();
      msg.innerHTML = notice('ok', `Zapisano <code>${esc(res.file)}</code> — ${res.nx}×${res.ny}, wysokość ${res.min.toFixed(1)}–${res.max.toFixed(1)}.
        Formularz: terrain.type = file, wymiary siatki z mapy.`) + res.warnings.map((w) => notice('warn', esc(w))).join('');
    } catch (err) {
      msg.innerHTML = (err.errors || [err.message]).map((e) => notice('error', esc(e))).join('');
    }
  }
}

function readBase64(file) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result).split(',', 2)[1] || '');
    r.onerror = () => reject(new Error(`nie można odczytać pliku ${file.name}`));
    r.readAsDataURL(file);
  });
}

/** Mapa wysokości (wiersz 0 = y = 0) jako obraz w skali szarości dopasowany do canvasu; y rośnie do góry. */
export function drawHeights(canvas, h, w, ht, lo, hi) {
  const ctx = canvas.getContext('2d');
  const img = ctx.createImageData(w, ht);
  for (let y = 0; y < ht; y++) {
    for (let x = 0; x < w; x++) {
      const t = hi > lo ? (h[y * w + x] - lo) / (hi - lo) : 0.5;
      const v = Math.round(255 * (0.12 + 0.83 * t));
      const o = ((ht - 1 - y) * w + x) * 4;
      img.data[o] = v; img.data[o + 1] = v; img.data[o + 2] = Math.round(v * 0.97); img.data[o + 3] = 255;
    }
  }
  const tmp = document.createElement('canvas');
  tmp.width = w;
  tmp.height = ht;
  tmp.getContext('2d').putImageData(img, 0, 0);
  const scale = Math.min(canvas.width / w, canvas.height / ht);
  const dw = w * scale, dh = ht * scale;
  ctx.fillStyle = themeColors().viewBg;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.imageSmoothingEnabled = scale < 1;
  ctx.drawImage(tmp, (canvas.width - dw) / 2, (canvas.height - dh) / 2, dw, dh);
}
