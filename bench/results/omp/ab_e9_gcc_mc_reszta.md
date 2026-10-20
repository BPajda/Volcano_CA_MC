# Test A/B `ab_e9_gcc_mc_reszta`

- Programy: `e8` = `engine_e8`, `e9` = `engine_e9`
- Przypięcie: sched_setaffinity({2}) (WSL2: procesor wirtualny); priorytet: domyślny; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 2.2 min, 2026-10-18T05:27
- Zgodność wyników z `e8`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e8 [ms] | e9 [ms] | e9/e8 | zgodne |
|---|---|---|---|---|---|
| mc_full_2d_200 | mcSim | 123 [121–128] | 123 [120–129] | ×1.000 | tak |
| mc_full_2d_200 | mcStats | 15.8 [15.4–16.3] | 15.7 [15.2–16.6] | ×0.994 | tak |
| mc_full_2d_200 | total | 142 [139–147] | 141 [138–148] | ×0.998 | tak |
| mc_full_2d_200 | procWall | 143 [141–149] | 144 [140–150] | ×1.002 | tak |
| mc_full_2d_1000 | mcSim | 9 168 [8 909–9 741] | 9 133 [8 936–10 022] | ×0.996 | tak |
| mc_full_2d_1000 | mcStats | 395 [389–396] | 395 [393–400] | ×1.000 | tak |
| mc_full_2d_1000 | mcSave | 21.8 [20.5–25.3] | 21.6 [20.1–25.1] | ×0.992 | tak |
| mc_full_2d_1000 | total | 9 619 [9 353–10 189] | 9 580 [9 376–10 467] | ×0.996 | tak |
| mc_full_2d_1000 | procWall | 9 622 [9 355–10 191] | 9 582 [9 379–10 470] | ×0.996 | tak |
| mc_full_3d_50 | mcSim | 1 088 [1 079–1 130] | 1 086 [1 073–1 120] | ×0.998 | tak |
| mc_full_3d_50 | mcStats | 241 [236–243] | 235 [232–245] | ×0.977 | tak |
| mc_full_3d_50 | total | 1 336 [1 323–1 380] | 1 329 [1 316–1 363] | ×0.995 | tak |
| mc_full_3d_50 | procWall | 1 338 [1 326–1 382] | 1 331 [1 318–1 365] | ×0.995 | tak |
| lava_mc_3d | mcSim | 41.5 [40.8–43.9] | 41.5 [41.0–42.2] | ×1.001 | tak |
| lava_mc_3d | caSim | 57.6 [56.9–59.7] | 59.5 [57.4–61.2] | ×1.033 | tak |
| lava_mc_3d | total | 165 [161–168] | 165 [162–171] | ×1.005 | tak |
| lava_mc_3d | procWall | 167 [164–170] | 168 [165–174] | ×1.005 | tak |

Tło (Windows, poza WSL): start 33% (WmiPrvSE.exe 225%, inny program 84%, Code.exe 52%), koniec 24%.
