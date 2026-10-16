#pragma once
// Etap krystalizacji Monte Carlo w przebiegu programu (etap 2):
//   przygotowanie domeny i mobilności (z configu i wyniku CA)        -> czas mcInit,
//   pętla kroków MCS                                                  -> czas mcSim,
//   statystyki co mc.statsEvery MCS (liczenie ziaren, energia)        -> czas mcStats (NIE w mcSim),
//   migawki kryształów co mc.snapshotsEvery MCS (domyślnie wyłączone) -> czas mcSnapshots (NIE w mcSim),
//   zapis mc_result.txt / mc_result.bin i mc_stats.csv                -> czas mcSave.
// Sam algorytm jest w mc/PottsMC — tu tylko „klej” między configiem, CA, plikami i czasami.

#include <cstdint>
#include <string>
#include <vector>

#include "app/Progress.hpp"
#include "core/Types.hpp"
#include "io/Config.hpp"
#include "io/TimingReport.hpp"
#include "json.hpp"
#include "mc/McRules.hpp"

namespace volcano {

// Jakie dane o stygnięciu zawiera wynik CA (wynik w pamięci i bin v2: pełne).
enum class CoolingData {
    None,       // ca_result.txt — brak solidStep i arrivalStep: mobilność niedostępna
    SolidOnly,  // ca_result.bin v1 — solidStep bez arrivalStep (przyjmowane 0)
    Full        // solidStep i arrivalStep
};

// Wynik etapu MC.
struct McSummary {
    McDomain domain = McDomain::Basalt;
    std::size_t domainCells = 0;
    int mcs = 0;
    int Q = 0;
    bool mobilityUsed = false;            // czy mobilność wpływała na przebieg MC
    std::vector<McStats> history;         // wiersze mc_stats.csv
    CrystalMap crystals;                  // mapa kryształów (mc_result.*)
    nlohmann::ordered_json stats;         // sekcja "mc" w stats.json
    std::vector<std::string> warnings;    // ostrzeżenia do wypisania użytkownikowi
};

class McStage {
public:
    // Próg mobilności dzielący komórki na „długo płynne” (>= próg) i „szybko zastygłe”.
    static constexpr double kMobilityThreshold = 0.5;

    // Uruchamia MC wg cfg.mc. ca == nullptr -> tryb full (cała przestrzeń cfg.space, bez CA);
    // inaczej domena = komórki BASALT/LAVA z ca, a cooling mówi, czy są dane do mobilności.
    // Czasy trafiają do timing (mcInit, mcSim, mcStats). progress (--progress) dostaje „mc k/mcs”
    // po każdym MCS — poza pomiarem mcSim. Gdy mc.snapshotsEvery > 0 i podano outDir: migawki
    // outDir/mc_snapshots/mcs_<k>.bin (format mc_result.bin) dla MCS 0, co snapshotsEvery i na końcu
    // — do odtwarzania wzrostu ziaren w GUI; czas w osobnej sekcji mcSnapshots.
    static McSummary run(const Config& cfg, const Microstructure* ca, CoolingData cooling, TimingReport& timing,
                         ProgressReporter* progress = nullptr, const std::string& outDir = "");

    // Zapisuje mc_result.txt / mc_result.bin (wg output.format) i mc_stats.csv do outDir.
    // Czas trafia do sekcji mcSave.
    static void save(const Config& cfg, const McSummary& s, const std::string& outDir, TimingReport& timing);

    // Kilka linii podsumowania do konsoli.
    static std::string describe(const McSummary& s);
};

}  // namespace volcano
