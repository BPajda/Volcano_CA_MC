# Typy MPI i MPI-IO `pomiar_msvc_cz3`

- Program: `engine_mpi_e11_msvc.exe` (MS-MPI `mpiexec -n p`); `--high-priority`, `parallel.affinity = pcores`; warianty naprzemiennie (kolejność odwracana co powtórzenie); mediana [min–max]
- Czas pomiaru: 5.5 min, 2026-10-21T10:20
- Tło: start 12% CPU (WmiPrvSE.exe 211%, python.exe 39%, svchost.exe 39%), koniec 12%
- Zgodność wyników w przypadku: wszystkie przebiegi bitowo zgodne

### `io_bin_classic_300` — zapis: zebranie na proces 0 (m) vs MPI-IO (i)

| p | save m [ms] | save i [ms] | i/m | plik m [ms] | plik i [ms] | MB/s m / i | udział w total m / i | zebranie m (maks.) [ms] | formatowanie i (maks.) [ms] | MPI-IO i (maks.) [ms] | pamięć procesu 0 m / i [MB] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 704 [691–792] | 436 [434–437] | ×0.620 | 288 [277–375] | 173 [170–174] | 1219 / 2026 | 15.5% / 10.3% | 43.6 | 0.0 | 173.2 | 1145 / 794 | tak |
| 2 | 575 [566–581] | 463 [455–467] | ×0.804 | 278 [270–279] | 328 [321–334] | 1261 / 1071 | 20.2% / 17.7% | 163.7 | 0.0 | 328.6 | 760 / 410 | tak |
| 4 | 519 [507–556] | 379 [374–386] | ×0.730 | 280 [267–318] | 309 [305–311] | 1252 / 1135 | 25.9% / 22.9% | 169.1 | 0.0 | 309.6 | 566 / 215 | tak |
| 8 | 489 [484–501] | 325 [323–331] | ×0.664 | 279 [272–282] | 286 [282–289] | 1256 / 1227 | 29.1% / 25.2% | 174.8 | 0.0 | 287.2 | 469 / 118 | tak |
Plik: 351.00 MB. save — od końca fazy CA: pas bez ramki, (m) zebranie na proces 0, zapis pliku.

### `io_txt_classic_300` — zapis: zebranie na proces 0 (m) vs MPI-IO (i)

| p | save m [ms] | save i [ms] | i/m | plik m [ms] | plik i [ms] | MB/s m / i | udział w total m / i | zebranie m (maks.) [ms] | formatowanie i (maks.) [ms] | MPI-IO i (maks.) [ms] | pamięć procesu 0 m / i [MB] | zgodne |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2 045 [2 043–2 055] | 2 409 [2 397–2 417] | ×1.178 | 1 629 [1 628–1 639] | 2 145 [2 135–2 155] | 345 / 262 | 35.0% / 39.0% | 43.4 | 1613.9 | 499.0 | 1145 / 925 | tak |
| 2 | 1 931 [1 925–1 935] | 1 478 [1 465–1 491] | ×0.765 | 1 633 [1 628–1 636] | 1 344 [1 331–1 359] | 344 / 418 | 45.7% / 40.7% | 162.4 | 817.7 | 521.2 | 760 / 464 | tak |
| 4 | 1 869 [1 864–1 873] | 983 [976–1 002] | ×0.526 | 1 629 [1 626–1 633] | 913 [908–933] | 345 / 616 | 55.5% / 43.4% | 168.8 | 405.0 | 500.4 | 566 / 236 | tak |
| 8 | 1 843 [1 840–1 850] | 728 [718–752] | ×0.395 | 1 631 [1 630–1 635] | 691 [677–715] | 345 / 814 | 61.0% / 42.7% | 174.8 | 207.6 | 489.6 | 469 / 125 | tak |
Plik: 562.29 MB. save — od końca fazy CA: pas bez ramki, (m) zebranie na proces 0, zapis pliku.

