#pragma once
// Dwie reprezentacje siatki komórek (porównanie w benchmarku vector vs macierz):
//
//   VectorStorage  — jedna płaska std::vector<T> na każde pole (SoA),
//                    indeks (x+fx) + (nx+2fx)*((y+fy) + (ny+2fy)*(z+fz)),
//   MatrixStorage  — std::vector<std::vector<std::vector<T>>> na każde pole,
//                    dostęp [z+fz][y+fy][x+fx].
//
// Obie mają ramkę 1 komórki dookoła (współrzędne -1 i n są poprawne) — warunki
// brzegowe to wypełnienie ramki przed krokiem, a w wersji równoległej ramka stanie się
// komórkami nadmiarowymi (ghost cells) przy podziale MPI. Od etapu 8 ramka jest tylko w osiach
// o rozmiarze > 1 (fx, fy, fz = Dims::frameX/Y/Z): w nieużywanej osi przestrzeni 2D jej nie ma
// (OPTYMALIZACJA: pamięć siatki 2D 3× mniejsza, brak kopiowania dwóch pełnych warstw co krok).
//
// Obie klasy mają identyczny interfejs, ale NIE dziedziczą po wspólnej klasie bazowej:
// algorytm (LavaCA<Storage>) jest szablonem, więc dostęp do komórki jest funkcją inline,
// bez wywołań wirtualnych w gorącej pętli. Jeden obiekt Storage = jeden bufor;
// automat w pełnym przebiegu (ca.sweep = full) trzyma dwa (cur, next) i zamienia je metodą swap() — bez
// kopiowania danych; automat frontalny (domyślny od etapu 8) trzyma jeden bufor i listę zmian kroku.
//
// Pozycja komórki (etap 8): obok dostępu przez współrzędne (x, y, z) obie klasy mają typ Pos
// i dostęp przez pozycję. VectorStorage::Pos to indeks w płaskiej tablicy z ramką — sąsiad to
// pozycja + stałe przesunięcie liniowe (linear(o)), następna komórka w osi x to pozycja + 1;
// MatrixStorage::Pos to współrzędne (x, y, z), więc dla macierzy koszt dostępu jest jak dotąd.
// Oba bufory automatu mają ten sam układ, więc pozycja z cur_ jest poprawna także w next_.
// OPTYMALIZACJA: bez liczenia indeksu z (x, y, z) (dwa mnożenia) przy każdym odczycie sąsiada.

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
          sx_(static_cast<std::size_t>(d.nx + 2 * d.frameX())),
          sy_(static_cast<std::size_t>(d.ny + 2 * d.frameY())),
          base_(static_cast<std::size_t>(d.frameX()) +
                sx_ * (static_cast<std::size_t>(d.frameY()) + sy_ * static_cast<std::size_t>(d.frameZ()))) {
        const std::size_t n = d.framedCells();
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

    // --- dostęp przez pozycję (indeks w tablicy z ramką) ---
    using Pos = std::size_t;
    Pos pos(int x, int y, int z) const { return index(x, y, z); }
    // Przesunięcie liniowe sąsiada o: dx + sx·(dy + sy·dz).
    std::ptrdiff_t linear(const Offset& o) const {
        const std::ptrdiff_t sx = static_cast<std::ptrdiff_t>(sx_);
        const std::ptrdiff_t sy = static_cast<std::ptrdiff_t>(sy_);
        return o.dx + sx * (o.dy + sy * o.dz);
    }
    // Sąsiad pozycji p o przesunięciu o (lin = linear(o), policzone raz przed pętlą).
    static Pos shifted(Pos p, const Offset&, std::ptrdiff_t lin) {
        return static_cast<Pos>(static_cast<std::ptrdiff_t>(p) + lin);
    }
    // Następna komórka w osi x.
    static Pos nextX(Pos p) { return p + 1; }

    CellType type(Pos i) const { return type_[i]; }
    std::int32_t flowId(Pos i) const { return flowId_[i]; }
    float temp(Pos i) const { return temp_[i]; }
    CellState cell(Pos i) const { return CellState{type_[i], flowId_[i], temp_[i], solidStep_[i], arrivalStep_[i]}; }
    void setCell(Pos i, const CellState& c) {
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
        std::swap(base_, other.base_);
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
    // base_ = indeks komórki (0, 0, 0); współrzędne ramki (-1) dają ujemny składnik, suma jest >= 0.
    std::size_t index(int x, int y, int z) const {
        assert(x >= -dims_.frameX() && x < dims_.nx + dims_.frameX() && y >= -dims_.frameY() &&
               y < dims_.ny + dims_.frameY() && z >= -dims_.frameZ() && z < dims_.nz + dims_.frameZ());
        return base_ + static_cast<std::size_t>(x) +
               sx_ * (static_cast<std::size_t>(y) + sy_ * static_cast<std::size_t>(z));
    }

    Dims dims_;
    std::size_t sx_ = 0;    // nx + 2·fx
    std::size_t sy_ = 0;    // ny + 2·fy
    std::size_t base_ = 0;  // fx + sx·(fy + sy·fz)
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

    explicit MatrixStorage(const Dims& d) : dims_(d), fx_(d.frameX()), fy_(d.frameY()), fz_(d.frameZ()) {
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

    CellType type(int x, int y, int z) const { return type_[az(z)][ay(y)][ax(x)]; }
    std::int32_t flowId(int x, int y, int z) const { return flowId_[az(z)][ay(y)][ax(x)]; }
    float temp(int x, int y, int z) const { return temp_[az(z)][ay(y)][ax(x)]; }
    std::uint16_t solidStep(int x, int y, int z) const { return solidStep_[az(z)][ay(y)][ax(x)]; }
    std::uint16_t arrivalStep(int x, int y, int z) const { return arrivalStep_[az(z)][ay(y)][ax(x)]; }

    void setType(int x, int y, int z, CellType v) { type_[az(z)][ay(y)][ax(x)] = v; }
    void setFlowId(int x, int y, int z, std::int32_t v) { flowId_[az(z)][ay(y)][ax(x)] = v; }
    void setTemp(int x, int y, int z, float v) { temp_[az(z)][ay(y)][ax(x)] = v; }
    void setSolidStep(int x, int y, int z, std::uint16_t v) { solidStep_[az(z)][ay(y)][ax(x)] = v; }
    void setArrivalStep(int x, int y, int z, std::uint16_t v) { arrivalStep_[az(z)][ay(y)][ax(x)] = v; }

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

    // --- dostęp przez pozycję: tu pozycja to współrzędne (ten sam koszt co dostęp przez x, y, z) ---
    struct Pos {
        int x;
        int y;
        int z;
    };
    Pos pos(int x, int y, int z) const { return Pos{x, y, z}; }
    std::ptrdiff_t linear(const Offset&) const { return 0; }  // nieużywane — sąsiad z współrzędnych
    static Pos shifted(Pos p, const Offset& o, std::ptrdiff_t) { return Pos{p.x + o.dx, p.y + o.dy, p.z + o.dz}; }
    static Pos nextX(Pos p) { return Pos{p.x + 1, p.y, p.z}; }

    CellType type(Pos p) const { return type(p.x, p.y, p.z); }
    std::int32_t flowId(Pos p) const { return flowId(p.x, p.y, p.z); }
    float temp(Pos p) const { return temp(p.x, p.y, p.z); }
    CellState cell(Pos p) const { return cell(p.x, p.y, p.z); }
    void setCell(Pos p, const CellState& c) { setCell(p.x, p.y, p.z, c); }

    void swap(MatrixStorage& other) noexcept {
        std::swap(dims_, other.dims_);
        std::swap(fx_, other.fx_);
        std::swap(fy_, other.fy_);
        std::swap(fz_, other.fz_);
        type_.swap(other.type_);
        flowId_.swap(other.flowId_);
        temp_.swap(other.temp_);
        solidStep_.swap(other.solidStep_);
        arrivalStep_.swap(other.arrivalStep_);
    }

    // Pusty bufor (konstruktor domyślny — np. next_ automatu frontalnego) nie zajmuje pamięci.
    std::size_t bytes() const {
        if (type_.empty()) {
            return 0;
        }
        return dims_.framedCells() *
               (sizeof(CellType) + sizeof(std::int32_t) + sizeof(float) + 2 * sizeof(std::uint16_t));
    }

private:
    // Współrzędna z ramką -> indeks w wektorze (ramka ma indeks 0 i n+1; w osi bez ramki wnętrze od 0).
    std::size_t ax(int x) const { return static_cast<std::size_t>(x + fx_); }
    std::size_t ay(int y) const { return static_cast<std::size_t>(y + fy_); }
    std::size_t az(int z) const { return static_cast<std::size_t>(z + fz_); }

    // Tworzy macierz [nz+2fz][ny+2fy][nx+2fx] wypełnioną wartością v.
    template <class T>
    Matrix3<T> make(T v) const {
        const std::size_t sx = static_cast<std::size_t>(dims_.nx + 2 * fx_);
        const std::size_t sy = static_cast<std::size_t>(dims_.ny + 2 * fy_);
        const std::size_t sz = static_cast<std::size_t>(dims_.nz + 2 * fz_);
        return Matrix3<T>(sz, std::vector<std::vector<T>>(sy, std::vector<T>(sx, v)));
    }

    Dims dims_;
    int fx_ = 1;  // szerokość ramki w osiach x, y, z (Dims::frameX/Y/Z)
    int fy_ = 1;
    int fz_ = 1;
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
