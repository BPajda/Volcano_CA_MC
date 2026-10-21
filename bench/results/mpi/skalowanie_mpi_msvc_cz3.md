# Skalowanie MPI `skalowanie_mpi_msvc_cz3`

- Programy: `engine_mpi_e10_msvc.exe` (MS-MPI `mpiexec -n p`), `engine_e10_msvc.exe` (warianty o<t>); `--high-priority`, przypięcie `parallel.affinity = pcores` (proces r z t wątkami na rdzeniach r·t … r·t + t − 1); warianty naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 4.0 min, 2026-10-21T03:38
- Tło: start 18% CPU (WmiPrvSE.exe 200%, BackgroundDownload.exe 113%, python.exe 39%), koniec 14%
- Zgodność wyników z `m1`: wszystkie przebiegi bitowo zgodne

| Przypadek | wariant | rdzenie | total [ms] | S | E | faza [ms] | S fazy | E fazy | komunikacja / faza | nierówność | B / wymianę | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| classic_2000x2000_s400_vn | m1 | 1 | 711 [700–713] | 1.00 | 1.00 | 539 [532–543] | 1.00 | 1.00 | 0% | ×1.00 | 0.00 | tak |
| classic_2000x2000_s400_vn | m2 | 2 | 404 [403–414] | 1.76 | 0.88 | 263 [259–272] | 2.05 | 1.02 | 4% | ×1.01 | 56 060 | tak |
| classic_2000x2000_s400_vn | m3 | 3 | 317 [313–325] | 2.24 | 0.75 | 187 [183–189] | 2.88 | 0.96 | 12% | ×1.01 | 84 090 | tak |
| classic_2000x2000_s400_vn | m4 | 4 | 265 [261–365] | 2.68 | 0.67 | 137 [136–140] | 3.94 | 0.99 | 14% | ×1.02 | 112 120 | tak |
| classic_2000x2000_s400_vn | m6 | 6 | 220 [216–344] | 3.24 | 0.54 | 95.8 [94.5–116] | 5.63 | 0.94 | 22% | ×1.04 | 168 180 | tak |
| classic_2000x2000_s400_vn | m7 | 7 | 203 [202–220] | 3.50 | 0.50 | 80.7 [79.8–96.3] | 6.68 | 0.95 | 24% | ×1.04 | 196 210 | tak |
| classic_2000x2000_s400_vn | m8 | 8 | 222 [197–302] | 3.20 | 0.40 | 90.3 [75.3–145] | 5.97 | 0.75 | 39% | ×1.19 | 224 240 | tak |
| classic_2000x2000_s400_vn | h2x4 | 8 | 236 [195–333] | 3.01 | 0.38 | 107 [80.2–141] | 5.02 | 0.63 | 25% | ×1.23 | 56 060 | tak |
| classic_2000x2000_s400_vn | h4x2 | 8 | 261 [194–318] | 2.73 | 0.34 | 97.0 [75.5–150] | 5.56 | 0.69 | 33% | ×1.21 | 112 120 | tak |
| classic_2000x2000_s400_vn | c4 | 4 | 264 [262–360] | 2.69 | 0.67 | 137 [136–138] | 3.94 | 0.98 | 14% | ×1.02 | 83 810 | tak |
| classic_2000x2000_s400_vn | c8 | 8 | 214 [195–250] | 3.32 | 0.41 | 91.2 [74.7–121] | 5.91 | 0.74 | 39% | ×1.16 | 164 240 | tak |
| classic_2000x2000_s400_vn | o4 | 4 | 222 [220–227] | 3.20 | 0.80 | 134 [132–137] | 4.02 | 1.00 | — | — | — | tak |
| classic_2000x2000_s400_vn | o8 | 8 | 186 [156–276] | 3.82 | 0.48 | 86.1 [69.7–163] | 6.26 | 0.78 | — | — | — | tak |
| classic_300x300x300_s100_vn | m1 | 1 | 4 539 [4 526–4 824] | 1.00 | 1.00 | 3 379 [3 376–3 407] | 1.00 | 1.00 | 0% | ×1.00 | 0.00 | tak |
| classic_300x300x300_s100_vn | m2 | 2 | 2 922 [2 876–3 092] | 1.55 | 0.78 | 1 943 [1 922–1 995] | 1.74 | 0.87 | 6% | ×1.01 | 2 553 716 | tak |
| classic_300x300x300_s100_vn | m3 | 3 | 2 425 [2 305–2 666] | 1.87 | 0.62 | 1 427 [1 404–1 770] | 2.37 | 0.79 | 9% | ×1.01 | 3 830 574 | tak |
| classic_300x300x300_s100_vn | m4 | 4 | 2 109 [2 026–2 228] | 2.15 | 0.54 | 1 179 [1 168–1 371] | 2.87 | 0.72 | 12% | ×1.01 | 5 107 432 | tak |
| classic_300x300x300_s100_vn | m6 | 6 | 1 835 [1 758–2 102] | 2.47 | 0.41 | 947 [934–1 264] | 3.57 | 0.59 | 17% | ×1.01 | 7 661 148 | tak |
| classic_300x300x300_s100_vn | m7 | 7 | 1 818 [1 714–1 990] | 2.50 | 0.36 | 932 [893–1 100] | 3.62 | 0.52 | 24% | ×1.03 | 8 938 006 | tak |
| classic_300x300x300_s100_vn | m8 | 8 | 1 877 [1 821–2 017] | 2.42 | 0.30 | 1 019 [976–1 081] | 3.32 | 0.41 | 34% | ×1.20 | 10 214 864 | tak |
| classic_300x300x300_s100_vn | h2x4 | 8 | 1 675 [1 603–1 844] | 2.71 | 0.34 | 866 [822–968] | 3.90 | 0.49 | 16% | ×1.06 | 2 553 716 | tak |
| classic_300x300x300_s100_vn | h4x2 | 8 | 1 608 [1 560–1 778] | 2.82 | 0.35 | 871 [832–1 035] | 3.88 | 0.48 | 20% | ×1.08 | 5 107 432 | tak |
| classic_300x300x300_s100_vn | c4 | 4 | 2 079 [2 039–2 467] | 2.18 | 0.55 | 1 202 [1 180–1 596] | 2.81 | 0.70 | 13% | ×1.02 | 4 777 018 | tak |
| classic_300x300x300_s100_vn | c8 | 8 | 2 007 [1 781–2 239] | 2.26 | 0.28 | 1 059 [974–1 276] | 3.19 | 0.40 | 36% | ×1.22 | 9 554 035 | tak |
| classic_300x300x300_s100_vn | o4 | 4 | 1 703 [1 662–1 842] | 2.67 | 0.67 | 1 029 [1 009–1 130] | 3.28 | 0.82 | — | — | — | tak |
| classic_300x300x300_s100_vn | o8 | 8 | 1 406 [1 324–1 493] | 3.23 | 0.40 | 717 [697–781] | 4.72 | 0.59 | — | — | — | tak |

Komunikacja / faza — średni po procesach czas wymiany warstw brzegowych i MPI_Allreduce w fazie obliczeń przez czas fazy (czekanie na wolniejszy pas wlicza się do MPI_Allreduce); nierówność — maks / średnia czasu obliczeń procesów; B / wymianę — bajty wszystkich komunikatów jednej wymiany.

Prawo Amdahla (warianty m<p>) — część szeregowa f (najmniejsze kwadraty na 1/S); „szeregowe z pomiaru” = (total − faza)/total przy 1 procesie; S(∞) = 1/f:

| Przypadek | f (total) | f (faza) | szeregowe z pomiaru | S(8) z f | S(∞) |
|---|---|---|---|---|---|
| classic_2000x2000_s400_vn | 0.176 | 0.017 | 0.242 | 3.59 | 5.7 |
| classic_300x300x300_s100_vn | 0.301 | 0.155 | 0.256 | 2.58 | 3.3 |
