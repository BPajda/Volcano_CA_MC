# Test A/B `ab_e9_msvc_mc_3d_100`

- Programy: `e8` = `engine_e8_msvc.exe`, `e9` = `engine_e9_msvc.exe`
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 4.2 min, 2026-10-18T05:22
- Tło: start 21% CPU (WmiPrvSE.exe 231%, inny program 70%, python.exe 41%), koniec 18%
- Zgodność wyników z `e8`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e8 [ms] | e9 [ms] | e9/e8 | zgodne |
|---|---|---|---|---|---|
| mc_full_3d_100 | mcSim | 23 429 [22 926–23 876] | 23 419 [22 939–23 482] | ×1.000 | tak |
| mc_full_3d_100 | mcStats | 1 099 [1 092–1 107] | 1 105 [1 092–1 147] | ×1.006 | tak |
| mc_full_3d_100 | mcSave | 40.4 [40.2–41.5] | 41.3 [41.2–44.6] | ×1.024 | tak |
| mc_full_3d_100 | total | 24 611 [24 100–25 070] | 24 627 [24 125–24 718] | ×1.001 | tak |
| mc_full_3d_100 | procWall | 24 631 [24 119–25 087] | 24 647 [24 143–24 735] | ×1.001 | tak |
