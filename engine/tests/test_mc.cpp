// Testy krystalizacji Monte Carlo: energia i ΔE na ręcznych przykładach, akceptacja dla kT = 0,
// domena (komórki spoza nie zmieniają się i nie wnoszą energii), brzegi periodyczne (ramka),
// rozrost ziaren w trybie full, determinizm, mobilność, liczenie ziaren, MC z pliku wyniku CA.
#include "doctest.h"

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>

#include "app/McStage.hpp"
#include "app/Simulation.hpp"
#include "core/Boundary.hpp"
#include "core/Neighborhood.hpp"
#include "io/Config.hpp"
#include "io/ResultReader.hpp"
#include "io/ResultWriter.hpp"
#include "io/TimingReport.hpp"
#include "mc/CoolingMobility.hpp"
#include "mc/Grains.hpp"
#include "mc/PottsMC.hpp"

using namespace volcano;

namespace {

// Parametry MC do testów.
McParams params(int Q, double J = 1.0, double kT = 0.0, std::uint64_t seed = 42) {
    McParams p;
    p.seed = seed;
    p.Q = Q;
    p.J = J;
    p.kT = kT;
    return p;
}

// MC na całej przestrzeni (tryb full) po inicjalizacji.
PottsMC fullMc(const Dims& d, NeighborhoodKind nb, BoundaryKind bc, const McParams& p) {
    PottsMC mc(d, p, Neighborhood(nb, d), Boundary(bc, CaMode::Classic));
    mc.setDomainAll();
    mc.initialize();
    return mc;
}

// Ustawia orientację s we wszystkich komórkach domeny.
void fill(PottsMC& mc, std::int32_t s) {
    const Dims& d = mc.dims();
    for (int z = 0; z < d.nz; ++z) {
        for (int y = 0; y < d.ny; ++y) {
            for (int x = 0; x < d.nx; ++x) {
                if (mc.inDomain(x, y, z)) {
                    mc.setOrientation(x, y, z, s);
                }
            }
        }
    }
}

std::filesystem::path tempDir(const std::string& name) {
    const auto dir = std::filesystem::temp_directory_path() / "volcano_tests" / name;
    std::filesystem::remove_all(dir);
    std::filesystem::create_directories(dir);
    return dir;
}

// Mały przypadek lawy 2D z grubszym bazaltem (jezioro lawy w szerokim kraterze).
const std::vector<std::string> kLavaMc2D = {
    "space.nx=90", "space.nz=50", "terrain.peakHeight=32", "terrain.baseRadius=42", "terrain.craterRadius=10",
    "terrain.craterDepth=5", "ca.coolingAmbient=2", "ca.coolingLateral=6", "ca.coolingFall=3",
    "vents.eruptionSteps=60", "mc.enabled=true", "mc.Q=20", "mc.mcs=20", "mc.statsEvery=5",
    "output.format=both"};

}  // namespace

TEST_CASE("MC: energia komórki i ΔE — ręczny przykład 2D (von Neumann i Moore)") {
    // Siatka 5x5 (płaszczyzna x–y), wokół komórki (2,2) o orientacji 1:
    //   y=3:  1 2 1        sąsiedzi przez ścianę: 2, 3, 1, 2   -> różnych od 1: 3
    //   y=2:  2 1 3        narożniki: 4, 1, 1, 5               -> różnych od 1: 2
    //   y=1:  4 1 5
    const Dims d{5, 5, 1};
    for (NeighborhoodKind nb : {NeighborhoodKind::VonNeumann, NeighborhoodKind::Moore}) {
        PottsMC mc = fullMc(d, nb, BoundaryKind::Absorbing, params(10, 2.0));
        fill(mc, 1);
        mc.setOrientation(1, 2, 0, 2);
        mc.setOrientation(3, 2, 0, 3);
        mc.setOrientation(2, 1, 0, 1);
        mc.setOrientation(2, 3, 0, 2);
        mc.setOrientation(1, 1, 0, 4);
        mc.setOrientation(3, 3, 0, 1);
        mc.setOrientation(1, 3, 0, 1);
        mc.setOrientation(3, 1, 0, 5);
        if (nb == NeighborhoodKind::VonNeumann) {
            CHECK(mc.energyAt(2, 2, 0) == doctest::Approx(6.0));      // J · 3
            CHECK(mc.energyIf(2, 2, 0, 2) == doctest::Approx(4.0));   // różne: 3, 1 -> J · 2
            CHECK(mc.deltaEnergy(2, 2, 0, 2) == doctest::Approx(-2.0));
            CHECK(mc.deltaEnergy(2, 2, 0, 7) == doctest::Approx(2.0));  // wszyscy 4 różni
        } else {
            CHECK(mc.energyAt(2, 2, 0) == doctest::Approx(10.0));     // J · (3 + 2)
            CHECK(mc.energyIf(2, 2, 0, 2) == doctest::Approx(12.0));  // J · (2 + 4)
            CHECK(mc.deltaEnergy(2, 2, 0, 2) == doctest::Approx(2.0));
        }
        // Komórka przy brzegu absorbującym: ramka nie wnosi energii (narożnik (0,0) ma 2 / 3 sąsiadów).
        mc.setOrientation(0, 0, 0, 9);
        CHECK(mc.energyAt(0, 0, 0) == doctest::Approx(nb == NeighborhoodKind::VonNeumann ? 4.0 : 6.0));
    }
}

TEST_CASE("MC: energia komórki i ΔE — ręczny przykład 3D (von Neumann i Moore)") {
    // Kostka 3x3x3, środek (1,1,1) = 1; sąsiedzi przez ścianę: (0,1,1) = 2, (2,1,1) = 2, (1,0,1) = 3,
    // reszta ścian 1; dodatkowo narożnik (0,0,0) = 2 i krawędź (2,2,1) = 4.
    const Dims d{3, 3, 3};
    for (NeighborhoodKind nb : {NeighborhoodKind::VonNeumann, NeighborhoodKind::Moore}) {
        PottsMC mc = fullMc(d, nb, BoundaryKind::Absorbing, params(10));
        fill(mc, 1);
        mc.setOrientation(0, 1, 1, 2);
        mc.setOrientation(2, 1, 1, 2);
        mc.setOrientation(1, 0, 1, 3);
        mc.setOrientation(0, 0, 0, 2);
        mc.setOrientation(2, 2, 1, 4);
        if (nb == NeighborhoodKind::VonNeumann) {
            CHECK(mc.energyAt(1, 1, 1) == doctest::Approx(3.0));
            CHECK(mc.deltaEnergy(1, 1, 1, 2) == doctest::Approx(1.0));   // 6 ścian: różne 3, 1, 1, 1 -> 4
        } else {
            CHECK(mc.energyAt(1, 1, 1) == doctest::Approx(5.0));
            CHECK(mc.deltaEnergy(1, 1, 1, 2) == doctest::Approx(18.0));  // 26 − 3 równych = 23
        }
    }
}

TEST_CASE("MC: energia całkowita liczy każdą parę raz; brzeg periodyczny dokłada granicę przez krawędź") {
    // 4x4, lewa połowa 1, prawa 2 — granica pionowa: 4 pary (absorbujący), 8 par (periodyczny).
    const Dims d{4, 4, 1};
    for (BoundaryKind bc : {BoundaryKind::Absorbing, BoundaryKind::Periodic}) {
        PottsMC mc = fullMc(d, NeighborhoodKind::VonNeumann, bc, params(5, 1.5));
        fill(mc, 1);
        for (int y = 0; y < 4; ++y) {
            mc.setOrientation(2, y, 0, 2);
            mc.setOrientation(3, y, 0, 2);
        }
        CHECK(mc.totalEnergy() == doctest::Approx(bc == BoundaryKind::Absorbing ? 6.0 : 12.0));
    }
}

TEST_CASE("MC: ramka periodyczna jest odświeżana po zmianie komórki przy ścianie") {
    const Dims d{4, 4, 1};
    {
        PottsMC mc = fullMc(d, NeighborhoodKind::VonNeumann, BoundaryKind::Periodic, params(5));
        fill(mc, 1);
        mc.setOrientation(0, 1, 0, 2);
        CHECK(mc.energyAt(3, 1, 0) == doctest::Approx(1.0));  // sąsiad +x zawija się do (0,1)
        mc.setOrientation(0, 1, 0, 1);
        CHECK(mc.energyAt(3, 1, 0) == doctest::Approx(0.0));
    }
    {
        PottsMC mc = fullMc(d, NeighborhoodKind::Moore, BoundaryKind::Periodic, params(5));
        fill(mc, 1);
        mc.setOrientation(0, 0, 0, 3);
        CHECK(mc.energyAt(3, 3, 0) == doctest::Approx(1.0));  // narożnik ramki = (0,0)
        CHECK(mc.energyAt(3, 0, 0) == doctest::Approx(1.0));
        CHECK(mc.energyAt(0, 3, 0) == doctest::Approx(1.0));
        CHECK(mc.energyAt(2, 2, 0) == doctest::Approx(0.0));
    }
    {
        // 3D: narożnik (0,0,0) ma 7 kopii w ramce — widzi go przeciwległy narożnik.
        const Dims d3{3, 3, 3};
        PottsMC mc = fullMc(d3, NeighborhoodKind::Moore, BoundaryKind::Periodic, params(5));
        fill(mc, 1);
        mc.setOrientation(0, 0, 0, 2);
        CHECK(mc.energyAt(2, 2, 2) == doctest::Approx(1.0));
    }
}

TEST_CASE("MC: sąsiedzi spoza domeny nie wnoszą energii, komórki spoza domeny nigdy się nie zmieniają") {
    const Dims d{12, 1, 8};  // przekrój x–z jak w trybie lava
    std::vector<std::uint8_t> mask(d.cells(), 0);
    for (std::size_t i = 0; i < mask.size(); ++i) {
        mask[i] = (i % 3 != 0) ? 1 : 0;  // dziurawa domena
    }
    PottsMC mc(d, params(6), Neighborhood(NeighborhoodKind::Moore, d), Boundary(BoundaryKind::Periodic, CaMode::Lava));
    mc.setDomain(mask);
    mc.initialize();
    CHECK(mc.domainCells() == static_cast<std::size_t>(std::count(mask.begin(), mask.end(), std::uint8_t(1))));

    // Komórka domeny otoczona wyłącznie komórkami spoza domeny ma energię 0.
    std::vector<std::uint8_t> lonely(d.cells(), 0);
    lonely[globalIndex(d, 5, 0, 4)] = 1;
    PottsMC one(d, params(6), Neighborhood(NeighborhoodKind::Moore, d), Boundary(BoundaryKind::Absorbing, CaMode::Lava));
    one.setDomain(lonely);
    one.initialize();
    CHECK(one.energyAt(5, 0, 4) == 0.0);
    CHECK(one.deltaEnergy(5, 0, 4, one.orientation(5, 0, 4) % 6 + 1) == 0.0);

    for (int k = 0; k < 15; ++k) {
        mc.sweep();
    }
    const CrystalMap m = mc.crystals();
    for (std::size_t i = 0; i < mask.size(); ++i) {
        if (mask[i] == 0) {
            CHECK(m.crystal[i] == 0);
        } else {
            CHECK(m.crystal[i] >= 1);
            CHECK(m.crystal[i] <= 6);
        }
    }
    CHECK(mc.accepted() > 0);
}

TEST_CASE("MC: kT = 0 nigdy nie akceptuje ΔE > 0 (energia nie rośnie), kT > 0 akceptuje czasem") {
    const Dims d2{30, 30, 1};
    const Dims d3{10, 10, 10};
    for (NeighborhoodKind nb : {NeighborhoodKind::VonNeumann, NeighborhoodKind::Moore}) {
        for (const Dims& d : {d2, d3}) {
            PottsMC mc = fullMc(d, nb, BoundaryKind::Periodic, params(8));
            double e = mc.totalEnergy();
            for (int k = 0; k < 15; ++k) {
                mc.sweep();
                const double now = mc.totalEnergy();
                CHECK(now <= e);
                e = now;
            }
            CHECK(mc.acceptedUphill() == 0);
            CHECK(mc.accepted() > 0);
        }
    }
    PottsMC hot = fullMc(d2, NeighborhoodKind::Moore, BoundaryKind::Periodic, params(8, 1.0, 2.0));
    for (int k = 0; k < 5; ++k) {
        hot.sweep();
    }
    CHECK(hot.acceptedUphill() > 0);
}

TEST_CASE("MC full: ziarna rosną — po 50 MCS jest ich mniej niż na starcie (2D i 3D, różne sąsiedztwa)") {
    // Losowe pentagonalne rośnie bardzo wolno: decyzja widzi 5 z 8 sąsiadów, więc para komórek
    // rozpada się, gdy wylosowany wariant nie obejmuje partnera (ΔE = 0) — stąd słabszy warunek.
    struct Case {
        Dims d;
        NeighborhoodKind nb;
        bool fastGrowth;
    };
    const Case cases[] = {{{40, 40, 1}, NeighborhoodKind::VonNeumann, true},
                          {{40, 40, 1}, NeighborhoodKind::Hexagonal, true},
                          {{40, 1, 40}, NeighborhoodKind::Moore, true},
                          {{40, 1, 40}, NeighborhoodKind::Pentagonal, false},
                          {{14, 14, 14}, NeighborhoodKind::Moore, true},
                          {{14, 14, 14}, NeighborhoodKind::VonNeumann, true},
                          {{14, 14, 14}, NeighborhoodKind::Pentagonal, false}};
    for (const Case& c : cases) {
        const std::string nbName = Neighborhood::name(c.nb);
        CAPTURE(nbName);
        PottsMC mc = fullMc(c.d, c.nb, BoundaryKind::Periodic, params(50));
        const McStats start = mc.measure();
        CHECK(start.grains > c.d.cells() / 2);  // Q = 50: prawie każda komórka to osobne ziarno
        for (int k = 0; k < 50; ++k) {
            mc.sweep();
        }
        const McStats end = mc.measure();
        CHECK(end.mcs == 50);
        CHECK(end.grains < start.grains);
        CHECK(end.energy < start.energy);
        if (c.fastGrowth) {
            CHECK(end.grains < start.grains / 2);
            CHECK(end.meanGrainSize > 2.0 * start.meanGrainSize);
        }
    }
}

TEST_CASE("MC: ten sam seed -> identyczny wynik, inny seed -> inny") {
    const Dims d{25, 25, 1};
    auto run = [&](std::uint64_t seed, NeighborhoodKind nb) {
        PottsMC mc = fullMc(d, nb, BoundaryKind::Periodic, params(20, 1.0, 0.5, seed));
        for (int k = 0; k < 10; ++k) {
            mc.sweep();
        }
        return mc.crystals().crystal;
    };
    for (NeighborhoodKind nb : {NeighborhoodKind::Moore, NeighborhoodKind::Pentagonal}) {
        CHECK(run(7, nb) == run(7, nb));
        CHECK(run(7, nb) != run(8, nb));
    }
}

TEST_CASE("MC: mobilność 0 -> brak zmian; mobilność ze stygnięcia: min–max, równe czasy -> 1") {
    const Dims d{20, 1, 10};
    PottsMC mc(d, params(10), Neighborhood(NeighborhoodKind::Moore, d),
               Boundary(BoundaryKind::Absorbing, CaMode::Lava));
    mc.setDomainAll();
    mc.setMobility(std::vector<float>(d.cells(), 0.0f));
    mc.initialize();
    const CrystalMap before = mc.crystals();
    for (int k = 0; k < 10; ++k) {
        mc.sweep();
    }
    CHECK(mc.crystals().crystal == before.crystal);
    CHECK(mc.accepted() == 0);
    CHECK(mc.attempts() == 0);  // wszystkie próby pominięte

    // Mikrostruktura: trzy komórki bazaltu (czasy płynięcia 2, 10, 6) i jedna płynna lawa.
    Microstructure m;
    m.resize(Dims{4, 1, 2});
    m.type = {CellType::Basalt, CellType::Basalt, CellType::Basalt, CellType::Rock,
              CellType::Air,    CellType::Air,    CellType::Air,    CellType::Lava};
    m.arrivalStep = {3, 0, 4, 0, 0, 0, 0, 8};
    m.solidStep = {5, 10, 10, 0, 0, 0, 0, 0};
    const std::vector<std::uint8_t> dom = CoolingMobility::basaltDomain(m);
    CHECK(dom == std::vector<std::uint8_t>{1, 1, 1, 0, 0, 0, 0, 1});
    const std::vector<std::uint32_t> time = CoolingMobility::liquidTime(m, dom);
    CHECK(time[0] == 2);
    CHECK(time[1] == 10);
    CHECK(time[2] == 6);
    CHECK(time[7] == 2);  // płynna lawa: koniec CA = największy zapisany krok (10) − 8
    const std::vector<float> mob0 = CoolingMobility::fromCooling(m, dom, 0.0);
    CHECK(mob0[0] == doctest::Approx(0.0));   // najkrótszy czas -> mobilityMin = 0
    CHECK(mob0[1] == doctest::Approx(1.0));   // najdłuższy -> 1
    CHECK(mob0[2] == doctest::Approx(0.5));
    CHECK(mob0[3] == 0.0f);                   // poza domeną
    const std::vector<float> mob = CoolingMobility::fromCooling(m, dom, 0.2);
    CHECK(mob[0] == doctest::Approx(0.2));
    CHECK(mob[2] == doctest::Approx(0.6));

    Microstructure same = m;
    same.arrivalStep = {0, 0, 0, 0, 0, 0, 0, 0};
    same.solidStep = {7, 7, 7, 0, 0, 0, 0, 0};
    same.type[7] = CellType::Air;
    const std::vector<float> ones = CoolingMobility::fromCooling(same, CoolingMobility::basaltDomain(same), 0.05);
    CHECK(ones[0] == 1.0f);
    CHECK(ones[2] == 1.0f);
}

TEST_CASE("Grains: liczba spójnych składowych na ręcznym przykładzie (VN, Moore, periodyczne)") {
    //   y=2:  1 0 0 1
    //   y=1:  0 1 0 0
    //   y=0:  2 2 0 1        (0 = poza domeną)
    CrystalMap m;
    m.dims = Dims{4, 3, 1};
    m.crystal = {2, 2, 0, 1,
                 0, 1, 0, 0,
                 1, 0, 0, 1};
    const bool none[3] = {false, false, false};
    const bool px[3] = {true, false, false};
    const bool pxy[3] = {true, true, false};

    const GrainLabels vn = Grains::label(m, false, none);
    CHECK(vn.grains == 5);  // cztery pojedyncze „1” + para „2”
    CHECK(vn.cells == 6);
    CHECK(vn.root[2] == GrainLabels::kNone);
    CHECK(vn.size[vn.root[0]] == 2);
    CHECK(vn.root[0] == vn.root[1]);

    const GrainLabels moore = Grains::label(m, true, none);
    CHECK(moore.grains == 4);  // (1,1) łączy się po przekątnej z (0,2)
    CHECK(moore.root[globalIndex(m.dims, 1, 1, 0)] == moore.root[globalIndex(m.dims, 0, 2, 0)]);

    CHECK(Grains::label(m, false, px).grains == 4);   // (3,2)–(0,2) przez brzeg x
    CHECK(Grains::label(m, false, pxy).grains == 3);  // dodatkowo (3,0)–(3,2) przez brzeg y

    // 3D: kostka 2x2x2 tej samej orientacji = 1 ziarno; jedna komórka inna -> 2 ziarna.
    CrystalMap c;
    c.dims = Dims{2, 2, 2};
    c.crystal.assign(8, 5);
    CHECK(Grains::label(c, false, none).grains == 1);
    c.crystal[7] = 6;
    const GrainLabels g3 = Grains::label(c, true, none);
    CHECK(g3.grains == 2);
    CHECK(g3.size[g3.root[0]] == 7);
}

TEST_CASE("MC basalt: wynik z pliku (--mc-from) = wynik w pamięci; txt bez mobilności") {
    const auto caDir = tempDir("mc_ca");
    const auto memDir = tempDir("mc_mem");
    const auto fileDir = tempDir("mc_file");
    const auto txtDir = tempDir("mc_txt");

    // 1. CA + MC w jednym przebiegu (wynik CA w pamięci).
    const Config cfg = Config::load("", kLavaMc2D);
    TimingReport t1;
    Simulation sim(cfg);
    const RunSummary s = sim.run(memDir.string(), t1);
    REQUIRE(s.mcRan);
    REQUIRE(s.mc.domainCells > 50);
    CHECK(s.mc.mobilityUsed);
    CHECK(t1.get("mcSim") > 0.0);
    CHECK(std::filesystem::exists(memDir / "mc_result.txt"));
    CHECK(std::filesystem::exists(memDir / "mc_result.bin"));
    CHECK(std::filesystem::exists(memDir / "mc_stats.csv"));
    // Domena = BASALT + LAVA z wyniku CA; poza nią 0.
    std::size_t lavaLike = 0;
    for (std::size_t i = 0; i < s.result.type.size(); ++i) {
        const bool dom = s.result.type[i] == CellType::Basalt || s.result.type[i] == CellType::Lava;
        lavaLike += dom ? 1 : 0;
        CHECK((s.mc.crystals.crystal[i] > 0) == dom);
    }
    CHECK(s.mc.domainCells == lavaLike);
    // Statystyki: MCS 0, 5, 10, 15, 20.
    REQUIRE(s.mc.history.size() == 5);
    CHECK(s.mc.history.back().mcs == 20);
    CHECK(s.mc.stats.contains("byMobility"));

    // 2. To samo MC z pliku ca_result.bin (v2) — identyczny wynik.
    std::filesystem::copy_file(memDir / "ca_result.bin", caDir / "ca_result.bin");
    TimingReport t2;
    const McSummary f = Simulation::runMcFrom(cfg, caDir.string(), fileDir.string(), t2);
    CHECK(f.mobilityUsed);
    CHECK(f.crystals.crystal == s.mc.crystals.crystal);
    CHECK(ResultReader::readCrystalFolder(fileDir.string()).crystal == s.mc.crystals.crystal);
    CHECK(t2.get("readInput") > 0.0);
    CHECK(std::filesystem::exists(fileDir / "stats.json"));
    CHECK(std::filesystem::exists(fileDir / "config_used.json"));

    // 3. Z pliku txt: brak danych o stygnięciu -> ostrzeżenie, mobilność wyłączona.
    std::filesystem::remove(caDir / "ca_result.bin");
    std::filesystem::copy_file(memDir / "ca_result.txt", caDir / "ca_result.txt");
    TimingReport t3;
    const McSummary txt = Simulation::runMcFrom(cfg, caDir.string(), txtDir.string(), t3);
    CHECK_FALSE(txt.mobilityUsed);
    CHECK_FALSE(txt.warnings.empty());
    CHECK(txt.domainCells == s.mc.domainCells);

    // Config bez space (same domyślne wymiary 200x1x100): wymiary z pliku, bez ostrzeżenia
    // o konflikcie; podane space różne od pliku -> ostrzeżenie, wygrywa plik.
    TimingReport t5;
    const McSummary noSpace = Simulation::runMcFrom(Config::load("", {"mc.Q=20", "mc.mcs=3"}), caDir.string(),
                                                    txtDir.string(), t5);
    CHECK((noSpace.crystals.dims == s.result.dims));
    for (const std::string& w : noSpace.warnings) {
        CHECK(w.find("wymiary") == std::string::npos);
    }
    const McSummary badSpace = Simulation::runMcFrom(Config::load("", {"space.nx=10", "mc.mcs=1"}),
                                                     caDir.string(), txtDir.string(), t5);
    CHECK((badSpace.crystals.dims == s.result.dims));
    bool dimsWarning = false;
    for (const std::string& w : badSpace.warnings) {
        dimsWarning = dimsWarning || w.find("wymiary") != std::string::npos;
    }
    CHECK(dimsWarning);

    // 4. --mc-from wymaga domeny basalt.
    TimingReport t4;
    CHECK_THROWS_AS(Simulation::runMcFrom(Config::load("", {"mc.domain=full", "space.nz=1", "space.ny=20"}),
                                          caDir.string(), txtDir.string(), t4),
                    ConfigError);
}

TEST_CASE("MC full przez Simulation: bez CA, czasy MC w raporcie, stats.json z sekcją mc") {
    const auto dir = tempDir("mc_full");
    const Config cfg = Config::load("", {"mc.enabled=true", "mc.domain=full", "mc.mobilityFromCooling=false",
                                         "space.nx=30", "space.ny=30", "space.nz=1", "neighborhood=von_neumann",
                                         "boundary=periodic", "mc.mcs=12", "mc.statsEvery=5", "output.format=bin"});
    TimingReport t;
    Simulation sim(cfg);
    const RunSummary s = sim.run(dir.string(), t);
    CHECK_FALSE(s.caRan);
    CHECK(s.mcRan);
    CHECK(s.mc.domainCells == 900);
    CHECK(t.get("caSim") == 0.0);  // sekcji CA nie ma
    CHECK(t.get("mcSim") > 0.0);
    CHECK(std::filesystem::exists(dir / "mc_result.bin"));
    CHECK_FALSE(std::filesystem::exists(dir / "mc_result.txt"));
    CHECK_FALSE(std::filesystem::exists(dir / "ca_result.bin"));
    // MCS 0, 5, 10 i ostatni (12).
    REQUIRE(s.mc.history.size() == 4);
    CHECK(s.mc.history[3].mcs == 12);
    CHECK(s.mc.history[3].grains < s.mc.history[0].grains);
    CHECK_FALSE(s.mc.stats.contains("byMobility"));  // w trybie full nie ma czasu stygnięcia
}
