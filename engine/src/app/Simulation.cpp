#include "app/Simulation.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <filesystem>
#include <iostream>
#include <limits>
#include <sstream>
#include <utility>

#include "ca/LavaCA.hpp"
#include "core/Boundary.hpp"
#include "core/MemoryModel.hpp"
#include "core/Neighborhood.hpp"
#include "core/ProcessInfo.hpp"
#include "core/Storage.hpp"
#include "io/ResultReader.hpp"
#include "io/ResultWriter.hpp"
#include "terrain/HeightmapLoader.hpp"

namespace volcano {

namespace fs = std::filesystem;

namespace {

// Liczba z podaną liczbą miejsc po przecinku (do podsumowania w konsoli).
std::string fixed(double v, int decimals) {
    char buf[64];
    std::snprintf(buf, sizeof(buf), "%.*f", decimals, v);
    return buf;
}

// Ścieżka pliku terenu: względem bieżącego katalogu, a jeśli tam go nie ma —
// względem folderu, w którym leży plik konfiguracyjny.
std::string resolveTerrainFile(const Config& c) {
    const fs::path p(c.terrain.file);
    if (p.is_absolute() || fs::exists(p) || c.sourcePath.empty()) {
        return p.string();
    }
    const fs::path nextToConfig = fs::path(c.sourcePath).parent_path() / p;
    return fs::exists(nextToConfig) ? nextToConfig.string() : p.string();
}

// Raport postępu kroku CA: krok / ca.maxSteps i liczba komórek LAVA po kroku (classic:
// komórki ziaren). Koniec CA zwykle następuje dużo przed maxSteps (brak lawy / brak zmian),
// dlatego GUI dostaje też liczbę aktywnych komórek.
template <class Storage>
void reportCa(ProgressReporter& progress, const LavaCA<Storage>& ca, int maxSteps, bool force) {
    const std::uint64_t active = ca.activeHistory().empty() ? 0 : ca.activeHistory().back();
    progress.report("ca", ca.steps(), maxSteps, force, "active", active);
}

// Kroki automatu z raportem postępu (tylko z --progress). Ta sama sekwencja wywołań step()
// co LavaCA::run(); odczyt zegara raz na krok, poza pętlą po komórkach.
template <class Storage>
void runCaWithProgress(LavaCA<Storage>& ca, ProgressReporter& progress, int maxSteps) {
    reportCa(progress, ca, maxSteps, true);
    while (ca.step()) {
        reportCa(progress, ca, maxSteps, false);
    }
    reportCa(progress, ca, maxSteps, true);
}

}  // namespace

Simulation::Simulation(Config cfg) : cfg_(std::move(cfg)) {}

CaParams Simulation::caParams(const Config& c) {
    CaParams p;
    p.mode = c.ca.mode;
    p.seed = c.rngSeed;
    p.maxSteps = c.ca.maxSteps;
    p.eruptionSteps = c.vents.eruptionSteps;
    p.eruptTemp = static_cast<float>(c.vents.eruptTemp);
    p.solidusTemp = static_cast<float>(c.ca.solidusTemp);
    p.coolingAmbient = static_cast<float>(c.ca.coolingAmbient);
    p.coolingLateral = static_cast<float>(c.ca.coolingLateral);
    p.coolingFall = static_cast<float>(c.ca.coolingFall);
    p.ponding = c.ca.ponding;
    p.frontSweep = c.ca.frontSweep;
    return p;
}

Heightmap Simulation::buildTerrain(const Config& c) {
    if (c.ca.mode == CaMode::Classic) {
        return Heightmap{};  // klasyczny rozrost — brak terenu
    }
    if (c.terrain.type == TerrainType::File) {
        return HeightmapLoader::loadCsv(resolveTerrainFile(c), c.space);
    }
    return TerrainGenerator::cone(c.terrain, c.space, c.rngSeed);
}

std::vector<Vent> Simulation::buildVents(const Config& c, const Heightmap& hm) {
    if (c.ca.mode == CaMode::Classic) {
        return VentPlacer::placeSeeds(c.vents.count, c.space, c.rngSeed);
    }
    if (c.vents.placement == VentPlacement::Positions) {
        return VentPlacer::placeAt(c.ventColumns(), c.space, hm);  // kratery w zadanych kolumnach (etap 6)
    }
    return VentPlacer::placeVents(c.vents, c.terrain, c.space, hm, c.rngSeed);
}

template <class Storage>
RunSummary Simulation::runWith(const std::string& outDir, TimingReport& timing) {
    RunSummary s;

    // 1. Alokacja: oba bufory automatu + prekomputowane sąsiedztwo.
    Timer t;
    const Neighborhood nb(cfg_.neighborhood, cfg_.space);
    const Boundary bc(cfg_.boundary, cfg_.ca.mode);
    LavaCA<Storage> ca(cfg_.space, caParams(cfg_), nb, bc);
    timing.add("allocate", t.elapsedMs());
    // Model pamięci (etap 3): oba bufory z ramką i tablice pomocnicze automatu.
    MemoryModel& mem = timing.memory();
    mem.allocate("caGrid", ca.gridBytes());
    mem.allocate("caAux", ca.auxBytes());

    // 2. Teren (mapa wysokości + wpisanie skały do siatki).
    t.reset();
    const Heightmap hm = buildTerrain(cfg_);
    if (!hm.empty()) {
        ca.applyTerrain(hm);
    }
    timing.add("terrain", t.elapsedMs());
    mem.allocate("caAux", ca.auxBytes() + hm.height.size() * sizeof(int));  // + poziomy przelewu i mapa wysokości

    // 3. Kratery / zarodki.
    t.reset();
    s.vents = buildVents(cfg_, hm);
    ca.placeSeeds(s.vents);
    timing.add("vents", t.elapsedMs());

    // 4. Symulacja. Migawki (snapshotsEvery) mierzone osobno, nie wliczają się do caSim.
    //    --timing-detail: automat sumuje czasy faz kroku (ramka, D(n), reguły, zamiana buforów).
    ca.enablePhaseTiming(timing.detailEnabled());
    //    --progress: kroki z raportem postępu (osobna ścieżka — bez flagi przebieg jak wcześniej).
    const int every = cfg_.output.snapshotsEvery;
    const bool progress = progress_ != nullptr && progress_->enabled();
    if (every <= 0) {
        t.reset();
        if (progress) {
            runCaWithProgress(ca, *progress_, cfg_.ca.maxSteps);
        } else {
            ca.run();
        }
        timing.add("caSim", t.elapsedMs());
    } else {
        // Migawka step_<k>.bin = stan po k krokach (k = 0 — stan początkowy z kraterami), co `every`
        // kroków i na końcu. Służy do sprawdzenia odtwarzania erupcji z arrivalStep/solidStep (etap 6).
        const fs::path snapDir = fs::path(outDir) / "snapshots";
        fs::create_directories(snapDir);
        double caMs = 0.0;
        double snapMs = 0.0;
        auto writeSnapshot = [&]() {
            t.reset();
            char name[32];
            std::snprintf(name, sizeof(name), "step_%06d.bin", ca.steps());
            mem.allocate("caSnapshotTemp", ca.state().bytes());  // chwilowa kopia wnętrza siatki (jak jeden bufor)
            ResultWriter::writeBin((snapDir / name).string(), ca.result());
            mem.release("caSnapshotTemp");
            snapMs += t.elapsedMs();
        };
        writeSnapshot();
        while (!ca.finished()) {
            t.reset();
            ca.step();
            caMs += t.elapsedMs();
            if (progress) {
                reportCa(*progress_, ca, cfg_.ca.maxSteps, ca.finished());
            }
            if (ca.steps() % every == 0 || ca.finished()) {
                writeSnapshot();
            }
        }
        timing.add("caSim", caMs);
        timing.add("snapshots", snapMs);
        timing.addFile(snapDir.string(), snapMs);
    }
    if (ca.frontSweep()) {
        // Listy automatu frontalnego (etap 8): pojemność po przebiegu = największy rozmiar w trakcie.
        mem.allocate("caFront", ca.frontBytes());
    }
    if (timing.detailEnabled()) {
        const CaPhaseTimes& ph = ca.phaseTimes();
        timing.addDetail("caFrame", ph.frame);
        if (cfg_.ca.mode == CaMode::Lava) {
            timing.addDetail("caDescent", ph.descent);
        }
        timing.addDetail("caRules", ph.rules);
        timing.addDetail("caFinish", ph.finish);
    }

    // 5. Zapis wyników (stats.json zapisuje run() — po ewentualnym etapie MC).
    if (progress) {
        progress_->report("save", 0, 1, true);
    }
    t.reset();
    s.steps = ca.steps();
    s.stop = ca.stopReason();
    s.activeHistory = ca.activeHistory();
    s.changedHistory = ca.changedHistory();
    s.result = ca.result();
    mem.allocate("caResult", s.result.bytes());
    const fs::path out(outDir);
    Timer tf;  // czas zapisu każdego pliku osobno (sekcja files w times.json)
    if (cfg_.output.format == OutputFormat::Txt || cfg_.output.format == OutputFormat::Both) {
        const std::string path = (out / "ca_result.txt").string();
        tf.reset();
        ResultWriter::writeTxt(path, s.result);
        timing.addFile(path, tf.elapsedMs());
    }
    if (cfg_.output.format == OutputFormat::Bin || cfg_.output.format == OutputFormat::Both) {
        const std::string path = (out / "ca_result.bin").string();
        tf.reset();
        ResultWriter::writeBin(path, s.result);
        timing.addFile(path, tf.elapsedMs());
    }
    timing.add("save", t.elapsedMs());
    // Automat (oba bufory) i mapa terenu giną przy wyjściu z funkcji; wynik zostaje w RunSummary.
    mem.release("caGrid");
    mem.release("caAux");
    mem.release("caFront");
    return s;
}

RunSummary Simulation::run(const std::string& outDir, TimingReport& timing) {
    const fs::path out(outDir);
    Timer tc;
    ResultWriter::writeJson((out / "config_used.json").string(), cfg_.effective);
    timing.addFile((out / "config_used.json").string(), tc.elapsedMs());

    RunSummary s;
    if (cfg_.mc.fullOnly()) {
        // Klasyczny naiwny rozrost ziaren MC na całej przestrzeni: teren i CA są pomijane
        // (w times.json nie ma sekcji allocate, terrain, vents, caSim, save).
        s.caRan = false;
    } else {
        s = (cfg_.grid == GridKind::Matrix) ? runWith<MatrixStorage>(outDir, timing)
                                             : runWith<VectorStorage>(outDir, timing);
    }

    nlohmann::ordered_json stats = s.caRan ? buildStats(cfg_, s) : nlohmann::ordered_json::object();
    if (cfg_.mc.enabled) {
        // Wynik CA jest w pamięci z pełnymi danymi o stygnięciu (solidStep, arrivalStep).
        s.mc = McStage::run(cfg_, s.caRan ? &s.result : nullptr, CoolingData::Full, timing, progress_, outDir);
        s.mcRan = true;
        if (progress_ != nullptr) {
            progress_->report("save", 0, 1, true);
        }
        McStage::save(cfg_, s.mc, outDir, timing);
        stats["mc"] = s.mc.stats;
    }
    Timer t;
    ResultWriter::writeJson((out / "stats.json").string(), stats);
    timing.addFile((out / "stats.json").string(), t.elapsedMs());
    timing.add(s.mcRan ? "mcSave" : "save", t.elapsedMs());
    return s;
}

McSummary Simulation::runMcFrom(const Config& cfgIn, const std::string& caFolder, const std::string& outDir,
                                TimingReport& timing, ProgressReporter* progress) {
    if (cfgIn.mc.domain != McDomain::Basalt) {
        throw ConfigError("--mc-from krystalizuje wynik CA z pliku — wymaga mc.domain = \"basalt\" (podano \"" +
                          std::string(nameOf(cfgIn.mc.domain)) + "\")");
    }
    Config cfg = cfgIn;
    std::vector<std::string> warnings;
    if (!cfg.mc.enabled) {
        warnings.push_back("mc.enabled = false — w trybie --mc-from Monte Carlo jest uruchamiane zawsze");
        cfg.mc.enabled = true;
    }

    // 1. Wynik CA z pliku (czas readInput).
    Timer t;
    ResultSource src;
    const Microstructure ca = ResultReader::readFolder(caFolder, &src);
    timing.add("readInput", t.elapsedMs());
    timing.memory().allocate("caInput", ca.bytes());

    // 2. Wymiary z pliku mają pierwszeństwo przed space z configu (ostrzeżenie tylko, gdy
    //    użytkownik podał space — domyślne wymiary nie są konfliktem).
    if (ca.dims != cfg.space && cfg.spaceFromUser) {
        warnings.push_back("wymiary z pliku " + std::to_string(ca.dims.nx) + " x " + std::to_string(ca.dims.ny) +
                           " x " + std::to_string(ca.dims.nz) + " różnią się od space z configu (" +
                           std::to_string(cfg.space.nx) + " x " + std::to_string(cfg.space.ny) + " x " +
                           std::to_string(cfg.space.nz) + ") — obowiązują wymiary z pliku");
    }
    cfg.space = ca.dims;
    if (cfg.neighborhood == NeighborhoodKind::Hexagonal && !cfg.space.is2D()) {
        throw ConfigError("Sąsiedztwo „hexagonal” jest zdefiniowane tylko w 2D, a wynik CA z pliku jest 3D");
    }
    cfg.effective["space"] = {{"nx", ca.dims.nx}, {"ny", ca.dims.ny}, {"nz", ca.dims.nz}};
    cfg.effective["mc"]["enabled"] = true;
    cfg.effective["_mcFrom"] = fs::absolute(fs::path(caFolder)).lexically_normal().string();
    const fs::path out(outDir);
    t.reset();
    ResultWriter::writeJson((out / "config_used.json").string(), cfg.effective);
    timing.addFile((out / "config_used.json").string(), t.elapsedMs());

    // 3. MC na wczytanym bazalcie. Dane o stygnięciu zależą od formatu pliku.
    const CoolingData cooling = src.hasArrivalStep ? CoolingData::Full
                                : src.hasSolidStep ? CoolingData::SolidOnly
                                                   : CoolingData::None;
    McSummary s = McStage::run(cfg, &ca, cooling, timing, progress, outDir);
    s.warnings.insert(s.warnings.begin(), warnings.begin(), warnings.end());
    if (progress != nullptr) {
        progress->report("save", 0, 1, true);
    }
    McStage::save(cfg, s, outDir, timing);

    // 4. stats.json: skąd pochodził wynik CA + sekcja mc.
    t.reset();
    nlohmann::ordered_json stats;
    stats["source"] = {{"folder", cfg.effective["_mcFrom"]},
                       {"file", src.path},
                       {"format", src.format},
                       {"version", src.version},
                       {"coolingData", cooling == CoolingData::Full        ? "solidStep+arrivalStep"
                                       : cooling == CoolingData::SolidOnly ? "solidStep"
                                                                           : "brak"}};
    stats["mc"] = s.stats;
    Timer tf;
    ResultWriter::writeJson((out / "stats.json").string(), stats);
    timing.addFile((out / "stats.json").string(), tf.elapsedMs());
    timing.add("mcSave", t.elapsedMs());
    return s;
}

nlohmann::ordered_json Simulation::buildStats(const Config& c, const RunSummary& s) {
    using ojson = nlohmann::ordered_json;
    const Microstructure& m = s.result;
    const std::size_t flows = s.vents.size();

    // Zliczenie komórek każdego „ziarna” i zasięgu (maks. odległość pozioma od krateru).
    std::vector<std::uint64_t> lava(flows + 1, 0);
    std::vector<std::uint64_t> basalt(flows + 1, 0);
    std::vector<double> reach(flows + 1, 0.0);
    std::size_t i = 0;
    for (int z = 0; z < m.dims.nz; ++z) {
        for (int y = 0; y < m.dims.ny; ++y) {
            for (int x = 0; x < m.dims.nx; ++x, ++i) {
                const CellType t = m.type[i];
                const std::int32_t f = m.flowId[i];
                if ((t != CellType::Lava && t != CellType::Basalt) || f <= 0 ||
                    static_cast<std::size_t>(f) > flows) {
                    continue;
                }
                const std::size_t fi = static_cast<std::size_t>(f);
                (t == CellType::Lava ? lava : basalt)[fi] += 1;
                const Vent& v = s.vents[fi - 1];
                reach[fi] = std::max(reach[fi], std::hypot(double(x - v.x), double(y - v.y)));
            }
        }
    }

    ojson j;
    j["mode"] = nameOf(c.ca.mode);
    j["steps"] = s.steps;
    j["stopReason"] = describe(s.stop);
    std::uint64_t total = 0;
    std::uint64_t totalLava = 0;
    double maxReach = 0.0;
    std::uint64_t minSize = std::numeric_limits<std::uint64_t>::max();
    std::uint64_t maxSize = 0;
    ojson list = ojson::array();
    const std::size_t listLimit = 10000;  // przy milionie ziaren pomijamy szczegółową listę
    for (std::size_t f = 1; f <= flows; ++f) {
        const std::uint64_t cells = lava[f] + basalt[f];
        total += cells;
        totalLava += lava[f];
        maxReach = std::max(maxReach, reach[f]);
        minSize = std::min(minSize, cells);
        maxSize = std::max(maxSize, cells);
        if (f <= listLimit) {
            const Vent& v = s.vents[f - 1];
            ojson e;
            e["flowId"] = f;
            e["vent"] = {v.x, v.y, v.z};
            e["cells"] = cells;
            if (c.ca.mode == CaMode::Lava) {
                e["lava"] = lava[f];
                e["basalt"] = basalt[f];
                e["maxReach"] = std::round(reach[f] * 100.0) / 100.0;
            }
            list.push_back(e);
        }
    }
    if (c.ca.mode == CaMode::Lava) {
        j["totalLavaVolume"] = total;   // LAVA + BASALT [komórki]
        j["liquidLava"] = totalLava;
        j["maxReach"] = std::round(maxReach * 100.0) / 100.0;
    } else {
        j["grains"] = flows;
        j["meanGrainSize"] = flows ? double(total) / double(flows) : 0.0;
        j["minGrainSize"] = flows ? minSize : 0;
        j["maxGrainSize"] = maxSize;
    }
    j["flows"] = list;
    if (flows > listLimit) {
        j["flowsTruncated"] = true;
    }
    j["activeCells"] = s.activeHistory;
    j["changedCells"] = s.changedHistory;
    return j;
}

int Simulation::runFromCli(const CliOptions& opt, const Timer& sinceStart) {
    // Pamięć procesu przed wczytaniem danych (kod programu, biblioteki, sterta startowa) —
    // punkt odniesienia dla modelu teoretycznego w sekcji memory pliku times.json.
    const ProcessMemory startMemory = ProcessInfo::memory();
    TimingReport timing;
    timing.enableDetail(opt.timingDetail);
    // --progress: linie „PROGRESS etap i/n” na stdout dla GUI (bez flagi raport jest wyłączony).
    ProgressReporter progress = opt.progress ? ProgressReporter(std::cout) : ProgressReporter();

    // Wczytanie i walidacja configu (+ nadpisania z --set / --grid).
    Timer t;
    Config cfg = Config::load(opt.configPath, opt.overrides);
    timing.add("readConfig", t.elapsedMs());
    for (const std::string& w : cfg.warnings) {
        std::cerr << "Ostrzeżenie: " << w << '\n';
    }

    // Folder wyników: --out albo results/<nazwa configu>.
    std::string outDir = opt.outDir;
    if (outDir.empty()) {
        const std::string stem = opt.configPath.empty() ? "default" : fs::path(opt.configPath).stem().string();
        outDir = (fs::path("results") / stem).string();
    }
    fs::create_directories(outDir);

    // Wspólne informacje o przebiegu i środowisku w times.json.
    auto setCommonInfo = [&timing](const Config& c, const Dims& d) {
        timing.setInfo("cells", d.cells());
        timing.setInfo("space", {d.nx, d.ny, d.nz});
        timing.setInfo("neighborhood", Neighborhood::name(c.neighborhood));
        timing.setInfo("boundary", Boundary::name(c.boundary));
    };
    auto setMcInfo = [&timing](const McSummary& mc) {
        timing.setInfo("mcDomain", nameOf(mc.domain));
        timing.setInfo("mcs", mc.mcs);
        timing.setInfo("domainCells", mc.domainCells);
        timing.setInfo("Q", mc.Q);
        timing.setInfo("mcMobility", mc.mobilityUsed);
    };
    auto setEnvInfo = [&timing]() {
        timing.setInfo("cpu", TimingReport::cpuName());
        timing.setInfo("compiler", TimingReport::compilerName());
        timing.setInfo("build", TimingReport::buildType());
    };
    // Profil (etap 3): rozmiary zapisanych plików i pamięć (szczyt procesu + model teoretyczny).
    auto setResourceInfo = [&timing, &startMemory](const Dims& d) {
        timing.recordFileSizes();
        timing.recordMemory(startMemory, d.cells());
    };
    // Linia z czasami wszystkich sekcji.
    auto timesLine = [&timing]() {
        std::string line = "Czasy [ms]     ";
        const char* sep = "";
        for (const auto& [name, ms] : timing.sections()) {
            line += sep + name + ' ' + fixed(ms, 2);
            sep = " | ";
        }
        return line + '\n';
    };

    // --- engine --mc-from: samo MC na wyniku CA z pliku ---
    if (!opt.mcFrom.empty()) {
        const McSummary mc = runMcFrom(cfg, opt.mcFrom, outDir, timing, &progress);
        timing.add("total", sinceStart.elapsedMs());
        const Dims& d = mc.crystals.dims;
        setCommonInfo(cfg, d);
        timing.setInfo("mode", "mc_from");
        timing.setInfo("mcFrom", opt.mcFrom);
        setMcInfo(mc);
        setEnvInfo();
        setResourceInfo(d);
        ResultWriter::writeJson((fs::path(outDir) / "times.json").string(), timing.toJson());

        for (const std::string& w : mc.warnings) {
            std::cerr << "Ostrzeżenie: " << w << '\n';
        }
        std::ostringstream os;
        os << "=== Monte Carlo na wyniku CA z pliku zakończone ===\n";
        os << "Wejście        " << opt.mcFrom << '\n';
        os << "Przestrzeń     " << d.nx << " x " << d.ny << " x " << d.nz << " (" << (d.is2D() ? "2D" : "3D")
           << ", " << d.cells() << " komórek)\n";
        os << "Sąsiedztwo     " << Neighborhood::name(cfg.neighborhood) << ", brzeg " << Boundary::name(cfg.boundary)
           << ", seed " << cfg.rngSeed << '\n';
        os << McStage::describe(mc) << timesLine() << "Wyniki         " << outDir << '\n';
        std::cout << os.str();
        return 0;
    }

    // --- zwykły przebieg: CA (+ MC na bazalcie) albo samo MC na całej przestrzeni ---
    const Config cfgCopy = cfg;  // do podsumowania (Simulation przejmuje config)
    Simulation sim(std::move(cfg));
    sim.setProgress(&progress);
    const RunSummary s = sim.run(outDir, timing);
    timing.add("total", sinceStart.elapsedMs());

    // times.json
    const Dims& d = cfgCopy.space;
    setCommonInfo(cfgCopy, d);
    if (s.caRan) {
        timing.setInfo("steps", s.steps);
        timing.setInfo("grid", nameOf(cfgCopy.grid));
        timing.setInfo("mode", nameOf(cfgCopy.ca.mode));
        timing.setInfo("stopReason", describe(s.stop));
    } else {
        timing.setInfo("mode", "mc_full");
    }
    if (s.mcRan) {
        setMcInfo(s.mc);
    }
    setEnvInfo();
    setResourceInfo(d);
    ResultWriter::writeJson((fs::path(outDir) / "times.json").string(), timing.toJson());

    // Podsumowanie w konsoli.
    for (const std::string& w : s.mc.warnings) {
        std::cerr << "Ostrzeżenie: " << w << '\n';
    }
    std::ostringstream os;
    os << "=== Symulacja zakończona ===\n";
    os << "Przestrzeń     " << d.nx << " x " << d.ny << " x " << d.nz << " (" << (d.is2D() ? "2D" : "3D")
       << ", " << d.cells() << " komórek)\n";
    if (s.caRan) {
        os << "Tryb / siatka  " << nameOf(cfgCopy.ca.mode) << (s.mcRan ? " + MC" : "") << " / "
           << nameOf(cfgCopy.grid) << '\n';
    } else {
        os << "Tryb           Monte Carlo na całej przestrzeni (bez terenu i CA)\n";
    }
    os << "Sąsiedztwo     " << Neighborhood::name(cfgCopy.neighborhood) << ", brzeg "
       << Boundary::name(cfgCopy.boundary) << ", seed " << cfgCopy.rngSeed << '\n';
    if (s.caRan) {
        os << "Kroki          " << s.steps << " (koniec: " << describe(s.stop) << ")\n";
        const nlohmann::ordered_json stats = buildStats(cfgCopy, s);
        if (cfgCopy.ca.mode == CaMode::Lava) {
            os << "Lawa           " << stats["totalLavaVolume"].get<std::uint64_t>() << " komórek (płynna: "
               << stats["liquidLava"].get<std::uint64_t>() << "), zasięg maks. "
               << fixed(stats["maxReach"].get<double>(), 1) << '\n';
            for (const auto& f : stats["flows"]) {
                os << "  krater " << f["flowId"].get<int>() << " (" << f["vent"][0] << ", " << f["vent"][1] << ", "
                   << f["vent"][2] << "): " << f["cells"].get<std::uint64_t>() << " komórek, zasięg "
                   << fixed(f["maxReach"].get<double>(), 1) << '\n';
            }
        } else {
            os << "Ziarna         " << stats["grains"].get<std::uint64_t>() << ", średnia wielkość "
               << fixed(stats["meanGrainSize"].get<double>(), 1) << " komórek (min "
               << stats["minGrainSize"].get<std::uint64_t>() << ", maks "
               << stats["maxGrainSize"].get<std::uint64_t>() << ")\n";
        }
    }
    if (s.mcRan) {
        os << McStage::describe(s.mc);
    }
    os << timesLine() << "Wyniki         " << outDir << '\n';
    std::cout << os.str();
    return 0;
}

}  // namespace volcano
