# Skalowanie MPI `skalowanie_mpi_msvc_cz4`

- Programy: `engine_mpi_e10_msvc.exe` (MS-MPI `mpiexec -n p`), `engine_e10_msvc.exe` (warianty o<t>); `--high-priority`, przypięcie `parallel.affinity = pcores` (proces r z t wątkami na rdzeniach r·t … r·t + t − 1); warianty naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 4.4 min, 2026-10-21T03:44
- Tło: start 13% CPU (WmiPrvSE.exe 197%, python.exe 37%, svchost.exe 34%), koniec 13%
- Zgodność wyników z `m1`: wszystkie przebiegi bitowo zgodne

| Przypadek | wariant | rdzenie | total [ms] | S | E | faza [ms] | S fazy | E fazy | komunikacja / faza | nierówność | B / wymianę | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| mc_cb_2d_1000 | m1 | 1 | 2 571 [2 569–2 578] | 1.00 | 1.00 | 2 052 [2 051–2 056] | 1.00 | 1.00 | 0% | ×1.00 | 0.00 | tak |
| mc_cb_2d_1000 | m2 | 2 | 1 495 [1 493–1 603] | 1.72 | 0.86 | 1 031 [1 030–1 068] | 1.99 | 1.00 | 1% | ×1.00 | 16 036 | tak |
| mc_cb_2d_1000 | m3 | 3 | 1 135 [1 131–1 140] | 2.27 | 0.76 | 689 [688–694] | 2.98 | 0.99 | 1% | ×1.01 | 24 054 | tak |
| mc_cb_2d_1000 | m4 | 4 | 954 [943–1 050] | 2.70 | 0.67 | 518 [517–539] | 3.96 | 0.99 | 1% | ×1.00 | 32 072 | tak |
| mc_cb_2d_1000 | m6 | 6 | 770 [766–785] | 3.34 | 0.56 | 351 [349–354] | 5.85 | 0.97 | 2% | ×1.01 | 48 108 | tak |
| mc_cb_2d_1000 | m7 | 7 | 727 [720–731] | 3.54 | 0.51 | 305 [303–311] | 6.72 | 0.96 | 4% | ×1.01 | 56 126 | tak |
| mc_cb_2d_1000 | m8 | 8 | 758 [721–876] | 3.39 | 0.42 | 340 [298–374] | 6.03 | 0.75 | 21% | ×1.24 | 64 144 | tak |
| mc_cb_2d_1000 | h2x4 | 8 | 794 [763–1 033] | 3.24 | 0.40 | 332 [312–482] | 6.17 | 0.77 | 11% | ×1.07 | 16 036 | tak |
| mc_cb_2d_1000 | h4x2 | 8 | 762 [734–931] | 3.38 | 0.42 | 328 [315–394] | 6.26 | 0.78 | 16% | ×1.14 | 32 072 | tak |
| mc_cb_2d_1000 | c4 | 4 | 953 [945–960] | 2.70 | 0.67 | 519 [518–519] | 3.96 | 0.99 | 1% | ×1.00 | 32 072 | tak |
| mc_cb_2d_1000 | c8 | 8 | 776 [756–835] | 3.31 | 0.41 | 336 [321–389] | 6.11 | 0.76 | 21% | ×1.23 | 64 144 | tak |
| mc_cb_2d_1000 | o4 | 4 | 957 [954–960] | 2.69 | 0.67 | 527 [524–533] | 3.90 | 0.97 | — | — | — | tak |
| mc_cb_2d_1000 | o8 | 8 | 767 [752–1 366] | 3.35 | 0.42 | 336 [321–748] | 6.10 | 0.76 | — | — | — | tak |
| mc_cb_3d_100 | m1 | 1 | 6 906 [6 897–7 052] | 1.00 | 1.00 | 5 741 [5 730–5 835] | 1.00 | 1.00 | 0% | ×1.00 | 0.00 | tak |
| mc_cb_3d_100 | m2 | 2 | 3 982 [3 945–4 733] | 1.73 | 0.87 | 2 940 [2 907–3 674] | 1.95 | 0.98 | 2% | ×1.00 | 166 468 | tak |
| mc_cb_3d_100 | m3 | 3 | 2 993 [2 977–3 495] | 2.31 | 0.77 | 2 014 [1 990–2 494] | 2.85 | 0.95 | 5% | ×1.02 | 249 702 | tak |
| mc_cb_3d_100 | m4 | 4 | 2 468 [2 466–2 752] | 2.80 | 0.70 | 1 519 [1 519–1 785] | 3.78 | 0.94 | 6% | ×1.00 | 332 936 | tak |
| mc_cb_3d_100 | m6 | 6 | 1 991 [1 982–2 362] | 3.47 | 0.58 | 1 061 [1 058–1 423] | 5.41 | 0.90 | 10% | ×1.02 | 499 404 | tak |
| mc_cb_3d_100 | m7 | 7 | 1 882 [1 880–2 087] | 3.67 | 0.52 | 963 [950–1 112] | 5.96 | 0.85 | 15% | ×1.05 | 582 638 | tak |
| mc_cb_3d_100 | m8 | 8 | 2 004 [1 894–2 106] | 3.45 | 0.43 | 1 035 [961–1 167] | 5.55 | 0.69 | 28% | ×1.14 | 665 872 | tak |
| mc_cb_3d_100 | h2x4 | 8 | 2 049 [1 907–2 667] | 3.37 | 0.42 | 1 090 [944–1 217] | 5.27 | 0.66 | 15% | ×1.15 | 166 468 | tak |
| mc_cb_3d_100 | h4x2 | 8 | 1 883 [1 846–2 130] | 3.67 | 0.46 | 956 [916–1 088] | 6.00 | 0.75 | 18% | ×1.12 | 332 936 | tak |
| mc_cb_3d_100 | c4 | 4 | 2 461 [2 459–2 576] | 2.81 | 0.70 | 1 509 [1 508–1 615] | 3.80 | 0.95 | 5% | ×1.00 | 166 680 | tak |
| mc_cb_3d_100 | c8 | 8 | 2 007 [1 860–2 192] | 3.44 | 0.43 | 1 028 [934–1 159] | 5.58 | 0.70 | 28% | ×1.19 | 333 360 | tak |
| mc_cb_3d_100 | o4 | 4 | 2 465 [2 463–2 467] | 2.80 | 0.70 | 1 497 [1 497–1 498] | 3.83 | 0.96 | — | — | — | tak |
| mc_cb_3d_100 | o8 | 8 | 1 888 [1 871–1 973] | 3.66 | 0.46 | 916 [903–1 010] | 6.27 | 0.78 | — | — | — | tak |

Komunikacja / faza — średni po procesach czas wymiany warstw brzegowych i MPI_Allreduce w fazie obliczeń przez czas fazy (czekanie na wolniejszy pas wlicza się do MPI_Allreduce); nierówność — maks / średnia czasu obliczeń procesów; B / wymianę — bajty wszystkich komunikatów jednej wymiany.

Prawo Amdahla (warianty m<p>) — część szeregowa f (najmniejsze kwadraty na 1/S); „szeregowe z pomiaru” = (total − faza)/total przy 1 procesie; S(∞) = 1/f:

| Przypadek | f (total) | f (faza) | szeregowe z pomiaru | S(8) z f | S(∞) |
|---|---|---|---|---|---|
| mc_cb_2d_1000 | 0.169 | 0.014 | 0.202 | 3.67 | 5.9 |
| mc_cb_3d_100 | 0.157 | 0.033 | 0.169 | 3.81 | 6.4 |
