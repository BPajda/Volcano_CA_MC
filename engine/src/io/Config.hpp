#pragma once
// Konfiguracja symulacji: wczytanie z pliku JSON, nadpisania z linii poleceń (--set),
// walidacja z czytelnymi komunikatami po polsku i zamiana na typowaną strukturę Config.
//
// Kolejność scalania: wartości domyślne <- plik JSON <- kolejne --set.
// Nieznane klucze są błędem (łapie literówki typu "neighbourhood"); klucze zaczynające
// się od "_" są pomijane — można w nich trzymać komentarze, np. "_opis": "...".

#include <cstdint>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "core/Types.hpp"
#include "json.hpp"
#include "parallel/Omp.hpp"

namespace volcano {

// Błąd konfiguracji — komunikat po polsku, gotowy do wyświetlenia użytkownikowi.
class ConfigError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

enum class TerrainType { Cone, File };
// Rozmieszczenie kraterów: losowo w kraterze szczytowym, losowo na zboczu albo w zadanych kolumnach
// (vents.positions — prawdziwe wulkany, etap 6).
enum class VentPlacement { Crater, Random, Positions };
enum class OutputFormat { Txt, Bin, Both, None };

// Teren: stożek wulkanu z kraterem albo mapa wysokości z pliku CSV.
struct TerrainConfig {
    TerrainType type = TerrainType::Cone;
    double peakHeight = 70.0;    // wysokość szczytu [komórki]
    double baseRadius = 90.0;    // promień podstawy stożka [komórki]
    double craterRadius = 6.0;   // promień krateru [komórki]
    double craterDepth = 4.0;    // głębokość krateru poniżej krawędzi [komórki]
    double noise = 0.05;         // amplituda szumu jako ułamek peakHeight
    std::string file;            // ścieżka CSV dla type = file
};

// Kratery (tryb lava) / zarodki ziaren (tryb classic).
struct VentsConfig {
    int count = 1;
    VentPlacement placement = VentPlacement::Crater;
    // Lista kolumn dla placement = positions (vents.positions) NIE jest polem tej struktury — zwraca ją
    // Config::ventColumns(). Pole-wektor zmieniało kod kopiowania/niszczenia Config i dokładało instancje
    // szablonów, a linker MSVC przesuwał przez to gorącą pętlę automatu (CA wolniejszy o ~7% przy tym samym
    // kodzie automatu — docs/prawdziwe-wulkany.md, punkt 7).
    int eruptionSteps = 300;     // przez tyle kroków krater ma stałą temperaturę eruptTemp
    double eruptTemp = 1200.0;   // [°C]
};

// Parametry automatu komórkowego.
struct CaConfig {
    CaMode mode = CaMode::Lava;
    int maxSteps = 5000;
    double coolingAmbient = 0.3;  // stygnięcie płynnej lawy na krok [°C]
    double coolingLateral = 1.5;  // stygnięcie przy rozlewaniu na boki [°C]
    double coolingFall = 0.1;     // stygnięcie przy spadaniu [°C]
    double solidusTemp = 800.0;   // poniżej tej temperatury lawa zastyga w bazalt [°C]
    bool ponding = true;          // wypełnianie zagłębień (rozszerzenie reguł, patrz CaRules.hpp)
    // ca.sweep (etap 8): "front" — automat frontalny (tylko komórki, które mogą się zmienić), "full" — pełny
    // przebieg (wersja referencyjna). Wynik bitowo ten sam. Pole 1 B w miejscu wypełnienia — rozmiar struktury
    // bez zmian (układ kodu MSVC, etap 6, punkt 7).
    bool frontSweep = true;
};

// Krystalizacja Monte Carlo (etap 2) — opis algorytmu w mc/McRules.hpp.
struct McConfig {
    bool enabled = false;
    McDomain domain = McDomain::Basalt;  // basalt: na wyniku CA; full: cała przestrzeń, bez CA
    int Q = 50;                          // liczba orientacji (stanów początkowych)
    int mcs = 100;                       // liczba kroków Monte Carlo (MCS)
    double J = 1.0;                      // energia granicy ziarna
    double kT = 0.0;                     // temperatura Metropolisa (0 = tylko ΔE <= 0)
    bool mobilityFromCooling = true;     // mobilność z czasu stygnięcia (tylko basalt)
    // mc.update (etap 9): false = "random" — próby w losowych komórkach po kolei (wariant naiwny, sekwencyjny);
    // true = "checkerboard" — szachownica: kolory komórek niebędących sąsiadami, kolor po kolorze, równolegle.
    // Pole 1 B w miejscu wypełnienia po mobilityFromCooling — rozmiar struktury bez zmian.
    bool checkerboard = false;
    double mobilityMin = 0.05;           // mobilność najszybciej zastygłej lawy
    int statsEvery = 10;                 // co ile MCS liczyć statystyki (mc_stats.csv)
    int snapshotsEvery = 0;              // co ile MCS zapisać migawkę kryształów (0 = wyłączone)

    // Czy przebieg pomija teren i automat (MC na całej przestrzeni).
    bool fullOnly() const { return enabled && domain == McDomain::Full; }
};

struct OutputConfig {
    OutputFormat format = OutputFormat::Txt;
    int snapshotsEvery = 0;       // co ile kroków zapisać migawkę .bin (0 = wyłączone)
};

// Równoległość OpenMP (etap 9, sekcja parallel) — opis w parallel/Omp.hpp i docs/openmp.md.
struct ParallelConfig {
    int threads = 1;                       // 1 = jeden wątek (kod jak w etapie 8); 0 = omp_get_max_threads()
    Schedule schedule = Schedule::Static;  // harmonogram pętli po warstwach / pasach
    int chunk = 0;                         // rozmiar porcji harmonogramu; 0 = domyślny OpenMP
    Affinity affinity = Affinity::None;    // pcores — jeden wątek na rdzeń fizyczny P (parallel/Affinity.hpp)
};

// Pełna, zwalidowana konfiguracja.
struct Config {
    Dims space{200, 1, 100};
    GridKind grid = GridKind::Vector;
    BoundaryKind boundary = BoundaryKind::Absorbing;
    NeighborhoodKind neighborhood = NeighborhoodKind::Moore;
    std::uint64_t rngSeed = 42;
    TerrainConfig terrain;
    VentsConfig vents;
    CaConfig ca;
    McConfig mc;
    OutputConfig output;
    ParallelConfig parallel;

    std::string sourcePath;              // plik, z którego wczytano config (może być pusty)
    bool spaceFromUser = false;          // czy wymiary podano w pliku lub --set (a nie z domyślnych)
    std::vector<std::string> warnings;   // ostrzeżenia (nie przerywają symulacji)
    nlohmann::ordered_json effective;    // pełny JSON po scaleniu — zapisywany jako config_used.json

    // Domyślna konfiguracja w postaci JSON (wszystkie dozwolone klucze).
    static nlohmann::ordered_json defaultsJson();

    // Wczytuje plik (pusta ścieżka = same domyślne), stosuje nadpisania "a.b=wartość"
    // i waliduje. Rzuca ConfigError z opisem problemu.
    static Config load(const std::string& path, const std::vector<std::string>& overrides);

    // Waliduje scalony JSON i zamienia go na strukturę. Rzuca ConfigError.
    static Config fromJson(const nlohmann::ordered_json& j);

    // Kolumny kraterów (x, y) z vents.positions (sprawdzone przez fromJson: format, zakres, bez powtórzeń),
    // w kolejności listy = flowId 1, 2, … Pusta lista, gdy nie podano.
    std::vector<std::pair<int, int>> ventColumns() const;

    // Ustawienia równoległości do obliczeń (etap 9): threads = 0 -> omp_get_max_threads(), bez OpenMP zawsze 1.
    ParallelSettings parallelSettings() const;

    // Etap 10 (wartości z effective, sprawdzone przez fromJson — bez nowych pól struktury):
    // parallel.priority = "high" — proces z wysokim priorytetem (pomiary wielowątkowe i MPI; --high-priority);
    bool highPriority() const;
    // mpi.exchange = "changed" — engine_mpi przesyła warstwę brzegową tylko, gdy się zmieniła ("always" — co krok).
    bool mpiExchangeChanged() const;
    // Etap 11 (też z effective): mpi.pack = "datatype" — warstwy brzegowe opisane typem pochodnym MPI (bez pakowania
    // do bufora; "manual" — pakowanie memcpy jak w etapie 10); mpi.bcast = "struct" — parametry i kratery / zarodki
    // rozsyłane jako struktury (typ MPI_Type_create_struct; "json" — scalony JSON configu); mpi.io = "mpiio" — każdy
    // proces zapisuje swój pas do wspólnego pliku (MPI-IO; "gather" — zebranie na proces 0 i zapis tam).
    bool mpiPackDatatype() const;
    bool mpiBcastStruct() const;
    bool mpiIoParallel() const;

    // Nakłada nadpisanie "ścieżka.z.kropkami=wartość" na JSON. Wartość jest parsowana
    // jako JSON (liczby, true/false, null); jeśli się nie da — traktowana jako tekst.
    static void applyOverride(nlohmann::ordered_json& j, const std::string& keyValue);

    // Scala obiekt patch z base, zgłaszając nieznane klucze (prefix — ścieżka do komunikatów).
    static void merge(nlohmann::ordered_json& base, const nlohmann::ordered_json& patch,
                      const std::string& prefix);
};

// Nazwy wartości wyliczeniowych używane w configu i plikach wynikowych.
const char* nameOf(GridKind g);
const char* nameOf(CaMode m);
const char* nameOf(OutputFormat f);
const char* nameOf(McDomain d);
// mc.update: "random" albo "checkerboard".
inline const char* mcUpdateName(bool checkerboard) { return checkerboard ? "checkerboard" : "random"; }

}  // namespace volcano
