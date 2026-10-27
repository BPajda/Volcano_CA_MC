# Test A/B `ab_k5_gcc_mc_3d_100`

Optymalizacja 5 (tańsze statystyki MC), GCC, taktowanie bazowe — część mc_full_3d_100 (scalona tabela: ab_k5_gcc.md)

- Programy: `przed` = `engine_przed`, `k4` = `engine_k4`, `k5` = `engine_k5`
- Przypięcie: sched_setaffinity({2}) (WSL2: procesor wirtualny); priorytet: domyślny; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 6.6 min, 2026-10-17T22:16
- Zgodność wyników z `przed`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | przed [ms] | k4 [ms] | k5 [ms] | k4/przed | k5/przed | k5/k4 | zgodne |
|---|---|---|---|---|---|---|---|---|
| mc_full_3d_100 | mcSim | 27 985 [27 611–31 488] | 20 238 [19 519–21 181] | 20 056 [19 474–21 416] | ×0.723 | ×0.717 | ×0.991 | tak |
| mc_full_3d_100 | mcStats | 1 938 [1 918–2 156] | 1 821 [1 770–1 924] | 969 [933–1 032] | ×0.939 | ×0.500 | ×0.532 | tak |
| mc_full_3d_100 | mcSave | 66.5 [65.0–75.0] | 71.9 [67.6–74.5] | 68.8 [65.1–70.8] | ×1.081 | ×1.035 | ×0.958 | tak |
| mc_full_3d_100 | total | 30 015 [29 636–33 756] | 22 169 [21 389–23 212] | 21 116 [20 499–22 547] | ×0.739 | ×0.703 | ×0.952 | tak |
| mc_full_3d_100 | procWall | 30 017 [29 639–33 759] | 22 171 [21 391–23 216] | 21 118 [20 501–22 549] | ×0.739 | ×0.704 | ×0.952 | tak |

Tło (Windows, poza WSL): start 19% (WmiPrvSE.exe 214%, python.exe 42%, inny program 37%), koniec 17%.
