# Skalowanie MPI `skalowanie_mpi_msvc_cz2`

- Programy: `engine_mpi_e10_msvc.exe` (MS-MPI `mpiexec -n p`), `engine_e10_msvc.exe` (warianty o<t>); `--high-priority`, przypięcie `parallel.affinity = pcores` (proces r z t wątkami na rdzeniach r·t … r·t + t − 1); warianty naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 5.1 min, 2026-10-21T03:33
- Tło: start 24% CPU (WmiPrvSE.exe 220%, svchost.exe 85%, BackgroundDownload.exe 79%), koniec 14%
- Zgodność wyników z `m1`: wszystkie przebiegi bitowo zgodne

| Przypadek | wariant | rdzenie | total [ms] | S | E | faza [ms] | S fazy | E fazy | komunikacja / faza | nierówność | B / wymianę | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| lava_duza_3d_full | m1 | 1 | 13 475 [13 456–13 508] | 1.00 | 1.00 | 13 415 [13 395–13 447] | 1.00 | 1.00 | 0% | ×1.00 | 0.00 | tak |
| lava_duza_3d_full | m2 | 2 | 8 196 [8 049–8 933] | 1.64 | 0.82 | 8 145 [7 994–8 874] | 1.65 | 0.82 | 16% | ×1.18 | 574 618 | tak |
| lava_duza_3d_full | m3 | 3 | 5 456 [5 448–5 690] | 2.47 | 0.82 | 5 406 [5 396–5 532] | 2.48 | 0.83 | 16% | ×1.18 | 1 149 236 | tak |
| lava_duza_3d_full | m4 | 4 | 4 242 [4 230–4 339] | 3.18 | 0.79 | 4 194 [4 177–4 216] | 3.20 | 0.80 | 18% | ×1.19 | 1 706 953 | tak |
| lava_duza_3d_full | m6 | 6 | 2 923 [2 907–3 013] | 4.61 | 0.77 | 2 871 [2 858–2 912] | 4.67 | 0.78 | 19% | ×1.18 | 2 771 684 | tak |
| lava_duza_3d_full | m7 | 7 | 2 562 [2 541–2 591] | 5.26 | 0.75 | 2 506 [2 491–2 543] | 5.35 | 0.76 | 20% | ×1.17 | 3 329 401 | tak |
| lava_duza_3d_full | m8 | 8 | 3 008 [2 721–3 782] | 4.48 | 0.56 | 2 960 [2 671–3 628] | 4.53 | 0.57 | 37% | ×1.45 | 3 853 316 | tak |
| lava_duza_3d_full | h2x4 | 8 | 2 539 [2 449–2 747] | 5.31 | 0.66 | 2 487 [2 398–2 614] | 5.39 | 0.67 | 21% | ×1.19 | 574 618 | tak |
| lava_duza_3d_full | h4x2 | 8 | 2 767 [2 604–2 812] | 4.87 | 0.61 | 2 719 [2 556–2 756] | 4.93 | 0.62 | 29% | ×1.35 | 1 706 953 | tak |
| lava_duza_3d_full | c4 | 4 | 4 244 [4 198–4 883] | 3.17 | 0.79 | 4 190 [4 147–4 729] | 3.20 | 0.80 | 18% | ×1.19 | 973 948 | tak |
| lava_duza_3d_full | c8 | 8 | 2 962 [2 673–3 845] | 4.55 | 0.57 | 2 820 [2 613–3 700] | 4.76 | 0.59 | 35% | ×1.40 | 2 139 071 | tak |
| lava_duza_3d_full | o4 | 4 | 3 786 [3 761–3 809] | 3.56 | 0.89 | 3 750 [3 724–3 771] | 3.58 | 0.89 | — | — | — | tak |
| lava_duza_3d_full | o8 | 8 | 2 207 [2 178–2 276] | 6.11 | 0.76 | 2 164 [2 133–2 233] | 6.20 | 0.78 | — | — | — | tak |

Komunikacja / faza — średni po procesach czas wymiany warstw brzegowych i MPI_Allreduce w fazie obliczeń przez czas fazy (czekanie na wolniejszy pas wlicza się do MPI_Allreduce); nierówność — maks / średnia czasu obliczeń procesów; B / wymianę — bajty wszystkich komunikatów jednej wymiany.

Prawo Amdahla (warianty m<p>) — część szeregowa f (najmniejsze kwadraty na 1/S); „szeregowe z pomiaru” = (total − faza)/total przy 1 procesie; S(∞) = 1/f:

| Przypadek | f (total) | f (faza) | szeregowe z pomiaru | S(8) z f | S(∞) |
|---|---|---|---|---|---|
| lava_duza_3d_full | 0.092 | 0.089 | 0.004 | 4.86 | 10.8 |
