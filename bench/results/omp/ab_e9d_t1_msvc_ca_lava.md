# Test A/B `ab_e9d_t1_msvc_ca_lava`

- Programy: `e8` = `engine_e8_msvc.exe`, `e9d` = `engine_e9d_msvc.exe`
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 0.3 min, 2026-10-18T03:59
- Tło: start 33% CPU (WmiPrvSE.exe 228%, inny program 161%, inny program 100%), koniec 29%
- Zgodność wyników z `e8`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e8 [ms] | e9d [ms] | e9d/e8 | zgodne |
|---|---|---|---|---|---|
| lava_test_3d | caSim | 94.0 [92.8–95.8] | 94.8 [93.5–99.4] | ×1.008 | tak |
| lava_test_3d | total | 120 [118–122] | 121 [118–126] | ×1.001 | tak |
| lava_test_3d | procWall | 138 [136–147] | 139 [136–150] | ×1.011 | tak |
| lava_etna_real | caSim | 86.3 [84.8–89.4] | 86.1 [85.4–89.2] | ×0.997 | tak |
| lava_etna_real | total | 147 [145–175] | 147 [146–151] | ×1.001 | tak |
| lava_etna_real | procWall | 169 [164–200] | 171 [167–182] | ×1.012 | tak |
| lava_mc_2d_ca | caSim | 5.97 [5.90–6.09] | 6.26 [6.20–6.54] | ×1.048 | tak |
| lava_mc_2d_ca | total | 14.5 [13.4–15.5] | 14.7 [13.8–19.5] | ×1.017 | tak |
| lava_mc_2d_ca | procWall | 33.5 [29.2–49.7] | 35.1 [31.0–52.4] | ×1.048 | tak |
