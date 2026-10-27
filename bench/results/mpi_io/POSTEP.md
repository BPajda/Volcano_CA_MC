# Etap 11 — dziennik postępu (typy pochodne MPI i równoległy zapis MPI-IO)

Plik prowadzony na bieżąco w trakcie etapu 11: każdy krok, jego pliki, wyniki, zgodność bajtowa i obciążenie tła.
Opis implementacji: [`docs/mpi-typy-i-zapis.md`](../../../docs/mpi-typy-i-zapis.md). Etap 10 (MPI):
[`docs/mpi.md`](../../../docs/mpi.md), dziennik [`../mpi/POSTEP.md`](../mpi/POSTEP.md).

Oznaczenia: `e10` = programy po etapie 10 (`bench/baseline/engine_e10_*`, `engine_mpi_e10_*`; binarki lokalne, katalog
`bench/baseline/` jest w `.gitignore`), `mN` = `engine_mpi` na N procesach. Nowe opcje (`mpi.pack`, `mpi.bcast`,
`mpi.io`) w skrócie: `d` = `pack = datatype`, `s` = `bcast = struct`, `i` = `io = mpiio` (np. `m3dsi` — 3 procesy,
wszystkie trzy nowe ścieżki). Tło = obciążenie całego CPU przez inne programy (psutil, 2 s). Tryb oszczędny (od etapu 8,
do końca projektu): procesor bez turbo, WSL 8 procesorów / 8 GB, buildy `--parallel 4` / `-j 4`, jedna ciężka
operacja naraz, łącznie najwyżej 8 procesów × wątków na rdzeniach P.

## Tabela kroków

| Krok | Stan | Pliki wyników | Wynik | Zgodność | Tło [% CPU] | Uwagi |
|---|---|---|---|---|---|---|
| 0.1 Tryb oszczędny | zrobione | — | rdzeń P pod obciążeniem 96,9–97,0% taktowania bazowego (bez turbo); WSL `nproc` = 8, 7 GB | — | 33 | `PROCTHROTTLEMAX` i `PROCTHROTTLEMAX1` = 99% (sieć i bateria) |
| 0.2 MPI-IO | zrobione | — | MS-MPI 10.1: nagłówek ma MPI-IO, `create_struct`, `subarray`, `resized`, `Exscan`; OpenMPI 4.1.2: `io` = OMPIO / ROMIO 3.2.1 — oba działają na ext4 i na dysku Windows (9p), 9p 8–16× wolniej | — | — | punkt 0.2 dziennika |
| 0.3 Opcje configu | zrobione | — | `mpi.pack` (`manual` / `datatype`), `mpi.bcast` (`json` / `struct`), `mpi.io` (`gather` / `mpiio`); walidacja, opisy w GUI | — | — | domyślne = etap 10 |
| 1 Typy pochodne | zrobione | — | wymiana typem `MPI_Type_create_struct` z warstw pól (dwa zestawy `cur` / `next`, `changed`: flagi + typ na maskę); blok configu 215 B (`sizeof` 232 B); kratery jako tablica struktur | testy 1–8 procesów | — | punkt „Implementacja” |
| 2 MPI-IO | zrobione | — | bin: widok struct z `subarray`, `MPI_File_write_all`; txt: `MPI_Exscan` + `write_at_all`; odczyt `--mc-from` pasami; `stats.json` z `MPI_Reduce` | testy 1–8 procesów | — | poprawka MS-MPI (typ pamięci nie od `MPI_BOTTOM`) |
| 3 Testy, zgodność | zrobione | `zgodnosc_mpi_io_{msvc,gcc,full}.md`, `zgodnosc_e11_engine*.md`, `ab_e11_*.md` | `ctest` 21/21: MSVC Release i Debug, GCC; `VOLCANO_MPI=OFF` 12/12; `pytest` 102/102; mutacje M1–M6 wykryte | **15/15** we wszystkich tabelach | 28–36 (A/B) | binarki `engine_mpi_e11_*`, `engine_e11_*` |
| 4 Dokumentacja wstępna | zrobione | `docs/etap-11-mpi-typy-io.md` | implementacja, schematy (tekstowe), zgodność, ograniczenia; wyniki — część 2 | — | — | + `docs/README.md`, `architektura.md`, `uruchamianie.md`, `bench/README.md` |
| 5 Plan pomiaru | zrobione | `dobor_{msvc,gcc}.md`, `PLAN_POMIARU.md` | 9 części, MSVC ~19 min, GCC ~8 min (z ROMIO), razem ~30 min | dobór: wszystkie przebiegi zgodne | 18–26 | — |
| 6 Cichy pomiar | zrobione | `pomiar_msvc*.md`, `pomiar_gcc*.md`, `pomiar_gcc_romio.md` (+ `_raw.csv`) | 9 części, ~23 min, bez powtórek; wymiana d / m ×0,50–0,75 (MC ×0,84–1,04), faza ×0,91–1,00; zapis duży i / m ×0,40–0,80, małe ×0,93–1,62; odczyt ×0,04–0,43 | wszystkie przebiegi bitowo zgodne | 10–24 | punkt „Część 2” |
| 7 Wykresy | zrobione | `docs/img/etap11_*.png` (5) | `bench/plot_etap11.py`: schemat, wymiana, zapis, udział zapisu, odczyt | — | — | jedna poprawka (schemat, odczyt) |
| 8 Dokumentacja | zrobione | `docs/etap-11-mpi-typy-io.md` | punkty 8 (wyniki), 9 (ograniczenia), 10 (klaster), 11 (etap 12); README, `docs/README.md`, `uruchamianie.md`, `architektura.md`, `bench/README.md`, `CLAUDE.md` | eksport: słownictwo 0 trafień | — | — |

## Dziennik

### Część 1 (21.10.2026, od 04:50)

- Stan repozytorium: ostatni commit „etap 10: MPI”, `git status` czysty.
- **Tryb oszczędny:** `powercfg /qh … PROCTHROTTLEMAX` i `PROCTHROTTLEMAX1` = 0x63 (99%) dla zasilania sieciowego
  i baterii, zasilanie sieciowe (bateria 100%); pętla w Pythonie przypięta do procesora logicznego 2, licznik
  „% wydajności procesora”: 97,0 / 96,9 / 96,9 / 96,9 / 96,9% — **bez turbo**. WSL (`.wslconfig`): `processors=8`,
  `memory=8GB`; `nproc` = 8, 7 GB. Tło 33% CPU (programy działające w tle, np. narzędzia producenta laptopa).
- Binarki odniesienia z etapu 10 są: `bench/baseline/engine_e10_{msvc.exe,gcc}`, `engine_mpi_e10_{msvc.exe,gcc}`.
- **0.2 Wsparcie MPI-IO.**
  - MS-MPI 10.1.12498.52 (SDK): `mpi.h` deklaruje `MPI_File_open`, `MPI_File_set_view`, `MPI_File_write_at_all`,
    `MPI_File_write_all`, `MPI_File_read_at_all`, `MPI_File_set_size`, `MPI_Type_create_subarray`,
    `MPI_Type_create_struct`, `MPI_Type_create_resized`, `MPI_Get_address`, `MPI_Exscan` oraz typy o stałym rozmiarze
    (`MPI_INT32_T`, `MPI_UINT64_T`, `MPI_UINT8_T`, …), choć zgłasza `MPI_VERSION 2.0`. Zapis na NTFS — sprawdzony
    programem (punkt 2 niżej).
  - OpenMPI 4.1.2 w WSL: komponenty `io` — **OMPIO** (domyślny; `fs: ufs`, `fcoll: vulcan / dynamic / two_phase /
    individual`, `fbtl: posix`) i **ROMIO 3.2.1** (`--mca io romio321`). Próba (program w folderze tymczasowym:
    4 procesy, każdy pisze swój pas 4 MB przez `MPI_File_write_at_all` i drugi raz przez widok
    `MPI_Type_create_subarray` + `MPI_File_write_all`, proces 0 czyta plik i sprawdza bajty): **ext4 (`/tmp`)** — OMPIO
    60 ms, ROMIO 15 ms, plik poprawny; **dysk Windows przez 9p (`/mnt/<dysk>`)** — też poprawny (bez błędów blokad),
    ale OMPIO 465 ms, ROMIO 239 ms, czyli 8–16× wolniej (pojedyncze przebiegi, czasy orientacyjne). Wniosek: w WSL
    MPI-IO tylko na ext4 (`/tmp` albo katalog w systemie plików WSL) — testy i pomiary piszą tam, a na dysk Windows
    trafiają dopiero kopie do porównania.
- **Implementacja (05:00–06:05)** — kod opisany w `docs/etap-11-mpi-typy-io.md`:
  - config: `mpi.pack` (`manual` / `datatype`), `mpi.bcast` (`json` / `struct`), `mpi.io` (`gather` / `mpiio`);
    walidacja w `Config::fromJson`, odczyt metodami `mpiPackDatatype()`, `mpiBcastStruct()`, `mpiIoParallel()`
    z `effective` (bez nowych pól struktury `Config` — układ kodu MSVC, etap 6); opisy w `gui/static/js/form.js`;
  - `engine/src/mpi/MpiTypes.*` — `MpiType` (zwalnianie typu), `ConfigBlock` + `MPI_Type_create_struct`
    (20 pól, `offsetof`, `MPI_Type_create_resized` do `sizeof`), typ `Vent` (tablica kraterów / zarodków);
  - `MpiHalo` — `runTyped`: typ warstwy pola `MPI_Type_contiguous`, komunikat `MPI_Type_create_struct` z adresów
    bezwzględnych (`MPI_BOTTOM`), kolejne warstwy tego samego pola łączone w jeden blok; typy w pamięci podręcznej
    (bufor, kierunek, komunikat, maska flag) — dwa zestawy w pełnym przebiegu (zamiana `cur` / `next`); `changed`:
    flagi osobnym komunikatem, dane typem z warstw z flagą 1;
  - `engine/src/mpi/MpiIo.*` — zapis bin: widok `MPI_File_set_view` = `MPI_Type_create_struct` z
    `MPI_Type_create_subarray` każdej tablicy, `MPI_File_write_all` od `MPI_BOTTOM`, nagłówek `MPI_File_write_at`
    (proces 0), `MPI_File_set_size`; txt: wiersze pasa formatowane tym samym kodem co `writeTxt`, `MPI_Exscan`,
    `MPI_File_write_at_all` (porcje < 2 GB); odczyt `--mc-from`: `MPI_File_read_at_all` pasa `type`, `solidStep`,
    `arrivalStep`;
  - `ResultWriter` — `binHeader`, `crystalBinHeader`, `txtHeader`, `appendTxtRows`, `appendCrystalTxtRows`
    (`LineBuffer` jako szablon: plik albo napis); `ResultReader::readBinHeader`; `Simulation::buildStats` rozdzielone
    na `flowSums` (sumy po ziarnach w pasie) i `statsFromSums` — przy `mpi.io = mpiio` stats.json z sum `MPI_Reduce`
    (bez zebrania siatki CA na procesie 0);
  - `MpiSimulation` — rozsyłanie configu (`json` / `struct`), kratery z procesu 0 (`struct`), zapis CA / MC / migawek
    i odczyt `--mc-from` przez MPI-IO, `times.json`: `mpi.pack`, `mpi.bcast.{mode, configPrepMs, configBuildMs,
    ventsBytes, ventsMs}`, `mpi.ca/mc.{typesBuilt, typeBuildMs}`, `mpi.io` (pliki: bajty, formatowanie i MPI-IO
    min / średnia / maks, MB/s; odczyt).
  - Zaległość z etapu 10: zmienne numerów procesów w `engine/tests/test_strip.cpp` → `rank0` / `rank1` (stara nazwa
    dawała fałszywe trafienie kontroli słownictwa eksportu).
- Pierwsza próba (GCC/OpenMPI, 3 procesy, `test_3d` i `lava_mc_2d` z MC szachownicą, `output.format = both`):
  e10 vs nowy `engine_mpi` z `d`, `s`, `i`, `dsi`, `di` + `changed` — **wszystkie pliki bajtowo zgodne** (bez
  poprawek). `test_3d` m3: `manual` 1 420 komunikatów / 82 895 908 B, `datatype` 1 420 / 82 885 968 B (bez
  9 940 B flag), 10 typów komunikatów (5 wysyłek + 5 odbiorów na 3 procesach), budowa typów 0,008 ms; `datatype +
  changed` 2 141 komunikatów (flagi + dane) / 21,4 MB, 460 typów (różne maski flag), budowa 1,1 ms; config `struct`
  219 B wobec 871 B JSON, budowa Config na procesach ≠ 0: 0,008 ms wobec 0,075 ms; kratery 56 B.
- **Testy** (`engine/tests/mpi/test_mpi.cpp`, 3 nowe przypadki; `test_io.cpp` — pasy tekstu = `writeTxt`, nagłówki,
  `readBinHeader`; `test_config.cpp` — nowe opcje): typy w wymianie = pakowanie (lawa 2D / 3D front i full, classic
  pierścień i x–y, MC 2D / 3D, `always` i `changed`, hybryda; komunikaty i bajty: `always` — te same komunikaty, bajty
  = pakowanie − flagi; `changed` — te same bajty i warstwy pominięte); blok configu po `MPI_Bcast` = config wczytany
  lokalnie (5 configów, `memcmp`), blok → Config → blok bez zmian, extent typów = `sizeof`; kratery / zarodki
  z procesu 0 = wyznaczone lokalnie (lawa crater / random / positions, classic 3D i x–y); **pliki bajt po bajcie**
  (`MpiSimulation::runFromCli` w procesie testów vs `Simulation::run` / `runMcFrom`) — 9 przypadków (lawa 2D, 3D
  front z migawkami, 3D full, classic VN pierścień 17 warstw, classic x–y Moore, MC 2D z migawkami, MC 3D,
  lawa + MC, `--mc-from`) × 10 kombinacji (8 × pack/bcast/io + `md`/`mdsi` z `changed`) + hybryda 2 × 4 (m i mdsi).
  GCC Release: build bez ostrzeżeń, **`ctest` 21/21** (`mpi_np1…8` po 9–13 s); 3 procesy: 12 przypadków, 825 asercji.
- **Czułość nowych testów (mutacje, każda osobno, cofnięte; 3 procesy):** M1 zapis bin od warstwy 0 zamiast `lo`,
  M2 tekst bez przesunięcia `MPI_Exscan`, M3 odczyt `arrivalStep` spod adresu `solidStep`, M4 `datatype + changed`
  bez kopii odebranych warstw do drugiego bufora, M5 typ bloku configu bez jednego pola (`mobilityMin`), M6 typ
  nadawcy opisuje złą warstwę — **każda wykryta** (M1–M3: test plików; M4, M6: test plików i test wymiany; M5: test
  bloku i test plików).
- **MSVC / MS-MPI (05:25–05:38):** build Release bez ostrzeżeń; `ctest` — **5 testów MPI (np2…np8) nie przeszło**:
  `engine_mpi` kończył się naruszeniem dostępu (0xc0000005) przy zapisie `mc_result.bin` przez MPI-IO (CA — 5 tablic —
  działał). Przyczyna: typ pamięci z **jednym** blokiem pod adresem bezwzględnym, zapis od `MPI_BOTTOM` — MS-MPI (ROMIO)
  uznaje taki typ za ciągły i czyta dane od samego wskaźnika bufora (adres 0). OpenMPI (OMPIO) robi to poprawnie.
  Poprawka w `MpiIo.cpp` (`writeStrips`): przesunięcia bloków względem tablicy o najniższym adresie, a ta tablica jest
  buforem zapisu (bez `MPI_BOTTOM` w MPI-IO; wymiana warstw zostaje przy `MPI_BOTTOM` — tam MS-MPI działa, także
  z jednym blokiem w MC). Po poprawce: MSVC `ctest` **21/21** (`mpi_np1…8` po 20–30 s — pliki tymczasowe na NTFS),
  GCC `ctest` **21/21**; 2 procesy MS-MPI: 12 przypadków, 877 asercji.
- `bench/compare_results.py`: programy WSL piszą wyniki na ext4 (`/tmp/volcano_cmp`), do porównania trafia kopia;
  folder `--mc-from` kopiowany przed przebiegiem na ext4. Próba (`test_3d`, `lava_mc_2d`, `mc_basalt`; e10_gcc m3 vs
  GCC i MSVC `dsi` m3) — zgodne.
- **Binarki etapu 11** (05:41): `bench/baseline/engine_e11_msvc.exe` (e6b8fb86…), `engine_mpi_e11_msvc.exe`
  (f2909f24…), `engine_e11_gcc` (6412c777…), `engine_mpi_e11_gcc` (2b650212…).
- 05:42–05:43 **zgodność zwykłego engine** e10 / e11: [`zgodnosc_e11_engine.md`](zgodnosc_e11_engine.md) — **15/15:
  e10 = e11 = e10_gcc = e11_gcc**; [`zgodnosc_e11_engine_t8.md`](zgodnosc_e11_engine_t8.md) (8 wątków, MC
  szachownicą) — **15/15** (e10 = e11 = e11_gcc).
- W toku: A/B narzutu engine e10 / e11 (1 wątek, procesor 2), MSVC, lawa (3 przypadki), classic 1000² VN (z zapisem txt), MC 1000², lawa + MC 3D, 9 powtórzeń, start 05:44, tło 30% (stabilne), polecenie: `python bench\ab.py --bin e10=bench\baseline\engine_e10_msvc.exe --bin e11=bench\baseline\engine_e11_msvc.exe --cases lava_test_3d,lava_etna_real,lava_mc_2d_ca,classic_1000x1000_s100_vn,mc_full_2d_1000,lava_mc_3d --reps 9 --name ab_e11_msvc --out bench\results\mpi_io` (potem to samo `--wsl` z `engine_e1x_gcc` → `ab_e11_gcc`)
  - 05:44–05:48 MSVC (pierwsza wersja, zapisana jako `ab_e11a_msvc.md`): fazy obliczeń ×0,99–1,01, ale **zapis
    `save` classic 1000² ×1,098**. Sprawdzenie plików (`times.json` → `files`, 9–15 powtórzeń naprzemiennie, procesor
    2): `ca_result.txt` 63–64 → 69–70 ms (+9%), `ca_result.bin` bez zmian. `LineBuffer` z powrotem jako zwykła klasa
    — bez zmian (69,8 ms); próba z pustymi `appendTxtRows` / `appendCrystalTxtRows` — 64,6 ms (jak e10). Przyczyna:
    nowe pętle formatowania w tym samym pliku co `writeTxt` zmieniały decyzje MSVC o wstawianiu funkcji pomocniczych
    w `writeTxt` (bez zmiany jego kodu źródłowego). **Poprawka:** `txtHeader`, `appendTxtRows`,
    `appendCrystalTxtRows` w osobnym pliku `engine/src/io/ResultWriterSlabs.cpp` (drobne funkcje znaków skopiowane,
    `formatTemp` wspólne; `engine.exe` tego pliku nie dołącza — biblioteka statyczna); `ResultWriter.cpp` różni się
    od e10 tylko nagłówkami `binHeader` / `crystalBinHeader`. Wynik (15 powtórzeń, tło 36%): e10 62,6 ms, e11 63,6 ms
    (+1,6%), pierwsza wersja 69,4 ms. Pierwsze binarki zapisane jako `engine_e11a_*`, `engine_mpi_e11a_*`.
  - 05:55–05:58 po poprawce: MSVC Release i GCC Release bez ostrzeżeń, `ctest` **21/21** w obu.
- **Binarki końcowe etapu 11** (05:59): `engine_e11_msvc.exe` (ad2f33ac…), `engine_mpi_e11_msvc.exe` (51a28442…),
  `engine_e11_gcc` (40d8d186…), `engine_mpi_e11_gcc` (971f30a7…). Zgodność zwykłego engine powtórzona:
  `zgodnosc_e11_engine.md` i `_t8.md` — **15/15** (06:00).
- 06:01–06:05 **A/B e10 / e11 MSVC** ([`ab_e11_msvc.md`](ab_e11_msvc.md), 9 powtórzeń, tło 28%): lawa caSim ×0,995–0,998,
  classic 1000² caSim ×0,991, **`save` ×1,000**, MC 1000² mcSim ×0,994, lawa + MC mcSim ×1,013 / caSim ×1,009; cały
  przebieg ×0,968–1,010. Wszystkie przebiegi bitowo zgodne.
- 06:06–06:10 **A/B e10 / e11 GCC** ([`ab_e11_gcc.md`](ab_e11_gcc.md), WSL, tło 29%): lawa caSim ×0,980–1,028, classic
  1000² caSim ×0,932 / `save` ×0,998, MC 1000² mcSim ×1,026, lawa + MC ×1,012 / ×0,988; cały przebieg ×0,987–1,026
  (przedziały min–max e10 i e11 się nakładają). Kod automatu i MC w GCC jest ten sam: `nm -S` — 144 ze 156 funkcji
  `LavaCA` / `PottsMC` / `Grains` / `Boundary::apply` / `McStage::run` mają ten sam rozmiar i adres mod 64, różnią się
  tylko fragmenty `.cold` (ścieżki błędów, nie są wyrównywane) i `McStage::run` (+8 B przesunięcia, poza pętlą MCS).
  Różnice ±3% w GCC to więc szum procesorów wirtualnych WSL (jak w etapach 9–10). **Narzut domyślnego engine:
  brak** (MSVC ≤ 1,5% we wszystkich miarach; GCC w granicach szumu przy identycznym kodzie gorących funkcji).
- **Zgodność wszystkich configów `engine_mpi`** (`compare_results.py`, `mc.update = checkerboard`, binarki końcowe;
  odniesienie: `engine_mpi_e10` na 3 procesach; `d` / `s` / `i` — `pack = datatype` / `bcast = struct` /
  `io = mpiio`, `c` — `exchange = changed`):
  - 06:11–06:12 [`zgodnosc_mpi_io_msvc.md`](zgodnosc_mpi_io_msvc.md) — **15/15: e10 m3 = m3 (domyślne = etap 10) = d3
    = s3 = i3 = dsi1 = dsi3 = dsi8 = dsi 2 × 4 = dsi8c = dsi3_gcc** (krzyżowo GCC/OpenMPI; 76 s);
  - 06:12–06:15 [`zgodnosc_mpi_io_gcc.md`](zgodnosc_mpi_io_gcc.md) — **15/15: e10_gcc m3 = m3 = d3 = s3 = i3 = dsi1 = dsi3
    = dsi8 = dsi 2 × 4 = dsi8c** (GCC/OpenMPI, wyniki na ext4; 177 s);
  - 06:15–06:20 [`zgodnosc_mpi_io_full.md`](zgodnosc_mpi_io_full.md) (`ca.sweep = full` — dwa zestawy typów `cur` /
    `next`) — **15/15: e10 m3 = dsi3 = dsi8 = dsi 2 × 4 = dsi8c = dsi8_gcc = dsi8c_gcc** (310 s).
- 06:21–06:23 **GCC z `VOLCANO_MPI=OFF`** (`build-gcc-nompi/`): build bez ostrzeżeń, `ctest` **12/12**, program `engine`
  bajtowo ten sam co z MPI (SHA-256 40d8d186… = `engine_e11_gcc`). **`pytest gui\tests` 102/102**; `node --check
  gui/static/js/form.js` — składnia poprawna.
- 06:24–06:27 skrypty pomiaru: `bench/scaling_mpi.py` — przyrostki wariantów `d` / `s` / `i` (np. `m8d`, `m4i`,
  `h2x4dsi`), opcjonalne `--mc-from`, nowe miary z `times.json` (pliki wyników, `mpi.io`, `mpi.bcast`, typy); nowy
  `bench/mpi_io.py` (grupy `pack` / `bcast` / `io` / `read`). Przerwa 06:27–08:44 (skrypty jeszcze niesprawdzone).

### Część 1 — sesja 2 (21.10.2026, od 08:44)

- Stan na początku: binarki w `build/Release` i `build-gcc-release/bin` = końcowe `e11` (SHA-256 jak wyżej), tryb
  oszczędny bez zmian (`PROCTHROTTLEMAX` / `PROCTHROTTLEMAX1` = 99%, zasilanie sieciowe), WSL 8 procesorów / 8 GB,
  tło 20%. Zostało: sprawdzenie skryptów, dobór przypadków, plan pomiaru, MSVC Debug, dokumentacja.
- 08:48–08:51 **próba `bench/mpi_io.py`** (MSVC, 1 powtórzenie, wyniki w folderze tymczasowym): grupy `bcast`
  (`etna_real` m1 / m1s / m3 / m3s), `pack` (lawa front m1 / m4 ± d), `io` (classic 2000² bin i txt, m1 / m4 ± i),
  `read` (lawa front, m1 / m4 ± i) — przebiegi bitowo zgodne; poprawiony błąd tabel (dzielenie przez zero przy
  1 procesie — brak wymiany). `readInput` przy `mpiio` = nagłówek + odczyt pasa (`TimingReport::add` sumuje).
- **Poprawka pomiaru zapisu CA** (08:52): w trybie gather sekcja `save` = `ca.gatherMs` (kopia pasa okna bez ramki,
  `ownLayers`, + `MPI_Gatherv`) + zapis plików, a w trybie `mpiio` — tylko zapis plików: kopia pasa (classic 2000²,
  2 procesy: ~21 ms z 46 ms `ca.gatherMs`) nie trafiała do żadnej sekcji, więc porównanie zapisu byłoby zawyżone na
  korzyść MPI-IO. Teraz `save` w obu trybach liczy się od końca fazy CA (`MpiSimulation.cpp`, gałąź `mpiio`:
  `ca.gatherMs` + zapis). Wyniki bez zmian (tylko czas). Zapis MC był już spójny (kopia mapy kryształów w obu trybach
  w `mcStats`). Skrypty: `scaling_mpi.py` zapisuje też `peakRoot` (szczyt pamięci procesu 0), `peakMax`, `caPrepMax`
  (`mpi.ca.gatherMs`); tabela zapisu `mpi_io.py` — kolumna pamięci procesu 0 (classic 2000², 2 procesy: gather 119 MB,
  `mpiio` 82 MB).
- 08:53–08:59 przebudowa po poprawce: MSVC Release i GCC Release bez ostrzeżeń, `engine` bez zmian (AD2F33AC… /
  40d8d186…), `ctest` **21/21** w obu. **Binarki końcowe `engine_mpi`** (zastępują te z 05:59, przeniesione jako
  `engine_mpi_e11b_*`): `engine_mpi_e11_msvc.exe` (4667EECD…), `engine_mpi_e11_gcc` (301bd275…); `engine_e11_*` bez
  zmian.
- 08:59–09:09 tabele zgodności powtórzone na binarkach końcowych: [`zgodnosc_mpi_io_msvc.md`](zgodnosc_mpi_io_msvc.md)
  (74 s), [`zgodnosc_mpi_io_gcc.md`](zgodnosc_mpi_io_gcc.md) (177 s), [`zgodnosc_mpi_io_full.md`](zgodnosc_mpi_io_full.md)
  (287 s) — **wszystkie 15/15, 0 różnic** (te same warianty co wyżej).
- 09:09–09:24 **MSVC Debug** (z MS-MPI, `cmake --build --preset msvc-debug --parallel 4`): build bez ostrzeżeń (96 s);
  `ctest --preset msvc-debug` w częściach (limit czasu jednego polecenia) — **21/21**: 15 testów bez `mpi_np*` (214 s,
  głównie `unit_tests`), `mpi_np1` 104 s, `np2` 96 s, `np3` 86 s, `np4` 85 s, `np5` 82 s, `np8` 78 s (asercje Debug
  w kodzie MPI, typach i MPI-IO włączone; pliki tymczasowe testów na NTFS).
- 09:24–09:28 **dobór przypadków MSVC** ([`dobor_msvc.md`](dobor_msvc.md), `python bench\mpi_io.py --bin
  bench\baseline\engine_mpi_e11_msvc.exe --omp-bin bench\baseline\engine_e11_msvc.exe --reps 1 --min-reps 1 --name
  dobor_msvc`): 14 przypadków, 100 przebiegów, 4,0 min, tło 20–21%, wszystkie przebiegi bitowo zgodne. Pojedyncze
  przebiegi przy zwykłym użyciu komputera — obserwacje wstępne, bez wniosków:
  - **wymiana** (`pack`): te same komunikaty i bajty na wymianę (typ pochodny = dane bez flag); czas wymiany `d` / `m`
    ×0,45–0,64 (front lawy), ×0,46–0,59 (classic 300³), ×0,63–0,67 (pełny przebieg lawy, p = 4 i 7); MC 100³ od ×0,19
    do ×1,46 — w MC czas wymiany zawiera czekanie na wolniejszy pas po kolorze. Faza ×0,70–1,22 — szum pojedynczych
    przebiegów większy niż różnica (np. pełny przebieg lawy m8 4,7 s wobec 2,96 s w pomiarze etapu 10). Budowa typów
    0,03–0,36 ms na cały przebieg (4–100 typów);
  - **rozsyłanie** (`bcast`): config JSON 881–980 B, struktura 219 B; budowa `Config` na procesach ≠ 0: JSON 0,27–2,9 ms,
    struktura 0,04–0,08 ms; sam `MPI_Bcast` ~0,6–0,7 ms w obu (pierwsza operacja zbiorowa po starcie); kratery 56 B
    (Etna), zarodki 6 408 B (classic 2000², 400 zarodków);
  - **zapis** (`io`): classic 300³ bin (351 MB) — `save` p = 1 750 → 451 ms (bez kopii całej siatki do wyniku), p = 8
    540 → 394 ms (znika zebranie 196 ms; sam plik przez MPI-IO 353 ms wobec 306 ms jednym strumieniem), szczyt pamięci
    procesu 0: p = 8 469 → 118 MB, p = 1 1 144 → 794 MB; txt (562 MB) — p = 1 wolniej (2 157 → 2 539 ms: formatowanie
    do pamięci + MPI-IO zamiast zapisu strumieniem), p = 4 / 8 ×0,54 / ×0,48 (formatowanie równoległe 425 / 366 ms,
    MPI-IO 580 / 696 ms); classic 2000² bin (52 MB) — MPI-IO 54–81 ms wobec 23 ms strumieniem (`save` ×0,79–1,41);
    lawa 3D bin (14 MB) m8i — jeden przebieg 310 ms (MPI-IO 307 ms) wobec ~23 ms pozostałych;
  - **odczyt** `--mc-from` (`read`): classic 300³ — `readInput` procesu 0 (cały plik, 13 B na komórkę) 515–566 ms,
    MPI-IO (pasy 3 tablic, 5 B na komórkę, 135 MB) 23–43 ms; `total` ×0,78–0,86.
- 09:30–09:35 **dobór GCC** (WSL, ext4; po grupach z węższym zestawem wariantów: `pack` m4/m4d/m8/m8d, `io`
  m1/m1i/m4/m4i/m8/m8i, `bcast` m3/m3s/m8/m8s, `read` m1/m1i/m8/m8i; scalone [`dobor_gcc.md`](dobor_gcc.md)): 2,6 min,
  tło 18–26%, zgodne. Zapis tekstu przez MPI-IO (OMPIO — domyślny komponent OpenMPI) **wolniejszy niż jeden proces**:
  classic 300³ txt p = 8 `save` 1 319 → 1 889 ms (MPI-IO 1 733 ms); bin p = 8 ×0,69, p = 1 ×0,60.
- 09:37 **ROMIO zamiast OMPIO** (`mpiexec --mca io romio321`, classic 2000², 8 procesów, MPI-IO, 2 × 2 przebiegi
  na ext4): `save` 120–147 ms wobec 285–294 ms (OMPIO), tekst MPI-IO 55–77 wobec 175–199 ms, bin 42–45 wobec
  55–76 ms; pliki identyczne. Skrypty: `--mpiexec` może mieć opcje (`shlex.split`; `scaling_mpi.py` i `mpi_io.py`,
  przekazywane do WSL) — w planie osobna część GCC z ROMIO.
- Czas planu z doboru (suma czasów procesów × powtórzenia × 1,12 — narzut skryptu w doborze MSVC: 240 s / 214,5 s):
  MSVC ~19 min, GCC ~8 min → [`PLAN_POMIARU.md`](PLAN_POMIARU.md). Zawężenia względem listy przypadków: lawa 3D
  `io` i `read` — p = 1 i 8; GCC — `pack` i `io` p = 8, `read` p = 1 i 8, `bcast` p = 8 (wyniki porównawcze).
- 09:38–09:55 polecenia do dokumentacji sprawdzone (`engine_mpi` z `dsi`, `--mc-from` z `mpiio`, WSL na `/tmp` + kopia;
  `mpi_io.py` MSVC, `--wsl`, `--wsl --mpiexec "mpiexec --mca io romio321"`, `--from-raw`; `scaling_mpi.py` z `m4d` /
  `m4i`) — działają, wyniki zgodne. Dokumentacja: `docs/etap-11-mpi-typy-io.md` (wstępna), `docs/README.md`,
  `docs/architektura.md` (krok 6b i 9 — numery linii po zmianach, mapa, ściąga), `docs/uruchamianie.md` (testy,
  punkt 4.2, nowy 7.4, `times.json`, config, FAQ), `bench/README.md`. Eksport wersji minimalnej do folderu
  tymczasowego: wynik OK, **słownictwo spoza projektu: 0 trafień** (po zmianie nazw zmiennych w `test_strip.cpp`);
  ta sama kontrola na nowych dokumentach i wynikach etapu — 0 trafień, odnośniki względne — 0 złych.

## Stan na koniec części 1 — gotowe do cichego pomiaru

- **Kod silnika zamknięty.** Binarki końcowe (te same, które przeszły `ctest` 21/21 i tabele zgodności 15/15):
  `bench/baseline/engine_mpi_e11_msvc.exe` (SHA-256 4667EECD…), `engine_mpi_e11_gcc` (301bd275…),
  `engine_e11_msvc.exe` (AD2F33AC…), `engine_e11_gcc` (40d8d186…). Wersje pośrednie: `engine_mpi_e11b_*` (przed
  poprawką `save`), `engine_e11a_*` / `engine_mpi_e11a_*` (pierwsza wersja, zapis txt +9% w MSVC).
- **Pomiar:** [`PLAN_POMIARU.md`](PLAN_POMIARU.md) — przygotowanie ~3 min (tryb oszczędny, SHA-256, miejsce na dysku,
  próba), potem części A–D (MSVC) i E, F, G, G2, H (GCC, H — ROMIO), scalenie `pomiar_msvc`, `pomiar_gcc`; ok. 30 min.
  Skrypt `bench/mpi_io.py` sprawdzony na wszystkich grupach w obu kompilatorach (dobór: 100 + 68 przebiegów, wszystkie
  bitowo zgodne).
- **Do zrobienia w części 2:** cichy pomiar, wykresy `docs/img/etap11_*.png` (skrypt do napisania, np.
  `bench/plot_etap11.py`, na wzór `plot_etap10.py`), punkty 8 („Wyniki pomiaru”) i 10 („Wnioski dla etapu 12”) w
  `docs/etap-11-mpi-typy-io.md` + schematy jako rysunki, `README.md` (1–2 zdania), numery linii w `architektura.md`,
  jeśli się zmienią (kod silnika — nie).
- **Na co uważać przy pomiarze:** pojedyncze przebiegi odstające (dobór: lawa 3D bin m8i 310 ms wobec ~23 ms; pełny
  przebieg lawy m8 4,7 s wobec 2,96 s w etapie 10) — mediana z ≥ 5 powtórzeń; w MC czas wymiany zawiera czekanie;
  pliki tekstowe classic 300³ 562 MB — na dysku systemowym ~1,5 GB wolnego.

### Część 2 — cichy pomiar (21.10.2026, od 10:05)

- **Weryfikacja (10:05–10:09):** `git status` zgodny z dziennikiem (ostatni commit „etap 10: MPI”, zmiany etapu 11
  niezatwierdzone); `PROCTHROTTLEMAX` / `PROCTHROTTLEMAX1` = 0x63 (99%, sieć i bateria), zasilanie sieciowe (bateria
  100%); `.wslconfig` 8 procesorów / 8 GB, `nproc` = 8; SHA-256 binarek = końcowe z części 1 (`engine_mpi_e11_msvc.exe`
  4667EECD…, `engine_e11_msvc.exe` AD2F33AC…, `engine_mpi_e11_gcc` 301bd275…, `engine_e11_gcc` 40d8d186…);
  `mpiexec` MS-MPI i `mpiexec` / `mpirun` OpenMPI w WSL są; `/tmp` w WSL = ext4 (236 GB wolne), dysk systemowy 78 GB
  wolne; tło 17–20% (stałe, inny program w tle). Próba z planu (`bcast_etna_real` m3 / m3s, MSVC i GCC, 30 s):
  różnic 0, config 980 / 938 B (JSON, MSVC / GCC) i 219 B (struktura).
- W toku: część **A** (MSVC, wymiana: lawa front i full), start 10:10, polecenie: `python bench\mpi_io.py --bin
  bench\baseline\engine_mpi_e11_msvc.exe --omp-bin bench\baseline\engine_e11_msvc.exe --cases
  pack_lava_3d_front,pack_lava_3d_full --name pomiar_msvc_cz1 --out bench\results\mpi_io`
  - 10:10–10:14 **A** [`pomiar_msvc_cz1.md`](pomiar_msvc_cz1.md) (3,8 min): tło 15 → 14%, wszystkie przebiegi bitowo
    zgodne; kontrola: `priority` = `high`, procesory `2 4 …` (m7 bez 0, m8 z 0), bajty i komunikaty na wymianę stałe
    i równe w m / d (d = m bez flag: 18–116 B mniej), typy 4 / 16 / 34 / 50 (front), 2× więcej w `full`. Wymiana d / m
    ×0,60–0,72 (front), ×0,63–0,75 (full); faza ×0,92–1,00. Pojedyncze przebiegi odstające (front m4 836 ms wobec
    ~399, full m7 3 306 wobec ~2 619) — mediana bez wpływu, część bez powtórki.
- W toku: część **B** (MSVC, wymiana classic 300³, MC 100³ + rozsyłanie), start 10:15, polecenie jak A z `--cases
  pack_classic_300,pack_mc_cb_3d_100,bcast_etna_real,bcast_classic_2000 --name pomiar_msvc_cz2`
  - 10:14–10:18 **B** [`pomiar_msvc_cz2.md`](pomiar_msvc_cz2.md) (3,4 min): tło 12 → 13%, zgodne; bajty d = m − flagi
    (4–16 B), typy 4 / 16 / 28 / 32. Wymiana classic 300³ d / m ×0,50–0,53, faza ×0,91–0,97; MC 100³ wymiana ×0,84–0,89
    (p = 2–7), ×1,04 (p = 8), faza ×0,98–1,00 (jeden przebieg m8d 1 642 ms wobec ~870 — mediana bez wpływu).
    Rozsyłanie: budowa `Config` 0,26–0,41 → 0,04–0,07 ms, `MPI_Bcast` bez różnicy (0,46–0,68 ms), razem < 1,1 ms.
- W toku: część **C** (MSVC, zapis classic 300³ bin i txt), start 10:18, `--cases io_bin_classic_300,io_txt_classic_300
  --name pomiar_msvc_cz3`
  - 10:20–10:25 **C** [`pomiar_msvc_cz3.md`](pomiar_msvc_cz3.md) (5,5 min): tło 12 → 12%, zgodne; rozmiary plików stałe
    (351 000 020 / 562 292 586 B), `ioMode` = `mpiio` tylko w `…i`; rozrzut powtórzeń ≤ 2% (poza m1 bin: jeden 792 ms).
    bin: `save` i / m ×0,62–0,80, sam plik przez MPI-IO przy p ≥ 2 nieco wolniej (286–328 wobec 278–280 ms), zysk =
    brak zebrania (164–175 ms); pamięć procesu 0 p = 8: 469 → 118 MB. txt: p = 1 ×1,18 (wolniej), p = 2 / 4 / 8
    ×0,77 / ×0,53 / ×0,40 (formatowanie 1 614 → 208 ms przy 8 procesach, MPI-IO ~490–520 ms niezależnie od p).
- W toku: część **D** (MSVC, zapis classic 2000² i lawy 3D + odczyt `--mc-from`), start 10:26, `--cases
  io_bin_classic_2000,io_txt_classic_2000,io_bin_lava_3d,io_txt_lava_3d,read_lava_3d,read_classic_300 --name
  pomiar_msvc_cz4`
  - 10:23–10:26 **D** [`pomiar_msvc_cz4.md`](pomiar_msvc_cz4.md) (3,0 min): tło 13 → 12%, zgodne. classic 2000² bin:
    `save` ×0,80 (p = 1), ×0,93–1,04 (p ≥ 2; plik przez MPI-IO 44–49 ms wobec 22 ms jednym strumieniem); txt ×1,17 (p = 1),
    ×0,74 / ×0,46 / ×0,32 (p = 2 / 4 / 8). Lawa 3D (14–19 MB): bin p = 8 ×1,29 (wolniej), txt p = 8 ×0,38. Odczyt
    `--mc-from` classic 300³: 515 + 17–31 ms (proces 0 + `MPI_Scatterv`) → 20–44 ms (pasy, 135 MB), `total` −10 / −21%.
  - Scalenie: [`pomiar_msvc.md`](pomiar_msvc.md).
- W toku: część **E** (GCC, wymiana m8 / m8d), start 10:27, `python bench\mpi_io.py --wsl --bin
  bench/baseline/engine_mpi_e11_gcc --omp-bin bench/baseline/engine_e11_gcc --cases
  pack_lava_3d_front,pack_classic_300,pack_mc_cb_3d_100 --variants m8,m8d --name pomiar_gcc_cz1`
  - 10:25–10:26 **E** [`pomiar_gcc_cz1.md`](pomiar_gcc_cz1.md) (1,0 min): tło 16 → 16%, zgodne; procesory WSL
    `0 2 4 6 1 3 5 7`, `priority` = `high`. Wymiana m8d / m8: lawa front ×0,68, classic 300³ ×0,59, MC 100³ ×1,02;
    faza ×0,89 / ×0,97 / ×1,00 (rozrzut powtórzeń WSL ±10–20%).
- W toku: część **F** (GCC, zapis OMPIO, m8 / m8i), start 10:28, `--cases
  io_bin_classic_300,io_txt_classic_300,io_bin_classic_2000,io_txt_classic_2000 --variants m8,m8i --name pomiar_gcc_cz2`
  - 10:27–10:28 **F** [`pomiar_gcc_cz2.md`](pomiar_gcc_cz2.md) (1,2 min): tło 13 → 19%, zgodne. OMPIO, p = 8: classic
    300³ bin ×0,77 (zebranie 227 ms znika, sam plik 335 wobec 214 ms), txt ×0,88; classic 2000² bin ×1,62 (wolniej),
    txt ×0,95. Pliki tekstowe w WSL o 1 B na wiersz mniejsze niż w Windows (535 / 82 MB wobec 562 / 86 MB).
- W toku: część **G** (GCC, odczyt `--mc-from`, m1 / m1i / m8 / m8i), start 10:29, `--cases read_lava_3d,read_classic_300
  --name pomiar_gcc_cz3`
  - 10:29–10:30 **G** [`pomiar_gcc_cz3.md`](pomiar_gcc_cz3.md) (1,5 min): tło 10 → 19%, zgodne. Odczyt `--mc-from` w WSL:
    proces 0 czyta cały plik szybciej niż w Windows (classic 300³ 101–106 ms wobec 515 ms), pasy przez MPI-IO 20 ms
    (p = 1) i 54 ms (p = 8); lawa 3D p = 8 ×1,10 (oba ~7–8 ms).
- W toku: część **G2** (GCC, rozsyłanie m8 / m8s), start 10:31, `--cases bcast_etna_real,bcast_classic_2000
  --variants m8,m8s --name pomiar_gcc_cz4`
  - 10:30 **G2** [`pomiar_gcc_cz4.md`](pomiar_gcc_cz4.md) (0,2 min): tło 14 → 20%, zgodne. `MPI_Bcast` 0,06 → 0,03 ms,
    budowa `Config` 0,14 → 0,02 ms; zarodki classic 2000² (6 408 B) 0,1–1,8 ms.
  - Scalenie: [`pomiar_gcc.md`](pomiar_gcc.md).
- W toku: część **H** (GCC, zapis ROMIO, m8 / m8i), start 10:32, `--mpiexec "mpiexec --mca io romio321" --cases
  io_bin_classic_300,io_txt_classic_300,io_bin_classic_2000,io_txt_classic_2000 --variants m8,m8i --name
  pomiar_gcc_romio`
  - 10:32–10:33 **H** [`pomiar_gcc_romio.md`](pomiar_gcc_romio.md) (1,2 min): tło 17 → 24%, zgodne. ROMIO, p = 8: classic
    300³ bin ×0,59, txt ×0,49; classic 2000² bin ×0,78, txt ×0,50 — wyraźnie lepiej niż OMPIO (×0,77 / ×0,88 / ×1,62 /
    ×0,95), sam zapis MPI-IO txt 300³ 418 wobec 899 ms.
- **Koniec cichego pomiaru (10:33).** 9 części, ok. 23 min pomiaru (plan ~27 min), tło 10–24% (stałe, inny program
  w tle), **żadna część nie wymagała powtórki**, wszystkie przebiegi bitowo zgodne. Pamięć podręczna systemu plików:
  każdy przebieg pisze nowy plik (folder usuwany przed i po przebiegu, warianty naprzemiennie), więc wszystkie zapisy
  są w tych samych warunkach („ciepła” pamięć podręczna, bez wymuszania zapisu na dysk); pierwszy przebieg części to
  rozgrzewka poza wynikami. Odczyt `--mc-from` — zawsze z pliku w pamięci podręcznej.
- 10:34–10:45 **wykresy** (`bench/plot_etap11.py`, 5 obrazów `docs/img/etap11_*.png`; jedna poprawka: w schemacie
  podpisy bloków nachodziły na wiersz wyżej, w odczycie legenda zasłaniała etykietę) i **dokumentacja**:
  `docs/etap-11-mpi-typy-io.md` — skrót wyników na początku, schemat, punkt 8 (warunki, wymiana, rozsyłanie, zapis
  z trzema implementacjami MPI-IO, udział zapisu, odczyt, wnioski), 9 (pamięć podręczna systemu plików, ext4 vs NTFS),
  10 (przewidywania dla klastra), 11 (wnioski dla etapu 12); `README.md` (punkt „zrobione”), `docs/README.md`,
  `docs/uruchamianie.md` (7.4), `docs/architektura.md` (drzewo — numery linii bez zmian, kod silnika nie zmienił się),
  `bench/README.md`, `CLAUDE.md`. Eksport wersji minimalnej do folderu tymczasowego: **OK, słownictwo spoza projektu
  0 trafień**, odnośniki 0 złych; nowe pliki etapu (dokument, wyniki, skrypt wykresów) — 0 trafień, odnośniki 0 złych.

## Stan na koniec części 2 — etap 11 zakończony

- Kod silnika bez zmian od części 1 (binarki `engine_mpi_e11_*`, `engine_e11_*` — SHA-256 jak wyżej). Pomiar, wykresy
  i dokumentacja — zrobione. Do commita: zmiany części 1 (`engine/`, `gui/static/js/form.js`, `bench/*.py`, `docs/`)
  + części 2: `bench/plot_etap11.py`, `bench/results/mpi_io/pomiar_*`, `docs/img/etap11_*.png`,
  `docs/etap-11-mpi-typy-io.md`, `README.md`, `docs/README.md`, `docs/uruchamianie.md`, `docs/architektura.md`,
  `bench/README.md`, `CLAUDE.md`, ten dziennik.
