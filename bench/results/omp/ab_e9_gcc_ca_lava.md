# Test A/B `ab_e9_gcc_ca_lava`

- Programy: `e8` = `engine_e8`, `e9` = `engine_e9`
- Przypięcie: sched_setaffinity({2}) (WSL2: procesor wirtualny); priorytet: domyślny; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 0.1 min, 2026-10-18T05:23
- Zgodność wyników z `e8`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e8 [ms] | e9 [ms] | e9/e8 | zgodne |
|---|---|---|---|---|---|
| lava_test_3d | caSim | 94.4 [92.2–97.3] | 96.6 [95.3–99.8] | ×1.023 | tak |
| lava_test_3d | total | 107 [104–112] | 110 [108–113] | ×1.022 | tak |
| lava_test_3d | procWall | 110 [107–115] | 112 [111–116] | ×1.024 | tak |
| lava_etna_real | caSim | 86.1 [83.5–94.6] | 89.1 [86.7–92.3] | ×1.035 | tak |
| lava_etna_real | total | 137 [131–159] | 139 [134–165] | ×1.011 | tak |
| lava_etna_real | procWall | 142 [136–164] | 144 [138–169] | ×1.014 | tak |
| lava_mc_2d_ca | caSim | 6.12 [5.96–6.95] | 6.26 [6.08–6.41] | ×1.023 | tak |
| lava_mc_2d_ca | total | 8.38 [8.16–9.12] | 8.54 [8.25–8.72] | ×1.018 | tak |
| lava_mc_2d_ca | procWall | 10.6 [10.3–11.3] | 10.8 [10.4–11.2] | ×1.021 | tak |

Tło (Windows, poza WSL): start 21% (WmiPrvSE.exe 218%, inny program 89%, python.exe 52%), koniec 26%.
