#include "core/ProcessInfo.hpp"

#ifdef _WIN32
#  ifndef WIN32_LEAN_AND_MEAN
#    define WIN32_LEAN_AND_MEAN
#  endif
#  ifndef NOMINMAX
#    define NOMINMAX
#  endif
#  include <windows.h>
// psapi.h po windows.h; od Windows 7 funkcja jest w kernel32 (K32GetProcessMemoryInfo).
#  include <psapi.h>
#else
#  include <sys/resource.h>
#  include <unistd.h>

#  include <fstream>
#endif

namespace volcano {

ProcessMemory ProcessInfo::memory() {
    ProcessMemory m;
#ifdef _WIN32
    PROCESS_MEMORY_COUNTERS pmc{};
    pmc.cb = sizeof(pmc);
    if (GetProcessMemoryInfo(GetCurrentProcess(), &pmc, sizeof(pmc))) {
        m.available = true;
        m.currentRss = static_cast<std::uint64_t>(pmc.WorkingSetSize);
        m.peakRss = static_cast<std::uint64_t>(pmc.PeakWorkingSetSize);
        m.peakPrivate = static_cast<std::uint64_t>(pmc.PeakPagefileUsage);
        m.method = "GetProcessMemoryInfo (PeakWorkingSetSize, PeakPagefileUsage)";
    }
#else
    rusage ru{};
    if (getrusage(RUSAGE_SELF, &ru) == 0) {
        m.available = true;
        m.peakRss = static_cast<std::uint64_t>(ru.ru_maxrss) * 1024ULL;  // Linux: ru_maxrss w KiB
        m.method = "getrusage (ru_maxrss), /proc/self/statm";
    }
    // /proc/self/statm: rozmiar całkowity i rezydentny w stronach.
    std::ifstream statm("/proc/self/statm");
    unsigned long long totalPages = 0;
    unsigned long long residentPages = 0;
    if (statm >> totalPages >> residentPages) {
        const long page = sysconf(_SC_PAGESIZE);
        m.currentRss = residentPages * static_cast<unsigned long long>(page > 0 ? page : 4096);
    }
#endif
    return m;
}

}  // namespace volcano
