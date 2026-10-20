# Skalowanie OpenMP `skalowanie_msvc_cz3`

- Program: `engine.exe`; przypięcie `parallel.affinity = pcores` (jeden wątek na rdzeń fizyczny P); priorytet HIGH_PRIORITY_CLASS; warianty naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 3.4 min, 2026-10-20T05:09
- Tło: start 15% CPU (WmiPrvSE.exe 207%, WmiPrvSE.exe 59%, python.exe 42%), koniec 10%
- Zgodność wyników z p = 1 (albo z pierwszym harmonogramem): wszystkie przebiegi bitowo zgodne

| Przypadek | p | total [ms] | S | E | faza [ms] | S fazy | E fazy | zgodne |
|---|---|---|---|---|---|---|---|---|
| mc_cb_3d_100 | 1 | 6 902 [6 899–6 914] | 1.00 | 1.00 | 5 743 [5 742–5 759] | 1.00 | 1.00 | tak |
| mc_cb_3d_100 | 2 | 4 159 [3 946–4 237] | 1.66 | 0.83 | 3 093 [2 898–3 170] | 1.86 | 0.93 | tak |
| mc_cb_3d_100 | 4 | 2 526 [2 502–2 598] | 2.73 | 0.68 | 1 517 [1 495–1 582] | 3.79 | 0.95 | tak |
| mc_cb_3d_100 | 6 | 2 045 [2 036–2 073] | 3.38 | 0.56 | 1 039 [1 037–1 070] | 5.53 | 0.92 | tak |
| mc_cb_3d_100 | 8 | 1 944 [1 918–2 055] | 3.55 | 0.44 | 948 [916–1 039] | 6.06 | 0.76 | tak |
| mc_random_3d_100 | 1 | 19 982 [19 921–20 693] | 1.00 | 1.00 | 18 860 [18 798–19 576] | 1.00 | 1.00 | tak |

Prawo Amdahla — część szeregowa f (dopasowanie do mediany S(p), najmniejsze kwadraty na 1/S); „szeregowe z pomiaru” = (total − faza)/total przy p = 1; S(∞) = 1/f:

| Przypadek | f (total) | f (faza) | szeregowe z pomiaru | S(8) z f | S(∞) |
|---|---|---|---|---|---|
| mc_cb_3d_100 | 0.169 | 0.034 | 0.168 | 3.67 | 5.9 |
