# Test A/B `ab_e11_msvc`

- Programy: `e10` = `engine_e10_msvc.exe`, `e11` = `engine_e11_msvc.exe`
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 4.4 min, 2026-10-21T05:47
- Tło: start 30% CPU (inny program 289%, WmiPrvSE.exe 230%, System 53%), koniec 31%
- Zgodność wyników z `e10`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e10 [ms] | e11 [ms] | e11/e10 | zgodne |
|---|---|---|---|---|---|
| lava_test_3d | caSim | 96.7 [95.0–104] | 97.1 [95.0–99.5] | ×1.004 | tak |
| lava_test_3d | total | 124 [121–136] | 124 [123–129] | ×1.006 | tak |
| lava_test_3d | procWall | 148 [141–159] | 148 [142–154] | ×1.000 | tak |
| lava_etna_real | caSim | 88.1 [86.5–92.3] | 88.7 [86.6–90.7] | ×1.006 | tak |
| lava_etna_real | total | 150 [148–179] | 152 [148–156] | ×1.014 | tak |
| lava_etna_real | procWall | 176 [174–203] | 179 [169–184] | ×1.016 | tak |
| lava_mc_2d_ca | caSim | 6.35 [6.21–7.32] | 6.29 [6.24–6.64] | ×0.992 | tak |
| lava_mc_2d_ca | total | 15.6 [14.4–28.2] | 15.5 [13.7–16.2] | ×0.992 | tak |
| lava_mc_2d_ca | procWall | 38.3 [33.5–57.3] | 38.5 [33.4–47.9] | ×1.004 | tak |
| classic_1000x1000_s100_vn | caSim | 122 [119–128] | 123 [119–144] | ×1.010 | tak |
| classic_1000x1000_s100_vn | save | 82.4 [81.8–85.6] | 90.4 [87.8–107] | ×1.098 | tak |
| classic_1000x1000_s100_vn | total | 227 [221–234] | 232 [228–283] | ×1.022 | tak |
| classic_1000x1000_s100_vn | procWall | 258 [253–270] | 267 [259–329] | ×1.035 | tak |
| mc_full_2d_1000 | mcSim | 12 665 [11 443–12 913] | 12 584 [12 016–12 840] | ×0.994 | tak |
| mc_full_2d_1000 | mcStats | 446 [433–454] | 452 [438–459] | ×1.012 | tak |
| mc_full_2d_1000 | mcSave | 43.7 [41.4–47.5] | 43.3 [41.6–53.5] | ×0.990 | tak |
| mc_full_2d_1000 | total | 13 193 [11 977–13 443] | 13 132 [12 538–13 387] | ×0.995 | tak |
| mc_full_2d_1000 | procWall | 13 231 [12 021–13 465] | 13 157 [12 559–13 413] | ×0.994 | tak |
| lava_mc_3d | mcSim | 46.7 [45.9–67.4] | 47.2 [46.3–48.2] | ×1.011 | tak |
| lava_mc_3d | caSim | 64.7 [63.9–67.0] | 64.8 [63.8–69.1] | ×1.002 | tak |
| lava_mc_3d | total | 243 [240–309] | 248 [244–256] | ×1.020 | tak |
| lava_mc_3d | procWall | 269 [263–336] | 275 [264–284] | ×1.021 | tak |
