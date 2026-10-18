# Zgodność wyników `zgodnosc_k7_cz1`

Programy: `przed` = `bench/baseline/engine_przed_msvc.exe`, `k7` = `bench/baseline/engine_k7_msvc.exe`, `przed_gcc` = `wsl:bench/baseline/engine_przed_gcc`, `k7_gcc` = `wsl:bench/baseline/engine_k7_gcc`
Porównanie bajt po bajcie z `przed` (bez times.json i config_used.json; stats.json bez ścieżki folderu wejściowego --mc-from; MSVC ↔ GCC: txt/csv bez różnicy końców linii CRLF/LF).

| Config | pliki | k7 = przed | przed_gcc = przed | k7_gcc = przed |
|---|---|---|---|---|
| `classic_ref` | ca_result.bin, ca_result.txt, stats.json | tak | tak | tak |
| `etna_3d` | ca_result.bin, stats.json | tak | tak | tak |
| `etna_real` | ca_result.bin, stats.json | tak | tak | tak |
| `etna_real_boczna` | ca_result.bin, stats.json | tak | tak | tak |
| `heightmap_kanion` | ca_result.bin, stats.json | tak | tak | tak |
| `heightmap_podwojny` | ca_result.bin, stats.json | tak | tak | tak |
| `wezuwiusz_real` | ca_result.bin, stats.json | tak | tak | tak |
