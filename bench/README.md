# bench — profil aplikacji i testy wydajności

Opis metody i wyników: [`../docs/etap-3-profilowanie.md`](../docs/etap-3-profilowanie.md) (profil),
[`../docs/etap-8-optymalizacja-sekwencyjna.md`](../docs/etap-8-optymalizacja-sekwencyjna.md) (optymalizacja, testy A/B),
[`../docs/etap-9-openmp.md`](../docs/etap-9-openmp.md) (OpenMP: skalowanie, harmonogramy, walidacja szachownicy MC).

| Plik | Co robi |
|---|---|
| `run_profile.py` | macierz pomiarów: generuje configi, uruchamia `engine` (MSVC, opcjonalnie GCC przez WSL), 3 powtórzenia, przypięcie do rdzenia P, zbiera `times.json` -> `results/profile_<data>.csv` (+ `_raw.csv`, `_meta.json`, `_benchmark.csv`); `--cases` — wybrane warianty |
| `plot_profile.py` | wykresy `../docs/img/profile_*.png` z najnowszego (lub wskazanego `--csv`) zestawu |
| `ab.py` | test A/B dwóch lub więcej programów `engine` na stałym zestawie 13 przypadków: naprzemiennie, przypięte, mediana [min–max], zgodność bitowa wyników po każdym powtórzeniu -> `results/ab/<nazwa>.md/.csv/_raw.csv`; `--wsl` (GCC), `--from-raw` (tabela z pomiaru w częściach) |
| `compare_results.py` | zgodność bitowa wszystkich `configs/*.json` liczonych kilkoma programami (MSVC i GCC przez WSL) -> `results/ab/zgodnosc_*.md`; `--launch "<etykieta>=mpiexec -n 3"` — program pod `mpiexec` (etap 10) |
| `plot_etap8.py` | wykresy `../docs/img/etap8_*.png`: przed/po (profil `_przed2`/`_po`), przyspieszenie każdego kroku, automat frontalny vs pełny przebieg |
| `baseline/` | programy odniesienia do testów A/B (`engine_przed_*`, `engine_kN_*`) — lokalne, w `.gitignore` |
| `profile_gcc.sh` | profilowanie GCC w WSL: gprof (`gcc-profile`, `gcc-profile-noinline`) i callgrind (`gcc-o2`, `gcc-o2-noinline`) -> `profiles/` (`SKIP_GPROF=1` — sam callgrind; `ETAP8=1` — krótki profil gprof po etapie 8 -> `profiles/etap8_gprof_*`) |
| `profile_msvc.py` | profilowanie MSVC: kolektor CPU Usage profilera Visual Studio (`VSDiagnostics.exe`) + `xperf` (symbole z PDB) na `msvc-profile`, `msvc-profile-noinline` -> `profiles/msvc_*.txt` |
| `micro/mc_kernels.cpp` | mikrobenchmark składników próby MC i indeksowania (cel CMake `mc_kernels`, te same flagi co silnik) — wyjaśnienie różnicy GCC vs MSVC |
| `scaling.py` | skalowanie OpenMP (etap 9): przypadki × p ∈ {1, 2, 4, 6, 8} wątków naprzemiennie, rdzenie P (`pcores`), wysoki priorytet, ≥ 5 powtórzeń, zgodność bitowa z p = 1 po każdym powtórzeniu; S(p), E(p), część szeregowa f z prawa Amdahla -> `results/omp/<nazwa>.md/.csv/_raw.csv/_threads.json`; `--schedules` (6 harmonogramów przy 8 wątkach), `--wsl` (GCC), `--from-raw` |
| `mc_validation.py` | walidacja statystyczna szachownicy MC względem wariantu naiwnego (12 ziaren generatora, liczba ziaren, wielkość, wykładnik wzrostu, t Welcha) -> `results/omp/mc_walidacja.*`, `../docs/img/etap9_mc_walidacja.png`; `--from-csv` — bez pomiaru |
| `scaling_mpi.py` | skalowanie MPI (etap 10): przypadki z `scaling.py` × warianty `m<p>` (procesy), `h<p>x<t>` (procesy × wątki), `c<p>` (`mpi.exchange = changed`), `o<t>` (OpenMP) naprzemiennie, `--high-priority`, rdzenie P, ≥ 5 powtórzeń, zgodność bitowa z pierwszym wariantem; S(p), E(p), Amdahl, udział komunikacji, nierównomierność pasów, bajty na wymianę -> `results/mpi/<nazwa>.md/.csv/_raw.csv`; `--wsl` (GCC/OpenMPI), `--from-raw`; plan pomiaru `results/mpi/PLAN_POMIARU.md` |
| `plot_etap9.py` | wykresy `../docs/img/etap9_*.png`: schemat podziału, S(p) i E(p), Amdahl, harmonogramy, praca wątków, części szeregowe, MSVC vs GCC |
| `plot_etap10.py` | wykresy `../docs/img/etap10_*.png` (etap 10, MPI): schemat pasów z warstwami brzegowymi, S(p) i E(p), Amdahl, MPI vs OpenMP, tryb hybrydowy, udział komunikacji, czas obliczeń procesów, `changed` vs `always` |
| `mpi_io.py` | pomiar etapu 11 (typy pochodne MPI i MPI-IO): grupy `pack` (pakowanie vs typy pochodne w wymianie), `bcast` (JSON vs struktury), `io` (zebranie na proces 0 vs MPI-IO: czas zapisu, MB/s, udział w `total`, pamięć procesu 0), `read` (`--mc-from`); warianty jak w `scaling_mpi.py` z przyrostkami `d` / `s` / `i`, naprzemiennie, zgodność bitowa każdego przebiegu -> `results/mpi_io/<nazwa>.md/_raw.csv`; `--wsl` (wyniki na ext4), `--mpiexec "mpiexec --mca io romio321"` (ROMIO w OpenMPI), `--from-raw`; plan pomiaru `results/mpi_io/PLAN_POMIARU.md` |
| `plot_etap11.py` | wykresy `../docs/img/etap11_*.png` (etap 11): schemat typów (struct warstwy z pól SoA, widok subarray pasa w pliku, przesunięcia `MPI_Exscan`), wymiana manual vs datatype, zapis gather vs MPI-IO (czas, MB/s, MS-MPI / OMPIO / ROMIO), udział zapisu w `total`, odczyt `--mc-from` — z `results/mpi_io/pomiar_*_raw.csv` |
| `micro/omp_overhead.cpp` | mikrotest narzutu OpenMP (cel CMake `omp_overhead`): region, bariera, krok „3 fazy × 64 warstwy” dla każdego harmonogramu, trwałość wątków puli; `--pin` |
| `ab_progress.py` | test A/B narzutu opcji `--progress` (stary program, nowy bez flagi, nowy z flagą; przemiennie, przypięte) |
| `results/` | dane pomiarowe (CSV, meta); **`profile_2026-10-09*` = punkt odniesienia etapu 3 — nie nadpisywać**; etap 8: `profile_2026-10-17_przed*`, `_po*`, `ab/` (testy A/B, zgodność, dziennik `POSTEP.md`); etap 9: `omp/` (skalowanie, harmonogramy, narzut przy 1 wątku, zgodność, walidacja szachownicy, dziennik `POSTEP.md`); etap 10: `mpi/` (skalowanie `skalowanie_mpi_{msvc,gcc}*`, zgodność MPI, narzut `engine`, dobór przypadków, plan pomiaru, dziennik `POSTEP.md`); etap 11: `mpi_io/` (zgodność typów MPI i MPI-IO, narzut `engine`, dobór przypadków, plan pomiaru, dziennik `POSTEP.md`) |
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

Pomiary wielowątkowe (etap 9): tylko rdzenie P, jeden wątek na rdzeń fizyczny, najwyżej 8 wątków, wysoki priorytet
procesu; pomiar dłuższy niż ~10 min w częściach (`--cases`) scalanych `--from-raw`. Pomiary MPI (etap 10,
`scaling_mpi.py`; etap 11, `mpi_io.py`) — tak samo: 1–8 procesów (× wątki ≤ 8), każdy na swoim rdzeniu P,
`--high-priority`. MPI-IO w WSL tylko na ext4 (`/tmp`) — dysk Windows przez 9p jest wielokrotnie wolniejszy.
