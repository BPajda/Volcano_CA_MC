# Test A/B `ab_e9_gcc`

Narzut OpenMP przy 1 wątku (etap 9): program po etapie 8 (e8) vs końcowy program etapu 9 (e9) z domyślnym parallel.threads = 1, GCC (WSL).

- Tabela z pomiaru `ab_e9_gcc_ca_lava_raw.csv`, `ab_e9_gcc_ca_classic_raw.csv`, `ab_e9_gcc_mc_reszta_raw.csv`, `ab_e9_gcc_mc_3d_100_raw.csv` (te same przebiegi naprzemienne; programy e8, e9; warunki pomiaru i tło — w nagłówku `ab_e9_gcc_ca_lava.md`, `ab_e9_gcc_ca_classic.md`, `ab_e9_gcc_mc_reszta.md`, `ab_e9_gcc_mc_3d_100.md`)

| Przypadek | miara | e8 [ms] | e9 [ms] | e9/e8 | zgodne |
|---|---|---|---|---|---|
| lava_test_3d | caSim | 94.4 [92.2–97.3] | 96.6 [95.3–99.8] | ×1.023 | tak |
| lava_test_3d | total | 107 [104–112] | 110 [108–113] | ×1.022 | tak |
| lava_test_3d | procWall | 110 [107–115] | 112 [111–116] | ×1.024 | tak |
| lava_etna_real | caSim | 86.1 [83.5–94.6] | 89.1 [86.7–92.3] | ×1.035 | tak |
| lava_etna_real | total | 137 [131–159] | 139 [134–165] | ×1.011 | tak |
| lava_etna_real | procWall | 142 [136–164] | 144 [138–169] | ×1.014 | tak |
| lava_mc_2d_ca | caSim | 6.12 [5.96–6.95] | 6.26 [6.08–6.41] | ×1.023 | tak |
| lava_mc_2d_ca | total | 8.38 [8.16–9.12] | 8.54 [8.25–8.72] | ×1.018 | tak |
| lava_mc_2d_ca | procWall | 10.6 [10.3–11.3] | 10.8 [10.4–11.2] | ×1.021 | tak |
| classic_1000x1000_s100_vn | caSim | 122 [108–129] | 117 [108–123] | ×0.961 | tak |
| classic_1000x1000_s100_vn | save | 51.1 [43.9–69.8] | 56.4 [46.3–70.3] | ×1.103 | tak |
| classic_1000x1000_s100_vn | total | 200 [171–284] | 198 [174–213] | ×0.993 | tak |
| classic_1000x1000_s100_vn | procWall | 216 [185–300] | 215 [188–228] | ×0.996 | tak |
| classic_1000x1000_s100_moore | caSim | 128 [118–134] | 123 [115–132] | ×0.965 | tak |
| classic_1000x1000_s100_moore | total | 196 [183–208] | 199 [182–205] | ×1.014 | tak |
| classic_1000x1000_s100_moore | procWall | 213 [197–224] | 215 [196–222] | ×1.008 | tak |
| classic_100x100x100_s10_vn | caSim | 99.1 [90.0–184] | 96.2 [91.0–216] | ×0.970 | tak |
| classic_100x100x100_s10_vn | save | 48.5 [41.9–64.5] | 47.0 [43.6–65.5] | ×0.969 | tak |
| classic_100x100x100_s10_vn | total | 168 [150–264] | 163 [153–300] | ×0.968 | tak |
| classic_100x100x100_s10_vn | procWall | 185 [165–280] | 180 [168–317] | ×0.975 | tak |
| classic_100x100x100_s10_moore | caSim | 193 [174–271] | 193 [180–261] | ×1.001 | tak |
| classic_100x100x100_s10_moore | total | 260 [236–349] | 263 [244–342] | ×1.012 | tak |
| classic_100x100x100_s10_moore | procWall | 277 [252–364] | 280 [260–357] | ×1.010 | tak |
| classic_300x300x300_s100_vn | caSim | 3 761 [3 702–3 883] | 3 635 [3 551–3 709] | ×0.966 | tak |
| classic_300x300x300_s100_vn | save | 649 [627–865] | 710 [616–808] | ×1.094 | tak |
| classic_300x300x300_s100_vn | total | 4 984 [4 898–5 076] | 4 856 [4 579–4 898] | ×0.974 | tak |
| classic_300x300x300_s100_vn | procWall | 5 345 [5 255–5 434] | 5 215 [4 916–5 273] | ×0.976 | tak |
| mc_full_2d_200 | mcSim | 123 [121–128] | 123 [120–129] | ×1.000 | tak |
| mc_full_2d_200 | mcStats | 15.8 [15.4–16.3] | 15.7 [15.2–16.6] | ×0.994 | tak |
| mc_full_2d_200 | total | 142 [139–147] | 141 [138–148] | ×0.998 | tak |
| mc_full_2d_200 | procWall | 143 [141–149] | 144 [140–150] | ×1.002 | tak |
| mc_full_2d_1000 | mcSim | 9 168 [8 909–9 741] | 9 133 [8 936–10 022] | ×0.996 | tak |
| mc_full_2d_1000 | mcStats | 395 [389–396] | 395 [393–400] | ×1.000 | tak |
| mc_full_2d_1000 | mcSave | 21.8 [20.5–25.3] | 21.6 [20.1–25.1] | ×0.992 | tak |
| mc_full_2d_1000 | total | 9 619 [9 353–10 189] | 9 580 [9 376–10 467] | ×0.996 | tak |
| mc_full_2d_1000 | procWall | 9 622 [9 355–10 191] | 9 582 [9 379–10 470] | ×0.996 | tak |
| mc_full_3d_50 | mcSim | 1 088 [1 079–1 130] | 1 086 [1 073–1 120] | ×0.998 | tak |
| mc_full_3d_50 | mcStats | 241 [236–243] | 235 [232–245] | ×0.977 | tak |
| mc_full_3d_50 | total | 1 336 [1 323–1 380] | 1 329 [1 316–1 363] | ×0.995 | tak |
| mc_full_3d_50 | procWall | 1 338 [1 326–1 382] | 1 331 [1 318–1 365] | ×0.995 | tak |
| mc_full_3d_100 | mcSim | 21 212 [20 878–21 815] | 21 465 [21 148–21 608] | ×1.012 | tak |
| mc_full_3d_100 | mcStats | 940 [940–978] | 937 [926–991] | ×0.996 | tak |
| mc_full_3d_100 | mcSave | 21.0 [19.0–23.5] | 21.9 [18.7–23.3] | ×1.044 | tak |
| mc_full_3d_100 | total | 22 205 [21 867–22 811] | 22 448 [22 124–22 646] | ×1.011 | tak |
| mc_full_3d_100 | procWall | 22 208 [21 869–22 816] | 22 451 [22 127–22 648] | ×1.011 | tak |
| lava_mc_3d | mcSim | 41.5 [40.8–43.9] | 41.5 [41.0–42.2] | ×1.001 | tak |
| lava_mc_3d | caSim | 57.6 [56.9–59.7] | 59.5 [57.4–61.2] | ×1.033 | tak |
| lava_mc_3d | total | 165 [161–168] | 165 [162–171] | ×1.005 | tak |
| lava_mc_3d | procWall | 167 [164–170] | 168 [165–174] | ×1.005 | tak |
