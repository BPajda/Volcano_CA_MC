#include "mc/Grains.hpp"

#include <stdexcept>

#include "core/Neighborhood.hpp"

namespace volcano {

namespace {

// Reprezentant zbioru z kompresją ścieżki „co drugi węzeł” (path halving).
std::uint32_t findRoot(std::vector<std::uint32_t>& parent, std::uint32_t i) {
    while (parent[i] != i) {
        parent[i] = parent[parent[i]];
        i = parent[i];
    }
    return i;
}

// Łączy zbiory a i b; reprezentantem zostaje mniejszy indeks (wynik nie zależy od kolejności).
void unite(std::vector<std::uint32_t>& parent, std::uint32_t a, std::uint32_t b) {
    a = findRoot(parent, a);
    b = findRoot(parent, b);
    if (a < b) {
        parent[b] = a;
    } else if (b < a) {
        parent[a] = b;
    }
}

// Zawija współrzędną na osi periodycznej; -1 = poza przestrzenią (oś nieperiodyczna).
int wrapOrOut(int v, int n, bool periodic) {
    if (v >= 0 && v < n) {
        return v;
    }
    if (!periodic) {
        return -1;
    }
    return v < 0 ? v + n : v - n;
}

}  // namespace

GrainLabels Grains::label(const CrystalMap& m, bool moore, const bool periodic[3]) {
    const Dims& d = m.dims;
    const std::size_t n = d.cells();
    if (n >= GrainLabels::kNone) {
        throw std::invalid_argument("za dużo komórek do etykietowania ziaren (limit 2^32 - 1)");
    }

    // Połowa przesunięć sąsiedztwa („do przodu” w kolejności z, y, x): każda para sąsiadów
    // jest rozpatrywana dokładnie raz. W 2D Neighborhood daje przesunięcia w płaszczyźnie siatki.
    std::vector<Offset> forward;
    const Neighborhood conn(moore ? NeighborhoodKind::Moore : NeighborhoodKind::VonNeumann, d);
    for (const Offset& o : conn.variant(0)) {
        if (o.dz > 0 || (o.dz == 0 && (o.dy > 0 || (o.dy == 0 && o.dx > 0)))) {
            forward.push_back(o);
        }
    }

    GrainLabels g;
    g.root.resize(n);
    for (std::size_t i = 0; i < n; ++i) {
        g.root[i] = static_cast<std::uint32_t>(i);
    }

    std::size_t i = 0;
    for (int z = 0; z < d.nz; ++z) {
        for (int y = 0; y < d.ny; ++y) {
            for (int x = 0; x < d.nx; ++x, ++i) {
                const std::int32_t s = m.crystal[i];
                if (s <= 0) {
                    continue;
                }
                for (const Offset& o : forward) {
                    const int qx = wrapOrOut(x + o.dx, d.nx, periodic[0]);
                    const int qy = wrapOrOut(y + o.dy, d.ny, periodic[1]);
                    const int qz = wrapOrOut(z + o.dz, d.nz, periodic[2]);
                    if (qx < 0 || qy < 0 || qz < 0) {
                        continue;
                    }
                    const std::size_t j = static_cast<std::size_t>(globalIndex(d, qx, qy, qz));
                    if (m.crystal[j] == s) {
                        unite(g.root, static_cast<std::uint32_t>(i), static_cast<std::uint32_t>(j));
                    }
                }
            }
        }
    }

    // Ostateczne etykiety i rozmiary ziaren.
    g.size.assign(n, 0);
    for (std::size_t k = 0; k < n; ++k) {
        if (m.crystal[k] <= 0) {
            g.root[k] = GrainLabels::kNone;
            continue;
        }
        const std::uint32_t r = findRoot(g.root, static_cast<std::uint32_t>(k));
        g.root[k] = r;
        ++g.size[r];
        ++g.cells;
        g.grains += (r == k) ? 1 : 0;
    }
    return g;
}

}  // namespace volcano
