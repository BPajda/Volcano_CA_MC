# Test A/B `ab_k5_gcc_ca`

Optymalizacja 5 (tańsze statystyki MC), GCC, tryb oszczędny (bez turbo) — kontrola CA: k5 nie zmienia kodu automatu

- Programy: `k4` = `engine_k4`, `k5` = `engine_k5`
- Przypięcie: sched_setaffinity({2}) (WSL2: procesor wirtualny); priorytet: domyślny; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 1.4 min, 2026-10-17T22:22
- Zgodność wyników z `k4`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | k4 [ms] | k5 [ms] | k5/k4 | zgodne |
|---|---|---|---|---|---|
| lava_test_3d | caSim | 84.8 [83.7–93.0] | 85.6 [83.7–88.1] | ×1.009 | tak |
| lava_test_3d | total | 135 [134–143] | 137 [134–139] | ×1.017 | tak |
| lava_test_3d | procWall | 138 [136–146] | 140 [136–141] | ×1.013 | tak |
| lava_etna_real | caSim | 78.6 [77.1–79.2] | 78.4 [76.9–79.4] | ×0.997 | tak |
| lava_etna_real | total | 122 [121–145] | 123 [119–145] | ×1.008 | tak |
| lava_etna_real | procWall | 126 [125–149] | 127 [123–149] | ×1.007 | tak |
| lava_mc_2d_ca | caSim | 5.50 [5.29–5.90] | 5.43 [5.39–10.2] | ×0.987 | tak |
| lava_mc_2d_ca | total | 10.7 [10.4–11.4] | 10.7 [10.5–18.7] | ×1.001 | tak |
| lava_mc_2d_ca | procWall | 12.8 [12.3–13.3] | 12.7 [12.3–22.4] | ×0.993 | tak |
| classic_1000x1000_s100_vn | caSim | 109 [107–208] | 109 [106–113] | ×1.003 | tak |
| classic_1000x1000_s100_vn | save | 243 [232–346] | 243 [233–329] | ×1.000 | tak |
| classic_1000x1000_s100_vn | total | 395 [362–474] | 373 [358–455] | ×0.945 | tak |
| classic_1000x1000_s100_vn | procWall | 408 [376–489] | 387 [371–469] | ×0.948 | tak |
| classic_1000x1000_s100_moore | caSim | 114 [111–118] | 115 [111–209] | ×1.002 | tak |
| classic_1000x1000_s100_moore | total | 367 [363–385] | 381 [365–498] | ×1.038 | tak |
| classic_1000x1000_s100_moore | procWall | 381 [377–399] | 394 [379–512] | ×1.036 | tak |
| classic_100x100x100_s10_vn | caSim | 89.7 [87.2–91.1] | 88.3 [85.0–94.9] | ×0.983 | tak |
| classic_100x100x100_s10_vn | save | 234 [232–246] | 237 [233–337] | ×1.015 | tak |
| classic_100x100x100_s10_vn | total | 342 [339–352] | 346 [339–440] | ×1.012 | tak |
| classic_100x100x100_s10_vn | procWall | 356 [354–368] | 361 [354–455] | ×1.013 | tak |
| classic_100x100x100_s10_moore | caSim | 176 [173–270] | 174 [169–262] | ×0.985 | tak |
| classic_100x100x100_s10_moore | total | 441 [423–547] | 442 [422–530] | ×1.002 | tak |
| classic_100x100x100_s10_moore | procWall | 456 [438–563] | 457 [437–545] | ×1.002 | tak |
| classic_300x300x300_s100_vn | caSim | 3 375 [3 319–3 514] | 3 428 [3 336–3 497] | ×1.016 | tak |
| classic_300x300x300_s100_vn | save | 620 [531–762] | 593 [549–715] | ×0.956 | tak |
| classic_300x300x300_s100_vn | total | 4 510 [4 306–4 742] | 4 429 [4 285–4 615] | ×0.982 | tak |
| classic_300x300x300_s100_vn | procWall | 4 840 [4 633–5 083] | 4 753 [4 610–4 962] | ×0.982 | tak |

Tło (Windows, poza WSL): start 18% (WmiPrvSE.exe 215%, python.exe 46%, inny program 40%), koniec 14%.
