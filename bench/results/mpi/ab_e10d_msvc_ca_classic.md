# Test A/B `ab_e10d_msvc_ca_classic`

- Programy: `e9` = `engine_e9_msvc.exe`, `e10` = wersja e10d (`frontRulesLayer<Shifted>`, przed `frontStepSequential<Strip>`; binarka `engine_e10d_*`)
- Przypięcie: psutil.cpu_affinity([2]); priorytet: HIGH_PRIORITY_CLASS; kolejność naprzemienna (odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 1.3 min, 2026-10-20T13:49
- Tło: start 23% CPU (WmiPrvSE.exe 218%, CompatTelRunner.exe 95%, System 44%), koniec 16%
- Zgodność wyników z `e9`: wszystkie przebiegi bitowo zgodne

| Przypadek | miara | e9 [ms] | e10 [ms] | e10/e9 | zgodne |
|---|---|---|---|---|---|
| classic_1000x1000_s100_vn | caSim | 118 [116–124] | 119 [116–127] | ×1.011 | tak |
| classic_1000x1000_s100_vn | save | 83.0 [80.9–86.0] | 85.2 [82.1–87.2] | ×1.027 | tak |
| classic_1000x1000_s100_vn | total | 220 [217–238] | 224 [219–236] | ×1.018 | tak |
| classic_1000x1000_s100_vn | procWall | 253 [248–266] | 253 [247–273] | ×1.002 | tak |
| classic_1000x1000_s100_moore | caSim | 127 [123–140] | 129 [125–134] | ×1.009 | tak |
| classic_1000x1000_s100_moore | total | 233 [225–251] | 235 [230–249] | ×1.011 | tak |
| classic_1000x1000_s100_moore | procWall | 270 [257–284] | 268 [259–287] | ×0.990 | tak |
| classic_100x100x100_s10_vn | caSim | 97.0 [94.6–101] | 98.4 [93.8–104] | ×1.015 | tak |
| classic_100x100x100_s10_vn | save | 81.3 [79.2–91.8] | 82.0 [80.3–90.4] | ×1.008 | tak |
| classic_100x100x100_s10_vn | total | 200 [195–210] | 201 [195–207] | ×1.002 | tak |
| classic_100x100x100_s10_vn | procWall | 230 [224–242] | 231 [223–235] | ×1.004 | tak |
| classic_100x100x100_s10_moore | caSim | 197 [191–207] | 200 [195–204] | ×1.012 | tak |
| classic_100x100x100_s10_moore | total | 301 [293–314] | 302 [295–308] | ×1.004 | tak |
| classic_100x100x100_s10_moore | procWall | 332 [322–346] | 334 [325–340] | ×1.005 | tak |
| classic_300x300x300_s100_vn | caSim | 3 476 [3 413–3 511] | 3 491 [3 416–3 512] | ×1.004 | tak |
| classic_300x300x300_s100_vn | save | 570 [554–607] | 586 [562–762] | ×1.028 | tak |
| classic_300x300x300_s100_vn | total | 4 519 [4 409–4 549] | 4 542 [4 414–4 644] | ×1.005 | tak |
| classic_300x300x300_s100_vn | procWall | 4 820 [4 701–4 861] | 4 835 [4 708–4 943] | ×1.003 | tak |
