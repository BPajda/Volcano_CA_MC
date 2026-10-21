# Test A/B `ab_e10d_gcc_mc`

- Programy: `e9` = `engine_e9`, `e10` = wersja e10d (`frontRulesLayer<Shifted>`, przed `frontStepSequential<Strip>`; binarka `engine_e10d_*`)
- Przypięcie: sched_setaffinity({2}) (WSL2: procesor wirtualny); priorytet: domyślny; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 2.0 min, 2026-10-20T13:55
- Zgodność wyników z `e9`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e9 [ms] | e10 [ms] | e10/e9 | zgodne |
|---|---|---|---|---|---|
| mc_full_2d_200 | mcSim | 120 [117–121] | 119 [118–122] | ×0.997 | tak |
| mc_full_2d_200 | mcStats | 15.5 [14.9–15.8] | 15.2 [14.9–16.0] | ×0.986 | tak |
| mc_full_2d_200 | total | 138 [135–139] | 138 [136–141] | ×1.001 | tak |
| mc_full_2d_200 | procWall | 140 [137–142] | 140 [138–143] | ×1.004 | tak |
| mc_full_2d_1000 | mcSim | 8 567 [8 467–8 627] | 8 559 [8 538–8 691] | ×0.999 | tak |
| mc_full_2d_1000 | mcStats | 392 [388–396] | 389 [386–390] | ×0.992 | tak |
| mc_full_2d_1000 | mcSave | 23.1 [19.5–23.4] | 22.5 [19.6–24.6] | ×0.976 | tak |
| mc_full_2d_1000 | total | 9 008 [8 913–9 071] | 8 998 [8 973–9 130] | ×0.999 | tak |
| mc_full_2d_1000 | procWall | 9 010 [8 916–9 074] | 9 000 [8 975–9 133] | ×0.999 | tak |
| mc_full_3d_50 | mcSim | 1 054 [1 034–1 065] | 1 049 [1 015–1 054] | ×0.995 | tak |
| mc_full_3d_50 | mcStats | 233 [229–237] | 234 [231–240] | ×1.004 | tak |
| mc_full_3d_50 | total | 1 291 [1 273–1 309] | 1 289 [1 261–1 293] | ×0.999 | tak |
| mc_full_3d_50 | procWall | 1 293 [1 275–1 311] | 1 292 [1 263–1 296] | ×0.999 | tak |
| lava_mc_3d | mcSim | 40.8 [40.6–41.8] | 41.0 [40.4–41.8] | ×1.005 | tak |
| lava_mc_3d | caSim | 57.1 [56.8–59.2] | 66.9 [66.7–69.4] | ×1.172 | tak |
| lava_mc_3d | total | 160 [158–165] | 171 [166–174] | ×1.070 | tak |
| lava_mc_3d | procWall | 163 [160–167] | 174 [169–177] | ×1.068 | tak |

Tło (Windows, poza WSL): start 24% (WmiPrvSE.exe 229%, inny program 182%, System 69%), koniec 19%.
