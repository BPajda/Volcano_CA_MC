# Test A/B `ab_e9b_t1_gcc_ca_lava`

- Programy: `e8` = `engine_e8`, `e9b` = `engine_e9b`
- Przypięcie: sched_setaffinity({2}) (WSL2: procesor wirtualny); priorytet: domyślny; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 0.1 min, 2026-10-18T03:56
- Zgodność wyników z `e8`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e8 [ms] | e9b [ms] | e9b/e8 | zgodne |
|---|---|---|---|---|---|
| lava_test_3d | caSim | 95.6 [94.1–118] | 97.6 [94.9–149] | ×1.021 | tak |
| lava_test_3d | total | 109 [107–133] | 110 [108–169] | ×1.016 | tak |
| lava_test_3d | procWall | 112 [110–138] | 113 [111–173] | ×1.015 | tak |
| lava_etna_real | caSim | 87.6 [84.8–93.5] | 88.4 [86.5–92.0] | ×1.009 | tak |
| lava_etna_real | total | 138 [133–168] | 140 [135–149] | ×1.017 | tak |
| lava_etna_real | procWall | 143 [137–175] | 145 [140–154] | ×1.018 | tak |
| lava_mc_2d_ca | caSim | 6.13 [5.92–9.35] | 6.40 [6.18–8.56] | ×1.043 | tak |
| lava_mc_2d_ca | total | 8.61 [8.20–12.9] | 8.77 [8.51–10.8] | ×1.018 | tak |
| lava_mc_2d_ca | procWall | 10.9 [10.4–15.5] | 11.4 [10.8–14.6] | ×1.045 | tak |

Tło (Windows, poza WSL): start 24% (WmiPrvSE.exe 230%, inny program 105%, inny program 87%), koniec 31%.
