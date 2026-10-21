# Typy MPI i MPI-IO `dobor_gcc_bcast`

- Program: `engine_mpi_e11_gcc` (OpenMPI `mpiexec --allow-run-as-root --use-hwthread-cpus --bind-to none -n p` (WSL, wyniki na ext4)); `--high-priority`, `parallel.affinity = pcores`; warianty naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max]
- Czas pomiaru: 0.1 min, 2026-10-21T09:33
- Zgodność wyników w przypadku: wszystkie przebiegi bitowo zgodne

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
| m3 | 0.05 [0.05–0.05] | 881 | 0.01 [0.01–0.01] | 0.11 [0.11–0.11] | 0.00 [0.00–0.00] | 0 | 0.17 | tak |
| m3s | 0.03 [0.03–0.03] | 219 | 0.00 [0.00–0.00] | 0.01 [0.01–0.01] | 0.09 [0.09–0.09] | 6408 | 0.13 | tak |
| m8 | 0.10 [0.10–0.10] | 881 | 0.01 [0.01–0.01] | 0.14 [0.14–0.14] | 0.00 [0.00–0.00] | 0 | 0.25 | tak |
| m8s | 0.04 [0.04–0.04] | 219 | 0.00 [0.00–0.00] | 0.01 [0.01–0.01] | 0.27 [0.27–0.27] | 6408 | 0.32 | tak |


Tło (Windows, poza WSL): start 20% (WmiPrvSE.exe 225%, python.exe 51%, WmiPrvSE.exe 38%), koniec 24%.
