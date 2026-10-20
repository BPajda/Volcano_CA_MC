# Test A/B `ab_e9g_msvc_ca_lava`

- Programy: `e8` = `engine_e8_msvc.exe`, `e9f` = `engine_e9f_msvc.exe`, `e9g` = `engine_e9g_msvc.exe`
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 0.4 min, 2026-10-18T05:08
- Tło: start 15% CPU (WmiPrvSE.exe 148%, python.exe 44%, inny program 31%), koniec 21%
- Zgodność wyników z `e8`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e8 [ms] | e9f [ms] | e9g [ms] | e9f/e8 | e9g/e8 | e9g/e9f | zgodne |
|---|---|---|---|---|---|---|---|---|
| lava_test_3d | caSim | 93.3 [92.7–94.3] | 94.1 [92.6–98.3] | 96.6 [95.7–103] | ×1.009 | ×1.035 | ×1.026 | tak |
| lava_test_3d | total | 119 [118–119] | 119 [118–124] | 122 [120–128] | ×1.007 | ×1.025 | ×1.018 | tak |
| lava_test_3d | procWall | 135 [133–139] | 137 [135–142] | 139 [137–146] | ×1.019 | ×1.032 | ×1.013 | tak |
| lava_etna_real | caSim | 85.9 [84.7–126] | 86.2 [84.9–135] | 87.9 [87.1–106] | ×1.004 | ×1.023 | ×1.020 | tak |
| lava_etna_real | total | 146 [144–204] | 147 [144–217] | 148 [147–175] | ×1.003 | ×1.014 | ×1.011 | tak |
| lava_etna_real | procWall | 166 [163–226] | 166 [164–246] | 171 [166–198] | ×0.998 | ×1.028 | ×1.029 | tak |
| lava_mc_2d_ca | caSim | 6.01 [5.90–6.16] | 6.23 [6.13–6.26] | 6.12 [5.99–6.25] | ×1.036 | ×1.018 | ×0.983 | tak |
| lava_mc_2d_ca | total | 14.1 [13.3–16.0] | 13.9 [13.4–15.1] | 14.4 [13.6–15.4] | ×0.984 | ×1.021 | ×1.038 | tak |
| lava_mc_2d_ca | procWall | 32.1 [28.4–36.7] | 30.3 [29.4–36.3] | 31.4 [29.9–42.5] | ×0.946 | ×0.980 | ×1.036 | tak |
