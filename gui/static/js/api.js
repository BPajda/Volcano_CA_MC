// Komunikacja z backendem FastAPI (ten sam serwer, adresy względne /api/...).

/** Błąd żądania z listą komunikatów (np. błędy walidacji configu dla formularza). */
export class ApiError extends Error {
  constructor(message, status, errors = [], warnings = []) {
    super(message);
    this.status = status;
    this.errors = errors.length ? errors : [message];
    this.warnings = warnings;
  }
}

async function check(resp) {
  if (resp.ok) return resp;
  let body = {};
  try { body = await resp.json(); } catch { /* treść nie-JSON */ }
  let detail = body.detail ?? resp.statusText;
  if (Array.isArray(detail)) detail = detail.map((d) => d.msg ?? JSON.stringify(d)).join('; ');
  throw new ApiError(String(detail), resp.status, body.errors ?? [], body.warnings ?? []);
}

export async function getJSON(url) {
  return (await check(await fetch(url))).json();
}

export async function getText(url) {
  return (await check(await fetch(url))).text();
}

export async function postJSON(url, body) {
  const resp = await fetch(url, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body ?? {}),
  });
  return (await check(resp)).json();
}

/** Dane binarne: { meta (z nagłówka X-Meta), buffer (ArrayBuffer) }. */
export async function getBinary(url, signal) {
  const resp = await check(await fetch(url, { signal }));
  const meta = JSON.parse(resp.headers.get('X-Meta') || '{}');
  return { meta, buffer: await resp.arrayBuffer() };
}

const TYPED = {
  uint8: Uint8Array, uint16: Uint16Array, int32: Int32Array, float32: Float32Array,
};

/** Tablica typowana z fragmentu bufora (kopia, gdy przesunięcie nie jest wyrównane do rozmiaru elementu). */
export function typed(dtype, buffer, offset = 0, length = undefined) {
  const T = TYPED[dtype];
  if (!T) throw new Error(`nieznany typ tablicy: ${dtype}`);
  const n = length ?? (buffer.byteLength - offset) / T.BYTES_PER_ELEMENT;
  if (offset % T.BYTES_PER_ELEMENT === 0) return new T(buffer, offset, n);
  return new T(buffer.slice(offset, offset + n * T.BYTES_PER_ELEMENT));
}

/** Adres z parametrami zapytania. */
export function url(path, params) {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null) q.set(k, v);
  return `${path}?${q}`;
}
