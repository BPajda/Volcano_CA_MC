# Test A/B `ab_k8_gcc`

Optymalizacja 8 (presety kompilatora): GCC -O3 vs -O3 -march=native (preset gcc-release-native), oba z -falign-functions=64, taktowanie bazowe — kilka przypadków

- Programy: `k7a` = `engine_k7a`, `native` = `engine_native`
- Przypięcie: sched_setaffinity({2}) (WSL2: procesor wirtualny); priorytet: domyślny; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 0.6 min, 2026-10-18T00:20
- Zgodność wyników z `k7a`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | k7a [ms] | native [ms] | native/k7a | zgodne |
|---|---|---|---|---|---|
| lava_test_3d | caSim | 92.5 [91.4–94.5] | 92.8 [92.0–94.4] | ×1.003 | tak |
| lava_test_3d | total | 106 [105–109] | 105 [104–106] | ×0.989 | tak |
| lava_test_3d | procWall | 108 [107–111] | 107 [106–109] | ×0.989 | tak |
| lava_etna_real | caSim | 85.4 [82.8–86.2] | 84.6 [83.6–86.7] | ×0.991 | tak |
| lava_etna_real | total | 145 [138–151] | 145 [138–158] | ×0.999 | tak |
| lava_etna_real | procWall | 149 [142–155] | 149 [142–162] | ×0.998 | tak |
| classic_1000x1000_s100_vn | caSim | 116 [113–120] | 124 [120–145] | ×1.067 | tak |
| classic_1000x1000_s100_vn | save | 47.9 [47.4–67.4] | 47.8 [44.1–75.3] | ×0.999 | tak |
| classic_1000x1000_s100_vn | total | 185 [182–204] | 191 [184–241] | ×1.032 | tak |
| classic_1000x1000_s100_vn | procWall | 200 [197–218] | 206 [199–256] | ×1.031 | tak |
| classic_100x100x100_s10_moore | caSim | 186 [182–230] | 192 [185–202] | ×1.032 | tak |
| classic_100x100x100_s10_moore | total | 259 [249–305] | 254 [248–300] | ×0.982 | tak |
| classic_100x100x100_s10_moore | procWall | 276 [265–321] | 270 [264–323] | ×0.979 | tak |
| mc_full_2d_200 | mcSim | 132 [129–139] | 131 [128–155] | ×0.996 | tak |
| mc_full_2d_200 | mcStats | 17.0 [16.7–19.0] | 16.9 [16.8–17.7] | ×0.999 | tak |
| mc_full_2d_200 | total | 152 [149–161] | 152 [149–176] | ×0.999 | tak |
| mc_full_2d_200 | procWall | 154 [151–163] | 154 [151–178] | ×1.001 | tak |
| mc_full_3d_50 | mcSim | 1 169 [1 120–1 204] | 1 164 [1 119–1 222] | ×0.996 | tak |
| mc_full_3d_50 | mcStats | 261 [254–269] | 269 [263–280] | ×1.030 | tak |
| mc_full_3d_50 | total | 1 446 [1 382–1 470] | 1 452 [1 389–1 500] | ×1.004 | tak |
| mc_full_3d_50 | procWall | 1 448 [1 384–1 472] | 1 455 [1 391–1 503] | ×1.005 | tak |
| lava_mc_3d | mcSim | 44.2 [43.6–45.0] | 44.8 [43.9–46.1] | ×1.015 | tak |
| lava_mc_3d | caSim | 62.3 [60.8–69.5] | 62.8 [61.2–66.6] | ×1.008 | tak |
| lava_mc_3d | total | 179 [175–186] | 177 [173–181] | ×0.992 | tak |
| lava_mc_3d | procWall | 182 [178–189] | 180 [176–184] | ×0.992 | tak |

Tło (Windows, poza WSL): start 13% (WmiPrvSE.exe 225%, python.exe 42%, svchost.exe 37%), koniec 9%.
