# Plan pomiaru skalowania MPI

Plan pomiaru z 21.10.2026: dokładne polecenia, kolejność i szacowany czas. Przygotowany na podstawie
pojedynczych przebiegów doboru przypadków ([`dobor_msvc.md`](dobor_msvc.md), [`dobor_gcc.md`](dobor_gcc.md)); opis
i wnioski z doboru: [`POSTEP.md`](POSTEP.md), punkt „Dobór przypadków”. Wszystkie polecenia z katalogu projektu
(PowerShell); każda część trwa ≤ 10 min (szacunek = suma czasów procesów z doboru × powtórzenia × 1,1).

**Razem: ok. 30 min**: MSVC/MS-MPI ~17 min (4 części), GCC/OpenMPI ~8 min (2 części), przygotowanie i kontrola
między częściami ~5 min.

## 0. Przed pomiarem (≈ 5 min)

1. **Warunki** (jak w pomiarach optymalizacji i OpenMP): zasilanie sieciowe, uśpienie „Nigdy”, zamknięte inne programy (przeglądarka,
   wideo), zamknięte programy działające w tle, np. narzędzia producenta laptopa; przy 8 procesach na 8 rdzeniach P
   każdy program w tle opóźnia cały krok (pasy czekają na najwolniejszy).
2. **Taktowanie bazowe i WSL 8 procesorów:**

   ```powershell
   powercfg /qh SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX  | Select-String "Current"   # 0x00000063 (99%)
   powercfg /qh SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX1 | Select-String "Current"   # 0x00000063 (99%)
   Get-Content $env:USERPROFILE\.wslconfig                                               # processors=8, memory=8GB
   python -c "import psutil; print(psutil.cpu_percent(interval=5))"                      # tło < 30%, najlepiej < 10%
   ```

3. **Programy:** binarki końcowe (te same, które przeszły testy i tabele zgodności):

   ```powershell
   Get-FileHash bench\baseline\engine_mpi_e10_msvc.exe, bench\baseline\engine_e10_msvc.exe | Select-Object Hash, Path
   ```

   Oczekiwane początki SHA-256: `engine_mpi_e10_msvc.exe` 524187DF…, `engine_e10_msvc.exe` 1D58245B…,
   `engine_mpi_e10_gcc` d7a8bc1c…, `engine_e10_gcc` 8a3d35e6… (GCC: `wsl -e sha256sum bench/baseline/engine_mpi_e10_gcc
   bench/baseline/engine_e10_gcc`). Jeśli się różnią, kod zmienił się po testach: zbudować, powtórzyć `ctest` i tabele
   zgodności, zapisać nowe binarki i dopiero wtedy mierzyć.
4. **Próba przypięcia** (2 s):

   ```powershell
   mpiexec -n 3 bench\baseline\engine_mpi_e10_msvc.exe --config configs\test_3d.json --out results\plan_proba --high-priority --set parallel.affinity=pcores
   python -c "import json; m=json.load(open(r'results\plan_proba\times.json', encoding='utf-8'))['mpi']; print(m['cpus'], m['priority'])"
   ```

   Oczekiwane: `[[2], [4], [6]] ['high', 'high', 'high']`.
5. Każda część zapisana w [`POSTEP.md`](POSTEP.md): polecenie, godzina, wynik, tło, uwagi.

## 1. Przypadki

Te same co w skalowaniu OpenMP (`bench/scaling.py`; `python bench/scaling_mpi.py --list`), bez MC `random`
(sekwencyjny, tylko 1 proces). T(1): faza obliczeń przy 1 procesie z doboru (MSVC).

| Przypadek | T(1) faza | Powt. | Harmonogram wątków (hybryda, o<t>) | Po co |
|---|---|---|---|---|
| `lava_duza_3d_full`: lawa 3D 128² × 64, pełny przebieg | 13,9 s | 5 | `guided` | najwięcej pracy na krok (54 ms), wzorzec skalowania siatki |
| `lava_duza_3d_front`: ta sama lawa, automat frontalny | 793 ms | 7 | `static,1` | krótki krok (2,8 ms), lawa w dolnych warstwach, czyli nierównomierność pasów |
| `classic_2000x2000_s400_vn`: classic 2D, pasy w y | 577 ms | 7 | `static` | równomierna praca, mało bajtów (1 warstwa brzegowa, 7 B na komórkę) |
| `classic_300x300x300_s100_vn`: classic 3D | 3,45 s | 5 | `dynamic,4` | duże warstwy (2,6–10 MB na wymianę), duży zapis wyniku (351 MB, proces 0) |
| `mc_cb_2d_1000`: MC szachownica 1000² | 2,09 s | 5 | `guided,4` | von Neumann: 2 kolory = 2 wymiany na MCS; statystyki ziaren na procesie 0 (część szeregowa, 350 ms) |
| `mc_cb_3d_100`: MC szachownica 100³ (Moore) | 5,63 s | 5 | `dynamic` | 8 kolorów = 8 wymian na MCS |
| `lava_etna_real`: Etna, 1,8 mln komórek | 94 ms | 11 | `static,1` | przypadek „za mały”: krok 0,33 ms, MPI zwalnia (S = 0,4–0,7) |

Lawa ma **17 warstw brzegowych pod pasem** (zasięg `dropDepth` + `hasSupport`) i 1 nad pasem: przy 8 procesach
i 64 warstwach pas ma 8 warstw własnych, a okno ~26 (3,85 MB na wymianę; przy 1 warstwie z każdej strony byłoby
2,13 MB). Z doboru: wymiana to ~0,3 ms na krok, a głównym kosztem jest nierównomierność (lawa w dolnych pasach),
czyli czekanie w `MPI_Allreduce`.

## 2. Warianty

| Wariant | Co | Pytanie |
|---|---|---|
| `m1` | `engine_mpi` na 1 procesie | T(1): odniesienie S(p) i zgodności bitowej (ścieżka `engine`) |
| `m2`, `m3`, `m4`, `m6`, `m8` | p procesów po 1 wątku, rdzenie P 2, 4, …, 14, 0 | S(p), E(p), Amdahl, udział komunikacji (wymagane ≥ 3 procesy) |
| `m7` | 7 procesów na procesorach 2–14 (bez procesora 0) | wpływ procesora 0 (przerwania systemu): w doborze proces na nim liczył pas 30–60% dłużej, a m8 bywało wolniejsze od m6 |
| `h2x4`, `h4x2` | 2 procesy × 4 wątki, 4 × 2 (tryb hybrydowy, 8 rdzeni) | mniej pasów (mniej warstw brzegowych, mniejsza nierównomierność) vs narzut OpenMP |
| `c4`, `c8` | 4 / 8 procesów, `mpi.exchange = changed` | bajty na wymianę i czas: wymiana wszystkich warstw vs tylko zmienionych |
| `o4`, `o8` | `engine` (OpenMP) na 4 / 8 wątkach | MPI vs OpenMP przy tej samej liczbie rdzeni |

**MPI vs OpenMP: nowy pomiar w tym samym przebiegu** (`o4`, `o8` naprzemiennie z wariantami MPI), nie wyniki pomiaru
wersji OpenMP: te same binarki wersji MPI, to samo tło i przypięcie, te same przypadki i harmonogramy, S liczone od tego samego T(1)
(`m1` = ścieżka `engine` przy 1 wątku). Wyniki pomiaru wersji OpenMP (`bench/results/omp/skalowanie_*`) służą tylko
do kontroli (inny dzień, binarka e9). Każdy wariant: `--high-priority`, `parallel.affinity = pcores` (proces r z t wątkami na
rdzeniach P nr r·t … r·t + t − 1; `o<t>`: wątki na rdzeniach P jak w pomiarze OpenMP).

**GCC/OpenMPI: krótszy zestaw** `m1, m3, m8, h2x4, o8`: procesory wirtualne WSL bez gwarancji rdzeni fizycznych P
(jak GCC w pomiarze OpenMP, wyniki porównawcze). OpenMPI widzi 4 rdzenie × 2 wątki SMT; `scaling_mpi.py --wsl` uruchamia
`mpiexec --allow-run-as-root --use-hwthread-cpus --bind-to none`: 8 miejsc, więc 8 procesów **bez nadsubskrypcji**
(`--oversubscribe` niepotrzebne; w próbie oba warianty dały czasy w granicach szumu), przypina program. `total` w WSL
zawiera start OpenMPI (~0,3 s, kolumna `initMax`), więc porównywać fazę obliczeń.

## 3. Polecenia (kolejno)

Wyniki w `bench/results/mpi/` (`<nazwa>.md`, `.csv`, `_raw.csv`); każda część kończy się linią „Zgodność wyników
z `m1`: wszystkie przebiegi bitowo zgodne”.

| Część | Polecenie | Czas |
|---|---|---|
| **A1** MSVC, lawa: Etna, front | `python bench\scaling_mpi.py --bin bench\baseline\engine_mpi_e10_msvc.exe --omp-bin bench\baseline\engine_e10_msvc.exe --variants m1,m2,m3,m4,m6,m7,m8,h2x4,h4x2,c4,c8,o4,o8 --cases lava_etna_real,lava_duza_3d_front --name skalowanie_mpi_msvc_cz1` | ~2 min |
| **A2** MSVC, lawa: pełny przebieg | to samo z `--cases lava_duza_3d_full --name skalowanie_mpi_msvc_cz2` | ~6 min |
| **B** MSVC, classic | to samo z `--cases classic_2000x2000_s400_vn,classic_300x300x300_s100_vn --name skalowanie_mpi_msvc_cz3` | ~4 min |
| **C** MSVC, MC | to samo z `--cases mc_cb_2d_1000,mc_cb_3d_100 --name skalowanie_mpi_msvc_cz4` | ~5,5 min |
| scalenie MSVC | `python bench\scaling_mpi.py --from-raw bench\results\mpi\skalowanie_mpi_msvc_cz1_raw.csv,bench\results\mpi\skalowanie_mpi_msvc_cz2_raw.csv,bench\results\mpi\skalowanie_mpi_msvc_cz3_raw.csv,bench\results\mpi\skalowanie_mpi_msvc_cz4_raw.csv --name skalowanie_mpi_msvc` | — |
| **D** GCC, lawa | `python bench\scaling_mpi.py --wsl --bin bench/baseline/engine_mpi_e10_gcc --omp-bin bench/baseline/engine_e10_gcc --variants m1,m3,m8,h2x4,o8 --cases lava_etna_real,lava_duza_3d_front,lava_duza_3d_full --name skalowanie_mpi_gcc_cz1` | ~3,5 min |
| **E** GCC, classic + MC | to samo z `--cases classic_2000x2000_s400_vn,classic_300x300x300_s100_vn,mc_cb_2d_1000,mc_cb_3d_100 --name skalowanie_mpi_gcc_cz2` | ~4,5 min |
| scalenie GCC | `python bench\scaling_mpi.py --from-raw bench\results\mpi\skalowanie_mpi_gcc_cz1_raw.csv,bench\results\mpi\skalowanie_mpi_gcc_cz2_raw.csv --name skalowanie_mpi_gcc` | — |

Szacunek części (suma czasów 13 wariantów na powtórzenie z doboru × powtórzenia × 1,1): A1 4,3 s × 11 + 7,7 s × 7;
A2 65,6 s × 5; B 6,0 s × 7 + 31,8 s × 5; C 16,3 s × 5 + 41,0 s × 5; D 2,8 s × 11 + 4,1 s × 7 + 26,9 s × 5;
E 3,7 s × 7 + (14,3 + 8,3 + 17,9) s × 5.

**Powtórzenie części:** tło > 30% albo skok tła między startem i końcem (nagłówek `.md`), różnica wyników, pojedyncze
przebiegi odstające (np. m8 ×2 względem reszty powtórzeń): powtórzyć całą część pod nową nazwą (`…_cz3b`) i do
scalenia wziąć nową. Przerwa 1–2 min między częściami (temperatura).

## 4. Kontrola po każdej części

- nagłówek `.md`: „wszystkie przebiegi bitowo zgodne”, tło start / koniec;
- `_raw.csv`: `priority` = `high` we wszystkich procesach, `cpus`: Windows `2 4 6 …` (m8: `… 14 0`, m7: bez `0`;
  h2×4: `2/4/6/8 10/12/14/0`), WSL `0 2 4 6 1 3 5 7`;
- `computePerRank`: czy proces na procesorze 0 znowu odstaje (porównać m7 i m8);
- `bytesPerExchange` stałe między powtórzeniami (zależy tylko od podziału), `c<p>` mniej bajtów w lawie.

## 5. Wyniki

- tabele `skalowanie_mpi_msvc.md`, `skalowanie_mpi_gcc.md`: S(p), E(p) fazy i całego przebiegu, Amdahl (f, S(∞)),
  udział komunikacji, nierównomierność, bajty na wymianę;
- wykresy (`docs/img/mpi_*.png`, `bench/plot_mpi.py`): S(p) i E(p) fazy dla
  przypadków (MSVC), MPI vs OpenMP vs hybryda przy 8 rdzeniach, rozkład czasu fazy (obliczenia / wymiana / czekanie)
  na proces dla lawy (nierównomierność), bajty i czas `always` vs `changed`, schemat podziału na pasy z warstwami
  brzegowymi (`docs/img/mpi_podzial.png`);
- opis wyników w [`docs/mpi.md`](../../../docs/mpi.md), punkt 9.
