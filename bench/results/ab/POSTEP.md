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

## Tabela kroków

| Krok | Stan | Pliki wyników | MSVC (B/A) | GCC (B/A) | Zgodność | Tło [% CPU] | Uwagi |
|---|---|---|---|---|---|---|---|
| 0. Punkt odniesienia | zrobione (sesja 1) | `bench/results/profile_2026-10-17_przed*` | — | — | — | 16,6 → 20,0 | tło powyżej 5% (WMI ~2 procesory, Windows Update, skan antywirusowy); powtórka `_przed2` przy profilu „po” |
| 1. `bench/ab.py`, `bench/compare_results.py` | zrobione (sesja 1) | — | — | — | — | — | w sesji 2: `compare_results.py` zapisuje ścieżki względne; `ab.py --from-raw` (tabela z podzbioru programów istniejącego pomiaru) |
| k1. MC bez skoku warunkowego, jedno przejście po sąsiadach, stała część hasha przed pętlą | zrobione (sesja 1: MC; sesja 2: CA) | `ab_k1_mc_msvc.md`, `ab_k1_mc_gcc.md`, `ab_k1_ca_msvc.md`, `ab_k1_ca_gcc.md`, `zgodnosc_k1.md` | mcSim ×0,25–0,52; CA ×0,98–1,00 (bez zmian) | mcSim ×0,44–0,82; CA: patrz `ab_k1_ca_gcc.md` | 15/15 configów, MSVC i GCC | MC: MSVC 13 → 14, GCC 14 → 14 (sesja 1); CA: z pomiaru k2 | CA z pomiaru przed / k1 / k2 (`ab.py --from-raw`) |
| k2. Ramka tylko w osiach używanych przez sąsiedztwo | przyjęte (MSVC 3D CA wolniejsze — patrz uwagi) | `ab_k2_msvc.md`, `ab_k2_gcc.md`, `zgodnosc_k2.md` | classic 2D ×0,56–0,62, lawa 2D ×0,82, MC ×0,98–1,04 (szum); **CA 3D ×1,10–1,12** (lawa, classic Moore) | CA 3D ×0,90–0,93 (lawa), classic 3D ×0,91–0,97, classic 2D ×0,58–0,63, lawa 2D ×0,81, MC ×0,99–1,08 względem k1 (szum, duży rozrzut) | 15/15 configów, MSVC i GCC; A/B bitowo zgodne | MSVC 16 → 14; GCC 16 → 9 | MSVC: CA 3D wolniejsze o 10–12% przy tym samym automacie (zmienił się tylko wzór indeksu `base_ + x + sx·(y + sy·z)` i pętle ramki) — arytmetyka indeksu / układ kodu MSVC (etap 6, p. 7); k3 usuwa indeks z gorących pętli, sprawdzić k3/przed. GCC: bez straty w 3D |
| k3. Przesunięcia liniowe sąsiadów (CA) | przyjęte (sesja 2: kod i binarki; sesja 3: zgodność, A/B) | `ab_k3_msvc.md`, `ab_k3_gcc.md` (części `_ca_lava`, `_ca_classic`, `_mc`), `zgodnosc_k3.md` | k3/k2: lawa 3D ×0,88–0,91, lawa 2D ×0,91, classic ×0,52–0,57, MC ×1,00–1,04 (bez zmian w MC); k3/przed: lawa 3D ×0,97–1,00 (strata k2 odrobiona), lawa 2D ×0,73, classic ×0,31–0,57 | k3/k2: lawa 3D ×0,86–0,88, lawa 2D ×0,79, classic ×0,45–0,57, MC ×0,95–1,02; k3/przed: lawa 3D ×0,75–0,80, lawa 2D ×0,64, classic ×0,28–0,55 | 15/15 configów, MSVC i GCC; A/B bitowo zgodne | MSVC 15 → 15, 14 → 14, 18 → 14; GCC 15 → 19, 21 → 20, 20 → 20 | pomiar w trzech częściach po grupach (limit 10 min na polecenie, bez pomiarów w tle), tabela scalona `ab.py --from-raw a,b,c` |
| k4. Automat frontalny (`ca.sweep: front` domyślnie, `full` = wersja referencyjna) | przyjęte (sesja 2: większość kodu; sesja 3: dokończenie, build, zgodność, A/B) | `ab_k4_msvc.md`, `ab_k4_gcc.md` (części `_ca_lava`, `_ca_classic`, `_mc`), `ab_k4_*_front_full.md`, `zgodnosc_k4.md` | k4/k3: lawa 3D ×0,003–0,028, lawa 2D ×0,06, classic ×0,11–0,26, MC ×0,99–1,01; k4/przed: `etna_real` 13 085 → 39 ms (×0,003), classic 1000² ×0,03–0,05, 300³ ×0,11; front/full w tym samym programie: lawa ×0,004–0,07, classic ×0,10–0,28 | k4/k3: lawa 3D ×0,003–0,035, lawa 2D ×0,09, classic ×0,12–0,35, MC ×0,98–1,04; k4/przed: `etna_real` 11 951 → 35 ms (×0,003), classic 1000² ×0,04–0,05, 300³ ×0,13 | 15/15 configów w trybach `front` i `full`, MSVC i GCC; A/B bitowo zgodne | MSVC 19 → 16, 16 → 19, 21 → 24; GCC 16 → 20, 17 → 14, 23 → 20 | MSVC: `k4_full` szybsze od k3 w lawie 3D o ~22% przy tej samej pętli pełnego przebiegu (GCC: bez różnicy) — układ kodu MSVC (etap 6, p. 7); domyślny jest front |
| k5. Tańsze statystyki MC (etykiety ziaren, energia całkowita) | w kodzie (sesja 3), MSVC zbudowane i zielone; GCC przerwany błędem kompilatora; bez zgodności i A/B | `engine_k5_msvc.exe` | pojedynczy przebieg 50³: mcStats 229 → 120–137 ms (nie A/B) | — | wynik `mc_full_3d` identyczny z k4 (cmp, MSVC) | — | dokończyć w sesji 4 |
| k6–k8, warianty MC, profil „po”, dokumentacja | do zrobienia | | | | | | |

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
