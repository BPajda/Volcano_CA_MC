# Pamięć główna `pamiec_gcc`

- Szczyt pamięci procesu: Windows `PeakWorkingSetSize`, Linux `ru_maxrss` (proces 0 — `memory.peakRssBytes`; MPI: `mpi.peakRssBytes` min / średnia / maks po procesach, suma = średnia × p). Model: `MemoryModel` (duże tablice × `sizeof`; proces 0 — z silnika, pozostałe procesy — rozszerzenie w skrypcie). MB = 2²⁰ B.
- Tabela z `pamiec_gcc_raw.csv`
- Czas pomiaru: 0.7 min, 2026-10-21T14:33

## Narzut stały procesu (classic 16³ — dane < 0,1 MB)

| Wariant | szczyt procesu 0 [MB] | na starcie (proces 0) [MB] | na końcu (proces 0) [MB] | średnio na proces [MB] | maks [MB] |
|---|---|---|---|---|---|
| o1 | 14,7 | 2,1 | 4,8 | 14,7 | 14,7 |
| o8 | 14,7 | 2,1 | 4,9 | 14,7 | 14,7 |
| m1d | 20,9 | 19,5 | 20,9 | 20,9 | 20,9 |
| m2d | 23,0 | 21,7 | 23,0 | 21,8 | 23,0 |
| m3d | 20,9 | 19,4 | 20,9 | 20,2 | 20,9 |
| m4d | 20,9 | 19,5 | 20,9 | 21,0 | 22,7 |
| m5d | 21,0 | 19,6 | 21,0 | 20,7 | 21,0 |
| m6d | 23,0 | 21,9 | 23,0 | 20,8 | 23,0 |
| m7d | 21,1 | 19,9 | 21,1 | 20,8 | 22,7 |
| m8d | 20,9 | 19,6 | 20,9 | 20,2 | 20,9 |

## OpenMP — szczyt pamięci w funkcji liczby wątków

| Przypadek | komórki | 1 wątek [MB] | 2 | 4 | 8 | 8 / 1 | model [MB] | (szczyt − narzut) / model | B / komórkę: pomiar / model |
|---|---|---|---|---|---|---|---|---|---|
| classic 2000², VN | 4 000 000 | 113 | 113 | 113 | 113 | 0,997 | 108 | 1,006 | 28,4 / 28,2 |
| lawa 128² × 64, front | 1 048 576 | 35,5 | 35,1 | 35,5 | 35,2 | 0,989 | 30,4 | 1,014 | 30,8 / 30,4 |
| MC 100³, Moore, szachownica | 1 000 000 | 48,1 | 48,1 | 48,1 | 53,0 | 1,101 | 40,1 | 1,080 | 45,5 / 42,1 |

Narzut stały = szczyt classic 16³ przy 1 wątku (4,8 MB; w Linuksie RSS na końcu przebiegu — `ru_maxrss` bardzo małego procesu pokazuje szczyt procesu, który go uruchomił).

## MPI — pamięć wszystkich procesów i procesu 0

Suma = średnia × p; „dane” = pomiar − p × narzut stały procesu MPI (grupa base, ta sama liczba procesów). Model: suma / maksimum po procesach (rozszerzenie modelu procesu 0; MPI-IO przy p > 1 — proces 0 z buforem agregatora zapisu zbiorowego ≤ 16 MB); warstwy brzegowe = siatka okien poza pasami własnymi (udział w siatce wszystkich okien).

| Przypadek | p | zapis | suma [MB] | dane: suma [MB] | model: suma [MB] | dane / model | maks [MB] | proces 0 [MB] | model: maks [MB] | min [MB] | warstwy brzegowe [MB] (udział) | suma / 1 proces |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| classic 2000², VN | 1 | gather | 180 | 159 | 157 | 1,013 | 180 | 180 | 157 | 180 | 0,0 (0%) | 1,00 |
| classic 2000², VN | 2 | gather | 199 | 156 | 157 | 0,990 | 124 | 124 | 103 | 74,8 | 0,1 (0%) | 0,98 |
| classic 2000², VN | 3 | gather | 224 | 163 | 157 | 1,039 | 108 | 108 | 85,5 | 57,3 | 0,1 (0%) | 1,03 |
| classic 2000², VN | 4 | gather | 245 | 160 | 157 | 1,021 | 99,6 | 99,6 | 76,5 | 47,5 | 0,2 (0%) | 1,01 |
| classic 2000², VN | 8 | gather | 329 | 167 | 158 | 1,058 | 84,1 | 84,1 | 63,1 | 34,1 | 0,4 (1%) | 1,05 |
| classic 2000², VN | 1 | MPI-IO | 128 | 107 | 108 | 0,997 | 128 | 128 | 108 | 128 | 0,0 (0%) | 0,67 |
| classic 2000², VN | 2 | MPI-IO | 149 | 105 | 107 | 0,981 | 74,7 | 74,5 | 53,7 | 74,5 | 0,1 (0%) | 0,66 |
| classic 2000², VN | 3 | MPI-IO | 175 | 114 | 108 | 1,063 | 61,8 | 61,8 | 35,9 | 56,2 | 0,1 (0%) | 0,72 |
| classic 2000², VN | 4 | MPI-IO | 199 | 115 | 109 | 1,052 | 55,9 | 55,9 | 28,4 | 47,5 | 0,2 (0%) | 0,72 |
| classic 2000², VN | 8 | MPI-IO | 289 | 127 | 117 | 1,085 | 47,7 | 47,7 | 22,2 | 34,2 | 0,4 (1%) | 0,80 |
| lawa 128² × 64, front | 1 | gather | 64,1 | 43,2 | 43,4 | 0,997 | 64,1 | 64,1 | 43,4 | 64,1 | 0,0 (0%) | 1,00 |
| lawa 128² × 64, front | 2 | gather | 90,4 | 46,7 | 49,5 | 0,945 | 50,5 | 50,5 | 29,3 | 39,9 | 3,8 (21%) | 1,08 |
| lawa 128² × 64, front | 3 | gather | 118 | 57,8 | 55,0 | 1,051 | 45,5 | 45,5 | 24,6 | 35,8 | 7,5 (34%) | 1,34 |
| lawa 128² × 64, front | 4 | gather | 147 | 62,7 | 60,1 | 1,044 | 45,3 | 45,3 | 21,7 | 32,7 | 11,1 (42%) | 1,45 |
| lawa 128² × 64, front | 8 | gather | 254 | 92,2 | 79,5 | 1,159 | 39,5 | 39,5 | 17,9 | 27,9 | 24,3 (59%) | 2,13 |
| lawa 128² × 64, front | 1 | MPI-IO | 51,0 | 30,1 | 30,4 | 0,992 | 51,0 | 51,0 | 30,4 | 51,0 | 0,0 (0%) | 0,70 |
| lawa 128² × 64, front | 2 | MPI-IO | 91,4 | 47,7 | 39,7 | 1,203 | 51,5 | 51,5 | 20,2 | 39,9 | 3,8 (21%) | 1,10 |
| lawa 128² × 64, front | 3 | MPI-IO | 117 | 56,5 | 47,8 | 1,181 | 44,6 | 44,6 | 17,5 | 35,8 | 7,5 (34%) | 1,31 |
| lawa 128² × 64, front | 4 | MPI-IO | 142 | 57,8 | 54,6 | 1,059 | 42,4 | 42,4 | 16,3 | 32,8 | 11,1 (42%) | 1,34 |
| lawa 128² × 64, front | 8 | MPI-IO | 250 | 88,5 | 76,3 | 1,160 | 40,1 | 40,1 | 14,6 | 28,3 | 24,3 (59%) | 2,05 |
| MC 100³, Moore, szachownica | 1 | gather | 63,3 | 42,4 | 40,1 | 1,055 | 63,3 | 63,3 | 40,1 | 63,3 | 0,0 (0%) | 1,00 |
| MC 100³, Moore, szachownica | 2 | gather | 86,7 | 43,0 | 40,4 | 1,064 | 52,0 | 52,0 | 29,8 | 34,7 | 0,8 (4%) | 1,02 |
| MC 100³, Moore, szachownica | 3 | gather | 116 | 55,9 | 48,2 | 1,160 | 55,0 | 55,0 | 29,0 | 30,0 | 1,6 (5%) | 1,32 |
| MC 100³, Moore, szachownica | 4 | gather | 134 | 50,2 | 40,8 | 1,230 | 50,9 | 50,9 | 24,5 | 27,6 | 1,5 (7%) | 1,19 |
| MC 100³, Moore, szachownica | 8 | gather | 215 | 52,8 | 41,2 | 1,283 | 44,2 | 44,2 | 21,9 | 24,3 | 2,7 (12%) | 1,25 |
| MC 100³, Moore, szachownica | 1 | MPI-IO | 63,7 | 42,8 | 40,1 | 1,067 | 63,7 | 63,7 | 40,1 | 63,7 | 0,0 (0%) | 1,01 |
| MC 100³, Moore, szachownica | 2 | MPI-IO | 86,9 | 43,2 | 40,4 | 1,068 | 52,2 | 52,2 | 29,8 | 34,7 | 0,8 (4%) | 1,02 |
| MC 100³, Moore, szachownica | 3 | MPI-IO | 111 | 50,9 | 48,2 | 1,055 | 50,3 | 50,3 | 29,0 | 30,0 | 1,6 (5%) | 1,20 |
| MC 100³, Moore, szachownica | 4 | MPI-IO | 131 | 46,5 | 40,8 | 1,139 | 47,2 | 47,2 | 24,5 | 27,7 | 1,5 (7%) | 1,10 |
| MC 100³, Moore, szachownica | 8 | MPI-IO | 215 | 52,8 | 41,2 | 1,283 | 44,3 | 44,3 | 21,9 | 24,2 | 2,7 (12%) | 1,25 |

