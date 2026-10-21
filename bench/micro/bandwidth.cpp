// Mikrotest przepustowości pamięci (etap 12): czy przy 8 rdzeniach CA / MC są ograniczone pamięcią.
//
//   * stream   — jądra jak w STREAM (McCalpin): copy c = a, scale b = s·c, add c = a + b, triad a = b + s·c oraz odczyt
//                (suma a — CA i MC głównie czytają); tablice double po --size-mb MB każda (domyślnie 160 MB > 4 × L3),
//                pętle `omp for schedule(static)`, pierwsze dotknięcie stron przez te same wątki; dla p z --threads;
//                MB/s wg konwencji STREAM (copy, scale 16 B na element, add, triad 24 B, odczyt 8 B — bez dodatkowego
//                odczytu linii przy zapisie, tzw. write-allocate, który dokłada 8 B na zapisany element);
//   * sizes    — przepustowość w funkcji rozmiaru zbioru roboczego (odczyt i triad, 32 KB … 512 MB, p wątków) —
//                empiryczne progi L1 / L2 / L3 / RAM;
//   * false    — fałszywe współdzielenie: (1) licznik każdego wątku w sąsiednich 8 B jednej linii vs co 64 B,
//                zapis do pamięci w każdej iteracji (volatile — tak jak licznik przez referencję w etapie 9)
//                i atomowe dodawanie (fetch_add — każda operacja wymaga wyłącznego posiadania linii);
//                (2) listy warstw jak FrontLayer automatu frontalnego (4 × std::vector = 96 B w ciągłej tablicy —
//                nagłówki sąsiednich warstw w jednej linii 64 B) vs nagłówki wyrównane do 128 B; wątki dostają warstwy
//                cyklicznie (static,1 — jak front lawy), push_back zapisuje wskaźnik końca listy przy każdym elemencie.
//
// Użycie: bandwidth [--mode stream|sizes|false|all] [--threads 1,2,4,6,8] [--size-mb 160] [--reps 10] [--pin]
//                   [--high-priority] [--csv plik]
//   --pin: wątki przypięte jak parallel.affinity = pcores (rdzenie P: procesory 2, 4, …, 14, 0; parallel/Affinity.*).
// Wynik: tabela na stdout (+ CSV). Build: cel CMake bandwidth (tylko z OpenMP). Pomiar czasu — wolny komputer, tryb
// oszczędny (bez turbo), procesy przypięte; plan: bench/results/testy/PLAN_POMIARU.md.

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <memory>
#include <string>
#include <vector>

#include "parallel/Affinity.hpp"
#include "parallel/Omp.hpp"

namespace {

using Clock = std::chrono::steady_clock;

double nowSec() { return std::chrono::duration<double>(Clock::now().time_since_epoch()).count(); }

volatile double g_sink = 0.0;  // wynik sumy — kompilator nie może usunąć pętli odczytu

// Wynik jednego wariantu: najlepszy (jak STREAM) i mediana z powtórzeń.
struct Result {
    std::string mode, kernel;
    int threads = 0;
    double workingSet = 0.0;  // B
    double best = 0.0;        // MB/s albo ns / operację (false)
    double median = 0.0;
    const char* unit = "MB/s";
};

double median(std::vector<double> v) {
    std::sort(v.begin(), v.end());
    const std::size_t n = v.size();
    return n == 0 ? 0.0 : (n % 2 ? v[n / 2] : 0.5 * (v[n / 2 - 1] + v[n / 2]));
}

// Ustawia przypięcie zespołu p wątków (każda liczba wątków osobno — wątek i na i-tym rdzeniu P planu).
void pinTeam(const volcano::CpuPlan* plan, int p) {
    if (plan != nullptr) {
        volcano::CpuAffinity::pinThreads(*plan, p);
    }
}

// --- STREAM: jądra na tablicach a, b, c (n elementów), p wątków ---
struct Arrays {
    std::unique_ptr<double[]> a, b, c;
    std::ptrdiff_t n = 0;
};

Arrays allocArrays(std::ptrdiff_t n, int p) {
    Arrays r;
    n = std::max<std::ptrdiff_t>(8, n / 8 * 8);  // wielokrotność 8 — odczyt po blokach 8 elementów
    r.n = n;
    r.a.reset(new double[static_cast<std::size_t>(n)]);
    r.b.reset(new double[static_cast<std::size_t>(n)]);
    r.c.reset(new double[static_cast<std::size_t>(n)]);
    double* a = r.a.get();
    double* b = r.b.get();
    double* c = r.c.get();
    // Pierwsze dotknięcie stron przez te same wątki i ten sam podział co w pomiarze.
#ifdef _OPENMP
#  pragma omp parallel for schedule(static) num_threads(p)
#endif
    for (std::ptrdiff_t i = 0; i < n; ++i) {
        a[i] = 1.0;
        b[i] = 2.0;
        c[i] = 0.0;
    }
    return r;
}

// Jedno wykonanie jądra k (0 copy, 1 scale, 2 add, 3 triad, 4 odczyt); zwraca czas [s].
double runKernel(int k, Arrays& r, int p) {
    double* a = r.a.get();
    double* b = r.b.get();
    double* c = r.c.get();
    const std::ptrdiff_t n = r.n;
    const double s = 3.0;
    double sum = 0.0;
    const double t0 = nowSec();
#ifdef _OPENMP
#  pragma omp parallel num_threads(p)
#endif
    {
        switch (k) {
        case 0:
#ifdef _OPENMP
#  pragma omp for schedule(static)
#endif
            for (std::ptrdiff_t i = 0; i < n; ++i) {
                c[i] = a[i];
            }
            break;
        case 1:
#ifdef _OPENMP
#  pragma omp for schedule(static)
#endif
            for (std::ptrdiff_t i = 0; i < n; ++i) {
                b[i] = s * c[i];
            }
            break;
        case 2:
#ifdef _OPENMP
#  pragma omp for schedule(static)
#endif
            for (std::ptrdiff_t i = 0; i < n; ++i) {
                c[i] = a[i] + b[i];
            }
            break;
        case 3:
#ifdef _OPENMP
#  pragma omp for schedule(static)
#endif
            for (std::ptrdiff_t i = 0; i < n; ++i) {
                a[i] = b[i] + s * c[i];
            }
            break;
        default: {
            // 8 niezależnych sum częściowych: jedna suma to łańcuch zależnych dodawań (opóźnienie dodawania, nie
            // pamięć, ograniczałoby odczyt do ~8 GB/s na rdzeń). n jest wielokrotnością 8 (allocArrays).
            double s0 = 0.0, s1 = 0.0, s2 = 0.0, s3 = 0.0, s4 = 0.0, s5 = 0.0, s6 = 0.0, s7 = 0.0;
            const std::ptrdiff_t blocks = n / 8;
#ifdef _OPENMP
#  pragma omp for schedule(static)
#endif
            for (std::ptrdiff_t j = 0; j < blocks; ++j) {
                const double* q = a + 8 * j;
                s0 += q[0];
                s1 += q[1];
                s2 += q[2];
                s3 += q[3];
                s4 += q[4];
                s5 += q[5];
                s6 += q[6];
                s7 += q[7];
            }
            const double local = ((s0 + s1) + (s2 + s3)) + ((s4 + s5) + (s6 + s7));
#ifdef _OPENMP
#  pragma omp atomic
#endif
            sum += local;
        }
        }
    }
    const double t = nowSec() - t0;
    g_sink = g_sink + sum;
    return t;
}

const char* kKernels[] = {"copy", "scale", "add", "triad", "odczyt"};
const double kBytesPerElem[] = {16.0, 16.0, 24.0, 24.0, 8.0};

void stream(std::vector<Result>& out, const std::vector<int>& threads, double sizeMb, int reps,
            const volcano::CpuPlan* plan) {
    const auto n = static_cast<std::ptrdiff_t>(sizeMb * 1024.0 * 1024.0 / sizeof(double));
    for (const int p : threads) {
        pinTeam(plan, p);
        Arrays r = allocArrays(n, p);
        for (int k = 0; k < 5; ++k) {
            runKernel(k, r, p);  // rozgrzewka
            std::vector<double> mbs;
            for (int i = 0; i < reps; ++i) {
                mbs.push_back(kBytesPerElem[k] * static_cast<double>(n) / runKernel(k, r, p) / 1e6);
            }
            out.push_back(Result{"stream", kKernels[k], p, 3.0 * static_cast<double>(n) * sizeof(double),
                                 *std::max_element(mbs.begin(), mbs.end()), median(mbs)});
        }
        std::printf("stream p = %d: copy %.0f, scale %.0f, add %.0f, triad %.0f, odczyt %.0f MB/s (najlepszy)\n", p,
                    out[out.size() - 5].best, out[out.size() - 4].best, out[out.size() - 3].best,
                    out[out.size() - 2].best, out[out.size() - 1].best);
        std::fflush(stdout);
    }
}

// --- przepustowość w funkcji rozmiaru zbioru roboczego (odczyt i triad) ---
void sizes(std::vector<Result>& out, const std::vector<int>& threads, int reps, const volcano::CpuPlan* plan) {
    for (const int p : threads) {
        pinTeam(plan, p);
        for (double kb = 32; kb <= 512.0 * 1024.0; kb *= 2.0) {
            // Zbiór roboczy = 3 tablice (triad); odczyt — tylko a, więc ta sama długość tablicy daje 1/3 zbioru.
            const auto n = static_cast<std::ptrdiff_t>(kb * 1024.0 / 3.0 / sizeof(double));
            Arrays r = allocArrays(n, p);
            // Tyle powtórzeń jądra w jednym pomiarze, żeby przenieść ~256 MB (krótkie pętle mierzą się źle).
            const int inner = std::max(1, static_cast<int>(256.0 * 1024 * 1024 / (24.0 * static_cast<double>(n))));
            for (const int k : {4, 3}) {
                runKernel(k, r, p);
                std::vector<double> mbs;
                for (int i = 0; i < reps; ++i) {
                    double t = 0.0;
                    for (int j = 0; j < inner; ++j) {
                        t += runKernel(k, r, p);
                    }
                    mbs.push_back(kBytesPerElem[k] * static_cast<double>(n) * inner / t / 1e6);
                }
                const double ws = (k == 4 ? 1.0 : 3.0) * static_cast<double>(n) * sizeof(double);
                out.push_back(Result{"sizes", kKernels[k], p, ws, *std::max_element(mbs.begin(), mbs.end()),
                                     median(mbs)});
            }
            std::printf("sizes p = %d, %8.0f KB: odczyt %.0f, triad %.0f MB/s\n", p, kb, out[out.size() - 2].best,
                        out[out.size() - 1].best);
            std::fflush(stdout);
        }
    }
}

// --- fałszywe współdzielenie ---
// Struktura jak LavaCA::FrontLayer (4 listy) i ta sama wyrównana do 128 B (nagłówki sąsiednich warstw w różnych liniach).
struct Coord3 {
    int x, y, z;
};
struct LayerPacked {
    std::vector<Coord3> src, cand, nextSrc, changes;
};
#ifdef _MSC_VER
#  pragma warning(push)
#  pragma warning(disable : 4324)  // struktura dopełniona do wyrównania — tu celowo
#endif
struct alignas(128) LayerPadded {
    std::vector<Coord3> src, cand, nextSrc, changes;
};
#ifdef _MSC_VER
#  pragma warning(pop)
#endif

template <typename Layer>
double layersNsPerPush(int p, int layers, int perLayer, int steps) {
    std::vector<Layer> ls(static_cast<std::size_t>(layers));
    for (Layer& l : ls) {  // pojemność z góry — mierzymy zapis nagłówka, nie realokację
        l.cand.reserve(static_cast<std::size_t>(perLayer));
        l.nextSrc.reserve(static_cast<std::size_t>(perLayer));
        l.changes.reserve(static_cast<std::size_t>(perLayer));
    }
    const double t0 = nowSec();
    for (int s = 0; s < steps; ++s) {
#ifdef _OPENMP
#  pragma omp parallel for schedule(static, 1) num_threads(p)
#endif
        for (std::ptrdiff_t k = 0; k < layers; ++k) {
            Layer& l = ls[static_cast<std::size_t>(k)];
            l.cand.clear();
            l.nextSrc.clear();
            l.changes.clear();
            for (int i = 0; i < perLayer; ++i) {  // jak kandydaci i reguły: trzy listy rosną na zmianę
                const Coord3 c{i, static_cast<int>(k), s};
                l.cand.push_back(c);
                l.nextSrc.push_back(c);
                l.changes.push_back(c);
            }
        }
    }
    const double t = nowSec() - t0;
    std::size_t check = 0;
    for (const Layer& l : ls) {
        check += l.changes.size();
    }
    g_sink = g_sink + static_cast<double>(check);
    return t * 1e9 / (3.0 * static_cast<double>(layers) * perLayer * steps / p);  // ns na push_back w wątku
}

// Licznik każdego wątku co strideBytes: zwykły zapis do pamięci w każdej iteracji (volatile) albo atomowe dodawanie
// (instrukcja z blokadą — każda operacja wymaga wyłącznego posiadania linii).
double countersNsPerInc(int p, int strideBytes, std::int64_t iters, bool atomicAdd) {
    const int stride = strideBytes / static_cast<int>(sizeof(std::int64_t));
    const std::size_t n = static_cast<std::size_t>(stride) * 8 + 16;
    std::vector<std::int64_t> cnt(n, 0);
    std::unique_ptr<std::atomic<std::int64_t>[]> acnt(new std::atomic<std::int64_t>[n]);
    for (std::size_t i = 0; i < n; ++i) {
        acnt[i].store(0);
    }
    const double t0 = nowSec();
#ifdef _OPENMP
#  pragma omp parallel num_threads(p)
#endif
    {
        const std::size_t off = static_cast<std::size_t>(omp_get_thread_num()) * static_cast<std::size_t>(stride);
        if (atomicAdd) {
            std::atomic<std::int64_t>& c = acnt[off];
            for (std::int64_t i = 0; i < iters; ++i) {
                c.fetch_add(1, std::memory_order_relaxed);
            }
        } else {
            volatile std::int64_t* c = cnt.data() + off;
            for (std::int64_t i = 0; i < iters; ++i) {
                *c = *c + 1;
            }
        }
    }
    const double t = nowSec() - t0;
    g_sink = g_sink + static_cast<double>(cnt[0] + acnt[0].load());
    return t * 1e9 / static_cast<double>(iters);
}

void falseSharing(std::vector<Result>& out, const std::vector<int>& threads, int reps, const volcano::CpuPlan* plan) {
    for (const int p : threads) {
        pinTeam(plan, p);
        for (const bool atomicAdd : {false, true}) {
            for (const int stride : {8, 64}) {
                std::vector<double> ns;
                const std::int64_t iters = atomicAdd ? 2000000 : 20000000;
                countersNsPerInc(p, stride, iters / 10, atomicAdd);
                for (int i = 0; i < reps; ++i) {
                    ns.push_back(countersNsPerInc(p, stride, iters, atomicAdd));
                }
                const std::string name = std::string(atomicAdd ? "licznik atomowy" : "licznik (zapis)") +
                                         (stride == 8 ? " co 8 B" : " co 64 B");
                out.push_back(Result{"false", name, p, 0.0, *std::min_element(ns.begin(), ns.end()), median(ns),
                                     "ns/op"});
            }
        }
        // 64 warstwy (jak lawa 3D 128² × 64), po 2000 elementów na listę i krok, 200 kroków.
        for (const bool padded : {false, true}) {
            std::vector<double> ns;
            for (int i = 0; i < reps; ++i) {
                ns.push_back(padded ? layersNsPerPush<LayerPadded>(p, 64, 2000, 200)
                                    : layersNsPerPush<LayerPacked>(p, 64, 2000, 200));
            }
            out.push_back(Result{"false", padded ? "listy warstw: nagłówki co 128 B" : "listy warstw: nagłówki 96 B",
                                 p, 0.0, *std::min_element(ns.begin(), ns.end()), median(ns), "ns/op"});
        }
        const std::size_t e = out.size();
        std::printf("false p = %d: zapis co 8 / 64 B %.2f / %.2f ns, atomowy co 8 / 64 B %.2f / %.2f ns; listy "
                    "96 / 128 B %.2f / %.2f ns (mediany)\n",
                    p, out[e - 6].median, out[e - 5].median, out[e - 4].median, out[e - 3].median, out[e - 2].median,
                    out[e - 1].median);
        std::fflush(stdout);
    }
}

std::vector<int> parseList(const char* s) {
    std::vector<int> v;
    std::string cur;
    for (const char* q = s;; ++q) {
        if (*q == ',' || *q == '\0') {
            if (!cur.empty()) {
                v.push_back(std::stoi(cur));
            }
            cur.clear();
            if (*q == '\0') {
                break;
            }
        } else {
            cur += *q;
        }
    }
    return v;
}

}  // namespace

int main(int argc, char** argv) {
    using namespace volcano;
    std::string mode = "all";
    std::vector<int> threads = {1, 2, 4, 6, 8};
    double sizeMb = 160.0;
    int reps = 10;
    bool pin = false;
    bool high = false;
    std::string csv;
    for (int i = 1; i < argc; ++i) {
        const std::string a = argv[i];
        if (a == "--mode" && i + 1 < argc) {
            mode = argv[++i];
        } else if (a == "--threads" && i + 1 < argc) {
            threads = parseList(argv[++i]);
        } else if (a == "--size-mb" && i + 1 < argc) {
            sizeMb = std::stod(argv[++i]);
        } else if (a == "--reps" && i + 1 < argc) {
            reps = std::stoi(argv[++i]);
        } else if (a == "--csv" && i + 1 < argc) {
            csv = argv[++i];
        } else if (a == "--pin") {
            pin = true;
        } else if (a == "--high-priority") {
            high = true;
        } else {
            std::fprintf(stderr, "Nieznana opcja %s\n", argv[i]);
            return 2;
        }
    }
    for (const int p : threads) {
        if (p < 1 || p > 8) {
            std::fprintf(stderr, "Tryb oszczędny: 1–8 wątków (podano %d)\n", p);
            return 2;
        }
    }
    CpuPlan plan;
    if (pin) {
        plan = CpuAffinity::performanceCores();
    }
    std::string pri = "normalny";
    if (high && CpuAffinity::raisePriority(pri)) {
        pri = "wysoki (" + pri + ")";
    }
    std::printf("bandwidth: _OPENMP %ld, przypięcie %s, priorytet %s, tablice %.0f MB, powtórzeń %d\n",
                openmpVersion(), pin ? ("pcores — " + plan.method).c_str() : "brak", pri.c_str(), sizeMb, reps);
    std::vector<Result> out;
    const CpuPlan* pp = pin ? &plan : nullptr;
    if (mode == "stream" || mode == "all") {
        stream(out, threads, sizeMb, reps, pp);
    }
    if (mode == "sizes" || mode == "all") {
        sizes(out, threads, std::max(3, reps / 3), pp);
    }
    if (mode == "false" || mode == "all") {
        falseSharing(out, threads, std::max(3, reps / 2), pp);
    }
    if (!csv.empty()) {
        std::ofstream f(csv, std::ios::binary);  // binarnie — końce linii LF także w Windows
        if (!f) {
            std::fprintf(stderr, "Nie można zapisać %s\n", csv.c_str());
            return 1;
        }
        f << "mode,kernel,threads,workingSetBytes,best,median,unit\n";
        char line[256];
        for (const Result& r : out) {
            std::snprintf(line, sizeof(line), "%s,%s,%d,%.0f,%.3f,%.3f,%s\n", r.mode.c_str(), r.kernel.c_str(),
                          r.threads, r.workingSet, r.best, r.median, r.unit);
            f << line;
        }
        std::printf("Zapisano %s\n", csv.c_str());
    }
    return 0;
}
