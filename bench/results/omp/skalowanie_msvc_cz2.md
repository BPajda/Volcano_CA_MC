# Skalowanie OpenMP `skalowanie_msvc_cz2`

- Program: `engine.exe`; przypięcie `parallel.affinity = pcores` (jeden wątek na rdzeń fizyczny P); priorytet HIGH_PRIORITY_CLASS; warianty naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 3.1 min, 2026-10-20T05:05
- Tło: start 14% CPU (WmiPrvSE.exe 193%, WmiPrvSE.exe 53%, python.exe 41%), koniec 12%
- Zgodność wyników z p = 1 (albo z pierwszym harmonogramem): wszystkie przebiegi bitowo zgodne

| Przypadek | p | total [ms] | S | E | faza [ms] | S fazy | E fazy | zgodne |
|---|---|---|---|---|---|---|---|---|
| classic_2000x2000_s400_vn | 1 | 659 [644–718] | 1.00 | 1.00 | 530 [515–584] | 1.00 | 1.00 | tak |
| classic_2000x2000_s400_vn | 2 | 366 [360–597] | 1.80 | 0.90 | 264 [259–475] | 2.01 | 1.00 | tak |
| classic_2000x2000_s400_vn | 4 | 224 [220–305] | 2.94 | 0.74 | 134 [133–215] | 3.95 | 0.99 | tak |
| classic_2000x2000_s400_vn | 6 | 176 [172–190] | 3.74 | 0.62 | 91.3 [89.8–108] | 5.81 | 0.97 | tak |
| classic_2000x2000_s400_vn | 8 | 180 [158–388] | 3.66 | 0.46 | 79.4 [74.8–245] | 6.67 | 0.83 | tak |
| classic_300x300x300_s100_vn | 1 | 4 396 [4 368–4 404] | 1.00 | 1.00 | 3 406 [3 393–3 430] | 1.00 | 1.00 | tak |
| classic_300x300x300_s100_vn | 2 | 2 634 [2 614–3 888] | 1.67 | 0.83 | 1 884 [1 856–2 122] | 1.81 | 0.90 | tak |
| classic_300x300x300_s100_vn | 4 | 1 691 [1 656–1 811] | 2.60 | 0.65 | 1 025 [1 008–1 137] | 3.32 | 0.83 | tak |
| classic_300x300x300_s100_vn | 6 | 1 395 [1 368–1 427] | 3.15 | 0.53 | 774 [759–788] | 4.40 | 0.73 | tak |
| classic_300x300x300_s100_vn | 8 | 1 365 [1 294–1 433] | 3.22 | 0.40 | 707 [688–782] | 4.82 | 0.60 | tak |
| mc_cb_2d_1000 | 1 | 2 532 [2 515–2 560] | 1.00 | 1.00 | 2 059 [2 044–2 079] | 1.00 | 1.00 | tak |
| mc_cb_2d_1000 | 2 | 1 491 [1 485–1 501] | 1.70 | 0.85 | 1 044 [1 042–1 056] | 1.97 | 0.99 | tak |
| mc_cb_2d_1000 | 4 | 967 [960–971] | 2.62 | 0.65 | 529 [526–532] | 3.89 | 0.97 | tak |
| mc_cb_2d_1000 | 6 | 792 [788–800] | 3.20 | 0.53 | 358 [357–362] | 5.75 | 0.96 | tak |
| mc_cb_2d_1000 | 8 | 768 [752–831] | 3.30 | 0.41 | 333 [316–377] | 6.18 | 0.77 | tak |
| mc_random_2d_1000 | 1 | 8 788 [8 473–9 543] | 1.00 | 1.00 | 8 324 [7 996–9 073] | 1.00 | 1.00 | tak |

Prawo Amdahla — część szeregowa f (dopasowanie do mediany S(p), najmniejsze kwadraty na 1/S); „szeregowe z pomiaru” = (total − faza)/total przy p = 1; S(∞) = 1/f:

| Przypadek | f (total) | f (faza) | szeregowe z pomiaru | S(8) z f | S(∞) |
|---|---|---|---|---|---|
| classic_2000x2000_s400_vn | 0.136 | 0.012 | 0.196 | 4.10 | 7.4 |
| classic_300x300x300_s100_vn | 0.193 | 0.082 | 0.225 | 3.40 | 5.2 |
| mc_cb_2d_1000 | 0.185 | 0.021 | 0.187 | 3.48 | 5.4 |
