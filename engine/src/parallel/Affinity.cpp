#include "parallel/Affinity.hpp"

#include <algorithm>
#include <fstream>
#include <set>
#include <sstream>

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
#  include <sched.h>
#  include <unistd.h>
#endif

namespace volcano {

namespace {

#ifndef _WIN32
// Lista procesorów w formacie jądra Linux („0-3,8,10-11”).
std::vector<int> parseCpuList(const std::string& text) {
    std::vector<int> out;
    std::stringstream ss(text);
    std::string part;
    while (std::getline(ss, part, ',')) {
        const std::size_t dash = part.find('-');
        try {
            if (dash == std::string::npos) {
                out.push_back(std::stoi(part));
            } else {
                const int a = std::stoi(part.substr(0, dash));
                const int b = std::stoi(part.substr(dash + 1));
                for (int c = a; c <= b; ++c) {
                    out.push_back(c);
                }
            }
        } catch (const std::exception&) {
            // pusty albo uszkodzony fragment — pomijamy
        }
    }
    return out;
}

// Pierwsza linia pliku (pusta, gdy pliku nie ma).
std::string firstLine(const std::string& path) {
    std::ifstream in(path);
    std::string line;
    std::getline(in, line);
    return line;
}
#endif

}  // namespace

CpuPlan CpuAffinity::performanceCores() {
    CpuPlan plan;
#ifdef _WIN32
    DWORD size = 0;
    GetLogicalProcessorInformationEx(RelationProcessorCore, nullptr, &size);
    std::vector<char> buf(size);
    auto* info = reinterpret_cast<SYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX*>(buf.data());
    if (size == 0 || !GetLogicalProcessorInformationEx(RelationProcessorCore, info, &size)) {
        plan.method = "GetLogicalProcessorInformationEx niedostępne";
        return plan;
    }
    // Rdzenie: najniższy procesor logiczny (grupa 0) i klasa wydajności.
    struct Core {
        int cpu;
        int efficiency;
    };
    std::vector<Core> cores;
    for (DWORD off = 0; off < size;) {
        const auto* e = reinterpret_cast<const SYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX*>(buf.data() + off);
        if (e->Relationship == RelationProcessorCore && e->Processor.GroupCount >= 1 &&
            e->Processor.GroupMask[0].Group == 0) {
            const KAFFINITY mask = e->Processor.GroupMask[0].Mask;
            for (int c = 0; c < 64; ++c) {
                if ((mask >> c) & 1) {
                    cores.push_back(Core{c, e->Processor.EfficiencyClass});
                    break;
                }
            }
        }
        off += e->Size;
    }
    int best = 0;
    for (const Core& c : cores) {
        best = std::max(best, c.efficiency);
    }
    for (const Core& c : cores) {
        if (c.efficiency == best) {
            plan.cpus.push_back(c.cpu);
        }
    }
    std::sort(plan.cpus.begin(), plan.cpus.end());
    // Start od drugiego rdzenia P (procesor 2 — jak pomiary jednowątkowe), procesor 0 na końcu.
    if (plan.cpus.size() > 1) {
        std::rotate(plan.cpus.begin(), plan.cpus.begin() + 1, plan.cpus.end());
    }
    plan.method = "GetLogicalProcessorInformationEx: " + std::to_string(plan.cpus.size()) + " z " +
                  std::to_string(cores.size()) + " rdzeni w klasie wydajności " + std::to_string(best);
#else
    std::vector<int> candidates = parseCpuList(firstLine("/sys/devices/cpu_core/cpus"));
    if (!candidates.empty()) {
        plan.method = "/sys/devices/cpu_core/cpus (rdzenie P procesora hybrydowego)";
    } else {
        // Wszystkie procesory systemu — nie maska procesu: przy OMP_PROC_BIND libgomp przypina wątek główny do
        // pierwszego miejsca jeszcze przed main(), więc sched_getaffinity widziałby jeden procesor.
        candidates = parseCpuList(firstLine("/sys/devices/system/cpu/online"));
        if (candidates.empty()) {
            const long n = sysconf(_SC_NPROCESSORS_ONLN);
            for (int c = 0; c < n; ++c) {
                candidates.push_back(c);
            }
        }
        plan.method = "brak informacji o rdzeniach P — wszystkie procesory systemu (" +
                      std::to_string(candidates.size()) + ")";
    }
    // Najpierw pierwszy procesor logiczny każdego rdzenia fizycznego (rdzeń rozpoznany po najmniejszym numerze z listy
    // rodzeństwa SMT), potem pozostałe wątki SMT: przy liczbie wątków <= liczba rdzeni — jeden wątek na rdzeń, a gdy
    // wątków jest więcej, kolejne trafiają na drugie wątki SMT. W WSL 2 topologia SMT jest wirtualna (8 procesorów
    // wirtualnych zgłoszonych jako 4 rdzenie × 2) — 8 wątków dostaje wtedy wszystkie 8 procesorów wirtualnych.
    std::sort(candidates.begin(), candidates.end());
    std::set<int> taken;
    std::vector<int> siblings;
    for (const int c : candidates) {
        const std::string topo = "/sys/devices/system/cpu/cpu" + std::to_string(c) + "/topology/thread_siblings_list";
        const std::vector<int> sib = parseCpuList(firstLine(topo));
        const int core = sib.empty() ? c : *std::min_element(sib.begin(), sib.end());
        (taken.insert(core).second ? plan.cpus : siblings).push_back(c);
    }
    plan.cpus.insert(plan.cpus.end(), siblings.begin(), siblings.end());
#endif
    return plan;
}

std::vector<int> CpuAffinity::pinThreads(const CpuPlan& plan, int threads) {
    std::vector<int> used;
    if (plan.cpus.empty() || threads < 1) {
        return used;
    }
    const std::size_t n = plan.cpus.size();
    used.assign(static_cast<std::size_t>(threads), -1);
#ifdef _WIN32
    DWORD_PTR processMask = 0;
    for (const int c : plan.cpus) {
        processMask |= DWORD_PTR(1) << c;
    }
    if (!SetProcessAffinityMask(GetCurrentProcess(), processMask)) {
        return {};
    }
#endif
    // Każdy wątek regionu przypina się sam (wątki puli OpenMP są trwałe — kolejne regiony używają tych samych wątków).
#ifdef _OPENMP
#  pragma omp parallel num_threads(threads)
#endif
    {
        const int tid = omp_get_thread_num();
        const int cpu = plan.cpus[static_cast<std::size_t>(tid) % n];
#ifdef _WIN32
        const bool ok = SetThreadAffinityMask(GetCurrentThread(), DWORD_PTR(1) << cpu) != 0;
#else
        cpu_set_t set;
        CPU_ZERO(&set);
        CPU_SET(cpu, &set);
        const bool ok = sched_setaffinity(0, sizeof(set), &set) == 0;  // pid 0 = wywołujący wątek
#endif
        used[static_cast<std::size_t>(tid)] = ok ? cpu : -1;
    }
    return used;
}

int CpuAffinity::currentCpu() {
#ifdef _WIN32
    return static_cast<int>(GetCurrentProcessorNumber());
#else
    return sched_getcpu();
#endif
}

}  // namespace volcano
