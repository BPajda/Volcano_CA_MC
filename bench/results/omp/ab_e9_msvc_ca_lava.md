# Test A/B `ab_e9_msvc_ca_lava`

- Programy: `e8` = `engine_e8_msvc.exe`, `e9` = `engine_e9_msvc.exe`
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 0.3 min, 2026-10-18T05:14
- Tło: start 19% CPU (WmiPrvSE.exe 221%, inny program 71%, python.exe 45%), koniec 24%
- Zgodność wyników z `e8`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e8 [ms] | e9 [ms] | e9/e8 | zgodne |
|---|---|---|---|---|---|
| lava_test_3d | caSim | 96.4 [94.6–103] | 96.2 [95.1–99.7] | ×0.997 | tak |
| lava_test_3d | total | 122 [120–130] | 122 [121–126] | ×1.004 | tak |
| lava_test_3d | procWall | 140 [137–149] | 140 [138–143] | ×1.002 | tak |
| lava_etna_real | caSim | 88.1 [86.8–106] | 88.3 [87.3–94.7] | ×1.002 | tak |
| lava_etna_real | total | 150 [147–179] | 150 [148–155] | ×1.000 | tak |
| lava_etna_real | procWall | 172 [169–202] | 172 [169–185] | ×1.004 | tak |
| lava_mc_2d_ca | caSim | 6.10 [6.05–6.73] | 6.44 [6.20–6.64] | ×1.055 | tak |
| lava_mc_2d_ca | total | 14.6 [13.9–16.1] | 14.8 [13.4–19.1] | ×1.011 | tak |
| lava_mc_2d_ca | procWall | 34.0 [29.7–37.0] | 35.2 [30.9–51.6] | ×1.036 | tak |
