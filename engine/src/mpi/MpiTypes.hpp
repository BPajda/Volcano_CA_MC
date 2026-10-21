#pragma once
// Typy pochodne MPI do rozsyłania danych wejściowych (etap 11, mpi.bcast = "struct").
//
// W etapie 10 proces 0 rozsyłał scalony config jako tekst JSON (MPI_Bcast długości i treści), a pozostałe procesy
// parsowały go i walidowały (Config::fromJson); kratery / zarodki każdy proces wyznaczał sam z tego samego ziarna.
// Wariant "struct":
//   * ConfigBlock — blok liczbowy configu (wszystko, czego obliczenia potrzebują na każdym procesie) jako struktura
//     POD z polami różnych typów (int32, uint64, double, uint8); typ MPI_Type_create_struct opisuje każde pole przez
//     offsetof i typ MPI o stałym rozmiarze, więc jeden MPI_Bcast przesyła cały blok bez tekstu i bez parsowania;
//   * Vent — globalna lista kraterów / zarodków (położenie i ID) wyznaczona przez proces 0 i rozesłana jako tablica
//     struktur (typ MPI_Type_create_struct + MPI_Type_create_resized: rozmiar elementu = sizeof(Vent)).
// Granica: poza blokiem zostają pola tekstowe i zmiennej długości — terrain.file (mapę czyta tylko proces 0 i rozsyła
// tablicę wysokości, jak w etapie 10), vents.positions (lista kolumn — zbędna, bo kratery przychodzą gotowe), ścieżki
// (sourcePath, --mc-from: ścieżkę pliku do odczytu MPI-IO rozsyła osobny MPI_Bcast tekstu) i effective (pełny JSON
// configu — config_used.json zapisuje proces 0).
//
// MpiType — właściciel jednego typu MPI (MPI_Type_free w destruktorze, przed MPI_Finalize).

#include <mpi.h>

#include <cstdint>
#include <utility>
#include <vector>

#include "io/Config.hpp"
#include "terrain/VentPlacer.hpp"

namespace volcano {

// Typ MPI z automatycznym zwolnieniem (tylko przenoszenie).
class MpiType {
public:
    MpiType() = default;
    explicit MpiType(MPI_Datatype t) : t_(t) {}
    MpiType(MpiType&& o) noexcept : t_(std::exchange(o.t_, MPI_DATATYPE_NULL)) {}
    MpiType& operator=(MpiType&& o) noexcept {
        if (this != &o) {
            reset();
            t_ = std::exchange(o.t_, MPI_DATATYPE_NULL);
        }
        return *this;
    }
    MpiType(const MpiType&) = delete;
    MpiType& operator=(const MpiType&) = delete;
    ~MpiType() { reset(); }

    MPI_Datatype get() const { return t_; }
    void reset() {
        if (t_ != MPI_DATATYPE_NULL) {
            MPI_Type_free(&t_);
        }
    }

private:
    MPI_Datatype t_ = MPI_DATATYPE_NULL;
};

// Blok liczbowy configu (kolejność i znaczenie pól jak w Config; wartości wyliczeniowe jako int32).
struct ConfigBlock {
    std::int32_t space[3];     // nx, ny, nz
    std::int32_t grid;         // GridKind
    std::int32_t boundary;     // BoundaryKind
    std::int32_t neighborhood; // NeighborhoodKind
    std::uint64_t rngSeed;
    std::int32_t terrainType;  // TerrainType
    double terrain[5];         // peakHeight, baseRadius, craterRadius, craterDepth, noise
    std::int32_t vents[3];     // count, placement (VentPlacement), eruptionSteps
    double eruptTemp;
    std::int32_t caMode;       // CaMode
    std::int32_t maxSteps;
    double ca[4];              // coolingAmbient, coolingLateral, coolingFall, solidusTemp
    std::uint8_t caFlags[2];   // ponding, frontSweep
    std::uint8_t mcFlags[4];   // enabled, domain = full, mobilityFromCooling, checkerboard
    std::int32_t mc[4];        // Q, mcs, statsEvery, snapshotsEvery
    double mcNum[3];           // J, kT, mobilityMin
    std::int32_t output[2];    // format (OutputFormat), snapshotsEvery
    std::int32_t parallel[4];  // threads, schedule (Schedule), chunk, affinity (Affinity)
    std::uint8_t mpi[5];       // priority high, exchange changed, pack datatype, bcast struct, io mpiio
    std::int32_t cooling;      // --mc-from: CoolingData wyniku CA z pliku (proces 0 czyta plik)
};

class MpiTypes {
public:
    // Typ MPI bloku configu (MPI_Type_create_struct z przesunięciami offsetof; extent = sizeof(ConfigBlock)).
    static MpiType configBlockType();
    // Typ MPI krateru / zarodka (x, y, z, flowId; extent = sizeof(Vent) — tablica elementów).
    static MpiType ventType();

    // Config -> blok (wypełnienie wyzerowane, więc bloki można porównać memcmp). cooling — CoolingData (--mc-from).
    static ConfigBlock toBlock(const Config& c, int cooling);
    // Blok -> Config na procesie innym niż 0: te same pola liczbowe co Config::fromJson; effective zawiera tylko klucze
    // czytane przez metody Config (parallel.priority, mpi.*) — pełny JSON configu ma proces 0.
    static Config fromBlock(const ConfigBlock& b);
};

}  // namespace volcano
