# Test A/B `ab_k3_gcc_ca_lava`

Optymalizacja 3 (przesunięcia liniowe sąsiadów w CA), GCC — część ca_lava pełnego zestawu (scalona tabela: ab_k3_gcc.md)

- Programy: `przed` = `engine_przed`, `k2` = `engine_k2`, `k3` = `engine_k3`
- Przypięcie: sched_setaffinity({2}) (WSL2: procesor wirtualny); priorytet: domyślny; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 3.2 min, 2026-10-17T19:34
- Zgodność wyników z `przed`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | przed [ms] | k2 [ms] | k3 [ms] | k2/przed | k3/przed | k3/k2 | zgodne |
|---|---|---|---|---|---|---|---|---|
| lava_test_3d | caSim | 1 273 [1 221–1 449] | 1 183 [1 150–1 372] | 1 012 [1 004–1 150] | ×0.929 | ×0.794 | ×0.855 | tak |
| lava_test_3d | total | 1 296 [1 242–1 476] | 1 207 [1 172–1 401] | 1 034 [1 027–1 178] | ×0.932 | ×0.798 | ×0.857 | tak |
| lava_test_3d | procWall | 1 297 [1 243–1 477] | 1 208 [1 173–1 402] | 1 035 [1 029–1 179] | ×0.932 | ×0.798 | ×0.857 | tak |
| lava_etna_real | caSim | 11 830 [10 877–12 058] | 10 221 [9 862–11 097] | 8 830 [8 582–9 710] | ×0.864 | ×0.746 | ×0.864 | tak |
| lava_etna_real | total | 11 865 [10 911–12 094] | 10 255 [9 895–11 132] | 8 862 [8 611–9 742] | ×0.864 | ×0.747 | ×0.864 | tak |
| lava_etna_real | procWall | 11 867 [10 913–12 096] | 10 257 [9 897–11 134] | 8 864 [8 613–9 744] | ×0.864 | ×0.747 | ×0.864 | tak |
| lava_mc_2d_ca | caSim | 42.6 [40.6–49.3] | 34.2 [32.7–38.7] | 27.1 [26.0–31.0] | ×0.802 | ×0.635 | ×0.792 | tak |
| lava_mc_2d_ca | total | 45.4 [42.9–52.3] | 36.7 [35.0–41.6] | 29.5 [28.1–33.6] | ×0.808 | ×0.649 | ×0.804 | tak |
| lava_mc_2d_ca | procWall | 46.4 [43.8–53.4] | 37.7 [35.9–42.9] | 30.3 [29.1–34.7] | ×0.812 | ×0.654 | ×0.805 | tak |

Tło (Windows, poza WSL): start 15% (WmiPrvSE.exe 205%, SRE.exe 84%, svchost.exe 36%), koniec 19%.
