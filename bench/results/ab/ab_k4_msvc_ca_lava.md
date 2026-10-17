# Test A/B `ab_k4_msvc_ca_lava`

Optymalizacja 4 (automat frontalny), MSVC — część ca_lava pełnego zestawu; k4_full = ten sam program z ca.sweep = full (scalona tabela: ab_k4_msvc.md)

- Programy: `przed` = `engine_przed_msvc.exe`, `k3` = `engine_k3_msvc.exe`, `k4_full` = `engine_k4_msvc.exe` `--set ca.sweep=full`, `k4` = `engine_k4_msvc.exe`
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 3.8 min, 2026-10-17T20:06
- Tło: start 19% CPU (WmiPrvSE.exe 298%, MsMpEng.exe 90%, python.exe 67%), koniec 16%
- Zgodność wyników z `przed`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | przed [ms] | k3 [ms] | k4_full [ms] | k4 [ms] | k3/przed | k4_full/przed | k4/przed | k4_full/k3 | k4/k4_full | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|
| lava_test_3d | caSim | 1 526 [1 501–1 547] | 1 487 [1 467–1 531] | 1 164 [1 141–1 189] | 41.7 [40.4–48.5] | ×0.974 | ×0.763 | ×0.027 | ×0.783 | ×0.036 | tak |
| lava_test_3d | total | 1 557 [1 532–1 583] | 1 517 [1 499–1 565] | 1 195 [1 173–1 220] | 71.9 [70.8–88.1] | ×0.974 | ×0.768 | ×0.046 | ×0.788 | ×0.060 | tak |
| lava_test_3d | procWall | 1 566 [1 540–1 590] | 1 525 [1 507–1 573] | 1 203 [1 181–1 227] | 79.6 [78.8–95.9] | ×0.974 | ×0.769 | ×0.051 | ×0.789 | ×0.066 | tak |
| lava_etna_real | caSim | 13 085 [13 021–13 281] | 13 065 [12 923–13 155] | 10 074 [10 042–10 199] | 39.1 [37.4–40.9] | ×0.999 | ×0.770 | ×0.003 | ×0.771 | ×0.004 | tak |
| lava_etna_real | total | 13 118 [13 056–13 326] | 13 099 [12 956–13 188] | 10 125 [10 075–10 234] | 68.8 [64.9–72.6] | ×0.999 | ×0.772 | ×0.005 | ×0.773 | ×0.007 | tak |
| lava_etna_real | procWall | 13 128 [13 066–13 336] | 13 109 [12 965–13 198] | 10 134 [10 084–10 244] | 78.7 [73.6–81.7] | ×0.999 | ×0.772 | ×0.006 | ×0.773 | ×0.008 | tak |
| lava_mc_2d_ca | caSim | 51.8 [49.6–61.5] | 37.7 [36.5–44.6] | 35.4 [33.5–37.8] | 2.36 [2.29–2.45] | ×0.729 | ×0.685 | ×0.046 | ×0.940 | ×0.066 | tak |
| lava_mc_2d_ca | total | 59.4 [55.7–67.4] | 42.7 [41.5–51.2] | 41.5 [39.3–43.8] | 7.71 [7.00–8.49] | ×0.718 | ×0.698 | ×0.130 | ×0.972 | ×0.186 | tak |
| lava_mc_2d_ca | procWall | 66.5 [63.3–76.4] | 50.4 [49.0–59.2] | 49.0 [47.0–51.4] | 16.1 [14.8–20.7] | ×0.758 | ×0.737 | ×0.243 | ×0.972 | ×0.330 | tak |
