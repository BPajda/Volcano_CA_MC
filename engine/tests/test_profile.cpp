// Testy elementów profilu aplikacji (etap 3): pamięć procesu, model pamięci, sekcje
// files/detail/memory w times.json, opcja --timing-detail i to, że pomiar czasów faz
// nie zmienia wyniku symulacji.
#include "doctest.h"

#include <cstring>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>

#include "app/Cli.hpp"
#include "app/Simulation.hpp"
#include "ca/LavaCA.hpp"
#include "core/MemoryModel.hpp"
#include "core/ProcessInfo.hpp"
#include "core/Storage.hpp"
#include "io/Config.hpp"
#include "io/TimingReport.hpp"
#include "mc/PottsMC.hpp"

using namespace volcano;

namespace {

// Pusty folder tymczasowy na wyniki testu.
std::filesystem::path tempDir(const std::string& name) {
    const auto dir = std::filesystem::temp_directory_path() / "volcano_tests" / name;
    std::filesystem::remove_all(dir);
    std::filesystem::create_directories(dir);
    return dir;
}

// Przebieg automatu z pomiarem faz włączonym albo nie; zwraca wynik i czasy faz.
template <class S>
Microstructure simulate(const Config& c, bool timed, CaPhaseTimes* phases = nullptr) {
    const Heightmap hm = Simulation::buildTerrain(c);
    LavaCA<S> ca(c.space, Simulation::caParams(c), Neighborhood(c.neighborhood, c.space),
                 Boundary(c.boundary, c.ca.mode));
    if (!hm.empty()) {
        ca.applyTerrain(hm);
    }
    ca.placeSeeds(Simulation::buildVents(c, hm));
    ca.enablePhaseTiming(timed);
    ca.run();
    if (phases != nullptr) {
        *phases = ca.phaseTimes();
    }
    return ca.result();
}

bool identical(const Microstructure& a, const Microstructure& b) {
    return a.dims == b.dims && a.type == b.type && a.flowId == b.flowId && a.solidStep == b.solidStep &&
           a.arrivalStep == b.arrivalStep &&
           std::memcmp(a.temp.data(), b.temp.data(), a.temp.size() * sizeof(float)) == 0;
}

}  // namespace

TEST_CASE("ProcessInfo: pamięć procesu jest dostępna, szczyt rośnie po alokacji") {
    const ProcessMemory before = ProcessInfo::memory();
    REQUIRE(before.available);
    CHECK(before.peakRss > 0);
    CHECK(before.currentRss > 0);
    CHECK(before.peakRss >= before.currentRss);
    // 64 MB zapisane (strony muszą być dotknięte, inaczej nie trafiają do zbioru roboczego).
    const std::size_t n = std::size_t(64) << 20;
    std::vector<char> big(n, 1);
    const ProcessMemory after = ProcessInfo::memory();
    CHECK(after.peakRss >= before.currentRss + n / 2);
    CHECK(big[n - 1] == 1);
}

TEST_CASE("MemoryModel: szczyt to największa suma żyjących tablic i jego skład") {
    MemoryModel m;
    m.allocate("a", 100);
    m.allocate("b", 50);
    CHECK(m.current() == 150);
    m.release("a");
    m.allocate("c", 80);  // 130 < 150 — szczyt bez zmian
    CHECK(m.peak() == 150);
    REQUIRE(m.peakBlocks().size() == 2);
    CHECK(m.peakBlocks()[0].name == "a");
    m.allocate("b", 200);  // zmiana rozmiaru zarejestrowanej tablicy: 280
    CHECK(m.peak() == 280);
    CHECK(m.current() == 280);
    m.release("nieznana");
    CHECK(m.current() == 280);
    // largest() pamięta największy rozmiar każdej tablicy, także zwolnionej.
    REQUIRE(m.largest().size() == 3);
    CHECK(m.largest()[0].bytes == 100);
    CHECK(m.largest()[1].bytes == 200);
}

TEST_CASE("Model pamięci CA: oba bufory z ramką po 13 B na komórkę") {
    const Dims d{10, 8, 6};
    const Config c = Config::load("", {"ca.mode=classic", "space.nx=10", "space.ny=8", "space.nz=6", "ca.sweep=full"});
    LavaCA<VectorStorage> ca(d, Simulation::caParams(c), Neighborhood(c.neighborhood, d),
                             Boundary(c.boundary, c.ca.mode));
    const std::size_t perCell = sizeof(CellType) + sizeof(std::int32_t) + sizeof(float) + 2 * sizeof(std::uint16_t);
    CHECK(perCell == 13);
    CHECK(ca.gridBytes() == 2 * 12 * 10 * 8 * perCell);
    CHECK(ca.auxBytes() == 0);  // classic: bez D(n) i terenu
    Microstructure m;
    m.resize(d);
    CHECK(m.bytes() == d.cells() * perCell);
}

TEST_CASE("Model pamięci CA 2D: ramka tylko w osiach używanych przez sąsiedztwo") {
    const std::size_t perCell = 13;
    // Płaszczyzna x–y (nz = 1): ramka w x i y, bez dwóch warstw z = -1 i z = 1 (wcześniej 3·N_f).
    const Dims xy{10, 8, 1};
    const Config c = Config::load("", {"ca.mode=classic", "space.nx=10", "space.ny=8", "space.nz=1", "ca.sweep=full"});
    LavaCA<VectorStorage> ca(xy, Simulation::caParams(c), Neighborhood(c.neighborhood, xy),
                             Boundary(c.boundary, c.ca.mode));
    CHECK(xy.framedCells() == 12 * 10 * 1);
    CHECK(ca.gridBytes() == 2 * 12 * 10 * 1 * perCell);
    CHECK(MatrixStorage(xy).bytes() == VectorStorage(xy).bytes());
    // Przekrój x–z lawy (ny = 1): ramka w x i z.
    const Dims xz{20, 1, 9};
    CHECK(xz.framedCells() == 22 * 1 * 11);
    CHECK(VectorStorage(xz).bytes() == 22 * 11 * perCell);
    // 3D: ramka we wszystkich osiach jak wcześniej.
    CHECK(Dims{4, 3, 2}.framedCells() == 6 * 5 * 4);
    // MC 2D: orientacja int32 + maska uint8 na komórkę z ramką (+ listy domeny po initialize).
    const Dims mcd{30, 20, 1};
    McParams mp;
    PottsMC mc(mcd, mp, Neighborhood(NeighborhoodKind::Moore, mcd), Boundary(BoundaryKind::Periodic, CaMode::Classic));
    const std::size_t linear = 8 * sizeof(std::ptrdiff_t);  // przesunięcia 8 sąsiadów Moore 2D
    CHECK(mc.bytes() == 32 * 22 * (sizeof(std::int32_t) + sizeof(std::uint8_t)) + linear);
}

TEST_CASE("TimingReport: sekcje files, memory i detail") {
    const auto dir = tempDir("profile_report");
    const auto file = dir / "a.bin";
    {
        std::ofstream out(file, std::ios::binary);
        out << std::string(1234, 'x');
    }
    TimingReport t;
    t.addFile(file.string(), 2.5);
    t.recordFileSizes();
    t.memory().allocate("caGrid", 2600);
    t.recordMemory(ProcessInfo::memory(), 100);
    t.addDetail("caRules", 1.0);
    auto j = t.toJson();
    CHECK(j["files"]["a.bin"]["bytes"] == 1234);
    CHECK(j["files"]["a.bin"]["writeMs"].get<double>() == doctest::Approx(2.5));
    CHECK(j["memory"]["model"]["peakBytes"] == 2600);
    CHECK(j["memory"]["model"]["peakBytesPerCell"].get<double>() == doctest::Approx(26.0));
    CHECK(j["memory"]["model"]["blocks"]["caGrid"]["bytesPerCell"].get<double>() == doctest::Approx(26.0));
    CHECK(j["memory"]["peakRssBytes"].get<std::uint64_t>() > 0);
    CHECK_FALSE(j.contains("detail"));  // bez --timing-detail sekcji nie ma
    t.enableDetail(true);
    t.addDetail("caRules", 0.5);
    j = t.toJson();
    CHECK(j["detail"]["caRules"].get<double>() == doctest::Approx(1.5));
}

TEST_CASE("Cli: --timing-detail") {
    const char* argv[] = {"engine", "--config", "a.json", "--timing-detail"};
    CHECK(Cli::parse(4, argv).timingDetail);
    const char* plain[] = {"engine", "--config", "a.json"};
    CHECK_FALSE(Cli::parse(3, plain).timingDetail);
    const char* withBenchmark[] = {"engine", "--benchmark", "--timing-detail"};
    CHECK_THROWS_AS(Cli::parse(3, withBenchmark), CliError);
}

TEST_CASE("Pomiar czasów faz (--timing-detail) nie zmienia wyniku CA") {
    const Config lava = Config::load("", {"space.nx=40", "space.ny=40", "space.nz=30", "terrain.peakHeight=22",
                                          "terrain.baseRadius=20", "vents.count=3", "vents.placement=random",
                                          "ca.coolingAmbient=2", "ca.coolingLateral=4", "ca.coolingFall=2",
                                          "vents.eruptionSteps=60"});
    CaPhaseTimes ph;
    const Microstructure timed = simulate<VectorStorage>(lava, true, &ph);
    CHECK(identical(timed, simulate<VectorStorage>(lava, false)));
    CHECK(ph.rules > 0.0);
    CHECK(ph.descent > 0.0);

    const Config classic = Config::load("", {"ca.mode=classic", "space.nx=30", "space.ny=30", "space.nz=30",
                                             "vents.count=5", "boundary=periodic"});
    CaPhaseTimes pc;
    CHECK(identical(simulate<VectorStorage>(classic, true, &pc), simulate<VectorStorage>(classic, false)));
    CHECK(pc.rules > 0.0);
    CHECK(pc.descent == 0.0);  // classic nie liczy D(n)
}

TEST_CASE("times.json z przebiegu: rozmiary plików, pamięć i model teoretyczny") {
    const auto dir = tempDir("profile_run");
    Config c = Config::load("", {"ca.mode=classic", "space.nx=20", "space.ny=20", "space.nz=20", "vents.count=4",
                                 "output.format=both", "mc.enabled=false", "ca.sweep=full"});
    TimingReport t;
    t.enableDetail(true);
    Simulation sim(c);
    sim.run(dir.string(), t);
    t.recordFileSizes();
    t.recordMemory(ProcessInfo::memory(), c.space.cells());
    const auto j = t.toJson();
    CHECK(j["files"]["ca_result.bin"]["bytes"].get<std::uint64_t>() == 20 + 8000ULL * 13);
    CHECK(j["files"]["ca_result.txt"]["bytes"].get<std::uint64_t>() ==
          std::filesystem::file_size(dir / "ca_result.txt"));
    CHECK(j["files"].contains("stats.json"));
    // Szczyt modelu: oba bufory (22^3 · 13 · 2) + wynik bez ramki (20^3 · 13).
    CHECK(j["memory"]["model"]["peakBytes"].get<std::uint64_t>() == 22ULL * 22 * 22 * 13 * 2 + 8000ULL * 13);
    CHECK(j["detail"].contains("caRules"));
    CHECK_FALSE(j["detail"].contains("caDescent"));

    // Automat frontalny (domyślny, etap 8): jeden bufor z ramką + znaczniki kandydatów (1 B/komórkę) + listy
    // frontu + wynik bez ramki.
    const auto dirFront = tempDir("profile_run_front");
    Config f = Config::load("", {"ca.mode=classic", "space.nx=20", "space.ny=20", "space.nz=20", "vents.count=4",
                                 "output.format=bin", "mc.enabled=false"});
    TimingReport tf;
    Simulation(f).run(dirFront.string(), tf);
    tf.recordMemory(ProcessInfo::memory(), f.space.cells());
    const auto jf = tf.toJson();
    const auto& blocks = jf["memory"]["model"]["blocks"];
    REQUIRE(blocks.contains("caFront"));
    CHECK(blocks["caGrid"]["bytes"].get<std::uint64_t>() == 22ULL * 22 * 22 * 13);
    CHECK(blocks["caAux"]["bytes"].get<std::uint64_t>() == 8000ULL);
    CHECK(jf["memory"]["model"]["peakBytes"].get<std::uint64_t>() ==
          22ULL * 22 * 22 * 13 + 8000ULL + blocks["caFront"]["bytes"].get<std::uint64_t>() + 8000ULL * 13);
}
