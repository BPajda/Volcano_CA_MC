# Plan pomiaru testów wydajności (skalowanie słabe, czas na komórkę, przepustowość pamięci)

Plan pomiaru z 21.10.2026: dokładne polecenia, kolejność i szacowany czas. Przygotowany na podstawie
pojedynczych przebiegów sprawdzających (p = 1, 2 i 8 skalowania słabego, jedno powtórzenie krzywej, wszystkie tryby
mikrotestu — opis w [`POSTEP.md`](POSTEP.md), punkt „Przygotowanie pomiarów czasu”). Wszystkie polecenia z katalogu projektu
(PowerShell); każda część trwa ≤ 4 min.

**Razem: ok. 23 min** — 6 części pomiaru (~18 min), przygotowanie (~3 min) i kontrola między częściami (~2 min).

Czego **nie** mierzymy (jest już z pomiarów OpenMP, MPI i typów MPI, zestawione w [`zestawienie.md`](zestawienie.md)): skalowanie silne
OpenMP, MPI i hybrydy, typy pochodne, MPI-IO. Pamięć i pamięć podręczna (cachegrind) zmierzone wcześniej, nie zależą od tła.

## 0. Przed pomiarem (≈ 3 min)

1. **Warunki** (jak w poprzednich pomiarach): zasilanie sieciowe, uśpienie „Nigdy”, zamknięte inne programy (przeglądarka,
   wideo, GUI projektu), zamknięte programy działające w tle, np. narzędzia producenta laptopa.
2. **Taktowanie bazowe i licznik „% wydajności procesora”** (taktowanie bazowe: pod obciążeniem ≤ 100%,
   dynamiczne: ~197%):

   ```powershell
   powercfg /qh SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX  | Select-String "Current"   # 0x00000063 (99%)
   powercfg /qh SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX1 | Select-String "Current"   # 0x00000063 (99%)
   Get-Content $env:USERPROFILE\.wslconfig                                               # processors=8, memory=8GB
   $job = Start-Job { python -c "import psutil,time; psutil.Process().cpu_affinity([2]); t=time.time(); exec('while time.time()-t<9: pass')" }; Start-Sleep 2; (Get-Counter '\Informacje o procesorze(0,2)\% wydajności procesora' -SampleInterval 1 -MaxSamples 5).CounterSamples | ForEach-Object { [math]::Round($_.CookedValue, 1) }; Receive-Job $job -Wait | Out-Null; Remove-Job $job
   python -c "import psutil; print(psutil.cpu_percent(interval=5))"                      # tło < 30%, najlepiej < 10%
   ```

   Sprawdzone tym poleceniem przy przygotowaniu (21.10.2026): 97,2 / 96,9 / 97,1 / 97,1 / 97,2% (taktowanie bazowe).
3. **Programy** — te same co w pomiarach OpenMP, MPI i typów MPI (silnik bez zmian):

   ```powershell
   Get-FileHash build\Release\engine.exe, build\Release\engine_mpi.exe, build\Release\bandwidth.exe | Select-Object Hash, Path
   wsl -e sha256sum build-gcc-release/bin/engine build-gcc-release/bin/engine_mpi build-gcc-release/bin/bandwidth
   ```

   Oczekiwane początki SHA-256: `engine.exe` AD2F33AC…, `engine_mpi.exe` 4667EECD… (= `bench/baseline/*_e11_msvc.exe`),
   `bandwidth.exe` 273211EB…; GCC: `engine` 40d8d186…, `engine_mpi` 301bd275… (= `*_e11_gcc`), `bandwidth`
   c3601427…. Jeśli się różnią — program zmienił się po przygotowaniu: nie mierzyć, opisać w dzienniku.
4. **Próba** (≈ 40 s; wyniki do folderu tymczasowego, nie do `bench/results`):

   ```powershell
   python bench\scaling.py --weak --threads 1,2 --cases weak_lava_front --reps 1 --min-reps 1 --no-stats --name proba --out $env:TEMP\volcano_proba
   python bench\scaling_mpi.py --weak --variants m1d,m2d --cases weak_classic_2d --reps 1 --min-reps 1 --name proba_mpi --out $env:TEMP\volcano_proba
   python bench\cell_time.py --curves mc_random --sizes 256,1024 --reps 1 --name proba_krzywa --out $env:TEMP\volcano_proba
   ```

   Oczekiwane (przebieg sprawdzający, przy tle ~40%): `weak_lava_front` przy p = 1 ~560 ms, p = 2 ~590 ms fazy, 260 kroków w obu;
   `weak_classic_2d` m1d ~670 ms, m2d ~800 ms; MC random 256² ~39 ns, 1024² ~115–125 ns na próbę.
5. Przed każdą częścią linia „W toku: …” w [`POSTEP.md`](POSTEP.md) (polecenie, godzina), po części — wynik, tło, uwagi.

## 1. Co mierzymy

### 1.1 Skalowanie słabe (Gustafson) — `--weak` w `bench/scaling.py` i `bench/scaling_mpi.py`

Przestrzeń rośnie z liczbą rdzeni p w osi warstw podziału, więc praca na rdzeń jest stała; efektywność słaba
E_w(p) = T(1) / T(p) (ideał 1). `output.format = none` (zapis zestawiony w pomiarze MPI-IO), typy pochodne w MPI
(`mpi.pack = datatype`), `--high-priority`, `parallel.affinity = pcores`; wyników różnych rozmiarów nie porównuje się
bitowo (zgodność wątków i procesów sprawdzona w pomiarach OpenMP i MPI, `ctest`). Lista: `python bench\scaling.py --weak --list`.

| Przypadek | Rozmiar przy p | Harmonogram OpenMP | Co pokazuje |
|---|---|---|---|
| `weak_classic_2d` | classic 2000 × 2000·p, 400·p zarodków, VN | `static` | prosty przypadek: równa praca na komórkę; liczba kroków zależy od położenia zarodków (199 / 223 / 247 przy p = 1 / 2 / 8) — dlatego obok E_w także E_w znormalizowana (czas na komórkę × krok) |
| `weak_mc_cb_2d` | MC szachownica 1000 × 1000·p, VN, 30 MCS | `guided,4` | MC wielowątkowo: 8 wymian / synchronizacji na MCS |
| `weak_lava_full` | lawa `full` 128 × 128·p × 64, 24·p kraterów, 20 kroków | `guided` | lawa, pełny przebieg — praca na komórkę równa |
| `weak_lava_front` | lawa `front` 128 × 128·p × 64, 24·p kraterów | `static,1` | przypadek trudny: praca skupiona w dolnych warstwach z (MPI dzieli w z — pas dolny ma najwięcej lawy; m2d w przebiegu sprawdzającym: E_w 0,47) |

Teren lawy: p takich samych kafli 128 × 128 (stożek jak `lava_big` z pomiarów OpenMP i MPI) wzdłuż y, kratery w tych samych
miejscach każdego kafla (`vents.placement = positions`) — każda warstwa z ma przy każdym p ten sam skład.

### 1.2 Czas na komórkę w funkcji rozmiaru siatki — `bench/cell_time.py`

Jeden wątek na rdzeniu P (procesor logiczny 2, priorytet wysoki; GCC: libgomp `OMP_PROC_BIND=close`), siatki 2D
o boku 128 … 2896 co √2, ta sama gęstość zarodków i liczba kroków / MCS; miara: faza / (komórki × kroki) albo / próby.
Krzywe: `classic_full` (dostęp po kolei, 26 B na komórkę w kroku), `mc_random` (dostęp losowy, 12 B), `mc_cb`
(szachownica). Progi: zbiór roboczy kroku = 2 MB (L2) i 36 MB (L3) — classic przy n ≈ 280 / 1 200, MC ≈ 410 / 1 770.
W przebiegu sprawdzającym (1 powtórzenie, tło ~40%) MC random: 38 ns (L2) → 54–140 ns (L3) → 164–186 ns (RAM); classic i szachownica
bez progu (8–9 ns / 25 ns) — do potwierdzenia w ciszy.

### 1.3 Przepustowość pamięci — mikrotest `bandwidth` (`bench/micro/bandwidth.cpp`)

Tryby (`--mode all`): `stream` (copy / scale / add / triad / odczyt, tablice 160 MB, 1–8 wątków), `sizes`
(przepustowość odczytu i triad w funkcji zbioru roboczego 32 KB … 512 MB), `false` (powtórka w ciszy testu
fałszywego współdzielenia: licznik w sąsiednich 8 B vs co 64 B, zwykły zapis i `fetch_add`; nagłówki list warstw jak
`LavaCA::FrontLayer` co 96 B vs co 128 B). Odniesienie (część 2, wykres): B na komórkę i krok z modelu × komórki / s
przy 8 wątkach (z zestawienia S / E) → czy CA / MC zbliżają się do granicy przepustowości.

## 2. Polecenia (kolejno)

Wyniki w `bench/results/testy/` (`<nazwa>.md`, `<nazwa>.csv`, `<nazwa>_raw.csv`). Szacunki z przebiegów
sprawdzających (czas procesów × powtórzenia + narzut skryptu i startu; WSL — ~10 s na część).

| Część | Polecenie | Czas |
|---|---|---|
| **A** MSVC, skalowanie słabe OpenMP (p = 1, 2, 4, 6, 8; 4 przypadki; 5 powt.) | `python bench\scaling.py --weak --no-stats --name slabe_omp_msvc` | ~2,5 min |
| **B** MSVC, skalowanie słabe MPI (m1d, m2d, m4d, m6d, m7d, m8d; 4 przypadki; 5 powt.) | `python bench\scaling_mpi.py --weak --name slabe_mpi_msvc` | ~4,0 min |
| **C1** GCC, skalowanie słabe OpenMP (p = 1, 4, 8; 3 przypadki; 5 powt.) | `python bench\scaling.py --weak --wsl --threads 1,4,8 --cases weak_classic_2d,weak_mc_cb_2d,weak_lava_front --no-stats --name slabe_omp_gcc` | ~1,3 min |
| **C2** GCC, skalowanie słabe MPI (m1d, m4d, m8d; 3 przypadki; 5 powt.) | `python bench\scaling_mpi.py --weak --wsl --variants m1d,m4d,m8d --cases weak_classic_2d,weak_mc_cb_2d,weak_lava_front --name slabe_mpi_gcc` | ~2,0 min |
| **D** MSVC, czas na komórkę vs rozmiar (3 krzywe × 10 rozmiarów; 5 powt.) | `python bench\cell_time.py --name krzywa_msvc` | ~3,0 min |
| **E** GCC, czas na komórkę vs rozmiar | `python bench\cell_time.py --wsl --name krzywa_gcc` | ~3,0 min |
| **F** przepustowość 1–8 wątków, rozmiary, fałszywe współdzielenie (MSVC, potem GCC; 20 powt.) | `python -c "import psutil; print(psutil.cpu_percent(interval=3))"; build\Release\bandwidth.exe --mode all --threads 1,2,4,6,8 --reps 20 --pin --high-priority --csv bench\results\testy\przepustowosc_msvc.csv; wsl -e env OMP_PROC_BIND=close OMP_PLACES=cores build-gcc-release/bin/bandwidth --mode all --threads 1,2,4,6,8 --reps 20 --csv bench/results/testy/przepustowosc_gcc.csv; python -c "import psutil; print(psutil.cpu_percent(interval=3))"` | ~2,0 min |

- Część F: tło przed i po (mikrotest go nie zapisuje) — do dziennika; tabela z wyjścia na ekranie także do dziennika
  (CSV ma wszystkie liczby). W WSL bez `--pin` — wątki wiąże libgomp, jak w pomiarze OpenMP (procesory wirtualne).
- Szacunek: A — total przy p = 1 / 2 / 8 z przebiegów sprawdzających (0,6–1,9 s na przebieg; 20 przebiegów na powtórzenie);
  B — 0,6–2,5 s, lawa front przy m8d 2,5 s (24 przebiegi na powtórzenie); C — jak A / B dla 3 przypadków i p = 1, 4,
  8; D / E — pełne powtórzenie krzywej 34 / 35 s; F — wszystkie tryby przy 10 powtórzeniach 26 s.

**Powtórzenie części:** tło > 30% albo skok tła między startem i końcem (nagłówek `.md`), pojedyncze przebiegi
odstające (np. jeden wariant ×2 względem reszty powtórzeń) — powtórzyć całą część pod nową nazwą (`…_b`); drugi raz
źle — zapisać i iść dalej. Kontrola między częściami ~0,3 min (tło, temperatura).

## 3. Kontrola po każdej części

- nagłówek `.md`: tło start / koniec, czas części;
- `_raw.csv`: `cpus` — Windows `2 4 6 …` (8 wątków / procesów: `… 14 0`, m7d: bez `0`), WSL — wiąże libgomp / program;
  `priority` = `high` (MPI);
- skalowanie słabe: komórki = p × komórki przy p = 1, kroki lawy stałe (front: 260, full: 20), MCS = 30;
- krzywa: `cpus` = `2`, `steps` = 40 (classic), `mcs` = 3;
- `bandwidth`: wiersz „przypięcie pcores … priorytet wysoki” na Windows; `stream` p = 1 ~14–17 GB/s (przebieg sprawdzający, przy tle).

## 4. Wyniki

- tabele `slabe_*`, `krzywa_*`, `przepustowosc_*` + wpisy w dzienniku;
- wykresy `docs/img/testy_*.png` — `python bench\plot_testy.py` (wykresy z danych bez pomiaru czasu są już w skrypcie;
  słabe skalowanie, krzywa i przepustowość czytają pliki z tego planu, a gdy ich brak — są pomijane);
- opis wyników w [`docs/testy-wydajnosci.md`](../../../docs/testy-wydajnosci.md) (punkty 2.4, 4.3–4.5 i 5): E_w(8)
  OpenMP i MPI (Gustafson vs Amdahl), progi L2 / L3 z krzywej (porównanie z cachegrind), przepustowość i czy CA / MC
  przy 8 wątkach są ograniczone pamięcią, fałszywe współdzielenie.
