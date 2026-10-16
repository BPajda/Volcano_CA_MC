# bench — profil aplikacji i testy wydajności

Opis metody i wyników: [`../docs/etap-3-profilowanie.md`](../docs/etap-3-profilowanie.md).

| Plik | Co robi |
|---|---|
| `run_profile.py` | macierz pomiarów: generuje configi, uruchamia `engine` (MSVC, opcjonalnie GCC przez WSL), 3 powtórzenia, przypięcie do rdzenia P, zbiera `times.json` -> `results/profile_<data>.csv` (+ `_raw.csv`, `_meta.json`, `_benchmark.csv`) |
| `plot_profile.py` | wykresy `../docs/img/profile_*.png` z najnowszego (lub wskazanego `--csv`) zestawu |
| `profile_gcc.sh` | profilowanie GCC w WSL: gprof (`gcc-profile`, `gcc-profile-noinline`) i callgrind (`gcc-o2`, `gcc-o2-noinline`) -> `profiles/` (`SKIP_GPROF=1` — sam callgrind) |
| `profile_msvc.py` | profilowanie MSVC: kolektor CPU Usage profilera Visual Studio (`VSDiagnostics.exe`) + `xperf` (symbole z PDB) na `msvc-profile`, `msvc-profile-noinline` -> `profiles/msvc_*.txt` |
| `micro/mc_kernels.cpp` | mikrobenchmark składników próby MC i indeksowania (cel CMake `mc_kernels`, te same flagi co silnik) — wyjaśnienie różnicy GCC vs MSVC |
| `ab_progress.py` | test A/B narzutu opcji `--progress` (stary program, nowy bez flagi, nowy z flagą; przemiennie, przypięte) |
| `results/` | dane pomiarowe (CSV, meta); **`profile_2026-10-09*` = punkt odniesienia dla dalszej optymalizacji — nie nadpisywać** |
| `profiles/` | raporty gprof (profile płaskie) i callgrind (tekst), profil MSVC (xperf), mikrobenchmark, analiza GCC vs MSVC (`gcc_vs_msvc_mc.txt`, `asm/`), rdzeń P vs E; pełne grafy wywołań gprof odtwarza `profile_gcc.sh` |

Szybki start (z katalogu projektu):

```
python bench/run_profile.py --quick
python bench/run_profile.py --full --gcc
python bench/plot_profile.py
wsl -e bash -lc "bash bench/profile_gcc.sh"
python bench/profile_msvc.py
```

`wsl` uruchomiony z katalogu projektu startuje w tym samym katalogu (`/mnt/<dysk>/…`), więc ścieżka nie jest potrzebna.

Zasady pomiaru: tylko buildy Release (Debug i -O0 wyłącznie w porównaniu kompilatorów), przypięcie do
jednego rdzenia wydajnościowego, ≥ 3 powtórzenia (mediana, min–max, odchylenie), pomiary < 5 ms traktowane
jako zaszumione. Pomiar czasu faz wewnątrz CA/MC tylko z `--timing-detail` — stoper w pętli kroku zmieniał
kod generowany przez MSVC (krok lawy +10%), dlatego krok z pomiarem faz ma osobną ścieżkę (`LavaCA::stepTimed`).

Planowany dalszy rozwój: skrypt pomiaru przyspieszenia i efektywności wersji równoległych (OpenMP, MPI).
