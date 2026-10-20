# Skalowanie OpenMP `skalowanie_gcc_cz2`

- Program: `engine`; wiązanie libgomp OMP_PROC_BIND=close, OMP_PLACES=cores (`parallel.affinity = none`); priorytet domyślny; warianty naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 3.9 min, 2026-10-20T05:25
- Zgodność wyników z p = 1 (albo z pierwszym harmonogramem): wszystkie przebiegi bitowo zgodne

| Przypadek | p | total [ms] | S | E | faza [ms] | S fazy | E fazy | zgodne |
|---|---|---|---|---|---|---|---|---|
| classic_2000x2000_s400_vn | 1 | 636 [591–646] | 1.00 | 1.00 | 491 [444–511] | 1.00 | 1.00 | tak |
| classic_2000x2000_s400_vn | 2 | 349 [335–370] | 1.82 | 0.91 | 249 [240–258] | 1.97 | 0.99 | tak |
| classic_2000x2000_s400_vn | 4 | 223 [216–248] | 2.85 | 0.71 | 140 [130–180] | 3.52 | 0.88 | tak |
| classic_2000x2000_s400_vn | 6 | 197 [168–255] | 3.22 | 0.54 | 114 [89.3–157] | 4.31 | 0.72 | tak |
| classic_2000x2000_s400_vn | 8 | 203 [167–783] | 3.13 | 0.39 | 113 [86.2–645] | 4.33 | 0.54 | tak |
| classic_300x300x300_s100_vn | 1 | 4 196 [4 036–4 298] | 1.00 | 1.00 | 3 151 [3 081–3 259] | 1.00 | 1.00 | tak |
| classic_300x300x300_s100_vn | 2 | 2 573 [2 487–2 636] | 1.63 | 0.82 | 1 789 [1 732–1 805] | 1.76 | 0.88 | tak |
| classic_300x300x300_s100_vn | 4 | 1 771 [1 489–1 821] | 2.37 | 0.59 | 1 068 [962–1 219] | 2.95 | 0.74 | tak |
| classic_300x300x300_s100_vn | 6 | 1 427 [1 313–1 498] | 2.94 | 0.49 | 772 [744–857] | 4.08 | 0.68 | tak |
| classic_300x300x300_s100_vn | 8 | 1 835 [1 248–1 981] | 2.29 | 0.29 | 1 103 [630–1 236] | 2.86 | 0.36 | tak |
| mc_cb_2d_1000 | 1 | 2 334 [2 309–2 371] | 1.00 | 1.00 | 1 919 [1 907–1 920] | 1.00 | 1.00 | tak |
| mc_cb_2d_1000 | 2 | 1 359 [1 347–1 368] | 1.72 | 0.86 | 972 [962–981] | 1.97 | 0.99 | tak |
| mc_cb_2d_1000 | 4 | 889 [883–1 087] | 2.63 | 0.66 | 508 [506–592] | 3.78 | 0.94 | tak |
| mc_cb_2d_1000 | 6 | 789 [746–927] | 2.96 | 0.49 | 373 [358–466] | 5.14 | 0.86 | tak |
| mc_cb_2d_1000 | 8 | 808 [775–2 299] | 2.89 | 0.36 | 408 [347–1 762] | 4.70 | 0.59 | tak |
| mc_cb_3d_100 | 1 | 6 272 [6 199–6 321] | 1.00 | 1.00 | 5 273 [5 229–5 315] | 1.00 | 1.00 | tak |
| mc_cb_3d_100 | 2 | 3 561 [3 523–3 588] | 1.76 | 0.88 | 2 686 [2 654–2 696] | 1.96 | 0.98 | tak |
| mc_cb_3d_100 | 4 | 2 294 [2 259–2 310] | 2.73 | 0.68 | 1 444 [1 400–1 477] | 3.65 | 0.91 | tak |
| mc_cb_3d_100 | 6 | 1 888 [1 869–1 970] | 3.32 | 0.55 | 1 041 [1 015–1 128] | 5.06 | 0.84 | tak |
| mc_cb_3d_100 | 8 | 1 878 [1 673–3 250] | 3.34 | 0.42 | 1 029 [840–2 177] | 5.13 | 0.64 | tak |

Prawo Amdahla — część szeregowa f (dopasowanie do mediany S(p), najmniejsze kwadraty na 1/S); „szeregowe z pomiaru” = (total − faza)/total przy p = 1; S(∞) = 1/f:

| Przypadek | f (total) | f (faza) | szeregowe z pomiaru | S(8) z f | S(∞) |
|---|---|---|---|---|---|
| classic_2000x2000_s400_vn | 0.172 | 0.077 | 0.227 | 3.63 | 5.8 |
| classic_300x300x300_s100_vn | 0.265 | 0.160 | 0.249 | 2.80 | 3.8 |
| mc_cb_2d_1000 | 0.209 | 0.050 | 0.178 | 3.24 | 4.8 |
| mc_cb_3d_100 | 0.170 | 0.048 | 0.159 | 3.66 | 5.9 |

Tło (Windows, poza WSL): start 14% (WmiPrvSE.exe 189%, WmiPrvSE.exe 60%, python.exe 43%), koniec 13%.
