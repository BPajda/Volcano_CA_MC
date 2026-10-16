// Testy terenu i rozmieszczenia kraterów / zarodków.
#include "doctest.h"

#include <filesystem>
#include <fstream>
#include <set>

#include "terrain/HeightmapLoader.hpp"
#include "terrain/TerrainGenerator.hpp"
#include "terrain/VentPlacer.hpp"

using namespace volcano;

TEST_CASE("Stożek: krater niżej niż krawędź, zbocze opada, wysokości w [0, nz]") {
    TerrainConfig t;
    t.noise = 0.0;  // bez szumu — profil symetryczny
    const Dims d{200, 1, 100};
    const Heightmap hm = TerrainGenerator::cone(t, d, 42);
    const int center = 100;
    const int rim = center + 6;  // pierwsza kolumna poza kraterem (r >= craterRadius)
    CHECK(hm.at(center, 0) < hm.at(rim, 0));          // dno krateru poniżej krawędzi
    CHECK(hm.at(rim, 0) > hm.at(rim + 20, 0));        // zbocze opada
    CHECK(hm.at(rim + 20, 0) > hm.at(rim + 60, 0));
    CHECK(hm.at(0, 0) == 0);                          // poza podstawą stożka
    for (int x = 0; x < d.nx; ++x) {
        CHECK(hm.at(x, 0) >= 0);
        CHECK(hm.at(x, 0) <= d.nz);
    }
}

TEST_CASE("Stożek: szum deterministyczny (ten sam seed -> ta sama mapa)") {
    TerrainConfig t;
    t.noise = 0.1;
    const Dims d{40, 40, 60};
    CHECK(TerrainGenerator::cone(t, d, 7).height == TerrainGenerator::cone(t, d, 7).height);
    CHECK(TerrainGenerator::cone(t, d, 7).height != TerrainGenerator::cone(t, d, 8).height);
    for (int i = 0; i < 100; ++i) {
        const double n = TerrainGenerator::smoothNoise(3, i, 2 * i);
        CHECK(n >= -1.0);
        CHECK(n <= 1.0);
    }
}

TEST_CASE("HeightmapLoader: wczytanie CSV i czytelne błędy") {
    const auto dir = std::filesystem::temp_directory_path() / "volcano_tests";
    std::filesystem::create_directories(dir);
    const std::string ok = (dir / "hm_ok.csv").string();
    std::ofstream(ok) << "# mapa 3x2\n1,2,3\n4.5; 0  9\n";
    const Heightmap hm = HeightmapLoader::loadCsv(ok, Dims{3, 2, 8});
    CHECK(hm.at(0, 0) == 1);
    CHECK(hm.at(2, 0) == 3);
    CHECK(hm.at(0, 1) == 5);  // 4.5 -> skała w z < 4.5 -> 5 komórek
    CHECK(hm.at(2, 1) == 8);  // przycięte do nz

    const std::string bad = (dir / "hm_bad.csv").string();
    std::ofstream(bad) << "1,2,3\n4,5\n";
    CHECK_THROWS_AS(HeightmapLoader::loadCsv(bad, Dims{3, 2, 8}), ConfigError);
}

TEST_CASE("Kratery: w kraterze, na powierzchni, unikalne, flowId 1..count") {
    TerrainConfig t;
    VentsConfig v;
    v.count = 5;
    const Dims d{60, 60, 80};
    const Heightmap hm = TerrainGenerator::cone(t, d, 1);
    const auto vents = VentPlacer::placeVents(v, t, d, hm, 1);
    REQUIRE(vents.size() == 5);
    std::set<std::pair<int, int>> columns;
    for (std::size_t i = 0; i < vents.size(); ++i) {
        const Vent& e = vents[i];
        CHECK(e.flowId == static_cast<int>(i) + 1);
        CHECK(e.z == hm.at(e.x, e.y));  // pierwsza komórka AIR nad terenem
        CHECK(TerrainGenerator::distanceFromCenter(d, e.x, e.y) <= t.craterRadius);
        columns.insert({e.x, e.y});
    }
    CHECK(columns.size() == 5);

    v.count = 1000;  // więcej niż kolumn w kraterze
    CHECK_THROWS_AS(VentPlacer::placeVents(v, t, d, hm, 1), ConfigError);
}

TEST_CASE("Kratery random: na zboczu, poza kraterem") {
    TerrainConfig t;
    VentsConfig v;
    v.count = 10;
    v.placement = VentPlacement::Random;
    const Dims d{80, 80, 80};
    const Heightmap hm = TerrainGenerator::cone(t, d, 1);
    for (const Vent& e : VentPlacer::placeVents(v, t, d, hm, 1)) {
        CHECK(TerrainGenerator::distanceFromCenter(d, e.x, e.y) > t.craterRadius);
        CHECK(hm.at(e.x, e.y) >= 1);
    }
}

TEST_CASE("Kratery positions: zadane kolumny, z = wysokość terenu, flowId wg kolejności, kolumna pełna skały") {
    TerrainConfig t;
    std::vector<std::pair<int, int>> cols = {{30, 30}, {5, 52}, {44, 20}};
    const Dims d{60, 60, 80};
    const Heightmap hm = TerrainGenerator::cone(t, d, 1);
    const auto vents = VentPlacer::placeAt(cols, d, hm);
    REQUIRE(vents.size() == 3);
    for (std::size_t i = 0; i < vents.size(); ++i) {
        CHECK(vents[i].x == cols[i].first);
        CHECK(vents[i].y == cols[i].second);
        CHECK(vents[i].z == hm.at(vents[i].x, vents[i].y));  // pierwsza komórka AIR nad terenem
        CHECK(vents[i].flowId == static_cast<int>(i) + 1);
    }

    // Kolumna w całości ze skały (wysokość terenu >= nz) i kolumna poza siatką — czytelny błąd.
    Heightmap full = hm;
    full.height[static_cast<std::size_t>(5 + 60 * 52)] = 80;
    CHECK_THROWS_WITH_AS(VentPlacer::placeAt(cols, d, full), doctest::Contains("vents.positions[1]"), ConfigError);
    cols[2] = {60, 0};
    CHECK_THROWS_AS(VentPlacer::placeAt(cols, d, hm), ConfigError);
    // placeVents nie obsługuje listy (rozmieszcza ją placeAt w Simulation::buildVents).
    VentsConfig v;
    v.placement = VentPlacement::Positions;
    CHECK_THROWS_AS(VentPlacer::placeVents(v, t, d, hm, 1), ConfigError);
}

TEST_CASE("Zarodki classic: unikalne komórki, deterministyczne") {
    const Dims d{10, 10, 10};
    const auto a = VentPlacer::placeSeeds(1000, d, 5);  // wszystkie komórki
    std::set<std::tuple<int, int, int>> cells;
    for (const Vent& s : a) {
        cells.insert({s.x, s.y, s.z});
    }
    CHECK(cells.size() == 1000);
    const auto b = VentPlacer::placeSeeds(10, d, 5);
    const auto c = VentPlacer::placeSeeds(10, d, 5);
    for (std::size_t i = 0; i < b.size(); ++i) {
        CHECK(b[i].x == c[i].x);
        CHECK(b[i].z == c[i].z);
    }
}

TEST_CASE("Poziom przelewu niecek (priority-flood)") {
    // Profil 1D: dołek w x = 2..3 otoczony wysokościami 5 i 4 -> wypełnia się do 4.
    Heightmap hm;
    hm.nx = 7;
    hm.ny = 1;
    hm.height = {5, 5, 2, 2, 4, 1, 0};
    const Heightmap f = TerrainGenerator::fillDepressions(hm, false, false);
    CHECK(f.height == std::vector<int>{5, 5, 4, 4, 4, 1, 0});

    // Krater stożka: dno wypełnia się do najniższego punktu krawędzi; zbocze bez zmian.
    TerrainConfig t;
    t.noise = 0.0;
    const Dims d{200, 1, 100};
    const Heightmap cone = TerrainGenerator::cone(t, d, 1);
    const Heightmap fc = TerrainGenerator::fillDepressions(cone, false, false);
    CHECK(fc.at(100, 0) > cone.at(100, 0));   // środek krateru — niecka
    CHECK(fc.at(100, 0) == cone.at(106, 0));  // do wysokości krawędzi
    CHECK(fc.at(150, 0) == cone.at(150, 0));  // zbocze — nie niecka
}
