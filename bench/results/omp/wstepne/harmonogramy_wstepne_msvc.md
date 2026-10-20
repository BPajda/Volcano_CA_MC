# Skalowanie OpenMP `harmonogramy_wstepne_msvc` (wstępne: 3 powtórzenia, tło 31% — tylko do wyboru harmonogramów)

- Program: `engine.exe`; przypięcie `parallel.affinity = pcores` (jeden wątek na rdzeń fizyczny P); priorytet HIGH_PRIORITY_CLASS; warianty naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 3.4 min, 2026-10-18T04:18
- Tło: start 31% CPU (WmiPrvSE.exe 232%, inny program 140%, inny program 102%), koniec 37%
- Zgodność wyników z p = 1 (albo z pierwszym harmonogramem): wszystkie przebiegi bitowo zgodne

| Przypadek | harmonogram | p | faza [ms] | total [ms] | faza / najlepszy | zgodne |
|---|---|---|---|---|---|---|
| lava_etna_real | static | 8 | 63.8 [59.9–66.7] | 124 | ×1.94 | tak |
| lava_etna_real | static,1 | 8 | 32.8 [29.9–47.5] | 89.8 | ×1.00 | tak |
| lava_etna_real | dynamic | 8 | 73.8 [67.6–79.0] | 131 | ×2.25 | tak |
| lava_etna_real | dynamic,4 | 8 | 75.6 [60.2–81.5] | 133 | ×2.30 | tak |
| lava_etna_real | guided | 8 | 70.0 [61.6–115] | 134 | ×2.13 | tak |
| lava_etna_real | guided,4 | 8 | 62.8 [50.1–96.7] | 115 | ×1.92 | tak |
| lava_duza_3d_front | static | 8 | 231 [221–308] | 267 | ×1.70 | tak |
| lava_duza_3d_front | static,1 | 8 | 136 [126–238] | 173 | ×1.00 | tak |
| lava_duza_3d_front | dynamic | 8 | 145 [142–252] | 189 | ×1.07 | tak |
| lava_duza_3d_front | dynamic,4 | 8 | 208 [169–321] | 245 | ×1.53 | tak |
| lava_duza_3d_front | guided | 8 | 264 [248–353] | 300 | ×1.94 | tak |
| lava_duza_3d_front | guided,4 | 8 | 315 [264–348] | 351 | ×2.32 | tak |
| lava_duza_3d_full | static | 8 | 4 181 [4 032–4 361] | 4 234 | ×1.62 | tak |
| lava_duza_3d_full | static,1 | 8 | 2 891 [2 640–3 617] | 2 939 | ×1.12 | tak |
| lava_duza_3d_full | dynamic | 8 | 2 727 [2 542–2 799] | 2 769 | ×1.06 | tak |
| lava_duza_3d_full | dynamic,4 | 8 | 3 290 [3 232–3 359] | 3 341 | ×1.28 | tak |
| lava_duza_3d_full | guided | 8 | 2 578 [2 495–2 813] | 2 618 | ×1.00 | tak |
| lava_duza_3d_full | guided,4 | 8 | 2 927 [2 800–3 103] | 2 967 | ×1.14 | tak |
| classic_2000x2000_s400_vn | static | 8 | 125 [125–139] | 261 | ×1.00 | tak |
| classic_2000x2000_s400_vn | static,1 | 8 | 238 [195–274] | 383 | ×1.90 | tak |
| classic_2000x2000_s400_vn | dynamic | 8 | 455 [440–494] | 601 | ×3.63 | tak |
| classic_2000x2000_s400_vn | dynamic,4 | 8 | 244 [216–270] | 374 | ×1.94 | tak |
| classic_2000x2000_s400_vn | guided | 8 | 176 [171–177] | 325 | ×1.40 | tak |
| classic_2000x2000_s400_vn | guided,4 | 8 | 157 [155–181] | 297 | ×1.25 | tak |
| classic_300x300x300_s100_vn | static | 8 | 1 120 [1 099–1 234] | 2 013 | ×1.46 | tak |
| classic_300x300x300_s100_vn | static,1 | 8 | 1 259 [1 235–1 304] | 2 169 | ×1.64 | tak |
| classic_300x300x300_s100_vn | dynamic | 8 | 952 [933–975] | 1 840 | ×1.24 | tak |
| classic_300x300x300_s100_vn | dynamic,4 | 8 | 765 [740–874] | 1 656 | ×1.00 | tak |
| classic_300x300x300_s100_vn | guided | 8 | 951 [765–995] | 1 844 | ×1.24 | tak |
| classic_300x300x300_s100_vn | guided,4 | 8 | 923 [836–977] | 1 879 | ×1.21 | tak |
| mc_cb_2d_1000 | static | 8 | 373 [341–493] | 818 | ×1.15 | tak |
| mc_cb_2d_1000 | static,1 | 8 | 396 [377–517] | 831 | ×1.22 | tak |
| mc_cb_2d_1000 | dynamic | 8 | 399 [395–488] | 842 | ×1.23 | tak |
| mc_cb_2d_1000 | dynamic,4 | 8 | 371 [331–409] | 827 | ×1.14 | tak |
| mc_cb_2d_1000 | guided | 8 | 350 [350–429] | 808 | ×1.08 | tak |
| mc_cb_2d_1000 | guided,4 | 8 | 324 [304–455] | 766 | ×1.00 | tak |
| mc_cb_3d_100 | static | 8 | 1 142 [989–1 517] | 2 130 | ×1.22 | tak |
| mc_cb_3d_100 | static,1 | 8 | 2 098 [2 039–2 100] | 3 128 | ×2.25 | tak |
| mc_cb_3d_100 | dynamic | 8 | 934 [907–943] | 1 928 | ×1.00 | tak |
| mc_cb_3d_100 | dynamic,4 | 8 | 1 154 [1 010–1 281] | 2 246 | ×1.24 | tak |
| mc_cb_3d_100 | guided | 8 | 1 293 [1 063–1 326] | 2 283 | ×1.38 | tak |
| mc_cb_3d_100 | guided,4 | 8 | 1 233 [1 097–1 319] | 2 246 | ×1.32 | tak |
