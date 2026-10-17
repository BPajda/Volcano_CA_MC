# Test A/B `ab_k3_msvc_ca_lava`

Optymalizacja 3 (przesunięcia liniowe sąsiadów w CA), MSVC — część ca_lava pełnego zestawu (scalona tabela: ab_k3_msvc.md)

- Programy: `przed` = `engine_przed_msvc.exe`, `k2` = `engine_k2_msvc.exe`, `k3` = `engine_k3_msvc.exe`
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 4.1 min, 2026-10-17T19:19
- Tło: start 15% CPU (WmiPrvSE.exe 183%, svchost.exe 41%, System 40%), koniec 15%
- Zgodność wyników z `przed`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | przed [ms] | k2 [ms] | k3 [ms] | k2/przed | k3/przed | k3/k2 | zgodne |
|---|---|---|---|---|---|---|---|---|
| lava_test_3d | caSim | 1 522 [1 501–1 595] | 1 678 [1 649–1 754] | 1 526 [1 463–1 595] | ×1.102 | ×1.003 | ×0.910 | tak |
| lava_test_3d | total | 1 551 [1 532–1 630] | 1 708 [1 679–1 787] | 1 557 [1 493–1 628] | ×1.101 | ×1.004 | ×0.912 | tak |
| lava_test_3d | procWall | 1 559 [1 541–1 638] | 1 716 [1 687–1 795] | 1 566 [1 501–1 639] | ×1.100 | ×1.004 | ×0.913 | tak |
| lava_etna_real | caSim | 13 234 [12 925–13 996] | 14 722 [14 566–15 481] | 12 896 [12 837–13 677] | ×1.112 | ×0.974 | ×0.876 | tak |
| lava_etna_real | total | 13 267 [12 957–14 042] | 14 756 [14 599–15 518] | 12 930 [12 868–13 713] | ×1.112 | ×0.975 | ×0.876 | tak |
| lava_etna_real | procWall | 13 276 [12 967–14 051] | 14 767 [14 609–15 529] | 12 939 [12 878–13 723] | ×1.112 | ×0.975 | ×0.876 | tak |
| lava_mc_2d_ca | caSim | 50.8 [48.8–55.6] | 41.1 [38.4–42.9] | 37.3 [35.8–42.7] | ×0.808 | ×0.733 | ×0.908 | tak |
| lava_mc_2d_ca | total | 56.9 [54.6–66.2] | 46.4 [43.4–49.5] | 43.2 [40.9–47.7] | ×0.816 | ×0.759 | ×0.930 | tak |
| lava_mc_2d_ca | procWall | 64.4 [61.7–79.8] | 53.6 [51.0–58.4] | 50.9 [48.4–57.0] | ×0.833 | ×0.791 | ×0.950 | tak |
