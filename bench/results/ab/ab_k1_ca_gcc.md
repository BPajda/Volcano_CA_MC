# Test A/B `ab_k1_ca_gcc`

Optymalizacja 1 (zmiana tylko w MC) — przypadki CA, GCC: kolumny przed i k1 z pomiaru ab_k2_gcc

- Tabela z pomiaru `ab_k2_gcc_raw.csv` (te same przebiegi naprzemienne; programy przed, k1; warunki pomiaru i tło — w nagłówku `ab_k2_gcc.md`)

| Przypadek | miara | przed [ms] | k1 [ms] | k1/przed | zgodne |
|---|---|---|---|---|---|
| lava_test_3d | caSim | 1 233 [1 210–1 413] | 1 235 [1 214–1 380] | ×1.002 | tak |
| lava_test_3d | total | 1 255 [1 232–1 441] | 1 258 [1 236–1 409] | ×1.003 | tak |
| lava_test_3d | procWall | 1 256 [1 233–1 443] | 1 259 [1 237–1 410] | ×1.003 | tak |
| lava_etna_real | caSim | 10 781 [10 597–12 313] | 10 764 [10 597–11 643] | ×0.998 | tak |
| lava_etna_real | total | 10 813 [10 630–12 351] | 10 793 [10 626–11 673] | ×0.998 | tak |
| lava_etna_real | procWall | 10 815 [10 632–12 354] | 10 795 [10 628–11 675] | ×0.998 | tak |
| lava_mc_2d_ca | caSim | 41.3 [37.8–46.8] | 41.1 [39.2–42.9] | ×0.994 | tak |
| lava_mc_2d_ca | total | 43.7 [40.3–49.4] | 43.6 [41.8–46.9] | ×0.997 | tak |
| lava_mc_2d_ca | procWall | 44.8 [41.1–50.4] | 44.5 [42.8–47.9] | ×0.995 | tak |
| classic_1000x1000_s100_vn | caSim | 1 153 [1 134–1 193] | 1 151 [1 126–1 206] | ×0.998 | tak |
| classic_1000x1000_s100_vn | save | 108 [100–116] | 107 [98.1–125] | ×0.988 | tak |
| classic_1000x1000_s100_vn | total | 1 276 [1 258–1 327] | 1 283 [1 239–1 345] | ×1.006 | tak |
| classic_1000x1000_s100_vn | procWall | 1 282 [1 264–1 333] | 1 289 [1 245–1 351] | ×1.005 | tak |
| classic_1000x1000_s100_moore | caSim | 987 [959–998] | 973 [952–1 021] | ×0.985 | tak |
| classic_1000x1000_s100_moore | total | 1 106 [1 078–1 117] | 1 088 [1 065–1 139] | ×0.984 | tak |
| classic_1000x1000_s100_moore | procWall | 1 112 [1 084–1 123] | 1 094 [1 071–1 146] | ×0.984 | tak |
| classic_100x100x100_s10_vn | caSim | 382 [360–396] | 382 [366–415] | ×0.999 | tak |
| classic_100x100x100_s10_vn | save | 104 [97.8–113] | 102 [99.0–105] | ×0.979 | tak |
| classic_100x100x100_s10_vn | total | 499 [467–511] | 491 [475–528] | ×0.984 | tak |
| classic_100x100x100_s10_vn | procWall | 505 [474–517] | 497 [481–535] | ×0.984 | tak |
| classic_100x100x100_s10_moore | caSim | 549 [538–560] | 537 [516–548] | ×0.977 | tak |
| classic_100x100x100_s10_moore | total | 663 [649–677] | 651 [624–668] | ×0.982 | tak |
| classic_100x100x100_s10_moore | procWall | 669 [655–683] | 658 [631–675] | ×0.983 | tak |
| classic_300x300x300_s100_vn | caSim | 15 217 [15 065–15 772] | 15 280 [15 019–17 612] | ×1.004 | tak |
| classic_300x300x300_s100_vn | save | 294 [246–387] | 269 [251–349] | ×0.914 | tak |
| classic_300x300x300_s100_vn | total | 15 804 [15 532–16 479] | 15 770 [15 474–18 178] | ×0.998 | tak |
| classic_300x300x300_s100_vn | procWall | 15 943 [15 665–16 622] | 15 909 [15 608–18 317] | ×0.998 | tak |
