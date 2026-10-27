# src/mc: krystalizacja Monte Carlo

Rozrost ziaren Monte Carlo (model Pottsa, kroki 1–5 wersji naiwnej): krystalizacja zastygłej lawy
albo klasyczny rozrost MC na całej przestrzeni. Opis reguł: `McRules.hpp`; opis wersji:
`docs/monte-carlo.md`.

| Plik | Zawartość |
|---|---|
| `McRules.hpp` | opis algorytmu (kroki 1–5, domena, brzegi, mobilność, statystyki), `McParams`, `McStats` |
| `PottsMC.hpp/.cpp` | siatka z ramką (orientacja, maska domeny, mobilność), `initialize()`, `sweep()` = 1 MCS, energia, `measure()`; tryb szachownicy (`mc.update = checkerboard`, kolory komórek niebędących sąsiadami, wątki OpenMP) i pas wersji MPI (`setStrip`) |
| `Grains.hpp/.cpp` | liczba ziaren = spójne składowe tej samej orientacji (union-find, VN lub Moore, brzegi periodyczne) |
| `CoolingMobility.hpp/.cpp` | domena `basalt` (BASALT + LAVA) i mobilność z czasu w stanie płynnym `solidStep − arrivalStep` |

Integracja z programem (czasy `mcInit`, `mcSim`, `mcStats`, `mcSave`, zapis `mc_result.*`,
`mc_stats.csv`, sekcja `mc` w `stats.json`): `app/McStage.*`; uruchamianie: `app/Simulation.*`
(`mc.enabled` w configu albo `engine --mc-from <folder_wyniku_CA>`).

Wejście trybu `basalt`: `Microstructure` z CA (w pamięci albo `ResultReader::readFolder`;
`ca_result.bin` v2 ma `solidStep` i `arrivalStep`, z `ca_result.txt` mobilność jest niedostępna).

Optymalizacje wersji sekwencyjnej (liczenie sąsiadów bez skoku warunkowego, energia przed i po w jednym przejściu,
tańsze statystyki) są oznaczone w kodzie komentarzem `// OPTYMALIZACJA:`; opis: `docs/optymalizacja-sekwencyjna.md`.
Szachownica i jej walidacja statystyczna: `docs/openmp.md`; pasy MPI: `docs/mpi.md`.
