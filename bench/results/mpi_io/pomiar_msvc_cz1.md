# Typy MPI i MPI-IO `pomiar_msvc_cz1`

- Program: `engine_mpi_e11_msvc.exe` (MS-MPI `mpiexec -n p`); `--high-priority`, `parallel.affinity = pcores`; warianty naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max]
- Czas pomiaru: 3.8 min, 2026-10-21T10:10
- Tło: start 15% CPU (WmiPrvSE.exe 212%, svchost.exe 40%, python.exe 39%), koniec 14%
- Zgodność wyników w przypadku: wszystkie przebiegi bitowo zgodne

### `pack_lava_3d_front` — wymiana warstw: pakowanie (m) vs typy pochodne (d)

| p | faza m [ms] | faza d [ms] | d/m faza | wymiana m [ms] | wymiana d [ms] | d/m wymiana | na wymianę m / d [ms] | B / wymianę m / d | komunikaty / wymianę | typy (suma) | budowa typów [ms] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 670 [668–675] | 668 [658–679] | ×0.997 | 34.2 [33.9–35.8] | 24.5 [22.5–28.4] | ×0.717 | 0.132 / 0.094 | 0.57 MB / 0.57 MB | 2.0 / 2.0 | 4 | 0.042 | tak |
| 4 | 399 [397–836] | 380 [378–386] | ×0.953 | 51.2 [51.0–271] | 32.5 [31.9–34.6] | ×0.634 | 0.197 / 0.125 | 1.71 MB / 1.71 MB | 8.0 / 8.0 | 16 | 0.091 | tak |
| 7 | 285 [282–290] | 268 [265–278] | ×0.940 | 53.7 [52.3–56.0] | 32.3 [31.0–37.3] | ×0.601 | 0.207 / 0.124 | 3.33 MB / 3.33 MB | 17.0 / 17.0 | 34 | 0.091 | tak |
| 8 | 264 [255–326] | 243 [235–265] | ×0.922 | 63.4 [58.4–97.7] | 39.0 [36.0–54.8] | ×0.615 | 0.244 / 0.150 | 3.85 MB / 3.85 MB | 25.0 / 25.0 | 50 | 0.099 | tak |

### `pack_lava_3d_full` — wymiana warstw: pakowanie (m) vs typy pochodne (d)

| p | faza m [ms] | faza d [ms] | d/m faza | wymiana m [ms] | wymiana d [ms] | d/m wymiana | na wymianę m / d [ms] | B / wymianę m / d | komunikaty / wymianę | typy (suma) | budowa typów [ms] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 8 453 [8 421–9 054] | 8 462 [8 418–9 403] | ×1.001 | 61.3 [60.0–70.0] | 42.8 [42.4–45.8] | ×0.698 | 0.236 / 0.165 | 0.57 MB / 0.57 MB | 2.0 / 2.0 | 8 | 0.114 | tak |
| 4 | 4 361 [4 309–4 409] | 4 316 [4 294–4 348] | ×0.990 | 86.2 [84.0–94.8] | 64.3 [62.5–64.6] | ×0.746 | 0.332 / 0.247 | 1.71 MB / 1.71 MB | 8.0 / 8.0 | 32 | 0.121 | tak |
| 7 | 2 619 [2 574–3 306] | 2 571 [2 538–2 592] | ×0.982 | 101 [95.7–475] | 66.8 [62.2–75.7] | ×0.662 | 0.388 / 0.257 | 3.33 MB / 3.33 MB | 17.0 / 17.0 | 68 | 0.140 | tak |
| 8 | 2 572 [2 381–2 812] | 2 404 [2 339–2 736] | ×0.935 | 116 [105–172] | 73.1 [72.0–86.4] | ×0.632 | 0.445 / 0.281 | 3.85 MB / 3.85 MB | 25.0 / 25.0 | 100 | 0.165 | tak |

