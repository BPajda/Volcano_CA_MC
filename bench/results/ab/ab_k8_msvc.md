# Test A/B `ab_k8_msvc`

Optymalizacja 8 (presety kompilatora): MSVC /O2 vs /O2 /arch:AVX2 (preset msvc-release-avx2), tryb oszczędny (bez turbo) — kilka przypadków

- Programy: `k7` = `engine_k7_msvc.exe`, `avx2` = `engine_k8avx2_msvc.exe`
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 0.8 min, 2026-10-18T00:19
- Tło: start 18% CPU (WmiPrvSE.exe 222%, python.exe 42%, inny program 36%), koniec 16%
- Zgodność wyników z `k7`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | k7 [ms] | avx2 [ms] | avx2/k7 | zgodne |
|---|---|---|---|---|---|
| lava_test_3d | caSim | 92.8 [92.4–94.5] | 95.2 [93.8–97.8] | ×1.025 | tak |
| lava_test_3d | total | 119 [117–129] | 121 [119–125] | ×1.023 | tak |
| lava_test_3d | procWall | 140 [133–174] | 140 [135–143] | ×1.002 | tak |
| lava_etna_real | caSim | 84.5 [83.8–85.4] | 85.9 [85.4–86.3] | ×1.017 | tak |
| lava_etna_real | total | 144 [143–171] | 145 [145–146] | ×1.013 | tak |
| lava_etna_real | procWall | 164 [162–193] | 165 [163–168] | ×1.001 | tak |
| classic_1000x1000_s100_vn | caSim | 115 [114–126] | 115 [114–120] | ×1.008 | tak |
| classic_1000x1000_s100_vn | save | 79.3 [78.2–80.5] | 83.2 [82.4–97.8] | ×1.049 | tak |
| classic_1000x1000_s100_vn | total | 214 [213–229] | 219 [217–242] | ×1.025 | tak |
| classic_1000x1000_s100_vn | procWall | 247 [240–258] | 247 [244–270] | ×1.001 | tak |
| classic_100x100x100_s10_moore | caSim | 188 [186–206] | 188 [186–196] | ×1.003 | tak |
| classic_100x100x100_s10_moore | total | 292 [284–312] | 293 [291–300] | ×1.004 | tak |
| classic_100x100x100_s10_moore | procWall | 319 [311–343] | 320 [317–326] | ×1.004 | tak |
| mc_full_2d_200 | mcSim | 129 [128–133] | 127 [127–128] | ×0.989 | tak |
| mc_full_2d_200 | mcStats | 18.0 [17.9–19.1] | 18.0 [17.8–18.4] | ×0.997 | tak |
| mc_full_2d_200 | total | 158 [156–163] | 156 [155–158] | ×0.990 | tak |
| mc_full_2d_200 | procWall | 174 [172–189] | 174 [171–177] | ×0.998 | tak |
| mc_full_3d_50 | mcSim | 1 091 [1 083–1 250] | 1 078 [1 073–1 120] | ×0.988 | tak |
| mc_full_3d_50 | mcStats | 280 [278–299] | 275 [273–280] | ×0.983 | tak |
| mc_full_3d_50 | total | 1 390 [1 377–1 566] | 1 369 [1 363–1 417] | ×0.985 | tak |
| mc_full_3d_50 | procWall | 1 406 [1 393–1 582] | 1 384 [1 378–1 432] | ×0.984 | tak |
| lava_mc_3d | mcSim | 44.9 [44.6–46.8] | 45.8 [45.5–54.2] | ×1.021 | tak |
| lava_mc_3d | caSim | 61.2 [61.0–65.3] | 61.7 [61.3–62.3] | ×1.008 | tak |
| lava_mc_3d | total | 234 [232–254] | 237 [236–258] | ×1.014 | tak |
| lava_mc_3d | procWall | 250 [249–272] | 254 [253–274] | ×1.013 | tak |
