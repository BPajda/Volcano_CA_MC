# Zgodność wyników `zgodnosc_e9_full`

Programy: `e8` = `bench/baseline/engine_e8_msvc.exe`, `t8` = `bench/baseline/engine_e9_msvc.exe` `--threads 8 --set parallel.schedule=guided`, `e8_gcc` = `wsl:bench/baseline/engine_e8_gcc`, `t8_gcc` = `wsl:bench/baseline/engine_e9_gcc` `--threads 8 --set parallel.schedule=dynamic`; nadpisania: ca.sweep=full
Porównanie bajt po bajcie z `e8` (bez times.json i config_used.json; stats.json bez ścieżki folderu wejściowego --mc-from; MSVC ↔ GCC: txt/csv bez różnicy końców linii CRLF/LF).

| Config | pliki | t8 = e8 | e8_gcc = e8 | t8_gcc = e8 |
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
| `test_2d` | ca_result.bin, ca_result.txt, stats.json | tak | tak | tak |
| `test_3d` | ca_result.bin, ca_result.txt, stats.json | tak | tak | tak |
| `wezuwiusz_real` | ca_result.bin, stats.json | tak | tak | tak |
