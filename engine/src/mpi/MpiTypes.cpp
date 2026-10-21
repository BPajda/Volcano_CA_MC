#include "mpi/MpiTypes.hpp"

#include <cstddef>
#include <cstring>
#include <type_traits>

namespace volcano {

namespace {

static_assert(std::is_standard_layout<ConfigBlock>::value && std::is_trivially_copyable<ConfigBlock>::value,
              "ConfigBlock musi być strukturą POD (offsetof, przesyłanie bajtów)");
static_assert(std::is_standard_layout<Vent>::value && std::is_trivially_copyable<Vent>::value,
              "Vent musi być strukturą POD (tablica struktur w MPI_Bcast)");
static_assert(sizeof(int) == sizeof(std::int32_t), "Vent::x, y, z jako MPI_INT32_T");

// Pole struktury w opisie typu MPI: przesunięcie, liczba elementów, typ elementu.
struct Field {
    std::size_t offset;
    int count;
    MPI_Datatype type;
};

// Typ struktury z listy pól; extent ustawiony na size (rozmiar struktury z wypełnieniem na końcu), żeby tablica
// elementów tego typu miała krok sizeof — inaczej extent kończyłby się na ostatnim polu.
MpiType structType(const std::vector<Field>& fields, std::size_t size) {
    std::vector<int> lens;
    std::vector<MPI_Aint> displs;
    std::vector<MPI_Datatype> types;
    for (const Field& f : fields) {
        lens.push_back(f.count);
        displs.push_back(static_cast<MPI_Aint>(f.offset));
        types.push_back(f.type);
    }
    MPI_Datatype raw = MPI_DATATYPE_NULL;
    MPI_Type_create_struct(static_cast<int>(fields.size()), lens.data(), displs.data(), types.data(), &raw);
    MPI_Datatype resized = MPI_DATATYPE_NULL;
    MPI_Type_create_resized(raw, 0, static_cast<MPI_Aint>(size), &resized);
    MPI_Type_free(&raw);
    MPI_Type_commit(&resized);
    return MpiType(resized);
}

}  // namespace

MpiType MpiTypes::configBlockType() {
    const std::vector<Field> fields = {
        {offsetof(ConfigBlock, space), 3, MPI_INT32_T},
        {offsetof(ConfigBlock, grid), 1, MPI_INT32_T},
        {offsetof(ConfigBlock, boundary), 1, MPI_INT32_T},
        {offsetof(ConfigBlock, neighborhood), 1, MPI_INT32_T},
        {offsetof(ConfigBlock, rngSeed), 1, MPI_UINT64_T},
        {offsetof(ConfigBlock, terrainType), 1, MPI_INT32_T},
        {offsetof(ConfigBlock, terrain), 5, MPI_DOUBLE},
        {offsetof(ConfigBlock, vents), 3, MPI_INT32_T},
        {offsetof(ConfigBlock, eruptTemp), 1, MPI_DOUBLE},
        {offsetof(ConfigBlock, caMode), 1, MPI_INT32_T},
        {offsetof(ConfigBlock, maxSteps), 1, MPI_INT32_T},
        {offsetof(ConfigBlock, ca), 4, MPI_DOUBLE},
        {offsetof(ConfigBlock, caFlags), 2, MPI_UINT8_T},
        {offsetof(ConfigBlock, mcFlags), 4, MPI_UINT8_T},
        {offsetof(ConfigBlock, mc), 4, MPI_INT32_T},
        {offsetof(ConfigBlock, mcNum), 3, MPI_DOUBLE},
        {offsetof(ConfigBlock, output), 2, MPI_INT32_T},
        {offsetof(ConfigBlock, parallel), 4, MPI_INT32_T},
        {offsetof(ConfigBlock, mpi), 5, MPI_UINT8_T},
        {offsetof(ConfigBlock, cooling), 1, MPI_INT32_T},
    };
    return structType(fields, sizeof(ConfigBlock));
}

MpiType MpiTypes::ventType() {
    const std::vector<Field> fields = {
        {offsetof(Vent, x), 1, MPI_INT32_T},
        {offsetof(Vent, y), 1, MPI_INT32_T},
        {offsetof(Vent, z), 1, MPI_INT32_T},
        {offsetof(Vent, flowId), 1, MPI_INT32_T},
    };
    return structType(fields, sizeof(Vent));
}

ConfigBlock MpiTypes::toBlock(const Config& c, int cooling) {
    ConfigBlock b;
    std::memset(&b, 0, sizeof(b));  // wypełnienie też zerami — bloki porównywalne bajtowo (testy)
    b.space[0] = c.space.nx;
    b.space[1] = c.space.ny;
    b.space[2] = c.space.nz;
    b.grid = static_cast<std::int32_t>(c.grid);
    b.boundary = static_cast<std::int32_t>(c.boundary);
    b.neighborhood = static_cast<std::int32_t>(c.neighborhood);
    b.rngSeed = c.rngSeed;
    b.terrainType = static_cast<std::int32_t>(c.terrain.type);
    b.terrain[0] = c.terrain.peakHeight;
    b.terrain[1] = c.terrain.baseRadius;
    b.terrain[2] = c.terrain.craterRadius;
    b.terrain[3] = c.terrain.craterDepth;
    b.terrain[4] = c.terrain.noise;
    b.vents[0] = c.vents.count;
    b.vents[1] = static_cast<std::int32_t>(c.vents.placement);
    b.vents[2] = c.vents.eruptionSteps;
    b.eruptTemp = c.vents.eruptTemp;
    b.caMode = static_cast<std::int32_t>(c.ca.mode);
    b.maxSteps = c.ca.maxSteps;
    b.ca[0] = c.ca.coolingAmbient;
    b.ca[1] = c.ca.coolingLateral;
    b.ca[2] = c.ca.coolingFall;
    b.ca[3] = c.ca.solidusTemp;
    b.caFlags[0] = c.ca.ponding ? 1 : 0;
    b.caFlags[1] = c.ca.frontSweep ? 1 : 0;
    b.mcFlags[0] = c.mc.enabled ? 1 : 0;
    b.mcFlags[1] = c.mc.domain == McDomain::Full ? 1 : 0;
    b.mcFlags[2] = c.mc.mobilityFromCooling ? 1 : 0;
    b.mcFlags[3] = c.mc.checkerboard ? 1 : 0;
    b.mc[0] = c.mc.Q;
    b.mc[1] = c.mc.mcs;
    b.mc[2] = c.mc.statsEvery;
    b.mc[3] = c.mc.snapshotsEvery;
    b.mcNum[0] = c.mc.J;
    b.mcNum[1] = c.mc.kT;
    b.mcNum[2] = c.mc.mobilityMin;
    b.output[0] = static_cast<std::int32_t>(c.output.format);
    b.output[1] = c.output.snapshotsEvery;
    b.parallel[0] = c.parallel.threads;
    b.parallel[1] = static_cast<std::int32_t>(c.parallel.schedule);
    b.parallel[2] = c.parallel.chunk;
    b.parallel[3] = static_cast<std::int32_t>(c.parallel.affinity);
    b.mpi[0] = c.highPriority() ? 1 : 0;
    b.mpi[1] = c.mpiExchangeChanged() ? 1 : 0;
    b.mpi[2] = c.mpiPackDatatype() ? 1 : 0;
    b.mpi[3] = c.mpiBcastStruct() ? 1 : 0;
    b.mpi[4] = c.mpiIoParallel() ? 1 : 0;
    b.cooling = cooling;
    return b;
}

Config MpiTypes::fromBlock(const ConfigBlock& b) {
    Config c;
    c.space = Dims{b.space[0], b.space[1], b.space[2]};
    c.grid = static_cast<GridKind>(b.grid);
    c.boundary = static_cast<BoundaryKind>(b.boundary);
    c.neighborhood = static_cast<NeighborhoodKind>(b.neighborhood);
    c.rngSeed = b.rngSeed;
    c.terrain.type = static_cast<TerrainType>(b.terrainType);
    c.terrain.peakHeight = b.terrain[0];
    c.terrain.baseRadius = b.terrain[1];
    c.terrain.craterRadius = b.terrain[2];
    c.terrain.craterDepth = b.terrain[3];
    c.terrain.noise = b.terrain[4];
    c.vents.count = b.vents[0];
    c.vents.placement = static_cast<VentPlacement>(b.vents[1]);
    c.vents.eruptionSteps = b.vents[2];
    c.vents.eruptTemp = b.eruptTemp;
    c.ca.mode = static_cast<CaMode>(b.caMode);
    c.ca.maxSteps = b.maxSteps;
    c.ca.coolingAmbient = b.ca[0];
    c.ca.coolingLateral = b.ca[1];
    c.ca.coolingFall = b.ca[2];
    c.ca.solidusTemp = b.ca[3];
    c.ca.ponding = b.caFlags[0] != 0;
    c.ca.frontSweep = b.caFlags[1] != 0;
    c.mc.enabled = b.mcFlags[0] != 0;
    c.mc.domain = b.mcFlags[1] != 0 ? McDomain::Full : McDomain::Basalt;
    c.mc.mobilityFromCooling = b.mcFlags[2] != 0;
    c.mc.checkerboard = b.mcFlags[3] != 0;
    c.mc.Q = b.mc[0];
    c.mc.mcs = b.mc[1];
    c.mc.statsEvery = b.mc[2];
    c.mc.snapshotsEvery = b.mc[3];
    c.mc.J = b.mcNum[0];
    c.mc.kT = b.mcNum[1];
    c.mc.mobilityMin = b.mcNum[2];
    c.output.format = static_cast<OutputFormat>(b.output[0]);
    c.output.snapshotsEvery = b.output[1];
    c.parallel.threads = b.parallel[0];
    c.parallel.schedule = static_cast<Schedule>(b.parallel[1]);
    c.parallel.chunk = b.parallel[2];
    c.parallel.affinity = static_cast<Affinity>(b.parallel[3]);
    // Metody Config czytają te warianty z effective (bez nowych pól struktury — etap 6, punkt 7).
    c.effective = {{"parallel", {{"priority", b.mpi[0] != 0 ? "high" : "normal"}}},
                   {"mpi",
                    {{"exchange", b.mpi[1] != 0 ? "changed" : "always"},
                     {"pack", b.mpi[2] != 0 ? "datatype" : "manual"},
                     {"bcast", b.mpi[3] != 0 ? "struct" : "json"},
                     {"io", b.mpi[4] != 0 ? "mpiio" : "gather"}}}};
    return c;
}

}  // namespace volcano
