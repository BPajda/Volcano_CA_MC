# Test A/B `ab_k3_gcc_ca_classic`

Optymalizacja 3 (przesunięcia liniowe sąsiadów w CA), GCC — część ca_classic pełnego zestawu (scalona tabela: ab_k3_gcc.md)

- Programy: `przed` = `engine_przed`, `k2` = `engine_k2`, `k3` = `engine_k3`
- Przypięcie: sched_setaffinity({2}) (WSL2: procesor wirtualny); priorytet: domyślny; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 5.0 min, 2026-10-17T19:43
- Zgodność wyników z `przed`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | przed [ms] | k2 [ms] | k3 [ms] | k2/przed | k3/przed | k3/k2 | zgodne |
|---|---|---|---|---|---|---|---|---|
| classic_1000x1000_s100_vn | caSim | 1 193 [1 169–1 351] | 710 [681–820] | 405 [374–425] | ×0.595 | ×0.340 | ×0.571 | tak |
| classic_1000x1000_s100_vn | save | 111 [103–127] | 117 [103–225] | 110 [108–112] | ×1.055 | ×0.990 | ×0.938 | tak |
| classic_1000x1000_s100_vn | total | 1 415 [1 300–1 477] | 823 [813–954] | 524 [492–550] | ×0.582 | ×0.370 | ×0.636 | tak |
| classic_1000x1000_s100_vn | procWall | 1 421 [1 307–1 484] | 829 [819–960] | 530 [498–556] | ×0.584 | ×0.373 | ×0.639 | tak |
| classic_1000x1000_s100_moore | caSim | 1 090 [977–1 172] | 635 [617–825] | 307 [302–367] | ×0.583 | ×0.282 | ×0.484 | tak |
| classic_1000x1000_s100_moore | total | 1 230 [1 110–1 300] | 804 [735–963] | 424 [417–500] | ×0.654 | ×0.345 | ×0.528 | tak |
| classic_1000x1000_s100_moore | procWall | 1 236 [1 119–1 306] | 811 [741–969] | 430 [423–506] | ×0.656 | ×0.348 | ×0.530 | tak |
| classic_100x100x100_s10_vn | caSim | 399 [376–437] | 402 [359–442] | 211 [196–225] | ×1.007 | ×0.528 | ×0.525 | tak |
| classic_100x100x100_s10_vn | save | 113 [106–150] | 102 [98.2–126] | 112 [101–129] | ×0.895 | ×0.991 | ×1.107 | tak |
| classic_100x100x100_s10_vn | total | 526 [499–564] | 522 [470–579] | 338 [308–365] | ×0.991 | ×0.642 | ×0.648 | tak |
| classic_100x100x100_s10_vn | procWall | 533 [505–571] | 529 [477–587] | 346 [314–373] | ×0.993 | ×0.650 | ×0.654 | tak |
| classic_100x100x100_s10_moore | caSim | 565 [537–597] | 513 [494–580] | 231 [214–253] | ×0.909 | ×0.410 | ×0.451 | tak |
| classic_100x100x100_s10_moore | total | 680 [654–727] | 627 [613–707] | 355 [327–385] | ×0.921 | ×0.521 | ×0.566 | tak |
| classic_100x100x100_s10_moore | procWall | 687 [661–735] | 633 [620–715] | 362 [334–393] | ×0.922 | ×0.527 | ×0.572 | tak |
| classic_300x300x300_s100_vn | caSim | 15 946 [15 523–17 141] | 15 196 [15 103–16 624] | 8 712 [8 296–9 235] | ×0.953 | ×0.546 | ×0.573 | tak |
| classic_300x300x300_s100_vn | save | 305 [260–328] | 318 [263–338] | 333 [256–353] | ×1.042 | ×1.093 | ×1.049 | tak |
| classic_300x300x300_s100_vn | total | 16 530 [16 042–17 844] | 15 720 [15 633–17 201] | 9 406 [8 817–9 807] | ×0.951 | ×0.569 | ×0.598 | tak |
| classic_300x300x300_s100_vn | procWall | 16 676 [16 188–18 000] | 15 859 [15 776–17 361] | 9 554 [8 954–9 966] | ×0.951 | ×0.573 | ×0.602 | tak |

Tło (Windows, poza WSL): start 21% (WmiPrvSE.exe 203%, inny program 43%, System 41%), koniec 20%.
