#pragma once
// engine --batch <folder> --out <folder> (etap 5): automatyzacja uruchamiania wersji serwerowej
// dla wielu zestawów danych — „po wygenerowaniu kilku plików zlecenie obliczeń”.
//
// Po kolei (w kolejności nazw) wszystkie configi *.json z folderu, każdy do własnego podfolderu
// <out>/<nazwa configu>/ (+ engine.log z wyjściem programu). Pomijane są series.json (opis serii
// zapisywany przez generator serii — gui/series.py, tools/make_series.py) i pliki _*.json.
// Błąd jednego configu nie przerywa serii — trafia do podsumowania. Po każdym przebiegu
// <out>/batch_summary.csv jest zapisywany od nowa (nazwa, status, kroki, czasy sekcji z times.json,
// pamięć, rozmiary plików), więc przerwana seria też zostawia podsumowanie; na końcu tabela w konsoli.
//
// Każdy config liczy OSOBNY PROCES silnika (ten sam program: engine --config <plik> --out <folder>):
//  - szczytowa pamięć procesu (PeakWorkingSetSize, ru_maxrss) rośnie monotonicznie — w jednym procesie
//    kolejny przebieg „widziałby” szczyt poprzednich, a times.json ma opisywać jeden przebieg (etap 3);
//  - awaria jednego przebiegu (brak pamięci, wyjątek systemu) nie kończy serii;
//  - wyniki i czasy są dokładnie takie, jak przy ręcznym uruchomieniu (tak samo liczy GUI).

#include <filesystem>
#include <functional>
#include <ostream>
#include <string>
#include <vector>

#include "app/Cli.hpp"
#include "app/Progress.hpp"
#include "core/ChildProcess.hpp"

namespace volcano {

// Jeden przebieg serii.
struct BatchItem {
    std::string name;              // nazwa configu bez .json = nazwa podfolderu wyników (UTF-8)
    std::filesystem::path config;  // plik konfiguracyjny
    std::filesystem::path outDir;  // <out>/<name>
};

// Wynik przebiegu.
struct BatchOutcome {
    BatchItem item;
    int exitCode = -1;
    double wallMs = 0.0;  // czas procesu potomnego mierzony przez --batch (start programu .. koniec zapisu)
    std::string error;    // ostatnia linia „Błąd…” z engine.log albo powód z ChildProcess; pusty = OK

    bool ok() const { return exitCode == 0 && error.empty(); }
};

class BatchRunner {
public:
    // Uruchamia jeden przebieg, wyjście programu dopisuje do log. Domyślnie — proces potomny
    // (processRunner); testy mogą podać własną funkcję.
    using Runner = std::function<ChildResult(const BatchItem& item, const std::filesystem::path& log)>;

    // Configi z folderu (bez series.json i _*.json), posortowane po nazwie; outDir = out/<nazwa>.
    static std::vector<BatchItem> collect(const std::filesystem::path& folder, const std::filesystem::path& out);

    // Przebieg w osobnym procesie: exe --config <config> --out <outDir> [extraArgs...].
    static Runner processRunner(const std::filesystem::path& exe, const std::vector<std::string>& extraArgs);

    // Wykonuje wszystkie przebiegi po kolei; po każdym zapisuje summaryCsv i linię stanu do out.
    // progress (może być nullptr) dostaje „PROGRESS batch i/N”.
    static std::vector<BatchOutcome> run(const std::vector<BatchItem>& items, const Runner& runner,
                                         const std::filesystem::path& summaryCsv, std::ostream& out,
                                         ProgressReporter* progress = nullptr);

    // Kolumny batch_summary.csv i wiersz dla przebiegu (dane z times.json i config_used.json
    // z folderu wyników; puste pola, gdy przebieg się nie udał albo sekcji nie ma).
    static std::vector<std::string> summaryColumns();
    static std::vector<std::string> summaryRow(const BatchOutcome& o);
    static void writeSummary(const std::filesystem::path& csv, const std::vector<BatchOutcome>& outcomes);

    // Tabela podsumowania do konsoli.
    static std::string describe(const std::vector<BatchOutcome>& outcomes);

    // engine --batch: kod 0 — wszystkie przebiegi OK, 5 — co najmniej jeden z błędem.
    static int runFromCli(const CliOptions& opt);
};

}  // namespace volcano
