# Skalowanie OpenMP `harmonogramy_msvc`

- Program: `engine.exe`; przypięcie `parallel.affinity = pcores` (jeden wątek na rdzeń fizyczny P); priorytet HIGH_PRIORITY_CLASS; warianty naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 5.1 min, 2026-10-20T05:15
- Tło: start 14% CPU (WmiPrvSE.exe 186%, WmiPrvSE.exe 52%, svchost.exe 44%), koniec 15%
- Zgodność wyników z p = 1 (albo z pierwszym harmonogramem): wszystkie przebiegi bitowo zgodne

| Przypadek | harmonogram | p | faza [ms] | total [ms] | faza / najlepszy | zgodne |
|---|---|---|---|---|---|---|
| lava_etna_real | static | 8 | 35.7 [32.9–66.0] | 90.3 | ×1.55 | tak |
| lava_etna_real | static,1 | 8 | 23.0 [15.7–34.2] | 74.1 | ×1.00 | tak |
| lava_etna_real | dynamic | 8 | 51.7 [37.5–67.9] | 100 | ×2.25 | tak |
| lava_etna_real | dynamic,4 | 8 | 46.1 [35.1–59.9] | 97.2 | ×2.00 | tak |
| lava_etna_real | guided | 8 | 51.3 [36.3–64.3] | 100 | ×2.23 | tak |
| lava_etna_real | guided,4 | 8 | 48.5 [37.7–62.7] | 101 | ×2.11 | tak |
| lava_duza_3d_front | static | 8 | 216 [206–298] | 249 | ×1.60 | tak |
| lava_duza_3d_front | static,1 | 8 | 135 [121–183] | 167 | ×1.00 | tak |
| lava_duza_3d_front | dynamic | 8 | 147 [120–198] | 190 | ×1.09 | tak |
| lava_duza_3d_front | dynamic,4 | 8 | 169 [144–191] | 202 | ×1.25 | tak |
| lava_duza_3d_front | guided | 8 | 241 [214–263] | 272 | ×1.79 | tak |
| lava_duza_3d_front | guided,4 | 8 | 235 [229–322] | 272 | ×1.74 | tak |
| lava_duza_3d_full | static | 8 | 2 496 [2 209–2 525] | 2 532 | ×1.33 | tak |
| lava_duza_3d_full | static,1 | 8 | 2 056 [2 013–2 380] | 2 097 | ×1.10 | tak |
| lava_duza_3d_full | dynamic | 8 | 1 874 [1 782–1 891] | 1 910 | ×1.00 | tak |
| lava_duza_3d_full | dynamic,4 | 8 | 2 039 [2 016–2 177] | 2 081 | ×1.09 | tak |
| lava_duza_3d_full | guided | 8 | 1 879 [1 860–1 940] | 1 918 | ×1.00 | tak |
| lava_duza_3d_full | guided,4 | 8 | 2 136 [2 035–2 181] | 2 173 | ×1.14 | tak |
| classic_2000x2000_s400_vn | static | 8 | 86.9 [69.3–127] | 177 | ×1.00 | tak |
| classic_2000x2000_s400_vn | static,1 | 8 | 144 [120–211] | 225 | ×1.66 | tak |
| classic_2000x2000_s400_vn | dynamic | 8 | 325 [302–414] | 416 | ×3.74 | tak |
| classic_2000x2000_s400_vn | dynamic,4 | 8 | 146 [139–174] | 233 | ×1.68 | tak |
| classic_2000x2000_s400_vn | guided | 8 | 91.0 [81.4–102] | 176 | ×1.05 | tak |
| classic_2000x2000_s400_vn | guided,4 | 8 | 104 [82.2–114] | 195 | ×1.19 | tak |
| classic_300x300x300_s100_vn | static | 8 | 787 [739–1 055] | 1 434 | ×1.15 | tak |
| classic_300x300x300_s100_vn | static,1 | 8 | 906 [876–1 064] | 1 526 | ×1.32 | tak |
| classic_300x300x300_s100_vn | dynamic | 8 | 881 [861–939] | 1 497 | ×1.28 | tak |
| classic_300x300x300_s100_vn | dynamic,4 | 8 | 686 [672–798] | 1 287 | ×1.00 | tak |
| classic_300x300x300_s100_vn | guided | 8 | 719 [703–870] | 1 344 | ×1.05 | tak |
| classic_300x300x300_s100_vn | guided,4 | 8 | 716 [708–890] | 1 355 | ×1.04 | tak |
| mc_cb_2d_1000 | static | 8 | 351 [326–453] | 791 | ×1.09 | tak |
| mc_cb_2d_1000 | static,1 | 8 | 396 [364–436] | 846 | ×1.23 | tak |
| mc_cb_2d_1000 | dynamic | 8 | 423 [399–451] | 861 | ×1.31 | tak |
| mc_cb_2d_1000 | dynamic,4 | 8 | 348 [314–389] | 796 | ×1.08 | tak |
| mc_cb_2d_1000 | guided | 8 | 333 [309–390] | 767 | ×1.03 | tak |
| mc_cb_2d_1000 | guided,4 | 8 | 322 [305–334] | 765 | ×1.00 | tak |
| mc_cb_3d_100 | static | 8 | 964 [955–1 149] | 1 981 | ×1.03 | tak |
| mc_cb_3d_100 | static,1 | 8 | 1 809 [1 662–1 837] | 2 831 | ×1.93 | tak |
| mc_cb_3d_100 | dynamic | 8 | 956 [909–1 070] | 1 959 | ×1.02 | tak |
| mc_cb_3d_100 | dynamic,4 | 8 | 1 076 [1 032–1 187] | 2 080 | ×1.15 | tak |
| mc_cb_3d_100 | guided | 8 | 935 [917–1 069] | 1 948 | ×1.00 | tak |
| mc_cb_3d_100 | guided,4 | 8 | 964 [909–1 041] | 1 960 | ×1.03 | tak |
