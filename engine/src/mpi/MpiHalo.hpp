#pragma once
// Wymiana warstw brzegowych pasów między procesami MPI (etap 10) — implementacja StripLink (parallel/Strip.hpp).
//
// Jedna wymiana = jeden komunikat do każdego sąsiada, który potrzebuje naszych warstw, i jeden od każdego, którego
// warstwy są u nas brzegowe (plan: planStrip). Wszystkie odbiory i wysyłki są nieblokujące (MPI_Irecv / MPI_Isend),
// a potem MPI_Waitall: przy pasach cieńszych niż 17 warstw lawa dostaje warstwy od kilku procesów pod sobą, więc
// zamiast par MPI_Sendrecv „w górę” i „w dół” jest lista komunikatów bez ustalonej kolejności — bez ryzyka
// zakleszczenia i z przesyłem do wszystkich sąsiadów naraz.
//
// Dwa sposoby budowy komunikatu (mpi.pack):
//   "manual" (etap 10) — pakowanie do bufora bajtów:
//     [flaga warstwy 1] … [flaga warstwy n] [dane warstw z flagą 1, po kolei]
//     dane warstwy = pola z maski warstwy (kFieldType, kFieldFlow, …) po kolei; każde pole to ciągły fragment tablicy
//     z ramką w pozostałych osiach (VectorStorage::layerStart / layerCells) — kopiowany jednym memcpy przy pakowaniu
//     i rozpakowaniu.
//   "datatype" (etap 11) — typ pochodny MPI opisuje dane komunikatu wprost w siatce okna, bez bufora pośredniego:
//     warstwa jednego pola = MPI_Type_contiguous(komórki warstwy, typ pola) (MPI_UNSIGNED_CHAR typ komórki, MPI_INT
//     flowId i orientacja MC, MPI_FLOAT temperatura, MPI_UNSIGNED_SHORT solidStep / arrivalStep);
//     komunikat = MPI_Type_create_struct z bloków „warstwa pola” pod adresami bezwzględnymi (MPI_Get_address, wysyłka
//     i odbiór od MPI_BOTTOM) — pola SoA leżą w osobnych tablicach, więc struktura łączy fragmenty kilku tablic;
//     kolejne warstwy tego samego pola leżą w tablicy obok siebie (oś warstw jest zewnętrzna), więc łączą się w jeden
//     blok (lawa: 16 warstw samego typu pod pasem = 1 blok). Kolejność danych (warstwa po warstwie, pole po polu) jest
//     ta sama u nadawcy i odbiorcy, więc sygnatury typów się zgadzają.
//     Typy są budowane raz na bufor i komunikat (przy pierwszej wymianie z danym buforem), zatwierdzane
//     MPI_Type_commit i trzymane do końca (MPI_Type_free w destruktorze). Pełny przebieg automatu zamienia bufory
//     cur / next (VectorStorage::swap zamienia tablice) — adresy pól zmieniają się co krok, dlatego są DWA zestawy
//     typów, po jednym na bufor (klucz = adres tablicy typu komórki); przesunięcia względne nie wystarczą, bo każde pole
//     to osobna alokacja. Wariant "changed": flagi warstw idą osobnym małym komunikatem (MPI_UNSIGNED_CHAR, znacznik
//     tag + 100), a dane — typem złożonym tylko z warstw z flagą 1 (typ na bufor, komunikat i maskę flag, też z pamięci
//     podręcznej); odbiorca czeka na flagi, potem odbiera dane typem dla tej samej maski.
// Wariant mpi.exchange = "changed": nadawca porównuje warstwę z ostatnio wysłaną (memcmp) i przy braku zmian jej nie
// wysyła; odbiorca zostawia wtedy poprzednią kopię. "always" — wszystkie warstwy. Wynik jest ten sam, zmienia się
// liczba bajtów (liczniki CommCounters).
//
// Pełny przebieg automatu dostaje odebrane warstwy w obu buforach (cur, next): po zamianie buforów okno musi mieć
// ostatnio otrzymane warstwy brzegowe, także te pominięte przez "changed" (manual: rozpakowanie do obu; datatype:
// odbiór do cur i kopia odebranych warstw do next).

#include <mpi.h>

#include <cstddef>
#include <cstdint>
#include <map>
#include <tuple>
#include <vector>

#include "mpi/MpiTypes.hpp"
#include "parallel/Strip.hpp"

namespace volcano {

// Komunikacja jednego etapu (CA albo MC) na jednym procesie.
struct CommCounters {
    double haloMs = 0.0;              // wymiana warstw brzegowych: pakowanie, przesył, czekanie, rozpakowanie
    double reduceMs = 0.0;            // MPI_Allreduce liczników (reguła końca, energia, akceptacja)
    std::uint64_t exchanges = 0;      // wymiany warstw
    std::uint64_t messages = 0;       // wysłane komunikaty
    std::uint64_t bytes = 0;          // wysłane bajty (z flagami)
    std::uint64_t layersSent = 0;     // warstwy wysłane z danymi
    std::uint64_t layersSkipped = 0;  // warstwy pominięte ("changed": bez zmian od ostatniej wysyłki)
    std::uint64_t reductions = 0;     // wywołania MPI_Allreduce
    std::uint64_t typesBuilt = 0;     // datatype: zbudowane i zatwierdzone typy komunikatów
    double typeBuildMs = 0.0;         // datatype: czas budowy typów (część haloMs)

    double commMs() const { return haloMs + reduceMs; }
};

class MpiHalo final : public StripLink {
public:
    // plan — pas tego procesu; changedOnly — mpi.exchange = "changed"; datatypes — mpi.pack = "datatype";
    // tag — znacznik komunikatów etapu.
    MpiHalo(MPI_Comm comm, StripPlan plan, bool changedOnly, bool datatypes, int tag);
    MpiHalo(const MpiHalo&) = delete;
    MpiHalo& operator=(const MpiHalo&) = delete;

    void sum(std::uint64_t* values, int n) override;
    void exchange(VectorStorage& cur, VectorStorage* next) override;
    void exchange(PottsMC& mc) override;

    const StripPlan& plan() const { return plan_; }
    // Liczniki: część „sim” (kroki CA / MCS) i „stats” (statystyki MC) — wybór setStatsPhase.
    void setStatsPhase(bool stats) { active_ = stats ? &stats_ : &sim_; }
    const CommCounters& simCounters() const { return sim_; }
    const CommCounters& statsCounters() const { return stats_; }

private:
    // Dostęp do warstw okna: wskaźniki pól (indeks = numer bitu maski StripField) i układ warstw.
    struct Layers {
        unsigned char* field[6] = {nullptr, nullptr, nullptr, nullptr, nullptr, nullptr};
        std::size_t elem[6] = {0, 0, 0, 0, 0, 0};
        std::size_t start0 = 0;  // layerStart(0); layerStart(k) = start0 + k · cells
        std::size_t cells = 0;   // komórki warstwy z ramką
        // Adres pola f warstwy okna k.
        unsigned char* at(int f, int k) const {
            return field[f] + (start0 + static_cast<std::size_t>(k) * cells) * elem[f];
        }
        // Klucz bufora (typy datatype): tablica typu komórki (CA) albo orientacji (MC).
        std::uintptr_t key() const {
            return reinterpret_cast<std::uintptr_t>(field[0] != nullptr ? field[0] : field[5]);
        }
    };
    static Layers of(VectorStorage& s);
    static Layers of(PottsMC& mc);
    std::size_t segmentBytes(unsigned fields) const;
    void run(const Layers& src, const Layers* second);       // mpi.pack = "manual"
    void runTyped(const Layers& src, const Layers* second);  // mpi.pack = "datatype"
    // Typ komunikatu m (warstwy z bitem w masce mask) w buforze src — z pamięci podręcznej albo zbudowany teraz.
    MPI_Datatype messageType(const Layers& src, bool send, std::size_t index, const StripPlan::Message& m,
                             std::uint64_t mask, int& bytes);
    // Kopia warstw z maską mask komunikatu m z bufora src do second (pełny przebieg).
    static void copyLayers(const Layers& src, const Layers& second, const StripPlan::Message& m, std::uint64_t mask);

    MPI_Comm comm_;
    StripPlan plan_;
    bool changedOnly_;
    bool datatypes_;
    int tag_;
    std::size_t elem_[6] = {1, 4, 4, 2, 2, 4};  // rozmiar elementu pola
    std::size_t cells_ = 0;                       // komórki warstwy (ustalane przy pierwszej wymianie)
    std::vector<std::vector<unsigned char>> sendBuf_;
    std::vector<std::vector<unsigned char>> lastSent_;  // "changed": ostatnio wysłane dane każdego komunikatu
    std::vector<bool> lastValid_;
    std::vector<std::vector<unsigned char>> recvBuf_;
    std::vector<MPI_Request> requests_;
    // datatype: typ warstwy każdego pola i typy komunikatów (bufor, kierunek, komunikat, maska) -> (typ, bajty)
    MpiType layerType_[6];
    std::map<std::tuple<std::uintptr_t, bool, std::size_t, std::uint64_t>, std::pair<MpiType, int>> types_;
    std::vector<std::vector<unsigned char>> flagsOut_;  // datatype + changed: flagi warstw do wysłania / odebrane
    std::vector<std::vector<unsigned char>> flagsIn_;
    CommCounters sim_;
    CommCounters stats_;
    CommCounters* active_ = &sim_;
};

}  // namespace volcano
