# Zgodność wyników `zgodnosc_e10_engine`

Programy: `e9` = `bench/baseline/engine_e9_msvc.exe`, `e10` = `bench/baseline/engine_e10_msvc.exe`, `e9_gcc` = `wsl:bench/baseline/engine_e9_gcc`, `e10_gcc` = `wsl:bench/baseline/engine_e10_gcc`
Porównanie bajt po bajcie z `e9` (bez times.json i config_used.json; stats.json bez ścieżki folderu wejściowego --mc-from; MSVC ↔ GCC: txt/csv bez różnicy końców linii CRLF/LF).

| Config | pliki | e10 = e9 | e9_gcc = e9 | e10_gcc = e9 |
|---|---|---|---|---|
| `classic_ref` | ca_result.bin, ca_result.txt, stats.json | tak | tak | tak |
| `etna_3d` | ca_result.bin, stats.json | tak | tak | tak |
| `etna_real` | ca_result.bin, stats.json | tak | tak | tak |
| `etna_real_boczna` | ca_result.bin, stats.json | tak | tak | tak |
| `heightmap_kaldera` | ca_result.bin, mc_result.bin, mc_stats.csv, stats.json | tak | tak | tak |
| `heightmap_kanion` | ca_result.bin, stats.json | tak | tak | tak |
| `heightmap_podwojny` | ca_result.bin, stats.json | tak | tak | tak |
| `lava_mc_2d` | ca_result.bin, ca_result.txt, mc_result.bin, mc_result.txt, mc_stats.csv, stats.json | tak | tak | tak |
| `mc_basalt (--mc-from)` | mc_result.bin, mc_result.txt, mc_stats.csv, stats.json | tak | tak | tak |
| `lava_mc_3d` | ca_result.bin, ca_result.txt, mc_result.bin, mc_result.txt, mc_stats.csv, stats.json | tak | tak | tak |
| `mc_full_2d` | mc_result.bin, mc_result.txt, mc_stats.csv, stats.json | tak | tak | tak |
| `mc_full_3d` | mc_result.bin, mc_result.txt, mc_stats.csv, stats.json | tak | tak | tak |
| `test_2d` | ca_result.bin, ca_result.txt, stats.json | tak | tak | tak |
| `test_3d` | ca_result.bin, ca_result.txt, stats.json | tak | tak | tak |
| `wezuwiusz_real` | ca_result.bin, stats.json | tak | tak | tak |
