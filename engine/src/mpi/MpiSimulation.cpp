#include "mpi/MpiSimulation.hpp"

#include <algorithm>
#include <climits>
#include <cmath>
#include <cstdio>
#include <filesystem>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <utility>

#include "app/Simulation.hpp"
#include "ca/LavaCA.hpp"
#include "core/Boundary.hpp"
#include "core/Neighborhood.hpp"
#include "core/ProcessInfo.hpp"
#include "core/Storage.hpp"
#include "io/ResultReader.hpp"
#include "io/ResultWriter.hpp"
#include "mc/CoolingMobility.hpp"
#include "mc/Grains.hpp"
#include "mc/PottsMC.hpp"
#include "parallel/Affinity.hpp"
#include "parallel/Omp.hpp"
#include "parallel/ThreadStats.hpp"

namespace volcano {

namespace fs = std::filesystem;
using ojson = nlohmann::ordered_json;

namespace {

constexpr int kTagCa = 101;  // komunikaty warstw brzegowych automatu
constexpr int kTagMc = 102;  // … i MC

// Liczba z podaną liczbą miejsc po przecinku (podsumowanie w konsoli).
std::string fixed(double v, int decimals) {
    char buf[64];
    std::snprintf(buf, sizeof(buf), "%.*f", decimals, v);
    return buf;
}

double round3(double v) { return std::round(v * 1000.0) / 1000.0; }

// --- rozsyłanie danych wejściowych (proces 0 -> wszyscy) ---

// Tekst: długość, potem treść (MPI_Bcast).
void bcastText(MpiContext& ctx, std::string& text) {
    const double t0 = MPI_Wtime();
    unsigned long long n = text.size();
    MPI_Bcast(&n, 1, MPI_UNSIGNED_LONG_LONG, 0, ctx.comm);
    if (n > static_cast<unsigned long long>(INT_MAX)) {
        throw std::runtime_error("config za duży do rozesłania");
    }
    if (!ctx.root()) {
        text.assign(static_cast<std::size_t>(n), '\0');
    }
    if (n > 0) {
        MPI_Bcast(&text[0], static_cast<int>(n), MPI_CHAR, 0, ctx.comm);
    }
    ctx.bcastConfigMs += (MPI_Wtime() - t0) * 1000.0;
    ctx.bcastConfigBytes += sizeof(n) + n;
}

// Mapa wysokości: wymiary, potem tablica wysokości.
void bcastHeightmap(MpiContext& ctx, Heightmap& hm) {
    const double t0 = MPI_Wtime();
    int dims[2] = {hm.nx, hm.ny};
    MPI_Bcast(dims, 2, MPI_INT, 0, ctx.comm);
    const std::size_t n = static_cast<std::size_t>(dims[0]) * static_cast<std::size_t>(dims[1]);
    if (!ctx.root()) {
        hm.nx = dims[0];
        hm.ny = dims[1];
        hm.height.assign(n, 0);
    }
    if (n > 0 && !hm.height.empty()) {
        MPI_Bcast(hm.height.data(), static_cast<int>(n), MPI_INT, 0, ctx.comm);
    }
    ctx.bcastTerrainMs += (MPI_Wtime() - t0) * 1000.0;
    ctx.bcastTerrainBytes += sizeof(dims) + (hm.height.empty() ? 0 : n * sizeof(int));
}

// --- zbieranie i rozdział pasów (ciągłe fragmenty tablic globalnych) ---

// Liczniki / przesunięcia [B] dla MPI_Gatherv / MPI_Scatterv pasów warstw split[r] .. split[r + 1].
void counts(const std::vector<int>& split, std::uint64_t plane, std::size_t elem, std::vector<int>& cnt,
            std::vector<int>& displ) {
    const std::size_t p = split.size() - 1;
    cnt.assign(p, 0);
    displ.assign(p, 0);
    for (std::size_t r = 0; r < p; ++r) {
        const std::uint64_t c = static_cast<std::uint64_t>(split[r + 1] - split[r]) * plane * elem;
        const std::uint64_t d = static_cast<std::uint64_t>(split[r]) * plane * elem;
        if (c > static_cast<std::uint64_t>(INT_MAX) || d > static_cast<std::uint64_t>(INT_MAX)) {
            throw std::runtime_error("tablica za duża dla MPI_Gatherv w jednym komunikacie (> 2 GB)");
        }
        cnt[r] = static_cast<int>(c);
        displ[r] = static_cast<int>(d);
    }
}

// Pas own (warstwy tego procesu) do tablicy all na procesie 0 (all może być pusta na pozostałych).
template <class T>
void gatherField(MpiContext& ctx, const std::vector<int>& split, std::uint64_t plane, const std::vector<T>& own,
                 std::vector<T>& all) {
    const double t0 = MPI_Wtime();
    std::vector<int> cnt;
    std::vector<int> displ;
    counts(split, plane, sizeof(T), cnt, displ);
    MPI_Gatherv(const_cast<T*>(own.data()), static_cast<int>(own.size() * sizeof(T)), MPI_BYTE,
                ctx.root() ? all.data() : nullptr, cnt.data(), displ.data(), MPI_BYTE, 0, ctx.comm);
    ctx.gatherMs += (MPI_Wtime() - t0) * 1000.0;
    ctx.gatherBytes += own.size() * sizeof(T);
}

// Tablica all z procesu 0 -> pas own każdego procesu.
template <class T>
void scatterField(MpiContext& ctx, const std::vector<int>& split, std::uint64_t plane, const std::vector<T>& all,
                  std::vector<T>& own) {
    const double t0 = MPI_Wtime();
    std::vector<int> cnt;
    std::vector<int> displ;
    counts(split, plane, sizeof(T), cnt, displ);
    MPI_Scatterv(ctx.root() ? const_cast<T*>(all.data()) : nullptr, cnt.data(), displ.data(), MPI_BYTE, own.data(),
                 static_cast<int>(own.size() * sizeof(T)), MPI_BYTE, 0, ctx.comm);
    ctx.scatterMs += (MPI_Wtime() - t0) * 1000.0;
    ctx.scatterBytes += own.size() * sizeof(T);
}

// Warstwy okna [k0, k1) jako mikrostruktura (bez ramki, kolejność globalIndex pasa).
Microstructure ownLayers(const VectorStorage& s, int k0, int k1) {
    const Dims d = s.dims();
    const bool lz = d.nz > 1;
    Microstructure m;
    m.resize(windowDims(d, k1 - k0));
    std::size_t i = 0;
    const int z0 = lz ? k0 : 0;
    const int z1 = lz ? k1 : 1;
    const int y0 = lz ? 0 : k0;
    const int y1 = lz ? d.ny : k1;
    for (int z = z0; z < z1; ++z) {
        for (int y = y0; y < y1; ++y) {
            for (int x = 0; x < d.nx; ++x, ++i) {
                m.type[i] = s.type(x, y, z);
                m.flowId[i] = s.flowId(x, y, z);
                m.temp[i] = s.temp(x, y, z);
                m.solidStep[i] = s.solidStep(x, y, z);
                m.arrivalStep[i] = s.arrivalStep(x, y, z);
            }
        }
    }
    return m;
}

// Wynik CA całej przestrzeni na procesie 0 z pasów wszystkich procesów.
void gatherMicro(MpiContext& ctx, const std::vector<int>& split, const Dims& global, const Microstructure& own,
                 Microstructure& all) {
    const std::uint64_t plane = layerPlane(global);
    if (ctx.root()) {
        all.resize(global);
    }
    gatherField(ctx, split, plane, own.type, all.type);
    gatherField(ctx, split, plane, own.flowId, all.flowId);
    gatherField(ctx, split, plane, own.temp, all.temp);
    gatherField(ctx, split, plane, own.solidStep, all.solidStep);
    gatherField(ctx, split, plane, own.arrivalStep, all.arrivalStep);
}

// Kratery / zarodki leżące w oknie pasa, we współrzędnych okna. Przy pierścieniu (brzeg periodyczny) ta sama warstwa
// globalna może wystąpić w oknie dwa razy (np. 2 procesy) — zarodek trafia wtedy do obu kopii.
std::vector<Vent> ventsInWindow(const std::vector<Vent>& vents, const StripPlan& plan, bool lz) {
    std::vector<Vent> out;
    const int L = plan.layers;
    for (const Vent& v : vents) {
        const int g = lz ? v.z : v.y;
        for (int k = g - plan.windowLo - L; k <= g - plan.windowLo + L; k += L) {
            if (k >= 0 && k < plan.windowLayers) {
                Vent w = v;
                (lz ? w.z : w.y) = k;
                out.push_back(w);
            }
        }
    }
    return out;
}

// Pas procesu dla automatu / MC.
Strip stripOf(const StripPlan& plan, const Dims& global, const Boundary& bc, StripLink* link) {
    Strip s;
    s.global = global;
    s.globalPeriodic[0] = bc.periodicX();
    s.globalPeriodic[1] = bc.periodicY();
    s.globalPeriodic[2] = bc.periodicZ();
    s.ownLo = plan.ownLo;
    s.ownHi = plan.ownHi;
    s.windowLo = plan.windowLo;
    // globalIndex komórki okna (0, 0, 0) = windowLo · (komórki warstwy); windowLo = -1 (pierścień) — modulo 2^64.
    s.hashBase = static_cast<std::uint64_t>(static_cast<std::int64_t>(plan.windowLo)) * layerPlane(global);
    s.link = link;
    return s;
}

// Równoległość w stats.json (jak w engine; klucz pomijany przy porównaniu wyników) + procesy MPI.
ojson parallelJson(const Config& c, int processes) {
    const ParallelSettings par = c.parallelSettings();
    ojson j;
    j["threads"] = par.threads;
    j["schedule"] = nameOf(par.schedule);
    j["chunk"] = par.chunk;
    j["affinity"] = nameOf(c.parallel.affinity);
    j["processes"] = processes;
    j["exchange"] = c.mpiExchangeChanged() ? "changed" : "always";
    return j;
}

// Statystyka po procesach: min / średnia / maks wartości v każdego procesu (na procesie 0; reszta — pusty obiekt).
ojson spread(MpiContext& ctx, double v, std::vector<double>* perRank = nullptr) {
    std::vector<double> all(ctx.root() ? static_cast<std::size_t>(ctx.size) : 0);
    MPI_Gather(&v, 1, MPI_DOUBLE, ctx.root() ? all.data() : nullptr, 1, MPI_DOUBLE, 0, ctx.comm);
    if (!ctx.root()) {
        return ojson::object();
    }
    double mn = all[0];
    double mx = all[0];
    double sum = 0.0;
    for (const double x : all) {
        mn = std::min(mn, x);
        mx = std::max(mx, x);
        sum += x;
    }
    if (perRank != nullptr) {
        *perRank = all;
    }
    return ojson{{"min", round3(mn)}, {"avg", round3(sum / ctx.size)}, {"max", round3(mx)}};
}

// Suma po procesach (na procesie 0).
std::uint64_t total(MpiContext& ctx, std::uint64_t v) {
    unsigned long long in = v;
    unsigned long long out = 0;
    MPI_Reduce(&in, &out, 1, MPI_UNSIGNED_LONG_LONG, MPI_SUM, 0, ctx.comm);
    return out;
}

// Opis komunikacji jednego etapu do sekcji "mpi" w times.json (wywołują wszystkie procesy).
ojson stageJson(MpiContext& ctx, const StripPlan& plan, const CommCounters& c, double simMs, std::uint64_t steps) {
    std::vector<double> simR;
    std::vector<double> commR;
    std::vector<double> computeR;
    ojson j;
    int below = 0;
    int above = 0;
    for (const GhostLayer& g : plan.ghosts) {
        (g.local < plan.ownLo ? below : above) += 1;
    }
    int ghostBelow = 0;
    int ghostAbove = 0;
    MPI_Reduce(&below, &ghostBelow, 1, MPI_INT, MPI_MAX, 0, ctx.comm);
    MPI_Reduce(&above, &ghostAbove, 1, MPI_INT, MPI_MAX, 0, ctx.comm);
    j["ghostLayersBelow"] = ghostBelow;
    j["ghostLayersAbove"] = ghostAbove;
    j["simMs"] = spread(ctx, simMs, &simR);
    j["commMs"] = spread(ctx, c.commMs(), &commR);
    j["haloMs"] = spread(ctx, c.haloMs);
    j["reduceMs"] = spread(ctx, c.reduceMs);
    j["computeMs"] = spread(ctx, simMs - c.commMs(), &computeR);
    const std::uint64_t messages = total(ctx, c.messages);
    const std::uint64_t bytes = total(ctx, c.bytes);
    const std::uint64_t sent = total(ctx, c.layersSent);
    const std::uint64_t skipped = total(ctx, c.layersSkipped);
    if (ctx.root()) {
        j["perRank"] = {{"simMs", simR}, {"commMs", commR}, {"computeMs", computeR}};
        for (const char* k : {"simMs", "commMs", "computeMs"}) {
            for (auto& v : j["perRank"][k]) {
                v = round3(v.get<double>());
            }
        }
        j["steps"] = steps;
        j["exchanges"] = c.exchanges;
        j["reductions"] = c.reductions;
        j["messages"] = messages;
        j["bytes"] = bytes;
        j["layersSent"] = sent;
        j["layersSkipped"] = skipped;
        j["bytesPerExchange"] = c.exchanges > 0 ? round3(double(bytes) / double(c.exchanges)) : 0.0;
        j["messagesPerExchange"] = c.exchanges > 0 ? round3(double(messages) / double(c.exchanges)) : 0.0;
    }
    return j;
}

// Wersja biblioteki MPI (napis biblioteki tylko w MPI >= 3).
std::string mpiLibrary() {
#if defined(MPI_VERSION) && MPI_VERSION >= 3
    char buf[MPI_MAX_LIBRARY_VERSION_STRING] = {};
    int len = 0;
    MPI_Get_library_version(buf, &len);
    std::string s(buf, static_cast<std::size_t>(len));
    const std::size_t nl = s.find_first_of("\r\n,");
    return nl == std::string::npos ? s : s.substr(0, nl);
#else
    return "MPI";
#endif
}

// Proces przed obliczeniami: priorytet, liczba wątków OpenMP, przypięcie wątków procesu do jego rdzeni P
// (proces r z T wątkami — pozycje r·T … r·T + T − 1 planu: 2, 4, …, 14, 0; procesy nie dzielą rdzeni).
struct ProcessSetup {
    bool highPriority = false;
    std::vector<int> cpus;
};
ProcessSetup setupProcess(MpiContext& ctx, const Config& c, TimingReport& timing, std::vector<std::string>& warnings) {
    ProcessSetup out;
    const ParallelSettings par = c.parallelSettings();
    timing.setInfo("threads", par.threads);
    timing.setInfo("schedule", nameOf(par.schedule));
    timing.setInfo("chunk", par.chunk);
    timing.setInfo("affinity", nameOf(c.parallel.affinity));
    timing.setInfo("openmp", openmpVersion());
    if (c.highPriority()) {
        std::string method;
        out.highPriority = CpuAffinity::raisePriority(method);
        if (!out.highPriority && ctx.root()) {
            warnings.push_back("nie udało się podnieść priorytetu procesów (" + method + ")");
        }
    }
    if (par.threads > 1) {
        omp_set_num_threads(par.threads);
    }
    if (c.parallel.affinity == Affinity::PCores) {
        const CpuPlan plan = CpuAffinity::performanceCores();
        out.cpus = CpuAffinity::pinThreadsFrom(plan, par.threads, ctx.rank * par.threads);
        timing.setInfo("affinityMethod", plan.method);
        if (ctx.root() && static_cast<std::size_t>(ctx.size) * static_cast<std::size_t>(par.threads) >
                              plan.cpus.size()) {
            warnings.push_back("procesy × wątki = " + std::to_string(ctx.size * par.threads) + " > liczba rdzeni P (" +
                               std::to_string(plan.cpus.size()) + ") — część rdzeni dostaje po kilka wątków");
        }
    }
    return out;
}

// --mc-from (proces 0): wynik CA z folderu, wymiary z pliku — jak Simulation::runMcFrom.
void prepareMcFrom(Config& cfg, const std::string& folder, Microstructure& ca, ResultSource& src, CoolingData& cooling,
                   std::vector<std::string>& warnings, TimingReport& timing) {
    if (cfg.mc.domain != McDomain::Basalt) {
        throw ConfigError("--mc-from krystalizuje wynik CA z pliku — wymaga mc.domain = \"basalt\" (podano \"" +
                          std::string(nameOf(cfg.mc.domain)) + "\")");
    }
    if (!cfg.mc.enabled) {
        warnings.push_back("mc.enabled = false — w trybie --mc-from Monte Carlo jest uruchamiane zawsze");
        cfg.mc.enabled = true;
    }
    Timer t;
    ca = ResultReader::readFolder(folder, &src);
    timing.add("readInput", t.elapsedMs());
    if (ca.dims != cfg.space && cfg.spaceFromUser) {
        warnings.push_back("wymiary z pliku " + std::to_string(ca.dims.nx) + " x " + std::to_string(ca.dims.ny) +
                           " x " + std::to_string(ca.dims.nz) + " różnią się od space z configu (" +
                           std::to_string(cfg.space.nx) + " x " + std::to_string(cfg.space.ny) + " x " +
                           std::to_string(cfg.space.nz) + ") — obowiązują wymiary z pliku");
    }
    cfg.space = ca.dims;
    if (cfg.neighborhood == NeighborhoodKind::Hexagonal && !cfg.space.is2D()) {
        throw ConfigError("Sąsiedztwo „hexagonal” jest zdefiniowane tylko w 2D, a wynik CA z pliku jest 3D");
    }
    cfg.effective["space"] = {{"nx", ca.dims.nx}, {"ny", ca.dims.ny}, {"nz", ca.dims.nz}};
    cfg.effective["mc"]["enabled"] = true;
    cfg.effective["_mcFrom"] = fs::absolute(fs::path(folder)).lexically_normal().string();
    cooling = src.hasArrivalStep ? CoolingData::Full : src.hasSolidStep ? CoolingData::SolidOnly : CoolingData::None;
}

}  // namespace

MpiContext MpiContext::world() {
    MpiContext c;
    c.comm = MPI_COMM_WORLD;
    MPI_Comm_rank(c.comm, &c.rank);
    MPI_Comm_size(c.comm, &c.size);
    return c;
}

void MpiSimulation::checkConfig(const Config& cfg, int processes) {
    if (cfg.grid == GridKind::Matrix) {
        throw ConfigError("engine_mpi liczy tylko na siatce \"vector\" (grid = \"matrix\" służy do porównania "
                          "reprezentacji siatki w programie engine)");
    }
    if (cfg.mc.enabled && !cfg.mc.checkerboard && processes > 1) {
        throw ConfigError("mc.update = \"random\" (wariant naiwny) jest sekwencyjny — każda próba widzi wynik "
                          "poprzednich, więc nie da się go rozdzielić między procesy; przy " +
                          std::to_string(processes) + " procesach wymagane mc.update = \"checkerboard\" "
                          "(szachownica, etap 9) albo 1 proces");
    }
    const int layers = layerCountOf(cfg.space);
    if (processes > layers) {
        throw ConfigError("za dużo procesów: " + std::to_string(processes) + " > liczba warstw przestrzeni (" +
                          std::to_string(layers) + (layerAxisZ(cfg.space) ? " w osi z" : " w osi y") +
                          ") — każdy proces potrzebuje co najmniej jednej warstwy");
    }
}

MpiCaRun MpiSimulation::runCa(MpiContext& ctx, const Config& cfg, TimingReport& timing, ProgressReporter* progress,
                              const std::string& outDir, const std::vector<Vent>* ventsOverride) {
    MpiCaRun r;
    const Dims G = cfg.space;
    const bool lz = layerAxisZ(G);
    const int axis = lz ? 2 : 1;
    const int L = layerCountOf(G);

    // 1. Pas i okno: warstwy brzegowe tyle, ile czytają reguły (lava: 17 pod pasem, 1 nad; classic: 1 + 1).
    Timer t;
    const Neighborhood nb(cfg.neighborhood, G);
    const Boundary bc(cfg.boundary, cfg.ca.mode);
    GhostSpec spec;
    if (cfg.ca.mode == CaMode::Lava) {
        const unsigned full = kFieldType | kFieldFlow | kFieldTemp;  // reguły czytają typ, flowId i temperaturę sąsiada
        spec.below.assign(static_cast<std::size_t>(LavaCA<VectorStorage>::reachBelow(CaMode::Lava)), kFieldType);
        spec.below[0] = full;  // tylko warstwa tuż pod pasem: wypełnianie zagłębień czyta też flowId i temperaturę
        spec.above.assign(static_cast<std::size_t>(LavaCA<VectorStorage>::reachAbove(CaMode::Lava)), full);
    } else {
        // classic: typ i flowId sąsiadów + arrivalStep (listy src automatu frontalnego w warstwach brzegowych)
        const unsigned f = kFieldType | kFieldFlow | kFieldArrival;
        spec.below.assign(static_cast<std::size_t>(LavaCA<VectorStorage>::reachBelow(CaMode::Classic)), f);
        spec.above.assign(static_cast<std::size_t>(LavaCA<VectorStorage>::reachAbove(CaMode::Classic)), f);
    }
    spec.periodic = bc.periodic(axis);
    r.plan = planStrip(L, ctx.size, ctx.rank, spec);
    const StripPlan& plan = r.plan;
    const std::vector<int> split = splitLayers(L, ctx.size);
    const Boundary bcw = ctx.size > 1 ? bc.withoutPeriodic(axis) : bc;
    LavaCA<VectorStorage> ca(windowDims(G, plan.windowLayers), Simulation::caParams(cfg), nb, bcw);
    MpiHalo halo(ctx.comm, plan, cfg.mpiExchangeChanged(), kTagCa);
    // 1 proces: okno = cała przestrzeń, bez wymiany i sum — kroki jak w engine.
    ca.setStrip(stripOf(plan, G, bc, ctx.size > 1 ? &halo : nullptr));
    ParallelSettings par = cfg.parallelSettings();
    std::unique_ptr<ThreadStats> threadStats;
    if (timing.threadStatsEnabled() && par.parallel()) {
        threadStats = std::make_unique<ThreadStats>(
            par.threads, LavaCA<VectorStorage>::threadPhases(cfg.ca.frontSweep, cfg.ca.mode));
        par.stats = threadStats.get();
    }
    ca.setParallel(par);
    timing.add("allocate", t.elapsedMs());
    MemoryModel& mem = timing.memory();
    mem.allocate("caGrid", ca.gridBytes());
    mem.allocate("caAux", ca.auxBytes());

    // 2. Teren: mapę wysokości buduje / czyta proces 0 i rozsyła; poziomy przelewu każdy proces liczy sam (to samo).
    t.reset();
    Heightmap hm;
    if (cfg.ca.mode == CaMode::Lava) {
        if (ctx.root()) {
            hm = Simulation::buildTerrain(cfg);
        }
        bcastHeightmap(ctx, hm);
        ca.applyTerrain(hm);
    }
    timing.add("terrain", t.elapsedMs());
    mem.allocate("caAux", ca.auxBytes() + hm.height.size() * sizeof(int));

    // 3. Kratery / zarodki: ta sama globalna lista na każdym procesie (to samo ziarno), w oknie — te, które w nim leżą.
    t.reset();
    r.vents = ventsOverride != nullptr ? *ventsOverride : Simulation::buildVents(cfg, hm);
    ca.placeSeeds(ventsInWindow(r.vents, plan, lz));
    timing.add("vents", t.elapsedMs());

    // 4. Kroki (wymiana warstw przed krokiem, sumy liczników po kroku — w LavaCA przez StripLink).
    ca.enablePhaseTiming(timing.detailEnabled());
    const int every = cfg.output.snapshotsEvery;
    const bool showProgress = progress != nullptr && progress->enabled();
    const auto report = [&](bool force) {
        if (showProgress) {
            const std::uint64_t active = ca.activeHistory().empty() ? 0 : ca.activeHistory().back();
            progress->report("ca", ca.steps(), cfg.ca.maxSteps, force, "active", active);
        }
    };
    const fs::path snapDir = fs::path(outDir) / "snapshots";
    double snapMs = 0.0;
    const auto writeSnapshot = [&]() {
        const double s0 = MPI_Wtime();
        const Microstructure own = ownLayers(ca.state(), plan.ownLo, plan.ownHi);
        Microstructure all;
        gatherMicro(ctx, split, G, own, all);
        if (ctx.root()) {
            char name[32];
            std::snprintf(name, sizeof(name), "step_%06d.bin", ca.steps());
            ResultWriter::writeBin((snapDir / name).string(), all);
        }
        snapMs += (MPI_Wtime() - s0) * 1000.0;
    };
    double simMs = 0.0;
    if (every <= 0) {
        const double s0 = MPI_Wtime();
        report(true);
        while (ca.step()) {
            report(false);
        }
        report(true);
        simMs = (MPI_Wtime() - s0) * 1000.0;
    } else {
        if (ctx.root()) {
            fs::create_directories(snapDir);
        }
        writeSnapshot();
        while (!ca.finished()) {
            const double s0 = MPI_Wtime();
            ca.step();
            simMs += (MPI_Wtime() - s0) * 1000.0;
            report(ca.finished());
            if (ca.steps() % every == 0 || ca.finished()) {
                writeSnapshot();
            }
        }
        timing.add("snapshots", snapMs);
        if (ctx.root()) {
            timing.addFile(snapDir.string(), snapMs);
        }
    }
    r.simMs = simMs;
    timing.add("caSim", simMs);
    if (ca.frontSweep()) {
        mem.allocate("caFront", ca.frontBytes());
    }
    if (threadStats) {
        timing.addThreadStats("ca", threadStats->toJson());
    }
    if (timing.detailEnabled()) {
        const CaPhaseTimes& ph = ca.phaseTimes();
        timing.addDetail("caFrame", ph.frame);
        if (cfg.ca.mode == CaMode::Lava) {
            timing.addDetail("caDescent", ph.descent);
        }
        timing.addDetail("caRules", ph.rules);
        timing.addDetail("caFinish", ph.finish);
    }

    // 5. Wynik: pas własny (wejście MC) i cała przestrzeń na procesie 0.
    r.steps = ca.steps();
    r.stop = ca.stopReason();
    r.activeHistory = ca.activeHistory();
    r.changedHistory = ca.changedHistory();
    r.comm = halo.simCounters();
    const double g0 = MPI_Wtime();
    r.slab = ownLayers(ca.state(), plan.ownLo, plan.ownHi);
    gatherMicro(ctx, split, G, r.slab, r.result);
    r.gatherMs = (MPI_Wtime() - g0) * 1000.0;
    if (ctx.root()) {
        mem.allocate("caResult", r.result.bytes());
    }
    mem.release("caGrid");
    mem.release("caAux");
    mem.release("caFront");
    return r;
}

McSummary MpiSimulation::runMc(MpiContext& ctx, const Config& cfg, const Microstructure* slab, CoolingData cooling,
                               TimingReport& timing, ProgressReporter* progress, const std::string& outDir,
                               MpiMcRun* info) {
    McSummary s;
    const bool full = (slab == nullptr);
    s.domain = full ? McDomain::Full : McDomain::Basalt;
    s.mcs = cfg.mc.mcs;
    s.Q = cfg.mc.Q;
    const Dims G = cfg.space;
    const bool lz = layerAxisZ(G);
    const int axis = lz ? 2 : 1;
    const int L = layerCountOf(G);

    // --- przygotowanie (mcInit): okno z 1 warstwą brzegową z każdej strony (promień sąsiedztwa) ---
    Timer t;
    const Neighborhood nb(cfg.neighborhood, G);
    const Boundary bc(cfg.boundary, full ? CaMode::Classic : CaMode::Lava);
    GhostSpec spec;
    spec.below.assign(1, kFieldSpin);
    spec.above.assign(1, kFieldSpin);
    spec.periodic = bc.periodic(axis);
    const StripPlan plan = planStrip(L, ctx.size, ctx.rank, spec);
    const std::vector<int> split = splitLayers(L, ctx.size);
    const Boundary bcw = ctx.size > 1 ? bc.withoutPeriodic(axis) : bc;
    const Dims W = windowDims(G, plan.windowLayers);
    McParams p;
    p.seed = cfg.rngSeed;
    p.Q = cfg.mc.Q;
    p.J = cfg.mc.J;
    p.kT = cfg.mc.kT;
    PottsMC mc(W, p, nb, bcw);
    mc.setCheckerboard(cfg.mc.checkerboard);
    ParallelSettings par = cfg.parallelSettings();
    mc.setParallel(par);
    MpiHalo halo(ctx.comm, plan, cfg.mpiExchangeChanged(), kTagMc);
    StripLink* const link = ctx.size > 1 ? &halo : nullptr;
    mc.setStrip(stripOf(plan, G, bc, link));
    MemoryModel& mem = timing.memory();
    mem.allocate("mcGrid", mc.bytes());
    const std::uint64_t plane = layerPlane(G);
    const std::size_t ownOff = static_cast<std::size_t>(plan.ownLo) * static_cast<std::size_t>(plane);
    const bool periodic[3] = {bc.periodicX() && G.nx > 1, bc.periodicY() && G.ny > 1, bc.periodicZ() && G.nz > 1};

    std::vector<float> cellMobility;  // mobilność całej przestrzeni (proces 0) — statystyki wg klas mobilności
    if (full) {
        mc.setDomainAll();
    } else {
        const std::vector<std::uint8_t> domOwn = CoolingMobility::basaltDomain(*slab);
        std::vector<std::uint8_t> domain(W.cells(), 0);
        std::copy(domOwn.begin(), domOwn.end(), domain.begin() + static_cast<std::ptrdiff_t>(ownOff));
        mc.setDomain(domain);
        if (cooling != CoolingData::None) {
            // Mobilność jak CoolingMobility::fromCooling, ale koniec CA i zakres czasów — po wszystkich procesach.
            unsigned end = CoolingMobility::endStep(*slab, domOwn);
            MPI_Allreduce(MPI_IN_PLACE, &end, 1, MPI_UNSIGNED, MPI_MAX, ctx.comm);
            const std::vector<std::uint32_t> time = CoolingMobility::liquidTime(*slab, domOwn, end);
            std::uint32_t tMin = 0;
            std::uint32_t tMax = 0;
            CoolingMobility::timeRange(time, domOwn, tMin, tMax);
            unsigned range[2] = {tMin, tMax};
            MPI_Allreduce(MPI_IN_PLACE, &range[0], 1, MPI_UNSIGNED, MPI_MIN, ctx.comm);
            MPI_Allreduce(MPI_IN_PLACE, &range[1], 1, MPI_UNSIGNED, MPI_MAX, ctx.comm);
            const std::vector<float> mobOwn =
                CoolingMobility::normalize(time, domOwn, range[0], range[1], cfg.mc.mobilityMin);
            if (ctx.root()) {
                cellMobility.assign(G.cells(), 0.0f);
            }
            gatherField(ctx, split, plane, mobOwn, cellMobility);
            if (cfg.mc.mobilityFromCooling) {
                std::vector<float> mobility(W.cells(), 0.0f);
                std::copy(mobOwn.begin(), mobOwn.end(), mobility.begin() + static_cast<std::ptrdiff_t>(ownOff));
                mc.setMobility(mobility);
                mem.allocate("mcGrid", mc.bytes());
                s.mobilityUsed = true;
            }
        }
        if (cooling == CoolingData::None && cfg.mc.mobilityFromCooling) {
            s.warnings.push_back("wynik CA bez solidStep/arrivalStep (plik txt) — mobilność ze stygnięcia "
                                 "wyłączona, MC jak dla mobilityFromCooling = false");
        }
        if (cooling == CoolingData::SolidOnly) {
            s.warnings.push_back("ca_result.bin w wersji 1 nie zawiera arrivalStep — czas w stanie płynnym "
                                 "liczony od kroku 0 (= solidStep)");
        }
    }
    mc.initialize();
    if (link != nullptr) {
        halo.exchange(mc);  // warstwy brzegowe = orientacje początkowe sąsiadów
    }
    mem.allocate("mcGrid", mc.bytes());
    unsigned long long cells = mc.domainCells();
    MPI_Allreduce(MPI_IN_PLACE, &cells, 1, MPI_UNSIGNED_LONG_LONG, MPI_SUM, ctx.comm);
    s.domainCells = static_cast<std::size_t>(cells);
    if (s.domainCells == 0) {
        s.warnings.push_back(full ? "domena MC jest pusta" : "domena MC jest pusta — wynik CA nie zawiera bazaltu");
    }
    std::unique_ptr<ThreadStats> threadStats;
    if (timing.threadStatsEnabled() && par.parallel() && mc.checkerboard()) {
        std::vector<std::string> phases;
        for (int c = 0; c < mc.colorCount(); ++c) {
            phases.push_back("c" + std::to_string(c));
        }
        threadStats = std::make_unique<ThreadStats>(par.threads, phases);
        par.stats = threadStats.get();
        mc.setParallel(par);
    }
    timing.add("mcInit", t.elapsedMs());

    // Mapa kryształów całej przestrzeni na procesie 0 (pas własny z okna).
    double statsGatherMs = 0.0;
    const auto gatherCrystals = [&]() {
        const double g0 = MPI_Wtime();
        const CrystalMap win = mc.crystals();
        std::vector<std::int32_t> own(win.crystal.begin() + static_cast<std::ptrdiff_t>(ownOff),
                                      win.crystal.begin() + static_cast<std::ptrdiff_t>(plan.ownHi) *
                                                                static_cast<std::ptrdiff_t>(plane));
        CrystalMap all;
        all.dims = G;
        if (ctx.root()) {
            all.crystal.assign(G.cells(), 0);
        }
        gatherField(ctx, split, plane, own, all.crystal);
        statsGatherMs += (MPI_Wtime() - g0) * 1000.0;
        return all;
    };
    // Statystyki: liczba ziaren (union-find na procesie 0 — część szeregowa), energia (suma po procesach).
    double labelMs = 0.0;
    const std::uint64_t measureTempBytes = G.cells() * sizeof(std::int32_t) + GrainLabels::bytesFor(G.cells());
    const auto measure = [&](GrainLabels* keep, const char* keepName) {
        halo.setStatsPhase(true);
        McStats st;
        st.mcs = mc.sweepsDone();
        const CrystalMap map = gatherCrystals();
        if (ctx.root()) {
            mem.allocate("mcStatsTemp", measureTempBytes);
            Timer tl;
            GrainLabels g = Grains::label(map, mc.mooreConnectivity(), periodic);
            labelMs += tl.elapsedMs();
            st.grains = g.grains;
            st.meanGrainSize = g.grains > 0 ? double(g.cells) / double(g.grains) : 0.0;
            mem.release("mcStatsTemp");
            if (keep != nullptr) {
                *keep = std::move(g);
                mem.allocate(keepName, keep->bytes());
            }
        }
        st.energy = mc.totalEnergy();  // MPI_Allreduce liczby par „różnych” sąsiadów
        halo.setStatsPhase(false);
        return st;
    };

    // Migawki kryształów (proces 0) — czas osobno, jak w engine.
    const int snapEvery = outDir.empty() ? 0 : cfg.mc.snapshotsEvery;
    const fs::path snapDir = fs::path(outDir) / "mc_snapshots";
    double snapMs = 0.0;
    const auto writeSnapshot = [&](int k) {
        const double s0 = MPI_Wtime();
        const CrystalMap map = gatherCrystals();
        if (ctx.root()) {
            char name[32];
            std::snprintf(name, sizeof(name), "mcs_%06d.bin", k);
            ResultWriter::writeCrystalBin((snapDir / name).string(), map);
        }
        snapMs += (MPI_Wtime() - s0) * 1000.0;
    };
    if (snapEvery > 0) {
        if (ctx.root()) {
            fs::create_directories(snapDir);
        }
        writeSnapshot(0);
    }

    // --- pętla MCS (mcSim) ze statystykami co statsEvery (mcStats) ---
    double simMs = 0.0;
    double statsMs = 0.0;
    double sweepMin = 0.0;
    double sweepMax = 0.0;
    double sweepFirst = 0.0;
    double sweepLast = 0.0;
    GrainLabels startLabels;
    GrainLabels endLabels;
    double s0 = MPI_Wtime();
    s.history.push_back(measure(&startLabels, "mcLabelsStart"));
    statsMs += (MPI_Wtime() - s0) * 1000.0;
    std::uint64_t attemptsBefore = 0;
    std::uint64_t acceptedBefore = 0;
    if (progress != nullptr) {
        progress->report("mc", 0, cfg.mc.mcs, true);
    }
    for (int k = 1; k <= cfg.mc.mcs; ++k) {
        s0 = MPI_Wtime();
        mc.sweep();
        const double sweepMs = (MPI_Wtime() - s0) * 1000.0;
        simMs += sweepMs;
        sweepMin = (k == 1) ? sweepMs : std::min(sweepMin, sweepMs);
        sweepMax = std::max(sweepMax, sweepMs);
        sweepFirst = (k == 1) ? sweepMs : sweepFirst;
        sweepLast = sweepMs;
        if (k % cfg.mc.statsEvery == 0 || k == cfg.mc.mcs) {
            s0 = MPI_Wtime();
            McStats st = measure(k == cfg.mc.mcs ? &endLabels : nullptr, "mcLabelsEnd");
            std::uint64_t v[2] = {mc.attempts() - attemptsBefore, mc.accepted() - acceptedBefore};
            halo.setStatsPhase(true);
            halo.sum(v, 2);
            halo.setStatsPhase(false);
            st.acceptRate = v[0] > 0 ? double(v[1]) / double(v[0]) : 0.0;
            attemptsBefore = mc.attempts();
            acceptedBefore = mc.accepted();
            s.history.push_back(st);
            statsMs += (MPI_Wtime() - s0) * 1000.0;
        }
        if (snapEvery > 0 && (k % snapEvery == 0 || k == cfg.mc.mcs)) {
            writeSnapshot(k);
        }
        if (progress != nullptr) {
            progress->report("mc", k, cfg.mc.mcs, k == cfg.mc.mcs);
        }
    }
    if (cfg.mc.mcs == 0 && ctx.root()) {
        endLabels = startLabels;
        mem.allocate("mcLabelsEnd", endLabels.bytes());
    }
    timing.add("mcSim", simMs);
    if (threadStats) {
        timing.addThreadStats("mc", threadStats->toJson());
    }
    if (snapEvery > 0) {
        timing.add("mcSnapshots", snapMs);
        if (ctx.root()) {
            timing.addFile(snapDir.string(), snapMs);
        }
    }
    if (timing.detailEnabled()) {
        timing.addDetail("mcSweepFirst", sweepFirst);
        timing.addDetail("mcSweepLast", sweepLast);
        timing.addDetail("mcSweepMin", sweepMin);
        timing.addDetail("mcSweepMax", sweepMax);
        timing.addDetail("mcStatsLabels", labelMs);
        timing.addDetail("mcStatsGather", statsGatherMs);
    }

    // --- statystyki końcowe (proces 0) i mapa kryształów ---
    s0 = MPI_Wtime();
    std::uint64_t counts3[3] = {mc.attempts(), mc.accepted(), mc.acceptedUphill()};
    halo.setStatsPhase(true);
    halo.sum(counts3, 3);
    halo.setStatsPhase(false);
    s.crystals = gatherCrystals();
    if (ctx.root()) {
        McStatsInput in;
        in.dims = G;
        in.checkerboard = mc.checkerboard();
        in.colors = mc.colorCount();
        in.mooreConnectivity = mc.mooreConnectivity();
        in.attempts = counts3[0];
        in.accepted = counts3[1];
        in.acceptedUphill = counts3[2];
        in.startLabels = &startLabels;
        in.endLabels = &endLabels;
        in.cellMobility = &cellMobility;
        s.stats = McStage::statsJson(cfg, s, in);
        mem.allocate("mcCrystals", s.crystals.bytes());
    }
    statsMs += (MPI_Wtime() - s0) * 1000.0;
    timing.add("mcStats", statsMs);
    mem.release("mcGrid");
    mem.release("mcLabelsStart");
    mem.release("mcLabelsEnd");
    if (info != nullptr) {
        info->plan = plan;
        info->sim = halo.simCounters();
        info->stats = halo.statsCounters();
        info->simMs = simMs;
        info->statsMs = statsMs;
        info->statsGatherMs = statsGatherMs;
        info->labelMs = labelMs;
    }
    return s;
}

int MpiSimulation::runFromCli(const CliOptions& opt, const Timer& sinceStart, double mpiInitMs) {
    MpiContext ctx = MpiContext::world();
    ctx.initMs = mpiInitMs;
    const ProcessMemory startMemory = ProcessInfo::memory();
    TimingReport timing;
    timing.enableDetail(opt.timingDetail);
    timing.enableThreadStats(opt.threadStats && ctx.root());
    ProgressReporter progress = (opt.progress && ctx.root()) ? ProgressReporter(std::cout) : ProgressReporter();

    // 1. Config: proces 0 wczytuje plik (+ --set), sprawdza i rozsyła scalony JSON; pozostałe procesy budują z niego
    //    ten sam Config (Config::fromJson) i niczego nie czytają z dysku. --mc-from: proces 0 czyta też wynik CA.
    Timer t;
    Config cfg;
    std::string text;
    Microstructure caInput;
    ResultSource src;
    CoolingData cooling = CoolingData::Full;
    std::vector<std::string> warnings;
    if (ctx.root()) {
        cfg = Config::load(opt.configPath, opt.overrides);
        if (!opt.mcFrom.empty()) {
            prepareMcFrom(cfg, opt.mcFrom, caInput, src, cooling, warnings, timing);
        }
        checkConfig(cfg, ctx.size);
        text = cfg.effective.dump();
    }
    const double readMs = t.elapsedMs();
    bcastText(ctx, text);
    if (!ctx.root()) {
        cfg = Config::fromJson(ojson::parse(text));
    }
    int coolingCode = static_cast<int>(cooling);
    MPI_Bcast(&coolingCode, 1, MPI_INT, 0, ctx.comm);
    cooling = static_cast<CoolingData>(coolingCode);
    timing.add("readConfig", readMs);

    // 2. Proces przed obliczeniami: priorytet, wątki, rdzenie.
    if (ctx.root()) {
        warnings.insert(warnings.begin(), cfg.warnings.begin(), cfg.warnings.end());
    }
    const ProcessSetup setup = setupProcess(ctx, cfg, timing, warnings);
    if (ctx.root()) {
        for (const std::string& w : warnings) {
            std::cerr << "Ostrzeżenie: " << w << '\n';
        }
    }
    std::string outDir = opt.outDir;
    if (outDir.empty()) {
        const std::string stem = opt.configPath.empty() ? "default" : fs::path(opt.configPath).stem().string();
        outDir = (fs::path("results") / stem).string();
    }
    const fs::path out(outDir);
    if (ctx.root()) {
        fs::create_directories(outDir);
        Timer tc;
        ResultWriter::writeJson((out / "config_used.json").string(), cfg.effective);
        timing.addFile((out / "config_used.json").string(), tc.elapsedMs());
    }

    // 3. Symulacja (wszystkie procesy), zapis plików (proces 0).
    MpiCaRun ca;
    McSummary mcs;
    MpiMcRun mcRun;
    bool caRan = false;
    bool mcRan = false;
    ojson stats = ojson::object();
    if (!opt.mcFrom.empty()) {
        // --mc-from: proces 0 rozdziela pasy wyniku CA z pliku (MPI_Scatterv), dalej MC jak na wyniku z pamięci.
        const std::vector<int> split = splitLayers(layerCountOf(cfg.space), ctx.size);
        const std::uint64_t plane = layerPlane(cfg.space);
        Microstructure slab;
        slab.resize(windowDims(cfg.space, split[static_cast<std::size_t>(ctx.rank) + 1] -
                                              split[static_cast<std::size_t>(ctx.rank)]));
        scatterField(ctx, split, plane, caInput.type, slab.type);
        scatterField(ctx, split, plane, caInput.solidStep, slab.solidStep);
        scatterField(ctx, split, plane, caInput.arrivalStep, slab.arrivalStep);
        mcs = runMc(ctx, cfg, &slab, cooling, timing, &progress, outDir, &mcRun);
        mcRan = true;
        if (ctx.root()) {
            progress.report("save", 0, 1, true);
            McStage::save(cfg, mcs, outDir, timing);
            Timer ts;
            stats["source"] = {{"folder", cfg.effective["_mcFrom"]},
                               {"file", src.path},
                               {"format", src.format},
                               {"version", src.version},
                               {"coolingData", cooling == CoolingData::Full        ? "solidStep+arrivalStep"
                                               : cooling == CoolingData::SolidOnly ? "solidStep"
                                                                                   : "brak"}};
            stats["parallel"] = parallelJson(cfg, ctx.size);
            stats["mc"] = mcs.stats;
            Timer tf;
            ResultWriter::writeJson((out / "stats.json").string(), stats);
            timing.addFile((out / "stats.json").string(), tf.elapsedMs());
            timing.add("mcSave", ts.elapsedMs());
        }
    } else {
        RunSummary rs;
        if (!cfg.mc.fullOnly()) {
            caRan = true;
            ca = runCa(ctx, cfg, timing, &progress, outDir);
            if (ctx.root()) {
                progress.report("save", 0, 1, true);
                Timer ts;
                Timer tf;
                if (cfg.output.format == OutputFormat::Txt || cfg.output.format == OutputFormat::Both) {
                    const std::string path = (out / "ca_result.txt").string();
                    tf.reset();
                    ResultWriter::writeTxt(path, ca.result);
                    timing.addFile(path, tf.elapsedMs());
                }
                if (cfg.output.format == OutputFormat::Bin || cfg.output.format == OutputFormat::Both) {
                    const std::string path = (out / "ca_result.bin").string();
                    tf.reset();
                    ResultWriter::writeBin(path, ca.result);
                    timing.addFile(path, tf.elapsedMs());
                }
                timing.add("save", ca.gatherMs + ts.elapsedMs());
                rs.steps = ca.steps;
                rs.stop = ca.stop;
                rs.vents = ca.vents;
                rs.activeHistory = ca.activeHistory;
                rs.changedHistory = ca.changedHistory;
                rs.result = std::move(ca.result);
                Timer tStats;
                stats = Simulation::buildStats(cfg, rs);
                timing.add("caStats", tStats.elapsedMs());
            } else {
                timing.add("save", ca.gatherMs);
            }
        }
        stats["parallel"] = parallelJson(cfg, ctx.size);
        if (cfg.mc.enabled) {
            mcs = runMc(ctx, cfg, caRan ? &ca.slab : nullptr, CoolingData::Full, timing, &progress, outDir, &mcRun);
            mcRan = true;
            if (ctx.root()) {
                progress.report("save", 0, 1, true);
                McStage::save(cfg, mcs, outDir, timing);
                stats["mc"] = mcs.stats;
            }
        }
        if (ctx.root()) {
            Timer ts;
            ResultWriter::writeJson((out / "stats.json").string(), stats);
            timing.addFile((out / "stats.json").string(), ts.elapsedMs());
            timing.add(mcRan ? "mcSave" : "save", ts.elapsedMs());
        }
    }

    // 4. Sekcja "mpi" w times.json — wszystkie procesy biorą udział w zbieraniu (MPI_Gather / MPI_Reduce).
    ojson m;
    m["processes"] = ctx.size;
    m["threadsPerProcess"] = cfg.parallelSettings().threads;
    m["library"] = mpiLibrary();
    int ver = 0;
    int sub = 0;
    MPI_Get_version(&ver, &sub);
    m["standard"] = std::to_string(ver) + "." + std::to_string(sub);
    m["exchange"] = cfg.mpiExchangeChanged() ? "changed" : "always";
    m["axis"] = layerAxisZ(cfg.space) ? "z" : "y";
    m["layers"] = layerCountOf(cfg.space);
    m["split"] = splitLayers(layerCountOf(cfg.space), ctx.size);
    m["initMs"] = spread(ctx, ctx.initMs);  // MPI_Init_thread (część total, której nie ma w engine)
    m["bcast"] = {{"configBytes", ctx.bcastConfigBytes},
                  {"configMs", round3(ctx.bcastConfigMs)},
                  {"terrainBytes", ctx.bcastTerrainBytes},
                  {"terrainMs", round3(ctx.bcastTerrainMs)}};
    if (caRan) {
        m["ca"] = stageJson(ctx, ca.plan, ca.comm, ca.simMs, static_cast<std::uint64_t>(ca.steps));
        m["ca"]["gatherMs"] = spread(ctx, ca.gatherMs);
    }
    if (mcRan) {
        ojson j = stageJson(ctx, mcRun.plan, mcRun.sim, mcRun.simMs, static_cast<std::uint64_t>(cfg.mc.mcs));
        j["statsMs"] = spread(ctx, mcRun.statsMs);
        j["statsCommMs"] = spread(ctx, mcRun.stats.commMs());
        j["statsGatherMs"] = spread(ctx, mcRun.statsGatherMs);
        if (ctx.root()) {
            j["statsLabelMs"] = round3(mcRun.labelMs);
        }
        m["mc"] = j;
    }
    m["gather"] = {{"bytes", total(ctx, ctx.gatherBytes)}, {"ms", spread(ctx, ctx.gatherMs)}};
    if (!opt.mcFrom.empty()) {
        m["scatter"] = {{"bytes", total(ctx, ctx.scatterBytes)}, {"ms", spread(ctx, ctx.scatterMs)}};
    }
    // Procesory i priorytet każdego procesu.
    const int threads = cfg.parallelSettings().threads;
    std::vector<int> mine(static_cast<std::size_t>(threads), -1);
    for (std::size_t i = 0; i < setup.cpus.size() && i < mine.size(); ++i) {
        mine[i] = setup.cpus[i];
    }
    std::vector<int> cpusAll(ctx.root() ? static_cast<std::size_t>(ctx.size * threads) : 0);
    MPI_Gather(mine.data(), threads, MPI_INT, ctx.root() ? cpusAll.data() : nullptr, threads, MPI_INT, 0, ctx.comm);
    int high = setup.highPriority ? 1 : 0;
    std::vector<int> highAll(ctx.root() ? static_cast<std::size_t>(ctx.size) : 0);
    MPI_Gather(&high, 1, MPI_INT, ctx.root() ? highAll.data() : nullptr, 1, MPI_INT, 0, ctx.comm);
    double peak = static_cast<double>(ProcessInfo::memory().peakRss);
    const ojson peakSpread = spread(ctx, peak);
    timing.add("total", sinceStart.elapsedMs());
    if (!ctx.root()) {
        return 0;
    }
    if (cfg.parallel.affinity == Affinity::PCores) {
        ojson cpus = ojson::array();
        for (int r = 0; r < ctx.size; ++r) {
            cpus.push_back(std::vector<int>(cpusAll.begin() + r * threads, cpusAll.begin() + (r + 1) * threads));
        }
        m["cpus"] = cpus;
    }
    ojson pri = ojson::array();
    for (const int h : highAll) {
        pri.push_back(h != 0 ? "high" : "normal");
    }
    m["priority"] = pri;
    m["peakRssBytes"] = peakSpread;

    // 5. times.json i podsumowanie (proces 0).
    const Dims& d = mcRan ? mcs.crystals.dims : cfg.space;
    timing.setInfo("cells", d.cells());
    timing.setInfo("space", {d.nx, d.ny, d.nz});
    timing.setInfo("neighborhood", Neighborhood::name(cfg.neighborhood));
    timing.setInfo("boundary", Boundary::name(cfg.boundary));
    if (!opt.mcFrom.empty()) {
        timing.setInfo("mode", "mc_from");
        timing.setInfo("mcFrom", opt.mcFrom);
    } else if (caRan) {
        timing.setInfo("steps", ca.steps);
        timing.setInfo("grid", nameOf(cfg.grid));
        timing.setInfo("mode", nameOf(cfg.ca.mode));
        timing.setInfo("stopReason", describe(ca.stop));
    } else {
        timing.setInfo("mode", "mc_full");
    }
    if (mcRan) {
        timing.setInfo("mcDomain", nameOf(mcs.domain));
        timing.setInfo("mcs", mcs.mcs);
        timing.setInfo("domainCells", mcs.domainCells);
        timing.setInfo("Q", mcs.Q);
        timing.setInfo("mcMobility", mcs.mobilityUsed);
    }
    timing.setInfo("cpu", TimingReport::cpuName());
    timing.setInfo("compiler", TimingReport::compilerName());
    timing.setInfo("build", TimingReport::buildType());
    timing.setInfo("mpi", m);
    timing.recordFileSizes();
    timing.recordMemory(startMemory, d.cells());
    ResultWriter::writeJson((out / "times.json").string(), timing.toJson());

    for (const std::string& w : mcs.warnings) {
        std::cerr << "Ostrzeżenie: " << w << '\n';
    }
    std::ostringstream os;
    os << "=== Symulacja zakończona (MPI: " << ctx.size << " proc. × " << threads << " wątk.) ===\n";
    os << "Przestrzeń     " << d.nx << " x " << d.ny << " x " << d.nz << " (" << (d.is2D() ? "2D" : "3D") << ", "
       << d.cells() << " komórek), pasy w osi " << (layerAxisZ(d) ? "z" : "y") << " po "
       << layerCountOf(d) / ctx.size << (layerCountOf(d) % ctx.size != 0 ? "+" : "") << " warstw\n";
    os << "Sąsiedztwo     " << Neighborhood::name(cfg.neighborhood) << ", brzeg " << Boundary::name(cfg.boundary)
       << ", seed " << cfg.rngSeed << ", wymiana " << (cfg.mpiExchangeChanged() ? "changed" : "always") << '\n';
    if (caRan) {
        os << "Kroki          " << ca.steps << " (koniec: " << describe(ca.stop) << ")\n";
        if (m.contains("ca")) {
            os << "Komunikacja CA " << m["ca"]["messages"].get<std::uint64_t>() << " komunikatów, "
               << m["ca"]["bytes"].get<std::uint64_t>() << " B; czas kroków "
               << fixed(m["ca"]["simMs"]["max"].get<double>(), 1) << " ms, z tego komunikacja "
               << fixed(m["ca"]["commMs"]["min"].get<double>(), 1) << "–"
               << fixed(m["ca"]["commMs"]["max"].get<double>(), 1) << " ms\n";
        }
    }
    if (mcRan) {
        os << McStage::describe(mcs);
    }
    std::string line = "Czasy [ms]     ";
    const char* sep = "";
    for (const auto& [name, ms] : timing.sections()) {
        line += sep + name + ' ' + fixed(ms, 2);
        sep = " | ";
    }
    os << line << '\n' << "Wyniki         " << outDir << '\n';
    std::cout << os.str();
    return 0;
}

}  // namespace volcano
