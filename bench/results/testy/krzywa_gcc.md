# Czas na komórkę vs rozmiar siatki `krzywa_gcc`

- Program: `build-gcc-release/bin/engine`, 1 wątek (`parallel.affinity = none`, libgomp OMP_PROC_BIND=close)
- 2026-10-21T18:46, 1.4 min, powtórzeń 5 (rozmiary naprzemiennie rosnąco / malejąco)

| Krzywa | bok n | komórki | zbiór roboczy kroku [MB] | mieści się w | model: siatka [MB] | ns / jedn. — mediana [min–max] | względem najmniejszej | n powt. |
|---|---|---|---|---|---|---|---|---|
| classic_full | 128 | 16 384 | 0,42 | L2 | 0,42 | 6,87 [6,74–7,06] | 1,00 | 5 |
| classic_full | 181 | 32 761 | 0,83 | L2 | 0,83 | 6,91 [6,70–7,06] | 1,01 | 5 |
| classic_full | 256 | 65 536 | 1,65 | L2 | 1,65 | 6,70 [6,59–6,85] | 0,97 | 5 |
| classic_full | 362 | 131 044 | 3,29 | L3 | 3,29 | 6,80 [6,68–7,03] | 0,99 | 5 |
| classic_full | 512 | 262 144 | 6,55 | L3 | 6,55 | 6,83 [6,68–7,09] | 0,99 | 5 |
| classic_full | 724 | 524 176 | 13,07 | L3 | 13,07 | 6,91 [6,80–7,20] | 1,01 | 5 |
| classic_full | 1024 | 1 048 576 | 26,10 | L3 | 26,10 | 6,93 [6,89–7,29] | 1,01 | 5 |
| classic_full | 1448 | 2 096 704 | 52,13 | RAM | 52,13 | 6,95 [6,88–7,20] | 1,01 | 5 |
| classic_full | 2048 | 4 194 304 | 104,20 | RAM | 104,20 | 6,93 [6,90–7,21] | 1,01 | 5 |
| classic_full | 2896 | 8 386 816 | 208,24 | RAM | 208,24 | 6,97 [6,87–7,12] | 1,02 | 5 |
| mc_random | 128 | 16 384 | 0,19 | L2 | 0,33 | 36,56 [36,03–37,84] | 1,00 | 5 |
| mc_random | 181 | 32 761 | 0,38 | L2 | 0,66 | 37,39 [37,11–39,08] | 1,02 | 5 |
| mc_random | 256 | 65 536 | 0,76 | L2 | 1,32 | 38,97 [38,88–41,35] | 1,07 | 5 |
| mc_random | 362 | 131 044 | 1,52 | L2 | 2,63 | 42,22 [40,81–42,62] | 1,15 | 5 |
| mc_random | 512 | 262 144 | 3,02 | L3 | 5,26 | 53,70 [52,53–57,47] | 1,47 | 5 |
| mc_random | 724 | 524 176 | 6,03 | L3 | 10,51 | 68,13 [66,45–71,35] | 1,86 | 5 |
| mc_random | 1024 | 1 048 576 | 12,05 | L3 | 21,02 | 102,21 [96,38–105,03] | 2,80 | 5 |
| mc_random | 1448 | 2 096 704 | 24,06 | L3 | 42,03 | 126,63 [124,01–136,03] | 3,46 | 5 |
| mc_random | 2048 | 4 194 304 | 48,09 | RAM | 84,04 | 152,94 [149,61–155,72] | 4,18 | 5 |
| mc_random | 2896 | 8 386 816 | 96,11 | RAM | 168,05 | 170,68 [168,50–172,82] | 4,67 | 5 |
| mc_cb | 128 | 16 384 | 0,19 | L2 | 0,33 | 25,00 [24,43–26,22] | 1,00 | 5 |
| mc_cb | 181 | 32 761 | 0,38 | L2 | 0,67 | 24,94 [24,34–27,51] | 1,00 | 5 |
| mc_cb | 256 | 65 536 | 0,76 | L2 | 1,32 | 25,21 [24,88–26,90] | 1,01 | 5 |
| mc_cb | 362 | 131 044 | 1,52 | L2 | 2,64 | 25,23 [24,60–25,39] | 1,01 | 5 |
| mc_cb | 512 | 262 144 | 3,02 | L3 | 5,27 | 25,17 [24,46–25,46] | 1,01 | 5 |
| mc_cb | 724 | 524 176 | 6,03 | L3 | 10,52 | 24,66 [24,26–24,93] | 0,99 | 5 |
| mc_cb | 1024 | 1 048 576 | 12,05 | L3 | 21,04 | 24,66 [24,32–28,94] | 0,99 | 5 |
| mc_cb | 1448 | 2 096 704 | 24,06 | L3 | 42,05 | 24,82 [24,40–25,25] | 0,99 | 5 |
| mc_cb | 2048 | 4 194 304 | 48,09 | RAM | 84,07 | 24,81 [24,53–25,90] | 0,99 | 5 |
| mc_cb | 2896 | 8 386 816 | 96,11 | RAM | 168,09 | 24,94 [24,68–25,83] | 1,00 | 5 |

Jednostka: classic — komórka × krok (faza caSim), MC — próba (faza mcSim). Zbiór roboczy kroku = bajty dotykane na komórkę × komórki z ramką (classic `full` 26 B — oba bufory automatu; MC 12 B — lista domeny i orientacje); model: siatka = caGrid / mcGrid z modelu pamięci silnika (z tablicami, których krok nie dotyka). Progi rdzenia P: L1d 48 KB, L2 2 MB, L3 36 MB (L3 wspólna dla wszystkich rdzeni).

Tło (Windows, poza WSL): start 11% (WmiPrvSE.exe 148%, python.exe 40%, WmiPrvSE.exe 35%), koniec 21%.
