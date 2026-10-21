# Typy MPI i MPI-IO `pomiar_gcc`

- Tabele z pomiaru w częściach: bench\results\mpi_io\pomiar_gcc_cz1_raw.csv,bench\results\mpi_io\pomiar_gcc_cz2_raw.csv,bench\results\mpi_io\pomiar_gcc_cz3_raw.csv,bench\results\mpi_io\pomiar_gcc_cz4_raw.csv
- `pomiar_gcc_cz1_raw.csv`: Czas pomiaru: 1.0 min, 2026-10-21T10:25
- `pomiar_gcc_cz1_raw.csv`: Tło (Windows, poza WSL): start 16% (WmiPrvSE.exe 214%, Code.exe 63%, python.exe 38%), koniec 16%.
- `pomiar_gcc_cz2_raw.csv`: Czas pomiaru: 1.2 min, 2026-10-21T10:27
- `pomiar_gcc_cz2_raw.csv`: Tło (Windows, poza WSL): start 13% (WmiPrvSE.exe 191%, python.exe 40%, svchost.exe 33%), koniec 19%.
- `pomiar_gcc_cz3_raw.csv`: Czas pomiaru: 1.5 min, 2026-10-21T10:29
- `pomiar_gcc_cz3_raw.csv`: Tło (Windows, poza WSL): start 10% (WmiPrvSE.exe 143%, python.exe 43%, System 27%), koniec 19%.
- `pomiar_gcc_cz4_raw.csv`: Czas pomiaru: 0.2 min, 2026-10-21T10:30
- `pomiar_gcc_cz4_raw.csv`: Tło (Windows, poza WSL): start 14% (WmiPrvSE.exe 167%, inny program 89%, python.exe 40%), koniec 20%.

### `pack_lava_3d_front` — wymiana warstw: pakowanie (m) vs typy pochodne (d)

| p | faza m [ms] | faza d [ms] | d/m faza | wymiana m [ms] | wymiana d [ms] | d/m wymiana | na wymianę m / d [ms] | B / wymianę m / d | komunikaty / wymianę | typy (suma) | budowa typów [ms] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 8 | 283 [259–341] | 252 [226–290] | ×0.892 | 55.3 [48.2–75.6] | 37.4 [34.7–42.7] | ×0.677 | 0.213 / 0.144 | 3.85 MB / 3.85 MB | 25.0 / 25.0 | 50 | 0.013 | tak |

### `pack_classic_300` — wymiana warstw: pakowanie (m) vs typy pochodne (d)

| p | faza m [ms] | faza d [ms] | d/m faza | wymiana m [ms] | wymiana d [ms] | d/m wymiana | na wymianę m / d [ms] | B / wymianę m / d | komunikaty / wymianę | typy (suma) | budowa typów [ms] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 8 | 960 [945–1 027] | 928 [856–1 001] | ×0.967 | 111 [106–115] | 65.4 [63.5–69.3] | ×0.587 | 0.977 / 0.574 | 10.21 MB / 10.21 MB | 16.0 / 16.0 | 32 | 0.011 | tak |

### `pack_mc_cb_3d_100` — wymiana warstw: pakowanie (m) vs typy pochodne (d)

| p | faza m [ms] | faza d [ms] | d/m faza | wymiana m [ms] | wymiana d [ms] | d/m wymiana | na wymianę m / d [ms] | B / wymianę m / d | komunikaty / wymianę | typy (suma) | budowa typów [ms] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 8 | 1 163 [1 139–1 286] | 1 168 [1 059–1 216] | ×1.004 | 363 [336–467] | 372 [284–394] | ×1.023 | 0.454 / 0.464 | 0.67 MB / 0.67 MB | 16.0 / 16.0 | 32 | 0.011 | tak |

### `bcast_etna_real` — rozsyłanie: JSON (m) vs struktury (s)

| wariant | MPI_Bcast configu [ms] | config [B] | przygotowanie (proces 0) [ms] | budowa Config (maks.) [ms] | kratery [ms] | kratery [B] | razem [ms] | zgodne |
|---|---|---|---|---|---|---|---|---|
| m8 | 0.06 [0.05–0.12] | 938 | 0.01 [0.01–0.02] | 0.14 [0.11–12.9] | 0.00 [0.00–0.00] | 0 | 0.21 | tak |
| m8s | 0.03 [0.03–0.08] | 219 | 0.00 [0.00–0.01] | 0.02 [0.01–0.02] | 0.01 [0.01–0.02] | 56 | 0.07 | tak |

### `bcast_classic_2000` — rozsyłanie: JSON (m) vs struktury (s)

| wariant | MPI_Bcast configu [ms] | config [B] | przygotowanie (proces 0) [ms] | budowa Config (maks.) [ms] | kratery [ms] | kratery [B] | razem [ms] | zgodne |
|---|---|---|---|---|---|---|---|---|
| m8 | 0.06 [0.06–8.87] | 881 | 0.01 [0.01–0.02] | 0.14 [0.13–0.23] | 0.00 [0.00–0.00] | 0 | 0.30 | tak |
| m8s | 0.03 [0.03–0.04] | 219 | 0.00 [0.00–0.00] | 0.02 [0.01–0.02] | 1.15 [0.10–1.77] | 6408 | 1.20 | tak |

### `io_bin_classic_300` — zapis: zebranie na proces 0 (m) vs MPI-IO (i)

| p | save m [ms] | save i [ms] | i/m | plik m [ms] | plik i [ms] | MB/s m / i | udział w total m / i | zebranie m (maks.) [ms] | formatowanie i (maks.) [ms] | MPI-IO i (maks.) [ms] | pamięć procesu 0 m / i [MB] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 8 | 496 [380–556] | 381 [366–442] | ×0.769 | 214 [198–372] | 335 [330–397] | 1642 / 1047 | 22.5% / 21.0% | 227.1 | 0.0 | 336.2 | 479 / 128 | tak |
Plik: 351.00 MB. save — od końca fazy CA: pas bez ramki, (m) zebranie na proces 0, zapis pliku.

### `io_txt_classic_300` — zapis: zebranie na proces 0 (m) vs MPI-IO (i)

| p | save m [ms] | save i [ms] | i/m | plik m [ms] | plik i [ms] | MB/s m / i | udział w total m / i | zebranie m (maks.) [ms] | formatowanie i (maks.) [ms] | MPI-IO i (maks.) [ms] | pamięć procesu 0 m / i [MB] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 8 | 1 175 [1 105–1 256] | 1 035 [942–1 115] | ×0.881 | 903 [858–1 070] | 1 008 [905–1 066] | 593 / 531 | 40.8% / 41.1% | 209.4 | 145.4 | 899.4 | 479 / 176 | tak |
Plik: 535.29 MB. save — od końca fazy CA: pas bez ramki, (m) zebranie na proces 0, zapis pliku.

### `io_bin_classic_2000` — zapis: zebranie na proces 0 (m) vs MPI-IO (i)

| p | save m [ms] | save i [ms] | i/m | plik m [ms] | plik i [ms] | MB/s m / i | udział w total m / i | zebranie m (maks.) [ms] | formatowanie i (maks.) [ms] | MPI-IO i (maks.) [ms] | pamięć procesu 0 m / i [MB] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 8 | 52.6 [49.9–56.3] | 85.4 [76.2–189] | ×1.623 | 28.9 [27.7–30.0] | 80.4 [71.3–184] | 1800 / 647 | 9.2% / 14.6% | 18.9 | 0.0 | 80.5 | 88 / 65 | tak |
Plik: 52.00 MB. save — od końca fazy CA: pas bez ramki, (m) zebranie na proces 0, zapis pliku.

### `io_txt_classic_2000` — zapis: zebranie na proces 0 (m) vs MPI-IO (i)

| p | save m [ms] | save i [ms] | i/m | plik m [ms] | plik i [ms] | MB/s m / i | udział w total m / i | zebranie m (maks.) [ms] | formatowanie i (maks.) [ms] | MPI-IO i (maks.) [ms] | pamięć procesu 0 m / i [MB] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 8 | 166 [153–203] | 158 [125–187] | ×0.953 | 139 [129–169] | 151 [118–179] | 592 / 545 | 22.9% / 24.5% | 21.1 | 27.4 | 136.3 | 88 / 75 | tak |
Plik: 82.49 MB. save — od końca fazy CA: pas bez ramki, (m) zebranie na proces 0, zapis pliku.

### `read_lava_3d` — odczyt --mc-from: proces 0 + MPI_Scatterv (m) vs MPI_File_read_at_all (i)

| p | readInput m [ms] | rozdział m (maks.) [ms] | odczyt i [ms] | MPI-IO i (maks.) [ms] | i / m (odczyt + rozdział) | total m / i [ms] | zgodne |
|---|---|---|---|---|---|---|---|
| 1 | 6.40 [5.93–6.76] | 0.6 | 2.60 [2.55–8.70] | 2.6 | ×0.371 | 325 / 325 | tak |
| 8 | 6.84 [5.91–8.17] | 0.8 | 8.48 [4.45–13.4] | 8.4 | ×1.104 | 418 / 427 | tak |
Przeczytane pasy (MPI-IO): 5.24 MB (type, solidStep, arrivalStep).

### `read_classic_300` — odczyt --mc-from: proces 0 + MPI_Scatterv (m) vs MPI_File_read_at_all (i)

| p | readInput m [ms] | rozdział m (maks.) [ms] | odczyt i [ms] | MPI-IO i (maks.) [ms] | i / m (odczyt + rozdział) | total m / i [ms] | zgodne |
|---|---|---|---|---|---|---|---|
| 1 | 106 [95.3–218] | 16.1 | 20.5 [20.1–27.5] | 20.5 | ×0.168 | 4 142 / 3 902 | tak |
| 8 | 101 [94.5–112] | 23.3 | 54.0 [44.4–132] | 53.9 | ×0.433 | 2 643 / 2 495 | tak |
Przeczytane pasy (MPI-IO): 135.00 MB (type, solidStep, arrivalStep).

