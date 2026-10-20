# Zgodność wyników `zgodnosc_e9_szachownica`

Programy: `t1` = `bench/baseline/engine_e9_msvc.exe`, `t8` = `bench/baseline/engine_e9_msvc.exe` `--threads 8 --set parallel.schedule=dynamic`, `t3` = `bench/baseline/engine_e9_msvc.exe` `--threads 3 --set parallel.schedule=guided --set parallel.chunk=2`, `t1_gcc` = `wsl:bench/baseline/engine_e9_gcc`, `t8_gcc` = `wsl:bench/baseline/engine_e9_gcc` `--threads 8`; nadpisania: mc.update=checkerboard
Porównanie bajt po bajcie z `t1` (bez times.json i config_used.json; stats.json bez ścieżki folderu wejściowego --mc-from; MSVC ↔ GCC: txt/csv bez różnicy końców linii CRLF/LF).

| Config | pliki | t8 = t1 | t3 = t1 | t1_gcc = t1 | t8_gcc = t1 |
|---|---|---|---|---|---|
| `heightmap_kaldera` | ca_result.bin, mc_result.bin, mc_stats.csv, stats.json | tak | tak | tak | tak |
| `lava_mc_2d` | ca_result.bin, ca_result.txt, mc_result.bin, mc_result.txt, mc_stats.csv, stats.json | tak | tak | tak | tak |
| `mc_basalt (--mc-from)` | mc_result.bin, mc_result.txt, mc_stats.csv, stats.json | tak | tak | tak | tak |
| `lava_mc_3d` | ca_result.bin, ca_result.txt, mc_result.bin, mc_result.txt, mc_stats.csv, stats.json | tak | tak | tak | tak |
| `mc_full_2d` | mc_result.bin, mc_result.txt, mc_stats.csv, stats.json | tak | tak | tak | tak |
| `mc_full_3d` | mc_result.bin, mc_result.txt, mc_stats.csv, stats.json | tak | tak | tak | tak |
