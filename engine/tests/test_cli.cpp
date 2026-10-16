// Testy parsera linii poleceń.
#include "doctest.h"

#include "app/Cli.hpp"

using namespace volcano;

TEST_CASE("Cli: konfiguracja, folder wyników i nadpisania") {
    const char* argv[] = {"engine", "--config", "a.json", "--out", "res", "--set", "space.nx=10",
                          "--grid", "matrix"};
    const CliOptions opt = Cli::parse(9, argv);
    CHECK(opt.configPath == "a.json");
    CHECK(opt.outDir == "res");
    REQUIRE(opt.overrides.size() == 2);
    CHECK(opt.overrides[0] == "space.nx=10");
    CHECK(opt.overrides[1] == "grid=matrix");
    CHECK_FALSE(opt.benchmark);
}

TEST_CASE("Cli: benchmark z opcjami") {
    const char* argv[] = {"engine", "--benchmark", "--repeats", "5", "--quick"};
    const CliOptions opt = Cli::parse(5, argv);
    CHECK(opt.benchmark);
    CHECK(opt.quick);
    CHECK(opt.repeats == 5);
}

TEST_CASE("Cli: błędne wywołania dają czytelny błąd") {
    const char* unknown[] = {"engine", "--nx", "5"};
    CHECK_THROWS_AS(Cli::parse(3, unknown), CliError);
    const char* missing[] = {"engine", "--config"};
    CHECK_THROWS_AS(Cli::parse(2, missing), CliError);
    const char* badSet[] = {"engine", "--set", "space.nx"};
    CHECK_THROWS_AS(Cli::parse(3, badSet), CliError);
    const char* badRepeats[] = {"engine", "--benchmark", "--repeats", "zero"};
    CHECK_THROWS_AS(Cli::parse(4, badRepeats), CliError);
}

TEST_CASE("Cli: --mc-from (MC na wyniku CA z pliku)") {
    const char* argv[] = {"engine", "--mc-from", "results/lava", "--config", "mc.json", "--out", "res"};
    const CliOptions opt = Cli::parse(7, argv);
    CHECK(opt.mcFrom == "results/lava");
    CHECK(opt.configPath == "mc.json");
    const char* missing[] = {"engine", "--mc-from"};
    CHECK_THROWS_AS(Cli::parse(2, missing), CliError);
    const char* withBenchmark[] = {"engine", "--benchmark", "--mc-from", "x"};
    CHECK_THROWS_AS(Cli::parse(4, withBenchmark), CliError);
}
