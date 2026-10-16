# src/parallel — wersje równoległe (planowane: OpenMP, MPI)

Miejsce na planowane wersje równoległe:

- OpenMP — podział pętli kroku CA na pasy; wynik identyczny dla każdej liczby wątków,
  bo losowość pochodzi z `hashRand(seed, krok, globalIndex, sól)`;
- MPI — podział na pasy wzdłuż `x`, ramka 1 komórki = komórki nadmiarowe (ghost cells),
  `MPI_Bcast` parametrów, typy pochodne, równoległy zapis `ca_result.bin`.

Kod sekwencyjny jest do tego przygotowany: płaskie tablice SoA, synchroniczny CA z podwójnym
buforem, osobny przebieg `computeDescent()` czytający tylko bufor `cur`.
