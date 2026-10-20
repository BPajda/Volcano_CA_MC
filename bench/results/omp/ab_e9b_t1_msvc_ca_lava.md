# Test A/B `ab_e9b_t1_msvc_ca_lava`

- Programy: `e8` = `engine_e8_msvc.exe`, `e9a` = `engine_e9a_msvc.exe`, `e9b` = `engine_e9b_msvc.exe`
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 0.2 min, 2026-10-18T03:52
- Tło: start 24% CPU (WmiPrvSE.exe 233%, inny program 100%, inny program 95%), koniec 19%
- Zgodność wyników z `e8`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e8 [ms] | e9a [ms] | e9b [ms] | e9a/e8 | e9b/e8 | e9b/e9a | zgodne |
|---|---|---|---|---|---|---|---|---|
| lava_test_3d | caSim | 97.5 [93.7–108] | 103 [97.5–114] | 98.0 [96.9–114] | ×1.055 | ×1.005 | ×0.953 | tak |
| lava_test_3d | total | 124 [120–139] | 129 [124–142] | 124 [123–140] | ×1.042 | ×0.999 | ×0.959 | tak |
| lava_test_3d | procWall | 142 [136–156] | 147 [141–161] | 142 [140–173] | ×1.037 | ×1.000 | ×0.964 | tak |
| lava_etna_real | caSim | 94.3 [86.0–96.3] | 90.6 [89.6–92.6] | 94.0 [89.2–100.0] | ×0.961 | ×0.997 | ×1.037 | tak |
| lava_etna_real | total | 160 [146–184] | 155 [154–161] | 160 [154–167] | ×0.971 | ×0.998 | ×1.028 | tak |
| lava_etna_real | procWall | 181 [172–206] | 180 [174–198] | 185 [176–193] | ×0.997 | ×1.022 | ×1.025 | tak |
| lava_mc_2d_ca | caSim | 6.14 [5.97–6.66] | 6.39 [6.31–6.91] | 6.52 [6.26–8.63] | ×1.040 | ×1.061 | ×1.020 | tak |
| lava_mc_2d_ca | total | 14.2 [12.9–15.5] | 14.4 [14.1–16.2] | 15.1 [13.5–18.6] | ×1.017 | ×1.062 | ×1.044 | tak |
| lava_mc_2d_ca | procWall | 34.4 [29.4–43.6] | 32.3 [30.7–35.5] | 34.0 [30.1–49.2] | ×0.941 | ×0.989 | ×1.051 | tak |
