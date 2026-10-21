# Skalowanie MPI `slabe_mpi_gcc`

- Programy: `engine_mpi` (OpenMPI `mpiexec --allow-run-as-root --use-hwthread-cpus --bind-to none -n p` (WSL, procesory wirtualne)), `engine` (warianty o<t>); `--high-priority`, przypięcie `parallel.affinity = pcores` (proces r z t wątkami na rdzeniach r·t … r·t + t − 1); warianty naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max] z n powtórzeń
- Czas pomiaru: 1.4 min, 2026-10-21T18:43
- Skalowanie słabe: przestrzeń razy liczba rdzeni wariantu, `output.format = none`; wyników różnych rozmiarów nie porównuje się bitowo (zgodność procesów — etapy 10–11)

| Przypadek | wariant | p | komórki | kroki / MCS | faza [ms] | E_w fazy | total [ms] | E_w total | ns rdzenia / (komórka × krok) albo / próbę | E_w znormalizowana |
|---|---|---|---|---|---|---|---|---|---|---|
| weak_classic_2d | m1d | 1 | 4 000 000 | 199 | 509 [505–547] | 1.00 | 904 | 1.00 | 0.64 | 1.00 |
| weak_classic_2d | m4d | 4 | 16 000 000 | 228 | 698 [665–744] | 0.73 | 1 391 | 0.65 | 0.76 | 0.84 |
| weak_classic_2d | m8d | 8 | 32 000 000 | 247 | 1 258 [1 088–1 404] | 0.40 | 2 387 | 0.38 | 1.27 | 0.50 |
| weak_mc_cb_2d | m1d | 1 | 1 000 000 | 30 | 708 [698–782] | 1.00 | 1 063 | 1.00 | 23.61 | 1.00 |
| weak_mc_cb_2d | m4d | 4 | 4 000 000 | 30 | 765 [761–834] | 0.93 | 1 441 | 0.74 | 25.50 | 0.93 |
| weak_mc_cb_2d | m8d | 8 | 8 000 000 | 30 | 1 088 [904–1 109] | 0.65 | 2 003 | 0.53 | 36.28 | 0.65 |
| weak_lava_front | m1d | 1 | 1 048 576 | 260 | 487 [481–530] | 1.00 | 779 | 1.00 | 1.79 | 1.00 |
| weak_lava_front | m4d | 4 | 4 194 304 | 260 | 1 431 [1 411–1 605] | 0.34 | 1 843 | 0.42 | 5.25 | 0.34 |
| weak_lava_front | m8d | 8 | 8 388 608 | 260 | 2 187 [2 110–2 432] | 0.22 | 2 741 | 0.28 | 8.02 | 0.22 |

E_w = T(1) / T(p) przy przestrzeni p razy większej (ideał 1); znormalizowana — z czasu na (komórkę × krok / p), gdy liczba kroków albo MCS zmienia się z p (classic: największa luka między zarodkami).

Tło (Windows, poza WSL): start 14% (WmiPrvSE.exe 189%, python.exe 41%, System 41%), koniec 13%.
