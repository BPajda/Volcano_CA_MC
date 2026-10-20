# Test A/B `ab_e9_msvc_mc_reszta`

- Programy: `e8` = `engine_e8_msvc.exe`, `e9` = `engine_e9_msvc.exe`
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 2.3 min, 2026-10-18T05:18
- Tło: start 19% CPU (WmiPrvSE.exe 218%, inny program 84%, python.exe 45%), koniec 21%
- Zgodność wyników z `e8`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e8 [ms] | e9 [ms] | e9/e8 | zgodne |
|---|---|---|---|---|---|
| mc_full_2d_200 | mcSim | 134 [131–144] | 133 [130–147] | ×0.996 | tak |
| mc_full_2d_200 | mcStats | 18.9 [18.4–20.2] | 18.9 [18.4–20.1] | ×1.002 | tak |
| mc_full_2d_200 | total | 163 [160–175] | 165 [159–178] | ×1.010 | tak |
| mc_full_2d_200 | procWall | 181 [176–199] | 182 [176–195] | ×1.009 | tak |
| mc_full_2d_1000 | mcSim | 9 897 [9 720–10 634] | 9 954 [9 791–10 213] | ×1.006 | tak |
| mc_full_2d_1000 | mcStats | 431 [428–435] | 433 [428–439] | ×1.005 | tak |
| mc_full_2d_1000 | mcSave | 41.1 [39.6–41.4] | 42.5 [41.8–42.8] | ×1.032 | tak |
| mc_full_2d_1000 | total | 10 413 [10 232–11 156] | 10 476 [10 302–10 727] | ×1.006 | tak |
| mc_full_2d_1000 | procWall | 10 430 [10 249–11 172] | 10 499 [10 319–10 745] | ×1.007 | tak |
| mc_full_3d_50 | mcSim | 1 170 [1 117–1 217] | 1 164 [1 133–1 219] | ×0.995 | tak |
| mc_full_3d_50 | mcStats | 287 [283–292] | 287 [285–288] | ×1.002 | tak |
| mc_full_3d_50 | total | 1 485 [1 418–1 527] | 1 469 [1 435–1 524] | ×0.989 | tak |
| mc_full_3d_50 | procWall | 1 506 [1 434–1 551] | 1 487 [1 459–1 542] | ×0.987 | tak |
| lava_mc_3d | mcSim | 46.2 [45.3–47.6] | 46.6 [45.3–51.2] | ×1.009 | tak |
| lava_mc_3d | caSim | 63.2 [62.5–64.4] | 65.3 [63.7–67.9] | ×1.034 | tak |
| lava_mc_3d | total | 241 [237–255] | 243 [239–261] | ×1.008 | tak |
| lava_mc_3d | procWall | 258 [254–283] | 263 [258–280] | ×1.019 | tak |
