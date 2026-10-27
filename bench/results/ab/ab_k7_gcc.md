# Test A/B `ab_k7_gcc`

Optymalizacja 7 (zapis plików tekstowych wyników), GCC, taktowanie bazowe; k7 bez wyrównania funkcji — caSim zawiera efekt układu kodu (+16 B), patrz ab_k7a_gcc.md

- Tabela z pomiaru `ab_k7_gcc_ca_raw.csv`, `ab_k7_gcc_mc_raw.csv` (te same przebiegi naprzemienne; programy k5, k7; warunki pomiaru i tło — w nagłówku `ab_k7_gcc_ca.md`, `ab_k7_gcc_mc.md`)

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
