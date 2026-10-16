// Drobne funkcje wspólne dla modułów GUI: wybór elementów, escape HTML, odmiana liczebników, ikony SVG (icon),
// komunikaty (notice), opóźnione wywołanie (debounce) i zapis drobnych ustawień w localStorage.

export const $ = (s, root = document) => root.querySelector(s);
export const $$ = (s, root = document) => [...root.querySelectorAll(s)];

/** Tekst do wstawienia w HTML (dane z plików i od użytkownika nigdy nie trafiają do innerHTML bez tego). */
export const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

/** Odmiana liczebnika: plural(5, 'krater', 'kratery', 'kraterów') -> '5 kraterów'. */
export function plural(n, one, few, many) {
  const d = n % 10, dd = n % 100;
  return `${n} ${n === 1 ? one : d >= 2 && d <= 4 && (dd < 12 || dd > 14) ? few : many}`;
}

/** Ikona SVG z zestawu w index.html (<symbol id="i-…">): kolor = kolor tekstu, rozmiar z CSS (.i). */
export const icon = (name, cls = '') => `<svg class="i${cls ? ` ${cls}` : ''}" aria-hidden="true" focusable="false"><use href="#i-${name}"></use></svg>`;

const ICONS = { ok: 'check', warn: 'alert', error: 'x', info: 'info' };
/** Komunikat z ikoną (ok / warn / error / info); html — już bezpieczny HTML. */
export function notice(level, html) {
  return `<div class="notice ${level}"><span class="icon" aria-hidden="true">${icon(ICONS[level])}</span><div>${html}</div></div>`;
}

/** Tekst elementu — zmieniany tylko, gdy inny (paski stanu odświeżane w każdej klatce odtwarzania). */
export function setText(el, text) {
  if (el.textContent !== text) el.textContent = text;
}

/** Funkcja wywoływana dopiero po `ms` ciszy (np. podgląd serii przy pisaniu). */
export function debounce(fn, ms) {
  let t = null;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

/** Wypełnienie toru suwaka (input type=range) do bieżącej wartości — zmienna CSS --fill (css/style.css). */
export function rangeFill(el) {
  const lo = Number(el.min) || 0, hi = Number(el.max) || 0, v = Number(el.value) || 0;
  el.style.setProperty('--fill', `${hi > lo ? (100 * (v - lo)) / (hi - lo) : 0}%`);
}

/** localStorage odporne na tryb prywatny / zablokowany dostęp. */
export const store = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* tryb prywatny — pomijamy */ } },
};

/** Pobranie pliku z przeglądarki (Blob -> <a download>). */
export function downloadBlob(blob, name) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
