// Punkt wejścia programu engine_mpi — wersja rozproszona symulacji (etap 10, MPI):
//     mpiexec -n 4 engine_mpi --config configs\test_3d.json --out results\test_3d_mpi4 [--high-priority]
// Te same opcje przebiegu co engine (--config, --set, --out, --mc-from, --threads, --timing-detail, --thread-stats,
// --progress) i te same pliki wyników; przebieg opisuje engine/src/mpi/MpiSimulation.hpp.
//
// Błędy: proces 0 wypisuje komunikat (błąd configu wykrywa tylko on — pozostałe procesy czekają na rozesłanie configu),
// a program kończy wszystkie procesy przez MPI_Abort z kodem jak w engine: 1 — błąd configu, 2 — błąd argumentów,
// 3 — inny błąd (komunikat z numerem procesu).

#include <mpi.h>

#include <iostream>
#include <string>

#include "app/Cli.hpp"
#include "core/Timer.hpp"
#include "io/Config.hpp"
#include "mpi/MpiSimulation.hpp"

int main(int argc, char** argv) {
    using namespace volcano;
    const Timer sinceStart;  // sekcja "total" w times.json (procesu 0)
    int provided = 0;
    // Tryb hybrydowy: MPI woła tylko wątek główny (poza regionami OpenMP albo w regionie przez wątek 0).
    MPI_Init_thread(&argc, &argv, MPI_THREAD_FUNNELED, &provided);
    const double initMs = sinceStart.elapsedMs();  // start środowiska MPI — times.json: mpi.initMs
    Cli::prepareConsole();
    int rank = 0;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    int code = 0;
    std::string message;
    try {
        const CliOptions opt = Cli::parse(argc, argv);
        if (opt.help) {
            if (rank == 0) {
                std::cout << "engine_mpi — wersja rozproszona (MPI) programu engine: przestrzeń podzielona na pasy\n"
                             "warstw (oś z, w płaszczyźnie x–y — y) między procesy, wynik bitowo taki sam.\n"
                             "  mpiexec -n <procesy> engine_mpi --config <plik.json> --out <folder> [opcje engine]\n"
                             "  mpi.exchange = always | changed — wymiana warstw brzegowych co krok albo tylko "
                             "zmienionych\n"
                             "  --high-priority — wysoki priorytet procesów (mpiexec uruchamia je z normalnym)\n"
                             "  parallel.affinity = pcores — proces r z T wątkami na rdzeniach P nr r·T … r·T + T − 1\n"
                             "Bez --batch, --benchmark, --validate i --print-defaults (to robi program engine).\n\n"
                          << Cli::usage();
            }
        } else if (opt.printDefaults || opt.validate || opt.benchmark || !opt.batchDir.empty()) {
            throw CliError("engine_mpi liczy jedną symulację w wielu procesach — --print-defaults, --validate, "
                           "--benchmark i --batch obsługuje program engine");
        } else {
            if (provided < MPI_THREAD_FUNNELED && rank == 0) {
                std::cerr << "Ostrzeżenie: biblioteka MPI nie zapewnia MPI_THREAD_FUNNELED — tryb hybrydowy "
                             "(parallel.threads > 1) może być niepoprawny\n";
            }
            code = MpiSimulation::runFromCli(opt, sinceStart, initMs);
        }
    } catch (const CliError& e) {
        code = 2;
        message = std::string("Błąd argumentów: ") + e.what() + "\n\n" + Cli::usage();
    } catch (const ConfigError& e) {
        code = 1;
        message = std::string("Błąd konfiguracji: ") + e.what();
    } catch (const std::exception& e) {
        code = 3;
        message = "Błąd (proces " + std::to_string(rank) + "): " + e.what();
    }
    if (code != 0) {
        // Błędy argumentów są takie same na każdym procesie — wypisuje je tylko proces 0.
        if (rank == 0 || code == 3) {
            std::cerr << message << std::endl;
        }
        MPI_Abort(MPI_COMM_WORLD, code);
    }
    MPI_Finalize();
    return code;
}
