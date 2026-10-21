# Typy MPI i MPI-IO `pomiar_msvc_cz2`

- Program: `engine_mpi_e11_msvc.exe` (MS-MPI `mpiexec -n p`); `--high-priority`, `parallel.affinity = pcores`; warianty naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max]
- Czas pomiaru: 3.4 min, 2026-10-21T10:14
- Tło: start 12% CPU (WmiPrvSE.exe 199%, System 49%, svchost.exe 45%), koniec 13%
- Zgodność wyników w przypadku: wszystkie przebiegi bitowo zgodne

### `pack_classic_300` — wymiana warstw: pakowanie (m) vs typy pochodne (d)

| p | faza m [ms] | faza d [ms] | d/m faza | wymiana m [ms] | wymiana d [ms] | d/m wymiana | na wymianę m / d [ms] | B / wymianę m / d | komunikaty / wymianę | typy (suma) | budowa typów [ms] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 1 919 [1 903–1 962] | 1 866 [1 846–1 917] | ×0.973 | 67.0 [66.4–71.4] | 35.1 [34.5–38.4] | ×0.524 | 0.587 / 0.308 | 2.55 MB / 2.55 MB | 2.0 / 2.0 | 4 | 0.049 | tak |
| 4 | 1 148 [1 143–1 174] | 1 105 [1 098–1 135] | ×0.962 | 75.1 [73.9–76.3] | 39.6 [39.1–40.7] | ×0.527 | 0.659 / 0.348 | 5.11 MB / 5.11 MB | 8.0 / 8.0 | 16 | 0.088 | tak |
| 7 | 879 [878–897] | 816 [801–833] | ×0.929 | 97.6 [94.9–98.3] | 48.4 [47.1–49.5] | ×0.496 | 0.856 / 0.425 | 8.94 MB / 8.94 MB | 14.0 / 14.0 | 28 | 0.086 | tak |
| 8 | 867 [845–877] | 789 [768–801] | ×0.910 | 107 [102–113] | 53.6 [50.7–53.9] | ×0.503 | 0.935 / 0.470 | 10.21 MB / 10.21 MB | 16.0 / 16.0 | 32 | 0.089 | tak |

### `pack_mc_cb_3d_100` — wymiana warstw: pakowanie (m) vs typy pochodne (d)

| p | faza m [ms] | faza d [ms] | d/m faza | wymiana m [ms] | wymiana d [ms] | d/m wymiana | na wymianę m / d [ms] | B / wymianę m / d | komunikaty / wymianę | typy (suma) | budowa typów [ms] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 2 894 [2 892–2 995] | 2 888 [2 879–2 991] | ×0.998 | 40.0 [39.2–91.5] | 34.4 [30.6–89.2] | ×0.859 | 0.050 / 0.043 | 0.17 MB / 0.17 MB | 2.0 / 2.0 | 4 | 0.029 | tak |
| 4 | 1 529 [1 512–1 579] | 1 497 [1 493–1 571] | ×0.979 | 97.7 [88.8–139] | 81.9 [77.3–135] | ×0.839 | 0.122 / 0.102 | 0.33 MB / 0.33 MB | 8.0 / 8.0 | 16 | 0.064 | tak |
| 7 | 951 [940–958] | 934 [924–946] | ×0.982 | 136 [124–140] | 121 [115–130] | ×0.892 | 0.170 / 0.151 | 0.58 MB / 0.58 MB | 14.0 / 14.0 | 28 | 0.063 | tak |
| 8 | 868 [834–880] | 871 [830–1 642] | ×1.003 | 148 [122–159] | 154 [119–935] | ×1.036 | 0.185 / 0.192 | 0.67 MB / 0.67 MB | 16.0 / 16.0 | 32 | 0.062 | tak |

### `bcast_etna_real` — rozsyłanie: JSON (m) vs struktury (s)

| wariant | MPI_Bcast configu [ms] | config [B] | przygotowanie (proces 0) [ms] | budowa Config (maks.) [ms] | kratery [ms] | kratery [B] | razem [ms] | zgodne |
|---|---|---|---|---|---|---|---|---|
| m3 | 0.53 [0.44–0.62] | 980 | 0.03 [0.03–0.03] | 0.27 [0.26–0.28] | 0.00 [0.00–0.00] | 0 | 0.81 | tak |
| m3s | 0.50 [0.44–0.56] | 219 | 0.02 [0.01–0.02] | 0.04 [0.04–0.06] | 0.03 [0.03–0.03] | 56 | 0.59 | tak |
| m8 | 0.68 [0.64–0.69] | 980 | 0.03 [0.03–0.03] | 0.41 [0.39–0.60] | 0.00 [0.00–0.00] | 0 | 1.10 | tak |
| m8s | 0.63 [0.59–0.96] | 219 | 0.02 [0.01–0.02] | 0.06 [0.05–0.16] | 0.02 [0.02–0.02] | 56 | 0.73 | tak |

### `bcast_classic_2000` — rozsyłanie: JSON (m) vs struktury (s)

| wariant | MPI_Bcast configu [ms] | config [B] | przygotowanie (proces 0) [ms] | budowa Config (maks.) [ms] | kratery [ms] | kratery [B] | razem [ms] | zgodne |
|---|---|---|---|---|---|---|---|---|
| m3 | 0.46 [0.45–0.78] | 881 | 0.03 [0.02–0.03] | 0.26 [0.25–0.36] | 0.00 [0.00–0.00] | 0 | 0.84 | tak |
| m3s | 0.50 [0.48–0.55] | 219 | 0.02 [0.01–0.02] | 0.04 [0.04–0.08] | 0.09 [0.09–0.10] | 6408 | 0.67 | tak |
| m8 | 0.66 [0.57–0.68] | 881 | 0.03 [0.03–0.03] | 0.36 [0.30–0.40] | 0.00 [0.00–0.00] | 0 | 1.00 | tak |
| m8s | 0.63 [0.58–0.65] | 219 | 0.01 [0.01–0.02] | 0.07 [0.06–0.08] | 0.10 [0.09–0.11] | 6408 | 0.80 | tak |

