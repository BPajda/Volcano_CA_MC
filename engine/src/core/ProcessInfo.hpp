#pragma once
// Informacje o procesie do profilu aplikacji (etap 3): bieżące i szczytowe zużycie pamięci.
// Jedyny kod zależny od systemu jest w ProcessInfo.cpp, w #ifdef:
//   Windows: GetProcessMemoryInfo — WorkingSetSize / PeakWorkingSetSize (pamięć fizyczna
//            procesu, bieżąca i szczytowa) oraz PeakPagefileUsage (szczytowa pamięć prywatna
//            zatwierdzona, „commit” — liczona także wtedy, gdy strony nie są w RAM),
//   Linux:   getrusage(RUSAGE_SELF).ru_maxrss — szczytowy RSS (w KiB), bieżący RSS
//            z /proc/self/statm; odpowiednika PeakPagefileUsage nie podajemy (0).
// Szczyt jest monotoniczny, więc odczyt na końcu programu daje szczyt całego przebiegu.

#include <cstdint>

namespace volcano {

// Zużycie pamięci procesu [B].
struct ProcessMemory {
    bool available = false;         // false — system nie dostarczył danych
    std::uint64_t currentRss = 0;   // bieżący zbiór roboczy (Windows) / RSS (Linux)
    std::uint64_t peakRss = 0;      // szczytowy zbiór roboczy / szczytowy RSS
    std::uint64_t peakPrivate = 0;  // Windows: szczytowa pamięć prywatna (PeakPagefileUsage); Linux: 0
    const char* method = "brak";    // źródło liczb (zapisywane w times.json)
};

// Odczyt informacji o bieżącym procesie. Klasa statyczna — bez stanu.
class ProcessInfo {
public:
    static ProcessMemory memory();
};

}  // namespace volcano
