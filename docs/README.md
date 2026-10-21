# Dokumentacja

Projekt powstawał etapami; każdy opis etapu podsumowuje, co doszło, jak to działa, wyniki pomiarów i znane
ograniczenia (stan z dnia etapu — późniejsze zmiany opisują kolejne etapy).

## Etapy

| Dokument | Zawartość |
|---|---|
| [Etap 1 — automat komórkowy](etap-1-automat-komorkowy.md) | Silnik C++17 w wersji serwerowej, reguły spływu lawy, dwie reprezentacje siatki i benchmark ich zgodności. |
| [Etap 2 — Monte Carlo](etap-2-monte-carlo.md) | Krystalizacja bazaltu modelem Pottsa z mobilnością ze stygnięcia, MC na wyniku CA z pliku, zgodność GCC i MSVC. |
| [Etap 3 — profilowanie i wydajność](etap-3-profilowanie.md) | Profil CPU (gprof, callgrind, Visual Studio), skalowanie czasu, model pamięci, wymagania sprzętowe, lista optymalizacji. |
| [Etap 4 — GUI](etap-4-gui.md) | Aplikacja w przeglądarce: formularz z domyślnej konfiguracji silnika, zadania jako osobne procesy, podgląd 2D i 3D. |
| [Etap 5 — kolejka, serie, dane we/wy](etap-5-kolejka-serie-dane.md) | Generator serii, kolejka zadań, `engine --batch`, mapy wysokości z pliku, eksport ZIP/VTK, porównanie czasów CA i MC. |
| [Etap 6 — prawdziwe wulkany](etap-6-prawdziwe-wulkany.md) | Teren Etny i Wezuwiusza z AWS Terrain Tiles, kratery w zadanych miejscach, odtwarzanie erupcji krok po kroku. |
| [Etap 7 — wygląd GUI](etap-7-wyglad-gui.md) | Motyw „Bazalt i lawa” (ciemny i jasny), paleta danych sprawdzona pod kątem kontrastu i daltonizmu, płynność odtwarzania. |
| [Etap 8 — optymalizacja sekwencyjna](etap-8-optymalizacja-sekwencyjna.md) | Automat frontalny, MC bez skoku warunkowego, ramka i przesunięcia liniowe, tańsze statystyki i zapis; testy A/B i bitowa zgodność każdego kroku; wnioski dla OpenMP. |
| [Etap 9 — OpenMP](etap-9-openmp.md) | Podział przestrzeni na warstwy między wątki, szachownica MC z walidacją statystyczną, przypinanie do rdzeni P; przyspieszenie, efektywność, prawo Amdahla, harmonogramy i nierównomierność obciążenia; narzut przy 1 wątku; wnioski dla MPI. |
| [Etap 10 — MPI](etap-10-mpi.md) | Wersja rozproszona `engine_mpi`: pasy warstw między procesy, warstwy brzegowe (dla lawy 17 pod pasem), zarodkowanie z indeksem globalnym, wynik bitowo ten sam przy każdej liczbie procesów (MS-MPI i OpenMPI); przypinanie procesów do rdzeni P; skalowanie 1–8 procesów, prawo Amdahla, MPI vs OpenMP, tryb hybrydowy, koszt komunikacji, nierównomierność pasów, wymiana `always` / `changed`; wnioski dla typów MPI i MPI-IO. |

## Przewodniki i wyniki

| Dokument | Zawartość |
|---|---|
| [Architektura](architektura.md) | Droga jednej symulacji od configu do pliku wynikowego, kluczowe miejsca w kodzie, słowniczek, najczęstsze pytania. |
| [Uruchamianie](uruchamianie.md) | Instalacja, budowanie (MSVC, GCC), testy, silnik, GUI, serie, pomiary oraz pełny opis opcji, configu i plików wynikowych. |
| [Wyniki](wyniki.md) | Zestawienie wyników przykładowych przypadków (czasy, statystyki CA i MC, pamięć) — generuje `tools/zestaw_wynikow.py`. |
| [Raport (PDF)](raport.pdf) | Raport techniczny (10 stron): architektura, modele CA i MC, interfejs, wyniki i profil wydajności; źródło [`raport.md`](raport.md), budowanie `python tools/build_report.py`. |

Dane do wykresów: [`data/`](data/) (seria CA vs MC), [`../bench/results/`](../bench/results/) (profil),
[`../bench/results/ab/`](../bench/results/ab/) (testy A/B i zgodność etapu 8, dziennik `POSTEP.md`),
[`../bench/results/omp/`](../bench/results/omp/) (skalowanie, harmonogramy, narzut i zgodność etapu 9, dziennik `POSTEP.md`),
[`../bench/results/mpi/`](../bench/results/mpi/) (skalowanie, zgodność, narzut, dobór przypadków i plan pomiaru etapu 10, dziennik `POSTEP.md`);
obrazy: [`img/`](img/) (zrzuty GUI i wykresy), [`img/raport/`](img/raport/) (rysunki raportu: `python gui/tests/raport_shots.py`,
`python tools/raport_wykresy.py`), [`img/readme/`](img/readme/) (zrzuty do README:
`python gui/tests/raport_shots.py --shots 3,4 --etna etna_real --theme dark --out docs/img/readme`).
