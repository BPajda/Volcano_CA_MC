# Skalowanie MPI `skalowanie_mpi_msvc_cz1`

- Programy: `engine_mpi_e10_msvc.exe` (MS-MPI `mpiexec -n p`), `engine_e10_msvc.exe` (warianty o<t>); `--high-priority`, przypięcie `parallel.affinity = pcores` (proces r z t wątkami na rdzeniach r·t … r·t + t − 1); warianty naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 1.8 min, 2026-10-21T03:26
- Tło: start 13% CPU (WmiPrvSE.exe 187%, python.exe 37%, svchost.exe 31%), koniec 14%
- Zgodność wyników z `m1`: wszystkie przebiegi bitowo zgodne

| Przypadek | wariant | rdzenie | total [ms] | S | E | faza [ms] | S fazy | E fazy | komunikacja / faza | nierówność | B / wymianę | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| lava_etna_real | m1 | 1 | 175 [174–178] | 1.00 | 1.00 | 92.0 [91.0–92.6] | 1.00 | 1.00 | 0% | ×1.00 | 0.00 | tak |
| lava_etna_real | m2 | 2 | 225 [217–281] | 0.78 | 0.39 | 149 [148–206] | 0.62 | 0.31 | 62% | ×1.53 | 892 314 | tak |
| lava_etna_real | m3 | 3 | 238 [232–334] | 0.73 | 0.24 | 167 [165–254] | 0.55 | 0.18 | 72% | ×1.50 | 1 784 628 | tak |
| lava_etna_real | m4 | 4 | 253 [242–376] | 0.69 | 0.17 | 180 [178–302] | 0.51 | 0.13 | 77% | ×1.79 | 2 676 942 | tak |
| lava_etna_real | m6 | 6 | 240 [231–345] | 0.73 | 0.12 | 169 [167–256] | 0.54 | 0.09 | 79% | ×1.72 | 4 330 345 | tak |
| lava_etna_real | m7 | 7 | 242 [233–537] | 0.72 | 0.10 | 174 [168–204] | 0.53 | 0.08 | 81% | ×1.63 | 5 170 169 | tak |
| lava_etna_real | m8 | 8 | 280 [258–357] | 0.63 | 0.08 | 203 [188–271] | 0.45 | 0.06 | 84% | ×1.62 | 6 036 238 | tak |
| lava_etna_real | h2x4 | 8 | 187 [169–312] | 0.93 | 0.12 | 116 [100–172] | 0.80 | 0.10 | 67% | ×1.44 | 892 314 | tak |
| lava_etna_real | h4x2 | 8 | 289 [250–359] | 0.61 | 0.08 | 203 [172–265] | 0.45 | 0.06 | 78% | ×1.42 | 2 676 942 | tak |
| lava_etna_real | c4 | 4 | 209 [206–308] | 0.84 | 0.21 | 141 [140–146] | 0.65 | 0.16 | 71% | ×1.80 | 691 824 | tak |
| lava_etna_real | c8 | 8 | 239 [203–357] | 0.73 | 0.09 | 157 [136–251] | 0.58 | 0.07 | 81% | ×1.64 | 1 179 989 | tak |
| lava_etna_real | o4 | 4 | 76.0 [75.1–81.9] | 2.30 | 0.58 | 25.9 [25.7–28.7] | 3.55 | 0.89 | — | — | — | tak |
| lava_etna_real | o8 | 8 | 71.6 [65.2–96.6] | 2.44 | 0.31 | 18.5 [15.4–32.5] | 4.96 | 0.62 | — | — | — | tak |
| lava_duza_3d_front | m1 | 1 | 818 [813–840] | 1.00 | 1.00 | 762 [757–764] | 1.00 | 1.00 | 0% | ×1.00 | 0.00 | tak |
| lava_duza_3d_front | m2 | 2 | 757 [753–764] | 1.08 | 0.54 | 708 [704–713] | 1.08 | 0.54 | 45% | ×1.73 | 574 618 | tak |
| lava_duza_3d_front | m3 | 3 | 586 [583–588] | 1.40 | 0.47 | 538 [537–540] | 1.42 | 0.47 | 52% | ×1.84 | 1 149 236 | tak |
| lava_duza_3d_front | m4 | 4 | 467 [465–567] | 1.75 | 0.44 | 421 [418–425] | 1.81 | 0.45 | 53% | ×1.85 | 1 706 953 | tak |
| lava_duza_3d_front | m6 | 6 | 369 [364–461] | 2.22 | 0.37 | 320 [318–325] | 2.38 | 0.40 | 58% | ×1.99 | 2 771 684 | tak |
| lava_duza_3d_front | m7 | 7 | 352 [347–431] | 2.33 | 0.33 | 302 [300–323] | 2.52 | 0.36 | 61% | ×2.11 | 3 329 401 | tak |
| lava_duza_3d_front | m8 | 8 | 445 [330–495] | 1.84 | 0.23 | 340 [282–396] | 2.24 | 0.28 | 72% | ×1.93 | 3 853 316 | tak |
| lava_duza_3d_front | h2x4 | 8 | 341 [321–452] | 2.40 | 0.30 | 288 [270–374] | 2.64 | 0.33 | 47% | ×1.27 | 574 618 | tak |
| lava_duza_3d_front | h4x2 | 8 | 357 [324–531] | 2.29 | 0.29 | 299 [276–355] | 2.54 | 0.32 | 59% | ×1.58 | 1 706 953 | tak |
| lava_duza_3d_front | c4 | 4 | 472 [467–565] | 1.73 | 0.43 | 423 [420–428] | 1.80 | 0.45 | 53% | ×1.85 | 975 053 | tak |
| lava_duza_3d_front | c8 | 8 | 360 [341–409] | 2.27 | 0.28 | 302 [291–364] | 2.52 | 0.31 | 68% | ×1.96 | 2 142 451 | tak |
| lava_duza_3d_front | o4 | 4 | 225 [223–258] | 3.63 | 0.91 | 193 [191–212] | 3.95 | 0.99 | — | — | — | tak |
| lava_duza_3d_front | o8 | 8 | 183 [148–200] | 4.47 | 0.56 | 126 [108–161] | 6.03 | 0.75 | — | — | — | tak |

Komunikacja / faza — średni po procesach czas wymiany warstw brzegowych i MPI_Allreduce w fazie obliczeń przez czas fazy (czekanie na wolniejszy pas wlicza się do MPI_Allreduce); nierówność — maks / średnia czasu obliczeń procesów; B / wymianę — bajty wszystkich komunikatów jednej wymiany.

Prawo Amdahla (warianty m<p>) — część szeregowa f (najmniejsze kwadraty na 1/S); „szeregowe z pomiaru” = (total − faza)/total przy 1 procesie; S(∞) = 1/f:

| Przypadek | f (total) | f (faza) | szeregowe z pomiaru | S(8) z f | S(∞) |
|---|---|---|---|---|---|
| lava_etna_real | 1.000 | 1.000 | 0.475 | 1.00 | 1.0 |
| lava_duza_3d_front | 0.451 | 0.406 | 0.069 | 1.92 | 2.2 |
