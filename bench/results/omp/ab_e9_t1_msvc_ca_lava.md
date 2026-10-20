# Test A/B `ab_e9_t1_msvc_ca_lava`

- Programy: `e8` = `engine_e8_msvc.exe`, `e9` = `engine_e9a_msvc.exe`
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 0.2 min, 2026-10-18T03:50
- Tło: start 22% CPU (WmiPrvSE.exe 233%, inny program 79%, python.exe 44%), koniec 20%
- Zgodność wyników z `e8`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e8 [ms] | e9 [ms] | e9/e8 | zgodne |
|---|---|---|---|---|---|
| lava_test_3d | caSim | 97.0 [93.6–106] | 101 [97.0–146] | ×1.037 | tak |
| lava_test_3d | total | 123 [119–133] | 127 [123–181] | ×1.033 | tak |
| lava_test_3d | procWall | 141 [136–158] | 145 [140–204] | ×1.032 | tak |
| lava_etna_real | caSim | 88.1 [85.9–95.9] | 92.5 [88.6–101] | ×1.051 | tak |
| lava_etna_real | total | 149 [147–171] | 158 [152–181] | ×1.060 | tak |
| lava_etna_real | procWall | 169 [167–195] | 183 [173–202] | ×1.080 | tak |
| lava_mc_2d_ca | caSim | 6.19 [5.98–7.72] | 6.53 [6.26–8.37] | ×1.055 | tak |
| lava_mc_2d_ca | total | 14.3 [13.6–24.8] | 14.4 [13.7–18.1] | ×1.006 | tak |
| lava_mc_2d_ca | procWall | 33.9 [30.0–45.0] | 31.9 [30.2–47.2] | ×0.940 | tak |
