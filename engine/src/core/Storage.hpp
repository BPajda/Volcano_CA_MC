#pragma once
// Dwie reprezentacje siatki komórek (porównanie w benchmarku vector vs macierz):
//
//   VectorStorage  — jedna płaska std::vector<T> na każde pole (SoA),
//                    indeks (x+1) + (nx+2)*((y+1) + (ny+2)*(z+1)),
//   MatrixStorage  — std::vector<std::vector<std::vector<T>>> na każde pole,
//                    dostęp [z+1][y+1][x+1].
//
// Obie mają ramkę 1 komórki dookoła (współrzędne -1 i n są poprawne) — warunki
// brzegowe to wypełnienie ramki przed krokiem, a w wersji równoległej ramka stanie się
// komórkami nadmiarowymi (ghost cells) przy podziale MPI.
//
// Obie klasy mają identyczny interfejs, ale NIE dziedziczą po wspólnej klasie bazowej:
// algorytm (LavaCA<Storage>) jest szablonem, więc dostęp do komórki jest funkcją inline,
// bez wywołań wirtualnych w gorącej pętli. Jeden obiekt Storage = jeden bufor;
// automat trzyma dwa (cur, next) i zamienia je metodą swap() — bez kopiowania danych.

#include <cassert>
#include <cstddef>
#include <cstdint>
#include <utility>
#include <vector>

#include "core/Profile.hpp"
#include "core/Types.hpp"

namespace volcano {

// ---------------------------------------------------------------------------
// Płaska tablica — główna reprezentacja (ciągła pamięć, przyjazna cache i MPI).
// ---------------------------------------------------------------------------
class VectorStorage {
public:
    static constexpr const char* kName = "vector";

    VectorStorage() = default;

    // Alokuje wszystkie pola z ramką; wnętrze i ramka = AIR / 0.
    explicit VectorStorage(const Dims& d)
        : dims_(d),
          sx_(static_cast<std::size_t>(d.nx) + 2),
          sy_(static_cast<std::size_t>(d.ny) + 2) {
        const std::size_t n = sx_ * sy_ * (static_cast<std::size_t>(d.nz) + 2);
        type_.assign(n, CellType::Air);
        flowId_.assign(n, 0);
        temp_.assign(n, 0.0f);
        solidStep_.assign(n, 0);
        arrivalStep_.assign(n, 0);
    }

    const Dims& dims() const { return dims_; }
    int nx() const { return dims_.nx; }
    int ny() const { return dims_.ny; }
    int nz() const { return dims_.nz; }

    // --- dostęp do pól (współrzędne od -1 do n włącznie) ---
    CellType type(int x, int y, int z) const { return type_[index(x, y, z)]; }
    std::int32_t flowId(int x, int y, int z) const { return flowId_[index(x, y, z)]; }
    float temp(int x, int y, int z) const { return temp_[index(x, y, z)]; }
    std::uint16_t solidStep(int x, int y, int z) const { return solidStep_[index(x, y, z)]; }
    std::uint16_t arrivalStep(int x, int y, int z) const { return arrivalStep_[index(x, y, z)]; }

    void setType(int x, int y, int z, CellType v) { type_[index(x, y, z)] = v; }
    void setFlowId(int x, int y, int z, std::int32_t v) { flowId_[index(x, y, z)] = v; }
    void setTemp(int x, int y, int z, float v) { temp_[index(x, y, z)] = v; }
    void setSolidStep(int x, int y, int z, std::uint16_t v) { solidStep_[index(x, y, z)] = v; }
    void setArrivalStep(int x, int y, int z, std::uint16_t v) { arrivalStep_[index(x, y, z)] = v; }

    // Cały stan komórki naraz (kopiowanie ramki, przepisanie niezmienionej komórki).
    CellState cell(int x, int y, int z) const {
        const std::size_t i = index(x, y, z);
        return CellState{type_[i], flowId_[i], temp_[i], solidStep_[i], arrivalStep_[i]};
    }
    void setCell(int x, int y, int z, const CellState& c) {
        const std::size_t i = index(x, y, z);
        type_[i] = c.type;
        flowId_[i] = c.flowId;
        temp_[i] = c.temp;
        solidStep_[i] = c.solidStep;
        arrivalStep_[i] = c.arrivalStep;
    }

    // Zamiana buforów w O(1) — zamieniane są tylko wskaźniki wewnątrz std::vector.
    void swap(VectorStorage& other) noexcept {
        std::swap(dims_, other.dims_);
        std::swap(sx_, other.sx_);
        std::swap(sy_, other.sy_);
        type_.swap(other.type_);
        flowId_.swap(other.flowId_);
        temp_.swap(other.temp_);
        solidStep_.swap(other.solidStep_);
        arrivalStep_.swap(other.arrivalStep_);
    }

    // Zajętość pamięci przez dane komórek [B] (do profilu, etap 3).
    std::size_t bytes() const {
        return type_.size() * (sizeof(CellType) + sizeof(std::int32_t) + sizeof(float) +
                               2 * sizeof(std::uint16_t));
    }

private:
    // Indeks w płaskiej tablicy z ramką; asercja łapie wyjście poza ramkę (Debug).
    std::size_t index(int x, int y, int z) const {
        assert(x >= -1 && x <= dims_.nx && y >= -1 && y <= dims_.ny && z >= -1 && z <= dims_.nz);
        return static_cast<std::size_t>(x + 1) +
               sx_ * (static_cast<std::size_t>(y + 1) + sy_ * static_cast<std::size_t>(z + 1));
    }

    Dims dims_;
    std::size_t sx_ = 0;  // nx + 2
    std::size_t sy_ = 0;  // ny + 2
    std::vector<CellType> type_;
    std::vector<std::int32_t> flowId_;
    std::vector<float> temp_;
    std::vector<std::uint16_t> solidStep_;
    std::vector<std::uint16_t> arrivalStep_;
};

// ---------------------------------------------------------------------------
// Macierz 3D — vector<vector<vector<T>>>: każdy wiersz x to osobna alokacja,
// więc dostęp wymaga dwóch dodatkowych odczytów wskaźników, a dane są rozproszone
// w pamięci. Służy do porównania wydajności z VectorStorage.
// ---------------------------------------------------------------------------
class MatrixStorage {
public:
    static constexpr const char* kName = "matrix";

    template <class T>
    using Matrix3 = std::vector<std::vector<std::vector<T>>>;

    MatrixStorage() = default;

    explicit MatrixStorage(const Dims& d) : dims_(d) {
        type_ = make<CellType>(CellType::Air);
        flowId_ = make<std::int32_t>(0);
        temp_ = make<float>(0.0f);
        solidStep_ = make<std::uint16_t>(0);
        arrivalStep_ = make<std::uint16_t>(0);
    }

    const Dims& dims() const { return dims_; }
    int nx() const { return dims_.nx; }
    int ny() const { return dims_.ny; }
    int nz() const { return dims_.nz; }

    CellType type(int x, int y, int z) const { return type_[at(z)][at(y)][at(x)]; }
    std::int32_t flowId(int x, int y, int z) const { return flowId_[at(z)][at(y)][at(x)]; }
    float temp(int x, int y, int z) const { return temp_[at(z)][at(y)][at(x)]; }
    std::uint16_t solidStep(int x, int y, int z) const { return solidStep_[at(z)][at(y)][at(x)]; }
    std::uint16_t arrivalStep(int x, int y, int z) const { return arrivalStep_[at(z)][at(y)][at(x)]; }

    void setType(int x, int y, int z, CellType v) { type_[at(z)][at(y)][at(x)] = v; }
    void setFlowId(int x, int y, int z, std::int32_t v) { flowId_[at(z)][at(y)][at(x)] = v; }
    void setTemp(int x, int y, int z, float v) { temp_[at(z)][at(y)][at(x)] = v; }
    void setSolidStep(int x, int y, int z, std::uint16_t v) { solidStep_[at(z)][at(y)][at(x)] = v; }
    void setArrivalStep(int x, int y, int z, std::uint16_t v) { arrivalStep_[at(z)][at(y)][at(x)] = v; }

    CellState cell(int x, int y, int z) const {
        return CellState{type(x, y, z), flowId(x, y, z), temp(x, y, z), solidStep(x, y, z),
                         arrivalStep(x, y, z)};
    }
    void setCell(int x, int y, int z, const CellState& c) {
        setType(x, y, z, c.type);
        setFlowId(x, y, z, c.flowId);
        setTemp(x, y, z, c.temp);
        setSolidStep(x, y, z, c.solidStep);
        setArrivalStep(x, y, z, c.arrivalStep);
    }

    void swap(MatrixStorage& other) noexcept {
        std::swap(dims_, other.dims_);
        type_.swap(other.type_);
        flowId_.swap(other.flowId_);
        temp_.swap(other.temp_);
        solidStep_.swap(other.solidStep_);
        arrivalStep_.swap(other.arrivalStep_);
    }

    std::size_t bytes() const {
        const std::size_t n = (static_cast<std::size_t>(dims_.nx) + 2) *
                              (static_cast<std::size_t>(dims_.ny) + 2) *
                              (static_cast<std::size_t>(dims_.nz) + 2);
        return n * (sizeof(CellType) + sizeof(std::int32_t) + sizeof(float) + 2 * sizeof(std::uint16_t));
    }

private:
    // Współrzędna z ramką -> indeks w wektorze (ramka ma indeks 0 i n+1).
    static std::size_t at(int i) { return static_cast<std::size_t>(i + 1); }

    // Tworzy macierz [nz+2][ny+2][nx+2] wypełnioną wartością v.
    template <class T>
    Matrix3<T> make(T v) const {
        const std::size_t sx = static_cast<std::size_t>(dims_.nx) + 2;
        const std::size_t sy = static_cast<std::size_t>(dims_.ny) + 2;
        const std::size_t sz = static_cast<std::size_t>(dims_.nz) + 2;
        return Matrix3<T>(sz, std::vector<std::vector<T>>(sy, std::vector<T>(sx, v)));
    }

    Dims dims_;
    Matrix3<CellType> type_;
    Matrix3<std::int32_t> flowId_;
    Matrix3<float> temp_;
    Matrix3<std::uint16_t> solidStep_;
    Matrix3<std::uint16_t> arrivalStep_;
};

// ---------------------------------------------------------------------------
// Konwersje Storage <-> Microstructure (wnętrze bez ramki).
// ---------------------------------------------------------------------------

// Kopiuje wnętrze siatki do płaskiej mikrostruktury (do zapisu, statystyk, porównań).
template <class Storage>
VOLCANO_NOINLINE Microstructure toMicrostructure(const Storage& s) {
    Microstructure m;
    m.resize(s.dims());
    std::size_t i = 0;
    for (int z = 0; z < s.nz(); ++z) {
        for (int y = 0; y < s.ny(); ++y) {
            for (int x = 0; x < s.nx(); ++x, ++i) {
                m.type[i] = s.type(x, y, z);
                m.flowId[i] = s.flowId(x, y, z);
                m.temp[i] = s.temp(x, y, z);
                m.solidStep[i] = s.solidStep(x, y, z);
                m.arrivalStep[i] = s.arrivalStep(x, y, z);
            }
        }
    }
    return m;
}

// Wczytuje mikrostrukturę do wnętrza siatki (np. stan początkowy z pliku).
template <class Storage>
void loadMicrostructure(Storage& s, const Microstructure& m) {
    assert(s.dims() == m.dims);
    std::size_t i = 0;
    for (int z = 0; z < s.nz(); ++z) {
        for (int y = 0; y < s.ny(); ++y) {
            for (int x = 0; x < s.nx(); ++x, ++i) {
                s.setCell(x, y, z,
                          CellState{m.type[i], m.flowId[i], m.temp[i], m.solidStep[i], m.arrivalStep[i]});
            }
        }
    }
}

}  // namespace volcano
