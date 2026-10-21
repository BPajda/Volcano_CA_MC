# Test A/B `ab_e10a_gcc_ca_lava`

- Programy: `e9` = `engine_e9`, `e10` = `engine_e10a_gcc` (pierwsza wersja etapu 10, przed poprawką `frontRulesLayer<Shifted>`)
- Przypięcie: sched_setaffinity({2}) (WSL2: procesor wirtualny); priorytet: domyślny; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 0.1 min, 2026-10-20T13:25
- Zgodność wyników z `e9`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e9 [ms] | e10 [ms] | e10/e9 | zgodne |
|---|---|---|---|---|---|
| lava_test_3d | caSim | 86.6 [85.9–109] | 89.7 [89.1–114] | ×1.036 | tak |
| lava_test_3d | total | 97.6 [96.9–120] | 101 [100–127] | ×1.034 | tak |
| lava_test_3d | procWall | 100 [99.3–123] | 103 [102–130] | ×1.032 | tak |
| lava_etna_real | caSim | 78.2 [77.7–79.6] | 80.9 [79.9–84.0] | ×1.035 | tak |
| lava_etna_real | total | 122 [119–144] | 124 [121–132] | ×1.014 | tak |
| lava_etna_real | procWall | 126 [123–148] | 128 [125–136] | ×1.014 | tak |
| lava_mc_2d_ca | caSim | 5.50 [5.43–5.58] | 5.66 [5.57–5.77] | ×1.031 | tak |
| lava_mc_2d_ca | total | 7.45 [7.37–7.58] | 7.59 [7.53–7.81] | ×1.019 | tak |
| lava_mc_2d_ca | procWall | 9.51 [9.34–9.71] | 9.65 [9.40–9.92] | ×1.014 | tak |

Tło (Windows, poza WSL): start 11% (WmiPrvSE.exe 209%, python.exe 36%, svchost.exe 34%), koniec 12%.
