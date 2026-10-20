# Test A/B `ab_e9c_t1_msvc_lava`

- Programy: `e8` = `engine_e8_msvc.exe`, `e9b` = `engine_e9b_msvc.exe`, `e9c` = `engine_e9c_msvc.exe`
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 0.4 min, 2026-10-18T03:54
- Tło: start 23% CPU (WmiPrvSE.exe 223%, inny program 76%, python.exe 45%), koniec 32%
- Zgodność wyników z `e8`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e8 [ms] | e9b [ms] | e9c [ms] | e9b/e8 | e9c/e8 | e9c/e9b | zgodne |
|---|---|---|---|---|---|---|---|---|
| lava_test_3d | caSim | 95.7 [92.9–111] | 98.9 [97.3–125] | 99.1 [96.3–104] | ×1.033 | ×1.035 | ×1.002 | tak |
| lava_test_3d | total | 121 [118–150] | 125 [122–155] | 125 [122–131] | ×1.030 | ×1.029 | ×0.999 | tak |
| lava_test_3d | procWall | 142 [134–171] | 143 [139–177] | 145 [140–152] | ×1.012 | ×1.023 | ×1.011 | tak |
| lava_etna_real | caSim | 87.7 [85.6–93.3] | 91.4 [89.6–101] | 92.1 [89.6–99.5] | ×1.043 | ×1.051 | ×1.008 | tak |
| lava_etna_real | total | 150 [147–172] | 158 [155–173] | 159 [154–168] | ×1.050 | ×1.056 | ×1.006 | tak |
| lava_etna_real | procWall | 174 [166–196] | 181 [175–195] | 182 [175–204] | ×1.037 | ×1.046 | ×1.009 | tak |
