# Skalowanie OpenMP `harmonogramy_gcc`

- Program: `engine`; wiązanie libgomp OMP_PROC_BIND=close, OMP_PLACES=cores (`parallel.affinity = none`); priorytet domyślny; warianty naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 1.8 min, 2026-10-20T05:28
- Zgodność wyników z p = 1 (albo z pierwszym harmonogramem): wszystkie przebiegi bitowo zgodne

| Przypadek | harmonogram | p | faza [ms] | total [ms] | faza / najlepszy | zgodne |
|---|---|---|---|---|---|---|
| lava_etna_real | static | 8 | 43.6 [32.0–54.7] | 92.2 | ×2.07 | tak |
| lava_etna_real | static,1 | 8 | 21.0 [14.0–29.9] | 63.9 | ×1.00 | tak |
| lava_etna_real | dynamic | 8 | 23.5 [21.7–41.6] | 66.3 | ×1.12 | tak |
| lava_etna_real | dynamic,4 | 8 | 27.8 [25.0–38.1] | 69.6 | ×1.32 | tak |
| lava_etna_real | guided | 8 | 31.3 [25.0–41.0] | 73.4 | ×1.49 | tak |
| lava_etna_real | guided,4 | 8 | 31.5 [26.4–49.9] | 77.4 | ×1.50 | tak |
| lava_duza_3d_front | static | 8 | 219 [200–256] | 243 | ×1.65 | tak |
| lava_duza_3d_front | static,1 | 8 | 137 [119–209] | 163 | ×1.03 | tak |
| lava_duza_3d_front | dynamic | 8 | 132 [118–172] | 161 | ×1.00 | tak |
| lava_duza_3d_front | dynamic,4 | 8 | 168 [146–260] | 192 | ×1.27 | tak |
| lava_duza_3d_front | guided | 8 | 256 [193–351] | 280 | ×1.93 | tak |
| lava_duza_3d_front | guided,4 | 8 | 224 [209–319] | 247 | ×1.69 | tak |
| lava_duza_3d_full | static | 8 | 2 512 [2 385–2 656] | 2 551 | ×1.35 | tak |
| lava_duza_3d_full | static,1 | 8 | 2 286 [2 222–2 525] | 2 326 | ×1.23 | tak |
| lava_duza_3d_full | dynamic | 8 | 1 857 [1 816–1 888] | 1 897 | ×1.00 | tak |
| lava_duza_3d_full | dynamic,4 | 8 | 2 271 [2 056–2 322] | 2 309 | ×1.22 | tak |
| lava_duza_3d_full | guided | 8 | 1 973 [1 868–2 199] | 2 010 | ×1.06 | tak |
| lava_duza_3d_full | guided,4 | 8 | 2 236 [2 038–2 280] | 2 270 | ×1.20 | tak |

Tło (Windows, poza WSL): start 14% (WmiPrvSE.exe 149%, WmiPrvSE.exe 52%, python.exe 42%), koniec 11%.
