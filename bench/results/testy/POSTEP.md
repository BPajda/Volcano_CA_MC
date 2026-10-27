# Dziennik pomiarów: testy wydajności (przyspieszenie, efektywność, pamięć, pamięć podręczna)

Pomiary z 21.10.2026. Opis i wnioski: [`docs/testy-wydajnosci.md`](../../../docs/testy-wydajnosci.md). Dzienniki
wcześniejszych pomiarów: optymalizacja sekwencyjna [`../ab/POSTEP.md`](../ab/POSTEP.md), OpenMP
[`../omp/POSTEP.md`](../omp/POSTEP.md), MPI [`../mpi/POSTEP.md`](../mpi/POSTEP.md), typy MPI i MPI-IO
[`../mpi_io/POSTEP.md`](../mpi_io/POSTEP.md).

**Zasada: pomiarów, które już są, nie powtarzamy.** Przyspieszenie i efektywność OpenMP, MPI, trybu hybrydowego oraz
typów pochodnych i MPI-IO zmierzono z bitową zgodnością każdego przebiegu, a programy później nie zmieniły zachowania
ani szybkości (A/B `ab_e10_*`, `ab_e11_*`), więc te dane są tu zestawione. Mierzone jest tylko to, czego brakowało:
skalowanie słabe, pamięć główna wersji równoległych, pamięć podręczna i przepustowość pamięci. Pomiary pamięci (RSS)
i symulacja pamięci podręcznej (cachegrind) nie zależą od tła; pomiary czasu — krótki pomiar w ciszy według
[`PLAN_POMIARU.md`](PLAN_POMIARU.md).

## Warunki

- Programy = binarki wersji z typami MPI i MPI-IO (SHA-256 `engine.exe` AD2F33AC…, `engine_mpi.exe` 4667EECD…, GCC
  `engine` 40d8d186…, `engine_mpi` 301bd275…), więc dane wcześniejszych pomiarów dotyczą tych samych programów.
- Taktowanie bazowe (`PROCTHROTTLEMAX` i `PROCTHROTTLEMAX1` = 99%, sieć i bateria, zasilanie sieciowe; licznik
  „% wydajności procesora” pod obciążeniem 96,1–97,2%), WSL 8 procesorów / 8 GB, buildy z 4 zadaniami, jedna ciężka
  operacja naraz, łącznie najwyżej 8 procesów × wątków na rdzeniach P.
- Ustawienia pomiarów MPI: `mpi.pack = datatype`; w WSL ROMIO (`mpiexec --mca io romio321`) tam, gdzie jest zapis
  MPI-IO; w testach skalowania `output.format = none` albo `bin`.
- **Procesor** (`bench/cache_info.py` → [`procesor.md`](procesor.md)): rdzeń P — L1d 48 KB (12-drożna), L1i 32 KB,
  L2 2 MB (16-drożna) na rdzeń; rdzeń E — L1d 32 KB, L2 4 MB na grupę 4 rdzeni; L3 36 MB (12-drożna) wspólna dla
  wszystkich 32 procesorów logicznych; linia 64 B. WSL 2 widzi 4 rdzenie × 2 wątki z parametrami rdzenia P.
- **Liczniki sprzętowe niedostępne:** w WSL nie ma programu `perf` (brak pakietu dla jądra 5.15.167.4-microsoft-standard-WSL2,
  a maszyna wirtualna i tak zwykle nie udostępnia liczników PMU); w Windows `xperf … -pmcprofile CacheMisses` bez
  uprawnień administratora kończy się „Failed to configure counters”. Zamiast liczników: symulacja
  `valgrind --tool=cachegrind` (valgrind 3.18.1).

## Tabela kroków

| Krok | Pliki wyników | Wynik | Uwagi |
|---|---|---|---|
| Zestawienie S / E | `zestawienie.{md,csv}`, `zestawienie_lacznie.csv` | najlepsze S fazy (MSVC): OpenMP 8 — lawa full 6,34, Etna 4,98; MPI 7 — classic 2000² 6,68, MC 1000² 6,72; łącznie Etna ×1 871, classic 300³ ×50, MC ×47 / ×39 | bez nowych przebiegów |
| Pamięć główna | `pamiec_{msvc,gcc}.md`, `_raw.csv` | wątki 8 / 1 = 0,96–1,05; suma MPI przy 8 procesach: classic ×1,00–1,14, lawa ×1,71–1,84 (warstwy brzegowe 59%); proces 0 gather → MPI-IO ×0,25; model ±8% (CA) | pomiar przy tle (RSS od niego nie zależy) |
| Pamięć podręczna (cachegrind) | `cachegrind.{md,csv}`, `bench/profiles/cachegrind/` | szachownica ×10–12 mniej chybień D1 niż random; front ×19 mniej niż full; progi L2 / L3 / RAM zgodne z rozmiarem zbioru roboczego | symulacja |
| Skalowanie słabe (`--weak`) | `slabe_{omp,mpi}_{msvc,gcc}.*` | E_w(8) fazy OpenMP: classic 0,49, MC 0,87, lawa full 0,88, front 1,00; MPI 7 / 8: 0,61 / 0,49, 0,97 / 0,84, 0,78 / 0,67, 0,27 / 0,25 | części A, B, C1, C2 |
| Krzywa czasu na komórkę | `krzywa_{msvc,gcc}.*` | MC random 36 → 169 ns (×4,6), próg L2 przy 131 → 262 tys. komórek; classic i szachownica bez progu | części D, E |
| Przepustowość, fałszywe współdzielenie | `przepustowosc_{msvc,gcc}.csv` | triad 17,6 → 48,8 GB/s (nasycenie przy 6 wątkach); `fetch_add` w jednej linii ×4–14, listy 96 B ×1,01–1,09 | część F |
| Wykresy | `bench/plot_testy.py`, `docs/img/testy_*.png` (11) | — | — |

## Zestawienie S / E (bez przebiegów)

`bench/zestawienie.py` czyta `profile_2026-10-17_{przed2,po}.csv`, `omp/skalowanie_{msvc,gcc}.csv`,
`mpi/skalowanie_mpi_{msvc,gcc}.csv`, `mpi_io/pomiar_*_raw.csv` → [`zestawienie.md`](zestawienie.md), `zestawienie.csv`
(233 wiersze: przypadek × kompilator × wariant, T / S / E / f, źródło, warunki), `zestawienie_lacznie.csv`.

- S zawsze od T(1) z tej samej sesji; typy pochodne przez stosunek faz m / d z jednej sesji × S(m<p>) wersji MPI, bo
  **ten sam wariant m8 w dwóch sesjach różni się o 13–29%** (lawa front 340 → 264 ms, lawa full 2 960 → 2 572 ms,
  classic 300³ S(8) 3,32 → 3,84). Profil przed / po optymalizacji sekwencyjnej był z zapisem txt + bin w classic i MC —
  tam tylko faza.
- Najlepsze S fazy na ≤ 8 rdzeniach (MSVC): OpenMP 8 — lawa full 6,34, Etna 4,98, classic 300³ 4,82, lawa front 5,36;
  MPI 7 (bez procesora 0) — classic 2000² 6,68, MC 1000² 6,72; MC 100³ — MPI 7 z typami 6,07 ≈ OpenMP 8 6,06.
- **Łączne przyspieszenie fazy od programu sprzed optymalizacji** (iloczyn ilorazów z sesji; wprost — kontrola): Etna
  ×375 (algorytm) × 4,98 (OpenMP 8) = ×1 871 (wprost ×1 878); classic 300³ ×10,4 × 4,82 = ×50; MC 1000² ×1,7
  (algorytm) × 4,04 (szachownica przy 1 wątku) × 6,72 (MPI 7) = ×47; MC 100³ ×2,0 × 3,28 × 6,07 = ×39. GCC: Etna ×1 328,
  classic 300³ ×42, MC ×38 / ×29. E > 1 tylko w classic 2000² przy p = 2 (OpenMP 1,003, MPI 1,023) i o4 (1,005),
  w granicy rozrzutu. Zapis: classic 300³ / 2000² `.txt` przy 8 procesach S(8) całości 1,93 / 2,11 (zebranie) →
  3,43 / 4,34 (MPI-IO).

## Pamięć główna (21.10.2026, 14:25–14:28)

`python bench/memory.py --groups base,omp,mpi --name pamiec_msvc` (3,2 min, 1 powtórzenie — szczyt pamięci jest
powtarzalny, tło 43% / 39%) → [`pamiec_msvc.md`](pamiec_msvc.md); GCC krótko: `python bench/memory.py --wsl --cases
classic2d_2000,lava3d_128,mc3d_100 --name pamiec_gcc` (0,7 min) → [`pamiec_gcc.md`](pamiec_gcc.md). Przypadki:
classic 2D 1000² / 2000² / 4000², classic 3D 100³ / 200³ / 300³, lawa 64² / 128² / 256² × 64 (front), MC 3D 50³ /
100³ / 200³ (szachownica), `etna_real`; warianty o1 / o2 / o4 / o8 (engine), m1–m8 z typami pochodnymi, zapis
zebraniem i MPI-IO.

- **Wątki prawie nie zwiększają pamięci:** szczyt przy 8 wątkach / przy 1 = 0,96–1,05 (MSVC), 0,99–1,10 (GCC); narzut
  stały procesu 6,3 MB (8 wątków: 6,7 MB, stosy wątków).
- **Model pamięci:** (szczyt − narzut stały) / model = 1,00–1,06 dla CA; B na komórkę: classic 2D 28,4–29,0, classic 3D
  29,0–34,3, lawa 29–33, MC 3D 41–45. MC 200³: model zawyża o 16% (0,84), MC 50³ o 6% — część zarezerwowanej pamięci
  statystyk MC nie jest dotykana. GCC: 1,01–1,08.
- **MPI, suma po procesach** (dane = pomiar − p × narzut stały procesu MPI) przy 8 procesach / przy 1: classic 2D
  1,00–1,02, classic 3D 1,04–1,14, MC 3D 1,04–1,16, **lawa 1,71–1,84** — warstwy brzegowe lawy (17 pod pasem + 1 nad)
  to przy 2 / 3 / 4 / 8 procesach 21 / 34 / 42 / 59% siatki wszystkich okien; classic i MC: 2D ≤ 1%, 3D 100³ / 200³ /
  300³ — 12 / 7 / 5%. Model rozszerzony na procesy zgadza się z sumą: zebranie 0,96–1,08 (MC do 1,20).
- **Narzut stały procesu MPI:** MS-MPI 9,6–10,1 MB na proces (engine 6,3 MB), OpenMPI (WSL) ~21 MB.
- **Proces 0: zebranie vs MPI-IO** (8 procesów): zebranie trzyma cały wynik (13 B na komórkę) — classic 300³ 445 MB
  wobec 107 MB pozostałych; MPI-IO wyrównuje procesy (300³: maks 110, min 107 MB) — szczyt procesu 0 ×0,25. Wyjątek:
  małe siatki — przy p > 1 zapis MPI-IO jest zbiorowy, a proces 0 (jedyny agregator) zbiera dane innych w buforze
  ≤ 16 MB (ROMIO `cb_buffer_size`): classic 1000² proces 0 26 MB wobec 13 MB pozostałych. MC: MPI-IO nie zmniejsza
  pamięci procesu 0 (statystyki ziaren zbierają mapę). Przy 1 procesie MPI-IO zużywa ×0,69–0,73 pamięci zebrania.
- **Linux, `ru_maxrss`:** szczyt bardzo małego procesu pokazuje szczyt procesu rodzica (Python ~15–17 MB), bo
  `ru_maxrss` przechodzi przez fork / exec; narzut stały w Linuksie liczony z RSS na końcu przebiegu (`endRssBytes`).

## Pamięć podręczna (cachegrind, 21.10.2026, 11:35–11:45)

`wsl -e python3 bench/cachegrind.py --ll L2,L3 --name cachegrind` (20 przypadków × LL = L2 / L3) →
[`cachegrind.md`](cachegrind.md), `cachegrind.csv`, `bench/profiles/cachegrind/*.txt` (40 raportów `cg_annotate`).
Preset `gcc-release-g` (Release -O3 + `-g`): sekcje `.text` programów identyczne z `gcc-release` (`objcopy
--only-section=.text` + `cmp`), więc symulacja dotyczy tego samego kodu maszynowego co pomiary. Model: I1 32 KB
8-drożna, D1 48 KB 12-drożna, LL = L2 (2 MB 16-drożna) i LL = L3 (36 MB, 18 dróg zamiast 12 — valgrind wymaga potęgi 2
zbiorów). Tabela główna liczy osobno **jądro** (funkcje kroku), bo w małych przypadkach większość chybień L3 to pierwsze
dotknięcie pamięci przy przygotowaniu. „Jedn.” = komórka × krok albo próba MC; GCC -O3, 1 wątek.

- **Lawa, front vs full** (`test_3d`, 150 kroków): front 4,7 odwołania do danych na komórkę × krok wobec 186,8 (×40
  mniej), chybień D1 0,034 wobec 0,639 (×19 mniej), chybień L2 prawie zero wobec 0,50. Front dotyka tylko aktywnego
  brzegu potoku (mieści się w L2), pełny przebieg co krok przechodzi całą siatkę (~6 MB, w L3).
- **Classic, VN vs Moore** (front): Moore ma ×1,8 (2D) i ×4,9 (3D) więcej odwołań, a chybień D1 tyle samo (2D) albo
  ×1,24 (3D) — chybienia zależą od liczby dotykanych wierszy / warstw, nie od liczby sąsiadów.
- **Układ danych, vector vs macierz** (classic 1000², full): macierz ma ×2,6 więcej odwołań (92,4 vs 35,6 na komórkę ×
  krok), ale tyle samo chybień D1 i L2 — wolniejsza macierz to koszt instrukcji i adresowania, nie pamięci podręcznej.
- **MC, random vs szachownica:** ta sama liczba odwołań na próbę (21,7 w 2D, 67 w 3D), ale chybień D1 ×12 (2D) i ×11
  (3D) mniej w szachownicy (0,41 vs 4,86 i 1,08 vs 11,57 na próbę), chybień L2 ×9 mniej. Losowa próba trafia w losową
  komórkę; szachownica idzie po kolei. To tłumaczy, czemu szachownica już przy 1 wątku jest 3–4× szybsza.
- **Progi L2 / L3 / RAM** (jądro): classic `full` 256² (~1,7 MB) — 0 chybień L2; 1 024² (~27 MB) — 0,41 chybienia L2,
  0 L3; 2 896² (~218 MB) — 0,41 chybienia L3. MC random 256² — 4,1 chybienia D1 na próbę, 0 L2; 1 024² — 3,7 L2,
  0 L3; 4 096² — 3,5 chybienia L3 na próbę. Classic idzie po kolei (prefetcher sprzętowy ukrywa większość chybień —
  symulator go nie ma), MC random losowo.
- **Pas MPI przy 8 procesach** (MC szachownica 1000 × 125, 1,1 MB, mieści się w L2, wobec 1000² ~9 MB): chybień L2
  0,26 vs 0,41 na próbę (−37%), L3 zero w obu; szachownica i tak ma 98% trafień w D1, więc zysk czasu jest mały.
- **Ograniczenia:** symulacja (zdarzenia, nie czas); L3 18-drożna; dwa poziomy na przebieg (D1 + LL); 1 wątek; bez
  prefetchera; kod GCC.

## Przygotowanie pomiarów czasu

- `--weak` w `bench/scaling.py` i `bench/scaling_mpi.py`: classic 2000 × 2000·p, MC szachownica 1000 × 1000·p, lawa
  `full` / `front` 128 × 128·p × 64 na terenie z p kafli 128 × 128 (24 kratery na kafel); E_w fazy i całości, ns rdzenia
  na komórkę × krok, E_w znormalizowana do liczby kroków. Próba (tło ~40%, tylko działanie): MSVC OpenMP p = 1 / 2 E_w
  0,90–0,98; MPI m2d lawa front 0,47 (dolny pas ma prawie całą lawę).
- `bench/cell_time.py`: 1 wątek na rdzeniu P, siatki 2D 128 … 2896 co √2; krzywe `classic_full` (VN, `full`, 40
  kroków), `mc_random` / `mc_cb` (VN, 3 MCS); zbiór roboczy kroku z bajtów dotykanych na komórkę (classic 26 B, MC 12 B).
- Mikrotest `bench/micro/bandwidth.cpp` (tryby `stream`, `sizes`, `false`); w odczycie 8 sum częściowych zamiast
  jednego łańcucha zależnych dodawań (8 → 13 GB/s na 1 wątku). SHA-256: `bandwidth.exe` 273211EB…, GCC c3601427….

## Pomiar czasu (21.10.2026, 18:34–18:52)

Przed pomiarem: SHA-256 programów jak wyżej, licznik „% wydajności procesora” 96,1–97,2%, tło 14,2%; próba (36 s)
— skrypty działają. Komputer bez innej pracy.

| Część | Polecenie | Czas, tło | Wynik |
|---|---|---|---|
| A | `python bench\scaling.py --weak --no-stats --name slabe_omp_msvc` (zapis w domyślnym `bench/results/omp/`, pliki przeniesione do `testy/`) | 1,9 min, 15 → 9% | E_w fazy przy p = 8: classic 0,49 (znorm. 0,61), MC szachownica 0,87, lawa full 0,88, lawa front 1,00 (p = 4 / 6: 1,15 / 1,18) |
| B | `python bench\scaling_mpi.py --weak --name slabe_mpi_msvc --out bench\results\testy` | 3,1 min, 12 → 15% | E_w fazy przy m8d: classic 0,49 (znorm. 0,61), MC 0,84 (m7d 0,97), lawa full 0,67 (m7d 0,78), lawa front 0,25 (podział w z, lawa w dolnym pasie) |
| C1 | `scaling.py --weak --wsl --threads 1,4,8 --cases weak_classic_2d,weak_mc_cb_2d,weak_lava_front --no-stats --name slabe_omp_gcc --out bench\results\testy` | 0,8 min, 16 → 16% | E_w przy p = 4 / 8: classic 0,68 / 0,42 (znorm. 0,78 / 0,52), MC 0,94 / 0,79, lawa front 0,98 / 0,76 |
| C2 | `scaling_mpi.py --weak --wsl --variants m1d,m4d,m8d --cases <jak C1> --name slabe_mpi_gcc --out bench\results\testy` | 1,4 min, 14 → 13% | E_w przy m4d / m8d: classic 0,73 / 0,40, MC 0,93 / 0,65, lawa front 0,34 / 0,22 |
| D | `python bench\cell_time.py --name krzywa_msvc` | 1,6 min, 22 → 14% | classic `full` 8,1–8,3 ns na komórkę × krok (bez progu); szachownica 24,6–25,3 ns na próbę (bez progu); **MC random 36,4 ns (n = 128) → 40,6 (362, 1,5 MB, L2) → 52,6 (512, 3 MB, po progu L2) → 94–120 (1 024–1 448, 12–24 MB, L3) → 146–169 ns (2 048–2 896, 48–96 MB, RAM), ×4,6** |
| E | `python bench\cell_time.py --wsl --name krzywa_gcc` | 1,6 min, 12 → 17% | classic 6,7–7,0 ns, szachownica 24,7–25,2 ns, MC random 36,6 → 42,2 → 53,7 → 102–127 → 153–171 ns (×4,7) — te same progi |
| F | `bandwidth --mode all --threads 1,2,4,6,8 --reps 20` (MSVC `--pin --high-priority`, GCC `OMP_PROC_BIND=close OMP_PLACES=cores`) | 1,2 min, 17 → 17% | MSVC triad 17,6 / 30,9 / 43,2 / 48,8 / 48,1 GB/s, odczyt 14,4 / 28,1 / 46,9 / 54,5 / 58,9 GB/s przy p = 1 / 2 / 4 / 6 / 8 (nasycenie od p = 6); GCC triad 19,3 … 47,5, odczyt 15,4 … 58,7 GB/s. Rozmiary (p = 1): triad 54–66 GB/s do 2 MB, ~22 GB/s 4–32 MB, ~18 GB/s od 128 MB. Fałszywe współdzielenie (MSVC): zapis co 8 B / co 64 B ×1,1–1,2; `fetch_add` 35 / 8,7 ns (p = 2), 122 / 8,8 ns (p = 8), ×4–14; listy 96 / 128 B ×1,06–1,09. GCC: atomowy ×3–10, listy bez stałej różnicy |

- Razem ~18 min, tło 9–22%, bez skoków i bez przebiegów odstających — żadnej części nie powtarzano.
- Wykresy `python bench\plot_testy.py` (11 plików `docs/img/testy_*.png`); zapotrzebowanie na przepustowość przy
  8 wątkach (jednostki / s ze skalowania słabego × chybienia L2 z cachegrind × 64 B): classic 16,0, MC 7,2, lawa full
  4,2, front 0,1 GB/s.
- `bench/cell_time.py` zapisuje w nagłówku `.md` program względem katalogu projektu (w `krzywa_gcc.md` pełna ścieżka
  WSL zastąpiona ręcznie).
