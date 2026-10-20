# Test A/B `ab_e9e2_msvc_ca_lava` (program e9e + caStats — przed wyborem wariantu e9f)

- Programy: `e8` = `engine_e8_msvc.exe`, `e9` = `engine_e9_msvc.exe`
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 0.3 min, 2026-10-18T05:04
- Tło: start 16% CPU (WmiPrvSE.exe 216%, python.exe 44%, svchost.exe 32%), koniec 14%
- Zgodność wyników z `e8`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e8 [ms] | e9 [ms] | e9/e8 | zgodne |
|---|---|---|---|---|---|
| lava_test_3d | caSim | 92.9 [92.6–93.7] | 96.6 [96.1–102] | ×1.039 | tak |
| lava_test_3d | total | 118 [116–131] | 122 [120–130] | ×1.033 | tak |
| lava_test_3d | procWall | 134 [133–149] | 139 [138–148] | ×1.038 | tak |
| lava_etna_real | caSim | 85.4 [84.6–87.4] | 88.5 [87.6–90.9] | ×1.037 | tak |
| lava_etna_real | total | 146 [143–175] | 148 [147–152] | ×1.018 | tak |
| lava_etna_real | procWall | 166 [162–197] | 171 [167–174] | ×1.028 | tak |
| lava_mc_2d_ca | caSim | 6.00 [5.91–7.64] | 6.01 [5.96–6.06] | ×1.002 | tak |
| lava_mc_2d_ca | total | 14.1 [13.3–24.1] | 13.7 [13.3–16.9] | ×0.974 | tak |
| lava_mc_2d_ca | procWall | 32.8 [28.6–45.1] | 31.4 [29.1–39.7] | ×0.956 | tak |
