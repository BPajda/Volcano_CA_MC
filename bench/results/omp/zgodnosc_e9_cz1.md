# Zgodność wyników `zgodnosc_e9_cz1`

Programy: `e8` = `bench/baseline/engine_e8_msvc.exe`, `t1` = `build/Release/engine.exe`, `t8` = `build/Release/engine.exe` `--threads 8`, `e8_gcc` = `wsl:bench/baseline/engine_e8_gcc`, `t1_gcc` = `wsl:build-gcc-release/bin/engine`, `t8_gcc` = `wsl:build-gcc-release/bin/engine` `--threads 8`
Porównanie bajt po bajcie z `e8` (bez times.json i config_used.json; stats.json bez ścieżki folderu wejściowego --mc-from; MSVC ↔ GCC: txt/csv bez różnicy końców linii CRLF/LF).

| Config | pliki | t1 = e8 | t8 = e8 | e8_gcc = e8 | t1_gcc = e8 | t8_gcc = e8 |
|---|---|---|---|---|---|---|
| `classic_ref` | ca_result.bin, ca_result.txt, stats.json | tak | tak | tak | tak | tak |
| `etna_3d` | ca_result.bin, stats.json | tak | tak | tak | tak | tak |
| `etna_real` | ca_result.bin, stats.json | tak | tak | tak | tak | tak |
| `etna_real_boczna` | ca_result.bin, stats.json | tak | tak | tak | tak | tak |
| `heightmap_kanion` | ca_result.bin, stats.json | tak | tak | tak | tak | tak |
| `heightmap_podwojny` | ca_result.bin, stats.json | tak | tak | tak | tak | tak |
| `wezuwiusz_real` | ca_result.bin, stats.json | tak | tak | tak | tak | tak |
