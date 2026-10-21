# Skalowanie OpenMP `slabe_omp_msvc`

- Program: `engine.exe`; przypięcie `parallel.affinity = pcores` (jeden wątek na rdzeń fizyczny P); priorytet HIGH_PRIORITY_CLASS; warianty naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 1.9 min, 2026-10-21T18:36
- Tło: start 15% CPU (WmiPrvSE.exe 195%, python.exe 39%, WmiPrvSE.exe 35%), koniec 9%
- Skalowanie słabe: przestrzeń p razy większa przy p wątkach, `output.format = none`; wyników różnych rozmiarów nie porównuje się bitowo (zgodność wątków — etapy 9–10)

| Przypadek | wariant | p | komórki | kroki / MCS | faza [ms] | E_w fazy | total [ms] | E_w total | ns rdzenia / (komórka × krok) albo / próbę | E_w znormalizowana |
|---|---|---|---|---|---|---|---|---|---|---|
| weak_classic_2d | p1 | 1 | 4 000 000 | 199 | 533 [527–543] | 1.00 | 642 | 1.00 | 0.67 | 1.00 |
| weak_classic_2d | p2 | 2 | 8 000 000 | 223 | 642 [617–659] | 0.83 | 792 | 0.81 | 0.72 | 0.93 |
| weak_classic_2d | p4 | 4 | 16 000 000 | 228 | 705 [689–727] | 0.75 | 940 | 0.68 | 0.77 | 0.87 |
| weak_classic_2d | p6 | 6 | 24 000 000 | 233 | 819 [798–830] | 0.65 | 1 142 | 0.56 | 0.88 | 0.76 |
| weak_classic_2d | p8 | 8 | 32 000 000 | 247 | 1 084 [1 044–1 360] | 0.49 | 1 569 | 0.41 | 1.10 | 0.61 |
| weak_mc_cb_2d | p1 | 1 | 1 000 000 | 30 | 755 [754–758] | 1.00 | 869 | 1.00 | 25.16 | 1.00 |
| weak_mc_cb_2d | p2 | 2 | 2 000 000 | 30 | 793 [763–802] | 0.95 | 1 010 | 0.86 | 26.43 | 0.95 |
| weak_mc_cb_2d | p4 | 4 | 4 000 000 | 30 | 762 [759–787] | 0.99 | 1 187 | 0.73 | 25.39 | 0.99 |
| weak_mc_cb_2d | p6 | 6 | 6 000 000 | 30 | 764 [762–812] | 0.99 | 1 394 | 0.62 | 25.47 | 0.99 |
| weak_mc_cb_2d | p8 | 8 | 8 000 000 | 30 | 869 [827–884] | 0.87 | 1 724 | 0.50 | 28.96 | 0.87 |
| weak_lava_full | p1 | 1 | 1 048 576 | 20 | 1 121 [1 120–1 133] | 1.00 | 1 158 | 1.00 | 53.48 | 1.00 |
| weak_lava_full | p2 | 2 | 2 097 152 | 20 | 1 190 [1 163–1 324] | 0.94 | 1 258 | 0.92 | 56.72 | 0.94 |
| weak_lava_full | p4 | 4 | 4 194 304 | 20 | 1 160 [1 151–1 175] | 0.97 | 1 266 | 0.91 | 55.30 | 0.97 |
| weak_lava_full | p6 | 6 | 6 291 456 | 20 | 1 186 [1 181–1 198] | 0.95 | 1 343 | 0.86 | 56.54 | 0.95 |
| weak_lava_full | p8 | 8 | 8 388 608 | 20 | 1 278 [1 256–1 956] | 0.88 | 1 487 | 0.78 | 60.93 | 0.88 |
| weak_lava_front | p1 | 1 | 1 048 576 | 260 | 527 [526–528] | 1.00 | 559 | 1.00 | 1.93 | 1.00 |
| weak_lava_front | p2 | 2 | 2 097 152 | 260 | 552 [543–693] | 0.96 | 615 | 0.91 | 2.03 | 0.96 |
| weak_lava_front | p4 | 4 | 4 194 304 | 260 | 458 [456–494] | 1.15 | 548 | 1.02 | 1.68 | 1.15 |
| weak_lava_front | p6 | 6 | 6 291 456 | 260 | 448 [447–488] | 1.18 | 575 | 0.97 | 1.64 | 1.18 |
| weak_lava_front | p8 | 8 | 8 388 608 | 260 | 525 [518–569] | 1.00 | 707 | 0.79 | 1.93 | 1.00 |

E_w = T(1) / T(p) przy przestrzeni p razy większej (ideał 1); znormalizowana — z czasu na (komórkę × krok / p), gdy liczba kroków albo MCS zmienia się z p (classic: największa luka między zarodkami).
