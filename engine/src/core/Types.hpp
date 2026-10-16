#pragma once
// Podstawowe typy wspólne dla całego silnika: stany komórek, wymiary przestrzeni,
// rodzaje sąsiedztw / warunków brzegowych / trybów oraz „mikrostruktura” —
// płaski (bez ramki) zapis wyniku symulacji używany do zapisu, statystyk i porównań.

#include <cstddef>
#include <cstdint>
#include <vector>

namespace volcano {

// Typ komórki (woksela). Wartości liczbowe są częścią formatu plików wynikowych.
enum class CellType : std::uint8_t {
    Air = 0,     // powietrze — tu może wpłynąć lawa
    Rock = 1,    // skała (teren)
    Lava = 2,    // płynna lawa (w trybie classic: komórka należąca do ziarna)
    Basalt = 3,  // zastygła lawa
    Void = 255   // „pustka” w ramce przy brzegu absorbującym — nigdy nie jest sąsiadem z lawą
};

// Rodzaje sąsiedztwa (nazwy w configu: von_neumann, moore, pentagonal, hexagonal).
enum class NeighborhoodKind { VonNeumann, Moore, Pentagonal, Hexagonal };

// Warunki brzegowe (nazwy w configu: absorbing, periodic).
enum class BoundaryKind { Absorbing, Periodic };

// Tryb automatu: spływ lawy albo klasyczny rozrost ziaren (do porównań z referencją).
enum class CaMode { Lava, Classic };

// Domena krystalizacji Monte Carlo: komórki bazaltu z wyniku CA albo cała przestrzeń
// (klasyczny naiwny rozrost ziaren MC, bez terenu i bez CA).
enum class McDomain { Basalt, Full };

// Reprezentacja siatki: płaski std::vector albo macierz 3D (vector<vector<vector>>).
enum class GridKind { Vector, Matrix };

// Wymiary przestrzeni. Oś z jest pionowa (grawitacja w dół, z = 0 to spód).
struct Dims {
    int nx = 1;
    int ny = 1;
    int nz = 1;

    // Liczba komórek wnętrza (bez ramki).
    std::size_t cells() const {
        return static_cast<std::size_t>(nx) * static_cast<std::size_t>(ny) *
               static_cast<std::size_t>(nz);
    }

    // Liczba wymiarów o rozmiarze > 1 (2 = przestrzeń 2D, 3 = 3D).
    int activeAxes() const { return (nx > 1 ? 1 : 0) + (ny > 1 ? 1 : 0) + (nz > 1 ? 1 : 0); }

    bool is2D() const { return activeAxes() == 2; }

    friend bool operator==(const Dims& a, const Dims& b) {
        return a.nx == b.nx && a.ny == b.ny && a.nz == b.nz;
    }
    friend bool operator!=(const Dims& a, const Dims& b) { return !(a == b); }
};

// Przesunięcie do sąsiada.
struct Offset {
    int dx;
    int dy;
    int dz;
};

// Pełny stan jednej komórki — używany przy kopiowaniu komórek (ramka, przepisanie do next).
// Czas w stanie płynnym = solidStep - arrivalStep; od niego zależy mobilność komórki
// w krystalizacji Monte Carlo (mc/McRules.hpp).
struct CellState {
    CellType type = CellType::Air;
    std::int32_t flowId = 0;        // ID krateru / ziarna (0 = brak)
    float temp = 0.0f;              // temperatura [°C]
    std::uint16_t solidStep = 0;    // krok zastygnięcia (BASALT)
    std::uint16_t arrivalStep = 0;  // krok, w którym komórka stała się lawą (kratery: 0)
};

// Globalny indeks komórki bez ramki: x + nx*(y + ny*z).
// Nie zależy od reprezentacji siatki ani (w wersji równoległej) od podziału na wątki/procesy,
// dlatego jest wejściem do deterministycznej losowości (Rng.hpp).
inline std::uint64_t globalIndex(const Dims& d, int x, int y, int z) {
    return static_cast<std::uint64_t>(x) +
           static_cast<std::uint64_t>(d.nx) *
               (static_cast<std::uint64_t>(y) +
                static_cast<std::uint64_t>(d.ny) * static_cast<std::uint64_t>(z));
}

// Mikrostruktura końcowa: płaskie tablice SoA bez ramki, indeks globalIndex(x,y,z).
// Niezależna od reprezentacji siatki — na niej działa zapis wyników, statystyki,
// porównanie vector vs macierz i krystalizacja MC (także uruchamiana z pliku).
struct Microstructure {
    Dims dims;
    std::vector<CellType> type;
    std::vector<std::int32_t> flowId;
    std::vector<float> temp;
    std::vector<std::uint16_t> solidStep;
    std::vector<std::uint16_t> arrivalStep;

    // Alokuje tablice dla podanych wymiarów (wszystko AIR / 0).
    void resize(const Dims& d) {
        dims = d;
        const std::size_t n = d.cells();
        type.assign(n, CellType::Air);
        flowId.assign(n, 0);
        temp.assign(n, 0.0f);
        solidStep.assign(n, 0);
        arrivalStep.assign(n, 0);
    }

    std::size_t index(int x, int y, int z) const {
        return static_cast<std::size_t>(globalIndex(dims, x, y, z));
    }

    // Zajętość pamięci przez tablice [B] (model pamięci, etap 3).
    std::size_t bytes() const {
        return type.size() * sizeof(CellType) + flowId.size() * sizeof(std::int32_t) +
               temp.size() * sizeof(float) + solidStep.size() * sizeof(std::uint16_t) +
               arrivalStep.size() * sizeof(std::uint16_t);
    }
};

// Mapa kryształów — wynik krystalizacji Monte Carlo: orientacja (ID kryształu 1..Q)
// każdej komórki, 0 poza domeną MC. Indeks globalIndex(x,y,z), bez ramki.
struct CrystalMap {
    Dims dims;
    std::vector<std::int32_t> crystal;

    // Zajętość pamięci [B] (model pamięci, etap 3).
    std::size_t bytes() const { return crystal.size() * sizeof(std::int32_t); }
};

}  // namespace volcano
