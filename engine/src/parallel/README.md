# src/parallel: równoległość, wątki OpenMP i podział na pasy dla MPI

Kod sekwencyjny był do tego przygotowany: płaskie tablice SoA, synchroniczny CA (reguły czytają tylko stan z początku
kroku), ramka 1 komórki zamiast `if`-ów na brzegach i losowość z `hashRand(seed, krok, globalIndex, sól)` — wynik nie
zależy od kolejności komórek, liczby wątków ani liczby procesów.

| Plik | Co |
|---|---|
| `Omp.hpp` | zastępcze `omp_*` dla buildu bez OpenMP, `ParallelSettings`, `ompFor` (harmonogram z configu przez `switch` — OpenMP 2.0 w MSVC), `ompBarrier` |
| `Affinity.*` | rdzenie P (Windows: `GetLogicalProcessorInformationEx`, Linux: `/sys`), przypinanie wątków (`pinThreads`), przypinanie od pozycji planu dla procesu MPI (`pinThreadsFrom`), wysoki priorytet (`raisePriority`, `parallel.priority = high`, `--high-priority`) |
| `ThreadStats.*` | `--thread-stats`: czas pracy każdego wątku w fazach kroku, nierównomierność obciążenia |
| `Strip.*` | MPI: podział warstw na pasy (`splitLayers`), plan okna pasa i warstw brzegowych (`planStrip`), interfejs komunikacji `StripLink` (implementacja z MPI w `src/mpi/`) |

**OpenMP.** Jednostka pracy = warstwa (oś z, w płaszczyźnie x–y — y), liczona w fazie w całości przez jeden
wątek; fazy kroku rozdzielone barierami, liczniki przez `reduction`. Opis: `docs/openmp.md`.

**MPI.** Ta sama oś warstw dzielona na pasy między procesy: proces liczy swoje warstwy w oknie (pas +
warstwy brzegowe), `LavaCA::setStrip` / `PottsMC::setStrip` ograniczają reguły do warstw własnych, a `StripLink`
odświeża warstwy brzegowe (przed krokiem CA, po każdym kolorze szachownicy MC) i sumuje liczniki po procesach.
Grubość warstw brzegowych = zasięg reguł w osi warstw (`LavaCA::reachBelow/Above`): classic i MC — 1, lawa — 17 pod
pasem (głębokość spadku `dropDepth`) i 1 nad. Biblioteka silnika nie zależy od MPI; program `engine_mpi`
(`src/mpi/`) powstaje, gdy CMake znajdzie MPI. Opis: `docs/mpi.md`.
