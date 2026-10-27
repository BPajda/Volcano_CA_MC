// Szacunek pamięci, czasu i rozmiaru plików przed uruchomieniem — prosta heurystyka z pomiarów
// profilu aplikacji (docs/profilowanie.md, punkty 3.2, 3.3, 4 i 5.1; MSVC Release, rdzeń P i9-13900HX).
//
// Pamięć (model z MemoryModel, zgodny z pomiarem do 0–4%), N — komórki, Nf = (nx+2)(ny+2)(nz+2):
//   CA (lava/classic):  26·Nf + 14·N   (oba bufory z ramką + wynik + D(n))  -> 3D ≈ 40 B/kom., 2D ≈ 91 B/kom.
//   MC full:            5·Nf + 37·N    (orientacja + maska, listy domeny, etykiety ziaren)  -> 3D ≈ 42, 2D ≈ 52
//   lava + MC:          CA + 5·Nf + 8·N (domena MC to zwykle kilka % przestrzeni)
// Czas: CA = c · N · kroki; c [ns/(komórka·krok)]: classic VN 3D 7, 2D 9; Moore 3D 20, 2D 11; lava 32.
//   Kroki classic ≈ promień największej luki między zarodkami: VN (nx+ny+nz)/2 / zarodki^(1/d),
//   Moore max(n)/2 / zarodki^(1/d); lava — górny szacunek: eruptionSteps + 2·max(nx, ny, nz) (≤ maxSteps).
//   MC = ns/próbę · N_domena · MCS; ns/próbę: < 10⁵ komórek 40 (VN) / 130 (Moore 3D), większe 110 / 250.
//   Domena basalt ≈ 5% N (górny szacunek z lava_mc_3d: 1,3%).
// Pliki: bin 13 B/kom. (mc 4 B), txt ≈ 15–21 B/kom. (mc ≈ 13 B). To tylko rząd wielkości — na innym
// komputerze i dla innych parametrów lawy czasy mogą się różnić kilkukrotnie.

const MB = 1024 * 1024;

export function fmtBytes(b) {
  if (b < 1024) return `${b} B`;
  if (b < MB) return `${(b / 1024).toFixed(1)} KiB`;
  if (b < 1024 * MB) return `${(b / MB).toFixed(1)} MiB`;
  return `${(b / MB / 1024).toFixed(2)} GiB`;
}

export function fmtTime(ms) {
  if (ms < 1000) return `${Math.max(1, Math.round(ms))} ms`;
  const s = ms / 1000;
  if (s < 120) return `${s.toFixed(s < 10 ? 1 : 0)} s`;
  if (s < 7200) return `${(s / 60).toFixed(0)} min`;
  return `${(s / 3600).toFixed(1)} h`;
}

export const fmtInt = (n) => Math.round(n).toLocaleString('pl-PL');

/** Szacunek dla configu: { cells, dims, bytes, ms, steps, files, warnings[] }. mcFrom — tylko MC na wyniku CA. */
export function estimate(cfg, mcFrom = null) {
  const { nx = 1, ny = 1, nz = 1 } = mcFrom?.dims ? { nx: mcFrom.dims[0], ny: mcFrom.dims[1], nz: mcFrom.dims[2] } : cfg.space;
  const N = nx * ny * nz;
  const Nf = (nx + 2) * (ny + 2) * (nz + 2);
  const d = [nx, ny, nz].filter((v) => v > 1).length;
  const mc = cfg.mc || {};
  const mcOn = !!mc.enabled || !!mcFrom;
  const full = mcOn && mc.domain === 'full' && !mcFrom;
  const classic = cfg.ca?.mode === 'classic';
  const nb = cfg.neighborhood;
  const moore = nb !== 'von_neumann';
  const warnings = [];

  let bytes = 0, caMs = 0, mcMs = 0, steps = null;
  if (!full && !mcFrom) {
    bytes += 26 * Nf + 14 * N;
    const seeds = Math.max(1, cfg.vents?.count || 1);
    if (classic) {
      const reach = moore ? Math.max(nx, ny, nz) / 2 : (nx + ny + nz) / 2;
      steps = Math.ceil(reach / Math.pow(seeds, 1 / Math.max(d, 1)));
      const c = moore ? (d === 3 ? 20 : 11) : (d === 3 ? 7 : 9);
      caMs = (c * N * steps) / 1e6;
    } else {
      steps = Math.min(cfg.ca?.maxSteps ?? 5000, (cfg.vents?.eruptionSteps ?? 300) + 2 * Math.max(nx, ny, nz));
      caMs = (32 * N * steps) / 1e6;
    }
    steps = Math.min(steps, cfg.ca?.maxSteps ?? steps);
  }
  if (mcOn) {
    const domain = full ? N : 0.05 * N;
    const big = N > 1e5;
    const ns = moore && d === 3 ? (big ? 250 : 130) : (big ? 110 : 40);
    mcMs = (ns * domain * (mc.mcs ?? 100)) / 1e6;
    bytes += full ? 5 * Nf + 37 * N : 5 * Nf + 8 * N + (mcFrom ? 13 * N : 0);
  }

  const fmt = cfg.output?.format ?? 'txt';
  const txt = fmt === 'txt' || fmt === 'both', bin = fmt === 'bin' || fmt === 'both';
  const digits = String(Math.max(nx, ny, nz)).length;
  let fileBytes = 0;
  if (!full && !mcFrom) fileBytes += (txt ? (9 + 3 * digits) * N : 0) + (bin ? 13 * N : 0);
  if (mcOn) fileBytes += (txt ? (5 + 3 * digits) * N : 0) + (bin ? 4 * N : 0);
  if (!full && !mcFrom && (cfg.output?.snapshotsEvery ?? 0) > 0 && steps) {
    fileBytes += Math.floor(steps / cfg.output.snapshotsEvery) * 13 * N;
  }
  const ms = caMs + mcMs + (txt ? N * 150e-6 : 0);

  if (bytes > 8 * 1024 * MB) warnings.push({ level: 'error', text: `Szacowana pamięć ${fmtBytes(bytes)}: więcej niż typowy komputer (zostaw ~25% RAM systemowi).` });
  else if (bytes > 2 * 1024 * MB) warnings.push({ level: 'warn', text: `Duża siatka: ~${fmtBytes(bytes)} pamięci.` });
  if (ms > 10 * 60 * 1000) warnings.push({ level: 'warn', text: `Szacowany czas ${fmtTime(ms)}: długie obliczenia (zadanie można anulować).` });
  if (txt && N > 1e7) warnings.push({ level: 'warn', text: `Plik txt dla ${fmtInt(N)} komórek: ~${fmtBytes((9 + 3 * digits) * N)} i wolny zapis; wybierz format bin.` });
  if (N > 3e7) warnings.push({ level: 'warn', text: 'Bardzo duży wynik: podgląd 2D/3D czyta tylko przekroje i ściany, ale wczytanie metadanych może potrwać.' });
  if (d === 2 && Nf > 2.5 * N && N > 1e6) warnings.push({ level: 'info', text: 'Siatka 2D: ramka w nieużywanej osi zajmuje 2/3 pamięci.' });
  return { cells: N, dims: [nx, ny, nz], d, bytes, ms, caMs, mcMs, steps, fileBytes, warnings, mcOn, full, classic };
}
