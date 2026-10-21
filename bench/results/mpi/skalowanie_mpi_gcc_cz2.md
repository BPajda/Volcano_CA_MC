# Skalowanie MPI `skalowanie_mpi_gcc_cz2`

- Programy: `engine_mpi_e10_gcc` (OpenMPI `mpiexec --allow-run-as-root --use-hwthread-cpus --bind-to none -n p` (WSL, procesory wirtualne)), `engine_e10_gcc` (warianty o<t>); `--high-priority`, przypięcie `parallel.affinity = pcores` (proces r z t wątkami na rdzeniach r·t … r·t + t − 1); warianty naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 3.9 min, 2026-10-21T03:54
- Zgodność wyników z `m1`: wszystkie przebiegi bitowo zgodne

| Przypadek | wariant | rdzenie | total [ms] | S | E | faza [ms] | S fazy | E fazy | komunikacja / faza | nierówność | B / wymianę | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| classic_2000x2000_s400_vn | m1 | 1 | 904 [876–922] | 1.00 | 1.00 | 487 [475–508] | 1.00 | 1.00 | 0% | ×1.00 | 0.00 | tak |
| classic_2000x2000_s400_vn | m3 | 3 | 616 [566–648] | 1.47 | 0.49 | 177 [170–192] | 2.76 | 0.92 | 13% | ×1.03 | 84 090 | tak |
| classic_2000x2000_s400_vn | m8 | 8 | 611 [579–616] | 1.48 | 0.18 | 106 [90.8–138] | 4.59 | 0.57 | 51% | ×1.19 | 224 240 | tak |
| classic_2000x2000_s400_vn | h2x4 | 8 | 509 [458–573] | 1.77 | 0.22 | 117 [92.9–179] | 4.17 | 0.52 | 30% | ×1.10 | 56 060 | tak |
| classic_2000x2000_s400_vn | o8 | 8 | 180 [158–231] | 5.03 | 0.63 | 90.1 [83.2–140] | 5.41 | 0.68 | — | — | — | tak |
| classic_300x300x300_s100_vn | m1 | 1 | 4 609 [4 479–4 827] | 1.00 | 1.00 | 3 196 [3 148–3 436] | 1.00 | 1.00 | 0% | ×1.00 | 0.00 | tak |
| classic_300x300x300_s100_vn | m3 | 3 | 2 497 [2 446–2 659] | 1.85 | 0.62 | 1 389 [1 288–1 412] | 2.30 | 0.77 | 12% | ×1.02 | 3 830 574 | tak |
| classic_300x300x300_s100_vn | m8 | 8 | 2 187 [2 168–2 359] | 2.11 | 0.26 | 961 [869–1 055] | 3.33 | 0.42 | 39% | ×1.12 | 10 214 864 | tak |
| classic_300x300x300_s100_vn | h2x4 | 8 | 1 744 [1 666–1 773] | 2.64 | 0.33 | 768 [737–822] | 4.16 | 0.52 | 16% | ×1.02 | 2 553 716 | tak |
| classic_300x300x300_s100_vn | o8 | 8 | 1 345 [1 337–1 399] | 3.43 | 0.43 | 743 [665–791] | 4.30 | 0.54 | — | — | — | tak |
| mc_cb_2d_1000 | m1 | 1 | 2 762 [2 614–2 793] | 1.00 | 1.00 | 2 010 [1 934–2 074] | 1.00 | 1.00 | 0% | ×1.00 | 0.00 | tak |
| mc_cb_2d_1000 | m3 | 3 | 1 441 [1 309–1 504] | 1.92 | 0.64 | 674 [654–766] | 2.98 | 0.99 | 5% | ×1.02 | 24 054 | tak |
| mc_cb_2d_1000 | m8 | 8 | 1 140 [1 114–1 402] | 2.42 | 0.30 | 372 [344–615] | 5.40 | 0.68 | 28% | ×1.11 | 64 144 | tak |
| mc_cb_2d_1000 | h2x4 | 8 | 1 030 [992–1 098] | 2.68 | 0.34 | 336 [309–364] | 5.98 | 0.75 | 12% | ×1.05 | 16 036 | tak |
| mc_cb_2d_1000 | o8 | 8 | 730 [685–825] | 3.78 | 0.47 | 341 [298–439] | 5.89 | 0.74 | — | — | — | tak |
| mc_cb_3d_100 | m1 | 1 | 6 660 [6 518–6 766] | 1.00 | 1.00 | 5 391 [5 254–5 452] | 1.00 | 1.00 | 0% | ×1.00 | 0.00 | tak |
| mc_cb_3d_100 | m3 | 3 | 3 102 [3 018–3 114] | 2.15 | 0.72 | 1 914 [1 895–1 950] | 2.82 | 0.94 | 7% | ×1.03 | 249 702 | tak |
| mc_cb_3d_100 | m8 | 8 | 2 328 [2 217–2 488] | 2.86 | 0.36 | 1 079 [1 002–1 188] | 4.99 | 0.62 | 33% | ×1.04 | 665 872 | tak |
| mc_cb_3d_100 | h2x4 | 8 | 2 103 [2 080–2 176] | 3.17 | 0.40 | 991 [944–1 024] | 5.44 | 0.68 | 15% | ×1.02 | 166 468 | tak |
| mc_cb_3d_100 | o8 | 8 | 1 714 [1 685–1 850] | 3.89 | 0.49 | 861 [818–948] | 6.26 | 0.78 | — | — | — | tak |

Komunikacja / faza — średni po procesach czas wymiany warstw brzegowych i MPI_Allreduce w fazie obliczeń przez czas fazy (czekanie na wolniejszy pas wlicza się do MPI_Allreduce); nierówność — maks / średnia czasu obliczeń procesów; B / wymianę — bajty wszystkich komunikatów jednej wymiany.

Prawo Amdahla (warianty m<p>) — część szeregowa f (najmniejsze kwadraty na 1/S); „szeregowe z pomiaru” = (total − faza)/total przy 1 procesie; S(∞) = 1/f:

| Przypadek | f (total) | f (faza) | szeregowe z pomiaru | S(8) z f | S(∞) |
|---|---|---|---|---|---|
| classic_2000x2000_s400_vn | 0.591 | 0.083 | 0.461 | 1.56 | 1.7 |
| classic_300x300x300_s100_vn | 0.367 | 0.183 | 0.307 | 2.24 | 2.7 |
| mc_cb_2d_1000 | 0.312 | 0.045 | 0.272 | 2.51 | 3.2 |
| mc_cb_3d_100 | 0.235 | 0.066 | 0.191 | 3.02 | 4.2 |

Tło (Windows, poza WSL): start 17% (WmiPrvSE.exe 204%, System 54%, svchost.exe 50%), koniec 10%.
