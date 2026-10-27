# Zestawienie przyspieszenia i efektywności (etapy 8–11)

Bez nowych przebiegów — `python bench/zestawienie.py` czyta CSV etapów 8–11. S = T(1)/T(p), E = S/p, f — część szeregowa z dopasowania prawa Amdahla (z tabel etapów 9 i 10, warianty jednego rodzaju); „faza” = `caSim` / `mcSim`, „total” = cały przebieg. T(1) i T(p) zawsze z tej samej sesji pomiarowej. Warunki wszystkich wierszy: bez turbo, rdzenie P, wysoki priorytet (etap 8 — 1 rdzeń P); każdy przebieg etapów 9–11 bitowo zgodny z wariantem odniesienia.

## MSVC / MS-MPI — S / E fazy obliczeń przy 7–8 rdzeniach

| Przypadek | T(1) faza [ms] (etap 9 / 10) | OpenMP 8: S / E | MPI 7: S / E | MPI 8: S / E | 2 × 4: S / E | 4 × 2: S / E | MPI 8 + typy: S / E | najlepszy (S fazy) | S całego przebiegu najlepszego |
|---|---|---|---|---|---|---|---|---|---|
| lawa `etna_real`, front | 85,5 / 92,0 | 4,98 / 0,62 | 0,53 / 0,08 | 0,45 / 0,06 | 0,80 / 0,10 | 0,45 / 0,06 | — | OpenMP 8 wątków (etap 9): **4,98** | 2,12 |
| lawa 3D 128² × 64, front | 718 / 762 | 5,36 / 0,67 | 2,52 / 0,36 | 2,24 / 0,28 | 2,64 / 0,33 | 2,54 / 0,32 | 2,43 / 0,30 | OpenMP 8 (etap 10, kontrola) (etap 10): **6,03** | 4,47 |
| lawa 3D 128² × 64, full | 12 489 / 13 415 | 6,34 / 0,79 | 5,35 / 0,76 | 4,53 / 0,57 | 5,39 / 0,67 | 4,93 / 0,62 | 4,85 / 0,61 | OpenMP 8 wątków (etap 9): **6,34** | 6,22 |
| classic 2000², VN | 530 / 539 | 6,67 / 0,83 | 6,68 / 0,95 | 5,97 / 0,75 | 5,02 / 0,63 | 5,56 / 0,69 | — | MPI 7 procesów (bez procesora 0) (etap 10): **6,68** | 3,50 |
| classic 300³, VN | 3 406 / 3 379 | 4,82 / 0,60 | 3,62 / 0,52 | 3,32 / 0,41 | 3,90 / 0,49 | 3,88 / 0,48 | 3,64 / 0,46 | OpenMP 8 wątków (etap 9): **4,82** | 3,22 |
| MC szachownica 1000², VN | 2 059 / 2 052 | 6,18 / 0,77 | 6,72 / 0,96 | 6,03 / 0,75 | 6,17 / 0,77 | 6,26 / 0,78 | — | MPI 7 procesów (bez procesora 0) (etap 10): **6,72** | 3,54 |
| MC szachownica 100³, Moore | 5 743 / 5 741 | 6,06 / 0,76 | 5,96 / 0,85 | 5,55 / 0,69 | 5,27 / 0,66 | 6,00 / 0,75 | 5,53 / 0,69 | OpenMP 8 (etap 10, kontrola) (etap 10): **6,27** | 3,66 |

## GCC / OpenMPI — S / E fazy obliczeń przy 7–8 rdzeniach

| Przypadek | T(1) faza [ms] (etap 9 / 10) | OpenMP 8: S / E | MPI 8: S / E | 2 × 4: S / E | MPI 8 + typy: S / E | najlepszy (S fazy) | S całego przebiegu najlepszego |
|---|---|---|---|---|---|---|---|
| lawa `etna_real`, front | 79,1 / 81,7 | 3,44 / 0,43 | 0,46 / 0,06 | 1,02 / 0,13 | — | OpenMP 6 wątków (etap 9): **4,17** | 1,94 |
| lawa 3D 128² × 64, front | 666 / 681 | 5,11 / 0,64 | 2,28 / 0,29 | 2,79 / 0,35 | 2,56 / 0,32 | OpenMP 8 wątków (etap 9): **5,11** | 4,49 |
| lawa 3D 128² × 64, full | 12 227 / 11 621 | 6,26 / 0,78 | 4,89 / 0,61 | 5,47 / 0,68 | — | OpenMP 8 wątków (etap 9): **6,26** | 6,16 |
| classic 2000², VN | 491 / 487 | 4,33 / 0,54 | 4,59 / 0,57 | 4,17 / 0,52 | — | OpenMP 8 (etap 10, kontrola) (etap 10): **5,41** | 5,03 |
| classic 300³, VN | 3 151 / 3 196 | 2,86 / 0,36 | 3,33 / 0,42 | 4,16 / 0,52 | 3,44 / 0,43 | OpenMP 8 (etap 10, kontrola) (etap 10): **4,30** | 3,43 |
| MC szachownica 1000², VN | 1 919 / 2 010 | 4,70 / 0,59 | 5,40 / 0,68 | 5,98 / 0,75 | — | hybryda 2 × 4 (etap 10): **5,98** | 2,68 |
| MC szachownica 100³, Moore | 5 273 / 5 391 | 5,13 / 0,64 | 4,99 / 0,62 | 5,44 / 0,68 | 4,97 / 0,62 | OpenMP 8 (etap 10, kontrola) (etap 10): **6,26** | 3,89 |

## Łączne przyspieszenie od programu sprzed optymalizacji (faza obliczeń)

Iloczyn ilorazów z sesji: algorytm (etap 8: profil `_przed2` / `_po`, ta sama sesja) × szachownica przy 1 wątku (MC, etap 9: random / szachownica, ta sama sesja) × równoległość (T(1) / T(p) w sesji najlepszego wariantu). Kolumna „wprost” dzieli czasy z różnych dni — kontrola.

| Przypadek | Kompilator | przed etapem 8 [ms] | po etapie 8 [ms] | zysk z algorytmu (etap 8) | szachownica przy 1 wątku (etap 9) | najlepszy wariant równoległy | jego T [ms] | zysk z równoległości | **łącznie** (iloczyn) | wprost: przed / najlepszy |
|---|---|---|---|---|---|---|---|---|---|---|
| lawa `etna_real`, front | MSVC | 32 203 | 85,8 | ×375,2 | — | OpenMP 8 wątków (etap 9) | 17,1 | ×4,98 | **×1871** | ×1878 |
| classic 300³, VN | MSVC | 38 122 | 3 663 | ×10,4 | — | OpenMP 8 wątków (etap 9) | 707 | ×4,82 | **×50** | ×54 |
| MC szachownica 1000², VN | MSVC | 16 321 | 9 401 | ×1,7 | ×4,04 | MPI 7 procesów (bez procesora 0) (etap 10) | 305 | ×6,72 | **×47** | ×53 |
| MC szachownica 100³, Moore | MSVC | 42 850 | 21 942 | ×2,0 | ×3,28 | MPI 7, typy pochodne (etap 11) | 934 | ×6,07 | **×39** | ×46 |
| lawa `etna_real`, front | GCC | 24 621 | 77,3 | ×318,6 | — | OpenMP 6 wątków (etap 9) | 19,0 | ×4,17 | **×1328** | ×1298 |
| classic 300³, VN | GCC | 34 540 | 3 423 | ×10,1 | — | hybryda 2 × 4 (etap 10) | 768 | ×4,16 | **×42** | ×45 |
| MC szachownica 1000², VN | GCC | 12 331 | 8 588 | ×1,4 | ×4,48¹ | hybryda 2 × 4 (etap 10) | 336 | ×5,98 | **×38** | ×37 |
| MC szachownica 100³, Moore | GCC | 27 793 | 19 920 | ×1,4 | ×3,78¹ | hybryda 2 × 4 (etap 10) | 991 | ×5,44 | **×29** | ×28 |

¹ GCC nie mierzył wariantu random w sesji etapu 9 — szachownica wprost: po etapie 8 (profil `_po`, wariant random) / szachownica przy 1 wątku (etap 9), dwie sesje.

## Cały przebieg z zapisem wyniku (etap 11)

Grupa `io` etapu 11, MSVC / MS-MPI (T(1) = m1 gather tej samej sesji; GCC mierzono tylko przy 8 procesach — `bench/results/mpi_io/pomiar_gcc*.md`):

| Przypadek (zapis) | Kompilator | T(1) total, gather [ms] | S(8) total, gather | S(8) total, MPI-IO | S(8) faza | udział zapisu w total przy 8 procesach: gather / MPI-IO |
|---|---|---|---|---|---|---|
| bin classic 300³ | msvc | 4 533 | 2,70 | 3,52 | 3,84 | 29% / 25% |
| txt classic 300³ | msvc | 5 846 | 1,93 | 3,43 | 3,86 | 61% / 43% |
| bin classic 2000² | msvc | 697 | 3,29 | 3,39 | 6,34 | 28% / 29% |
| txt classic 2000² | msvc | 923 | 2,11 | 4,34 | 6,97 | 65% / 42% |

## Przyspieszenie ponadliniowe (E > 1)

| Przypadek | Kompilator | Wariant | Etap | S faza | E faza | S total | E total |
|---|---|---|---|---|---|---|---|
| classic 2000², VN | msvc | OpenMP 2 wątki | 9 | 2,01 | 1,003 | 1,80 | 0,901 |
| classic 2000², VN | msvc | MPI 2 procesy | 10 | 2,05 | 1,023 | 1,76 | 0,879 |
| classic 2000², VN | msvc | OpenMP 4 (etap 10) | 10 | 4,02 | 1,005 | 3,20 | 0,800 |

## Wszystkie warianty — MSVC / MS-MPI

| Przypadek | Wariant | Etap | Rdzenie | T faza [ms] | T total [ms] | S faza | E faza | S total | E total | f faza | f total | Źródło | Uwagi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| lawa `etna_real`, front | przed etapem 8 | 8 | 1 | 32 203 | 32 281 | — | — | — | — | — | — | `profile_2026-10-17_przed2.csv` |  |
| lawa `etna_real`, front | po etapie 8 | 8 | 1 | 85,8 | 150 | 375,24 | 375,24 | 215,19 | 215,19 | — | — | `profile_2026-10-17_po.csv` | S = przed / po (zysk z algorytmu) |
| lawa `etna_real`, front | OpenMP 1 wątek | 9 | 1 | 85,5 | 146 | 1,00 | 1,00 | 1,00 | 1,00 | — | — | `omp/skalowanie_msvc.csv` |  |
| lawa `etna_real`, front | OpenMP 2 wątki | 9 | 2 | 48,5 | 102 | 1,76 | 0,88 | 1,43 | 0,72 | 0,080 | 0,374 | `omp/skalowanie_msvc.csv` |  |
| lawa `etna_real`, front | OpenMP 4 wątki | 9 | 4 | 25,9 | 75,6 | 3,30 | 0,82 | 1,93 | 0,48 | 0,080 | 0,374 | `omp/skalowanie_msvc.csv` |  |
| lawa `etna_real`, front | OpenMP 6 wątków | 9 | 6 | 18,6 | 67,3 | 4,58 | 0,76 | 2,17 | 0,36 | 0,080 | 0,374 | `omp/skalowanie_msvc.csv` |  |
| lawa `etna_real`, front | OpenMP 8 wątków | 9 | 8 | 17,1 | 68,8 | 4,98 | 0,62 | 2,12 | 0,26 | 0,080 | 0,374 | `omp/skalowanie_msvc.csv` |  |
| lawa `etna_real`, front | MPI 1 proces | 10 | 1 | 92,0 | 175 | 1,00 | 1,00 | 1,00 | 1,00 | 1,000 | 1,000 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa `etna_real`, front | MPI 2 procesy | 10 | 2 | 149 | 225 | 0,62 | 0,31 | 0,78 | 0,39 | 1,000 | 1,000 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa `etna_real`, front | MPI 3 procesy | 10 | 3 | 167 | 238 | 0,55 | 0,18 | 0,73 | 0,24 | 1,000 | 1,000 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa `etna_real`, front | MPI 4 procesy | 10 | 4 | 180 | 253 | 0,51 | 0,13 | 0,69 | 0,17 | 1,000 | 1,000 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa `etna_real`, front | MPI 6 procesów | 10 | 6 | 169 | 240 | 0,54 | 0,09 | 0,73 | 0,12 | 1,000 | 1,000 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa `etna_real`, front | MPI 7 procesów (bez procesora 0) | 10 | 7 | 174 | 242 | 0,53 | 0,08 | 0,72 | 0,10 | 1,000 | 1,000 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa `etna_real`, front | MPI 8 procesów | 10 | 8 | 203 | 280 | 0,45 | 0,06 | 0,63 | 0,08 | 1,000 | 1,000 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa `etna_real`, front | hybryda 2 × 4 | 10 | 8 | 116 | 187 | 0,80 | 0,10 | 0,93 | 0,12 | — | — | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa `etna_real`, front | hybryda 4 × 2 | 10 | 8 | 203 | 289 | 0,45 | 0,06 | 0,61 | 0,08 | — | — | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa `etna_real`, front | MPI 4, changed | 10 | 4 | 141 | 209 | 0,65 | 0,16 | 0,84 | 0,21 | — | — | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa `etna_real`, front | MPI 8, changed | 10 | 8 | 157 | 239 | 0,58 | 0,07 | 0,73 | 0,09 | — | — | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa `etna_real`, front | OpenMP 4 (etap 10) | 10 | 4 | 25,9 | 76,0 | 3,55 | 0,89 | 2,30 | 0,58 | — | — | `mpi/skalowanie_mpi_msvc.csv` |  |
| lawa `etna_real`, front | OpenMP 8 (etap 10, kontrola) | 10 | 8 | 18,5 | 71,6 | 4,96 | 0,62 | 2,44 | 0,31 | — | — | `mpi/skalowanie_mpi_msvc.csv` |  |
| lawa 3D 128² × 64, front | OpenMP 1 wątek | 9 | 1 | 718 | 755 | 1,00 | 1,00 | 1,00 | 1,00 | — | — | `omp/skalowanie_msvc.csv` |  |
| lawa 3D 128² × 64, front | OpenMP 2 wątki | 9 | 2 | 394 | 428 | 1,82 | 0,91 | 1,76 | 0,88 | 0,047 | 0,084 | `omp/skalowanie_msvc.csv` |  |
| lawa 3D 128² × 64, front | OpenMP 4 wątki | 9 | 4 | 190 | 222 | 3,77 | 0,94 | 3,40 | 0,85 | 0,047 | 0,084 | `omp/skalowanie_msvc.csv` |  |
| lawa 3D 128² × 64, front | OpenMP 6 wątków | 9 | 6 | 134 | 165 | 5,34 | 0,89 | 4,57 | 0,76 | 0,047 | 0,084 | `omp/skalowanie_msvc.csv` |  |
| lawa 3D 128² × 64, front | OpenMP 8 wątków | 9 | 8 | 134 | 165 | 5,36 | 0,67 | 4,59 | 0,57 | 0,047 | 0,084 | `omp/skalowanie_msvc.csv` |  |
| lawa 3D 128² × 64, front | MPI 1 proces | 10 | 1 | 762 | 818 | 1,00 | 1,00 | 1,00 | 1,00 | 0,406 | 0,451 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa 3D 128² × 64, front | MPI 2 procesy | 10 | 2 | 708 | 757 | 1,08 | 0,54 | 1,08 | 0,54 | 0,406 | 0,451 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa 3D 128² × 64, front | MPI 3 procesy | 10 | 3 | 538 | 586 | 1,42 | 0,47 | 1,40 | 0,47 | 0,406 | 0,451 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa 3D 128² × 64, front | MPI 4 procesy | 10 | 4 | 421 | 467 | 1,81 | 0,45 | 1,75 | 0,44 | 0,406 | 0,451 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa 3D 128² × 64, front | MPI 6 procesów | 10 | 6 | 320 | 369 | 2,38 | 0,40 | 2,22 | 0,37 | 0,406 | 0,451 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa 3D 128² × 64, front | MPI 7 procesów (bez procesora 0) | 10 | 7 | 302 | 352 | 2,52 | 0,36 | 2,33 | 0,33 | 0,406 | 0,451 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa 3D 128² × 64, front | MPI 8 procesów | 10 | 8 | 340 | 445 | 2,24 | 0,28 | 1,84 | 0,23 | 0,406 | 0,451 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa 3D 128² × 64, front | hybryda 2 × 4 | 10 | 8 | 288 | 341 | 2,64 | 0,33 | 2,40 | 0,30 | — | — | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa 3D 128² × 64, front | hybryda 4 × 2 | 10 | 8 | 299 | 357 | 2,54 | 0,32 | 2,29 | 0,29 | — | — | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa 3D 128² × 64, front | MPI 4, changed | 10 | 4 | 423 | 472 | 1,80 | 0,45 | 1,73 | 0,43 | — | — | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa 3D 128² × 64, front | MPI 8, changed | 10 | 8 | 302 | 360 | 2,52 | 0,31 | 2,27 | 0,28 | — | — | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa 3D 128² × 64, front | OpenMP 4 (etap 10) | 10 | 4 | 193 | 225 | 3,95 | 0,99 | 3,63 | 0,91 | — | — | `mpi/skalowanie_mpi_msvc.csv` |  |
| lawa 3D 128² × 64, front | OpenMP 8 (etap 10, kontrola) | 10 | 8 | 126 | 183 | 6,03 | 0,75 | 4,47 | 0,56 | — | — | `mpi/skalowanie_mpi_msvc.csv` |  |
| lawa 3D 128² × 64, front | MPI 2, typy pochodne | 11 | 2 | 668 | — | 1,08 | 0,54 | — | — | — | — | `mpi_io/pomiar_msvc_cz1_raw.csv …` | S = S(m2) etapu 10 × faza m / d etapu 11 (×1.003); faza m2 w etapie 11: 670 ms, w etapie 10: 708 ms |
| lawa 3D 128² × 64, front | MPI 4, typy pochodne | 11 | 4 | 380 | — | 1,90 | 0,48 | — | — | — | — | `mpi_io/pomiar_msvc_cz1_raw.csv …` | S = S(m4) etapu 10 × faza m / d etapu 11 (×1.049); faza m4 w etapie 11: 399 ms, w etapie 10: 421 ms |
| lawa 3D 128² × 64, front | MPI 7, typy pochodne | 11 | 7 | 268 | — | 2,68 | 0,38 | — | — | — | — | `mpi_io/pomiar_msvc_cz1_raw.csv …` | S = S(m7) etapu 10 × faza m / d etapu 11 (×1.064); faza m7 w etapie 11: 285 ms, w etapie 10: 302 ms |
| lawa 3D 128² × 64, front | MPI 8, typy pochodne | 11 | 8 | 243 | — | 2,43 | 0,30 | — | — | — | — | `mpi_io/pomiar_msvc_cz1_raw.csv …` | S = S(m8) etapu 10 × faza m / d etapu 11 (×1.085); faza m8 w etapie 11: 264 ms, w etapie 10: 340 ms |
| lawa 3D 128² × 64, full | OpenMP 1 wątek | 9 | 1 | 12 489 | 12 550 | 1,00 | 1,00 | 1,00 | 1,00 | — | — | `omp/skalowanie_msvc.csv` |  |
| lawa 3D 128² × 64, full | OpenMP 2 wątki | 9 | 2 | 6 513 | 6 552 | 1,92 | 0,96 | 1,92 | 0,96 | 0,024 | 0,027 | `omp/skalowanie_msvc.csv` |  |
| lawa 3D 128² × 64, full | OpenMP 4 wątki | 9 | 4 | 3 230 | 3 271 | 3,87 | 0,97 | 3,84 | 0,96 | 0,024 | 0,027 | `omp/skalowanie_msvc.csv` |  |
| lawa 3D 128² × 64, full | OpenMP 6 wątków | 9 | 6 | 2 218 | 2 254 | 5,63 | 0,94 | 5,57 | 0,93 | 0,024 | 0,027 | `omp/skalowanie_msvc.csv` |  |
| lawa 3D 128² × 64, full | OpenMP 8 wątków | 9 | 8 | 1 971 | 2 017 | 6,34 | 0,79 | 6,22 | 0,78 | 0,024 | 0,027 | `omp/skalowanie_msvc.csv` |  |
| lawa 3D 128² × 64, full | MPI 1 proces | 10 | 1 | 13 415 | 13 475 | 1,00 | 1,00 | 1,00 | 1,00 | 0,089 | 0,092 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa 3D 128² × 64, full | MPI 2 procesy | 10 | 2 | 8 145 | 8 196 | 1,65 | 0,82 | 1,64 | 0,82 | 0,089 | 0,092 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa 3D 128² × 64, full | MPI 3 procesy | 10 | 3 | 5 406 | 5 456 | 2,48 | 0,83 | 2,47 | 0,82 | 0,089 | 0,092 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa 3D 128² × 64, full | MPI 4 procesy | 10 | 4 | 4 194 | 4 242 | 3,20 | 0,80 | 3,18 | 0,79 | 0,089 | 0,092 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa 3D 128² × 64, full | MPI 6 procesów | 10 | 6 | 2 871 | 2 923 | 4,67 | 0,78 | 4,61 | 0,77 | 0,089 | 0,092 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa 3D 128² × 64, full | MPI 7 procesów (bez procesora 0) | 10 | 7 | 2 506 | 2 562 | 5,35 | 0,76 | 5,26 | 0,75 | 0,089 | 0,092 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa 3D 128² × 64, full | MPI 8 procesów | 10 | 8 | 2 960 | 3 008 | 4,53 | 0,57 | 4,48 | 0,56 | 0,089 | 0,092 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa 3D 128² × 64, full | hybryda 2 × 4 | 10 | 8 | 2 487 | 2 539 | 5,39 | 0,67 | 5,31 | 0,66 | — | — | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa 3D 128² × 64, full | hybryda 4 × 2 | 10 | 8 | 2 719 | 2 767 | 4,93 | 0,62 | 4,87 | 0,61 | — | — | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa 3D 128² × 64, full | MPI 4, changed | 10 | 4 | 4 190 | 4 244 | 3,20 | 0,80 | 3,17 | 0,79 | — | — | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa 3D 128² × 64, full | MPI 8, changed | 10 | 8 | 2 820 | 2 962 | 4,76 | 0,59 | 4,55 | 0,57 | — | — | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| lawa 3D 128² × 64, full | OpenMP 4 (etap 10) | 10 | 4 | 3 750 | 3 786 | 3,58 | 0,89 | 3,56 | 0,89 | — | — | `mpi/skalowanie_mpi_msvc.csv` |  |
| lawa 3D 128² × 64, full | OpenMP 8 (etap 10, kontrola) | 10 | 8 | 2 164 | 2 207 | 6,20 | 0,78 | 6,11 | 0,76 | — | — | `mpi/skalowanie_mpi_msvc.csv` |  |
| lawa 3D 128² × 64, full | MPI 2, typy pochodne | 11 | 2 | 8 462 | — | 1,65 | 0,82 | — | — | — | — | `mpi_io/pomiar_msvc_cz1_raw.csv …` | S = S(m2) etapu 10 × faza m / d etapu 11 (×0.999); faza m2 w etapie 11: 8453 ms, w etapie 10: 8145 ms |
| lawa 3D 128² × 64, full | MPI 4, typy pochodne | 11 | 4 | 4 316 | — | 3,23 | 0,81 | — | — | — | — | `mpi_io/pomiar_msvc_cz1_raw.csv …` | S = S(m4) etapu 10 × faza m / d etapu 11 (×1.010); faza m4 w etapie 11: 4361 ms, w etapie 10: 4194 ms |
| lawa 3D 128² × 64, full | MPI 7, typy pochodne | 11 | 7 | 2 571 | — | 5,45 | 0,78 | — | — | — | — | `mpi_io/pomiar_msvc_cz1_raw.csv …` | S = S(m7) etapu 10 × faza m / d etapu 11 (×1.019); faza m7 w etapie 11: 2619 ms, w etapie 10: 2506 ms |
| lawa 3D 128² × 64, full | MPI 8, typy pochodne | 11 | 8 | 2 404 | — | 4,85 | 0,61 | — | — | — | — | `mpi_io/pomiar_msvc_cz1_raw.csv …` | S = S(m8) etapu 10 × faza m / d etapu 11 (×1.070); faza m8 w etapie 11: 2572 ms, w etapie 10: 2960 ms |
| classic 2000², VN | OpenMP 1 wątek | 9 | 1 | 530 | 659 | 1,00 | 1,00 | 1,00 | 1,00 | — | — | `omp/skalowanie_msvc.csv` |  |
| classic 2000², VN | OpenMP 2 wątki | 9 | 2 | 264 | 366 | 2,01 | 1,00 | 1,80 | 0,90 | 0,012 | 0,136 | `omp/skalowanie_msvc.csv` |  |
| classic 2000², VN | OpenMP 4 wątki | 9 | 4 | 134 | 224 | 3,95 | 0,99 | 2,94 | 0,74 | 0,012 | 0,136 | `omp/skalowanie_msvc.csv` |  |
| classic 2000², VN | OpenMP 6 wątków | 9 | 6 | 91,3 | 176 | 5,81 | 0,97 | 3,74 | 0,62 | 0,012 | 0,136 | `omp/skalowanie_msvc.csv` |  |
| classic 2000², VN | OpenMP 8 wątków | 9 | 8 | 79,4 | 180 | 6,67 | 0,83 | 3,66 | 0,46 | 0,012 | 0,136 | `omp/skalowanie_msvc.csv` |  |
| classic 2000², VN | MPI 1 proces | 10 | 1 | 539 | 711 | 1,00 | 1,00 | 1,00 | 1,00 | 0,017 | 0,176 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| classic 2000², VN | MPI 2 procesy | 10 | 2 | 263 | 404 | 2,05 | 1,02 | 1,76 | 0,88 | 0,017 | 0,176 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| classic 2000², VN | MPI 3 procesy | 10 | 3 | 187 | 317 | 2,88 | 0,96 | 2,24 | 0,75 | 0,017 | 0,176 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| classic 2000², VN | MPI 4 procesy | 10 | 4 | 137 | 265 | 3,94 | 0,99 | 2,68 | 0,67 | 0,017 | 0,176 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| classic 2000², VN | MPI 6 procesów | 10 | 6 | 95,8 | 220 | 5,63 | 0,94 | 3,24 | 0,54 | 0,017 | 0,176 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| classic 2000², VN | MPI 7 procesów (bez procesora 0) | 10 | 7 | 80,7 | 203 | 6,68 | 0,95 | 3,50 | 0,50 | 0,017 | 0,176 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| classic 2000², VN | MPI 8 procesów | 10 | 8 | 90,3 | 222 | 5,97 | 0,75 | 3,20 | 0,40 | 0,017 | 0,176 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| classic 2000², VN | hybryda 2 × 4 | 10 | 8 | 107 | 236 | 5,02 | 0,63 | 3,01 | 0,38 | — | — | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| classic 2000², VN | hybryda 4 × 2 | 10 | 8 | 97,0 | 261 | 5,56 | 0,69 | 2,73 | 0,34 | — | — | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| classic 2000², VN | MPI 4, changed | 10 | 4 | 137 | 264 | 3,94 | 0,98 | 2,69 | 0,67 | — | — | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| classic 2000², VN | MPI 8, changed | 10 | 8 | 91,2 | 214 | 5,91 | 0,74 | 3,32 | 0,41 | — | — | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| classic 2000², VN | OpenMP 4 (etap 10) | 10 | 4 | 134 | 222 | 4,02 | 1,00 | 3,20 | 0,80 | — | — | `mpi/skalowanie_mpi_msvc.csv` |  |
| classic 2000², VN | OpenMP 8 (etap 10, kontrola) | 10 | 8 | 86,1 | 186 | 6,26 | 0,78 | 3,82 | 0,48 | — | — | `mpi/skalowanie_mpi_msvc.csv` |  |
| classic 300³, VN | przed etapem 8 | 8 | 1 | 38 122 | — | — | — | — | — | — | — | `profile_2026-10-17_przed2.csv` | profil z zapisem txt + bin — total nieporównywalny z etapami 9–11 |
| classic 300³, VN | po etapie 8 | 8 | 1 | 3 663 | — | 10,41 | 10,41 | — | — | — | — | `profile_2026-10-17_po.csv` | S = przed / po (zysk z algorytmu); profil z zapisem txt + bin — total nieporównywalny z etapami 9–11 |
| classic 300³, VN | OpenMP 1 wątek | 9 | 1 | 3 406 | 4 396 | 1,00 | 1,00 | 1,00 | 1,00 | — | — | `omp/skalowanie_msvc.csv` |  |
| classic 300³, VN | OpenMP 2 wątki | 9 | 2 | 1 884 | 2 634 | 1,81 | 0,90 | 1,67 | 0,83 | 0,082 | 0,193 | `omp/skalowanie_msvc.csv` |  |
| classic 300³, VN | OpenMP 4 wątki | 9 | 4 | 1 025 | 1 691 | 3,32 | 0,83 | 2,60 | 0,65 | 0,082 | 0,193 | `omp/skalowanie_msvc.csv` |  |
| classic 300³, VN | OpenMP 6 wątków | 9 | 6 | 774 | 1 395 | 4,40 | 0,73 | 3,15 | 0,53 | 0,082 | 0,193 | `omp/skalowanie_msvc.csv` |  |
| classic 300³, VN | OpenMP 8 wątków | 9 | 8 | 707 | 1 365 | 4,82 | 0,60 | 3,22 | 0,40 | 0,082 | 0,193 | `omp/skalowanie_msvc.csv` |  |
| classic 300³, VN | MPI 1 proces | 10 | 1 | 3 379 | 4 539 | 1,00 | 1,00 | 1,00 | 1,00 | 0,155 | 0,301 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| classic 300³, VN | MPI 2 procesy | 10 | 2 | 1 943 | 2 922 | 1,74 | 0,87 | 1,55 | 0,78 | 0,155 | 0,301 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| classic 300³, VN | MPI 3 procesy | 10 | 3 | 1 427 | 2 425 | 2,37 | 0,79 | 1,87 | 0,62 | 0,155 | 0,301 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| classic 300³, VN | MPI 4 procesy | 10 | 4 | 1 179 | 2 109 | 2,87 | 0,72 | 2,15 | 0,54 | 0,155 | 0,301 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| classic 300³, VN | MPI 6 procesów | 10 | 6 | 947 | 1 835 | 3,57 | 0,59 | 2,47 | 0,41 | 0,155 | 0,301 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| classic 300³, VN | MPI 7 procesów (bez procesora 0) | 10 | 7 | 932 | 1 818 | 3,62 | 0,52 | 2,50 | 0,36 | 0,155 | 0,301 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| classic 300³, VN | MPI 8 procesów | 10 | 8 | 1 019 | 1 877 | 3,32 | 0,41 | 2,42 | 0,30 | 0,155 | 0,301 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| classic 300³, VN | hybryda 2 × 4 | 10 | 8 | 866 | 1 675 | 3,90 | 0,49 | 2,71 | 0,34 | — | — | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| classic 300³, VN | hybryda 4 × 2 | 10 | 8 | 871 | 1 608 | 3,88 | 0,48 | 2,82 | 0,35 | — | — | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| classic 300³, VN | MPI 4, changed | 10 | 4 | 1 202 | 2 079 | 2,81 | 0,70 | 2,18 | 0,55 | — | — | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| classic 300³, VN | MPI 8, changed | 10 | 8 | 1 059 | 2 007 | 3,19 | 0,40 | 2,26 | 0,28 | — | — | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| classic 300³, VN | OpenMP 4 (etap 10) | 10 | 4 | 1 029 | 1 703 | 3,28 | 0,82 | 2,67 | 0,67 | — | — | `mpi/skalowanie_mpi_msvc.csv` |  |
| classic 300³, VN | OpenMP 8 (etap 10, kontrola) | 10 | 8 | 717 | 1 406 | 4,72 | 0,59 | 3,23 | 0,40 | — | — | `mpi/skalowanie_mpi_msvc.csv` |  |
| classic 300³, VN | MPI 2, typy pochodne | 11 | 2 | 1 866 | — | 1,79 | 0,89 | — | — | — | — | `mpi_io/pomiar_msvc_cz1_raw.csv …` | S = S(m2) etapu 10 × faza m / d etapu 11 (×1.028); faza m2 w etapie 11: 1919 ms, w etapie 10: 1943 ms |
| classic 300³, VN | MPI 4, typy pochodne | 11 | 4 | 1 105 | — | 2,98 | 0,74 | — | — | — | — | `mpi_io/pomiar_msvc_cz1_raw.csv …` | S = S(m4) etapu 10 × faza m / d etapu 11 (×1.039); faza m4 w etapie 11: 1148 ms, w etapie 10: 1179 ms |
| classic 300³, VN | MPI 7, typy pochodne | 11 | 7 | 816 | — | 3,90 | 0,56 | — | — | — | — | `mpi_io/pomiar_msvc_cz1_raw.csv …` | S = S(m7) etapu 10 × faza m / d etapu 11 (×1.077); faza m7 w etapie 11: 879 ms, w etapie 10: 932 ms |
| classic 300³, VN | MPI 8, typy pochodne | 11 | 8 | 789 | — | 3,64 | 0,46 | — | — | — | — | `mpi_io/pomiar_msvc_cz1_raw.csv …` | S = S(m8) etapu 10 × faza m / d etapu 11 (×1.099); faza m8 w etapie 11: 867 ms, w etapie 10: 1019 ms |
| MC szachownica 1000², VN | przed etapem 8 | 8 | 1 | 16 321 | — | — | — | — | — | — | — | `profile_2026-10-17_przed2.csv` | profil z zapisem txt + bin — total nieporównywalny z etapami 9–11 |
| MC szachownica 1000², VN | po etapie 8 | 8 | 1 | 9 401 | — | 1,74 | 1,74 | — | — | — | — | `profile_2026-10-17_po.csv` | S = przed / po (zysk z algorytmu); profil z zapisem txt + bin — total nieporównywalny z etapami 9–11 |
| MC szachownica 1000², VN | MC random, 1 wątek | 9 | 1 | 8 324 | 8 788 | — | — | — | — | — | — | `omp/skalowanie_msvc.csv` | wariant naiwny (sekwencyjny z definicji) |
| MC szachownica 1000², VN | OpenMP 1 wątek | 9 | 1 | 2 059 | 2 532 | 1,00 | 1,00 | 1,00 | 1,00 | — | — | `omp/skalowanie_msvc.csv` | szachownica przy 1 wątku: ×4.04 względem wariantu random (kolejność komórek zamiast losowych adresów) |
| MC szachownica 1000², VN | OpenMP 2 wątki | 9 | 2 | 1 044 | 1 491 | 1,97 | 0,99 | 1,70 | 0,85 | 0,021 | 0,185 | `omp/skalowanie_msvc.csv` |  |
| MC szachownica 1000², VN | OpenMP 4 wątki | 9 | 4 | 529 | 967 | 3,89 | 0,97 | 2,62 | 0,65 | 0,021 | 0,185 | `omp/skalowanie_msvc.csv` |  |
| MC szachownica 1000², VN | OpenMP 6 wątków | 9 | 6 | 358 | 792 | 5,75 | 0,96 | 3,20 | 0,53 | 0,021 | 0,185 | `omp/skalowanie_msvc.csv` |  |
| MC szachownica 1000², VN | OpenMP 8 wątków | 9 | 8 | 333 | 768 | 6,18 | 0,77 | 3,30 | 0,41 | 0,021 | 0,185 | `omp/skalowanie_msvc.csv` |  |
| MC szachownica 1000², VN | MPI 1 proces | 10 | 1 | 2 052 | 2 571 | 1,00 | 1,00 | 1,00 | 1,00 | 0,014 | 0,169 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| MC szachownica 1000², VN | MPI 2 procesy | 10 | 2 | 1 031 | 1 495 | 1,99 | 1,00 | 1,72 | 0,86 | 0,014 | 0,169 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| MC szachownica 1000², VN | MPI 3 procesy | 10 | 3 | 689 | 1 135 | 2,98 | 0,99 | 2,27 | 0,76 | 0,014 | 0,169 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| MC szachownica 1000², VN | MPI 4 procesy | 10 | 4 | 518 | 954 | 3,96 | 0,99 | 2,70 | 0,67 | 0,014 | 0,169 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| MC szachownica 1000², VN | MPI 6 procesów | 10 | 6 | 351 | 770 | 5,85 | 0,97 | 3,34 | 0,56 | 0,014 | 0,169 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| MC szachownica 1000², VN | MPI 7 procesów (bez procesora 0) | 10 | 7 | 305 | 727 | 6,72 | 0,96 | 3,54 | 0,51 | 0,014 | 0,169 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| MC szachownica 1000², VN | MPI 8 procesów | 10 | 8 | 340 | 758 | 6,03 | 0,75 | 3,39 | 0,42 | 0,014 | 0,169 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| MC szachownica 1000², VN | hybryda 2 × 4 | 10 | 8 | 332 | 794 | 6,17 | 0,77 | 3,24 | 0,40 | — | — | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| MC szachownica 1000², VN | hybryda 4 × 2 | 10 | 8 | 328 | 762 | 6,26 | 0,78 | 3,38 | 0,42 | — | — | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| MC szachownica 1000², VN | MPI 4, changed | 10 | 4 | 519 | 953 | 3,96 | 0,99 | 2,70 | 0,67 | — | — | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| MC szachownica 1000², VN | MPI 8, changed | 10 | 8 | 336 | 776 | 6,11 | 0,76 | 3,31 | 0,41 | — | — | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| MC szachownica 1000², VN | OpenMP 4 (etap 10) | 10 | 4 | 527 | 957 | 3,90 | 0,97 | 2,69 | 0,67 | — | — | `mpi/skalowanie_mpi_msvc.csv` |  |
| MC szachownica 1000², VN | OpenMP 8 (etap 10, kontrola) | 10 | 8 | 336 | 767 | 6,10 | 0,76 | 3,35 | 0,42 | — | — | `mpi/skalowanie_mpi_msvc.csv` |  |
| MC szachownica 100³, Moore | przed etapem 8 | 8 | 1 | 42 850 | — | — | — | — | — | — | — | `profile_2026-10-17_przed2.csv` | profil z zapisem txt + bin — total nieporównywalny z etapami 9–11 |
| MC szachownica 100³, Moore | po etapie 8 | 8 | 1 | 21 942 | — | 1,95 | 1,95 | — | — | — | — | `profile_2026-10-17_po.csv` | S = przed / po (zysk z algorytmu); profil z zapisem txt + bin — total nieporównywalny z etapami 9–11 |
| MC szachownica 100³, Moore | MC random, 1 wątek | 9 | 1 | 18 860 | 19 982 | — | — | — | — | — | — | `omp/skalowanie_msvc.csv` | wariant naiwny (sekwencyjny z definicji) |
| MC szachownica 100³, Moore | OpenMP 1 wątek | 9 | 1 | 5 743 | 6 902 | 1,00 | 1,00 | 1,00 | 1,00 | — | — | `omp/skalowanie_msvc.csv` | szachownica przy 1 wątku: ×3.28 względem wariantu random (kolejność komórek zamiast losowych adresów) |
| MC szachownica 100³, Moore | OpenMP 2 wątki | 9 | 2 | 3 093 | 4 159 | 1,86 | 0,93 | 1,66 | 0,83 | 0,034 | 0,169 | `omp/skalowanie_msvc.csv` |  |
| MC szachownica 100³, Moore | OpenMP 4 wątki | 9 | 4 | 1 517 | 2 526 | 3,79 | 0,95 | 2,73 | 0,68 | 0,034 | 0,169 | `omp/skalowanie_msvc.csv` |  |
| MC szachownica 100³, Moore | OpenMP 6 wątków | 9 | 6 | 1 039 | 2 045 | 5,53 | 0,92 | 3,38 | 0,56 | 0,034 | 0,169 | `omp/skalowanie_msvc.csv` |  |
| MC szachownica 100³, Moore | OpenMP 8 wątków | 9 | 8 | 948 | 1 944 | 6,06 | 0,76 | 3,55 | 0,44 | 0,034 | 0,169 | `omp/skalowanie_msvc.csv` |  |
| MC szachownica 100³, Moore | MPI 1 proces | 10 | 1 | 5 741 | 6 906 | 1,00 | 1,00 | 1,00 | 1,00 | 0,033 | 0,157 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| MC szachownica 100³, Moore | MPI 2 procesy | 10 | 2 | 2 940 | 3 982 | 1,95 | 0,98 | 1,73 | 0,87 | 0,033 | 0,157 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| MC szachownica 100³, Moore | MPI 3 procesy | 10 | 3 | 2 014 | 2 993 | 2,85 | 0,95 | 2,31 | 0,77 | 0,033 | 0,157 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| MC szachownica 100³, Moore | MPI 4 procesy | 10 | 4 | 1 519 | 2 468 | 3,78 | 0,94 | 2,80 | 0,70 | 0,033 | 0,157 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| MC szachownica 100³, Moore | MPI 6 procesów | 10 | 6 | 1 061 | 1 991 | 5,41 | 0,90 | 3,47 | 0,58 | 0,033 | 0,157 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| MC szachownica 100³, Moore | MPI 7 procesów (bez procesora 0) | 10 | 7 | 963 | 1 882 | 5,96 | 0,85 | 3,67 | 0,52 | 0,033 | 0,157 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| MC szachownica 100³, Moore | MPI 8 procesów | 10 | 8 | 1 035 | 2 004 | 5,55 | 0,69 | 3,45 | 0,43 | 0,033 | 0,157 | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| MC szachownica 100³, Moore | hybryda 2 × 4 | 10 | 8 | 1 090 | 2 049 | 5,27 | 0,66 | 3,37 | 0,42 | — | — | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| MC szachownica 100³, Moore | hybryda 4 × 2 | 10 | 8 | 956 | 1 883 | 6,00 | 0,75 | 3,67 | 0,46 | — | — | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| MC szachownica 100³, Moore | MPI 4, changed | 10 | 4 | 1 509 | 2 461 | 3,80 | 0,95 | 2,81 | 0,70 | — | — | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| MC szachownica 100³, Moore | MPI 8, changed | 10 | 8 | 1 028 | 2 007 | 5,58 | 0,70 | 3,44 | 0,43 | — | — | `mpi/skalowanie_mpi_msvc.csv` | total zawiera MPI_Init |
| MC szachownica 100³, Moore | OpenMP 4 (etap 10) | 10 | 4 | 1 497 | 2 465 | 3,83 | 0,96 | 2,80 | 0,70 | — | — | `mpi/skalowanie_mpi_msvc.csv` |  |
| MC szachownica 100³, Moore | OpenMP 8 (etap 10, kontrola) | 10 | 8 | 916 | 1 888 | 6,27 | 0,78 | 3,66 | 0,46 | — | — | `mpi/skalowanie_mpi_msvc.csv` |  |
| MC szachownica 100³, Moore | MPI 2, typy pochodne | 11 | 2 | 2 888 | — | 1,96 | 0,98 | — | — | — | — | `mpi_io/pomiar_msvc_cz1_raw.csv …` | S = S(m2) etapu 10 × faza m / d etapu 11 (×1.002); faza m2 w etapie 11: 2894 ms, w etapie 10: 2940 ms |
| MC szachownica 100³, Moore | MPI 4, typy pochodne | 11 | 4 | 1 497 | — | 3,86 | 0,96 | — | — | — | — | `mpi_io/pomiar_msvc_cz1_raw.csv …` | S = S(m4) etapu 10 × faza m / d etapu 11 (×1.021); faza m4 w etapie 11: 1529 ms, w etapie 10: 1519 ms |
| MC szachownica 100³, Moore | MPI 7, typy pochodne | 11 | 7 | 934 | — | 6,07 | 0,87 | — | — | — | — | `mpi_io/pomiar_msvc_cz1_raw.csv …` | S = S(m7) etapu 10 × faza m / d etapu 11 (×1.018); faza m7 w etapie 11: 951 ms, w etapie 10: 963 ms |
| MC szachownica 100³, Moore | MPI 8, typy pochodne | 11 | 8 | 871 | — | 5,53 | 0,69 | — | — | — | — | `mpi_io/pomiar_msvc_cz1_raw.csv …` | S = S(m8) etapu 10 × faza m / d etapu 11 (×0.997); faza m8 w etapie 11: 868 ms, w etapie 10: 1035 ms |

## Wszystkie warianty — GCC / OpenMPI

| Przypadek | Wariant | Etap | Rdzenie | T faza [ms] | T total [ms] | S faza | E faza | S total | E total | f faza | f total | Źródło | Uwagi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| lawa `etna_real`, front | przed etapem 8 | 8 | 1 | 24 621 | 24 729 | — | — | — | — | — | — | `profile_2026-10-17_przed2.csv` |  |
| lawa `etna_real`, front | po etapie 8 | 8 | 1 | 77,3 | 148 | 318,55 | 318,55 | 167,43 | 167,43 | — | — | `profile_2026-10-17_po.csv` | S = przed / po (zysk z algorytmu) |
| lawa `etna_real`, front | OpenMP 1 wątek | 9 | 1 | 79,1 | 128 | 1,00 | 1,00 | 1,00 | 1,00 | — | — | `omp/skalowanie_gcc.csv` |  |
| lawa `etna_real`, front | OpenMP 2 wątki | 9 | 2 | 44,7 | 91,4 | 1,77 | 0,89 | 1,40 | 0,70 | 0,136 | 0,430 | `omp/skalowanie_gcc.csv` |  |
| lawa `etna_real`, front | OpenMP 4 wątki | 9 | 4 | 27,3 | 70,7 | 2,90 | 0,73 | 1,81 | 0,45 | 0,136 | 0,430 | `omp/skalowanie_gcc.csv` |  |
| lawa `etna_real`, front | OpenMP 6 wątków | 9 | 6 | 19,0 | 66,2 | 4,17 | 0,70 | 1,94 | 0,32 | 0,136 | 0,430 | `omp/skalowanie_gcc.csv` |  |
| lawa `etna_real`, front | OpenMP 8 wątków | 9 | 8 | 23,0 | 67,8 | 3,44 | 0,43 | 1,89 | 0,24 | 0,136 | 0,430 | `omp/skalowanie_gcc.csv` |  |
| lawa `etna_real`, front | MPI 1 proces | 10 | 1 | 81,7 | 404 | 1,00 | 1,00 | 1,00 | 1,00 | 1,000 | 1,000 | `mpi/skalowanie_mpi_gcc.csv` | total zawiera MPI_Init |
| lawa `etna_real`, front | MPI 3 procesy | 10 | 3 | 145 | 504 | 0,56 | 0,19 | 0,80 | 0,27 | 1,000 | 1,000 | `mpi/skalowanie_mpi_gcc.csv` | total zawiera MPI_Init |
| lawa `etna_real`, front | MPI 8 procesów | 10 | 8 | 176 | 614 | 0,46 | 0,06 | 0,66 | 0,08 | 1,000 | 1,000 | `mpi/skalowanie_mpi_gcc.csv` | total zawiera MPI_Init |
| lawa `etna_real`, front | hybryda 2 × 4 | 10 | 8 | 80,3 | 428 | 1,02 | 0,13 | 0,95 | 0,12 | — | — | `mpi/skalowanie_mpi_gcc.csv` | total zawiera MPI_Init |
| lawa `etna_real`, front | OpenMP 8 (etap 10, kontrola) | 10 | 8 | 21,2 | 65,6 | 3,86 | 0,48 | 6,16 | 0,77 | — | — | `mpi/skalowanie_mpi_gcc.csv` |  |
| lawa 3D 128² × 64, front | OpenMP 1 wątek | 9 | 1 | 666 | 704 | 1,00 | 1,00 | 1,00 | 1,00 | — | — | `omp/skalowanie_gcc.csv` |  |
| lawa 3D 128² × 64, front | OpenMP 2 wątki | 9 | 2 | 351 | 377 | 1,90 | 0,95 | 1,87 | 0,93 | 0,064 | 0,099 | `omp/skalowanie_gcc.csv` |  |
| lawa 3D 128² × 64, front | OpenMP 4 wątki | 9 | 4 | 192 | 221 | 3,47 | 0,87 | 3,19 | 0,80 | 0,064 | 0,099 | `omp/skalowanie_gcc.csv` |  |
| lawa 3D 128² × 64, front | OpenMP 6 wątków | 9 | 6 | 144 | 179 | 4,64 | 0,77 | 3,93 | 0,66 | 0,064 | 0,099 | `omp/skalowanie_gcc.csv` |  |
| lawa 3D 128² × 64, front | OpenMP 8 wątków | 9 | 8 | 130 | 157 | 5,11 | 0,64 | 4,49 | 0,56 | 0,064 | 0,099 | `omp/skalowanie_gcc.csv` |  |
| lawa 3D 128² × 64, front | MPI 1 proces | 10 | 1 | 681 | 976 | 1,00 | 1,00 | 1,00 | 1,00 | 0,449 | 0,738 | `mpi/skalowanie_mpi_gcc.csv` | total zawiera MPI_Init |
| lawa 3D 128² × 64, front | MPI 3 procesy | 10 | 3 | 501 | 845 | 1,36 | 0,45 | 1,15 | 0,38 | 0,449 | 0,738 | `mpi/skalowanie_mpi_gcc.csv` | total zawiera MPI_Init |
| lawa 3D 128² × 64, front | MPI 8 procesów | 10 | 8 | 298 | 722 | 2,28 | 0,29 | 1,35 | 0,17 | 0,449 | 0,738 | `mpi/skalowanie_mpi_gcc.csv` | total zawiera MPI_Init |
| lawa 3D 128² × 64, front | hybryda 2 × 4 | 10 | 8 | 244 | 571 | 2,79 | 0,35 | 1,71 | 0,21 | — | — | `mpi/skalowanie_mpi_gcc.csv` | total zawiera MPI_Init |
| lawa 3D 128² × 64, front | OpenMP 8 (etap 10, kontrola) | 10 | 8 | 151 | 183 | 4,52 | 0,57 | 5,34 | 0,67 | — | — | `mpi/skalowanie_mpi_gcc.csv` |  |
| lawa 3D 128² × 64, front | MPI 8, typy pochodne | 11 | 8 | 252 | — | 2,56 | 0,32 | — | — | — | — | `mpi_io/pomiar_gcc_cz1_raw.csv …` | S = S(m8) etapu 10 × faza m / d etapu 11 (×1.121); faza m8 w etapie 11: 283 ms, w etapie 10: 298 ms |
| lawa 3D 128² × 64, full | OpenMP 1 wątek | 9 | 1 | 12 227 | 12 267 | 1,00 | 1,00 | 1,00 | 1,00 | — | — | `omp/skalowanie_gcc.csv` |  |
| lawa 3D 128² × 64, full | OpenMP 2 wątki | 9 | 2 | 6 157 | 6 196 | 1,99 | 0,99 | 1,98 | 0,99 | 0,028 | 0,031 | `omp/skalowanie_gcc.csv` |  |
| lawa 3D 128² × 64, full | OpenMP 4 wątki | 9 | 4 | 3 233 | 3 265 | 3,78 | 0,95 | 3,76 | 0,94 | 0,028 | 0,031 | `omp/skalowanie_gcc.csv` |  |
| lawa 3D 128² × 64, full | OpenMP 6 wątków | 9 | 6 | 2 325 | 2 370 | 5,26 | 0,88 | 5,18 | 0,86 | 0,028 | 0,031 | `omp/skalowanie_gcc.csv` |  |
| lawa 3D 128² × 64, full | OpenMP 8 wątków | 9 | 8 | 1 953 | 1 990 | 6,26 | 0,78 | 6,16 | 0,77 | 0,028 | 0,031 | `omp/skalowanie_gcc.csv` |  |
| lawa 3D 128² × 64, full | MPI 1 proces | 10 | 1 | 11 621 | 11 941 | 1,00 | 1,00 | 1,00 | 1,00 | 0,085 | 0,117 | `mpi/skalowanie_mpi_gcc.csv` | total zawiera MPI_Init |
| lawa 3D 128² × 64, full | MPI 3 procesy | 10 | 3 | 4 454 | 4 805 | 2,61 | 0,87 | 2,49 | 0,83 | 0,085 | 0,117 | `mpi/skalowanie_mpi_gcc.csv` | total zawiera MPI_Init |
| lawa 3D 128² × 64, full | MPI 8 procesów | 10 | 8 | 2 374 | 2 801 | 4,89 | 0,61 | 4,26 | 0,53 | 0,085 | 0,117 | `mpi/skalowanie_mpi_gcc.csv` | total zawiera MPI_Init |
| lawa 3D 128² × 64, full | hybryda 2 × 4 | 10 | 8 | 2 125 | 2 458 | 5,47 | 0,68 | 4,86 | 0,61 | — | — | `mpi/skalowanie_mpi_gcc.csv` | total zawiera MPI_Init |
| lawa 3D 128² × 64, full | OpenMP 8 (etap 10, kontrola) | 10 | 8 | 1 966 | 2 002 | 5,91 | 0,74 | 5,96 | 0,75 | — | — | `mpi/skalowanie_mpi_gcc.csv` |  |
| classic 2000², VN | OpenMP 1 wątek | 9 | 1 | 491 | 636 | 1,00 | 1,00 | 1,00 | 1,00 | — | — | `omp/skalowanie_gcc.csv` |  |
| classic 2000², VN | OpenMP 2 wątki | 9 | 2 | 249 | 349 | 1,97 | 0,99 | 1,82 | 0,91 | 0,077 | 0,172 | `omp/skalowanie_gcc.csv` |  |
| classic 2000², VN | OpenMP 4 wątki | 9 | 4 | 140 | 223 | 3,52 | 0,88 | 2,85 | 0,71 | 0,077 | 0,172 | `omp/skalowanie_gcc.csv` |  |
| classic 2000², VN | OpenMP 6 wątków | 9 | 6 | 114 | 197 | 4,31 | 0,72 | 3,22 | 0,54 | 0,077 | 0,172 | `omp/skalowanie_gcc.csv` |  |
| classic 2000², VN | OpenMP 8 wątków | 9 | 8 | 113 | 203 | 4,33 | 0,54 | 3,13 | 0,39 | 0,077 | 0,172 | `omp/skalowanie_gcc.csv` |  |
| classic 2000², VN | MPI 1 proces | 10 | 1 | 487 | 904 | 1,00 | 1,00 | 1,00 | 1,00 | 0,083 | 0,591 | `mpi/skalowanie_mpi_gcc.csv` | total zawiera MPI_Init |
| classic 2000², VN | MPI 3 procesy | 10 | 3 | 177 | 616 | 2,76 | 0,92 | 1,47 | 0,49 | 0,083 | 0,591 | `mpi/skalowanie_mpi_gcc.csv` | total zawiera MPI_Init |
| classic 2000², VN | MPI 8 procesów | 10 | 8 | 106 | 611 | 4,59 | 0,57 | 1,48 | 0,18 | 0,083 | 0,591 | `mpi/skalowanie_mpi_gcc.csv` | total zawiera MPI_Init |
| classic 2000², VN | hybryda 2 × 4 | 10 | 8 | 117 | 509 | 4,17 | 0,52 | 1,77 | 0,22 | — | — | `mpi/skalowanie_mpi_gcc.csv` | total zawiera MPI_Init |
| classic 2000², VN | OpenMP 8 (etap 10, kontrola) | 10 | 8 | 90,1 | 180 | 5,41 | 0,68 | 5,03 | 0,63 | — | — | `mpi/skalowanie_mpi_gcc.csv` |  |
| classic 300³, VN | przed etapem 8 | 8 | 1 | 34 540 | — | — | — | — | — | — | — | `profile_2026-10-17_przed2.csv` | profil z zapisem txt + bin — total nieporównywalny z etapami 9–11 |
| classic 300³, VN | po etapie 8 | 8 | 1 | 3 423 | — | 10,09 | 10,09 | — | — | — | — | `profile_2026-10-17_po.csv` | S = przed / po (zysk z algorytmu); profil z zapisem txt + bin — total nieporównywalny z etapami 9–11 |
| classic 300³, VN | OpenMP 1 wątek | 9 | 1 | 3 151 | 4 196 | 1,00 | 1,00 | 1,00 | 1,00 | — | — | `omp/skalowanie_gcc.csv` |  |
| classic 300³, VN | OpenMP 2 wątki | 9 | 2 | 1 789 | 2 573 | 1,76 | 0,88 | 1,63 | 0,82 | 0,160 | 0,265 | `omp/skalowanie_gcc.csv` |  |
| classic 300³, VN | OpenMP 4 wątki | 9 | 4 | 1 068 | 1 771 | 2,95 | 0,74 | 2,37 | 0,59 | 0,160 | 0,265 | `omp/skalowanie_gcc.csv` |  |
| classic 300³, VN | OpenMP 6 wątków | 9 | 6 | 772 | 1 427 | 4,08 | 0,68 | 2,94 | 0,49 | 0,160 | 0,265 | `omp/skalowanie_gcc.csv` |  |
| classic 300³, VN | OpenMP 8 wątków | 9 | 8 | 1 103 | 1 835 | 2,86 | 0,36 | 2,29 | 0,29 | 0,160 | 0,265 | `omp/skalowanie_gcc.csv` |  |
| classic 300³, VN | MPI 1 proces | 10 | 1 | 3 196 | 4 609 | 1,00 | 1,00 | 1,00 | 1,00 | 0,183 | 0,367 | `mpi/skalowanie_mpi_gcc.csv` | total zawiera MPI_Init |
| classic 300³, VN | MPI 3 procesy | 10 | 3 | 1 389 | 2 497 | 2,30 | 0,77 | 1,85 | 0,62 | 0,183 | 0,367 | `mpi/skalowanie_mpi_gcc.csv` | total zawiera MPI_Init |
| classic 300³, VN | MPI 8 procesów | 10 | 8 | 961 | 2 187 | 3,33 | 0,42 | 2,11 | 0,26 | 0,183 | 0,367 | `mpi/skalowanie_mpi_gcc.csv` | total zawiera MPI_Init |
| classic 300³, VN | hybryda 2 × 4 | 10 | 8 | 768 | 1 744 | 4,16 | 0,52 | 2,64 | 0,33 | — | — | `mpi/skalowanie_mpi_gcc.csv` | total zawiera MPI_Init |
| classic 300³, VN | OpenMP 8 (etap 10, kontrola) | 10 | 8 | 743 | 1 345 | 4,30 | 0,54 | 3,43 | 0,43 | — | — | `mpi/skalowanie_mpi_gcc.csv` |  |
| classic 300³, VN | MPI 8, typy pochodne | 11 | 8 | 928 | — | 3,44 | 0,43 | — | — | — | — | `mpi_io/pomiar_gcc_cz1_raw.csv …` | S = S(m8) etapu 10 × faza m / d etapu 11 (×1.034); faza m8 w etapie 11: 960 ms, w etapie 10: 961 ms |
| MC szachownica 1000², VN | przed etapem 8 | 8 | 1 | 12 331 | — | — | — | — | — | — | — | `profile_2026-10-17_przed2.csv` | profil z zapisem txt + bin — total nieporównywalny z etapami 9–11 |
| MC szachownica 1000², VN | po etapie 8 | 8 | 1 | 8 588 | — | 1,44 | 1,44 | — | — | — | — | `profile_2026-10-17_po.csv` | S = przed / po (zysk z algorytmu); profil z zapisem txt + bin — total nieporównywalny z etapami 9–11 |
| MC szachownica 1000², VN | OpenMP 1 wątek | 9 | 1 | 1 919 | 2 334 | 1,00 | 1,00 | 1,00 | 1,00 | — | — | `omp/skalowanie_gcc.csv` |  |
| MC szachownica 1000², VN | OpenMP 2 wątki | 9 | 2 | 972 | 1 359 | 1,97 | 0,99 | 1,72 | 0,86 | 0,050 | 0,209 | `omp/skalowanie_gcc.csv` |  |
| MC szachownica 1000², VN | OpenMP 4 wątki | 9 | 4 | 508 | 889 | 3,78 | 0,94 | 2,63 | 0,66 | 0,050 | 0,209 | `omp/skalowanie_gcc.csv` |  |
| MC szachownica 1000², VN | OpenMP 6 wątków | 9 | 6 | 373 | 789 | 5,14 | 0,86 | 2,96 | 0,49 | 0,050 | 0,209 | `omp/skalowanie_gcc.csv` |  |
| MC szachownica 1000², VN | OpenMP 8 wątków | 9 | 8 | 408 | 808 | 4,70 | 0,59 | 2,89 | 0,36 | 0,050 | 0,209 | `omp/skalowanie_gcc.csv` |  |
| MC szachownica 1000², VN | MPI 1 proces | 10 | 1 | 2 010 | 2 762 | 1,00 | 1,00 | 1,00 | 1,00 | 0,045 | 0,312 | `mpi/skalowanie_mpi_gcc.csv` | total zawiera MPI_Init |
| MC szachownica 1000², VN | MPI 3 procesy | 10 | 3 | 674 | 1 441 | 2,98 | 0,99 | 1,92 | 0,64 | 0,045 | 0,312 | `mpi/skalowanie_mpi_gcc.csv` | total zawiera MPI_Init |
| MC szachownica 1000², VN | MPI 8 procesów | 10 | 8 | 372 | 1 140 | 5,40 | 0,68 | 2,42 | 0,30 | 0,045 | 0,312 | `mpi/skalowanie_mpi_gcc.csv` | total zawiera MPI_Init |
| MC szachownica 1000², VN | hybryda 2 × 4 | 10 | 8 | 336 | 1 030 | 5,98 | 0,75 | 2,68 | 0,34 | — | — | `mpi/skalowanie_mpi_gcc.csv` | total zawiera MPI_Init |
| MC szachownica 1000², VN | OpenMP 8 (etap 10, kontrola) | 10 | 8 | 341 | 730 | 5,89 | 0,74 | 3,78 | 0,47 | — | — | `mpi/skalowanie_mpi_gcc.csv` |  |
| MC szachownica 100³, Moore | przed etapem 8 | 8 | 1 | 27 793 | — | — | — | — | — | — | — | `profile_2026-10-17_przed2.csv` | profil z zapisem txt + bin — total nieporównywalny z etapami 9–11 |
| MC szachownica 100³, Moore | po etapie 8 | 8 | 1 | 19 920 | — | 1,40 | 1,40 | — | — | — | — | `profile_2026-10-17_po.csv` | S = przed / po (zysk z algorytmu); profil z zapisem txt + bin — total nieporównywalny z etapami 9–11 |
| MC szachownica 100³, Moore | OpenMP 1 wątek | 9 | 1 | 5 273 | 6 272 | 1,00 | 1,00 | 1,00 | 1,00 | — | — | `omp/skalowanie_gcc.csv` |  |
| MC szachownica 100³, Moore | OpenMP 2 wątki | 9 | 2 | 2 686 | 3 561 | 1,96 | 0,98 | 1,76 | 0,88 | 0,048 | 0,170 | `omp/skalowanie_gcc.csv` |  |
| MC szachownica 100³, Moore | OpenMP 4 wątki | 9 | 4 | 1 444 | 2 294 | 3,65 | 0,91 | 2,73 | 0,68 | 0,048 | 0,170 | `omp/skalowanie_gcc.csv` |  |
| MC szachownica 100³, Moore | OpenMP 6 wątków | 9 | 6 | 1 041 | 1 888 | 5,06 | 0,84 | 3,32 | 0,55 | 0,048 | 0,170 | `omp/skalowanie_gcc.csv` |  |
| MC szachownica 100³, Moore | OpenMP 8 wątków | 9 | 8 | 1 029 | 1 878 | 5,13 | 0,64 | 3,34 | 0,42 | 0,048 | 0,170 | `omp/skalowanie_gcc.csv` |  |
| MC szachownica 100³, Moore | MPI 1 proces | 10 | 1 | 5 391 | 6 660 | 1,00 | 1,00 | 1,00 | 1,00 | 0,066 | 0,235 | `mpi/skalowanie_mpi_gcc.csv` | total zawiera MPI_Init |
| MC szachownica 100³, Moore | MPI 3 procesy | 10 | 3 | 1 914 | 3 102 | 2,82 | 0,94 | 2,15 | 0,72 | 0,066 | 0,235 | `mpi/skalowanie_mpi_gcc.csv` | total zawiera MPI_Init |
| MC szachownica 100³, Moore | MPI 8 procesów | 10 | 8 | 1 079 | 2 328 | 4,99 | 0,62 | 2,86 | 0,36 | 0,066 | 0,235 | `mpi/skalowanie_mpi_gcc.csv` | total zawiera MPI_Init |
| MC szachownica 100³, Moore | hybryda 2 × 4 | 10 | 8 | 991 | 2 103 | 5,44 | 0,68 | 3,17 | 0,40 | — | — | `mpi/skalowanie_mpi_gcc.csv` | total zawiera MPI_Init |
| MC szachownica 100³, Moore | OpenMP 8 (etap 10, kontrola) | 10 | 8 | 861 | 1 714 | 6,26 | 0,78 | 3,89 | 0,49 | — | — | `mpi/skalowanie_mpi_gcc.csv` |  |
| MC szachownica 100³, Moore | MPI 8, typy pochodne | 11 | 8 | 1 168 | — | 4,97 | 0,62 | — | — | — | — | `mpi_io/pomiar_gcc_cz1_raw.csv …` | S = S(m8) etapu 10 × faza m / d etapu 11 (×0.996); faza m8 w etapie 11: 1163 ms, w etapie 10: 1079 ms |

