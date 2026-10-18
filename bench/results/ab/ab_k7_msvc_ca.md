# Test A/B `ab_k7_msvc_ca`

Optymalizacja 7 (zapis plików tekstowych wyników), MSVC, tryb oszczędny (bez turbo) — grupy CA (scalona tabela: ab_k7_msvc.md)

- Programy: `k5` = `engine_k5_msvc.exe`, `k7` = `engine_k7_msvc.exe`
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 1.5 min, 2026-10-17T22:37
- Tło: start 21% CPU (WmiPrvSE.exe 236%, python.exe 42%, inny program 42%), koniec 20%
- Zgodność wyników z `k5`: wszystkie przebiegi bitowo zgodne

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
