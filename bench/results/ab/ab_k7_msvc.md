# Test A/B `ab_k7_msvc`

Optymalizacja 7 (zapis plików tekstowych wyników ca_result.txt / mc_result.txt), MSVC, tryb oszczędny (bez turbo); k5 = poprzedni przyjęty krok (zapis bez zmian od stanu przed etapem 8)

- Tabela z pomiaru `ab_k7_msvc_ca_raw.csv`, `ab_k7_msvc_mc_raw.csv` (te same przebiegi naprzemienne; programy k5, k7; warunki pomiaru i tło — w nagłówku `ab_k7_msvc_ca.md`, `ab_k7_msvc_mc.md`)

| Przypadek | miara | k5 [ms] | k7 [ms] | k7/k5 | zgodne |
|---|---|---|---|---|---|
| lava_test_3d | caSim | 95.9 [93.5–98.6] | 94.9 [94.1–97.0] | ×0.990 | tak |
| lava_test_3d | total | 165 [161–172] | 120 [119–125] | ×0.729 | tak |
| lava_test_3d | procWall | 184 [179–196] | 139 [136–145] | ×0.760 | tak |
| lava_etna_real | caSim | 86.8 [85.6–88.0] | 87.8 [85.6–91.5] | ×1.011 | tak |
| lava_etna_real | total | 150 [147–173] | 149 [147–158] | ×0.995 | tak |
| lava_etna_real | procWall | 169 [167–196] | 171 [166–181] | ×1.011 | tak |
| lava_mc_2d_ca | caSim | 6.00 [5.92–6.76] | 6.05 [5.91–6.74] | ×1.008 | tak |
| lava_mc_2d_ca | total | 18.0 [17.1–26.5] | 14.3 [13.0–15.2] | ×0.795 | tak |
| lava_mc_2d_ca | procWall | 35.8 [31.9–45.5] | 33.1 [28.8–37.9] | ×0.923 | tak |
| classic_1000x1000_s100_vn | caSim | 118 [116–168] | 119 [117–121] | ×1.010 | tak |
| classic_1000x1000_s100_vn | save | 299 [290–320] | 81.9 [80.5–85.3] | ×0.274 | tak |
| classic_1000x1000_s100_vn | total | 437 [428–507] | 221 [218–225] | ×0.506 | tak |
| classic_1000x1000_s100_vn | procWall | 466 [455–539] | 252 [247–258] | ×0.540 | tak |
| classic_1000x1000_s100_moore | caSim | 128 [125–131] | 128 [126–129] | ×0.994 | tak |
| classic_1000x1000_s100_moore | total | 461 [441–510] | 234 [228–235] | ×0.508 | tak |
| classic_1000x1000_s100_moore | procWall | 492 [473–538] | 263 [256–269] | ×0.535 | tak |
| classic_100x100x100_s10_vn | caSim | 95.8 [94.4–99.7] | 96.9 [94.9–141] | ×1.011 | tak |
| classic_100x100x100_s10_vn | save | 298 [291–307] | 80.2 [78.4–101] | ×0.269 | tak |
| classic_100x100x100_s10_vn | total | 414 [408–423] | 197 [193–261] | ×0.476 | tak |
| classic_100x100x100_s10_vn | procWall | 442 [439–465] | 227 [219–288] | ×0.514 | tak |
| classic_100x100x100_s10_moore | caSim | 193 [191–204] | 195 [192–200] | ×1.007 | tak |
| classic_100x100x100_s10_moore | total | 517 [509–541] | 298 [293–317] | ×0.577 | tak |
| classic_100x100x100_s10_moore | procWall | 550 [538–567] | 332 [319–354] | ×0.603 | tak |
| classic_300x300x300_s100_vn | caSim | 3 544 [3 508–3 600] | 3 525 [3 430–3 614] | ×0.995 | tak |
| classic_300x300x300_s100_vn | save | 582 [573–616] | 571 [552–578] | ×0.982 | tak |
| classic_300x300x300_s100_vn | total | 4 600 [4 546–4 654] | 4 541 [4 440–4 649] | ×0.987 | tak |
| classic_300x300x300_s100_vn | procWall | 4 907 [4 862–4 969] | 4 855 [4 783–4 960] | ×0.989 | tak |
| mc_full_2d_200 | mcSim | 132 [129–133] | 131 [130–136] | ×0.999 | tak |
| mc_full_2d_200 | mcStats | 18.2 [17.9–18.7] | 18.5 [18.1–20.2] | ×1.016 | tak |
| mc_full_2d_200 | total | 164 [162–170] | 160 [158–166] | ×0.977 | tak |
| mc_full_2d_200 | procWall | 182 [177–188] | 179 [174–189] | ×0.984 | tak |
| mc_full_2d_1000 | mcSim | 9 376 [9 179–10 695] | 9 564 [9 235–10 214] | ×1.020 | tak |
| mc_full_2d_1000 | mcStats | 429 [427–438] | 438 [427–442] | ×1.019 | tak |
| mc_full_2d_1000 | mcSave | 129 [122–146] | 42.6 [40.6–44.3] | ×0.330 | tak |
| mc_full_2d_1000 | total | 9 989 [9 801–11 291] | 10 088 [9 741–10 737] | ×1.010 | tak |
| mc_full_2d_1000 | procWall | 10 006 [9 817–11 308] | 10 105 [9 757–10 756] | ×1.010 | tak |
| mc_full_3d_50 | mcSim | 1 135 [1 109–1 240] | 1 139 [1 114–1 187] | ×1.003 | tak |
| mc_full_3d_50 | mcStats | 270 [266–294] | 285 [282–293] | ×1.057 | tak |
| mc_full_3d_50 | total | 1 432 [1 404–1 565] | 1 441 [1 413–1 497] | ×1.006 | tak |
| mc_full_3d_50 | procWall | 1 453 [1 423–1 582] | 1 461 [1 432–1 515] | ×1.006 | tak |
| mc_full_3d_100 | mcSim | 22 596 [22 568–24 034] | 22 606 [22 271–22 887] | ×1.000 | tak |
| mc_full_3d_100 | mcStats | 1 037 [1 035–1 046] | 1 098 [1 094–1 111] | ×1.059 | tak |
| mc_full_3d_100 | mcSave | 123 [120–124] | 40.2 [39.5–40.5] | ×0.327 | tak |
| mc_full_3d_100 | total | 23 802 [23 773–25 243] | 23 781 [23 447–24 076] | ×0.999 | tak |
| mc_full_3d_100 | procWall | 23 822 [23 788–25 260] | 23 811 [23 463–24 093] | ×1.000 | tak |
| lava_mc_3d | mcSim | 46.7 [45.2–48.0] | 45.8 [44.8–56.4] | ×0.981 | tak |
| lava_mc_3d | caSim | 61.9 [61.6–63.5] | 62.8 [61.1–65.4] | ×1.014 | tak |
| lava_mc_3d | total | 332 [323–337] | 238 [233–267] | ×0.717 | tak |
| lava_mc_3d | procWall | 351 [341–359] | 264 [251–288] | ×0.752 | tak |
