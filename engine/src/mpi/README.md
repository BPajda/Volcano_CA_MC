# src/mpi: program engine_mpi (wersja rozproszona)

`engine_mpi` liczy tę samą symulację co `engine`, ale w pamięci rozproszonej: przestrzeń jest podzielona na pasy
warstw między procesy MPI (`parallel/Strip.*`), a każdy proces liczy swój pas tym samym kodem automatu i Monte Carlo
(`LavaCA`, `PottsMC` w oknie pasa). Wynik jest bitowo taki sam jak z `engine` przy każdej liczbie procesów (losowość
z indeksem globalnym komórki, kratery i zarodki z jednej globalnej listy). Cel CMake powstaje przy `VOLCANO_MPI=ON`
i znalezionym MPI (Windows: MS-MPI z SDK, Linux: OpenMPI); biblioteka silnika od MPI nie zależy.

| Plik | Co |
|---|---|
| `main_mpi.cpp` | punkt wejścia: `MPI_Init_thread`, te same opcje przebiegu co `engine` (`--config`, `--set`, `--out`, `--mc-from`, `--threads`, …), błędy przez `MPI_Abort` z kodami jak w `engine` |
| `MpiSimulation.*` | przebieg: rozesłanie configu i terenu z procesu 0, teren i kratery w oknie pasa, kroki CA z wymianą warstw brzegowych i sumą liczników (`MPI_Allreduce`), Monte Carlo szachownicą z wymianą po każdym kolorze, zebranie wyniku (`MPI_Gatherv`) albo zapis MPI-IO, sekcja `mpi` w `times.json` |
| `MpiHalo.*` | wymiana warstw brzegowych (implementacja `StripLink`): nieblokujące `MPI_Isend` / `MPI_Irecv` + `MPI_Waitall`; komunikat pakowany do bufora (`mpi.pack = manual`) albo opisany typem pochodnym z pól siatki (`datatype`); wymiana co krok albo tylko zmienionych warstw (`mpi.exchange`) |
| `MpiTypes.*` | typy pochodne danych wejściowych (`mpi.bcast = struct`): blok liczbowy configu (`ConfigBlock`, `MPI_Type_create_struct`) i lista kraterów / zarodków jako tablica struktur; `MpiType` zwalnia typ (RAII) |
| `MpiIo.*` | równoległy zapis i odczyt wyników (`mpi.io = mpiio`): pliki binarne przez widok `MPI_Type_create_subarray` i jeden zapis zbiorowy, pliki tekstowe z przesunięciami z `MPI_Exscan`, odczyt `--mc-from` pasami; pliki bajt w bajt jak z `engine` |

Warstwy brzegowe: lawa 17 pod pasem (głębokość spadku `dropDepth`) i 1 nad, rozrost ziaren i Monte Carlo po 1. Monte
Carlo przy więcej niż 1 procesie tylko w trybie szachownicy (`mc.update = checkerboard`). Opis: `docs/mpi.md`
(pasy, komunikacja, skalowanie) i `docs/mpi-typy-i-zapis.md` (typy pochodne, MPI-IO).
