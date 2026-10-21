# Test A/B `ab_e10_msvc_ca_classic`

- Programy: `e9` = `engine_e9_msvc.exe`, `e10` = `engine_e10_msvc.exe`
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 1.3 min, 2026-10-20T14:11
- Tło: start 22% CPU (WmiPrvSE.exe 208%, System 84%, python.exe 41%), koniec 18%
- Zgodność wyników z `e9`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e9 [ms] | e10 [ms] | e10/e9 | zgodne |
|---|---|---|---|---|---|
| classic_1000x1000_s100_vn | caSim | 118 [116–119] | 118 [116–132] | ×1.001 | tak |
| classic_1000x1000_s100_vn | save | 83.6 [82.6–84.6] | 81.9 [80.6–86.4] | ×0.980 | tak |
| classic_1000x1000_s100_vn | total | 222 [220–224] | 221 [217–241] | ×0.996 | tak |
| classic_1000x1000_s100_vn | procWall | 253 [248–264] | 253 [247–275] | ×1.002 | tak |
| classic_1000x1000_s100_moore | caSim | 128 [125–133] | 129 [126–134] | ×1.007 | tak |
| classic_1000x1000_s100_moore | total | 234 [229–238] | 232 [229–241] | ×0.994 | tak |
| classic_1000x1000_s100_moore | procWall | 265 [260–271] | 264 [258–275] | ×0.995 | tak |
| classic_100x100x100_s10_vn | caSim | 98.2 [96.0–99.6] | 98.3 [95.9–101] | ×1.001 | tak |
| classic_100x100x100_s10_vn | save | 81.5 [79.9–82.6] | 80.1 [78.0–82.1] | ×0.982 | tak |
| classic_100x100x100_s10_vn | total | 201 [196–202] | 199 [194–201] | ×0.991 | tak |
| classic_100x100x100_s10_vn | procWall | 231 [223–236] | 231 [224–241] | ×1.000 | tak |
| classic_100x100x100_s10_moore | caSim | 197 [193–209] | 205 [198–223] | ×1.042 | tak |
| classic_100x100x100_s10_moore | total | 301 [298–321] | 307 [298–332] | ×1.021 | tak |
| classic_100x100x100_s10_moore | procWall | 334 [327–356] | 341 [327–361] | ×1.021 | tak |
| classic_300x300x300_s100_vn | caSim | 3 458 [3 423–3 493] | 3 477 [3 462–3 527] | ×1.005 | tak |
| classic_300x300x300_s100_vn | save | 574 [563–657] | 573 [561–585] | ×0.998 | tak |
| classic_300x300x300_s100_vn | total | 4 471 [4 430–4 582] | 4 491 [4 470–4 533] | ×1.005 | tak |
| classic_300x300x300_s100_vn | procWall | 4 771 [4 727–4 878] | 4 808 [4 763–4 834] | ×1.008 | tak |
