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

    // OPTYMALIZACJA (etap 8, k5): komórka, której sąsiedzi „do przodu” nie wychodzą poza przestrzeń w żadnej osi
    // (wnętrze — prawie wszystkie komórki), sięga do nich przez stałe przesunięcie liniowe w tablicy bez ramki,
    // bez zawijania współrzędnych i liczenia globalIndex; reprezentant komórki jest liczony raz, a nie przy każdym
    // połączeniu. Wynik bitowo ten sam: składowe spójności nie zależą od kolejności połączeń, a reprezentantem
    // każdego ziarna jest zawsze jego najmniejszy indeks (join zostawia mniejszy reprezentanta).
    // Dodatkowo: gdy sąsiad x+1 ma tę samą orientację (będzie w tym samym ziarnie), sąsiedzi „do przodu” komórki
    // wspólni z sąsiadami x+1 (przesunięcie o − (1,0,0) też jest „do przodu”) są pomijani — połączy je komórka x+1
    // (Moore 3D: 8 z 13 sprawdzeń; von Neumann: brak wspólnych).
    const std::ptrdiff_t snx = d.nx;
    const std::ptrdiff_t sny = d.ny;
    const auto isForward = [&](int dx, int dy, int dz) {
        for (const Offset& f : forward) {
            if (f.dx == dx && f.dy == dy && f.dz == dz) {
                return true;
            }
        }
        return false;
    };
    const bool plusX = isForward(1, 0, 0);
    std::vector<std::ptrdiff_t> forwardLin;    // sprawdzane zawsze
    std::vector<std::ptrdiff_t> coveredByNext;  // sprawdzane tylko, gdy x+1 ma inną orientację
    for (const Offset& o : forward) {
        const std::ptrdiff_t lin = o.dx + snx * (o.dy + sny * o.dz);
        (plusX && isForward(o.dx - 1, o.dy, o.dz) ? coveredByNext : forwardLin).push_back(lin);
    }
    const auto innerAxis = [](int v, int n) { return n == 1 || (v >= 1 && v <= n - 2); };

    GrainLabels g;
    g.root.resize(n);
    for (std::size_t i = 0; i < n; ++i) {
        g.root[i] = static_cast<std::uint32_t>(i);
    }

    std::size_t i = 0;
    for (int z = 0; z < d.nz; ++z) {
        for (int y = 0; y < d.ny; ++y) {
            const bool innerYZ = innerAxis(y, d.ny) && (d.nz == 1 || z <= d.nz - 2);
            for (int x = 0; x < d.nx; ++x, ++i) {
                const std::int32_t s = m.crystal[i];
                if (s <= 0) {
                    continue;
                }
                std::uint32_t ri = findRoot(g.root, static_cast<std::uint32_t>(i));
                // Połączenie zbioru komórki i (reprezentant ri) ze zbiorem komórki j; mniejszy reprezentant zostaje.
                const auto join = [&](std::size_t j) {
                    const std::uint32_t rj = findRoot(g.root, static_cast<std::uint32_t>(j));
                    if (rj < ri) {
                        g.root[ri] = rj;
                        ri = rj;
                    } else if (ri < rj) {
                        g.root[rj] = ri;
                    }
                };
                if (innerYZ && innerAxis(x, d.nx)) {
                    const std::int32_t* const c = m.crystal.data() + i;
                    for (const std::ptrdiff_t lin : forwardLin) {
                        if (c[lin] == s) {
                            join(static_cast<std::size_t>(static_cast<std::ptrdiff_t>(i) + lin));
                        }
                    }
                    if (plusX && c[1] == s) {
                        continue;  // wspólnych sąsiadów połączy komórka x+1 (wnętrze: ten sam wiersz)
                    }
                    for (const std::ptrdiff_t lin : coveredByNext) {
                        if (c[lin] == s) {
                            join(static_cast<std::size_t>(static_cast<std::ptrdiff_t>(i) + lin));
                        }
                    }
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
                        join(j);
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
