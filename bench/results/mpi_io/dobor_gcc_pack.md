# Typy MPI i MPI-IO `dobor_gcc_pack`

- Program: `engine_mpi_e11_gcc` (OpenMPI `mpiexec --allow-run-as-root --use-hwthread-cpus --bind-to none -n p` (WSL, wyniki na ext4)); `--high-priority`, `parallel.affinity = pcores`; warianty naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max]
- Czas pomiaru: 0.8 min, 2026-10-21T09:31
- Zgodność wyników w przypadku: wszystkie przebiegi bitowo zgodne

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


Tło (Windows, poza WSL): start 18% (WmiPrvSE.exe 223%, python.exe 49%, svchost.exe 42%), koniec 23%.
