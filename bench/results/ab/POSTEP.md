# Dziennik pomiarów: optymalizacja wersji sekwencyjnej

Pomiary z 17–18.10.2026: testy A/B każdego kroku optymalizacji, zgodność bitowa wszystkich configów, skrócony profil
przed i po zmianach. Opis metodyki i wnioski: [`docs/optymalizacja-sekwencyjna.md`](../../../docs/optymalizacja-sekwencyjna.md).

## Oznaczenia i warunki

- `przed` = program sprzed optymalizacji (`bench/baseline/engine_przed_*`), `kN` = program po kroku N
  (`bench/baseline/engine_kN_*`; binarki są lokalne, katalog `bench/baseline/` jest w `.gitignore`).
- W tabelach `ab_k*.md` i poniżej stosunek = mediana czasu programu B / mediana programu A (B/A < 1: szybciej).
- Tło = obciążenie całego CPU przez inne programy (psutil, próbki 2–3 s, ta sama funkcja co `backgroundLoad`
  w `run_profile.py`) na początku i na końcu pomiaru, zapisane w nagłówku każdej tabeli. Stały składnik ok. 2 procesorów
  logicznych (ok. 7% CPU) to zapytania WMI programów działających w tle (np. narzędzi producenta laptopa).
- **Kroki k1–k4: taktowanie dynamiczne** (procesor podnosi częstotliwość pod obciążeniem), próg tła ≤ 20% przy stabilnym
  obciążeniu, powyżej 25% albo przy skoku pomiar powtarzany.
- **Kroki k5–k8 i profil `_przed2` / `_po`: taktowanie bazowe** (maksymalny stan procesora 99% dla obu klas rdzeni,
  także ukrytego ustawienia rdzeni P `PROCTHROTTLEMAX1`; sprawdzenie licznikiem „% wydajności procesora” pod obciążeniem
  jednego rdzenia P: 97% taktowania bazowego, ok. 2,13 GHz, wobec 196–198% przy taktowaniu dynamicznym;
  `psutil.cpu_freq()` na Windows zawsze podaje 2200 MHz). WSL ograniczony do 8 procesorów i 8 GB (`.wslconfig`).
  Buildy z 4 zadaniami, jedna ciężka operacja naraz. Próg tła ≤ 30% przy stabilnym obciążeniu. Przy taktowaniu
  bazowym czasy są ok. 2,2–2,8× dłuższe, dlatego każdy pomiar A/B zawiera program odniesienia mierzony w tych samych
  warunkach (`przed` albo `k4` / `k5`), a nie tabele z wcześniejszych pomiarów.
- Pomiary jednowątkowe przypięte do procesora logicznego 2 (rdzeń P). Dłuższe pomiary dzielone na części (grupy
  przypadków), tabela scalona `ab.py --from-raw`.

## Tabela kroków

| Krok | Wynik | Pliki wyników | MSVC (B/A) | GCC (B/A) | Zgodność | Tło [% CPU] | Uwagi |
|---|---|---|---|---|---|---|---|
| 0. Punkt odniesienia | zmierzony | `bench/results/profile_2026-10-17_przed*` | — | — | — | 16,6 → 20,0 | tło powyżej 5% (WMI ~2 procesory, aktualizacje systemu, skan antywirusowy); powtórka `_przed2` przy profilu „po” |
| Narzędzia: `bench/ab.py`, `bench/compare_results.py` | gotowe | — | — | — | — | — | `compare_results.py` zapisuje ścieżki względne; `ab.py --from-raw` (tabela z podzbioru programów istniejącego pomiaru albo z części pomiaru) |
| k1. MC bez skoku warunkowego, jedno przejście po sąsiadach, stała część hasha przed pętlą | przyjęty | `ab_k1_mc_msvc.md`, `ab_k1_mc_gcc.md`, `ab_k1_ca_msvc.md`, `ab_k1_ca_gcc.md`, `zgodnosc_k1.md` | mcSim ×0,25–0,52; CA ×0,98–1,00 (bez zmian) | mcSim ×0,44–0,82; CA: patrz `ab_k1_ca_gcc.md` | 15/15 configów, MSVC i GCC | MC: MSVC 13 → 14, GCC 14 → 14; CA: z pomiaru k2 | CA z pomiaru przed / k1 / k2 (`ab.py --from-raw`) |
| k2. Ramka tylko w osiach używanych przez sąsiedztwo | przyjęty (MSVC: CA 3D wolniejsze, patrz uwagi) | `ab_k2_msvc.md`, `ab_k2_gcc.md`, `zgodnosc_k2.md` | classic 2D ×0,56–0,62, lawa 2D ×0,82, MC ×0,98–1,04 (szum); **CA 3D ×1,10–1,12** (lawa, classic Moore) | CA 3D ×0,90–0,93 (lawa), classic 3D ×0,91–0,97, classic 2D ×0,58–0,63, lawa 2D ×0,81, MC ×0,99–1,08 względem k1 (szum, duży rozrzut) | 15/15 configów, MSVC i GCC; A/B bitowo zgodne | MSVC 16 → 14; GCC 16 → 9 | MSVC: CA 3D wolniejsze o 10–12% przy tym samym automacie (zmienił się tylko wzór indeksu `base_ + x + sx·(y + sy·z)` i pętle ramki): arytmetyka indeksu i układ kodu MSVC ([`prawdziwe-wulkany.md`](../../../docs/prawdziwe-wulkany.md), punkt 7); k3 usuwa indeks z gorących pętli. GCC: bez straty w 3D |
| k3. Przesunięcia liniowe sąsiadów (CA) | przyjęty | `ab_k3_msvc.md`, `ab_k3_gcc.md` (części `_ca_lava`, `_ca_classic`, `_mc`), `zgodnosc_k3.md` | k3/k2: lawa 3D ×0,88–0,91, lawa 2D ×0,91, classic ×0,52–0,57, MC ×1,00–1,04 (bez zmian w MC); k3/przed: lawa 3D ×0,97–1,00 (strata k2 odrobiona), lawa 2D ×0,73, classic ×0,31–0,57 | k3/k2: lawa 3D ×0,86–0,88, lawa 2D ×0,79, classic ×0,45–0,57, MC ×0,95–1,02; k3/przed: lawa 3D ×0,75–0,80, lawa 2D ×0,64, classic ×0,28–0,55 | 15/15 configów, MSVC i GCC; A/B bitowo zgodne | MSVC 15 → 15, 14 → 14, 18 → 14; GCC 15 → 19, 21 → 20, 20 → 20 | pomiar w trzech częściach po grupach, tabela scalona `ab.py --from-raw a,b,c` |
| k4. Automat frontalny (`ca.sweep: front` domyślnie, `full` = wersja referencyjna) | przyjęty | `ab_k4_msvc.md`, `ab_k4_gcc.md` (części `_ca_lava`, `_ca_classic`, `_mc`), `ab_k4_*_front_full.md`, `zgodnosc_k4.md` | k4/k3: lawa 3D ×0,003–0,028, lawa 2D ×0,06, classic ×0,11–0,26, MC ×0,99–1,01; k4/przed: `etna_real` 13 085 → 39 ms (×0,003), classic 1000² ×0,03–0,05, 300³ ×0,11; front/full w tym samym programie: lawa ×0,004–0,07, classic ×0,10–0,28 | k4/k3: lawa 3D ×0,003–0,035, lawa 2D ×0,09, classic ×0,12–0,35, MC ×0,98–1,04; k4/przed: `etna_real` 11 951 → 35 ms (×0,003), classic 1000² ×0,04–0,05, 300³ ×0,13 | 15/15 configów w trybach `front` i `full`, MSVC i GCC; A/B bitowo zgodne | MSVC 19 → 16, 16 → 19, 21 → 24; GCC 16 → 20, 17 → 14, 23 → 20 | MSVC: `k4_full` szybsze od k3 w lawie 3D o ~22% przy tej samej pętli pełnego przebiegu (GCC: bez różnicy), czyli układ kodu MSVC; domyślny jest front |
| k5. Tańsze statystyki MC (etykiety ziaren, energia całkowita) | przyjęty | `ab_k5_msvc.md`, `ab_k5_gcc.md` (części `_mc_3d_100`, `_mc_reszta`), `ab_k5_*_ca.md` (k4/k5), `zgodnosc_k5.md` | k5/k4: mcStats ×0,46–0,74, total MC ×0,82–1,00, mcSim ×0,98–1,02 (bez zmian); CA ×0,98–1,01 (bez zmian); k5/przed mcStats ×0,31–0,60 | k5/k4: mcStats ×0,53–0,87, total MC ×0,87–1,01, mcSim ×0,99–1,02; CA ×0,98–1,02; k5/przed mcStats ×0,50–0,83 | 15/15 configów, MSVC i GCC; A/B bitowo zgodne | MSVC 20 → 16, 28 → 20, 23 → 22; GCC 19 → 17, 20 → 18, 18 → 14 | największy zysk w 3D Moore (ziarna: pomijanie sąsiadów wspólnych z x+1); 2D VN: tylko szybka ścieżka wnętrza |
| k6. Mniejsze typy i mniej kopiowania; warianty algorytmiczne MC | niemierzone | — | — | — | — | — | opis pomysłów i spodziewanego efektu w dokumencie, punkt 6; k4 usunęło już bufor `next_` (jeden bufor siatki CA) |
| k7. Zapis `ca_result.txt` / `mc_result.txt` (bufor, własne formatowanie liczb, binarnie z jawnym końcem wiersza) + w GCC `-falign-functions=64` | przyjęty | `ab_k7_msvc.md`, `ab_k7_gcc.md` (części `_ca`, `_mc`), `ab_k7a_gcc.md` (części `_ca`, `_mc`), `zgodnosc_k7.md`, `zgodnosc_k7a_gcc.md` | k7/k5: save ×0,27 (txt + bin), mcSave ×0,33, total ×0,48–0,80 w przypadkach z txt; caSim, mcSim bez zmian; przypadki tylko z bin bez zmian | k7/k5: save ×0,18–0,23, mcSave ×0,31–0,32; k7 bez wyrównania: caSim ×1,03–1,25 (układ kodu, kod automatu identyczny); k7a (z wyrównaniem, domyślne) / k5: caSim ×0,99–1,03, MC ×0,98–1,02 | 15/15 configów (txt bajt w bajt), MSVC i GCC; k7a GCC 15/15; A/B bitowo zgodne | MSVC 21 → 20, 20 → 20; GCC 21 → 18, 19 → 17, k7a 22 → 30, 19 → 17 | binarki `engine_k7_*`, `engine_k7a_gcc` (= domyślny build GCC po zmianie) |
| Profil `_przed2` / `_po` (skrócony) | zmierzony | `bench/results/profile_2026-10-17_przed2*`, `_po*` | po/przed2: `etna_real` total ×0,005, classic ×0,06–0,14, MC ×0,50–0,58 | `etna_real` ×0,006, classic ×0,06–0,14, MC ×0,70 | — | przed2 25 → 19, 23 → 19, 22 → 24; po 17 → 18 | 9 przypadków, 3 powtórzenia, MSVC + GCC |
| k8. Presety kompilatora (`msvc-release-avx2`, `gcc-release-native`) | **bez zysku** (presety zostają jako opcja, domyślne bez zmian) | `ab_k8_msvc.md`, `ab_k8_gcc.md` (7 przypadków), `zgodnosc_k8.md` | avx2/k7: ×0,98–1,05 | native/k7a: ×0,99–1,07 | 15/15 configów, MSVC i GCC (także `-march=native`); A/B bitowo zgodne | MSVC 18 → 16; GCC 13 → 9 | gorące pętle ograniczone pamięcią i skokami, nie arytmetyką, więc szersze wektory nic nie dają |

## Przebieg pomiarów

### 17.10.2026, kroki k1–k4 (taktowanie dynamiczne)

- Profil odniesienia `profile_2026-10-17_przed` (20,7 min): tło 16,6% na początku, 20,0% na końcu.
- k1: A/B przypadków MC (MSVC 3,6 min, tło 13 → 14%; GCC 2,8 min, tło 14 → 14%); zgodność 15/15 (`zgodnosc_k1.md`).
  Przypadki CA k1 zmierzone razem z k2 (`przed`, `k1`, `k2`; tabela `ab_k1_ca_*` przez `ab.py --from-raw`).
- k2: zgodność 15/15 configów (4,4 min, `przed` = `k2` = `przed_gcc` = `k2_gcc`). Tło przed A/B: 19–24% (stałe WMI
  ~2 procesory, skan antywirusowy i indeksowanie plików po buildach). A/B MSVC 14,8 min (tło 16 → 14%), GCC 13,2 min
  (16 → 9%).
- k3: zgodność 15/15 (4,1 min). Tło przed A/B: 14–15% (WMI, indeksowanie plików, okno edytora). A/B w trzech częściach
  (`ca_lava`, `ca_classic`, `mc`): MSVC 4,1 + 5,3 + 5,0 min (tło 15 → 15%, 14 → 14%, 18 → 14%), GCC 3,2 + 5,0 + 4,2 min.
  Pierwsze uruchomienie części GCC `ca_classic` zakończyło się bez wyniku: maszyna wirtualna WSL została wyłączona
  w trakcie (po ponownym starcie pusty `/tmp`, w dzienniku `System` Windows brak błędów); powtórka bez zmian przeszła.
- Co zmienia k3: w CA dostęp do sąsiada przez pozycję (`Storage::Pos`; VectorStorage: indeks w tablicy z ramką,
  MatrixStorage: współrzędne), przesunięcie `linear(o)` = dx + sx·(dy + sy·dz) liczone raz w konstruktorze automatu
  dla każdego przesunięcia każdego wariantu, `shifted(p, o, lin)` = p + lin, `nextX(p)` = p + 1; wybór wariantu
  sąsiedztwa losowego ze stałej części hasha liczonej raz na krok. W MSVC k3 odrabia stratę k2 w CA 3D (k3/przed lawa
  3D ×0,97–1,00): strata k2 wynikała z arytmetyki indeksu w gorącej pętli, której k3 już nie ma.
- k4: zgodność w trybach `front` i `full` 15/15 (4,0 min, `przed` = `k4` = `k4_full` = `przed_gcc` = `k4_gcc` =
  `k4_gcc_full`). A/B w trzech częściach: MSVC 3,8 + 5,0 + 5,5 min (tło 19 → 16%, 16 → 19%, 21 → 24%), GCC 3,1 + 4,5
  + 4,3 min. Tabele `ab_k4_*.md` (przed / k3 / k4) i `ab_k4_*_front_full.md` (k4 full vs front).
- Budowa automatu frontalnego i dowód zgodności: listy kandydatów per warstwa, reguły czytają tylko stan z początku
  kroku, zmiany wpisywane po regułach wszystkich warstw; każda komórka, która może się zmienić, jest liczona tą samą
  funkcją reguł na tym samym stanie (opis w `engine/src/ca/CaRules.hpp` i w dokumencie, punkt 3.4; testy
  `engine/tests/test_front.cpp`: 11 przypadków, wszystkie sąsiedztwa, oba brzegi, obie reprezentacje siatki).
- Problem techniczny: przy pełnym obciążeniu wszystkich rdzeni kompilatory kilka razy przerwały budowanie losowym błędem
  wewnętrznym (MSVC C1001 / CL.exe 0xC0000409, GCC „internal compiler error: Segmentation fault”) w różnych plikach;
  ponowienie bez zmian w kodzie przechodziło. Od pomiarów k5 komputer pracował przy taktowaniu bazowym z buildami
  na 4 zadania (warunki wyżej); w tych warunkach błędów wewnętrznych nie było.

### 17–18.10.2026, kroki k5–k8 i profil skrócony (taktowanie bazowe)

- Tło na początku: 23% CPU (zapytania WMI programów w tle ~2,3 procesora logicznego, usługi systemu, przeglądarka).
- k5: zgodność 15/15 (dwie części, 4,1 + 0,7 min, `przed` = `k5` = `przed_gcc` = `k5_gcc`). A/B (k5 zmienia tylko
  statystyki MC): grupa mc — `przed`, `k4`, `k5` w dwóch częściach (`mc_full_3d_100` osobno, ok. 6,5 min); grupy CA —
  `k4`, `k5` (kontrola układu kodu).
  - MSVC: `mc_full_3d_100` 8,1 min (tło 20 → 16%): mcStats ×0,455 (2 316 → 1 053 ms), total ×0,960, mcSim ×1,012
    (szum); pozostałe MC 4,6 min (28 → 20%): mcStats ×0,488–0,744, total ×0,82–1,00; CA 1,6 min (23 → 22%): caSim
    ×0,98–1,01 (układ kodu nie przesunął automatu).
  - GCC: `mc_full_3d_100` 6,6 min: mcStats ×0,532 (1 821 → 969 ms), total ×0,952; pozostałe MC 3,7 min: mcStats
    ×0,556–0,866; CA 1,4 min (18 → 14%): caSim ×0,98–1,02.
  - Co zmienia k5: `Grains::label` — dla komórek wnętrza sąsiedzi „do przodu” przez stałe przesunięcie liniowe
    w tablicy bez ramki, reprezentant komórki raz na komórkę, a gdy sąsiad x+1 ma tę samą orientację, pominięte
    przesunięcia wspólne z x+1 (Moore 3D: 8 z 13); `PottsMC::totalEnergy` — przy sąsiedztwie symetrycznym tylko pary
    „do przodu”, bez skoków warunkowych. Testy: etykiety vs BFS, energia vs suma energii komórek (`test_mc.cpp`).
- k7: przed zmianą (pojedynczy przebieg, classic 1000² VN) `ca_result.txt` 303 ms (19,7 MB), `ca_result.bin` 8 ms;
  `mc_full_2d` 1000²: `mc_result.txt` 138 ms (13,6 MB); po zmianie 60 ms i 36 ms, pliki identyczne (`cmp`). Zgodność
  15/15 (4,0 + 0,7 min; pliki txt bajt w bajt na tej samej platformie).
  - MSVC: CA 1,5 min — save ×0,27 (txt + bin), total ×0,48–0,80 w przypadkach z plikiem txt, caSim bez zmian;
    mc 6,3 min — mcSave ×0,33, `lava_mc_3d` total ×0,72.
  - GCC: CA 1,4 min (tło 21 → 18%) — save ×0,18–0,23, ale caSim ×1,04–1,27 przy kodzie automatu bez zmian. `nm`
    i `objdump`: kod maszynowy `frontRules`, `frontDescent`, `stepTimed`, `gatherLavaCandidates`, `PottsMC::sweep`
    w k5 i k7 identyczny (bez adresów), wszystkie funkcje `LavaCA` przesunięte o +16 B (np. `frontRules` mod 64:
    48 → 0), czyli efekt układu kodu GCC. mc 6,2 min — mcSave ×0,31–0,32, `lava_mc_3d` caSim ×1,22 (ten sam efekt).
  - Build z `-falign-functions=64` (`engine_k7a_gcc`, wszystkie gorące funkcje mod 64 = 0): A/B CA k5 / k7 / k7a
    2,0 min — k7/k5 caSim ×1,03–1,25 (powtarzalne), k7a/k5 ×0,99–1,03 (classic 1000² VN ×1,07 przy rozrzucie
    107–261 ms); A/B mc 3,1 min (tło 22 → 30%) — k7a/k7 mcSim, mcStats ×0,98–1,02. Wyrównanie funkcji przyjęte
    w `engine/CMakeLists.txt` dla GCC Release (MSVC nie ma odpowiednika dla pojedynczych funkcji; w MSVC k7 nie
    zmieniło caSim). Zgodność k7a GCC 15/15 (2,2 min).
- Profil skrócony (`run_profile.py --cases`, 9 przypadków, 3 powtórzenia, MSVC + GCC): `profile_2026-10-17_przed2`
  w trzech częściach (6,5 + 4,9 + 4,6 min; tło 25 → 19%, 23 → 19%, 22 → 24%), `profile_2026-10-17_po` jedna część
  (4,7 min; 17 → 18%). Mediany po/przed2: `etna_real` caSim MSVC 32 203 → 86 ms (×0,003), GCC 24 621 → 77 ms, total
  ×0,005–0,006; `test_3d` caSim ×0,027–0,030; classic 1000² caSim ×0,036–0,047, total ×0,06–0,07; 300³ caSim
  ×0,096–0,099, total ×0,14; MC 1000² VN total MSVC ×0,58, GCC ×0,70; MC 100³ Moore total MSVC ×0,50, GCC ×0,70
  (mcStats ×0,33 / ×0,48); save ×0,19–0,30 (z txt), mcSave ×0,32–0,33. `_przed2` (taktowanie bazowe) względem
  `_przed` (taktowanie dynamiczne): ×2,2–2,8 dłużej, dlatego para przed/po to `_przed2` / `_po`.
- Profil gorących miejsc po zmianach (gprof, `gcc-profile-noinline`, `bench/profile_gcc.sh` z `PO_OPTYMALIZACJI=1`,
  1,8 min) → `bench/profiles/po_optymalizacji_gprof_profile-noinline_*_flat.txt`. Udział czasu własnego (build bez
  wstawiania funkcji, tylko podział): lawa `etna_real` — `frontCandidates` 40%, `gatherLavaCandidates` 13%,
  `frontRules` 6%, przygotowanie (mapa wysokości, wypełnianie tablic, `initFront`, `toMicrostructure`) ~25%;
  `test_3d` — `frontCandidates` 56%, `gatherLavaCandidates` 27%; classic (`classic_ref`) — `frontCandidates` 42%,
  `frontRules` 19%, `frontApply` 9%, `syncCell` 7%; MC (`mc_full_3d`, 300 MCS) — `sweepTrials` 83%,
  `Grains::label` 14%, `totalEnergy` 3%.
- Asembler k1: MSVC 19.38 `/O2 /FAs` — pętla po sąsiadach `$LL25` liczy przez `setne`/`sete`, jedyny skok to powrót
  pętli (przed: `je` po porównaniu orientacji); GCC 11.4 — `cmp`/`sbb` + 2 × `sete`, jedyny skok `jne` pętli.
  Fragment: `bench/profiles/asm/PottsMC_unlike_msvc_O2.asm`.
- Testy końcowe: MSVC Release i Debug — ctest 12/12; GCC Release — ctest 12/12; `pytest gui\tests` 100/100.
- k8: presety `msvc-release-avx2` (`/O2 /Ob2 /DNDEBUG /arch:AVX2`) i `gcc-release-native` (`-O3 -DNDEBUG -march=native`).
  Zgodność 15/15 (3,9 + 0,7 min; `-march=native` nie złamało zgodności MSVC ↔ GCC). A/B 7 przypadków: MSVC 0,8 min —
  avx2/k7 caSim ×1,00–1,03, mcSim ×0,99–1,02, save ×1,05; GCC 0,6 min (tło 13 → 9%) — native/k7a caSim ×0,99–1,07,
  mcSim ×0,99–1,02. Bez zysku ponad szum; presety zostają jako opcja.
- Nazwy procesów tła w wynikach: `ab.py` i `run_profile.py` zapisują nazwy tylko procesów systemowych i narzędzi
  programistycznych (`ab.PUBLIC_PROCESSES`), pozostałe jako „inny program”. W tabelach `ab_k*.md` i w meta
  `profile_2026-10-17_przed2/_po` podmienione tylko nazwy (wartości bez zmian).

## Polecenia (przykłady)

```
python bench/compare_results.py --bin przed=bench/baseline/engine_przed_msvc.exe --bin k4=bench/baseline/engine_k4_msvc.exe ^
    --bin k4_full=bench/baseline/engine_k4_msvc.exe --bin przed_gcc=wsl:bench/baseline/engine_przed_gcc ^
    --bin k4_gcc=wsl:bench/baseline/engine_k4_gcc --args "k4_full=--set ca.sweep=full" --name zgodnosc_k4
python bench/ab.py --bin przed=bench/baseline/engine_przed_msvc.exe --bin k3=bench/baseline/engine_k3_msvc.exe ^
    --bin k4=bench/baseline/engine_k4_msvc.exe --groups ca_lava --name ab_k4_msvc_ca_lava
python bench/ab.py --wsl --bin k5=bench/baseline/engine_k5_gcc --bin k7=bench/baseline/engine_k7_gcc ^
    --bin k7a=bench/baseline/engine_k7a_gcc --groups ca_lava,ca_classic --name ab_k7a_gcc_ca
python bench/ab.py --from-raw ab_k3_msvc_ca_lava_raw.csv,ab_k3_msvc_ca_classic_raw.csv,ab_k3_msvc_mc_raw.csv ^
    --labels przed,k2,k3 --name ab_k3_msvc
python bench/run_profile.py --full --gcc --groups classic,mc,lava,big,detail --cases <przypadki> ^
    --name profile_2026-10-17_po --engine bench/baseline/engine_k7_msvc.exe --gcc-engine bench/baseline/engine_k7a_gcc
```
