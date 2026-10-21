# Etap 10 — dziennik pomiarów i postępu (MPI)

Plik prowadzony na bieżąco w trakcie etapu 10 (wersja rozproszona silnika w MPI): każdy krok, jego pliki, wyniki,
zgodność bitowa i obciążenie tła. Opis implementacji i wnioski: [`docs/etap-10-mpi.md`](../../../docs/etap-10-mpi.md).

Oznaczenia: `e9` = program po etapie 9 (`bench/baseline/engine_e9_msvc.exe`, `engine_e9_gcc`; binarki lokalne,
katalog `bench/baseline/` jest w `.gitignore`), `mN` = `engine_mpi` uruchomiony na N procesach, `mN×T` — N procesów
po T wątków OpenMP (tryb hybrydowy). Tło = obciążenie całego CPU przez inne programy (psutil, 2 s próbki). Tryb
oszczędny (od etapu 8, do końca projektu): procesor bez turbo, WSL 8 procesorów / 8 GB, buildy `--parallel 4` /
`-j 4`, jedna ciężka operacja naraz, łącznie najwyżej 8 procesów × wątków na rdzeniach P.

## Tabela kroków

| Krok | Stan | Pliki wyników | Wynik | Zgodność | Tło [% CPU] | Uwagi |
|---|---|---|---|---|---|---|
| 0.1 MPI | zrobione | — | MS-MPI 10.1.12498.52 — tylko środowisko uruchomieniowe (`mpiexec`), **bez SDK**; OpenMPI 4.1.2 w WSL (`mpicxx` = g++ 11.4) | — | — | punkt 0.1 dziennika |
| 0.2 Tryb oszczędny | zrobione | — | rdzeń P pod obciążeniem 95,3–97,1% taktowania bazowego (bez turbo); WSL `nproc` = 8, 7 GB | — | 11–17 | `PROCTHROTTLEMAX` i `PROCTHROTTLEMAX1` = 99% (sieć i bateria) |
| 0.3 Binarki odniesienia | zrobione | `bench/baseline/engine_e9_msvc.exe`, `engine_e9_gcc` | = `build/Release/engine.exe` / `build-gcc-release/bin/engine` (bajtowo) | — | — | — |
| 1.1 MSVC + MS-MPI (sesja 2) | zrobione | `build/Release/engine_mpi.exe` | SDK MS-MPI zainstalowane; build bez ostrzeżeń, `ctest` 21/21 (Release i Debug) | — | 18–33 | — |
| 1.2 Przypinanie w Windows | zrobione | — | maski procesów 2, 4, 6, 8 / {2,4,6,8} {10,12,14,0}, priorytet `High`; `mpiexec -affinity` odrzucone (rdzenie E) | — | — | silnik przypina sam |
| 1.3 Zgodność MSVC/MS-MPI | zrobione | `zgodnosc_mpi_msvc*.md` | e9 = m1 = m3 = m8 = c3 = c8 = m2×4 = m3_gcc; `full`; `random` p = 1 | 15/15 × 3 | — | po każdej zmianie kodu powtórzone |
| 2.1 Buildy | zrobione | `build-gcc-nompi/` | MSVC Debug 21/21, GCC `VOLCANO_MPI=OFF` 12/12 (`engine` bajtowo ten sam), `pytest` 102/102 | — | — | — |
| 2.3 A/B narzutu `engine` | zrobione | `ab_e10_{msvc,gcc}_*.md` (+ `ab_e10a_*`, `ab_e10d_*`) | e10a: MSVC lawa +7–8%, GCC +3–21% → poprawka `frontStepSequential<bool Strip>` → cały przebieg ≤ +2,1% | 15/15 | 20–30 | punkt „sesja 2” |
| 2.4 Binarki etapu 10 | zrobione | `bench/baseline/engine_{,mpi_}e10_{msvc.exe,gcc}` | e10e (+ wersje pośrednie e10a, e10d) | — | — | — |
| 2.5 Próba `scaling_mpi.py` | zrobione | `results/skalowanie_mpi_test/` | Windows i WSL; CSV, przypięcie, priorytet, `initMax`; WSL `--use-hwthread-cpus` | zgodne | — | — |
| 3 GUI | pominięte | — | uzasadnienie w `docs/etap-10-mpi.md`, punkt 7 | — | — | — |
| 4 Dobór i plan | zrobione | `dobor_{msvc,gcc}.*`, `PLAN_POMIARU.md` | 6 części, ~30 min | zgodne | 16–21 | — |
| C2.0 Weryfikacja (część 2) | zrobione | `results/proba_cz2/` | binarki = plan, MPI działa, bez turbo (94,8–97,2%) | zgodne | 16 | — |
| C2.1 Cichy pomiar MSVC (A1, A2, B, C) | zrobione | `skalowanie_mpi_msvc{,_cz1…4}.*` | 7 przypadków × 13 wariantów, 18,3 min | 585/585 | 13–24 | bez powtórzeń |
| C2.2 Cichy pomiar GCC (D, E) | zrobione | `skalowanie_mpi_gcc{,_cz1,_cz2}.*` | 7 przypadków × 5 wariantów, 7,0 min | 225/225 | 10–19 | bez powtórzeń |
| C2.3 Zgodność `full` (binarki końcowe) | zrobione | `zgodnosc_mpi_{msvc,gcc}_full.md` | odświeżone po poprawce frontu | 15/15 × 2 | — | — |
| C2.4 Wykresy | zrobione | `bench/plot_etap10.py`, `docs/img/etap10_*.png` | 8 wykresów, sprawdzone | — | — | — |
| C2.5 Dokumentacja i eksport | zrobione | `docs/etap-10-mpi.md` (+ 6 plików) | eksport tymczasowy buduje `engine_mpi` | wynik = m3 | — | 4 fałszywe trafienia słownictwa (`p1` w teście) |

## Dziennik

### Część 1 (20.10.2026, od ok. 06:15)

- Stan repozytorium: `git status` czysty, ostatni commit „etap 9: OpenMP”.
- **MPI na Windows:** `mpiexec -help` — „Microsoft MPI Startup Program [Version 10.1.12498.52]”, `MSMPI_BIN` =
  `C:\Program Files\Microsoft MPI\Bin\`. **SDK MS-MPI (`msmpisdk.msi`) nie jest zainstalowane:** zmienne `MSMPI_INC`
  i `MSMPI_LIB64` puste (także w zmiennych systemowych), na dysku nie ma `mpi.h` ani `msmpi.lib`, w folderze pobranych
  plików jest tylko `msmpisetup.exe`. Bez nagłówków i biblioteki importu MSVC nie zbuduje `engine_mpi.exe` — zgodnie
  z zasadami etapu nic nie instaluję. Kod MPI jest pisany przenośnie (bez funkcji MPI-3, bufory bez `const`), a cel
  CMake `engine_mpi` powstaje tylko, gdy `find_package(MPI)` znajdzie MPI — build MSVC idzie dalej bez MPI.
- **MPI w WSL:** OpenMPI 4.1.2 (`openmpi-bin`, `libopenmpi-dev` 4.1.2-2ubuntu1), `mpicxx --version` = g++ 11.4.0,
  `mpirun --version` = Open MPI 4.1.2. Implementacja i weryfikacja idą na GCC/OpenMPI.
- Tryb oszczędny: `powercfg /qh … PROCTHROTTLEMAX` i `PROCTHROTTLEMAX1` = 0x63 (99%) dla zasilania sieciowego i baterii;
  pętla w Pythonie przypięta do procesora logicznego 2, licznik „\Informacje o procesorze(0,2)\% wydajności procesora”:
  97,1 / 97,1 / 96,4 / 96,4 / 95,3% — **bez turbo**. WSL: `nproc` = 8, 7 GB. Tło 11–17%.
- Binarki odniesienia `engine_e9_msvc.exe`, `engine_e9_gcc` = obecne buildy Release (porównanie skrótów SHA-256).
- **Projekt (06:35–07:40).** Ustalenie z kodu reguł: w osi z reguły lawy NIE mają promienia 1 — `dropDepth()` (głębokość
  spadku z komórki powietrza) schodzi do 16 poziomów w dół, a `hasSupport()` najniższego czyta jeszcze komórkę pod
  spodem, więc pas z potrzebuje **17 warstw brzegowych pod sobą** (z głębszych niż pierwsza reguły czytają tylko typ)
  i 1 nad sobą; classic i MC — po 1 warstwie (promień sąsiedztwa). Wybór: pasy w osi warstw z etapu 9 (z; płaszczyzna
  x–y — y), bo to oś zewnętrzna pamięci: indeks globalny komórki okna = indeks w oknie + stała (`hashBase`), pas jest
  ciągłym fragmentem tablic (zbieranie `MPI_Gatherv` bez przepakowania), a `LavaCA` / `PottsMC` liczą okno tym samym
  kodem co engine (zakres warstw własnych zamiast wszystkich).
- Kod (06:40–07:40): `engine/src/parallel/Strip.*` (podział warstw, plan warstw brzegowych i komunikatów, interfejs
  `StripLink`), `LavaCA::setStrip` (warstwy własne, D(n) warstwy nad pasem, `hashBase_`, teren i poziomy przelewu
  z przesunięciem z, wymiana przed krokiem, listy src warstw brzegowych, sumy liczników), `PottsMC::setStrip` (kolory
  z położenia globalnego, wymiana po kolorze, energia — suma), `Boundary::withoutPeriodic`, warstwy w
  `VectorStorage` / `PottsMC`, `CoolingMobility` rozbite na składniki (koniec CA i zakres czasów — `MPI_Allreduce`),
  `McStage::statsJson` (wspólna sekcja mc w stats.json), config `parallel.priority` i `mpi.exchange` (walidacja,
  odczyt z `effective` — bez nowych pól `Config`), `--high-priority`, `CpuAffinity::raisePriority`,
  `pinThreadsFrom`; MPI: `engine/src/mpi/MpiHalo.*` (`Isend`/`Irecv` + `Waitall`, pakowanie warstw, `always` /
  `changed`), `MpiSimulation.*`, `main_mpi.cpp`; testy `engine/tests/test_strip.cpp`, `engine/tests/mpi/*`; CMake
  `VOLCANO_MPI`, cele `engine_mpi`, `engine_mpi_tests`, testy `mpi_np{1,2,3,4,5,8}` i dymne `mpi_cli_*`.
- W toku: build GCC Release (OpenMPI) + ctest, start 07:42, polecenie: `wsl -e bash -lc "cmake --preset gcc-release && cmake --build --preset gcc-release -j 4"`
  - 07:42–08:05 build GCC Release (`Found MPI_CXX … (found version "3.1")`) bez błędów i ostrzeżeń. WSL pracuje jako
    `root`, a OpenMPI bez `--allow-run-as-root` odmawia startu; WSL zgłasza 4 rdzenie, więc 8 procesów wymaga
    `--oversubscribe` — obie opcje (i `--bind-to none` dla trybu hybrydowego) CMake dodaje do testów, gdy `mpiexec
    --version` zgłasza Open MPI. Pierwsza próba wykrywała OpenMPI przez `MPI_CXX_LIBRARY_VERSION_STRING` (puste w tym
    FindMPI) — poprawione na `mpiexec --version`.
  - `engine_tests` 123/123 (318 388 asercji, w tym nowe `test_strip.cpp`); `engine_mpi_tests` pod `mpiexec -n 1/2/3/4/5/8`:
    9/9 przypadków na każdej liczbie procesów (276–364 asercje; tryb hybrydowy 4 wątki tylko przy 1 i 2 procesach —
    razem ≤ 8). `ctest --preset gcc-release` **21/21** (12 dotychczasowych + `mpi_np1…8` + 3 dymne `mpi_cli_*`).
  - **Czułość testów (mutacje, cofnięte po sprawdzeniu):** (1) lawa z 1 warstwą brzegową pod pasem zamiast 17 —
    4 przypadki lawy niezgodne (37 asercji) przy 3 procesach: głęboka warstwa brzegowa jest potrzebna i sprawdzana;
    (2) bez list src warstw brzegowych w automacie frontalnym — 6 przypadków (84 asercje): front gubiłby kandydatów
    na granicach pasów; (3) MC z wymianą tylko po ostatnim kolorze — 3 przypadki MC (9–19 asercji).
  - Przebieg dymny `mpiexec -n 3 engine_mpi --config configs/test_3d.json`: 284 kroki, sekcja `mpi` w `times.json`;
    obliczenia procesów 45,7 / 40,3 / 2,1 ms (lawa w dolnych warstwach — pas górny prawie bez pracy), czekanie na
    `MPI_Allreduce` to w praktyce czekanie na najwolniejszy pas. `mc.update = random` przy 2 procesach: komunikat
    i `MPI_Abort` z kodem 1.
- W toku: build MSVC Release (bez MPI — brak SDK) + ctest, start 08:12, polecenie: `cmake --preset msvc-release` + `cmake --build --preset msvc-release --parallel 4`
- W toku: zgodność domyślnego engine (e9 / e10, MSVC i GCC, 15 configów), start 08:20, polecenie: `python bench/compare_results.py --bin e9=bench/baseline/engine_e9_msvc.exe --bin e10=build/Release/engine.exe --bin e9_gcc=wsl:bench/baseline/engine_e9_gcc --bin e10_gcc=wsl:build-gcc-release/bin/engine --name zgodnosc_e10_engine --out bench/results/mpi`
- W toku: zgodność engine_mpi (GCC/OpenMPI) — wszystkie configi z `mc.update = checkerboard`: e9_gcc, m1, m3, m8, m3 i m8 z `mpi.exchange = changed`, m2×4, start 08:25, polecenie: `python bench/compare_results.py --set mc.update=checkerboard --bin e9_gcc=wsl:bench/baseline/engine_e9_gcc --bin m1=wsl:build-gcc-release/bin/engine_mpi … --launch "m1=mpiexec --allow-run-as-root --oversubscribe --bind-to none -n 1" … --name zgodnosc_mpi_gcc --out bench/results/mpi`
  - 08:20–08:21 `zgodnosc_e10_engine.md` — **15/15 configów: e9 = e10 = e9_gcc = e10_gcc** (domyślny engine po zmianach
    etapu 10 daje te same pliki co po etapie 9, MSVC i GCC; 29 s).
  - 08:25–08:36 `zgodnosc_mpi_gcc.md` (wszystkie configi z `mc.update = checkerboard`, także `mc_basalt` przez
    `--mc-from`) — **15/15: e9_gcc = m1 = m3 = m8 = m3 `changed` = m8 `changed` = m2×4** (2 procesy × 4 wątki).
- W toku: zgodność (B) domyślne configi (MC `random`) przy 1 procesie: e9 MSVC = e9_gcc = m1 (krzyżowo MSVC ↔ GCC/MPI);
  (C) `ca.sweep = full` + szachownica: e9_gcc, m3, m8, m2×4; start 08:40
- (Sesja przerwana limitem — wyniki B i C są zapisane, opis w sesji 2.)

### Część 1 — sesja 2 (20.10.2026, od 12:55)

Weryfikacja stanu zastanego (zegar systemowy; godziny sesji 1 w tym dzienniku są przesunięte względem czasów plików
o ok. 1 h — nie poprawiam ich, liczy się kolejność):

- `git status`: ostatni commit „etap 9: OpenMP”, zmiany etapu 10 niezatwierdzone (20 plików zmienionych, +626 / −129
  wierszy; nowe: `engine/src/mpi/`, `parallel/Strip.*`, `engine/tests/mpi/`, `test_strip.cpp`, `bench/scaling_mpi.py`,
  `bench/results/mpi/`, `docs/etap-10-mpi.md`) — zgodnie z dziennikiem.
- **SDK MS-MPI jest teraz zainstalowane:** `MSMPI_INC` = `C:\Program Files (x86)\Microsoft SDKs\MPI\Include\`,
  `MSMPI_LIB64` = `…\MPI\Lib\x64\`; są `mpi.h` (nagłówek deklaruje `MPI_VERSION 2`, `MPI_SUBVERSION 0` — MS-MPI 10.1
  ma część funkcji MPI-3, ale w nagłówku zgłasza 2.0) i `msmpi.lib`. Środowisko uruchomieniowe bez zmian
  (`mpiexec` 10.1.12498.52).
- Tryb oszczędny: `PROCTHROTTLEMAX` i `PROCTHROTTLEMAX1` = 0x63 (99%, sieć i bateria), `.wslconfig` `processors=8`,
  `memory=8GB`. Tło na starcie 33% CPU (narzędzia producenta laptopa działają).
- Zgodność z sesji 1 — wszystkie cztery tabele zapisane i kompletne: `zgodnosc_e10_engine.md` 15/15,
  `zgodnosc_mpi_gcc.md` 15/15, `zgodnosc_mpi_gcc_full.md` (`ca.sweep = full` + szachownica: m3 = m8 = m2×4 = e9_gcc)
  **15/15**, `zgodnosc_mpi_gcc_p1_random.md` (domyślne configi: e9_gcc = e9 MSVC, m1 = e9 MSVC) **15/15**.
- `bench/scaling_mpi.py` jeszcze nie był uruchomiony (brak `*_raw.csv` w `bench/results/mpi/`).
- Brak: binarek `engine_e10_*` / `engine_mpi_e10_*`, A/B narzutu, buildu MSVC z MPI, MSVC Debug, `VOLCANO_MPI=OFF`,
  `pytest`, doboru przypadków, `PLAN_POMIARU.md`.
- W toku: build MSVC Release z MS-MPI, start 12:58, polecenie: `cmake --preset msvc-release` (`Found MPI_CXX: …/msmpi.lib (found version "2.0")`) + `cmake --build --preset msvc-release --parallel 4`
  - 12:58–13:00 build bez błędów i **bez ostrzeżeń** (`/W4 /permissive-`; kod MPI kompiluje się z nagłówkiem MS-MPI
    bez zmian — przenośność z sesji 1 wystarczyła): `engine_mpi.exe`, `engine_mpi_tests.exe`, `volcano_mpi.lib`.
  - `ctest --preset msvc-release` **21/21** (54 s): 12 dotychczasowych + `mpi_np1/2/3/4/5/8` pod MS-MPI `mpiexec -n N`
    (każdy 3,3–4,8 s) + 3 dymne `mpi_cli_*`. Ręcznie: `mpiexec -n 3 engine_mpi_tests.exe` — 9/9 przypadków, 332 asercje;
    `mc.update = random` przy 2 procesach — komunikat po polsku na procesie 0 i `job aborted` (kod 1).
- **Przypinanie i priorytet w Windows (13:00–13:03)** — `mpiexec -n p engine_mpi … --high-priority --set
  parallel.affinity=pcores --thread-stats`, MC szachownica 100³ (`mc_cb_3d_100`); maski i priorytet procesów odczytane
  z zewnątrz w trakcie przebiegu (`Get-Process engine_mpi`: `ProcessorAffinity`, `PriorityClass`):
  - m4: maski 0x4, 0x10, 0x40, 0x100 → **procesory 2, 4, 6, 8** (proces r → r-ty rdzeń P listy 2, 4, …, 14, 0),
    priorytet `High` we wszystkich 4 procesach; `times.json` `mpi.cpus` = [[2], [4], [6], [8]], `mpi.priority` = 4 × high.
  - h2×4: maski 0x154 i 0x5401 → procesory {2, 4, 6, 8} i {10, 12, 14, 0}; `--thread-stats` procesu 0: każdy z 4 wątków
    pracował tylko na swoim procesorze (2 / 4 / 6 / 8). mcSim 915 ms (m4: 1 472 ms; e9 OpenMP 4 wątki — etap 9).
  - **`mpiexec -affinity` MS-MPI nie nadaje się na tym procesorze** (program z `parallel.affinity = none`, h4×2, wątki
    procesu 0 z `--thread-stats`): maska procesu zostaje pełna (0xFFFFFFFF), a `-affinity` (= `spr:L`, „rozłóż jak
    najdalej”) posłał wątki procesu 0 na **rdzenie E** (procesory 16–31); `-affinity_layout seq:P` związał oba wątki
    procesu z jednym procesorem logicznym (6) — w trybie hybrydowym wątki dzielą jeden procesor (mcSim 1 897 ms
    zamiast ~900); bez przypinania system rozrzuca wątki po rdzeniach P, E i wątkach SMT. MS-MPI nie rozróżnia rdzeni
    P i E, więc **przypina sam silnik** (`pinThreadsFrom`: maska procesu + wątek → procesor), tak samo na Windows
    i w Linuksie; `mpiexec` uruchamiany bez `-affinity`.
  - Komunikacja m4 (100³, Moore, 8 kolorów): 801 wymian (8 na MCS + 1 po inicjalizacji), 8 komunikatów i 332 936 B na
    wymianę, 104 ms średnio na proces (7% fazy); statystyki ziaren na procesie 0 — 864 ms union-find (część szeregowa,
    jak w etapie 9).
- W toku: przebudowa GCC Release (źródła `LavaCA.hpp`, `Storage.hpp`, `McRules.hpp` zmienione o 07:14, build GCC z 07:05), start 13:04, polecenie: `wsl -e bash -lc "cmake --preset gcc-release && cmake --build --preset gcc-release -j 4"`
  - 13:05–13:07 build GCC Release bez ostrzeżeń (102 s); `engine` i `engine_mpi` **bajtowo identyczne** z buildem
    z sesji 1 (SHA-256 bez zmian) — zmiany z 07:14 dotyczyły tylko komentarzy, więc tabele zgodności GCC z sesji 1 są
    aktualne.
- W toku: zgodność MSVC/MS-MPI (A) wszystkie configi z `mc.update = checkerboard`: e9 (MSVC), m1, m3, m8, c3/c8 (`changed`), m2×4 + krzyżowo m3_gcc (GCC/OpenMPI), start 13:06, polecenie: `python bench/compare_results.py --set mc.update=checkerboard --bin e9=bench/baseline/engine_e9_msvc.exe --bin m1=build/Release/engine_mpi.exe … --launch "m1=mpiexec -n 1" … --name zgodnosc_mpi_msvc --out bench/results/mpi`
  - 13:07–13:08 `zgodnosc_mpi_msvc.md` — **15/15: e9 (MSVC, szachownica) = m1 = m3 = m8 = c3 = c8 (`changed`) = m2×4
    = m3_gcc** (ostatnia kolumna krzyżowo: GCC/OpenMPI na 3 procesach = MSVC; 58 s).
  - 13:08–13:12 `zgodnosc_mpi_msvc_full.md` (`ca.sweep = full` + szachownica) — **15/15: e9 = m3 = m8 = m2×4 = m8_gcc**
    (259 s).
  - 13:12 `zgodnosc_mpi_msvc_p1_random.md` (domyślne configi, MC `random`) — **15/15: e9 = m1 = m1_gcc** (27 s).
- W toku: build GCC z `VOLCANO_MPI=OFF` (`build-gcc-nompi/`) + ctest, start 13:12, polecenie: `wsl -e bash -lc "cmake -S . -B build-gcc-nompi -G 'Unix Makefiles' -DCMAKE_CXX_COMPILER=g++ -DCMAKE_BUILD_TYPE=Release -DVOLCANO_MPI=OFF && cmake --build build-gcc-nompi -j 4 && ctest --test-dir build-gcc-nompi"`
  - 13:13–13:15 konfiguracja bez komunikatu o MPI (opcja wyłączona — `find_package(MPI)` nie jest wołane), build bez
    ostrzeżeń, cele `engine`, `engine_tests`, `mc_kernels`, `omp_overhead` (bez `engine_mpi`); `ctest` **12/12** (24 s).
- W toku: build MSVC Debug (z MS-MPI) + ctest, start 13:15, polecenie: `cmake --build --preset msvc-debug --parallel 4` + `ctest --preset msvc-debug`
  - 13:16–13:23 MSVC Debug: build bez błędów i ostrzeżeń (82 s); `ctest --preset msvc-debug` **21/21** (315 s:
    `unit_tests` 191 s, `mpi_np1…8` po 19–24 s pod `mpiexec`, asercje Debug w kodzie MPI i w oknach pasów włączone).
- Bez zmian: `engine` z `VOLCANO_MPI=OFF` (GCC) jest bajtowo identyczny z `engine` z buildu z MPI (SHA-256) —
  program bez MPI nie zależy od opcji.
- W toku: `python -m pytest gui\tests`, start 13:22
  - 13:24 `pytest gui\tests` — **102 passed** (14 s; GUI bez zmian poza opisami pól w `form.js`).
- Binarki etapu 10 (13:23): `bench/baseline/engine_e10_msvc.exe`, `engine_mpi_e10_msvc.exe` (= `build/Release/`,
  SHA-256 63e6a33c… / a37cf91a…), `engine_e10_gcc`, `engine_mpi_e10_gcc` (= `build-gcc-release/bin/`, 05385cda… /
  706edbcd…).
- W toku: zgodność domyślnego engine na binarkach e10 (odświeżenie `zgodnosc_e10_engine.md`) + 8 wątków z szachownicą (`zgodnosc_e10_engine_t8.md`), start 13:23, polecenie: `python bench/compare_results.py --bin e9=bench/baseline/engine_e9_msvc.exe --bin e10=bench/baseline/engine_e10_msvc.exe --bin e9_gcc=wsl:bench/baseline/engine_e9_gcc --bin e10_gcc=wsl:bench/baseline/engine_e10_gcc --name zgodnosc_e10_engine --out bench/results/mpi`
  - 13:23–13:24 `zgodnosc_e10_engine.md` (odświeżona na binarkach z `bench/baseline/`) — **15/15: e9 = e10 = e9_gcc =
    e10_gcc** (34 s); `zgodnosc_e10_engine_t8.md` (`parallel.threads = 8`, `mc.update = checkerboard`) — **15/15**
    (25 s).
- W toku: A/B narzutu domyślnego engine (e9 / e10, 1 wątek, przypięty do procesora 2), MSVC: ca_lava (15 powt.), ca_classic, mc bez 100³, start 13:24, polecenie: `python bench/ab.py --bin e9=bench/baseline/engine_e9_msvc.exe --bin e10=bench/baseline/engine_e10_msvc.exe --groups ca_lava --reps 15 --name ab_e10_msvc_ca_lava --out bench/results/mpi` (+ `--groups ca_classic --name ab_e10_msvc_ca_classic`, `--groups mc --cases mc_full_2d_200,mc_full_2d_1000,mc_full_3d_50,lava_mc_3d --name ab_e10_msvc_mc`)
  - (wstępnie) MSVC lawa caSim e10/e9: test_3d ×1,078, etna_real ×1,073, lava_mc_2d ×1,001; GCC: ×1,036 / ×1,035 / ×1,031 — powyżej progu 3%, szukam przyczyny w zmianach `LavaCA` (13:27)
- W toku: diagnoza narzutu MSVC — kopie źródeł e9 (`git archive HEAD`) i e10 w folderze tymczasowym, build `engine` z `/MAP` (mapa linkera, adresy funkcji automatu mod 64), start 13:28
  - 13:25–13:33 **diagnoza**: `--timing-detail` (e9 / e10 naprzemiennie, 11 powtórzeń, procesor 2): ramka, D(n)
    i `caFinish` bez zmian, **faza reguł frontu +8–9%** (`test_3d` 84,5 → 90,8 ms, `etna_real` 73,9 → 80,2 ms). Jedyna
    zmiana kodu w tej fazie: `gidx = idx + hashBase_` (losowość z indeksem globalnym okna pasa). Kopia lokalna pola
    (`const auto hashBase = hashBase_`) — bez zmian (×1,085). Próba bez `hashBase_` (kod reguł jak w e9, tylko
    pomiar): reguły nadal **+4,8%** — w MSVC większość to układ kodu. Mapy linkera kopii e9 (`git archive HEAD`) i e10
    (`/MAP`, `dumpbin /disasm`): `gatherLavaCandidates`, `frontCandidatesLayer`, `frontCandidatesRules`, `frontApply`,
    `frontDescent` — **kod maszynowy identyczny** instrukcja w instrukcję, ale przesunięty (mod 64: 0 → 48, 32 → 16,
    0 → 48, 32 → 16, 48 → 32); `frontRulesLayer` (48 → 0) ma dodatkowo inny przydział rejestrów (ramka stosu
    0x1A0 → 0x1A8) przez dodawanie `hashBase_`.
  - Poprawka (próba e10d): `frontRulesLayer<bool Shifted>` — wersja bez przesunięcia (`hashBase_ == 0`: engine,
    jeden proces, pierwszy pas) ma pętlę kandydatów jak w etapie 9, wersja z przesunięciem — dla pozostałych pasów.
- W toku: build e10d (GCC i MSVC, cel engine) + A/B lawy e9 / e10 / e10d, start 13:33
  - 13:34–13:37 A/B e9 / e10 / e10d: **MSVC** (`--timing-detail`, 11 powtórzeń) caSim `test_3d` ×1,077 → **×1,017**,
    `etna_real` ×1,071 → **×1,010** (reguły frontu ×1,088 → ×1,016–1,019); **GCC** (21 powtórzeń) e10 ×1,033–1,037,
    e10d ×1,033–1,050 — w GCC poprawka nie zmienia nic (e10d/e10 ×1,001–1,016, faza reguł +4% w obu). W GCC
    (`-falign-functions=64`, `nm -S`) zmieniły się decyzje o wstawianiu funkcji: `frontStepSequential` (z wstawionymi
    `frontCandidatesRules` / `frontCandidatesLayer` — pętle po warstwach `[ownLo_, ownHi_)` zamiast `[0, n)`) 2 252 →
    2 165 B, `frontRulesLayer` 2 398 → 2 510 B (e10) / 2 178 B (e10d `<false>`). Poprawka zostaje (MSVC −6 pkt, GCC
    bez zmian); pierwsza wersja zapisana jako `engine_e10a_*` / `engine_mpi_e10a_*`, tabele A/B lawy jako
    `ab_e10a_{msvc,gcc}_ca_lava.md`.
- W toku: pełne buildy z poprawką (MSVC Release + GCC Release, wszystkie cele) + ctest, start 13:37
  - 13:37–13:41 MSVC Release (wszystkie cele) i GCC Release: bez ostrzeżeń; `ctest` **21/21** w obu (55 s / 52 s).
- Binarki końcowe etapu 10 (13:41; poprzednie jako `*_e10a_*`): `engine_e10_msvc.exe` (33ad0f92…),
  `engine_mpi_e10_msvc.exe` (5fe0d9fd…), `engine_e10_gcc` (85f0e829… = `engine_e10d_gcc`), `engine_mpi_e10_gcc`
  (30144798…).
- W toku: ponowna zgodność po poprawce (front lawy): zgodnosc_e10_engine (+_t8), zgodnosc_mpi_msvc, zgodnosc_mpi_msvc_p1_random, potem GCC (zgodnosc_mpi_gcc, _p1_random), start 13:42 — te same polecenia co wyżej
  - 13:42–13:46 po poprawce — wszystkie bez różnic: `zgodnosc_e10_engine.md` **15/15** (e9 = e10 = e9_gcc = e10_gcc),
    `zgodnosc_e10_engine_t8.md` **15/15**, `zgodnosc_mpi_msvc.md` **15/15** (e9 = m1 = m3 = m8 = c3 = c8 = m2×4 =
    m3_gcc), `zgodnosc_mpi_msvc_p1_random.md` **15/15**, `zgodnosc_mpi_gcc.md` **15/15** (e9_gcc = m1 = m3 = m8 =
    m3/m8 `changed` = m2×4), `zgodnosc_mpi_gcc_p1_random.md` **15/15** (141 s). Tabele `ca.sweep = full`
    (`zgodnosc_mpi_{msvc,gcc}_full.md`) nie są powtarzane: pełny przebieg nie używa `frontRulesLayer` (zmiana dotyczy
    tylko automatu frontalnego), a kod pełnego przebiegu jest ten sam.
- W toku: A/B narzutu domyślnego engine na binarkach końcowych (e9 / e10), MSVC i GCC: ca_lava (15 powt.), ca_classic, mc bez 100³, start 13:47, polecenia: `python bench/ab.py [--wsl] --bin e9=bench/baseline/engine_e9_{msvc.exe,gcc} --bin e10=bench/baseline/engine_e10_{msvc.exe,gcc} --groups ca_lava --reps 15 --name ab_e10_{msvc,gcc}_ca_lava --out bench/results/mpi` (+ `--groups ca_classic`, `--groups mc --cases mc_full_2d_200,mc_full_2d_1000,mc_full_3d_50,lava_mc_3d`)
- W toku: GCC — granice warstw w kroku frontu (e10e: `frontStepSequential<bool Strip>`), start 13:59
  - 13:47–13:55 A/B e9 / e10d (binarki „końcowe” z 13:41), 1 wątek, procesor 2: **MSVC** lawa ×0,996–1,008, classic
    ×1,004–1,015, MC ×0,970–1,012 — dobrze; **GCC** lawa caSim ×1,039–1,051, classic ×1,016–1,158 (Moore 100³ ×1,158),
    `lava_mc_3d` caSim ×1,172, MC ×0,995–1,005 — **źle** (tabele zapisane jako `ab_e10d_*`).
  - 13:56–14:03 diagnoza GCC (`--timing-detail` w WSL, `taskset -c 2`, 9 powtórzeń): faza reguł frontu (kandydaci
    `frontCandidatesLayer`, wstawiani w `frontStepSequential`, + reguły) classic Moore 100³ **+21%**, lawa
    w `lava_mc_3d` **+20…30%**, już w e10a (nie przez szablon). Próba (tylko pomiar): w `frontStepSequential` granice
    `0 … layers_.size()` jak w e9 zamiast pól `ownLo_` / `ownHi_` / `descHi_` → +21% → +11%, +30% → +7%.
  - **Poprawka e10e:** `frontStepSequential<bool Strip>` i `frontCandidatesRules<bool Strip>` (+ `frontRulesLayer<Strip>`
    zamiast `<Shifted>`): bez pasów (`link_ == nullptr` — engine, 1 proces MPI) stałe granice `0 … n` i bez
    `hashBase_` — kod etapu 9; w oknie pasa — warstwy własne i indeks globalny. W wersji wielowątkowej wybór
    `<true>` / `<false>` na warstwę. Pomiar faz: **GCC** classic Moore 100³ caSim e10d ×1,188 → **e10e ×0,993**,
    `lava_mc_3d` ×1,169 → **×0,993**; **MSVC** `test_3d` ×1,010 → ×1,005, `lava_mc_3d` ×1,009 → ×1,011, classic Moore
    100³ ×1,026 → ×1,034 (w granicach „huśtawki” układu kodu MSVC). e10e przyjęta; e10d zapisana jako
    `engine_e10d_*` / `engine_mpi_e10d_*`.
- W toku: pełne buildy e10e (MSVC Release, GCC Release) + ctest, potem ponowna zgodność (6 tabel jak o 13:42) i końcowe A/B, start 14:01
  - 14:00–14:03 e10e: MSVC Release i GCC Release bez ostrzeżeń, `ctest` **21/21** w obu (54 s / 51 s).
- **Binarki końcowe etapu 10** (14:04): `engine_e10_msvc.exe` (1d58245b…), `engine_mpi_e10_msvc.exe` (d890853e…),
  `engine_e10_gcc` (8a3d35e6…), `engine_mpi_e10_gcc` (473a901c…).
  - 14:04–14:09 zgodność na binarkach końcowych — **wszystkie 15/15, 0 różnic**: `zgodnosc_e10_engine.md`,
    `zgodnosc_e10_engine_t8.md`, `zgodnosc_mpi_msvc.md` (e9 = m1 = m3 = m8 = c3 = c8 = m2×4 = m3_gcc),
    `zgodnosc_mpi_msvc_p1_random.md` (e9 = m1 = m1_gcc), `zgodnosc_mpi_gcc.md` (e9_gcc = m1 = m3 = m8 = m3/m8
    `changed` = m2×4), `zgodnosc_mpi_gcc_p1_random.md` (e9 = e9_gcc = m1); 263 s. Tabele `ca.sweep = full` z 13:08
    (MSVC) i z sesji 1 (GCC) zostają — pełny przebieg (`stepLava`, `fullStepParallel`) nie zmienił się od tamtej pory.
- W toku: końcowe A/B e9 / e10 (e10e), MSVC i GCC: ca_lava (15 powt.), ca_classic, mc bez 100³, start 14:09, polecenia jak o 13:47 (`--name ab_e10_{msvc,gcc}_{ca_lava,ca_classic,mc}`)
  - 14:09–14:17 **końcowe A/B e9 / e10** (1 wątek, procesor 2, naprzemiennie; wszystkie przebiegi bitowo zgodne):

    | Grupa | MSVC e10/e9 (faza) | MSVC (total) | GCC e10/e9 (faza) | GCC (total) |
    |---|---|---|---|---|
    | lawa `test_3d`, `etna_real`, `lava_mc_2d` (caSim, 15 powt.) | ×1,022 / ×1,017 / ×0,999 | — | ×0,995 / ×0,989 / ×0,985 | — |
    | classic 1000² VN / Moore, 100³ VN / Moore, 300³ (caSim) | ×1,001 / 1,007 / 1,001 / **1,042** / 1,005 | ×0,991–1,021 | ×0,998 / 0,982 / 1,010 / 0,996 / 0,942 | ×0,968–1,017 |
    | MC 200², 1000², 50³ (mcSim), `lava_mc_3d` (mcSim / caSim) | ×1,003 / 1,005 / 0,977, ×1,002 / 1,017 | ×0,976–1,004 | ×1,002 / 0,979 / 1,000, ×1,013 / 0,995 | ×0,979–1,017 |

    Narzut domyślnego `engine` po etapie 10: **cały przebieg ≤ 2,1%**, faza ≤ 2,2% poza classic Moore 100³ w MSVC
    (×1,042, cały przebieg ×1,021 — w granicach „huśtawki” układu kodu MSVC ±4%; GCC tego przypadku ×0,996).
    Tabele: `ab_e10_{msvc,gcc}_{ca_lava,ca_classic,mc}.md`; tło 20–30% (programy działające w tle).
- W toku: próba `scaling_mpi.py` (p. 2.5): Windows i WSL, `lava_etna_real`, m1 / m3, 1 powtórzenie, do `results/`, start 14:17, polecenie: `python bench/scaling_mpi.py [--wsl] --cases lava_etna_real --variants m1,m3 --reps 1 --min-reps 1 --name skalowanie_mpi_test --out results/skalowanie_mpi_test`
  - 14:18 próba `scaling_mpi.py` — działa w obu środowiskach: tabela `.md`, `.csv`, `_raw.csv`, przebiegi bitowo
    zgodne z m1; w surowym CSV `priority` = `high` we wszystkich procesach (Windows `HIGH_PRIORITY_CLASS`, WSL nice −5 —
    WSL pracuje jako root), `cpus` Windows 2 / 4 / 6, WSL 0 / 2 / 4 (procesory wirtualne). `lava_etna_real` przy 3
    procesach **wolniej niż przy 1** (MSVC caSim 90 → 180 ms; komunikacja 74% fazy, 1,78 MB na wymianę, obliczenia
    procesów 14 / 71 / 58 ms) — przypadek „za mały” zgodnie z oczekiwaniem. W WSL `total` m1 = 434 ms przy caSim 80 ms:
    `total` liczy od startu programu, więc obejmuje `MPI_Init_thread` (OpenMPI w WSL ~0,3 s).
- Dodane (14:19–14:22): **`mpi.initMs`** w `times.json` (`main_mpi.cpp` mierzy czas do końca `MPI_Init_thread`,
  `MpiSimulation::runFromCli(…, mpiInitMs)`; min / średnia / maks po procesach) i kolumna `initMax` w
  `scaling_mpi.py`. `test_3d` na 3 procesach: MS-MPI 11–17 ms, OpenMPI (WSL) 296–298 ms. `engine` bez zmian (SHA-256
  ten sam w MSVC i GCC), `ctest -R mpi` 9/9 w obu, kontrola zgodności (`test_3d`, `lava_mc_2d` + `mc_basalt`,
  `mc_full_3d`, `etna_real`; m3, m8, m3_gcc = e9) bez różnic. `engine_mpi_e10_msvc.exe` (524187df…) i
  `engine_mpi_e10_gcc` (d7a8bc1c…) podmienione.
- W toku: dobór przypadków (p. 4.1) — pojedyncze przebiegi (1 powtórzenie, komputer w zwykłym użyciu — czasy orientacyjne), MSVC: 7 przypadków × m1, m2, m3, m4, m6, m8, h2x4, h4x2, c8, o8; potem WSL: m1, m3, m8, h2x4, o8; start 14:22, polecenie: `python bench/scaling_mpi.py --variants m1,m2,m3,m4,m6,m8,h2x4,h4x2,c8,o8 --reps 1 --min-reps 1 --name dobor_msvc` (+ `--wsl --variants m1,m3,m8,h2x4,o8 --name dobor_gcc`)
  - 14:24–14:27 **dobór przypadków** — `dobor_msvc.md` (10 wariantów, 2,5 min, tło 16–21%) i `dobor_gcc.md` (5 wariantów,
    1,3 min); 1 powtórzenie, komputer w zwykłym użyciu — czasy orientacyjne; wszystkie przebiegi bitowo zgodne z m1.
    Faza obliczeń, MSVC (S fazy = T(m1) / T):

    | Przypadek | T(1) faza | m3 | m6 | m8 | h2×4 | h4×2 | c8 | o8 (OpenMP) | komunikacja / faza m8 |
    |---|---|---|---|---|---|---|---|---|---|
    | lawa 3D 128²×64 `full` | 13,9 s | 2,09 | 4,79 | 4,19 | **5,60** | 5,09 | 4,59 | 6,27 | 41% |
    | lawa 3D 128²×64 `front` | 793 ms | 1,38 | 2,22 | 2,36 | 2,62 | 2,66 | 2,52 | 4,62 | 68% |
    | classic 2000² | 577 ms | 2,91 | **5,51** | 1,77* | 3,96 | 4,66 | 4,17 | 5,35 | 91%* |
    | classic 300³ | 3,45 s | 2,32 | 3,54 | 3,24 | 3,84 | 3,88 | 3,15 | 5,02 | 38% |
    | MC szachownica 1000² | 2,09 s | 2,71 | 5,45 | 5,93 | 6,02 | 5,92 | 4,70 | 6,86 | 23% |
    | MC szachownica 100³ | 5,63 s | 2,16 | 4,92 | 4,18 | 5,82 | 5,33 | 5,21 | 5,55 | 42% |
    | `etna_real` | 94 ms | 0,53 | 0,52 | 0,40 | 0,67 | 0,45 | 0,56 | 2,23 | 86% |

    (* jeden zakłócony przebieg: obliczenia procesu 4 — 57 ms przy 18–28 ms pozostałych.) GCC/OpenMPI (WSL): `full`
    m3 2,44, m8 3,98, h2×4 4,86, o8 3,89; classic 2000² m8 5,15; MC 1000² m8 4,56; `etna_real` m3 0,59.
  - **Wnioski do planu** (z `computePerRank`, `haloAvg`, `reduceAvg` w `dobor_msvc_raw.csv`):
    - **Procesor 0 jest wolniejszy.** Proces na procesorze logicznym 0 (8. rdzeń P; obsługuje przerwania systemu) liczy
      pas 30–60% dłużej niż procesy na 2–14: classic 300³ m8 873 ms przy 593–692 ms pozostałych, MC 1000² 336 / 250–285,
      MC 100³ 1 057 / 650–922; to samo w h4×2 (proces 3 z procesorami 14 i 0). Pasy są statyczne, więc najwolniejszy
      proces wyznacza czas kroku — dlatego m8 bywa wolniejsze od m6. W planie dodatkowo **m7** (7 procesów, bez procesora 0).
    - **Lawa: ogranicza nierównomierność, nie bajty.** Front dużej lawy m8: wymiana warstw 82 ms na 260 wymian
      (~0,3 ms na krok, 3,85 MB), a czekanie w `MPI_Allreduce` 145 ms — obliczenia procesów 10–216 ms (lawa spływa po
      dolnych warstwach, górne pasy prawie bez pracy). 17 warstw brzegowych pod pasem kosztuje bajty (m8: 3,85 MB na
      wymianę, z tego 1,72 MB to 102 głębsze warstwy samego typu; przy 1 warstwie z każdej strony byłoby 2,13 MB), ale
      przez pamięć współdzieloną to tylko ~0,3 ms na krok.
    - **Przestaje się opłacać,** gdy krok procesu jest krótszy niż ~1 ms: `etna_real` (krok frontu 0,33 ms przy 1 procesie,
      1,8 MB na wymianę przy 3 procesach — ~0,3 ms wymiany + `MPI_Allreduce` co krok) jest wolniejsza przy każdej liczbie
      procesów (S = 0,4–0,7), a front dużej lawy daje najwyżej ~2,6×. Pełny przebieg (krok 54 ms) skaluje do ~5,6×.
    - **`changed`:** w lawie m8 pomija 14 985 z 30 160 warstw (116 na wymianę × 260; front 3,85 → 2,14 MB na wymianę),
      w classic i MC prawie nic (warstwy zmieniają się co krok) — tam to tylko koszt porównania.
    - **Tryb hybrydowy** (h2×4 albo h4×2) jest najlepszym wariantem MPI na 8 rdzeniach w 6 z 7 przypadków (wyjątek:
      classic 2000², m6 = 5,51): mniej pasów — mniej warstw brzegowych i mniejsza nierównomierność, a wolniejszy
      procesor 0 dzieli pas z innymi wątkami procesu.
    - **`MPI_Init`** jest wliczony w `total`: MS-MPI zwykle 12–40 ms (do 128 ms), OpenMPI w WSL 265–410 ms (`initMax`)
      — S(p) całego przebiegu w WSL jest przez to zaniżone; główną miarą jest faza obliczeń.
  - 14:28–14:30 OpenMPI w WSL: **`--use-hwthread-cpus` zamiast `--oversubscribe`** — OpenMPI widzi 4 rdzenie × 2 wątki
    SMT, a z tą opcją ma 8 miejsc, więc 8 procesów nie jest nadsubskrypcją (przy nadsubskrypcji OpenMPI może przejść w
    tryb oddawania procesora podczas czekania). m8, naprzemiennie: classic 2000² 122 / 136 / 103 ms (`--oversubscribe`)
    vs 154 / 101 / 101 ms, MC 1000² 447 / 434 vs 464 / 425 ms — różnica w granicach szumu. `scaling_mpi.py --wsl`
    używa teraz `--use-hwthread-cpus` (sprawdzone: m1, m8, h2×4 na `etna_real`); testy CMake zostają przy
    `--oversubscribe` (poprawność, nie czas).
- 14:35 `bench/results/mpi/PLAN_POMIARU.md` — 6 części (MSVC 4 × ≤ 6 min, GCC 2 × ≤ 4,5 min), ~30 min razem; warianty MSVC m1–m8 + m7 (bez procesora 0), h2×4, h4×2, c4, c8, o4, o8 (OpenMP w tym samym przebiegu); GCC m1, m3, m8, h2×4, o8. Sprawdzenie poleceń planu: próba przypięcia z p. 0 i krótkie przebiegi m7 / c4 / o4 (niżej).
- GUI (p. 3) — **pominięte**: liczba procesów nie jest polem configu symulacji, więc `mpiexec -n N engine_mpi` z kolejki
  wymagałby osobnej ścieżki formularz → zadanie → polecenie (`jobs.json`, ponowienie, serie), wykrywania `engine_mpi`
  i `mpiexec`, priorytetu bez przypięcia i walidacji `random` przy > 1 procesie, z testami; pola `parallel.priority`
  i `mpi.exchange` są w formularzu (z `--print-defaults`). Opis w `docs/etap-10-mpi.md`, punkt 7.
- Dokumentacja (14:30–14:40): `docs/etap-10-mpi.md` — MS-MPI z SDK, `--use-hwthread-cpus`, `mpi.initMs`, przypinanie
  w Windows i `mpiexec -affinity`, GUI, tabela zgodności MSVC i GCC (8 tabel), punkt 8.1 (narzut `engine`: e10a →
  e10d → e10e), 8.2 (dobór przypadków i wstępne obserwacje), ograniczenia; `docs/uruchamianie.md` — MS-MPI i OpenMPI
  w wymaganiach, `VOLCANO_MPI`, testy MPI (21), punkt 4.2 (`engine_mpi`), 7.3 (skalowanie MPI), `--high-priority`,
  `parallel.priority`, `mpi.exchange`, sekcja `mpi` w `times.json` — polecenia z 4.2 i 7.3 sprawdzone (kod 0);
  `docs/README.md` — etap 10 w spisie; `docs/architektura.md` — numery linii zmienionych plików (`LavaCA.hpp`,
  `PottsMC.*`, `Storage.hpp`, `Boundary.hpp`, `Config.cpp`, `Cli.cpp`, `Simulation.cpp`, `McStage.cpp`,
  `CoolingMobility.cpp`, `Affinity.cpp`; wyliczone z definicji funkcji, sprawdzone na źródłach e9) i fragment
  `frontStepSequential<Strip>`. Opis kodu MPI krok po kroku w `architektura.md` — część 2.

## Stan na koniec części 1 — gotowe do cichego pomiaru

**Gotowe:**

- `engine_mpi` (MS-MPI 10.1 z SDK / OpenMPI 4.1.2): rozsyłanie configu i terenu, pasy warstw z warstwami brzegowymi
  (lawa 17 pod + 1 nad, classic i MC po 1), wymiana `Isend`/`Irecv` + `Waitall` (`always` / `changed`), liczniki
  i reguła końca przez `MPI_Allreduce`, kratery i zarodki z globalnej listy, losowość z indeksem globalnym, MC
  szachownicą z wymianą po kolorze, zebranie wyników `MPI_Gatherv`, `times.json` z sekcją `mpi` (komunikacja,
  obliczenia na proces, bajty, `initMs`, procesory, priorytet), `--high-priority`, przypinanie procesów do rdzeni P.
- **Poprawność:** `ctest` 21/21 — MSVC Release i Debug, GCC Release (testy MPI 9/9 przypadków na 1, 2, 3, 4, 5
  i 8 procesach); GCC bez MPI 12/12; `pytest` 102/102; zgodność wszystkich 15 configów bajt po bajcie: e9 = m1 = m3 = m8
  = `changed` = 2 × 4 wątki w MSVC/MS-MPI i GCC/OpenMPI, krzyżowo MS-MPI = OpenMPI, `full`, `random` przy 1 procesie
  (8 tabel `zgodnosc_*.md`, ostatnio na binarkach końcowych 14:04–14:09 + kontrola po `initMs` 14:22).
- **`engine` bez zmian:** wyniki = e9 (15/15, 1 i 8 wątków, MSVC i GCC); narzut po poprawce `frontStepSequential<Strip>`
  — cały przebieg ×0,968–1,021, faza ≤ +2,2% (poza classic Moore 100³ MSVC ×1,042 — „huśtawka” układu kodu).
- **Binarki do pomiaru** (`bench/baseline/`, lokalne): `engine_mpi_e10_msvc.exe` (524187df…), `engine_e10_msvc.exe`
  (1d58245b…), `engine_mpi_e10_gcc` (d7a8bc1c…), `engine_e10_gcc` (8a3d35e6…). Wersje pośrednie: `*_e10a_*`
  (pierwsza), `*_e10d_*` (poprawka tylko `frontRulesLayer`).
- **Plan:** [`PLAN_POMIARU.md`](PLAN_POMIARU.md) — przygotowanie (tryb oszczędny, tło, skróty binarek, próba
  przypięcia), 7 przypadków, MSVC 13 wariantów (m1–m4, m6, m7, m8, h2×4, h4×2, c4, c8, o4, o8) w 4 częściach,
  GCC 5 wariantów w 2 częściach, scalanie `--from-raw`; **~30 min**.

**Od czego zacząć część 2:** `PLAN_POMIARU.md` punkt 0 (warunki, skróty binarek — przy innych skrótach najpierw build,
`ctest`, tabele zgodności), potem części A1 → A2 → B → C → D → E z linią „W toku” w tym dzienniku przed każdą.
Na co uważać: proces na procesorze 0 (m8, h4×2) — porównać m7 i m8 (`computePerRank`); `total` w WSL zawiera
`MPI_Init` (~0,3 s, `initMax`); `etna_real` ma być wolniejsza przy wielu procesach (przypadek „za mały”).

## Część 2 — cichy pomiar i dokumentacja (21.10.2026, od 03:21)

Weryfikacja przed pomiarem (03:21–03:25, bez pomiarów):

- `git status`: ostatni commit „etap 9: OpenMP”, zmiany etapu 10 niezatwierdzone (24 pliki zmienione; nowe:
  `engine/src/mpi/`, `parallel/Strip.*`, `engine/tests/mpi/`, `test_strip.cpp`, `bench/scaling_mpi.py`,
  `bench/results/mpi/`, `docs/etap-10-mpi.md`) — zgodnie z dziennikiem; najnowsze źródła `engine/` z 20.10 14:19,
  binarki z 14:21.
- **Binarki = plan:** SHA-256 `engine_mpi_e10_msvc.exe` 524187df…, `engine_e10_msvc.exe` 1d58245b…, `engine_mpi_e10_gcc`
  d7a8bc1c…, `engine_e10_gcc` 8a3d35e6… — te same co w `PLAN_POMIARU.md` i co obecne buildy Release
  (`build/Release/`, `build-gcc-release/bin/`).
- MPI: `mpiexec` MS-MPI 10.1.12498.52, OpenMPI 4.1.2 (`mpicxx` = g++ 11.4.0) — oba uruchamiają `engine_mpi` na 3
  procesach (`test_3d`).
- Tryb oszczędny: `PROCTHROTTLEMAX` i `PROCTHROTTLEMAX1` = 0x63 (99%, sieć i bateria), zasilanie sieciowe (100%),
  `.wslconfig` `processors=8`, `memory=8GB`, `nproc` = 8; pętla przypięta do procesora 2 — „% wydajności procesora”
  94,8–97,2% (**bez turbo**). Tło 16% (programy działające w tle, ~2 procesory logiczne).
- Próba przypięcia (plan, p. 0.4): Windows `[[2], [4], [6]]`, 3 × `high`; WSL `[[0], [2], [4]]`, 3 × `high`.
- Próba `scaling_mpi.py` (`lava_etna_real`, m1 / m3, 1 powtórzenie, `results/proba_cz2/`): 11 s, bitowo zgodne,
  `priority` / `cpus` w surowym CSV jak w części 1; faza m1 91,7 ms, m3 166 ms (komunikacja 72%).

Cichy pomiar wg `PLAN_POMIARU.md` (części A1 → A2 → B → C → D → E, przerwa ~1 min między częściami):

- W toku: część A1 (MSVC, `lava_etna_real` + `lava_duza_3d_front`, 13 wariantów), start 03:24, polecenie: `python bench\scaling_mpi.py --bin bench\baseline\engine_mpi_e10_msvc.exe --omp-bin bench\baseline\engine_e10_msvc.exe --variants m1,m2,m3,m4,m6,m7,m8,h2x4,h4x2,c4,c8,o4,o8 --cases lava_etna_real,lava_duza_3d_front --name skalowanie_mpi_msvc_cz1`
  - 03:24–03:26 `skalowanie_mpi_msvc_cz1.*` — 1,8 min, **tło 13% → 14%**, wszystkie przebiegi bitowo zgodne z m1;
    `priority` = `high` we wszystkich procesach, `cpus` jak w planie (m7 bez 0, h2×4 `2/4/6/8 10/12/14/0`), bajty na
    wymianę stałe między powtórzeniami. Faza: Etna m1 92,0 ms, m3 167 (S 0,55), m8 203 (0,45), h2×4 116 (0,80), o8 18,5
    (4,96); front dużej lawy m1 762 ms, m3 538 (1,42), m7 302 (2,52), m8 340 (2,24), h2×4 288 (2,64), o8 126 (6,03).
    Front m8: najdłużej liczy pas dolny (proces 0, procesor 2: ~200 ms), proces na procesorze 0 (pas górny) ~9 ms —
    tu ogranicza nierównomierność, nie procesor 0. Bez powtórzenia.
- W toku: część A2 (MSVC, `lava_duza_3d_full`), start 03:28, polecenie: to samo z `--cases lava_duza_3d_full --name skalowanie_mpi_msvc_cz2`
  - 03:28–03:33 `skalowanie_mpi_msvc_cz2.*` — 5,1 min, **tło 24% → 14%** (na starcie chwilowo pobieranie w tle),
    bitowo zgodne. Faza m1 13 415 ms [13 395–13 447], m3 5 406 (S 2,48), m6 2 871 (4,67), m7 2 506 (5,35), m8 2 960
    (4,53), h2×4 2 487 (5,39), o8 2 164 (6,20). **Procesor 0:** w m8 ostatni proces (procesor 0, pas górny) liczy
    2 460–2 770 ms przy 2 080–2 130 ms pasów pod nim — w każdym powtórzeniu, więc m7 < m8. Rozrzut m8 i c8 (pojedyncze
    przebiegi +25–35%: m8 3 628, c8 3 700 / 3 600) w różnych powtórzeniach, nie na początku części — przy 8 procesach na
    8 rdzeniach P każde wejście programu w tle zatrzymuje krok; mediana z 5 stabilna. Bez powtórzenia (tło < 30%).
- W toku: część B (MSVC, classic 2000² + 300³), start 03:35, polecenie: to samo z `--cases classic_2000x2000_s400_vn,classic_300x300x300_s100_vn --name skalowanie_mpi_msvc_cz3`
  - 03:34–03:38 `skalowanie_mpi_msvc_cz3.*` — 4,0 min, **tło 18% → 14%**, bitowo zgodne. Classic 2000²: faza m1 539 ms,
    m2 263 (S 2,05), m4 137 (3,94), m7 80,7 (**6,68**), m8 90,3 (5,97), o8 86,1 (6,26) — m7 szybsze od OpenMP na
    8 rdzeniach; w m8 proces na procesorze 0 liczy 54–95 ms przy 49–56 ms pozostałych (4 z 7 powtórzeń). Classic 300³:
    m1 3 379 ms, m4 1 179 (2,87), m7 932 (3,62), m8 1 019 (3,32), h2×4 866 (3,90), o8 717 (4,72); m8 procesor 0
    727–831 ms przy 600–698 ms. Bez powtórzenia.
- W toku: część C (MSVC, MC szachownica 1000² + 100³), start 03:39, polecenie: to samo z `--cases mc_cb_2d_1000,mc_cb_3d_100 --name skalowanie_mpi_msvc_cz4`
  - 03:40–03:44 `skalowanie_mpi_msvc_cz4.*` — 4,4 min, **tło 13% → 13%**, bitowo zgodne. MC 1000²: faza m1 2 052 ms,
    m4 518 (3,96), m7 305 (**6,72**), m8 340 (6,03), o8 336 (6,10); MC 100³: m1 5 741, m4 1 519 (3,78), m7 963 (5,96),
    m8 1 035 (5,55), h4×2 956 (6,00), o8 916 (6,27). m8: proces na procesorze 0 — 1000² 292–367 ms przy 245–260,
    100³ 817–1 011 przy 676–776 (w każdym powtórzeniu). Bez powtórzenia.
- 03:45 scalenie MSVC: `skalowanie_mpi_msvc.{md,csv}` (`--from-raw` z 4 części).
- W toku: część D (GCC/OpenMPI w WSL, lawa: Etna, front, full; m1, m3, m8, h2×4, o8), start 03:46, polecenie: `python bench\scaling_mpi.py --wsl --bin bench/baseline/engine_mpi_e10_gcc --omp-bin bench/baseline/engine_e10_gcc --variants m1,m3,m8,h2x4,o8 --cases lava_etna_real,lava_duza_3d_front,lava_duza_3d_full --name skalowanie_mpi_gcc_cz1`
  - 03:46–03:49 `skalowanie_mpi_gcc_cz1.*` — 3,1 min, **tło (Windows) 12% → 19%**, bitowo zgodne; `cpus` WSL
    `0 2 4 6 1 3 5 7` (m8), h2×4 `0/2/4/6 1/3/5/7`, `priority` = `high`. Faza: Etna m1 81,7 ms, m8 176 (0,46), h2×4 80,3
    (1,02), o8 21,2 (3,86); front m1 681, m8 298 (2,28), h2×4 244 (2,79), o8 151 (4,52); full m1 11 621, m3 4 454
    (2,61), m8 2 374 (4,89), h2×4 2 125 (5,47), o8 1 966 (5,91). m1 w GCC w pierwszych 3 powtórzeniach ~8% wolniejszy
    niż w ostatnich (full 11,75 → 10,72 s, front 734 → 668 ms) — procesory wirtualne WSL; mediany. `total` w WSL
    zawiera start OpenMPI (~0,3 s). Bez powtórzenia.
- W toku: część E (GCC/OpenMPI, classic 2000² + 300³, MC 1000² + 100³), start 03:50, polecenie: to samo z `--cases classic_2000x2000_s400_vn,classic_300x300x300_s100_vn,mc_cb_2d_1000,mc_cb_3d_100 --name skalowanie_mpi_gcc_cz2`
  - 03:50–03:54 `skalowanie_mpi_gcc_cz2.*` — 3,9 min, **tło (Windows) 17% → 10%**, bitowo zgodne. Faza: classic 2000²
    m1 487 ms, m8 106 (4,59), h2×4 117 (4,17), o8 90,1 (5,41); classic 300³ m1 3 196, m8 961 (3,33), h2×4 768 (4,16),
    o8 743 (4,30); MC 1000² m1 2 010, m8 372 (5,40), h2×4 336 (5,98), o8 341 (5,89); MC 100³ m1 5 391, m8 1 079
    (4,99), h2×4 991 (5,44), o8 861 (6,26). Bez powtórzenia.
- 03:55 scalenie GCC: `skalowanie_mpi_gcc.{md,csv}`.
- **Cichy pomiar skończony 03:55** (03:24–03:54, 6 części, 22,3 min pomiaru + przerwy): żadna część nie była
  powtarzana — tło 10–24% (< 30%), w każdej części wszystkie przebiegi bitowo zgodne z m1, `priority` = `high`
  i `cpus` zgodne z planem we wszystkich procesach.

Po pomiarze (komputer wolny):

- W toku: zgodność `ca.sweep = full` na binarkach końcowych (tabele z 13:08 i z sesji 1 liczone przed poprawką `frontStepSequential<Strip>`), MSVC: e9 vs `engine_mpi_e10_msvc.exe` m3, m8, m2×4 + m8_gcc, start 03:57, polecenie: `python bench\compare_results.py --set ca.sweep=full --set mc.update=checkerboard --bin e9=bench\baseline\engine_e9_msvc.exe --bin m3=bench\baseline\engine_mpi_e10_msvc.exe --bin m8=bench\baseline\engine_mpi_e10_msvc.exe --bin m2x4=bench\baseline\engine_mpi_e10_msvc.exe --bin m8_gcc=wsl:bench/baseline/engine_mpi_e10_gcc --launch "m3=mpiexec -n 3" --launch "m8=mpiexec -n 8" --launch "m2x4=mpiexec -n 2" --args "m2x4=--threads 4" --launch "m8_gcc=mpiexec --allow-run-as-root --oversubscribe --bind-to none -n 8" --name zgodnosc_mpi_msvc_full --out bench\results\mpi` (potem GCC: e9_gcc vs m3, m8, m2×4 → `zgodnosc_mpi_gcc_full`)
  - 03:55–03:59 `zgodnosc_mpi_msvc_full.md` (odświeżona, binarki `bench/baseline/engine_mpi_e10_*`) — **15/15, 0 różnic:
    e9 = m3 = m8 = m2×4 = m8_gcc** (`ca.sweep = full`, MC szachownicą; 4,2 min).
  - 03:59–04:03 `zgodnosc_mpi_gcc_full.md` (odświeżona; `--launch` z `--oversubscribe` jak w części 1) — **15/15,
    0 różnic: e9_gcc = m3 = m8 = m2×4** (3,9 min). Wszystkie 8 tabel zgodności dotyczą teraz binarek końcowych.
- Wykresy: `bench/plot_etap10.py` (nowy, na wzór `plot_etap9.py`) → `docs/img/etap10_*.png`.
  - 04:04–04:10 8 wykresów (`etap10_podzial`, `_skalowanie`, `_amdahl`, `_mpi_omp`, `_hybryda`, `_komunikacja`,
    `_obciazenie`, `_wymiana`), każdy obejrzany; poprawki po obejrzeniu: podpis w schemacie, Etna w Amdahlu bez
    dopasowania (S < 1), kolory MPI / OpenMP (niebieski / pomarańczowy zamiast dwóch niebieskich), legendy nad danymi,
    proces na procesorze 0 kreskowany (nie tylko kolor), bajty `always` w podpisach osi zamiast nad słupkami. OpenMP
    z etapu 9 (`bench/results/omp/skalowanie_{msvc,gcc}.csv`) jako romb kontrolny na wykresie MPI vs OpenMP.
- Dokumentacja (04:10–04:21): `docs/etap-10-mpi.md` — pełna wersja (wynik w skrócie, czas `MPI_Bcast`, zebranie
  `MPI_Gatherv`, `MPI_Init`, tabela bajtów, koszt statystyk MC, punkt 9 „Wyniki pomiaru” 9.1–9.10, ograniczenia,
  wnioski dla etapu 11: `MPI_Type_create_struct` / `hindexed` / `contiguous` dla warstw, MPI-IO `write_at_all`
  zamiast `Gatherv` + zapisu na procesie 0).
  `docs/architektura.md` — krok 6b (MPI, numery linii `main_mpi.cpp`, `MpiSimulation.cpp`, `MpiHalo.cpp`, `Strip.cpp`,
  `LavaCA.hpp`, `PottsMC.cpp` — sprawdzone na źródłach), mapa, ściąga, słowniczek, FAQ „MPI czy OpenMP”;
  `docs/uruchamianie.md` (7.3: `plot_etap10.py`, wyniki), `docs/README.md`, `README.md` (wynik MPI, dalszy rozwój),
  `bench/README.md`, szablon `tools/export_minimal/README.md` (instalacja MS-MPI / OpenMPI, `engine_mpi`).
- Eksport (04:15) do folderu tymczasowego (nie do repozytorium wersji minimalnej): 213 plików, odnośniki 0 błędów,
  ścieżki `docs/` w kodzie 0; **kontrola słownictwa: 4 trafienia — fałszywe**: nazwa zmiennej `p1`
  w `engine/tests/test_strip.cpp:145–148` pasuje do jednego z lokalnych wzorców (kod silnika zamknięty — nie zmieniam;
  do decyzji: zmiana nazwy zmiennej albo wzorzec z rozróżnianiem wielkości liter). Eksport zawiera `engine/src/mpi/`,
  `engine/tests/mpi/`, `VOLCANO_MPI` w CMake, `scaling_mpi.py`, `plot_etap10.py`; **build `engine_mpi` z eksportu
  (MSVC, MS-MPI) udany**, wynik `test_3d` na 3 procesach = wynik `engine_mpi_e10_msvc.exe` (SHA-256 `ca_result.bin`).
  Słownictwo w zmienionych plikach pełnego repozytorium: tylko dozwolone ostatnie zdanie `README.md`.

## Stan na koniec części 2 — etap 10 zakończony

- **Pomiar:** 6 części wg planu, 810 przebiegów, wszystkie bitowo zgodne z 1 procesem, `high` i rdzenie P zgodne
  z planem; tło 10–24%, bez powtórzeń. Tabele `skalowanie_mpi_{msvc,gcc}.md`.
- **Główne wyniki (MSVC, faza):** MC 1000² S(7) = 6,72, classic 2000² 6,68 (> OpenMP 8 wątków 6,10 / 6,26), MC 100³
  h4×2 6,00, pełny przebieg lawy h2×4 5,39, classic 300³ h2×4 3,90, front lawy h2×4 2,64, Etna ≤ 0,80 (MPI wolniejsze).
  S(8) < S(7) wszędzie (procesor 0, 13–30% dłuższe obliczenia pasu); udział komunikacji przy 8 procesach 21–84%,
  głównie czekanie na najwolniejszy pas; `changed`: lawa 20–57% bajtów (Etna −22% czasu), MC 100³ 50%, MC 1000² 100%.
- **Zgodność:** wszystkie 8 tabel `zgodnosc_*.md` na binarkach końcowych 15/15.
- **Do decyzji:** fałszywe trafienie słownictwa (`p1` w `test_strip.cpp`) przy eksporcie.
