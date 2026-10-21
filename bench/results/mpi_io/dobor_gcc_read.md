# Typy MPI i MPI-IO `dobor_gcc_read`

- Program: `engine_mpi_e11_gcc` (OpenMPI `mpiexec --allow-run-as-root --use-hwthread-cpus --bind-to none -n p` (WSL, wyniki na ext4)); `--high-priority`, `parallel.affinity = pcores`; warianty naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max]
- Czas pomiaru: 0.4 min, 2026-10-21T09:34
- Zgodność wyników w przypadku: wszystkie przebiegi bitowo zgodne

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


Tło (Windows, poza WSL): start 23% (WmiPrvSE.exe 216%, System 52%, python.exe 45%), koniec 26%.
