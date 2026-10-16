// Testy deterministycznej losowości (hash z położenia).
#include "doctest.h"

#include <set>

#include "core/Rng.hpp"

using namespace volcano;

TEST_CASE("hashRand: te same wejścia -> ta sama liczba, różne wejścia -> różne") {
    CHECK(hashRand(42, 7, 1000, kSaltTieBreak) == hashRand(42, 7, 1000, kSaltTieBreak));
    CHECK(hashRand(42, 7, 1000, kSaltTieBreak) != hashRand(43, 7, 1000, kSaltTieBreak));
    CHECK(hashRand(42, 7, 1000, kSaltTieBreak) != hashRand(42, 8, 1000, kSaltTieBreak));
    CHECK(hashRand(42, 7, 1000, kSaltTieBreak) != hashRand(42, 7, 1001, kSaltTieBreak));
    CHECK(hashRand(42, 7, 1000, kSaltTieBreak) != hashRand(42, 7, 1000, kSaltNeighborhood));
}

TEST_CASE("hashUniform: wartości w [0,1) i w miarę równomierne") {
    int buckets[10] = {};
    const int n = 100000;
    for (int i = 0; i < n; ++i) {
        const double u = hashUniform(1, 0, static_cast<std::uint64_t>(i), kSaltTerrain);
        REQUIRE(u >= 0.0);
        REQUIRE(u < 1.0);
        ++buckets[static_cast<int>(u * 10)];
    }
    for (int b : buckets) {
        CHECK(b > n / 10 * 0.95);
        CHECK(b < n / 10 * 1.05);
    }
}

TEST_CASE("uniformBelow: zakres i powtarzalność dla tego samego ziarna") {
    std::mt19937_64 a(5);
    std::mt19937_64 b(5);
    std::set<std::uint64_t> seen;
    for (int i = 0; i < 1000; ++i) {
        const auto va = uniformBelow(a, 7);
        CHECK(va < 7);
        CHECK(va == uniformBelow(b, 7));
        seen.insert(va);
    }
    CHECK(seen.size() == 7);
}
