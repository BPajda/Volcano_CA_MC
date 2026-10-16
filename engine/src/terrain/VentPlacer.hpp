#pragma once
// Rozmieszczenie kraterów (tryb lava) i zarodków ziaren (tryb classic).
//
// Krater = pierwsza komórka AIR nad powierzchnią terenu, czyli (x, y, h(x,y)).
//   placement "crater": losowe kolumny w promieniu craterRadius od środka (krater szczytowy),
//   placement "random": losowe kolumny zbocza poza kraterem (szczeliny boczne),
//   placement "positions": kolumny z listy vents.positions (prawdziwe wulkany — etap 6), bez losowania.
// Zarodek (classic) = losowa komórka całej przestrzeni.
//
// Położenia są unikalne. Losowanie: mt19937_64 + częściowe tasowanie Fishera–Yatesa
// (deterministyczne na każdym kompilatorze — patrz Rng.hpp). Kratery dostają flowId 1..count.

#include <cstdint>
#include <utility>
#include <vector>

#include "core/Types.hpp"
#include "io/Config.hpp"
#include "terrain/TerrainGenerator.hpp"

namespace volcano {

// Krater / zarodek: położenie i ID „ziarna”.
struct Vent {
    int x;
    int y;
    int z;
    std::int32_t flowId;
};

class VentPlacer {
public:
    // Kratery na powierzchni terenu (crater, random). Rzuca ConfigError, gdy jest za mało miejsc.
    // placement = positions rozmieszcza placeAt (lista z Config::ventColumns(), Simulation::buildVents).
    static std::vector<Vent> placeVents(const VentsConfig& v, const TerrainConfig& t, const Dims& d,
                                        const Heightmap& hm, std::uint64_t seed);

    // Kratery w podanych kolumnach (placement = positions), flowId = numer na liście + 1.
    // Rzuca ConfigError, gdy kolumna leży poza siatką albo jest w całości skałą (h >= nz).
    static std::vector<Vent> placeAt(const std::vector<std::pair<int, int>>& columns, const Dims& d,
                                     const Heightmap& hm);

    // Zarodki w losowych, różnych komórkach całej przestrzeni (count <= liczba komórek).
    static std::vector<Vent> placeSeeds(int count, const Dims& d, std::uint64_t seed);
};

}  // namespace volcano
