#pragma once
// Sąsiedztwa automatu jako prekomputowane listy przesunięć (dx, dy, dz).
//
//   nazwa         2D                                   3D
//   von_neumann   4                                    6
//   moore         8                                    26
//   pentagonal    Moore bez jednej z 4 „stron” -> 5    Moore bez jednej z 6 ścian 3x3 -> 17
//   hexagonal     Moore bez 2 przeciwległych narożników -> 6   (nieobsługiwane)
//
// Sąsiedztwa losowe mają kilka wariantów; wariant dla komórki w danym kroku wybiera
// hashRand(seed, krok, indeks, kSaltNeighborhood) — bez stanu, więc deterministycznie.
// W 2D sąsiedztwo leży w płaszczyźnie dwóch osi o rozmiarze > 1 (np. x–z dla ny = 1).

#include <cstdint>
#include <vector>

#include "core/Rng.hpp"
#include "core/Types.hpp"

namespace volcano {

class Neighborhood {
public:
    // Buduje listy przesunięć dla podanego rodzaju i wymiarów przestrzeni.
    // Rzuca std::invalid_argument dla kombinacji nieobsługiwanych (hexagonal w 3D).
    Neighborhood(NeighborhoodKind kind, const Dims& dims);

    NeighborhoodKind kind() const { return kind_; }

    // Czy sąsiedztwo jest losowe (ma więcej niż jeden wariant).
    bool isRandom() const { return variants_.size() > 1; }

    int variantCount() const { return static_cast<int>(variants_.size()); }

    // Lista przesunięć wariantu v (0 <= v < variantCount()).
    const std::vector<Offset>& variant(int v) const {
        return variants_[static_cast<std::size_t>(v)];
    }

    // Numer wariantu dla komórki o globalnym indeksie cellIndex w kroku step (CA) albo
    // kroku MCS (Monte Carlo). Dla sąsiedztw deterministycznych zawsze 0.
    int variantFor(std::uint64_t seed, std::uint64_t step, std::uint64_t cellIndex) const {
        if (variants_.size() == 1) {
            return 0;
        }
        const std::uint64_t r = hashRand(seed, step, cellIndex, kSaltNeighborhood);
        return static_cast<int>(r % variants_.size());
    }

    // To samo co variantFor, gdy stała część hasha (seed, krok) jest już policzona — prefix = hashPrefix(seed, step)
    // (pętla prób MC, etap 8). Wynik bitowo ten sam.
    int variantFromPrefix(std::uint64_t prefix, std::uint64_t cellIndex) const {
        if (variants_.size() == 1) {
            return 0;
        }
        const std::uint64_t r = hashSalt(hashIndex(prefix, cellIndex), kSaltNeighborhood);
        return static_cast<int>(r % variants_.size());
    }

    // Przesunięcia sąsiadów komórki o globalnym indeksie cellIndex w kroku step.
    // Dla sąsiedztw deterministycznych zawsze ten sam (jedyny) wariant.
    const std::vector<Offset>& offsetsFor(std::uint64_t seed, std::uint64_t step,
                                          std::uint64_t cellIndex) const {
        return variants_[static_cast<std::size_t>(variantFor(seed, step, cellIndex))];
    }

    // Największa liczba sąsiadów spośród wariantów (rozmiar buforów kandydatów).
    int maxSize() const;

    // Nazwa do plików wynikowych i tabel.
    static const char* name(NeighborhoodKind kind);

private:
    NeighborhoodKind kind_;
    std::vector<std::vector<Offset>> variants_;
};

}  // namespace volcano
