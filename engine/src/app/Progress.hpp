#pragma once
// Raport postępu dla GUI (opcja --progress, etap 4): linie maszynowe na stdout
//   PROGRESS ca 120/5000 active=1834     (krok CA / ca.maxSteps, liczba komórek LAVA po kroku;
//                                         w classic: komórki należące do ziaren; przed 1. krokiem 0)
//   PROGRESS mc 35/100                   (MCS / mc.mcs)
//   PROGRESS save 0/1                    (zaczyna się zapis wyników)
// Linia jest wypisywana najwyżej co intervalMs (domyślnie 0,5 s) i od razu opróżniana (flush),
// żeby proces nadrzędny dostał ją bez czekania na zapełnienie bufora potoku.
//
// Koszt: jeden odczyt zegara na krok CA / MCS — poza gorącą pętlą (krok trwa od mikrosekund
// do setek milisekund). Bez --progress przebieg idzie dotychczasową ścieżką (LavaCA::run()),
// więc pomiar czasu i wynik są dokładnie takie jak wcześniej.

#include <cstdint>
#include <ostream>

#include "core/Timer.hpp"

namespace volcano {

class ProgressReporter {
public:
    // Wyłączony raport — report() nic nie robi.
    ProgressReporter() = default;

    // Raport do strumienia out (zwykle std::cout), najwyżej co intervalMs milisekund.
    explicit ProgressReporter(std::ostream& out, double intervalMs = 500.0)
        : out_(&out), intervalMs_(intervalMs) {}

    bool enabled() const { return out_ != nullptr; }

    // Zgłasza stan etapu stage: wykonane done z total. Linia trafia na wyjście, gdy od
    // poprzedniej minęło intervalMs albo gdy force (początek i koniec etapu — GUI zawsze
    // dostaje stan końcowy). extraKey/extraValue — opcjonalna para „klucz=wartość” na końcu linii.
    void report(const char* stage, long long done, long long total, bool force = false,
                const char* extraKey = nullptr, std::uint64_t extraValue = 0) {
        if (out_ == nullptr || (!force && sinceLast_.elapsedMs() < intervalMs_)) {
            return;
        }
        *out_ << "PROGRESS " << stage << ' ' << done << '/' << total;
        if (extraKey != nullptr) {
            *out_ << ' ' << extraKey << '=' << extraValue;
        }
        *out_ << '\n' << std::flush;
        sinceLast_.reset();
    }

private:
    std::ostream* out_ = nullptr;
    double intervalMs_ = 500.0;
    Timer sinceLast_;  // czas od ostatniej wypisanej linii
};

}  // namespace volcano
