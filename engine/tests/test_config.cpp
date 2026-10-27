// Testy konfiguracji: wartości domyślne, scalanie z plikiem, --set, czytelne błędy.
#include "doctest.h"

#include <filesystem>
#include <fstream>
#include <string>

#include "io/Config.hpp"

using namespace volcano;

namespace {

// Wczytuje config z samych nadpisań i zwraca komunikat błędu (pusty, gdy brak błędu).
std::string errorOf(const std::vector<std::string>& overrides) {
    try {
        Config::load("", overrides);
    } catch (const ConfigError& e) {
        return e.what();
    }
    return "";
}

// Zapisuje tekst do pliku tymczasowego i zwraca ścieżkę.
std::string writeTemp(const std::string& name, const std::string& text) {
    const auto dir = std::filesystem::temp_directory_path() / "volcano_tests";
    std::filesystem::create_directories(dir);
    const auto path = dir / name;
    std::ofstream(path) << text;
    return path.string();
}

bool contains(const std::string& s, const std::string& part) { return s.find(part) != std::string::npos; }

}  // namespace

TEST_CASE("Config: wartości domyślne zgodne z opisem") {
    const Config c = Config::load("", {});
    CHECK((c.space == Dims{200, 1, 100}));
    CHECK(c.grid == GridKind::Vector);
    CHECK(c.boundary == BoundaryKind::Absorbing);
    CHECK(c.neighborhood == NeighborhoodKind::Moore);
    CHECK(c.rngSeed == 42);
    CHECK(c.ca.mode == CaMode::Lava);
    CHECK(c.ca.maxSteps == 5000);
    CHECK(c.vents.eruptTemp == 1200.0);
    CHECK(c.output.format == OutputFormat::Txt);
    CHECK(c.effective["terrain"]["file"].is_null());
}

TEST_CASE("Config: nadpisania --set (liczby, tekst, wartości logiczne)") {
    const Config c = Config::load("", {"space.nx=1000", "neighborhood=von_neumann", "ca.ponding=false",
                                       "grid=matrix", "ca.coolingFall=0.25"});
    CHECK(c.space.nx == 1000);
    CHECK(c.neighborhood == NeighborhoodKind::VonNeumann);
    CHECK_FALSE(c.ca.ponding);
    CHECK(c.grid == GridKind::Matrix);
    CHECK(c.ca.coolingFall == 0.25);
    CHECK(c.effective["space"]["nx"] == 1000);  // trafia do config_used.json
}

TEST_CASE("Config: plik JSON scalany z domyślnymi, komentarze dozwolone") {
    const std::string path = writeTemp("cfg_ok.json", R"({
        "_opis": "komentarz w kluczu z podkreśleniem",
        // komentarz w stylu C++
        "space": { "nx": 50, "nz": 40 },
        "vents": { "count": 2 }
    })");
    const Config c = Config::load(path, {"space.nz=30"});
    CHECK((c.space == Dims{50, 1, 30}));  // ny z domyślnych, nz z --set (po pliku)
    CHECK(c.vents.count == 2);
    CHECK(c.sourcePath == path);
}

TEST_CASE("Config: błędne wartości dają czytelny komunikat z nazwą parametru") {
    std::string e = errorOf({"neighborhood=octagonal"});
    CHECK(contains(e, "neighborhood"));
    CHECK(contains(e, "octagonal"));
    CHECK(contains(e, "von_neumann"));  // lista dozwolonych

    e = errorOf({"space.nx=abc"});
    CHECK(contains(e, "space.nx"));
    CHECK(contains(e, "liczbą całkowitą"));

    e = errorOf({"space.nx=0"});
    CHECK(contains(e, "zakresu"));

    e = errorOf({"space.nxx=10"});
    CHECK(contains(e, "Nieznany parametr"));
    CHECK(contains(e, "space.nxx"));

    e = errorOf({"ca.coolingFall=-1"});
    CHECK(contains(e, "ca.coolingFall"));
}

TEST_CASE("Config: niedozwolone kombinacje") {
    // sąsiedztwo heksagonalne tylko w 2D
    CHECK(contains(errorOf({"space.ny=50", "neighborhood=hexagonal"}), "tylko w 2D"));
    // lawa w 2D wymaga przekroju x–z (ny = 1)
    CHECK(contains(errorOf({"space.ny=50", "space.nz=1"}), "ny = 1"));
    // przestrzeń 1D
    CHECK(contains(errorOf({"space.nz=1"}), "2D"));
    // classic: więcej ziaren niż komórek
    CHECK(contains(errorOf({"ca.mode=classic", "space.nx=3", "space.nz=3", "vents.count=10"}), "vents.count"));
    // classic 2D w dowolnej płaszczyźnie jest dozwolony
    CHECK(errorOf({"ca.mode=classic", "space.nx=20", "space.ny=20", "space.nz=1"}).empty());
}

TEST_CASE("Config: błąd składni i brak pliku") {
    const std::string bad = writeTemp("cfg_bad.json", R"({ "space": { "nx": 10, } )");
    CHECK_THROWS_AS(Config::load(bad, {}), ConfigError);
    CHECK_THROWS_AS(Config::load("nie_ma_takiego_pliku.json", {}), ConfigError);
}

TEST_CASE("Config: sekcja mc — wartości domyślne i nadpisania") {
    const Config c = Config::load("", {});
    CHECK_FALSE(c.mc.enabled);
    CHECK(c.mc.domain == McDomain::Basalt);
    CHECK(c.mc.Q == 50);
    CHECK(c.mc.mcs == 100);
    CHECK(c.mc.J == 1.0);
    CHECK(c.mc.kT == 0.0);
    CHECK(c.mc.mobilityFromCooling);
    CHECK(c.mc.mobilityMin == 0.05);
    CHECK(c.mc.statsEvery == 10);
    CHECK(c.effective["mc"]["Q"] == 50);

    const Config m = Config::load("", {"mc.enabled=true", "mc.Q=7", "mc.mcs=0", "mc.J=0.5", "mc.kT=1.25",
                                       "mc.mobilityMin=0", "mc.statsEvery=3"});
    CHECK(m.mc.enabled);
    CHECK(m.mc.Q == 7);
    CHECK(m.mc.mcs == 0);
    CHECK(m.mc.J == 0.5);
    CHECK(m.mc.kT == 1.25);
    CHECK(m.mc.mobilityMin == 0.0);
    CHECK(m.mc.statsEvery == 3);
    CHECK(m.warnings.empty());  // dawne ostrzeżenie „mc.enabled ignorowane” zniknęło
}

TEST_CASE("Config: walidacja sekcji mc") {
    CHECK(contains(errorOf({"mc.Q=1"}), "mc.Q"));
    CHECK(contains(errorOf({"mc.mcs=-1"}), "mc.mcs"));
    CHECK(contains(errorOf({"mc.J=0"}), "mc.J"));
    CHECK(contains(errorOf({"mc.J=-2"}), "mc.J"));
    CHECK(contains(errorOf({"mc.kT=-0.5"}), "mc.kT"));
    CHECK(contains(errorOf({"mc.mobilityMin=1.5"}), "mc.mobilityMin"));
    CHECK(contains(errorOf({"mc.statsEvery=0"}), "mc.statsEvery"));
    CHECK(contains(errorOf({"mc.domain=granite"}), "basalt"));
    CHECK(contains(errorOf({"mc.Q=2.5"}), "liczbą całkowitą"));
    CHECK(contains(errorOf({"mc.mobilityFromCooling=1"}), "true lub false"));
    CHECK(contains(errorOf({"mc.temperature=1"}), "Nieznany parametr"));
    // basalt wymaga lawy (w classic nie ma bazaltu); wyłączone MC nie przeszkadza
    CHECK(contains(errorOf({"mc.enabled=true", "ca.mode=classic", "space.ny=20", "space.nz=1"}), "mc.domain"));
    CHECK(errorOf({"ca.mode=classic", "space.ny=20", "space.nz=1"}).empty());
}

TEST_CASE("Config: tryb mc full pomija walidację lawy, mobilityFromCooling daje ostrzeżenie") {
    // 2D w płaszczyźnie x–y jest niedozwolone dla lawy, ale w trybie full CA nie działa.
    CHECK(contains(errorOf({"space.ny=50", "space.nz=1"}), "ny = 1"));
    const Config f = Config::load("", {"mc.enabled=true", "mc.domain=full", "space.ny=50", "space.nz=1"});
    CHECK(f.mc.fullOnly());
    REQUIRE(f.warnings.size() == 1);
    CHECK(contains(f.warnings[0], "mobilityFromCooling"));
    const Config g = Config::load("", {"mc.enabled=true", "mc.domain=full", "mc.mobilityFromCooling=false",
                                       "space.ny=50", "space.nz=1"});
    CHECK(g.warnings.empty());
    // hexagonal w 3D jest błędem także dla MC
    CHECK(contains(errorOf({"mc.enabled=true", "mc.domain=full", "space.ny=20", "neighborhood=hexagonal"}),
                   "tylko w 2D"));
}

TEST_CASE("Config: vents.positions — kratery w zadanych kolumnach") {
    // Domyślnie lista pusta i placement = crater (stare configi bez zmian).
    const Config d = Config::load("", {});
    CHECK(d.vents.placement == VentPlacement::Crater);
    CHECK(d.ventColumns().empty());
    CHECK(d.effective["vents"]["positions"].is_array());
    CHECK(d.mc.snapshotsEvery == 0);

    // Poprawna lista (przekrój 2D 200 x 1: y = 0); kolejność zachowana.
    const Config c = Config::load("", {"vents.placement=positions", "vents.count=2",
                                       "vents.positions=[[100, 0], [40, 0]]"});
    CHECK(c.vents.placement == VentPlacement::Positions);
    const auto cols = c.ventColumns();
    REQUIRE(cols.size() == 2);
    CHECK(cols[0].first == 100);
    CHECK(cols[1].first == 40);
    CHECK(cols[1].second == 0);
    CHECK(c.warnings.empty());

    // Błędy z nazwą parametru (GUI podświetla pole).
    CHECK(contains(errorOf({"vents.placement=positions"}), "vents.positions"));                       // pusta lista
    CHECK(contains(errorOf({"vents.placement=positions", "vents.positions=[[1, 0], [2, 0]]"}), "vents.count"));
    CHECK(contains(errorOf({"vents.positions=[[200, 0]]"}), "poza siatką"));                           // x = nx
    CHECK(contains(errorOf({"vents.positions=[[5, 1]]"}), "poza siatką"));                             // y = ny
    CHECK(contains(errorOf({"vents.positions=[[-1, 0]]"}), "poza siatką"));
    CHECK(contains(errorOf({"vents.placement=positions", "vents.count=2", "vents.positions=[[7, 0], [7, 0]]"}),
                   "powtarza"));
    CHECK(contains(errorOf({"vents.positions=[[1]]"}), "parą liczb"));
    CHECK(contains(errorOf({"vents.positions=[[1.5, 0]]"}), "parą liczb"));
    CHECK(contains(errorOf({"vents.positions=[[\"a\", 0]]"}), "parą liczb"));
    CHECK(contains(errorOf({"vents.positions=[[99999999999, 0]]"}), "parą liczb"));
    CHECK(contains(errorOf({"vents.positions=7"}), "listą par"));
    CHECK(contains(errorOf({"vents.placement=everywhere"}), "positions"));                             // lista dozwolonych

    // Lista przy placement crater/random jest ignorowana z ostrzeżeniem; w classic — ostrzeżenie przy positions.
    const Config w = Config::load("", {"vents.positions=[[100, 0]]"});
    REQUIRE(w.warnings.size() == 1);
    CHECK(contains(w.warnings[0], "vents.positions"));
    const Config cl = Config::load("", {"ca.mode=classic", "space.ny=20", "space.nz=1", "vents.count=3",
                                        "vents.placement=positions"});
    REQUIRE(cl.warnings.size() == 1);
    CHECK(contains(cl.warnings[0], "classic"));

    // Migawki MC: liczba >= 0.
    CHECK(Config::load("", {"mc.snapshotsEvery=5"}).mc.snapshotsEvery == 5);
    CHECK(contains(errorOf({"mc.snapshotsEvery=-1"}), "mc.snapshotsEvery"));
}

TEST_CASE("Config: warianty MPI: mpi.pack, mpi.bcast, mpi.io") {
    const Config d = Config::load("", {});
    CHECK_FALSE(d.mpiPackDatatype());  // domyślnie jak w etapie 10: manual, json, gather
    CHECK_FALSE(d.mpiBcastStruct());
    CHECK_FALSE(d.mpiIoParallel());
    const Config c = Config::load("", {"mpi.pack=datatype", "mpi.bcast=struct", "mpi.io=mpiio"});
    CHECK(c.mpiPackDatatype());
    CHECK(c.mpiBcastStruct());
    CHECK(c.mpiIoParallel());
    CHECK(contains(errorOf({"mpi.pack=memcpy"}), "mpi.pack"));
    CHECK(contains(errorOf({"mpi.bcast=text"}), "mpi.bcast"));
    CHECK(contains(errorOf({"mpi.io=posix"}), "mpi.io"));
}
