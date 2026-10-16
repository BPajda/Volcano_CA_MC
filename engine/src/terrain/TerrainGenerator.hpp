#pragma once
// Generator terenu: stożek wulkanu z kraterem na szczycie i gładkim szumem.
//
//   h(x,y) = peakHeight * max(0, 1 - r/baseRadius) + szum,     r = odległość od środka mapy
//   w kraterze (r < craterRadius): płaskie dno na wysokości krawędzi minus craterDepth
//
// Komórki z < h(x,y) są skałą (ROCK). Dla 2D (ny = 1) to samo w przekroju: r = |x - środek|.
// Teren jest opisany mapą wysokości (Heightmap) — wspólną dla obu reprezentacji siatki.

#include <cstdint>
#include <vector>

#include "core/Types.hpp"
#include "io/Config.hpp"

namespace volcano {

// Mapa wysokości: liczba komórek skały w każdej kolumnie (x, y).
// Kolumna o wysokości h ma ROCK w z = 0..h-1, a pierwsza komórka AIR to z = h.
struct Heightmap {
    int nx = 0;
    int ny = 0;
    std::vector<int> height;  // indeks x + nx*y

    int at(int x, int y) const {
        return height[static_cast<std::size_t>(x) + static_cast<std::size_t>(nx) * static_cast<std::size_t>(y)];
    }
    bool empty() const { return height.empty(); }
};

class TerrainGenerator {
public:
    // Stożek wulkanu z kraterem i szumem dla przestrzeni d. Wysokości są przycinane do [0, nz].
    static Heightmap cone(const TerrainConfig& t, const Dims& d, std::uint64_t seed);

    // Pozioma odległość kolumny (x, y) od środka mapy (w 2D: |x - środek|).
    static double distanceFromCenter(const Dims& d, int x, int y);

    // Gładki szum wartości z hasha w zakresie [-1, 1] (3 oktawy, interpolacja smoothstep).
    // Deterministyczny: zależy tylko od seed i (x, y).
    static double smoothNoise(std::uint64_t seed, int x, int y);

    // Poziom przelewu każdej kolumny: do jakiej wysokości wypełniłaby się zamknięta niecka
    // terenu (krater, dołek), zanim ciecz wyleje się przez najniższy punkt krawędzi.
    // Algorytm priority-flood (Barnes, Lehman, Mulla 2014): zalewanie od „ujść” w kolejności
    // rosnącej wysokości. Ujścia to kolumny na brzegu nieperiodycznym (lawa wypływa poza
    // mapę); gdy obie osie poziome są periodyczne — kolumny o najmniejszej wysokości.
    // Wynik >= wysokość terenu; równość oznacza kolumnę spoza niecki.
    static Heightmap fillDepressions(const Heightmap& hm, bool periodicX, bool periodicY);
};

}  // namespace volcano
