# Test A/B `ab_e10_gcc_ca_lava`

- Programy: `e9` = `engine_e9`, `e10` = `engine_e10`
- Przypięcie: sched_setaffinity({2}) (WSL2: procesor wirtualny); priorytet: domyślny; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 0.1 min, 2026-10-20T14:14
- Zgodność wyników z `e9`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e9 [ms] | e10 [ms] | e10/e9 | zgodne |
|---|---|---|---|---|---|
| lava_test_3d | caSim | 94.8 [94.2–97.8] | 94.3 [92.7–97.0] | ×0.995 | tak |
| lava_test_3d | total | 107 [106–111] | 106 [105–109] | ×0.997 | tak |
| lava_test_3d | procWall | 109 [109–115] | 109 [107–112] | ×0.997 | tak |
| lava_etna_real | caSim | 86.4 [85.0–88.5] | 85.4 [83.9–88.8] | ×0.989 | tak |
| lava_etna_real | total | 134 [130–159] | 133 [130–165] | ×0.993 | tak |
| lava_etna_real | procWall | 138 [135–163] | 137 [134–169] | ×0.994 | tak |
| lava_mc_2d_ca | caSim | 6.10 [5.94–6.70] | 6.01 [5.95–6.19] | ×0.985 | tak |
| lava_mc_2d_ca | total | 8.35 [8.04–8.94] | 8.17 [8.02–8.37] | ×0.979 | tak |
| lava_mc_2d_ca | procWall | 10.5 [10.2–11.2] | 10.4 [10.2–10.7] | ×0.993 | tak |

Tło (Windows, poza WSL): start 21% (WmiPrvSE.exe 202%, inny program 65%, svchost.exe 43%), koniec 19%.
