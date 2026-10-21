# Typy MPI i MPI-IO `pomiar_msvc`

- Tabele z pomiaru w częściach: bench\results\mpi_io\pomiar_msvc_cz1_raw.csv,bench\results\mpi_io\pomiar_msvc_cz2_raw.csv,bench\results\mpi_io\pomiar_msvc_cz3_raw.csv,bench\results\mpi_io\pomiar_msvc_cz4_raw.csv
- `pomiar_msvc_cz1_raw.csv`: Czas pomiaru: 3.8 min, 2026-10-21T10:10
- `pomiar_msvc_cz1_raw.csv`: Tło: start 15% CPU (WmiPrvSE.exe 212%, svchost.exe 40%, python.exe 39%), koniec 14%
- `pomiar_msvc_cz2_raw.csv`: Czas pomiaru: 3.4 min, 2026-10-21T10:14
- `pomiar_msvc_cz2_raw.csv`: Tło: start 12% CPU (WmiPrvSE.exe 199%, System 49%, svchost.exe 45%), koniec 13%
- `pomiar_msvc_cz3_raw.csv`: Czas pomiaru: 5.5 min, 2026-10-21T10:20
- `pomiar_msvc_cz3_raw.csv`: Tło: start 12% CPU (WmiPrvSE.exe 211%, python.exe 39%, svchost.exe 39%), koniec 12%
- `pomiar_msvc_cz4_raw.csv`: Czas pomiaru: 3.0 min, 2026-10-21T10:23
- `pomiar_msvc_cz4_raw.csv`: Tło: start 13% CPU (WmiPrvSE.exe 209%, svchost.exe 42%, python.exe 38%), koniec 12%

### `pack_lava_3d_front` — wymiana warstw: pakowanie (m) vs typy pochodne (d)

| p | faza m [ms] | faza d [ms] | d/m faza | wymiana m [ms] | wymiana d [ms] | d/m wymiana | na wymianę m / d [ms] | B / wymianę m / d | komunikaty / wymianę | typy (suma) | budowa typów [ms] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 670 [668–675] | 668 [658–679] | ×0.997 | 34.2 [33.9–35.8] | 24.5 [22.5–28.4] | ×0.717 | 0.132 / 0.094 | 0.57 MB / 0.57 MB | 2.0 / 2.0 | 4 | 0.042 | tak |
| 4 | 399 [397–836] | 380 [378–386] | ×0.953 | 51.2 [51.0–271] | 32.5 [31.9–34.6] | ×0.634 | 0.197 / 0.125 | 1.71 MB / 1.71 MB | 8.0 / 8.0 | 16 | 0.091 | tak |
| 7 | 285 [282–290] | 268 [265–278] | ×0.940 | 53.7 [52.3–56.0] | 32.3 [31.0–37.3] | ×0.601 | 0.207 / 0.124 | 3.33 MB / 3.33 MB | 17.0 / 17.0 | 34 | 0.091 | tak |
| 8 | 264 [255–326] | 243 [235–265] | ×0.922 | 63.4 [58.4–97.7] | 39.0 [36.0–54.8] | ×0.615 | 0.244 / 0.150 | 3.85 MB / 3.85 MB | 25.0 / 25.0 | 50 | 0.099 | tak |

### `pack_lava_3d_full` — wymiana warstw: pakowanie (m) vs typy pochodne (d)

| p | faza m [ms] | faza d [ms] | d/m faza | wymiana m [ms] | wymiana d [ms] | d/m wymiana | na wymianę m / d [ms] | B / wymianę m / d | komunikaty / wymianę | typy (suma) | budowa typów [ms] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 8 453 [8 421–9 054] | 8 462 [8 418–9 403] | ×1.001 | 61.3 [60.0–70.0] | 42.8 [42.4–45.8] | ×0.698 | 0.236 / 0.165 | 0.57 MB / 0.57 MB | 2.0 / 2.0 | 8 | 0.114 | tak |
| 4 | 4 361 [4 309–4 409] | 4 316 [4 294–4 348] | ×0.990 | 86.2 [84.0–94.8] | 64.3 [62.5–64.6] | ×0.746 | 0.332 / 0.247 | 1.71 MB / 1.71 MB | 8.0 / 8.0 | 32 | 0.121 | tak |
| 7 | 2 619 [2 574–3 306] | 2 571 [2 538–2 592] | ×0.982 | 101 [95.7–475] | 66.8 [62.2–75.7] | ×0.662 | 0.388 / 0.257 | 3.33 MB / 3.33 MB | 17.0 / 17.0 | 68 | 0.140 | tak |
| 8 | 2 572 [2 381–2 812] | 2 404 [2 339–2 736] | ×0.935 | 116 [105–172] | 73.1 [72.0–86.4] | ×0.632 | 0.445 / 0.281 | 3.85 MB / 3.85 MB | 25.0 / 25.0 | 100 | 0.165 | tak |

### `pack_classic_300` — wymiana warstw: pakowanie (m) vs typy pochodne (d)

| p | faza m [ms] | faza d [ms] | d/m faza | wymiana m [ms] | wymiana d [ms] | d/m wymiana | na wymianę m / d [ms] | B / wymianę m / d | komunikaty / wymianę | typy (suma) | budowa typów [ms] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 1 919 [1 903–1 962] | 1 866 [1 846–1 917] | ×0.973 | 67.0 [66.4–71.4] | 35.1 [34.5–38.4] | ×0.524 | 0.587 / 0.308 | 2.55 MB / 2.55 MB | 2.0 / 2.0 | 4 | 0.049 | tak |
| 4 | 1 148 [1 143–1 174] | 1 105 [1 098–1 135] | ×0.962 | 75.1 [73.9–76.3] | 39.6 [39.1–40.7] | ×0.527 | 0.659 / 0.348 | 5.11 MB / 5.11 MB | 8.0 / 8.0 | 16 | 0.088 | tak |
| 7 | 879 [878–897] | 816 [801–833] | ×0.929 | 97.6 [94.9–98.3] | 48.4 [47.1–49.5] | ×0.496 | 0.856 / 0.425 | 8.94 MB / 8.94 MB | 14.0 / 14.0 | 28 | 0.086 | tak |
| 8 | 867 [845–877] | 789 [768–801] | ×0.910 | 107 [102–113] | 53.6 [50.7–53.9] | ×0.503 | 0.935 / 0.470 | 10.21 MB / 10.21 MB | 16.0 / 16.0 | 32 | 0.089 | tak |

### `pack_mc_cb_3d_100` — wymiana warstw: pakowanie (m) vs typy pochodne (d)

| p | faza m [ms] | faza d [ms] | d/m faza | wymiana m [ms] | wymiana d [ms] | d/m wymiana | na wymianę m / d [ms] | B / wymianę m / d | komunikaty / wymianę | typy (suma) | budowa typów [ms] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 2 894 [2 892–2 995] | 2 888 [2 879–2 991] | ×0.998 | 40.0 [39.2–91.5] | 34.4 [30.6–89.2] | ×0.859 | 0.050 / 0.043 | 0.17 MB / 0.17 MB | 2.0 / 2.0 | 4 | 0.029 | tak |
| 4 | 1 529 [1 512–1 579] | 1 497 [1 493–1 571] | ×0.979 | 97.7 [88.8–139] | 81.9 [77.3–135] | ×0.839 | 0.122 / 0.102 | 0.33 MB / 0.33 MB | 8.0 / 8.0 | 16 | 0.064 | tak |
| 7 | 951 [940–958] | 934 [924–946] | ×0.982 | 136 [124–140] | 121 [115–130] | ×0.892 | 0.170 / 0.151 | 0.58 MB / 0.58 MB | 14.0 / 14.0 | 28 | 0.063 | tak |
| 8 | 868 [834–880] | 871 [830–1 642] | ×1.003 | 148 [122–159] | 154 [119–935] | ×1.036 | 0.185 / 0.192 | 0.67 MB / 0.67 MB | 16.0 / 16.0 | 32 | 0.062 | tak |

### `bcast_etna_real` — rozsyłanie: JSON (m) vs struktury (s)

| wariant | MPI_Bcast configu [ms] | config [B] | przygotowanie (proces 0) [ms] | budowa Config (maks.) [ms] | kratery [ms] | kratery [B] | razem [ms] | zgodne |
|---|---|---|---|---|---|---|---|---|
| m3 | 0.53 [0.44–0.62] | 980 | 0.03 [0.03–0.03] | 0.27 [0.26–0.28] | 0.00 [0.00–0.00] | 0 | 0.81 | tak |
| m3s | 0.50 [0.44–0.56] | 219 | 0.02 [0.01–0.02] | 0.04 [0.04–0.06] | 0.03 [0.03–0.03] | 56 | 0.59 | tak |
| m8 | 0.68 [0.64–0.69] | 980 | 0.03 [0.03–0.03] | 0.41 [0.39–0.60] | 0.00 [0.00–0.00] | 0 | 1.10 | tak |
| m8s | 0.63 [0.59–0.96] | 219 | 0.02 [0.01–0.02] | 0.06 [0.05–0.16] | 0.02 [0.02–0.02] | 56 | 0.73 | tak |

### `bcast_classic_2000` — rozsyłanie: JSON (m) vs struktury (s)

| wariant | MPI_Bcast configu [ms] | config [B] | przygotowanie (proces 0) [ms] | budowa Config (maks.) [ms] | kratery [ms] | kratery [B] | razem [ms] | zgodne |
|---|---|---|---|---|---|---|---|---|
| m3 | 0.46 [0.45–0.78] | 881 | 0.03 [0.02–0.03] | 0.26 [0.25–0.36] | 0.00 [0.00–0.00] | 0 | 0.84 | tak |
| m3s | 0.50 [0.48–0.55] | 219 | 0.02 [0.01–0.02] | 0.04 [0.04–0.08] | 0.09 [0.09–0.10] | 6408 | 0.67 | tak |
| m8 | 0.66 [0.57–0.68] | 881 | 0.03 [0.03–0.03] | 0.36 [0.30–0.40] | 0.00 [0.00–0.00] | 0 | 1.00 | tak |
| m8s | 0.63 [0.58–0.65] | 219 | 0.01 [0.01–0.02] | 0.07 [0.06–0.08] | 0.10 [0.09–0.11] | 6408 | 0.80 | tak |

### `io_bin_classic_300` — zapis: zebranie na proces 0 (m) vs MPI-IO (i)

| p | save m [ms] | save i [ms] | i/m | plik m [ms] | plik i [ms] | MB/s m / i | udział w total m / i | zebranie m (maks.) [ms] | formatowanie i (maks.) [ms] | MPI-IO i (maks.) [ms] | pamięć procesu 0 m / i [MB] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 704 [691–792] | 436 [434–437] | ×0.620 | 288 [277–375] | 173 [170–174] | 1219 / 2026 | 15.5% / 10.3% | 43.6 | 0.0 | 173.2 | 1145 / 794 | tak |
| 2 | 575 [566–581] | 463 [455–467] | ×0.804 | 278 [270–279] | 328 [321–334] | 1261 / 1071 | 20.2% / 17.7% | 163.7 | 0.0 | 328.6 | 760 / 410 | tak |
| 4 | 519 [507–556] | 379 [374–386] | ×0.730 | 280 [267–318] | 309 [305–311] | 1252 / 1135 | 25.9% / 22.9% | 169.1 | 0.0 | 309.6 | 566 / 215 | tak |
| 8 | 489 [484–501] | 325 [323–331] | ×0.664 | 279 [272–282] | 286 [282–289] | 1256 / 1227 | 29.1% / 25.2% | 174.8 | 0.0 | 287.2 | 469 / 118 | tak |
Plik: 351.00 MB. save — od końca fazy CA: pas bez ramki, (m) zebranie na proces 0, zapis pliku.

### `io_txt_classic_300` — zapis: zebranie na proces 0 (m) vs MPI-IO (i)

| p | save m [ms] | save i [ms] | i/m | plik m [ms] | plik i [ms] | MB/s m / i | udział w total m / i | zebranie m (maks.) [ms] | formatowanie i (maks.) [ms] | MPI-IO i (maks.) [ms] | pamięć procesu 0 m / i [MB] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2 045 [2 043–2 055] | 2 409 [2 397–2 417] | ×1.178 | 1 629 [1 628–1 639] | 2 145 [2 135–2 155] | 345 / 262 | 35.0% / 39.0% | 43.4 | 1613.9 | 499.0 | 1145 / 925 | tak |
| 2 | 1 931 [1 925–1 935] | 1 478 [1 465–1 491] | ×0.765 | 1 633 [1 628–1 636] | 1 344 [1 331–1 359] | 344 / 418 | 45.7% / 40.7% | 162.4 | 817.7 | 521.2 | 760 / 464 | tak |
| 4 | 1 869 [1 864–1 873] | 983 [976–1 002] | ×0.526 | 1 629 [1 626–1 633] | 913 [908–933] | 345 / 616 | 55.5% / 43.4% | 168.8 | 405.0 | 500.4 | 566 / 236 | tak |
| 8 | 1 843 [1 840–1 850] | 728 [718–752] | ×0.395 | 1 631 [1 630–1 635] | 691 [677–715] | 345 / 814 | 61.0% / 42.7% | 174.8 | 207.6 | 489.6 | 469 / 125 | tak |
Plik: 562.29 MB. save — od końca fazy CA: pas bez ramki, (m) zebranie na proces 0, zapis pliku.

### `io_bin_classic_2000` — zapis: zebranie na proces 0 (m) vs MPI-IO (i)

| p | save m [ms] | save i [ms] | i/m | plik m [ms] | plik i [ms] | MB/s m / i | udział w total m / i | zebranie m (maks.) [ms] | formatowanie i (maks.) [ms] | MPI-IO i (maks.) [ms] | pamięć procesu 0 m / i [MB] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 87.2 [85.6–88.9] | 69.6 [68.2–70.4] | ×0.799 | 22.2 [21.8–22.9] | 27.3 [26.5–28.1] | 2345 / 1904 | 12.5% / 10.3% | 6.5 | 0.0 | 27.3 | 176 / 124 | tak |
| 2 | 69.7 [69.6–70.9] | 72.2 [70.6–83.3] | ×1.037 | 21.8 [21.6–23.1] | 48.5 [48.2–49.8] | 2384 / 1071 | 17.4% / 18.9% | 24.8 | 0.0 | 48.8 | 120 / 68 | tak |
| 4 | 61.5 [60.6–62.5] | 57.1 [56.8–58.5] | ×0.929 | 22.1 [21.5–22.5] | 44.2 [43.7–45.4] | 2350 / 1178 | 22.6% / 23.6% | 26.1 | 0.0 | 44.4 | 91 / 47 | tak |
| 8 | 58.4 [57.7–59.4] | 59.9 [51.8–67.5] | ×1.026 | 21.7 [21.4–22.6] | 49.1 [43.5–59.1] | 2393 / 1059 | 27.6% / 29.1% | 27.8 | 0.0 | 50.1 | 77 / 37 | tak |
Plik: 52.00 MB. save — od końca fazy CA: pas bez ramki, (m) zebranie na proces 0, zapis pliku.

### `io_txt_classic_2000` — zapis: zebranie na proces 0 (m) vs MPI-IO (i)

| p | save m [ms] | save i [ms] | i/m | plik m [ms] | plik i [ms] | MB/s m / i | udział w total m / i | zebranie m (maks.) [ms] | formatowanie i (maks.) [ms] | MPI-IO i (maks.) [ms] | pamięć procesu 0 m / i [MB] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 313 [313–315] | 366 [365–384] | ×1.169 | 248 [248–250] | 325 [324–343] | 348 / 266 | 33.9% / 37.6% | 6.5 | 248.6 | 71.5 | 176 / 150 | tak |
| 2 | 295 [294–296] | 217 [216–218] | ×0.736 | 248 [247–249] | 195 [194–196] | 348 / 443 | 47.2% / 41.3% | 24.4 | 125.4 | 69.0 | 120 / 80 | tak |
| 4 | 287 [286–291] | 132 [127–136] | ×0.460 | 248 [248–251] | 120 [115–124] | 348 / 720 | 58.1% / 43.1% | 25.7 | 63.4 | 57.0 | 91 / 46 | tak |
| 8 | 285 [283–309] | 89.9 [78.3–94.1] | ×0.315 | 248 [248–252] | 82.5 [70.6–86.1] | 348 / 1048 | 65.2% / 42.2% | 27.4 | 32.5 | 50.8 | 77 / 28 | tak |
Plik: 86.49 MB. save — od końca fazy CA: pas bez ramki, (m) zebranie na proces 0, zapis pliku.

### `io_bin_lava_3d` — zapis: zebranie na proces 0 (m) vs MPI-IO (i)

| p | save m [ms] | save i [ms] | i/m | plik m [ms] | plik i [ms] | MB/s m / i | udział w total m / i | zebranie m (maks.) [ms] | formatowanie i (maks.) [ms] | MPI-IO i (maks.) [ms] | pamięć procesu 0 m / i [MB] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 24.8 [24.5–25.5] | 21.0 [20.9–21.8] | ×0.848 | 6.30 [5.90–6.57] | 8.46 [8.23–8.72] | 2163 / 1612 | 3.2% / 2.7% | 1.6 | 0.0 | 8.4 | 56 / 42 | tak |
| 8 | 18.1 [17.8–20.4] | 23.4 [22.3–25.1] | ×1.292 | 6.11 [5.97–6.66] | 18.7 [18.4–19.6] | 2233 / 729 | 5.8% / 7.3% | 8.2 | 0.0 | 19.5 | 30 / 28 | tak |
Plik: 13.63 MB. save — od końca fazy CA: pas bez ramki, (m) zebranie na proces 0, zapis pliku.

### `io_txt_lava_3d` — zapis: zebranie na proces 0 (m) vs MPI-IO (i)

| p | save m [ms] | save i [ms] | i/m | plik m [ms] | plik i [ms] | MB/s m / i | udział w total m / i | zebranie m (maks.) [ms] | formatowanie i (maks.) [ms] | MPI-IO i (maks.) [ms] | pamięć procesu 0 m / i [MB] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 82.6 [82.1–83.6] | 89.0 [88.3–90.0] | ×1.078 | 63.7 [63.3–64.3] | 77.8 [76.7–77.8] | 299 / 245 | 10.0% / 10.7% | 1.6 | 63.6 | 12.8 | 56 / 45 | tak |
| 8 | 76.3 [73.7–76.6] | 29.2 [27.2–115] | ×0.382 | 63.8 [63.2–64.7] | 26.1 [24.7–111] | 299 / 730 | 20.4% / 9.1% | 8.2 | 8.7 | 18.1 | 30 / 16 | tak |
Plik: 19.07 MB. save — od końca fazy CA: pas bez ramki, (m) zebranie na proces 0, zapis pliku.

### `read_lava_3d` — odczyt --mc-from: proces 0 + MPI_Scatterv (m) vs MPI_File_read_at_all (i)

| p | readInput m [ms] | rozdział m (maks.) [ms] | odczyt i [ms] | MPI-IO i (maks.) [ms] | i / m (odczyt + rozdział) | total m / i [ms] | zgodne |
|---|---|---|---|---|---|---|---|
| 1 | 20.6 [20.0–20.9] | 0.6 | 2.95 [2.80–3.09] | 2.8 | ×0.139 | 121 / 101 | tak |
| 8 | 20.3 [19.7–20.7] | 5.5 | 5.28 [5.05–5.46] | 5.1 | ×0.204 | 89.6 / 64.1 | tak |
Przeczytane pasy (MPI-IO): 5.24 MB (type, solidStep, arrivalStep).

### `read_classic_300` — odczyt --mc-from: proces 0 + MPI_Scatterv (m) vs MPI_File_read_at_all (i)

| p | readInput m [ms] | rozdział m (maks.) [ms] | odczyt i [ms] | MPI-IO i (maks.) [ms] | i / m (odczyt + rozdział) | total m / i [ms] | zgodne |
|---|---|---|---|---|---|---|---|
| 1 | 515 [505–516] | 16.7 | 43.5 [43.0–43.9] | 43.3 | ×0.082 | 5 599 / 5 059 | tak |
| 8 | 516 [506–523] | 30.6 | 20.4 [20.2–22.5] | 20.2 | ×0.037 | 2 971 / 2 342 | tak |
Przeczytane pasy (MPI-IO): 135.00 MB (type, solidStep, arrivalStep).

