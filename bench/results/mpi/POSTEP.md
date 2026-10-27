# Dziennik pomiarów: wersja MPI

Pomiary z 20–21.10.2026: zgodność bitowa `engine_mpi` z `engine` (MS-MPI i OpenMPI), narzut zmian w `engine`,
przypinanie procesów, dobór przypadków i pomiar skalowania według [`PLAN_POMIARU.md`](PLAN_POMIARU.md). Opis
implementacji i wnioski: [`docs/mpi.md`](../../../docs/mpi.md).

## Oznaczenia i warunki

- `e9` = program wersji OpenMP (`bench/baseline/engine_e9_msvc.exe`, `engine_e9_gcc`; binarki lokalne, katalog
  `bench/baseline/` jest w `.gitignore`), `e10*` = kolejne wersje programu po dodaniu pasów MPI, `mN` = `engine_mpi`
  na N procesach, `mN×T` / `hNxT` = N procesów po T wątków OpenMP (tryb hybrydowy), `cN` = N procesów
  z `mpi.exchange = changed`, `oT` = `engine` z T wątkami OpenMP w tym samym przebiegu.
- MPI: MS-MPI 10.1.12498.52 z SDK (`mpi.h` deklaruje MPI 2.0, `msmpi.lib`), OpenMPI 4.1.2 w WSL (`mpicxx` = g++ 11.4).
- Taktowanie bazowe (`PROCTHROTTLEMAX` i `PROCTHROTTLEMAX1` = 99%, sieć i bateria; licznik „% wydajności procesora”
  pod obciążeniem rdzenia P 94,8–97,2%), WSL 8 procesorów / 8 GB, buildy z 4 zadaniami, jedna ciężka operacja naraz.
  Łącznie najwyżej 8 procesów × wątków na rdzeniach P (procesory logiczne 0, 2, …, 14). Tło = obciążenie całego CPU
  przez inne programy (psutil, próbki 2 s), próg 30%.
- Każdy pomiar: `--high-priority` (`mpiexec` uruchamia procesy z priorytetem normalnym) i `parallel.affinity = pcores`.

## Tabela kroków

| Krok | Pliki wyników | Wynik | Zgodność | Tło [% CPU] |
|---|---|---|---|---|
| Zgodność domyślnego `engine` po zmianach | `zgodnosc_e10_engine.md`, `zgodnosc_e10_engine_t8.md` | e9 = e10 (MSVC, GCC), także 8 wątków z szachownicą | 15/15 × 2 | — |
| Zgodność `engine_mpi`, MSVC / MS-MPI | `zgodnosc_mpi_msvc.md`, `_full.md`, `_p1_random.md` | e9 = m1 = m3 = m8 = c3 = c8 = m2×4 = m3_gcc (krzyżowo OpenMPI); `ca.sweep = full`; MC `random` przy 1 procesie | 15/15 × 3 | — |
| Zgodność `engine_mpi`, GCC / OpenMPI | `zgodnosc_mpi_gcc.md`, `_full.md`, `_p1_random.md` | e9_gcc = m1 = m3 = m8 = m3/m8 `changed` = m2×4; `full`; `random` przy 1 procesie | 15/15 × 3 | — |
| Przypinanie w Windows | — | maski procesów 2, 4, 6, 8 / {2,4,6,8} {10,12,14,0}, priorytet `High`; `mpiexec -affinity` odrzucone (rdzenie E) | — | — |
| Buildy i testy | — | MSVC Release i Debug: `ctest` 21/21; GCC Release 21/21; GCC `VOLCANO_MPI=OFF` 12/12 (`engine` bajtowo ten sam); `pytest` 102/102 | — | 18–33 |
| A/B narzutu `engine` (1 wątek) | `ab_e10_{msvc,gcc}_*.md` (+ wersje pośrednie `ab_e10a_*`, `ab_e10d_*`) | e10a: MSVC lawa +7–8%, GCC +3–21% → poprawka `frontStepSequential<bool Strip>` → cały przebieg ≤ +2,1% | wszystkie przebiegi | 20–30 |
| Dobór przypadków | `dobor_{msvc,gcc}.*` | 7 przypadków, pojedyncze przebiegi; plan pomiaru 6 części, ~30 min | zgodne | 16–21 |
| Pomiar skalowania MSVC (A1, A2, B, C) | `skalowanie_mpi_msvc{,_cz1…4}.*` | 7 przypadków × 13 wariantów, 18,3 min | 585/585 | 13–24 |
| Pomiar skalowania GCC (D, E) | `skalowanie_mpi_gcc{,_cz1,_cz2}.*` | 7 przypadków × 5 wariantów, 7,0 min | 225/225 | 10–19 |
| Wykresy | `bench/plot_mpi.py`, `docs/img/mpi_*.png` | 8 wykresów | — | — |

## Przygotowanie i poprawność (20.10.2026)

- **Warstwy brzegowe:** w osi z reguły lawy nie mają promienia 1 — `dropDepth()` (głębokość spadku z komórki powietrza)
  schodzi do 16 poziomów w dół, a `hasSupport()` najniższego czyta jeszcze komórkę pod spodem, więc pas potrzebuje
  17 warstw brzegowych pod sobą (z głębszych niż pierwsza reguły czytają tylko typ) i 1 nad sobą; classic i MC po 1.
  Pasy w osi warstw wersji OpenMP (z; płaszczyzna x–y: y), bo to oś zewnętrzna pamięci: indeks globalny komórki okna =
  indeks w oknie + stała, pas jest ciągłym fragmentem tablic.
- Build GCC Release (`Found MPI_CXX … (found version "3.1")`) bez ostrzeżeń. WSL pracuje jako `root`, a OpenMPI bez
  `--allow-run-as-root` odmawia startu; WSL zgłasza 4 rdzenie, więc 8 procesów w testach wymaga `--oversubscribe`
  (CMake dodaje obie opcje i `--bind-to none`, gdy `mpiexec --version` zgłasza Open MPI). `engine_tests` 123/123,
  `engine_mpi_tests` pod `mpiexec -n 1/2/3/4/5/8`: 9/9 przypadków; `ctest` 21/21.
- **Czułość testów (mutacje, cofnięte po sprawdzeniu):** lawa z 1 warstwą brzegową pod pasem zamiast 17 — 4 przypadki
  lawy niezgodne przy 3 procesach; bez list src warstw brzegowych w automacie frontalnym — 6 przypadków; MC z wymianą
  tylko po ostatnim kolorze — 3 przypadki MC.
- Przebieg dymny `mpiexec -n 3 engine_mpi --config configs/test_3d.json`: 284 kroki; obliczenia procesów 45,7 / 40,3 /
  2,1 ms (lawa w dolnych warstwach, pas górny prawie bez pracy). `mc.update = random` przy 2 procesach: komunikat
  i `MPI_Abort` z kodem 1.
- Build MSVC Release z MS-MPI bez ostrzeżeń (`/W4 /permissive-`; kod MPI pisany przenośnie, bez funkcji MPI-3),
  `ctest` 21/21; MSVC Debug 21/21 (315 s, asercje w kodzie MPI włączone); GCC z `VOLCANO_MPI=OFF` (`build-gcc-nompi/`)
  12/12, `engine` bajtowo identyczny z buildem z MPI.
- **Przypinanie i priorytet w Windows** (`--high-priority --set parallel.affinity=pcores`, MC 100³; maski odczytane
  w trakcie przebiegu przez `Get-Process`): m4 — maski 0x4, 0x10, 0x40, 0x100 (procesory 2, 4, 6, 8), priorytet `High`;
  h2×4 — maski 0x154 i 0x5401 (procesory {2, 4, 6, 8} i {10, 12, 14, 0}), każdy wątek tylko na swoim procesorze.
  `mpiexec -affinity` MS-MPI z programem bez przypinania: maska procesu zostaje pełna, a `-affinity` (= `spr:L`) posłał
  wątki procesu 0 na rdzenie E (procesory 16–31); `-affinity_layout seq:P` związał oba wątki procesu z jednym
  procesorem logicznym (mcSim 1 897 ms zamiast ~900). MS-MPI nie rozróżnia rdzeni P i E, więc przypina sam silnik.
  Komunikacja m4 (MC 100³, Moore, 8 kolorów): 801 wymian, 8 komunikatów i 332 936 B na wymianę, 104 ms na proces (7%
  fazy); statystyki ziaren na procesie 0: 864 ms (część szeregowa).
- **Narzut domyślnego `engine` (1 wątek, A/B e9 / e10):**
  - e10a: MSVC lawa caSim ×1,071–1,078, GCC ×1,031–1,036. `--timing-detail`: faza reguł frontu +8–9%
    (`test_3d` 84,5 → 90,8 ms). Jedyna zmiana kodu w tej fazie: indeks globalny `idx + hashBase_`; bez niego (próba)
    nadal +4,8%, czyli w MSVC głównie układ kodu: mapy linkera (`/MAP`, `dumpbin /disasm`) pokazują identyczny kod
    maszynowy `gatherLavaCandidates`, `frontCandidatesLayer`, `frontApply`, `frontDescent`, przesunięty względem linii
    64 B (mod 64: 0 → 48, 32 → 16 …), a `frontRulesLayer` ma dodatkowo inny przydział rejestrów.
  - e10d (`frontRulesLayer<bool Shifted>`): MSVC caSim ×1,010–1,017; GCC bez zmian. Pełny A/B e10d: MSVC dobrze, GCC
    lawa ×1,039–1,051, classic Moore 100³ ×1,158, `lava_mc_3d` caSim ×1,172. Przyczyna w GCC: granice pętli z pól
    obiektu (`ownLo_`, `ownHi_`) w `frontStepSequential` (próba ze stałymi granicami: +21% → +11%).
  - e10e (`frontStepSequential<bool Strip>`, `frontCandidatesRules<Strip>`, `frontRulesLayer<Strip>`: bez pasów stałe
    granice `0 … n` i bez `hashBase_`, jak w wersji OpenMP): GCC classic Moore 100³ ×1,188 → ×0,993, `lava_mc_3d`
    ×1,169 → ×0,993; MSVC w granicach ±4% układu kodu. Przyjęta.
  - Końcowe A/B e9 / e10 (1 wątek, procesor 2, naprzemiennie, wszystkie przebiegi bitowo zgodne, tło 20–30%):

    | Grupa | MSVC e10/e9 (faza) | MSVC (total) | GCC e10/e9 (faza) | GCC (total) |
    |---|---|---|---|---|
    | lawa `test_3d`, `etna_real`, `lava_mc_2d` (caSim, 15 powt.) | ×1,022 / ×1,017 / ×0,999 | — | ×0,995 / ×0,989 / ×0,985 | — |
    | classic 1000² VN / Moore, 100³ VN / Moore, 300³ (caSim) | ×1,001 / 1,007 / 1,001 / **1,042** / 1,005 | ×0,991–1,021 | ×0,998 / 0,982 / 1,010 / 0,996 / 0,942 | ×0,968–1,017 |
    | MC 200², 1000², 50³ (mcSim), `lava_mc_3d` (mcSim / caSim) | ×1,003 / 1,005 / 0,977, ×1,002 / 1,017 | ×0,976–1,004 | ×1,002 / 0,979 / 1,000, ×1,013 / 0,995 | ×0,979–1,017 |

    Cały przebieg ≤ +2,1%, faza ≤ +2,2% poza classic Moore 100³ w MSVC (×1,042, cały przebieg ×1,021; w GCC ×0,996).
- Zgodność (wszystkie tabele powtórzone po każdej zmianie kodu, ostatnio na binarkach końcowych i po dodaniu
  `mpi.initMs`): wszystkie 8 tabel `zgodnosc_*.md` 15/15, 0 różnic.
- `mpi.initMs` w `times.json` (czas do końca `MPI_Init_thread`, min / średnia / maks po procesach) i kolumna `initMax`
  w `scaling_mpi.py`: `test_3d` na 3 procesach MS-MPI 11–17 ms, OpenMPI (WSL) 296–298 ms; `total` w WSL zawiera
  start OpenMPI (~0,3 s).
- Próba `scaling_mpi.py` (Windows i WSL, `lava_etna_real`, m1 / m3): bitowo zgodne, `priority` = `high` we wszystkich
  procesach (Windows `HIGH_PRIORITY_CLASS`, WSL nice −5), `cpus` Windows 2 / 4 / 6, WSL 0 / 2 / 4. Etna przy 3 procesach
  wolniej niż przy 1 (caSim 90 → 180 ms; komunikacja 74% fazy, 1,78 MB na wymianę).
- OpenMPI w WSL: `--use-hwthread-cpus` zamiast `--oversubscribe` w pomiarach (8 miejsc = 4 rdzenie × 2 wątki SMT, więc
  8 procesów nie jest nadsubskrypcją); m8 naprzemiennie: classic 2000² 122 / 136 / 103 ms vs 154 / 101 / 101 ms,
  MC 1000² 447 / 434 vs 464 / 425 ms (różnica w granicach szumu). Testy CMake zostają przy `--oversubscribe`.

### Dobór przypadków (20.10.2026, pojedyncze przebiegi)

`dobor_msvc.md` (10 wariantów, 2,5 min, tło 16–21%) i `dobor_gcc.md` (5 wariantów, 1,3 min); komputer w zwykłym
użyciu, czasy orientacyjne; wszystkie przebiegi bitowo zgodne z m1. Faza obliczeń, MSVC (S fazy = T(m1) / T):

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

Obserwacje (z `computePerRank`, `haloAvg`, `reduceAvg` w `dobor_msvc_raw.csv`), które ustaliły plan:

- **Procesor 0 jest wolniejszy.** Proces na procesorze logicznym 0 (8. rdzeń P; obsługuje przerwania systemu) liczy pas
  30–60% dłużej niż procesy na 2–14 (classic 300³ m8: 873 ms przy 593–692 ms pozostałych). Pasy są statyczne, więc
  najwolniejszy proces wyznacza czas kroku; dlatego w planie dodatkowo m7 (bez procesora 0).
- **Lawę ogranicza nierównomierność, nie bajty.** Front dużej lawy m8: wymiana warstw 82 ms na 260 wymian (~0,3 ms
  na krok, 3,85 MB), czekanie w `MPI_Allreduce` 145 ms, obliczenia procesów 10–216 ms. 17 warstw pod pasem kosztuje
  bajty (z 3,85 MB na wymianę 1,72 MB to głębsze warstwy samego typu; przy 1 warstwie byłoby 2,13 MB), ale przez pamięć
  współdzieloną to tylko ~0,3 ms na krok.
- MPI przestaje się opłacać, gdy krok procesu jest krótszy niż ~1 ms (Etna: krok frontu 0,33 ms, S = 0,4–0,7).
- `changed`: w lawie m8 pomija 14 985 z 30 160 warstw (front 3,85 → 2,14 MB na wymianę), w classic i MC prawie nic.
- Tryb hybrydowy (h2×4 albo h4×2) najlepszy z wariantów MPI na 8 rdzeniach w 6 z 7 przypadków (wyjątek: classic 2000²).

## Pomiar skalowania (21.10.2026, 03:24–03:54)

Przed pomiarem: binarki zgodne z planem (SHA-256 `engine_mpi_e10_msvc.exe` 524187df…, `engine_e10_msvc.exe` 1d58245b…,
`engine_mpi_e10_gcc` d7a8bc1c…, `engine_e10_gcc` 8a3d35e6…), taktowanie bazowe (94,8–97,2%), tło 16%; próba przypięcia
Windows `[[2], [4], [6]]`, WSL `[[0], [2], [4]]`, 3 × `high`; próba `scaling_mpi.py` (Etna, m1 / m3) bitowo zgodna.
Części według planu, przerwa ~1 min między częściami, komputer bez innej pracy.

| Część | Przypadki | Czas, tło | Wynik (faza; S w nawiasie) |
|---|---|---|---|
| A1 (MSVC) | `lava_etna_real`, `lava_duza_3d_front` | 1,8 min, 13 → 14% | Etna m1 92,0 ms, m3 167 (0,55), m8 203 (0,45), h2×4 116 (0,80), o8 18,5 (4,96); front m1 762 ms, m3 538 (1,42), m7 302 (2,52), m8 340 (2,24), h2×4 288 (2,64), o8 126 (6,03). Front m8: najdłużej liczy pas dolny (~200 ms), pas górny na procesorze 0 ~9 ms, więc ogranicza nierównomierność |
| A2 (MSVC) | `lava_duza_3d_full` | 5,1 min, 24 → 14% (na starcie chwilowo pobieranie w tle) | m1 13 415 ms [13 395–13 447], m3 5 406 (2,48), m6 2 871 (4,67), m7 2 506 (5,35), m8 2 960 (4,53), h2×4 2 487 (5,39), o8 2 164 (6,20). W m8 ostatni proces (procesor 0) 2 460–2 770 ms przy 2 080–2 130 ms pozostałych w każdym powtórzeniu, więc m7 < m8. Pojedyncze przebiegi m8 i c8 +25–35% w różnych powtórzeniach (każde wejście programu w tle zatrzymuje krok przy 8 procesach na 8 rdzeniach); mediana z 5 stabilna |
| B (MSVC) | classic 2000², 300³ | 4,0 min, 18 → 14% | 2000²: m1 539 ms, m2 263 (2,05), m4 137 (3,94), m7 80,7 (**6,68**), m8 90,3 (5,97), o8 86,1 (6,26); 300³: m1 3 379, m4 1 179 (2,87), m7 932 (3,62), m8 1 019 (3,32), h2×4 866 (3,90), o8 717 (4,72) |
| C (MSVC) | MC szachownica 1000², 100³ | 4,4 min, 13 → 13% | 1000²: m1 2 052 ms, m4 518 (3,96), m7 305 (**6,72**), m8 340 (6,03), o8 336 (6,10); 100³: m1 5 741, m4 1 519 (3,78), m7 963 (5,96), m8 1 035 (5,55), h4×2 956 (6,00), o8 916 (6,27) |
| D (GCC, WSL) | Etna, front, full | 3,1 min, 12 → 19% | Etna m1 81,7 ms, m8 176 (0,46), h2×4 80,3 (1,02), o8 21,2 (3,86); front m1 681, m8 298 (2,28), h2×4 244 (2,79), o8 151 (4,52); full m1 11 621, m3 4 454 (2,61), m8 2 374 (4,89), h2×4 2 125 (5,47), o8 1 966 (5,91). m1 w pierwszych 3 powtórzeniach ~8% wolniejszy (procesory wirtualne WSL) |
| E (GCC, WSL) | classic 2000², 300³, MC 1000², 100³ | 3,9 min, 17 → 10% | classic 2000² m1 487 ms, m8 106 (4,59), h2×4 117 (4,17), o8 90,1 (5,41); 300³ m1 3 196, m8 961 (3,33), h2×4 768 (4,16), o8 743 (4,30); MC 1000² m1 2 010, m8 372 (5,40), h2×4 336 (5,98), o8 341 (5,89); MC 100³ m1 5 391, m8 1 079 (4,99), h2×4 991 (5,44), o8 861 (6,26) |

- 810 przebiegów, wszystkie bitowo zgodne z 1 procesem; `priority` = `high` i `cpus` zgodne z planem we wszystkich
  procesach (WSL m8 `0 2 4 6 1 3 5 7`); tło 10–24%, żadna część nie była powtarzana. Scalone tabele
  `skalowanie_mpi_msvc.{md,csv}` i `skalowanie_mpi_gcc.{md,csv}` (`--from-raw`).
- Po pomiarze: tabele `zgodnosc_mpi_{msvc,gcc}_full.md` odświeżone na binarkach końcowych (15/15, 0 różnic; 4,2 i 3,9 min).
- Główne wyniki (MSVC, faza): MC 1000² S(7) = 6,72, classic 2000² 6,68 (więcej niż OpenMP na 8 wątkach: 6,10 / 6,26),
  MC 100³ h4×2 6,00, pełny przebieg lawy h2×4 5,39, classic 300³ h2×4 3,90, front lawy h2×4 2,64, Etna ≤ 0,80.
  S(8) < S(7) wszędzie (procesor 0: obliczenia pasa 13–30% dłuższe); udział komunikacji przy 8 procesach 21–84%,
  głównie czekanie na najwolniejszy pas; `changed`: lawa 20–57% bajtów (Etna −22% czasu), MC 100³ 50%, MC 1000² 100%.
- Wykresy `python bench/plot_mpi.py` (8 wykresów); OpenMP z pomiaru wersji OpenMP
  (`bench/results/omp/skalowanie_{msvc,gcc}.csv`) jako romb kontrolny na wykresie MPI vs OpenMP.
- Wersja minimalna (eksport do folderu tymczasowego) buduje `engine_mpi` (MSVC, MS-MPI); wynik `test_3d` na 3 procesach
  = wynik `engine_mpi_e10_msvc.exe` (SHA-256 `ca_result.bin`).
