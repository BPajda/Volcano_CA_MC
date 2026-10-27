# Dziennik pomiarów: typy pochodne MPI i równoległy zapis MPI-IO

Pomiary z 21.10.2026: zgodność bajtowa nowych ścieżek MPI, narzut w `engine`, dobór przypadków i pomiar według
[`PLAN_POMIARU.md`](PLAN_POMIARU.md). Opis implementacji i wnioski:
[`docs/mpi-typy-i-zapis.md`](../../../docs/mpi-typy-i-zapis.md); wersja MPI: [`docs/mpi.md`](../../../docs/mpi.md),
dziennik [`../mpi/POSTEP.md`](../mpi/POSTEP.md).

## Oznaczenia i warunki

- `e10` = programy wersji MPI (`bench/baseline/engine_e10_*`, `engine_mpi_e10_*`), `e11*` = programy z typami
  pochodnymi i MPI-IO (binarki lokalne, katalog `bench/baseline/` jest w `.gitignore`), `mN` = `engine_mpi`
  na N procesach. Przyrostki wariantów: `d` = `mpi.pack = datatype`, `s` = `mpi.bcast = struct`, `i` = `mpi.io = mpiio`,
  `c` = `mpi.exchange = changed` (np. `m3dsi`: 3 procesy, wszystkie trzy nowe ścieżki).
- Taktowanie bazowe (`PROCTHROTTLEMAX` i `PROCTHROTTLEMAX1` = 99%, sieć i bateria, zasilanie sieciowe; licznik
  „% wydajności procesora” 96,9–97,0%), WSL 8 procesorów / 8 GB, buildy z 4 zadaniami, jedna ciężka operacja naraz,
  łącznie najwyżej 8 procesów × wątków na rdzeniach P, `--high-priority`, `parallel.affinity = pcores`. Tło = obciążenie
  całego CPU przez inne programy (psutil, próbki 2 s), próg 30%.

## Tabela kroków

| Krok | Pliki wyników | Wynik | Zgodność | Tło [% CPU] |
|---|---|---|---|---|
| Wsparcie MPI-IO | — | MS-MPI 10.1: nagłówek ma MPI-IO, `create_struct`, `subarray`, `resized`, `Exscan`; OpenMPI 4.1.2: `io` = OMPIO / ROMIO 3.2.1, oba działają na ext4 i na dysku Windows (9p), 9p 8–16× wolniej | — | — |
| Testy, zgodność | `zgodnosc_mpi_io_{msvc,gcc,full}.md`, `zgodnosc_e11_engine*.md`, `ab_e11_*.md` | `ctest` 21/21: MSVC Release i Debug, GCC; `VOLCANO_MPI=OFF` 12/12; `pytest` 102/102; mutacje M1–M6 wykryte | **15/15** we wszystkich tabelach | 28–36 (A/B) |
| Dobór i plan | `dobor_{msvc,gcc}.md`, `PLAN_POMIARU.md` | 9 części, MSVC ~19 min, GCC ~8 min (z ROMIO) | wszystkie przebiegi zgodne | 18–26 |
| Pomiar | `pomiar_msvc*.md`, `pomiar_gcc*.md`, `pomiar_gcc_romio.md` (+ `_raw.csv`) | 9 części, ~23 min, bez powtórek; wymiana d / m ×0,50–0,75 (MC ×0,84–1,04), faza ×0,91–1,00; zapis dużych plików i / m ×0,40–0,80, małych ×0,93–1,62; odczyt ×0,04–0,43 | wszystkie przebiegi bitowo zgodne | 10–24 |
| Wykresy | `docs/img/mpi_io_*.png` (5) | `bench/plot_mpi_io.py`: schemat, wymiana, zapis, udział zapisu, odczyt | — | — |

## Przygotowanie i poprawność

- **Wsparcie MPI-IO.** MS-MPI 10.1.12498.52 (SDK): `mpi.h` deklaruje `MPI_File_open`, `MPI_File_set_view`,
  `MPI_File_write_at_all`, `MPI_File_write_all`, `MPI_File_read_at_all`, `MPI_File_set_size`,
  `MPI_Type_create_subarray`, `MPI_Type_create_struct`, `MPI_Type_create_resized`, `MPI_Get_address`, `MPI_Exscan`
  i typy o stałym rozmiarze, choć zgłasza `MPI_VERSION 2.0`. OpenMPI 4.1.2 w WSL: komponenty `io` OMPIO (domyślny)
  i ROMIO 3.2.1 (`--mca io romio321`). Próba (4 procesy, każdy pisze pas 4 MB przez `MPI_File_write_at_all` i przez widok
  `MPI_Type_create_subarray` + `MPI_File_write_all`, proces 0 sprawdza bajty): ext4 (`/tmp`) — OMPIO 60 ms, ROMIO 15 ms;
  dysk Windows przez 9p — plik poprawny, ale OMPIO 465 ms, ROMIO 239 ms (8–16× wolniej). W WSL MPI-IO tylko na ext4;
  testy i pomiary piszą tam, a na dysk Windows trafiają kopie do porównania.
- Pierwsza próba (GCC/OpenMPI, 3 procesy, `test_3d` i `lava_mc_2d` z MC szachownicą): e10 vs nowy `engine_mpi` z `d`,
  `s`, `i`, `dsi`, `di` + `changed` — wszystkie pliki bajtowo zgodne. `test_3d` m3: `manual` 1 420 komunikatów /
  82 895 908 B, `datatype` 1 420 / 82 885 968 B (bez 9 940 B flag), 10 typów komunikatów, budowa typów 0,008 ms;
  `datatype + changed` 2 141 komunikatów / 21,4 MB, 460 typów (różne maski flag), budowa 1,1 ms; config `struct` 219 B
  wobec 871 B JSON, budowa Config na procesach ≠ 0: 0,008 wobec 0,075 ms; kratery 56 B.
- **Testy** (`engine/tests/mpi/test_mpi.cpp`, `test_io.cpp`, `test_config.cpp`): typy w wymianie = pakowanie (lawa 2D /
  3D front i full, classic, MC 2D / 3D, `always` i `changed`, hybryda); blok configu po `MPI_Bcast` = config wczytany
  lokalnie (`memcmp`); kratery / zarodki z procesu 0 = wyznaczone lokalnie; pliki bajt po bajcie dla 9 przypadków ×
  10 kombinacji opcji + hybryda 2 × 4. GCC Release: `ctest` 21/21.
- **Czułość nowych testów** (mutacje, każda osobno, cofnięte; 3 procesy): M1 zapis bin od warstwy 0 zamiast `lo`,
  M2 tekst bez przesunięcia `MPI_Exscan`, M3 odczyt `arrivalStep` spod adresu `solidStep`, M4 `datatype + changed`
  bez kopii odebranych warstw do drugiego bufora, M5 typ bloku configu bez jednego pola, M6 typ nadawcy opisuje złą
  warstwę — każda wykryta.
- **Problem techniczny MS-MPI:** w pierwszej wersji 5 testów MPI (np2…np8) w MSVC kończyło się naruszeniem dostępu
  (0xc0000005) przy zapisie `mc_result.bin` przez MPI-IO. Przyczyna: typ pamięci z jednym blokiem pod adresem
  bezwzględnym, zapis od `MPI_BOTTOM` — MS-MPI (ROMIO) uznaje taki typ za ciągły i czyta od adresu 0 (OpenMPI robi to
  poprawnie). Poprawka: przesunięcia bloków względem tablicy o najniższym adresie, która jest buforem zapisu. Po
  poprawce MSVC i GCC `ctest` 21/21.
- `bench/compare_results.py`: programy WSL piszą wyniki na ext4 (`/tmp/volcano_cmp`), do porównania trafia kopia.
- **Narzut w `engine`** (A/B e10 / e11, 1 wątek, procesor 2, 9 powtórzeń): pierwsza wersja (`ab_e11a_msvc.md`) — fazy
  ×0,99–1,01, ale zapis `save` classic 1000² ×1,098 (`ca_result.txt` 63–64 → 69–70 ms). Przyczyna: nowe pętle
  formatowania w tym samym pliku co `writeTxt` zmieniały decyzje MSVC o wstawianiu funkcji pomocniczych (próba
  z pustymi nowymi funkcjami: 64,6 ms, jak e10). Poprawka: formatowanie pasów w osobnym pliku
  `engine/src/io/ResultWriterSlabs.cpp`; 15 powtórzeń: e10 62,6 ms, e11 63,6 ms. Końcowe A/B:
  - MSVC (`ab_e11_msvc.md`, tło 28%): lawa caSim ×0,995–0,998, classic 1000² caSim ×0,991, `save` ×1,000, MC 1000²
    mcSim ×0,994, lawa + MC ×1,013 / ×1,009; cały przebieg ×0,968–1,010;
  - GCC (`ab_e11_gcc.md`, tło 29%): lawa caSim ×0,980–1,028, classic 1000² ×0,932 / `save` ×0,998, MC 1000² ×1,026;
    cały przebieg ×0,987–1,026 (przedziały min–max się nakładają). `nm -S`: 144 ze 156 funkcji automatu i MC mają ten
    sam rozmiar i adres mod 64, różnią się tylko fragmenty `.cold` (ścieżki błędów), więc ±3% to szum procesorów
    wirtualnych WSL.
- **Pomiar zapisu CA:** w trybie zebrania sekcja `save` obejmowała kopię pasa okna bez ramki i `MPI_Gatherv`, a w trybie
  MPI-IO kopia pasa (classic 2000², 2 procesy: ~21 ms) nie trafiała do żadnej sekcji, co zawyżałoby zysk MPI-IO.
  Teraz `save` w obu trybach liczy się od końca fazy CA. Wyniki bez zmian (tylko czas). Skrypty zapisują też szczyt
  pamięci procesu 0 (`peakRoot`), `peakMax`, `caPrepMax`.
- Binarki końcowe: `engine_mpi_e11_msvc.exe` (SHA-256 4667EECD…), `engine_mpi_e11_gcc` (301bd275…),
  `engine_e11_msvc.exe` (AD2F33AC…), `engine_e11_gcc` (40d8d186…). Wersje pośrednie: `engine_mpi_e11b_*` (przed
  poprawką `save`), `engine_e11a_*` / `engine_mpi_e11a_*` (pierwsza wersja).
- **Zgodność na binarkach końcowych** (`mc.update = checkerboard`, odniesienie `engine_mpi_e10` na 3 procesach):
  `zgodnosc_mpi_io_msvc.md` — 15/15: e10 m3 = m3 = d3 = s3 = i3 = dsi1 = dsi3 = dsi8 = dsi 2 × 4 = dsi8c = dsi3_gcc
  (krzyżowo GCC/OpenMPI); `zgodnosc_mpi_io_gcc.md` — 15/15 (wyniki na ext4); `zgodnosc_mpi_io_full.md`
  (`ca.sweep = full`, dwa zestawy typów `cur` / `next`) — 15/15; `zgodnosc_e11_engine.md` i `_t8.md` — 15/15.
- Inne buildy: GCC z `VOLCANO_MPI=OFF` — `ctest` 12/12, `engine` bajtowo ten sam co z MPI; MSVC Debug (z MS-MPI) —
  `ctest` 21/21 (`mpi_np1…8` po 78–104 s, asercje w kodzie MPI, typach i MPI-IO włączone); `pytest gui\tests` 102/102.

### Dobór przypadków (21.10.2026)

- MSVC (`dobor_msvc.md`, 14 przypadków, 100 przebiegów, 4,0 min, tło 20–21%, wszystkie zgodne; pojedyncze przebiegi
  przy zwykłym użyciu komputera, obserwacje wstępne):
  - wymiana: te same komunikaty i bajty (typ pochodny = dane bez flag); czas wymiany d / m ×0,45–0,64 (front lawy),
    ×0,46–0,59 (classic 300³), ×0,63–0,67 (pełny przebieg lawy); MC 100³ od ×0,19 do ×1,46 (w MC czas wymiany zawiera
    czekanie na wolniejszy pas po kolorze); budowa typów 0,03–0,36 ms na cały przebieg;
  - rozsyłanie: config JSON 881–980 B, struktura 219 B; budowa `Config` na procesach ≠ 0: JSON 0,27–2,9 ms, struktura
    0,04–0,08 ms; `MPI_Bcast` ~0,6–0,7 ms w obu; kratery 56 B (Etna), zarodki 6 408 B (classic 2000²);
  - zapis classic 300³ bin (351 MB): `save` p = 1 750 → 451 ms, p = 8 540 → 394 ms (znika zebranie 196 ms), szczyt
    pamięci procesu 0 p = 8 469 → 118 MB; txt (562 MB): p = 1 wolniej (2 157 → 2 539 ms), p = 4 / 8 ×0,54 / ×0,48;
    classic 2000² bin (52 MB): MPI-IO 54–81 ms wobec 23 ms strumieniem;
  - odczyt `--mc-from` classic 300³: proces 0 (cały plik, 13 B na komórkę) 515–566 ms, MPI-IO (pasy 3 tablic, 5 B na
    komórkę) 23–43 ms.
- GCC (`dobor_gcc.md`, WSL, ext4, węższy zestaw wariantów, 2,6 min, tło 18–26%): zapis tekstu przez MPI-IO (OMPIO)
  wolniejszy niż jeden proces (classic 300³ txt p = 8 `save` 1 319 → 1 889 ms); bin p = 8 ×0,69.
- ROMIO zamiast OMPIO (`mpiexec --mca io romio321`, classic 2000², 8 procesów, 2 × 2 przebiegi na ext4): `save`
  120–147 ms wobec 285–294 ms, tekst przez MPI-IO 55–77 wobec 175–199 ms, bin 42–45 wobec 55–76 ms; pliki identyczne.
  W planie osobna część GCC z ROMIO (`--mpiexec` z opcjami).

## Pomiar (21.10.2026, 10:10–10:33)

Przed pomiarem: SHA-256 binarek = końcowe, `/tmp` w WSL = ext4 (236 GB wolne), dysk systemowy 78 GB wolne, tło
17–20%; próba z planu (`bcast_etna_real` m3 / m3s, MSVC i GCC) bez różnic. Każdy przebieg pisze nowy plik (folder
usuwany przed i po przebiegu, warianty naprzemiennie), więc wszystkie zapisy są w tych samych warunkach („ciepła”
pamięć podręczna systemu plików); pierwszy przebieg części to rozgrzewka poza wynikami. Odczyt `--mc-from` zawsze
z pliku w pamięci podręcznej.

| Część | Plik | Czas, tło | Wynik |
|---|---|---|---|
| A (MSVC, wymiana lawy) | `pomiar_msvc_cz1.md` | 3,8 min, 15 → 14% | bajty i komunikaty stałe, d = m bez flag (18–116 B mniej); typy 4 / 16 / 34 / 50 (front), 2× więcej w `full`. Wymiana d / m ×0,60–0,72 (front), ×0,63–0,75 (full); faza ×0,92–1,00. Pojedyncze przebiegi odstające (front m4 836 ms wobec ~399) bez wpływu na medianę |
| B (MSVC, wymiana classic 300³, MC 100³, rozsyłanie) | `pomiar_msvc_cz2.md` | 3,4 min, 12 → 13% | wymiana classic 300³ ×0,50–0,53, faza ×0,91–0,97; MC 100³ wymiana ×0,84–0,89 (p = 2–7), ×1,04 (p = 8), faza ×0,98–1,00; rozsyłanie: budowa `Config` 0,26–0,41 → 0,04–0,07 ms, `MPI_Bcast` 0,46–0,68 ms w obu, razem < 1,1 ms |
| C (MSVC, zapis classic 300³) | `pomiar_msvc_cz3.md` | 5,5 min, 12 → 12% | rozmiary plików stałe (351 000 020 / 562 292 586 B); bin: `save` i / m ×0,62–0,80, sam plik przez MPI-IO przy p ≥ 2 nieco wolniej (286–328 wobec 278–280 ms), zysk = brak zebrania (164–175 ms); pamięć procesu 0 p = 8: 469 → 118 MB. txt: p = 1 ×1,18 (wolniej), p = 2 / 4 / 8 ×0,77 / ×0,53 / ×0,40 (formatowanie 1 614 → 208 ms przy 8 procesach, MPI-IO ~490–520 ms niezależnie od p) |
| D (MSVC, zapis classic 2000² i lawy 3D, odczyt) | `pomiar_msvc_cz4.md` | 3,0 min, 13 → 12% | classic 2000² bin `save` ×0,80 (p = 1), ×0,93–1,04 (p ≥ 2; plik przez MPI-IO 44–49 ms wobec 22 ms jednym strumieniem); txt ×1,17 (p = 1), ×0,74 / ×0,46 / ×0,32 (p = 2 / 4 / 8). Lawa 3D (14–19 MB): bin p = 8 ×1,29 (wolniej), txt p = 8 ×0,38. Odczyt classic 300³: 515 + 17–31 ms (proces 0 + `MPI_Scatterv`) → 20–44 ms, `total` −10 / −21% |
| E (GCC, wymiana m8 / m8d) | `pomiar_gcc_cz1.md` | 1,0 min, 16 → 16% | procesory WSL `0 2 4 6 1 3 5 7`; wymiana lawa front ×0,68, classic 300³ ×0,59, MC 100³ ×1,02; faza ×0,89 / ×0,97 / ×1,00 (rozrzut powtórzeń WSL ±10–20%) |
| F (GCC, zapis OMPIO) | `pomiar_gcc_cz2.md` | 1,2 min, 13 → 19% | p = 8: classic 300³ bin ×0,77 (zebranie 227 ms znika, sam plik 335 wobec 214 ms), txt ×0,88; classic 2000² bin ×1,62 (wolniej), txt ×0,95. Pliki tekstowe w WSL o 1 B na wiersz mniejsze (koniec wiersza `\n` zamiast `\r\n`) |
| G (GCC, odczyt) | `pomiar_gcc_cz3.md` | 1,5 min, 10 → 19% | proces 0 czyta cały plik szybciej niż w Windows (classic 300³ 101–106 ms wobec 515 ms), pasy przez MPI-IO 20 ms (p = 1) i 54 ms (p = 8); lawa 3D p = 8 ×1,10 (oba ~7–8 ms) |
| G2 (GCC, rozsyłanie) | `pomiar_gcc_cz4.md` | 0,2 min, 14 → 20% | `MPI_Bcast` 0,06 → 0,03 ms, budowa `Config` 0,14 → 0,02 ms; zarodki classic 2000² (6 408 B) 0,1–1,8 ms |
| H (GCC, zapis ROMIO) | `pomiar_gcc_romio.md` | 1,2 min, 17 → 24% | p = 8: classic 300³ bin ×0,59, txt ×0,49; classic 2000² bin ×0,78, txt ×0,50, wyraźnie lepiej niż OMPIO; sam zapis MPI-IO txt 300³ 418 wobec 899 ms |

- 9 części, ok. 23 min pomiaru, tło 10–24% (stałe), żadna część nie wymagała powtórki, wszystkie przebiegi bitowo
  zgodne; `priority` = `high`, procesory zgodne z planem. Scalone tabele: `pomiar_msvc.md`, `pomiar_gcc.md`.
- Wykresy `python bench/plot_mpi_io.py` (5 obrazów).
