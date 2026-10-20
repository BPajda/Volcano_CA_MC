#pragma once
// OpenMP w silniku (etap 9) — jeden nagłówek dla całego kodu:
//
//   * <omp.h> albo zastępcze funkcje omp_* dla buildu bez OpenMP (opcja CMake VOLCANO_OPENMP=OFF) — kod woła
//     omp_get_thread_num(), omp_get_wtime() itd. zawsze tak samo, a dyrektywy #pragma omp kompilator bez OpenMP
//     po prostu pomija;
//   * ustawienia równoległości z configu (sekcja parallel): liczba wątków, harmonogram, rozmiar porcji, przypinanie;
//   * ompFor — pętla podziału pracy z harmonogramem wybranym w czasie działania programu;
//   * PhaseClock / ThreadStats (ThreadStats.hpp) — czas pracy każdego wątku (--thread-stats).
//
// MSVC buduje z /openmp, czyli OpenMP 2.0 (biblioteka vcomp140 z pakietu redystrybucyjnego Visual C++): pętla
// równoległa wymaga indeksu ze znakiem (std::ptrdiff_t), nie ma collapse, zadań (task) ani omp_set_schedule().
// Harmonogramu z configu nie da się więc przekazać przez schedule(runtime) — ompFor wybiera jeden z sześciu wariantów
// dyrektywy (static / dynamic / guided, z porcją i bez) instrukcją switch. Ten sam kod kompiluje GCC (OpenMP 4.5).
// Dlaczego nie /openmp:llvm (OpenMP 3.1+): docs/etap-9-openmp.md, punkt 1.
//
// Zasady kodu równoległego (wynik nie zależy od liczby wątków ani harmonogramu):
//   * w pętli równoległej wątek pisze tylko do „swoich” elementów (komórki swojej warstwy, swoje listy, swój slot);
//   * losowość wyłącznie z hashRand(seed, krok, globalIndex, sól) — bez generatorów ze stanem;
//   * liczniki przez reduction (liczby całkowite — suma nie zależy od kolejności);
//   * faza czytająca wynik poprzedniej zaczyna się po barierze (ompBarrier()).

#include <cstddef>
#include <cstdint>

#ifdef _OPENMP
#  include <omp.h>
#else
#  include <chrono>
// Zastępcze funkcje OpenMP dla buildu bez OpenMP: jeden wątek, zegar monotoniczny.
inline int omp_get_thread_num() { return 0; }
inline int omp_get_num_threads() { return 1; }
inline int omp_get_max_threads() { return 1; }
inline int omp_in_parallel() { return 0; }
inline void omp_set_num_threads(int) {}
inline double omp_get_wtime() {
    return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
}
#endif

namespace volcano {

// Czy program zbudowano z OpenMP (i wersja specyfikacji z makra _OPENMP, np. 200203 = 2.0, 201511 = 4.5).
inline bool openmpBuilt() {
#ifdef _OPENMP
    return true;
#else
    return false;
#endif
}
inline long openmpVersion() {
#ifdef _OPENMP
    return static_cast<long>(_OPENMP);
#else
    return 0;
#endif
}

// Harmonogram podziału iteracji pętli równoległej (parallel.schedule).
enum class Schedule { Static, Dynamic, Guided };

// Przypinanie wątków (parallel.affinity): none — o rdzeniach decyduje system; pcores — jeden wątek na rdzeń
// fizyczny wydajny (P), parallel/Affinity.hpp.
enum class Affinity { None, PCores };

inline const char* nameOf(Schedule s) {
    switch (s) {
        case Schedule::Static: return "static";
        case Schedule::Dynamic: return "dynamic";
        case Schedule::Guided: return "guided";
    }
    return "?";
}

inline const char* nameOf(Affinity a) { return a == Affinity::PCores ? "pcores" : "none"; }

class ThreadStats;

// Ustawienia równoległości przekazywane do automatu i MC (z configu i linii poleceń, po rozwinięciu threads = 0).
struct ParallelSettings {
    int threads = 1;                       // liczba wątków regionów równoległych (1 = kod sekwencyjny jak w etapie 8)
    Schedule schedule = Schedule::Static;  // harmonogram pętli po warstwach / pasach
    int chunk = 0;                         // rozmiar porcji; 0 = domyślny OpenMP (static: równe bloki, dynamic: 1)
    ThreadStats* stats = nullptr;          // --thread-stats: czas pracy wątków (nullptr = bez pomiaru)

    bool parallel() const { return threads > 1; }
};

// Pętla i = 0..n-1 dzielona między wątki BIEŻĄCEGO regionu równoległego wg harmonogramu s i porcji chunk — dyrektywa
// „osierocona” (orphaned) wywoływana z wnętrza #pragma omp parallel. Bez bariery na końcu (nowait): barierę stawia
// wywołujący, gdy następna faza czyta wynik tej. Poza regionem (albo bez OpenMP) — zwykła pętla w jednym wątku.
template <class Body>
inline void ompFor(std::ptrdiff_t n, Schedule s, int chunk, Body&& body) {
#ifdef _OPENMP
    switch (s) {
        case Schedule::Static:
            if (chunk > 0) {
#  pragma omp for schedule(static, chunk) nowait
                for (std::ptrdiff_t i = 0; i < n; ++i) {
                    body(i);
                }
            } else {
#  pragma omp for schedule(static) nowait
                for (std::ptrdiff_t i = 0; i < n; ++i) {
                    body(i);
                }
            }
            break;
        case Schedule::Dynamic:
            if (chunk > 0) {
#  pragma omp for schedule(dynamic, chunk) nowait
                for (std::ptrdiff_t i = 0; i < n; ++i) {
                    body(i);
                }
            } else {
#  pragma omp for schedule(dynamic) nowait
                for (std::ptrdiff_t i = 0; i < n; ++i) {
                    body(i);
                }
            }
            break;
        case Schedule::Guided:
            if (chunk > 0) {
#  pragma omp for schedule(guided, chunk) nowait
                for (std::ptrdiff_t i = 0; i < n; ++i) {
                    body(i);
                }
            } else {
#  pragma omp for schedule(guided) nowait
                for (std::ptrdiff_t i = 0; i < n; ++i) {
                    body(i);
                }
            }
            break;
    }
#else
    (void)s;
    (void)chunk;
    for (std::ptrdiff_t i = 0; i < n; ++i) {
        body(i);
    }
#endif
}

// Bariera wątków bieżącego regionu („osierocona” — wywoływana z funkcji w regionie). Bez OpenMP nic nie robi.
inline void ompBarrier() {
#ifdef _OPENMP
#  pragma omp barrier
#endif
}

}  // namespace volcano
