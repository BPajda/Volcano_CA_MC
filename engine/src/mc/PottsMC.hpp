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
//
// Szachownica (mc.update = checkerboard, etap 9; opis reguł w McRules.hpp): komórki domeny podzielone na kolory tak,
// że żadne dwie komórki jednego koloru nie są sąsiadami w żadnym wariancie sąsiedztwa; MCS = kolory po kolei, w kolorze
// każda komórka domeny dokładnie raz, losowość z hashRand(seed, MCS, globalIndex, sól). Próba komórki czyta tylko
// sąsiadów (innych kolorów — w tej fazie niezmiennych), więc kolejność prób w kolorze nie ma znaczenia: komórki koloru
// dzielone są między wątki po warstwach (z, w płaszczyźnie x–y — y), a wynik jest ten sam dla każdej liczby wątków.
//
// Wersja rozproszona (MPI, etap 10; setStrip, parallel/Strip.hpp): siatka MC jest oknem pasa — warstwy własne
// [ownLo_, ownHi_) i po jednej warstwie brzegowej z każdej strony. Próby dotyczą tylko komórek domeny w warstwach
// własnych, kolory i losowość liczone są we współrzędnych / indeksach globalnych (kolor zależy od globalnej
// parzystości, hash — od globalIndex), a po każdym kolorze link_->exchange() przysyła warstwy brzegowe (komórki tego
// koloru zmieniły się u sąsiadów, a następny kolor ich sąsiaduje). Energię całkowitą sumuje link_->sum().

#include <cstddef>
#include <cstdint>
#include <vector>

#include "core/Boundary.hpp"
#include "core/Neighborhood.hpp"
#include "core/Profile.hpp"
#include "core/Types.hpp"
#include "mc/Grains.hpp"
#include "mc/McRules.hpp"
#include "parallel/Omp.hpp"
#include "parallel/Strip.hpp"

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

    // Tryb szachownicy (mc.update = checkerboard, etap 9) — przed initialize().
    void setCheckerboard(bool on) { checkerboard_ = on; }
    bool checkerboard() const { return checkerboard_; }
    // Ustawienia równoległości (etap 9): szachownica, energia i mapa kryształów w wielu wątkach; tryb random —
    // pętla prób zawsze w jednym wątku (każda próba widzi wynik poprzednich).
    void setParallel(const ParallelSettings& par) { par_ = par; }
    // Pas procesu w wersji rozproszonej (MPI, etap 10) — przed initialize(). dims z konstruktora to wymiary okna,
    // bc — warunki brzegowe okna (oś warstw bez zawijania przy kilku procesach). Komórki warstw brzegowych nie należą
    // do domeny okna (orientacje dostają z wymiany), mobilność i domena dotyczą warstw własnych.
    void setStrip(const Strip& s);

    // Inicjalizacja: każda komórka domeny dostaje orientację 1 + hashRand(seed, 0, idx, kSaltMcInit) mod Q
    // (poza domeną 0), powstaje lista komórek domeny, ramka jest wypełniana wg warunków brzegowych.
    // Szachownica: lista komórek domeny ułożona kolor po kolorze, w kolorze warstwa po warstwie (globalIndex rosnąco).
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

    // --- szachownica (etap 9) ---

    // Liczba kolorów (po initialize w trybie checkerboard; 0 w trybie random).
    int colorCount() const { return colors_; }
    // Kolor komórki (x, y, z) wnętrza: von Neumann przy parzystych osiach periodycznych — parzystość x + y + z
    // (2 kolory); inaczej (Moore, pentagonal, hexagonal albo nieparzysta oś periodyczna) — iloczyn klas osi
    // (parzystość współrzędnej, a w osi periodycznej o nieparzystej długości ostatnia warstwa jako trzecia klasa):
    // 4 kolory w 2D, 8 w 3D (do 27 z nieparzystymi osiami periodycznymi). Kolory numerowane 0..colorCount()-1.
    // Współrzędne i wymiary — całej przestrzeni (w oknie pasa MPI: globalne, etap 10).
    int colorOf(int x, int y, int z) const;

    // --- warstwy osi zewnętrznej (etap 10: wymiana warstw brzegowych MPI) ---
    // Warstwa k okna (z, w płaszczyźnie x–y — y) z ramką w pozostałych osiach: ciągły fragment tablicy orientacji
    // [layerStart(k), layerStart(k) + layerCells()).
    std::size_t layerCells() const { return dims_.nz > 1 ? sx_ * sy_ : sx_; }
    std::size_t layerStart(int k) const {
        return dims_.nz > 1 ? frameIndex(-frame_[0], -frame_[1], k) : frameIndex(-frame_[0], k, 0);
    }
    std::int32_t* spinData() { return spin_.data(); }
    // Zakres listy komórek domeny dla koloru c (begin, end) — testy.
    std::size_t colorBegin(int c) const { return colorLayerStart_[static_cast<std::size_t>(c * layers_)]; }
    std::size_t colorEnd(int c) const { return colorLayerStart_[static_cast<std::size_t>((c + 1) * layers_)]; }

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

    // Liczniki prób szachownicy (sumy wątku, potem redukcja).
    struct TrialCounts {
        std::uint64_t attempts = 0;
        std::uint64_t accepted = 0;
        std::uint64_t uphill = 0;
    };
    // MCS szachownicy: kolory po kolei, w wielu wątkach komórki koloru dzielone po warstwach (bariera po kolorze).
    template <bool kMobility, bool kRandomNb>
    std::uint64_t sweepColors();
    // Próby komórek listy domeny [b, e) jednego koloru w kroku MCS o stałej części hasha prefix.
    template <bool kMobility, bool kRandomNb>
    void colorTrials(std::uint64_t prefix, std::size_t b, std::size_t e, TrialCounts& out);
    // Lista komórek domeny w kolejności szachownicy i granice kolorów / warstw (colorLayerStart_).
    void buildColors();
    // Klasa współrzędnej c w osi a (kolory iloczynowe): parzystość, w osi periodycznej o nieparzystej długości
    // ostatnia warstwa — klasa 2.
    int axisClass(int c, int a) const;

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
    // --- szachownica i wątki (etap 9) ---
    bool checkerboard_ = false;
    bool parityColors_ = false;                 // 2 kolory (parzystość x + y + z) zamiast kolorów iloczynowych
    int colors_ = 0;                            // liczba kolorów (0 — tryb random)
    int layers_ = 1;                            // warstwy (z, w płaszczyźnie x–y — y): jednostka podziału na wątki
    int colorIndex_[27] = {};                   // kolor iloczynowy cx + 3·cy + 9·cz -> numer koloru 0..colors_-1
    std::vector<std::size_t> colorLayerStart_;  // początek (kolor c, warstwa k) w liście domeny: [c·layers_ + k]
    ParallelSettings par_;
    // --- pas w wersji rozproszonej (MPI, etap 10; setStrip) — bez podziału: okno = cała przestrzeń ---
    Dims global_;                 // wymiary całej przestrzeni (kolory)
    bool globalPeriodic_[3];      // periodyczność osi całej przestrzeni (kolory przy nieparzystej osi)
    int ownLo_ = 0;               // własne warstwy okna [ownLo_, ownHi_)
    int ownHi_ = 0;
    int windowLo_ = 0;            // globalny numer warstwy okna 0
    std::uint64_t hashBase_ = 0;  // globalIndex komórki okna (0, 0, 0)
    StripLink* link_ = nullptr;   // wymiana warstw brzegowych i sumy (nullptr — jeden proces)
};

}  // namespace volcano
