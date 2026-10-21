# Typy MPI i MPI-IO `pomiar_gcc_cz3`

- Program: `engine_mpi_e11_gcc` (OpenMPI `mpiexec --allow-run-as-root --use-hwthread-cpus --bind-to none -n p` (WSL, wyniki na ext4)); `--high-priority`, `parallel.affinity = pcores`; warianty naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max]
- Czas pomiaru: 1.5 min, 2026-10-21T10:29
- Zgodność wyników w przypadku: wszystkie przebiegi bitowo zgodne

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


Tło (Windows, poza WSL): start 10% (WmiPrvSE.exe 143%, python.exe 43%, System 27%), koniec 19%.
