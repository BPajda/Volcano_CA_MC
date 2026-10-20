#pragma once
// Raport czasów działania aplikacji (wymaganie: „pomiar czasu działania aplikacji,
// zapis do pliku z czasem symulacji”). Nazwane sekcje w milisekundach
// (readConfig, allocate, terrain, vents, caSim, save, total) + informacje o przebiegu
// (kroki, liczba komórek, siatka, sąsiedztwo, brzeg, tryb, procesor) -> times.json.
//
// Profil aplikacji (etap 3) dokłada do times.json:
//   "memory" — szczytowa pamięć procesu (ProcessInfo) obok modelu teoretycznego (MemoryModel:
//              tablice × sizeof, bajty na komórkę),
//   "files"  — rozmiar i czas zapisu każdego pliku wynikowego,
//   "detail" — czasy faz wewnątrz CA i MC, tylko z --timing-detail (domyślnie wyłączone,
//              żeby dodatkowe odczyty zegara nie zaburzały zwykłych pomiarów).

#include <cstddef>
#include <string>
#include <utility>
#include <vector>

#include "core/MemoryModel.hpp"
#include "core/ProcessInfo.hpp"
#include "json.hpp"

namespace volcano {

class TimingReport {
public:
    // Dodaje czas do sekcji (kolejne wywołania dla tej samej sekcji sumują się).
    void add(const std::string& section, double ms);

    // Czas sekcji [ms] (0, jeśli sekcji nie ma).
    double get(const std::string& section) const;

    // Dodatkowa informacja o przebiegu (np. "steps", "grid").
    void setInfo(const std::string& key, nlohmann::ordered_json value);

    // Sekcje w kolejności dodania.
    const std::vector<std::pair<std::string, double>>& sections() const { return sections_; }

    // --- profil (etap 3) ---

    // Model teoretycznego zapotrzebowania na pamięć — etapy rejestrują w nim duże tablice.
    MemoryModel& memory() { return memory_; }
    const MemoryModel& memory() const { return memory_; }

    // Sekcja "memory": pomiar procesu na starcie (atStart) i teraz (szczyt) + model
    // teoretyczny z bajtami na komórkę (cells = liczba komórek przestrzeni).
    void recordMemory(const ProcessMemory& atStart, std::size_t cells);

    // Plik wynikowy zapisany w czasie ms; rozmiar odczytuje recordFileSizes().
    // Ścieżka może wskazywać folder (migawki) — wtedy liczy się suma plików w nim.
    void addFile(const std::string& path, double ms);
    // Uzupełnia sekcję "files" o rozmiary zarejestrowanych plików (po zapisie wszystkich).
    void recordFileSizes();

    // Szczegółowe czasy faz (--timing-detail). addDetail sumuje jak add(); bez włączenia
    // sekcja "detail" nie trafia do times.json.
    void enableDetail(bool on) { detail_ = on; }
    bool detailEnabled() const { return detail_; }
    void addDetail(const std::string& name, double ms);

    // Czas pracy wątków (--thread-stats, etap 9): etapy (ca, mc) dopisują swoją sekcję do "threadStats".
    void enableThreadStats(bool on) { threadStats_ = on; }
    bool threadStatsEnabled() const { return threadStats_; }
    void addThreadStats(const std::string& stage, nlohmann::ordered_json stats);

    // times.json: {"unit": "ms", <sekcje>..., <informacje>...}
    nlohmann::ordered_json toJson() const;

    // Nazwa procesora (rejestr Windows / /proc/cpuinfo); "nieznany", gdy niedostępna.
    static std::string cpuName();

    // Kompilator i jego wersja, np. "MSVC 19.38" albo "GCC 13.2.0".
    static std::string compilerName();

    // "Release" albo "Debug" (wg makra NDEBUG) — pomiary mają sens tylko w Release.
    static std::string buildType();

private:
    // Zarejestrowany plik wynikowy.
    struct FileRecord {
        std::string path;
        double ms = 0.0;
    };

    std::vector<std::pair<std::string, double>> sections_;
    nlohmann::ordered_json info_ = nlohmann::ordered_json::object();
    MemoryModel memory_;
    std::vector<FileRecord> files_;
    bool detail_ = false;
    std::vector<std::pair<std::string, double>> details_;
    bool threadStats_ = false;
};

}  // namespace volcano
