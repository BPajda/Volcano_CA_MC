#include "app/Benchmark.hpp"

#include <algorithm>
#include <cstdio>
#include <cstring>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <iostream>

#include "app/Simulation.hpp"
#include "ca/LavaCA.hpp"
#include "core/Boundary.hpp"
#include "core/Neighborhood.hpp"
#include "core/Storage.hpp"
#include "core/Timer.hpp"
#include "io/ResultWriter.hpp"
#include "io/TimingReport.hpp"

namespace volcano {

namespace fs = std::filesystem;

namespace {

// Parametry lawy jak w configs/test_2d.json i configs/test_3d.json — przy zmianie
// tamtych plików trzeba zaktualizować także te listy.
const std::vector<std::string> kLava2D = {
    "space.nx=200", "space.ny=1", "space.nz=100", "neighborhood=moore", "boundary=absorbing",
    "terrain.peakHeight=70", "terrain.baseRadius=90", "terrain.craterRadius=6", "terrain.craterDepth=4",
    "terrain.noise=0.05", "vents.count=1", "vents.placement=crater", "vents.eruptionSteps=150",
    "vents.eruptTemp=1200", "ca.coolingAmbient=2.0", "ca.coolingLateral=8.0", "ca.coolingFall=5.0",
    "ca.solidusTemp=800"};
const std::vector<std::string> kLava3D = {
    "space.nx=64", "space.ny=64", "space.nz=48", "neighborhood=moore", "boundary=absorbing",
    "terrain.peakHeight=36", "terrain.baseRadius=30", "terrain.craterRadius=4", "terrain.craterDepth=3",
    "terrain.noise=0.08", "vents.count=3", "vents.placement=random", "vents.eruptionSteps=150",
    "vents.eruptTemp=1200", "ca.coolingAmbient=3.0", "ca.coolingLateral=25.0", "ca.coolingFall=20.0",
    "ca.solidusTemp=800"};

// Buduje przypadek z wartości domyślnych i listy nadpisań (ta sama ścieżka co --set).
BenchmarkCase makeCase(const std::string& label, const std::vector<std::string>& overrides) {
    nlohmann::ordered_json j = Config::defaultsJson();
    for (const std::string& o : overrides) {
        Config::applyOverride(j, o);
    }
    return BenchmarkCase{label, Config::fromJson(j)};
}

// Klasyczny rozrost ziaren, brzeg periodyczny. Domyślnie von Neumann (jak w opisie etapu);
// wariant Moore dla rozmiarów z tabeli referencyjnej — przy Moore liczba kroków (4 i 6–7)
// zgadza się z referencją, przy von Neumannie wychodzi ok. 2x więcej kroków.
BenchmarkCase classicCase(int nx, int ny, int nz, int grains, const char* neighborhood = "von_neumann") {
    const std::string label = (nz == 1) ? std::to_string(nx) + "x" + std::to_string(ny)
                                        : std::to_string(nx) + "x" + std::to_string(ny) + "x" + std::to_string(nz);
    return makeCase(label, {"ca.mode=classic", std::string("neighborhood=") + neighborhood, "boundary=periodic",
                            "ca.maxSteps=65535", "space.nx=" + std::to_string(nx),
                            "space.ny=" + std::to_string(ny), "space.nz=" + std::to_string(nz),
                            "vents.count=" + std::to_string(grains)});
}

// Krótka nazwa sąsiedztwa do kolumny „tryb” (np. "classic/vn").
const char* shortName(NeighborhoodKind k) {
    switch (k) {
        case NeighborhoodKind::VonNeumann: return "vn";
        case NeighborhoodKind::Moore: return "moore";
        case NeighborhoodKind::Pentagonal: return "pent";
        case NeighborhoodKind::Hexagonal: return "hex";
    }
    return "?";
}

// Wynik jednego uruchomienia: czas caSim, liczba kroków i mikrostruktura.
struct TimedRun {
    double ms = 0.0;
    int steps = 0;
    Microstructure result;
};

// Jedno uruchomienie na reprezentacji Storage. Mierzony jest tylko sam automat
// (bez alokacji, terenu i kraterów — te są wspólne dla obu reprezentacji).
template <class Storage>
TimedRun timeRun(const Config& cfg, const Heightmap& hm, const std::vector<Vent>& vents) {
    const Neighborhood nb(cfg.neighborhood, cfg.space);
    const Boundary bc(cfg.boundary, cfg.ca.mode);
    LavaCA<Storage> ca(cfg.space, Simulation::caParams(cfg), nb, bc);
    if (!hm.empty()) {
        ca.applyTerrain(hm);
    }
    ca.placeSeeds(vents);
    Timer t;
    ca.run();
    TimedRun r;
    r.ms = t.elapsedMs();
    r.steps = ca.steps();
    r.result = ca.result();
    return r;
}

double median(std::vector<double> v) {
    std::sort(v.begin(), v.end());
    const std::size_t n = v.size();
    return (n % 2 == 1) ? v[n / 2] : 0.5 * (v[n / 2 - 1] + v[n / 2]);
}

// Porównanie bitowe dwóch mikrostruktur (temp przez memcmp — wykrywa każdą różnicę bitu).
bool identical(const Microstructure& a, const Microstructure& b) {
    if (a.dims != b.dims || a.type != b.type || a.flowId != b.flowId || a.solidStep != b.solidStep ||
        a.arrivalStep != b.arrivalStep) {
        return false;
    }
    return std::memcmp(a.temp.data(), b.temp.data(), a.temp.size() * sizeof(float)) == 0;
}

// Czas w ms: więcej miejsc po przecinku dla krótkich pomiarów.
std::string formatMs(double ms) {
    char buf[32];
    std::snprintf(buf, sizeof(buf), ms < 1.0 ? "%.3f" : (ms < 100.0 ? "%.2f" : "%.1f"), ms);
    return buf;
}

// Wyrównanie tekstu do szerokości kolumny.
std::string pad(const std::string& s, std::size_t width) {
    return s.size() >= width ? s + " " : s + std::string(width - s.size(), ' ');
}

}  // namespace

std::vector<BenchmarkCase> Benchmark::defaultCases(bool quick) {
    std::vector<BenchmarkCase> cases = {
        classicCase(10, 10, 10, 10),         classicCase(10, 10, 10, 10, "moore"),
        classicCase(25, 25, 25, 62),         classicCase(25, 25, 25, 62, "moore"),
        classicCase(50, 50, 50, 100),        classicCase(100, 100, 100, 100),
        classicCase(100, 100, 1, 10),        classicCase(1000, 1000, 1, 100),
        makeCase("200x1x100", kLava2D),      makeCase("64x64x48", kLava3D),
    };
    if (quick) {
        cases.erase(std::remove_if(cases.begin(), cases.end(),
                                   [](const BenchmarkCase& c) { return c.config.space.cells() >= 1000000; }),
                    cases.end());
    }
    return cases;
}

BenchmarkRow Benchmark::runCase(const BenchmarkCase& c, int repeats) {
    const Config& cfg = c.config;
    const Heightmap hm = Simulation::buildTerrain(cfg);
    const std::vector<Vent> vents = Simulation::buildVents(cfg, hm);

    std::vector<double> vectorMs;
    std::vector<double> matrixMs;
    TimedRun lastVector;
    TimedRun lastMatrix;
    bool deterministic = true;
    // Naprzemiennie vector / macierz — zmiany taktowania CPU rozkładają się na obie wersje.
    for (int r = 0; r < repeats; ++r) {
        TimedRun v = timeRun<VectorStorage>(cfg, hm, vents);
        TimedRun m = timeRun<MatrixStorage>(cfg, hm, vents);
        if (r > 0) {
            deterministic = deterministic && identical(v.result, lastVector.result);
        }
        vectorMs.push_back(v.ms);
        matrixMs.push_back(m.ms);
        lastVector = std::move(v);
        lastMatrix = std::move(m);
    }

    BenchmarkRow row;
    row.label = c.label;
    row.cells = cfg.space.cells();
    row.grains = cfg.vents.count;
    row.steps = lastVector.steps;
    row.vectorMs = median(vectorMs);
    row.matrixMs = median(matrixMs);
    row.match = deterministic && lastVector.steps == lastMatrix.steps &&
                identical(lastVector.result, lastMatrix.result);
    row.mode = std::string(nameOf(cfg.ca.mode)) + "/" + shortName(cfg.neighborhood);
    row.neighborhood = Neighborhood::name(cfg.neighborhood);
    row.boundary = Boundary::name(cfg.boundary);
    return row;
}

std::string Benchmark::tableHeader() {
    return pad("siatka", 12) + pad("komorki", 9) + pad("ziarna", 8) + pad("kroki", 7) + pad("vector [ms]", 13) +
           pad("macierz [ms]", 14) + pad("mac/vec", 9) + pad("zgodne", 8) + "tryb";
}

std::string Benchmark::tableRow(const BenchmarkRow& r) {
    char ratio[16];
    std::snprintf(ratio, sizeof(ratio), "%.2f", r.ratio());
    return pad(r.label, 12) + pad(std::to_string(r.cells), 9) + pad(std::to_string(r.grains), 8) +
           pad(std::to_string(r.steps), 7) + pad(formatMs(r.vectorMs), 13) + pad(formatMs(r.matrixMs), 14) +
           pad(ratio, 9) + pad(r.match ? "tak" : "NIE", 8) + r.mode;
}

int Benchmark::runFromCli(const CliOptions& opt) {
    const std::string outDir = opt.outDir.empty() ? (fs::path("results") / "benchmark").string() : opt.outDir;
    fs::create_directories(outDir);

    const std::string cpu = TimingReport::cpuName();
    std::cout << "Benchmark: vector vs macierz (mediana z " << opt.repeats << " powtórzeń, czas samego CA)\n"
              << "CPU: " << cpu << ", kompilator: " << TimingReport::compilerName() << ", build: "
              << TimingReport::buildType() << "\n";
    if (TimingReport::buildType() != "Release") {
        std::cout << "UWAGA: build Debug — czasy nie są miarodajne, uruchom wersję Release.\n";
    }
    std::cout << '\n' << tableHeader() << '\n' << std::flush;

    std::ofstream csv((fs::path(outDir) / "benchmark.csv").string());
    csv << "siatka,komorki,ziarna,kroki,vector_ms,macierz_ms,mac_vec,zgodne,tryb,sasiedztwo,brzeg,powtorzenia\n";

    bool allMatch = true;
    for (const BenchmarkCase& c : defaultCases(opt.quick)) {
        const BenchmarkRow r = runCase(c, opt.repeats);
        allMatch = allMatch && r.match;
        std::cout << tableRow(r) << '\n' << std::flush;
        csv << r.label << ',' << r.cells << ',' << r.grains << ',' << r.steps << ',' << r.vectorMs << ','
            << r.matrixMs << ',' << r.ratio() << ',' << (r.match ? "tak" : "nie") << ',' << r.mode << ','
            << r.neighborhood << ',' << r.boundary << ',' << opt.repeats << '\n';
    }

    // Informacje o środowisku pomiaru (do raportu).
    nlohmann::ordered_json meta;
    char date[32];
    const std::time_t now = std::time(nullptr);
    std::tm local{};
#ifdef _WIN32
    localtime_s(&local, &now);  // wersja bezpieczna wątkowo (MSVC)
#else
    localtime_r(&now, &local);  // wersja bezpieczna wątkowo (POSIX)
#endif
    std::strftime(date, sizeof(date), "%Y-%m-%d %H:%M:%S", &local);
    meta["date"] = date;
    meta["cpu"] = cpu;
    meta["compiler"] = TimingReport::compilerName();
    meta["build"] = TimingReport::buildType();
    meta["repeats"] = opt.repeats;
    meta["quick"] = opt.quick;
    meta["timeMeasured"] = "caSim (sam automat, bez alokacji, terenu i zapisu); mediana";
    ResultWriter::writeJson((fs::path(outDir) / "benchmark_meta.json").string(), meta);

    std::cout << "\nWyniki zapisane w " << outDir << " (benchmark.csv, benchmark_meta.json)\n";
    if (!allMatch) {
        std::cout << "UWAGA: wyniki vector i macierz NIE są zgodne w co najmniej jednym przypadku!\n";
        return 4;
    }
    return 0;
}

}  // namespace volcano
