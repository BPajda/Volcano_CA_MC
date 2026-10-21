# Test A/B `ab_e10d_gcc_ca_classic`

- Programy: `e9` = `engine_e9`, `e10` = wersja e10d (`frontRulesLayer<Shifted>`, przed `frontStepSequential<Strip>`; binarka `engine_e10d_*`)
- Przypięcie: sched_setaffinity({2}) (WSL2: procesor wirtualny); priorytet: domyślny; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 1.2 min, 2026-10-20T13:53
- Zgodność wyników z `e9`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e9 [ms] | e10 [ms] | e10/e9 | zgodne |
|---|---|---|---|---|---|
| classic_1000x1000_s100_vn | caSim | 115 [113–222] | 117 [115–230] | ×1.016 | tak |
| classic_1000x1000_s100_vn | save | 53.8 [46.7–71.7] | 63.9 [46.9–67.0] | ×1.189 | tak |
| classic_1000x1000_s100_vn | total | 191 [179–313] | 200 [181–315] | ×1.047 | tak |
| classic_1000x1000_s100_vn | procWall | 206 [194–328] | 215 [196–330] | ×1.042 | tak |
| classic_1000x1000_s100_moore | caSim | 121 [118–128] | 130 [125–178] | ×1.073 | tak |
| classic_1000x1000_s100_moore | total | 192 [184–203] | 200 [192–269] | ×1.038 | tak |
| classic_1000x1000_s100_moore | procWall | 207 [200–219] | 215 [207–284] | ×1.036 | tak |
| classic_100x100x100_s10_vn | caSim | 97.3 [93.3–205] | 103 [99.4–198] | ×1.055 | tak |
| classic_100x100x100_s10_vn | save | 48.7 [46.1–60.3] | 48.1 [45.6–66.2] | ×0.987 | tak |
| classic_100x100x100_s10_vn | total | 166 [160–284] | 171 [167–282] | ×1.029 | tak |
| classic_100x100x100_s10_vn | procWall | 183 [177–301] | 188 [183–298] | ×1.027 | tak |
| classic_100x100x100_s10_moore | caSim | 192 [186–207] | 222 [217–242] | ×1.158 | tak |
| classic_100x100x100_s10_moore | total | 261 [253–368] | 293 [285–314] | ×1.124 | tak |
| classic_100x100x100_s10_moore | procWall | 277 [269–386] | 310 [301–331] | ×1.119 | tak |
| classic_300x300x300_s100_vn | caSim | 3 626 [3 499–3 807] | 3 858 [3 693–4 009] | ×1.064 | tak |
| classic_300x300x300_s100_vn | save | 745 [705–964] | 829 [649–983] | ×1.113 | tak |
| classic_300x300x300_s100_vn | total | 5 085 [4 772–5 103] | 5 165 [5 065–5 318] | ×1.016 | tak |
| classic_300x300x300_s100_vn | procWall | 5 451 [5 148–5 479] | 5 534 [5 465–5 699] | ×1.015 | tak |

Tło (Windows, poza WSL): start 22% (WmiPrvSE.exe 217%, System 64%, svchost.exe 52%), koniec 29%.
