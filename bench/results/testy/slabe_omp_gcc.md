# Skalowanie OpenMP `slabe_omp_gcc`

- Program: `engine`; wiązanie libgomp OMP_PROC_BIND=close, OMP_PLACES=cores (`parallel.affinity = none`); priorytet domyślny; warianty naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 0.8 min, 2026-10-21T18:41
- Skalowanie słabe: przestrzeń p razy większa przy p wątkach, `output.format = none`; wyników różnych rozmiarów nie porównuje się bitowo (zgodność wątków — etapy 9–10)

| Przypadek | wariant | p | komórki | kroki / MCS | faza [ms] | E_w fazy | total [ms] | E_w total | ns rdzenia / (komórka × krok) albo / próbę | E_w znormalizowana |
|---|---|---|---|---|---|---|---|---|---|---|
| weak_classic_2d | p1 | 1 | 4 000 000 | 199 | 544 [530–567] | 1.00 | 634 | 1.00 | 0.68 | 1.00 |
| weak_classic_2d | p4 | 4 | 16 000 000 | 228 | 800 [767–842] | 0.68 | 999 | 0.63 | 0.88 | 0.78 |
| weak_classic_2d | p8 | 8 | 32 000 000 | 247 | 1 307 [1 226–1 705] | 0.42 | 1 759 | 0.36 | 1.32 | 0.52 |
| weak_mc_cb_2d | p1 | 1 | 1 000 000 | 30 | 763 [758–826] | 1.00 | 862 | 1.00 | 25.44 | 1.00 |
| weak_mc_cb_2d | p4 | 4 | 4 000 000 | 30 | 812 [804–846] | 0.94 | 1 190 | 0.72 | 27.08 | 0.94 |
| weak_mc_cb_2d | p8 | 8 | 8 000 000 | 30 | 970 [885–1 069] | 0.79 | 1 661 | 0.52 | 32.34 | 0.79 |
| weak_lava_front | p1 | 1 | 1 048 576 | 260 | 530 [522–548] | 1.00 | 552 | 1.00 | 1.94 | 1.00 |
| weak_lava_front | p4 | 4 | 4 194 304 | 260 | 542 [503–597] | 0.98 | 603 | 0.91 | 1.99 | 0.98 |
| weak_lava_front | p8 | 8 | 8 388 608 | 260 | 694 [585–930] | 0.76 | 811 | 0.68 | 2.54 | 0.76 |

E_w = T(1) / T(p) przy przestrzeni p razy większej (ideał 1); znormalizowana — z czasu na (komórkę × krok / p), gdy liczba kroków albo MCS zmienia się z p (classic: największa luka między zarodkami).

Tło (Windows, poza WSL): start 16% (WmiPrvSE.exe 148%, python.exe 39%, WmiPrvSE.exe 36%), koniec 16%.
