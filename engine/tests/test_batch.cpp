// Testy serii --batch (etap 5): wybór configów z folderu, podsumowanie batch_summary.csv
// z przebiegiem poprawnym i błędnym (także z prawdziwym programem engine jako procesem potomnym),
// przekazanie wspólnych opcji (--set) do przebiegów i cytowanie argumentów w Windows.
#include "doctest.h"

#include <filesystem>
#include <fstream>
#include <iterator>
#include <sstream>
#include <string>
#include <vector>

#include "app/Batch.hpp"
#include "app/Cli.hpp"
#include "core/ChildProcess.hpp"
#include "json.hpp"

using namespace volcano;
namespace fs = std::filesystem;

namespace {

// Pusty folder tymczasowy (nazwa w UTF-8 — u8path, żeby polskie litery działały też w MSVC).
fs::path tempDir(const std::string& utf8Name) {
    const fs::path dir = fs::temp_directory_path() / "volcano_tests" / fs::u8path(utf8Name);
    fs::remove_all(dir);
    fs::create_directories(dir);
    return dir;
}

void writeText(const fs::path& p, const std::string& text) {
    std::ofstream out(p, std::ios::binary);
    out << text;
}

std::string readText(const fs::path& p) {
    std::ifstream in(p, std::ios::binary);
    return std::string(std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>());
}

// Prosty parser CSV (pola w cudzysłowie z podwojonym cudzysłowem) — wiersze jako listy pól.
std::vector<std::vector<std::string>> readCsv(const fs::path& p) {
    std::vector<std::vector<std::string>> rows;
    std::istringstream in(readText(p));
    std::string line;
    while (std::getline(in, line)) {
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();  // Windows: plik tekstowy z końcami linii CRLF
        }
        std::vector<std::string> row;
        std::string cur;
        bool quoted = false;
        for (std::size_t i = 0; i < line.size(); ++i) {
            const char c = line[i];
            if (quoted) {
                if (c == '"' && i + 1 < line.size() && line[i + 1] == '"') {
                    cur += '"';
                    ++i;
                } else if (c == '"') {
                    quoted = false;
                } else {
                    cur += c;
                }
            } else if (c == '"') {
                quoted = true;
            } else if (c == ',') {
                row.push_back(cur);
                cur.clear();
            } else {
                cur += c;
            }
        }
        row.push_back(cur);
        rows.push_back(row);
    }
    return rows;
}

// Wartość kolumny col w wierszu row (nagłówek = rows[0]).
std::string cell(const std::vector<std::vector<std::string>>& rows, std::size_t row, const std::string& col) {
    for (std::size_t i = 0; i < rows[0].size(); ++i) {
        if (rows[0][i] == col) {
            return i < rows[row].size() ? rows[row][i] : std::string("<brak pola>");
        }
    }
    return "<brak kolumny " + col + ">";
}

}  // namespace

TEST_CASE("Cli: --batch i niedozwolone połączenia") {
    const char* ok[] = {"engine", "--batch", "seria", "--out", "wyniki", "--set", "rngSeed=7", "--progress"};
    const CliOptions opt = Cli::parse(8, ok);
    CHECK(opt.batchDir == "seria");
    CHECK(opt.outDir == "wyniki");
    CHECK(opt.progress);
    REQUIRE(opt.overrides.size() == 1);

    const char* withConfig[] = {"engine", "--batch", "seria", "--config", "a.json"};
    CHECK_THROWS_AS(Cli::parse(5, withConfig), CliError);
    const char* withMcFrom[] = {"engine", "--batch", "seria", "--mc-from", "r"};
    CHECK_THROWS_AS(Cli::parse(5, withMcFrom), CliError);
    const char* withBenchmark[] = {"engine", "--batch", "seria", "--benchmark"};
    CHECK_THROWS_AS(Cli::parse(4, withBenchmark), CliError);
    const char* withValidate[] = {"engine", "--batch", "seria", "--validate"};
    CHECK_THROWS_AS(Cli::parse(4, withValidate), CliError);
    const char* missing[] = {"engine", "--batch"};
    CHECK_THROWS_AS(Cli::parse(2, missing), CliError);
}

TEST_CASE("BatchRunner::collect: kolejność nazw, pomija series.json, _*.json i inne pliki") {
    const fs::path dir = tempDir("batch_collect");
    for (const char* name : {"b_druga.json", "a_pierwsza.JSON", "series.json", "_notatki.json", "opis.txt"}) {
        writeText(dir / name, "{}");
    }
    fs::create_directories(dir / "podfolder");
    writeText(dir / "podfolder" / "x.json", "{}");

    const std::vector<BatchItem> items = BatchRunner::collect(dir, dir / "out");
    REQUIRE(items.size() == 2);
    CHECK(items[0].name == "a_pierwsza");
    CHECK(items[1].name == "b_druga");
    CHECK(items[0].outDir == dir / "out" / "a_pierwsza");
    CHECK(items[1].config == dir / "b_druga.json");
}

TEST_CASE("BatchRunner: podsumowanie z poprawnym i błędnym przebiegiem (funkcja testowa zamiast procesu)") {
    const fs::path dir = tempDir("batch_fake");
    writeText(dir / "01_ok.json", "{}");
    writeText(dir / "02_zly.json", "{}");
    writeText(dir / "03_ok.json", "{}");
    const std::vector<BatchItem> items = BatchRunner::collect(dir, dir / "out");

    // Udany przebieg zostawia times.json i config_used.json; błędny — komunikat w logu i kod 1.
    std::vector<std::string> calls;
    const BatchRunner::Runner fake = [&calls](const BatchItem& item, const fs::path& log) {
        calls.push_back(item.name);
        ChildResult r;
        r.started = true;
        if (item.name == "02_zly") {
            std::ofstream(log, std::ios::app) << "Ostrzeżenie: coś\nBłąd konfiguracji: Parametr „neighborhood” zły\n";
            r.exitCode = 1;
            return r;
        }
        writeText(item.outDir / "times.json",
                  R"({"unit":"ms","readConfig":0.3,"caSim":12.5,"total":20.25,"steps":17,"cells":400,)"
                  R"("space":[20,20,1],"neighborhood":"von_neumann","boundary":"periodic","mode":"classic",)"
                  R"("memory":{"peakRssBytes":5000000,"model":{"peakBytes":12345}},)"
                  R"("files":{"ca_result.bin":{"bytes":5220,"writeMs":0.1},"stats.json":{"bytes":80,"writeMs":0.1}}})");
        writeText(item.outDir / "config_used.json", R"({"vents":{"count":4}})");
        r.exitCode = 0;
        return r;
    };
    std::ostringstream console;
    const std::vector<BatchOutcome> outcomes = BatchRunner::run(items, fake, dir / "out" / "batch_summary.csv", console);

    // Błąd drugiego przebiegu nie przerwał serii; kolejność = kolejność nazw.
    CHECK(calls == std::vector<std::string>{"01_ok", "02_zly", "03_ok"});
    REQUIRE(outcomes.size() == 3);
    CHECK(outcomes[0].ok());
    CHECK_FALSE(outcomes[1].ok());
    CHECK(outcomes[1].error.find("neighborhood") != std::string::npos);
    CHECK(outcomes[2].ok());
    CHECK(fs::is_regular_file(dir / "out" / "02_zly" / "engine.log"));
    CHECK(readText(dir / "out" / "02_zly" / "engine.log").find("# koniec: kod wyjścia 1") != std::string::npos);

    const auto rows = readCsv(dir / "out" / "batch_summary.csv");
    REQUIRE(rows.size() == 4);
    CHECK(rows[0] == BatchRunner::summaryColumns());
    CHECK(cell(rows, 1, "status") == "ok");
    CHECK(cell(rows, 1, "caSim") == "12.5");
    CHECK(cell(rows, 1, "steps") == "17");
    CHECK(cell(rows, 1, "seeds") == "4");
    CHECK(cell(rows, 1, "nx") == "20");
    CHECK(cell(rows, 1, "peakRssBytes") == "5000000");
    CHECK(cell(rows, 1, "modelPeakBytes") == "12345");
    CHECK(cell(rows, 1, "caResultBinBytes") == "5220");
    CHECK(cell(rows, 1, "outputBytes") == "5300");
    CHECK(cell(rows, 1, "mcSim").empty());  // sekcji nie było
    CHECK(cell(rows, 2, "status") == "error");
    CHECK(cell(rows, 2, "exitCode") == "1");
    CHECK(cell(rows, 2, "error").find("Błąd konfiguracji") == 0);
    CHECK(cell(rows, 2, "caSim").empty());
    CHECK(console.str().find("BŁĄD") != std::string::npos);
    CHECK(BatchRunner::describe(outcomes).find("Razem: 3 przebiegi: 2 ok, 1 z błędem") != std::string::npos);
}

TEST_CASE("engine --batch: prawdziwy program — poprawny i błędny config, wspólne --set, ścieżka ze spacją") {
    const fs::path exe = fs::u8path(VOLCANO_ENGINE_EXE);
    REQUIRE(fs::is_regular_file(exe));
    const fs::path dir = tempDir("batch real ąść");  // spacja i polskie litery w ścieżce
    writeText(dir / "01_classic.json",
              R"({"space":{"nx":30,"ny":30,"nz":1},"ca":{"mode":"classic"},"vents":{"count":4},)"
              R"("boundary":"periodic","neighborhood":"von_neumann","output":{"format":"bin"}})");
    writeText(dir / "02_zly.json", R"({"neighborhood":"octagonal"})");
    writeText(dir / "03_mc.json",
              R"({"space":{"nx":20,"ny":20,"nz":1},"mc":{"enabled":true,"domain":"full","mcs":3,)"
              R"("mobilityFromCooling":false},"output":{"format":"bin"}})");
    writeText(dir / "series.json", R"({"opis":"opis serii — nie config"})");
    const fs::path out = dir / "wyniki serii";
    const std::vector<BatchItem> items = BatchRunner::collect(dir, out);
    REQUIRE(items.size() == 3);

    std::ostringstream console;
    const std::vector<BatchOutcome> outcomes =
        BatchRunner::run(items, BatchRunner::processRunner(exe, {"--set", "rngSeed=7"}), out / "batch_summary.csv",
                         console);
    REQUIRE(outcomes.size() == 3);
    CHECK(outcomes[0].ok());
    CHECK_FALSE(outcomes[1].ok());
    CHECK(outcomes[1].exitCode == 1);
    CHECK(outcomes[1].error.find("neighborhood") != std::string::npos);
    CHECK(outcomes[2].ok());

    // Wyniki w osobnych podfolderach, log z wyjściem programu, wspólne --set dotarło do przebiegu.
    CHECK(fs::is_regular_file(out / "01_classic" / "ca_result.bin"));
    CHECK(fs::is_regular_file(out / "03_mc" / "mc_result.bin"));
    CHECK(readText(out / "01_classic" / "engine.log").find("Symulacja zakończona") != std::string::npos);
    const auto used = nlohmann::json::parse(readText(out / "01_classic" / "config_used.json"));
    CHECK(used["rngSeed"] == 7);

    const auto rows = readCsv(out / "batch_summary.csv");
    REQUIRE(rows.size() == 4);
    CHECK(cell(rows, 1, "status") == "ok");
    CHECK(cell(rows, 1, "mode") == "classic");
    CHECK_FALSE(cell(rows, 1, "steps").empty());
    CHECK_FALSE(cell(rows, 1, "caSim").empty());
    CHECK_FALSE(cell(rows, 1, "peakRssBytes").empty());
    CHECK(cell(rows, 1, "caResultBinBytes") == std::to_string(20 + 13 * 30 * 30));
    CHECK(cell(rows, 2, "status") == "error");
    CHECK(cell(rows, 3, "mode") == "mc_full");
    CHECK(cell(rows, 3, "mcs") == "3");
    CHECK(cell(rows, 3, "mcResultBinBytes") == std::to_string(16 + 4 * 20 * 20));
    CHECK(cell(rows, 3, "seeds").empty());  // MC full — bez zarodków CA
}

#ifdef _WIN32
TEST_CASE("ChildProcess::quoteArg: cytowanie zgodne z CommandLineToArgvW") {
    CHECK(ChildProcess::quoteArg(L"abc") == L"abc");
    CHECK(ChildProcess::quoteArg(L"a\\b\\c") == L"a\\b\\c");  // bez spacji — bez zmian
    CHECK(ChildProcess::quoteArg(L"") == L"\"\"");
    CHECK(ChildProcess::quoteArg(L"a b") == L"\"a b\"");
    // Ukośnik na końcu argumentu w cudzysłowie musi być podwojony, inaczej „zjadłby” cudzysłów.
    CHECK(ChildProcess::quoteArg(L"C:\\Program Files\\x\\") == L"\"C:\\Program Files\\x\\\\\"");
    CHECK(ChildProcess::quoteArg(L"say \"hi\"") == L"\"say \\\"hi\\\"\"");
    CHECK(ChildProcess::quoteArg(L"a\\\"b c") == L"\"a\\\\\\\"b c\"");
}
#endif
