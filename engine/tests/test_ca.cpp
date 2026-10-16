// Testy automatu: classic wypełnia przestrzeń, zgodność vector/macierz, determinizm,
// lawa nie wchodzi w skałę i nie wspina się, warunki brzegowe w trybie lava.
#include "doctest.h"

#include <cstring>
#include <set>
#include <string>
#include <vector>

#include "app/Simulation.hpp"
#include "ca/LavaCA.hpp"
#include "core/Storage.hpp"
#include "io/Config.hpp"

using namespace volcano;

namespace {

// Wynik przebiegu: mikrostruktura + liczba kroków + kratery.
struct Outcome {
    Microstructure m;
    int steps = 0;
    StopReason stop = StopReason::Running;
    std::vector<Vent> vents;
};

// Config z wartości domyślnych + nadpisania (jak --set).
Config cfgOf(const std::vector<std::string>& overrides) { return Config::load("", overrides); }

// Pełny przebieg automatu na wybranej reprezentacji siatki.
template <class S>
Outcome simulate(const Config& c) {
    const Heightmap hm = Simulation::buildTerrain(c);
    Outcome o;
    o.vents = Simulation::buildVents(c, hm);
    LavaCA<S> ca(c.space, Simulation::caParams(c), Neighborhood(c.neighborhood, c.space),
                 Boundary(c.boundary, c.ca.mode));
    if (!hm.empty()) {
        ca.applyTerrain(hm);
    }
    ca.placeSeeds(o.vents);
    ca.run();
    o.m = ca.result();
    o.steps = ca.steps();
    o.stop = ca.stopReason();
    return o;
}

// Zgodność bitowa wszystkich pól (łącznie z solidStep i arrivalStep — wejściem MC).
bool identical(const Microstructure& a, const Microstructure& b) {
    return a.dims == b.dims && a.type == b.type && a.flowId == b.flowId && a.solidStep == b.solidStep &&
           a.arrivalStep == b.arrivalStep &&
           std::memcmp(a.temp.data(), b.temp.data(), a.temp.size() * sizeof(float)) == 0;
}

std::size_t countType(const Microstructure& m, CellType t) {
    std::size_t n = 0;
    for (CellType c : m.type) {
        n += (c == t) ? 1 : 0;
    }
    return n;
}

// Mały 2D i 3D przypadek lawy (szybkie testy).
const std::vector<std::string> kLava2D = {"space.nx=120", "space.nz=70", "terrain.peakHeight=45",
                                          "terrain.baseRadius=55", "ca.coolingAmbient=1",
                                          "ca.coolingLateral=3", "ca.coolingFall=1", "vents.eruptionSteps=100"};
const std::vector<std::string> kLava3D = {"space.nx=40", "space.ny=40", "space.nz=30", "terrain.peakHeight=22",
                                          "terrain.baseRadius=20", "terrain.craterRadius=4",
                                          "terrain.craterDepth=2", "vents.count=3", "ca.coolingAmbient=2",
                                          "ca.coolingLateral=4", "ca.coolingFall=2", "vents.eruptionSteps=60"};

std::vector<std::string> with(std::vector<std::string> base, const std::vector<std::string>& extra) {
    base.insert(base.end(), extra.begin(), extra.end());
    return base;
}

}  // namespace

TEST_CASE("Classic: rozrost wypełnia całą przestrzeń, każde ziarno ma >= 1 komórkę") {
    const char* nbs[] = {"von_neumann", "moore", "pentagonal", "hexagonal"};
    const char* bcs[] = {"absorbing", "periodic"};
    const char* spaces[][3] = {{"30", "20", "1"}, {"12", "10", "8"}};  // 2D (x–y) i 3D
    for (const auto& sp : spaces) {
        for (const char* nb : nbs) {
            const bool is3D = std::string(sp[2]) != "1";
            if (is3D && std::string(nb) == "hexagonal") {
                continue;  // heksagonalne tylko w 2D
            }
            for (const char* bc : bcs) {
                CAPTURE(nb);
                CAPTURE(bc);
                CAPTURE(sp[2]);
                const Config c = cfgOf({"ca.mode=classic", std::string("neighborhood=") + nb,
                                        std::string("boundary=") + bc, std::string("space.nx=") + sp[0],
                                        std::string("space.ny=") + sp[1], std::string("space.nz=") + sp[2],
                                        "vents.count=7", "ca.maxSteps=10000"});
                const Outcome o = simulate<VectorStorage>(c);
                CHECK(o.stop == StopReason::NoAir);
                CHECK(countType(o.m, CellType::Air) == 0);
                std::vector<int> size(8, 0);
                for (std::int32_t f : o.m.flowId) {
                    REQUIRE(f >= 1);
                    REQUIRE(f <= 7);
                    ++size[static_cast<std::size_t>(f)];
                }
                for (int f = 1; f <= 7; ++f) {
                    CHECK(size[static_cast<std::size_t>(f)] >= 1);
                }
            }
        }
    }
}

TEST_CASE("Classic: liczba kroków jak w rozroście von Neumanna (promień rośnie o 1 na krok)") {
    // Jeden zarodek, brzeg periodyczny, 2D 21x21: najdalsza komórka w metryce taksówkowej
    // jest w odległości 20 (10 + 10) -> dokładnie 20 kroków.
    const Config c = cfgOf({"ca.mode=classic", "neighborhood=von_neumann", "boundary=periodic", "space.nx=21",
                            "space.ny=21", "space.nz=1", "vents.count=1"});
    CHECK(simulate<VectorStorage>(c).steps == 20);
}

TEST_CASE("VectorStorage i MatrixStorage dają identyczny wynik") {
    const std::vector<std::vector<std::string>> cases = {
        kLava2D,
        kLava3D,
        with(kLava2D, {"neighborhood=pentagonal", "boundary=periodic"}),
        with(kLava2D, {"neighborhood=hexagonal", "vents.count=3"}),
        with(kLava3D, {"neighborhood=von_neumann", "boundary=periodic", "vents.placement=random"}),
        {"ca.mode=classic", "neighborhood=moore", "boundary=periodic", "space.nx=20", "space.ny=20",
         "space.nz=20", "vents.count=30"},
        {"ca.mode=classic", "neighborhood=pentagonal", "boundary=absorbing", "space.nx=20", "space.ny=15",
         "space.nz=10", "vents.count=12"},
    };
    for (const auto& overrides : cases) {
        CAPTURE(overrides.front());
        CAPTURE(overrides.size());
        const Config c = cfgOf(overrides);
        const Outcome v = simulate<VectorStorage>(c);
        const Outcome m = simulate<MatrixStorage>(c);
        CHECK(v.steps == m.steps);
        CHECK(v.steps > 1);
        CHECK(identical(v.m, m.m));
    }
}

TEST_CASE("Ten sam seed -> identyczny wynik, inny seed -> inny") {
    for (const auto& base : {kLava2D, kLava3D}) {
        const Outcome a = simulate<VectorStorage>(cfgOf(with(base, {"rngSeed=1"})));
        const Outcome b = simulate<VectorStorage>(cfgOf(with(base, {"rngSeed=1"})));
        const Outcome c = simulate<VectorStorage>(cfgOf(with(base, {"rngSeed=2"})));
        CHECK(identical(a.m, b.m));
        CHECK_FALSE(identical(a.m, c.m));
    }
    const std::vector<std::string> classic = {"ca.mode=classic", "space.nx=30", "space.ny=30", "space.nz=1",
                                              "vents.count=10"};
    CHECK(identical(simulate<VectorStorage>(cfgOf(with(classic, {"rngSeed=5"}))).m,
                    simulate<VectorStorage>(cfgOf(with(classic, {"rngSeed=5"}))).m));
    CHECK_FALSE(identical(simulate<VectorStorage>(cfgOf(with(classic, {"rngSeed=5"}))).m,
                          simulate<VectorStorage>(cfgOf(with(classic, {"rngSeed=6"}))).m));
}

TEST_CASE("Lawa nie wchodzi w skałę: każda komórka ROCK terenu zostaje ROCK") {
    for (const auto& base : {kLava2D, kLava3D}) {
        const Config c = cfgOf(base);
        const Heightmap hm = Simulation::buildTerrain(c);
        const Outcome o = simulate<VectorStorage>(c);
        std::size_t rock = 0;
        for (int y = 0; y < c.space.ny; ++y) {
            for (int x = 0; x < c.space.nx; ++x) {
                for (int z = 0; z < c.space.nz; ++z) {
                    const bool isTerrain = z < hm.at(x, y);
                    CHECK((o.m.type[o.m.index(x, y, z)] == CellType::Rock) == isTerrain);
                    rock += isTerrain ? 1 : 0;
                }
            }
        }
        CHECK(countType(o.m, CellType::Rock) == rock);
        CHECK(countType(o.m, CellType::Basalt) > 0);  // lawa w ogóle popłynęła i zastygła
    }
}

TEST_CASE("Lawa nie wspina się: bez wypełniania zagłębień nie wychodzi ponad poziom krateru") {
    for (const auto& base : {kLava2D, kLava3D}) {
        const Config c = cfgOf(with(base, {"ca.ponding=false"}));
        const Outcome o = simulate<VectorStorage>(c);
        int ventLevel = 0;
        for (const Vent& v : o.vents) {
            ventLevel = std::max(ventLevel, v.z);
        }
        for (std::size_t i = 0; i < o.m.type.size(); ++i) {
            if (o.m.type[i] == CellType::Lava || o.m.type[i] == CellType::Basalt) {
                const int z = static_cast<int>(i / (static_cast<std::size_t>(c.space.nx) * c.space.ny));
                CHECK(z <= ventLevel);
            }
        }
    }
}

TEST_CASE("Wypełnianie zagłębień: bez niego lawa zostaje w kraterze, z nim wypływa na zbocze") {
    const Config off = cfgOf(with(kLava2D, {"ca.ponding=false", "terrain.noise=0"}));
    const Config on = cfgOf(with(kLava2D, {"ca.ponding=true", "terrain.noise=0"}));
    const Outcome a = simulate<VectorStorage>(off);
    const Outcome b = simulate<VectorStorage>(on);
    const double craterRadius = off.terrain.craterRadius;
    double reachOff = 0.0;
    double reachOn = 0.0;
    for (int x = 0; x < off.space.nx; ++x) {
        for (int z = 0; z < off.space.nz; ++z) {
            const std::size_t i = a.m.index(x, 0, z);
            const double r = std::abs(x - a.vents[0].x);
            if (a.m.type[i] == CellType::Basalt) reachOff = std::max(reachOff, r);
            if (b.m.type[i] == CellType::Basalt) reachOn = std::max(reachOn, r);
        }
    }
    CHECK(reachOff <= 2 * craterRadius);
    CHECK(reachOn > 3 * craterRadius);
}

TEST_CASE("Na płaskim terenie lawa tworzy jedną warstwę (brak „piramid”)") {
    // Ręcznie zbudowany płaski teren (wysokość 3) i krater na środku.
    const Dims d{60, 1, 20};
    Heightmap hm;
    hm.nx = d.nx;
    hm.ny = d.ny;
    hm.height.assign(static_cast<std::size_t>(d.nx), 3);
    CaParams p;
    p.coolingLateral = 5.0f;
    p.eruptionSteps = 50;
    LavaCA<VectorStorage> ca(d, p, Neighborhood(NeighborhoodKind::Moore, d),
                             Boundary(BoundaryKind::Absorbing, CaMode::Lava));
    ca.applyTerrain(hm);
    ca.placeSeeds({Vent{30, 0, 3, 1}});
    ca.run();
    const Microstructure m = ca.result();
    int maxZ = 0;
    int width = 0;
    for (int x = 0; x < d.nx; ++x) {
        for (int z = 0; z < d.nz; ++z) {
            if (m.type[m.index(x, 0, z)] == CellType::Basalt) {
                maxZ = std::max(maxZ, z);
                width += (z == 3) ? 1 : 0;
            }
        }
    }
    CHECK(maxZ == 3);
    CHECK(width > 20);  // rozlała się na boki
}

TEST_CASE("Brzeg w trybie lava: periodyczny zawija w poziomie, absorbujący nie") {
    // Płaski teren, krater przy lewej krawędzi. Lawa rozlewa się na ~6 komórek.
    const Dims d{40, 1, 10};
    Heightmap hm;
    hm.nx = d.nx;
    hm.ny = d.ny;
    hm.height.assign(static_cast<std::size_t>(d.nx), 2);
    CaParams p;
    p.coolingLateral = 60.0f;
    p.coolingAmbient = 1.0f;
    p.eruptionSteps = 20;
    auto lavaAtRightEdge = [&](BoundaryKind bk) {
        LavaCA<VectorStorage> ca(d, p, Neighborhood(NeighborhoodKind::Moore, d), Boundary(bk, CaMode::Lava));
        ca.applyTerrain(hm);
        ca.placeSeeds({Vent{1, 0, 2, 1}});
        ca.run();
        const Microstructure m = ca.result();
        return m.type[m.index(d.nx - 1, 0, 2)] == CellType::Basalt;
    };
    CHECK(lavaAtRightEdge(BoundaryKind::Periodic));
    CHECK_FALSE(lavaAtRightEdge(BoundaryKind::Absorbing));
}

TEST_CASE("arrivalStep: krater 0, lawa ma arrivalStep <= solidStep, czas płynięcia rośnie przy kraterze") {
    const Config c = cfgOf(kLava2D);
    const Outcome o = simulate<VectorStorage>(c);
    const std::size_t vent = o.m.index(o.vents[0].x, o.vents[0].y, o.vents[0].z);
    CHECK(o.m.arrivalStep[vent] == 0);
    std::size_t lava = 0;
    std::size_t positive = 0;
    for (std::size_t i = 0; i < o.m.type.size(); ++i) {
        const CellType t = o.m.type[i];
        if (t == CellType::Basalt) {
            CHECK(o.m.arrivalStep[i] <= o.m.solidStep[i]);
            ++lava;
            positive += (o.m.arrivalStep[i] > 0) ? 1 : 0;
        } else if (t == CellType::Air || t == CellType::Rock) {
            CHECK(o.m.arrivalStep[i] == 0);
            CHECK(o.m.solidStep[i] == 0);
        }
    }
    CHECK(lava > 10);
    CHECK(positive > lava / 2);  // arrivalStep = 0 mają tylko krater i komórki zalane w kroku 0
    // Krater był płynny najdłużej (eruptionSteps + stygnięcie).
    const int ventTime = o.m.solidStep[vent] - o.m.arrivalStep[vent];
    for (std::size_t i = 0; i < o.m.type.size(); ++i) {
        if (o.m.type[i] == CellType::Basalt) {
            CHECK(o.m.solidStep[i] - o.m.arrivalStep[i] <= ventTime);
        }
    }
}

TEST_CASE("Lava: kraterem są komórki z flowId i limit kroków działa") {
    const Config c = cfgOf(with(kLava2D, {"ca.maxSteps=10"}));
    const Outcome o = simulate<VectorStorage>(c);
    CHECK(o.steps == 10);
    CHECK(o.stop == StopReason::MaxSteps);
    const std::size_t vent = o.m.index(o.vents[0].x, o.vents[0].y, o.vents[0].z);
    CHECK(o.m.type[vent] == CellType::Lava);
    CHECK(o.m.temp[vent] == 1200.0f);  // w trakcie erupcji krater ma stałą temperaturę
    CHECK(o.m.flowId[vent] == 1);
}
