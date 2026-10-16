// Testy sąsiedztw: liczba sąsiadów w 2D/3D, płaszczyzna 2D, losowanie wariantów.
#include "doctest.h"

#include <set>
#include <stdexcept>

#include "core/Neighborhood.hpp"

using namespace volcano;

namespace {
const Dims k2D{20, 1, 10};   // przekrój pionowy x–z
const Dims k2Dxy{20, 10, 1}; // płaszczyzna x–y (tryb classic)
const Dims k3D{8, 8, 8};

// Sprawdza, że wszystkie warianty mają podaną liczbę sąsiadów.
void checkSizes(const Neighborhood& n, std::size_t expected) {
    for (int v = 0; v < n.variantCount(); ++v) {
        CHECK(n.variant(v).size() == expected);
    }
}
}  // namespace

TEST_CASE("Sąsiedztwa 2D: liczba sąsiadów") {
    checkSizes(Neighborhood(NeighborhoodKind::VonNeumann, k2D), 4);
    checkSizes(Neighborhood(NeighborhoodKind::Moore, k2D), 8);
    checkSizes(Neighborhood(NeighborhoodKind::Pentagonal, k2D), 5);
    checkSizes(Neighborhood(NeighborhoodKind::Hexagonal, k2D), 6);
    CHECK(Neighborhood(NeighborhoodKind::Pentagonal, k2D).variantCount() == 4);
    CHECK(Neighborhood(NeighborhoodKind::Hexagonal, k2D).variantCount() == 2);
    CHECK_FALSE(Neighborhood(NeighborhoodKind::Moore, k2D).isRandom());
}

TEST_CASE("Sąsiedztwa 3D: liczba sąsiadów, heksagonalne nieobsługiwane") {
    checkSizes(Neighborhood(NeighborhoodKind::VonNeumann, k3D), 6);
    checkSizes(Neighborhood(NeighborhoodKind::Moore, k3D), 26);
    checkSizes(Neighborhood(NeighborhoodKind::Pentagonal, k3D), 17);
    CHECK(Neighborhood(NeighborhoodKind::Pentagonal, k3D).variantCount() == 6);
    CHECK_THROWS_AS(Neighborhood(NeighborhoodKind::Hexagonal, k3D), std::invalid_argument);
}

TEST_CASE("Sąsiedztwo 2D leży w płaszczyźnie osi o rozmiarze > 1") {
    // Obiekty nazwane: pętla po variant(0) obiektu tymczasowego czytałaby zwolnioną pamięć
    // (czas życia tymczasowego obiektu nie jest przedłużany przez referencję do jego pola).
    const Neighborhood xz(NeighborhoodKind::Moore, k2D);
    for (const Offset& o : xz.variant(0)) {
        CHECK(o.dy == 0);
    }
    const Neighborhood xy(NeighborhoodKind::Moore, k2Dxy);
    for (const Offset& o : xy.variant(0)) {
        CHECK(o.dz == 0);
    }
}

TEST_CASE("Pentagonalne 2D: wariant usuwa całą jedną stronę (3 komórki)") {
    const Neighborhood n(NeighborhoodKind::Pentagonal, k2D);
    for (int v = 0; v < 4; ++v) {
        // Brakujące 3 komórki mają wspólną współrzędną ±1 na jednej osi.
        std::set<std::pair<int, int>> present;
        for (const Offset& o : n.variant(v)) {
            present.insert({o.dx, o.dz});
        }
        int missingSides = 0;
        for (int side = -1; side <= 1; side += 2) {
            bool allMissingX = true;
            bool allMissingZ = true;
            for (int k = -1; k <= 1; ++k) {
                allMissingX = allMissingX && !present.count({side, k});
                allMissingZ = allMissingZ && !present.count({k, side});
            }
            missingSides += (allMissingX ? 1 : 0) + (allMissingZ ? 1 : 0);
        }
        CHECK(missingSides == 1);
    }
}

TEST_CASE("Sąsiedztwo losowe: wariant zależy tylko od (seed, krok, komórka) i pokrywa wszystkie") {
    const Neighborhood n(NeighborhoodKind::Pentagonal, k3D);
    std::set<const std::vector<Offset>*> used;
    for (std::uint64_t i = 0; i < 200; ++i) {
        const auto* a = &n.offsetsFor(42, 3, i);
        CHECK(a == &n.offsetsFor(42, 3, i));
        used.insert(a);
    }
    CHECK(used.size() == 6);
}
