# Skalowanie MPI `slabe_mpi_msvc`

- Programy: `engine_mpi.exe` (MS-MPI `mpiexec -n p`), `engine.exe` (warianty o<t>); `--high-priority`, przypięcie `parallel.affinity = pcores` (proces r z t wątkami na rdzeniach r·t … r·t + t − 1); warianty naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 3.1 min, 2026-10-21T18:39
- Tło: start 12% CPU (WmiPrvSE.exe 161%, svchost.exe 40%, python.exe 38%), koniec 15%
- Skalowanie słabe: przestrzeń razy liczba rdzeni wariantu, `output.format = none`; wyników różnych rozmiarów nie porównuje się bitowo (zgodność procesów — etapy 10–11)

| Przypadek | wariant | p | komórki | kroki / MCS | faza [ms] | E_w fazy | total [ms] | E_w total | ns rdzenia / (komórka × krok) albo / próbę | E_w znormalizowana |
|---|---|---|---|---|---|---|---|---|---|---|
| weak_classic_2d | m1d | 1 | 4 000 000 | 199 | 527 [501–529] | 1.00 | 674 | 1.00 | 0.66 | 1.00 |
| weak_classic_2d | m2d | 2 | 8 000 000 | 223 | 600 [596–873] | 0.88 | 823 | 0.82 | 0.67 | 0.98 |
| weak_classic_2d | m4d | 4 | 16 000 000 | 228 | 697 [694–774] | 0.76 | 1 060 | 0.64 | 0.76 | 0.87 |
| weak_classic_2d | m6d | 6 | 24 000 000 | 233 | 798 [787–907] | 0.66 | 1 291 | 0.52 | 0.86 | 0.77 |
| weak_classic_2d | m7d | 7 | 28 000 000 | 216 | 865 [840–1 165] | 0.61 | 1 446 | 0.47 | 1.00 | 0.66 |
| weak_classic_2d | m8d | 8 | 32 000 000 | 247 | 1 079 [1 062–1 258] | 0.49 | 1 722 | 0.39 | 1.09 | 0.61 |
| weak_mc_cb_2d | m1d | 1 | 1 000 000 | 30 | 755 [754–755] | 1.00 | 893 | 1.00 | 25.17 | 1.00 |
| weak_mc_cb_2d | m2d | 2 | 2 000 000 | 30 | 758 [756–967] | 1.00 | 1 063 | 0.84 | 25.26 | 1.00 |
| weak_mc_cb_2d | m4d | 4 | 4 000 000 | 30 | 759 [757–983] | 1.00 | 1 083 | 0.82 | 25.29 | 1.00 |
| weak_mc_cb_2d | m6d | 6 | 6 000 000 | 30 | 769 [765–864] | 0.98 | 1 223 | 0.73 | 25.63 | 0.98 |
| weak_mc_cb_2d | m7d | 7 | 7 000 000 | 30 | 779 [770–885] | 0.97 | 1 307 | 0.68 | 25.95 | 0.97 |
| weak_mc_cb_2d | m8d | 8 | 8 000 000 | 30 | 900 [896–1 227] | 0.84 | 1 502 | 0.59 | 30.01 | 0.84 |
| weak_lava_full | m1d | 1 | 1 048 576 | 20 | 1 078 [1 072–1 091] | 1.00 | 1 132 | 1.00 | 51.38 | 1.00 |
| weak_lava_full | m2d | 2 | 2 097 152 | 20 | 1 313 [1 289–1 472] | 0.82 | 1 498 | 0.76 | 62.61 | 0.82 |
| weak_lava_full | m4d | 4 | 4 194 304 | 20 | 1 325 [1 318–1 547] | 0.81 | 1 551 | 0.73 | 63.19 | 0.81 |
| weak_lava_full | m6d | 6 | 6 291 456 | 20 | 1 370 [1 366–1 393] | 0.79 | 1 527 | 0.74 | 65.33 | 0.79 |
| weak_lava_full | m7d | 7 | 7 340 032 | 20 | 1 385 [1 381–1 402] | 0.78 | 1 576 | 0.72 | 66.02 | 0.78 |
| weak_lava_full | m8d | 8 | 8 388 608 | 20 | 1 609 [1 601–1 893] | 0.67 | 1 825 | 0.62 | 76.72 | 0.67 |
| weak_lava_front | m1d | 1 | 1 048 576 | 260 | 523 [520–524] | 1.00 | 574 | 1.00 | 1.92 | 1.00 |
| weak_lava_front | m2d | 2 | 2 097 152 | 260 | 1 093 [1 056–1 121] | 0.48 | 1 191 | 0.48 | 4.01 | 0.48 |
| weak_lava_front | m4d | 4 | 4 194 304 | 260 | 1 565 [1 554–1 612] | 0.33 | 1 678 | 0.34 | 5.74 | 0.33 |
| weak_lava_front | m6d | 6 | 6 291 456 | 260 | 1 826 [1 806–1 843] | 0.29 | 1 991 | 0.29 | 6.70 | 0.29 |
| weak_lava_front | m7d | 7 | 7 340 032 | 260 | 1 971 [1 964–1 986] | 0.27 | 2 135 | 0.27 | 7.23 | 0.27 |
| weak_lava_front | m8d | 8 | 8 388 608 | 260 | 2 125 [2 100–2 395] | 0.25 | 2 319 | 0.25 | 7.79 | 0.25 |

E_w = T(1) / T(p) przy przestrzeni p razy większej (ideał 1); znormalizowana — z czasu na (komórkę × krok / p), gdy liczba kroków albo MCS zmienia się z p (classic: największa luka między zarodkami).
