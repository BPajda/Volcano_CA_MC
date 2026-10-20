#include "app/Cli.hpp"

#include <cstdlib>

#ifdef _WIN32
#  ifndef WIN32_LEAN_AND_MEAN
#    define WIN32_LEAN_AND_MEAN
#  endif
#  ifndef NOMINMAX
#    define NOMINMAX
#  endif
#  include <windows.h>
#endif

namespace volcano {

namespace {

// Pobiera wartość opcji (następny argument) albo zgłasza czytelny błąd.
std::string requireValue(int& i, int argc, const char* const* argv, const std::string& option) {
    if (i + 1 >= argc) {
        throw CliError("opcja " + option + " wymaga wartości");
    }
    ++i;
    return argv[i];
}

// Zamienia tekst na dodatnią liczbę całkowitą (dla --repeats).
int parsePositiveInt(const std::string& text, const std::string& option) {
    char* end = nullptr;
    const long value = std::strtol(text.c_str(), &end, 10);
    if (end == text.c_str() || *end != '\0' || value < 1 || value > 1000) {
        throw CliError("opcja " + option + " wymaga liczby całkowitej 1..1000, podano: " + text);
    }
    return static_cast<int>(value);
}

}  // namespace

CliOptions Cli::parse(int argc, const char* const* argv) {
    CliOptions opt;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--help" || arg == "-h") {
            opt.help = true;
        } else if (arg == "--config") {
            opt.configPath = requireValue(i, argc, argv, arg);
        } else if (arg == "--out") {
            opt.outDir = requireValue(i, argc, argv, arg);
        } else if (arg == "--mc-from") {
            opt.mcFrom = requireValue(i, argc, argv, arg);
        } else if (arg == "--batch") {
            opt.batchDir = requireValue(i, argc, argv, arg);
        } else if (arg == "--set") {
            const std::string kv = requireValue(i, argc, argv, arg);
            if (kv.find('=') == std::string::npos || kv.front() == '=') {
                throw CliError("--set wymaga postaci klucz=wartość (np. space.nx=100), podano: " + kv);
            }
            opt.overrides.push_back(kv);
        } else if (arg == "--grid") {
            // Skrót dla --set grid=...; poprawność nazwy sprawdza walidacja configu.
            opt.overrides.push_back("grid=" + requireValue(i, argc, argv, arg));
        } else if (arg == "--threads") {
            // Skrót dla --set parallel.threads=N (etap 9) — nadpisuje config, zakres sprawdza walidacja configu.
            const std::string n = requireValue(i, argc, argv, arg);
            if (n.empty() || n.find_first_not_of("0123456789") != std::string::npos) {
                throw CliError("opcja --threads wymaga liczby całkowitej >= 0 (0 = wszystkie wątki OpenMP), podano: " +
                               n);
            }
            opt.overrides.push_back("parallel.threads=" + n);
        } else if (arg == "--thread-stats") {
            opt.threadStats = true;
        } else if (arg == "--benchmark") {
            opt.benchmark = true;
        } else if (arg == "--repeats") {
            opt.repeats = parsePositiveInt(requireValue(i, argc, argv, arg), arg);
        } else if (arg == "--quick") {
            opt.quick = true;
        } else if (arg == "--timing-detail") {
            opt.timingDetail = true;
        } else if (arg == "--print-defaults") {
            opt.printDefaults = true;
        } else if (arg == "--validate") {
            opt.validate = true;
        } else if (arg == "--progress") {
            opt.progress = true;
        } else {
            throw CliError("nieznany argument: " + arg + " (zobacz --help)");
        }
    }
    // Opcje dla GUI (etap 4): --print-defaults i --validate niczego nie liczą i nie zapisują,
    // więc nie łączą się z opcjami przebiegu.
    if (opt.printDefaults &&
        (opt.validate || opt.benchmark || opt.progress || opt.timingDetail || opt.threadStats ||
         !opt.configPath.empty() || !opt.outDir.empty() || !opt.mcFrom.empty() || !opt.batchDir.empty() ||
         !opt.overrides.empty())) {
        throw CliError("--print-defaults nie przyjmuje innych opcji");
    }
    // Seria (etap 5): configi pochodzą z folderu, więc --config i --mc-from nie mają sensu;
    // --set, --grid, --timing-detail i --out dotyczą wszystkich przebiegów serii.
    if (!opt.batchDir.empty() && (!opt.configPath.empty() || !opt.mcFrom.empty() || opt.benchmark || opt.validate)) {
        throw CliError("--batch uruchamia wszystkie configi z folderu — nie łączy się z --config, --mc-from, "
                       "--benchmark ani --validate (dozwolone: --out, --set, --grid, --threads, --timing-detail, "
                       "--thread-stats, --progress)");
    }
    if (opt.validate && (opt.benchmark || opt.progress || opt.timingDetail || opt.threadStats)) {
        throw CliError("--validate tylko sprawdza config (--config, --set, --mc-from) — nie łączy się z "
                       "--benchmark, --progress, --timing-detail ani --thread-stats");
    }
    if (opt.benchmark && opt.threadStats) {
        throw CliError("--thread-stats dotyczy pojedynczej symulacji — nie działa razem z --benchmark");
    }
    if (opt.benchmark && opt.progress) {
        throw CliError("--progress dotyczy pojedynczej symulacji — nie działa razem z --benchmark");
    }
    if (!opt.benchmark && (opt.quick || opt.repeats != 3)) {
        throw CliError("--quick i --repeats działają tylko razem z --benchmark");
    }
    if (opt.benchmark && !opt.mcFrom.empty()) {
        throw CliError("--mc-from nie działa razem z --benchmark");
    }
    if (opt.benchmark && opt.timingDetail) {
        throw CliError("--timing-detail dotyczy pojedynczej symulacji — nie działa razem z --benchmark");
    }
    return opt;
}

std::string Cli::usage() {
    return
        "engine — symulacja erupcji wulkanu: spływ lawy (automat komórkowy) i krystalizacja\n"
        "zastygłej lawy (Monte Carlo)\n"
        "\n"
        "Użycie:\n"
        "  engine --config <plik.json> --out <folder> [--set klucz=wartość]... [--grid vector|matrix]\n"
        "         [--threads N] [--timing-detail] [--thread-stats] [--progress]\n"
        "  engine --mc-from <folder_wyniku_CA> --config <mc.json> --out <folder> [--set klucz=wartość]...\n"
        "         [--progress]\n"
        "  engine --batch <folder_z_configami> --out <folder_wyników> [--set klucz=wartość]... [--progress]\n"
        "  engine --validate [--config <plik.json>] [--set klucz=wartość]... [--mc-from <folder>]\n"
        "  engine --print-defaults\n"
        "  engine --benchmark [--out <folder>] [--repeats N] [--quick]\n"
        "  engine --help\n"
        "\n"
        "Opcje:\n"
        "  --config <plik>    konfiguracja JSON; brakujące pola mają wartości domyślne\n"
        "                     (bez --config: same wartości domyślne)\n"
        "  --out <folder>     folder wyników, tworzony automatycznie\n"
        "                     (domyślnie results/<nazwa configu> lub results/benchmark)\n"
        "  --set k=w          nadpisanie parametru ścieżką z kropkami, np.\n"
        "                     --set space.nx=1000 --set neighborhood=von_neumann\n"
        "  --grid <g>         reprezentacja siatki: vector (płaska tablica) lub matrix\n"
        "  --threads N        liczba wątków OpenMP (skrót dla --set parallel.threads=N; 0 = wszystkie,\n"
        "                     1 = jeden wątek); harmonogram i przypinanie: parallel.schedule, parallel.chunk,\n"
        "                     parallel.affinity (pcores — jeden wątek na rdzeń fizyczny P)\n"
        "  --mc-from <f>      samo Monte Carlo na wyniku CA z folderu f (ca_result.bin lub .txt);\n"
        "                     parametry MC z sekcji mc configu (mc.domain = basalt), wymiary z pliku\n"
        "  --batch <f>        seria: po kolei wszystkie configi *.json z folderu f (kolejność nazw,\n"
        "                     pomija series.json i pliki _*.json), każdy w osobnym procesie do\n"
        "                     <out>/<nazwa configu>/ (+ engine.log); błąd jednego configu nie przerywa\n"
        "                     serii; na końcu <out>/batch_summary.csv i tabela w konsoli\n"
        "                     (domyślnie --out results/<nazwa folderu>; kod 5 = część przebiegów z błędem)\n"
        "  --benchmark        porównanie vector vs macierz (czas + zgodność wyników)\n"
        "  --repeats N        liczba powtórzeń każdego przypadku benchmarku (mediana), domyślnie 3\n"
        "  --quick            benchmark bez przypadków >= 1 mln komórek\n"
        "  --timing-detail    dodatkowo czasy faz wewnątrz CA (ramka, D(n), reguły, zamiana buforów)\n"
        "                     i MC (kroki, składniki statystyk) — sekcja detail w times.json\n"
        "  --thread-stats     czas pracy każdego wątku w fazach kroku CA i MC (min / średnia / maks po wątkach,\n"
        "                     nierównomierność obciążenia, procesory) — sekcja threadStats w times.json\n"
        "  --progress         co ~0,5 s linia postępu na stdout: PROGRESS ca <krok>/<maxSteps> active=<n>,\n"
        "                     PROGRESS mc <MCS>/<mcs>, PROGRESS save 0/1 (dla GUI); z --batch:\n"
        "                     PROGRESS batch <gotowe>/<wszystkie> po każdym configu\n"
        "  --validate         tylko walidacja configu (bez symulacji i bez zapisu); na stdout JSON\n"
        "                     {\"ok\": ..., \"errors\": [...], \"warnings\": [...]}, kod wyjścia 0 lub 1\n"
        "  --print-defaults   wypisuje pełny domyślny config JSON (wszystkie dozwolone klucze)\n"
        "\n"
        "Wyniki symulacji w folderze --out:\n"
        "  config_used.json, ca_result.txt (i/lub ca_result.bin), times.json, stats.json;\n"
        "  przy mc.enabled = true także mc_result.txt (i/lub mc_result.bin) i mc_stats.csv.\n"
        "  times.json: czasy etapów [ms], szczytowa pamięć procesu + model teoretyczny (memory),\n"
        "  rozmiary i czasy zapisu plików (files)\n";
}

void Cli::prepareConsole() {
#ifdef _WIN32
    SetConsoleOutputCP(CP_UTF8);
#endif
}

}  // namespace volcano
