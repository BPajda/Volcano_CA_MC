#include "app/McStage.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <filesystem>
#include <sstream>

#include "core/Boundary.hpp"
#include "core/Neighborhood.hpp"
#include "core/Timer.hpp"
#include "io/ResultWriter.hpp"
#include "mc/CoolingMobility.hpp"
#include "mc/Grains.hpp"
#include "mc/PottsMC.hpp"

namespace volcano {

namespace fs = std::filesystem;

namespace {

// Zaokrąglenie do podanej liczby miejsc po przecinku (czytelniejszy stats.json).
double rounded(double v, int decimals) {
    const double f = std::pow(10.0, decimals);
    return std::round(v * f) / f;
}

// Liczba z podaną liczbą miejsc po przecinku (do podsumowania w konsoli).
std::string fixed(double v, int decimals) {
    char buf[64];
    std::snprintf(buf, sizeof(buf), "%.*f", decimals, v);
    return buf;
}

// Ziarna jednej klasy mobilności.
struct ClassGrains {
    std::uint64_t grains = 0;      // ziarna przypisane do klasy
    std::uint64_t grainCells = 0;  // komórki tych ziaren
    std::uint64_t largest = 0;     // największe ziarno klasy

    double mean() const { return grains > 0 ? double(grainCells) / double(grains) : 0.0; }
};

// Dzieli ziarna na klasy wg mobilności: ziarno należy do klasy „wysokiej”, gdy co najmniej
// połowa jego komórek ma mobilność >= progu (decyduje większość komórek ziarna).
void classify(const GrainLabels& g, const std::vector<float>& mobility, double threshold, ClassGrains& high,
              ClassGrains& low) {
    std::vector<std::uint32_t> highCells(g.root.size(), 0);
    for (std::size_t i = 0; i < g.root.size(); ++i) {
        if (g.root[i] != GrainLabels::kNone && mobility[i] >= threshold) {
            ++highCells[g.root[i]];
        }
    }
    for (std::size_t r = 0; r < g.root.size(); ++r) {
        if (g.root[r] != r) {
            continue;  // tylko reprezentanci ziaren (poza domeną root = kNone != r)
        }
        ClassGrains& c = (2ULL * highCells[r] >= g.size[r]) ? high : low;
        ++c.grains;
        c.grainCells += g.size[r];
        c.largest = std::max<std::uint64_t>(c.largest, g.size[r]);
    }
}

// Opis klasy mobilności do stats.json.
nlohmann::ordered_json classJson(std::uint64_t cells, const ClassGrains& start, const ClassGrains& end) {
    nlohmann::ordered_json j;
    j["cells"] = cells;
    j["grainsStart"] = start.grains;
    j["grainsEnd"] = end.grains;
    j["meanGrainSizeStart"] = rounded(start.mean(), 3);
    j["meanGrainSizeEnd"] = rounded(end.mean(), 3);
    j["largestGrainEnd"] = end.largest;
    return j;
}

// Największe ziarno w etykietach.
std::uint64_t largestGrain(const GrainLabels& g) {
    std::uint64_t m = 0;
    for (std::size_t r = 0; r < g.root.size(); ++r) {
        if (g.root[r] == r) {
            m = std::max<std::uint64_t>(m, g.size[r]);
        }
    }
    return m;
}

}  // namespace

McSummary McStage::run(const Config& cfg, const Microstructure* ca, CoolingData cooling, TimingReport& timing,
                       ProgressReporter* progress, const std::string& outDir) {
    McSummary s;
    const bool full = (ca == nullptr);
    s.domain = full ? McDomain::Full : McDomain::Basalt;
    s.mcs = cfg.mc.mcs;
    s.Q = cfg.mc.Q;

    // --- przygotowanie: siatka, domena, mobilność, orientacje początkowe (mcInit) ---
    Timer t;
    const Dims dims = full ? cfg.space : ca->dims;
    const Neighborhood nb(cfg.neighborhood, dims);
    // Tryb full nie ma grawitacji (jak classic CA) — zawijamy wszystkie osie; basalt jak lawa: tylko x, y.
    const Boundary bc(cfg.boundary, full ? CaMode::Classic : CaMode::Lava);
    McParams p;
    p.seed = cfg.rngSeed;
    p.Q = cfg.mc.Q;
    p.J = cfg.mc.J;
    p.kT = cfg.mc.kT;
    PottsMC mc(dims, p, nb, bc);
    // Model pamięci (etap 3): tablice MC rejestrowane przy alokacji, zwalniane przy końcu etapu.
    MemoryModel& mem = timing.memory();
    mem.allocate("mcGrid", mc.bytes());

    std::vector<float> cellMobility;  // mobilność ze stygnięcia (także do statystyk wg klas)
    if (full) {
        mc.setDomainAll();
    } else {
        const std::vector<std::uint8_t> domain = CoolingMobility::basaltDomain(*ca);
        mem.allocate("mcDomainMask", domain.size() * sizeof(std::uint8_t));
        mc.setDomain(domain);
        if (cooling != CoolingData::None) {
            // fromCooling trzyma chwilowo czas w stanie płynnym (uint32) obok wynikowej mobilności.
            mem.allocate("mcCoolingTemp", domain.size() * sizeof(std::uint32_t));
            cellMobility = CoolingMobility::fromCooling(*ca, domain, cfg.mc.mobilityMin);
            mem.allocate("mcMobilityInput", cellMobility.size() * sizeof(float));
            mem.release("mcCoolingTemp");
            if (cfg.mc.mobilityFromCooling) {
                mc.setMobility(cellMobility);
                mem.allocate("mcGrid", mc.bytes());
                s.mobilityUsed = true;
            }
        }
        if (cooling == CoolingData::None && cfg.mc.mobilityFromCooling) {
            s.warnings.push_back("wynik CA bez solidStep/arrivalStep (plik txt) — mobilność ze stygnięcia "
                                 "wyłączona, MC jak dla mobilityFromCooling = false");
        }
        if (cooling == CoolingData::SolidOnly) {
            s.warnings.push_back("ca_result.bin w wersji 1 nie zawiera arrivalStep — czas w stanie płynnym "
                                 "liczony od kroku 0 (= solidStep)");
        }
        mem.release("mcDomainMask");  // maska domeny ginie przy wyjściu z bloku
    }
    mc.initialize();
    mem.allocate("mcGrid", mc.bytes());  // + listy komórek domeny
    s.domainCells = mc.domainCells();
    if (s.domainCells == 0) {
        s.warnings.push_back(full ? "domena MC jest pusta" : "domena MC jest pusta — wynik CA nie zawiera bazaltu");
    }
    timing.add("mcInit", t.elapsedMs());

    // Pomiar statystyk z rejestracją pamięci chwilowej (mapa kryształów + etykiety ziaren);
    // keep != nullptr — etykiety zostają (keepName w modelu pamięci).
    McMeasureTimes measureTimes;
    McMeasureTimes* detailTimes = timing.detailEnabled() ? &measureTimes : nullptr;
    const std::uint64_t measureTempBytes =
        dims.cells() * sizeof(std::int32_t) + GrainLabels::bytesFor(dims.cells());
    auto measure = [&](GrainLabels* keep, const char* keepName) {
        mem.allocate("mcStatsTemp", measureTempBytes);
        McStats st = mc.measure(keep, detailTimes);
        mem.release("mcStatsTemp");
        if (keep != nullptr) {
            mem.allocate(keepName, keep->bytes());
        }
        return st;
    };

    // Migawki kryształów (etap 6, odtwarzanie wzrostu ziaren w GUI): mapa kryształów co snapshotsEvery
    // MCS do outDir/mc_snapshots/mcs_<k>.bin. Czas osobno (mcSnapshots) — nie wlicza się do mcSim.
    const int snapEvery = outDir.empty() ? 0 : cfg.mc.snapshotsEvery;
    const fs::path snapDir = fs::path(outDir) / "mc_snapshots";
    double snapMs = 0.0;
    auto writeSnapshot = [&](int k) {
        Timer ts;
        char name[32];
        std::snprintf(name, sizeof(name), "mcs_%06d.bin", k);
        mem.allocate("mcSnapshotTemp", dims.cells() * sizeof(std::int32_t));  // chwilowa mapa kryształów
        ResultWriter::writeCrystalBin((snapDir / name).string(), mc.crystals());
        mem.release("mcSnapshotTemp");
        snapMs += ts.elapsedMs();
    };
    if (snapEvery > 0) {
        fs::create_directories(snapDir);
        writeSnapshot(0);
    }

    // --- pętla MCS (mcSim) ze statystykami co statsEvery (mcStats, liczone osobno) ---
    double simMs = 0.0;
    double statsMs = 0.0;
    double sweepMin = 0.0;
    double sweepMax = 0.0;
    double sweepFirst = 0.0;
    double sweepLast = 0.0;
    GrainLabels startLabels;
    GrainLabels endLabels;
    t.reset();
    s.history.push_back(measure(&startLabels, "mcLabelsStart"));  // MCS 0 — stan początkowy, acceptRate = 0
    statsMs += t.elapsedMs();
    std::uint64_t attemptsBefore = 0;
    std::uint64_t acceptedBefore = 0;
    if (progress != nullptr) {
        progress->report("mc", 0, cfg.mc.mcs, true);
    }
    for (int k = 1; k <= cfg.mc.mcs; ++k) {
        t.reset();
        mc.sweep();
        const double sweepMs = t.elapsedMs();
        simMs += sweepMs;
        // Rozrzut czasu jednego MCS (--timing-detail): czy koszt kroku zmienia się wraz z rozrostem ziaren.
        sweepMin = (k == 1) ? sweepMs : std::min(sweepMin, sweepMs);
        sweepMax = std::max(sweepMax, sweepMs);
        sweepFirst = (k == 1) ? sweepMs : sweepFirst;
        sweepLast = sweepMs;
        if (k % cfg.mc.statsEvery == 0 || k == cfg.mc.mcs) {
            t.reset();
            McStats st = measure(k == cfg.mc.mcs ? &endLabels : nullptr, "mcLabelsEnd");
            const std::uint64_t att = mc.attempts() - attemptsBefore;
            const std::uint64_t acc = mc.accepted() - acceptedBefore;
            st.acceptRate = att > 0 ? double(acc) / double(att) : 0.0;
            attemptsBefore = mc.attempts();
            acceptedBefore = mc.accepted();
            s.history.push_back(st);
            statsMs += t.elapsedMs();
        }
        if (snapEvery > 0 && (k % snapEvery == 0 || k == cfg.mc.mcs)) {
            writeSnapshot(k);
        }
        if (progress != nullptr) {
            progress->report("mc", k, cfg.mc.mcs, k == cfg.mc.mcs);  // poza pomiarem mcSim i mcStats
        }
    }
    if (cfg.mc.mcs == 0) {
        endLabels = startLabels;
        mem.allocate("mcLabelsEnd", endLabels.bytes());
    }
    timing.add("mcSim", simMs);
    if (snapEvery > 0) {
        timing.add("mcSnapshots", snapMs);
        timing.addFile(snapDir.string(), snapMs);
    }
    if (timing.detailEnabled()) {
        timing.addDetail("mcSweepFirst", sweepFirst);
        timing.addDetail("mcSweepLast", sweepLast);
        timing.addDetail("mcSweepMin", sweepMin);
        timing.addDetail("mcSweepMax", sweepMax);
        timing.addDetail("mcStatsCrystals", measureTimes.crystals);
        timing.addDetail("mcStatsGrains", measureTimes.grains);
        timing.addDetail("mcStatsEnergy", measureTimes.energy);
    }

    // --- statystyki końcowe do stats.json (też mcStats) ---
    t.reset();
    const McStats& first = s.history.front();
    const McStats& last = s.history.back();
    nlohmann::ordered_json j;
    j["domain"] = nameOf(s.domain);
    j["domainCells"] = s.domainCells;
    j["space"] = {dims.nx, dims.ny, dims.nz};
    j["Q"] = cfg.mc.Q;
    j["mcs"] = cfg.mc.mcs;
    j["J"] = cfg.mc.J;
    j["kT"] = cfg.mc.kT;
    j["neighborhood"] = Neighborhood::name(cfg.neighborhood);
    j["boundary"] = Boundary::name(cfg.boundary);
    j["grainConnectivity"] = mc.mooreConnectivity() ? "moore" : "von_neumann";
    j["mobility"] = s.mobilityUsed ? "cooling" : "off";
    if (s.mobilityUsed) {
        j["mobilityMin"] = cfg.mc.mobilityMin;
    }
    j["grainsStart"] = first.grains;
    j["grainsEnd"] = last.grains;
    j["meanGrainSizeStart"] = rounded(first.meanGrainSize, 3);
    j["meanGrainSizeEnd"] = rounded(last.meanGrainSize, 3);
    j["largestGrainEnd"] = largestGrain(endLabels);
    j["energyStart"] = first.energy;
    j["energyEnd"] = last.energy;
    j["attempts"] = mc.attempts();
    j["accepted"] = mc.accepted();
    j["acceptedUphill"] = mc.acceptedUphill();
    if (!cellMobility.empty()) {
        // Efekt „duże ziarna w długo płynnej lawie, drobne w szybko zastygłej”. Klasy liczone
        // zawsze, gdy są dane o stygnięciu — także bez mobilności w dynamice (do porównania).
        ClassGrains hiStart;
        ClassGrains loStart;
        ClassGrains hiEnd;
        ClassGrains loEnd;
        mem.allocate("mcClassifyTemp", startLabels.root.size() * sizeof(std::uint32_t));  // licznik w classify
        classify(startLabels, cellMobility, kMobilityThreshold, hiStart, loStart);
        classify(endLabels, cellMobility, kMobilityThreshold, hiEnd, loEnd);
        mem.release("mcClassifyTemp");
        std::uint64_t hiCells = 0;
        for (std::size_t i = 0; i < cellMobility.size(); ++i) {
            hiCells += (startLabels.root[i] != GrainLabels::kNone && cellMobility[i] >= kMobilityThreshold) ? 1 : 0;
        }
        nlohmann::ordered_json bm;
        bm["threshold"] = kMobilityThreshold;
        bm["mobilityMin"] = cfg.mc.mobilityMin;
        bm["rule"] = "ziarno należy do klasy, w której jest większość jego komórek";
        bm["high"] = classJson(hiCells, hiStart, hiEnd);
        bm["low"] = classJson(s.domainCells - hiCells, loStart, loEnd);
        j["byMobility"] = bm;
    }
    s.stats = j;
    s.crystals = mc.crystals();
    mem.allocate("mcCrystals", s.crystals.bytes());
    timing.add("mcStats", statsMs + t.elapsedMs());
    // Siatka MC, etykiety i mobilność giną przy wyjściu z funkcji; mapa kryształów zostaje w McSummary.
    mem.release("mcGrid");
    mem.release("mcLabelsStart");
    mem.release("mcLabelsEnd");
    mem.release("mcMobilityInput");
    return s;
}

void McStage::save(const Config& cfg, const McSummary& s, const std::string& outDir, TimingReport& timing) {
    Timer t;
    const fs::path out(outDir);
    Timer tf;  // czas zapisu każdego pliku osobno (sekcja files w times.json)
    if (cfg.output.format == OutputFormat::Txt || cfg.output.format == OutputFormat::Both) {
        const std::string path = (out / "mc_result.txt").string();
        tf.reset();
        ResultWriter::writeCrystalTxt(path, s.crystals);
        timing.addFile(path, tf.elapsedMs());
    }
    if (cfg.output.format == OutputFormat::Bin || cfg.output.format == OutputFormat::Both) {
        const std::string path = (out / "mc_result.bin").string();
        tf.reset();
        ResultWriter::writeCrystalBin(path, s.crystals);
        timing.addFile(path, tf.elapsedMs());
    }
    const std::string statsPath = (out / "mc_stats.csv").string();
    tf.reset();
    ResultWriter::writeMcStatsCsv(statsPath, s.history);
    timing.addFile(statsPath, tf.elapsedMs());
    timing.add("mcSave", t.elapsedMs());
}

std::string McStage::describe(const McSummary& s) {
    const nlohmann::ordered_json& j = s.stats;
    std::ostringstream os;
    os << "Monte Carlo    domena " << nameOf(s.domain) << ": " << s.domainCells << " komórek, Q " << s.Q << ", "
       << s.mcs << " MCS, J " << j["J"].get<double>() << ", kT " << j["kT"].get<double>() << ", mobilność "
       << (s.mobilityUsed ? "ze stygnięcia" : "wyłączona") << '\n';
    os << "Ziarna (MC)    " << j["grainsStart"].get<std::uint64_t>() << " -> " << j["grainsEnd"].get<std::uint64_t>()
       << ", średnia wielkość " << fixed(j["meanGrainSizeStart"].get<double>(), 2) << " -> "
       << fixed(j["meanGrainSizeEnd"].get<double>(), 2) << " komórek, energia " << fixed(j["energyStart"].get<double>(), 0)
       << " -> " << fixed(j["energyEnd"].get<double>(), 0) << '\n';
    if (j.contains("byMobility")) {
        const auto& hi = j["byMobility"]["high"];
        const auto& lo = j["byMobility"]["low"];
        os << "  mobilność >= " << kMobilityThreshold << ": " << hi["cells"].get<std::uint64_t>()
           << " komórek, ziarna " << hi["grainsStart"].get<std::uint64_t>() << " -> "
           << hi["grainsEnd"].get<std::uint64_t>() << ", średnia " << fixed(hi["meanGrainSizeEnd"].get<double>(), 2)
           << '\n';
        os << "  mobilność <  " << kMobilityThreshold << ": " << lo["cells"].get<std::uint64_t>()
           << " komórek, ziarna " << lo["grainsStart"].get<std::uint64_t>() << " -> "
           << lo["grainsEnd"].get<std::uint64_t>() << ", średnia " << fixed(lo["meanGrainSizeEnd"].get<double>(), 2)
           << '\n';
    }
    return os.str();
}

}  // namespace volcano
