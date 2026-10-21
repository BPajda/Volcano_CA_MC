# Typy MPI i MPI-IO `pomiar_gcc_cz2`

- Program: `engine_mpi_e11_gcc` (OpenMPI `mpiexec --allow-run-as-root --use-hwthread-cpus --bind-to none -n p` (WSL, wyniki na ext4)); `--high-priority`, `parallel.affinity = pcores`; warianty naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max]
- Czas pomiaru: 1.2 min, 2026-10-21T10:27
- Zgodność wyników w przypadku: wszystkie przebiegi bitowo zgodne

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


Tło (Windows, poza WSL): start 13% (WmiPrvSE.exe 191%, python.exe 40%, svchost.exe 33%), koniec 19%.
