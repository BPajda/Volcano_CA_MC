// Automat frontalny (etap 8, ca.sweep = front) vs pełny przebieg (ca.sweep = full): bitowo ten sam wynik,
// ta sama liczba kroków, powód zakończenia i historia liczników (activeCells / changedCells w stats.json)
// na wielu configach: lawa 2D/3D, classic 2D/3D, wszystkie sąsiedztwa (także losowe), brzeg periodyczny
// i absorbujący, wypełnianie zagłębień, limit kroków, obie reprezentacje siatki i ścieżka --timing-detail.
#include "doctest.h"

#include <cstring>
#include <string>
#include <vector>

#include "app/Simulation.hpp"
#include "ca/LavaCA.hpp"
#include "core/Storage.hpp"
#include "io/Config.hpp"

using namespace volcano;

namespace {

// Wszystko, co automat oddaje na zewnątrz (wynik + liczniki do stats.json).
struct Run {
    Microstructure m;
    int steps = 0;
    StopReason stop = StopReason::Running;
    std::vector<std::uint64_t> active;
    std::vector<std::uint64_t> changed;
    bool front = false;
};

template <class S>
Run simulate(const Config& c, bool timed = false) {
    const Heightmap hm = Simulation::buildTerrain(c);
    LavaCA<S> ca(c.space, Simulation::caParams(c), Neighborhood(c.neighborhood, c.space),
                 Boundary(c.boundary, c.ca.mode));
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
    r.front = ca.frontSweep();
    return r;
}

bool identical(const Microstructure& a, const Microstructure& b) {
    return a.dims == b.dims && a.type == b.type && a.flowId == b.flowId && a.solidStep == b.solidStep &&
           a.arrivalStep == b.arrivalStep &&
           std::memcmp(a.temp.data(), b.temp.data(), a.temp.size() * sizeof(float)) == 0;
}

std::vector<std::string> with(std::vector<std::string> base, const std::vector<std::string>& extra) {
    base.insert(base.end(), extra.begin(), extra.end());
    return base;
}

// Porównanie front vs full dla jednego configu (oba w tej samej reprezentacji siatki).
template <class S>
void checkSame(const std::vector<std::string>& overrides) {
    CAPTURE(S::kName);
    const Run full = simulate<S>(Config::load("", with(overrides, {"ca.sweep=full"})));
    const Run front = simulate<S>(Config::load("", with(overrides, {"ca.sweep=front"})));
    REQUIRE_FALSE(full.front);
    REQUIRE(front.front);
    CHECK(full.steps > 1);
    CHECK(front.steps == full.steps);
    CHECK(front.stop == full.stop);
    CHECK(front.active == full.active);
    CHECK(front.changed == full.changed);
    CHECK(identical(front.m, full.m));
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

}  // namespace

TEST_CASE("Front = full: domyślnie ca.sweep = front") {
    CHECK(Simulation::caParams(Config::load("", {})).frontSweep);
    CHECK_FALSE(Simulation::caParams(Config::load("", {"ca.sweep=full"})).frontSweep);
    CHECK_THROWS_AS(Config::load("", {"ca.sweep=fast"}), ConfigError);
}

TEST_CASE_TEMPLATE("Front = full: lawa 2D (przekrój x–z), sąsiedztwa i brzegi", S, VectorStorage, MatrixStorage) {
    for (const char* nb : {"moore", "von_neumann", "pentagonal", "hexagonal"}) {
        for (const char* bc : {"absorbing", "periodic"}) {
            CAPTURE(nb);
            CAPTURE(bc);
            checkSame<S>(with(kLava2D, {std::string("neighborhood=") + nb, std::string("boundary=") + bc}));
        }
    }
}

TEST_CASE("Front = full: lawa 3D, sąsiedztwa, brzegi, wypełnianie zagłębień, limit kroków") {
    for (const char* nb : {"moore", "von_neumann", "pentagonal"}) {
        for (const char* bc : {"absorbing", "periodic"}) {
            CAPTURE(nb);
            CAPTURE(bc);
            checkSame<VectorStorage>(with(kLava3D, {std::string("neighborhood=") + nb, std::string("boundary=") + bc}));
        }
    }
    checkSame<MatrixStorage>(with(kLava3D, {"boundary=periodic"}));
    checkSame<VectorStorage>(with(kLava3D, {"ca.ponding=false"}));                        // bez wypełniania zagłębień
    checkSame<VectorStorage>(with(kLava3D, {"vents.placement=random", "vents.count=6"}));  // kratery na zboczu
    checkSame<VectorStorage>(with(kLava2D, {"ca.maxSteps=17"}));                          // koniec: limit kroków
}

TEST_CASE("Front = full: lawa przechodząca przez brzeg periodyczny (krater przy krawędzi)") {
    // Płaski teren, krater przy lewej krawędzi — lawa przelewa się na prawą stronę przez ramkę periodyczną.
    for (const char* nb : {"moore", "von_neumann"}) {
        CAPTURE(nb);
        checkSame<VectorStorage>({"space.nx=40", "space.ny=30", "space.nz=12", "terrain.peakHeight=3",
                                  "terrain.baseRadius=1000", "terrain.craterRadius=0", "terrain.noise=0",
                                  "vents.placement=positions", "vents.count=2", "vents.positions=[[0,0],[39,15]]",
                                  "boundary=periodic", "ca.coolingLateral=4", "ca.coolingAmbient=1",
                                  "vents.eruptionSteps=30", std::string("neighborhood=") + nb});
    }
}

TEST_CASE_TEMPLATE("Front = full: classic 2D (x–y, x–z, y–z), sąsiedztwa i brzegi", S, VectorStorage, MatrixStorage) {
    for (const char* nb : {"von_neumann", "moore", "pentagonal", "hexagonal"}) {
        for (const char* bc : {"periodic", "absorbing"}) {
            CAPTURE(nb);
            CAPTURE(bc);
            checkSame<S>(classic(60, 45, 1, 12, nb, bc));  // płaszczyzna x–y: warstwy w osi y
        }
    }
    checkSame<S>(classic(50, 1, 40, 7, "moore", "periodic"));     // x–z
    checkSame<S>(classic(1, 50, 40, 7, "pentagonal", "periodic"));  // y–z: bez ramki w osi x
}

TEST_CASE("Front = full: classic 3D, sąsiedztwa i brzegi") {
    for (const char* nb : {"von_neumann", "moore", "pentagonal"}) {
        for (const char* bc : {"periodic", "absorbing"}) {
            CAPTURE(nb);
            CAPTURE(bc);
            checkSame<VectorStorage>(classic(22, 18, 15, 9, nb, bc));
        }
    }
    checkSame<MatrixStorage>(classic(22, 18, 15, 9, "moore", "periodic"));
    checkSame<VectorStorage>(classic(2, 9, 7, 3, "moore", "periodic"));  // oś o rozmiarze 2 (ramka = sąsiad)
}

TEST_CASE("Front = full: reguła „krok bez zmian kończy symulację” i pozostałe powody końca") {
    // Lawa bez stygnięcia w powietrzu (coolingAmbient = 0): po końcu erupcji i rozlaniu lawa stoi w miejscu —
    // krok bez zmian kończy symulację (sąsiedztwo deterministyczne), w tym samym kroku w obu trybach.
    for (const char* nb : {"moore", "von_neumann"}) {
        CAPTURE(nb);
        const std::vector<std::string> o =
            with(kLava2D, {"ca.coolingAmbient=0", "vents.eruptionSteps=40", std::string("neighborhood=") + nb});
        const Run full = simulate<VectorStorage>(Config::load("", with(o, {"ca.sweep=full"})));
        CHECK(full.stop == StopReason::NoChange);
        CHECK(full.changed.back() == 0);
        checkSame<VectorStorage>(o);
        checkSame<MatrixStorage>(o);
    }
    // Ta sama lawa przy sąsiedztwie losowym: krok bez zmian NIE kończy (koniec dopiero na limicie kroków).
    {
        const std::vector<std::string> o = with(kLava2D, {"ca.coolingAmbient=0", "vents.eruptionSteps=40",
                                                          "neighborhood=pentagonal", "ca.maxSteps=400"});
        const Run full = simulate<VectorStorage>(Config::load("", with(o, {"ca.sweep=full"})));
        CHECK(full.stop == StopReason::MaxSteps);
        checkSame<VectorStorage>(o);
    }
    // Koniec przez brak lawy (domyślny dla lawy) i przez brak wolnych komórek (classic).
    CHECK(simulate<VectorStorage>(Config::load("", kLava3D)).stop == StopReason::NoLava);
    CHECK(simulate<VectorStorage>(Config::load("", classic(30, 20, 1, 4, "moore", "absorbing"))).stop ==
          StopReason::NoAir);
}

TEST_CASE("Front: ścieżka --timing-detail daje ten sam wynik co zwykły krok") {
    for (const auto& o : {kLava3D, classic(40, 30, 1, 5, "pentagonal", "periodic")}) {
        const Config c = Config::load("", o);
        const Run plain = simulate<VectorStorage>(c);
        const Run timed = simulate<VectorStorage>(c, true);
        CHECK(plain.front);
        CHECK(timed.steps == plain.steps);
        CHECK(timed.active == plain.active);
        CHECK(timed.changed == plain.changed);
        CHECK(identical(timed.m, plain.m));
    }
}

TEST_CASE("Front: tylko jeden bufor siatki (next nie jest alokowany)") {
    const Config c = Config::load("", classic(10, 8, 6, 2, "moore", "periodic"));
    const Config f = Config::load("", with(classic(10, 8, 6, 2, "moore", "periodic"), {"ca.sweep=full"}));
    LavaCA<VectorStorage> front(c.space, Simulation::caParams(c), Neighborhood(c.neighborhood, c.space),
                                Boundary(c.boundary, c.ca.mode));
    LavaCA<VectorStorage> full(f.space, Simulation::caParams(f), Neighborhood(f.neighborhood, f.space),
                               Boundary(f.boundary, f.ca.mode));
    CHECK(full.gridBytes() == 2 * front.gridBytes());
    CHECK(front.auxBytes() == c.space.cells());  // znaczniki kandydatów: 1 B na komórkę
    CHECK(full.auxBytes() == 0);
}
