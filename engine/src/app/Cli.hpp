#pragma once
// Obsługa linii poleceń programu engine (wersja serwerowa, bez GUI).
// Dane wejściowe symulacji pochodzą z pliku JSON i/lub z argumentów funkcji main
// (--set klucz=wartość) — bez edycji pliku konfiguracyjnego — a dla MC także
// z pliku wyniku CA (--mc-from). Etap 5: --batch
// uruchamia po kolei wszystkie configi z folderu (automatyzacja wersji serwerowej).

#include <stdexcept>
#include <string>
#include <vector>

namespace volcano {

// Błąd w argumentach wywołania (nieznana opcja, brak wartości itp.).
class CliError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

// Wynik analizy argumentów: co uruchomić i z jakimi ustawieniami.
struct CliOptions {
    bool help = false;                   // --help: wypisz pomoc i zakończ
    bool benchmark = false;              // --benchmark: porównanie vector vs macierz
    bool quick = false;                  // --quick: benchmark bez przypadków >= 1 mln komórek
    int repeats = 3;                     // --repeats N: liczba powtórzeń w benchmarku
    bool timingDetail = false;           // --timing-detail: czasy faz wewnątrz CA i MC (profil, etap 3)
    bool printDefaults = false;          // --print-defaults: wypisz domyślny config JSON (GUI buduje z niego formularz)
    bool validate = false;               // --validate: tylko walidacja configu, wynik jako JSON na stdout
    bool progress = false;               // --progress: linie „PROGRESS etap i/n” na stdout (postęp w GUI)
    std::string configPath;             // --config: plik JSON (pusty = same wartości domyślne)
    std::string outDir;                  // --out: folder wyników (pusty = domyślny)
    std::string mcFrom;                  // --mc-from: folder z wynikiem CA — samo MC na tym wyniku
    std::string batchDir;                // --batch: folder z configami *.json — seria przebiegów (etap 5)
    std::vector<std::string> overrides;  // --set a.b=v oraz --grid (jako "grid=...")
};

// Parser argumentów. Klasa statyczna — nie przechowuje stanu.
class Cli {
public:
    // Analizuje argv; rzuca CliError z opisem po polsku przy błędnym wywołaniu.
    static CliOptions parse(int argc, const char* const* argv);

    // Tekst pomocy (--help).
    static std::string usage();

    // Ustawia konsolę Windows na UTF-8, żeby polskie komunikaty były czytelne.
    // Na innych systemach nic nie robi.
    static void prepareConsole();
};

}  // namespace volcano
