# Etap 12 — dziennik postępu (testy wydajności: przyspieszenie, efektywność, pamięć, pamięć podręczna)

Plik prowadzony na bieżąco w trakcie etapu 12: każdy krok, jego pliki, wyniki i warunki. Opis i wnioski:
[`docs/etap-12-testy-wydajnosci.md`](../../../docs/etap-12-testy-wydajnosci.md). Poprzednie etapy: OpenMP
[`../omp/POSTEP.md`](../omp/POSTEP.md), MPI [`../mpi/POSTEP.md`](../mpi/POSTEP.md), typy MPI i MPI-IO
[`../mpi_io/POSTEP.md`](../mpi_io/POSTEP.md), optymalizacja sekwencyjna [`../ab/POSTEP.md`](../ab/POSTEP.md).

**Zasada etapu: nie powtarzamy pomiarów, które już są.** Przyspieszenie i efektywność OpenMP (etap 9), MPI i hybrydy
(etap 10) oraz typów pochodnych / MPI-IO (etap 11) zmierzono z bitową zgodnością każdego przebiegu, a programy później
nie zmieniły zachowania ani szybkości (A/B `ab_e10_*`, `ab_e11_*`) — te dane są tu zestawione. Mierzone jest tylko to,
czego brakowało: skalowanie słabe, pamięć główna wersji równoległych, pamięć podręczna, przepustowość pamięci.

Część 1 (ta): zestawienie istniejących danych, pomiary pamięci (RSS — nie zależą od tła) i symulacja pamięci
podręcznej (cachegrind — liczy zdarzenia, nie czas), przygotowanie i sprawdzenie na małych przypadkach pomiarów czasu.
Część 2: krótki cichy pomiar czasu wg [`PLAN_POMIARU.md`](PLAN_POMIARU.md).

Ustawienia pomiarów MPI w tym etapie (wnioski z etapu 11): `mpi.pack = datatype`; w WSL ROMIO (`mpiexec --mca io
romio321`) tam, gdzie jest zapis MPI-IO; w testach skalowania `output.format = none` albo `bin` (zapis zestawiony
osobno w etapie 11). Tryb oszczędny (od etapu 8, do końca projektu): procesor bez turbo, WSL 8 procesorów / 8 GB,
buildy `--parallel 4` / `-j 4`, jedna ciężka operacja naraz, łącznie najwyżej 8 procesów × wątków na rdzeniach P.

## Tabela kroków

| Krok | Stan | Pliki wyników | Wynik | Uwagi |
|---|---|---|---|---|
| 0 Warunki | zrobione | `procesor.md` | `PROCTHROTTLEMAX` i `PROCTHROTTLEMAX1` = 99% (sieć i bateria), zasilanie sieciowe; WSL `nproc` = 8, 7 GB; buildy = binarki etapu 11 (SHA-256); licznik „% wydajności procesora” 97% | — |
| 1 Zestawienie S / E | zrobione | `zestawienie.{md,csv}`, `zestawienie_lacznie.csv` | najlepsze S fazy (MSVC): OpenMP 8 — lawa full 6,34, Etna 4,98; MPI 7 — classic 2000² 6,68, MC 1000² 6,72; łącznie Etna ×1 871, classic 300³ ×50, MC ×47 / ×39 | bez nowych przebiegów |
| 2 Pamięć główna | zrobione | `pamiec_{msvc,gcc}.md`, `_raw.csv` | wątki 8 / 1 = 0,96–1,05; suma MPI przy 8 procesach: classic ×1,00–1,14, lawa ×1,71–1,84 (warstwy brzegowe 59%); proces 0 gather → MPI-IO ×0,25; model ±8% (CA) | przy tle — RSS od niego nie zależy |
| 3 Pamięć podręczna (cachegrind) | zrobione | `cachegrind.{md,csv}`, `bench/profiles/cachegrind/` | szachownica ×10–12 mniej chybień D1 niż random; front ×19 mniej niż full; progi L2 / L3 / RAM zgodne z rozmiarem zbioru roboczego | symulacja, bez liczników |
| 4 Skalowanie słabe (`--weak`) | zrobione (część 2) | `slabe_{omp,mpi}_{msvc,gcc}.*` | E_w(8) fazy OpenMP: classic 0,49, MC 0,87, lawa full 0,88, front 1,00; MPI 7 / 8: 0,61 / 0,49, 0,97 / 0,84, 0,78 / 0,67, 0,27 / 0,25 | A, B, C1, C2 |
| 5 Krzywa czasu na komórkę | zrobione (część 2) | `krzywa_{msvc,gcc}.*` | MC random 36 → 169 ns (×4,6), próg L2 przy 131 → 262 tys. komórek; classic i szachownica bez progu | D, E |
| 6 Przepustowość, fałszywe współdzielenie | zrobione (część 2) | `przepustowosc_{msvc,gcc}.csv` | triad 17,6 → 48,8 GB/s (nasycenie przy 6 wątkach); `fetch_add` w jednej linii ×4–14, listy 96 B ×1,01–1,09 | F |
| 7 Wykresy | zrobione | `bench/plot_etap12.py`, `docs/img/etap12_*.png` (11) | część 2: `etap12_{slabe,krzywa,przepustowosc,falszywe}` | krzywa — oś w komórkach (1 poprawka) |
| 8 Plan pomiaru, dokumentacja | zrobione | `PLAN_POMIARU.md` (pomiar ~18 min), `docs/etap-12-testy-wydajnosci.md` | podsumowanie wersji równoległych (punkt 5), klaster (punkt 6) | eksport: słownictwo 0 trafień |

## Dziennik

### Część 1 (21.10.2026, od 11:14)

- Stan repozytorium: ostatni commit „etap 11: typy MPI i MPI-IO”, `git status` czysty (tylko odczyt).
- Programy: `build/Release/engine.exe` = `bench/baseline/engine_e11_msvc.exe` (AD2F33AC…), `engine_mpi.exe` =
  `engine_mpi_e11_msvc.exe` (4667EECD…), `build-gcc-release/bin/engine` = `engine_e11_gcc` (40d8d186…), `engine_mpi` =
  `engine_mpi_e11_gcc` (301bd275…) — dane etapów 9–11 dotyczą tych samych programów co pomiary tego etapu.
- **Tryb oszczędny:** `powercfg /qh … PROCTHROTTLEMAX` i `PROCTHROTTLEMAX1` = 0x63 (99%) dla zasilania sieciowego
  i baterii, zasilanie sieciowe (bateria 100%). WSL: `nproc` = 8, 7 GB. (Licznik „% wydajności procesora” pod
  obciążeniem — w części 2, przed pomiarem czasu.)
- **Procesor i pamięć podręczna** — `bench/cache_info.py` (nowy: Windows `GetLogicalProcessorInformationEx`, Linux
  `/sys/devices/system/cpu/*/cache`) → [`procesor.md`](procesor.md): rdzeń P — L1d 48 KB (12-drożna), L1i 32 KB, L2
  2 MB (16-drożna) na rdzeń (wspólne dla 2 wątków SMT), rdzeń E — L1d 32 KB, L2 4 MB na grupę 4 rdzeni; L3 36 MB
  (12-drożna) wspólna dla wszystkich 32 procesorów logicznych; linia 64 B. WSL 2 widzi 4 rdzenie × 2 wątki z tymi
  samymi parametrami co rdzeń P (L2 2 MB, L3 36 MB).
- **Liczniki sprzętowe:** w WSL nie ma programu `perf` (brak `/usr/bin/perf*` i pakietu `linux-tools` dla jądra
  5.15.167.4-microsoft-standard-WSL2; zasada etapu — nic nie instalujemy), a maszyna wirtualna WSL 2 i tak zwykle nie
  udostępnia liczników PMU gościowi. Dalej: symulacja `valgrind --tool=cachegrind` (valgrind 3.18.1 jest w WSL).
  Windows: `xperf -on PROC_THREAD+LOADER+PMC_PROFILE -pmcprofile CacheMisses` bez uprawnień administratora kończy się
  „Failed to configure counters” (`wpr -pmcsources` widzi liczniki `CacheMisses`, `TotalCycles` itd., ale sesja jądra
  z licznikami wymaga administratora) — **liczników sprzętowych nie ma po żadnej stronie**.
- **1. Zestawienie S / E** — `bench/zestawienie_e12.py` (nowy, bez przebiegów: czyta `profile_2026-10-17_{przed2,po}.csv`,
  `omp/skalowanie_{msvc,gcc}.csv`, `mpi/skalowanie_mpi_{msvc,gcc}.csv`, `mpi_io/pomiar_*_raw.csv`) →
  [`zestawienie.md`](zestawienie.md), `zestawienie.csv` (233 wiersze: przypadek × kompilator × wariant, T / S / E / f,
  źródło, warunki), `zestawienie_lacznie.csv`. Zasady: S zawsze od T(1) z tej samej sesji; typy pochodne (etap 11)
  przez stosunek faz m / d z jednej sesji × S(m<p>) etapu 10, bo **ten sam wariant m8 w dwóch sesjach różni się
  o 13–29%** (lawa front 340 → 264 ms, lawa full 2 960 → 2 572 ms, classic 300³ — z grupy io — S(8) 3,32 → 3,84);
  profil przed / po etapie 8 był z zapisem txt + bin w classic i MC — tam tylko faza (total nieporównywalny).
  Najlepsze S fazy na ≤ 8 rdzeniach (MSVC): OpenMP 8 — lawa full 6,34, Etna 4,98, classic 300³ 4,82, lawa front 5,36;
  MPI 7 (bez procesora 0) — classic 2000² 6,68, MC 1000² 6,72; MC 100³ — MPI 7 z typami 6,07 ≈ OpenMP 8 6,06.
  **Łączne przyspieszenie fazy od programu sprzed etapu 8** (iloczyn ilorazów z sesji; wprost — kontrola): Etna
  ×375 (algorytm) × 4,98 (OpenMP 8) = **×1 871** (wprost ×1 878); classic 300³ ×10,4 × 4,82 = ×50; MC 1000²
  ×1,7 (etap 8) × 4,04 (szachownica przy 1 wątku) × 6,72 (MPI 7) = ×47; MC 100³ ×2,0 × 3,28 × 6,07 = ×39. GCC: Etna
  ×1 328, classic 300³ ×42, MC ×38 / ×29. E > 1 tylko w classic 2000² przy p = 2 (OpenMP 1,003, MPI 1,023)
  i o4 (1,005) — w granicy rozrzutu (punkt 3.6 w dokumentacji). Zapis z etapu 11: classic 300³ / 2000² `.txt`
  przy 8 procesach S(8) całości 1,93 / 2,11 (gather) → 3,43 / 4,34 (MPI-IO).
- **Mikrotest przepustowości** `bench/micro/bandwidth.cpp` (nowy, cel CMake `bandwidth` przy OpenMP; tryby `stream`,
  `sizes`, `false`): MSVC `--target bandwidth` (silnik nie przebudowany — SHA `engine.exe` / `engine_mpi.exe` bez zmian),
  GCC w `build-gcc-release` (ponowna konfiguracja, tylko cel `bandwidth`; SHA `engine` / `engine_mpi` bez zmian).
  Poprawki po próbie: suma w odczycie była łańcuchem zależnych dodawań (8 GB/s na 1 wątku, mniej niż copy) — teraz
  8 sum częściowych (13 GB/s); `fopen` → `std::ofstream` (C4996). Krótka obserwacja fałszywego współdzielenia (priorytet
  normalny, tło — tylko kierunek): licznik zapisywany do pamięci w każdej iteracji w sąsiednich 8 B vs co 64 B —
  0,58 / 0,54 ns (p = 2), 0,97 / 0,85 ns (p = 8), czyli ×1,1; licznik atomowy (`fetch_add`) 28 / 9,8 ns (p = 2),
  75 / 9,9 ns (p = 4), 117 / 16 ns (p = 8) — ×3–12; listy warstw jak `LavaCA::FrontLayer` (nagłówki 96 B w ciągłej
  tablicy, wątki co warstwę jak `static,1`) vs nagłówki co 128 B — 4,42 / 4,49 ns (p = 2), 4,60 / 4,66 ns (p = 4),
  bez stałej różnicy. Pomiar w ciszy — część 2.
- **Preset `gcc-release-g`** (nowy w `CMakePresets.json`, katalog `build-gcc-release-g/`): Release -O3 + `-g` dla
  cachegrind. **Sekcje `.text` programów `engine` i `engine_mpi` identyczne z `gcc-release`** (`objcopy
  --only-section=.text` + `cmp`), więc symulacja dotyczy tego samego kodu maszynowego co pomiary.
- **Cachegrind** — `bench/cachegrind.py` (nowy, uruchamiany w WSL): I1 32 KB 8-drożna, D1 48 KB 12-drożna, LL = L2
  (2 MB 16-drożna) i LL = L3 (36 MB, **18 dróg zamiast 12** — valgrind odrzuca `--LL=37748736,12,64`, bo 49 152
  zbiorów to nie potęga 2; 18 dróg daje 32 768 zbiorów przy tym samym rozmiarze). Valgrind 3.18 nie ma włączania
  zbierania w trakcie programu, a w małych przypadkach większość chybień L3 to pierwsze dotknięcie pamięci przy
  przygotowaniu (`std::vector::_M_fill_assign`, `memset`, `memcpy`, `PottsMC::initialize` — lawa `test_3d`: 73% chybień
  L3 w `_M_fill_assign`) — dlatego tabela główna liczy osobno **jądro** (funkcje kroku: `LavaCA::` poza
  przygotowaniem, `Boundary::`, `push_back` list frontu; MC — `sweepTrials` / `colorTrials` / `syncFrame`), a obok cały
  program. Pliki robocze w katalogu domowym WSL (`~/.cache/volcano_cg`), bo WSL wyłączył bezczynną maszynę i wyczyścił
  `/tmp` między poleceniami. Próba: lawa `test_3d` front 150 kroków — 3,1 s pod cachegrind; classic 1000² full 40 kroków
  (macierz) — 47 s.
- Pełny zestaw cachegrind (20 przypadków × LL = L2 / L3), 11:35–11:45, polecenie `wsl -e python3
  bench/cachegrind.py --ll L2,L3 --name cachegrind` → [`cachegrind.md`](cachegrind.md), `cachegrind.csv`,
  `bench/profiles/cachegrind/*.txt` (40 raportów `cg_annotate`). Sesję przerwał limit o 11:45 (zaraz po zakończeniu
  zestawu, przed wpisem wyników) — wyniki i wnioski w części „sesja 2” niżej.

### Część 1 — sesja 2 (21.10.2026, od 14:20)

- Stan zastany (sprawdzony, tylko odczyt git): ostatni commit „etap 11: typy MPI i MPI-IO”; zmienione
  `CMakePresets.json` (preset `gcc-release-g`), `engine/CMakeLists.txt` (cel `bandwidth`), `bench/scaling.py`,
  `bench/scaling_mpi.py` (tryb `--weak` — dopisany tuż przed przerwą, sprawdzone tylko `--list`), nowe
  `bench/{cache_info,cachegrind,memory,zestawienie_e12}.py`, `bench/micro/bandwidth.cpp`, `bench/profiles/cachegrind/`,
  `bench/results/testy/`. **Silnik nietknięty:** SHA-256 `engine.exe` / `engine_mpi.exe` / `engine` / `engine_mpi` =
  `*_e11_*` (AD2F33AC… / 4667EECD… / 40d8d186… / 301bd275…). `memory.py` nie był uruchomiony (brak wyników pamięci).
  Tryb oszczędny bez zmian (`PROCTHROTTLEMAX` / `PROCTHROTTLEMAX1` = 99%, WSL `nproc` = 8).
- **Cachegrind — wyniki i wnioski** ([`cachegrind.md`](cachegrind.md); „jądro” = funkcje kroku, „jedn.” = komórka ×
  krok albo próba MC; GCC -O3, 1 wątek):
  - **Lawa: front vs full** (`test_3d`, 150 kroków): front robi 4,7 odwołania do danych na komórkę × krok wobec 186,8
    (×40 mniej), chybień D1 0,034 wobec 0,639 (×19 mniej), chybień L2 prawie zero wobec 0,50. Miss rate frontu jest
    wyższy (0,73% vs 0,34% — rozproszony dostęp przez listę kandydatów), ale liczy się liczba chybień, nie ich udział:
    front dotyka tylko aktywnego brzegu potoku, który mieści się w L2, a pełny przebieg co krok przechodzi całą siatkę
    (~6 MB, poza L2, w L3). Gorące funkcje: front — `frontStepSequential` 37%, `frontRulesLayer` 17%,
    `gatherLavaCandidates` 11% chybień D1; full — `updateLava` 63%, `Boundary::applyWith` 16% (odświeżanie ramki),
    `gatherLavaCandidates` 15%.
  - **Classic: VN vs Moore** (front): Moore ma ×1,8 (2D) i ×4,9 (3D) więcej odwołań, a chybień D1 tyle samo (2D 0,044
    vs 0,048) albo ×1,24 (3D 0,248 vs 0,200) — chybienia zależą od liczby różnych wierszy / warstw dotykanych przez
    sąsiedztwo (y ± 1, z ± 1 — te same dla VN i Moore), nie od liczby sąsiadów. Dodatkowe odwołania Moore trafiają w D1.
  - **Układ danych: vector vs macierz** (classic 1000², full, 40 kroków): macierz `MatrixStorage` ma ×2,6 więcej
    odwołań do danych (92,4 vs 35,6 na komórkę × krok — pośrednie odwołania do wierszy), ale tyle samo chybień D1
    i L2 (0,414 / 0,413 vs 0,413 / 0,412). Wolniejsza macierz to koszt instrukcji i adresowania, nie pamięci podręcznej
    (wiersze są ciągłe, siatka jest przechodzona tą samą kolejnością).
  - **MC: random vs szachownica** — ta sama liczba odwołań na próbę (21,7 w 2D, 67 w 3D), ale **chybień D1 ×12 (2D)
    i ×11 (3D) mniej** w szachownicy (0,41 vs 4,86 i 1,08 vs 11,57 na próbę; miss rate 1,9% vs 22,4% i 1,6% vs 17,3%),
    chybień L2 ×9 mniej. Losowa próba trafia w losową komórkę, więc jej linie i linie wierszy / warstw sąsiadów nie są
    w D1 (~5 chybień na próbę w 2D VN); szachownica idzie po kolei i używa tych samych linii dla kolejnych komórek
    koloru. **To tłumaczy, czemu szachownica już przy 1 wątku jest 3–4× szybsza** (zestawienie: ×4,04 MC 1000², ×3,28
    MC 100³) — wcześniej (etap 9) było to tylko obserwacją czasu.
  - **Progi L2 / L3 / RAM** (jądro): classic `full` 256² (~1,7 MB) — 0 chybień L2; 1 024² (~27 MB) — 0,41 chybienia
    L2 na komórkę × krok, 0 L3; 2 896² (~218 MB) — 0,41 chybienia L3 (każda linia siatki z RAM co krok). MC random
    256² (~0,3 MB) — 4,1 chybienia D1 na próbę, 0 L2; 1 024² (~5 MB) — 3,7 L2, 0 L3; 4 096² (~84 MB) — 3,5 chybienia
    L3 na próbę (16% odwołań). Progi wypadają tam, gdzie przewiduje rozmiar siatki z modelu pamięci. Classic przechodzi
    siatkę po kolei (prefetcher sprzętowy ukrywa większość tych chybień — symulator go nie ma), MC random — losowo
    (każde chybienie L3 to pełne opóźnienie RAM), stąd MC najbardziej wrażliwe na rozmiar i na programy w tle (wspólna
    L3).
  - **Pas MPI przy 8 procesach** (MC szachownica 1000 × 125, 1,1 MB — mieści się w L2, wobec 1000², ~9 MB — L3; ta
    sama liczba prób): chybień L2 0,26 vs 0,41 na próbę (−37%), L3 zero w obu; D1 nieco więcej (0,54 vs 0,41 — większy
    udział ramki i `syncFrame` w małym pasie). Mniejszy pas = mniej odwołań do L3, ale szachownica i tak ma 98% trafień
    w D1, więc zysk czasu jest mały — przyczynek do E bliskiego 1 w MPI MC (m7 E = 0,96), nie do superliniowości.
  - **Cały program vs jądro:** w małych przypadkach większość chybień L3 to pierwsze dotknięcie pamięci przy alokacji
    i przygotowaniu (`_M_fill_assign` 60–87%, `memset`, `memcpy`, `PottsMC::initialize`), w MC szachownicy 16–22%
    chybień D1 to statystyki ziaren (`Grains::label`, union-find) — dlatego tabela główna liczy jądro osobno.
  - **Ograniczenia:** symulacja, nie liczniki sprzętowe (liczy zdarzenia, nie czas); L3 18-drożna zamiast 12 (wymóg
    potęgi 2 zbiorów; ten sam rozmiar); cachegrind modeluje dwa poziomy (D1 + LL), więc L2 i L3 to dwa osobne przebiegi;
    1 wątek (bez współdzielenia L3 z innymi rdzeniami, bez ruchu koherencji między rdzeniami); bez prefetchera
    sprzętowego (chybienia przy przechodzeniu po kolei są w procesorze w dużej części ukryte); kod GCC (MSVC może się
    różnić liczbą odwołań, nie układem danych).
- **2. Pamięć główna** — `bench/memory.py` (sprawdzenie: classic 1000² + narzut stały, 27 s; potem pełny zestaw):
  `python bench/memory.py --groups base,omp,mpi --name pamiec_msvc` (14:25–14:28, 3,2 min, 1 powtórzenie — szczyt
  pamięci jest powtarzalny, tło 43% / 39% — pamięć od niego nie zależy) → [`pamiec_msvc.md`](pamiec_msvc.md),
  `pamiec_msvc_raw.csv`; GCC krótko: `python bench/memory.py --wsl --cases classic2d_2000,lava3d_128,mc3d_100 --name
  pamiec_gcc` (0,7 min) → [`pamiec_gcc.md`](pamiec_gcc.md). Przypadki: classic 2D 1000² / 2000² / 4000², classic 3D
  100³ / 200³ / 300³, lawa 64² / 128² / 256² × 64 (front), MC 3D 50³ / 100³ / 200³ (szachownica), `etna_real`; warianty
  o1 / o2 / o4 / o8 (engine), m1 / m2 / m3 / m4 / m8 z typami pochodnymi, zapis gather i MPI-IO.
  - **Wątki prawie nie zwiększają pamięci:** szczyt przy 8 wątkach / przy 1 = 0,96–1,05 (MSVC), 0,99–1,10 (GCC);
    narzut stały procesu 6,3 MB (8 wątków: 6,7 MB — stosy wątków). OpenMP dzieli pracę, nie dane.
  - **Model pamięci zgadza się z pomiarem:** (szczyt − narzut stały) / model = 1,00–1,06 dla CA (classic, lawa,
    `etna_real`), B na komórkę: classic 2D 28,4–29,0, classic 3D 29,0–34,3 (mniejsze siatki — większy udział ramki),
    lawa 29–33, MC 3D 41–45. MC 200³: model zawyża o 16% (0,84), MC 50³ o 6% — część zarezerwowanej pamięci
    statystyk MC nie jest dotykana, więc nie wchodzi do zbioru roboczego. GCC: 1,01–1,08.
  - **MPI — suma po procesach:** dane (pomiar − p × narzut stały procesu MPI) przy 8 procesach / przy 1: classic 2D
    1,00–1,02, classic 3D 1,04–1,14, MC 3D 1,04–1,16, **lawa 1,71–1,84** — warstwy brzegowe lawy (17 pod pasem + 1
    nad) to przy 2 / 3 / 4 / 8 procesach 21 / 34 / 42 / 59% siatki wszystkich okien (64 warstwy z — przy 8 procesach
    8 warstw własnych i do 18 brzegowych); classic i MC (po 1 warstwie): 2D ≤ 1%, 3D 100³ / 200³ / 300³ — 12 / 7 / 5%.
    Model rozszerzony na procesy (okno = pas + warstwy brzegowe, B na komórkę z modelu procesu 0) zgadza się z sumą:
    gather 0,96–1,08 (MC do 1,20 — statystyki MC zbierają mapę kryształów, bufory zbierania nie są w modelu).
  - **Narzut stały procesu MPI:** MS-MPI 9,6–10,1 MB na proces (engine 6,3 MB), OpenMPI (WSL) ~21 MB — przy 8
    procesach 78 / 165 MB samego środowiska; w małych siatkach to większość pamięci (classic 1000² m8: 119 MB, dane 41).
  - **Proces 0: gather vs MPI-IO** (8 procesów): gather trzyma cały wynik (13 B na komórkę) — classic 300³ 445 MB wobec
    107 MB pozostałych, classic 4000² 263 vs 64 MB; MPI-IO wyrównuje procesy (300³: maks 110, min 107 MB; 4000²: 64,5
    / 63,9 MB) — **szczyt procesu 0 ×0,25**. Wyjątek: małe siatki — przy p > 1 zapis MPI-IO jest zbiorowy, a proces 0
    (jedyny agregator na jednym komputerze) zbiera dane innych w buforze ≤ 16 MB (ROMIO `cb_buffer_size`; MS-MPI ma
    MPI-IO z ROMIO): classic 1000² proces 0 26 MB przy MPI-IO wobec 13 MB pozostałych. Model procesu 0 przy MPI-IO =
    max(kroki, zapis: pas + min(16 MB, plik)) — po tej poprawce dane / model dla siatek ≤ 1,8 mln komórek 1,01–1,29
    zamiast 1,13–1,49 (reszta: wewnętrzne bufory zapisu biblioteki, najwięcej przy p = 2); większe 0,99–1,08. MC: MPI-IO nie zmniejsza pamięci
    procesu 0 (statystyki ziaren dalej zbierają mapę — etap 11, punkt 4.3).
  - **Przy 1 procesie** MPI-IO zużywa ×0,69–0,73 pamięci gather — nie składa osobnej kopii wyniku całej przestrzeni.
  - **Kiedy MPI pozwala policzyć większą siatkę:** na jednym komputerze nie — suma pamięci procesów jest ≥ pamięci
    jednego procesu (+ narzut stały, + warstwy brzegowe). Na klastrze każdy węzeł trzyma swój pas: przy MPI-IO szczyt
    procesu ≈ (B / komórkę × N / p) × (1 + udział warstw brzegowych) + narzut stały, przy zbieraniu proces 0 potrzebuje
    dodatkowo 13 B × N. Np. classic 3D, węzły po 8 GB, p = 8: gather — proces 0 ≤ 8 GB → N ≤ ~0,5 mld komórek (~800³),
    MPI-IO → N ≤ ~2,3 mld (~1 320³), ×4,5 więcej (29,6 B na komórkę pasa — classic 300³ przy MPI-IO). Lawa przy podziale w osi z potrzebuje warstw własnych ≫ 18 na
    proces, inaczej warstwy brzegowe zjadają pamięć (59% przy 8 procesach i 64 warstwach).
  - **Linux, `ru_maxrss`:** szczyt bardzo małego procesu pokazuje szczyt procesu rodzica (Python ~15–17 MB) —
    `ru_maxrss` przechodzi przez fork / exec; bezpośrednie uruchomienie classic 16³ z powłoki: 5,0 MB. Narzut stały
    w Linuksie liczony z RSS na końcu przebiegu (`endRssBytes`, `/proc/self/statm`); duże przypadki bez zmian.
  - Poprawki skryptu po sprawdzeniu: `resultBytes` (rozmiar pliku wyniku — bufor agregatora), `endRss`, model procesu 0
    przy MPI-IO, kolumna RSS na końcu; tabele przeliczone `--from-raw` (bez nowych przebiegów, poza powtórzonym
    krótkim zestawem GCC po dodaniu `endRss`).
- **3. Skalowanie słabe — `--weak`** w `bench/scaling.py` i `bench/scaling_mpi.py` (kod z sesji 1, przejrzany:
  `weak_cases()` — classic 2000 × 2000·p, MC szachownica 1000 × 1000·p, lawa `full` / `front` 128 × 128·p × 64 na
  terenie z p kafli 128 × 128 (`lava_tile_heightmap`: mapa CSV n × n·p, 24 kratery na kafel, `placement =
  positions`); configi osobno dla każdego p; `summarize_weak` — E_w fazy i całości, ns rdzenia na komórkę × krok,
  E_w znormalizowana; bez porównania bitowego i bez `--thread-stats`). Sprawdzenie (1 powtórzenie, wyniki do folderu
  tymczasowego, tło ~40% — tylko czy działa, nie pomiar):
  - MSVC OpenMP, p = 1 / 2: E_w fazy classic 0,90 (kroki 199 → 223, znormalizowana 1,01), MC 0,98, lawa full 0,95,
    front 0,96; MPI m1d / m2d: 0,83 (znorm. 0,93) / 0,88 / 0,84 / **0,47** (lawa front — dolny pas ma prawie całą
    lawę; OpenMP `static,1` przeplata warstwy i tego nie ma); 0,3 min na zestaw.
  - GCC (`--wsl`, OpenMP p = 1 / 2 i MPI m1d / m2d na 2 przypadkach): działa, E_w 0,86–0,95, lawa front MPI 0,55.
  - Przy p = 8 (1 przebieg, do szacunku czasu planu): OpenMP total 1,0–1,9 s, MPI m8d 1,7–2,5 s na przebieg.
- **4. Krzywa czasu na komórkę** — `bench/cell_time.py` (nowy): 1 wątek na rdzeniu P (`scaling.Runner`, `pcores`,
  priorytet wysoki; WSL — libgomp), siatki 2D 128 … 2896 co √2; krzywe `classic_full` (VN, `full`, 1 zarodek na
  10⁴ komórek, 40 kroków), `mc_random` / `mc_cb` (VN, 3 MCS); zbiór roboczy kroku z bajtów dotykanych na komórkę
  (classic 26 B — oba bufory, zgodnie z cachegrind; MC 12 B — `domainFrame` 8 B + `spin` 4 B, z kodu
  `PottsMC::sweepTrials`), obok siatka z modelu pamięci; tryb `--wsl`, `--from-raw`. Sprawdzenie: 3 rozmiary, potem
  jedno pełne powtórzenie MSVC i GCC (34 / 35 s; wyniki w folderze tymczasowym). Wstępnie (tło ~40%): MC random 38 ns
  na próbę (L2) → 54–140 ns (L3) → 164–186 ns (RAM, ×5); classic `full` 8–9 ns bez progu (dostęp po kolei —
  prefetcher), szachownica ~25 ns bez progu. Zmiany po próbie: domyślne rozmiary do 2896 (zamiast 4096 — 2896² jest
  już poza L3 we wszystkich krzywych, połowa czasu), MC 3 MCS zamiast 5.
- **Mikrotest `bandwidth`** — czas wszystkich trybów (do planu, wynik odrzucony): `stream` 5,3 s, `sizes` 6,4 s,
  `false` 14,7 s przy 10 powtórzeniach. SHA-256: `bandwidth.exe` 273211EB…, GCC `bandwidth` c3601427….
- **Licznik „% wydajności procesora”** (polecenie z planu: pętla Pythona przypięta do procesora 2 + `Get-Counter`):
  97,2 / 96,9 / 97,1 / 97,1 / 97,2% — bez turbo.
- **6. Plan pomiaru** → [`PLAN_POMIARU.md`](PLAN_POMIARU.md): A — skalowanie słabe OpenMP MSVC (~2,5 min), B — MPI
  MSVC (~4 min), C1 / C2 — GCC krótko (p = 1, 4, 8; 3 przypadki; ~3,3 min), D / E — krzywa MSVC / GCC (~3 + 3 min),
  F — przepustowość i fałszywe współdzielenie MSVC + GCC (~2 min); **razem ok. 23 min** z przygotowaniem i kontrolą.
- **5. Wykresy** — `bench/plot_etap12.py` (nowy; styl i paleta jak `etap9`–`etap11`, kolejność kolorów stała; paleta
  kategorii 4 kolorów i rampa D1 / L2 / L3 (#86b6ef / #2a78d6 / #104281) sprawdzone walidatorem palet: daltonizm
  ΔE ≥ 9,1, rampa monotoniczna; kontrast żółtego i zielonego < 3:1 — wartości podpisane na wykresach, liczby
  w tabelach). Z danych części 1 → `docs/img/`: `etap12_skalowanie_{lawa,classic,mc}.png` (S i E fazy: OpenMP etapu 9,
  MPI etapu 10, m7, hybrydy), `etap12_schodki.png` (łączne przyspieszenie: algorytm → szachownica → równoległość,
  MSVC, GCC w podpisie), `etap12_cachegrind.png` (chybienia D1 / L2 / L3 na jednostkę: pary, rozmiar, pas MPI),
  `etap12_pamiec_p.png` (suma danych MPI vs p, proces 0 gather / MPI-IO / najmniejszy przy 8), `etap12_pamiec_rozmiar.png`
  (szczyt vs komórki + model, model vs pomiar). Poprawki po obejrzeniu: legenda nad tytułem i etykiety przy 8
  (skalowanie), nakładające się etykiety końcowe i separator tysięcy psujący przecinki (schodki), kolejność słupków
  i „0” bez słupka (cachegrind), kolor = przypadek w obu panelach (pamięć). Wykresy części 2 (`etap12_slabe`,
  `etap12_krzywa`, `etap12_przepustowosc` — z zapotrzebowaniem CA / MC przy 8 wątkach: jednostki / s ze skalowania
  słabego przy p = 8 × chybienia L2 z cachegrind × 64 B — i `etap12_falszywe`) sprawdzone na danych przebiegów
  próbnych w folderze tymczasowym (nie w `docs/img`); bez plików części 2 skrypt je pomija.
- `tools/export_minimal.py`: komentarz listy `bench/micro` uzupełniony o `bandwidth.cpp` (skrypty `bench/*.py`
  kopiuje wzorzec — nowe pliki wchodzą same).
- **7. Dokumentacja (wstępna)** — [`docs/etap-12-testy-wydajnosci.md`](../../../docs/etap-12-testy-wydajnosci.md):
  metodyka (dane istniejące i nowe, warunki — wszystkie wiersze zestawienia bez turbo, procesor, brak liczników
  sprzętowych, ustawienia MPI), zestawienie S / E i łączne przyspieszenie, superliniowość, skalowanie słabe (przypadki;
  wyniki — część 2), pamięć główna (wątki, procesy i warstwy brzegowe, proces 0 gather vs MPI-IO, bufor agregatora,
  model vs pomiar, kiedy MPI mieści większą siatkę), pamięć podręczna (cachegrind, progi, pas MPI, fałszywe
  współdzielenie — przegląd kodu: liczniki lokalne / `reduction`, `ThreadStats` `alignas(64)`, jedyne możliwe miejsce —
  nagłówki `FrontLayer` co 96 B przy `static,1`; dlaczego nie ma przyspieszenia ponadliniowego — L3 wspólna, pasy nie
  mieszczą się w L2 albo zbiór roboczy mieści się już przy 1 wątku), ograniczenia, pliki. Miejsca na wyniki części 2
  oznaczone kursywą. Wpis w `docs/README.md` (tabela etapów + katalog danych `bench/results/testy/`). `CLAUDE.md`
  (lokalny): sekcja „Testy wydajności (etap 12)” z ustawieniami pomiarów MPI, numeracja etapów, lista skryptów.
- Kontrola słownictwa (wzorce `tools/export_minimal/slownictwo.txt`) na wszystkich zmienionych i nowych plikach
  repozytorium: 3 trafienia „p<liczba>” bez spacji (liczba wątków) — przepisane na „p = 1 / 2”; ścieżek prywatnych brak (raporty
  `cg_annotate` mają `<repo>`). Silnik bez zmian (SHA jak na początku sesji, żadnego buildu `engine` / `engine_mpi`).

### Stan na koniec części 1 — gotowe do cichego pomiaru (21.10.2026, 15:05)

- **Zrobione (część 1):** zestawienie S / E etapów 8–11 i łączne przyspieszenie; pamięć główna MSVC (13 przypadków)
  i GCC (3); cachegrind (20 przypadków × L2 / L3) z wnioskami; skrypty części 2 sprawdzone na małych przypadkach
  (`scaling.py --weak`, `scaling_mpi.py --weak` — MSVC i GCC; `cell_time.py` — MSVC i GCC; mikrotest `bandwidth`
  — wszystkie tryby); wykresy z danych części 1 (`docs/img/etap12_*.png`, 7 plików) i skrypt wykresów części 2;
  [`PLAN_POMIARU.md`](PLAN_POMIARU.md) — **ok. 23 min** (6 części ≤ 4 min + przygotowanie i kontrola); wstępna
  dokumentacja i wpis w `docs/README.md`.
- **Programy do pomiaru:** `build/Release/engine.exe` / `engine_mpi.exe` / `bandwidth.exe` (AD2F33AC… / 4667EECD… /
  273211EB…), GCC `build-gcc-release/bin/engine` / `engine_mpi` / `bandwidth` (40d8d186… / 301bd275… / c3601427…).
- **Część 2 zaczyna się od:** `PLAN_POMIARU.md`, punkt 0 (warunki, turbo licznikiem, SHA, próba ~40 s), potem części
  A → F; po pomiarze `python bench\plot_etap12.py` (wykresy części 2: `etap12_slabe`, `etap12_krzywa`,
  `etap12_przepustowosc`, `etap12_falszywe`) i uzupełnienie miejsc oznaczonych kursywą w
  `docs/etap-12-testy-wydajnosci.md` (punkty 2.4, 4.3, 4.4, 4.5) + podsumowanie wersji równoległych; aktualizacje
  `docs/uruchamianie.md` (nowe skrypty, `--weak`), `docs/architektura.md` (jeśli trzeba), `README.md`, `CLAUDE.md`.
- **Do decyzji / uwagi:** brak. Odstępstwa od planu etapu: liczników sprzętowych nie ma (symulacja zamiast nich);
  krzywa do boku 2896 zamiast 4096 i MC 3 MCS (czas planu); skalowanie słabe GCC skrócone do p = 1, 4, 8 i 3 przypadków
  („GCC krótko”).

### Część 2 — cichy pomiar (21.10.2026, od 18:32)

- **Weryfikacja:** `git status` zgodny ze stanem na koniec części 1 (ostatni commit „etap 11: typy MPI i MPI-IO”, te
  same zmienione / nowe pliki); SHA-256 programów jak w planie (`engine.exe` AD2F33AC…, `engine_mpi.exe` 4667EECD…,
  `bandwidth.exe` 273211EB…, GCC 40d8d186… / 301bd275… / c3601427…); `mpiexec` (MS-MPI) i `mpirun` (WSL) są.
  Tryb oszczędny: `PROCTHROTTLEMAX` / `PROCTHROTTLEMAX1` = 0x63 (99%), `.wslconfig` 8 procesorów / 8 GB, WSL `nproc`
  = 8, zasilanie sieciowe. Licznik „% wydajności procesora” pod obciążeniem: 97,2 / 96,1 / 96,9 / 96,1 / 96,7% — bez
  turbo. Tło 14,2% (5 s; z tego ~5% WmiPrvSE — inny program w tle, ~1% Menedżer zadań).
- **Próba** (folder tymczasowy, 36 s): `weak_lava_front` p = 1 / 2 — faza 526 / 642 ms, 260 kroków; `weak_classic_2d`
  m1d / m2d — 526 / 612 ms (199 / 223 kroki); MC random 256² / 1024² — 39,0 / 83,5 ns na próbę. Skrypty działają.
- W toku: A (18:34) — `python bench\scaling.py --weak --no-stats --name slabe_omp_msvc`
- **A** (18:34–18:36, 1,9 min; pliki przeniesione z `bench/results/omp/` — domyślny folder skryptu — do `testy/`): tło 15% → 9%, 5 powtórzeń, bez odstających. E_w fazy przy p = 8: classic 0,49 (znorm. 0,61), MC szachownica 0,87, lawa full 0,88, lawa front 1,00 (p = 4 / 6: 1,15 / 1,18).
- W toku: B (18:38) — `python bench\scaling_mpi.py --weak --name slabe_mpi_msvc --out bench\results\testy`
- **B** (18:39–18:42, 3,1 min): tło 12% → 15%, `cpus` m7d bez 0, m8d z 0, priorytet `high`; bez odstających. E_w fazy przy m8d: classic 0,49 (znorm. 0,61), MC 0,84 (m7d 0,97), lawa full 0,67 (m7d 0,78), lawa front 0,25 (podział w z, lawa w dolnym pasie — czas rośnie ∝ p).
- W toku: C1 (18:43) — `python bench\scaling.py --weak --wsl --threads 1,4,8 --cases weak_classic_2d,weak_mc_cb_2d,weak_lava_front --no-stats --name slabe_omp_gcc --out bench\results\testy`
- W toku: C2 (18:44) — `python bench\scaling_mpi.py --weak --wsl --variants m1d,m4d,m8d --cases weak_classic_2d,weak_mc_cb_2d,weak_lava_front --name slabe_mpi_gcc --out bench\results\testy`
- W toku: D (18:46) — `python bench\cell_time.py --name krzywa_msvc`
- W toku: E (18:48) — `python bench\cell_time.py --wsl --name krzywa_gcc`
- W toku: F (18:51) — `bandwidth --mode all --threads 1,2,4,6,8 --reps 20` (MSVC `--pin --high-priority`, GCC `OMP_PROC_BIND=close OMP_PLACES=cores`)
- **C1** (0,8 min): tło 16% → 16%. E_w fazy przy p = 4 / 8: classic 0,68 / 0,42 (znorm. 0,78 / 0,52), MC 0,94 / 0,79,
  lawa front 0,98 / 0,76.
- **C2** (1,4 min): tło 14% → 13%. E_w fazy przy m4d / m8d: classic 0,73 / 0,40 (znorm. 0,84 / 0,50), MC 0,93 / 0,65,
  lawa front 0,34 / 0,22.
- **D** (1,6 min): tło 22% → 14%. MSVC, 1 wątek: classic `full` 8,1–8,3 ns na komórkę × krok we wszystkich rozmiarach
  (bez progu); MC szachownica 24,6–25,3 ns na próbę (bez progu); **MC random 36,4 ns (n = 128) → 40,6 (362, zbiór
  roboczy 1,5 MB — L2) → 52,6 (512, 3 MB — po progu L2) → 94–120 (1 024–1 448, 12–24 MB — L3) → 146–169 ns (2 048–2 896,
  48–96 MB — RAM), ×4,6.**
- **E** (1,6 min): tło 12% → 17%. GCC: classic 6,7–7,0 ns, szachownica 24,7–25,2 ns (bez progu), MC random 36,6 → 42,2
  → 53,7 → 102–127 → 153–171 ns (×4,7) — te same progi.
- **F** (1,2 min): tło 17% → 17%. MSVC (`pcores`, priorytet wysoki): triad 17,6 / 30,9 / 43,2 / 48,8 / 48,1 GB/s, odczyt
  14,4 / 28,1 / 46,9 / 54,5 / 58,9 GB/s przy p = 1 / 2 / 4 / 6 / 8 (nasycenie od p = 6); GCC triad 19,3 / 31,8 / 46,8 /
  53,6 / 47,5, odczyt 15,4 … 58,7 GB/s. Rozmiary (p = 1): triad 54–66 GB/s do 2 MB, ~22 GB/s 4–32 MB, ~18 GB/s od
  128 MB. Fałszywe współdzielenie (MSVC): zapis co 8 B / co 64 B — 0,53 / 0,48 ns (p = 2), 0,76 / 0,65 ns (p = 8), ×1,1–1,2;
  `fetch_add` 35 / 8,7 ns (p = 2), 122 / 8,8 ns (p = 8), ×4–14; listy 96 / 128 B 4,12 / 3,88 (p = 2), 4,45 / 4,07 ns
  (p = 8), ×1,06–1,09. GCC: atomowy ×3–10, listy bez stałej różnicy.
- **Pomiar skończony, komputer wolny** (18:52). Razem ~18 min (cel ≤ 25). Tło 9–22% (< 30%), bez skoków, bez
  przebiegów ×2 względem reszty powtórzeń — żadnej części nie powtarzano. Odstępstwo: część A zapisana w domyślnym
  folderze `bench/results/omp/` (polecenie z planu bez `--out`) — pliki przeniesione do `testy/`; B–E z `--out
  bench\results\testy`.
- **Wykresy** (`python bench\plot_etap12.py --only slabe,krzywa,przepustowosc,falszywe`): `etap12_slabe.png` (E_w(p)
  OpenMP / MPI, MSVC / GCC, obok silne E(p) etapów 9–10), `etap12_krzywa.png`, `etap12_przepustowosc.png`
  (zapotrzebowanie przy 8 wątkach: classic 16,0, MC 7,2, lawa full 4,2, front 0,1 GB/s), `etap12_falszywe.png`.
  Jedna poprawka: krzywa — oś X w liczbie komórek, progi L2 / L3 dla 26 B (classic) i 12 B (MC), legenda nad
  wykresem (zasłaniała linię MC random). Wykresy części 1 bez zmian.
- **Dokumentacja:** `docs/etap-12-testy-wydajnosci.md` — metodyka (warunki części 2), 2.4 skalowanie słabe (tabela,
  Amdahl vs Gustafson), 4.3 krzywa, 4.4 przepustowość i zapotrzebowanie, 4.5 fałszywe współdzielenie w ciszy, 5 wersje
  równoległe — podsumowanie, 6 ograniczenia i klaster; `docs/README.md`, `docs/architektura.md` (drzewo `bench/`,
  ściąga), `docs/uruchamianie.md` (7.5 — nowe skrypty, `--weak`), `README.md` („Wybrane wyniki”, „Dalszy rozwój”,
  etapy 1–12), `bench/README.md` (skrypty etapu 12), `CLAUDE.md` (lokalny).
- `bench/cell_time.py`: nagłówek `.md` z programem względem katalogu projektu (był pełną ścieżką WSL — prywatna
  ścieżka w `krzywa_gcc.md`, poprawiona ręcznie w pliku wyników).
- **Kontrola słownictwa:** eksport wersji minimalnej do folderu tymczasowego — OK, 0 trafień; zmienione pliki pełnego
  repozytorium — 0 poza nazwą `CLAUDE.md` w dzienniku (jak w dziennikach etapów 10–11) i etykietami wariantów `p1`,
  `p2` … w `slabe_omp_*` (liczba wątków — ta sama konwencja co `omp/skalowanie_*` etapu 9). Do repo uczelnianego nie
  eksportowano.

### Stan na koniec części 2 — etap 12 zakończony (21.10.2026)

- Silnik bez zmian (SHA jak w części 1). Pomiar ~18 min, tło 9–22%, bez powtórzeń części.
- **Do decyzji:** commit etapu 12 (lista plików w podsumowaniu sesji); `PLAN_POMIARU.md` część A — polecenie bez
  `--out` (zapis do `results/omp/`, pliki przeniesione) — zostawione jako zapis tego, co uruchomiono.

