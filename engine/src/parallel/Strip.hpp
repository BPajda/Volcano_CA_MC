#pragma once
// Podział przestrzeni na pasy warstw między procesy (etap 10, MPI) — część niezależna od MPI.
//
// Oś warstw jest ta sama co w etapie 9 (OpenMP): z, a w płaszczyźnie x–y (nz = 1) — y. Warstwa = wszystkie komórki
// o danej wartości tej osi; oś warstw jest najbardziej zewnętrzną osią pamięci, więc pas kolejnych warstw to ciągły
// fragment każdej płaskiej tablicy pola (także w ca_result.bin — przyda się do zapisu MPI-IO w etapie 11).
//
// Proces liczy pas WŁASNYCH warstw [lo, hi) w OKNIE: siatce obejmującej pas i warstwy brzegowe (ghost) wokół niego.
// Okno ma własną ramkę 1 komórki jak zwykła siatka (Storage, PottsMC), ale w osi warstw ramka leży dopiero za
// warstwami brzegowymi. Automat i MC liczą reguły tylko dla warstw własnych; warstwy brzegowe są kopiami warstw
// sąsiednich procesów, odświeżanymi przez StripLink::exchange przed każdym krokiem (MC — po każdym kolorze).
//
// Ile warstw brzegowych: tyle, ile warstw pod / nad komórką czytają reguły jednego kroku (LavaCA::reachBelow/Above):
//   classic, MC — promień sąsiedztwa: 1 warstwa z każdej strony;
//   lava        — 1 warstwa nad pasem, ale 17 pod nim: dropDepth() (głębokość spadku z komórki powietrza, CaRules.hpp)
//                 schodzi do 16 poziomów w dół, a hasSupport() najniższego z nich czyta jeszcze komórkę pod spodem.
//                 Z warstw głębszych niż pierwsza reguły czytają tylko typ komórki, więc tam wymieniamy sam typ.
// Brzeg globalny absorbujący: przy pierwszym / ostatnim pasie nie ma warstw brzegowych, a ramka okna to VOID — jak
// w wersji sekwencyjnej. Brzeg periodyczny w osi warstw (classic, MC full): pierwszy i ostatni proces wymieniają się
// warstwami (pierścień), a ramka okna w tej osi nie jest zawijana lokalnie (Boundary::withoutPeriodic).
//
// Indeksy globalne: komórka okna (x, y, z) ma globalIndex = globalIndex okna(x, y, z) + hashBase (mod 2^64), bo okno
// to ciągły zakres warstw osi zewnętrznej. hashBase = globalIndex komórki (0, 0, windowLo); przy brzegu periodycznym
// windowLo może być -1 (warstwa L − 1 jako brzegowa procesu 0) — arytmetyka modulo 2^64 daje poprawny indeks warstw
// własnych, a warstw brzegowych nie hashujemy (reguły losują tylko dla komórek własnych).

#include <cstdint>
#include <vector>

#include "core/Types.hpp"

namespace volcano {

class VectorStorage;
class PottsMC;

// Komunikacja między pasami — implementacja z MPI w engine/src/mpi/ (program engine_mpi). Automat i MC dostają tylko
// wskaźnik do tego interfejsu, więc biblioteka silnika i program engine nie zależą od MPI.
class StripLink {
public:
    virtual ~StripLink() = default;
    // Suma n liczników po wszystkich procesach, w miejscu (MPI_Allreduce) — liczniki kroku i reguła końca symulacji.
    virtual void sum(std::uint64_t* values, int n) = 0;
    // Odświeża warstwy brzegowe okna automatu (cur; w pełnym przebiegu także next — po zamianie buforów okno musi mieć
    // aktualne warstwy brzegowe w obu buforach, bo wariant „changed” nie przysyła warstw bez zmian).
    virtual void exchange(VectorStorage& cur, VectorStorage* next) = 0;
    // Odświeża warstwy brzegowe orientacji MC.
    virtual void exchange(PottsMC& mc) = 0;
};

// Pas procesu w oknie (ustawiany w LavaCA::setStrip / PottsMC::setStrip przed obliczeniami).
struct Strip {
    Dims global;                                     // wymiary całej przestrzeni
    bool globalPeriodic[3] = {false, false, false};  // periodyczność osi całej przestrzeni (kolory szachownicy MC)
    int ownLo = 0;                                   // własne warstwy okna [ownLo, ownHi) — indeksy w oknie
    int ownHi = 0;
    int windowLo = 0;                                // globalny numer warstwy okna 0 (-1 = warstwa L − 1, pierścień)
    std::uint64_t hashBase = 0;                      // globalIndex komórki okna (0, 0, 0), modulo 2^64
    StripLink* link = nullptr;                       // komunikacja (nullptr = jeden proces, bez wymiany)
};

// Pola komórki w wymianie warstw brzegowych (maska bitowa).
enum StripField : unsigned {
    kFieldType = 1u,
    kFieldFlow = 2u,
    kFieldTemp = 4u,
    kFieldSolid = 8u,
    kFieldArrival = 16u,
    kFieldSpin = 32u,  // orientacja MC (int32)
};

// Warstwa brzegowa okna: indeks w oknie, globalny numer warstwy, proces-właściciel i pola do przesłania.
struct GhostLayer {
    int local = 0;
    int global = 0;
    int owner = 0;
    unsigned fields = 0;
};

// Jakie warstwy brzegowe potrzebuje pas: below[d - 1] — pola warstwy lo − d, above[d - 1] — warstwy hi − 1 + d.
struct GhostSpec {
    std::vector<unsigned> below;
    std::vector<unsigned> above;
    bool periodic = false;  // oś warstw periodyczna — pierścień (pierwszy i ostatni proces są sąsiadami)
};

// Plan pasa jednego procesu: własne warstwy, okno, warstwy brzegowe do odebrania i warstwy własne do wysłania.
struct StripPlan {
    int layers = 0;        // L — liczba warstw całej przestrzeni
    int ranks = 1;
    int rank = 0;
    int lo = 0;            // własne warstwy (globalnie) [lo, hi)
    int hi = 0;
    int windowLo = 0;      // globalny numer warstwy okna 0 (bez zawinięcia: -1 przy pierścieniu)
    int windowLayers = 0;  // warstwy okna (własne + brzegowe)
    int ownLo = 0;         // własne warstwy w oknie [ownLo, ownHi)
    int ownHi = 0;
    std::vector<GhostLayer> ghosts;  // warstwy brzegowe tego procesu (rosnąco wg indeksu w oknie)

    // Komunikat do jednego sąsiada: warstwy w kolejności, w jakiej odbiorca je rozpakowuje.
    struct Message {
        int peer = 0;
        std::vector<GhostLayer> layers;  // przy wysyłce: local = warstwa okna nadawcy, global/fields jak u odbiorcy
    };
    std::vector<Message> sends;
    std::vector<Message> recvs;
};

// Równy podział L warstw na p części: pierwsze L mod p części dostają o jedną warstwę więcej.
// lo[r] = r·⌊L/p⌋ + min(r, L mod p). Wymaga 1 <= p <= L.
std::vector<int> splitLayers(int layers, int parts);

// Plan pasa procesu rank z ranks. Przy ranks = 1 okno = cała przestrzeń, bez warstw brzegowych (brzeg periodyczny
// liczy wtedy ramka okna, jak w wersji sekwencyjnej). Rzuca std::invalid_argument, gdy ranks > layers.
StripPlan planStrip(int layers, int ranks, int rank, const GhostSpec& spec);

// Oś warstw przestrzeni (jak w etapie 9): true — z, false — y (płaszczyzna x–y).
inline bool layerAxisZ(const Dims& d) { return d.nz > 1; }
// Liczba warstw przestrzeni.
inline int layerCountOf(const Dims& d) { return layerAxisZ(d) ? d.nz : d.ny; }
// Wymiary okna o windowLayers warstwach.
inline Dims windowDims(const Dims& global, int windowLayers) {
    Dims w = global;
    (layerAxisZ(global) ? w.nz : w.ny) = windowLayers;
    return w;
}
// Komórki jednej warstwy (bez ramki).
inline std::uint64_t layerPlane(const Dims& d) {
    return layerAxisZ(d) ? static_cast<std::uint64_t>(d.nx) * static_cast<std::uint64_t>(d.ny)
                         : static_cast<std::uint64_t>(d.nx);
}

}  // namespace volcano
