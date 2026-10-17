# Test A/B `ab_k3_msvc_ca_classic`

Optymalizacja 3 (przesunięcia liniowe sąsiadów w CA), MSVC — część ca_classic pełnego zestawu (scalona tabela: ab_k3_msvc.md)

- Programy: `przed` = `engine_przed_msvc.exe`, `k2` = `engine_k2_msvc.exe`, `k3` = `engine_k3_msvc.exe`
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 5.3 min, 2026-10-17T19:25
- Tło: start 14% CPU (WmiPrvSE.exe 183%, MsMpEng.exe 53%, svchost.exe 32%), koniec 14%
- Zgodność wyników z `przed`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | przed [ms] | k2 [ms] | k3 [ms] | k2/przed | k3/przed | k3/k2 | zgodne |
|---|---|---|---|---|---|---|---|---|
| classic_1000x1000_s100_vn | caSim | 1 440 [1 415–1 469] | 798 [784–849] | 447 [443–461] | ×0.554 | ×0.310 | ×0.560 | tak |
| classic_1000x1000_s100_vn | save | 133 [131–137] | 133 [132–135] | 135 [133–138] | ×1.001 | ×1.022 | ×1.020 | tak |
| classic_1000x1000_s100_vn | total | 1 599 [1 568–1 627] | 942 [929–996] | 594 [591–610] | ×0.589 | ×0.371 | ×0.630 | tak |
| classic_1000x1000_s100_vn | procWall | 1 613 [1 581–1 640] | 956 [942–1 009] | 607 [603–623] | ×0.593 | ×0.376 | ×0.635 | tak |
| classic_1000x1000_s100_moore | caSim | 1 178 [1 169–1 195] | 730 [714–735] | 380 [372–385] | ×0.620 | ×0.323 | ×0.521 | tak |
| classic_1000x1000_s100_moore | total | 1 329 [1 321–1 346] | 871 [857–876] | 526 [516–534] | ×0.655 | ×0.395 | ×0.604 | tak |
| classic_1000x1000_s100_moore | procWall | 1 343 [1 335–1 360] | 884 [870–889] | 539 [529–548] | ×0.658 | ×0.402 | ×0.610 | tak |
| classic_100x100x100_s10_vn | caSim | 446 [440–469] | 431 [428–440] | 246 [242–300] | ×0.967 | ×0.553 | ×0.571 | tak |
| classic_100x100x100_s10_vn | save | 128 [125–132] | 130 [126–132] | 132 [130–139] | ×1.014 | ×1.033 | ×1.018 | tak |
| classic_100x100x100_s10_vn | total | 587 [579–609] | 575 [569–580] | 389 [384–444] | ×0.978 | ×0.661 | ×0.676 | tak |
| classic_100x100x100_s10_vn | procWall | 601 [592–622] | 587 [582–593] | 402 [397–457] | ×0.978 | ×0.669 | ×0.684 | tak |
| classic_100x100x100_s10_moore | caSim | 606 [598–618] | 661 [649–678] | 342 [336–358] | ×1.091 | ×0.565 | ×0.518 | tak |
| classic_100x100x100_s10_moore | total | 745 [733–757] | 799 [788–818] | 485 [476–504] | ×1.073 | ×0.650 | ×0.606 | tak |
| classic_100x100x100_s10_moore | procWall | 758 [746–769] | 812 [800–830] | 497 [489–518] | ×1.070 | ×0.655 | ×0.612 | tak |
| classic_300x300x300_s100_vn | caSim | 17 640 [17 536–18 007] | 17 473 [17 259–17 529] | 9 724 [9 691–10 044] | ×0.991 | ×0.551 | ×0.557 | tak |
| classic_300x300x300_s100_vn | save | 317 [298–332] | 320 [297–353] | 310 [298–342] | ×1.010 | ×0.980 | ×0.970 | tak |
| classic_300x300x300_s100_vn | total | 18 248 [18 191–18 580] | 18 109 [17 876–18 133] | 10 307 [10 283–10 663] | ×0.992 | ×0.565 | ×0.569 | tak |
| classic_300x300x300_s100_vn | procWall | 18 400 [18 339–18 723] | 18 263 [18 016–18 284] | 10 448 [10 429–10 817] | ×0.993 | ×0.568 | ×0.572 | tak |
