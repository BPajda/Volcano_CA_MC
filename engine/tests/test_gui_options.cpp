// Testy opcji silnika dla GUI (etap 4): --print-defaults, --validate, --progress.
// Najważniejsze: raport postępu nie zmienia wyniku symulacji (pliki bitowo identyczne),
// a walidacja zwraca te same komunikaty co uruchomienie.
#include "doctest.h"

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <sstream>
#include <string>
#include <vector>

#include "app/Cli.hpp"
#include "app/ConfigCheck.hpp"
#include "app/Progress.hpp"
#include "app/Simulation.hpp"
#include "io/Config.hpp"
#include "io/TimingReport.hpp"

using namespace volcano;

namespace {

// Pusty folder tymczasowy na wyniki testu.
std::filesystem::path tempDir(const std::string& name) {
    const auto dir = std::filesystem::temp_directory_path() / "volcano_tests" / name;
    std::filesystem::remove_all(dir);
    std::filesystem::create_directories(dir);
    return dir;
}

// Zawartość pliku binarnego.
std::string readBytes(const std::filesystem::path& p) {
    std::ifstream in(p, std::ios::binary);
    return std::string(std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>());
}

// Czy któryś z błędów walidacji zawiera fragment tekstu.
bool hasError(const ValidationResult& r, const std::string& fragment) {
    for (const std::string& e : r.errors) {
        if (e.find(fragment) != std::string::npos) {
            return true;
        }
    }
    return false;
}

// Mały wulkan 2D (CA + MC) — kilka dziesiątek kroków, żeby test był szybki także w Debug.
Config smallLavaMc() {
    return Config::load("", {"space.nx=100", "space.nz=50", "terrain.peakHeight=35", "terrain.baseRadius=45",
                             "terrain.craterRadius=8", "terrain.craterDepth=4", "ca.coolingAmbient=2",
                             "ca.coolingLateral=8", "ca.coolingFall=5", "vents.eruptionSteps=60", "mc.enabled=true",
                             "mc.mcs=7", "mc.statsEvery=3", "output.format=bin"});
}

}  // namespace

TEST_CASE("Cli: opcje dla GUI --print-defaults, --validate, --progress") {
    const char* defaults[] = {"engine", "--print-defaults"};
    CHECK(Cli::parse(2, defaults).printDefaults);

    const char* validate[] = {"engine", "--validate", "--config", "a.json", "--set", "space.nx=10", "--mc-from", "r"};
    const CliOptions v = Cli::parse(8, validate);
    CHECK(v.validate);
    CHECK(v.configPath == "a.json");
    CHECK(v.mcFrom == "r");
    REQUIRE(v.overrides.size() == 1);

    const char* progress[] = {"engine", "--config", "a.json", "--out", "o", "--progress"};
    CHECK(Cli::parse(6, progress).progress);

    // Niedozwolone połączenia.
    const char* defaultsWithConfig[] = {"engine", "--print-defaults", "--config", "a.json"};
    CHECK_THROWS_AS(Cli::parse(4, defaultsWithConfig), CliError);
    const char* validateBenchmark[] = {"engine", "--validate", "--benchmark"};
    CHECK_THROWS_AS(Cli::parse(3, validateBenchmark), CliError);
    const char* validateProgress[] = {"engine", "--validate", "--progress"};
    CHECK_THROWS_AS(Cli::parse(3, validateProgress), CliError);
    const char* benchmarkProgress[] = {"engine", "--benchmark", "--progress"};
    CHECK_THROWS_AS(Cli::parse(3, benchmarkProgress), CliError);
}

TEST_CASE("ConfigCheck: --print-defaults to pełny domyślny config, który przechodzi walidację") {
    const nlohmann::ordered_json j = nlohmann::ordered_json::parse(ConfigCheck::defaultsText());
    CHECK(j == Config::defaultsJson());
    CHECK(j["space"]["nx"] == 200);
    CHECK(j["mc"].contains("mobilityMin"));
    CHECK_NOTHROW(Config::fromJson(j));
}

TEST_CASE("ConfigCheck: walidacja — poprawny config, błędy i ostrzeżenia po polsku") {
    SUBCASE("same wartości domyślne są poprawne") {
        const ValidationResult r = ConfigCheck::validate(CliOptions{});
        CHECK(r.ok);
        CHECK(r.errors.empty());
        CHECK(r.warnings.empty());
        CHECK(r.toJson()["ok"] == true);
    }
    SUBCASE("zła wartość wyliczeniowa i nieznany klucz") {
        CliOptions o;
        o.overrides = {"neighborhood=octagonal"};
        ValidationResult r = ConfigCheck::validate(o);
        CHECK_FALSE(r.ok);
        REQUIRE(r.errors.size() == 1);
        CHECK(hasError(r, "neighborhood"));
        CHECK(hasError(r, "dozwolone"));
        CHECK(r.toJson()["ok"] == false);

        o.overrides = {"space.nq=3"};
        r = ConfigCheck::validate(o);
        CHECK(hasError(r, "Nieznany parametr"));
    }
    SUBCASE("ostrzeżenie nie blokuje uruchomienia") {
        CliOptions o;
        o.overrides = {"mc.enabled=true", "mc.domain=full"};  // mobilityFromCooling = true jest ignorowane
        const ValidationResult r = ConfigCheck::validate(o);
        CHECK(r.ok);
        CHECK(r.warnings.size() == 1);
    }
    SUBCASE("brak pliku configu albo mapy wysokości") {
        CliOptions o;
        o.configPath = "nie_ma_takiego_configu.json";
        CHECK(hasError(ConfigCheck::validate(o), "Nie można otworzyć pliku konfiguracyjnego"));
        CliOptions t;
        t.overrides = {"terrain.type=file", "terrain.file=nie_ma_takiej_mapy.csv"};
        CHECK(hasError(ConfigCheck::validate(t), "mapy wysokości"));
    }
    SUBCASE("--mc-from: folder bez wyniku CA, brak folderu, zła domena") {
        const auto empty = tempDir("validate_mc_from");
        CliOptions o;
        o.overrides = {"mc.enabled=true"};
        o.mcFrom = empty.string();
        CHECK(hasError(ConfigCheck::validate(o), "ca_result"));
        o.mcFrom = (empty / "nie_ma").string();
        CHECK(hasError(ConfigCheck::validate(o), "nie istnieje"));
        o.mcFrom = empty.string();
        o.overrides = {"mc.enabled=true", "mc.domain=full"};
        CHECK(hasError(ConfigCheck::validate(o), "basalt"));
    }
    SUBCASE("runFromCli: JSON na wyjściu, kod 0 albo 1") {
        std::ostringstream good;
        CHECK(ConfigCheck::runFromCli(CliOptions{}, good) == 0);
        CHECK(nlohmann::json::parse(good.str())["ok"] == true);
        CliOptions o;
        o.overrides = {"space.nx=-5"};
        std::ostringstream bad;
        CHECK(ConfigCheck::runFromCli(o, bad) == 1);
        const nlohmann::json j = nlohmann::json::parse(bad.str());
        CHECK(j["ok"] == false);
        CHECK(j["errors"].size() == 1);
    }
}

TEST_CASE("ProgressReporter: format linii, odstęp między liniami, raport wyłączony") {
    std::ostringstream every;
    ProgressReporter p(every, 0.0);  // odstęp 0 — każda linia
    p.report("ca", 3, 10, false, "active", 7);
    p.report("mc", 1, 5);
    CHECK(every.str() == "PROGRESS ca 3/10 active=7\nPROGRESS mc 1/5\n");

    std::ostringstream rare;
    ProgressReporter slow(rare, 1e9);  // odstęp „nieskończony” — tylko linie wymuszone
    slow.report("ca", 1, 10);
    slow.report("ca", 2, 10, true);
    slow.report("ca", 3, 10);
    CHECK(rare.str() == "PROGRESS ca 2/10\n");

    ProgressReporter off;
    CHECK_FALSE(off.enabled());
    off.report("ca", 1, 1, true);  // nic nie robi
}

TEST_CASE("Simulation: --progress nie zmienia wyniku CA i MC; ostatnie linie = stan końcowy") {
    const auto plain = tempDir("progress_off");
    const auto withProgress = tempDir("progress_on");

    TimingReport t1;
    Simulation a(smallLavaMc());
    const RunSummary sa = a.run(plain.string(), t1);

    std::ostringstream lines;
    ProgressReporter progress(lines, 0.0);
    TimingReport t2;
    Simulation b(smallLavaMc());
    b.setProgress(&progress);
    const RunSummary sb = b.run(withProgress.string(), t2);

    REQUIRE(sa.steps > 10);
    CHECK(sa.steps == sb.steps);
    CHECK(readBytes(plain / "ca_result.bin") == readBytes(withProgress / "ca_result.bin"));
    CHECK(readBytes(plain / "mc_result.bin") == readBytes(withProgress / "mc_result.bin"));
    CHECK(readBytes(plain / "mc_stats.csv") == readBytes(withProgress / "mc_stats.csv"));

    // Linia na każdy krok (odstęp 0) + wymuszone na początku i końcu etapów.
    std::vector<std::string> ls;
    std::istringstream in(lines.str());
    for (std::string l; std::getline(in, l);) {
        ls.push_back(l);
    }
    REQUIRE(!ls.empty());
    CHECK(ls.front() == "PROGRESS ca 0/5000 active=0");  // przed pierwszym krokiem historia jest pusta
    const std::string caEnd = "PROGRESS ca " + std::to_string(sa.steps) + "/5000 active=";
    bool caEndSeen = false;
    for (const std::string& l : ls) {
        caEndSeen = caEndSeen || l.rfind(caEnd, 0) == 0;
    }
    CHECK(caEndSeen);
    CHECK(std::count(ls.begin(), ls.end(), "PROGRESS mc 0/7") == 1);
    CHECK(std::count(ls.begin(), ls.end(), "PROGRESS mc 7/7") >= 1);
    CHECK(ls.back() == "PROGRESS save 0/1");
}
