# Test A/B `ab_e9f_msvc_ca_lava`

- Programy: `e8` = `engine_e8_msvc.exe`, `e9` = `engine_e9_msvc.exe`, `e9f` = `engine_e9f_msvc.exe`
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 0.4 min, 2026-10-18T05:06
- Tło: start 16% CPU (WmiPrvSE.exe 220%, python.exe 42%, svchost.exe 40%), koniec 17%
- Zgodność wyników z `e8`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e8 [ms] | e9 [ms] | e9f [ms] | e9/e8 | e9f/e8 | e9f/e9 | zgodne |
|---|---|---|---|---|---|---|---|---|
| lava_test_3d | caSim | 94.3 [93.4–104] | 97.3 [96.3–146] | 94.3 [93.4–140] | ×1.032 | ×1.001 | ×0.970 | tak |
| lava_test_3d | total | 119 [118–130] | 123 [121–181] | 121 [119–171] | ×1.029 | ×1.010 | ×0.981 | tak |
| lava_test_3d | procWall | 136 [134–154] | 140 [138–204] | 139 [136–191] | ×1.028 | ×1.019 | ×0.991 | tak |
| lava_etna_real | caSim | 85.7 [84.9–88.1] | 88.9 [87.8–103] | 86.2 [84.9–99.0] | ×1.038 | ×1.006 | ×0.969 | tak |
| lava_etna_real | total | 147 [144–181] | 149 [148–170] | 147 [146–159] | ×1.014 | ×1.001 | ×0.987 | tak |
| lava_etna_real | procWall | 170 [163–241] | 168 [167–191] | 170 [166–187] | ×0.989 | ×1.000 | ×1.010 | tak |
| lava_mc_2d_ca | caSim | 6.04 [5.95–7.08] | 6.06 [5.98–6.60] | 6.26 [6.19–6.38] | ×1.004 | ×1.037 | ×1.033 | tak |
| lava_mc_2d_ca | total | 14.2 [13.4–15.9] | 13.9 [13.1–17.7] | 14.1 [13.8–15.1] | ×0.978 | ×0.990 | ×1.013 | tak |
| lava_mc_2d_ca | procWall | 33.7 [28.6–39.3] | 30.8 [29.3–36.7] | 31.6 [30.1–38.2] | ×0.914 | ×0.937 | ×1.025 | tak |
