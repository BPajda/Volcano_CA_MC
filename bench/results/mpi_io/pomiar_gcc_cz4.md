# Typy MPI i MPI-IO `pomiar_gcc_cz4`

- Program: `engine_mpi_e11_gcc` (OpenMPI `mpiexec --allow-run-as-root --use-hwthread-cpus --bind-to none -n p` (WSL, wyniki na ext4)); `--high-priority`, `parallel.affinity = pcores`; warianty naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max]
- Czas pomiaru: 0.2 min, 2026-10-21T10:30
- Zgodność wyników w przypadku: wszystkie przebiegi bitowo zgodne

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


Tło (Windows, poza WSL): start 14% (WmiPrvSE.exe 167%, inny program 89%, python.exe 40%), koniec 20%.
