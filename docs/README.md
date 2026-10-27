# Dokumentacja

Każdy dokument opisuje jeden obszar projektu: co doszło, jak to działa, wyniki pomiarów i znane ograniczenia. Opis
podaje stan z dnia, w którym powstał; późniejsze zmiany opisują kolejne dokumenty (kolejność w tabeli = kolejność prac).
Każdy dokument tematyczny i przewodnik ma też wersję PDF w [`pdf/`](pdf/) (tytuły i liczby stron:
[`pdf/index.json`](pdf/index.json); odświeżanie: `python tools/build_docs_pdf.py`).

## Dokumenty tematyczne

| Dokument | Zawartość |
|---|---|
| [Automat komórkowy: spływ lawy i rozrost ziaren](automat-komorkowy.md) | Silnik C++17 w wersji serwerowej, reguły spływu lawy i dwie reprezentacje siatki z benchmarkiem ich zgodności. |
| [Monte Carlo: krystalizacja (model Pottsa)](monte-carlo.md) | Krystalizacja bazaltu modelem Pottsa z mobilnością zależną od stygnięcia, także na wyniku automatu z pliku. |
| [Profil aplikacji](profilowanie.md) | Profil CPU (gprof, callgrind, Visual Studio), skalowanie czasu, model pamięci, wymagania sprzętowe i lista optymalizacji. |
| [Interfejs graficzny](interfejs-graficzny.md) | Aplikacja w przeglądarce z formularzem budowanym z konfiguracji silnika, zadaniami jako osobnymi procesami i podglądem 2D i 3D. |
| [Kolejka zadań, serie, dane wejściowe](kolejka-serie-dane.md) | Generator serii, kolejka zadań, `engine --batch`, mapy wysokości z pliku, eksport ZIP i VTK oraz porównanie czasów CA i MC. |
| [Prawdziwy teren i odtwarzanie erupcji](prawdziwe-wulkany.md) | Teren Etny i Wezuwiusza z AWS Terrain Tiles, kratery w zadanych miejscach i odtwarzanie erupcji krok po kroku. |
| [Wygląd interfejsu](wyglad-interfejsu.md) | Motyw „Bazalt i lawa” (ciemny i jasny) z paletą sprawdzoną pod kątem kontrastu i daltonizmu oraz płynnością odtwarzania. |
| [Optymalizacja wersji sekwencyjnej](optymalizacja-sekwencyjna.md) | Automat frontalny, MC bez skoku warunkowego, tańsze statystyki i zapis, każdy krok sprawdzony testem A/B i zgodnością bitową. |
| [Zrównoleglenie OpenMP](openmp.md) | Podział przestrzeni na warstwy między wątki i szachownica MC z walidacją statystyczną, z pomiarem przyspieszenia, harmonogramów i narzutu. |
| [Wersja rozproszona MPI](mpi.md) | Program `engine_mpi` z pasami warstw i warstwami brzegowymi, bitowo zgodny z `engine`, ze skalowaniem do 8 procesów, trybem hybrydowym i kosztem komunikacji. |
| [Typy pochodne MPI i równoległy zapis](mpi-typy-i-zapis.md) | Wymiana warstw typami pochodnymi, parametry jako struktury i równoległy zapis oraz odczyt MPI-IO, z pomiarem zysku względem wersji MPI. |
| [Testy wydajności](testy-wydajnosci.md) | Zestawienie przyspieszenia i efektywności wszystkich wersji, pamięć główna i podręczna, skalowanie słabe i przepustowość pamięci. |
| [Zakładka „Wydajność” w interfejsie](zakladka-wydajnosc.md) | Wyniki optymalizacji i zrównoleglenia na 25 interaktywnych wykresach w GUI, z wnioskiem, opisem „Jak czytać” i źródłem danych przy każdym. |

## Przewodniki i wyniki

| Dokument | Zawartość |
|---|---|
| [Architektura](architektura.md) | Droga jednej symulacji od configu do pliku wynikowego, kluczowe miejsca w kodzie, słowniczek i najczęstsze pytania. |
| [Uruchamianie](uruchamianie.md) | Instalacja, budowanie (MSVC, GCC), testy, silnik, GUI, serie i pomiary oraz pełny opis opcji, configu i plików wynikowych. |
| [Wyniki](wyniki.md) | Zestawienie wyników przykładowych przypadków (czasy, statystyki CA i MC, pamięć) generowane przez `tools/zestaw_wynikow.py`. |
| [Raport, część 1 (PDF)](raport-1.pdf) | Raport techniczny (10 stron) o architekturze, modelach CA i MC, interfejsie, wynikach i profilu wydajności; źródło [`raport-1.md`](raport-1.md), budowanie `python tools/build_report.py 1`. |
| [Raport, część 2 (PDF)](raport-2.pdf) | Raport techniczny (10 stron) o optymalizacji sekwencyjnej, OpenMP, MPI, typach pochodnych MPI i MPI-IO oraz testach wydajności; źródło [`raport-2.md`](raport-2.md), budowanie `python tools/build_report.py 2`. |

## Opisy katalogów

Krótkie opisy plików w katalogach kodu: [`../gui/README.md`](../gui/README.md) (interfejs),
[`../bench/README.md`](../bench/README.md) (skrypty pomiarów), [`../engine/src/mc/README.md`](../engine/src/mc/README.md)
(Monte Carlo), [`../engine/src/parallel/README.md`](../engine/src/parallel/README.md) (wątki OpenMP i pasy),
[`../engine/src/mpi/README.md`](../engine/src/mpi/README.md) (program `engine_mpi`),
[`../configs/heightmaps/README.md`](../configs/heightmaps/README.md) (mapy wysokości i przypisanie danych terenu).

Dane do wykresów: [`data/`](data/) (seria CA vs MC), [`../bench/results/`](../bench/results/) (profil),
[`../bench/results/ab/`](../bench/results/ab/) (testy A/B i zgodność optymalizacji sekwencyjnej, dziennik `POSTEP.md`),
[`../bench/results/omp/`](../bench/results/omp/) (skalowanie, harmonogramy, narzut i zgodność wersji OpenMP, dziennik `POSTEP.md`),
[`../bench/results/mpi/`](../bench/results/mpi/) (skalowanie, zgodność, narzut, dobór przypadków i plan pomiaru wersji MPI, dziennik `POSTEP.md`),
[`../bench/results/mpi_io/`](../bench/results/mpi_io/) (zgodność, narzut, dobór przypadków i plan pomiaru typów MPI i MPI-IO, dziennik `POSTEP.md`),
[`../bench/results/testy/`](../bench/results/testy/) (zestawienie S / E, pamięć, cachegrind, procesor i plan pomiaru testów wydajności, dziennik `POSTEP.md`);
obrazy: [`img/`](img/) (zrzuty GUI i wykresy), [`img/raport/`](img/raport/) (rysunki raportu 1: `python gui/tests/raport_shots.py`,
`python tools/raport_wykresy.py 1`), [`img/raport-2/`](img/raport-2/) (rysunki raportu 2: `python tools/raport_wykresy.py 2`,
`python gui/tests/raport2_shots.py`), [`img/readme/`](img/readme/) (zrzuty do README:
`python gui/tests/raport_shots.py --shots 3,4 --etna etna_real --theme dark --out docs/img/readme`).
