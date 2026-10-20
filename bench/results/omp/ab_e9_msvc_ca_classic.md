# Test A/B `ab_e9_msvc_ca_classic`

- Programy: `e8` = `engine_e8_msvc.exe`, `e9` = `engine_e9_msvc.exe`
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 1.3 min, 2026-10-18T05:15
- Tło: start 23% CPU (WmiPrvSE.exe 217%, inny program 79%, python.exe 46%), koniec 22%
- Zgodność wyników z `e8`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e8 [ms] | e9 [ms] | e9/e8 | zgodne |
|---|---|---|---|---|---|
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
