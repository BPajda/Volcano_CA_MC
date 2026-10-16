#include "terrain/TerrainGenerator.hpp"

#include <algorithm>
#include <cmath>
#include <functional>
#include <queue>
#include <utility>

#include "core/Rng.hpp"

namespace volcano {

namespace {

// Wartość szumu w węźle siatki (i, j) oktawy o — liczba z [-1, 1] z hasha.
double latticeValue(std::uint64_t seed, int octave, int i, int j) {
    const std::uint64_t key = static_cast<std::uint64_t>(static_cast<std::uint32_t>(i)) |
                              (static_cast<std::uint64_t>(static_cast<std::uint32_t>(j)) << 32);
    return 2.0 * hashUniform(seed, static_cast<std::uint64_t>(octave), key, kSaltTerrain) - 1.0;
}

// Interpolacja z wygładzeniem (smoothstep) — bez „kantów” na granicach komórek siatki szumu.
double smooth(double t) { return t * t * (3.0 - 2.0 * t); }

// Jedna oktawa szumu wartości: siatka węzłów co `spacing` komórek, interpolacja dwuliniowa.
double valueNoise(std::uint64_t seed, int octave, int spacing, int x, int y) {
    const int i = x / spacing;
    const int j = y / spacing;
    const double fx = smooth(static_cast<double>(x % spacing) / spacing);
    const double fy = smooth(static_cast<double>(y % spacing) / spacing);
    const double v00 = latticeValue(seed, octave, i, j);
    const double v10 = latticeValue(seed, octave, i + 1, j);
    const double v01 = latticeValue(seed, octave, i, j + 1);
    const double v11 = latticeValue(seed, octave, i + 1, j + 1);
    const double a = v00 + (v10 - v00) * fx;
    const double b = v01 + (v11 - v01) * fx;
    return a + (b - a) * fy;
}

// Wysokość samego stożka (bez krateru i szumu) w odległości r od środka.
double coneHeight(const TerrainConfig& t, double r) {
    return t.peakHeight * std::max(0.0, 1.0 - r / t.baseRadius);
}

}  // namespace

double TerrainGenerator::distanceFromCenter(const Dims& d, int x, int y) {
    const double cx = (d.nx - 1) / 2.0;
    const double cy = (d.ny - 1) / 2.0;  // dla ny = 1 środek to y = 0
    return std::hypot(x - cx, y - cy);
}

double TerrainGenerator::smoothNoise(std::uint64_t seed, int x, int y) {
    // Oktawy: duże formy (co 16 komórek) + coraz drobniejsze szczegóły o mniejszej amplitudzie.
    // Biały szum (osobna wartość dla każdej kolumny) tworzyłby jamy, w których lawa grzęźnie.
    const double n = 1.0 * valueNoise(seed, 0, 16, x, y) + 0.5 * valueNoise(seed, 1, 8, x, y) +
                     0.25 * valueNoise(seed, 2, 4, x, y);
    return n / 1.75;
}

Heightmap TerrainGenerator::cone(const TerrainConfig& t, const Dims& d, std::uint64_t seed) {
    Heightmap hm;
    hm.nx = d.nx;
    hm.ny = d.ny;
    hm.height.resize(static_cast<std::size_t>(d.nx) * static_cast<std::size_t>(d.ny));

    const double amplitude = t.noise * t.peakHeight;
    // Krater: płaskie dno poniżej krawędzi. (Odjęcie craterDepth od samego stożka
    // zostawiłoby w środku krateru szczyt wyższy niż krawędź.)
    const double craterFloor = coneHeight(t, t.craterRadius) - t.craterDepth;

    for (int y = 0; y < d.ny; ++y) {
        for (int x = 0; x < d.nx; ++x) {
            const double r = distanceFromCenter(d, x, y);
            double h = (r < t.craterRadius) ? craterFloor : coneHeight(t, r);
            h += amplitude * smoothNoise(seed, x, y);
            // Komórki z < h są skałą -> liczba komórek skały = ceil(h), przycięta do [0, nz].
            const int cells = static_cast<int>(std::ceil(h));
            hm.height[static_cast<std::size_t>(x) + static_cast<std::size_t>(d.nx) * static_cast<std::size_t>(y)] =
                std::clamp(cells, 0, d.nz);
        }
    }
    return hm;
}

Heightmap TerrainGenerator::fillDepressions(const Heightmap& hm, bool periodicX, bool periodicY) {
    const int nx = hm.nx;
    const int ny = hm.ny;
    const std::size_t n = hm.height.size();
    Heightmap filled = hm;
    std::vector<bool> closed(n, false);
    using Item = std::pair<int, std::size_t>;  // (poziom, indeks kolumny)
    std::priority_queue<Item, std::vector<Item>, std::greater<Item>> open;

    auto idx = [nx](int x, int y) {
        return static_cast<std::size_t>(x) + static_cast<std::size_t>(nx) * static_cast<std::size_t>(y);
    };
    auto seed = [&](int x, int y) {
        const std::size_t i = idx(x, y);
        if (!closed[i]) {
            closed[i] = true;
            open.push({hm.height[i], i});
        }
    };

    // Ujścia: kolumny przy brzegu nieperiodycznym (oś o rozmiarze 1 nie ma brzegu).
    for (int y = 0; y < ny; ++y) {
        for (int x = 0; x < nx; ++x) {
            const bool edgeX = !periodicX && nx > 1 && (x == 0 || x == nx - 1);
            const bool edgeY = !periodicY && ny > 1 && (y == 0 || y == ny - 1);
            if (edgeX || edgeY) {
                seed(x, y);
            }
        }
    }
    if (open.empty() && n > 0) {
        // Brak brzegu (pełne zawijanie): ujściem są najniższe kolumny.
        const int lowest = *std::min_element(hm.height.begin(), hm.height.end());
        for (int y = 0; y < ny; ++y) {
            for (int x = 0; x < nx; ++x) {
                if (hm.at(x, y) == lowest) {
                    seed(x, y);
                }
            }
        }
    }

    // Zalewanie: sąsiad (4-spójność w poziomie) dostaje max(własna wysokość, poziom źródła).
    const int dx[4] = {-1, 1, 0, 0};
    const int dy[4] = {0, 0, -1, 1};
    while (!open.empty()) {
        const auto [level, i] = open.top();
        open.pop();
        const int x = static_cast<int>(i % static_cast<std::size_t>(nx));
        const int y = static_cast<int>(i / static_cast<std::size_t>(nx));
        for (int k = 0; k < 4; ++k) {
            int sx = x + dx[k];
            int sy = y + dy[k];
            if (sx < 0 || sx >= nx) {
                if (!periodicX || nx == 1) {
                    continue;  // poza mapą (brzeg absorbujący)
                }
                sx = (sx + nx) % nx;
            }
            if (sy < 0 || sy >= ny) {
                if (!periodicY || ny == 1) {
                    continue;
                }
                sy = (sy + ny) % ny;
            }
            const std::size_t j = idx(sx, sy);
            if (closed[j]) {
                continue;
            }
            closed[j] = true;
            filled.height[j] = std::max(hm.height[j], level);
            open.push({filled.height[j], j});
        }
    }
    return filled;
}

}  // namespace volcano
