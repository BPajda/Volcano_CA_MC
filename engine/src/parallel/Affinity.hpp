#pragma once
// Przypinanie wątków OpenMP do rdzeni wydajnych (etap 9, parallel.affinity = "pcores").
//
// Procesor pomiarowy (i9-13900HX) jest hybrydowy: 8 rdzeni P (z SMT — procesory logiczne {0,1}, {2,3}, …, {14,15})
// i 16 rdzeni E (16–31). Rdzenie P i E mają różną wydajność, więc wątki rozrzucone przez system na oba rodzaje dawałyby
// zaburzone przyspieszenie i efektywność. Przy "pcores" program:
//   * Windows — z GetLogicalProcessorInformationEx wybiera rdzenie najwyższej klasy wydajności (EfficiencyClass)
//     i z każdego pierwszy procesor logiczny (jeden wątek na rdzeń fizyczny, bez drugiego wątku SMT), ustawia maskę
//     procesu na te procesory i przypina wątek i do i-tego z listy. Kolejność zaczyna się od DRUGIEGO rdzenia P
//     (procesor logiczny 2, jak w pomiarach jednowątkowych z etapów 3 i 8), a procesor 0, który obsługuje część
//     przerwań systemu, dostaje wątek dopiero, gdy potrzebny jest ósmy rdzeń;
//   * Linux — rdzenie P z /sys/devices/cpu_core/cpus (procesor hybrydowy Intel), a bez tego pliku wszystkie procesory
//     systemu (/sys/devices/system/cpu/online — nie maska procesu, bo przy OMP_PROC_BIND libgomp przypina wątek główny
//     do jednego procesora przed main()); najpierw pierwszy procesor logiczny każdego rdzenia fizycznego
//     (topology/thread_siblings_list), potem pozostałe wątki SMT; wątek i -> i-ty procesor listy. W WSL 2 to procesory
//     wirtualne (zgłaszane jako 4 rdzenie × 2 wątki SMT) — maszyna wirtualna nie mówi, na których rdzeniach fizycznych
//     pracują (ograniczenie opisane w docs/etap-9-openmp.md).
// Wątki puli OpenMP są trwałe (te same wątki w kolejnych regionach — sprawdzone w bench/micro/omp_overhead.cpp), więc
// przypięcie robi się raz, przed obliczeniami; --thread-stats zapisuje, na których procesorach wątki faktycznie
// pracowały.

#include <string>
#include <vector>

namespace volcano {

// Plan przypięcia: procesory logiczne w kolejności przydziału wątkom i opis źródła informacji o rdzeniach.
struct CpuPlan {
    std::vector<int> cpus;   // wątek i -> cpus[i mod cpus.size()]
    std::string method;      // skąd wiadomo, które rdzenie są wydajne
};

class CpuAffinity {
public:
    // Rdzenie wydajne (P), po jednym procesorze logicznym na rdzeń fizyczny.
    static CpuPlan performanceCores();

    // Ustawia maskę procesu na procesory planu i przypina wątki regionu num_threads(threads): wątek i -> cpus[i mod n].
    // Zwraca procesory przypisane kolejnym wątkom (pusta lista, gdy system odmówił).
    static std::vector<int> pinThreads(const CpuPlan& plan, int threads);

    // To samo od pozycji first planu i z maską procesu tylko na użyte procesory: wątek i -> cpus[(first + i) mod n]
    // (etap 10: proces MPI nr r z T wątkami dostaje rdzenie P nr r·T … r·T + T − 1, więc procesy nie dzielą rdzeni).
    static std::vector<int> pinThreadsFrom(const CpuPlan& plan, int threads, int first);

    // Wysoki priorytet procesu (parallel.priority = "high", etap 10): Windows — HIGH_PRIORITY_CLASS (jak bench/ab.py
    // i scaling.py z etapów 8–9), Linux — nice −5 (zwykle wymaga uprawnień; bez nich false i proces zostaje przy
    // priorytecie normalnym). method — opis do times.json.
    static bool raisePriority(std::string& method);

    // Procesor logiczny, na którym pracuje wywołujący wątek (-1, gdy nieznany).
    static int currentCpu();
};

}  // namespace volcano
