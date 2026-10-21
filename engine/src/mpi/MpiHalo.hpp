#pragma once
// Wymiana warstw brzegowych pasów między procesami MPI (etap 10) — implementacja StripLink (parallel/Strip.hpp).
//
// Jedna wymiana = jeden komunikat do każdego sąsiada, który potrzebuje naszych warstw, i jeden od każdego, którego
// warstwy są u nas brzegowe (plan: planStrip). Wszystkie odbiory i wysyłki są nieblokujące (MPI_Irecv / MPI_Isend),
// a potem MPI_Waitall: przy pasach cieńszych niż 17 warstw lawa dostaje warstwy od kilku procesów pod sobą, więc
// zamiast par MPI_Sendrecv „w górę” i „w dół” jest lista komunikatów bez ustalonej kolejności — bez ryzyka
// zakleszczenia i z przesyłem do wszystkich sąsiadów naraz.
//
// Komunikat (pakowanie do bufora bajtów; typy pochodne MPI — etap 11):
//   [flaga warstwy 1] … [flaga warstwy n] [dane warstw z flagą 1, po kolei]
//   dane warstwy = pola z maski warstwy (kFieldType, kFieldFlow, …) po kolei; każde pole to ciągły fragment tablicy
//   z ramką w pozostałych osiach (VectorStorage::layerStart / layerCells) — kopiowany jednym memcpy.
// Wariant mpi.exchange = "changed": nadawca porównuje spakowaną warstwę z ostatnio wysłaną (memcmp) i przy braku zmian
// wysyła samą flagę 0; odbiorca zostawia wtedy poprzednią kopię. "always" — flaga zawsze 1. Wynik jest ten sam,
// zmienia się liczba bajtów (liczniki CommCounters).
//
// Pełny przebieg automatu rozpakowuje warstwy do obu buforów (cur, next): po zamianie buforów okno musi mieć ostatnio
// otrzymane warstwy brzegowe, także te pominięte przez "changed".

#include <mpi.h>

#include <cstddef>
#include <cstdint>
#include <vector>

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

    double commMs() const { return haloMs + reduceMs; }
};

class MpiHalo final : public StripLink {
public:
    // plan — pas tego procesu; changedOnly — mpi.exchange = "changed"; tag — znacznik komunikatów etapu.
    MpiHalo(MPI_Comm comm, StripPlan plan, bool changedOnly, int tag);

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
    };
    static Layers of(VectorStorage& s);
    static Layers of(PottsMC& mc);
    std::size_t segmentBytes(unsigned fields) const;
    void run(const Layers& src, const Layers* second);

    MPI_Comm comm_;
    StripPlan plan_;
    bool changedOnly_;
    int tag_;
    std::size_t elem_[6] = {1, 4, 4, 2, 2, 4};  // rozmiar elementu pola
    std::size_t cells_ = 0;                       // komórki warstwy (ustalane przy pierwszej wymianie)
    std::vector<std::vector<unsigned char>> sendBuf_;
    std::vector<std::vector<unsigned char>> lastSent_;  // "changed": ostatnio wysłane dane każdego komunikatu
    std::vector<bool> lastValid_;
    std::vector<std::vector<unsigned char>> recvBuf_;
    std::vector<MPI_Request> requests_;
    CommCounters sim_;
    CommCounters stats_;
    CommCounters* active_ = &sim_;
};

}  // namespace volcano
