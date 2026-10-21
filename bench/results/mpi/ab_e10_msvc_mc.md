# Test A/B `ab_e10_msvc_mc`

- Programy: `e9` = `engine_e9_msvc.exe`, `e10` = `engine_e10_msvc.exe`
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 2.3 min, 2026-10-20T14:13
- Tło: start 18% CPU (WmiPrvSE.exe 204%, python.exe 39%, System 33%), koniec 19%
- Zgodność wyników z `e9`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e9 [ms] | e10 [ms] | e10/e9 | zgodne |
|---|---|---|---|---|---|
| mc_full_2d_200 | mcSim | 131 [129–142] | 132 [130–145] | ×1.003 | tak |
| mc_full_2d_200 | mcStats | 18.6 [18.2–20.1] | 18.3 [17.8–21.0] | ×0.985 | tak |
| mc_full_2d_200 | total | 161 [157–174] | 159 [158–176] | ×0.992 | tak |
| mc_full_2d_200 | procWall | 182 [174–193] | 180 [175–197] | ×0.989 | tak |
| mc_full_2d_1000 | mcSim | 9 679 [9 501–10 359] | 9 730 [9 368–10 433] | ×1.005 | tak |
| mc_full_2d_1000 | mcStats | 441 [433–447] | 429 [426–459] | ×0.975 | tak |
| mc_full_2d_1000 | mcSave | 42.8 [41.5–46.9] | 41.4 [41.1–45.2] | ×0.967 | tak |
| mc_full_2d_1000 | total | 10 202 [10 014–10 892] | 10 240 [9 875–10 981] | ×1.004 | tak |
| mc_full_2d_1000 | procWall | 10 225 [10 041–10 916] | 10 260 [9 900–11 001] | ×1.003 | tak |
| mc_full_3d_50 | mcSim | 1 193 [1 104–1 258] | 1 166 [1 096–1 248] | ×0.977 | tak |
| mc_full_3d_50 | mcStats | 286 [281–293] | 275 [270–286] | ×0.960 | tak |
| mc_full_3d_50 | total | 1 495 [1 403–1 567] | 1 458 [1 383–1 551] | ×0.976 | tak |
| mc_full_3d_50 | procWall | 1 513 [1 429–1 588] | 1 477 [1 411–1 569] | ×0.976 | tak |
| lava_mc_3d | mcSim | 46.1 [45.7–46.6] | 46.2 [45.5–52.5] | ×1.002 | tak |
| lava_mc_3d | caSim | 63.3 [62.4–68.9] | 64.4 [63.7–72.0] | ×1.017 | tak |
| lava_mc_3d | total | 240 [237–245] | 241 [237–267] | ×1.004 | tak |
| lava_mc_3d | procWall | 259 [255–265] | 260 [257–287] | ×1.005 | tak |
