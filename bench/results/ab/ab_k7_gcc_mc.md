# Test A/B `ab_k7_gcc_mc`

Optymalizacja 7 (zapis plików tekstowych wyników), GCC, tryb oszczędny (bez turbo) — grupa mc (scalona tabela: ab_k7_gcc.md)

- Programy: `k5` = `engine_k5`, `k7` = `engine_k7`
- Przypięcie: sched_setaffinity({2}) (WSL2: procesor wirtualny); priorytet: domyślny; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 6.2 min, 2026-10-17T22:55
- Zgodność wyników z `k5`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | k5 [ms] | k7 [ms] | k7/k5 | zgodne |
|---|---|---|---|---|---|
| mc_full_2d_200 | mcSim | 122 [121–140] | 122 [120–124] | ×0.995 | tak |
| mc_full_2d_200 | mcStats | 16.6 [15.9–20.0] | 15.9 [15.6–16.9] | ×0.962 | tak |
| mc_full_2d_200 | total | 143 [141–166] | 141 [139–145] | ×0.985 | tak |
| mc_full_2d_200 | procWall | 145 [144–168] | 143 [141–147] | ×0.985 | tak |
| mc_full_2d_1000 | mcSim | 8 488 [8 317–9 167] | 8 596 [8 385–8 881] | ×1.013 | tak |
| mc_full_2d_1000 | mcStats | 412 [397–418] | 395 [390–424] | ×0.960 | tak |
| mc_full_2d_1000 | mcSave | 67.0 [66.5–71.6] | 21.7 [20.6–23.2] | ×0.323 | tak |
| mc_full_2d_1000 | total | 8 979 [8 808–9 682] | 9 037 [8 822–9 328] | ×1.006 | tak |
| mc_full_2d_1000 | procWall | 8 981 [8 811–9 685] | 9 039 [8 825–9 331] | ×1.006 | tak |
| mc_full_3d_50 | mcSim | 1 087 [1 063–1 155] | 1 098 [1 076–1 118] | ×1.009 | tak |
| mc_full_3d_50 | mcStats | 241 [239–248] | 236 [232–253] | ×0.976 | tak |
| mc_full_3d_50 | total | 1 342 [1 319–1 417] | 1 340 [1 318–1 382] | ×0.999 | tak |
| mc_full_3d_50 | procWall | 1 344 [1 321–1 420] | 1 342 [1 321–1 384] | ×0.998 | tak |
| mc_full_3d_100 | mcSim | 21 935 [20 984–22 678] | 20 868 [20 579–21 874] | ×0.951 | tak |
| mc_full_3d_100 | mcStats | 952 [947–968] | 925 [919–934] | ×0.972 | tak |
| mc_full_3d_100 | mcSave | 68.3 [65.0–71.5] | 21.3 [19.4–22.5] | ×0.312 | tak |
| mc_full_3d_100 | total | 22 981 [22 039–23 725] | 21 842 [21 553–22 858] | ×0.950 | tak |
| mc_full_3d_100 | procWall | 22 983 [22 042–23 728] | 21 845 [21 557–22 860] | ×0.950 | tak |
| lava_mc_3d | mcSim | 41.3 [40.6–46.1] | 41.8 [41.4–42.6] | ×1.014 | tak |
| lava_mc_3d | caSim | 58.4 [57.0–60.4] | 71.1 [70.1–75.9] | ×1.217 | tak |
| lava_mc_3d | total | 237 [234–249] | 175 [170–182] | ×0.739 | tak |
| lava_mc_3d | procWall | 240 [238–252] | 178 [173–184] | ×0.740 | tak |

Tło (Windows, poza WSL): start 19% (WmiPrvSE.exe 208%, inny program 85%, python.exe 45%), koniec 17%.
