# Test A/B `ab_e10d_msvc_mc`

- Programy: `e9` = `engine_e9_msvc.exe`, `e10` = wersja e10d (`frontRulesLayer<Shifted>`, przed `frontStepSequential<Strip>`; binarka `engine_e10d_*`)
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 2.3 min, 2026-10-20T13:51
- Tło: start 18% CPU (WmiPrvSE.exe 214%, System 43%, python.exe 42%), koniec 23%
- Zgodność wyników z `e9`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e9 [ms] | e10 [ms] | e10/e9 | zgodne |
|---|---|---|---|---|---|
| mc_full_2d_200 | mcSim | 131 [130–135] | 133 [131–148] | ×1.012 | tak |
| mc_full_2d_200 | mcStats | 18.6 [18.3–19.8] | 18.7 [18.3–21.0] | ×1.005 | tak |
| mc_full_2d_200 | total | 161 [159–171] | 162 [158–181] | ×1.004 | tak |
| mc_full_2d_200 | procWall | 180 [176–192] | 182 [178–201] | ×1.009 | tak |
| mc_full_2d_1000 | mcSim | 9 767 [9 518–9 869] | 9 613 [9 490–9 742] | ×0.984 | tak |
| mc_full_2d_1000 | mcStats | 441 [435–451] | 435 [428–439] | ×0.987 | tak |
| mc_full_2d_1000 | mcSave | 41.9 [41.1–43.7] | 42.8 [41.6–46.9] | ×1.020 | tak |
| mc_full_2d_1000 | total | 10 285 [10 043–10 390] | 10 131 [9 999–10 259] | ×0.985 | tak |
| mc_full_2d_1000 | procWall | 10 304 [10 061–10 417] | 10 150 [10 018–10 278] | ×0.985 | tak |
| mc_full_3d_50 | mcSim | 1 174 [1 122–1 205] | 1 162 [1 137–1 205] | ×0.989 | tak |
| mc_full_3d_50 | mcStats | 287 [283–289] | 278 [277–288] | ×0.970 | tak |
| mc_full_3d_50 | total | 1 477 [1 422–1 511] | 1 458 [1 432–1 504] | ×0.987 | tak |
| mc_full_3d_50 | procWall | 1 495 [1 444–1 532] | 1 476 [1 456–1 524] | ×0.987 | tak |
| lava_mc_3d | mcSim | 46.6 [45.3–55.2] | 47.1 [46.3–50.3] | ×1.011 | tak |
| lava_mc_3d | caSim | 65.0 [63.0–68.1] | 65.3 [63.9–70.5] | ×1.006 | tak |
| lava_mc_3d | total | 243 [239–277] | 244 [239–251] | ×1.006 | tak |
| lava_mc_3d | procWall | 267 [259–299] | 263 [258–271] | ×0.988 | tak |
