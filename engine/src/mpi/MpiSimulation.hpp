#pragma once
// Program engine_mpi (etap 10) — ta sama symulacja co engine (CA lawy / classic, MC na bazalcie albo na całej
// przestrzeni, --mc-from), w pamięci rozproszonej: przestrzeń jest podzielona na pasy warstw między procesy MPI
// (parallel/Strip.hpp), a każdy proces liczy swój pas tym samym kodem automatu i MC co engine (LavaCA, PottsMC
// w oknie pasa). Przebieg:
//   1. proces 0 wczytuje i sprawdza config (+ --set), rozsyła scalony JSON (MPI_Bcast długości i treści); mapę
//      wysokości (stożek albo plik CSV) liczy / czyta proces 0 i rozsyła tablicę wysokości — pozostałe procesy nie
//      czytają niczego z dysku;
//   2. teren w oknie, poziomy przelewu (priority-flood na całej mapie — każdy proces liczy to samo), kratery /
//      zarodki z tego samego ziarna (każdy proces ma tę samą globalną listę z ID, wstawia te w swoim oknie);
//   3. kroki CA: przed krokiem wymiana warstw brzegowych (MpiHalo), po kroku MPI_Allreduce liczników — historia
//      i reguła końca są globalne;
//   4. wynik: MPI_Gatherv pasów do procesu 0, który zapisuje te same pliki co engine (ca_result.*, stats.json, …);
//   5. MC (tylko szachownica przy > 1 procesie): domena i mobilność z pasa wyniku CA (koniec CA i zakres czasów —
//      MPI_Allreduce), po każdym kolorze wymiana warstw brzegowych, energia — MPI_Allreduce, liczba ziaren —
//      MPI_Gatherv mapy kryształów do procesu 0 i union-find tam (część szeregowa);
//   6. times.json (proces 0): czasy jak w engine + sekcja "mpi" (procesy, podział, rozsyłanie, komunikacja
//      i obliczenia każdego procesu: min / średnia / maks, bajty i komunikaty).
// Etap 11 — warianty (config, sekcja mpi; domyślnie jak w etapie 10):
//   mpi.bcast = "struct" — w kroku 1 zamiast JSON blok liczbowy configu jednym MPI_Bcast typu struct, a kratery /
//                          zarodki wyznacza proces 0 i rozsyła jako tablicę struktur (mpi/MpiTypes.hpp);
//   mpi.pack = "datatype" — w kroku 3 komunikaty warstw brzegowych opisane typami pochodnymi (mpi/MpiHalo.hpp);
//   mpi.io = "mpiio"     — w kroku 4 (i przy zapisie MC, migawek, odczycie --mc-from) każdy proces zapisuje / czyta
//                          swój pas wspólnego pliku (mpi/MpiIo.hpp); statystyki CA (stats.json) liczone w pasach
//                          i sumowane MPI_Reduce — proces 0 nie potrzebuje pamięci na cały wynik CA.
// Wynik przy dowolnej liczbie procesów i każdej kombinacji wariantów jest bitowo ten sam co w engine (testy
// engine/tests/mpi/).

#include <mpi.h>

#include <cstdint>
#include <string>
#include <vector>

#include "app/Cli.hpp"
#include "app/McStage.hpp"
#include "app/Progress.hpp"
#include "ca/CaRules.hpp"
#include "core/Timer.hpp"
#include "core/Types.hpp"
#include "io/Config.hpp"
#include "io/TimingReport.hpp"
#include "mpi/MpiHalo.hpp"
#include "mpi/MpiIo.hpp"
#include "parallel/Strip.hpp"
#include "terrain/VentPlacer.hpp"

namespace volcano {

// Plik wyników zapisany przez MPI-IO (mpi.io = "mpiio") — czasy tego procesu (sekcja mpi.io w times.json).
struct IoRecord {
    std::string file;   // nazwa pliku
    IoTimes times;      // formatowanie, MPI-IO, bajty
    double wallMs = 0;  // cały zapis pliku na tym procesie (formatowanie + MPI-IO)
};

// Proces MPI i komunikacja zbiorowa poza krokami symulacji (rozsyłanie danych wejściowych, zbieranie wyników).
struct MpiContext {
    MPI_Comm comm = MPI_COMM_WORLD;
    int rank = 0;
    int size = 1;
    double initMs = 0.0;         // start programu -> koniec MPI_Init_thread (wliczony w sekcję total)
    double bcastConfigMs = 0.0;  // MPI_Bcast configu (JSON: długość + tekst; struct: blok liczbowy)
    std::uint64_t bcastConfigBytes = 0;
    bool bcastStruct = false;     // etap 11: mpi.bcast = "struct"
    double configPrepMs = 0.0;    // proces 0: config -> tekst JSON / blok struktury
    double configBuildMs = 0.0;   // procesy != 0: tekst -> Config (parsowanie + walidacja) / blok -> Config
    double bcastVentsMs = 0.0;    // struct: MPI_Bcast tablicy kraterów / zarodków
    std::uint64_t bcastVentsBytes = 0;
    double bcastTerrainMs = 0.0;  // MPI_Bcast mapy wysokości
    std::uint64_t bcastTerrainBytes = 0;
    double gatherMs = 0.0;  // MPI_Gatherv wyników na proces 0 (CA, MC, migawki, mapa kryształów do statystyk)
    std::uint64_t gatherBytes = 0;
    double scatterMs = 0.0;  // MPI_Scatterv wyniku CA z pliku (--mc-from)
    std::uint64_t scatterBytes = 0;
    std::vector<IoRecord> io;  // etap 11: pliki zapisane przez MPI-IO (ta sama kolejność na każdym procesie)
    bool readParallel = false;  // etap 11: --mc-from przez MPI-IO (każdy proces czyta swój pas)
    IoTimes read;

    bool root() const { return rank == 0; }
    static MpiContext world();
};

// Wynik części CA.
struct MpiCaRun {
    int steps = 0;
    StopReason stop = StopReason::Running;
    std::vector<Vent> vents;                    // globalna lista kraterów / zarodków (każdy proces)
    std::vector<std::uint64_t> activeHistory;   // historia liczników — globalna, ta sama na każdym procesie
    std::vector<std::uint64_t> changedHistory;
    Microstructure result;                      // cały wynik (tylko proces 0; mpi.io = "mpiio" — pusty)
    Microstructure slab;                        // własne warstwy wyniku (każdy proces) — wejście MC, zapis MPI-IO
    StripPlan plan;                             // pas tego procesu (okno, warstwy brzegowe)
    CommCounters comm;                          // komunikacja w krokach
    double simMs = 0.0;                         // czas kroków na tym procesie (MPI_Wtime)
    double gatherMs = 0.0;                      // pas bez ramki (ownLayers) + zebranie wyniku na proces 0 (bez mpiio)
};

// Komunikacja i czasy części MC.
struct MpiMcRun {
    StripPlan plan;
    CommCounters sim;           // w MCS (wymiana warstw po każdym kolorze)
    CommCounters stats;         // w statystykach (energia, współczynnik akceptacji)
    double simMs = 0.0;         // MCS (MPI_Wtime)
    double statsMs = 0.0;       // statystyki razem: mapa kryształów do procesu 0, union-find (proces 0), energia
    double statsGatherMs = 0.0; // w tym MPI_Gatherv mapy kryształów
    double labelMs = 0.0;       // w tym etykiety ziaren na procesie 0
    Dims ownDims;                          // mpi.io = "mpiio": wymiary pasa i mapa kryształów własnych warstw
    std::vector<std::int32_t> ownCrystals; // (zapis mc_result.* przez MPI-IO; McSummary::crystals jest wtedy puste)
};

class MpiSimulation {
public:
    // engine_mpi --config … --out … (te same opcje przebiegu co engine). Zwraca kod wyjścia; błąd configu na procesie 0
    // jest zgłaszany wyjątkiem ConfigError (main: komunikat + MPI_Abort). mpiInitMs — czas MPI_Init_thread od startu
    // programu (times.json: mpi.initMs; OpenMPI w WSL ~0,3 s, które wchodzą w total).
    static int runFromCli(const CliOptions& opt, const Timer& sinceStart, double mpiInitMs = 0.0);

    // Kombinacje nieobsługiwane w wersji rozproszonej (proces 0, przed rozesłaniem configu) — ConfigError.
    static void checkConfig(const Config& cfg, int processes);

    // Część CA (wszystkie procesy). ventsOverride (testy) — własna lista kraterów / zarodków zamiast z configu.
    // mpi.io = "mpiio": wynik zostaje w pasach (MpiCaRun::slab), bez zebrania na procesie 0.
    static MpiCaRun runCa(MpiContext& ctx, const Config& cfg, TimingReport& timing, ProgressReporter* progress,
                          const std::string& outDir, const std::vector<Vent>* ventsOverride = nullptr);

    // Część MC (wszystkie procesy) na przestrzeni cfg.space. slab — własne warstwy wyniku CA (domena basalt), nullptr —
    // cała przestrzeń (mc.domain = full). Statystyki, historia i mapa kryształów — na procesie 0 (mpi.io = "mpiio":
    // mapa zostaje w pasach — info->ownCrystals).
    static McSummary runMc(MpiContext& ctx, const Config& cfg, const Microstructure* slab, CoolingData cooling,
                           TimingReport& timing, ProgressReporter* progress, const std::string& outDir,
                           MpiMcRun* info = nullptr);
};

}  // namespace volcano
