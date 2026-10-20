# Test A/B `ab_e9b_t1_msvc_ca_lava_r15`

- Programy: `e8` = `engine_e8_msvc.exe`, `e9b` = `engine_e9b_msvc.exe`
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 0.3 min, 2026-10-18T03:52
- Tło: start 26% CPU (WmiPrvSE.exe 234%, inny program 83%, Code.exe 61%), koniec 26%
- Zgodność wyników z `e8`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e8 [ms] | e9b [ms] | e9b/e8 | zgodne |
|---|---|---|---|---|---|
| lava_test_3d | caSim | 95.6 [93.5–98.8] | 98.3 [96.7–106] | ×1.028 | tak |
| lava_test_3d | total | 121 [119–127] | 124 [122–133] | ×1.024 | tak |
| lava_test_3d | procWall | 138 [135–148] | 142 [140–163] | ×1.030 | tak |
| lava_etna_real | caSim | 86.7 [85.5–125] | 92.0 [89.6–105] | ×1.062 | tak |
| lava_etna_real | total | 148 [146–209] | 157 [154–177] | ×1.064 | tak |
| lava_etna_real | procWall | 170 [167–237] | 180 [174–208] | ×1.055 | tak |
| lava_mc_2d_ca | caSim | 6.39 [5.93–7.41] | 6.28 [6.17–6.92] | ×0.983 | tak |
| lava_mc_2d_ca | total | 14.5 [13.6–17.3] | 14.6 [13.7–15.3] | ×1.008 | tak |
| lava_mc_2d_ca | procWall | 32.8 [29.4–41.9] | 34.1 [30.1–43.6] | ×1.037 | tak |
