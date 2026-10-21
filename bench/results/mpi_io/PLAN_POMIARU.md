# Etap 11 — plan cichego pomiaru (typy pochodne MPI i MPI-IO)

Plan dla części 2 etapu: dokładne polecenia, kolejność i szacowany czas. Przygotowany w części 1 na podstawie
pojedynczych przebiegów doboru przypadków ([`dobor_msvc.md`](dobor_msvc.md), [`dobor_gcc.md`](dobor_gcc.md)) — opis
i obserwacje wstępne: [`POSTEP.md`](POSTEP.md), część 1 — sesja 2. Wszystkie polecenia z katalogu projektu
(PowerShell); każda część trwa ≤ 7 min (szacunek = suma czasów procesów z doboru × powtórzenia × 1,12 — narzut
skryptu: porównanie plików, usuwanie wyników, start).

**Razem: ok. 30 min** — MSVC / MS-MPI ~19 min (4 części), GCC / OpenMPI ~8 min (5 krótkich części), przygotowanie
i kontrola między częściami ~3 min.

## 0. Przed pomiarem (≈ 3 min)

1. **Warunki** (jak w etapach 8–10): zasilanie sieciowe, uśpienie „Nigdy”, zamknięte inne programy (przeglądarka,
   wideo, GUI projektu), zamknięte programy działające w tle, np. narzędzia producenta laptopa.
2. **Tryb oszczędny** (bez turbo, WSL 8 procesorów):

   ```powershell
   powercfg /qh SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX  | Select-String "Current"   # 0x00000063 (99%)
   powercfg /qh SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX1 | Select-String "Current"   # 0x00000063 (99%)
   Get-Content $env:USERPROFILE\.wslconfig                                               # processors=8, memory=8GB
   python -c "import psutil; print(psutil.cpu_percent(interval=5))"                      # tło < 30%, najlepiej < 10%
   ```

3. **Programy** — binarki końcowe części 1 (te, które przeszły `ctest` i tabele zgodności `zgodnosc_mpi_io_*.md`):

   ```powershell
   Get-FileHash bench\baseline\engine_mpi_e11_msvc.exe, bench\baseline\engine_e11_msvc.exe | Select-Object Hash, Path
   wsl -e sha256sum bench/baseline/engine_mpi_e11_gcc bench/baseline/engine_e11_gcc
   ```

   Oczekiwane początki SHA-256: `engine_mpi_e11_msvc.exe` 4667EECD…, `engine_e11_msvc.exe` AD2F33AC…,
   `engine_mpi_e11_gcc` 301bd275…, `engine_e11_gcc` 40d8d186…. Jeśli się różnią — kod zmienił się po części 1: nie
   mierzyć (kod silnika jest w części 2 zamknięty), opisać w dzienniku.
4. **Miejsce na dysku i system plików:** MSVC pisze do folderu tymczasowego systemu (NTFS, dysk systemowy) — potrzeba
   ~1,5 GB wolnego (dwa pliki tekstowe classic 300³ po 562 MB naraz + wejście `--mc-from` 351 MB); GCC — `/tmp` w WSL
   (ext4: `wsl -e df -hT /tmp` → `ext4`, ≥ 2 GB wolnego). Oba systemy plików leżą na tym samym dysku SSD NVMe (plik
   dysku WSL jest na dysku systemowym).
5. **Próba** (≈ 20 s; wynik do folderu tymczasowego, nie do `bench/results`):

   ```powershell
   python bench\mpi_io.py --bin bench\baseline\engine_mpi_e11_msvc.exe --cases bcast_etna_real --variants m3,m3s --reps 1 --min-reps 1 --name proba --out $env:TEMP\volcano_proba
   python bench\mpi_io.py --wsl --bin bench/baseline/engine_mpi_e11_gcc --omp-bin bench/baseline/engine_e11_gcc --cases bcast_etna_real --variants m3,m3s --reps 1 --min-reps 1 --name proba --out $env:TEMP\volcano_proba
   ```

   Oczekiwane: „różnic wyników: 0”, w tabeli config 219 B (`m3s`) i ~980 B (`m3`).
6. Przed każdą częścią linia „W toku: …” w [`POSTEP.md`](POSTEP.md) (polecenie, godzina), po części — wynik, tło, uwagi.

## 1. Pytania i przypadki

`python bench\mpi_io.py --list` — 14 przypadków w 4 grupach. Konfiguracje jak w pomiarach skalowania etapów 9–10
(`bench/scaling.py`: `lava_big`, `classic`), żeby czasy dało się zestawić z etapem 10.

| Grupa | Przypadek | Co | Powt. | Warianty MSVC | Warianty GCC | Czas 1 powt. MSVC |
|---|---|---|---|---|---|---|
| **pack** — wymiana warstw: pakowanie (m) vs typy pochodne (d) | `pack_lava_3d_front` | lawa 3D 128² × 64, 24 kratery, automat frontalny | 7 | m2, m4, m7, m8 ± d | m8 ± d | 5,4 s |
| | `pack_lava_3d_full` | ta sama lawa, pełny przebieg (dwa zestawy typów `cur` / `next`) | 5 | m2, m4, m7, m8 ± d | — | 46,4 s |
| | `pack_classic_300` | classic 300³, 100 zarodków, VN — największe warstwy (10 MB na wymianę przy 8 procesach) | 5 | m2, m4, m7, m8 ± d | m8 ± d | 17,1 s |
| | `pack_mc_cb_3d_100` | MC szachownica 100³, Moore, 100 MCS — 8 wymian na MCS | 5 | m2, m4, m7, m8 ± d | m8 ± d | 25,7 s |
| **bcast** — rozsyłanie: JSON (m) vs struktury (s) | `bcast_etna_real` | Etna: config + 3 kratery | 5 | m3, m8 ± s | m8 ± s | 1,8 s |
| | `bcast_classic_2000` | classic 2000², 400 zarodków (6,4 KB tablicy struktur) | 5 | m3, m8 ± s | m8 ± s | 1,9 s |
| **io** — zapis: zebranie na proces 0 (m) vs MPI-IO (i) | `io_bin_classic_300` | classic 300³, `ca_result.bin` 351 MB | 5 | m1, m2, m4, m8 ± i | m8 ± i (OMPIO i ROMIO) | 28,0 s |
| | `io_txt_classic_300` | classic 300³, `ca_result.txt` 562 MB | 5 | m1, m2, m4, m8 ± i | m8 ± i (OMPIO i ROMIO) | 37,5 s |
| | `io_bin_classic_2000` | classic 2000², bin 52 MB | 5 | m1, m2, m4, m8 ± i | m8 ± i (OMPIO i ROMIO) | 4,8 s |
| | `io_txt_classic_2000` | classic 2000², txt 86 MB | 5 | m1, m2, m4, m8 ± i | m8 ± i (OMPIO i ROMIO) | 6,2 s |
| | `io_bin_lava_3d` | duża lawa 3D, bin 14 MB (mały plik) | 5 | m1, m8 ± i | — | 4,1 s |
| | `io_txt_lava_3d` | duża lawa 3D, txt 19 MB | 5 | m1, m8 ± i | — | 3,3 s |
| **read** — odczyt `--mc-from`: proces 0 + `MPI_Scatterv` (m) vs `MPI_File_read_at_all` (i) | `read_lava_3d` | wynik dużej lawy (bin 14 MB), MC 0 MCS na bazalcie | 7 | m1, m8 ± i | m1, m8 ± i | 0,9 s |
| | `read_classic_300` | wynik classic 300³ (bin 351 MB) | 5 | m1, m8 ± i | m1, m8 ± i | 17,9 s |

- Przypadki `io` liczą tę samą symulację co pomiar skalowania (classic 300³ — 114 kroków, faza ~3,4 s przy 1 procesie),
  więc „udział zapisu w `total`” jest udziałem w prawdziwym przebiegu, nie w samym zapisie.
- Grupa `read`: wejście (wynik CA) liczy raz program `engine` (jeden wątek) przed pomiarem; MC z `mc.mcs = 0` — tylko
  odczyt, inicjalizacja, statystyki i zapis mapy kryształów.
- Zawężenia względem pełnego zestawu (czas): duża lawa w `io` i `read` — p = 1 i 8 (pliki ~14–19 MB, mało zależą od
  p); `read_classic_300` — p = 1 i 8; GCC (procesory wirtualne WSL — wyniki porównawcze, jak w etapach 9–10): `pack`,
  `io`, `bcast` przy 8 procesach, `read` przy 1 i 8.

## 2. Warianty i miary

| Wariant | Co |
|---|---|
| `m<p>` | `engine_mpi` na p procesach po 1 wątku, opcje jak w etapie 10 (`mpi.pack = manual`, `mpi.bcast = json`, `mpi.io = gather`) |
| przyrostek `d` | `mpi.pack = datatype` — typy pochodne w wymianie warstw brzegowych |
| przyrostek `s` | `mpi.bcast = struct` — blok liczbowy configu i kratery / zarodki jako struktury |
| przyrostek `i` | `mpi.io = mpiio` — zapis wyników i odczyt `--mc-from` przez MPI-IO |
| `m7` | 7 procesów na procesorach 2–14 (bez procesora 0 — w etapie 10 proces na nim liczył 13–30% dłużej) |

Każdy przebieg: `--high-priority`, `parallel.affinity = pcores` (proces r na rdzeniu P nr r — procesory logiczne 2, 4,
…, 14, 0), warianty przypadku naprzemiennie (kolejność odwracana co powtórzenie), mediana [min–max], wynik każdego
przebiegu porównany bajt po bajcie z pierwszym wariantem tego powtórzenia (`compare_dirs`).

Miary (z `times.json`; kolumny tabel `mpi_io.py`):

- **pack:** czas fazy (`caSim` / `mcSim`), czas wymiany warstw (`mpi.<etap>.haloMs`, średnia po procesach; w MC
  zawiera czekanie na wolniejszy pas po kolorze), na jedną wymianę, bajty i komunikaty na wymianę (te same w obu
  wariantach — kontrola), liczba typów i czas ich budowy (część czasu wymiany).
- **bcast:** `MPI_Bcast` configu (proces 0), bajty, przygotowanie na procesie 0 (`effective.dump()` / blok), budowa
  `Config` na pozostałych procesach (maks.; parsowanie i walidacja JSON / przepisanie pól), kratery (`MPI_Bcast` tablicy
  struktur — przy `m` każdy proces liczy je sam, czas w sekcji `vents`).
- **io:** `save` — od końca fazy CA: kopia pasa bez ramki, (m) `MPI_Gatherv` na proces 0, zapis pliku (proces 0)
  albo MPI-IO wszystkich procesów; czas samego pliku (`files.<plik>.writeMs`, proces 0), MB/s, udział `save` w `total`,
  zebranie (maks.), formatowanie tekstu i samo MPI-IO (maks. po procesach), **szczyt pamięci procesu 0**.
- **read:** `readInput` procesu 0 (m: cały plik — 5 tablic; i: nagłówek + odczyt pasa — 3 tablice potrzebne MC:
  typ, `solidStep`, `arrivalStep`), rozdział pasów `MPI_Scatterv` (m), samo MPI-IO (maks.), `total`.

**Pamięć podręczna systemu plików:** każdy przebieg pisze nowy plik (folder wyniku usuwany przed przebiegiem, wynik
porównany i usunięty zaraz po nim), a czas zapisu kończy się na zamknięciu pliku — bez wymuszania zapisu na dysk
(dane trafiają do pamięci podręcznej systemu i na dysk później). Tak samo w obu trybach i we wszystkich wariantach;
mierzymy więc koszt zapisu widziany przez program, nie przepustowość samego dysku. Przed pomiarem jeden przebieg
rozgrzewkowy (pierwszy wariant pierwszego przypadku części). Odczyt (`read`) jest zawsze „ciepły”: plik wejściowy
po zapisie przez `engine` jest w pamięci podręcznej — porównanie dotyczy drogi danych (proces 0 + rozdział vs
odczyt pasów), nie dysku.

**GCC / OpenMPI — dwie implementacje MPI-IO:** domyślny komponent OMPIO i ROMIO (`--mca io romio321` — implementacja
MPI-IO z MPICH, z której wywodzi się też MPI-IO w MS-MPI). W doborze ROMIO zapisywało tekst 2–3× szybciej niż OMPIO
(classic 2000², 8 procesów) — część H mierzy to samo co część F z ROMIO.

## 3. Polecenia (kolejno)

Wyniki w `bench/results/mpi_io/` (`<nazwa>.md`, `<nazwa>_raw.csv`); każda część kończy się linią „Zgodność wyników
w przypadku: wszystkie przebiegi bitowo zgodne” i „różnic wyników: 0”. Skróty w tabeli:

- `$M` = `python bench\mpi_io.py --bin bench\baseline\engine_mpi_e11_msvc.exe --omp-bin bench\baseline\engine_e11_msvc.exe`
- `$G` = `python bench\mpi_io.py --wsl --bin bench/baseline/engine_mpi_e11_gcc --omp-bin bench/baseline/engine_e11_gcc`

(w PowerShell wpisać polecenia w całości — zmienne są tu tylko skrótem zapisu).

| Część | Polecenie | Czas |
|---|---|---|
| **A** MSVC, wymiana: lawa | `$M --cases pack_lava_3d_front,pack_lava_3d_full --name pomiar_msvc_cz1` | ~5,0 min |
| **B** MSVC, wymiana: classic, MC + rozsyłanie | `$M --cases pack_classic_300,pack_mc_cb_3d_100,bcast_etna_real,bcast_classic_2000 --name pomiar_msvc_cz2` | ~4,3 min |
| **C** MSVC, zapis classic 300³ | `$M --cases io_bin_classic_300,io_txt_classic_300 --name pomiar_msvc_cz3` | ~6,1 min |
| **D** MSVC, zapis classic 2000², lawa + odczyt | `$M --cases io_bin_classic_2000,io_txt_classic_2000,io_bin_lava_3d,io_txt_lava_3d,read_lava_3d,read_classic_300 --name pomiar_msvc_cz4` | ~3,6 min |
| scalenie MSVC | `python bench\mpi_io.py --from-raw bench\results\mpi_io\pomiar_msvc_cz1_raw.csv,bench\results\mpi_io\pomiar_msvc_cz2_raw.csv,bench\results\mpi_io\pomiar_msvc_cz3_raw.csv,bench\results\mpi_io\pomiar_msvc_cz4_raw.csv --name pomiar_msvc` | — |
| **E** GCC, wymiana | `$G --cases pack_lava_3d_front,pack_classic_300,pack_mc_cb_3d_100 --variants m8,m8d --name pomiar_gcc_cz1` | ~1,6 min |
| **F** GCC, zapis (OMPIO) | `$G --cases io_bin_classic_300,io_txt_classic_300,io_bin_classic_2000,io_txt_classic_2000 --variants m8,m8i --name pomiar_gcc_cz2` | ~1,9 min |
| **G** GCC, odczyt | `$G --cases read_lava_3d,read_classic_300 --name pomiar_gcc_cz3` | ~2,1 min |
| **G2** GCC, rozsyłanie | `$G --cases bcast_etna_real,bcast_classic_2000 --variants m8,m8s --name pomiar_gcc_cz4` | ~0,5 min |
| scalenie GCC | `python bench\mpi_io.py --from-raw bench\results\mpi_io\pomiar_gcc_cz1_raw.csv,bench\results\mpi_io\pomiar_gcc_cz2_raw.csv,bench\results\mpi_io\pomiar_gcc_cz3_raw.csv,bench\results\mpi_io\pomiar_gcc_cz4_raw.csv --name pomiar_gcc` | — |
| **H** GCC, zapis (ROMIO) | `$G --mpiexec "mpiexec --mca io romio321" --cases io_bin_classic_300,io_txt_classic_300,io_bin_classic_2000,io_txt_classic_2000 --variants m8,m8i --name pomiar_gcc_romio` | ~1,9 min |

Szacunek części (suma czasów procesów wariantów na powtórzenie z doboru × powtórzenia × 1,12): A 5,4 s × 7 + 46,4 s ×
5; B 17,1 s × 5 + 25,7 s × 5 + 3,7 s × 5; C (28,0 + 37,5) s × 5; D (4,8 + 6,2 + 4,1 + 3,3 + 17,9) s × 5 + 0,9 s × 7
+ ~7 s (przygotowanie wejść `read` programem `engine`); E (2,2 × 7 + 5,7 × 5 + 6,1 × 5) s; F i H (6,6 + 7,5 + 2,0
+ 2,1) s × 5; G (2,4 × 7 + 15,5 × 5) s + ~7 s; G2 3,8 s × 5; WSL — do tego ~10 s na część (kopiowanie programów na
ext4, start).

**Powtórzenie części:** tło > 30% albo skok tła między startem i końcem (nagłówek `.md`), różnica wyników, pojedyncze
przebiegi odstające (np. jeden wariant ×2 względem reszty powtórzeń — w doborze lawa 3D bin m8i: 310 ms wobec ~23 ms)
— powtórzyć całą część pod nową nazwą (`…_cz3b`) i do scalenia wziąć nową; drugi raz źle — zapisać i iść dalej.
Kontrola między częściami ~0,5 min (temperatura, tło).

## 4. Kontrola po każdej części

- nagłówek `.md`: „wszystkie przebiegi bitowo zgodne”, tło start / koniec;
- `_raw.csv`: `priority` = `high`, `cpus` — Windows `2 4 6 …` (m8: `… 14 0`, m7: bez `0`), WSL `0 2 4 6 1 3 5 7`;
- `pack`: `bytesPerExchange` i `messagesPerExchange` takie same w `m<p>` i `m<p>d` i stałe między powtórzeniami,
  `typesBuilt` stałe (zależy tylko od podziału; pełny przebieg lawy — 2× więcej typów niż front);
- `io`: rozmiary plików stałe (`caBinBytes` 351 000 020 / 52 000 020, `caTxtBytes` 562 292 586 / 86 489 166),
  `ioMode` = `mpiio` tylko w wariantach `…i`;
- `read`: `readBytes` (MPI-IO) = 5 B × komórki (classic 300³: 135 000 000).

## 5. Co z tego powstaje w części 2

- tabele `pomiar_msvc.md`, `pomiar_gcc.md`, `pomiar_gcc_romio.md` (+ `_raw.csv` części): wymiana manual vs datatype,
  rozsyłanie JSON vs struktury, zapis gather vs MPI-IO (bin, txt, MB/s, udział w `total`, pamięć procesu 0), odczyt
  `--mc-from`; OMPIO vs ROMIO;
- wykresy `docs/img/etap11_*.png` (skrypt do napisania w części 2 na wzór `bench/plot_etap10.py`): czas wymiany
  manual vs datatype (przypadki × p), czas zapisu i MB/s gather vs MPI-IO (bin i txt osobno, p), udział zapisu
  w `total` przed / po, odczyt `--mc-from`, schematy (typ struct warstwy z pól SoA, widok subarray pasa w pliku,
  przesunięcia `MPI_Exscan` w pliku tekstowym);
- `docs/etap-11-mpi-typy-io.md`: punkt „Wyniki pomiaru” — uczciwe wnioski (czy typy pochodne przyspieszają wymianę
  na jednym komputerze, gdzie MPI-IO zyskuje: brak zebrania i kopii na procesie 0, równoległe formatowanie tekstu,
  pamięć procesu 0 — a gdzie nie: sam zapis jednego pliku na jednym dysku), ograniczenia, przewidywania dla klastra,
  wnioski dla etapu 12.
