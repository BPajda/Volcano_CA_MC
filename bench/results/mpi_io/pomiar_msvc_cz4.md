# Typy MPI i MPI-IO `pomiar_msvc_cz4`

- Program: `engine_mpi_e11_msvc.exe` (MS-MPI `mpiexec -n p`); `--high-priority`, `parallel.affinity = pcores`; warianty naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max]
- Czas pomiaru: 3.0 min, 2026-10-21T10:23
- Tło: start 13% CPU (WmiPrvSE.exe 209%, svchost.exe 42%, python.exe 38%), koniec 12%
- Zgodność wyników w przypadku: wszystkie przebiegi bitowo zgodne

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

