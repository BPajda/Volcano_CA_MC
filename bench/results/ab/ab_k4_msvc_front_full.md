# Test A/B `ab_k4_msvc_front_full`

Automat frontalny vs pełny przebieg w tym samym programie (engine_k4_msvc.exe, ca.sweep = full / front), MSVC.

- Tabela z pomiaru `ab_k4_msvc_ca_lava_raw.csv`, `ab_k4_msvc_ca_classic_raw.csv` (te same przebiegi naprzemienne; programy k4_full, k4; warunki pomiaru i tło — w nagłówku `ab_k4_msvc_ca_lava.md`, `ab_k4_msvc_ca_classic.md`)

| Przypadek | miara | k4_full [ms] | k4 [ms] | k4/k4_full | zgodne |
|---|---|---|---|---|---|
| lava_test_3d | caSim | 1 164 [1 141–1 189] | 41.7 [40.4–48.5] | ×0.036 | tak |
| lava_test_3d | total | 1 195 [1 173–1 220] | 71.9 [70.8–88.1] | ×0.060 | tak |
| lava_test_3d | procWall | 1 203 [1 181–1 227] | 79.6 [78.8–95.9] | ×0.066 | tak |
| lava_etna_real | caSim | 10 074 [10 042–10 199] | 39.1 [37.4–40.9] | ×0.004 | tak |
| lava_etna_real | total | 10 125 [10 075–10 234] | 68.8 [64.9–72.6] | ×0.007 | tak |
| lava_etna_real | procWall | 10 134 [10 084–10 244] | 78.7 [73.6–81.7] | ×0.008 | tak |
| lava_mc_2d_ca | caSim | 35.4 [33.5–37.8] | 2.36 [2.29–2.45] | ×0.066 | tak |
| lava_mc_2d_ca | total | 41.5 [39.3–43.8] | 7.71 [7.00–8.49] | ×0.186 | tak |
| lava_mc_2d_ca | procWall | 49.0 [47.0–51.4] | 16.1 [14.8–20.7] | ×0.330 | tak |
| classic_1000x1000_s100_vn | caSim | 457 [449–510] | 47.5 [46.2–49.5] | ×0.104 | tak |
| classic_1000x1000_s100_vn | save | 135 [132–139] | 135 [131–142] | ×0.997 | tak |
| classic_1000x1000_s100_vn | total | 602 [592–656] | 191 [186–201] | ×0.318 | tak |
| classic_1000x1000_s100_vn | procWall | 615 [605–669] | 206 [200–218] | ×0.334 | tak |
| classic_1000x1000_s100_moore | caSim | 376 [372–379] | 53.1 [52.4–54.7] | ×0.141 | tak |
| classic_1000x1000_s100_moore | total | 518 [516–524] | 196 [194–206] | ×0.377 | tak |
| classic_1000x1000_s100_moore | procWall | 531 [529–537] | 209 [207–221] | ×0.393 | tak |
| classic_100x100x100_s10_vn | caSim | 246 [241–253] | 41.1 [40.4–45.7] | ×0.167 | tak |
| classic_100x100x100_s10_vn | save | 128 [126–132] | 131 [127–139] | ×1.018 | tak |
| classic_100x100x100_s10_vn | total | 387 [378–397] | 182 [176–189] | ×0.469 | tak |
| classic_100x100x100_s10_vn | procWall | 400 [391–411] | 194 [189–202] | ×0.486 | tak |
| classic_100x100x100_s10_moore | caSim | 318 [314–323] | 88.5 [86.1–96.8] | ×0.278 | tak |
| classic_100x100x100_s10_moore | total | 463 [451–487] | 230 [225–247] | ×0.495 | tak |
| classic_100x100x100_s10_moore | procWall | 476 [464–499] | 242 [238–273] | ×0.509 | tak |
| classic_300x300x300_s100_vn | caSim | 9 690 [9 634–9 799] | 1 946 [1 926–1 984] | ×0.201 | tak |
| classic_300x300x300_s100_vn | save | 303 [300–323] | 302 [291–343] | ×0.997 | tak |
| classic_300x300x300_s100_vn | total | 10 274 [10 216–10 402] | 2 452 [2 448–2 549] | ×0.239 | tak |
| classic_300x300x300_s100_vn | procWall | 10 416 [10 357–10 540] | 2 591 [2 588–2 690] | ×0.249 | tak |
