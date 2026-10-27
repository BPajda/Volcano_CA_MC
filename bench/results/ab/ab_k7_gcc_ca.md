# Test A/B `ab_k7_gcc_ca`

Optymalizacja 7 (zapis plików tekstowych wyników), GCC, taktowanie bazowe — grupy CA (scalona tabela: ab_k7_gcc.md)

- Programy: `k5` = `engine_k5`, `k7` = `engine_k7`
- Przypięcie: sched_setaffinity({2}) (WSL2: procesor wirtualny); priorytet: domyślny; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 1.4 min, 2026-10-17T22:46
- Zgodność wyników z `k5`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | k5 [ms] | k7 [ms] | k7/k5 | zgodne |
|---|---|---|---|---|---|
| lava_test_3d | caSim | 93.6 [91.6–95.7] | 102 [99.8–105] | ×1.092 | tak |
| lava_test_3d | total | 150 [145–155] | 115 [112–119] | ×0.770 | tak |
| lava_test_3d | procWall | 152 [148–158] | 118 [115–122] | ×0.776 | tak |
| lava_etna_real | caSim | 87.2 [82.6–90.8] | 92.9 [91.1–94.6] | ×1.066 | tak |
| lava_etna_real | total | 141 [132–153] | 146 [140–156] | ×1.035 | tak |
| lava_etna_real | procWall | 146 [137–157] | 153 [144–161] | ×1.052 | tak |
| lava_mc_2d_ca | caSim | 6.04 [5.89–6.81] | 6.41 [6.19–6.98] | ×1.062 | tak |
| lava_mc_2d_ca | total | 11.9 [11.5–12.9] | 8.60 [8.38–9.20] | ×0.722 | tak |
| lava_mc_2d_ca | procWall | 14.2 [13.6–14.9] | 10.9 [10.3–11.6] | ×0.770 | tak |
| classic_1000x1000_s100_vn | caSim | 121 [118–127] | 126 [123–233] | ×1.046 | tak |
| classic_1000x1000_s100_vn | save | 260 [254–379] | 60.5 [47.1–67.0] | ×0.232 | tak |
| classic_1000x1000_s100_vn | total | 399 [396–526] | 206 [190–316] | ×0.516 | tak |
| classic_1000x1000_s100_vn | procWall | 414 [411–541] | 221 [205–331] | ×0.534 | tak |
| classic_1000x1000_s100_moore | caSim | 131 [123–145] | 131 [129–140] | ×0.997 | tak |
| classic_1000x1000_s100_moore | total | 409 [398–442] | 202 [196–224] | ×0.495 | tak |
| classic_1000x1000_s100_moore | procWall | 427 [413–457] | 218 [211–239] | ×0.512 | tak |
| classic_100x100x100_s10_vn | caSim | 99.5 [96.3–101] | 104 [102–117] | ×1.040 | tak |
| classic_100x100x100_s10_vn | save | 259 [254–273] | 46.7 [45.2–133] | ×0.181 | tak |
| classic_100x100x100_s10_vn | total | 378 [372–394] | 172 [168–262] | ×0.455 | tak |
| classic_100x100x100_s10_vn | procWall | 394 [387–411] | 188 [184–277] | ×0.478 | tak |
| classic_100x100x100_s10_moore | caSim | 190 [186–195] | 241 [238–332] | ×1.266 | tak |
| classic_100x100x100_s10_moore | total | 471 [464–582] | 321 [305–416] | ×0.682 | tak |
| classic_100x100x100_s10_moore | procWall | 488 [480–599] | 338 [322–432] | ×0.692 | tak |
| classic_300x300x300_s100_vn | caSim | 3 694 [3 638–3 918] | 3 896 [3 841–4 018] | ×1.055 | tak |
| classic_300x300x300_s100_vn | save | 657 [616–1 016] | 740 [672–749] | ×1.127 | tak |
| classic_300x300x300_s100_vn | total | 4 800 [4 758–5 162] | 5 054 [5 024–5 208] | ×1.053 | tak |
| classic_300x300x300_s100_vn | procWall | 5 156 [5 120–5 515] | 5 408 [5 378–5 567] | ×1.049 | tak |

Tło (Windows, poza WSL): start 21% (WmiPrvSE.exe 222%, inny program 77%, python.exe 44%), koniec 18%.
