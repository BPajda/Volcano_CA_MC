# Test A/B `ab_e10_msvc_ca_lava`

- Programy: `e9` = `engine_e9_msvc.exe`, `e10` = `engine_e10_msvc.exe`
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 0.3 min, 2026-10-20T14:09
- Tło: start 21% CPU (WmiPrvSE.exe 208%, python.exe 39%, inny program 36%), koniec 21%
- Zgodność wyników z `e9`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e9 [ms] | e10 [ms] | e10/e9 | zgodne |
|---|---|---|---|---|---|
| lava_test_3d | caSim | 94.7 [93.3–103] | 96.8 [94.6–98.5] | ×1.022 | tak |
| lava_test_3d | total | 120 [119–129] | 122 [120–125] | ×1.010 | tak |
| lava_test_3d | procWall | 139 [137–153] | 141 [138–145] | ×1.014 | tak |
| lava_etna_real | caSim | 86.5 [85.5–95.6] | 88.0 [86.4–90.7] | ×1.017 | tak |
| lava_etna_real | total | 147 [145–173] | 149 [147–152] | ×1.013 | tak |
| lava_etna_real | procWall | 170 [166–193] | 172 [169–175] | ×1.009 | tak |
| lava_mc_2d_ca | caSim | 6.18 [6.12–6.37] | 6.18 [6.10–6.48] | ×0.999 | tak |
| lava_mc_2d_ca | total | 14.3 [13.8–15.8] | 14.5 [13.5–15.0] | ×1.011 | tak |
| lava_mc_2d_ca | procWall | 35.4 [31.3–48.4] | 34.0 [31.0–47.3] | ×0.960 | tak |
