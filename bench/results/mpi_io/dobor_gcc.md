# Typy MPI i MPI-IO `dobor_gcc`

- Tabele z pomiaru w częściach: bench\results\mpi_io\dobor_gcc_pack_raw.csv,bench\results\mpi_io\dobor_gcc_io_raw.csv,bench\results\mpi_io\dobor_gcc_bcast_raw.csv,bench\results\mpi_io\dobor_gcc_read_raw.csv
- `dobor_gcc_pack_raw.csv`: Czas pomiaru: 0.8 min, 2026-10-21T09:31
- `dobor_gcc_pack_raw.csv`: Tło (Windows, poza WSL): start 18% (WmiPrvSE.exe 223%, python.exe 49%, svchost.exe 42%), koniec 23%.
- `dobor_gcc_io_raw.csv`: Czas pomiaru: 1.3 min, 2026-10-21T09:33
- `dobor_gcc_io_raw.csv`: Tło (Windows, poza WSL): start 21% (WmiPrvSE.exe 238%, python.exe 49%, inny program 48%), koniec 24%.
- `dobor_gcc_bcast_raw.csv`: Czas pomiaru: 0.1 min, 2026-10-21T09:33
- `dobor_gcc_bcast_raw.csv`: Tło (Windows, poza WSL): start 20% (WmiPrvSE.exe 225%, python.exe 51%, WmiPrvSE.exe 38%), koniec 24%.
- `dobor_gcc_read_raw.csv`: Czas pomiaru: 0.4 min, 2026-10-21T09:34
- `dobor_gcc_read_raw.csv`: Tło (Windows, poza WSL): start 23% (WmiPrvSE.exe 216%, System 52%, python.exe 45%), koniec 26%.

### `pack_lava_3d_front` — wymiana warstw: pakowanie (m) vs typy pochodne (d)

| p | faza m [ms] | faza d [ms] | d/m faza | wymiana m [ms] | wymiana d [ms] | d/m wymiana | na wymianę m / d [ms] | B / wymianę m / d | komunikaty / wymianę | typy (suma) | budowa typów [ms] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4 | 440 [440–440] | 383 [383–383] | ×0.871 | 63.4 [63.4–63.4] | 33.9 [33.9–33.9] | ×0.534 | 0.244 / 0.130 | 1.71 MB / 1.71 MB | 8.0 / 8.0 | 16 | 0.016 | tak |
| 8 | 500 [500–500] | 430 [430–430] | ×0.861 | 129 [129–129] | 93.0 [93.0–93.0] | ×0.722 | 0.496 / 0.358 | 3.85 MB / 3.85 MB | 25.0 / 25.0 | 50 | 0.014 | tak |

### `pack_lava_3d_full` — wymiana warstw: pakowanie (m) vs typy pochodne (d)

| p | faza m [ms] | faza d [ms] | d/m faza | wymiana m [ms] | wymiana d [ms] | d/m wymiana | na wymianę m / d [ms] | B / wymianę m / d | komunikaty / wymianę | typy (suma) | budowa typów [ms] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4 | 4 624 [4 624–4 624] | 4 577 [4 577–4 577] | ×0.990 | 121 [121–121] | 80.5 [80.5–80.5] | ×0.665 | 0.466 / 0.310 | 1.71 MB / 1.71 MB | 8.0 / 8.0 | 32 | 0.022 | tak |
| 8 | 2 967 [2 967–2 967] | 3 053 [3 053–3 053] | ×1.029 | 176 [176–176] | 145 [145–145] | ×0.825 | 0.677 / 0.558 | 3.85 MB / 3.85 MB | 25.0 / 25.0 | 100 | 0.041 | tak |

### `pack_classic_300` — wymiana warstw: pakowanie (m) vs typy pochodne (d)

| p | faza m [ms] | faza d [ms] | d/m faza | wymiana m [ms] | wymiana d [ms] | d/m wymiana | na wymianę m / d [ms] | B / wymianę m / d | komunikaty / wymianę | typy (suma) | budowa typów [ms] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4 | 4 148 [4 148–4 148] | 1 535 [1 535–1 535] | ×0.370 | 229 [229–229] | 75.0 [75.0–75.0] | ×0.328 | 2.009 / 0.658 | 5.11 MB / 5.11 MB | 8.0 / 8.0 | 16 | 0.015 | tak |
| 8 | 1 641 [1 641–1 641] | 1 212 [1 212–1 212] | ×0.738 | 167 [167–167] | 122 [122–122] | ×0.727 | 1.467 / 1.067 | 10.21 MB / 10.21 MB | 16.0 / 16.0 | 32 | 0.012 | tak |

### `pack_mc_cb_3d_100` — wymiana warstw: pakowanie (m) vs typy pochodne (d)

| p | faza m [ms] | faza d [ms] | d/m faza | wymiana m [ms] | wymiana d [ms] | d/m wymiana | na wymianę m / d [ms] | B / wymianę m / d | komunikaty / wymianę | typy (suma) | budowa typów [ms] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4 | 2 268 [2 268–2 268] | 1 790 [1 790–1 790] | ×0.789 | 621 [621–621] | 287 [287–287] | ×0.462 | 0.775 / 0.358 | 0.33 MB / 0.33 MB | 8.0 / 8.0 | 16 | 0.011 | tak |
| 8 | 1 524 [1 524–1 524] | 1 504 [1 504–1 504] | ×0.987 | 600 [600–600] | 599 [599–599] | ×0.997 | 0.750 / 0.747 | 0.67 MB / 0.67 MB | 16.0 / 16.0 | 32 | 0.012 | tak |

### `bcast_etna_real` — rozsyłanie: JSON (m) vs struktury (s)

| wariant | MPI_Bcast configu [ms] | config [B] | przygotowanie (proces 0) [ms] | budowa Config (maks.) [ms] | kratery [ms] | kratery [B] | razem [ms] | zgodne |
|---|---|---|---|---|---|---|---|---|
| m3 | 0.05 [0.05–0.05] | 938 | 0.01 [0.01–0.01] | 0.11 [0.11–0.11] | 0.00 [0.00–0.00] | 0 | 0.17 | tak |
| m3s | 0.03 [0.03–0.03] | 219 | 0.00 [0.00–0.00] | 0.01 [0.01–0.01] | 0.01 [0.01–0.01] | 56 | 0.06 | tak |
| m8 | 0.05 [0.05–0.05] | 938 | 0.01 [0.01–0.01] | 0.14 [0.14–0.14] | 0.00 [0.00–0.00] | 0 | 0.20 | tak |
| m8s | 0.04 [0.04–0.04] | 219 | 0.00 [0.00–0.00] | 0.02 [0.02–0.02] | 0.02 [0.02–0.02] | 56 | 0.08 | tak |

### `bcast_classic_2000` — rozsyłanie: JSON (m) vs struktury (s)

| wariant | MPI_Bcast configu [ms] | config [B] | przygotowanie (proces 0) [ms] | budowa Config (maks.) [ms] | kratery [ms] | kratery [B] | razem [ms] | zgodne |
|---|---|---|---|---|---|---|---|---|
| m3 | 0.05 [0.05–0.05] | 881 | 0.01 [0.01–0.01] | 0.11 [0.11–0.11] | 0.00 [0.00–0.00] | 0 | 0.18 | tak |
| m3s | 0.03 [0.03–0.03] | 219 | 0.00 [0.00–0.00] | 0.01 [0.01–0.01] | 0.09 [0.09–0.09] | 6408 | 0.13 | tak |
| m8 | 0.10 [0.10–0.10] | 881 | 0.01 [0.01–0.01] | 0.14 [0.14–0.14] | 0.00 [0.00–0.00] | 0 | 0.25 | tak |
| m8s | 0.04 [0.04–0.04] | 219 | 0.00 [0.00–0.00] | 0.01 [0.01–0.01] | 0.27 [0.27–0.27] | 6408 | 0.32 | tak |

### `io_bin_classic_300` — zapis: zebranie na proces 0 (m) vs MPI-IO (i)

| p | save m [ms] | save i [ms] | i/m | plik m [ms] | plik i [ms] | MB/s m / i | udział w total m / i | zebranie m (maks.) [ms] | formatowanie i (maks.) [ms] | MPI-IO i (maks.) [ms] | pamięć procesu 0 m / i [MB] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 740 [740–740] | 447 [447–447] | ×0.604 | 208 [208–208] | 147 [147–147] | 1684 / 2387 | 14.2% / 9.8% | 44.8 | 0.0 | 147.0 | 1155 / 804 | tak |
| 4 | 568 [568–568] | 377 [377–377] | ×0.664 | 197 [197–197] | 332 [332–332] | 1779 / 1058 | 22.4% / 16.4% | 284.5 | 0.0 | 334.3 | 577 / 224 | tak |
| 8 | 770 [770–770] | 529 [529–529] | ×0.687 | 261 [261–261] | 469 [469–469] | 1346 / 748 | 26.9% / 15.6% | 455.5 | 0.0 | 475.4 | 479 / 129 | tak |
Plik: 351.00 MB. save — od końca fazy CA: pas bez ramki, (m) zebranie na proces 0, zapis pliku.

### `io_txt_classic_300` — zapis: zebranie na proces 0 (m) vs MPI-IO (i)

| p | save m [ms] | save i [ms] | i/m | plik m [ms] | plik i [ms] | MB/s m / i | udział w total m / i | zebranie m (maks.) [ms] | formatowanie i (maks.) [ms] | MPI-IO i (maks.) [ms] | pamięć procesu 0 m / i [MB] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 448 [1 448–1 448] | 1 705 [1 705–1 705] | ×1.177 | 963 [963–963] | 1 445 [1 445–1 445] | 556 / 370 | 25.2% / 29.1% | 46.9 | 944.6 | 499.2 | 1155 / 912 | tak |
| 4 | 1 165 [1 165–1 165] | 1 379 [1 379–1 379] | ×1.183 | 878 [878–878] | 1 323 [1 323–1 323] | 610 / 405 | 36.9% / 43.9% | 246.6 | 250.1 | 1115.0 | 575 / 277 | tak |
| 8 | 1 319 [1 319–1 319] | 1 889 [1 889–1 889] | ×1.433 | 1 155 [1 155–1 155] | 1 849 [1 849–1 849] | 464 / 290 | 38.3% / 51.0% | 131.5 | 165.1 | 1733.3 | 479 / 176 | tak |
Plik: 535.29 MB. save — od końca fazy CA: pas bez ramki, (m) zebranie na proces 0, zapis pliku.

### `io_bin_classic_2000` — zapis: zebranie na proces 0 (m) vs MPI-IO (i)

| p | save m [ms] | save i [ms] | i/m | plik m [ms] | plik i [ms] | MB/s m / i | udział w total m / i | zebranie m (maks.) [ms] | formatowanie i (maks.) [ms] | MPI-IO i (maks.) [ms] | pamięć procesu 0 m / i [MB] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 73.4 [73.4–73.4] | 51.8 [51.8–51.8] | ×0.706 | 30.2 [30.2–30.2] | 28.1 [28.1–28.1] | 1722 / 1853 | 7.8% / 5.0% | 6.3 | 0.0 | 28.1 | 187 / 134 | tak |
| 4 | 61.2 [61.2–61.2] | 86.4 [86.4–86.4] | ×1.412 | 34.7 [34.7–34.7] | 78.3 [78.3–78.3] | 1497 / 664 | 10.3% / 15.1% | 18.5 | 0.0 | 78.3 | 104 / 71 | tak |
| 8 | 115 [115–115] | 130 [130–130] | ×1.134 | 54.6 [54.6–54.6] | 122 [122–122] | 952 / 425 | 15.5% / 14.4% | 54.1 | 0.0 | 124.0 | 88 / 64 | tak |
Plik: 52.00 MB. save — od końca fazy CA: pas bez ramki, (m) zebranie na proces 0, zapis pliku.

### `io_txt_classic_2000` — zapis: zebranie na proces 0 (m) vs MPI-IO (i)

| p | save m [ms] | save i [ms] | i/m | plik m [ms] | plik i [ms] | MB/s m / i | udział w total m / i | zebranie m (maks.) [ms] | formatowanie i (maks.) [ms] | MPI-IO i (maks.) [ms] | pamięć procesu 0 m / i [MB] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 217 [217–217] | 255 [255–255] | ×1.177 | 141 [141–141] | 211 [211–211] | 584 / 391 | 18.6% / 21.0% | 6.5 | 147.5 | 63.4 | 189 / 165 | tak |
| 4 | 185 [185–185] | 226 [226–226] | ×1.221 | 158 [158–158] | 218 [218–218] | 523 / 378 | 25.2% / 32.0% | 19.4 | 74.3 | 161.2 | 102 / 93 | tak |
| 8 | 237 [237–237] | 212 [212–212] | ×0.896 | 204 [204–204] | 206 [206–206] | 405 / 400 | 25.2% / 26.5% | 25.4 | 38.8 | 183.4 | 88 / 76 | tak |
Plik: 82.49 MB. save — od końca fazy CA: pas bez ramki, (m) zebranie na proces 0, zapis pliku.

### `io_bin_lava_3d` — zapis: zebranie na proces 0 (m) vs MPI-IO (i)

| p | save m [ms] | save i [ms] | i/m | plik m [ms] | plik i [ms] | MB/s m / i | udział w total m / i | zebranie m (maks.) [ms] | formatowanie i (maks.) [ms] | MPI-IO i (maks.) [ms] | pamięć procesu 0 m / i [MB] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 21.6 [21.6–21.6] | 17.4 [17.4–17.4] | ×0.805 | 7.77 [7.77–7.77] | 8.85 [8.85–8.85] | 1754 / 1540 | 2.3% / 1.7% | 1.7 | 0.0 | 8.8 | 67 / 53 | tak |
| 4 | 16.9 [16.9–16.9] | 17.1 [17.1–17.1] | ×1.015 | 8.08 [8.08–8.08] | 14.8 [14.8–14.8] | 1687 / 923 | 2.2% / 2.1% | 6.3 | 0.0 | 14.8 | 47 / 42 | tak |
| 8 | 16.0 [16.0–16.0] | 28.6 [28.6–28.6] | ×1.791 | 7.58 [7.58–7.58] | 26.5 [26.5–26.5] | 1799 / 515 | 1.8% / 3.2% | 6.2 | 0.0 | 26.5 | 42 / 41 | tak |
Plik: 13.63 MB. save — od końca fazy CA: pas bez ramki, (m) zebranie na proces 0, zapis pliku.

### `io_txt_lava_3d` — zapis: zebranie na proces 0 (m) vs MPI-IO (i)

| p | save m [ms] | save i [ms] | i/m | plik m [ms] | plik i [ms] | MB/s m / i | udział w total m / i | zebranie m (maks.) [ms] | formatowanie i (maks.) [ms] | MPI-IO i (maks.) [ms] | pamięć procesu 0 m / i [MB] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 38.3 [38.3–38.3] | 52.9 [52.9–52.9] | ×1.382 | 24.1 [24.1–24.1] | 43.0 [43.0–43.0] | 748 / 419 | 3.9% / 5.3% | 1.6 | 33.5 | 9.5 | 67 / 56 | tak |
| 4 | 33.0 [33.0–33.0] | 41.0 [41.0–41.0] | ×1.240 | 23.3 [23.3–23.3] | 38.1 [38.1–38.1] | 775 / 474 | 4.6% / 4.9% | 7.3 | 12.8 | 27.9 | 45 / 53 | tak |
| 8 | 43.2 [43.2–43.2] | 51.0 [51.0–51.0] | ×1.182 | 29.3 [29.3–29.3] | 48.5 [48.5–48.5] | 614 / 371 | 5.1% / 4.8% | 11.1 | 13.5 | 43.5 | 44 / 45 | tak |
Plik: 18.02 MB. save — od końca fazy CA: pas bez ramki, (m) zebranie na proces 0, zapis pliku.

### `read_lava_3d` — odczyt --mc-from: proces 0 + MPI_Scatterv (m) vs MPI_File_read_at_all (i)

| p | readInput m [ms] | rozdział m (maks.) [ms] | odczyt i [ms] | MPI-IO i (maks.) [ms] | i / m (odczyt + rozdział) | total m / i [ms] | zgodne |
|---|---|---|---|---|---|---|---|
| 1 | 9.16 [9.16–9.16] | 0.8 | 3.24 [3.24–3.24] | 3.2 | ×0.327 | 342 / 334 | tak |
| 8 | 11.3 [11.3–11.3] | 83.8 | 26.6 [26.6–26.6] | 26.5 | ×0.279 | 546 / 499 | tak |
Przeczytane pasy (MPI-IO): 5.24 MB (type, solidStep, arrivalStep).

### `read_classic_300` — odczyt --mc-from: proces 0 + MPI_Scatterv (m) vs MPI_File_read_at_all (i)

| p | readInput m [ms] | rozdział m (maks.) [ms] | odczyt i [ms] | MPI-IO i (maks.) [ms] | i / m (odczyt + rozdział) | total m / i [ms] | zgodne |
|---|---|---|---|---|---|---|---|
| 1 | 563 [563–563] | 16.8 | 33.0 [33.0–33.0] | 33.0 | ×0.057 | 5 107 / 3 976 | tak |
| 8 | 126 [126–126] | 26.9 | 62.9 [62.9–62.9] | 62.8 | ×0.411 | 3 073 / 2 797 | tak |
Przeczytane pasy (MPI-IO): 135.00 MB (type, solidStep, arrivalStep).

