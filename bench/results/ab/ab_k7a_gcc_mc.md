# Test A/B `ab_k7a_gcc_mc`

Próba stabilizacji układu kodu GCC: k7a = kod k7 z -falign-functions=64, tryb oszczędny (bez turbo) — grupa mc bez 100^3

- Programy: `k5` = `engine_k5`, `k7` = `engine_k7`, `k7a` = `engine_k7a`
- Przypięcie: sched_setaffinity({2}) (WSL2: procesor wirtualny); priorytet: domyślny; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 3.1 min, 2026-10-17T23:04
- Zgodność wyników z `k5`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | k5 [ms] | k7 [ms] | k7a [ms] | k7/k5 | k7a/k5 | k7a/k7 | zgodne |
|---|---|---|---|---|---|---|---|---|
| mc_full_2d_200 | mcSim | 121 [117–128] | 120 [118–125] | 120 [119–123] | ×0.994 | ×0.995 | ×1.001 | tak |
| mc_full_2d_200 | mcStats | 16.2 [15.8–16.8] | 15.5 [15.3–15.8] | 15.6 [15.3–16.3] | ×0.960 | ×0.964 | ×1.005 | tak |
| mc_full_2d_200 | total | 141 [138–152] | 138 [136–145] | 139 [137–142] | ×0.977 | ×0.983 | ×1.006 | tak |
| mc_full_2d_200 | procWall | 144 [140–154] | 140 [138–147] | 141 [139–144] | ×0.976 | ×0.983 | ×1.008 | tak |
| mc_full_2d_1000 | mcSim | 8 291 [8 205–9 120] | 8 507 [8 275–8 621] | 8 384 [8 237–8 466] | ×1.026 | ×1.011 | ×0.985 | tak |
| mc_full_2d_1000 | mcStats | 407 [401–409] | 392 [383–394] | 391 [383–396] | ×0.963 | ×0.961 | ×0.999 | tak |
| mc_full_2d_1000 | mcSave | 67.1 [65.3–69.0] | 23.8 [22.9–24.5] | 22.3 [21.6–23.9] | ×0.355 | ×0.333 | ×0.938 | tak |
| mc_full_2d_1000 | total | 8 789 [8 703–9 626] | 8 943 [8 715–9 065] | 8 825 [8 674–8 902] | ×1.018 | ×1.004 | ×0.987 | tak |
| mc_full_2d_1000 | procWall | 8 791 [8 705–9 629] | 8 946 [8 717–9 067] | 8 827 [8 676–8 905] | ×1.018 | ×1.004 | ×0.987 | tak |
| mc_full_3d_50 | mcSim | 1 065 [1 056–1 078] | 1 056 [1 048–1 082] | 1 059 [1 043–1 069] | ×0.992 | ×0.994 | ×1.002 | tak |
| mc_full_3d_50 | mcStats | 239 [236–247] | 231 [229–233] | 236 [235–247] | ×0.968 | ×0.989 | ×1.022 | tak |
| mc_full_3d_50 | total | 1 317 [1 305–1 333] | 1 293 [1 287–1 319] | 1 302 [1 288–1 312] | ×0.982 | ×0.989 | ×1.007 | tak |
| mc_full_3d_50 | procWall | 1 319 [1 307–1 335] | 1 295 [1 290–1 320] | 1 305 [1 290–1 314] | ×0.982 | ×0.989 | ×1.007 | tak |
| lava_mc_3d | mcSim | 40.9 [40.2–41.7] | 41.3 [40.5–43.0] | 41.0 [40.1–41.5] | ×1.012 | ×1.004 | ×0.992 | tak |
| lava_mc_3d | caSim | 57.2 [55.8–60.8] | 70.3 [69.5–72.0] | 56.5 [55.9–60.6] | ×1.228 | ×0.987 | ×0.804 | tak |
| lava_mc_3d | total | 238 [234–242] | 176 [175–181] | 161 [158–165] | ×0.739 | ×0.677 | ×0.916 | tak |
| lava_mc_3d | procWall | 241 [237–244] | 179 [177–183] | 164 [161–168] | ×0.741 | ×0.681 | ×0.918 | tak |

Tło (Windows, poza WSL): start 19% (WmiPrvSE.exe 212%, inny program 88%, python.exe 46%), koniec 17%.
