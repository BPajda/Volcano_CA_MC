// Testy etapu 6: kratery w zadanych kolumnach (vents.placement = positions), zgodność bitowa starych
// configów oraz odtwarzanie erupcji krok po kroku z arrivalStep / solidStep wyniku końcowego —
// porównanie z prawdziwym stanem automatu po k krokach i z migawkami silnika (output.snapshotsEvery).
// Ta sama reguła odtwarzania jest w gui/replay.py i gui/static/js/replay.js (opis: docs/architektura.md).
#include "doctest.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <set>
#include <string>
#include <vector>

#include "app/Simulation.hpp"
#include "ca/LavaCA.hpp"
#include "core/Storage.hpp"
#include "io/Config.hpp"
#include "io/ResultReader.hpp"
#include "io/TimingReport.hpp"

using namespace volcano;

namespace {

Config cfgOf(const std::vector<std::string>& overrides) { return Config::load("", overrides); }

std::vector<std::string> with(std::vector<std::string> base, const std::vector<std::string>& extra) {
    base.insert(base.end(), extra.begin(), extra.end());
    return base;
}

// Mały wulkan 3D z kilkoma kraterami (szybki także w Debug) i przekrój 2D.
const std::vector<std::string> kSmall3D = {"space.nx=36", "space.ny=36", "space.nz=28", "terrain.peakHeight=20",
                                           "terrain.baseRadius=18", "terrain.craterRadius=4",
                                           "terrain.craterDepth=2", "vents.count=3", "ca.coolingAmbient=2",
                                           "ca.coolingLateral=4", "ca.coolingFall=2", "vents.eruptionSteps=40"};
const std::vector<std::string> kSmall2D = {"space.nx=100", "space.nz=50", "terrain.peakHeight=35",
                                           "terrain.baseRadius=45", "terrain.craterRadius=8",
                                           "terrain.craterDepth=4", "ca.coolingAmbient=2", "ca.coolingLateral=8",
                                           "ca.coolingFall=5", "vents.eruptionSteps=60"};

// Pusty folder tymczasowy na wyniki testu.
std::filesystem::path tempDir(const std::string& name) {
    const auto dir = std::filesystem::temp_directory_path() / "volcano_tests" / name;
    std::filesystem::remove_all(dir);
    std::filesystem::create_directories(dir);
    return dir;
}

std::string readBytes(const std::filesystem::path& p) {
    std::ifstream in(p, std::ios::binary);
    return std::string(std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>());
}

// Czy times.json przebiegu ma sekcję czasu o tej nazwie.
bool hasSection(const TimingReport& t, const std::string& name) {
    const auto& s = t.sections();
    return std::any_of(s.begin(), s.end(), [&](const auto& e) { return e.first == name; });
}

// Stan komórki po k krokach odtworzony z wyniku końcowego:
//   skała -> skała; komórka, która nigdy nie była lawą (na końcu AIR) -> powietrze;
//   krater pojawia się w stanie 0, pozostała lawa w stanie arrivalStep + 1 (arrivalStep = numer kroku,
//   w którym komórka stała się lawą, a wynik kroku t to stan t + 1);
//   bazalt od stanu solidStep + 1; wcześniej płynna lawa.
CellType replayType(const Microstructure& fin, std::size_t i, bool vent, int k) {
    const CellType t = fin.type[i];
    if (t == CellType::Rock || t == CellType::Air) {
        return t;
    }
    const int appear = vent ? 0 : fin.arrivalStep[i] + 1;
    if (k < appear) {
        return CellType::Air;
    }
    if (t == CellType::Basalt && k >= fin.solidStep[i] + 1) {
        return CellType::Basalt;
    }
    return CellType::Lava;
}

// Temperatura płynnej lawy w stanie k: po przybyciu lawa traci dokładnie coolingAmbient na krok
// (krater w trakcie erupcji ma stałe eruptTemp), więc liczymy wstecz od temperatury końcowej:
// bazalt (zastygł w kroku s): T_k = T_końc + c·(s + 1 − k); lawa płynna na końcu: T_k = T_końc + c·(steps − k);
// górne ograniczenie eruptTemp obsługuje krater w trakcie erupcji.
double replayTemp(const Microstructure& fin, std::size_t i, int k, int steps, const CaParams& p) {
    const double c = p.coolingAmbient;
    const int end = fin.type[i] == CellType::Basalt ? fin.solidStep[i] + 1 : steps;
    return std::min<double>(p.eruptTemp, fin.temp[i] + c * (end - k));
}

// Przebieg automatu z zapisem stanu po każdym kroku; porównuje odtworzenie z prawdziwym stanem.
template <class S>
void checkReplay(const Config& c) {
    const Heightmap hm = Simulation::buildTerrain(c);
    const std::vector<Vent> vents = Simulation::buildVents(c, hm);
    const CaParams params = Simulation::caParams(c);
    LavaCA<S> ca(c.space, params, Neighborhood(c.neighborhood, c.space), Boundary(c.boundary, c.ca.mode));
    if (!hm.empty()) {
        ca.applyTerrain(hm);
    }
    ca.placeSeeds(vents);
    std::vector<Microstructure> states{ca.result()};  // stan 0 (same kratery na terenie)
    while (!ca.finished()) {
        ca.step();
        states.push_back(ca.result());  // stan k = po k krokach
    }
    const int steps = ca.steps();
    REQUIRE(states.size() == static_cast<std::size_t>(steps) + 1);
    REQUIRE(steps > 5);
    const Microstructure& fin = states.back();

    std::vector<char> isVent(fin.type.size(), 0);
    for (const Vent& v : vents) {
        isVent[fin.index(v.x, v.y, v.z)] = 1;
    }
    std::size_t typeErrors = 0;
    std::size_t flowErrors = 0;
    double maxTempError = 0.0;
    std::size_t liveChecked = 0;
    for (int k = 0; k <= steps; ++k) {
        const Microstructure& st = states[static_cast<std::size_t>(k)];
        for (std::size_t i = 0; i < fin.type.size(); ++i) {
            const CellType r = replayType(fin, i, isVent[i] != 0, k);
            typeErrors += (r != st.type[i]) ? 1 : 0;
            if (r == CellType::Lava || r == CellType::Basalt) {
                flowErrors += (fin.flowId[i] != st.flowId[i]) ? 1 : 0;
                ++liveChecked;
            }
            if (c.ca.mode == CaMode::Lava && r == CellType::Lava && st.type[i] == CellType::Lava) {
                maxTempError = std::max(maxTempError, std::abs(replayTemp(fin, i, k, steps, params) - st.temp[i]));
            }
        }
    }
    CHECK(typeErrors == 0);
    CHECK(flowErrors == 0);
    CHECK(liveChecked > 100);
    CHECK(maxTempError < 0.05);  // różnica tylko z zaokrągleń float (odejmowanie krok po kroku)
}

}  // namespace

TEST_CASE("Kratery positions: config z listą kolumn — krater = pierwsza komórka powietrza nad terenem") {
    const Config c = cfgOf(with(kSmall3D, {"vents.placement=positions", "vents.count=2",
                                           "vents.positions=[[18, 18], [10, 25]]"}));
    REQUIRE(c.ventColumns().size() == 2);
    const Heightmap hm = Simulation::buildTerrain(c);
    const std::vector<Vent> vents = Simulation::buildVents(c, hm);
    REQUIRE(vents.size() == 2);
    CHECK(vents[0].x == 18);
    CHECK(vents[0].y == 18);
    CHECK(vents[0].z == hm.at(18, 18));
    CHECK(vents[0].flowId == 1);
    CHECK(vents[1].x == 10);
    CHECK(vents[1].y == 25);
    CHECK(vents[1].z == hm.at(10, 25));
    CHECK(vents[1].flowId == 2);
}

TEST_CASE("Kratery positions: te same kolumny co wylosowane przez crater -> bitowo ten sam wynik") {
    const Config crater = cfgOf(kSmall3D);
    const Heightmap hm = Simulation::buildTerrain(crater);
    const std::vector<Vent> drawn = Simulation::buildVents(crater, hm);
    std::string list = "vents.positions=[";
    for (std::size_t i = 0; i < drawn.size(); ++i) {
        list += (i ? "," : "") + std::string("[") + std::to_string(drawn[i].x) + "," + std::to_string(drawn[i].y) + "]";
    }
    list += "]";
    const Config positions = cfgOf(with(kSmall3D, {"vents.placement=positions", list}));

    const auto a = tempDir("positions_crater");
    const auto b = tempDir("positions_list");
    TimingReport ta;
    TimingReport tb;
    Simulation(cfgOf(with(kSmall3D, {"output.format=bin"}))).run(a.string(), ta);
    Simulation(cfgOf(with(kSmall3D, {"vents.placement=positions", list, "output.format=bin"}))).run(b.string(), tb);
    CHECK(positions.vents.placement == VentPlacement::Positions);
    CHECK(readBytes(a / "ca_result.bin") == readBytes(b / "ca_result.bin"));
    CHECK(readBytes(a / "stats.json") == readBytes(b / "stats.json"));
}

TEST_CASE("Kratery positions: stare configi bez zmian (jawne positions = [] jak brak klucza)") {
    const auto a = tempDir("positions_default");
    const auto b = tempDir("positions_empty");
    TimingReport ta;
    TimingReport tb;
    Simulation(cfgOf(with(kSmall2D, {"output.format=bin"}))).run(a.string(), ta);
    Simulation(cfgOf(with(kSmall2D, {"vents.positions=[]", "output.format=bin"}))).run(b.string(), tb);
    CHECK(readBytes(a / "ca_result.bin") == readBytes(b / "ca_result.bin"));
    // Przekrój 2D (ny = 1): kolumna [x, 0].
    const Config c2 = cfgOf(with(kSmall2D, {"vents.placement=positions", "vents.positions=[[30, 0]]"}));
    const Heightmap hm = Simulation::buildTerrain(c2);
    const std::vector<Vent> v = Simulation::buildVents(c2, hm);
    REQUIRE(v.size() == 1);
    CHECK(v[0].x == 30);
    CHECK(v[0].z == hm.at(30, 0));
}

TEST_CASE("Odtwarzanie erupcji: stan po k krokach z arrivalStep/solidStep = prawdziwy stan automatu") {
    SUBCASE("lawa 3D, 3 kratery w kraterze szczytowym") { checkReplay<VectorStorage>(cfgOf(kSmall3D)); }
    SUBCASE("lawa 3D, kratery na zboczu, sąsiedztwo von Neumanna") {
        checkReplay<VectorStorage>(cfgOf(with(kSmall3D, {"vents.placement=random", "neighborhood=von_neumann"})));
    }
    SUBCASE("lawa 2D, krater stygnie po erupcji (eruptionSteps = 10)") {
        checkReplay<VectorStorage>(cfgOf(with(kSmall2D, {"vents.eruptionSteps=10"})));
    }
    SUBCASE("lawa 3D, kratery w zadanych kolumnach, MatrixStorage") {
        checkReplay<MatrixStorage>(cfgOf(with(kSmall3D, {"vents.placement=positions", "vents.count=2",
                                                          "vents.positions=[[18, 18], [26, 12]]"})));
    }
    SUBCASE("classic 2D (rozrost ziaren)") {
        checkReplay<VectorStorage>(cfgOf({"ca.mode=classic", "space.nx=40", "space.ny=40", "space.nz=1",
                                          "vents.count=12"}));
    }
}

TEST_CASE("Migawki silnika (output.snapshotsEvery): stan 0, co N kroków i końcowy = odtworzenie z wyniku") {
    const auto out = tempDir("snapshots_ca");
    const Config c = cfgOf(with(kSmall3D, {"output.format=bin", "output.snapshotsEvery=9"}));
    TimingReport t;
    const RunSummary s = Simulation(c).run(out.string(), t);
    REQUIRE(s.steps > 9);
    const Microstructure fin = ResultReader::readBin((out / "ca_result.bin").string());
    std::vector<char> isVent(fin.type.size(), 0);
    for (const Vent& v : s.vents) {
        isVent[fin.index(v.x, v.y, v.z)] = 1;
    }
    std::vector<int> expected;
    for (int k = 0; k < s.steps; k += 9) {
        expected.push_back(k);
    }
    expected.push_back(s.steps);
    int files = 0;
    for (const int k : expected) {
        char name[32];
        std::snprintf(name, sizeof(name), "step_%06d.bin", k);
        const auto path = out / "snapshots" / name;
        REQUIRE_MESSAGE(std::filesystem::exists(path), path.string());
        const Microstructure snap = ResultReader::readBin(path.string());
        std::size_t errors = 0;
        for (std::size_t i = 0; i < fin.type.size(); ++i) {
            errors += replayType(fin, i, isVent[i] != 0, k) != snap.type[i] ? 1 : 0;
        }
        CHECK_MESSAGE(errors == 0, "krok " << k);
        ++files;
    }
    CHECK(files == static_cast<int>(std::distance(std::filesystem::directory_iterator(out / "snapshots"),
                                                  std::filesystem::directory_iterator{})));
    // Ostatnia migawka = wynik końcowy; migawki nie zmieniają wyniku (przebieg bez migawek).
    char last[32];
    std::snprintf(last, sizeof(last), "step_%06d.bin", s.steps);
    CHECK(readBytes(out / "snapshots" / last) == readBytes(out / "ca_result.bin"));
    const auto plain = tempDir("snapshots_off");
    TimingReport t2;
    Simulation(cfgOf(with(kSmall3D, {"output.format=bin"}))).run(plain.string(), t2);
    CHECK(readBytes(plain / "ca_result.bin") == readBytes(out / "ca_result.bin"));
    CHECK(hasSection(t, "snapshots"));
    CHECK_FALSE(hasSection(t2, "snapshots"));
}

TEST_CASE("Migawki MC (mc.snapshotsEvery): MCS 0, co N i końcowa; wynik MC bez zmian") {
    const std::vector<std::string> base = with(kSmall2D, {"mc.enabled=true", "mc.mcs=7", "mc.statsEvery=3",
                                                          "output.format=bin"});
    const auto on = tempDir("snapshots_mc_on");
    const auto off = tempDir("snapshots_mc_off");
    TimingReport t1;
    TimingReport t2;
    Simulation(cfgOf(with(base, {"mc.snapshotsEvery=3"}))).run(on.string(), t1);
    Simulation(cfgOf(base)).run(off.string(), t2);
    CHECK(readBytes(on / "mc_result.bin") == readBytes(off / "mc_result.bin"));
    CHECK(readBytes(on / "mc_stats.csv") == readBytes(off / "mc_stats.csv"));
    std::set<std::string> names;
    for (const auto& e : std::filesystem::directory_iterator(on / "mc_snapshots")) {
        names.insert(e.path().filename().string());
    }
    CHECK(names == std::set<std::string>{"mcs_000000.bin", "mcs_000003.bin", "mcs_000006.bin", "mcs_000007.bin"});
    CHECK(readBytes(on / "mc_snapshots" / "mcs_000007.bin") == readBytes(on / "mc_result.bin"));
    // MCS 0 = orientacje początkowe: inne niż po 7 MCS, ta sama domena (komórki > 0).
    const CrystalMap m0 = ResultReader::readCrystalBin((on / "mc_snapshots" / "mcs_000000.bin").string());
    const CrystalMap m7 = ResultReader::readCrystalBin((on / "mc_result.bin").string());
    REQUIRE(m0.crystal.size() == m7.crystal.size());
    std::size_t differ = 0;
    for (std::size_t i = 0; i < m0.crystal.size(); ++i) {
        CHECK((m0.crystal[i] > 0) == (m7.crystal[i] > 0));
        differ += m0.crystal[i] != m7.crystal[i] ? 1 : 0;
    }
    CHECK(differ > 0);
    CHECK(hasSection(t1, "mcSnapshots"));
    CHECK_FALSE(hasSection(t2, "mcSnapshots"));
    CHECK_FALSE(std::filesystem::exists(off / "mc_snapshots"));
}
