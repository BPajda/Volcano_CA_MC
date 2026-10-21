# Typy MPI i MPI-IO `pomiar_gcc_romio`

- Program: `engine_mpi_e11_gcc` (OpenMPI `mpiexec --mca io romio321 --allow-run-as-root --use-hwthread-cpus --bind-to none -n p` (WSL, wyniki na ext4)); `--high-priority`, `parallel.affinity = pcores`; warianty naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max]
- Czas pomiaru: 1.2 min, 2026-10-21T10:32
- Zgodność wyników w przypadku: wszystkie przebiegi bitowo zgodne

### `io_bin_classic_300` — zapis: zebranie na proces 0 (m) vs MPI-IO (i)

| p | save m [ms] | save i [ms] | i/m | plik m [ms] | plik i [ms] | MB/s m / i | udział w total m / i | zebranie m (maks.) [ms] | formatowanie i (maks.) [ms] | MPI-IO i (maks.) [ms] | pamięć procesu 0 m / i [MB] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 8 | 500 [405–553] | 292 [285–312] | ×0.585 | 222 [192–231] | 252 [239–264] | 1578 / 1392 | 22.2% / 17.3% | 237.0 | 0.0 | 253.3 | 479 / 128 | tak |
Plik: 351.00 MB. save — od końca fazy CA: pas bez ramki, (m) zebranie na proces 0, zapis pliku.

### `io_txt_classic_300` — zapis: zebranie na proces 0 (m) vs MPI-IO (i)

| p | save m [ms] | save i [ms] | i/m | plik m [ms] | plik i [ms] | MB/s m / i | udział w total m / i | zebranie m (maks.) [ms] | formatowanie i (maks.) [ms] | MPI-IO i (maks.) [ms] | pamięć procesu 0 m / i [MB] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 8 | 1 169 [994–1 218] | 577 [496–620] | ×0.493 | 911 [866–951] | 530 [458–574] | 587 / 1009 | 40.9% / 29.9% | 222.9 | 122.5 | 418.4 | 479 / 142 | tak |
Plik: 535.29 MB. save — od końca fazy CA: pas bez ramki, (m) zebranie na proces 0, zapis pliku.

### `io_bin_classic_2000` — zapis: zebranie na proces 0 (m) vs MPI-IO (i)

| p | save m [ms] | save i [ms] | i/m | plik m [ms] | plik i [ms] | MB/s m / i | udział w total m / i | zebranie m (maks.) [ms] | formatowanie i (maks.) [ms] | MPI-IO i (maks.) [ms] | pamięć procesu 0 m / i [MB] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 8 | 55.0 [51.2–56.5] | 42.7 [38.5–46.4] | ×0.777 | 30.4 [27.9–31.8] | 37.6 [32.2–41.1] | 1713 / 1384 | 9.9% / 8.2% | 18.2 | 0.0 | 37.6 | 88 / 50 | tak |
Plik: 52.00 MB. save — od końca fazy CA: pas bez ramki, (m) zebranie na proces 0, zapis pliku.

### `io_txt_classic_2000` — zapis: zebranie na proces 0 (m) vs MPI-IO (i)

| p | save m [ms] | save i [ms] | i/m | plik m [ms] | plik i [ms] | MB/s m / i | udział w total m / i | zebranie m (maks.) [ms] | formatowanie i (maks.) [ms] | MPI-IO i (maks.) [ms] | pamięć procesu 0 m / i [MB] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 8 | 154 [152–187] | 77.1 [58.7–171] | ×0.500 | 129 [125–162] | 70.9 [52.8–166] | 638 / 1163 | 22.1% / 13.7% | 19.0 | 17.7 | 54.3 | 88 / 42 | tak |
Plik: 82.49 MB. save — od końca fazy CA: pas bez ramki, (m) zebranie na proces 0, zapis pliku.


Tło (Windows, poza WSL): start 17% (WmiPrvSE.exe 212%, python.exe 39%, svchost.exe 35%), koniec 24%.
