# Test A/B `ab_k4_gcc_front_full`

Automat frontalny vs pełny przebieg w tym samym programie (engine_k4_gcc, ca.sweep = full / front), GCC.

- Tabela z pomiaru `ab_k4_gcc_ca_lava_raw.csv`, `ab_k4_gcc_ca_classic_raw.csv` (te same przebiegi naprzemienne; programy k4_full, k4; warunki pomiaru i tło — w nagłówku `ab_k4_gcc_ca_lava.md`, `ab_k4_gcc_ca_classic.md`)

| Przypadek | miara | k4_full [ms] | k4 [ms] | k4/k4_full | zgodne |
|---|---|---|---|---|---|
| lava_test_3d | caSim | 1 087 [984–1 161] | 37.5 [34.6–41.5] | ×0.035 | tak |
| lava_test_3d | total | 1 114 [1 006–1 187] | 61.3 [56.4–68.2] | ×0.055 | tak |
| lava_test_3d | procWall | 1 115 [1 007–1 189] | 62.6 [57.5–69.4] | ×0.056 | tak |
| lava_etna_real | caSim | 9 328 [8 558–9 351] | 34.7 [33.4–36.9] | ×0.004 | tak |
| lava_etna_real | total | 9 367 [8 590–9 382] | 59.0 [54.7–71.2] | ×0.006 | tak |
| lava_etna_real | procWall | 9 369 [8 592–9 384] | 60.9 [56.6–73.2] | ×0.006 | tak |
| lava_mc_2d_ca | caSim | 24.8 [22.9–27.4] | 2.38 [2.13–3.82] | ×0.096 | tak |
| lava_mc_2d_ca | total | 27.4 [25.5–30.8] | 4.78 [4.50–6.33] | ×0.174 | tak |
| lava_mc_2d_ca | procWall | 28.5 [26.5–32.2] | 5.83 [5.40–7.17] | ×0.204 | tak |
| classic_1000x1000_s100_vn | caSim | 382 [374–523] | 44.6 [41.7–56.4] | ×0.117 | tak |
| classic_1000x1000_s100_vn | save | 109 [100–141] | 104 [100–126] | ×0.956 | tak |
| classic_1000x1000_s100_vn | total | 499 [491–680] | 156 [151–194] | ×0.313 | tak |
| classic_1000x1000_s100_vn | procWall | 505 [498–690] | 162 [157–201] | ×0.321 | tak |
| classic_1000x1000_s100_moore | caSim | 324 [313–338] | 49.6 [45.7–65.0] | ×0.153 | tak |
| classic_1000x1000_s100_moore | total | 446 [429–463] | 164 [158–188] | ×0.367 | tak |
| classic_1000x1000_s100_moore | procWall | 453 [436–472] | 170 [164–195] | ×0.376 | tak |
| classic_100x100x100_s10_vn | caSim | 205 [200–215] | 38.4 [35.9–40.6] | ×0.187 | tak |
| classic_100x100x100_s10_vn | save | 105 [98.3–119] | 104 [102–113] | ×0.996 | tak |
| classic_100x100x100_s10_vn | total | 321 [315–343] | 151 [147–162] | ×0.471 | tak |
| classic_100x100x100_s10_vn | procWall | 327 [321–350] | 158 [154–169] | ×0.482 | tak |
| classic_100x100x100_s10_moore | caSim | 229 [223–248] | 77.2 [74.1–87.5] | ×0.337 | tak |
| classic_100x100x100_s10_moore | total | 346 [337–370] | 193 [187–210] | ×0.558 | tak |
| classic_100x100x100_s10_moore | procWall | 353 [344–377] | 199 [194–216] | ×0.565 | tak |
| classic_300x300x300_s100_vn | caSim | 8 371 [8 284–8 507] | 1 946 [1 824–2 176] | ×0.233 | tak |
| classic_300x300x300_s100_vn | save | 302 [296–318] | 303 [287–370] | ×1.003 | tak |
| classic_300x300x300_s100_vn | total | 8 895 [8 813–9 026] | 2 426 [2 358–2 734] | ×0.273 | tak |
| classic_300x300x300_s100_vn | procWall | 9 046 [8 950–9 169] | 2 569 [2 499–2 879] | ×0.284 | tak |
