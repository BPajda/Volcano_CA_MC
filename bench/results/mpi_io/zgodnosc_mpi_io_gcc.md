# Zgodność wyników `zgodnosc_mpi_io_gcc`

Programy: `e10_m3` = `mpiexec --allow-run-as-root --oversubscribe --bind-to none -n 3` `wsl:bench/baseline/engine_mpi_e10_gcc`, `m3` = `mpiexec --allow-run-as-root --oversubscribe --bind-to none -n 3` `wsl:bench/baseline/engine_mpi_e11_gcc`, `d3` = `mpiexec --allow-run-as-root --oversubscribe --bind-to none -n 3` `wsl:bench/baseline/engine_mpi_e11_gcc` `--set mpi.pack=datatype`, `s3` = `mpiexec --allow-run-as-root --oversubscribe --bind-to none -n 3` `wsl:bench/baseline/engine_mpi_e11_gcc` `--set mpi.bcast=struct`, `i3` = `mpiexec --allow-run-as-root --oversubscribe --bind-to none -n 3` `wsl:bench/baseline/engine_mpi_e11_gcc` `--set mpi.io=mpiio`, `dsi1` = `mpiexec --allow-run-as-root --oversubscribe --bind-to none -n 1` `wsl:bench/baseline/engine_mpi_e11_gcc` `--set mpi.pack=datatype --set mpi.bcast=struct --set mpi.io=mpiio`, `dsi3` = `mpiexec --allow-run-as-root --oversubscribe --bind-to none -n 3` `wsl:bench/baseline/engine_mpi_e11_gcc` `--set mpi.pack=datatype --set mpi.bcast=struct --set mpi.io=mpiio`, `dsi8` = `mpiexec --allow-run-as-root --oversubscribe --bind-to none -n 8` `wsl:bench/baseline/engine_mpi_e11_gcc` `--set mpi.pack=datatype --set mpi.bcast=struct --set mpi.io=mpiio`, `dsi2x4` = `mpiexec --allow-run-as-root --oversubscribe --bind-to none -n 2` `wsl:bench/baseline/engine_mpi_e11_gcc` `--set mpi.pack=datatype --set mpi.bcast=struct --set mpi.io=mpiio --threads 4`, `dsi8c` = `mpiexec --allow-run-as-root --oversubscribe --bind-to none -n 8` `wsl:bench/baseline/engine_mpi_e11_gcc` `--set mpi.pack=datatype --set mpi.bcast=struct --set mpi.io=mpiio --set mpi.exchange=changed`; nadpisania: mc.update=checkerboard
Porównanie bajt po bajcie z `e10_m3` (bez times.json i config_used.json; stats.json bez ścieżki folderu wejściowego --mc-from; MSVC ↔ GCC: txt/csv bez różnicy końców linii CRLF/LF; programy WSL piszą na ext4).

| Config | pliki | m3 = e10_m3 | d3 = e10_m3 | s3 = e10_m3 | i3 = e10_m3 | dsi1 = e10_m3 | dsi3 = e10_m3 | dsi8 = e10_m3 | dsi2x4 = e10_m3 | dsi8c = e10_m3 |
|---|---|---|---|---|---|---|---|---|---|---|
| `classic_ref` | ca_result.bin, ca_result.txt, stats.json | tak | tak | tak | tak | tak | tak | tak | tak | tak |
| `etna_3d` | ca_result.bin, stats.json | tak | tak | tak | tak | tak | tak | tak | tak | tak |
| `etna_real` | ca_result.bin, stats.json | tak | tak | tak | tak | tak | tak | tak | tak | tak |
| `etna_real_boczna` | ca_result.bin, stats.json | tak | tak | tak | tak | tak | tak | tak | tak | tak |
| `heightmap_kaldera` | ca_result.bin, mc_result.bin, mc_stats.csv, stats.json | tak | tak | tak | tak | tak | tak | tak | tak | tak |
| `heightmap_kanion` | ca_result.bin, stats.json | tak | tak | tak | tak | tak | tak | tak | tak | tak |
| `heightmap_podwojny` | ca_result.bin, stats.json | tak | tak | tak | tak | tak | tak | tak | tak | tak |
| `lava_mc_2d` | ca_result.bin, ca_result.txt, mc_result.bin, mc_result.txt, mc_stats.csv, stats.json | tak | tak | tak | tak | tak | tak | tak | tak | tak |
| `mc_basalt (--mc-from)` | mc_result.bin, mc_result.txt, mc_stats.csv, stats.json | tak | tak | tak | tak | tak | tak | tak | tak | tak |
| `lava_mc_3d` | ca_result.bin, ca_result.txt, mc_result.bin, mc_result.txt, mc_stats.csv, stats.json | tak | tak | tak | tak | tak | tak | tak | tak | tak |
| `mc_full_2d` | mc_result.bin, mc_result.txt, mc_stats.csv, stats.json | tak | tak | tak | tak | tak | tak | tak | tak | tak |
| `mc_full_3d` | mc_result.bin, mc_result.txt, mc_stats.csv, stats.json | tak | tak | tak | tak | tak | tak | tak | tak | tak |
| `test_2d` | ca_result.bin, ca_result.txt, stats.json | tak | tak | tak | tak | tak | tak | tak | tak | tak |
| `test_3d` | ca_result.bin, ca_result.txt, stats.json | tak | tak | tak | tak | tak | tak | tak | tak | tak |
| `wezuwiusz_real` | ca_result.bin, stats.json | tak | tak | tak | tak | tak | tak | tak | tak | tak |
