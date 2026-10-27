# Biblioteki frontendu (kopie lokalne)

GUI ma działać bez internetu (np. na komputerze bez sieci), dlatego biblioteki i fonty są skopiowane do repozytorium
w przypiętych wersjach — bez npm i bez kroku budowania. Pobrane 09.10.2026 z npm przez jsDelivr.

| Plik | Biblioteka | Wersja | Źródło | Licencja | SHA-256 |
|---|---|---|---|---|---|
| `three/three.module.min.js` | three.js (moduł ES, zminifikowany) | 0.160.0 (r160) | `https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.min.js` | MIT (`three/LICENSE`) | `3e690ac7d180b0aadf0891bea39eec643e29e2d3e75c99b18689518665f69ba6` |
| `three/OrbitControls.js` | three.js — `examples/jsm/controls/OrbitControls.js` | 0.160.0 | `https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/controls/OrbitControls.js` | MIT (`three/LICENSE`) | `5a44a9e86a2a0fb11933eed69bc2cd33c76a496854c1aed6ed776efa87d7b064` |
| `chartjs/chart.umd.js` | Chart.js (UMD, zminifikowany) | 4.4.1 | `https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.js` | MIT (`chartjs/LICENSE.md`) | `74401d738dd3e03ee5dfb3b6841210fe2c4ead8a960c4011ca4ba0b78a9fd8f3` |

Łącznie ~0,9 MB. Pliki są niezmienione (sumy SHA-256 powyżej).

## Fonty (wygląd interfejsu, `docs/wyglad-interfejsu.md`)

Fonty zmiennej grubości (jeden plik na podzbiór znaków, grubości 100–900 / 100–800) w formacie WOFF2, pobrane
15.10.2026 z paczek npm Fontsource przez jsDelivr. Podzbiór `latin-ext` zawiera polskie litery (ą ć ę ł ń ó ś ź ż);
`css/style.css` ładuje oba podzbiory przez `@font-face` z `unicode-range` (przeglądarka pobiera tylko potrzebny).

| Plik | Krój | Wersja | Źródło | Licencja | SHA-256 |
|---|---|---|---|---|---|
| `fonts/inter-latin-wght-normal.woff2` | Inter (tekst interfejsu) | `@fontsource-variable/inter` 5.3.0 (Google Fonts v20) | `https://cdn.jsdelivr.net/npm/@fontsource-variable/inter@5.3.0/files/inter-latin-wght-normal.woff2` | SIL OFL 1.1 (`fonts/OFL-Inter.txt`) | `3100e775e8616cd2611beecfa23a4263d7037586789b43f035236a2e6fbd4c62` |
| `fonts/inter-latin-ext-wght-normal.woff2` | Inter — `latin-ext` | jw. | `…/inter@5.3.0/files/inter-latin-ext-wght-normal.woff2` | jw. | `34b9c504cab7a73e37b746343a449132e56cf7b5481af2cb81dc74dcff25c956` |
| `fonts/jetbrains-mono-latin-wght-normal.woff2` | JetBrains Mono (ścieżki, wartości) | `@fontsource-variable/jetbrains-mono` 5.3.0 | `https://cdn.jsdelivr.net/npm/@fontsource-variable/jetbrains-mono@5.3.0/files/jetbrains-mono-latin-wght-normal.woff2` | SIL OFL 1.1 (`fonts/OFL-JetBrainsMono.txt`) | `18be452724bfdc236c074ca94a249a7f41a86752c7d04ab258ce9ed5651f6a7e` |
| `fonts/jetbrains-mono-latin-ext-wght-normal.woff2` | JetBrains Mono — `latin-ext` | jw. | `…/jetbrains-mono@5.3.0/files/jetbrains-mono-latin-ext-wght-normal.woff2` | jw. | `79bfdab9ba467e26eea4122e6f2567e188dd8a09a8c730d501fc487c4ab99c6e` |

Łącznie ~190 KB. Licencja OFL pozwala dołączać fonty do oprogramowania (także w repozytorium) pod warunkiem
dołączenia tekstu licencji — pliki `fonts/OFL-*.txt` (z informacją o prawach autorskich: The Inter Project Authors,
The JetBrains Mono Project Authors). Serwer GUI podaje `.woff2` z typem `font/woff2` (`gui/app.py`, `mimetypes`).

## Jak są ładowane

- three.js — moduły ES przez *import map* w `index.html`:
  `"three"` → `./vendor/three/three.module.min.js`, `"three/addons/OrbitControls.js"` → `./vendor/three/OrbitControls.js`
  (`OrbitControls.js` importuje `'three'`, więc mapa rozwiązuje to bez modyfikacji pliku).
- Chart.js — zwykły `<script>` (UMD), dostępny jako `window.Chart`.

## Aktualizacja

Podmień pliki na inną przypiętą wersję (ten sam układ katalogów), zaktualizuj tabelę i sumy
(`sha256sum`) i sprawdź GUI skryptem `python gui/tests/screenshots.py` (wypisuje błędy konsoli przeglądarki).
Uwaga: od three.js r171 `three.module.js` importuje dodatkowo `three.core.js` — trzeba skopiować oba pliki.
