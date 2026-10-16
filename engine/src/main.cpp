// Punkt wejścia programu engine — wersja serwerowa symulacji (bez interfejsu użytkownika).
// Symulacja przebiega bez ingerencji użytkownika: dane z pliku JSON i argumentów main,
// wyniki i czasy zapisywane do plików. Cała logika jest w bibliotece volcano_engine;
// tu tylko wybór trybu i zamiana wyjątków na kody wyjścia.
//
// Kody wyjścia: 0 — OK, 1 — błąd konfiguracji, 2 — błąd argumentów,
//               3 — inny błąd (np. zapis pliku), 4 — benchmark: niezgodne wyniki,
//               5 — seria (--batch): co najmniej jeden przebieg zakończony błędem.

#include <iostream>

#include "app/Batch.hpp"
#include "app/Benchmark.hpp"
#include "app/Cli.hpp"
#include "app/ConfigCheck.hpp"
#include "app/Simulation.hpp"
#include "core/Timer.hpp"
#include "io/Config.hpp"

int main(int argc, char** argv) {
    using namespace volcano;
    const Timer sinceStart;  // sekcja "total" w times.json
    Cli::prepareConsole();
    try {
        const CliOptions opt = Cli::parse(argc, argv);
        if (opt.help) {
            std::cout << Cli::usage();
            return 0;
        }
        // Opcje dla GUI (etap 4): domyślny config i sama walidacja — bez symulacji.
        if (opt.printDefaults) {
            std::cout << ConfigCheck::defaultsText();
            return 0;
        }
        if (opt.validate) {
            return ConfigCheck::runFromCli(opt, std::cout);
        }
        if (opt.benchmark) {
            return Benchmark::runFromCli(opt);
        }
        // Etap 5: seria configów z folderu, każdy w osobnym procesie silnika.
        if (!opt.batchDir.empty()) {
            return BatchRunner::runFromCli(opt);
        }
        return Simulation::runFromCli(opt, sinceStart);
    } catch (const CliError& e) {
        std::cerr << "Błąd argumentów: " << e.what() << "\n\n" << Cli::usage();
        return 2;
    } catch (const ConfigError& e) {
        std::cerr << "Błąd konfiguracji: " << e.what() << '\n';
        return 1;
    } catch (const std::exception& e) {
        std::cerr << "Błąd: " << e.what() << '\n';
        return 3;
    }
}
