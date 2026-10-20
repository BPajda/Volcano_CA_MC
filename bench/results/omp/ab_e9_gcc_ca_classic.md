# Test A/B `ab_e9_gcc_ca_classic`

- Programy: `e8` = `engine_e8`, `e9` = `engine_e9`
- Przypięcie: sched_setaffinity({2}) (WSL2: procesor wirtualny); priorytet: domyślny; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 1.2 min, 2026-10-18T05:24
- Zgodność wyników z `e8`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e8 [ms] | e9 [ms] | e9/e8 | zgodne |
|---|---|---|---|---|---|
| classic_1000x1000_s100_vn | caSim | 122 [108–129] | 117 [108–123] | ×0.961 | tak |
| classic_1000x1000_s100_vn | save | 51.1 [43.9–69.8] | 56.4 [46.3–70.3] | ×1.103 | tak |
| classic_1000x1000_s100_vn | total | 200 [171–284] | 198 [174–213] | ×0.993 | tak |
| classic_1000x1000_s100_vn | procWall | 216 [185–300] | 215 [188–228] | ×0.996 | tak |
| classic_1000x1000_s100_moore | caSim | 128 [118–134] | 123 [115–132] | ×0.965 | tak |
| classic_1000x1000_s100_moore | total | 196 [183–208] | 199 [182–205] | ×1.014 | tak |
| classic_1000x1000_s100_moore | procWall | 213 [197–224] | 215 [196–222] | ×1.008 | tak |
| classic_100x100x100_s10_vn | caSim | 99.1 [90.0–184] | 96.2 [91.0–216] | ×0.970 | tak |
| classic_100x100x100_s10_vn | save | 48.5 [41.9–64.5] | 47.0 [43.6–65.5] | ×0.969 | tak |
| classic_100x100x100_s10_vn | total | 168 [150–264] | 163 [153–300] | ×0.968 | tak |
| classic_100x100x100_s10_vn | procWall | 185 [165–280] | 180 [168–317] | ×0.975 | tak |
| classic_100x100x100_s10_moore | caSim | 193 [174–271] | 193 [180–261] | ×1.001 | tak |
| classic_100x100x100_s10_moore | total | 260 [236–349] | 263 [244–342] | ×1.012 | tak |
| classic_100x100x100_s10_moore | procWall | 277 [252–364] | 280 [260–357] | ×1.010 | tak |
| classic_300x300x300_s100_vn | caSim | 3 761 [3 702–3 883] | 3 635 [3 551–3 709] | ×0.966 | tak |
| classic_300x300x300_s100_vn | save | 649 [627–865] | 710 [616–808] | ×1.094 | tak |
| classic_300x300x300_s100_vn | total | 4 984 [4 898–5 076] | 4 856 [4 579–4 898] | ×0.974 | tak |
| classic_300x300x300_s100_vn | procWall | 5 345 [5 255–5 434] | 5 215 [4 916–5 273] | ×0.976 | tak |

Tło (Windows, poza WSL): start 21% (WmiPrvSE.exe 223%, inny program 94%, Code.exe 54%), koniec 26%.
