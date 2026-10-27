# Dokumentacja

Każdy dokument opisuje jeden obszar projektu: co doszło, jak to działa, wyniki pomiarów i znane ograniczenia. Opis
podaje stan z dnia, w którym powstał; późniejsze zmiany opisują kolejne dokumenty (kolejność w tabeli = kolejność prac).
Każdy dokument tematyczny i przewodnik ma też wersję PDF w [`pdf/`](pdf/) (tytuły i liczby stron:
[`pdf/index.json`](pdf/index.json); odświeżanie: `python tools/build_docs_pdf.py`).

## Dokumenty tematyczne

| Dokument | Zawartość |
|---|---|
| [Automat komórkowy: spływ lawy i rozrost ziaren](automat-komorkowy.md) | Silnik C++17 w wersji serwerowej, reguły spływu lawy, dwie reprezentacje siatki i benchmark ich zgodności. |
| [Monte Carlo: krystalizacja (model Pottsa)](monte-carlo.md) | Krystalizacja bazaltu modelem Pottsa z mobilnością ze stygnięcia, MC na wyniku CA z pliku, zgodność GCC i MSVC. |
| [Profil aplikacji](profilowanie.md) | Profil CPU (gprof, callgrind, Visual Studio), skalowanie czasu, model pamięci, wymagania sprzętowe, lista optymalizacji. |
| [Interfejs graficzny](interfejs-graficzny.md) | Aplikacja w przeglądarce: formularz z domyślnej konfiguracji silnika, zadania jako osobne procesy, podgląd 2D i 3D. |
| [Kolejka zadań, serie, dane wejściowe](kolejka-serie-dane.md) | Generator serii, kolejka zadań, `engine --batch`, mapy wysokości z pliku, eksport ZIP/VTK, porównanie czasów CA i MC. |
| [Prawdziwy teren i odtwarzanie erupcji](prawdziwe-wulkany.md) | Teren Etny i Wezuwiusza z AWS Terrain Tiles, kratery w zadanych miejscach, odtwarzanie erupcji krok po kroku. |
| [Wygląd interfejsu](wyglad-interfejsu.md) | Motyw „Bazalt i lawa” (ciemny i jasny), paleta danych sprawdzona pod kątem kontrastu i daltonizmu, płynność odtwarzania. |
| [Optymalizacja wersji sekwencyjnej](optymalizacja-sekwencyjna.md) | Automat frontalny, MC bez skoku warunkowego, ramka i przesunięcia liniowe, tańsze statystyki i zapis; testy A/B i bitowa zgodność każdego kroku; wnioski dla wersji OpenMP. |
| [Zrównoleglenie OpenMP](openmp.md) | Podział przestrzeni na warstwy między wątki, szachownica MC z walidacją statystyczną, przypinanie do rdzeni wydajnościowych (P); przyspieszenie, efektywność, prawo Amdahla, harmonogramy i nierównomierność obciążenia; narzut przy 1 wątku; wnioski dla MPI. |
| [Wersja rozproszona MPI](mpi.md) | Program `engine_mpi`: pasy warstw między procesy, warstwy brzegowe (dla lawy 17 pod pasem), zarodkowanie z indeksem globalnym, wynik bitowo ten sam przy każdej liczbie procesów (MS-MPI i OpenMPI); przypinanie procesów do rdzeni P; skalowanie 1–8 procesów, prawo Amdahla, MPI vs OpenMP, tryb hybrydowy, koszt komunikacji, nierównomierność pasów, wymiana co krok albo tylko zmienionych warstw; wnioski dla typów MPI i MPI-IO. |
| [Typy pochodne MPI i równoległy zapis](mpi-typy-i-zapis.md) | Opcje `engine_mpi`: wymiana warstw typami pochodnymi (`MPI_Type_create_struct` z pól SoA, bez pakowania), parametry i kratery jako struktury, równoległy zapis i odczyt MPI-IO (widok `MPI_Type_create_subarray`, tekst przez `MPI_Exscan`); pliki bajtowo te same co w wersji MPI we wszystkich kombinacjach. Pomiar: wymiana typami krótsza o 25–50% (cała faza o 0–9%); MPI-IO: zapis dużych wyników 1,25–2,5× szybszy (tekst dzięki równoległemu formatowaniu), pamięć procesu 0 czterokrotnie mniejsza, odczyt `--mc-from` 12–27× szybszy, małe pliki bez zysku; OMPIO vs ROMIO; przewidywania dla klastra. |
| [Testy wydajności](testy-wydajnosci.md) | Zestawienie przyspieszenia i efektywności wszystkich wersji (OpenMP, MPI, tryb hybrydowy, typy pochodne) i łączne przyspieszenie od programu sprzed optymalizacji (Etna ×1 871); pamięć główna wątków i procesów (warstwy brzegowe, zebranie wyniku vs MPI-IO, model vs pomiar, kiedy MPI mieści większą siatkę); pamięć podręczna z symulacji cachegrind (automat frontalny vs pełny przebieg, szachownica vs losowa kolejność MC, progi L2 / L3 / RAM, fałszywe współdzielenie, brak przyspieszenia ponadliniowego); skalowanie słabe (efektywność przy 8 rdzeniach: MC i lawa 0,87–1,00, rozrost ziaren 0,49, ograniczenie przepustowością pamięci), czas na komórkę vs rozmiar siatki (MC w losowej kolejności 4,6× wolniejsze po wyjściu z L2 do RAM; rozrost ziaren i szachownica bez progu), przepustowość RAM (nasycenie przy 6 wątkach, ~48 GB/s); podsumowanie wersji równoległych i co dałby klaster. |
| [Zakładka „Wydajność” w interfejsie](zakladka-wydajnosc.md) | Wyniki optymalizacji i zrównoleglenia w GUI: zasada zgodności bitowej (15/15 konfiguracji, 1–8 wątków i procesów, MSVC i GCC), panel „Pojęcia”, podsumowanie (łączne przyspieszenie, najlepszy wariant każdego przypadku) i pięć sekcji z 25 interaktywnymi wykresami; przy każdym wykresie wniosek, „Jak czytać”, warunki pomiaru słownie, pochodzenie danych, tabela, eksport PNG i PDF dokumentu; dane z istniejących plików `bench/results/` przez `tools/wydajnosc_gui.py` (bez nowych pomiarów). |

## Przewodniki i wyniki

| Dokument | Zawartość |
|---|---|
| [Architektura](architektura.md) | Droga jednej symulacji od configu do pliku wynikowego, kluczowe miejsca w kodzie, słowniczek, najczęstsze pytania. |
| [Uruchamianie](uruchamianie.md) | Instalacja, budowanie (MSVC, GCC), testy, silnik, GUI, serie, pomiary oraz pełny opis opcji, configu i plików wynikowych. |
| [Wyniki](wyniki.md) | Zestawienie wyników przykładowych przypadków (czasy, statystyki CA i MC, pamięć); generuje je `tools/zestaw_wynikow.py`. |
| [Raport (PDF)](raport.pdf) | Raport techniczny (10 stron): architektura, modele CA i MC, interfejs, wyniki i profil wydajności; źródło [`raport.md`](raport.md), budowanie `python tools/build_report.py`. |

Dane do wykresów: [`data/`](data/) (seria CA vs MC), [`../bench/results/`](../bench/results/) (profil),
[`../bench/results/ab/`](../bench/results/ab/) (testy A/B i zgodność optymalizacji sekwencyjnej, dziennik `POSTEP.md`),
[`../bench/results/omp/`](../bench/results/omp/) (skalowanie, harmonogramy, narzut i zgodność wersji OpenMP, dziennik `POSTEP.md`),
[`../bench/results/mpi/`](../bench/results/mpi/) (skalowanie, zgodność, narzut, dobór przypadków i plan pomiaru wersji MPI, dziennik `POSTEP.md`),
[`../bench/results/mpi_io/`](../bench/results/mpi_io/) (zgodność, narzut, dobór przypadków i plan pomiaru typów MPI i MPI-IO, dziennik `POSTEP.md`),
[`../bench/results/testy/`](../bench/results/testy/) (zestawienie S / E, pamięć, cachegrind, procesor i plan pomiaru testów wydajności, dziennik `POSTEP.md`);
obrazy: [`img/`](img/) (zrzuty GUI i wykresy), [`img/raport/`](img/raport/) (rysunki raportu: `python gui/tests/raport_shots.py`,
`python tools/raport_wykresy.py`), [`img/readme/`](img/readme/) (zrzuty do README:
`python gui/tests/raport_shots.py --shots 3,4 --etna etna_real --theme dark --out docs/img/readme`).
