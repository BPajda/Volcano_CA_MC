# Etap 9 — dziennik pomiarów i postępu (OpenMP)

Plik prowadzony na bieżąco w trakcie etapu 9 (zrównoleglenie silnika w OpenMP): każdy krok, jego pliki wyników,
przyspieszenie, zgodność bitowa i obciążenie tła w czasie pomiaru. Opis metodyki i wnioski:
[`docs/etap-9-openmp.md`](../../../docs/etap-9-openmp.md).

Oznaczenia: `e8` = program po etapie 8 (`bench/baseline/engine_e8_msvc.exe`, `engine_e8_gcc`; binarki lokalne,
katalog `bench/baseline/` jest w `.gitignore`), `tN` = nowy program z `--threads N`. Przyspieszenie S(p) = T(1)/T(p),
efektywność E(p) = S(p)/p. Tło = obciążenie całego CPU przez inne programy (psutil, 2 s próbki) na początku i na końcu
pomiaru. Tryb oszczędny (od etapu 8, do końca projektu): procesor bez turbo, WSL 8 procesorów / 8 GB, buildy
`--parallel 4` / `-j 4`, jedna ciężka operacja naraz, próg tła 30% przy stabilnym tle, pomiary wielowątkowe tylko na
rdzeniach P (najwyżej 8 wątków, jeden na rdzeń fizyczny).

## Tabela kroków

| Krok | Stan | Pliki wyników | Wynik | Zgodność | Tło [% CPU] | Uwagi |
|---|---|---|---|---|---|---|
| 0.1 Tryb oszczędny | zrobione | — | rdzeń P pod obciążeniem: 96,6–97,0% taktowania bazowego (bez turbo); WSL `nproc` = 8, 7 GB | — | — | `PROCTHROTTLEMAX` i `PROCTHROTTLEMAX1` = 99% (zasilanie sieciowe i bateria) |
| 0.2 Binarki odniesienia | zrobione | `bench/baseline/engine_e8_msvc.exe`, `engine_e8_gcc` | = `engine_k7_msvc.exe` / `engine_k7a_gcc` (bajtowo) | — | — | kod silnika bez zmian od k7 (później tylko presety, testy, dokumentacja) |

## Dziennik

### Sesja 1 (18.10.2026, od ok. 03:00)

- Stan repozytorium: czysty (`git status` bez zmian), ostatni commit „etap 8: optymalizacja sekwencyjna”.
- Tryb oszczędny: `powercfg /qh … PROCTHROTTLEMAX` i `PROCTHROTTLEMAX1` — 0x63 (99%) dla zasilania sieciowego
  i baterii. Test: pętla w Pythonie przypięta do procesora logicznego 2, licznik „\Informacje o procesorze(0,2)\%
  wydajności procesora” co 1 s: 96,9 / 97,0 / 96,8 / 96,9 / 96,9 / 96,6% (z turbo ~197%) — **turbo wyłączone**.
  WSL: `nproc` = 8, `free -g` 7 GB + 2 GB wymiany.
- Topologia procesora (`GetLogicalProcessorInformationEx`, `RelationProcessorCore`): 24 rdzenie — **8 rdzeni P**
  (klasa wydajności 1, SMT, procesory logiczne {0,1}, {2,3}, …, {14,15}) i 16 rdzeni E (klasa 0, bez SMT, procesory
  logiczne 16–31). Jeden wątek na rdzeń fizyczny P = procesory logiczne 0, 2, 4, …, 14.
- Binarki odniesienia: `build/Release/engine.exe` = `engine_k7_msvc.exe`, `build-gcc-release/bin/engine` =
  `engine_k7a_gcc` (bajtowo; nowszy od nich jest tylko komentarz w `test_io.cpp`, presety k8 i flaga GCC już zawarta
  w k7a) → `bench/baseline/engine_e8_msvc.exe`, `engine_e8_gcc`.
- Mikrotest MSVC (scratchpad, ten sam wzorzec co później `bench/micro/omp_overhead.cpp`; 8 wątków): `/openmp` (vcomp,
  `_OPENMP` 200203) — region 3–4 µs, krok „4 fazy × omp for(64) + bariery” static 13–43 µs, dynamic 96–325 µs;
  `/openmp:llvm` (libomp140) — region 71 µs bez przypięcia, ~300 µs z przypięciem wątków, drugi przebieg zawiesił się
  (przerwany po 2 min). libomp140 w Visual Studio 17.8 leży w `debug_nonredist`. **Wybór: `/openmp` (OpenMP 2.0)**,
  kod zgodny z 2.0 (indeks pętli `std::ptrdiff_t`, harmonogram z configu przez `switch` po wariantach dyrektywy).
- Kod (03:05–03:25): `engine/src/parallel/Omp.hpp` (zastępcze `omp_*`, `ompFor`, `ompBarrier`, `ParallelSettings`),
  `ThreadStats.*` (`--thread-stats`), `Affinity.*` (rdzenie P, przypięcie), config `parallel.*` i `mc.update`, CLI
  `--threads`, `--thread-stats`; `LavaCA` — jeden region na krok (front: D(n) | kandydaci + reguły | zmiany; full:
  ramka | D(n) | reguły), warstwy z (2D x–y: y) dzielone między wątki, `initFront`, stan początkowy, teren i kopia
  wyniku równolegle; `Boundary::applyWith`; `PottsMC` — szachownica (`buildColors`, `sweepColors`), równoległa energia
  i mapa kryształów; `McStage`, `Simulation` (`times.json`: threads, schedule, chunk, affinity, cpus, openmp,
  threadStats; `stats.json`: `parallel`, `mc.update`); testy `engine/tests/test_parallel.cpp`; CMake `VOLCANO_OPENMP`,
  `VOLCANO_MSVC_OPENMP_LLVM`, cel `omp_overhead`.
- W toku: build MSVC Release + ctest, start 03:26, polecenie: `cmake --preset msvc-release` + `cmake --build --preset msvc-release --parallel 4`
  - 03:26–03:31 build MSVC Release (konfiguracja: `Found OpenMP_CXX: -openmp (found version "2.0")`) bez błędów
    i ostrzeżeń; ctest 12/12 (53 s); testy etapu 9 (`test_parallel.cpp`) zielone. Test lawy skrócony (pełny przebieg
    i warianty configów — po jednym harmonogramie na liczbę wątków, krótsze erupcje): 32 → 10,8 s w Release.
  - Rozpoznanie (pojedyncze przebiegi, nie pomiar): `test_3d` front 1 → 8 wątków (bez przypięcia) caSim 102 → 49 ms;
    full z `pcores` 3,0 s → 0,52–1,05 s (duży rozrzut przy 8 wątkach). `--thread-stats`: wątek na procesorze 0 jest
    stale najwolniejszy (reguły 360–530 ms wobec 330–350 ms pozostałych). Próba: 8. wątek na procesorze 1 (drugi wątek
    SMT rdzenia 0) zamiast 0 — bez wyraźnej różnicy przy dużym szumie (cofnięte). Ramka w pełnym przebiegu: 1/2/4/8
    wątków 58/39/25/67–115 ms — skaluje do 4 wątków.
  - `bench/micro/omp_overhead.cpp` (MSVC, 8 wątków, przypięte): region 6,5 µs, bariera 4,2 µs, krok „region + 3 fazy
    ompFor(64) + 2 bariery”: static 15,6 µs, dynamic 164 µs, guided 138 µs (bez przypięcia: 10 / 87 / 78 µs); wątki
    puli trwałe (0 zmian wątku systemu w 5000 regionów); region `num_threads(1)` 0,12 µs.
- `bench/ab.py`: `compare_dirs` pomija w `stats.json` klucze `parallel` i `update` (opis liczenia, nie wynik) — porównanie
  z `e8` i między liczbami wątków.
- W toku: build GCC Release + ctest, start 03:37, polecenie: `wsl -e bash -lc "cmake --preset gcc-release && cmake --build --preset gcc-release -j 4 && ctest --preset gcc-release"`
  - 03:37–03:39 build GCC Release (`Found OpenMP: TRUE (found version "4.5")`) bez błędów i ostrzeżeń; ctest 12/12 (23 s;
    pierwsze polecenie zawiesiło się na złym cudzysłowie w `wsl -e bash -lc`, ctest uruchomiony osobno); testy etapu 9
    zielone (lawa 9,7 s).
- W toku: zgodność bitowa (część 1: configi CA), start 03:49, polecenie: `python bench/compare_results.py --bin e8=bench/baseline/engine_e8_msvc.exe --bin t1=build/Release/engine.exe --bin t8=build/Release/engine.exe --bin e8_gcc=wsl:bench/baseline/engine_e8_gcc --bin t1_gcc=wsl:build-gcc-release/bin/engine --bin t8_gcc=wsl:build-gcc-release/bin/engine --args "t8=--threads 8" --args "t8_gcc=--threads 8" --configs classic_ref,etna_3d,etna_real,etna_real_boczna,heightmap_kanion,heightmap_podwojny,wezuwiusz_real --name zgodnosc_e9_cz1 --out bench/results/omp`
  - 03:49–03:50 część 1 (18 s): 7/7 configów zgodnych; 03:50–03:51 część 2 (`heightmap_kaldera, lava_mc_2d, lava_mc_3d,
    mc_full_2d, mc_full_3d, test_2d, test_3d` + `mc_basalt --mc-from`, 19 s): 8/8. **15/15 configów: `e8` = 1 wątek =
    8 wątków = `e8_gcc` = 1 wątek GCC = 8 wątków GCC** → `bench/results/omp/zgodnosc_e9_cz1.md`, `_cz2.md` (program
    wstępny, przed A/B).
- Binarki do A/B: `bench/baseline/engine_e9a_msvc.exe`, `engine_e9a_gcc` (= obecne buildy Release).
- W toku: A/B narzutu przy 1 wątku, MSVC, część ca_lava (e8, e9), start 03:50, polecenie: `python bench/ab.py --bin e8=bench/baseline/engine_e8_msvc.exe --bin e9=bench/baseline/engine_e9a_msvc.exe --groups ca_lava --name ab_e9_t1_msvc_ca_lava --out bench/results/omp`
  - A/B lawa MSVC (03:52, 0,2 min, tło 28%): e9a/e8 caSim `test_3d` ×1,037, `etna_real` ×1,051, `lava_mc_2d` ×1,055 —
    powyżej 3%. Poprawka e9b: liczniki reguł (`stay`, `changed`, `born`) i kontekst kroku jako zmienne lokalne
    (przez referencję do struktury kompilator zapisywał je do pamięci przy każdej zmianie — `push_back` mógłby je
    zmienić), `toMicrostructure` przy 1 wątku — pętla z etapu 8 bez regionu OpenMP.
  - A/B lawa MSVC e8 / e9b, 15 powtórzeń (`ab_e9b_t1_msvc_ca_lava_r15`): `test_3d` ×1,028, `etna_real` ×1,062
    (minimum 85,5 → 89,6 ms), `lava_mc_2d` ×0,983. Wariant e9c (kandydaci i reguły w dwóch osobnych pętlach po
    warstwach, jak w etapie 8): e9c/e9b ×1,00–1,01 — połączenie pętli nie jest przyczyną (cofnięte).
  - A/B lawa GCC e8 / e9b, 15 powtórzeń (`ab_e9b_t1_gcc_ca_lava`): `etna_real` ×1,009, `test_3d` ×1,021,
    `lava_mc_2d` ×1,043 (6,1 → 6,4 ms). GCC ma `-falign-functions=64` (położenie pętli niezależne od reszty kodu) —
    hipoteza: w MSVC to układ kodu (do sprawdzenia mapą linkera).
- W toku: A/B narzutu przy 1 wątku, MSVC, część ca_classic (e8, e9b), start 03:56
  - A/B classic MSVC e8 / e9b (`ab_e9b_t1_msvc_ca_classic`, 1,3 min): 1000² ×0,99–1,00; 100³ VN ×1,039, Moore
    ×1,082; 300³ caSim ×1,004, ale total ×1,032 — z sekcji: `vents` 29 → 87 ms (stan początkowy `countInitialState`).
    **Przyczyna:** `countLayers` / `scanLayer` (i `colorTrials` w szachownicy) dodawały do liczników przez referencję —
    MSVC (bez analizy aliasów wg typów) zapisywał je do pamięci i przeładowywał wskaźniki siatki w każdej iteracji (3×
    wolniej). Poprawka e9d: liczniki lokalne, dodawane na końcu.
  - A/B lawa MSVC e8 / e9d, 15 powtórzeń: `test_3d` ×1,008, `etna_real` ×0,997, `lava_mc_2d` ×1,048 (+0,3 ms na 6 ms —
    wywołania funkcji „na warstwę”: 80 warstw × 4 fazy × kilkaset kroków; w GCC też ×1,04). Poprawka e9e: funkcje
    frontu dostają zakres warstw (1 wątek — jedno wywołanie, pętla w środku jak w etapie 8; wiele wątków — warstwa).
  - A/B lawa e9e, 15 powtórzeń: MSVC `test_3d` ×1,040, `etna_real` ×1,037, `lava_mc_2d` ×1,013 (wąskie rozrzuty);
    GCC (`-falign-functions=64`) ×1,026 / ×1,027 / ×0,999. Mapa linkera MSVC (build e8 ze źródeł commitu etapu 8 przez
    `git archive` i build e9e, oba z `/MAP`, w folderze tymczasowym): `gatherLavaCandidates` mod 64 = 0 → 48,
    `hasSupport` 48 → 32, `dropDepth` 48 → 0, `CandidateVote::add` 48 → 0, `updateLava` 32 → 48 — gorące funkcje
    przesunięte względem linii 64 B (mechanizm z etapu 6, p. 7 i etapu 8, p. 3.6). W MSVC narzut 1 wątku waha się
    między wariantami kodu ±4% (e9d: −0,3…+1%, e9e: +3,7…4%) przy tej samej ścieżce wykonania; w GCC ≤ 2,7%.
    Oficjalny A/B narzutu (wszystkie grupy) — na końcowym programie, po zamrożeniu kodu.
- Dobór przypadków skalowania (pojedyncze przebiegi, ok. 04:00–04:15): `etna_real` front T(1) 0,15 s (zostaje — „front za
  mały”); duża lawa 3D (`test_3d` → 128 × 128 × 64, 24 kratery; `lava_duza_3d`): front T(1) 0,84 s, full 19,7 s;
  classic 1000² front tylko 0,12 s → 2000² (400 zarodków) 0,68 s; 300³ 3,6 s; MC szachownica 1000² mcSim 2,1 s
  (random 12–17 s); MC 100³ Moore.
- **Priorytet:** pełny przebieg dużej lawy przy 8 wątkach i priorytecie normalnym: 9,7 s (×2), `--thread-stats` —
  każdy wątek ~10 ms na krok w fazie ramki (czekanie na barierach). Ramka 1/2/4/8 wątków: 32/15/32/187 ms (40 kroków).
  Z `HIGH_PRIORITY_CLASS`: 8 wątków `dynamic` caSim 376 ms wobec 2788 ms przy 1 wątku (×7,4), ramka 13 ms. Przy 8
  zajętych rdzeniach P wątki o priorytecie normalnym są wywłaszczane przez programy w tle na cały kwant czasu, a reszta
  czeka na barierze — skrypt pomiarowy uruchamia silnik z wysokim priorytetem (jak `ab.py`).
- `bench/scaling.py` (nowy): przypadki, p ∈ {1, 2, 4, 6, 8}, naprzemiennie, `pcores`, HIGH, ≥ 5 powtórzeń, zgodność
  bitowa wyników wszystkich p z p = 1 w każdym powtórzeniu, S(p), E(p), Amdahl (najmniejsze kwadraty na 1/S),
  `--schedules`, `--thread-stats` (osobny przebieg na wariant), `--from-raw`, `--wsl`. Próba (`etna_real`, MC 2D,
  p = 1, 2, 8): zgodne, działa.
- Wstępne porównanie harmonogramów (8 wątków, 3 powtórzenia, tło 31% z innymi programami użytkownika, 3,4 min) →
  `bench/results/omp/wstepne/harmonogramy_wstepne_msvc.md`: lawa front najlepszy **static,1** (cyklicznie po warstwach;
  `etna_real` 33 ms wobec 60–75 ms innych), full — guided/dynamic (static ×1,6: dolne warstwy to tania skała, górne
  drogie powietrze), classic 2D — static (dynamic ×3,6 — koszt pobierania porcji w vcomp), classic 3D — dynamic,4,
  MC 2D — guided,4 (różnice ≤ 23%), MC 3D — dynamic (static,1 ×2,25). Te harmonogramy wpisane do przypadków
  `scaling.py`; końcowe porównanie harmonogramów — w cichym pomiarze.
- W toku: walidacja statystyczna szachownicy MC, start 04:20, polecenie: `python bench/mc_validation.py` (12 ziaren generatora, 3 przypadki)
  - 04:20–04:21 pierwszy przebieg (kT = 0,5 w trzecim przypadku — okazało się powyżej temperatury przejścia modelu
    Pottsa 2D dla Q = 50, kT_c = 1/ln(1 + √50) ≈ 0,48: ziarna nie rosną, wykładnik 0,02; zmienione na kT = 0,3)
    i 04:22–04:23 przebieg końcowy (40 s) → `bench/results/omp/mc_walidacja.csv`, `mc_walidacja.md`,
    `docs/img/etap9_mc_walidacja.png`. 12 ziaren generatora; po 100 MCS (szachownica / random − 1, t Welcha):
    2D VN kT = 0: liczba ziaren −1,7% (t = −9,3), średnia wielkość +1,7%, energia −0,7%, **wykładnik wzrostu
    0,660 / 0,660**; 3D Moore kT = 0: ziarna −2,3% (t = −5,1), wielkość +2,4%, wykładnik 0,806 / 0,777 (−3,6%);
    2D VN kT = 0,3: ziarna −1,1% (t = −3,0), wykładnik 0,405 / 0,406. Współczynnik akceptacji równy (±0,7%).
    Wniosek: ta sama kinetyka (w 2D ten sam wykładnik), szachownica nieco „wyprzedza” wariant naiwny o kilka MCS —
    każda komórka jest próbowana dokładnie raz na MCS, a w wariancie naiwnym (losowanie ze zwracaniem) ~37% komórek
    w danym MCS nie dostaje próby, a inne dostają kilka.
- GUI (04:35–04:45): formularz — `mc.update` (grupa MC) i nowa grupa „Równoległość (OpenMP)” (`parallel.threads`,
  `schedule`, `chunk`, `affinity`) z opisami w `SCHEMA`/`ENUMS`; tabela porównania — kolumny „wątki OpenMP”
  i „harmonogram OpenMP” (`gui/compare.py`); karta „Przebieg” — wątki, harmonogram, porcja, przypinanie, procesory
  (`stats.js`); szablon serii `openmp_threads` „OpenMP: liczba wątków” (lawa `test_3d` full + MC szachownica 500² ×
  1, 2, 4, 6, 8 wątków; wykres czas vs wątki). Próba: `tools/make_series.py --template openmp_threads --run`
  (folder tymczasowy) — 10/10 ok, lawa full 3528 → 549 ms, MC 537 → 96–122 ms.
- **Błąd przypinania pod Linuksem** (próba GCC w WSL): z `OMP_PROC_BIND=close` libgomp przypina wątek główny do
  jednego procesora przed `main()`, a `performanceCores()` brało listę z `sched_getaffinity` → 1 procesor, wszystkie
  wątki na nim (`test_3d` full 4 wątki: 51 s). Poprawka: lista z `/sys/devices/system/cpu/online`; kolejność — najpierw
  pierwszy procesor każdego rdzenia, potem drugie wątki SMT (WSL zgłasza wirtualnie 4 rdzenie × 2 wątki SMT).
  Po poprawce GCC `test_3d` full (guided, pcores): 1/2/4/6/8 wątków 2738 / 1393 / 779 / 520 / 468 ms.
- `omp_overhead` GCC (WSL): bez wiązania p = 8 region 165 µs, krok static 85 µs (procesory wirtualne bez wiązania);
  z `OMP_PROC_BIND=close OMP_PLACES=cores` bez `--pin`: region 0,9 / 2,0 / 4,9 µs (p = 2/4/8), bariera 0,3 / 0,6 /
  1,1 µs, krok static 1,6 / 3,5 / 27 µs, **dynamic 19 / 22 / 26 µs** (vcomp: 52–164 µs), guided 6 / 10 / 16 µs;
  z `--pin` i zmiennymi naraz przy zmianie zespołu 4 → 8 wątków region 39 ms (libgomp przepina wątki do miejsc
  `OMP_PLACES`, program — na swoje procesory). **Pomiar GCC w WSL:** wiązanie przez libgomp (`OMP_PROC_BIND=close`,
  `OMP_PLACES=cores`), program z `parallel.affinity = none` (`scaling.py --wsl`). Próba `--wsl`: `etna_real` 8 wątków
  faza ×3,6, MC 2D ×5,6 — działa.
- `bench/mc_validation.py` i `bench/plot_etap9.py` (nowe; wykresy przetestowane na próbnych danych z folderu
  tymczasowego). Wykres części szeregowych pokazał „resztę poza sekcjami” (classic 2000² przy 8 wątkach ~30%):
  `Simulation::buildStats` (stats.json — przegląd całej siatki z `hypot` dla komórek ziaren) nie był w żadnej sekcji.
  Teraz sekcja `caStats` i wiersze dzielone między wątki (sumy na wątek, łączenie: suma liczników, maksimum zasięgu —
  wynik ten sam); classic 2000²: caStats 40 → 12 ms (1 → 8 wątków). `caStats` dopisane do `SECTIONS` w `ab.py`
  i `scaling.py` oraz do nazw sekcji GUI.
- **Kod silnika zamknięty** (04:55). W toku: build GCC Release + ctest, ctest MSVC, start 04:56
  - 04:56–05:04 GCC Release (34 s) bez błędów i ostrzeżeń, ctest 12/12; MSVC ctest 12/12, doctest 119/119
    (314 574 asercji). Binarki końcowe: `bench/baseline/engine_e9_msvc.exe`, `engine_e9_gcc`.
- W toku: A/B narzutu przy 1 wątku (e8 / e9), MSVC, część ca_lava (15 powtórzeń), start 05:04, polecenie: `python bench/ab.py --bin e8=bench/baseline/engine_e8_msvc.exe --bin e9=bench/baseline/engine_e9_msvc.exe --groups ca_lava --reps 15 --name ab_e9_msvc_ca_lava --out bench/results/omp`
  - 05:05 A/B lawa MSVC e8 / e9 (pierwsza wersja końcowa, 15 powtórzeń; plik przemianowany na `ab_e9e2_msvc_ca_lava`):
    ×1,039 / ×1,037 / ×1,002 — jak e9e. Próby układu: e9f (reguły warstwy w osobnej funkcji zwracającej sumy przez
    wartość): e9f/e8 `test_3d` ×1,001, `etna_real` ×1,006, `lava_mc_2d` ×1,037 (6,04 → 6,26 ms); e9g (e9f + pomijanie
    pustych warstw bez wywołań funkcji): ×1,035 / ×1,023 / ×1,018 (e9f w tym samym pomiarze ×1,009 / ×1,004 / ×1,036).
    Każda zmiana przestawia układ funkcji w MSVC („huśtawka” ±4% przy tej samej ścieżce wykonania) — **wybrany e9f**
    (najmniejszy narzut w dużych przypadkach), pomijanie pustych warstw cofnięte. Linie > 120 znaków przeniesione
    (sekcja `.text` programu MSVC bajtowo równa e9f).
  - 05:11–05:13 GCC Release końcowy (61 s) bez ostrzeżeń, ctest 12/12; MSVC doctest 119/119. **Binarki końcowe:**
    `engine_e9_msvc.exe` (= e9f), `engine_e9_gcc`.
- W toku: oficjalny A/B narzutu przy 1 wątku (e8 / e9), MSVC, część ca_lava (15 powtórzeń), start 05:13, polecenie: `python bench/ab.py --bin e8=bench/baseline/engine_e8_msvc.exe --bin e9=bench/baseline/engine_e9_msvc.exe --groups ca_lava --reps 15 --name ab_e9_msvc_ca_lava --out bench/results/omp` (następne części: ca_classic, mc bez 100³, mc_full_3d_100)
- W toku: A/B GCC (4 części jak MSVC), start 05:22
  - 05:14–05:23 MSVC (tło 19–24%): `ab_e9_msvc` (scalone 4 części). caSim / mcSim e9/e8: lawa `test_3d` ×0,997,
    `etna_real` ×1,002, `lava_mc_2d` ×1,055 (6,10 → 6,44 ms), `lava_mc_3d` (CA) ×1,034; classic ×0,998–1,020;
    MC ×0,995–1,009 (100³ ×1,000); mcStats ×1,00–1,01; total ×0,989–1,014 we wszystkich przypadkach.
  - 05:23–05:31 GCC (tło 18–33%): `ab_e9_gcc`. Lawa caSim ×1,023 / ×1,035 / ×1,023, `lava_mc_3d` ×1,033; classic
    ×0,961–1,001; MC ×0,996–1,012; total ×0,968–1,022.
  - **Wniosek:** narzut OpenMP przy 1 wątku ≤ 3% w całym przebiegu (total) wszystkich 13 przypadków i w fazie obliczeń
    przypadków dłuższych niż ~0,1 s; w krótkich przypadkach lawy faza CA +2…5,5% (0,1–3 ms) — granica szumu układu
    kodu (MSVC: ±4% między wariantami e9d–e9g przy tej samej ścieżce wykonania), w GCC z wyrównaniem funkcji +2…3,5%.
    Przyczyny rzeczywiste (liczniki przez referencję, wywołania na warstwę) usunięte; regionów OpenMP przy 1 wątku
    nie ma (ścieżka sekwencyjna).
- W toku: końcowa zgodność bitowa, start 05:32 — (A) wszystkie configi domyślnie: e8, t1, t8 MSVC i GCC; (B) `ca.sweep
  = full`: e8 vs t8 MSVC i GCC; (C) `mc.update = checkerboard`: t1 vs t8 MSVC i GCC (configi z MC)
  - 05:32–05:43 zgodność końcowa: (A) `zgodnosc_e9.md` — **15/15 configów: e8 = 1 wątek = 8 wątków = e8_gcc = 1 wątek
    GCC = 8 wątków GCC**; (B) `zgodnosc_e9_full.md` (`ca.sweep = full`, 8 wątków: MSVC guided, GCC dynamic; 4,4 min) —
    13/13: e8 = t8 = e8_gcc = t8_gcc; (C) `zgodnosc_e9_szachownica.md` (`mc.update = checkerboard`, configi z MC) — 6/6:
    1 wątek = 8 wątków (dynamic) = 3 wątki (guided, porcja 2) = GCC 1 = GCC 8. (Wcześniejsze `zgodnosc_e9_cz1/_cz2` —
    program wstępny sprzed poprawek A/B.)
- W toku: build MSVC Debug + ctest, start 05:37
  - 05:37–05:42 MSVC Debug: build bez błędów i ostrzeżeń, ctest 12/12 (199 s).
  - 05:43–05:46 GCC z `VOLCANO_OPENMP=OFF` (`build-gcc-noomp/`): build bez ostrzeżeń (także bez -Wunknown-pragmas — dyrektywy w `#ifdef _OPENMP`), ctest 12/12; `--threads 8` — ostrzeżenie „program zbudowano bez OpenMP”, przebieg jednowątkowy.
- 05:47–05:58 ThreadSanitizer (GCC 11, `build-gcc-tsan/`: `-fsanitize=thread -g`, -O3; Clanga z libomp/Archer w WSL nie
  ma): build bez ostrzeżeń; 4 wątki, małe przypadki: lawa front (`dynamic`) 390–403 raporty, lawa full 24² × 20
  (30 kroków) 303, classic periodyczny 244, MC szachownica 24³ 66–67, lawa 2D + MC szachownica 258. Pary miejsc
  (skrypt w folderze tymczasowym): zawsze dostępy rozdzielone barierą albo końcem regionu — np. odczyt `type` w regułach
  ↔ zapis `setCell` w fazie zmian / przy zamianie buforów, `crystals` w regionie ↔ `Grains::label` po regionie, nowe
  obiekty na stosie wątku głównego po regionie ↔ odczyty wątków w regionie (`applyTerrain`, `buildStats`). libgomp nie
  jest instrumentowana, więc TSan nie widzi synchronizacji barier i końca regionu — **wynik nierozstrzygający
  (fałszywe alarmy na granicach faz)**; brak wyścigów potwierdzają testy bitowe (1/2/3/4/8 wątków × harmonogramy,
  `test_parallel.cpp`) i porównania wszystkich configów (A, B, C wyżej).
- 05:58–06:05 GUI: `python -m pytest gui\tests` — 100/100. Sprawdzenie w przeglądarce (Playwright, skrypt w folderze
  tymczasowym, zrzuty poza repozytorium): formularz — grupa „Równoległość (OpenMP)” z czterema polami i `mc.update`
  w grupie MC; seria z szablonu `openmp_threads` uruchomiona przez GUI (10/10 gotowe; lawa full 2609 / 1477 / 784 /
  541 / 579 ms, MC 522 / 391 / 138 / 95 / 109 ms dla 1 / 2 / 4 / 6 / 8 wątków — GUI uruchamia silnik z priorytetem
  normalnym, stąd 8 wątków nie szybciej niż 6); wykres porównania: pierwsza próba — oś X „liczba komórek”, bo
  `compare.js` ma listę dozwolonych osi X (`X_KEYS`) — dopisane `threads` i `schedule` (+ kolumna „wątki” w widoku
  „czasy i kroki”); po poprawce oś X = wątki OpenMP, log Y, serie wg algorytmu, bez błędów konsoli JS.
- **Gotowe do końcowego pomiaru** (06:05): plan — MSVC skalowanie w 3 częściach (~13 min), MSVC harmonogramy (~5 min),
  GCC skalowanie (krótszy zestaw, 2 części, ~9 min) i harmonogramy lawy (~2 min); razem ~30–35 min. Czekam na zgodę
  na ciszę (zatrzymane wideo / komputer bez użytkownika).

### Sesja 3 (20.10.2026)

- Stan: `git status` — zmiany etapu 9 zgodne z dziennikiem (22 pliki zmienione: silnik, `bench/ab.py`, GUI; nowe:
  `engine/src/parallel/*`, `engine/tests/test_parallel.cpp`, `bench/scaling.py`, `mc_validation.py`, `plot_etap9.py`,
  `micro/omp_overhead.cpp`, `bench/results/omp/`, `docs/img/etap9_mc_walidacja.png`); źródła silnika bez zmian od
  18.10 05:10. `build/Release/engine.exe` = `engine_e9_msvc.exe`, `build-gcc-release/bin/engine` = `engine_e9_gcc`
  (bajtowo).
- Tryb oszczędny: `PROCTHROTTLEMAX` i `PROCTHROTTLEMAX1` = 0x63 (sieć i bateria); pętla w Pythonie przypięta do
  procesora logicznego 2: 96,5 / 97,0 / 95,7 / 96,6 / 96,8 / 95,9% taktowania bazowego — **bez turbo**. WSL `nproc` = 8,
  7 GB.
- Próba `scaling.py` (`lava_etna_real`, p = 1, 2, jedno powtórzenie, folder tymczasowy): caSim 85,5 / 48,9 ms,
  wyniki zgodne. Tło 15–16% (`WmiPrvSE` ~1,8 procesora — narzędzia producenta laptopa w tle).
- Plan cichego pomiaru (części ≤ 10 min, tło na początku i końcu każdej, scalanie `--from-raw`):
  1. MSVC skalowanie cz. 1 — lawa: `lava_etna_real`, `lava_duza_3d_front`, `lava_duza_3d_full` (~4,5 min),
  2. MSVC skalowanie cz. 2 — classic i MC 2D: `classic_2000x2000_s400_vn`, `classic_300x300x300_s100_vn`,
     `mc_cb_2d_1000`, `mc_random_2d_1000` (~3 min),
  3. MSVC skalowanie cz. 3 — MC 3D: `mc_cb_3d_100`, `mc_random_3d_100` (~3,5 min),
  4. MSVC harmonogramy (8 wątków, 6 harmonogramów, przypadki bez `mc_random_*`, ~5 min),
  5. GCC skalowanie cz. 1 — lawa (3 przypadki, ~4,5 min), cz. 2 — classic 2D/3D, MC szachownica 2D/3D (~4,5 min),
  6. GCC harmonogramy lawy (3 przypadki, ~2 min).
- Zgoda na ciszę. W toku: MSVC skalowanie cz. 1 (lawa), polecenie: `python bench/scaling.py --cases lava_etna_real,lava_duza_3d_front,lava_duza_3d_full --name skalowanie_msvc_cz1`
  - 04:59–05:02 (3,0 min, tło 14 → 15%), wszystkie przebiegi zgodne z p = 1. S(8) total / faza: `etna_real`
    2,12 / 4,98 (f total 0,37 — przygotowanie terenu i zapis), duża lawa front 4,59 / 5,36, full 6,22 / 6,34
    (T(1) 12,6 s → 2,0 s; E(6) 0,93, E(8) 0,78).
- W toku: MSVC skalowanie cz. 2 (classic, MC 2D), polecenie: `python bench/scaling.py --cases classic_2000x2000_s400_vn,classic_300x300x300_s100_vn,mc_cb_2d_1000,mc_random_2d_1000 --name skalowanie_msvc_cz2`
  - 05:02–05:06 (3,1 min, tło 14 → 12%), zgodne. S(8) total / faza: classic 2000² 3,66 / 6,67, 300³ 3,22 / 4,82,
    MC szachownica 2D 3,30 / 6,18 (mcSim 2059 → 333 ms; `random` przy 1 wątku 8324 ms — szachownica przy 1 wątku
    ×4,0 szybsza: przegląd po kolei zamiast losowych adresów).
- W toku: MSVC skalowanie cz. 3 (MC 3D), polecenie: `python bench/scaling.py --cases mc_cb_3d_100,mc_random_3d_100 --name skalowanie_msvc_cz3`
  - 05:06–05:10 (3,4 min, tło 15 → 10%), zgodne. MC szachownica 3D S(8) total / faza 3,55 / 6,06 (mcSim 5743 →
    948 ms; mcStats ~1,1 s sekwencyjnie); `random` przy 1 wątku 18 860 ms (szachownica ×3,3 szybsza przy 1 wątku).
- W toku: MSVC harmonogramy (8 wątków), polecenie: `python bench/scaling.py --schedules --cases lava_etna_real,lava_duza_3d_front,lava_duza_3d_full,classic_2000x2000_s400_vn,classic_300x300x300_s100_vn,mc_cb_2d_1000,mc_cb_3d_100 --name harmonogramy_msvc`
  - 05:10–05:15 (5,1 min, tło 14 → 15%), zgodne. Najlepsze: lawa front `static,1` (`etna_real` 23 ms, inne
    ×1,55–2,25; duża lawa 135 ms, `dynamic` ×1,09, `static` ×1,60), lawa full `dynamic` / `guided` (1874 / 1879 ms,
    `static` ×1,33), classic 2D `static` (guided ×1,05, `dynamic` ×3,74), classic 3D `dynamic,4` (guided ×1,04–1,05),
    MC 2D `guided,4` (wszystkie ≤ ×1,31), MC 3D `guided` (`static`, `dynamic` ×1,02–1,03, `static,1` ×1,93).
    Wybór harmonogramów pomiaru skalowania (z porównania wstępnego) potwierdzony albo w granicy 5% od najlepszego.
- W toku: GCC skalowanie cz. 1 (lawa, WSL), polecenie: `python bench/scaling.py --wsl --cases lava_etna_real,lava_duza_3d_front,lava_duza_3d_full --name skalowanie_gcc_cz1`
  - 05:15–05:17 dwa nieudane starty (bez pomiaru): „nie można otworzyć pliku konfiguracyjnego /tmp/…”. Przyczyna —
    polecenie bez `--bin`: domyślny `build/Release/engine.exe` (program Windows) skopiowany do WSL i uruchomiony
    przez interop jako proces Windows, który nie widzi `/tmp` maszyny WSL. Ponowione z
    `--bin build-gcc-release/bin/engine` (jak w opisie skryptu); domyślny program dla `--wsl` — do poprawy po pomiarze.
  - 05:17–05:21 (3,0 min, tło Windows 13 → 12%), zgodne. S(8) total / faza: `etna_real` 1,89 / 3,44 (faza przy
    8 wątkach 23,0 [15,9–57,8] ms — szum procesorów wirtualnych; p = 6: 4,17), duża lawa front 4,49 / 5,11, full
    6,16 / 6,26 (T(1) 12,3 s → 2,0 s).
- W toku: GCC skalowanie cz. 2 (classic, MC szachownica), polecenie: `python bench/scaling.py --wsl --bin build-gcc-release/bin/engine --cases classic_2000x2000_s400_vn,classic_300x300x300_s100_vn,mc_cb_2d_1000,mc_cb_3d_100 --name skalowanie_gcc_cz2`
  - 05:21–05:25 (3,9 min, tło Windows 14 → 13%), zgodne. S(6) / S(8) fazy: classic 2000² 4,31 / 4,33, 300³ 4,08 /
    2,86, MC 2D 5,14 / 4,70, MC 3D 5,06 / 5,13. **p = 8 w WSL nie skaluje się dalej i ma duże skoki.** Classic 300³
    przy p = 8: 1103 / 630 / 1185 / 703 / 1236 ms — wolne w powtórzeniach parzystych (p rosnąco: p = 8 zaraz po p = 6,
    który zapisał 351 MB `ca_result.bin`), szybkie w nieparzystych (p = 8 pierwszy po małym przypadku). Przy 8 wątkach
    na 8 procesorach wirtualnych wątki jądra (zapis brudnych stron na dysk wirtualny) zabierają procesor jednemu
    wątkowi, a reszta czeka na barierze; przy p ≤ 6 są wolne procesory. Pozostałe skoki p = 8 (MC 2D 1762 ms, MC 3D
    2177 ms, classic 2000² 645 ms) skupione ok. 05:24 — chwilowa aktywność gospodarza albo maszyny wirtualnej. Tło
    stabilne, część niepowtarzana (efekt systematyczny dla p = 8 w WSL, opisany jako ograniczenie; mediany odporne).
- W toku: GCC harmonogramy lawy (8 wątków), polecenie: `python bench/scaling.py --wsl --bin build-gcc-release/bin/engine --schedules --cases lava_etna_real,lava_duza_3d_front,lava_duza_3d_full --name harmonogramy_gcc`
  - 05:26–05:28 (1,8 min, tło Windows 14 → 11%), zgodne. Najlepsze: `etna_real` `static,1` 21,0 ms (`dynamic` ×1,12 —
    w libgomp pobieranie porcji tanie, w vcomp ×2,25), duża lawa front `dynamic` 132 ms (`static,1` ×1,03), full
    `dynamic` 1857 ms (guided ×1,06, `static` ×1,35).
- **Cichy pomiar zakończony** (04:59–05:28, 29 min; komputer zwolniony do normalnej pracy). Scalone tabele:
  `skalowanie_msvc.md/.csv/_threads.json` (cz. 1–3), `skalowanie_gcc.*` (cz. 1–2), `harmonogramy_msvc.*`,
  `harmonogramy_gcc.*`. Tło we wszystkich częściach 10–15% (stałe `WmiPrvSE` narzędzi producenta laptopa ~1,3–2,1
  procesora), bez skoków; 0 różnic wyników we wszystkich przebiegach.
- `bench/scaling.py` (po pomiarze, bez wpływu na wyniki): domyślny `--bin` z `--wsl` = `build-gcc-release/bin/engine`;
  wyjście zawsze w UTF-8 (scalanie z wyjściem do `/dev/null` przerwało się na znaku „−” — w Windows NUL udaje terminal
  i ma kodowanie cp1250; `.md` zapisany, `_threads.json` nie — scalenie powtórzone).
- Wykresy (05:29–05:34): `python bench/plot_etap9.py` → `docs/img/etap9_skalowanie.png`, `_amdahl`, `_harmonogramy`,
  `_watki`, `_szeregowe`, `_msvc_gcc`, `_mc_walidacja` (ten ostatni z `mc_walidacja.csv` przez
  `mc_validation.py --from-csv`; `mc_walidacja.md` bez zmian). Poprawki po obejrzeniu: 7 przypadków na jednym wykresie
  linii nie przechodzi walidatora palety dla wszystkich par (zielony ↔ pomarańczowy dla protanopii, różowy ↔
  pomarańczowy) → S/E i Amdahl w panelach wg grup (lawa / classic / MC, ≤ 3 serie) + znaczniki; MSVC vs GCC — krótkie
  podpisy osi (nachodziły na siebie); praca wątków — miejsce na legendę; części szeregowe — mediany części z
  surowych przebiegów (mediany sekcji z tabeli nie sumują się do mediany total: „reszta” classic 2000², p = 8 wychodziła
  30 ms zamiast 11–15 ms; reszta = głównie zwolnienie pamięci automatu po sekcji `save`: 4 / 7 / 45 ms dla etna /
  2000² / 300³ przy p = 1). `plot_etap9.py` i `mc_validation.py` — wyjście zawsze w UTF-8 (jak `scaling.py`).
  Nowy schemat `etap9_podzial.png` (warstwy z → wątki przy `static` i `static,1` z frontem lawy; kolory szachownicy).
- Dokumentacja (05:35–06:30): `docs/etap-9-openmp.md` (nowy); aktualizacje `docs/README.md`, `docs/architektura.md`
  (numery linii po etapie 9 — skrypt w folderze tymczasowym liczy zakresy funkcji po klamrach; krok 6a „Wątki OpenMP”,
  szachownica w kroku 8, `times.json`, ściąga, słowniczek, FAQ), `docs/uruchamianie.md` (build bez OpenMP, `--threads`,
  `--thread-stats`, `parallel.*`, `mc.update`, punkt 7.2 `scaling.py` / `mc_validation.py` / `plot_etap9.py` /
  `omp_overhead`; każde nowe polecenie uruchomione — wyniki w `results/`, konfiguracja bez OpenMP w folderze
  tymczasowym), `README.md`. Spostrzeżenia z danych przy pisaniu: MC 3D `static,1` ×1,93 — kolor Moore 3D zależy od
  parzystości z, a przy 8 wątkach wątek t dostaje warstwy t, t + 8, … tej samej parzystości → w każdym kolorze połowa
  wątków bez pracy (`--thread-stats`, kolor 0: 172–188 ms / 0 ms); wątek na procesorze 0 wolniejszy o 30–35% przy tej
  samej pracy (MC 2D `static,1` 416 wobec 301–310 ms).
- Eksport wersji minimalnej do folderu tymczasowego (`tools/export_minimal.py`): 201 plików, odnośniki OK, słownictwo —
  pierwsza próba 5 trafień w `mc_validation.py` (fałszywe: „wykładnik” ⊃ „wykład”, „t Studenta”) → wzorzec lokalnej
  listy `wykład(?!ni)` i „kwantyl rozkładu t” w opisie; druga próba: 0 trafień, wynik OK. Nie eksportowano do repozytorium
  wersji minimalnej.
- GUI — priorytet zadań wielowątkowych (punkt opcjonalny, bez zmian w `engine/`): `gui/jobs.py` `launch_mode()` —
  `parallel.threads > 1` → `HIGH_PRIORITY_CLASS` i bez przypięcia procesu do jednego procesora (wcześniej wysoki
  priorytet tylko z przypięciem, a przypięcie wielowątkowego zadania ścisnęłoby wszystkie wątki na jednym procesorze);
  `threads = 0` — priorytet normalny. Testy `test_launch_mode_threads`, `test_multithreaded_job_not_pinned_to_one_cpu`;
  `pytest gui\tests` 102/102. Seria `openmp_threads` przez `JobManager` (skrypt w folderze tymczasowym, jeden przebieg,
  tło ~15%): lawa full 2691 / 1369 / 680 / 473 / **449** ms, MC 543 / 265 / 139 / 93 / **74** ms (1/2/4/6/8 wątków;
  wcześniej przy 8 wątkach 579 i 109 ms — wolniej niż 6). Opis: `docs/etap-9-openmp.md`, punkt 9.
- Sesja 3 bez buildów (kod silnika zamknięty; tylko konfiguracja CMake bez OpenMP w folderze tymczasowym do sprawdzenia
  polecenia z dokumentacji) — błędów wewnętrznych kompilatora: 0. `engine/src/parallel/README.md` jest nieaktualny
  („planowane”), ale nie zmieniony (zakaz zmian w `engine/` w tej sesji) — do poprawy przy najbliższej zmianie silnika.
