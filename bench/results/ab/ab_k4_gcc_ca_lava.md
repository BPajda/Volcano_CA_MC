# Test A/B `ab_k4_gcc_ca_lava`

Optymalizacja 4 (automat frontalny), GCC — część ca_lava pełnego zestawu; k4_full = ten sam program z ca.sweep = full (scalona tabela: ab_k4_gcc.md)

- Programy: `przed` = `engine_przed`, `k3` = `engine_k3`, `k4_full` = `engine_k4_full` `--set ca.sweep=full`, `k4` = `engine_k4`
- Przypięcie: sched_setaffinity({2}) (WSL2: procesor wirtualny); priorytet: domyślny; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 3.1 min, 2026-10-17T20:21
- Zgodność wyników z `przed`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | przed [ms] | k3 [ms] | k4_full [ms] | k4 [ms] | k3/przed | k4_full/przed | k4/przed | k4_full/k3 | k4/k4_full | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|
| lava_test_3d | caSim | 1 330 [1 244–1 429] | 1 086 [1 024–1 179] | 1 087 [984–1 161] | 37.5 [34.6–41.5] | ×0.817 | ×0.817 | ×0.028 | ×1.001 | ×0.035 | tak |
| lava_test_3d | total | 1 354 [1 267–1 460] | 1 112 [1 047–1 206] | 1 114 [1 006–1 187] | 61.3 [56.4–68.2] | ×0.821 | ×0.822 | ×0.045 | ×1.001 | ×0.055 | tak |
| lava_test_3d | procWall | 1 356 [1 268–1 461] | 1 114 [1 048–1 207] | 1 115 [1 007–1 189] | 62.6 [57.5–69.4] | ×0.821 | ×0.822 | ×0.046 | ×1.001 | ×0.056 | tak |
| lava_etna_real | caSim | 11 951 [10 916–12 077] | 9 436 [8 725–9 629] | 9 328 [8 558–9 351] | 34.7 [33.4–36.9] | ×0.790 | ×0.780 | ×0.003 | ×0.989 | ×0.004 | tak |
| lava_etna_real | total | 11 990 [10 950–12 115] | 9 467 [8 756–9 665] | 9 367 [8 590–9 382] | 59.0 [54.7–71.2] | ×0.790 | ×0.781 | ×0.005 | ×0.989 | ×0.006 | tak |
| lava_etna_real | procWall | 11 992 [10 952–12 117] | 9 469 [8 758–9 667] | 9 369 [8 592–9 384] | 60.9 [56.6–73.2] | ×0.790 | ×0.781 | ×0.005 | ×0.989 | ×0.006 | tak |
| lava_mc_2d_ca | caSim | 43.3 [40.9–47.5] | 27.8 [25.6–30.0] | 24.8 [22.9–27.4] | 2.38 [2.13–3.82] | ×0.642 | ×0.574 | ×0.055 | ×0.894 | ×0.096 | tak |
| lava_mc_2d_ca | total | 46.0 [43.6–50.6] | 30.3 [28.1–32.7] | 27.4 [25.5–30.8] | 4.78 [4.50–6.33] | ×0.657 | ×0.596 | ×0.104 | ×0.907 | ×0.174 | tak |
| lava_mc_2d_ca | procWall | 47.1 [44.6–51.7] | 31.2 [29.1–33.8] | 28.5 [26.5–32.2] | 5.83 [5.40–7.17] | ×0.663 | ×0.606 | ×0.124 | ×0.914 | ×0.204 | tak |

Tło (Windows, poza WSL): start 16% (WmiPrvSE.exe 278%, MsMpEng.exe 96%, python.exe 74%), koniec 20%.
