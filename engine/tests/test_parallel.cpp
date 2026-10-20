// Etap 9 (OpenMP): wynik nie zależy od liczby wątków ani harmonogramu.
//   * CA — lawa 2D/3D, classic (von Neumann, Moore, sąsiedztwa losowe; 2D i 3D), oba brzegi, wypełnianie zagłębień
//     wł./wył., automat frontalny i pełny przebieg: wynik, liczba kroków, powód końca i historia liczników bitowo te
//     same dla 1, 2, 3, 4, 8 wątków i każdego harmonogramu (static / dynamic / guided, z porcją i bez), obie
//     reprezentacje siatki, ścieżka --timing-detail;
//   * MC, szachownica — kolory poprawne (żadne dwie komórki jednego koloru nie są sąsiadami w żadnym wariancie
//     sąsiedztwa; 2D, 3D, osie periodyczne parzyste i nieparzyste), każda komórka domeny raz w MCS, ten sam wynik dla
//     1, 2, 4, 8 wątków (domena pełna i bazalt z mobilnością, kT = 0 i kT > 0);
//   * config i linia poleceń: sekcja parallel, mc.update, --threads, --thread-stats.
// W buildzie bez OpenMP te same testy sprawdzają, że ścieżka „wielu wątków” daje wynik sekwencyjny.
#include "doctest.h"

#include <cstring>
#include <string>
#include <vector>

#include "app/Cli.hpp"
#include "app/Simulation.hpp"
#include "ca/LavaCA.hpp"
#include "core/Storage.hpp"
#include "io/Config.hpp"
#include "mc/PottsMC.hpp"
#include "parallel/Omp.hpp"
#include "parallel/ThreadStats.hpp"

using namespace volcano;

namespace {

// Wszystko, co automat oddaje na zewnątrz (wynik + liczniki do stats.json).
struct Run {
    Microstructure m;
    int steps = 0;
    StopReason stop = StopReason::Running;
    std::vector<std::uint64_t> active;
    std::vector<std::uint64_t> changed;
};

ParallelSettings settings(int threads, Schedule s = Schedule::Static, int chunk = 0) {
    ParallelSettings p;
    p.threads = threads;
    p.schedule = s;
    p.chunk = chunk;
    return p;
}

template <class S>
Run simulate(const Config& c, const ParallelSettings& par, bool timed = false) {
    const Heightmap hm = Simulation::buildTerrain(c);
    LavaCA<S> ca(c.space, Simulation::caParams(c), Neighborhood(c.neighborhood, c.space),
                 Boundary(c.boundary, c.ca.mode));
    ca.setParallel(par);
    if (!hm.empty()) {
        ca.applyTerrain(hm);
    }
    ca.placeSeeds(Simulation::buildVents(c, hm));
    ca.enablePhaseTiming(timed);
    ca.run();
    Run r;
    r.m = ca.result();
    r.steps = ca.steps();
    r.stop = ca.stopReason();
    r.active = ca.activeHistory();
    r.changed = ca.changedHistory();
    return r;
}

bool identical(const Microstructure& a, const Microstructure& b) {
    return a.dims == b.dims && a.type == b.type && a.flowId == b.flowId && a.solidStep == b.solidStep &&
           a.arrivalStep == b.arrivalStep &&
           std::memcmp(a.temp.data(), b.temp.data(), a.temp.size() * sizeof(float)) == 0;
}

void checkSameRun(const Run& ref, const Run& r) {
    CHECK(ref.steps > 1);
    CHECK(r.steps == ref.steps);
    CHECK(r.stop == ref.stop);
    CHECK(r.active == ref.active);
    CHECK(r.changed == ref.changed);
    CHECK(identical(r.m, ref.m));
}

std::vector<std::string> with(std::vector<std::string> base, const std::vector<std::string>& extra) {
    base.insert(base.end(), extra.begin(), extra.end());
    return base;
}

// Porównanie z 1 wątkiem. Poziom: Quick — każda liczba wątków 2, 3, 4, 8 z innym harmonogramem (każdy harmonogram
// i każda liczba wątków co najmniej raz; pełny przebieg i warianty configów — krótszy test w buildzie Debug);
// All — wątki 2, 3, 4, 8 × static / dynamic / guided; Chunks — dodatkowo porcje 1 i 3.
enum class Level { Quick, All, Chunks };

template <class S>
void checkThreads(const std::vector<std::string>& overrides, Level level = Level::Quick) {
    CAPTURE(S::kName);
    const Config c = Config::load("", overrides);
    const Run ref = simulate<S>(c, settings(1));
    if (level == Level::Quick || !c.ca.frontSweep) {
        checkSameRun(ref, simulate<S>(c, settings(2, Schedule::Static)));
        checkSameRun(ref, simulate<S>(c, settings(3, Schedule::Dynamic)));
        checkSameRun(ref, simulate<S>(c, settings(4, Schedule::Guided)));
        checkSameRun(ref, simulate<S>(c, settings(8, Schedule::Dynamic, 2)));
        return;
    }
    for (const int t : {2, 3, 4, 8}) {
        for (const Schedule s : {Schedule::Static, Schedule::Dynamic, Schedule::Guided}) {
            CAPTURE(t);
            CAPTURE(nameOf(s));
            checkSameRun(ref, simulate<S>(c, settings(t, s)));
            if (level == Level::Chunks) {
                for (const int chunk : {1, 3}) {
                    CAPTURE(chunk);
                    checkSameRun(ref, simulate<S>(c, settings(t, s, chunk)));
                }
            }
        }
    }
}

const std::vector<std::string> kLava2D = {"space.nx=120", "space.nz=70", "terrain.peakHeight=45",
                                          "terrain.baseRadius=55", "ca.coolingAmbient=1",
                                          "ca.coolingLateral=3", "ca.coolingFall=1", "vents.eruptionSteps=100"};
const std::vector<std::string> kLava3D = {"space.nx=40", "space.ny=40", "space.nz=30", "terrain.peakHeight=22",
                                          "terrain.baseRadius=20", "terrain.craterRadius=4",
                                          "terrain.craterDepth=2", "vents.count=3", "ca.coolingAmbient=2",
                                          "ca.coolingLateral=4", "ca.coolingFall=2", "vents.eruptionSteps=60"};

std::vector<std::string> classic(int nx, int ny, int nz, int seeds, const std::string& nb, const std::string& bc) {
    return {"ca.mode=classic", "space.nx=" + std::to_string(nx), "space.ny=" + std::to_string(ny),
            "space.nz=" + std::to_string(nz), "vents.count=" + std::to_string(seeds), "neighborhood=" + nb,
            "boundary=" + bc, "ca.maxSteps=65535"};
}

// --- MC ---

McParams mcParams(int Q, double kT = 0.0, std::uint64_t seed = 7) {
    McParams p;
    p.seed = seed;
    p.Q = Q;
    p.J = 1.0;
    p.kT = kT;
    return p;
}

// Wynik przebiegu MC: mapa kryształów, liczniki prób, energia.
struct McRun {
    std::vector<std::int32_t> crystal;
    std::uint64_t attempts = 0;
    std::uint64_t accepted = 0;
    std::uint64_t uphill = 0;
    double energy = 0.0;
};

McRun runMc(const Dims& d, NeighborhoodKind nb, BoundaryKind bc, const McParams& p, const ParallelSettings& par,
            int mcs, bool checkerboard, bool basaltDomain = false) {
    PottsMC mc(d, p, Neighborhood(nb, d), Boundary(bc, basaltDomain ? CaMode::Lava : CaMode::Classic));
    if (basaltDomain) {
        // Domena z dziurami i mobilność zależna od położenia (jak bazalt z wyniku CA).
        std::vector<std::uint8_t> mask(d.cells());
        std::vector<float> mob(d.cells());
        for (std::size_t i = 0; i < mask.size(); ++i) {
            mask[i] = (i % 7 == 3 || i % 11 == 5) ? 0 : 1;
            mob[i] = 0.05f + 0.95f * static_cast<float>(i % 13) / 12.0f;
        }
        mc.setDomain(mask);
        mc.setMobility(mob);
    } else {
        mc.setDomainAll();
    }
    mc.setCheckerboard(checkerboard);
    mc.setParallel(par);
    mc.initialize();
    for (int k = 0; k < mcs; ++k) {
        mc.sweep();
    }
    McRun r;
    r.crystal = mc.crystals().crystal;
    r.attempts = mc.attempts();
    r.accepted = mc.accepted();
    r.uphill = mc.acceptedUphill();
    r.energy = mc.totalEnergy();
    return r;
}

// Współrzędna sąsiada w osi z zawinięciem (periodic) albo -1 poza siatką.
int neighborCoord(int c, int d, int n, bool periodic) {
    const int v = c + d;
    if (v >= 0 && v < n) {
        return v;
    }
    return periodic ? (v + n) % n : -1;
}

// Kolory szachownicy: żadne dwie komórki tego samego koloru nie są sąsiadami (w żadnym wariancie sąsiedztwa),
// a liczba komórek kolorów sumuje się do domeny.
void checkColors(const Dims& d, NeighborhoodKind kind, BoundaryKind bc, int expectedColors) {
    CAPTURE(d.nx);
    CAPTURE(d.ny);
    CAPTURE(d.nz);
    CAPTURE(Neighborhood::name(kind));
    CAPTURE(Boundary::name(bc));
    const Neighborhood nb(kind, d);
    PottsMC mc(d, mcParams(5), nb, Boundary(bc, CaMode::Classic));
    mc.setDomainAll();
    mc.setCheckerboard(true);
    mc.initialize();
    if (expectedColors > 0) {
        CHECK(mc.colorCount() == expectedColors);
    }
    const bool* per = mc.periodic();
    int bad = 0;
    std::size_t covered = 0;
    for (int c = 0; c < mc.colorCount(); ++c) {
        covered += mc.colorEnd(c) - mc.colorBegin(c);
    }
    CHECK(covered == d.cells());
    CHECK(mc.colorEnd(mc.colorCount() - 1) == mc.domainCells());
    for (int z = 0; z < d.nz; ++z) {
        for (int y = 0; y < d.ny; ++y) {
            for (int x = 0; x < d.nx; ++x) {
                const int col = mc.colorOf(x, y, z);
                for (int v = 0; v < nb.variantCount(); ++v) {
                    for (const Offset& o : nb.variant(v)) {
                        const int nx = neighborCoord(x, o.dx, d.nx, per[0]);
                        const int ny = neighborCoord(y, o.dy, d.ny, per[1]);
                        const int nz = neighborCoord(z, o.dz, d.nz, per[2]);
                        if (nx < 0 || ny < 0 || nz < 0 || (nx == x && ny == y && nz == z)) {
                            continue;
                        }
                        bad += mc.colorOf(nx, ny, nz) == col ? 1 : 0;
                    }
                }
            }
        }
    }
    CHECK(bad == 0);
}

}  // namespace

TEST_CASE("Równoległość: config parallel, mc.update, --threads, --thread-stats") {
    const Config d = Config::load("", {});
    CHECK(d.parallel.threads == 1);
    CHECK(d.parallel.schedule == Schedule::Static);
    CHECK(d.parallel.chunk == 0);
    CHECK(d.parallel.affinity == Affinity::None);
    CHECK_FALSE(d.mc.checkerboard);
    CHECK(d.parallelSettings().threads == 1);

    const Config c = Config::load("", {"parallel.threads=4", "parallel.schedule=guided", "parallel.chunk=2",
                                       "parallel.affinity=pcores", "mc.update=checkerboard"});
    CHECK(c.parallel.schedule == Schedule::Guided);
    CHECK(c.parallel.chunk == 2);
    CHECK(c.parallel.affinity == Affinity::PCores);
    CHECK(c.mc.checkerboard);
    CHECK(c.parallelSettings().threads == (openmpBuilt() ? 4 : 1));
    CHECK(Config::load("", {"parallel.threads=0"}).parallelSettings().threads == omp_get_max_threads());

    CHECK_THROWS_AS(Config::load("", {"parallel.threads=-1"}), ConfigError);
    CHECK_THROWS_AS(Config::load("", {"parallel.threads=1000"}), ConfigError);
    CHECK_THROWS_AS(Config::load("", {"parallel.schedule=auto"}), ConfigError);
    CHECK_THROWS_AS(Config::load("", {"parallel.affinity=ecores"}), ConfigError);
    CHECK_THROWS_AS(Config::load("", {"mc.update=parallel"}), ConfigError);
    // MC w trybie random z wieloma wątkami — ostrzeżenie (pętla prób zostaje sekwencyjna).
    CHECK_FALSE(Config::load("", {"mc.enabled=true", "parallel.threads=4"}).warnings.empty());

    const char* argv[] = {"engine", "--threads", "8", "--thread-stats"};
    const CliOptions o = Cli::parse(4, argv);
    CHECK(o.threadStats);
    REQUIRE(o.overrides.size() == 1);
    CHECK(o.overrides[0] == "parallel.threads=8");
    const char* bad[] = {"engine", "--threads", "-2"};
    CHECK_THROWS_AS(Cli::parse(3, bad), CliError);
}

TEST_CASE("Równoległość CA: lawa 2D i 3D, front i full, brzegi, wypełnianie zagłębień — 1, 2, 3, 4, 8 wątków") {
    for (const char* sweep : {"front", "full"}) {
        CAPTURE(sweep);
        const std::string sw = std::string("ca.sweep=") + sweep;
        // Warianty krótsze (krótsza erupcja, szybsze stygnięcie) — mniej kroków, krótszy test w buildzie Debug.
        const std::vector<std::string> shortLava = with(kLava3D, {sw, "vents.eruptionSteps=25", "ca.coolingAmbient=4"});
        checkThreads<VectorStorage>(with(kLava2D, {sw}), Level::Chunks);
        checkThreads<VectorStorage>(with(kLava2D, {sw, "neighborhood=von_neumann", "boundary=periodic"}));
        checkThreads<VectorStorage>(with(kLava3D, {sw}), Level::All);
        checkThreads<VectorStorage>(with(shortLava, {"boundary=periodic", "neighborhood=pentagonal"}));
        checkThreads<VectorStorage>(with(shortLava, {"ca.ponding=false", "vents.placement=random", "vents.count=6"}));
        checkThreads<MatrixStorage>(shortLava);
    }
}

TEST_CASE("Równoległość CA: classic — von Neumann, Moore, sąsiedztwa losowe, 2D i 3D, oba brzegi") {
    for (const char* sweep : {"front", "full"}) {
        CAPTURE(sweep);
        const std::string sw = std::string("ca.sweep=") + sweep;
        for (const char* bc : {"periodic", "absorbing"}) {
            CAPTURE(bc);
            checkThreads<VectorStorage>(with(classic(60, 50, 1, 12, "von_neumann", bc), {sw}), Level::All);
            checkThreads<VectorStorage>(with(classic(60, 50, 1, 12, "moore", bc), {sw}));
            checkThreads<VectorStorage>(with(classic(18, 16, 14, 8, "moore", bc), {sw}));
        }
        checkThreads<VectorStorage>(with(classic(50, 1, 40, 10, "hexagonal", "periodic"), {sw}), Level::Chunks);  // x–z
        checkThreads<VectorStorage>(with(classic(16, 14, 12, 6, "pentagonal", "periodic"), {sw}));
        checkThreads<MatrixStorage>(with(classic(40, 30, 1, 8, "von_neumann", "periodic"), {sw}));
    }
}

TEST_CASE("Równoległość CA: ścieżka --timing-detail i limit kroków dają ten sam wynik") {
    for (const char* sweep : {"front", "full"}) {
        CAPTURE(sweep);
        const Config c = Config::load("", with(kLava3D, {std::string("ca.sweep=") + sweep}));
        const Run ref = simulate<VectorStorage>(c, settings(1));
        checkSameRun(ref, simulate<VectorStorage>(c, settings(4, Schedule::Dynamic), true));
        const Config lim = Config::load("", with(kLava3D, {std::string("ca.sweep=") + sweep, "ca.maxSteps=17"}));
        const Run refLim = simulate<VectorStorage>(lim, settings(1));
        CHECK(refLim.stop == StopReason::MaxSteps);
        checkSameRun(refLim, simulate<VectorStorage>(lim, settings(3, Schedule::Guided, 2)));
    }
}

TEST_CASE("Równoległość CA: statystyki wątków (--thread-stats) — fazy, nierównomierność >= 1, procesory") {
    const Config c = Config::load("", kLava3D);
    ThreadStats ts(4, LavaCA<VectorStorage>::threadPhases(true, CaMode::Lava));
    ParallelSettings par = settings(4, Schedule::Dynamic);
    par.stats = &ts;
    const Run ref = simulate<VectorStorage>(c, settings(1));
    checkSameRun(ref, simulate<VectorStorage>(c, par));
    const nlohmann::ordered_json j = ts.toJson();
    CHECK(j["threads"] == 4);
    CHECK(j["steps"] == ref.steps);
    CHECK(j["phases"].size() == 3);
    CHECK(j["threadWorkMs"].size() == 4);
    CHECK(j["imbalance"].get<double>() >= 1.0);
    CHECK(j["stepMaxMs"].get<double>() >= j["stepMinMs"].get<double>());
    CHECK(j["cpus"].size() == 4);
}

TEST_CASE("Szachownica MC: kolory — żadne dwie komórki jednego koloru nie są sąsiadami") {
    using NK = NeighborhoodKind;
    using BK = BoundaryKind;
    // 2D (x–y i x–z), parzyste wymiary: von Neumann 2 kolory, Moore i sąsiedztwa losowe 4.
    for (const BK bc : {BK::Periodic, BK::Absorbing}) {
        checkColors(Dims{8, 6, 1}, NK::VonNeumann, bc, 2);
        checkColors(Dims{8, 1, 6}, NK::VonNeumann, bc, 2);
        checkColors(Dims{8, 6, 1}, NK::Moore, bc, 4);
        checkColors(Dims{8, 6, 1}, NK::Pentagonal, bc, 4);
        checkColors(Dims{8, 6, 1}, NK::Hexagonal, bc, 4);
        checkColors(Dims{6, 4, 4}, NK::VonNeumann, bc, 2);
        checkColors(Dims{6, 4, 4}, NK::Moore, bc, 8);
        checkColors(Dims{6, 4, 4}, NK::Pentagonal, bc, 8);
    }
    // Nieparzyste osie: przy brzegu absorbującym bez zmian, przy periodycznym — dodatkowa klasa ostatniej warstwy.
    checkColors(Dims{7, 5, 1}, NK::VonNeumann, BK::Absorbing, 2);
    checkColors(Dims{7, 5, 1}, NK::Moore, BK::Absorbing, 4);
    checkColors(Dims{7, 5, 1}, NK::VonNeumann, BK::Periodic, 9);
    checkColors(Dims{7, 6, 1}, NK::Moore, BK::Periodic, 6);
    checkColors(Dims{5, 4, 3}, NK::Moore, BK::Periodic, 18);
    checkColors(Dims{3, 3, 3}, NK::Pentagonal, BK::Periodic, 27);
    checkColors(Dims{7, 5, 3}, NK::VonNeumann, BK::Periodic, 27);
}

TEST_CASE("Szachownica MC: ten sam wynik dla 1, 2, 4, 8 wątków i każdego harmonogramu") {
    using NK = NeighborhoodKind;
    struct Case {
        Dims d;
        NK nb;
        BoundaryKind bc;
        double kT;
        bool basalt;
    };
    const Case cases[] = {
        {Dims{40, 36, 1}, NK::VonNeumann, BoundaryKind::Periodic, 0.0, false},
        {Dims{30, 1, 24}, NK::Moore, BoundaryKind::Absorbing, 0.0, false},
        {Dims{14, 12, 10}, NK::Moore, BoundaryKind::Periodic, 0.0, false},
        {Dims{13, 11, 9}, NK::Pentagonal, BoundaryKind::Periodic, 0.7, false},  // nieparzyste osie, sąsiedztwo losowe
        {Dims{20, 18, 12}, NK::Moore, BoundaryKind::Periodic, 0.3, true},       // bazalt z mobilnością
        {Dims{36, 30, 1}, NK::Hexagonal, BoundaryKind::Periodic, 0.0, false},
    };
    for (const Case& c : cases) {
        CAPTURE(c.d.nx);
        CAPTURE(c.d.ny);
        CAPTURE(c.d.nz);
        CAPTURE(Neighborhood::name(c.nb));
        const McRun ref = runMc(c.d, c.nb, c.bc, mcParams(12, c.kT), settings(1), 6, true, c.basalt);
        CHECK(ref.accepted > 0);
        for (const int t : {2, 4, 8}) {
            for (const Schedule s : {Schedule::Static, Schedule::Dynamic, Schedule::Guided}) {
                CAPTURE(t);
                CAPTURE(nameOf(s));
                const McRun r = runMc(c.d, c.nb, c.bc, mcParams(12, c.kT), settings(t, s, t == 4 ? 2 : 0), 6, true,
                                      c.basalt);
                CHECK(r.crystal == ref.crystal);
                CHECK(r.attempts == ref.attempts);
                CHECK(r.accepted == ref.accepted);
                CHECK(r.uphill == ref.uphill);
                CHECK(r.energy == ref.energy);
            }
        }
    }
}

TEST_CASE("Szachownica MC: każda komórka próbowana raz na MCS; inny proces niż random; ziarna rosną") {
    const Dims d{32, 32, 1};
    // Bez mobilności każda komórka domeny jest próbowana dokładnie raz w MCS.
    const McRun cb = runMc(d, NeighborhoodKind::Moore, BoundaryKind::Periodic, mcParams(20), settings(1), 5, true);
    CHECK(cb.attempts == 5 * d.cells());
    // Random i szachownica to różne procesy losowe (ten sam seed — inna trajektoria).
    const McRun rnd = runMc(d, NeighborhoodKind::Moore, BoundaryKind::Periodic, mcParams(20), settings(1), 5, false);
    CHECK(rnd.crystal != cb.crystal);
    // Tryb random z wieloma wątkami — pętla prób sekwencyjna, wynik jak przy 1 wątku.
    const McRun rnd4 = runMc(d, NeighborhoodKind::Moore, BoundaryKind::Periodic, mcParams(20), settings(4), 5, false);
    CHECK(rnd4.crystal == rnd.crystal);
    CHECK(rnd4.energy == rnd.energy);
    // Zgrubianie: energia (długość granic) maleje.
    PottsMC mc(d, mcParams(20), Neighborhood(NeighborhoodKind::VonNeumann, d),
               Boundary(BoundaryKind::Periodic, CaMode::Classic));
    mc.setDomainAll();
    mc.setCheckerboard(true);
    mc.initialize();
    const double e0 = mc.totalEnergy();
    for (int k = 0; k < 30; ++k) {
        mc.sweep();
    }
    CHECK(mc.totalEnergy() < 0.8 * e0);
}
