// Formularz „Nowa symulacja” — budowany z domyślnego configu silnika (engine --print-defaults),
// więc zawsze ma te same klucze co silnik. SCHEMA dodaje tylko opisy po polsku: etykiety, jednostki,
// podpowiedzi, listy wyboru i reguły „nie dotyczy” (pola wyszarzone w danym trybie). Klucz z silnika
// bez opisu w SCHEMA też trafia do formularza (pole ogólne) — formularz nie gubi parametrów.
// Błędy walidacji silnika: pole podświetlone + komunikat pod polem (markErrors), pełna lista nad przyciskami.

import { esc, icon } from './util.js';

const ENUMS = {
  grid: [['vector', 'vector — płaska tablica'], ['matrix', 'matrix — vector<vector<vector>>']],
  boundary: [['absorbing', 'absorbujące'], ['periodic', 'periodyczne']],
  neighborhood: [['von_neumann', 'von Neumann (4 / 6)'], ['moore', 'Moore (8 / 26)'],
    ['pentagonal', 'losowe pentagonalne (5 / 17)'], ['hexagonal', 'losowe heksagonalne (6, tylko 2D)']],
  'terrain.type': [['cone', 'stożek wulkanu (generator)'], ['file', 'mapa wysokości z pliku CSV']],
  'vents.placement': [['crater', 'w kraterze szczytowym'], ['random', 'losowo na zboczu (szczeliny)'],
    ['positions', 'w zadanych miejscach (lista / kliknięcie na mapie)']],
  'ca.mode': [['lava', 'lava — spływ lawy'], ['classic', 'classic — rozrost ziaren bez wulkanu']],
  'ca.sweep': [['front', 'front — automat frontalny'], ['full', 'full — pełny przebieg']],
  'mc.domain': [['basalt', 'basalt — zastygła lawa z wyniku CA'], ['full', 'full — cała przestrzeń (bez CA)']],
  'output.format': [['txt', 'txt'], ['bin', 'bin (13 B/komórkę, szybki zapis)'], ['both', 'txt + bin'], ['none', 'bez zapisu mikrostruktury']],
  'mc.update': [['random', 'random — losowe komórki po kolei (wariant naiwny)'], ['checkerboard', 'checkerboard — szachownica (równolegle)']],
  'parallel.schedule': [['static', 'static — równe pasy warstw'], ['dynamic', 'dynamic — porcje na żądanie'], ['guided', 'guided — malejące porcje']],
  'parallel.affinity': [['none', 'none — o rdzeniach decyduje system'], ['pcores', 'pcores — jeden wątek na rdzeń P']],
  'parallel.priority': [['normal', 'normal — zwykły'], ['high', 'high — wysoki (pomiary)']],
  'mpi.exchange': [['always', 'always — warstwy brzegowe co krok'], ['changed', 'changed — tylko zmienione warstwy']],
  'mpi.pack': [['manual', 'manual — pakowanie do bufora (memcpy)'], ['datatype', 'datatype — typ pochodny MPI, bez bufora']],
  'mpi.bcast': [['json', 'json — scalony config jako tekst'], ['struct', 'struct — struktury (MPI_Type_create_struct)']],
  'mpi.io': [['gather', 'gather — zebranie na proces 0 i zapis tam'], ['mpiio', 'mpiio — każdy proces pisze swój pas (MPI-IO)']],
};

// Grupy formularza (kolejność i podpisy jak w configu). keys — ścieżki z kropkami.
export const GROUPS = [
  { id: 'space', title: 'Przestrzeń', keys: ['space.nx', 'space.ny', 'space.nz'],
    note: '2D = dokładnie jeden wymiar równy 1. Oś z jest pionowa (z = 0 to spód); w trybie lava 2D to przekrój x–z (ny = 1).' },
  { id: 'general', title: 'Ogólne', keys: ['grid', 'boundary', 'neighborhood', 'rngSeed'] },
  { id: 'terrain', title: 'Teren', keys: ['terrain.type', 'terrain.peakHeight', 'terrain.baseRadius', 'terrain.craterRadius',
    'terrain.craterDepth', 'terrain.noise', 'terrain.file'] },
  { id: 'vents', title: 'Kratery / zarodki', keys: ['vents.count', 'vents.placement', 'vents.positions', 'vents.eruptionSteps',
    'vents.eruptTemp'] },
  { id: 'ca', title: 'Automat komórkowy (CA)', keys: ['ca.mode', 'ca.maxSteps', 'ca.coolingAmbient', 'ca.coolingLateral',
    'ca.coolingFall', 'ca.solidusTemp', 'ca.ponding', 'ca.sweep'] },
  { id: 'mc', title: 'Monte Carlo (krystalizacja, model Pottsa)', keys: ['mc.enabled', 'mc.domain', 'mc.Q', 'mc.mcs', 'mc.J',
    'mc.kT', 'mc.mobilityFromCooling', 'mc.mobilityMin', 'mc.statsEvery', 'mc.snapshotsEvery', 'mc.update'] },
  { id: 'output', title: 'Wyjście', keys: ['output.format', 'output.snapshotsEvery'] },
  { id: 'parallel', title: 'Równoległość (OpenMP)', keys: ['parallel.threads', 'parallel.schedule', 'parallel.chunk', 'parallel.affinity',
    'parallel.priority'],
    note: 'Wynik nie zależy od liczby wątków ani harmonogramu (poza mc.update: random i checkerboard to różne procesy losowe). Pomiary: rdzenie P, najwyżej 8 wątków.' },
  { id: 'mpi', title: 'MPI (program engine_mpi)', keys: ['mpi.exchange', 'mpi.pack', 'mpi.bcast', 'mpi.io'],
    note: 'Dotyczy tylko wersji rozproszonej (mpiexec -n N engine_mpi); GUI uruchamia engine — wynik od tego pola nie zależy.' },
];

// Opis pól: label, unit, hint, int (liczba całkowita), min, step.
const SCHEMA = {
  'space.nx': { label: 'nx', unit: 'komórek', int: true, min: 1 },
  'space.ny': { label: 'ny', unit: 'komórek', int: true, min: 1 },
  'space.nz': { label: 'nz (wysokość)', unit: 'komórek', int: true, min: 1 },
  grid: { label: 'Reprezentacja siatki', hint: 'obie dają bitowo ten sam wynik (engine --benchmark)' },
  boundary: { label: 'Warunki brzegowe', hint: 'w trybie lava oś pionowa nigdy nie jest periodyczna' },
  neighborhood: { label: 'Sąsiedztwo', hint: 'liczba sąsiadów 2D / 3D; warianty losowe co krok z hasha' },
  rngSeed: { label: 'Ziarno losowania', int: true, min: 0, hint: 'teren, kratery, remisy, sąsiedztwa losowe, MC' },
  'terrain.type': { label: 'Rodzaj terenu' },
  'terrain.peakHeight': { label: 'Wysokość szczytu', unit: 'komórek', min: 0, step: 1 },
  'terrain.baseRadius': { label: 'Promień podstawy', unit: 'komórek', min: 0, step: 1 },
  'terrain.craterRadius': { label: 'Promień krateru', unit: 'komórek', min: 0, step: 1 },
  'terrain.craterDepth': { label: 'Głębokość krateru', unit: 'komórek', min: 0, step: 1 },
  'terrain.noise': { label: 'Szum terenu', unit: '× wysokość', min: 0, step: 0.01, hint: 'amplituda nierówności, 0–1' },
  'terrain.file': { label: 'Plik mapy wysokości', text: true, hint: 'CSV: ny wierszy × nx wartości; ścieżka względem volcano-ca-mc' },
  'vents.count': { label: 'Liczba kraterów / ziaren', int: true, min: 1, hint: 'lava: kratery (zarodki strumieni); classic: zarodki ziaren' },
  'vents.placement': { label: 'Rozmieszczenie kraterów' },
  'vents.positions': { label: 'Położenia kraterów', json: true,
    hint: 'lista kolumn [[x, y], …] (JSON) dla placement = positions; najwygodniej kliknięciem w panelu „Kratery na mapie”' },
  'vents.eruptionSteps': { label: 'Czas erupcji', unit: 'kroków', int: true, min: 0, hint: 'przez tyle kroków krater ma stałą temperaturę' },
  'vents.eruptTemp': { label: 'Temperatura erupcji', unit: '°C', step: 10 },
  'ca.mode': { label: 'Tryb automatu' },
  'ca.maxSteps': { label: 'Limit kroków', unit: 'kroków', int: true, min: 0, hint: 'maks. 65535; zwykle koniec wcześniej (brak lawy / brak zmian)' },
  'ca.coolingAmbient': { label: 'Stygnięcie na krok', unit: '°C', min: 0, step: 0.1 },
  'ca.coolingLateral': { label: 'Stygnięcie przy rozlewaniu', unit: '°C', min: 0, step: 0.5 },
  'ca.coolingFall': { label: 'Stygnięcie przy spływie w dół', unit: '°C', min: 0, step: 0.5 },
  'ca.solidusTemp': { label: 'Temperatura zastygania', unit: '°C', step: 10, hint: 'poniżej lawa zastyga w bazalt' },
  'ca.ponding': { label: 'Wypełnianie zagłębień', hint: 'lawa podnosi się w kraterze do poziomu przelewu' },
  'ca.sweep': { label: 'Przetwarzanie kroku', hint: 'front — tylko komórki, które mogą się zmienić (szybciej); full — pełny przebieg (wersja referencyjna); wynik ten sam' },
  'mc.enabled': { label: 'Włącz Monte Carlo' },
  'mc.domain': { label: 'Domena MC' },
  'mc.Q': { label: 'Liczba orientacji Q', int: true, min: 2 },
  'mc.mcs': { label: 'Liczba kroków MCS', unit: 'MCS', int: true, min: 0 },
  'mc.J': { label: 'Energia granicy J', step: 0.1, min: 0 },
  'mc.kT': { label: 'Temperatura kT', step: 0.1, min: 0, hint: '0 = akceptacja tylko ΔE ≤ 0 (wariant naiwny)' },
  'mc.mobilityFromCooling': { label: 'Mobilność ze stygnięcia', hint: 'długo płynna lawa → duże kryształy (tylko basalt)' },
  'mc.mobilityMin': { label: 'Mobilność minimalna', step: 0.01, min: 0, hint: '0–1, dla najszybciej zastygłej lawy' },
  'mc.statsEvery': { label: 'Statystyki co', unit: 'MCS', int: true, min: 1, hint: 'wiersze mc_stats.csv (czas poza mcSim)' },
  'mc.snapshotsEvery': { label: 'Migawki kryształów co', unit: 'MCS', int: true, min: 0,
    hint: '0 = wyłączone; mc_snapshots/mcs_*.bin — odtwarzanie wzrostu ziaren w podglądzie (czas poza mcSim)' },
  'mc.update': { label: 'Kolejność prób MC', hint: 'random — wariant naiwny, zawsze 1 wątek; checkerboard — kolory komórek niebędących sąsiadami, równolegle (inny proces losowy, statystycznie zgodny)' },
  'parallel.threads': { label: 'Liczba wątków', int: true, min: 0, hint: '1 = jeden wątek (jak przed zrównolegleniem); 0 = wszystkie wątki OpenMP; pomiary: 1–8 (rdzenie P)' },
  'parallel.schedule': { label: 'Harmonogram', hint: 'podział warstw (pasów z) między wątki; lawa (front): static z porcją 1, pełny przebieg: guided' },
  'parallel.chunk': { label: 'Porcja harmonogramu', unit: 'warstw', int: true, min: 0, hint: '0 = domyślna OpenMP (static: równe bloki, dynamic/guided: 1)' },
  'parallel.affinity': { label: 'Przypinanie wątków', hint: 'pcores — wątek i na i-tym rdzeniu wydajnym (P), bez drugiego wątku SMT' },
  'parallel.priority': { label: 'Priorytet procesu', hint: 'high — silnik sam podnosi priorytet (pomiary wielowątkowe i MPI; jak --high-priority); GUI i tak uruchamia zadania wielowątkowe z wysokim priorytetem' },
  'mpi.exchange': { label: 'Wymiana warstw brzegowych', hint: 'always — co krok CA / kolor MC; changed — warstwa tylko, gdy się zmieniła (mniej bajtów, ten sam wynik)' },
  'mpi.pack': { label: 'Komunikat warstw brzegowych', hint: 'manual — pola kopiowane do bufora i z bufora; datatype — typ pochodny MPI opisuje pola w siatce (wysyłka i odbiór bez kopii); wynik ten sam' },
  'mpi.bcast': { label: 'Rozsyłanie parametrów', hint: 'json — proces 0 rozsyła scalony config jako tekst; struct — blok liczbowy configu i lista kraterów / zarodków jako struktury MPI; wynik ten sam' },
  'mpi.io': { label: 'Zapis wyników', hint: 'gather — pasy zbierane na proces 0, który zapisuje pliki; mpiio — każdy proces zapisuje swój pas do wspólnego pliku (w WSL tylko na ext4); pliki bajtowo te same' },
  'output.format': { label: 'Format mikrostruktury', hint: 'bin czyta się w GUI szybciej; txt — czytelny tekst x y z type flowId temp' },
  'output.snapshotsEvery': { label: 'Migawki co', unit: 'kroków', int: true, min: 0, hint: '0 = wyłączone; pliki snapshots/step_*.bin' },
};

/** Etykieta pola po polsku (np. do listy kluczy w zakładce „Seria”); bez opisu — sama ścieżka. */
export function fieldLabel(path) {
  return SCHEMA[path]?.label || path;
}

/** Grupa formularza (sekcja configu) dla ścieżki — do grupowania listy kluczy. */
export function fieldGroup(path) {
  return GROUPS.find((g) => g.keys.includes(path))?.title || 'Pozostałe parametry';
}

export const getPath = (obj, path) => path.split('.').reduce((o, k) => (o == null ? undefined : o[k]), obj);
export function setPath(obj, path, value) {
  const parts = path.split('.');
  let o = obj;
  for (const p of parts.slice(0, -1)) { if (typeof o[p] !== 'object' || o[p] === null) o[p] = {}; o = o[p]; }
  o[parts[parts.length - 1]] = value;
}
const clone = (x) => JSON.parse(JSON.stringify(x));

/** Ścieżki wszystkich liści obiektu (kolejność kluczy z silnika). */
export function leafPaths(obj, prefix = '') {
  const out = [];
  for (const [k, v] of Object.entries(obj)) {
    const p = prefix ? `${prefix}.${k}` : k;
    if (v !== null && typeof v === 'object' && !Array.isArray(v)) out.push(...leafPaths(v, p));
    else out.push(p);
  }
  return out;
}

/** Scalanie jak w silniku: config użytkownika na domyślnym (klucze z "_" pomijane). */
export function mergeConfig(base, patch) {
  const out = clone(base);
  for (const [k, v] of Object.entries(patch || {})) {
    if (k.startsWith('_')) continue;
    if (v !== null && typeof v === 'object' && !Array.isArray(v) && typeof out[k] === 'object' && out[k] !== null) {
      out[k] = mergeConfig(out[k], v);
    } else out[k] = v;
  }
  return out;
}

export class ConfigForm {
  /** form — element <form>, defaults — config z silnika, onChange(config) — po każdej zmianie. */
  constructor(form, defaults, onChange) {
    this.form = form;
    this.defaults = defaults;
    this.onChange = onChange;
    this.inputs = new Map();  // ścieżka -> {input, row, kind}
    this.mcFrom = false;
    this.build();
    this.set(defaults);
  }

  build() {
    const paths = leafPaths(this.defaults);
    const used = new Set();
    const groups = GROUPS.map((g) => ({ ...g, keys: g.keys.filter((k) => paths.includes(k)) }));
    groups.forEach((g) => g.keys.forEach((k) => used.add(k)));
    const extra = paths.filter((p) => !used.has(p));
    if (extra.length) groups.push({ id: 'other', title: 'Pozostałe parametry silnika', keys: extra });

    this.form.innerHTML = '';
    this.fieldsets = {};
    for (const g of groups) {
      const fs = document.createElement('fieldset');
      fs.dataset.group = g.id;
      if (['terrain', 'mc', 'ca'].includes(g.id)) fs.classList.add('wide');
      fs.innerHTML = `<legend>${g.title}</legend>${g.note ? `<p class="hint group-note">${g.note}</p>` : ''}`;
      for (const path of g.keys) fs.appendChild(this.buildRow(path));
      this.form.appendChild(fs);
      this.fieldsets[g.id] = fs;
    }
    this.form.addEventListener('input', () => this.changed());
    this.form.addEventListener('change', () => this.changed());
  }

  buildRow(path) {
    const s = SCHEMA[path] || {};
    const def = getPath(this.defaults, path);
    const row = document.createElement('div');
    row.className = 'frow';
    row.dataset.path = path;
    const id = `f-${path.replace(/\./g, '-')}`;
    let input, kind;
    if (s.json || Array.isArray(def)) {
      kind = 'json';  // lista (np. vents.positions) jako tekst JSON
      input = document.createElement('input');
      input.type = 'text';
      input.placeholder = '[]';
    } else if (ENUMS[path]) {
      kind = 'enum';
      input = document.createElement('select');
      for (const [v, label] of ENUMS[path]) input.add(new Option(label, v));
    } else if (typeof def === 'boolean') {
      kind = 'bool';
      input = document.createElement('input');
      input.type = 'checkbox';
    } else if (typeof def === 'number' && !s.text) {
      kind = s.int || (Number.isInteger(def) && s.step === undefined) ? 'int' : 'float';
      input = document.createElement('input');
      input.type = 'number';
      if (s.min !== undefined) input.min = s.min;
      input.step = s.step ?? (kind === 'int' ? 1 : 'any');
    } else {
      kind = def === null || s.text ? 'nullable' : 'text';
      input = document.createElement('input');
      input.type = 'text';
      if (def === null) input.placeholder = 'brak (null)';
    }
    input.id = id;
    input.name = path;
    row.innerHTML = `<label class="flabel" for="${id}">${s.label || path}<small>${path}</small></label><div class="fctl"></div>`;
    row.querySelector('.fctl').appendChild(input);
    if (s.unit) row.querySelector('.fctl').insertAdjacentHTML('beforeend', `<span class="unit">${s.unit}</span>`);
    if (s.hint) row.insertAdjacentHTML('beforeend', `<div class="fhint">${s.hint}</div>`);
    this.inputs.set(path, { input, row, kind });
    return row;
  }

  /** Wypełnia formularz configiem (scalonym z domyślnym). */
  set(config) {
    const full = mergeConfig(this.defaults, config);
    for (const [path, { input, kind }] of this.inputs) {
      const v = getPath(full, path);
      if (kind === 'bool') input.checked = !!v;
      else if (kind === 'json') input.value = v === undefined ? '' : JSON.stringify(v);
      else if (kind === 'nullable') input.value = v ?? '';
      else input.value = v ?? '';
      if (kind === 'enum' && v !== undefined && ![...input.options].some((o) => o.value === String(v))) {
        input.add(new Option(String(v), String(v)));  // wartość spoza listy — walidacja silnika powie, co nie tak
        input.value = String(v);
      }
    }
    this.changed();
  }

  /** Pełny config z formularza (wszystkie klucze silnika). */
  get() {
    const cfg = clone(this.defaults);
    for (const [path, { input, kind }] of this.inputs) {
      let v;
      if (kind === 'bool') v = input.checked;
      else if (kind === 'json') {
        const t = input.value.trim();
        try { v = t === '' ? [] : JSON.parse(t); } catch { v = t; }  // tekst — silnik zgłosi czytelny błąd
      } else if (kind === 'int' || kind === 'float') {
        const t = input.value.trim().replace(',', '.');
        v = t === '' ? null : Number(t);
        if (Number.isNaN(v)) v = t;  // przekazujemy tekst — silnik zgłosi czytelny błąd
      } else if (kind === 'nullable') v = input.value.trim() === '' ? null : input.value.trim();
      else v = input.value;
      setPath(cfg, path, v);
    }
    return cfg;
  }

  /** Zmienia wybrane pola ({'terrain.type': 'file', ...}), resztę formularza zostawia bez zmian. */
  setValues(values) {
    const cfg = this.get();
    for (const [path, v] of Object.entries(values)) setPath(cfg, path, v);
    this.set(cfg);
  }

  setMcFrom(on) {
    this.mcFrom = on;
    if (on) {
      this.inputs.get('mc.enabled').input.checked = true;
      this.inputs.get('mc.domain').input.value = 'basalt';
    }
    this.changed();
  }

  /** Reguły „nie dotyczy” — pola wyszarzone (wartości zostają w configu, silnik je ignoruje). */
  applyRules(cfg) {
    const mcOn = !!cfg.mc?.enabled;
    const full = mcOn && cfg.mc?.domain === 'full';
    const classic = cfg.ca?.mode === 'classic';
    const lavaCa = !full && !classic && !this.mcFrom;
    const fileTerrain = cfg.terrain?.type === 'file';
    const off = new Set();
    const groupOff = new Set();
    if (this.mcFrom) ['space', 'terrain', 'vents', 'ca'].forEach((g) => groupOff.add(g));
    if (full) ['terrain', 'vents', 'ca'].forEach((g) => groupOff.add(g));
    if (classic) groupOff.add('terrain');
    if (full || this.mcFrom) off.add('grid');
    if (classic) ['vents.placement', 'vents.eruptionSteps', 'vents.eruptTemp', 'ca.coolingAmbient', 'ca.coolingLateral',
      'ca.coolingFall', 'ca.solidusTemp', 'ca.ponding'].forEach((k) => off.add(k));
    if (lavaCa && fileTerrain) ['terrain.peakHeight', 'terrain.baseRadius', 'terrain.craterRadius', 'terrain.craterDepth',
      'terrain.noise'].forEach((k) => off.add(k));
    // Kratery w zadanych kolumnach: lista tylko przy placement = positions (wtedy count = długość listy, ustawia panel mapy).
    if (cfg.vents?.placement !== 'positions' || classic) off.add('vents.positions');
    if (!fileTerrain) off.add('terrain.file');
    if (!mcOn) GROUPS.find((g) => g.id === 'mc').keys.filter((k) => k !== 'mc.enabled').forEach((k) => off.add(k));
    if (full) ['mc.mobilityFromCooling', 'mc.mobilityMin'].forEach((k) => off.add(k));
    if (mcOn && !full && cfg.mc?.mobilityFromCooling === false) off.add('mc.mobilityMin');
    if (this.mcFrom) { off.add('mc.enabled'); off.add('mc.domain'); }
    for (const [path, { input, row }] of this.inputs) {
      const group = row.closest('fieldset').dataset.group;
      const disabled = off.has(path) || groupOff.has(group);
      input.disabled = disabled;
      row.classList.toggle('disabled', disabled);
      row.classList.toggle('changed', JSON.stringify(getPath(cfg, path)) !== JSON.stringify(getPath(this.defaults, path)));
    }
    for (const [id, fs] of Object.entries(this.fieldsets)) fs.classList.toggle('inactive', groupOff.has(id));
  }

  /** Podświetla pola wymienione w komunikatach błędów silnika (np. „space.nx”) i wpisuje komunikat pod polem. */
  markErrors(errors) {
    for (const { row } of this.inputs.values()) {
      row.classList.remove('error');
      row.querySelector('.ferr')?.remove();
    }
    for (const e of errors || []) {
      for (const [path, { row }] of this.inputs) {
        if (!e.includes(path)) continue;
        row.classList.add('error');
        row.insertAdjacentHTML('beforeend', `<div class="ferr" role="alert">${icon('alert')}<span>${esc(e)}</span></div>`);
      }
    }
  }

  changed() {
    const cfg = this.get();
    this.applyRules(cfg);
    this.onChange?.(cfg);
  }
}
