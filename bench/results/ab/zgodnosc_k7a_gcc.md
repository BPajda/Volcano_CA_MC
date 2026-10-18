# Zgodność wyników `zgodnosc_k7a_gcc`

Programy: `przed_gcc` = `wsl:bench/baseline/engine_przed_gcc`, `k7a_gcc` = `wsl:bench/baseline/engine_k7a_gcc`
Porównanie bajt po bajcie z `przed_gcc` (bez times.json i config_used.json; stats.json bez ścieżki folderu wejściowego --mc-from; MSVC ↔ GCC: txt/csv bez różnicy końców linii CRLF/LF).

| Config | pliki | k7a_gcc = przed_gcc |
|---|---|---|
| `classic_ref` | ca_result.bin, ca_result.txt, stats.json | tak |
| `etna_3d` | ca_result.bin, stats.json | tak |
| `etna_real` | ca_result.bin, stats.json | tak |
| `etna_real_boczna` | ca_result.bin, stats.json | tak |
| `heightmap_kaldera` | ca_result.bin, mc_result.bin, mc_stats.csv, stats.json | tak |
| `heightmap_kanion` | ca_result.bin, stats.json | tak |
| `heightmap_podwojny` | ca_result.bin, stats.json | tak |
| `lava_mc_2d` | ca_result.bin, ca_result.txt, mc_result.bin, mc_result.txt, mc_stats.csv, stats.json | tak |
| `mc_basalt (--mc-from)` | mc_result.bin, mc_result.txt, mc_stats.csv, stats.json | tak |
| `lava_mc_3d` | ca_result.bin, ca_result.txt, mc_result.bin, mc_result.txt, mc_stats.csv, stats.json | tak |
| `mc_full_2d` | mc_result.bin, mc_result.txt, mc_stats.csv, stats.json | tak |
| `mc_full_3d` | mc_result.bin, mc_result.txt, mc_stats.csv, stats.json | tak |
| `test_2d` | ca_result.bin, ca_result.txt, stats.json | tak |
| `test_3d` | ca_result.bin, ca_result.txt, stats.json | tak |
| `wezuwiusz_real` | ca_result.bin, stats.json | tak |
