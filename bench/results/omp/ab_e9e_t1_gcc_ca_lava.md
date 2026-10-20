# Test A/B `ab_e9e_t1_gcc_ca_lava`

- Programy: `e8` = `engine_e8`, `e9b` = `engine_e9b`, `e9e` = `engine_e9e`
- Przypięcie: sched_setaffinity({2}) (WSL2: procesor wirtualny); priorytet: domyślny; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 0.2 min, 2026-10-18T04:04
- Zgodność wyników z `e8`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e8 [ms] | e9b [ms] | e9e [ms] | e9b/e8 | e9e/e8 | e9e/e9b | zgodne |
|---|---|---|---|---|---|---|---|---|
| lava_test_3d | caSim | 95.4 [92.4–97.9] | 96.8 [94.3–109] | 97.8 [95.4–105] | ×1.015 | ×1.026 | ×1.010 | tak |
| lava_test_3d | total | 110 [106–112] | 110 [107–123] | 111 [109–118] | ×1.005 | ×1.009 | ×1.004 | tak |
| lava_test_3d | procWall | 113 [108–115] | 113 [110–126] | 114 [112–121] | ×1.006 | ×1.012 | ×1.007 | tak |
| lava_etna_real | caSim | 87.8 [84.7–106] | 88.6 [85.6–107] | 90.2 [86.7–93.6] | ×1.009 | ×1.027 | ×1.018 | tak |
| lava_etna_real | total | 139 [135–167] | 138 [135–184] | 141 [137–157] | ×0.991 | ×1.011 | ×1.021 | tak |
| lava_etna_real | procWall | 145 [140–171] | 143 [140–191] | 145 [142–162] | ×0.988 | ×1.006 | ×1.018 | tak |
| lava_mc_2d_ca | caSim | 6.19 [5.96–6.54] | 6.45 [6.24–8.05] | 6.19 [5.96–15.7] | ×1.042 | ×0.999 | ×0.959 | tak |
| lava_mc_2d_ca | total | 8.54 [8.12–9.06] | 8.85 [8.55–10.6] | 8.62 [8.34–18.1] | ×1.036 | ×1.009 | ×0.974 | tak |
| lava_mc_2d_ca | procWall | 10.9 [10.2–11.3] | 11.2 [10.8–12.9] | 11.2 [10.7–20.4] | ×1.031 | ×1.025 | ×0.994 | tak |

Tło (Windows, poza WSL): start 33% (WmiPrvSE.exe 229%, inny program 99%, System 87%), koniec 31%.
