# Test A/B `ab_k1_mc_gcc`

Optymalizacja 1, GCC

- Programy: `przed` = `engine_przed`, `k1` = `engine_k1`
- Przypięcie: sched_setaffinity({2}) (WSL2: procesor wirtualny); priorytet: domyślny; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 2.8 min, 2026-10-17T08:35
- Zgodność wyników z `przed`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | przed [ms] | k1 [ms] | k1/przed | zgodne |
|---|---|---|---|---|---|
| mc_full_2d_200 | mcSim | 60.9 [58.4–87.8] | 49.8 [47.6–65.7] | ×0.818 | tak |
| mc_full_2d_200 | mcStats | 8.16 [7.59–9.96] | 7.55 [7.32–12.5] | ×0.925 | tak |
| mc_full_2d_200 | total | 71.1 [68.4–100] | 59.5 [56.9–80.9] | ×0.837 | tak |
| mc_full_2d_200 | procWall | 72.1 [69.3–101] | 60.5 [57.8–81.9] | ×0.839 | tak |
| mc_full_2d_1000 | mcSim | 4 637 [3 965–5 630] | 3 025 [2 585–3 389] | ×0.652 | tak |
| mc_full_2d_1000 | mcStats | 238 [216–246] | 219 [211–236] | ×0.918 | tak |
| mc_full_2d_1000 | mcSave | 31.9 [28.5–34.8] | 32.7 [30.1–35.2] | ×1.024 | tak |
| mc_full_2d_1000 | total | 4 924 [4 225–5 936] | 3 284 [2 847–3 653] | ×0.667 | tak |
| mc_full_2d_1000 | procWall | 4 925 [4 226–5 937] | 3 285 [2 848–3 654] | ×0.667 | tak |
| mc_full_3d_50 | mcSim | 608 [587–658] | 445 [418–467] | ×0.731 | tak |
| mc_full_3d_50 | mcStats | 206 [191–220] | 196 [177–199] | ×0.951 | tak |
| mc_full_3d_50 | total | 810 [792–880] | 647 [604–670] | ×0.799 | tak |
| mc_full_3d_50 | procWall | 811 [793–881] | 648 [605–671] | ×0.799 | tak |
| mc_full_3d_100 | mcSim | 10 603 [10 224–12 719] | 6 651 [6 598–7 519] | ×0.627 | tak |
| mc_full_3d_100 | mcStats | 909 [839–937] | 822 [773–835] | ×0.904 | tak |
| mc_full_3d_100 | mcSave | 31.9 [30.8–33.1] | 30.1 [28.4–32.1] | ×0.944 | tak |
| mc_full_3d_100 | total | 11 568 [11 172–13 703] | 7 473 [7 466–8 389] | ×0.646 | tak |
| mc_full_3d_100 | procWall | 11 569 [11 173–13 704] | 7 475 [7 467–8 390] | ×0.646 | tak |
| lava_mc_3d | mcSim | 39.7 [38.2–48.3] | 17.3 [15.8–18.0] | ×0.435 | tak |
| lava_mc_3d | caSim | 965 [926–1 024] | 961 [923–1 035] | ×0.996 | tak |
| lava_mc_3d | total | 1 072 [1 030–1 160] | 1 038 [1 004–1 121] | ×0.969 | tak |
| lava_mc_3d | procWall | 1 073 [1 031–1 162] | 1 039 [1 006–1 123] | ×0.969 | tak |

Tło (Windows, poza WSL): start 14% (WmiPrvSE.exe 193%, svchost.exe 39%, System 32%), koniec 14%.
