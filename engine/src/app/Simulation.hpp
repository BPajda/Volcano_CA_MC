#pragma once
// Pojedyncza symulacja „od configu do plików”: teren -> kratery -> automat -> zapis,
// a gdy mc.enabled — dalej krystalizacja Monte Carlo na wyniku CA (mc.domain = basalt)
// albo samo MC na całej przestrzeni bez terenu i CA (mc.domain = full).
// Każdy etap ma osobny pomiar czasu (TimingReport -> times.json).
// Wybór reprezentacji siatki (vector / matrix) następuje raz, przy uruchomieniu —
// dalej działa kod szablonowy bez wywołań wirtualnych.

#include <cstdint>
#include <string>
#include <vector>

#include "app/Cli.hpp"
#include "app/McStage.hpp"
#include "app/Progress.hpp"
#include "ca/CaRules.hpp"
#include "core/Timer.hpp"
#include "core/Types.hpp"
#include "io/Config.hpp"
#include "io/TimingReport.hpp"
#include "json.hpp"
#include "terrain/TerrainGenerator.hpp"
#include "terrain/VentPlacer.hpp"

namespace volcano {

// Wynik przebiegu (niezależny od reprezentacji siatki).
struct RunSummary {
    bool caRan = true;                          // false w trybie mc.domain = full (bez CA)
    int steps = 0;
    StopReason stop = StopReason::Running;
    std::vector<Vent> vents;
    std::vector<std::uint64_t> activeHistory;   // LAVA po każdym kroku
    std::vector<std::uint64_t> changedHistory;  // zmienione komórki w każdym kroku
    Microstructure result;
    bool mcRan = false;                         // czy był etap Monte Carlo
    McSummary mc;
};

class Simulation {
public:
    explicit Simulation(Config cfg);

    // Raport postępu (--progress); nullptr albo wyłączony raport = przebieg bez zmian.
    void setProgress(ProgressReporter* progress) { progress_ = progress; }

    // Przebieg z zapisem config_used.json, ca_result.*, (mc_result.*, mc_stats.csv), stats.json
    // do outDir (folder musi istnieć). Czasy etapów trafiają do timing.
    RunSummary run(const std::string& outDir, TimingReport& timing);

    // Samo MC na wyniku CA wczytanym z folderu caFolder (engine --mc-from): ca_result.bin
    // (v1/v2) albo ca_result.txt. Wymiary bierze z pliku (konflikt z cfg.space -> ostrzeżenie).
    // Zapis do outDir: config_used.json, mc_result.*, mc_stats.csv, stats.json.
    static McSummary runMcFrom(const Config& cfg, const std::string& caFolder, const std::string& outDir,
                               TimingReport& timing, ProgressReporter* progress = nullptr);

    // --- elementy wspólne z benchmarkiem ---

    // Parametry automatu z configu.
    static CaParams caParams(const Config& c);

    // Teren (tryb lava): stożek albo mapa z pliku. W trybie classic — pusta mapa.
    static Heightmap buildTerrain(const Config& c);

    // Kratery (lava) albo zarodki (classic).
    static std::vector<Vent> buildVents(const Config& c, const Heightmap& hm);

    // Statystyki do stats.json: objętość lawy na krater, zasięg, aktywne komórki w krokach.
    static nlohmann::ordered_json buildStats(const Config& c, const RunSummary& s);

    // Obsługa wywołania z linii poleceń: wczytanie configu, folder wyników, times.json,
    // podsumowanie w konsoli. sinceStart mierzy czas od startu programu (sekcja total).
    static int runFromCli(const CliOptions& opt, const Timer& sinceStart);

private:
    template <class Storage>
    RunSummary runWith(const std::string& outDir, TimingReport& timing);

    Config cfg_;
    ProgressReporter* progress_ = nullptr;
};

}  // namespace volcano
