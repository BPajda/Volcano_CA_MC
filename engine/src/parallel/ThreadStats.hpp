#pragma once
// Czas pracy wątków w fazach kroku (--thread-stats, etap 9) — pomiar nierównomierności obciążenia.
//
// W regionie równoległym każdy wątek mierzy (omp_get_wtime) czas swojej części każdej fazy: od wejścia do pętli ompFor
// do jej końca, BEZ czekania na barierze. Po kroku (poza regionem) endStep() liczy dla kroku czas pracy każdego wątku
// (suma faz) i dodaje do sum min / średnia / maks po wątkach. Stosunek Σ maks / Σ średnia (imbalance) mówi, ile razy
// krok trwał dłużej, niż gdyby praca była podzielona równo — bez narzutu synchronizacji, który pokazuje osobno czas
// regionów (wallMs) mierzony przez wątek główny.
//
// Odczyt zegara to dwa wywołania na fazę na wątek (nie na komórkę), i tylko z --thread-stats; bez flagi kod regionów
// nie czyta zegara wcale (PhaseClock z pustym wskaźnikiem nic nie robi).

#include <cstdint>
#include <string>
#include <vector>

#include "json.hpp"
#include "parallel/Omp.hpp"

namespace volcano {

class ThreadStats {
public:
    static constexpr int kMaxPhases = 8;

    // threads — liczba wątków regionów; phases — nazwy faz kroku (najwyżej kMaxPhases).
    ThreadStats(int threads, std::vector<std::string> phases);

    int threads() const { return threads_; }

    // Wątek tid dodaje czas pracy [s] w fazie ph bieżącego kroku. Wywoływane w regionie równoległym — każdy wątek pisze
    // tylko swój wiersz (wiersz = osobna linia pamięci podręcznej, bez fałszywego współdzielenia).
    void add(int tid, int ph, double seconds) { step_[static_cast<std::size_t>(tid)].v[ph] += seconds; }

    // Zapamiętuje procesor logiczny, na którym pracuje wątek tid (sprawdzenie przypięcia).
    void noteCpu(int tid);

    // Czas regionu równoległego kroku [s] mierzony przez wątek główny (praca + synchronizacja).
    void addWall(double seconds) { wall_ += seconds; }

    // Koniec kroku (poza regionem): sumy po krokach i min / średnia / maks czasu pracy wątków w kroku.
    void endStep();

    // Sekcja do times.json (czasy w ms).
    nlohmann::ordered_json toJson() const;

private:
    // Wiersz jednego wątku: czasy faz bieżącego kroku, wyrównany do 64 B.
    struct alignas(64) Row {
        double v[kMaxPhases] = {};
    };

    int threads_;
    std::vector<std::string> phases_;
    std::vector<Row> step_;                  // bieżący krok: [wątek].v[faza]
    std::vector<Row> total_;                 // suma po krokach: [wątek].v[faza]
    std::vector<double> phaseMax_;           // Σ po krokach maksimum po wątkach — dla każdej fazy
    std::vector<double> phaseMean_;          // Σ po krokach średniej po wątkach — dla każdej fazy
    std::vector<std::uint64_t> cpus_;        // procesory logiczne, na których był wątek (maska bitowa, do 64)
    double sumMax_ = 0.0;                    // Σ po krokach maksimum czasu pracy wątku w kroku
    double sumMean_ = 0.0;                   // Σ po krokach średniej
    double sumMin_ = 0.0;                    // Σ po krokach minimum
    double wall_ = 0.0;                      // Σ czasu regionów
    int steps_ = 0;
};

// Stoper fazy jednego wątku: begin() przed pętlą, end(faza) po pętli (przed barierą). Pusty wskaźnik — nic nie mierzy.
class PhaseClock {
public:
    PhaseClock(ThreadStats* stats, int tid) : stats_(stats), tid_(tid) {}

    void begin() {
        if (stats_ != nullptr) {
            t0_ = omp_get_wtime();
        }
    }
    void end(int phase) {
        if (stats_ != nullptr) {
            stats_->add(tid_, phase, omp_get_wtime() - t0_);
        }
    }

private:
    ThreadStats* stats_;
    int tid_;
    double t0_ = 0.0;
};

}  // namespace volcano
