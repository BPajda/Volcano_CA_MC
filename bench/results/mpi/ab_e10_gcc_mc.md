# Test A/B `ab_e10_gcc_mc`

- Programy: `e9` = `engine_e9`, `e10` = `engine_e10`
- Przypięcie: sched_setaffinity({2}) (WSL2: procesor wirtualny); priorytet: domyślny; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 2.0 min, 2026-10-20T14:17
- Zgodność wyników z `e9`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e9 [ms] | e10 [ms] | e10/e9 | zgodne |
|---|---|---|---|---|---|
| mc_full_2d_200 | mcSim | 118 [117–131] | 119 [118–127] | ×1.002 | tak |
| mc_full_2d_200 | mcStats | 15.3 [15.0–16.1] | 15.4 [14.8–17.6] | ×1.003 | tak |
| mc_full_2d_200 | total | 137 [135–151] | 137 [136–149] | ×1.001 | tak |
| mc_full_2d_200 | procWall | 139 [137–153] | 139 [138–152] | ×1.001 | tak |
| mc_full_2d_1000 | mcSim | 8 507 [8 397–8 968] | 8 330 [8 291–8 446] | ×0.979 | tak |
| mc_full_2d_1000 | mcStats | 389 [389–407] | 382 [378–382] | ×0.981 | tak |
| mc_full_2d_1000 | mcSave | 22.0 [19.0–25.0] | 22.1 [20.7–23.2] | ×1.004 | tak |
| mc_full_2d_1000 | total | 8 950 [8 837–9 414] | 8 760 [8 722–8 875] | ×0.979 | tak |
| mc_full_2d_1000 | procWall | 8 952 [8 840–9 416] | 8 763 [8 725–8 877] | ×0.979 | tak |
| mc_full_3d_50 | mcSim | 1 036 [1 024–1 159] | 1 036 [1 023–1 104] | ×1.000 | tak |
| mc_full_3d_50 | mcStats | 231 [229–248] | 231 [229–244] | ×1.002 | tak |
| mc_full_3d_50 | total | 1 276 [1 260–1 415] | 1 277 [1 268–1 356] | ×1.001 | tak |
| mc_full_3d_50 | procWall | 1 278 [1 262–1 419] | 1 279 [1 270–1 359] | ×1.001 | tak |
| lava_mc_3d | mcSim | 40.5 [40.1–41.9] | 41.0 [40.0–46.7] | ×1.013 | tak |
| lava_mc_3d | caSim | 57.3 [56.7–74.1] | 57.0 [56.4–72.0] | ×0.995 | tak |
| lava_mc_3d | total | 160 [155–180] | 163 [156–194] | ×1.017 | tak |
| lava_mc_3d | procWall | 163 [158–183] | 166 [159–197] | ×1.017 | tak |

Tło (Windows, poza WSL): start 16% (WmiPrvSE.exe 212%, python.exe 40%, dwm.exe 32%), koniec 18%.
