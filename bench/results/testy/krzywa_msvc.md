# Czas na komórkę vs rozmiar siatki `krzywa_msvc`

- Program: `build/Release/engine.exe`, 1 wątek (`parallel.affinity = pcores`, priorytet wysoki)
- 2026-10-21T18:44, 1.6 min, powtórzeń 5 (rozmiary naprzemiennie rosnąco / malejąco)
- Tło: start 22% CPU (WmiPrvSE.exe 193%, svchost.exe 50%, System 47%), koniec 14%

| Krzywa | bok n | komórki | zbiór roboczy kroku [MB] | mieści się w | model: siatka [MB] | ns / jedn. — mediana [min–max] | względem najmniejszej | n powt. |
|---|---|---|---|---|---|---|---|---|
| classic_full | 128 | 16 384 | 0,42 | L2 | 0,42 | 8,27 [8,18–8,37] | 1,00 | 5 |
| classic_full | 181 | 32 761 | 0,83 | L2 | 0,83 | 8,27 [8,22–8,29] | 1,00 | 5 |
| classic_full | 256 | 65 536 | 1,65 | L2 | 1,65 | 8,14 [8,12–8,18] | 0,98 | 5 |
| classic_full | 362 | 131 044 | 3,29 | L3 | 3,29 | 8,13 [8,11–8,17] | 0,98 | 5 |
| classic_full | 512 | 262 144 | 6,55 | L3 | 6,55 | 8,16 [8,14–8,19] | 0,99 | 5 |
| classic_full | 724 | 524 176 | 13,07 | L3 | 13,07 | 8,18 [8,14–8,34] | 0,99 | 5 |
| classic_full | 1024 | 1 048 576 | 26,10 | L3 | 26,10 | 8,25 [8,19–8,28] | 1,00 | 5 |
| classic_full | 1448 | 2 096 704 | 52,13 | RAM | 52,13 | 8,25 [8,24–8,29] | 1,00 | 5 |
| classic_full | 2048 | 4 194 304 | 104,20 | RAM | 104,20 | 8,23 [8,21–8,26] | 0,99 | 5 |
| classic_full | 2896 | 8 386 816 | 208,24 | RAM | 208,24 | 8,23 [8,22–8,26] | 0,99 | 5 |
| mc_random | 128 | 16 384 | 0,19 | L2 | 0,36 | 36,44 [36,23–37,68] | 1,00 | 5 |
| mc_random | 181 | 32 761 | 0,38 | L2 | 0,78 | 37,78 [37,36–38,57] | 1,04 | 5 |
| mc_random | 256 | 65 536 | 0,76 | L2 | 1,72 | 38,86 [38,80–39,11] | 1,07 | 5 |
| mc_random | 362 | 131 044 | 1,52 | L2 | 2,74 | 40,61 [40,26–41,71] | 1,11 | 5 |
| mc_random | 512 | 262 144 | 3,02 | L3 | 6,01 | 52,55 [52,15–53,15] | 1,44 | 5 |
| mc_random | 724 | 524 176 | 6,03 | L3 | 13,19 | 65,67 [63,49–72,36] | 1,80 | 5 |
| mc_random | 1024 | 1 048 576 | 12,05 | L3 | 21,04 | 94,43 [92,16–95,07] | 2,59 | 5 |
| mc_random | 1448 | 2 096 704 | 24,06 | L3 | 46,07 | 120,17 [117,07–128,29] | 3,30 | 5 |
| mc_random | 2048 | 4 194 304 | 48,09 | RAM | 101,14 | 145,84 [141,62–149,43] | 4,00 | 5 |
| mc_random | 2896 | 8 386 816 | 96,11 | RAM | 222,52 | 168,56 [163,38–170,03] | 4,63 | 5 |
| mc_cb | 128 | 16 384 | 0,19 | L2 | 0,36 | 25,25 [25,13–25,31] | 1,00 | 5 |
| mc_cb | 181 | 32 761 | 0,38 | L2 | 0,80 | 24,86 [24,74–25,02] | 0,98 | 5 |
| mc_cb | 256 | 65 536 | 0,76 | L2 | 1,73 | 24,73 [24,66–24,84] | 0,98 | 5 |
| mc_cb | 362 | 131 044 | 1,52 | L2 | 2,75 | 24,73 [24,72–24,83] | 0,98 | 5 |
| mc_cb | 512 | 262 144 | 3,02 | L3 | 6,01 | 24,63 [24,56–24,66] | 0,98 | 5 |
| mc_cb | 724 | 524 176 | 6,03 | L3 | 13,20 | 24,55 [24,53–24,56] | 0,97 | 5 |
| mc_cb | 1024 | 1 048 576 | 12,05 | L3 | 21,05 | 24,61 [24,55–24,86] | 0,97 | 5 |
| mc_cb | 1448 | 2 096 704 | 24,06 | L3 | 46,09 | 24,61 [24,55–25,13] | 0,97 | 5 |
| mc_cb | 2048 | 4 194 304 | 48,09 | RAM | 101,17 | 24,58 [24,55–24,73] | 0,97 | 5 |
| mc_cb | 2896 | 8 386 816 | 96,11 | RAM | 222,57 | 24,64 [24,57–24,70] | 0,98 | 5 |

Jednostka: classic — komórka × krok (faza caSim), MC — próba (faza mcSim). Zbiór roboczy kroku = bajty dotykane na komórkę × komórki z ramką (classic `full` 26 B — oba bufory automatu; MC 12 B — lista domeny i orientacje); model: siatka = caGrid / mcGrid z modelu pamięci silnika (z tablicami, których krok nie dotyka). Progi rdzenia P: L1d 48 KB, L2 2 MB, L3 36 MB (L3 wspólna dla wszystkich rdzeni).
