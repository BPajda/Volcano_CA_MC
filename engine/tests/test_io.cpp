// Testy zapisu/odczytu wyników i raportu czasów.
#include "doctest.h"

#include <filesystem>
#include <fstream>

#include "io/ResultReader.hpp"
#include "io/ResultWriter.hpp"
#include "io/TimingReport.hpp"

using namespace volcano;

namespace {

std::filesystem::path tempDir(const std::string& name) {
    const auto dir = std::filesystem::temp_directory_path() / "volcano_tests" / name;
    std::filesystem::remove_all(dir);
    std::filesystem::create_directories(dir);
    return dir;
}

// Mikrostruktura z różnymi wartościami (temperatury z krokiem 0.5 — dokładne w txt).
Microstructure sample() {
    Microstructure m;
    m.resize(Dims{7, 3, 5});
    for (std::size_t i = 0; i < m.type.size(); ++i) {
        m.type[i] = static_cast<CellType>(i % 4);
        m.flowId[i] = static_cast<std::int32_t>(i % 11);
        m.temp[i] = 0.5f * static_cast<float>(i);
        m.solidStep[i] = static_cast<std::uint16_t>(i * 3);
        m.arrivalStep[i] = static_cast<std::uint16_t>(i);
    }
    return m;
}

// Zapisuje plik ca_result.bin w starym formacie (wersja 1: bez arrivalStep).
void writeBinV1(const std::filesystem::path& path, const Microstructure& m) {
    std::ofstream out(path, std::ios::binary);
    const std::uint32_t version = 1;
    const std::int32_t dims[3] = {m.dims.nx, m.dims.ny, m.dims.nz};
    out.write("VOLC", 4);
    out.write(reinterpret_cast<const char*>(&version), sizeof(version));
    out.write(reinterpret_cast<const char*>(dims), sizeof(dims));
    out.write(reinterpret_cast<const char*>(m.type.data()), static_cast<std::streamsize>(m.type.size()));
    out.write(reinterpret_cast<const char*>(m.flowId.data()), static_cast<std::streamsize>(m.flowId.size() * 4));
    out.write(reinterpret_cast<const char*>(m.temp.data()), static_cast<std::streamsize>(m.temp.size() * 4));
    out.write(reinterpret_cast<const char*>(m.solidStep.data()), static_cast<std::streamsize>(m.solidStep.size() * 2));
}

}  // namespace

TEST_CASE("ResultWriter/Reader: txt — zapis i odczyt dają te same dane") {
    const auto dir = tempDir("io_txt");
    const Microstructure m = sample();
    ResultWriter::writeTxt((dir / "ca_result.txt").string(), m);
    ResultSource src;
    const Microstructure r = ResultReader::readFolder(dir.string(), &src);
    CHECK((r.dims == m.dims));
    CHECK(r.type == m.type);
    CHECK(r.flowId == m.flowId);
    CHECK(r.temp == m.temp);
    CHECK(src.format == "txt");
    CHECK_FALSE(src.hasSolidStep);  // txt nie zawiera pól czasu
    CHECK_FALSE(src.hasArrivalStep);

    std::ifstream in(dir / "ca_result.txt");
    std::string l1;
    std::string l2;
    std::string l3;
    std::getline(in, l1);
    std::getline(in, l2);
    std::getline(in, l3);
    CHECK(l1 == "7 3 5");
    CHECK(l2 == "x y z type flowId temp");
    CHECK(l3 == "0 0 0 0 0 0.0");
}

TEST_CASE("ResultWriter/Reader: bin v2 — pełne dane łącznie z solidStep i arrivalStep") {
    const auto dir = tempDir("io_bin");
    const Microstructure m = sample();
    ResultWriter::writeBin((dir / "ca_result.bin").string(), m);
    ResultSource src;
    const Microstructure r = ResultReader::readFolder(dir.string(), &src);
    CHECK((r.dims == m.dims));
    CHECK(r.type == m.type);
    CHECK(r.flowId == m.flowId);
    CHECK(r.temp == m.temp);
    CHECK(r.solidStep == m.solidStep);
    CHECK(r.arrivalStep == m.arrivalStep);
    CHECK(src.format == "bin");
    CHECK(src.version == 2);
    CHECK(src.hasSolidStep);
    CHECK(src.hasArrivalStep);
    // nagłówek 20 B + N * (1 + 4 + 4 + 2 + 2)
    CHECK(std::filesystem::file_size(dir / "ca_result.bin") == 20 + m.type.size() * 13);

    std::ofstream(dir / "zly.bin", std::ios::binary) << "XXXX1234";
    CHECK_THROWS(ResultReader::readBin((dir / "zly.bin").string()));
}

TEST_CASE("ResultReader: bin v1 (bez arrivalStep) — czytany, arrivalStep = 0") {
    const auto dir = tempDir("io_bin_v1");
    const Microstructure m = sample();
    writeBinV1(dir / "ca_result.bin", m);
    CHECK(std::filesystem::file_size(dir / "ca_result.bin") == 20 + m.type.size() * 11);
    ResultSource src;
    const Microstructure r = ResultReader::readFolder(dir.string(), &src);
    CHECK(src.version == 1);
    CHECK(src.hasSolidStep);
    CHECK_FALSE(src.hasArrivalStep);
    CHECK(r.type == m.type);
    CHECK(r.flowId == m.flowId);
    CHECK(r.temp == m.temp);
    CHECK(r.solidStep == m.solidStep);
    CHECK(r.arrivalStep == std::vector<std::uint16_t>(m.type.size(), 0));

    // Nieznana (przyszła) wersja jest odrzucana.
    Microstructure bad = m;
    writeBinV1(dir / "v9.bin", bad);
    {
        std::fstream f(dir / "v9.bin", std::ios::in | std::ios::out | std::ios::binary);
        const std::uint32_t v9 = 9;
        f.seekp(4);
        f.write(reinterpret_cast<const char*>(&v9), sizeof(v9));
    }
    CHECK_THROWS(ResultReader::readBin((dir / "v9.bin").string()));
}

TEST_CASE("ResultWriter/Reader: mapa kryształów MC (txt i bin)") {
    const auto dir = tempDir("io_mc");
    CrystalMap m;
    m.dims = Dims{6, 1, 4};
    for (std::size_t i = 0; i < m.dims.cells(); ++i) {
        m.crystal.push_back(static_cast<std::int32_t>(i % 5));  // 0 = poza domeną
    }
    ResultWriter::writeCrystalTxt((dir / "mc_result.txt").string(), m);
    const CrystalMap t = ResultReader::readCrystalFolder(dir.string());
    CHECK((t.dims == m.dims));
    CHECK(t.crystal == m.crystal);
    std::ifstream in(dir / "mc_result.txt");
    std::string l1;
    std::string l2;
    std::getline(in, l1);
    std::getline(in, l2);
    CHECK(l1 == "6 1 4");
    CHECK(l2 == "x y z crystal");

    ResultWriter::writeCrystalBin((dir / "mc_result.bin").string(), m);
    CHECK(std::filesystem::file_size(dir / "mc_result.bin") == 16 + m.crystal.size() * 4);
    const CrystalMap b = ResultReader::readCrystalFolder(dir.string());  // bin ma pierwszeństwo
    CHECK(b.crystal == m.crystal);

    std::vector<McStats> h(2);
    h[1].mcs = 10;
    h[1].grains = 7;
    h[1].meanGrainSize = 3.5;
    ResultWriter::writeMcStatsCsv((dir / "mc_stats.csv").string(), h);
    std::ifstream csv(dir / "mc_stats.csv");
    std::string head;
    std::string row0;
    std::string row1;
    std::getline(csv, head);
    std::getline(csv, row0);
    std::getline(csv, row1);
    CHECK(head == "mcs,grains,meanGrainSize,energy,acceptRate");
    CHECK(row1.rfind("10,7,3.5000,", 0) == 0);
}

TEST_CASE("TimingReport: sekcje sumują się, JSON zawiera czasy i informacje") {
    TimingReport t;
    t.add("caSim", 1.5);
    t.add("save", 2.0);
    t.add("caSim", 0.5);
    t.setInfo("steps", 12);
    CHECK(t.get("caSim") == doctest::Approx(2.0));
    CHECK(t.get("brak") == 0.0);
    const auto j = t.toJson();
    CHECK(j["unit"] == "ms");
    CHECK(j["caSim"].get<double>() == doctest::Approx(2.0));
    CHECK(j["steps"] == 12);
    CHECK_FALSE(TimingReport::cpuName().empty());
}
