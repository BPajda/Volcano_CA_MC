# Test A/B `ab_e9_gcc_mc_3d_100`

- Programy: `e8` = `engine_e8`, `e9` = `engine_e9`
- Przypięcie: sched_setaffinity({2}) (WSL2: procesor wirtualny); priorytet: domyślny; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 4.0 min, 2026-10-18T05:32
- Zgodność wyników z `e8`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e8 [ms] | e9 [ms] | e9/e8 | zgodne |
|---|---|---|---|---|---|
| mc_full_3d_100 | mcSim | 21 212 [20 878–21 815] | 21 465 [21 148–21 608] | ×1.012 | tak |
| mc_full_3d_100 | mcStats | 940 [940–978] | 937 [926–991] | ×0.996 | tak |
| mc_full_3d_100 | mcSave | 21.0 [19.0–23.5] | 21.9 [18.7–23.3] | ×1.044 | tak |
| mc_full_3d_100 | total | 22 205 [21 867–22 811] | 22 448 [22 124–22 646] | ×1.011 | tak |
| mc_full_3d_100 | procWall | 22 208 [21 869–22 816] | 22 451 [22 127–22 648] | ×1.011 | tak |

Tło (Windows, poza WSL): start 27% (WmiPrvSE.exe 226%, inny program 98%, python.exe 50%), koniec 19%.
