# Test A/B `ab_e11_gcc`

- Programy: `e10` = `engine_e10`, `e11` = `engine_e11`
- Przypięcie: sched_setaffinity({2}) (WSL2: procesor wirtualny); priorytet: domyślny; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 4.1 min, 2026-10-21T06:09
- Zgodność wyników z `e10`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e10 [ms] | e11 [ms] | e11/e10 | zgodne |
|---|---|---|---|---|---|
| lava_test_3d | caSim | 92.8 [88.5–102] | 93.1 [87.6–106] | ×1.003 | tak |
| lava_test_3d | total | 107 [101–115] | 106 [99.1–119] | ×0.993 | tak |
| lava_test_3d | procWall | 109 [104–118] | 109 [102–122] | ×0.999 | tak |
| lava_etna_real | caSim | 83.7 [81.5–98.1] | 86.1 [82.5–92.4] | ×1.028 | tak |
| lava_etna_real | total | 140 [132–164] | 138 [132–166] | ×0.987 | tak |
| lava_etna_real | procWall | 144 [136–169] | 142 [136–171] | ×0.988 | tak |
| lava_mc_2d_ca | caSim | 6.12 [5.62–7.27] | 5.99 [5.74–7.75] | ×0.980 | tak |
| lava_mc_2d_ca | total | 8.53 [7.71–9.61] | 8.52 [7.84–10.5] | ×1.000 | tak |
| lava_mc_2d_ca | procWall | 10.9 [9.89–12.1] | 11.1 [9.89–13.1] | ×1.017 | tak |
| classic_1000x1000_s100_vn | caSim | 121 [114–141] | 113 [109–134] | ×0.932 | tak |
| classic_1000x1000_s100_vn | save | 50.7 [46.2–61.3] | 50.6 [44.4–60.0] | ×0.998 | tak |
| classic_1000x1000_s100_vn | total | 190 [182–217] | 188 [174–206] | ×0.990 | tak |
| classic_1000x1000_s100_vn | procWall | 205 [197–234] | 202 [188–222] | ×0.982 | tak |
| mc_full_2d_1000 | mcSim | 11 421 [11 233–12 702] | 11 719 [11 318–13 294] | ×1.026 | tak |
| mc_full_2d_1000 | mcStats | 405 [393–453] | 418 [401–475] | ×1.031 | tak |
| mc_full_2d_1000 | mcSave | 23.4 [21.1–28.5] | 23.9 [21.5–27.3] | ×1.024 | tak |
| mc_full_2d_1000 | total | 11 874 [11 689–13 202] | 12 180 [11 780–13 826] | ×1.026 | tak |
| mc_full_2d_1000 | procWall | 11 877 [11 692–13 205] | 12 183 [11 783–13 829] | ×1.026 | tak |
| lava_mc_3d | mcSim | 43.5 [42.2–49.0] | 44.0 [42.6–47.9] | ×1.012 | tak |
| lava_mc_3d | caSim | 61.4 [58.4–69.3] | 60.7 [59.0–71.0] | ×0.988 | tak |
| lava_mc_3d | total | 170 [164–189] | 171 [163–198] | ×1.003 | tak |
| lava_mc_3d | procWall | 173 [167–192] | 173 [166–201] | ×0.999 | tak |

Tło (Windows, poza WSL): start 34% (inny program 271%, WmiPrvSE.exe 209%, python.exe 63%), koniec 30%.
