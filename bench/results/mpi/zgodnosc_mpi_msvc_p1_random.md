# Zgodność wyników `zgodnosc_mpi_msvc_p1_random`

Programy: `e9` = `bench/baseline/engine_e9_msvc.exe`, `m1` = `mpiexec -n 1` `build/Release/engine_mpi.exe`, `m1_gcc` = `mpiexec --allow-run-as-root --oversubscribe --bind-to none -n 1` `wsl:build-gcc-release/bin/engine_mpi`
Porównanie bajt po bajcie z `e9` (bez times.json i config_used.json; stats.json bez ścieżki folderu wejściowego --mc-from; MSVC ↔ GCC: txt/csv bez różnicy końców linii CRLF/LF).

| Config | pliki | m1 = e9 | m1_gcc = e9 |
|---|---|---|---|
| `classic_ref` | ca_result.bin, ca_result.txt, stats.json | tak | tak |
| `etna_3d` | ca_result.bin, stats.json | tak | tak |
| `etna_real` | ca_result.bin, stats.json | tak | tak |
| `etna_real_boczna` | ca_result.bin, stats.json | tak | tak |
| `heightmap_kaldera` | ca_result.bin, mc_result.bin, mc_stats.csv, stats.json | tak | tak |
| `heightmap_kanion` | ca_result.bin, stats.json | tak | tak |
| `heightmap_podwojny` | ca_result.bin, stats.json | tak | tak |
| `lava_mc_2d` | ca_result.bin, ca_result.txt, mc_result.bin, mc_result.txt, mc_stats.csv, stats.json | tak | tak |
| `mc_basalt (--mc-from)` | mc_result.bin, mc_result.txt, mc_stats.csv, stats.json | tak | tak |
| `lava_mc_3d` | ca_result.bin, ca_result.txt, mc_result.bin, mc_result.txt, mc_stats.csv, stats.json | tak | tak |
| `mc_full_2d` | mc_result.bin, mc_result.txt, mc_stats.csv, stats.json | tak | tak |
| `mc_full_3d` | mc_result.bin, mc_result.txt, mc_stats.csv, stats.json | tak | tak |
| `test_2d` | ca_result.bin, ca_result.txt, stats.json | tak | tak |
| `test_3d` | ca_result.bin, ca_result.txt, stats.json | tak | tak |
| `wezuwiusz_real` | ca_result.bin, stats.json | tak | tak |
