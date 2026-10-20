# Test A/B `ab_e9b_t1_msvc_ca_classic`

- Programy: `e8` = `engine_e8_msvc.exe`, `e9b` = `engine_e9b_msvc.exe`
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 1.3 min, 2026-10-18T03:57
- Tło: start 28% CPU (WmiPrvSE.exe 245%, inny program 99%, inny program 80%), koniec 24%
- Zgodność wyników z `e8`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e8 [ms] | e9b [ms] | e9b/e8 | zgodne |
|---|---|---|---|---|---|
| classic_1000x1000_s100_vn | caSim | 123 [119–132] | 123 [119–150] | ×0.998 | tak |
| classic_1000x1000_s100_vn | save | 82.5 [78.2–112] | 81.3 [79.1–84.3] | ×0.986 | tak |
| classic_1000x1000_s100_vn | total | 226 [223–273] | 229 [223–255] | ×1.013 | tak |
| classic_1000x1000_s100_vn | procWall | 258 [254–315] | 262 [252–289] | ×1.014 | tak |
| classic_1000x1000_s100_moore | caSim | 134 [130–143] | 133 [129–146] | ×0.997 | tak |
| classic_1000x1000_s100_moore | total | 242 [235–251] | 239 [232–265] | ×0.990 | tak |
| classic_1000x1000_s100_moore | procWall | 271 [263–283] | 278 [264–303] | ×1.025 | tak |
| classic_100x100x100_s10_vn | caSim | 98.2 [96.3–101] | 102 [99.3–108] | ×1.039 | tak |
| classic_100x100x100_s10_vn | save | 79.7 [77.8–84.2] | 78.3 [76.8–84.8] | ×0.983 | tak |
| classic_100x100x100_s10_vn | total | 199 [195–205] | 203 [200–213] | ×1.018 | tak |
| classic_100x100x100_s10_vn | procWall | 230 [223–238] | 234 [228–246] | ×1.016 | tak |
| classic_100x100x100_s10_moore | caSim | 198 [192–229] | 214 [212–226] | ×1.082 | tak |
| classic_100x100x100_s10_moore | total | 306 [293–330] | 316 [313–328] | ×1.034 | tak |
| classic_100x100x100_s10_moore | procWall | 335 [321–363] | 348 [343–371] | ×1.039 | tak |
| classic_300x300x300_s100_vn | caSim | 3 601 [3 580–3 763] | 3 615 [3 524–3 719] | ×1.004 | tak |
| classic_300x300x300_s100_vn | save | 567 [555–589] | 574 [560–580] | ×1.013 | tak |
| classic_300x300x300_s100_vn | total | 4 632 [4 623–4 774] | 4 782 [4 593–4 826] | ×1.032 | tak |
| classic_300x300x300_s100_vn | procWall | 4 952 [4 940–5 084] | 5 128 [4 908–5 183] | ×1.035 | tak |
