# Skalowanie MPI `skalowanie_mpi_gcc_cz1`

- Programy: `engine_mpi_e10_gcc` (OpenMPI `mpiexec --allow-run-as-root --use-hwthread-cpus --bind-to none -n p` (WSL, procesory wirtualne)), `engine_e10_gcc` (warianty o<t>); `--high-priority`, przypięcie `parallel.affinity = pcores` (proces r z t wątkami na rdzeniach r·t … r·t + t − 1); warianty naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 3.1 min, 2026-10-21T03:49
- Zgodność wyników z `m1`: wszystkie przebiegi bitowo zgodne

| Przypadek | wariant | rdzenie | total [ms] | S | E | faza [ms] | S fazy | E fazy | komunikacja / faza | nierówność | B / wymianę | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| lava_etna_real | m1 | 1 | 404 [390–426] | 1.00 | 1.00 | 81.7 [79.8–89.5] | 1.00 | 1.00 | 0% | ×1.00 | 0.00 | tak |
| lava_etna_real | m3 | 3 | 504 [475–553] | 0.80 | 0.27 | 145 [139–174] | 0.56 | 0.19 | 74% | ×1.50 | 1 784 628 | tak |
| lava_etna_real | m8 | 8 | 614 [576–710] | 0.66 | 0.08 | 176 [156–258] | 0.46 | 0.06 | 86% | ×1.66 | 6 036 238 | tak |
| lava_etna_real | h2x4 | 8 | 428 [382–484] | 0.95 | 0.12 | 80.3 [70.6–130] | 1.02 | 0.13 | 68% | ×1.26 | 892 314 | tak |
| lava_etna_real | o8 | 8 | 65.6 [51.2–99.0] | 6.16 | 0.77 | 21.2 [14.4–33.3] | 3.86 | 0.48 | — | — | — | tak |
| lava_duza_3d_front | m1 | 1 | 976 [967–1 038] | 1.00 | 1.00 | 681 [668–734] | 1.00 | 1.00 | 0% | ×1.00 | 0.00 | tak |
| lava_duza_3d_front | m3 | 3 | 845 [778–959] | 1.15 | 0.38 | 501 [462–614] | 1.36 | 0.45 | 51% | ×1.88 | 1 149 236 | tak |
| lava_duza_3d_front | m8 | 8 | 722 [665–859] | 1.35 | 0.17 | 298 [258–422] | 2.28 | 0.29 | 68% | ×2.01 | 3 853 316 | tak |
| lava_duza_3d_front | h2x4 | 8 | 571 [507–653] | 1.71 | 0.21 | 244 [214–319] | 2.79 | 0.35 | 49% | ×1.65 | 574 618 | tak |
| lava_duza_3d_front | o8 | 8 | 183 [146–241] | 5.34 | 0.67 | 151 [121–209] | 4.52 | 0.57 | — | — | — | tak |
| lava_duza_3d_full | m1 | 1 | 11 941 [11 032–12 078] | 1.00 | 1.00 | 11 621 [10 722–11 758] | 1.00 | 1.00 | 0% | ×1.00 | 0.00 | tak |
| lava_duza_3d_full | m3 | 3 | 4 805 [4 753–5 209] | 2.49 | 0.83 | 4 454 [4 421–4 836] | 2.61 | 0.87 | 17% | ×1.17 | 1 149 236 | tak |
| lava_duza_3d_full | m8 | 8 | 2 801 [2 602–2 941] | 4.26 | 0.53 | 2 374 [2 155–2 513] | 4.89 | 0.61 | 35% | ×1.18 | 3 853 316 | tak |
| lava_duza_3d_full | h2x4 | 8 | 2 458 [2 247–2 664] | 4.86 | 0.61 | 2 125 [1 928–2 319] | 5.47 | 0.68 | 20% | ×1.18 | 574 618 | tak |
| lava_duza_3d_full | o8 | 8 | 2 002 [1 910–2 166] | 5.96 | 0.75 | 1 966 [1 879–2 124] | 5.91 | 0.74 | — | — | — | tak |

Komunikacja / faza — średni po procesach czas wymiany warstw brzegowych i MPI_Allreduce w fazie obliczeń przez czas fazy (czekanie na wolniejszy pas wlicza się do MPI_Allreduce); nierówność — maks / średnia czasu obliczeń procesów; B / wymianę — bajty wszystkich komunikatów jednej wymiany.

Prawo Amdahla (warianty m<p>) — część szeregowa f (najmniejsze kwadraty na 1/S); „szeregowe z pomiaru” = (total − faza)/total przy 1 procesie; S(∞) = 1/f:

| Przypadek | f (total) | f (faza) | szeregowe z pomiaru | S(8) z f | S(∞) |
|---|---|---|---|---|---|
| lava_etna_real | 1.000 | 1.000 | 0.798 | 1.00 | 1.0 |
| lava_duza_3d_front | 0.738 | 0.449 | 0.303 | 1.30 | 1.4 |
| lava_duza_3d_full | 0.117 | 0.085 | 0.027 | 4.39 | 8.5 |

Tło (Windows, poza WSL): start 12% (WmiPrvSE.exe 194%, python.exe 36%, System 34%), koniec 19%.
