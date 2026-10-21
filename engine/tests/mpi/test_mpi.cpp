// Etap 10 (MPI): wynik engine_mpi bitowo taki sam jak engine przy każdej liczbie procesów.
// Uruchamiane przez ctest pod mpiexec dla 1, 2, 3, 4, 5 i 8 procesów (engine/CMakeLists.txt). Każdy proces liczy
// sam wynik odniesienia (ten sam kod co engine: LavaCA na całej przestrzeni, McStage::run — małe przypadki),
// potem wersję rozproszoną (MpiSimulation::runCa / runMc); proces 0 porównuje wynik, liczbę kroków, powód końca,
// historię liczników (CA) oraz mapę kryształów, historię statystyk i sekcję mc pliku stats.json (MC).
//   * lawa 2D i 3D, automat frontalny i pełny przebieg, Moore / von Neumann / pentagonal, brzeg absorbujący
//     i periodyczny, wypełnianie zagłębień wł./wył.;
//   * kratery i zarodki dokładnie na granicach pasów i przy brzegu globalnym;
//   * classic 3D i w płaszczyźnie x–y (pasy w y), wszystkie sąsiedztwa, oba brzegi (pierścień przy periodycznym);
//   * MC szachownica 2D / 3D (pełna przestrzeń, osie parzyste i nieparzyste, kT = 0 i kT > 0), MC na bazalcie
//     z mobilnością ze stygnięcia; mpi.exchange "always" = "changed"; tryb hybrydowy (procesy × 4 wątki, gdy razem
//     najwyżej 8); mc.update = random przy 1 procesie.
#include "doctest.h"

#include <mpi.h>

#include <cstring>
#include <string>
#include <vector>

#include "app/McStage.hpp"
#include "app/Simulation.hpp"
#include "ca/LavaCA.hpp"
#include "core/Storage.hpp"
#include "io/Config.hpp"
#include "mpi/MpiSimulation.hpp"
#include "parallel/Strip.hpp"

using namespace volcano;

namespace {

int worldSize() {
    int n = 1;
    MPI_Comm_size(MPI_COMM_WORLD, &n);
    return n;
}

bool isRoot() {
    int r = 0;
    MPI_Comm_rank(MPI_COMM_WORLD, &r);
    return r == 0;
}

// Wynik procesu 0 rozesłany do wszystkich (asercja w każdym procesie).
bool agreed(bool okOnRoot) {
    int v = okOnRoot ? 1 : 0;
    MPI_Bcast(&v, 1, MPI_INT, 0, MPI_COMM_WORLD);
    return v != 0;
}

bool identical(const Microstructure& a, const Microstructure& b) {
    return a.dims == b.dims && a.type == b.type && a.flowId == b.flowId && a.solidStep == b.solidStep &&
           a.arrivalStep == b.arrivalStep && a.temp.size() == b.temp.size() &&
           std::memcmp(a.temp.data(), b.temp.data(), a.temp.size() * sizeof(float)) == 0;
}

// Wynik odniesienia: automat na całej przestrzeni w jednym procesie (jak Simulation::runWith w engine).
struct SeqCa {
    Microstructure result;
    int steps = 0;
    StopReason stop = StopReason::Running;
    std::vector<std::uint64_t> active;
    std::vector<std::uint64_t> changed;
};

SeqCa runSeqCa(const Config& c, const std::vector<Vent>* vents) {
    const Heightmap hm = Simulation::buildTerrain(c);
    LavaCA<VectorStorage> ca(c.space, Simulation::caParams(c), Neighborhood(c.neighborhood, c.space),
                             Boundary(c.boundary, c.ca.mode));
    ParallelSettings one;
    ca.setParallel(one);
    if (!hm.empty()) {
        ca.applyTerrain(hm);
    }
    ca.placeSeeds(vents != nullptr ? *vents : Simulation::buildVents(c, hm));
    ca.run();
    SeqCa r;
    r.result = ca.result();
    r.steps = ca.steps();
    r.stop = ca.stopReason();
    r.active = ca.activeHistory();
    r.changed = ca.changedHistory();
    return r;
}

// CA rozproszone = odniesienie. Zwraca wynik MPI (dla dalszego MC).
MpiCaRun checkCa(const Config& c, const std::vector<Vent>* vents = nullptr) {
    const SeqCa ref = runSeqCa(c, vents);
    MpiContext ctx = MpiContext::world();
    TimingReport timing;
    MpiCaRun r = MpiSimulation::runCa(ctx, c, timing, nullptr, "", vents);
    // Historia jest globalna na każdym procesie.
    CHECK(r.steps == ref.steps);
    CHECK(r.stop == ref.stop);
    CHECK(r.activeHistory == ref.active);
    CHECK(r.changedHistory == ref.changed);
    CHECK(ref.steps > 1);
    const bool same = isRoot() ? identical(r.result, ref.result) : true;
    CHECK(agreed(same));
    if (ctx.size > 1) {
        CHECK(r.comm.exchanges == static_cast<std::uint64_t>(ref.steps));  // wymiana przed każdym krokiem
        CHECK(r.comm.reductions >= static_cast<std::uint64_t>(ref.steps));
    }
    return r;
}

// MC rozproszone = McStage::run w jednym procesie (cała przestrzeń albo bazalt z wyniku CA odniesienia).
void checkMc(const Config& c, const Microstructure* seqCa, const Microstructure* slab) {
    TimingReport t1;
    const McSummary ref = McStage::run(c, seqCa, CoolingData::Full, t1);
    MpiContext ctx = MpiContext::world();
    TimingReport t2;
    MpiMcRun info;
    const McSummary s = MpiSimulation::runMc(ctx, c, slab, CoolingData::Full, t2, nullptr, "", &info);
    CHECK(s.domainCells == ref.domainCells);
    CHECK(s.mobilityUsed == ref.mobilityUsed);
    bool same = true;
    if (isRoot()) {
        same = s.crystals.crystal == ref.crystals.crystal && s.history.size() == ref.history.size() &&
               s.stats.dump() == ref.stats.dump();
        for (std::size_t i = 0; same && i < ref.history.size(); ++i) {
            const McStats& a = s.history[i];
            const McStats& b = ref.history[i];
            same = a.mcs == b.mcs && a.grains == b.grains && a.meanGrainSize == b.meanGrainSize &&
                   a.energy == b.energy && a.acceptRate == b.acceptRate;
        }
        if (!same) {
            MESSAGE("MPI: " << s.stats.dump());
            MESSAGE("ref: " << ref.stats.dump());
        }
    }
    CHECK(agreed(same));
    if (ctx.size > 1 && c.mc.mcs > 0) {
        // wymiana po każdym kolorze + raz po inicjalizacji
        const int colors = s.stats.contains("colors") ? s.stats["colors"].get<int>() : 0;
        if (isRoot()) {
            CHECK(info.sim.exchanges == 1 + static_cast<std::uint64_t>(colors) * static_cast<std::uint64_t>(c.mc.mcs));
        }
    }
}

std::vector<std::string> with(std::vector<std::string> base, const std::vector<std::string>& extra) {
    base.insert(base.end(), extra.begin(), extra.end());
    return base;
}

// Przypadki: małe, ale z co najmniej 8 warstwami (8 procesów) i z lawą przechodzącą przez granice pasów.
const std::vector<std::string> kLava2D = {"space.nx=90",  "space.ny=1",  "space.nz=40", "terrain.peakHeight=28",
                                          "terrain.baseRadius=40", "terrain.craterRadius=4", "terrain.craterDepth=3",
                                          "vents.count=2", "ca.coolingAmbient=1.5", "ca.coolingLateral=4",
                                          "ca.coolingFall=1", "vents.eruptionSteps=70"};
const std::vector<std::string> kLava3D = {"space.nx=30", "space.ny=30", "space.nz=24", "terrain.peakHeight=17",
                                          "terrain.baseRadius=15", "terrain.craterRadius=3",
                                          "terrain.craterDepth=2", "vents.count=3", "vents.placement=random",
                                          "ca.coolingAmbient=2", "ca.coolingLateral=6", "ca.coolingFall=2",
                                          "vents.eruptionSteps=50"};

std::vector<std::string> classic(int nx, int ny, int nz, int seeds, const std::string& nb, const std::string& bc) {
    return {"ca.mode=classic", "space.nx=" + std::to_string(nx), "space.ny=" + std::to_string(ny),
            "space.nz=" + std::to_string(nz), "vents.count=" + std::to_string(seeds), "neighborhood=" + nb,
            "boundary=" + bc, "ca.maxSteps=65535"};
}

std::vector<std::string> mcFull(int nx, int ny, int nz, const std::string& nb, const std::string& bc, int mcs) {
    return {"mc.enabled=true", "mc.domain=full", "mc.update=checkerboard", "mc.mobilityFromCooling=false",
            "space.nx=" + std::to_string(nx), "space.ny=" + std::to_string(ny), "space.nz=" + std::to_string(nz),
            "neighborhood=" + nb, "boundary=" + bc, "mc.mcs=" + std::to_string(mcs), "mc.statsEvery=4", "mc.Q=12"};
}

// Granice pasów dla bieżącej liczby procesów: ostatnia warstwa pasu r i pierwsza pasu r + 1.
std::vector<int> stripBorders(int layers) {
    const std::vector<int> split = splitLayers(layers, worldSize());
    std::vector<int> out = {0, layers - 1};
    for (std::size_t r = 1; r + 1 < split.size(); ++r) {
        out.push_back(split[r] - 1);
        out.push_back(split[r]);
    }
    return out;
}

}  // namespace

TEST_CASE("MPI: lawa 2D — automat frontalny i pełny przebieg") {
    checkCa(Config::load("", kLava2D));
    checkCa(Config::load("", with(kLava2D, {"ca.sweep=full"})));
    checkCa(Config::load("", with(kLava2D, {"ca.ponding=false", "neighborhood=von_neumann"})));
}

TEST_CASE("MPI: lawa 3D — front, full, sąsiedztwa, brzegi, ponding") {
    checkCa(Config::load("", kLava3D));
    checkCa(Config::load("", with(kLava3D, {"ca.sweep=full"})));
    checkCa(Config::load("", with(kLava3D, {"boundary=periodic"})));
    checkCa(Config::load("", with(kLava3D, {"neighborhood=von_neumann", "ca.ponding=false"})));
    checkCa(Config::load("", with(kLava3D, {"neighborhood=pentagonal", "ca.sweep=full"})));
    checkCa(Config::load("", with(kLava3D, {"neighborhood=pentagonal"})));
}

TEST_CASE("MPI: kratery na granicach pasów i przy brzegu globalnym") {
    const Config c = Config::load("", with(kLava3D, {"vents.eruptionSteps=30"}));
    std::vector<Vent> vents;
    int id = 1;
    for (const int z : stripBorders(c.space.nz)) {
        vents.push_back(Vent{(7 * id) % c.space.nx, (11 * id) % c.space.ny, z, id});
        ++id;
    }
    vents.push_back(Vent{0, 0, 0, id++});                                            // narożnik dna
    vents.push_back(Vent{c.space.nx - 1, c.space.ny - 1, c.space.nz - 1, id++});     // narożnik sufitu
    checkCa(c, &vents);
    checkCa(Config::load("", with(kLava3D, {"vents.eruptionSteps=30", "ca.sweep=full"})), &vents);
    // Classic: zarodki na granicach pasów, brzeg periodyczny (pierścień) i absorbujący.
    for (const std::string bc : {"periodic", "absorbing"}) {
        CAPTURE(bc);
        const Config k = Config::load("", classic(14, 13, 16, 1, "moore", bc));
        std::vector<Vent> seeds;
        int s = 1;
        for (const int z : stripBorders(k.space.nz)) {
            seeds.push_back(Vent{(3 * s) % k.space.nx, (5 * s) % k.space.ny, z, s});
            ++s;
        }
        checkCa(k, &seeds);
        checkCa(Config::load("", with(classic(14, 13, 16, 1, "moore", bc), {"ca.sweep=full"})), &seeds);
    }
}

TEST_CASE("MPI: classic 3D i płaszczyzna x–y — sąsiedztwa, brzegi") {
    for (const std::string bc : {"periodic", "absorbing"}) {
        CAPTURE(bc);
        checkCa(Config::load("", classic(16, 15, 17, 25, "von_neumann", bc)));
        checkCa(Config::load("", classic(16, 15, 17, 25, "moore", bc)));
        checkCa(Config::load("", classic(16, 15, 17, 25, "pentagonal", bc)));
        checkCa(Config::load("", with(classic(16, 15, 17, 25, "von_neumann", bc), {"ca.sweep=full"})));
        // płaszczyzna x–y: pasy w osi y
        checkCa(Config::load("", classic(37, 41, 1, 30, "von_neumann", bc)));
        checkCa(Config::load("", classic(37, 41, 1, 30, "hexagonal", bc)));
        checkCa(Config::load("", with(classic(37, 41, 1, 30, "moore", bc), {"ca.sweep=full"})));
    }
}

TEST_CASE("MPI: mpi.exchange = changed daje ten sam wynik") {
    checkCa(Config::load("", with(kLava3D, {"mpi.exchange=changed"})));
    checkCa(Config::load("", with(kLava3D, {"mpi.exchange=changed", "ca.sweep=full"})));
    checkCa(Config::load("", with(classic(16, 15, 17, 25, "moore", "periodic"), {"mpi.exchange=changed"})));
    checkCa(Config::load("", with(classic(16, 15, 17, 25, "von_neumann", "periodic"),
                                  {"mpi.exchange=changed", "ca.sweep=full"})));
    checkMc(Config::load("", with(mcFull(24, 20, 9, "moore", "periodic", 9), {"mpi.exchange=changed"})), nullptr,
            nullptr);
}

TEST_CASE("MPI: MC szachownica na całej przestrzeni") {
    checkMc(Config::load("", mcFull(40, 36, 1, "von_neumann", "periodic", 12)), nullptr, nullptr);
    checkMc(Config::load("", mcFull(40, 36, 1, "moore", "absorbing", 12)), nullptr, nullptr);
    checkMc(Config::load("", with(mcFull(41, 37, 1, "hexagonal", "periodic", 10), {"mc.kT=0.4"})), nullptr, nullptr);
    checkMc(Config::load("", mcFull(14, 12, 16, "moore", "periodic", 8)), nullptr, nullptr);
    checkMc(Config::load("", mcFull(15, 13, 17, "von_neumann", "periodic", 8)), nullptr, nullptr);  // osie nieparzyste
    checkMc(Config::load("", with(mcFull(13, 13, 11, "pentagonal", "absorbing", 8), {"mc.kT=0.3"})), nullptr,
            nullptr);
}

TEST_CASE("MPI: lawa + MC szachownica na bazalcie z mobilnością") {
    const std::vector<std::string> mc = {"mc.enabled=true", "mc.update=checkerboard", "mc.mcs=12",
                                         "mc.statsEvery=5", "mc.Q=20"};
    for (const auto& base : {kLava3D, kLava2D}) {
        const Config c = Config::load("", with(base, mc));
        const MpiCaRun r = checkCa(c);
        const SeqCa ref = runSeqCa(c, nullptr);
        checkMc(c, &ref.result, &r.slab);
    }
    const Config noMob = Config::load("", with(kLava3D, with(mc, {"mc.mobilityFromCooling=false"})));
    const MpiCaRun r = checkCa(noMob);
    const SeqCa ref = runSeqCa(noMob, nullptr);
    checkMc(noMob, &ref.result, &r.slab);
}

TEST_CASE("MPI: tryb hybrydowy — procesy × 4 wątki OpenMP") {
    if (worldSize() * 4 > 8) {
        return;  // tryb oszczędny: razem najwyżej 8 procesów × wątków
    }
    const std::vector<std::string> t4 = {"parallel.threads=4", "parallel.schedule=dynamic"};
    checkCa(Config::load("", with(kLava3D, t4)));
    checkCa(Config::load("", with(kLava3D, with(t4, {"ca.sweep=full"}))));
    checkCa(Config::load("", with(classic(16, 15, 17, 25, "moore", "periodic"), t4)));
    checkMc(Config::load("", with(mcFull(14, 12, 16, "moore", "periodic", 8), t4)), nullptr, nullptr);
    checkMc(Config::load("", with(mcFull(40, 36, 1, "von_neumann", "periodic", 8), t4)), nullptr, nullptr);
}

TEST_CASE("MPI: mc.update = random przy jednym procesie; nieobsługiwane kombinacje") {
    if (worldSize() == 1) {
        checkMc(Config::load("", {"mc.enabled=true", "mc.domain=full", "space.nx=30", "space.ny=30", "space.nz=1",
                                  "mc.mcs=6", "mc.mobilityFromCooling=false", "boundary=periodic"}),
                nullptr, nullptr);
    }
    const int p = worldSize();
    if (p > 1) {
        CHECK_THROWS_AS(MpiSimulation::checkConfig(Config::load("", {"mc.enabled=true"}), p), ConfigError);
    }
    CHECK_THROWS_AS(MpiSimulation::checkConfig(Config::load("", {"grid=matrix"}), p), ConfigError);
    CHECK_THROWS_AS(MpiSimulation::checkConfig(Config::load("", {"space.nz=3"}), 4), ConfigError);
    CHECK_NOTHROW(MpiSimulation::checkConfig(Config::load("", {"mc.enabled=true", "mc.update=checkerboard"}), p));
}
