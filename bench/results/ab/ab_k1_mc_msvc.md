# Test A/B `ab_k1_mc_msvc`

Optymalizacja 1 (MC: liczenie sąsiadów bez skoku, energia przed i po w jednym przejściu, stała część hashRand przed pętlą), MSVC

- Programy: `przed` = `engine_przed_msvc.exe`, `k1` = `engine_k1_msvc.exe`
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 3.6 min, 2026-10-17T08:31
- Tło: start 13% CPU (WmiPrvSE.exe 194%, svchost.exe 38%, python.exe 26%), koniec 14%
- Zgodność wyników z `przed`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | przed [ms] | k1 [ms] | k1/przed | zgodne |
|---|---|---|---|---|---|
| mc_full_2d_200 | mcSim | 145 [143–150] | 53.6 [52.1–54.7] | ×0.369 | tak |
| mc_full_2d_200 | mcStats | 12.6 [12.4–12.9] | 10.2 [9.89–10.3] | ×0.812 | tak |
| mc_full_2d_200 | total | 165 [163–169] | 70.6 [68.9–71.6] | ×0.429 | tak |
| mc_full_2d_200 | procWall | 172 [170–176] | 78.0 [76.0–79.1] | ×0.453 | tak |
| mc_full_2d_1000 | mcSim | 6 110 [6 087–6 286] | 3 186 [2 723–3 289] | ×0.521 | tak |
| mc_full_2d_1000 | mcStats | 316 [315–324] | 246 [246–249] | ×0.777 | tak |
| mc_full_2d_1000 | mcSave | 54.8 [54.0–55.7] | 54.4 [53.6–63.0] | ×0.993 | tak |
| mc_full_2d_1000 | total | 6 502 [6 476–6 677] | 3 510 [3 051–3 612] | ×0.540 | tak |
| mc_full_2d_1000 | procWall | 6 510 [6 484–6 684] | 3 517 [3 058–3 619] | ×0.540 | tak |
| mc_full_3d_50 | mcSim | 1 319 [1 312–1 326] | 450 [446–499] | ×0.341 | tak |
| mc_full_3d_50 | mcStats | 347 [346–350] | 222 [220–266] | ×0.639 | tak |
| mc_full_3d_50 | total | 1 680 [1 670–1 693] | 684 [678–779] | ×0.407 | tak |
| mc_full_3d_50 | procWall | 1 687 [1 678–1 701] | 691 [685–786] | ×0.410 | tak |
| mc_full_3d_100 | mcSim | 15 219 [14 962–16 042] | 6 773 [6 684–7 407] | ×0.445 | tak |
| mc_full_3d_100 | mcStats | 1 421 [1 408–1 439] | 922 [917–938] | ×0.649 | tak |
| mc_full_3d_100 | mcSave | 52.2 [51.3–54.4] | 53.2 [51.4–57.7] | ×1.019 | tak |
| mc_full_3d_100 | total | 16 706 [16 453–17 535] | 7 771 [7 670–8 395] | ×0.465 | tak |
| mc_full_3d_100 | procWall | 16 715 [16 460–17 543] | 7 778 [7 677–8 402] | ×0.465 | tak |
| lava_mc_3d | mcSim | 75.2 [74.6–76.2] | 18.6 [18.4–18.7] | ×0.247 | tak |
| lava_mc_3d | caSim | 1 114 [1 110–1 135] | 1 123 [1 104–1 130] | ×1.008 | tak |
| lava_mc_3d | total | 1 296 [1 290–1 320] | 1 241 [1 221–1 249] | ×0.958 | tak |
| lava_mc_3d | procWall | 1 304 [1 298–1 328] | 1 250 [1 229–1 257] | ×0.958 | tak |
