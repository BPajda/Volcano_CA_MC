# Symulacja pamięci podręcznej `cachegrind` (cachegrind)

- Program: `build-gcc-release-g/bin/engine` (GCC 11.4 -O3, -falign-functions=64, -g), 1 wątek, WSL 2; valgrind cachegrind, I1 32768,8,64, D1 49152,12,64 (rozmiar, drogi, linia), LL = L2 2097152,16,64 albo L3 37748736,18,64.
- Liczby z całego przebiegu programu (przygotowanie, kroki, statystyki; bez zapisu wyników). „Jedn.” — komórka × krok (CA) albo próba MC. Miss rate = chybienia / wszystkie odwołania do danych (odczyt + zapis).

Jądro — funkcje kroku (CA: `LavaCA::` poza przygotowaniem, `Boundary::`, wybór wariantu sąsiedztwa, `push_back` list frontu; MC: `PottsMC::sweepTrials` / `colorTrials` / `syncFrame`); miss rate = chybienia / odwołania do danych jądra:

| Przypadek | D odwołania / jedn. | D1: chybienia / jedn. | D1 miss rate | L2: chybienia / jedn. | L2 miss rate | L3: chybienia / jedn. | L3 miss rate | jednostka |
|---|---|---|---|---|---|---|---|---|
| lawa test_3d, front, 150 kroków | 4,7 | 0,034 | 0,73% | 0,000 | 0,01% | 0,0000 | 0,00% | komórkę × krok |
| lawa test_3d, full, 150 kroków | 186,8 | 0,639 | 0,34% | 0,499 | 0,27% | 0,0000 | 0,00% | komórkę × krok |
| classic 1000², VN, front | 1,3 | 0,048 | 3,77% | 0,034 | 2,69% | 0,0000 | 0,00% | komórkę × krok |
| classic 1000², Moore, front | 2,4 | 0,044 | 1,86% | 0,031 | 1,31% | 0,0004 | 0,02% | komórkę × krok |
| classic 100³, VN, front | 6,2 | 0,200 | 3,21% | 0,127 | 2,03% | 0,0007 | 0,01% | komórkę × krok |
| classic 100³, Moore, front | 30,2 | 0,248 | 0,82% | 0,150 | 0,50% | 0,0030 | 0,01% | komórkę × krok |
| classic 1000², VN, full, 40 kroków, vector | 35,6 | 0,413 | 1,16% | 0,412 | 1,16% | 0,0000 | 0,00% | komórkę × krok |
| classic 1000², VN, full, 40 kroków, matrix | 92,4 | 0,414 | 0,45% | 0,413 | 0,45% | 0,0000 | 0,00% | komórkę × krok |
| MC 1000², VN, random, 3 MCS | 21,7 | 4,864 | 22,42% | 3,572 | 16,46% | 0,0013 | 0,01% | próbę MC |
| MC 1000², VN, szachownica, 3 MCS | 21,7 | 0,407 | 1,87% | 0,407 | 1,87% | 0,0000 | 0,00% | próbę MC |
| MC 100³, Moore, random, 2 MCS | 66,8 | 11,573 | 17,33% | 7,267 | 10,88% | 0,0013 | 0,00% | próbę MC |
| MC 100³, Moore, szachownica, 2 MCS | 67,0 | 1,079 | 1,61% | 0,825 | 1,23% | 0,0000 | 0,00% | próbę MC |
| classic 256², VN, full, 40 kroków (siatka ~1,7 MB — L2) | 35,7 | 0,434 | 1,22% | 0,000 | 0,00% | 0,0000 | 0,00% | komórkę × krok |
| classic 1024², VN, full, 10 kroków (~27 MB — L3) | 37,0 | 0,414 | 1,12% | 0,412 | 1,11% | 0,0000 | 0,00% | komórkę × krok |
| classic 2896², VN, full, 3 kroki (~218 MB — RAM) | 37,0 | 0,441 | 1,19% | 0,409 | 1,10% | 0,4060 | 1,10% | komórkę × krok |
| MC 256², random, 20 MCS (~0,3 MB — L2) | 21,1 | 4,078 | 19,31% | 0,000 | 0,00% | 0,0000 | 0,00% | próbę MC |
| MC 1024², random, 2 MCS (~5 MB — L3) | 21,8 | 4,916 | 22,55% | 3,663 | 16,80% | 0,0001 | 0,00% | próbę MC |
| MC 4096², random, 1 MCS (~84 MB — RAM) | 21,8 | 4,991 | 22,92% | 4,906 | 22,53% | 3,5408 | 16,26% | próbę MC |
| MC szachownica 1000 × 125 (pas przy 8 procesach), 24 MCS | 21,1 | 0,535 | 2,54% | 0,256 | 1,21% | 0,0000 | 0,00% | próbę MC |
| MC szachownica 1000², 3 MCS (ta sama liczba prób) | 21,7 | 0,407 | 1,87% | 0,407 | 1,87% | 0,0000 | 0,00% | próbę MC |

Cały program (z przygotowaniem, statystykami i pierwszym dotknięciem pamięci przy alokacji):

| Przypadek | D odwołania / jedn. | D1: chybienia / jedn. | D1 miss rate | L2: chybienia / jedn. | L2 miss rate | L3: chybienia / jedn. | L3 miss rate | jednostka |
|---|---|---|---|---|---|---|---|---|
| lawa test_3d, front, 150 kroków | 5,0 | 0,042 | 0,85% | 0,007 | 0,14% | 0,0036 | 0,07% | komórkę × krok |
| lawa test_3d, full, 150 kroków | 187,1 | 0,649 | 0,35% | 0,507 | 0,27% | 0,0049 | 0,00% | komórkę × krok |
| classic 1000², VN, front | 1,7 | 0,054 | 3,10% | 0,040 | 2,28% | 0,0024 | 0,14% | komórkę × krok |
| classic 1000², Moore, front | 3,0 | 0,053 | 1,76% | 0,039 | 1,30% | 0,0043 | 0,14% | komórkę × krok |
| classic 100³, VN, front | 8,3 | 0,229 | 2,76% | 0,153 | 1,84% | 0,0124 | 0,15% | komórkę × krok |
| classic 100³, Moore, front | 34,4 | 0,309 | 0,90% | 0,202 | 0,59% | 0,0280 | 0,08% | komórkę × krok |
| classic 1000², VN, full, 40 kroków, vector | 36,6 | 0,444 | 1,21% | 0,442 | 1,21% | 0,0162 | 0,04% | komórkę × krok |
| classic 1000², VN, full, 40 kroków, matrix | 94,2 | 0,473 | 0,50% | 0,469 | 0,50% | 0,0172 | 0,02% | komórkę × krok |
| MC 1000², VN, random, 3 MCS | 68,2 | 5,875 | 8,61% | 4,562 | 6,69% | 0,2528 | 0,37% | próbę MC |
| MC 1000², VN, szachownica, 3 MCS | 77,3 | 1,554 | 2,01% | 1,533 | 1,98% | 0,2504 | 0,32% | próbę MC |
| MC 100³, Moore, random, 2 MCS | 189,0 | 13,626 | 7,21% | 8,775 | 4,64% | 0,3816 | 0,20% | próbę MC |
| MC 100³, Moore, szachownica, 2 MCS | 261,9 | 3,713 | 1,42% | 2,968 | 1,13% | 0,3778 | 0,14% | próbę MC |
| classic 256², VN, full, 40 kroków (siatka ~1,7 MB — L2) | 37,2 | 0,472 | 1,27% | 0,022 | 0,06% | 0,0195 | 0,05% | komórkę × krok |
| classic 1024², VN, full, 10 kroków (~27 MB — L3) | 39,4 | 0,536 | 1,36% | 0,533 | 1,35% | 0,0689 | 0,17% | komórkę × krok |
| classic 2896², VN, full, 3 kroki (~218 MB — RAM) | 44,5 | 0,845 | 1,90% | 0,807 | 1,81% | 0,8030 | 1,80% | komórkę × krok |
| MC 256², random, 20 MCS (~0,3 MB — L2) | 30,5 | 4,243 | 13,89% | 0,058 | 0,19% | 0,0513 | 0,17% | próbę MC |
| MC 1024², random, 2 MCS (~5 MB — L3) | 91,3 | 6,420 | 7,03% | 5,138 | 5,63% | 0,3462 | 0,38% | próbę MC |
| MC 4096², random, 1 MCS (~84 MB — RAM) | 155,4 | 8,397 | 5,40% | 7,890 | 5,08% | 6,4634 | 4,16% | próbę MC |
| MC szachownica 1000 × 125 (pas przy 8 procesach), 24 MCS | 33,2 | 0,698 | 2,10% | 0,336 | 1,01% | 0,0367 | 0,11% | próbę MC |
| MC szachownica 1000², 3 MCS (ta sama liczba prób) | 77,3 | 1,554 | 2,01% | 1,533 | 1,98% | 0,2504 | 0,32% | próbę MC |

Funkcje z największą liczbą chybień (LL = L3; udział w chybieniach D1 / L3 całego programu):

| Przypadek | funkcja: udział w chybieniach D1 | funkcja: udział w chybieniach L3 |
|---|---|---|
| lawa test_3d, front, 150 kroków | `LavaCA::frontStepSequential` 36,57%; `LavaCA::frontRulesLayer` 16,86%; `LavaCA::gatherLavaCandidates` 10,70% | `std::vector::_M_fill_assign` 73,16%; `__memset_avx2_unaligned_erms` 12,11%; `_dl_relocate_object` 5,13% |
| lawa test_3d, full, 150 kroków | `LavaCA::updateLava` 62,62%; `Boundary::applyWith` 15,81%; `LavaCA::gatherLavaCandidates` 15,13% | `std::vector::_M_fill_assign` 82,48%; `__memset_avx2_unaligned_erms` 9,18%; `_dl_relocate_object` 3,79% |
| classic 1000², VN, front | `LavaCA::frontStepSequential` 64,60%; `LavaCA::frontRulesLayer` 18,83%; `std::vector::emplace_back` 5,23% | `std::vector::_M_fill_assign` 82,39%; `__memset_avx2_unaligned_erms` 10,72%; `std::vector::_M_realloc_insert` 1,97% |
| classic 1000², Moore, front | `LavaCA::frontStepSequential` 58,58%; `LavaCA::frontRulesLayer` 16,50%; `std::vector::emplace_back` 6,97% | `std::vector::_M_fill_assign` 64,02%; `std::vector::_M_realloc_insert` 11,75%; `__memset_avx2_unaligned_erms` 8,33% |
| classic 100³, VN, front | `LavaCA::frontStepSequential` 48,69%; `LavaCA::frontRulesLayer` 31,79%; `std::vector::emplace_back` 4,46% | `std::vector::_M_fill_assign` 72,64%; `__memset_avx2_unaligned_erms` 9,35%; `std::vector::_M_realloc_insert` 7,71% |
| classic 100³, Moore, front | `LavaCA::frontStepSequential` 41,23%; `LavaCA::frontRulesLayer` 30,39%; `std::vector::emplace_back` 6,15% | `std::vector::_M_fill_assign` 59,93%; `std::vector::_M_realloc_insert` 13,45%; `std::vector::emplace_back` 8,48% |
| classic 1000², VN, full, 40 kroków, vector | `LavaCA::stepClassic` 91,70%; `std::vector::_M_fill_assign` 3,18%; `toMicrostructure` 2,29% | `std::vector::_M_fill_assign` 87,12%; `__memset_avx2_unaligned_erms` 7,56%; `toMicrostructure` 3,19% |
| classic 1000², VN, full, 40 kroków, matrix | `LavaCA::updateClassic` 87,20%; `__memcpy_avx_unaligned_erms` 6,32%; `toMicrostructure` 2,16% | `__memcpy_avx_unaligned_erms` 62,93%; `std::vector::_M_fill_assign` 27,22%; `toMicrostructure` 3,80% |
| MC 1000², VN, random, 3 MCS | `PottsMC::sweepTrials` 82,60%; `Grains::label` 4,26%; `__memcpy_avx_unaligned_erms` 2,97% | `__memcpy_avx_unaligned_erms` 29,03%; `PottsMC::initialize` 27,40%; `__memset_avx2_unaligned_erms` 24,50% |
| MC 1000², VN, szachownica, 3 MCS | `PottsMC::colorTrials` 26,17%; `Grains::label` 16,10%; `__memcpy_avx_unaligned_erms` 11,24% | `__memcpy_avx_unaligned_erms` 29,31%; `PottsMC::initialize` 27,66%; `__memset_avx2_unaligned_erms` 24,76% |
| MC 100³, Moore, random, 2 MCS | `PottsMC::sweepTrials` 84,59%; `Grains::label` 6,07%; `__memcpy_avx_unaligned_erms` 1,92% | `__memcpy_avx_unaligned_erms` 28,85%; `PottsMC::initialize` 27,23%; `__memset_avx2_unaligned_erms` 24,46% |
| MC 100³, Moore, szachownica, 2 MCS | `PottsMC::colorTrials` 28,88%; `Grains::label` 22,48%; `PottsMC::totalEnergy` 17,19% | `__memcpy_avx_unaligned_erms` 29,14%; `PottsMC::initialize` 27,50%; `__memset_avx2_unaligned_erms` 24,72% |
| classic 256², VN, full, 40 kroków (siatka ~1,7 MB — L2) | `LavaCA::stepClassic` 86,71%; `Boundary::applyWith` 5,19%; `std::vector::_M_fill_assign` 3,01% | `std::vector::_M_fill_assign` 72,72%; `_dl_relocate_object` 10,64%; `__memset_avx2_unaligned_erms` 6,10% |
| classic 1024², VN, full, 10 kroków (~27 MB — L3) | `LavaCA::stepClassic` 76,02%; `std::vector::_M_fill_assign` 10,52%; `toMicrostructure` 7,59% | `std::vector::_M_fill_assign` 81,84%; `toMicrostructure` 9,46%; `__memset_avx2_unaligned_erms` 6,83% |
| classic 2896², VN, full, 3 kroki (~218 MB — RAM) | `LavaCA::stepClassic` 52,00%; `std::vector::_M_fill_assign` 22,21%; `toMicrostructure` 16,12% | `LavaCA::stepClassic` 50,34%; `std::vector::_M_fill_assign` 23,37%; `toMicrostructure` 16,70% |
| MC 256², random, 20 MCS (~0,3 MB — L2) | `PottsMC::sweepTrials` 95,79%; `Grains::label` 0,89%; `__memcpy_avx_unaligned_erms` 0,58% | `__memcpy_avx_unaligned_erms` 22,43%; `PottsMC::initialize` 22,31%; `__memset_avx2_unaligned_erms` 20,84% |
| MC 1024², random, 2 MCS (~5 MB — L3) | `PottsMC::sweepTrials` 76,39%; `Grains::label` 5,84%; `__memcpy_avx_unaligned_erms` 3,89% | `__memcpy_avx_unaligned_erms` 30,33%; `PottsMC::initialize` 30,30%; `__memset_avx2_unaligned_erms` 19,57% |
| MC 4096², random, 1 MCS (~84 MB — RAM) | `PottsMC::sweepTrials` 59,39%; `Grains::label` 12,43%; `PottsMC::totalEnergy` 5,96% | `PottsMC::sweepTrials` 54,78%; `Grains::label` 11,61%; `__memcpy_avx_unaligned_erms` 7,04% |
| MC szachownica 1000 × 125 (pas przy 8 procesach), 24 MCS | `PottsMC::colorTrials` 76,41%; `Grains::label` 4,50%; `PottsMC::totalEnergy` 4,47% | `__memset_avx2_unaligned_erms` 27,15%; `std::vector::_M_fill_assign` 21,39%; `__memcpy_avx_unaligned_erms` 21,24% |
| MC szachownica 1000², 3 MCS (ta sama liczba prób) | `PottsMC::colorTrials` 26,17%; `Grains::label` 16,10%; `__memcpy_avx_unaligned_erms` 11,24% | `__memcpy_avx_unaligned_erms` 29,31%; `PottsMC::initialize` 27,66%; `__memset_avx2_unaligned_erms` 24,76% |
