// Mikrobenchmark składników próby Monte Carlo i dostępu do sąsiadów (etap 3).
//
// Cel: konkretna odpowiedź, dlaczego naiwne MC skompilowane GCC -O3 jest ~2x szybsze niż
// z MSVC /O2. Ten sam plik budują oba kompilatory z flagami silnika (cel CMake mc_kernels),
// a każde jądro mierzy jeden składnik próby z PottsMC::sweep():
//   - hashRand (kaskada 4 x splitmix64) — losowanie komórki, orientacji, akceptacji,
//   - dzielenie modulo 64-bit (wybór komórki % N i orientacji % (Q-1)),
//   - liczenie sąsiadów o innej orientacji (pętla po przesunięciach liniowych, VN 6 i Moore 26),
//   - exp(-dE/kT) (akceptacja Metropolisa przy kT > 0),
//   - indeks z współrzędnych (CA: x + sx*(y + sy*z) dla każdego sąsiada) vs przesunięcia liniowe (MC).
// Funkcje są kopiami pętli z silnika (hashRand wprost z core/Rng.hpp) — nie zmieniają silnika.
//
// Uruchomienie: build\Release\mc_kernels.exe   /   build-gcc-release/bin/mc_kernels
// (najlepiej przypięte do rdzenia P: start /affinity 4 ..., taskset -c 2 ...)
// Wynik: ns na iterację (minimum z 5 powtórzeń) i suma kontrolna (taka sama dla obu kompilatorów).

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <vector>

#include "core/Rng.hpp"

using namespace volcano;

namespace {

volatile std::uint64_t g_sink = 0;  // wynik jąder — kompilator nie może usunąć obliczeń
volatile std::uint64_t g_n = 125000;  // N komórek domeny (50^3) — wartość znana dopiero w czasie działania
volatile std::uint64_t g_q1 = 49;     // Q - 1
volatile double g_kT = 0.5;

constexpr std::uint64_t kSeed = 42;
constexpr std::uint64_t kStep = 7;

// Siatka 50^3 z ramką (52^3), jak w PottsMC: orientacje int32 i maska domeny uint8.
struct Grid {
    static constexpr int n = 50;
    static constexpr std::ptrdiff_t sx = n + 2;
    static constexpr std::ptrdiff_t sy = n + 2;
    std::vector<std::int32_t> spin;
    std::vector<std::uint8_t> mask;
    std::vector<std::size_t> domain;  // indeksy z ramką komórek domeny
    std::vector<std::ptrdiff_t> vn;   // przesunięcia liniowe von Neumanna (6)
    std::vector<std::ptrdiff_t> moore;  // Moore (26)

    // blockSize = 1: losowe orientacje (stan początkowy MC); > 1: bloki — jak po zgrubieniu ziaren.
    explicit Grid(int blockSize) : spin(sx * sy * (n + 2), 0), mask(sx * sy * (n + 2), 0) {
        for (int z = 0; z < n; ++z) {
            for (int y = 0; y < n; ++y) {
                for (int x = 0; x < n; ++x) {
                    const std::size_t i = static_cast<std::size_t>((x + 1) + sx * ((y + 1) + sy * (z + 1)));
                    const std::uint64_t cell = static_cast<std::uint64_t>(x / blockSize) +
                                               1000ULL * (static_cast<std::uint64_t>(y / blockSize) +
                                                          1000ULL * static_cast<std::uint64_t>(z / blockSize));
                    spin[i] = 1 + static_cast<std::int32_t>(hashRand(kSeed, 0, cell, kSaltMcInit) % 50);
                    mask[i] = 1;
                    domain.push_back(i);
                }
            }
        }
        for (int dz = -1; dz <= 1; ++dz) {
            for (int dy = -1; dy <= 1; ++dy) {
                for (int dx = -1; dx <= 1; ++dx) {
                    if (dx == 0 && dy == 0 && dz == 0) {
                        continue;
                    }
                    const std::ptrdiff_t off = dx + sx * (dy + sy * dz);
                    moore.push_back(off);
                    if (std::abs(dx) + std::abs(dy) + std::abs(dz) == 1) {
                        vn.push_back(off);
                    }
                }
            }
        }
    }

    // Kopia PottsMC::unlikeNeighbors.
    int unlike(std::size_t i, std::int32_t s, const std::vector<std::ptrdiff_t>& offsets) const {
        int c = 0;
        for (const std::ptrdiff_t o : offsets) {
            const std::size_t j = static_cast<std::size_t>(static_cast<std::ptrdiff_t>(i) + o);
            c += ((mask[j] & 1) != 0 && spin[j] != s) ? 1 : 0;
        }
        return c;
    }
};

// --- jądra: zwracają sumę kontrolną, iters = liczba iteracji ---

std::uint64_t kHash1(std::uint64_t iters) {
    std::uint64_t s = 0;
    for (std::uint64_t a = 0; a < iters; ++a) {
        s += hashRand(kSeed, kStep, a, kSaltMcPick);
    }
    return s;
}

std::uint64_t kHash2(std::uint64_t iters) {  // dwa hashe próby MC full: wybór komórki + orientacja
    std::uint64_t s = 0;
    for (std::uint64_t a = 0; a < iters; ++a) {
        s += hashRand(kSeed, kStep, a, kSaltMcPick) ^ hashRand(kSeed, kStep, a, kSaltMcOrient);
    }
    return s;
}

// To samo co kHash2, ale wspólny początek kaskady (seed, krok, indeks próby) liczony raz —
// tak, jak może to zrobić kompilator po wstawieniu hashRand (eliminacja wspólnych podwyrażeń).
std::uint64_t kHash2Shared(std::uint64_t iters) {
    std::uint64_t s = 0;
    const std::uint64_t h0 = splitmix64(splitmix64(kSeed ^ 0xA0761D6478BD642FULL) ^ kStep);
    for (std::uint64_t a = 0; a < iters; ++a) {
        const std::uint64_t h = splitmix64(h0 ^ a);
        s += splitmix64(h ^ kSaltMcPick) ^ splitmix64(h ^ kSaltMcOrient);
    }
    return s;
}

std::uint64_t kMod(std::uint64_t iters) {  // samo dzielenie modulo 64-bit przez N znane w czasie działania
    std::uint64_t s = 0;
    const std::uint64_t n = g_n;
    for (std::uint64_t a = 0; a < iters; ++a) {
        s += (a * 0x9E3779B97F4A7C15ULL) % n;
    }
    return s;
}

std::uint64_t kHash2Mod2(std::uint64_t iters) {  // część losowa próby: 2 hashe + 2 modulo
    std::uint64_t s = 0;
    const std::uint64_t n = g_n;
    const std::uint64_t q1 = g_q1;
    for (std::uint64_t a = 0; a < iters; ++a) {
        const std::uint64_t k = hashRand(kSeed, kStep, a, kSaltMcPick) % n;
        const std::uint64_t p = 1 + hashRand(kSeed, kStep, a, kSaltMcOrient) % q1;
        s += k * 64 + p;
    }
    return s;
}

// Energia przed i po zmianie dla losowych komórek (jak kroki 2 i 4 próby), bez hashy:
// wybrane komórki z gotowej listy, żeby mierzyć sam dostęp do sąsiadów.
std::uint64_t kNeighbors(const Grid& g, const std::vector<std::ptrdiff_t>& offsets, const std::vector<std::uint32_t>& picks,
                         std::uint64_t iters) {
    std::uint64_t s = 0;
    const std::size_t m = picks.size();
    for (std::uint64_t a = 0; a < iters; ++a) {
        const std::size_t i = g.domain[picks[a % m]];
        const std::int32_t cur = g.spin[i];
        const std::int32_t prop = 1 + static_cast<std::int32_t>((a * 7) % 49);
        s += static_cast<std::uint64_t>(g.unlike(i, cur, offsets) * 32 + g.unlike(i, prop, offsets));
    }
    return s;
}

std::uint64_t kExp(std::uint64_t iters) {  // akceptacja Metropolisa przy kT > 0
    double s = 0.0;
    const double kT = g_kT;
    for (std::uint64_t a = 0; a < iters; ++a) {
        s += std::exp(-static_cast<double>(1 + a % 26) / kT);
    }
    return static_cast<std::uint64_t>(s * 1e6);
}

// CA: odczyt 26 sąsiadów przez współrzędne (indeks liczony z x, y, z jak VectorStorage::index)
// vs przez stałe przesunięcia liniowe (jak PottsMC).
std::uint64_t kIndexCoords(const Grid& g, std::uint64_t iters) {
    std::uint64_t s = 0;
    const int n = Grid::n;
    std::uint64_t done = 0;
    while (done < iters) {
        for (int z = 0; z < n && done < iters; ++z) {
            for (int y = 0; y < n; ++y) {
                for (int x = 0; x < n; ++x, ++done) {
                    for (int dz = -1; dz <= 1; ++dz) {
                        for (int dy = -1; dy <= 1; ++dy) {
                            for (int dx = -1; dx <= 1; ++dx) {
                                const std::size_t j = static_cast<std::size_t>(x + dx + 1) +
                                                      static_cast<std::size_t>(Grid::sx) *
                                                          (static_cast<std::size_t>(y + dy + 1) +
                                                           static_cast<std::size_t>(Grid::sy) *
                                                               static_cast<std::size_t>(z + dz + 1));
                                s += g.mask[j];
                            }
                        }
                    }
                }
            }
        }
    }
    return s;
}

std::uint64_t kIndexLinear(const Grid& g, std::uint64_t iters) {
    std::uint64_t s = 0;
    std::uint64_t done = 0;
    while (done < iters) {
        for (std::size_t k = 0; k < g.domain.size() && done < iters; ++k, ++done) {
            const std::size_t i = g.domain[k];
            s += g.mask[i];
            for (const std::ptrdiff_t o : g.moore) {
                s += g.mask[static_cast<std::size_t>(static_cast<std::ptrdiff_t>(i) + o)];
            }
        }
    }
    return s;
}

// Minimum czasu z kilku powtórzeń [ns na iterację].
template <class F>
void measure(const char* name, std::uint64_t iters, F&& f) {
    double best = 1e300;
    std::uint64_t check = 0;
    for (int r = 0; r < 5; ++r) {
        const auto t0 = std::chrono::steady_clock::now();
        check = f(iters);
        const auto t1 = std::chrono::steady_clock::now();
        best = std::min(best, std::chrono::duration<double, std::nano>(t1 - t0).count() / static_cast<double>(iters));
        g_sink = g_sink + check;
    }
    std::printf("%-44s %9.2f ns   (suma kontrolna %016llx)\n", name, best, static_cast<unsigned long long>(check));
}

}  // namespace

int main() {
#if defined(_MSC_VER) && !defined(__clang__)
    std::printf("Kompilator: MSVC %d\n", _MSC_VER);
#elif defined(__GNUC__)
    std::printf("Kompilator: GCC %s\n", __VERSION__);
#endif
    const Grid random(1);  // stan początkowy MC: sąsiedzi prawie zawsze o innej orientacji
    const Grid coarse(3);  // bloki 3x3x3: jak po kilkudziesięciu MCS (ziarna ~20-30 komórek)
    std::vector<std::uint32_t> picks(1 << 20);
    for (std::size_t a = 0; a < picks.size(); ++a) {
        picks[a] = static_cast<std::uint32_t>(hashRand(kSeed, 1, a, kSaltMcPick) % random.domain.size());
    }
    const std::uint64_t it = 20'000'000;
    measure("hashRand x1", it, kHash1);
    measure("hashRand x2 (wybor + orientacja)", it, kHash2);
    measure("hashRand x2, wspolny poczatek kaskady", it, kHash2Shared);
    measure("modulo 64-bit (a*C) % N", it, kMod);
    measure("2 x hashRand + 2 x modulo (losowanie proby)", it, kHash2Mod2);
    measure("sasiedzi VN 6, E przed+po, losowe orient.", it, [&](std::uint64_t n) { return kNeighbors(random, random.vn, picks, n); });
    measure("sasiedzi VN 6, E przed+po, bloki 3^3", it, [&](std::uint64_t n) { return kNeighbors(coarse, coarse.vn, picks, n); });
    measure("sasiedzi Moore 26, E przed+po, losowe", it, [&](std::uint64_t n) { return kNeighbors(random, random.moore, picks, n); });
    measure("sasiedzi Moore 26, E przed+po, bloki 3^3", it, [&](std::uint64_t n) { return kNeighbors(coarse, coarse.moore, picks, n); });
    measure("exp(-dE/kT)", it, kExp);
    measure("CA: 27 odczytow, indeks z (x,y,z)", 5'000'000, [&](std::uint64_t n) { return kIndexCoords(random, n); });
    measure("MC: 27 odczytow, przesuniecia liniowe", 5'000'000, [&](std::uint64_t n) { return kIndexLinear(random, n); });
    return static_cast<int>(g_sink & 1);
}
