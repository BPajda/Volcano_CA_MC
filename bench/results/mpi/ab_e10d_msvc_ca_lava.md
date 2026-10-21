# Test A/B `ab_e10d_msvc_ca_lava`

- Programy: `e9` = `engine_e9_msvc.exe`, `e10` = wersja e10d (`frontRulesLayer<Shifted>`, przed `frontStepSequential<Strip>`; binarka `engine_e10d_*`)
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 0.3 min, 2026-10-20T13:47
- Tło: start 20% CPU (WmiPrvSE.exe 216%, CompatTelRunner.exe 97%, python.exe 39%), koniec 20%
- Zgodność wyników z `e9`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e9 [ms] | e10 [ms] | e10/e9 | zgodne |
|---|---|---|---|---|---|
| lava_test_3d | caSim | 97.0 [94.9–108] | 97.8 [95.9–103] | ×1.008 | tak |
| lava_test_3d | total | 123 [120–136] | 124 [122–129] | ×1.008 | tak |
| lava_test_3d | procWall | 142 [138–155] | 144 [141–154] | ×1.014 | tak |
| lava_etna_real | caSim | 89.5 [86.3–101] | 89.1 [87.2–96.0] | ×0.996 | tak |
| lava_etna_real | total | 152 [147–178] | 152 [149–158] | ×1.004 | tak |
| lava_etna_real | procWall | 175 [169–203] | 175 [169–195] | ×1.003 | tak |
| lava_mc_2d_ca | caSim | 6.34 [6.11–6.98] | 6.37 [6.22–7.09] | ×1.004 | tak |
| lava_mc_2d_ca | total | 14.8 [13.0–17.0] | 15.1 [14.0–16.1] | ×1.020 | tak |
| lava_mc_2d_ca | procWall | 36.7 [30.1–48.6] | 34.8 [31.7–41.3] | ×0.949 | tak |
