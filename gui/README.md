# gui — interfejs użytkownika

Lokalna aplikacja web: formularz parametrów albo **seria zadań** → pliki konfiguracyjne i foldery wyników →
silnik `engine` uruchamiany jako podproces (**kolejka zadań**) → wizualizacja wyniku 2D (przekroje) i 3D (ściany
zewnętrzne, powierzchnia, woksele), czasy i statystyki, **porównanie wyników serii (CA vs MC)**, import map wysokości,
eksport ZIP / VTK, **kratery na mapie** i **odtwarzanie erupcji krok po kroku** (etap 6). Wygląd „Bazalt i lawa”
(etap 7): motyw ciemny (domyślny) i jasny „popiół” — przełącznik w nagłówku, paleta komórek dobrana pod kątem
fizyki i daltonizmu. Opisy etapów: [`docs/etap-4-gui.md`](../docs/etap-4-gui.md), [`docs/etap-5-kolejka-serie-dane.md`](../docs/etap-5-kolejka-serie-dane.md),
[`docs/etap-6-prawdziwe-wulkany.md`](../docs/etap-6-prawdziwe-wulkany.md), [`docs/etap-7-wyglad-gui.md`](../docs/etap-7-wyglad-gui.md);
obsługa krok po kroku: [`docs/uruchamianie.md`](../docs/uruchamianie.md).

## Uruchomienie

```
cd volcano-ca-mc
python -m pip install --user -r gui\requirements.txt   # raz: fastapi, uvicorn, numpy, pillow (Python >= 3.11)
python -m gui                                          # http://127.0.0.1:8000, otwiera przeglądarkę
```

albo dwuklik `gui\run_gui.bat`. Opcje: `--port 8001`, `--no-browser`. Wymagany zbudowany silnik
(`cmake --build --preset msvc-release` → `build\Release\engine.exe`, wykrywany automatycznie). Inną ścieżkę,
port, domyślną liczbę workerów i procesory do przypinania (`pinCpus`) ustawia `gui/settings.json`
(wzór `settings.example.json`) albo zmienne `VOLCANO_ENGINE`, `VOLCANO_GUI_PORT`, `VOLCANO_GUI_WORKERS`.
Liczba workerów, pauza i przypięcie ustawione w GUI są zapamiętywane w `results/gui/jobs.json`.

## Struktura

| Plik | Rola |
|---|---|
| `__main__.py` | `python -m gui` — uvicorn na 127.0.0.1, sprawdzenie zajętego portu, otwarcie przeglądarki |
| `app.py` | FastAPI: endpointy `/api/...` (lista w docstringu, `docs/etap-4-gui.md`, `docs/etap-5-kolejka-serie-dane.md`), pliki statyczne, ochrona Host/Content-Type |
| `settings.py` | ścieżka silnika (env → `settings.json` → auto-wykrycie Release, potem Debug), katalogi `configs/`, `results/`, serii i map wysokości, port, workery, `pinCpus` |
| `engine.py` | wywołania silnika: `--print-defaults` (formularz), `--validate` (walidacja), polecenie uruchomienia z `--progress` |
| `jobs.py` | `JobManager`: zadanie = config + folder wyników + podproces + status + `engine.log`; **kolejka** (kolejność, pauza, workery zmieniane w locie, anulowanie zadania i serii, ponowienie, przypięcie do CPU + wysoki priorytet), **serie** (`create_series`: walidacja wszystkich configów → zapis wszystkich plików → kolejka), stan w `results/gui/jobs.json` (v2) |
| `series.py` | generator serii: osie (klucze, lista / zakres / potęgi, parowanie), iloczyn kartezjański, nazwy `NN_<opis>`, `write_series` (`configs/…/series/<id>/` + `series.json`, `results/…/series/<id>/`), szablony `TEMPLATES` — **wspólny z `tools/make_series.py`** (bez FastAPI) |
| `compare.py` | wyniki serii w tabeli (`times.json`, `stats.json`, `config_used.json`), koszt jednostkowy, wykrywanie parametrów zmiennych, CSV |
| `heightmap.py` | mapy wysokości: walidacja CSV (reguły silnika, komunikaty po polsku), obraz PNG/JPG → mapa (Pillow), lista i zapis w `configs/heightmaps/`, metadane map z prawdziwego terenu (`load_geo`: bbox, skala — szer./dł. w GUI) |
| `replay.py` | odtwarzanie erupcji (etap 6): pojawienie / zastygnięcie komórki, stan i temperatura w kroku k, liczby komórek w każdym kroku — ta sama reguła co `static/js/replay.js` |
| `export.py` | ZIP folderu wyniku, VTK ImageData `.vti` (zlib / binary / ascii) — także `tools/export_vtk.py` |
| `names.py` | bezpieczne nazwy plików z tekstu użytkownika, znacznik czasu |
| `results.py` | odczyt wyników: `ca_result.bin` v1/v2 i `.txt`, `mc_result.*`, `times.json`, `stats.json`, `mc_stats.csv`; `np.memmap` dla plików > 128 MB; LRU ostatnich wyników; lista wyników do 4 poziomów w głąb (`results/gui/series/<seria>/<zadanie>`, foldery po `engine --batch`); miniatury (`maxSide`) |
| `render.py` | czyste funkcje numpy: przekrój (próbkowanie > 4 mln komórek), ściany, mapa powierzchni (też wysokość samej skały), woksele |
| `static/` | frontend bez kroku budowania: `index.html` (+ zestaw ikon SVG), `css/style.css` (zmienne obu motywów), `js/*.js` (moduły ES; etap 6: `replay.js` — pasek odtwarzania, paleta „żar”, ZIP z klatkami PNG, WebM; `ventpicker.js` — kratery na mapie; etap 7: `theme.js` — motyw), `vendor/` (three.js, Chart.js, fonty Inter i JetBrains Mono — wersje, licencje i sumy w `vendor/README.md`) |
| `tests/` | pytest (`test_results.py`, `test_jobs.py`, `test_series.py`, `test_heightmap.py`, `test_export.py`, `test_fetch_dem.py`, `test_replay.py` — 100 testów), `screenshots.py` (Playwright: scenariusz i zrzuty `docs/img/gui_*.png`, etap 6: `real_*.png`, `replay_*.png`; `--only-series`, `--skip-series`, `--only-real`, `--skip-real`, `--theme dark/light`), `ui_shots.py` (etap 7: zrzuty zakładek bez tworzenia zadań — `ui_przed_*`, `ui_po_*`, `ui_jasny_*`, rozdzielczości `--size`/`--dpr`, płynność odtwarzania `--fps`), `palette_check.py` (kontrast WCAG obu motywów, kolory komórek przy daltonizmie — emulacja Chromium), `run_ca_vs_mc.py` (seria CA vs MC przez GUI → `docs/img/ca_vs_mc.png`, `docs/data/ca_vs_mc*.{csv,json}`) |

Frontend: `main.js` (zakładki, formularz, wyniki, wybór wyniku), `form.js` (formularz z domyślnego configu silnika
+ opisy pól i reguły „nie dotyczy”), `series.js` (zakładka „Seria”), `jobs.js` (zakładka „Zadania” — kolejka),
`compare.js` (zakładka „Porównanie” — tabela, wykres, galeria), `heightmap.js` (mapa wysokości w formularzu),
`estimate.js` (szacunek pamięci/czasu z pomiarów profilu, etap 3), `palette.js` (kolory danych i legendy — jedyne miejsce z paletą
naukową), `theme.js` (motyw ciemny / jasny: przełącznik, `localStorage`, kolory z CSS dla canvasu, three.js i Chart.js),
`viewer2d.js` (canvas), `viewer3d.js` (three.js), `stats.js` (Chart.js), `api.js` (fetch, dane binarne),
`util.js` (wspólne drobiazgi).

## Zasady

- **Backend tylko na 127.0.0.1**; nic nie liczy — obliczenia robi wyłącznie silnik C++ (także walidacja configów serii).
- **Frontend bez kroku budowania** (bez npm/webpack/React); biblioteki **lokalnie** w `static/vendor/`
  w przypiętych wersjach — GUI działa bez internetu.
- Do przeglądarki idą tylko wycinki (przekrój, ściany, powierzchnia, woksele, miniatury) jako surowe bajty
  z opisem w nagłówku `X-Meta`; kolorowanie po stronie przeglądarki.
- Identyfikatory wyników, serie, nazwy zadań i mapy nie mogą wyjść poza `results/`, `configs/gui/`,
  `configs/heightmaps/` (testy w `tests/`).
- Logika serii tylko w `series.py` (nie kopiować do `tools/`); pomiary czasu — 1 worker + przypięcie.
- Wykresy: jedna oś Y, kolor = wartość serii (CA = lawa, MC = fiolet — `theme.js`; inne podziały — paleta
  kategoryczna motywu), legenda + tabela jako uzupełnienie.
- Kolory: interfejs tylko przez zmienne CSS motywu (`css/style.css`), dane tylko przez `palette.js`; JS nie wpisuje
  kolorów na sztywno. Fonty i ikony lokalnie (bez internetu). Opis: `docs/etap-7-wyglad-gui.md`.
- Interfejs po polsku.

## Testy

```
python -m pip install --user -r gui\requirements-dev.txt  # pytest, httpx, playwright
python -m pytest gui\tests                                # wymaga zbudowanego silnika
python -m playwright install chromium                     # raz, do zrzutów
python gui\tests\screenshots.py                           # scenariusz w Chromium + docs\img\gui_*.png + błędy konsoli JS
python gui\tests\ui_shots.py --prefix x --theme light --size 1280x720 --out <katalog>   # zrzuty zakładek (bez zadań)
python gui\tests\ui_shots.py --fps                        # płynność odtwarzania etna_real w 3D (FPS, czas klatki)
python gui\tests\palette_check.py                         # kontrast WCAG + daltonizm -> docs\img\ui_paleta_daltonizm.png
python gui\tests\run_ca_vs_mc.py                          # pełna seria CA vs MC przez GUI + eksport wykresu i CSV
```
