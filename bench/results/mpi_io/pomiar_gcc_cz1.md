# Typy MPI i MPI-IO `pomiar_gcc_cz1`

- Program: `engine_mpi_e11_gcc` (OpenMPI `mpiexec --allow-run-as-root --use-hwthread-cpus --bind-to none -n p` (WSL, wyniki na ext4)); `--high-priority`, `parallel.affinity = pcores`; warianty naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max]
- Czas pomiaru: 1.0 min, 2026-10-21T10:25
- Zgodność wyników w przypadku: wszystkie przebiegi bitowo zgodne

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


Tło (Windows, poza WSL): start 16% (WmiPrvSE.exe 214%, Code.exe 63%, python.exe 38%), koniec 16%.
