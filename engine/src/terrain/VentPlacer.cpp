#include "terrain/VentPlacer.hpp"

#include <random>
#include <string>
#include <utility>

#include "core/Rng.hpp"

namespace volcano {

std::vector<Vent> VentPlacer::placeVents(const VentsConfig& v, const TerrainConfig& t, const Dims& d,
                                         const Heightmap& hm, std::uint64_t seed) {
    if (v.placement == VentPlacement::Positions) {
        throw ConfigError("vents.placement = \"positions\": kratery rozmieszcza VentPlacer::placeAt "
                          "(lista z Config::ventColumns())");
    }
    // 1. Kolumny-kandydaci (w ustalonej kolejności y, x — wynik nie zależy od niczego innego).
    std::vector<std::pair<int, int>> candidates;
    for (int y = 0; y < d.ny; ++y) {
        for (int x = 0; x < d.nx; ++x) {
            const int h = hm.at(x, y);
            if (h >= d.nz) {
                continue;  // kolumna pełna skały — nad nią nie ma miejsca na krater
            }
            const double r = TerrainGenerator::distanceFromCenter(d, x, y);
            bool ok = false;
            if (v.placement == VentPlacement::Crater) {
                ok = r <= t.craterRadius;
            } else {
                // Zbocze: poza kraterem, na terenie (h >= 1); dla stożka także w jego obrębie.
                ok = r > t.craterRadius && h >= 1 &&
                     (t.type != TerrainType::Cone || r < t.baseRadius);
            }
            if (ok) {
                candidates.emplace_back(x, y);
            }
        }
    }
    if (static_cast<int>(candidates.size()) < v.count) {
        throw ConfigError(std::string("Za mało miejsc na kratery (placement = ") +
                          (v.placement == VentPlacement::Crater ? "crater" : "random") + "): dostępnych " +
                          std::to_string(candidates.size()) + ", a vents.count = " + std::to_string(v.count) +
                          (v.placement == VentPlacement::Crater ? " — zwiększ terrain.craterRadius" : ""));
    }

    // 2. Częściowe tasowanie Fishera–Yatesa: pierwsze count elementów to losowy wybór bez powtórzeń.
    std::mt19937_64 gen(splitmix64(seed ^ kSaltVents));
    std::vector<Vent> vents;
    vents.reserve(static_cast<std::size_t>(v.count));
    for (int i = 0; i < v.count; ++i) {
        const std::size_t remaining = candidates.size() - static_cast<std::size_t>(i);
        const std::size_t j = static_cast<std::size_t>(i) + static_cast<std::size_t>(uniformBelow(gen, remaining));
        std::swap(candidates[static_cast<std::size_t>(i)], candidates[j]);
        const auto [x, y] = candidates[static_cast<std::size_t>(i)];
        vents.push_back(Vent{x, y, hm.at(x, y), i + 1});
    }
    return vents;
}

std::vector<Vent> VentPlacer::placeAt(const std::vector<std::pair<int, int>>& columns, const Dims& d,
                                      const Heightmap& hm) {
    std::vector<Vent> vents;
    vents.reserve(columns.size());
    for (std::size_t i = 0; i < columns.size(); ++i) {
        const int cx = columns[i].first;
        const int cy = columns[i].second;
        const std::string where = "vents.positions[" + std::to_string(i) + "] = [" + std::to_string(cx) + ", " +
                                  std::to_string(cy) + "]";
        if (cx < 0 || cx >= d.nx || cy < 0 || cy >= d.ny) {
            throw ConfigError(where + " leży poza siatką " + std::to_string(d.nx) + " x " + std::to_string(d.ny));
        }
        const int h = hm.empty() ? 0 : hm.at(cx, cy);
        if (h >= d.nz) {
            throw ConfigError(where + ": kolumna jest w całości skałą (wysokość terenu " + std::to_string(h) +
                              " >= space.nz = " + std::to_string(d.nz) +
                              ") — nad nią nie ma miejsca na krater; zwiększ space.nz albo wybierz inną kolumnę");
        }
        vents.push_back(Vent{cx, cy, h, static_cast<std::int32_t>(i + 1)});
    }
    return vents;
}

std::vector<Vent> VentPlacer::placeSeeds(int count, const Dims& d, std::uint64_t seed) {
    const std::uint64_t n = d.cells();
    std::mt19937_64 gen(splitmix64(seed ^ kSaltVents));
    std::vector<bool> taken(static_cast<std::size_t>(n), false);
    std::vector<Vent> seeds;
    seeds.reserve(static_cast<std::size_t>(count));
    // Losowanie z odrzucaniem powtórzeń — liczba zarodków jest zwykle << liczby komórek.
    while (static_cast<int>(seeds.size()) < count) {
        const std::uint64_t idx = uniformBelow(gen, n);
        if (taken[static_cast<std::size_t>(idx)]) {
            continue;
        }
        taken[static_cast<std::size_t>(idx)] = true;
        const int x = static_cast<int>(idx % static_cast<std::uint64_t>(d.nx));
        const int y = static_cast<int>((idx / static_cast<std::uint64_t>(d.nx)) % static_cast<std::uint64_t>(d.ny));
        const int z = static_cast<int>(idx / (static_cast<std::uint64_t>(d.nx) * static_cast<std::uint64_t>(d.ny)));
        seeds.push_back(Vent{x, y, z, static_cast<std::int32_t>(seeds.size() + 1)});
    }
    return seeds;
}

}  // namespace volcano
