# Test A/B `ab_e10_gcc_ca_classic`

- Programy: `e9` = `engine_e9`, `e10` = `engine_e10`
- Przypięcie: sched_setaffinity({2}) (WSL2: procesor wirtualny); priorytet: domyślny; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 1.2 min, 2026-10-20T14:15
- Zgodność wyników z `e9`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e9 [ms] | e10 [ms] | e10/e9 | zgodne |
|---|---|---|---|---|---|
| classic_1000x1000_s100_vn | caSim | 113 [110–116] | 112 [110–114] | ×0.998 | tak |
| classic_1000x1000_s100_vn | save | 47.3 [46.8–66.2] | 47.4 [46.9–63.4] | ×1.003 | tak |
| classic_1000x1000_s100_vn | total | 181 [176–198] | 179 [175–192] | ×0.992 | tak |
| classic_1000x1000_s100_vn | procWall | 195 [191–213] | 194 [190–206] | ×0.994 | tak |
| classic_1000x1000_s100_moore | caSim | 121 [118–225] | 118 [117–191] | ×0.982 | tak |
| classic_1000x1000_s100_moore | total | 193 [184–313] | 187 [184–279] | ×0.968 | tak |
| classic_1000x1000_s100_moore | procWall | 208 [200–328] | 202 [199–293] | ×0.970 | tak |
| classic_100x100x100_s10_vn | caSim | 96.3 [93.0–98.4] | 97.3 [93.5–204] | ×1.010 | tak |
| classic_100x100x100_s10_vn | save | 47.5 [45.5–178] | 47.0 [45.6–71.5] | ×0.990 | tak |
| classic_100x100x100_s10_vn | total | 164 [159–297] | 167 [161–289] | ×1.017 | tak |
| classic_100x100x100_s10_vn | procWall | 180 [176–313] | 183 [177–304] | ×1.015 | tak |
| classic_100x100x100_s10_moore | caSim | 188 [186–193] | 187 [185–197] | ×0.996 | tak |
| classic_100x100x100_s10_moore | total | 258 [252–348] | 257 [252–265] | ×0.996 | tak |
| classic_100x100x100_s10_moore | procWall | 274 [269–364] | 273 [268–282] | ×0.996 | tak |
| classic_300x300x300_s100_vn | caSim | 3 723 [3 500–3 864] | 3 508 [3 460–3 618] | ×0.942 | tak |
| classic_300x300x300_s100_vn | save | 677 [621–907] | 730 [689–1 192] | ×1.078 | tak |
| classic_300x300x300_s100_vn | total | 4 851 [4 656–5 139] | 4 765 [4 651–5 106] | ×0.982 | tak |
| classic_300x300x300_s100_vn | procWall | 5 204 [5 007–5 492] | 5 135 [5 003–5 459] | ×0.987 | tak |

Tło (Windows, poza WSL): start 18% (WmiPrvSE.exe 208%, python.exe 41%, svchost.exe 35%), koniec 19%.
