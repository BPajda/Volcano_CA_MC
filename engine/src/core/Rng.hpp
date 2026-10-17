#pragma once
// Deterministyczna losowość.
//
// W kroku automatu NIE używamy generatora ze stanem (rand(), mt19937), tylko funkcji
// mieszającej z położenia: hashRand(seed, krok, globalnyIndeksKomórki, sól).
// Dzięki temu wynik nie zależy od kolejności przetwarzania komórek, od reprezentacji
// siatki (vector / macierz), a w wersji równoległej — od liczby wątków OpenMP i procesów MPI.
//
// Generator ze stanem (mt19937_64) używamy tylko do rzeczy liczonych raz, sekwencyjnie
// (lista kraterów / zarodków). Jego wyjście jest określone przez standard C++, natomiast
// std::uniform_int_distribution i std::shuffle NIE są — dają inne wyniki w MSVC i GCC.
// Dlatego mamy własne uniformBelow() i przetasowanie Fishera–Yatesa w VentPlacer.

#include <cstdint>
#include <random>

#include "core/Profile.hpp"

namespace volcano {

// „Sole” — rozdzielają strumienie losowe różnych decyzji w tym samym kroku i komórce.
constexpr std::uint64_t kSaltNeighborhood = 0x4E45494748424F52ULL;  // wariant sąsiedztwa losowego
constexpr std::uint64_t kSaltTieBreak = 0x5449455F42524B31ULL;      // remis w głosowaniu flowId
constexpr std::uint64_t kSaltTerrain = 0x5445525241494E31ULL;       // szum terenu
constexpr std::uint64_t kSaltVents = 0x56454E5453454544ULL;         // rozmieszczenie kraterów
// Monte Carlo (mc/McRules.hpp): osobny strumień dla każdej decyzji w próbie.
constexpr std::uint64_t kSaltMcInit = 0x4D43494E49544F52ULL;        // orientacja początkowa komórki
constexpr std::uint64_t kSaltMcPick = 0x4D435049434B4345ULL;        // krok 1: wybór komórki
constexpr std::uint64_t kSaltMcMobility = 0x4D434D4F42494C49ULL;    // pominięcie próby (mobilność)
constexpr std::uint64_t kSaltMcOrient = 0x4D434F5249454E54ULL;      // krok 3: nowa orientacja
constexpr std::uint64_t kSaltMcAccept = 0x4D43414343455054ULL;      // krok 5: akceptacja Metropolisa

// splitmix64 (Steele, Lea, Flood 2014) — krótka funkcja mieszająca o bardzo dobrej
// jakości; ten sam algorytm służy do inicjalizacji xoshiro.
inline std::uint64_t splitmix64(std::uint64_t x) {
    x += 0x9E3779B97F4A7C15ULL;
    x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9ULL;
    x = (x ^ (x >> 27)) * 0x94D049BB133111EBULL;
    return x ^ (x >> 31);
}

// Liczba pseudolosowa zależna wyłącznie od (seed, step, globalIndex, salt).
// Kaskada splitmix64 — każde wejście przechodzi pełne mieszanie, więc sąsiednie
// komórki i kolejne kroki dają nieskorelowane wartości.
// (VOLCANO_NOINLINE — tylko w presetach profilowania: hashRand widoczny w profilu jako osobna funkcja.)
VOLCANO_NOINLINE inline std::uint64_t hashRand(std::uint64_t seed, std::uint64_t step, std::uint64_t globalIndex,
                                               std::uint64_t salt) {
    std::uint64_t h = splitmix64(seed ^ 0xA0761D6478BD642FULL);
    h = splitmix64(h ^ step);
    h = splitmix64(h ^ globalIndex);
    return splitmix64(h ^ salt);
}

// Liczba rzeczywista z [0, 1) — 53 najstarsze bity hasha (pełna precyzja double).
inline double hashUniform(std::uint64_t seed, std::uint64_t step, std::uint64_t globalIndex,
                          std::uint64_t salt) {
    return static_cast<double>(hashRand(seed, step, globalIndex, salt) >> 11) *
           (1.0 / 9007199254740992.0);
}

// Kaskada hashRand rozbita na ogniwa (etap 8). Pętla, w której seed i krok są stałe, liczy dwa pierwsze
// ogniwa raz przed pętlą (hashPrefix), ogniwo indeksu raz na próbę/komórkę (hashIndex) — wspólne dla
// wszystkich decyzji tej próby — i tylko ostatnie ogniwo osobno dla każdej soli (hashSalt). Wynik bitowo
// ten sam: hashRand(seed, step, i, salt) == hashSalt(hashIndex(hashPrefix(seed, step), i), salt).
// OPTYMALIZACJA: w próbie MC 3 wywołania splitmix64 zamiast 8 (test w test_rng.cpp).
inline std::uint64_t hashPrefix(std::uint64_t seed, std::uint64_t step) {
    return splitmix64(splitmix64(seed ^ 0xA0761D6478BD642FULL) ^ step);
}
inline std::uint64_t hashIndex(std::uint64_t prefix, std::uint64_t globalIndex) {
    return splitmix64(prefix ^ globalIndex);
}
inline std::uint64_t hashSalt(std::uint64_t indexHash, std::uint64_t salt) { return splitmix64(indexHash ^ salt); }
// Liczba z [0, 1) z gotowego hasha — jak hashUniform.
inline double toUniform(std::uint64_t r) { return static_cast<double>(r >> 11) * (1.0 / 9007199254740992.0); }

// Liczba całkowita z [0, n) z generatora mt19937_64 (n > 0).
// Operacja modulo ma pomijalne obciążenie dla n << 2^64, a w przeciwieństwie do
// std::uniform_int_distribution daje identyczny wynik na każdym kompilatorze.
inline std::uint64_t uniformBelow(std::mt19937_64& gen, std::uint64_t n) {
    return gen() % n;
}

}  // namespace volcano
