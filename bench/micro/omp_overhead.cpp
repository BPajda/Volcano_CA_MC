// Mikrotest narzutu OpenMP (etap 9): ile kosztuje synchronizacja w porównaniu z pracą kroku automatu.
//
//   * region równoległy (fork/join) — pusty #pragma omp parallel num_threads(p),
//   * bariera — wiele #pragma omp barrier w jednym regionie,
//   * krok „jak w automacie”: region + 3 fazy ompFor po 64 warstwach (praca ~0) + bariery, każdy harmonogram,
//   * trwałość wątków puli: czy wątek o numerze i jest w kolejnych regionach tym samym wątkiem systemu
//     (warunek jednorazowego przypięcia w parallel/Affinity.cpp),
//   * region z jednym wątkiem (num_threads(1)) w porównaniu ze zwykłą pętlą.
//
// Użycie: omp_overhead [--pin] [--reps N]   (--pin: wątki przypięte jak parallel.affinity = pcores)
// Wynik: tabela na stdout (µs na operację). Build: cel CMake omp_overhead (tylko z OpenMP).

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "parallel/Affinity.hpp"
#include "parallel/Omp.hpp"

#ifdef _WIN32
#  ifndef WIN32_LEAN_AND_MEAN
#    define WIN32_LEAN_AND_MEAN
#  endif
#  ifndef NOMINMAX
#    define NOMINMAX
#  endif
#  include <windows.h>
#else
#  include <pthread.h>
#endif

namespace {

volatile double g_sink = 0.0;  // wynik pętli — kompilator nie może jej usunąć

// Identyfikator wątku systemu (do sprawdzenia trwałości puli).
std::uint64_t osThreadId() {
#ifdef _WIN32
    return GetCurrentThreadId();
#else
    return static_cast<std::uint64_t>(pthread_self());
#endif
}

}  // namespace

int main(int argc, char** argv) {
    using namespace volcano;
    bool pin = false;
    int reps = 20000;
    for (int i = 1; i < argc; ++i) {
        if (std::strcmp(argv[i], "--pin") == 0) {
            pin = true;
        } else if (std::strcmp(argv[i], "--reps") == 0 && i + 1 < argc) {
            reps = std::stoi(argv[++i]);
        }
    }
    std::printf("_OPENMP %ld, omp_get_max_threads() %d, przypięcie: %s\n", openmpVersion(), omp_get_max_threads(),
                pin ? "pcores" : "brak");
    const int maxT = 8;
    if (pin) {
        const CpuPlan plan = CpuAffinity::performanceCores();
        const std::vector<int> cpus = CpuAffinity::pinThreads(plan, maxT);
        std::printf("%s; wątki ->", plan.method.c_str());
        for (const int c : cpus) {
            std::printf(" %d", c);
        }
        std::printf("\n");
    }
    std::printf("%-58s %10s %10s %10s\n", "operacja [µs]", "p = 2", "p = 4", "p = 8");
    const int threadCounts[3] = {2, 4, 8};

    // 1. Region (fork/join) i trwałość wątków.
    double region[3];
    int moved[3];
    for (int ti = 0; ti < 3; ++ti) {
        const int p = threadCounts[ti];
        std::vector<std::uint64_t> ids(static_cast<std::size_t>(p), 0);
#pragma omp parallel num_threads(p)
        ids[static_cast<std::size_t>(omp_get_thread_num())] = osThreadId();
        int changes = 0;
        const double t0 = omp_get_wtime();
        for (int r = 0; r < reps; ++r) {
#pragma omp parallel num_threads(p) reduction(+ : changes)
            changes += ids[static_cast<std::size_t>(omp_get_thread_num())] != osThreadId() ? 1 : 0;
        }
        region[ti] = (omp_get_wtime() - t0) / reps * 1e6;
        moved[ti] = changes;
    }
    std::printf("%-58s %10.2f %10.2f %10.2f\n", "region równoległy (fork/join)", region[0], region[1], region[2]);

    // 2. Bariera.
    double barrier[3];
    for (int ti = 0; ti < 3; ++ti) {
        const int p = threadCounts[ti];
        const int n = reps;
        double t = 0.0;
#pragma omp parallel num_threads(p)
        {
            ompBarrier();
            const double t0 = omp_get_wtime();
            for (int r = 0; r < n; ++r) {
                ompBarrier();
            }
            if (omp_get_thread_num() == 0) {
                t = omp_get_wtime() - t0;
            }
        }
        barrier[ti] = t / n * 1e6;
    }
    std::printf("%-58s %10.2f %10.2f %10.2f\n", "bariera", barrier[0], barrier[1], barrier[2]);

    // 3. Krok jak w automacie frontalnym: region + 3 fazy po 64 warstwach + 2 bariery.
    const Schedule kinds[3] = {Schedule::Static, Schedule::Dynamic, Schedule::Guided};
    for (const Schedule s : kinds) {
        double step[3];
        for (int ti = 0; ti < 3; ++ti) {
            const int p = threadCounts[ti];
            std::vector<double> layer(64, 1.0);
            const int n = reps / 4;
            const double t0 = omp_get_wtime();
            for (int r = 0; r < n; ++r) {
                std::uint64_t sum = 0;
#pragma omp parallel num_threads(p) reduction(+ : sum)
                {
                    for (int ph = 0; ph < 3; ++ph) {
                        ompFor(64, s, 0, [&](std::ptrdiff_t k) {
                            layer[static_cast<std::size_t>(k)] += 1e-9;
                            sum += static_cast<std::uint64_t>(k);
                        });
                        if (ph < 2) {
                            ompBarrier();
                        }
                    }
                }
                g_sink = g_sink + static_cast<double>(sum);
            }
            step[ti] = (omp_get_wtime() - t0) / n * 1e6;
        }
        const std::string name = std::string("krok: region + 3 fazy ompFor(64) + 2 bariery, ") + nameOf(s);
        std::printf("%-58s %10.2f %10.2f %10.2f\n", name.c_str(), step[0], step[1], step[2]);
    }
    std::printf("%-58s %10d %10d %10d\n", "zmiany wątku systemu w regionach (trwałość puli)", moved[0], moved[1],
                moved[2]);

    // 4. Jeden wątek: region num_threads(1) vs zwykła pętla.
    const int n1 = reps * 10;
    double t0 = omp_get_wtime();
    for (int r = 0; r < n1; ++r) {
        std::uint64_t sum = 0;
#pragma omp parallel num_threads(1) reduction(+ : sum)
        ompFor(64, Schedule::Static, 0, [&](std::ptrdiff_t k) { sum += static_cast<std::uint64_t>(k); });
        g_sink = g_sink + static_cast<double>(sum);
    }
    const double one = (omp_get_wtime() - t0) / n1 * 1e6;
    t0 = omp_get_wtime();
    for (int r = 0; r < n1; ++r) {
        std::uint64_t sum = 0;
        for (std::uint64_t k = 0; k < 64; ++k) {
            sum += k;
        }
        g_sink = g_sink + static_cast<double>(sum);
    }
    const double plain = (omp_get_wtime() - t0) / n1 * 1e6;
    std::printf("%-58s %10.3f\n", "region num_threads(1) + ompFor(64)", one);
    std::printf("%-58s %10.3f\n", "zwykła pętla (64)", plain);
    return 0;
}
