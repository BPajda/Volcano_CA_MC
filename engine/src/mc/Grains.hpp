#pragma once
// Wyznaczanie ziaren (kryształów) w mapie orientacji: spójne składowe komórek o tej samej
// orientacji > 0. Algorytm union-find (las zbiorów rozłącznych z kompresją ścieżek),
// O(N · α(N)) — jeden przebieg po siatce, bez kolejki BFS i bez rekurencji.
// Spójność: von Neumann (tylko ściany) albo Moore (ściany, krawędzie, narożniki) —
// wybór opisany w McRules.hpp. Brzegi periodyczne łączą ziarna przez krawędź przestrzeni.
// Od etapu 8 komórki wnętrza sięgają do sąsiadów przez stałe przesunięcie liniowe (bez zawijania),
// zawijanie współrzędnych zostaje tylko dla komórek przy brzegu (statystyki MC ~2× tańsze).

#include <cstddef>
#include <cstdint>
#include <vector>

#include "core/Types.hpp"

namespace volcano {

// Wynik etykietowania ziaren.
struct GrainLabels {
    static constexpr std::uint32_t kNone = 0xFFFFFFFFu;  // komórka poza domeną (orientacja 0)

    std::vector<std::uint32_t> root;  // reprezentant ziarna każdej komórki (indeks globalIndex) lub kNone
    std::vector<std::uint32_t> size;  // size[r] = liczba komórek ziarna, którego reprezentantem jest r
    std::uint64_t grains = 0;         // liczba ziaren
    std::uint64_t cells = 0;          // liczba komórek domeny (orientacja > 0)

    // Zajętość pamięci [B] (model pamięci, etap 3).
    std::size_t bytes() const { return root.size() * sizeof(std::uint32_t) + size.size() * sizeof(std::uint32_t); }

    // Pamięć etykiet dla n komórek [B] — do modelu przed wywołaniem Grains::label.
    static std::size_t bytesFor(std::size_t n) { return 2 * n * sizeof(std::uint32_t); }
};

class Grains {
public:
    // Etykietuje ziarna mapy m. moore = spójność Moore'a (inaczej von Neumanna);
    // periodic[a] = czy oś a (x, y, z) jest zawijana.
    static GrainLabels label(const CrystalMap& m, bool moore, const bool periodic[3]);
};

}  // namespace volcano
