# Test A/B `ab_e10a_msvc_ca_lava`

- Programy: `e9` = `engine_e9_msvc.exe`, `e10` = `engine_e10a_msvc.exe` (pierwsza wersja etapu 10, przed poprawką `frontRulesLayer<Shifted>`)
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 0.3 min, 2026-10-20T13:24
- Tło: start 12% CPU (WmiPrvSE.exe 194%, python.exe 37%, System 34%), koniec 13%
- Zgodność wyników z `e9`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e9 [ms] | e10 [ms] | e10/e9 | zgodne |
|---|---|---|---|---|---|
| lava_test_3d | caSim | 93.4 [92.0–93.9] | 101 [99.4–102] | ×1.078 | tak |
| lava_test_3d | total | 119 [117–129] | 126 [124–128] | ×1.059 | tak |
| lava_test_3d | procWall | 136 [134–146] | 143 [141–163] | ×1.053 | tak |
| lava_etna_real | caSim | 85.2 [84.6–86.1] | 91.5 [90.6–92.0] | ×1.073 | tak |
| lava_etna_real | total | 144 [144–169] | 151 [149–152] | ×1.046 | tak |
| lava_etna_real | procWall | 167 [164–192] | 172 [170–176] | ×1.030 | tak |
| lava_mc_2d_ca | caSim | 6.15 [6.05–6.35] | 6.15 [6.06–6.28] | ×1.001 | tak |
| lava_mc_2d_ca | total | 14.2 [13.3–24.3] | 14.0 [13.5–14.8] | ×0.983 | tak |
| lava_mc_2d_ca | procWall | 34.7 [29.8–46.0] | 31.4 [30.6–64.7] | ×0.907 | tak |
