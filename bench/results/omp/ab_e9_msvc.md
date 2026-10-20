# Test A/B `ab_e9_msvc`

Narzut OpenMP przy 1 wątku (etap 9): program po etapie 8 (e8) vs końcowy program etapu 9 (e9) z domyślnym parallel.threads = 1, MSVC.

- Tabela z pomiaru `ab_e9_msvc_ca_lava_raw.csv`, `ab_e9_msvc_ca_classic_raw.csv`, `ab_e9_msvc_mc_reszta_raw.csv`, `ab_e9_msvc_mc_3d_100_raw.csv` (te same przebiegi naprzemienne; programy e8, e9; warunki pomiaru i tło — w nagłówku `ab_e9_msvc_ca_lava.md`, `ab_e9_msvc_ca_classic.md`, `ab_e9_msvc_mc_reszta.md`, `ab_e9_msvc_mc_3d_100.md`)

| Przypadek | miara | e8 [ms] | e9 [ms] | e9/e8 | zgodne |
|---|---|---|---|---|---|
| lava_test_3d | caSim | 96.4 [94.6–103] | 96.2 [95.1–99.7] | ×0.997 | tak |
| lava_test_3d | total | 122 [120–130] | 122 [121–126] | ×1.004 | tak |
| lava_test_3d | procWall | 140 [137–149] | 140 [138–143] | ×1.002 | tak |
| lava_etna_real | caSim | 88.1 [86.8–106] | 88.3 [87.3–94.7] | ×1.002 | tak |
| lava_etna_real | total | 150 [147–179] | 150 [148–155] | ×1.000 | tak |
| lava_etna_real | procWall | 172 [169–202] | 172 [169–185] | ×1.004 | tak |
| lava_mc_2d_ca | caSim | 6.10 [6.05–6.73] | 6.44 [6.20–6.64] | ×1.055 | tak |
| lava_mc_2d_ca | total | 14.6 [13.9–16.1] | 14.8 [13.4–19.1] | ×1.011 | tak |
| lava_mc_2d_ca | procWall | 34.0 [29.7–37.0] | 35.2 [30.9–51.6] | ×1.036 | tak |
| classic_1000x1000_s100_vn | caSim | 120 [116–126] | 121 [117–125] | ×1.007 | tak |
| classic_1000x1000_s100_vn | save | 82.5 [79.9–90.3] | 83.8 [82.3–93.9] | ×1.016 | tak |
| classic_1000x1000_s100_vn | total | 225 [223–232] | 226 [223–232] | ×1.000 | tak |
| classic_1000x1000_s100_vn | procWall | 254 [252–262] | 254 [250–275] | ×1.001 | tak |
| classic_1000x1000_s100_moore | caSim | 129 [127–132] | 128 [126–134] | ×0.998 | tak |
| classic_1000x1000_s100_moore | total | 235 [231–242] | 234 [231–241] | ×0.994 | tak |
| classic_1000x1000_s100_moore | procWall | 266 [260–273] | 264 [260–280] | ×0.994 | tak |
| classic_100x100x100_s10_vn | caSim | 98.7 [97.5–102] | 101 [98.7–106] | ×1.020 | tak |
| classic_100x100x100_s10_vn | save | 80.9 [78.0–82.5] | 82.3 [80.4–86.5] | ×1.018 | tak |
| classic_100x100x100_s10_vn | total | 201 [196–209] | 203 [199–207] | ×1.014 | tak |
| classic_100x100x100_s10_vn | procWall | 232 [224–239] | 232 [229–241] | ×0.998 | tak |
| classic_100x100x100_s10_moore | caSim | 198 [193–217] | 200 [194–219] | ×1.010 | tak |
| classic_100x100x100_s10_moore | total | 303 [298–323] | 304 [299–335] | ×1.005 | tak |
| classic_100x100x100_s10_moore | procWall | 334 [324–356] | 336 [329–364] | ×1.004 | tak |
| classic_300x300x300_s100_vn | caSim | 3 580 [3 530–3 643] | 3 573 [3 540–3 590] | ×0.998 | tak |
| classic_300x300x300_s100_vn | save | 563 [557–576] | 563 [551–590] | ×1.000 | tak |
| classic_300x300x300_s100_vn | total | 4 601 [4 547–4 669] | 4 579 [4 544–4 617] | ×0.995 | tak |
| classic_300x300x300_s100_vn | procWall | 4 918 [4 892–4 984] | 4 884 [4 845–4 929] | ×0.993 | tak |
| mc_full_2d_200 | mcSim | 134 [131–144] | 133 [130–147] | ×0.996 | tak |
| mc_full_2d_200 | mcStats | 18.9 [18.4–20.2] | 18.9 [18.4–20.1] | ×1.002 | tak |
| mc_full_2d_200 | total | 163 [160–175] | 165 [159–178] | ×1.010 | tak |
| mc_full_2d_200 | procWall | 181 [176–199] | 182 [176–195] | ×1.009 | tak |
| mc_full_2d_1000 | mcSim | 9 897 [9 720–10 634] | 9 954 [9 791–10 213] | ×1.006 | tak |
| mc_full_2d_1000 | mcStats | 431 [428–435] | 433 [428–439] | ×1.005 | tak |
| mc_full_2d_1000 | mcSave | 41.1 [39.6–41.4] | 42.5 [41.8–42.8] | ×1.032 | tak |
| mc_full_2d_1000 | total | 10 413 [10 232–11 156] | 10 476 [10 302–10 727] | ×1.006 | tak |
| mc_full_2d_1000 | procWall | 10 430 [10 249–11 172] | 10 499 [10 319–10 745] | ×1.007 | tak |
| mc_full_3d_50 | mcSim | 1 170 [1 117–1 217] | 1 164 [1 133–1 219] | ×0.995 | tak |
| mc_full_3d_50 | mcStats | 287 [283–292] | 287 [285–288] | ×1.002 | tak |
| mc_full_3d_50 | total | 1 485 [1 418–1 527] | 1 469 [1 435–1 524] | ×0.989 | tak |
| mc_full_3d_50 | procWall | 1 506 [1 434–1 551] | 1 487 [1 459–1 542] | ×0.987 | tak |
| mc_full_3d_100 | mcSim | 23 429 [22 926–23 876] | 23 419 [22 939–23 482] | ×1.000 | tak |
| mc_full_3d_100 | mcStats | 1 099 [1 092–1 107] | 1 105 [1 092–1 147] | ×1.006 | tak |
| mc_full_3d_100 | mcSave | 40.4 [40.2–41.5] | 41.3 [41.2–44.6] | ×1.024 | tak |
| mc_full_3d_100 | total | 24 611 [24 100–25 070] | 24 627 [24 125–24 718] | ×1.001 | tak |
| mc_full_3d_100 | procWall | 24 631 [24 119–25 087] | 24 647 [24 143–24 735] | ×1.001 | tak |
| lava_mc_3d | mcSim | 46.2 [45.3–47.6] | 46.6 [45.3–51.2] | ×1.009 | tak |
| lava_mc_3d | caSim | 63.2 [62.5–64.4] | 65.3 [63.7–67.9] | ×1.034 | tak |
| lava_mc_3d | total | 241 [237–255] | 243 [239–261] | ×1.008 | tak |
| lava_mc_3d | procWall | 258 [254–283] | 263 [258–280] | ×1.019 | tak |
