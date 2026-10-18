# Test A/B `ab_k5_msvc_mc_3d_100`

Optymalizacja 5 (tańsze statystyki MC), MSVC, tryb oszczędny (bez turbo) — część mc_full_3d_100 (scalona tabela: ab_k5_msvc.md)

- Programy: `przed` = `engine_przed_msvc.exe`, `k4` = `engine_k4_msvc.exe`, `k5` = `engine_k5_msvc.exe`
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 8.1 min, 2026-10-17T22:01
- Tło: start 20% CPU (WmiPrvSE.exe 163%, inny program 49%, python.exe 44%), koniec 16%
- Zgodność wyników z `przed`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | przed [ms] | k4 [ms] | k5 [ms] | k4/przed | k5/przed | k5/k4 | zgodne |
|---|---|---|---|---|---|---|---|---|
| mc_full_3d_100 | mcSim | 43 409 [43 187–43 837] | 22 212 [22 109–22 447] | 22 480 [22 052–23 100] | ×0.512 | ×0.518 | ×1.012 | tak |
| mc_full_3d_100 | mcStats | 3 435 [3 386–3 451] | 2 316 [2 272–2 338] | 1 053 [1 042–1 074] | ×0.674 | ×0.307 | ×0.455 | tak |
| mc_full_3d_100 | mcSave | 125 [121–133] | 132 [128–138] | 127 [123–171] | ×1.061 | ×1.019 | ×0.960 | tak |
| mc_full_3d_100 | total | 47 017 [46 800–47 435] | 24 706 [24 570–24 890] | 23 710 [23 258–24 341] | ×0.525 | ×0.504 | ×0.960 | tak |
| mc_full_3d_100 | procWall | 47 033 [46 822–47 455] | 24 729 [24 588–24 907] | 23 730 [23 277–24 359] | ×0.526 | ×0.505 | ×0.960 | tak |
