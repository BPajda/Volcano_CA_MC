<!-- Szablon README wersji minimalnej: tools/export_minimal.py kopiuje go jako README.md (bez tego komentarza).
     Odnośniki są względne wobec katalogu głównego eksportu, nie wobec tego pliku. -->
# volcano-ca-mc — symulacja erupcji wulkanu (CA + Monte Carlo)

Spływ lawy jest modelowany automatem komórkowym w przestrzeni wokselowej 2D/3D jako rozrost ziaren: kratery są
zarodkami, a lawa rośnie po terenie — generowanym albo prawdziwym (Etna, Wezuwiusz) — spada, rozlewa się w kierunku
największego spadku, wypełnia krater, stygnie i zastyga w bazalt. Zastygły bazalt krystalizuje metodą Monte Carlo
(model Pottsa) z mobilnością zależną od czasu stygnięcia. Obliczenia wykonuje silnik C++17 bez interfejsu
(config JSON → symulacja → pliki wyników i `times.json`), a GUI w przeglądarce przygotowuje konfiguracje, kolejkuje
zadania i pokazuje wyniki w 2D i 3D (także odtwarzanie erupcji krok po kroku).

![Erupcja Etny w podglądzie 3D — odtwarzanie krok po kroku](docs/img/readme/gui_3_erupcja_3d.png)

## Wymagania

- **Windows:** Visual Studio 2022 z pakietem „Programowanie aplikacji klasycznych w języku C++” (zawiera narzędzia
  CMake) albo Build Tools 2022; **Linux:** GCC lub Clang z obsługą C++17.
- CMake ≥ 3.20.
- Python ≥ 3.11 — GUI (`gui/requirements.txt`: fastapi, uvicorn, numpy, pillow), testy (`gui/requirements-dev.txt`),
  narzędzia (`numpy`, `matplotlib`). Przeglądarka z obsługą WebGL2.
- Zależności C++ (nlohmann/json, doctest) i biblioteki frontendu (three.js, Chart.js, fonty) są w repozytorium —
  GUI działa bez internetu.

## Budowanie

**Windows, Visual Studio 2022** (wiersz poleceń bez środowiska vcvars; w VS: *Plik → Otwórz → Folder*, preset `msvc-release`):

```
cmake --preset msvc-release
cmake --build --preset msvc-release
```

Program: `build\Release\engine.exe`.

**Linux, GCC:**

```
cmake --preset gcc-release
cmake --build --preset gcc-release -j
```

Program: `build-gcc-release/bin/engine`.

## Uruchomienie

Silnik na przykładowym configu (wyniki w `results/test_2d/`: `ca_result.txt`/`.bin`, `times.json`, `stats.json`):

```
.\build\Release\engine.exe --config configs\test_2d.json --out results\test_2d
.\build\Release\engine.exe --config configs\lava_mc_3d.json --out results\lava_mc_3d
.\build\Release\engine.exe --help
```

(Linux: `build-gcc-release/bin/engine --config configs/test_2d.json --out results/test_2d`.) Gotowe konfiguracje
są w `configs/` — m.in. `etna_real.json` i `wezuwiusz_real.json` (prawdziwy teren), `mc_full_2d.json` (samo MC).

GUI (http://127.0.0.1:8000, otwiera przeglądarkę):

```
python -m pip install --user -r gui/requirements.txt
python -m gui
```

Testy:

```
ctest --preset msvc-release                  # Linux: ctest --preset gcc-release
python -m pip install --user -r gui/requirements-dev.txt
python -m pytest gui/tests                   # wymaga zbudowanego silnika
```

## Struktura katalogów

```
engine/      silnik C++17: src/ (core, terrain, ca, mc, io, app), tests/ (doctest), third_party/
gui/         GUI: backend Python (FastAPI, tylko 127.0.0.1), frontend HTML/JS (static/), testy pytest (tests/)
tools/       podgląd wyników (PNG), seria bez GUI, mapy wysokości, prawdziwy teren, eksport VTK
bench/       skrypty pomiarów profilu, mikrobenchmark, dane pomiarowe cytowane w raporcie (results/)
configs/     przykładowe konfiguracje JSON i mapy wysokości (heightmaps/)
raport.pdf   raport techniczny
```

Dane terenu Etny i Wezuwiusza pochodzą z AWS Terrain Tiles — wymagane przypisanie danych:
[configs/heightmaps/README.md](configs/heightmaps/README.md).

## Opis projektu i wyniki

Architektura, modele CA i MC, GUI i kolejkowanie zadań, wyniki symulacji oraz profil wydajności:
**[raport.pdf](raport.pdf)**.
