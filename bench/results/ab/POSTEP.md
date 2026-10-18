# Etap 8 — dziennik pomiarów i postępu

Plik prowadzony na bieżąco w trakcie etapu 8 (optymalizacja wersji sekwencyjnej): każdy krok, jego pliki wyników,
przyspieszenie, zgodność bitowa i obciążenie tła w czasie pomiaru. Opis metodyki i wnioski:
[`docs/etap-8-optymalizacja-sekwencyjna.md`](../../../docs/etap-8-optymalizacja-sekwencyjna.md).

Oznaczenia: `przed` = program sprzed etapu 8 (`bench/baseline/engine_przed_*`), `kN` = program po optymalizacji N
(`bench/baseline/engine_kN_*`; binarki są lokalne, katalog `bench/baseline/` jest w `.gitignore`). Przyspieszenie
= stosunek median czasu głównej miary (B/A < 1 — szybciej). Tło = obciążenie całego CPU przez inne programy
(psutil, 2–3 s próbki, ta sama funkcja co `backgroundLoad` w `run_profile.py`) na początku i na końcu pomiaru.

**Próg tła w tej serii pomiarów: ≤ 20% CPU przy stabilnym obciążeniu** (podobne na początku i końcu pomiaru);
powyżej 25% albo przy dużym skoku pomiar jest powtarzany. Stały składnik tła ~2 procesory logiczne to zapytania
WMI programów działających w tle (np. narzędzi producenta laptopa) — ok. 7% CPU (`docs/etap-5-kolejka-serie-dane.md`, p. 4.2).
**Od sesji 4 (tryb oszczędny, bez turbo): próg ≤ 30%** przy stabilnym tle; powyżej 30% albo przy dużym skoku część
pomiaru jest powtarzana.

## Tabela kroków

| Krok | Stan | Pliki wyników | MSVC (B/A) | GCC (B/A) | Zgodność | Tło [% CPU] | Uwagi |
|---|---|---|---|---|---|---|---|
| 0. Punkt odniesienia | zrobione (sesja 1) | `bench/results/profile_2026-10-17_przed*` | — | — | — | 16,6 → 20,0 | tło powyżej 5% (WMI ~2 procesory, Windows Update, skan antywirusowy); powtórka `_przed2` przy profilu „po” |
| 1. `bench/ab.py`, `bench/compare_results.py` | zrobione (sesja 1) | — | — | — | — | — | w sesji 2: `compare_results.py` zapisuje ścieżki względne; `ab.py --from-raw` (tabela z podzbioru programów istniejącego pomiaru) |
| k1. MC bez skoku warunkowego, jedno przejście po sąsiadach, stała część hasha przed pętlą | zrobione (sesja 1: MC; sesja 2: CA) | `ab_k1_mc_msvc.md`, `ab_k1_mc_gcc.md`, `ab_k1_ca_msvc.md`, `ab_k1_ca_gcc.md`, `zgodnosc_k1.md` | mcSim ×0,25–0,52; CA ×0,98–1,00 (bez zmian) | mcSim ×0,44–0,82; CA: patrz `ab_k1_ca_gcc.md` | 15/15 configów, MSVC i GCC | MC: MSVC 13 → 14, GCC 14 → 14 (sesja 1); CA: z pomiaru k2 | CA z pomiaru przed / k1 / k2 (`ab.py --from-raw`) |
| k2. Ramka tylko w osiach używanych przez sąsiedztwo | przyjęte (MSVC 3D CA wolniejsze — patrz uwagi) | `ab_k2_msvc.md`, `ab_k2_gcc.md`, `zgodnosc_k2.md` | classic 2D ×0,56–0,62, lawa 2D ×0,82, MC ×0,98–1,04 (szum); **CA 3D ×1,10–1,12** (lawa, classic Moore) | CA 3D ×0,90–0,93 (lawa), classic 3D ×0,91–0,97, classic 2D ×0,58–0,63, lawa 2D ×0,81, MC ×0,99–1,08 względem k1 (szum, duży rozrzut) | 15/15 configów, MSVC i GCC; A/B bitowo zgodne | MSVC 16 → 14; GCC 16 → 9 | MSVC: CA 3D wolniejsze o 10–12% przy tym samym automacie (zmienił się tylko wzór indeksu `base_ + x + sx·(y + sy·z)` i pętle ramki) — arytmetyka indeksu / układ kodu MSVC (etap 6, p. 7); k3 usuwa indeks z gorących pętli, sprawdzić k3/przed. GCC: bez straty w 3D |
| k3. Przesunięcia liniowe sąsiadów (CA) | przyjęte (sesja 2: kod i binarki; sesja 3: zgodność, A/B) | `ab_k3_msvc.md`, `ab_k3_gcc.md` (części `_ca_lava`, `_ca_classic`, `_mc`), `zgodnosc_k3.md` | k3/k2: lawa 3D ×0,88–0,91, lawa 2D ×0,91, classic ×0,52–0,57, MC ×1,00–1,04 (bez zmian w MC); k3/przed: lawa 3D ×0,97–1,00 (strata k2 odrobiona), lawa 2D ×0,73, classic ×0,31–0,57 | k3/k2: lawa 3D ×0,86–0,88, lawa 2D ×0,79, classic ×0,45–0,57, MC ×0,95–1,02; k3/przed: lawa 3D ×0,75–0,80, lawa 2D ×0,64, classic ×0,28–0,55 | 15/15 configów, MSVC i GCC; A/B bitowo zgodne | MSVC 15 → 15, 14 → 14, 18 → 14; GCC 15 → 19, 21 → 20, 20 → 20 | pomiar w trzech częściach po grupach (limit 10 min na polecenie, bez pomiarów w tle), tabela scalona `ab.py --from-raw a,b,c` |
| k4. Automat frontalny (`ca.sweep: front` domyślnie, `full` = wersja referencyjna) | przyjęte (sesja 2: większość kodu; sesja 3: dokończenie, build, zgodność, A/B) | `ab_k4_msvc.md`, `ab_k4_gcc.md` (części `_ca_lava`, `_ca_classic`, `_mc`), `ab_k4_*_front_full.md`, `zgodnosc_k4.md` | k4/k3: lawa 3D ×0,003–0,028, lawa 2D ×0,06, classic ×0,11–0,26, MC ×0,99–1,01; k4/przed: `etna_real` 13 085 → 39 ms (×0,003), classic 1000² ×0,03–0,05, 300³ ×0,11; front/full w tym samym programie: lawa ×0,004–0,07, classic ×0,10–0,28 | k4/k3: lawa 3D ×0,003–0,035, lawa 2D ×0,09, classic ×0,12–0,35, MC ×0,98–1,04; k4/przed: `etna_real` 11 951 → 35 ms (×0,003), classic 1000² ×0,04–0,05, 300³ ×0,13 | 15/15 configów w trybach `front` i `full`, MSVC i GCC; A/B bitowo zgodne | MSVC 19 → 16, 16 → 19, 21 → 24; GCC 16 → 20, 17 → 14, 23 → 20 | MSVC: `k4_full` szybsze od k3 w lawie 3D o ~22% przy tej samej pętli pełnego przebiegu (GCC: bez różnicy) — układ kodu MSVC (etap 6, p. 7); domyślny jest front |
| k5. Tańsze statystyki MC (etykiety ziaren, energia całkowita) | przyjęte (sesja 3: kod, MSVC; sesja 4: GCC, zgodność, A/B — bez turbo) | `ab_k5_msvc.md`, `ab_k5_gcc.md` (części `_mc_3d_100`, `_mc_reszta`), `ab_k5_*_ca.md` (k4/k5), `zgodnosc_k5.md` | k5/k4: mcStats ×0,46–0,74, total MC ×0,82–1,00, mcSim ×0,98–1,02 (bez zmian); CA ×0,98–1,01 (bez zmian); k5/przed mcStats ×0,31–0,60 | k5/k4: mcStats ×0,53–0,87, total MC ×0,87–1,01, mcSim ×0,99–1,02; CA ×0,98–1,02; k5/przed mcStats ×0,50–0,83 | 15/15 configów, MSVC i GCC; A/B bitowo zgodne | MSVC 20 → 16, 28 → 20, 23 → 22; GCC 19 → 17, 20 → 18, 18 → 14 | największy zysk w 3D Moore (ziarna: pomijanie sąsiadów wspólnych z x+1); 2D VN — tylko szybka ścieżka wnętrza |
| k6. Mniejsze typy i mniej kopiowania | pominięte (sesja 4, ograniczony czas pomiarów) | — | — | — | — | — | opis w dokumencie etapu („Dalsze możliwości”); k4 usunęło już bufor `next_` (jeden bufor siatki CA) |
| k7. Zapis `ca_result.txt` / `mc_result.txt` (bufor, własne formatowanie liczb, binarnie z jawnym końcem wiersza) + w GCC `-falign-functions=64` | przyjęte (sesja 4, bez turbo) | `ab_k7_msvc.md`, `ab_k7_gcc.md` (części `_ca`, `_mc`), `ab_k7a_gcc.md` (części `_ca`, `_mc`), `zgodnosc_k7.md`, `zgodnosc_k7a_gcc.md` | k7/k5: save ×0,27 (txt + bin), mcSave ×0,33, total ×0,48–0,80 w przypadkach z txt; caSim, mcSim bez zmian; przypadki tylko z bin bez zmian | k7/k5: save ×0,18–0,23, mcSave ×0,31–0,32; k7 bez wyrównania: caSim ×1,03–1,25 (układ kodu, kod automatu identyczny); k7a (z wyrównaniem, domyślne) / k5: caSim ×0,99–1,03, MC ×0,98–1,02 | 15/15 configów (txt bajt w bajt), MSVC i GCC; k7a GCC 15/15; A/B bitowo zgodne | MSVC 21 → 20, 20 → 20; GCC 21 → 18, 19 → 17, k7a 22 → 30, 19 → 17 | binarki `engine_k7_*`, `engine_k7a_gcc` (= domyślny build GCC po zmianie) |
| Profil `_przed2` / `_po` (skrócony) | zrobione (sesja 4, bez turbo) | `bench/results/profile_2026-10-17_przed2*`, `_po*` | po/przed2: `etna_real` total ×0,005, classic ×0,06–0,14, MC ×0,50–0,58 | `etna_real` ×0,006, classic ×0,06–0,14, MC ×0,70 | — | przed2 25 → 19, 23 → 19, 22 → 24; po 17 → 18 | 9 przypadków, 3 powtórzenia, MSVC + GCC |
| Wykresy, profil gorących miejsc, testy końcowe, dokumentacja | zrobione (sesja 4) | `docs/img/etap8_*.png`, `bench/profiles/etap8_gprof_*`, `docs/etap-8-optymalizacja-sekwencyjna.md` | — | — | ctest 12/12 (Release obu, Debug MSVC), pytest 100/100 | — | GCC Debug pominięty (tryb oszczędny); eksport do folderu tymczasowego: kontrola słownictwa 0 trafień |
| k6, warianty algorytmiczne MC | pominięte (ograniczony czas pomiarów) | — | — | — | — | — | opis pomysłów i spodziewanego efektu w dokumencie etapu, punkt 6 |
| k8. Presety kompilatora (`msvc-release-avx2`, `gcc-release-native`) | zrobione, **bez zysku** (presety zostają jako opcja, domyślne bez zmian) | `ab_k8_msvc.md`, `ab_k8_gcc.md` (7 przypadków), `zgodnosc_k8.md` | avx2/k7: ×0,98–1,05 | native/k7a: ×0,99–1,07 | 15/15 configów, MSVC i GCC (także `-march=native`); A/B bitowo zgodne | MSVC 18 → 16; GCC 13 → 9 | gorące pętle ograniczone pamięcią i skokami, nie arytmetyką — szersze wektory nic nie dają |

## Dziennik

### Sesja 1 (przerwana w trakcie k2)

- Profil odniesienia `profile_2026-10-17_przed` (20,7 min): tło 16,6% na początku, 20,0% na końcu.
- k1: A/B tylko przypadki MC (MSVC 3,6 min, tło 13 → 14%; GCC 2,8 min, tło 14 → 14%); zgodność 15/15 (`zgodnosc_k1.md`).

### Sesja 2 (17.10.2026, od ok. 10:45)

- Weryfikacja stanu: `git diff` = k1 + częściowe k2 zgodnie z opisem; brakowało tylko opisu modelu pamięci
  (`MemoryModel` sumuje rozmiary z `VectorStorage::bytes()` / `PottsMC::bytes()`, które już liczą ramkę z `framedCells()`;
  test 2D był dopisany w `test_profile.cpp`). Przejrzane miejsca zakładające ramkę we wszystkich osiach: `Boundary::apply`,
  `PottsMC::fillFrame/syncFrame`, `LavaCA` (2D lawy: `horizontal_` bez osi y przy `ny = 1`, sąsiedztwa 2D bez trzeciej osi),
  zapis wyników (`toMicrostructure` — tylko wnętrze), GUI/eksport (czytają pliki bez ramki) — bez dalszych zmian.
- Build: oba kompilatory kilka razy przerwały kompilację losowym błędem wewnętrznym (MSVC C1001 / kod -1073741819, GCC
  „internal compiler error: Segmentation fault”) w różnych miejscach i plikach; ponowienie bez zmian w kodzie przechodzi.
  Wygląda na chwilową niestabilność systemu, nie na problem z kodem (te same pliki kompilowane ręcznie 3/3 bez błędu).
- ctest MSVC 12/12, GCC 12/12. Zgodność k2 (`zgodnosc_k2.md`, 4,4 min): 15/15 configów, `przed` = `k2` = `przed_gcc` = `k2_gcc`.
- Tło przed A/B k2: 19–24% (stałe WMI ~2 procesory + skan antywirusowy i indeksowanie plików po buildach).
- A/B k2 MSVC (14,8 min, tło 16 → 14%) i GCC (13,2 min, zakończony 12:12, tło 16 → 9%) — wyniki w tabeli kroków.
- k3 (przesunięcia liniowe w CA): zbudowane MSVC i GCC Release (11:57–11:58), ctest MSVC i GCC zielony, binarki
  `engine_k3_msvc.exe`, `engine_k3_gcc`. Zaczęte k4 (automat frontalny) — sesja zakończona awarią komputera
  ok. 12:13 (nie błąd programu).

### Sesja 3 (17.10.2026, od ok. 19:00)

Stan zastany po weryfikacji (`git diff`, czasy modyfikacji plików, logi ctest):

- `git diff` względem ostatniego commitu (stan „przed”) = k1 + k2 + k3 + częściowe k4. Pliki k4 (zmienione 11:59–12:01):
  `engine/src/ca/LavaCA.hpp` (tryb `front`: listy per warstwa, `initFront`, `frontDescent`, `frontCandidates`,
  `frontRules`, `frontApply`, ścieżka `stepTimed`), `CaRules.hpp` (`CaParams::frontSweep`), `engine/src/io/Config.cpp/.hpp`
  (`ca.sweep: front|full`, domyślnie `front`), `engine/src/app/Simulation.cpp` (blok pamięci `caFront`),
  `engine/src/core/Boundary.hpp` (`syncCell`), `engine/tests/test_front.cpp` (nowy), `engine/tests/test_profile.cpp`,
  `engine/CMakeLists.txt`, `gui/static/js/form.js` (`ENUMS`/`GROUPS`/`SCHEMA` dla `ca.sweep`). Kod k4 nie był budowany.
- k3: `build/Release/engine.exe` i `build-gcc-release/bin/engine` (11:57–11:58) są bajtowo równe `engine_k3_*`;
  ctest z tych buildów: MSVC 96/96 przypadków doctest, GCC 95/95, wszystkie testy ctest zielone. Zmiana k3 jest
  w `Storage.hpp` (typ `Pos`, `linear`, `shifted`, `nextX`) i `LavaCA.hpp` (`NbStep`, pętle po pozycjach); MC
  używał przesunięć liniowych już wcześniej (`PottsMC` — bez zmian w k3).
- Brakowało: `zgodnosc_k3.md`, `ab_k3_*`, wpisu k3; uzupełnienie kolumny GCC dla k2 (zrobione wyżej z `ab_k2_gcc.md`).
- Śmieciowy folder `C:/Users/.../Temp/b` w katalogu projektu (wynik przebiegu WSL z sesji 1, 08:22, ścieżka Windows
  potraktowana jako względna) — do usunięcia (poza repozytorium).

Zasady bezpieczeństwa w tej sesji: jedna ciężka rzecz naraz, buildy `--parallel 6` / `-j 6`, Debug tylko raz na końcu,
żadnych buildów i pomiarów w tle; przed każdym długim krokiem linia „w toku” poniżej.

Błędy wewnętrzne kompilatora w sesji 3: **3** (19:52 MSVC — niepotwierdzony, komunikat utracony; 19:55 MSVC CL.exe
0xC0000409 przy `engine_tests`; 20:38 GCC ICE Segmentation fault przy `McStage.cpp`) → sesja przerwana (szczegóły niżej).

- 19:00–19:04 zgodność k3 (`compare_results.py`, binarki `przed`/`k3` MSVC i GCC, 4,1 min): 15/15 configów,
  `przed` = `k3` = `przed_gcc` = `k3_gcc` → `zgodnosc_k3.md`.
- Tło przed A/B k3: 14–15% CPU (WmiPrvSE ~2 procesory — zapytania WMI narzędzi producenta laptopa, indeksowanie
  plików, okno edytora).
- w toku: A/B k3 MSVC, część ca_lava (przed, k2, k3), start 19:15, polecenie: `python bench/ab.py --bin przed=bench/baseline/engine_przed_msvc.exe --bin k2=bench/baseline/engine_k2_msvc.exe --bin k3=bench/baseline/engine_k3_msvc.exe --groups ca_lava --name ab_k3_msvc_ca_lava`
  - ca_lava gotowe (19:19, 4,1 min). W toku: część ca_classic, start 19:19, to samo polecenie z `--groups ca_classic --name ab_k3_msvc_ca_classic`
  - ca_classic gotowe (19:25, 5,3 min). W toku: część mc, start 19:25, `--groups mc --name ab_k3_msvc_mc`
  - mc gotowe (19:30, 5,0 min); scalona tabela `ab_k3_msvc.md` (tło 15 → 15%, 14 → 14%, 18 → 14%). W toku: A/B k3 GCC, część ca_lava, start 19:30, polecenie: `python bench/ab.py --wsl --bin przed=bench/baseline/engine_przed_gcc --bin k2=bench/baseline/engine_k2_gcc --bin k3=bench/baseline/engine_k3_gcc --groups ca_lava --name ab_k3_gcc_ca_lava`
  - GCC ca_lava gotowe (19:34, 3,2 min). W toku: GCC część ca_classic, start 19:34, `--groups ca_classic --name ab_k3_gcc_ca_classic`
  - 19:38: część GCC ca_classic przerwana bez wyniku (maszyna WSL wyłączona w trakcie, /tmp wyczyszczony; brak błędów w dzienniku System). Powtórka, start 19:38
  - GCC ca_classic gotowe (19:43, 5,0 min). W toku: GCC część mc, start 19:43, `--groups mc --name ab_k3_gcc_mc`
  - GCC mc gotowe (19:48, 4,2 min); scalona tabela `ab_k3_gcc.md`. WSL zamknięty (`wsl --shutdown`).
- **k3 przyjęte.** Co zmieniono (sesja 2, opis z kodu): w CA dostęp do sąsiada przez pozycję — `Storage::Pos`
  (VectorStorage: indeks w tablicy z ramką; MatrixStorage: współrzędne), `linear(o)` = dx + sx·(dy + sy·dz) liczone raz
  w konstruktorze automatu dla każdego przesunięcia każdego wariantu (`LavaCA::nbSteps_`, `side_`), `shifted(p, o, lin)`
  = p + lin, `nextX(p)` = p + 1. Przeliczone na przesunięcia: pętle `updateLava`, `updateClassic`, `computeDescent`
  (pozycja przesuwana w osi x zamiast `index(x, y, z)` co komórkę), odczyt typu sąsiada w `gatherLavaCandidates`
  (współrzędne liczone dopiero, gdy sąsiad jest lawą — rzadko), głosowanie classic, `descent` (D(n)). Wybór wariantu
  sąsiedztwa losowego ze stałej części hasha liczonej raz na krok (`hashPrefix` + `variantFromPrefix`, jak w MC od k1).
  MC: bez zmian w k3 (przesunięcia liniowe w `PottsMC` od etapu 2). MSVC: k3 odrabia stratę k2 w CA 3D
  (k3/przed lawa 3D ×0,97–1,00) — strata k2 wynikała z arytmetyki indeksu w gorącej pętli, której k3 już nie ma.
- Uwaga z pomiaru: pierwsze uruchomienie części GCC ca_classic (19:34–19:38) zakończyło się bez wyniku — maszyna
  wirtualna WSL została wyłączona w trakcie (po ponownym starcie pusty `/tmp`, w dzienniku `System` Windows brak błędów
  i ostrzeżeń). Powtórka bez zmian przeszła. Przyczyna nieznana; to nie jest błąd kompilatora — licznik ICE bez zmian.
- k4: uzupełnienia kodu (licznik nowych komórek lokalny w `frontRules`, `MatrixStorage::bytes()` = 0 dla pustego bufora, pamięć migawki z `state().bytes()`, opis w `CaRules.hpp`, test reguły końca „krok bez zmian”). W toku: build MSVC Release k4, start 19:51, polecenie: `cmake --build --preset msvc-release --parallel 6`
  - 19:51–19:52 build MSVC Release k4: pierwsze wywołanie zakończone kodem 1 po zbudowaniu biblioteki
    `volcano_engine.lib` (dalsze cele — `engine.exe`, `engine_tests.exe` — niezbudowane); komunikat utracony (filtr
    `grep` uznał wyjście MSBuild w stronie kodowej Windows za binarne). Ponowienie bez zmian w kodzie przeszło bez
    błędów i ostrzeżeń. **Liczone ostrożnie jako możliwy błąd wewnętrzny kompilatora nr 1** (niepotwierdzony; MSVC,
    cele `engine`/`engine_tests`). Od teraz pełny log każdego builda do pliku.
  - W toku: build GCC Release k4 + ctest, start 19:53, polecenie: `wsl -e bash -lc "cmake --build --preset gcc-release -j 6 && ctest --preset gcc-release"`
  - GCC (19:58): build i ctest 12/12 zielone, ale ostrzeżenie -Wmaybe-uninitialized w `Boundary::syncCell` (`alt`) — poprawione (`= {}`). W toku: ponowny build MSVC Release k4, start 19:55
  - 19:54–19:55 ponowny build MSVC Release: biblioteka i `engine.exe` zbudowane, `engine_tests` — **CL.exe zakończony
    kodem -1073740791 (0xC0000409)** w fazie generowania kodu (pliki test_boundary, test_ca, test_front, test_mc,
    test_profile, test_replay w jednym procesie CL). **Błąd wewnętrzny kompilatora nr 2** (MSVC; nr 1 niepotwierdzony,
    19:52). Ponowienie raz bez zmian.
  - 19:56 ponowienie MSVC przeszło (bez ostrzeżeń); ctest MSVC 12/12, doctest 107/107. W toku: build GCC Release k4 + ctest, start 19:56
  - 19:58 GCC: build bez ostrzeżeń, ctest 12/12, doctest 106/106. Binarki `engine_k4_msvc.exe`, `engine_k4_gcc`. W toku: zgodność k4 (front i full, MSVC i GCC), start 19:57, polecenie: `python bench/compare_results.py --bin przed=bench/baseline/engine_przed_msvc.exe --bin k4=bench/baseline/engine_k4_msvc.exe --bin k4_full=bench/baseline/engine_k4_msvc.exe --bin przed_gcc=wsl:bench/baseline/engine_przed_gcc --bin k4_gcc=wsl:bench/baseline/engine_k4_gcc --bin k4_gcc_full=wsl:bench/baseline/engine_k4_gcc --args "k4_full=--set ca.sweep=full" --args "k4_gcc_full=--set ca.sweep=full" --name zgodnosc_k4`
  - 20:00–20:04 zgodność k4 (4,0 min): 15/15 configów, `przed` = `k4` = `k4_full` = `przed_gcc` = `k4_gcc` = `k4_gcc_full` → `zgodnosc_k4.md`.
  - W toku: A/B k4 MSVC, część ca_lava (przed, k3, k4_full, k4), start 20:02, polecenie: `python bench/ab.py --bin przed=bench/baseline/engine_przed_msvc.exe --bin k3=bench/baseline/engine_k3_msvc.exe --bin k4_full=bench/baseline/engine_k4_msvc.exe --bin k4=bench/baseline/engine_k4_msvc.exe --args "k4_full=--set ca.sweep=full" --groups ca_lava --name ab_k4_msvc_ca_lava`
  - ca_lava gotowe (20:06, 3,8 min). W toku: MSVC część ca_classic, start 20:06, `--groups ca_classic --name ab_k4_msvc_ca_classic`
  - ca_classic gotowe (20:11, 5,0 min). W toku: MSVC część mc (przed, k3, k4), start 20:11, `--groups mc --name ab_k4_msvc_mc`
  - mc gotowe (20:17, 5,5 min); scalone `ab_k4_msvc.md` (przed/k3/k4) i `ab_k4_msvc_front_full.md` (k4 full vs front). Tło MSVC: 19 → 16, 16 → 19, 21 → 24%. W toku: A/B k4 GCC, część ca_lava, start 20:17, polecenie: `python bench/ab.py --wsl --bin przed=bench/baseline/engine_przed_gcc --bin k3=bench/baseline/engine_k3_gcc --bin k4_full=bench/baseline/engine_k4_gcc --bin k4=bench/baseline/engine_k4_gcc --args "k4_full=--set ca.sweep=full" --groups ca_lava --name ab_k4_gcc_ca_lava`
  - GCC ca_lava gotowe (20:21, 3,1 min). W toku: GCC część ca_classic, start 20:21, `--groups ca_classic --name ab_k4_gcc_ca_classic`
  - GCC ca_classic gotowe (20:26, 4,5 min). W toku: GCC część mc (przed, k3, k4), start 20:26, `--groups mc --name ab_k4_gcc_mc`
  - GCC mc gotowe (20:31, 4,3 min); scalone `ab_k4_gcc.md`, `ab_k4_gcc_front_full.md`. WSL zamknięty.
- **k4 przyjęte.** Struktura frontu (`LavaCA.hpp`, sekcja „automat frontalny”):
  - **Listy per warstwa** (`FrontLayer` dla każdej wartości osi z; w płaszczyźnie x–y — osi y): `src` (lava: wszystkie
    komórki LAVA; classic: ziarna dodane w poprzednim kroku), `cand` (komórki AIR do sprawdzenia, bez powtórzeń dzięki
    znacznikom `mark_` 1 B/komórkę), `nextSrc`, `changes` (nowy stan zmienionych komórek). Krok: D(n) tylko dla lawy
    (`frontDescent`) → kandydaci = komórki AIR c, dla których jakieś `src` L = c + o (o z sumy WSZYSTKICH wariantów
    sąsiedztwa, więc też pentagonal/hexagonal i wypełnianie zagłębień z lawy pod c) → reguły (te same funkcje co pełny
    przebieg: `gatherLavaCandidates`, głosowanie, stygnięcie) czytają tylko `cur_`, piszą listy warstwy → zmiany do
    `cur_` po regułach wszystkich warstw (`frontApply`) + kopie w ramce periodycznej (`Boundary::syncCell`). Jeden bufor
    siatki (bez `next_`): pamięć siatki CA o połowę mniejsza.
  - **Dlaczego bitowo ten sam wynik:** zmienić się może tylko komórka LAVA i AIR z lawą/ziarnem w sąsiedztwie dowolnego
    wariantu (opis w `CaRules.hpp`); każda taka komórka jest przetwarzana tą samą funkcją reguł na tym samym stanie
    `cur_` z początku kroku (losowość `hashRand(seed, krok, globalIndex)` nie zależy od kolejności), komórki spoza frontu
    w pełnym przebiegu i tak zostają bez zmian. Liczniki: `active` = lawa, która została lawą + nowe (classic: wszystkie
    ziarna), `air` = AIR przed krokiem − nowe, `changed` z tych samych warunków co w `updateLava/updateClassic`; reguła
    „krok bez zmian” działa bez zmian (test). Classic przy sąsiedztwie losowym: kandydaci, którzy się nie zmienili, zostają
    na liście (wariant w następnym kroku może sięgnąć do ziarna). Ramka: wypełniona raz, potem tylko kopie zmienionych
    komórek przy ścianach periodycznych — to samo, co dałoby ponowne `apply()`.
  - **Testy** (`test_front.cpp`, 11 przypadków): lawa 2D/3D, classic 2D (x–y, x–z, y–z) i 3D, wszystkie sąsiedztwa,
    brzeg periodyczny i absorbujący (także lawa przechodząca przez brzeg), ponding wł./wył., kratery losowe, limit kroków,
    reguła „krok bez zmian” (i jej brak przy sąsiedztwie losowym), obie reprezentacje siatki, ścieżka `--timing-detail`,
    jeden bufor; porównanie wyniku bitowo + liczba kroków + powód końca + historia liczników.
  - **Zrównoleglenie (etap 9):** pętle po warstwach w `frontCandidates`, `frontRules`, `frontApply` (i `frontDescent`) są
    niezależne: kandydaci warstwy k powstają tylko z `src` warstw k−1..k+1 (grupy przesunięć `rev_[d]`) i trafiają do
    list i znaczników warstwy k; reguły czytają tylko `cur_` (stan z początku kroku), piszą listy swojej warstwy, sumy
    (`stay`, `changed`, `born`) są lokalne — redukcja; zmiany warstwy dotyczą komórek tej warstwy (kopie w ramce — różne
    komórki ramki). OpenMP: `parallel for schedule(dynamic)` po warstwach (front jest nierównomierny), bariera między
    fazami. MPI: podział osi warstw na pasy, wymiana `src`/zmian warstw brzegowych (ghost layers).
- k5 (tańsze statystyki MC): `Grains::label` — szybka ścieżka wnętrza (przesunięcia liniowe, reprezentant raz na komórkę), `PottsMC::totalEnergy` — pary „do przodu” przy sąsiedztwie symetrycznym; testy BFS i energii w `test_mc.cpp`. W toku: build MSVC Release k5, start 20:35
  - k5 wersja 1 (20:36): build MSVC bez błędów, ctest 12/12, doctest 109/109, wynik identyczny, ale energia wolniejsza
    (warunek `&&` — skoki) i ziarna tylko −25% → poprawki (energia bez skoków, pomijanie sąsiadów wspólnych z x+1).
  - 20:37–20:38 build MSVC k5 (wersja 2) bez ostrzeżeń, ctest 12/12, doctest 109/109; `mc_full_3d` 50³/100 MCS
    (pojedyncze przebiegi, nie A/B): mcStats 229 → 120–137 ms (ziarna 175 → 96–116, energia 48 → 16–18), `mc_result.bin`
    i `mc_stats.csv` identyczne z k4. Binarka `bench/baseline/engine_k5_msvc.exe`.
  - 20:38 build GCC Release k5: **„internal compiler error: Segmentation fault”** w `cc1plus` przy
    `engine/src/app/McStage.cpp` (konstruktor `std::basic_string` z `<bits/basic_string.h>`; kod `McStage.cpp` w k5 bez
    zmian — przekompilowany tylko przez zmianę komentarza w `Grains.hpp`). **Błąd wewnętrzny kompilatora nr 3 w tej
    sesji** (nr 1 MSVC 19:52 niepotwierdzony, nr 2 MSVC 19:55 0xC0000409, nr 3 GCC 20:38) → zgodnie z zasadą
    bezpieczeństwa **sesja 3 przerwana** (sygnał niestabilności sprzętu). Bez ponowienia. Błędną kopię `engine_k5_gcc`
    (skopiowana stara binarka k4 po nieudanym buildzie) usunięto; WSL zamknięty.

### Stan na koniec sesji 3 (przerwanej 20:38) — od czego zacząć następną

- **Przyjęte i zmierzone:** k1, k2, k3, k4 (zgodność 15/15 configów MSVC i GCC; A/B pełny zestaw; binarki
  `engine_k1..k4_*`). `zgodnosc_k3.md`, `ab_k3_*`, `zgodnosc_k4.md` (tryby `front` i `full`), `ab_k4_*`.
- **k5 w kodzie, niezmierzone:** `engine/src/mc/Grains.cpp/.hpp` (szybka ścieżka wnętrza + pomijanie sąsiadów wspólnych
  z x+1), `engine/src/mc/PottsMC.cpp` (`totalEnergy` — pary „do przodu”, bez skoków), `engine/tests/test_mc.cpp` (dwa nowe
  testy: etykiety vs BFS, energia vs suma energii komórek). MSVC Release zbudowany i zielony (`engine_k5_msvc.exe`).
  **Brakuje:** build GCC Release + ctest, `engine_k5_gcc`, `zgodnosc_k5.md` (vs przed), A/B przed / k4 / k5 (MSVC, GCC),
  wpis w tabeli kroków. Jeśli A/B nie pokaże zysku > 3% w przypadkach MC — cofnąć zmiany k5 w trzech plikach wyżej.
- **Do zrobienia potem:** k6–k8 (wg pliku 10 p. 2 i `10b` p. 4), warianty MC, profil `_przed2` + `_po`, wykresy, profil
  gorących miejsc, buildy Debug (raz, na końcu), `pytest gui\tests`, dokumentacja `docs/etap-8-optymalizacja-sekwencyjna.md`
  i aktualizacje, eksport do folderu tymczasowego z kontrolą słownictwa.
- Narzędzie: `bench/ab.py --from-raw a_raw.csv,b_raw.csv,c_raw.csv --labels …` scala pomiar podzielony na części
  (polecenie narzędzia wykonawczego ma limit 10 min, a pomiarów nie wolno puszczać w tle).
- Śmieciowy folder `C:/Users/.../Temp/b` w katalogu projektu (z sesji 1) — nadal do usunięcia ręcznie (poza repozytorium).

### Sesja 4 (17.10.2026, od ok. 21:30) — tryb oszczędny

Od tej sesji do końca projektu komputer nie pracuje z pełną mocą (laptop przy 100% obciążeniu wszystkich rdzeni się
restartował, a kompilatory dostawały losowe błędy wewnętrzne):

- **Procesor bez turbo.** Maksymalny stan procesora 99% był ustawiony tylko dla klasy wydajności 0 (rdzenie E);
  procesor hybrydowy ma osobne ustawienie dla klasy 1 (rdzenie P, `PROCTHROTTLEMAX1`), które miało 100% — pod
  obciążeniem jednego rdzenia P licznik „% wydajności procesora” pokazywał 196–198% taktowania bazowego (ok. 4,3 GHz),
  choć `psutil.cpu_freq()` podaje stałe 2200 MHz (bazowe; ta funkcja na Windows nie widzi turbo). Ustawione 99% także
  dla klasy 1 (zasilanie sieciowe i bateria; cofnięcie: `powercfg /setacvalueindex SCHEME_CURRENT SUB_PROCESSOR
  PROCTHROTTLEMAX1 100`). Po zmianie, ten sam test (pętla na procesorze logicznym 2, 9 s): 97,0% taktowania bazowego
  (~2,13 GHz) we wszystkich próbkach, `psutil.cpu_freq()` 2200 MHz, pętla 2,3× wolniejsza niż z turbo — **turbo wyłączone**.
- **WSL: 8 procesorów, 8 GB.** Pliku `.wslconfig` nie było (WSL widział 32 procesory, 15 GB) — utworzony z treścią
  `[wsl2] processors=8 memory=8GB`, `wsl --shutdown`. Teraz `nproc` = 8, `free -g`: 7 GB pamięci (8 GB po zaokrągleniu
  w dół), 2 GB wymiany.
- **Buildy:** MSVC `--parallel 4`, GCC `-j 4`; jedna ciężka operacja naraz (build albo pomiar).
- **Pomiary:** jednowątkowe, przypięte do procesora logicznego 2 (rdzeń P); próg tła 30% (wyżej). Komputer może być
  w tym czasie używany lekko (przeglądarka, wideo).
- Bez turbo czasy bezwzględne są ok. 2× dłuższe niż w k1–k4, więc porównania A/B w tej sesji obejmują zawsze program
  odniesienia mierzony w tych samych warunkach (`przed`, `k4`), a nie tabele z wcześniejszych sesji.
- Tło na start (21:42): 23% CPU (zapytania WMI narzędzi producenta laptopa ~2,3 procesora logicznego, usługi systemu,
  przeglądarka).

Porządek: folder `C:` w katalogu projektu (w Windows widoczny jako `C`) zawiera tylko wynik silnika
(`Users/…/AppData/Local/Temp/b/`: `ca_result.bin/.txt`, `stats.json`, `times.json`, `config_used.json` z
`configs/test_2d.json`, 08:22 w sesji 1). Przyczyna: polecenie w Git Bash `wsl -e …/engine … --out /tmp/b` — Git Bash
(MSYS) zamienia ścieżki w stylu POSIX w argumentach programów Windows (`wsl.exe`) na ścieżki Windows (`/tmp` →
`C:/Users/…/Temp`), a w WSL taka ścieżka jest względna. Skrypty w `bench/` (`ab.py`, `compare_results.py`,
`run_profile.py`) zamieniają ścieżki funkcją `wsl_path` i tego błędu nie mają; zasada dopisana do lokalnych konwencji
pracy (w Git Bash przed `wsl` z argumentem `/…` ustawić `MSYS_NO_PATHCONV=1` albo uruchamiać z PowerShell). Samo
usunięcie folderu zostaje do zrobienia ręcznie (narzędzie wykonawcze sesji nie pozwoliło usunąć folderu; folder jest
poza repozytorium — nazwa `C:` nie jest śledzona).

Błędy wewnętrzne kompilatora w sesji 4: 0.

- k5: kod bez zmian od sesji 3 (`build/Release/engine.exe` = `engine_k5_msvc.exe`, bajtowo). W toku: build GCC
  Release k5 + ctest, start 21:44, polecenie: `wsl -e bash -lc "cmake --build --preset gcc-release -j 4 && ctest --preset gcc-release"`
  - 21:44–21:45 build GCC Release k5 (1,1 min) bez błędów i ostrzeżeń, ctest 12/12, doctest 108/108; binarka
    `bench/baseline/engine_k5_gcc`.
  - W toku: zgodność k5 (część 1: configi CA), start 21:46, polecenie: `python bench/compare_results.py --bin przed=bench/baseline/engine_przed_msvc.exe --bin k5=bench/baseline/engine_k5_msvc.exe --bin przed_gcc=wsl:bench/baseline/engine_przed_gcc --bin k5_gcc=wsl:bench/baseline/engine_k5_gcc --configs classic_ref,etna_3d,etna_real,etna_real_boczna,heightmap_kanion,heightmap_podwojny,wezuwiusz_real --name zgodnosc_k5_cz1`
  - część 1 gotowa (21:46–21:51, 4,1 min): 7/7 zgodne. W toku: część 2 (configi z MC i małe CA), start 21:51, to samo
    polecenie z `--configs heightmap_kaldera,lava_mc_2d,lava_mc_3d,mc_full_2d,mc_full_3d,test_2d,test_3d --name zgodnosc_k5_cz2`
  - część 2 gotowa (21:51–21:52, 0,7 min): 8/8 zgodne. Scalone `zgodnosc_k5.md`: **15/15 configów, `przed` = `k5` =
    `przed_gcc` = `k5_gcc`**.
  - Plan A/B k5 (k5 zmienia tylko statystyki MC): grupa mc — `przed`, `k4`, `k5` w dwóch częściach (`mc_full_3d_100`
    osobno, bo bez turbo trwa ~6,5 min; reszta razem); grupy CA — tylko `k4`, `k5` (kontrola układu kodu; CA względem
    `przed` jest w `ab_k4_*`, łącznie — w profilu `_przed2`/`_po`).
  - W toku: A/B k5 MSVC, część mc_3d_100, start 21:53, polecenie: `python bench/ab.py --bin przed=bench/baseline/engine_przed_msvc.exe --bin k4=bench/baseline/engine_k4_msvc.exe --bin k5=bench/baseline/engine_k5_msvc.exe --cases mc_full_3d_100 --name ab_k5_msvc_mc_3d_100`
  - część mc_3d_100 gotowa (21:53–22:01, 8,1 min; tło 20 → 16%): k5/k4 mcStats ×0,455 (2 316 → 1 053 ms), total
    ×0,960, mcSim ×1,012 (szum); zgodne. W toku: A/B k5 MSVC, część mc (bez 100³), start 22:03, to samo polecenie z
    `--cases mc_full_2d_200,mc_full_2d_1000,mc_full_3d_50,lava_mc_3d --name ab_k5_msvc_mc_reszta`
  - część mc_reszta gotowa (22:03–22:08, 4,6 min): k5/k4 mcStats ×0,488–0,744, total ×0,82–1,00, mcSim ×0,98–1,02;
    zgodne. W toku: A/B k5 MSVC, grupy ca_lava i ca_classic (k4, k5), start 22:08, polecenie: `python bench/ab.py
    --bin k4=bench/baseline/engine_k4_msvc.exe --bin k5=bench/baseline/engine_k5_msvc.exe --groups ca_lava,ca_classic --name ab_k5_msvc_ca`
  - CA gotowe (22:08–22:10, 1,6 min; tło 23 → 22%): k5/k4 caSim ×0,98–1,01, procWall ×0,93–0,99 — bez zmian (układ
    kodu MSVC nie przesunął automatu). Scalone `ab_k5_msvc.md` (mc: przed, k4, k5; tło części: 20 → 16%, 28 → 20%).
  - W toku: A/B k5 GCC, część mc_3d_100, start 22:11, polecenie: `python bench/ab.py --wsl --bin przed=bench/baseline/engine_przed_gcc
    --bin k4=bench/baseline/engine_k4_gcc --bin k5=bench/baseline/engine_k5_gcc --cases mc_full_3d_100 --name ab_k5_gcc_mc_3d_100`
  - część gotowa (22:11–22:18, 6,6 min): k5/k4 mcStats ×0,532 (1 821 → 969 ms), total ×0,952, mcSim ×0,991; zgodne.
    W toku: A/B k5 GCC, część mc (bez 100³), start 22:18, `--cases mc_full_2d_200,mc_full_2d_1000,mc_full_3d_50,lava_mc_3d --name ab_k5_gcc_mc_reszta`
  - część gotowa (22:18–22:22, 3,7 min): k5/k4 mcStats ×0,556–0,866, total ×0,87–1,01, mcSim ×0,99–1,02; zgodne.
    W toku: A/B k5 GCC, grupy CA (k4, k5), start 22:22, `python bench/ab.py --wsl --bin k4=bench/baseline/engine_k4_gcc
    --bin k5=bench/baseline/engine_k5_gcc --groups ca_lava,ca_classic --name ab_k5_gcc_ca`
  - CA gotowe (22:22–22:24, 1,4 min; tło 18 → 14%): k5/k4 caSim ×0,98–1,02 — bez zmian. Scalone `ab_k5_gcc.md`.
- **k5 przyjęte** (zysk > 3% w mcStats wszystkich przypadków MC, MSVC i GCC; mcSim bez zmian, bo k5 nie dotyka
  pętli MC). Co zmieniono: `Grains::label` — dla komórek wnętrza sąsiedzi „do przodu” przez stałe przesunięcie liniowe
  w tablicy bez ramki (bez zawijania współrzędnych i `globalIndex`), reprezentant komórki raz na komórkę, a gdy sąsiad
  x+1 ma tę samą orientację — pominięte przesunięcia wspólne z x+1 (Moore 3D: 8 z 13); `PottsMC::totalEnergy` — przy
  sąsiedztwie symetrycznym tylko pary „do przodu” (pełna suma = 2 × suma „do przodu”, mnożenie przez 0,5 i 2 dokładne),
  bez skoków warunkowych. Testy: etykiety vs BFS, energia vs suma energii komórek (`test_mc.cpp`).
- k7 (zapis `ca_result.txt` / `mc_result.txt`): pomiar k5 przed zmianą (pojedynczy przebieg, classic 1000² VN):
  `ca_result.txt` 303 ms (19,7 MB), `ca_result.bin` 8 ms; `mc_full_2d` 1000²: `mc_result.txt` 138 ms (13,6 MB).
  Zmiana w `engine/src/io/ResultWriter.cpp/.hpp`: temperatura bez `snprintf` (`formatTemp`), bufor dopisywany
  wskaźnikiem, fragment „ y z ” raz na wiersz siatki, plik binarnie z jawnym końcem wiersza (Windows `\r\n` — te same
  bajty co tryb tekstowy). Testy w `test_io.cpp` (formatTemp = printf na ~520 tys. wartości, w tym remisy; plik bajt
  w bajt jak zapis sprzed zmiany). W toku: build MSVC Release k7 + ctest, start 22:27, polecenie:
  `cmake --build --preset msvc-release --parallel 4` + `ctest --preset msvc-release`
  - 22:28 build MSVC k7 (0,6 min) bez błędów i ostrzeżeń, ctest 12/12, doctest 111/111 (`formatTemp` = printf także
    dla remisów — biblioteka C Windows 11 zaokrągla remisy do parzystej). Pojedynczy przebieg (nie A/B): classic 1000²
    `ca_result.txt` 303 → 60 ms, `mc_full_2d` 1000² `mc_result.txt` 138 → 36 ms; pliki identyczne z k5 (`cmp`).
  - W toku: build GCC Release k7 + ctest, start 22:30, polecenie: `wsl -e bash -lc "cmake --build --preset gcc-release -j 4 && ctest --preset gcc-release"`
  - 22:30–22:31 build GCC k7 (1,3 min) bez błędów i ostrzeżeń, ctest 12/12, doctest 110/110. Binarki
    `engine_k7_msvc.exe`, `engine_k7_gcc`. W toku: zgodność k7 (część 1), start 22:32, polecenie: `python bench/compare_results.py
    --bin przed=bench/baseline/engine_przed_msvc.exe --bin k7=bench/baseline/engine_k7_msvc.exe --bin przed_gcc=wsl:bench/baseline/engine_przed_gcc
    --bin k7_gcc=wsl:bench/baseline/engine_k7_gcc --configs <jak w k5, część 1> --name zgodnosc_k7_cz1`
  - zgodność k7 gotowa (22:32–22:37, 4,0 + 0,7 min): **15/15 configów, `przed` = `k7` = `przed_gcc` = `k7_gcc`**
    (pliki txt bajt w bajt na tej samej platformie) → `zgodnosc_k7.md`.
  - W toku: A/B k7 MSVC, grupy CA (k5, k7), start 22:38, polecenie: `python bench/ab.py --bin k5=bench/baseline/engine_k5_msvc.exe
    --bin k7=bench/baseline/engine_k7_msvc.exe --groups ca_lava,ca_classic --name ab_k7_msvc_ca`
  - CA gotowe (22:38–22:40, 1,5 min): save ×0,27 (classic 1000² i 100³ VN — txt + bin), total ×0,48–0,80 w przypadkach
    z plikiem txt; 300³ i `etna_real` (tylko bin) bez zmian; caSim bez zmian. W toku: A/B k7 MSVC, grupa mc (k5, k7),
    start 22:40, `--groups mc --name ab_k7_msvc_mc`
  - mc gotowe (22:40–22:46, 6,3 min): mcSave ×0,33 (1000², 100³ — txt + bin), `lava_mc_3d` total ×0,72; mcSim bez
    zmian. Scalone `ab_k7_msvc.md`. W toku: A/B k7 GCC, grupy CA (k5, k7), start 22:47, `python bench/ab.py --wsl
    --bin k5=bench/baseline/engine_k5_gcc --bin k7=bench/baseline/engine_k7_gcc --groups ca_lava,ca_classic --name ab_k7_gcc_ca`
  - GCC CA gotowe (22:47–22:49, 1,4 min; tło 21 → 18%): save ×0,18–0,23 (txt + bin), total ×0,46–0,77 w przypadkach
    z txt; **ale caSim ×1,04–1,27** (najwięcej classic 100³ Moore), a 300³ (tylko bin) total ×1,05 — przy kodzie automatu
    bez zmian. Sprawdzenie (`nm`, `objdump`): kod maszynowy `frontRules`, `frontDescent`, `stepTimed`,
    `gatherLavaCandidates`, `PottsMC::sweep` w k5 i k7 identyczny (bez adresów), wszystkie funkcje `LavaCA` przesunięte
    o +16 B (np. `frontRules` mod 64: 48 → 0) — **efekt układu kodu GCC**, nie zmiany k7 (jak MSVC w etapie 6, p. 7).
  - W toku: A/B k7 GCC, grupa mc (k5, k7), start 22:49, `--groups mc --name ab_k7_gcc_mc`
  - GCC mc gotowe (22:49–22:55, 6,2 min): mcSave ×0,31–0,32, mcSim ×0,95–1,01; `lava_mc_3d` caSim ×1,22 (ten sam efekt
    układu), total ×0,74.
  - Próba stabilizacji układu kodu GCC: osobny build `build-gcc-align` (`-falign-functions=64` — każda funkcja od
    początku linii 64 B, więc położenie pętli względem linii nie zależy od kodu przed funkcją). W toku: build, start 22:56,
    polecenie: `wsl -e bash -lc "cmake --preset gcc-release -B build-gcc-align -DCMAKE_CXX_FLAGS=-falign-functions=64 && cmake --build build-gcc-align --target engine -j 4"`
  - 22:56–22:57 build (0,7 min) bez błędów i ostrzeżeń; binarka `bench/baseline/engine_k7a_gcc` (wszystkie gorące funkcje
    mod 64 = 0). W toku: A/B GCC CA k5 / k7 / k7a, start 22:58, `python bench/ab.py --wsl --bin k5=bench/baseline/engine_k5_gcc
    --bin k7=bench/baseline/engine_k7_gcc --bin k7a=bench/baseline/engine_k7a_gcc --groups ca_lava,ca_classic --name ab_k7a_gcc_ca`
  - A/B GCC CA gotowe (22:58–23:00, 2,0 min): efekt powtarzalny — k7/k5 caSim ×1,03–1,25 (classic 100³ Moore ×1,25);
    **k7a/k5 caSim ×0,99–1,03** (classic 1000² VN ×1,07 przy rozrzucie 107–261 ms), k7a/k7 ×0,79–0,97; save k7a = k7.
    W toku: A/B GCC mc (bez 100³) k5 / k7 / k7a, start 23:01, `--groups mc --cases mc_full_2d_200,mc_full_2d_1000,mc_full_3d_50,lava_mc_3d --name ab_k7a_gcc_mc`
  - A/B GCC mc gotowe (23:01–23:04, 3,1 min; tło 22 → 30%): k7a/k7 mcSim, mcStats ×0,98–1,02 (bez zmian), `lava_mc_3d`
    caSim ×0,80 (k7a/k5 ×0,99). **Przyjęte:** `-falign-functions=64` w `engine/CMakeLists.txt` dla GCC Release (MSVC
    nie ma odpowiednika dla pojedynczych funkcji; w MSVC k7 nie zmieniło caSim). W toku: przebudowa GCC Release + ctest,
    start 23:05, `wsl -e bash -lc "cmake --preset gcc-release && cmake --build --preset gcc-release -j 4 && ctest --preset gcc-release"`
  - 23:05–23:07 przebudowa GCC Release (1,9 min) bez błędów i ostrzeżeń, ctest 12/12, doctest 110/110; program
    `build-gcc-release/bin/engine` bajtowo identyczny z `engine_k7a_gcc`. W toku: zgodność k7a (GCC, wszystkie configi),
    start 23:08, `python bench/compare_results.py --bin przed_gcc=wsl:bench/baseline/engine_przed_gcc --bin k7a_gcc=wsl:bench/baseline/engine_k7a_gcc --name zgodnosc_k7a_gcc`
  - zgodność k7a GCC gotowa (23:06–23:08, 2,2 min): 15/15 configów `k7a_gcc` = `przed_gcc` → `zgodnosc_k7a_gcc.md`.
    Scalone `ab_k7_gcc.md` (k5, k7) i `ab_k7a_gcc.md` (k5, k7, k7a).
- **k7 przyjęte** (MSVC: k7; GCC: k7 + wyrównanie funkcji = `engine_k7a_gcc`).
- k8 (presety kompilatora): odłożone na koniec sesji (dokumentacja ma pierwszeństwo).
- Profil skrócony `_przed2` / `_po` (wybrane przypadki zestawu A/B, te same miary co `run_profile.py`): `run_profile.py`
  dostał opcję `--cases` (wybór wariantów z planu grup), a grupa `lava` — `etna_real`. Przypadki: `test_3d`, `etna_real`,
  `classic_1000x1000_s100_vn_per`, `classic_1000x1000_s100_moore_per`, `classic_300x300x300_s100_vn_per`,
  `mcfull_1000x1000_vn_mcs100`, `mcfull_100x100x100_moore_mcs100`, `test_3d_detail`, `mcfull_100x100x100_moore_mcs20_detail`;
  3 powtórzenia, MSVC + GCC. `_przed2` w trzech częściach (ta sama nazwa — skrypt dopisuje brakujące przebiegi, tło każdej
  części w `meta.passes`).
  - W toku: profil `profile_2026-10-17_przed2`, część 1 (300³, MC 1000²), start 23:13, polecenie: `python bench/run_profile.py --full --gcc
    --groups classic,mc,lava,big,detail --cases classic_300x300x300_s100_vn_per,mcfull_1000x1000_vn_mcs100 --name profile_2026-10-17_przed2
    --engine bench/baseline/engine_przed_msvc.exe --gcc-engine bench/baseline/engine_przed_gcc`
  - część 1 gotowa (23:12–23:18, 6,5 min). W toku: część 2 (MC 100³ Moore + fazy MC), start 23:19, to samo polecenie z
    `--cases mcfull_100x100x100_moore_mcs100,mcfull_100x100x100_moore_mcs20_detail`
  - część 2 gotowa (23:19–23:24, 4,9 min). W toku: część 3 (lawa, classic 1000², fazy test_3d), start 23:24, to samo
    polecenie z `--cases test_3d,etna_real,classic_1000x1000_s100_vn_per,classic_1000x1000_s100_moore_per,test_3d_detail`
  - część 3 gotowa (23:24–23:28, 4,6 min). **`profile_2026-10-17_przed2` gotowy** (18 wierszy, 54 przebiegi).
  - W toku: profil `profile_2026-10-17_po` (te same przypadki, jedna część), start 23:29, polecenie: `python bench/run_profile.py
    --full --gcc --groups classic,mc,lava,big,detail --cases <wszystkie 9> --name profile_2026-10-17_po
    --engine bench/baseline/engine_k7_msvc.exe --gcc-engine bench/baseline/engine_k7a_gcc` (= obecne buildy Release)
  - **`profile_2026-10-17_po` gotowy** (23:29–23:34, 4, 7 min; tło 17 → 18%). Tło `_przed2`: 25 → 19%, 23 → 19%, 22 → 24%.
    Przed2 → po (mediany, bez turbo): `etna_real` caSim MSVC 32 203 → 86 ms (×0,003), GCC 24 621 → 77 ms; total ×0,005–0,006;
    `test_3d` caSim ×0,027–0,030; classic 1000² caSim ×0,036–0,047, total ×0,06–0,07; 300³ caSim ×0,096–0,099, total ×0,14;
    MC 1000² VN total MSVC ×0,58, GCC ×0,70; MC 100³ Moore total MSVC ×0,50, GCC ×0,70 (mcStats ×0,33 / ×0,48);
    save ×0,19–0,30 (z txt), mcSave ×0,32–0,33.
    `_przed2` (bez turbo) względem pierwszego `_przed` (z turbo, tło 17–20%): ×2,2–2,8 dłużej — sam brak turbo; profile
    nie są porównywalne bezwzględnie, dlatego para przed/po to `_przed2` / `_po` (te same warunki).
- Profil gorących miejsc po zmianach (gprof, GCC): `bench/profile_gcc.sh` z `ETAP8=1` (tylko `gcc-profile-noinline`,
  przypadki `etna_real` ×20, `test_3d` ×20, `classic_ref` ×20, `mc_full_3d` 300 MCS). W toku: build `gcc-profile-noinline`,
  start 23:37, `wsl -e bash -lc "cmake --preset gcc-profile-noinline && cmake --build --preset gcc-profile-noinline --target engine -j 4"`
  - 23:35–23:37 build `gcc-profile-noinline` (1,5 min) bez błędów i ostrzeżeń; 23:37–23:39 profil (1,8 min) →
    `bench/profiles/etap8_gprof_profile-noinline_*_flat.txt`. Co dominuje (udział czasu własnego, build bez inline —
    tylko podział, nie czasy): **CA lawa** `etna_real`: `frontCandidates` 40%, `gatherLavaCandidates` 13%, `frontRules` 6%,
    przygotowanie (mapa wysokości, wypełnianie tablic, `initFront`, `toMicrostructure`) ~25%; `test_3d`: `frontCandidates`
    56%, `gatherLavaCandidates` 27%; **CA classic** (`classic_ref`): `frontCandidates` 42%, `frontRules` 19%, `frontApply` 9%,
    `syncCell` 7%; **MC** (`mc_full_3d`, 300 MCS): `sweepTrials` 83%, `Grains::label` 14%, `totalEnergy` 3%.
- Wykresy (`bench/plot_etap8.py`, nowy): `docs/img/etap8_przed_po.png` (total `_przed2` / `_po`), `etap8_kroki.png`
  (total po kroku / przed krokiem z `ab_k*.csv`, każdy przypadek), `etap8_front_full.png` (caSim k4 front / full).
- Końcowe testy (tryb oszczędny: buildy Release obu kompilatorów + **jeden** Debug — MSVC; GCC Debug pominięty: ten sam
  kod co GCC Release (ostrzeżenia `-Wall -Wextra` sprawdza Release), asercje i tryb bez optymalizacji sprawdza Debug MSVC,
  a każdy dodatkowy pełny build to ryzyko błędu wewnętrznego kompilatora). W toku: build MSVC Release + ctest, start 23:41,
  `cmake --build --preset msvc-release --parallel 4`
  - 23:41 MSVC Release: bez przebudowy (program = `engine_k7_msvc.exe`), bez ostrzeżeń, ctest 12/12, doctest 111/111.
  - W toku: build MSVC Debug + ctest, start 23:42, `cmake --build --preset msvc-debug --parallel 4` + `ctest --preset msvc-debug`
  - 23:42–23:46 MSVC Debug: build (1,2 min) bez błędów i ostrzeżeń, ctest 12/12 (2,1 min). W toku: GCC Release (sprawdzenie,
    czy aktualny) + ctest, start 23:47, `wsl -e bash -lc "cmake --build --preset gcc-release -j 4 && ctest --preset gcc-release"`
  - 23:47–23:48 GCC Release: bez przebudowy (= `engine_k7a_gcc`), ctest 12/12, doctest 110/110. `python -m pytest gui\tests`:
    100/100. **Końcowe testy zielone.**
- Asembler k1 (brakowało zapisu z sesji 1): MSVC 19.38 `/O2 /FAs` samego `PottsMC.cpp` — pętla po sąsiadach
  `$LL25` liczy przez `setne`/`sete`, jedyny skok to powrót pętli (przed: `je` po porównaniu orientacji); GCC 11.4 —
  `cmp`/`sbb` + 2 × `sete`, jedyny skok `jne` pętli. Fragment: `bench/profiles/asm/PottsMC_unlike_msvc_O2_etap8.asm`.
- W toku: dokumentacja `docs/etap-8-optymalizacja-sekwencyjna.md` i aktualizacje (start 23:51).
- Nazwy procesów tła w wynikach: `ab.py` i `run_profile.py` zapisują teraz nazwy tylko procesów systemowych i narzędzi
  programistycznych (`ab.PUBLIC_PROCESSES`), pozostałe jako „inny program” (repozytorium publiczne). W istniejących
  tabelach `ab_k*.md` i w meta `profile_2026-10-17_przed2/_po` podmienione tylko nazwy (wartości bez zmian);
  `profile_2026-10-09_meta.json` (punkt odniesienia etapu 3) bez zmian.
- 23:51–00:07 dokumentacja: nowy `docs/etap-8-optymalizacja-sekwencyjna.md`; aktualizacje `docs/README.md`,
  `docs/architektura.md` (krok 3, 6, 8, 9 — numery linii, automat frontalny, `ca.sweep`, ściąga), `docs/uruchamianie.md`
  (punkt 7.1 — `ab.py`, `compare_results.py`, `run_profile.py --cases`, `plot_etap8.py`; `ca.sweep` w tabeli configu; każde
  polecenie sprawdzone na krótkim wariancie, wyniki do `results/ab_test`), `README.md`, `bench/README.md`, lokalne
  konwencje. Przy sprawdzaniu: `ab.py --wsl` bez `--note` kończył się błędem WSL (pusty argument) — poprawione;
  `ab.py --from-raw` tworzy folder `--out`; `compare_results.py` ma `--out`. Eksport wersji minimalnej do folderu
  tymczasowego: kontrola odnośników i słownictwa OK (po zmianie słowa w komentarzu `test_io.cpp`); kontrola słownictwa
  wszystkich plików repozytorium (poza bibliotekami zewnętrznymi) — 0 trafień po usunięciu ścieżek bezwzględnych
  z `profile_2026-10-17_przed_meta.json` (→ `<repo>`, jak w raportach etapu 3).

### Stan na koniec sesji 4 (00:08) — etap 8 zakończony w zakresie skróconym

- Przyjęte: k1, k2, k3, k4, k5, k7 (+ w GCC `-falign-functions=64`); pominięte: k6, warianty algorytmiczne MC (opis
  w dokumencie); k8 — zrobione po dokumentacji, bez zysku (presety zostają jako opcja).
- Profile `_przed2` / `_po`, wykresy, profil gorących miejsc, testy końcowe, dokumentacja — gotowe.
- Błędy wewnętrzne kompilatora w sesji 4: 0.
- Do zrobienia ręcznie: usunięcie folderu `C:` w katalogu projektu (polecenie w WSL z katalogu projektu:
  `rm -r "C:"`; zawiera tylko wynik `test_2d`).

- k8 (opcjonalne): presety `msvc-release-avx2` (`/O2 /Ob2 /DNDEBUG /arch:AVX2`, `build-msvc-avx2/`) i
  `gcc-release-native` (`-O3 -DNDEBUG -march=native`, `build-gcc-native/`) w `CMakePresets.json`; domyślne bez zmian.
  W toku: build MSVC AVX2 + ctest, start 00:08, `cmake --preset msvc-release-avx2` + `cmake --build --preset msvc-release-avx2 --parallel 4`
  - 00:08–00:10 MSVC AVX2: build (1,8 min) bez błędów i ostrzeżeń, ctest 12/12, doctest 111/111; `engine_k8avx2_msvc.exe`.
    W toku: build GCC native + ctest, start 00:11, `wsl -e bash -lc "cmake --preset gcc-release-native && cmake --build --preset gcc-release-native -j 4 && ctest --preset gcc-release-native"`
  - 00:11–00:13 GCC native: build (1,9 min) bez błędów i ostrzeżeń, ctest 12/12, doctest 110/110; `engine_k8native_gcc`.
    W toku: zgodność k8 (część 1), start 00:13, `python bench/compare_results.py --bin przed=bench/baseline/engine_przed_msvc.exe
    --bin avx2=bench/baseline/engine_k8avx2_msvc.exe --bin przed_gcc=wsl:bench/baseline/engine_przed_gcc
    --bin native_gcc=wsl:bench/baseline/engine_k8native_gcc --configs <jak w k5, część 1> --name zgodnosc_k8_cz1`
  - zgodność k8 (00:13–00:18, 3,9 + 0,7 min): **15/15 configów, `przed` = `avx2` = `przed_gcc` = `native_gcc`** →
    `zgodnosc_k8.md` (`-march=native` nie złamało zgodności MSVC ↔ GCC).
  - W toku: A/B k8 MSVC (k7, avx2), start 00:19, `python bench/ab.py --bin k7=bench/baseline/engine_k7_msvc.exe
    --bin avx2=bench/baseline/engine_k8avx2_msvc.exe --cases lava_test_3d,lava_etna_real,classic_1000x1000_s100_vn,classic_100x100x100_s10_moore,mc_full_2d_200,mc_full_3d_50,lava_mc_3d --name ab_k8_msvc`
  - A/B k8 MSVC gotowe (00:19–00:20, 0,8 min): avx2/k7 caSim ×1,00–1,03, mcSim ×0,99–1,02, mcStats ×0,98–1,00,
    save ×1,05 — bez zysku ponad szum. W toku: A/B k8 GCC (k7a, native), start 00:20, `python bench/ab.py --wsl
    --bin k7a=bench/baseline/engine_k7a_gcc --bin native=bench/baseline/engine_k8native_gcc --cases <te same 7> --name ab_k8_gcc`
  - A/B k8 GCC gotowe (00:20–00:21, 0,6 min; tło 13 → 9%): native/k7a caSim ×0,99–1,07, mcSim ×0,99–1,02, mcStats
    ×1,00–1,03 — bez zysku. **k8: presety dodane jako opcja (nieprzenośne / bez zysku), domyślne bez zmian.**
  - Dokumentacja uzupełniona o k8 (`docs/etap-8-optymalizacja-sekwencyjna.md` p. 2 i 6.1, `docs/uruchamianie.md` p. 7.1).
