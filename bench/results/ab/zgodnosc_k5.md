# Zgodność wyników `zgodnosc_k5`

Programy: `przed` = `bench/baseline/engine_przed_msvc.exe`, `k5` = `bench/baseline/engine_k5_msvc.exe`, `przed_gcc` = `wsl:bench/baseline/engine_przed_gcc`, `k5_gcc` = `wsl:bench/baseline/engine_k5_gcc`
Porównanie bajt po bajcie z `przed` (bez times.json i config_used.json; stats.json bez ścieżki folderu wejściowego --mc-from; MSVC ↔ GCC: txt/csv bez różnicy końców linii CRLF/LF).

| Config | pliki | k5 = przed | przed_gcc = przed | k5_gcc = przed |
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

Tabela scalona z części: `zgodnosc_k5_cz1.md`, `zgodnosc_k5_cz2.md` (ta sama lista configów co w jednym przebiegu, podział na części — limit czasu jednego polecenia).
