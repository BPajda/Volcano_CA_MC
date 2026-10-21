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
// Etap 11 (typy pochodne MPI i MPI-IO, na końcu pliku):
//   * wymiana warstw typami (mpi.pack = datatype) = pakowanie: te same przypadki, liczba komunikatów i bajtów;
//   * blok configu (MPI_Type_create_struct) i tablica kraterów / zarodków rozesłane przez proces 0 = to samo, co każdy
//     proces wyznacza sam;
//   * cały program (MpiSimulation::runFromCli w tym procesie testów) dla każdej kombinacji pack × bcast × io (+ changed)
//     daje pliki wyników bajt po bajcie takie jak engine (Simulation::run, Simulation::runMcFrom): lawa 2D / 3D front
//     i full, classic VN / Moore, brzeg periodyczny i absorbujący, MC szachownica 2D / 3D, lawa + MC na bazalcie,
//     --mc-from, migawki, liczba warstw niepodzielna przez liczbę procesów, tryb hybrydowy. Pliki w folderze
//     tymczasowym systemu (WSL: /tmp na ext4 — MPI-IO nie na dysku Windows).
#include "doctest.h"

#include <mpi.h>

#include <algorithm>
#include <chrono>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <sstream>
#include <string>
#include <vector>

#include "app/McStage.hpp"
#include "app/Simulation.hpp"
#include "ca/LavaCA.hpp"
#include "core/Storage.hpp"
#include "io/Config.hpp"
#include "mpi/MpiSimulation.hpp"
#include "mpi/MpiTypes.hpp"
#include "parallel/Strip.hpp"

using namespace volcano;
namespace fs = std::filesystem;

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

// ---------------------------------------------------------------------------
// Etap 11: typy pochodne MPI i równoległy zapis MPI-IO
// ---------------------------------------------------------------------------

namespace {

// Folder tymczasowy wspólny dla procesów: nazwę wybiera proces 0 i rozsyła (MPI_Bcast).
std::string sharedTempDir(const std::string& tag) {
    std::string path;
    if (isRoot()) {
        const auto stamp = std::chrono::steady_clock::now().time_since_epoch().count();
        const fs::path p = fs::temp_directory_path() / ("volcano_mpi_" + tag + "_" + std::to_string(stamp));
        fs::remove_all(p);
        fs::create_directories(p);
        path = p.string();
    }
    unsigned long long n = path.size();
    MPI_Bcast(&n, 1, MPI_UNSIGNED_LONG_LONG, 0, MPI_COMM_WORLD);
    path.resize(static_cast<std::size_t>(n));
    MPI_Bcast(&path[0], static_cast<int>(n), MPI_CHAR, 0, MPI_COMM_WORLD);
    return path;
}

// Program engine_mpi w tym procesie (MpiSimulation::runFromCli); konsola wyciszona (podsumowanie procesu 0).
void runMpi(const std::vector<std::string>& overrides, const fs::path& out, const fs::path& mcFrom = {}) {
    CliOptions opt;
    opt.overrides = overrides;
    opt.outDir = out.string();
    opt.mcFrom = mcFrom.empty() ? std::string() : mcFrom.string();
    std::ostringstream sink;
    std::streambuf* const cout = std::cout.rdbuf(sink.rdbuf());
    std::streambuf* const cerr = std::cerr.rdbuf(sink.rdbuf());
    int code = -1;
    try {
        const Timer t;
        code = MpiSimulation::runFromCli(opt, t);
    } catch (...) {
        std::cout.rdbuf(cout);
        std::cerr.rdbuf(cerr);
        throw;
    }
    std::cout.rdbuf(cout);
    std::cerr.rdbuf(cerr);
    CHECK(code == 0);
}

// Odniesienie: program engine (Simulation::run / runMcFrom) na procesie 0, ten sam config.
void runEngine(const std::vector<std::string>& overrides, const fs::path& out, const fs::path& mcFrom = {}) {
    if (isRoot()) {
        fs::create_directories(out);
        const Config c = Config::load("", overrides);
        TimingReport timing;
        if (mcFrom.empty()) {
            Simulation sim(c);
            sim.run(out.string(), timing);
        } else {
            Simulation::runMcFrom(c, mcFrom.string(), out.string(), timing);
        }
    }
    MPI_Barrier(MPI_COMM_WORLD);
}

std::string bytesOf(const fs::path& p) {
    std::ifstream in(p, std::ios::binary);
    return std::string(std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>());
}

// Różnice folderu wyników b względem a: wszystkie pliki (także migawki) bajt po bajcie, bez times.json
// i config_used.json; stats.json bez sekcji parallel (opis liczenia) i ścieżek wejścia --mc-from.
std::vector<std::string> diffDirs(const fs::path& a, const fs::path& b) {
    const auto list = [](const fs::path& root) {
        std::vector<std::string> out;
        for (const auto& e : fs::recursive_directory_iterator(root)) {
            const std::string name = e.path().filename().string();
            if (e.is_regular_file() && name != "times.json" && name != "config_used.json") {
                out.push_back(fs::relative(e.path(), root).generic_string());
            }
        }
        std::sort(out.begin(), out.end());
        return out;
    };
    const std::vector<std::string> fa = list(a);
    if (fa != list(b)) {
        return {"różne listy plików"};
    }
    std::vector<std::string> diffs;
    for (const std::string& f : fa) {
        std::string x = bytesOf(a / f);
        std::string y = bytesOf(b / f);
        if (f == "stats.json") {
            nlohmann::ordered_json ja = nlohmann::ordered_json::parse(x);
            nlohmann::ordered_json jb = nlohmann::ordered_json::parse(y);
            for (nlohmann::ordered_json* j : {&ja, &jb}) {
                j->erase("parallel");
                if (j->contains("source")) {
                    (*j)["source"].erase("folder");
                    (*j)["source"].erase("file");
                }
            }
            x = ja.dump();
            y = jb.dump();
        }
        if (x != y) {
            diffs.push_back(f);
        }
    }
    return diffs;
}

// Kombinacja wariantów etapu 11 (m = jak etap 10; d = pack datatype, s = bcast struct, i = io mpiio).
struct Combo {
    std::string name;
    std::vector<std::string> sets;
};

std::vector<Combo> combos() {
    std::vector<Combo> out;
    for (int mask = 0; mask < 8; ++mask) {
        Combo c{"m", {}};
        if ((mask & 1) != 0) {
            c.name += "d";
            c.sets.push_back("mpi.pack=datatype");
        }
        if ((mask & 2) != 0) {
            c.name += "s";
            c.sets.push_back("mpi.bcast=struct");
        }
        if ((mask & 4) != 0) {
            c.name += "i";
            c.sets.push_back("mpi.io=mpiio");
        }
        out.push_back(c);
    }
    out.push_back({"md_changed", {"mpi.pack=datatype", "mpi.exchange=changed"}});
    out.push_back({"mdsi_changed", {"mpi.pack=datatype", "mpi.bcast=struct", "mpi.io=mpiio", "mpi.exchange=changed"}});
    return out;
}

// Przypadek: engine (odniesienie) i engine_mpi w każdej kombinacji — pliki bajt po bajcie. mcFromRef / mcFromMpi —
// --mc-from (wynik CA odniesienia i wyniki CA MPI tej samej kombinacji). Zwraca foldery wyników MPI.
std::vector<fs::path> checkFiles(const fs::path& dir, const std::string& name, const std::vector<std::string>& base,
                                 const std::vector<Combo>& cs, const fs::path& mcFromRef = {},
                                 const std::vector<fs::path>* mcFromMpi = nullptr) {
    const fs::path ref = dir / (name + "__engine");
    runEngine(base, ref, mcFromRef);
    std::vector<fs::path> outs;
    for (std::size_t k = 0; k < cs.size(); ++k) {
        CAPTURE(name);
        CAPTURE(cs[k].name);
        const fs::path out = dir / (name + "__" + cs[k].name);
        runMpi(with(base, cs[k].sets), out, mcFromMpi != nullptr ? (*mcFromMpi)[k] : fs::path());
        std::vector<std::string> diffs;
        if (isRoot()) {
            diffs = diffDirs(ref, out);
            for (const std::string& d : diffs) {
                MESSAGE("różnica: " << d);
            }
        }
        CHECK(agreed(diffs.empty()));
        outs.push_back(out);
    }
    return outs;
}

bool sameVents(const std::vector<Vent>& a, const std::vector<Vent>& b) {
    if (a.size() != b.size()) {
        return false;
    }
    for (std::size_t i = 0; i < a.size(); ++i) {
        if (a[i].x != b[i].x || a[i].y != b[i].y || a[i].z != b[i].z || a[i].flowId != b[i].flowId) {
            return false;
        }
    }
    return true;
}

}  // namespace

TEST_CASE("MPI etap 11: wymiana typami pochodnymi (mpi.pack = datatype) = pakowanie do bufora") {
    const std::vector<std::vector<std::string>> cases = {
        kLava3D, with(kLava3D, {"ca.sweep=full"}), kLava2D, classic(16, 15, 17, 25, "moore", "periodic"),
        with(classic(37, 41, 1, 30, "von_neumann", "absorbing"), {"ca.sweep=full"})};
    for (const std::string exchange : {"always", "changed"}) {
        CAPTURE(exchange);
        for (const auto& base : cases) {
            const std::vector<std::string> b = with(base, {"mpi.exchange=" + exchange});
            const MpiCaRun manual = checkCa(Config::load("", b));
            const MpiCaRun typed = checkCa(Config::load("", with(b, {"mpi.pack=datatype"})));
            if (worldSize() > 1) {
                CHECK(typed.comm.typesBuilt > 0);
                CHECK(typed.comm.layersSent == manual.comm.layersSent);
                CHECK(typed.comm.layersSkipped == manual.comm.layersSkipped);
                if (exchange == "always") {
                    // ten sam komunikat do każdego sąsiada, dane bez bajtów flag (flaga = 1 B na warstwę)
                    CHECK(typed.comm.messages == manual.comm.messages);
                    CHECK(typed.comm.bytes + typed.comm.layersSent == manual.comm.bytes);
                } else {
                    // changed: flagi osobnym komunikatem — bajty te same, komunikatów więcej
                    CHECK(typed.comm.bytes == manual.comm.bytes);
                    CHECK(typed.comm.messages >= manual.comm.messages);
                }
            }
        }
    }
    for (const std::string exchange : {"always", "changed"}) {
        const std::vector<std::string> b = {"mpi.pack=datatype", "mpi.exchange=" + exchange};
        checkMc(Config::load("", with(mcFull(40, 36, 1, "von_neumann", "periodic", 8), b)), nullptr, nullptr);
        checkMc(Config::load("", with(mcFull(15, 13, 17, "moore", "periodic", 6), b)), nullptr, nullptr);
    }
    if (worldSize() * 4 <= 8) {
        const std::vector<std::string> t4 = {"parallel.threads=4", "parallel.schedule=dynamic", "mpi.pack=datatype"};
        checkCa(Config::load("", with(kLava3D, with(t4, {"ca.sweep=full"}))));
        checkMc(Config::load("", with(mcFull(14, 12, 16, "moore", "periodic", 6), t4)), nullptr, nullptr);
    }
}

TEST_CASE("MPI etap 11: blok configu i kratery / zarodki jako struktury (mpi.bcast = struct)") {
    const MpiType blockType = MpiTypes::configBlockType();
    const MpiType ventType = MpiTypes::ventType();
    MPI_Aint lb = 0;
    MPI_Aint extent = 0;
    MPI_Type_get_extent(blockType.get(), &lb, &extent);
    CHECK(extent == static_cast<MPI_Aint>(sizeof(ConfigBlock)));
    MPI_Type_get_extent(ventType.get(), &lb, &extent);
    CHECK(extent == static_cast<MPI_Aint>(sizeof(Vent)));  // tablica struktur: krok = sizeof

    // Blok procesu 0 po MPI_Bcast = blok z configu wczytanego lokalnie; blok -> Config -> blok bez zmian.
    const std::vector<std::vector<std::string>> configs = {
        {},
        with(kLava3D, {"mc.enabled=true", "mc.update=checkerboard", "mc.kT=0.25", "parallel.threads=3"}),
        with(classic(16, 15, 17, 25, "pentagonal", "periodic"), {"rngSeed=9007199254740993", "ca.sweep=full"}),
        with(mcFull(40, 36, 1, "hexagonal", "periodic", 8), {"output.format=both", "parallel.priority=high"}),
        {"mpi.exchange=changed", "mpi.pack=datatype", "mpi.bcast=struct", "mpi.io=mpiio", "terrain.type=cone",
         "vents.placement=random", "parallel.affinity=pcores", "parallel.schedule=guided", "parallel.chunk=3"}};
    for (const auto& ov : configs) {
        const Config local = Config::load("", ov);
        ConfigBlock sent;
        std::memset(&sent, 0, sizeof(sent));
        if (isRoot()) {
            sent = MpiTypes::toBlock(local, 2);
        }
        MPI_Bcast(&sent, 1, blockType.get(), 0, MPI_COMM_WORLD);
        const ConfigBlock mine = MpiTypes::toBlock(local, 2);
        CHECK(std::memcmp(&sent, &mine, sizeof(ConfigBlock)) == 0);
        const Config back = MpiTypes::fromBlock(sent);
        const ConfigBlock again = MpiTypes::toBlock(back, sent.cooling);
        CHECK(std::memcmp(&again, &sent, sizeof(ConfigBlock)) == 0);
        CHECK(back.space == local.space);
        CHECK(back.rngSeed == local.rngSeed);
        CHECK(back.ca.coolingAmbient == local.ca.coolingAmbient);
        CHECK(back.mc.kT == local.mc.kT);
        CHECK(back.highPriority() == local.highPriority());
        CHECK(back.mpiIoParallel() == local.mpiIoParallel());
    }

    // Kratery / zarodki rozesłane przez proces 0 = lista, którą każdy proces wyznacza sam (etap 10); wynik CA ten sam.
    const std::vector<std::vector<std::string>> ventCases = {
        kLava3D, kLava2D,
        with(kLava3D, {"vents.placement=positions", "vents.count=3", "vents.positions=[[4, 5], [15, 15], [25, 9]]"}),
        classic(16, 15, 17, 25, "von_neumann", "absorbing"), classic(37, 41, 1, 30, "moore", "periodic")};
    for (const auto& ov : ventCases) {
        const Config c = Config::load("", with(ov, {"mpi.bcast=struct"}));
        const MpiCaRun r = checkCa(c);
        CHECK(sameVents(r.vents, Simulation::buildVents(c, Simulation::buildTerrain(c))));
    }
}

TEST_CASE("MPI etap 11: pliki wyników — każda kombinacja pack × bcast × io = engine bajt po bajcie") {
    const fs::path dir = sharedTempDir("pliki");
    const std::vector<Combo> cs = combos();
    const std::vector<std::string> both = {"output.format=both"};
    checkFiles(dir, "lava2d", with(kLava2D, both), cs);
    checkFiles(dir, "lava3d_front", with(kLava3D, {"output.format=both", "output.snapshotsEvery=20"}), cs);
    checkFiles(dir, "lava3d_full", with(kLava3D, {"output.format=both", "ca.sweep=full"}), cs);
    checkFiles(dir, "classic_vn_periodic", with(classic(16, 15, 17, 25, "von_neumann", "periodic"), both), cs);
    checkFiles(dir, "classic_xy_moore", with(classic(37, 41, 1, 30, "moore", "absorbing"), both), cs);
    checkFiles(dir, "mc_2d",
               with(mcFull(40, 36, 1, "von_neumann", "periodic", 8), {"output.format=both", "mc.snapshotsEvery=4"}),
               cs);
    checkFiles(dir, "mc_3d", with(mcFull(14, 12, 16, "moore", "periodic", 6), both), cs);
    // Lawa + MC na bazalcie, potem --mc-from na jej wyniku (MPI-IO: każdy proces czyta swój pas ca_result.bin).
    const std::vector<fs::path> caOuts =
        checkFiles(dir, "lava_mc",
                   with(kLava3D, {"output.format=both", "mc.enabled=true", "mc.update=checkerboard", "mc.mcs=8",
                                  "mc.statsEvery=4", "mc.Q=20"}),
                   cs);
    checkFiles(dir, "mc_from",
               {"output.format=both", "mc.enabled=true", "mc.update=checkerboard", "mc.mcs=6", "mc.statsEvery=3",
                "mc.Q=15"},
               cs, dir / "lava_mc__engine", &caOuts);
    if (worldSize() * 4 <= 8) {
        const std::vector<Combo> two = {cs.front(), cs[7]};  // jak etap 10 i wszystkie trzy nowe ścieżki
        checkFiles(dir, "hybrid_lava",
                   with(kLava3D, {"output.format=both", "parallel.threads=4", "parallel.schedule=dynamic"}), two);
        checkFiles(dir, "hybrid_mc",
                   with(mcFull(14, 12, 16, "moore", "periodic", 6), {"output.format=both", "parallel.threads=4"}),
                   two);
    }
    MPI_Barrier(MPI_COMM_WORLD);
    if (isRoot()) {
        fs::remove_all(dir);
    }
}
