# Dziennik pomiarów: wersja OpenMP

Pomiary z 18 i 20.10.2026: narzut przy 1 wątku, zgodność bitowa dla różnych liczb wątków, walidacja szachownicy MC,
skalowanie i harmonogramy (MSVC i GCC). Opis metodyki i wnioski: [`docs/openmp.md`](../../../docs/openmp.md).

## Oznaczenia i warunki

- `e8` = program po optymalizacji sekwencyjnej (`bench/baseline/engine_e8_msvc.exe`, `engine_e8_gcc`, bajtowo równe
  `engine_k7_msvc.exe` / `engine_k7a_gcc`; binarki lokalne, katalog `bench/baseline/` jest w `.gitignore`),
  `e9*` = kolejne wersje programu z OpenMP, `tN` = program z `--threads N`. S(p) = T(1)/T(p), E(p) = S(p)/p.
- Tło = obciążenie całego CPU przez inne programy (psutil, próbki 2 s) na początku i na końcu pomiaru.
- Taktowanie bazowe: maksymalny stan procesora 99% dla obu klas rdzeni (`PROCTHROTTLEMAX` i `PROCTHROTTLEMAX1` = 0x63,
  zasilanie sieciowe i bateria); sprawdzenie przed pomiarami: pętla przypięta do procesora logicznego 2, licznik
  „% wydajności procesora” 95,7–97,0% taktowania bazowego. WSL: `nproc` = 8, 7 GB pamięci. Buildy z 4 zadaniami,
  jedna ciężka operacja naraz, próg tła 30% przy stabilnym obciążeniu.
- Topologia (`GetLogicalProcessorInformationEx`, `RelationProcessorCore`): 24 rdzenie, **8 rdzeni P** (klasa wydajności 1,
  SMT, procesory logiczne {0,1}, {2,3}, …, {14,15}) i 16 rdzeni E (klasa 0, bez SMT, procesory 16–31). Pomiary
  wielowątkowe tylko na rdzeniach P, jeden wątek na rdzeń fizyczny (procesory 0, 2, …, 14), najwyżej 8 wątków,
  `parallel.affinity = pcores`, wysoki priorytet procesu.

## Przygotowanie i kontrola poprawności (18.10.2026)

- **Wybór biblioteki OpenMP w MSVC** (mikrotest, 8 wątków): `/openmp` (vcomp, OpenMP 2.0) — region 3–4 µs, krok
  „4 fazy × omp for(64) + bariery” static 13–43 µs, dynamic 96–325 µs; `/openmp:llvm` (libomp140) — region 71 µs bez
  przypięcia, ~300 µs z przypięciem, drugi przebieg zawiesił się (przerwany po 2 min); libomp140 w Visual Studio 17.8
  leży w `debug_nonredist`. Wybrane `/openmp`, kod zgodny z OpenMP 2.0.
- Build MSVC Release (`Found OpenMP_CXX: -openmp (found version "2.0")`) i GCC Release (`Found OpenMP: TRUE (found
  version "4.5")`) bez ostrzeżeń, ctest 12/12.
- Rozpoznanie (pojedyncze przebiegi): `test_3d` front 1 → 8 wątków caSim 102 → 49 ms; full z `pcores` 3,0 s →
  0,52–1,05 s (duży rozrzut przy 8 wątkach). `--thread-stats`: wątek na procesorze 0 stale najwolniejszy (reguły
  360–530 ms wobec 330–350 ms pozostałych); 8. wątek na procesorze 1 zamiast 0 bez wyraźnej różnicy.
- `bench/micro/omp_overhead.cpp` (MSVC, 8 wątków, przypięte): region 6,5 µs, bariera 4,2 µs, krok „region + 3 fazy
  ompFor(64) + 2 bariery”: static 15,6 µs, dynamic 164 µs, guided 138 µs (bez przypięcia: 10 / 87 / 78 µs); wątki puli
  trwałe (0 zmian wątku systemu w 5000 regionów); region `num_threads(1)` 0,12 µs.
- Zgodność wstępna (`zgodnosc_e9_cz1.md`, `_cz2.md`, program przed poprawkami narzutu): 15/15 configów, e8 = 1 wątek =
  8 wątków, MSVC i GCC.
- **Narzut przy 1 wątku** (A/B e8 / e9, 15 powtórzeń w lawie). Kolejne wersje i przyczyny:
  - e9a: lawa caSim ×1,037–1,055 (MSVC, tło 28%). Poprawka e9b: liczniki reguł i kontekst kroku jako zmienne lokalne
    (przez referencję do struktury kompilator zapisywał je do pamięci przy każdej zmianie), `toMicrostructure` przy
    1 wątku bez regionu OpenMP. e9b: MSVC `test_3d` ×1,028, `etna_real` ×1,062; GCC ×1,009–1,043. Wariant z osobnymi
    pętlami kandydatów i reguł (e9c) bez różnicy.
  - classic MSVC e8 / e9b: 100³ VN ×1,039, Moore ×1,082; 300³ total ×1,032 (sekcja `vents` 29 → 87 ms). Przyczyna:
    `countLayers` / `scanLayer` (i `colorTrials` szachownicy) dodawały do liczników przez referencję, a MSVC (bez
    analizy aliasów wg typów) zapisywał je do pamięci i przeładowywał wskaźniki siatki w każdej iteracji (3× wolniej).
    Poprawka e9d: liczniki lokalne, dodawane na końcu.
  - e9d: lawa `lava_mc_2d` ×1,048 (+0,3 ms na 6 ms: wywołania funkcji na warstwę). Poprawka e9e: funkcje frontu dostają
    zakres warstw (1 wątek: jedno wywołanie). e9e: MSVC ×1,013–1,040, GCC ×0,999–1,027.
  - Mapa linkera MSVC (build e8 i e9e z `/MAP` w folderze tymczasowym): gorące funkcje przesunięte względem linii 64 B
    (`gatherLavaCandidates` mod 64 = 0 → 48, `hasSupport` 48 → 32, `dropDepth` 48 → 0, `updateLava` 32 → 48). W MSVC
    narzut 1 wątku waha się między wariantami kodu o ±4% przy tej samej ścieżce wykonania (e9d: −0,3…+1%,
    e9e: +3,7…4%); w GCC (wyrównanie funkcji) ≤ 2,7%.
  - e9f (reguły warstwy w osobnej funkcji zwracającej sumy przez wartość): e9f/e8 ×1,001 / ×1,006 / ×1,037; e9g
    (+ pomijanie pustych warstw): ×1,035 / ×1,023 / ×1,018. Wybrany e9f (najmniejszy narzut w dużych przypadkach).
- **Dobór przypadków skalowania** (pojedyncze przebiegi): `etna_real` front T(1) 0,15 s (przykład zbyt małego frontu);
  duża lawa 3D 128 × 128 × 64 z 24 kraterami (`lava_duza_3d`): front 0,84 s, full 19,7 s; classic 1000² front tylko
  0,12 s → 2000² (400 zarodków) 0,68 s; classic 300³ 3,6 s; MC szachownica 1000² mcSim 2,1 s (random 12–17 s);
  MC 100³ Moore.
- **Priorytet procesu:** pełny przebieg dużej lawy przy 8 wątkach i priorytecie normalnym 9,7 s; `--thread-stats` —
  każdy wątek ~10 ms na krok w fazie ramki (czekanie na barierach). Z `HIGH_PRIORITY_CLASS`: caSim 376 ms wobec 2788 ms
  przy 1 wątku (×7,4), ramka 13 ms. Przy 8 zajętych rdzeniach P wątek o priorytecie normalnym wywłaszczony przez program
  w tle na cały kwant czasu zatrzymuje pozostałe na barierze, dlatego pomiary uruchamiają silnik z wysokim priorytetem.
- **Wstępne porównanie harmonogramów** (8 wątków, 3 powtórzenia, tło 31%, 3,4 min) →
  `wstepne/harmonogramy_wstepne_msvc.md`: lawa front `static,1` (`etna_real` 33 ms wobec 60–75 ms), full `guided` /
  `dynamic` (`static` ×1,6: dolne warstwy to tania skała, górne drogie powietrze), classic 2D `static` (`dynamic` ×3,6
  — koszt pobierania porcji w vcomp), classic 3D `dynamic,4`, MC 2D `guided,4` (różnice ≤ 23%), MC 3D `dynamic`
  (`static,1` ×2,25). Te harmonogramy wpisano do przypadków `scaling.py`.
- **Walidacja statystyczna szachownicy MC** (`bench/mc_validation.py`, 12 ziaren generatora, 40 s) → `mc_walidacja.csv`,
  `mc_walidacja.md`, `docs/img/openmp_mc_walidacja.png`. Pierwszy przebieg z kT = 0,5 w trzecim przypadku był powyżej
  temperatury przejścia modelu Pottsa 2D dla Q = 50 (kT_c = 1/ln(1 + √50) ≈ 0,48, ziarna nie rosną), więc kT = 0,3.
  Po 100 MCS (szachownica / random − 1, t Welcha): 2D VN kT = 0 — liczba ziaren −1,7% (t = −9,3), średnia wielkość
  +1,7%, energia −0,7%, wykładnik wzrostu 0,660 / 0,660; 3D Moore kT = 0 — ziarna −2,3% (t = −5,1), wielkość +2,4%,
  wykładnik 0,806 / 0,777; 2D VN kT = 0,3 — ziarna −1,1% (t = −3,0), wykładnik 0,405 / 0,406. Współczynnik akceptacji
  równy (±0,7%). Ta sama kinetyka; szachownica nieco „wyprzedza” wariant naiwny o kilka MCS (każda komórka próbowana
  dokładnie raz na MCS, a przy losowaniu ze zwracaniem ~37% komórek w danym MCS nie dostaje próby).
- **Przypinanie pod Linuksem:** z `OMP_PROC_BIND=close` libgomp przypina wątek główny do jednego procesora przed `main()`,
  a lista rdzeni z `sched_getaffinity` miała wtedy 1 procesor (wszystkie wątki na nim, `test_3d` full 4 wątki: 51 s).
  Poprawka: lista z `/sys/devices/system/cpu/online`, najpierw pierwszy procesor każdego rdzenia. Po poprawce GCC
  `test_3d` full (guided, pcores): 1/2/4/6/8 wątków 2738 / 1393 / 779 / 520 / 468 ms.
- `omp_overhead` GCC (WSL): bez wiązania p = 8 region 165 µs; z `OMP_PROC_BIND=close OMP_PLACES=cores`: region
  0,9 / 2,0 / 4,9 µs (p = 2/4/8), bariera 0,3 / 0,6 / 1,1 µs, krok static 1,6 / 3,5 / 27 µs, dynamic 19 / 22 / 26 µs
  (vcomp: 52–164 µs), guided 6 / 10 / 16 µs. Pomiar GCC w WSL: wiązanie przez libgomp, program z
  `parallel.affinity = none` (`scaling.py --wsl`).
- Statystyki wyniku CA (`stats.json`) nie były w żadnej sekcji czasu (classic 2000² przy 8 wątkach „reszta” ~30%):
  teraz sekcja `caStats`, liczona równolegle (wynik ten sam); classic 2000²: 40 → 12 ms (1 → 8 wątków).
- Binarki końcowe `engine_e9_msvc.exe` (= e9f), `engine_e9_gcc`; build GCC bez ostrzeżeń, ctest 12/12, doctest MSVC
  119/119.
- **Oficjalny A/B narzutu przy 1 wątku** (e8 / e9, 4 części, `ab_e9_msvc.md`, `ab_e9_gcc.md`): MSVC (tło 19–24%)
  caSim / mcSim: lawa `test_3d` ×0,997, `etna_real` ×1,002, `lava_mc_2d` ×1,055 (6,10 → 6,44 ms), `lava_mc_3d` (CA)
  ×1,034; classic ×0,998–1,020; MC ×0,995–1,009; total ×0,989–1,014. GCC (tło 18–33%): lawa ×1,023–1,035, classic
  ×0,961–1,001, MC ×0,996–1,012, total ×0,968–1,022. Narzut ≤ 3% w całym przebiegu wszystkich 13 przypadków; w krótkich
  przypadkach lawy faza CA +2…5,5% (0,1–3 ms), w granicy szumu układu kodu.
- **Zgodność końcowa:** `zgodnosc_e9.md` — 15/15 configów, e8 = 1 wątek = 8 wątków, MSVC i GCC;
  `zgodnosc_e9_full.md` (`ca.sweep = full`, 8 wątków, 4,4 min) — 13/13; `zgodnosc_e9_szachownica.md`
  (`mc.update = checkerboard`, configi z MC) — 6/6: 1 wątek = 8 wątków (dynamic) = 3 wątki (guided, porcja 2), MSVC i GCC.
- Inne buildy: MSVC Debug — ctest 12/12; GCC z `VOLCANO_OPENMP=OFF` (`build-gcc-noomp/`) — bez ostrzeżeń (także bez
  `-Wunknown-pragmas`), ctest 12/12, `--threads 8` daje ostrzeżenie i przebieg jednowątkowy.
- **ThreadSanitizer** (GCC 11, `-fsanitize=thread -g -O3`, 4 wątki, małe przypadki): 66–403 raportów na przypadek;
  pary miejsc zawsze rozdzielone barierą albo końcem regionu (np. odczyt `type` w regułach ↔ zapis w fazie zmian).
  libgomp nie jest instrumentowana, więc TSan nie widzi synchronizacji barier: wynik nierozstrzygający (fałszywe alarmy
  na granicach faz). Brak wyścigów potwierdzają testy bitowe (`test_parallel.cpp`: 1/2/3/4/8 wątków × harmonogramy)
  i porównania wszystkich configów.
- GUI: `pytest gui\tests` 100/100; seria z szablonu `openmp_threads` uruchomiona przez GUI (lawa full 2609 / 1477 /
  784 / 541 / 579 ms, MC 522 / 391 / 138 / 95 / 109 ms dla 1 / 2 / 4 / 6 / 8 wątków; GUI uruchamiało wtedy silnik
  z priorytetem normalnym, stąd 8 wątków nie szybciej niż 6).

## Pomiar skalowania i harmonogramów (20.10.2026, 04:59–05:28)

Przed pomiarem: taktowanie bazowe sprawdzone (95,7–97,0%), próba `scaling.py` (`lava_etna_real`, p = 1, 2) zgodna.
Pomiar w częściach ≤ 10 min, tło na początku i końcu każdej, scalanie `--from-raw`. Komputer bez innej pracy.

| Część | Polecenie (skrót) | Czas, tło | Wynik |
|---|---|---|---|
| MSVC skalowanie cz. 1 (lawa) | `scaling.py --cases lava_etna_real,lava_duza_3d_front,lava_duza_3d_full --name skalowanie_msvc_cz1` | 3,0 min, 14 → 15% | S(8) total / faza: `etna_real` 2,12 / 4,98 (f total 0,37: przygotowanie terenu i zapis), duża lawa front 4,59 / 5,36, full 6,22 / 6,34 (T(1) 12,6 s → 2,0 s; E(6) 0,93, E(8) 0,78) |
| MSVC skalowanie cz. 2 (classic, MC 2D) | `--cases classic_2000x2000_s400_vn,classic_300x300x300_s100_vn,mc_cb_2d_1000,mc_random_2d_1000` | 3,1 min, 14 → 12% | classic 2000² 3,66 / 6,67, 300³ 3,22 / 4,82, MC szachownica 2D 3,30 / 6,18 (mcSim 2059 → 333 ms; random przy 1 wątku 8324 ms, szachownica przy 1 wątku ×4,0 szybsza: przegląd po kolei zamiast losowych adresów) |
| MSVC skalowanie cz. 3 (MC 3D) | `--cases mc_cb_3d_100,mc_random_3d_100` | 3,4 min, 15 → 10% | MC szachownica 3D 3,55 / 6,06 (mcSim 5743 → 948 ms; mcStats ~1,1 s sekwencyjnie); random przy 1 wątku 18 860 ms (×3,3) |
| MSVC harmonogramy (8 wątków) | `--schedules --cases <7 przypadków>` | 5,1 min, 14 → 15% | lawa front `static,1` (`etna_real` 23 ms, inne ×1,55–2,25; duża lawa 135 ms, `dynamic` ×1,09, `static` ×1,60), lawa full `dynamic` / `guided` (1874 / 1879 ms, `static` ×1,33), classic 2D `static` (`guided` ×1,05, `dynamic` ×3,74), classic 3D `dynamic,4`, MC 2D `guided,4` (wszystkie ≤ ×1,31), MC 3D `guided` (`static,1` ×1,93) |
| GCC skalowanie cz. 1 (lawa, WSL) | `scaling.py --wsl --bin build-gcc-release/bin/engine --cases <lawa> --name skalowanie_gcc_cz1` | 3,0 min, 13 → 12% | `etna_real` 1,89 / 3,44 (faza przy 8 wątkach 23,0 [15,9–57,8] ms, szum procesorów wirtualnych; p = 6: 4,17), duża lawa front 4,49 / 5,11, full 6,16 / 6,26 |
| GCC skalowanie cz. 2 (classic, MC) | `--cases classic_2000x2000_s400_vn,classic_300x300x300_s100_vn,mc_cb_2d_1000,mc_cb_3d_100` | 3,9 min, 14 → 13% | S(6) / S(8) fazy: classic 2000² 4,31 / 4,33, 300³ 4,08 / 2,86, MC 2D 5,14 / 4,70, MC 3D 5,06 / 5,13 (p = 8 w WSL nie skaluje dalej, patrz niżej) |
| GCC harmonogramy lawy | `--wsl --schedules --cases <lawa> --name harmonogramy_gcc` | 1,8 min, 14 → 11% | `etna_real` `static,1` 21,0 ms (`dynamic` ×1,12: w libgomp pobieranie porcji jest tanie, w vcomp ×2,25), duża lawa front `dynamic` 132 ms, full `dynamic` 1857 ms (`static` ×1,35) |

- Wszystkie przebiegi bitowo zgodne z p = 1; tło 10–15% (stałe zapytania WMI programów w tle ~1,3–2,1 procesora),
  bez skoków. Scalone tabele: `skalowanie_msvc.md/.csv/_threads.json`, `skalowanie_gcc.*`, `harmonogramy_msvc.*`,
  `harmonogramy_gcc.*`.
- Problem techniczny: pierwsze dwa starty części GCC bez `--bin` zakończyły się błędem „nie można otworzyć pliku
  konfiguracyjnego /tmp/…”: domyślny program Windows uruchomiony przez interop nie widzi `/tmp` maszyny WSL.
  Ponowione z `--bin build-gcc-release/bin/engine`; po pomiarze domyślny `--bin` z `--wsl` to program GCC.
- **p = 8 w WSL:** classic 300³ przy p = 8: 1103 / 630 / 1185 / 703 / 1236 ms — wolne w powtórzeniach, w których p = 8
  idzie zaraz po p = 6, który zapisał 351 MB `ca_result.bin`. Przy 8 wątkach na 8 procesorach wirtualnych wątki jądra
  (zapis brudnych stron na dysk wirtualny) zabierają procesor jednemu wątkowi, a reszta czeka na barierze; przy p ≤ 6
  są wolne procesory. Efekt systematyczny, opisany jako ograniczenie pomiaru GCC (mediany odporne).
- Scalanie z wyjściem do `NUL` przerwało się na znaku „−” (w Windows NUL ma kodowanie cp1250); `scaling.py`,
  `plot_openmp.py` i `mc_validation.py` piszą teraz zawsze w UTF-8, scalenie powtórzone.

## Obserwacje z danych i wykresów

- Wykresy `python bench/plot_openmp.py` (+ `mc_validation.py --from-csv`, `mc_walidacja.md` bez zmian). 7 przypadków na
  jednym wykresie linii nie przechodzi kontroli rozróżnialności kolorów dla wszystkich par, więc S/E i Amdahl są
  w panelach wg rodzin (≤ 3 serie) ze znacznikami. Części szeregowe liczone jako mediany części z surowych przebiegów
  (mediany sekcji z tabeli nie sumują się do mediany total); „reszta” to głównie zwolnienie pamięci automatu po zapisie:
  4 / 7 / 45 ms dla Etny / 2000² / 300³ przy p = 1.
- MC 3D `static,1` ×1,93: kolor Moore 3D zależy od parzystości z, a przy 8 wątkach wątek t dostaje warstwy t, t + 8, …
  tej samej parzystości, więc w każdym kolorze połowa wątków nie ma pracy (`--thread-stats`, kolor 0: 172–188 ms / 0 ms).
  Wątek na procesorze 0 wolniejszy o 30–35% przy tej samej pracy (MC 2D `static,1` 416 wobec 301–310 ms).
- GUI uruchamia teraz zadania z `parallel.threads > 1` z wysokim priorytetem i bez przypięcia do jednego procesora
  (`gui/jobs.py`, `launch_mode()`); seria `openmp_threads` przez `JobManager` (jeden przebieg, tło ~15%): lawa full
  2691 / 1369 / 680 / 473 / 449 ms, MC 543 / 265 / 139 / 93 / 74 ms (1/2/4/6/8 wątków; wcześniej przy 8 wątkach 579
  i 109 ms).
