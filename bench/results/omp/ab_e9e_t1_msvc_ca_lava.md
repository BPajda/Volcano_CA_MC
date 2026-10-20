# Test A/B `ab_e9e_t1_msvc_ca_lava`

- Programy: `e8` = `engine_e8_msvc.exe`, `e9e` = `engine_e9e_msvc.exe`
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 0.3 min, 2026-10-18T04:02
- Tło: start 35% CPU (WmiPrvSE.exe 218%, inny program 100%, inny program 94%), koniec 31%
- Zgodność wyników z `e8`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e8 [ms] | e9e [ms] | e9e/e8 | zgodne |
|---|---|---|---|---|---|
| lava_test_3d | caSim | 93.1 [92.3–95.3] | 96.9 [96.3–97.3] | ×1.040 | tak |
| lava_test_3d | total | 119 [117–120] | 122 [121–124] | ×1.031 | tak |
| lava_test_3d | procWall | 136 [134–148] | 142 [139–151] | ×1.039 | tak |
| lava_etna_real | caSim | 85.3 [84.5–86.2] | 88.4 [87.7–89.7] | ×1.037 | tak |
| lava_etna_real | total | 147 [144–178] | 149 [148–151] | ×1.020 | tak |
| lava_etna_real | procWall | 168 [165–200] | 171 [169–181] | ×1.018 | tak |
| lava_mc_2d_ca | caSim | 6.03 [5.90–6.67] | 6.11 [6.02–7.35] | ×1.013 | tak |
| lava_mc_2d_ca | total | 13.8 [12.7–16.6] | 14.3 [13.7–16.4] | ×1.038 | tak |
| lava_mc_2d_ca | procWall | 32.2 [28.6–38.4] | 32.9 [30.4–41.9] | ×1.023 | tak |
