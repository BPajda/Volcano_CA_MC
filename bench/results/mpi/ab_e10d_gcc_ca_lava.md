# Test A/B `ab_e10d_gcc_ca_lava`

- Programy: `e9` = `engine_e9`, `e10` = wersja e10d (`frontRulesLayer<Shifted>`, przed `frontStepSequential<Strip>`; binarka `engine_e10d_*`)
- Przypięcie: sched_setaffinity({2}) (WSL2: procesor wirtualny); priorytet: domyślny; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 0.1 min, 2026-10-20T13:52
- Zgodność wyników z `e9`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e9 [ms] | e10 [ms] | e10/e9 | zgodne |
|---|---|---|---|---|---|
| lava_test_3d | caSim | 95.7 [93.9–99.7] | 99.4 [97.5–103] | ×1.039 | tak |
| lava_test_3d | total | 108 [106–115] | 112 [110–116] | ×1.037 | tak |
| lava_test_3d | procWall | 110 [109–118] | 114 [112–118] | ×1.036 | tak |
| lava_etna_real | caSim | 86.2 [84.6–93.1] | 90.5 [88.6–94.6] | ×1.051 | tak |
| lava_etna_real | total | 135 [132–157] | 138 [135–174] | ×1.024 | tak |
| lava_etna_real | procWall | 139 [136–161] | 143 [140–179] | ×1.024 | tak |
| lava_mc_2d_ca | caSim | 6.07 [5.93–6.31] | 6.32 [6.16–7.33] | ×1.043 | tak |
| lava_mc_2d_ca | total | 8.27 [8.09–8.70] | 8.46 [8.29–9.55] | ×1.022 | tak |
| lava_mc_2d_ca | procWall | 10.5 [10.2–10.9] | 10.7 [10.5–11.7] | ×1.021 | tak |

Tło (Windows, poza WSL): start 20% (WmiPrvSE.exe 218%, System 50%, python.exe 41%), koniec 16%.
