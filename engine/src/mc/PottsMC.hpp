#pragma once
// PottsMC — naiwny rozrost ziaren Monte Carlo (model Pottsa) — kroki 1–5 wersji naiwnej.
// Opis reguł, domeny, mobilności i statystyk: McRules.hpp.
//
// Siatka: własne płaskie tablice z ramką 1 komórki w osiach o rozmiarze > 1 (układ jak VectorStorage):
//   spin_     — orientacja int32 (1..Q w domenie, 0 poza),
//   mask_     — uint8: bit kInDomain (komórka należy do domeny), bit kPeriodicEdge (komórka
//               leży przy ścianie periodycznej — jej zmiana wymaga odświeżenia kopii w ramce),
//   mobility_ — float, tylko gdy mobilność jest włączona (tryb basalt).
// Sąsiad komórki o indeksie i to i + stałe przesunięcie liniowe (prekomputowane dla każdego
// wariantu sąsiedztwa), a brzegi są realizowane ramką — w pętli próby nie ma sprawdzania
// zakresu ani zawijania współrzędnych.
//
// Klasa nie zależy od CA ani od plików: dostaje maskę domeny (i opcjonalnie mobilność)
// w kolejności globalIndex, więc działa tak samo dla wyniku CA w pamięci, wyniku z pliku
// i dla całej przestrzeni (tryb full).

#include <cstddef>
#include <cstdint>
#include <vector>

#include "core/Boundary.hpp"
#include "core/Neighborhood.hpp"
#include "core/Profile.hpp"
#include "core/Types.hpp"
#include "mc/Grains.hpp"
#include "mc/McRules.hpp"

namespace volcano {

// Czasy składników pomiaru statystyk [ms], sumowane — tylko przy --timing-detail (etap 3).
struct McMeasureTimes {
    double crystals = 0.0;  // kopia orientacji do mapy kryształów (bez ramki)
    double grains = 0.0;    // etykietowanie ziaren (union-find)
    double energy = 0.0;    // energia całkowita
};

class PottsMC {
public:
    // Alokuje tablice z ramką; domena początkowo pusta. Periodyczność osi bierzemy z bc
    // (w trybie basalt oś z nie jest periodyczna — patrz McRules.hpp). Oś o rozmiarze 1
    // (płaszczyzna 2D) nigdy nie jest zawijana: sąsiedztwo 2D jej nie używa.
    PottsMC(const Dims& dims, const McParams& params, const Neighborhood& nb, const Boundary& bc);

    // --- przygotowanie (przed initialize) ---

    // Domena = cała przestrzeń (tryb full).
    void setDomainAll();
    // Domena z maski w kolejności globalIndex (1 = komórka domeny), np. CoolingMobility::basaltDomain.
    void setDomain(const std::vector<std::uint8_t>& inDomain);
    // Mobilność komórek w kolejności globalIndex, wartości z [0, 1]; pusty wektor = wyłączona.
    void setMobility(const std::vector<float>& mobility);

    // Inicjalizacja: każda komórka domeny dostaje orientację 1 + hashRand(seed, 0, idx, kSaltMcInit) mod Q
    // (poza domeną 0), powstaje lista komórek domeny, ramka jest wypełniana wg warunków brzegowych.
    void initialize();

    // --- symulacja ---

    // Jeden krok Monte Carlo: N_domena prób (kroki 1–5 wersji naiwnej). Zwraca liczbę zaakceptowanych zmian.
    std::uint64_t sweep();

    // Statystyki bieżącego stanu: liczba ziaren, średnia wielkość, energia całkowita
    // (mcs = liczba wykonanych kroków; acceptRate uzupełnia wywołujący). labels (opcjonalnie)
    // dostaje etykiety ziaren — np. do statystyk wg klas mobilności. times (opcjonalnie,
    // --timing-detail) sumuje czasy składników.
    McStats measure(GrainLabels* labels = nullptr, McMeasureTimes* times = nullptr) const;

    // Pamięć tablic MC [B] (model pamięci, etap 3): orientacje i maska z ramką, mobilność,
    // listy komórek domeny (pojemność — push_back rezerwuje zapas) i przesunięcia sąsiadów.
    std::size_t bytes() const;

    // --- dostęp (wyniki, testy) ---

    const Dims& dims() const { return dims_; }
    std::size_t domainCells() const { return domainFrame_.size(); }
    int sweepsDone() const { return sweeps_; }
    std::uint64_t attempts() const { return attempts_; }        // próby niepominięte przez mobilność
    std::uint64_t accepted() const { return accepted_; }        // zaakceptowane zmiany orientacji
    std::uint64_t acceptedUphill() const { return uphill_; }    // w tym z ΔE > 0 (możliwe tylko przy kT > 0)
    bool mobilityEnabled() const { return !mobility_.empty(); }
    // Spójność ziaren: Moore, gdy sąsiedztwo MC nie jest von Neumannem (McRules.hpp).
    bool mooreConnectivity() const { return nb_.kind() != NeighborhoodKind::VonNeumann; }
    // Periodyczność osi x, y, z w MC (po uwzględnieniu osi o rozmiarze 1).
    const bool* periodic() const { return periodic_; }

    bool inDomain(int x, int y, int z) const { return (mask_[frameIndex(x, y, z)] & kInDomain) != 0; }
    std::int32_t orientation(int x, int y, int z) const { return spin_[frameIndex(x, y, z)]; }
    // Ustawia orientację komórki domeny (testy, ręczne przykłady); odświeża kopie w ramce.
    void setOrientation(int x, int y, int z, std::int32_t s);

    // Energia komórki E = J · Σ(1 − δ) dla bieżącej orientacji / gdyby miała orientację s,
    // i zmiana energii przy zmianie orientacji na s. Wariant sąsiedztwa losowego — dla
    // bieżącego kroku MCS.
    double energyAt(int x, int y, int z) const;
    double energyIf(int x, int y, int z, std::int32_t s) const;
    double deltaEnergy(int x, int y, int z, std::int32_t s) const;
    // Energia całkowita ½ · Σ_i E_i (każda para sąsiadów raz).
    double totalEnergy() const;

    // Mapa kryształów (bez ramki): orientacja w domenie, 0 poza nią.
    CrystalMap crystals() const;

private:
    static constexpr std::uint8_t kInDomain = 1;
    static constexpr std::uint8_t kPeriodicEdge = 2;

    // Indeks w tablicy z ramką (współrzędne od -1 do n włącznie w osiach z ramką; base_ = indeks (0, 0, 0)).
    std::size_t frameIndex(int x, int y, int z) const {
        return base_ + static_cast<std::size_t>(x) +
               sx_ * (static_cast<std::size_t>(y) + sy_ * static_cast<std::size_t>(z));
    }

    // Przesunięcia liniowe sąsiadów komórki o globalnym indeksie gidx w kroku MCS t.
    const std::vector<std::ptrdiff_t>& offsetsFor(std::uint64_t t, std::uint64_t gidx) const {
        return linear_[static_cast<std::size_t>(nb_.variantFor(p_.seed, t, gidx))];
    }

    // Liczba sąsiadów W DOMENIE o orientacji różnej od s: Σ (1 − δ(s, S_j)).
    // Sąsiad spoza domeny (skała, powietrze, ramka absorbująca) nie wnosi energii.
    // OPTYMALIZACJA (etap 8): bez skoku warunkowego i bez odczytu maski. Orientacja 0 ma dokładnie komórka spoza
    // domeny (w domenie 1..Q, także kopie w ramce periodycznej), więc liczba „innych” = liczba sąsiadów w domenie
    // (S_j != 0) minus liczba sąsiadów o orientacji s (s >= 1). Porównania dają 0/1 dodawane arytmetycznie —
    // MSVC kompilował wcześniejszy warunek (maska && S_j != s) do źle przewidywanego skoku (etap 3, punkt 2.4).
    VOLCANO_NOINLINE int unlikeNeighbors(std::size_t i, std::int32_t s,
                                         const std::vector<std::ptrdiff_t>& offsets) const {
        const std::int32_t* const spin = spin_.data() + i;
        const std::int32_t match = (s != 0) ? s : -1;  // s = 0 (spoza domeny): różni są wszyscy sąsiedzi w domenie
        int inDomain = 0;
        int same = 0;
        for (const std::ptrdiff_t o : offsets) {
            const std::int32_t sj = spin[o];
            inDomain += static_cast<int>(sj != 0);
            same += static_cast<int>(sj == match);
        }
        return inDomain - same;
    }

    // Kroki 2 i 4 naraz: liczba sąsiadów w domenie o orientacji różnej od a (przed zmianą) i od b (po zmianie)
    // w JEDNYM przejściu po sąsiadach (a, b >= 1). Wynik jak dwa wywołania unlikeNeighbors.
    // OPTYMALIZACJA (etap 8): jedno przejście zamiast dwóch, bez skoków warunkowych.
    static void unlikeBeforeAfter(const std::int32_t* spinAtCell, std::int32_t a, std::int32_t b,
                                  const std::ptrdiff_t* offsets, std::size_t count, int& before, int& after) {
        int inDomain = 0;
        int sameA = 0;
        int sameB = 0;
        for (std::size_t k = 0; k < count; ++k) {
            const std::int32_t sj = spinAtCell[offsets[k]];
            inDomain += static_cast<int>(sj != 0);
            sameA += static_cast<int>(sj == a);
            sameB += static_cast<int>(sj == b);
        }
        before = inDomain - sameA;
        after = inDomain - sameB;
    }

    // Pętla prób jednego MCS. Szablon: decyzje stałe w czasie kroku (mobilność włączona, sąsiedztwo losowe)
    // wybrane raz przed pętlą, nie w każdej próbie (OPTYMALIZACJA, etap 8).
    template <bool kMobility, bool kRandomNb>
    std::uint64_t sweepTrials();

    // Wypełnia całą ramkę: oś periodyczna — kopia przeciwległej warstwy, inaczej poza domeną.
    void fillFrame();
    // Odświeża kopie komórki i (leżącej przy ścianie periodycznej) w ramce.
    void syncFrame(std::size_t i);

    Dims dims_;
    McParams p_;
    Neighborhood nb_;
    bool periodic_[3];
    int frame_[3];        // szerokość ramki w osiach x, y, z (Dims::frameX/Y/Z: 0 w nieużywanej osi 2D)
    std::size_t sx_;      // nx + 2·fx
    std::size_t sy_;      // ny + 2·fy
    std::size_t base_;    // indeks komórki (0, 0, 0)
    std::vector<std::int32_t> spin_;
    std::vector<std::uint8_t> mask_;
    std::vector<float> mobility_;
    std::vector<std::vector<std::ptrdiff_t>> linear_;  // przesunięcia liniowe każdego wariantu sąsiedztwa
    std::vector<std::size_t> domainFrame_;             // lista komórek domeny: indeks z ramką
    std::vector<std::uint64_t> domainGlobal_;          // ... i globalIndex (wariant sąsiedztwa losowego)
    int sweeps_ = 0;
    std::uint64_t attempts_ = 0;
    std::uint64_t accepted_ = 0;
    std::uint64_t uphill_ = 0;
};

}  // namespace volcano
