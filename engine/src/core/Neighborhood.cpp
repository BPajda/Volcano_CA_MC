#include "core/Neighborhood.hpp"

#include <algorithm>
#include <cstdlib>
#include <functional>
#include <stdexcept>

namespace volcano {

namespace {

// Predykat „czy przesunięcie (u, v[, w]) należy do wariantu”.
using Filter2D = std::function<bool(int u, int v)>;
using Filter3D = std::function<bool(int dx, int dy, int dz)>;

// Generuje sąsiedztwo 2D w płaszczyźnie osi axisA (u) i axisB (v) i zamienia
// współrzędne płaszczyzny na (dx, dy, dz). Kolejność: v zewnętrznie, u wewnętrznie.
std::vector<Offset> build2D(int axisA, int axisB, const Filter2D& keep) {
    std::vector<Offset> out;
    for (int v = -1; v <= 1; ++v) {
        for (int u = -1; u <= 1; ++u) {
            if ((u == 0 && v == 0) || !keep(u, v)) {
                continue;
            }
            int d[3] = {0, 0, 0};
            d[axisA] = u;
            d[axisB] = v;
            out.push_back(Offset{d[0], d[1], d[2]});
        }
    }
    return out;
}

// Generuje sąsiedztwo 3D (kolejność: dz, dy, dx — zgodna z układem pamięci).
std::vector<Offset> build3D(const Filter3D& keep) {
    std::vector<Offset> out;
    for (int dz = -1; dz <= 1; ++dz) {
        for (int dy = -1; dy <= 1; ++dy) {
            for (int dx = -1; dx <= 1; ++dx) {
                if ((dx == 0 && dy == 0 && dz == 0) || !keep(dx, dy, dz)) {
                    continue;
                }
                out.push_back(Offset{dx, dy, dz});
            }
        }
    }
    return out;
}

// Odległość „taksówkowa” przesunięcia — 1 oznacza sąsiada przez ścianę/krawędź (von Neumann).
int manhattan(int a, int b, int c = 0) { return std::abs(a) + std::abs(b) + std::abs(c); }

}  // namespace

Neighborhood::Neighborhood(NeighborhoodKind kind, const Dims& dims) : kind_(kind) {
    const int axes = dims.activeAxes();
    if (axes < 2) {
        throw std::invalid_argument("sąsiedztwo wymaga przestrzeni 2D lub 3D");
    }

    if (axes == 2) {
        // Dwie osie o rozmiarze > 1 wyznaczają płaszczyznę automatu.
        const int sizes[3] = {dims.nx, dims.ny, dims.nz};
        int plane[2] = {0, 0};
        int k = 0;
        for (int a = 0; a < 3; ++a) {
            if (sizes[a] > 1) {
                plane[k++] = a;
            }
        }
        const int A = plane[0];
        const int B = plane[1];
        switch (kind) {
            case NeighborhoodKind::VonNeumann:
                variants_.push_back(build2D(A, B, [](int u, int v) { return manhattan(u, v) == 1; }));
                break;
            case NeighborhoodKind::Moore:
                variants_.push_back(build2D(A, B, [](int, int) { return true; }));
                break;
            case NeighborhoodKind::Pentagonal:
                // 4 warianty: Moore bez jednej „strony” (3 komórek) -> 5 sąsiadów.
                variants_.push_back(build2D(A, B, [](int u, int) { return u != -1; }));
                variants_.push_back(build2D(A, B, [](int u, int) { return u != 1; }));
                variants_.push_back(build2D(A, B, [](int, int v) { return v != -1; }));
                variants_.push_back(build2D(A, B, [](int, int v) { return v != 1; }));
                break;
            case NeighborhoodKind::Hexagonal:
                // 2 warianty: Moore bez dwóch przeciwległych narożników -> 6 sąsiadów.
                variants_.push_back(build2D(A, B, [](int u, int v) {
                    return !((u == -1 && v == -1) || (u == 1 && v == 1));
                }));
                variants_.push_back(build2D(A, B, [](int u, int v) {
                    return !((u == -1 && v == 1) || (u == 1 && v == -1));
                }));
                break;
        }
    } else {
        switch (kind) {
            case NeighborhoodKind::VonNeumann:
                variants_.push_back(build3D([](int dx, int dy, int dz) { return manhattan(dx, dy, dz) == 1; }));
                break;
            case NeighborhoodKind::Moore:
                variants_.push_back(build3D([](int, int, int) { return true; }));
                break;
            case NeighborhoodKind::Pentagonal:
                // 6 wariantów: Moore26 bez jednej z 6 ścian 3x3 (9 komórek) -> 17 sąsiadów.
                variants_.push_back(build3D([](int dx, int, int) { return dx != -1; }));
                variants_.push_back(build3D([](int dx, int, int) { return dx != 1; }));
                variants_.push_back(build3D([](int, int dy, int) { return dy != -1; }));
                variants_.push_back(build3D([](int, int dy, int) { return dy != 1; }));
                variants_.push_back(build3D([](int, int, int dz) { return dz != -1; }));
                variants_.push_back(build3D([](int, int, int dz) { return dz != 1; }));
                break;
            case NeighborhoodKind::Hexagonal:
                // Heksagonalne jest zdefiniowane na płaszczyźnie; w 3D brak jednoznacznej definicji.
                throw std::invalid_argument("sąsiedztwo heksagonalne jest zdefiniowane tylko w 2D");
        }
    }
}

int Neighborhood::maxSize() const {
    std::size_t m = 0;
    for (const auto& v : variants_) {
        m = std::max(m, v.size());
    }
    return static_cast<int>(m);
}

const char* Neighborhood::name(NeighborhoodKind kind) {
    switch (kind) {
        case NeighborhoodKind::VonNeumann: return "von_neumann";
        case NeighborhoodKind::Moore: return "moore";
        case NeighborhoodKind::Pentagonal: return "pentagonal";
        case NeighborhoodKind::Hexagonal: return "hexagonal";
    }
    return "?";
}

}  // namespace volcano
