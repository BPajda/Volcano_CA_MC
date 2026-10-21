# Zgodność wyników `zgodnosc_mpi_gcc_full`

Programy: `e9_gcc` = `wsl:bench/baseline/engine_e9_gcc`, `m3` = `mpiexec --allow-run-as-root --oversubscribe --bind-to none -n 3` `wsl:bench/baseline/engine_mpi_e10_gcc`, `m8` = `mpiexec --allow-run-as-root --oversubscribe --bind-to none -n 8` `wsl:bench/baseline/engine_mpi_e10_gcc`, `m2x4` = `mpiexec --allow-run-as-root --oversubscribe --bind-to none -n 2` `wsl:bench/baseline/engine_mpi_e10_gcc` `--threads 4`; nadpisania: ca.sweep=full, mc.update=checkerboard
Porównanie bajt po bajcie z `e9_gcc` (bez times.json i config_used.json; stats.json bez ścieżki folderu wejściowego --mc-from; MSVC ↔ GCC: txt/csv bez różnicy końców linii CRLF/LF).

| Config | pliki | m3 = e9_gcc | m8 = e9_gcc | m2x4 = e9_gcc |
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
