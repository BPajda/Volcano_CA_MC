# Test A/B `ab_k5_msvc_ca`

Optymalizacja 5 (tańsze statystyki MC), MSVC, taktowanie bazowe — kontrola CA: k5 nie zmienia kodu automatu (układ kodu)

- Programy: `k4` = `engine_k4_msvc.exe`, `k5` = `engine_k5_msvc.exe`
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 1.6 min, 2026-10-17T22:08
- Tło: start 23% CPU (WmiPrvSE.exe 224%, inny program 52%, svchost.exe 47%), koniec 22%
- Zgodność wyników z `k4`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | k4 [ms] | k5 [ms] | k5/k4 | zgodne |
|---|---|---|---|---|---|
| lava_test_3d | caSim | 95.7 [93.0–99.3] | 95.0 [92.3–96.9] | ×0.993 | tak |
| lava_test_3d | total | 167 [158–175] | 164 [157–176] | ×0.979 | tak |
| lava_test_3d | procWall | 185 [177–193] | 183 [172–208] | ×0.991 | tak |
| lava_etna_real | caSim | 86.7 [85.0–89.2] | 87.7 [85.9–89.1] | ×1.011 | tak |
| lava_etna_real | total | 151 [145–171] | 150 [147–151] | ×0.991 | tak |
| lava_etna_real | procWall | 170 [167–197] | 171 [167–175] | ×1.001 | tak |
| lava_mc_2d_ca | caSim | 6.07 [5.85–7.05] | 6.13 [5.86–6.29] | ×1.010 | tak |
| lava_mc_2d_ca | total | 18.5 [17.7–28.6] | 18.4 [17.3–28.0] | ×0.996 | tak |
| lava_mc_2d_ca | procWall | 39.4 [33.5–51.5] | 36.8 [32.9–46.4] | ×0.932 | tak |
| classic_1000x1000_s100_vn | caSim | 120 [115–122] | 120 [115–123] | ×1.002 | tak |
| classic_1000x1000_s100_vn | save | 322 [316–333] | 312 [310–323] | ×0.968 | tak |
| classic_1000x1000_s100_vn | total | 465 [453–474] | 453 [445–465] | ×0.975 | tak |
| classic_1000x1000_s100_vn | procWall | 493 [481–502] | 487 [473–493] | ×0.988 | tak |
| classic_1000x1000_s100_moore | caSim | 128 [126–134] | 128 [124–131] | ×1.000 | tak |
| classic_1000x1000_s100_moore | total | 472 [451–479] | 462 [451–529] | ×0.979 | tak |
| classic_1000x1000_s100_moore | procWall | 503 [481–507] | 491 [483–561] | ×0.976 | tak |
| classic_100x100x100_s10_vn | caSim | 98.8 [96.6–116] | 96.6 [92.4–121] | ×0.978 | tak |
| classic_100x100x100_s10_vn | save | 312 [300–343] | 305 [292–317] | ×0.981 | tak |
| classic_100x100x100_s10_vn | total | 433 [417–482] | 423 [408–461] | ×0.977 | tak |
| classic_100x100x100_s10_vn | procWall | 462 [449–517] | 453 [434–489] | ×0.980 | tak |
| classic_100x100x100_s10_moore | caSim | 196 [188–250] | 197 [190–232] | ×1.004 | tak |
| classic_100x100x100_s10_moore | total | 529 [507–594] | 525 [505–573] | ×0.993 | tak |
| classic_100x100x100_s10_moore | procWall | 571 [540–634] | 555 [532–599] | ×0.973 | tak |
| classic_300x300x300_s100_vn | caSim | 3 515 [3 467–3 562] | 3 464 [3 406–3 569] | ×0.985 | tak |
| classic_300x300x300_s100_vn | save | 567 [555–609] | 561 [558–571] | ×0.989 | tak |
| classic_300x300x300_s100_vn | total | 4 533 [4 484–4 636] | 4 483 [4 427–4 599] | ×0.989 | tak |
| classic_300x300x300_s100_vn | procWall | 4 840 [4 795–4 993] | 4 797 [4 739–4 908] | ×0.991 | tak |
