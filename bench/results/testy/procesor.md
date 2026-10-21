# Procesor i pamięć podręczna (etap 12)

Odczyt z systemu: `python bench/cache_info.py` (Windows) i `wsl -e python3 bench/cache_info.py` (WSL 2), 21.10.2026.

## Windows

Źródło: Windows `GetLogicalProcessorInformationEx` (RelationCache, RelationProcessorCore — klasa wydajności); procesor: Intel64 Family 6 Model 183 Stepping 1, GenuineIntel; procesorów logicznych: 32.

Klasy wydajności rdzeni: klasa 1 — procesory 0–15; klasa 0 — procesory 16–31

| Poziom | Typ | Rozmiar | Asocjacyjność | Linia [B] | Rdzenie | Procesory logiczne na egzemplarz | Egzemplarze (procesory) |
|---|---|---|---|---|---|---|---|
| L1 | Data | 48 KB | 12 | 64 | P | 2 | 8 (0–1; 2–3; 4–5; 6–7; …) |
| L1 | Data | 32 KB | 8 | 64 | E | 1 | 16 (16; 17; 18; 19; …) |
| L1 | Instruction | 32 KB | 8 | 64 | P | 2 | 8 (0–1; 2–3; 4–5; 6–7; …) |
| L1 | Instruction | 64 KB | 8 | 64 | E | 1 | 16 (16; 17; 18; 19; …) |
| L2 | Unified | 2 MB | 16 | 64 | P | 2 | 8 (0–1; 2–3; 4–5; 6–7; …) |
| L2 | Unified | 4 MB | 16 | 64 | E | 4 | 4 (16–19; 20–23; 24–27; 28–31) |
| L3 | Unified | 36 MB | 12 | 64 | E/P | 32 | 1 (0–31) |

## WSL 2 (procesory wirtualne)

Źródło: Linux `/sys/devices/system/cpu/cpu*/cache` (w WSL 2 — procesory wirtualne); procesor: x86_64; procesorów logicznych: 8.

| Poziom | Typ | Rozmiar | Asocjacyjność | Linia [B] | Rdzenie | Procesory logiczne na egzemplarz | Egzemplarze (procesory) |
|---|---|---|---|---|---|---|---|
| L1 | Data | 48 KB | 12 | 64 | — | 2 | 4 (0–1; 2–3; 4–5; 6–7) |
| L1 | Instruction | 32 KB | 8 | 64 | — | 2 | 4 (0–1; 2–3; 4–5; 6–7) |
| L2 | Unified | 2 MB | 16 | 64 | — | 2 | 4 (0–1; 2–3; 4–5; 6–7) |
| L3 | Unified | 36 MB | 12 | 64 | — | 8 | 1 (0–7) |
