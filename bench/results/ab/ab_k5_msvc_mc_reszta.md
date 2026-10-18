# Test A/B `ab_k5_msvc_mc_reszta`

Optymalizacja 5 (tańsze statystyki MC), MSVC, tryb oszczędny (bez turbo) — część mc bez 100^3 (scalona tabela: ab_k5_msvc.md)

- Programy: `przed` = `engine_przed_msvc.exe`, `k4` = `engine_k4_msvc.exe`, `k5` = `engine_k5_msvc.exe`
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 4.6 min, 2026-10-17T22:06
- Tło: start 28% CPU (WmiPrvSE.exe 220%, inny program 73%, inny program 48%), koniec 20%
- Zgodność wyników z `przed`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | przed [ms] | k4 [ms] | k5 [ms] | k4/przed | k5/przed | k5/k4 | zgodne |
|---|---|---|---|---|---|---|---|---|
| mc_full_2d_200 | mcSim | 353 [348–365] | 132 [129–135] | 132 [129–135] | ×0.373 | ×0.374 | ×1.002 | tak |
| mc_full_2d_200 | mcStats | 30.4 [30.3–31.4] | 24.5 [24.2–26.9] | 18.2 [17.8–19.4] | ×0.806 | ×0.600 | ×0.744 | tak |
| mc_full_2d_200 | total | 398 [395–412] | 170 [167–173] | 164 [161–169] | ×0.427 | ×0.412 | ×0.964 | tak |
| mc_full_2d_200 | procWall | 418 [410–427] | 186 [183–191] | 183 [176–196] | ×0.446 | ×0.436 | ×0.979 | tak |
| mc_full_2d_1000 | mcSim | 15 933 [15 438–16 731] | 8 682 [8 572–9 414] | 8 846 [8 763–9 261] | ×0.545 | ×0.555 | ×1.019 | tak |
| mc_full_2d_1000 | mcStats | 725 [717–735] | 584 [579–592] | 433 [424–447] | ×0.806 | ×0.597 | ×0.741 | tak |
| mc_full_2d_1000 | mcSave | 129 [124–138] | 137 [132–138] | 128 [125–139] | ×1.062 | ×0.996 | ×0.938 | tak |
| mc_full_2d_1000 | total | 16 827 [16 330–17 632] | 9 438 [9 328–10 176] | 9 448 [9 350–9 863] | ×0.561 | ×0.561 | ×1.001 | tak |
| mc_full_2d_1000 | procWall | 16 842 [16 353–17 648] | 9 456 [9 344–10 192] | 9 465 [9 366–9 883] | ×0.561 | ×0.562 | ×1.001 | tak |
| mc_full_3d_50 | mcSim | 3 361 [3 237–3 431] | 1 184 [1 126–1 299] | 1 160 [1 123–1 169] | ×0.352 | ×0.345 | ×0.980 | tak |
| mc_full_3d_50 | mcStats | 829 [821–846] | 560 [553–597] | 274 [269–275] | ×0.676 | ×0.330 | ×0.488 | tak |
| mc_full_3d_50 | total | 4 212 [4 089–4 300] | 1 782 [1 708–1 922] | 1 459 [1 419–1 470] | ×0.423 | ×0.346 | ×0.819 | tak |
| mc_full_3d_50 | procWall | 4 232 [4 111–4 328] | 1 798 [1 724–1 938] | 1 477 [1 438–1 499] | ×0.425 | ×0.349 | ×0.822 | tak |
| lava_mc_3d | mcSim | 185 [183–188] | 45.4 [45.2–47.1] | 45.7 [45.0–46.9] | ×0.246 | ×0.248 | ×1.006 | tak |
| lava_mc_3d | caSim | 2 564 [2 533–2 638] | 63.0 [61.6–87.2] | 62.4 [61.7–64.9] | ×0.025 | ×0.024 | ×0.991 | tak |
| lava_mc_3d | total | 3 000 [2 954–3 102] | 339 [334–365] | 331 [327–352] | ×0.113 | ×0.110 | ×0.976 | tak |
| lava_mc_3d | procWall | 3 018 [2 971–3 119] | 358 [351–387] | 348 [345–371] | ×0.118 | ×0.115 | ×0.973 | tak |
