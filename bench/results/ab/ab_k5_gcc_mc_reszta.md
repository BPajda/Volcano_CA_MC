# Test A/B `ab_k5_gcc_mc_reszta`

Optymalizacja 5 (tańsze statystyki MC), GCC, taktowanie bazowe — część mc bez 100^3 (scalona tabela: ab_k5_gcc.md)

- Programy: `przed` = `engine_przed`, `k4` = `engine_k4`, `k5` = `engine_k5`
- Przypięcie: sched_setaffinity({2}) (WSL2: procesor wirtualny); priorytet: domyślny; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 3.7 min, 2026-10-17T22:20
- Zgodność wyników z `przed`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | przed [ms] | k4 [ms] | k5 [ms] | k4/przed | k5/przed | k5/k4 | zgodne |
|---|---|---|---|---|---|---|---|---|
| mc_full_2d_200 | mcSim | 148 [144–190] | 122 [119–133] | 120 [117–132] | ×0.823 | ×0.813 | ×0.988 | tak |
| mc_full_2d_200 | mcStats | 19.7 [19.4–21.0] | 18.9 [17.9–27.2] | 16.4 [15.7–17.1] | ×0.962 | ×0.834 | ×0.866 | tak |
| mc_full_2d_200 | total | 173 [168–216] | 146 [141–165] | 141 [138–157] | ×0.842 | ×0.816 | ×0.969 | tak |
| mc_full_2d_200 | procWall | 175 [171–221] | 148 [143–166] | 143 [140–159] | ×0.845 | ×0.818 | ×0.969 | tak |
| mc_full_2d_1000 | mcSim | 11 315 [10 860–11 709] | 7 906 [7 783–8 090] | 8 035 [7 737–8 515] | ×0.699 | ×0.710 | ×1.016 | tak |
| mc_full_2d_1000 | mcStats | 499 [497–509] | 475 [465–482] | 410 [402–456] | ×0.952 | ×0.822 | ×0.863 | tak |
| mc_full_2d_1000 | mcSave | 71.9 [66.4–73.7] | 73.0 [70.0–74.6] | 67.0 [64.9–68.5] | ×1.016 | ×0.932 | ×0.918 | tak |
| mc_full_2d_1000 | total | 11 953 [11 456–12 315] | 8 474 [8 354–8 671] | 8 531 [8 240–9 060] | ×0.709 | ×0.714 | ×1.007 | tak |
| mc_full_2d_1000 | procWall | 11 955 [11 459–12 317] | 8 476 [8 356–8 674] | 8 533 [8 242–9 062] | ×0.709 | ×0.714 | ×1.007 | tak |
| mc_full_3d_50 | mcSim | 1 542 [1 518–1 681] | 1 100 [1 053–1 289] | 1 086 [1 050–1 116] | ×0.713 | ×0.705 | ×0.988 | tak |
| mc_full_3d_50 | mcStats | 473 [468–507] | 435 [429–484] | 242 [238–245] | ×0.920 | ×0.512 | ×0.556 | tak |
| mc_full_3d_50 | total | 2 032 [2 002–2 201] | 1 546 [1 495–1 787] | 1 340 [1 301–1 372] | ×0.761 | ×0.660 | ×0.867 | tak |
| mc_full_3d_50 | procWall | 2 034 [2 004–2 202] | 1 548 [1 498–1 790] | 1 342 [1 303–1 375] | ×0.761 | ×0.660 | ×0.867 | tak |
| lava_mc_3d | mcSim | 98.3 [94.2–104] | 41.5 [40.5–44.3] | 41.2 [40.2–41.8] | ×0.422 | ×0.418 | ×0.992 | tak |
| lava_mc_3d | caSim | 2 171 [2 161–2 362] | 57.6 [55.8–58.0] | 58.3 [57.8–59.4] | ×0.027 | ×0.027 | ×1.013 | tak |
| lava_mc_3d | total | 2 427 [2 419–2 650] | 251 [248–255] | 242 [235–249] | ×0.103 | ×0.100 | ×0.964 | tak |
| lava_mc_3d | procWall | 2 430 [2 422–2 652] | 254 [251–257] | 244 [238–251] | ×0.104 | ×0.101 | ×0.964 | tak |

Tło (Windows, poza WSL): start 20% (WmiPrvSE.exe 222%, python.exe 43%, inny program 39%), koniec 18%.
