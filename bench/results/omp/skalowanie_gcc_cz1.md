# Skalowanie OpenMP `skalowanie_gcc_cz1`

- Program: `engine`; wiązanie libgomp OMP_PROC_BIND=close, OMP_PLACES=cores (`parallel.affinity = none`); priorytet domyślny; warianty naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 3.0 min, 2026-10-20T05:21
- Zgodność wyników z p = 1 (albo z pierwszym harmonogramem): wszystkie przebiegi bitowo zgodne

| Przypadek | p | total [ms] | S | E | faza [ms] | S fazy | E fazy | zgodne |
|---|---|---|---|---|---|---|---|---|
| lava_etna_real | 1 | 128 [121–132] | 1.00 | 1.00 | 79.1 [78.2–80.1] | 1.00 | 1.00 | tak |
| lava_etna_real | 2 | 91.4 [82.2–98.9] | 1.40 | 0.70 | 44.7 [43.6–55.2] | 1.77 | 0.89 | tak |
| lava_etna_real | 4 | 70.7 [60.7–102] | 1.81 | 0.45 | 27.3 [23.5–40.7] | 2.90 | 0.73 | tak |
| lava_etna_real | 6 | 66.2 [56.2–72.9] | 1.94 | 0.32 | 19.0 [16.6–25.2] | 4.17 | 0.70 | tak |
| lava_etna_real | 8 | 67.8 [61.8–106] | 1.89 | 0.24 | 23.0 [15.9–57.8] | 3.44 | 0.43 | tak |
| lava_duza_3d_front | 1 | 704 [686–735] | 1.00 | 1.00 | 666 [658–697] | 1.00 | 1.00 | tak |
| lava_duza_3d_front | 2 | 377 [372–385] | 1.87 | 0.93 | 351 [346–358] | 1.90 | 0.95 | tak |
| lava_duza_3d_front | 4 | 221 [203–293] | 3.19 | 0.80 | 192 [179–268] | 3.47 | 0.87 | tak |
| lava_duza_3d_front | 6 | 179 [168–214] | 3.93 | 0.66 | 144 [133–173] | 4.64 | 0.77 | tak |
| lava_duza_3d_front | 8 | 157 [128–255] | 4.49 | 0.56 | 130 [99.4–222] | 5.11 | 0.64 | tak |
| lava_duza_3d_full | 1 | 12 267 [12 254–12 319] | 1.00 | 1.00 | 12 227 [12 217–12 276] | 1.00 | 1.00 | tak |
| lava_duza_3d_full | 2 | 6 196 [6 177–6 349] | 1.98 | 0.99 | 6 157 [6 141–6 312] | 1.99 | 0.99 | tak |
| lava_duza_3d_full | 4 | 3 265 [3 248–3 322] | 3.76 | 0.94 | 3 233 [3 210–3 284] | 3.78 | 0.95 | tak |
| lava_duza_3d_full | 6 | 2 370 [2 309–2 465] | 5.18 | 0.86 | 2 325 [2 268–2 429] | 5.26 | 0.88 | tak |
| lava_duza_3d_full | 8 | 1 990 [1 874–2 016] | 6.16 | 0.77 | 1 953 [1 839–1 980] | 6.26 | 0.78 | tak |

Prawo Amdahla — część szeregowa f (dopasowanie do mediany S(p), najmniejsze kwadraty na 1/S); „szeregowe z pomiaru” = (total − faza)/total przy p = 1; S(∞) = 1/f:

| Przypadek | f (total) | f (faza) | szeregowe z pomiaru | S(8) z f | S(∞) |
|---|---|---|---|---|---|
| lava_etna_real | 0.430 | 0.136 | 0.383 | 1.99 | 2.3 |
| lava_duza_3d_front | 0.099 | 0.064 | 0.053 | 4.73 | 10.1 |
| lava_duza_3d_full | 0.031 | 0.028 | 0.003 | 6.59 | 32.7 |

Tło (Windows, poza WSL): start 13% (WmiPrvSE.exe 130%, WmiPrvSE.exe 55%, python.exe 42%), koniec 12%.
