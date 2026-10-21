# Test A/B `ab_e11_msvc`

- Programy: `e10` = `engine_e10_msvc.exe`, `e11` = `engine_e11_msvc.exe`
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 4.3 min, 2026-10-21T06:04
- Tło: start 32% CPU (inny program 261%, WmiPrvSE.exe 235%, python.exe 46%), koniec 26%
- Zgodność wyników z `e10`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e10 [ms] | e11 [ms] | e11/e10 | zgodne |
|---|---|---|---|---|---|
| lava_test_3d | caSim | 96.9 [95.5–109] | 96.7 [95.1–109] | ×0.998 | tak |
| lava_test_3d | total | 123 [121–138] | 123 [121–142] | ×0.997 | tak |
| lava_test_3d | procWall | 146 [142–163] | 146 [141–168] | ×0.997 | tak |
| lava_etna_real | caSim | 88.3 [86.9–92.0] | 87.9 [86.4–89.9] | ×0.995 | tak |
| lava_etna_real | total | 150 [147–183] | 150 [148–154] | ×0.998 | tak |
| lava_etna_real | procWall | 180 [173–209] | 176 [171–188] | ×0.977 | tak |
| lava_mc_2d_ca | caSim | 6.30 [6.17–6.63] | 6.28 [6.14–7.28] | ×0.997 | tak |
| lava_mc_2d_ca | total | 15.3 [14.7–27.5] | 14.9 [13.8–16.8] | ×0.968 | tak |
| lava_mc_2d_ca | procWall | 39.3 [33.5–53.7] | 37.9 [32.2–45.3] | ×0.964 | tak |
| classic_1000x1000_s100_vn | caSim | 123 [118–129] | 122 [118–134] | ×0.991 | tak |
| classic_1000x1000_s100_vn | save | 82.6 [80.5–86.9] | 82.6 [82.0–84.8] | ×1.000 | tak |
| classic_1000x1000_s100_vn | total | 226 [218–238] | 225 [221–245] | ×0.993 | tak |
| classic_1000x1000_s100_vn | procWall | 256 [250–272] | 256 [249–282] | ×1.000 | tak |
| mc_full_2d_1000 | mcSim | 12 138 [11 787–12 597] | 12 063 [11 285–12 996] | ×0.994 | tak |
| mc_full_2d_1000 | mcStats | 439 [429–449] | 438 [430–446] | ×0.998 | tak |
| mc_full_2d_1000 | mcSave | 43.8 [41.0–45.5] | 44.5 [43.9–48.1] | ×1.015 | tak |
| mc_full_2d_1000 | total | 12 668 [12 312–13 131] | 12 589 [11 803–13 524] | ×0.994 | tak |
| mc_full_2d_1000 | procWall | 12 701 [12 331–13 156] | 12 613 [11 827–13 546] | ×0.993 | tak |
| lava_mc_3d | mcSim | 47.4 [46.0–48.3] | 48.0 [47.3–49.7] | ×1.013 | tak |
| lava_mc_3d | caSim | 65.0 [63.6–67.8] | 65.6 [63.8–67.9] | ×1.009 | tak |
| lava_mc_3d | total | 244 [239–253] | 247 [243–253] | ×1.010 | tak |
| lava_mc_3d | procWall | 272 [263–274] | 273 [266–284] | ×1.005 | tak |
