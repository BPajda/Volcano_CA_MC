# Test A/B `ab_k7_msvc_mc`

Optymalizacja 7 (zapis plików tekstowych wyników), MSVC, taktowanie bazowe — grupa mc (scalona tabela: ab_k7_msvc.md)

- Programy: `k5` = `engine_k5_msvc.exe`, `k7` = `engine_k7_msvc.exe`
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 6.3 min, 2026-10-17T22:44
- Tło: start 20% CPU (WmiPrvSE.exe 222%, inny program 95%, python.exe 43%), koniec 20%
- Zgodność wyników z `k5`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | k5 [ms] | k7 [ms] | k7/k5 | zgodne |
|---|---|---|---|---|---|
| mc_full_2d_200 | mcSim | 132 [129–133] | 131 [130–136] | ×0.999 | tak |
| mc_full_2d_200 | mcStats | 18.2 [17.9–18.7] | 18.5 [18.1–20.2] | ×1.016 | tak |
| mc_full_2d_200 | total | 164 [162–170] | 160 [158–166] | ×0.977 | tak |
| mc_full_2d_200 | procWall | 182 [177–188] | 179 [174–189] | ×0.984 | tak |
| mc_full_2d_1000 | mcSim | 9 376 [9 179–10 695] | 9 564 [9 235–10 214] | ×1.020 | tak |
| mc_full_2d_1000 | mcStats | 429 [427–438] | 438 [427–442] | ×1.019 | tak |
| mc_full_2d_1000 | mcSave | 129 [122–146] | 42.6 [40.6–44.3] | ×0.330 | tak |
| mc_full_2d_1000 | total | 9 989 [9 801–11 291] | 10 088 [9 741–10 737] | ×1.010 | tak |
| mc_full_2d_1000 | procWall | 10 006 [9 817–11 308] | 10 105 [9 757–10 756] | ×1.010 | tak |
| mc_full_3d_50 | mcSim | 1 135 [1 109–1 240] | 1 139 [1 114–1 187] | ×1.003 | tak |
| mc_full_3d_50 | mcStats | 270 [266–294] | 285 [282–293] | ×1.057 | tak |
| mc_full_3d_50 | total | 1 432 [1 404–1 565] | 1 441 [1 413–1 497] | ×1.006 | tak |
| mc_full_3d_50 | procWall | 1 453 [1 423–1 582] | 1 461 [1 432–1 515] | ×1.006 | tak |
| mc_full_3d_100 | mcSim | 22 596 [22 568–24 034] | 22 606 [22 271–22 887] | ×1.000 | tak |
| mc_full_3d_100 | mcStats | 1 037 [1 035–1 046] | 1 098 [1 094–1 111] | ×1.059 | tak |
| mc_full_3d_100 | mcSave | 123 [120–124] | 40.2 [39.5–40.5] | ×0.327 | tak |
| mc_full_3d_100 | total | 23 802 [23 773–25 243] | 23 781 [23 447–24 076] | ×0.999 | tak |
| mc_full_3d_100 | procWall | 23 822 [23 788–25 260] | 23 811 [23 463–24 093] | ×1.000 | tak |
| lava_mc_3d | mcSim | 46.7 [45.2–48.0] | 45.8 [44.8–56.4] | ×0.981 | tak |
| lava_mc_3d | caSim | 61.9 [61.6–63.5] | 62.8 [61.1–65.4] | ×1.014 | tak |
| lava_mc_3d | total | 332 [323–337] | 238 [233–267] | ×0.717 | tak |
| lava_mc_3d | procWall | 351 [341–359] | 264 [251–288] | ×0.752 | tak |
