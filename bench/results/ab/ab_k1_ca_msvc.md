# Test A/B `ab_k1_ca_msvc`

Optymalizacja 1 (zmiana tylko w MC) — przypadki CA, MSVC: kolumny przed i k1 z pomiaru ab_k2_msvc

- Tabela z pomiaru `ab_k2_msvc_raw.csv` (te same przebiegi naprzemienne; programy przed, k1; warunki pomiaru i tło — w nagłówku `ab_k2_msvc.md`)

| Przypadek | miara | przed [ms] | k1 [ms] | k1/przed | zgodne |
|---|---|---|---|---|---|
| lava_test_3d | caSim | 1 501 [1 471–1 554] | 1 498 [1 459–1 509] | ×0.998 | tak |
| lava_test_3d | total | 1 532 [1 504–1 585] | 1 529 [1 489–1 541] | ×0.998 | tak |
| lava_test_3d | procWall | 1 540 [1 511–1 594] | 1 536 [1 497–1 548] | ×0.998 | tak |
| lava_etna_real | caSim | 12 926 [12 803–13 015] | 12 899 [12 722–13 157] | ×0.998 | tak |
| lava_etna_real | total | 12 958 [12 836–13 048] | 12 945 [12 756–13 195] | ×0.999 | tak |
| lava_etna_real | procWall | 12 967 [12 845–13 058] | 12 954 [12 765–13 206] | ×0.999 | tak |
| lava_mc_2d_ca | caSim | 48.8 [47.3–50.2] | 48.9 [47.3–54.7] | ×1.002 | tak |
| lava_mc_2d_ca | total | 55.9 [53.9–61.7] | 55.7 [53.6–60.4] | ×0.996 | tak |
| lava_mc_2d_ca | procWall | 63.3 [60.6–70.8] | 62.9 [60.6–68.2] | ×0.994 | tak |
| classic_1000x1000_s100_vn | caSim | 1 380 [1 362–1 410] | 1 384 [1 357–1 412] | ×1.003 | tak |
| classic_1000x1000_s100_vn | save | 132 [131–134] | 135 [125–143] | ×1.023 | tak |
| classic_1000x1000_s100_vn | total | 1 533 [1 514–1 563] | 1 542 [1 503–1 569] | ×1.006 | tak |
| classic_1000x1000_s100_vn | procWall | 1 553 [1 526–1 576] | 1 555 [1 516–1 583] | ×1.002 | tak |
| classic_1000x1000_s100_moore | caSim | 1 139 [1 121–1 160] | 1 131 [1 120–1 155] | ×0.993 | tak |
| classic_1000x1000_s100_moore | total | 1 290 [1 269–1 321] | 1 285 [1 271–1 318] | ×0.996 | tak |
| classic_1000x1000_s100_moore | procWall | 1 304 [1 282–1 334] | 1 298 [1 283–1 330] | ×0.995 | tak |
| classic_100x100x100_s10_vn | caSim | 429 [416–440] | 420 [416–440] | ×0.980 | tak |
| classic_100x100x100_s10_vn | save | 127 [122–129] | 126 [124–129] | ×0.991 | tak |
| classic_100x100x100_s10_vn | total | 566 [553–582] | 558 [551–580] | ×0.986 | tak |
| classic_100x100x100_s10_vn | procWall | 581 [564–595] | 570 [564–593] | ×0.980 | tak |
| classic_100x100x100_s10_moore | caSim | 590 [575–606] | 584 [577–607] | ×0.989 | tak |
| classic_100x100x100_s10_moore | total | 729 [710–754] | 723 [711–748] | ×0.991 | tak |
| classic_100x100x100_s10_moore | procWall | 742 [721–768] | 735 [722–760] | ×0.991 | tak |
| classic_300x300x300_s100_vn | caSim | 17 117 [17 000–17 255] | 17 131 [17 070–17 288] | ×1.001 | tak |
| classic_300x300x300_s100_vn | save | 296 [291–304] | 296 [278–321] | ×1.001 | tak |
| classic_300x300x300_s100_vn | total | 17 688 [17 591–17 833] | 17 704 [17 622–17 880] | ×1.001 | tak |
| classic_300x300x300_s100_vn | procWall | 17 827 [17 730–17 985] | 17 841 [17 760–18 031] | ×1.001 | tak |
