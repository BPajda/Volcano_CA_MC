# Skalowanie OpenMP `skalowanie_msvc_cz1`

- Program: `engine.exe`; przypięcie `parallel.affinity = pcores` (jeden wątek na rdzeń fizyczny P); priorytet HIGH_PRIORITY_CLASS; warianty naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 3.0 min, 2026-10-20T05:02
- Tło: start 14% CPU (WmiPrvSE.exe 170%, WmiPrvSE.exe 55%, svchost.exe 43%), koniec 15%
- Zgodność wyników z p = 1 (albo z pierwszym harmonogramem): wszystkie przebiegi bitowo zgodne

| Przypadek | p | total [ms] | S | E | faza [ms] | S fazy | E fazy | zgodne |
|---|---|---|---|---|---|---|---|---|
| lava_etna_real | 1 | 146 [144–146] | 1.00 | 1.00 | 85.5 [85.1–86.2] | 1.00 | 1.00 | tak |
| lava_etna_real | 2 | 102 [101–121] | 1.43 | 0.72 | 48.5 [48.0–67.4] | 1.76 | 0.88 | tak |
| lava_etna_real | 4 | 75.6 [74.9–82.5] | 1.93 | 0.48 | 25.9 [25.4–32.5] | 3.30 | 0.82 | tak |
| lava_etna_real | 6 | 67.3 [65.7–69.8] | 2.17 | 0.36 | 18.6 [18.2–19.7] | 4.58 | 0.76 | tak |
| lava_etna_real | 8 | 68.8 [63.6–88.6] | 2.12 | 0.26 | 17.1 [15.3–40.3] | 4.98 | 0.62 | tak |
| lava_duza_3d_front | 1 | 755 [752–766] | 1.00 | 1.00 | 718 [715–719] | 1.00 | 1.00 | tak |
| lava_duza_3d_front | 2 | 428 [406–453] | 1.76 | 0.88 | 394 [372–418] | 1.82 | 0.91 | tak |
| lava_duza_3d_front | 4 | 222 [221–226] | 3.40 | 0.85 | 190 [190–194] | 3.77 | 0.94 | tak |
| lava_duza_3d_front | 6 | 165 [164–168] | 4.57 | 0.76 | 134 [133–137] | 5.34 | 0.89 | tak |
| lava_duza_3d_front | 8 | 165 [140–250] | 4.59 | 0.57 | 134 [108–218] | 5.36 | 0.67 | tak |
| lava_duza_3d_full | 1 | 12 550 [12 503–12 638] | 1.00 | 1.00 | 12 489 [12 461–12 596] | 1.00 | 1.00 | tak |
| lava_duza_3d_full | 2 | 6 552 [6 455–6 841] | 1.92 | 0.96 | 6 513 [6 408–6 804] | 1.92 | 0.96 | tak |
| lava_duza_3d_full | 4 | 3 271 [3 266–3 276] | 3.84 | 0.96 | 3 230 [3 216–3 240] | 3.87 | 0.97 | tak |
| lava_duza_3d_full | 6 | 2 254 [2 237–2 260] | 5.57 | 0.93 | 2 218 [2 201–2 219] | 5.63 | 0.94 | tak |
| lava_duza_3d_full | 8 | 2 017 [1 972–2 061] | 6.22 | 0.78 | 1 971 [1 924–2 017] | 6.34 | 0.79 | tak |

Prawo Amdahla — część szeregowa f (dopasowanie do mediany S(p), najmniejsze kwadraty na 1/S); „szeregowe z pomiaru” = (total − faza)/total przy p = 1; S(∞) = 1/f:

| Przypadek | f (total) | f (faza) | szeregowe z pomiaru | S(8) z f | S(∞) |
|---|---|---|---|---|---|
| lava_etna_real | 0.374 | 0.080 | 0.414 | 2.21 | 2.7 |
| lava_duza_3d_front | 0.084 | 0.047 | 0.050 | 5.04 | 11.9 |
| lava_duza_3d_full | 0.027 | 0.024 | 0.005 | 6.73 | 37.2 |
