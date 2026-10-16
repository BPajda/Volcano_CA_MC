#pragma once
// Pomiar czasu rzeczywistego (wall time) na zegarze monotonicznym.
// steady_clock nie cofa się przy zmianie czasu systemowego — właściwy do pomiarów
// wydajności. Wynik w milisekundach z ułamkiem.

#include <chrono>

namespace volcano {

class Timer {
public:
    using Clock = std::chrono::steady_clock;

    Timer() : start_(Clock::now()) {}

    // Rozpoczyna pomiar od nowa.
    void reset() { start_ = Clock::now(); }

    // Czas od utworzenia / ostatniego reset() w milisekundach.
    double elapsedMs() const {
        return std::chrono::duration<double, std::milli>(Clock::now() - start_).count();
    }

private:
    Clock::time_point start_;
};

// Stoper faz kroku (--timing-detail, etap 3): lap(acc) dodaje do acc czas od poprzedniego
// okrążenia [ms]. Zegar jest czytany raz na fazę kroku, a nie na komórkę, więc pomiar jest
// tani. Wyłączony stoper nie czyta zegara wcale — zwykły przebieg nie jest zaburzany.
class LapTimer {
public:
    using Clock = std::chrono::steady_clock;

    explicit LapTimer(bool enabled) : enabled_(enabled) {
        if (enabled_) {
            last_ = Clock::now();
        }
    }

    void lap(double& accMs) {
        if (!enabled_) {
            return;
        }
        const Clock::time_point now = Clock::now();
        accMs += std::chrono::duration<double, std::milli>(now - last_).count();
        last_ = now;
    }

private:
    bool enabled_;
    Clock::time_point last_{};
};

}  // namespace volcano
