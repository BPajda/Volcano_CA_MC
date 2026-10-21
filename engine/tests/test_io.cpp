// Testy zapisu/odczytu wyników i raportu czasów.
#include "doctest.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <limits>

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

namespace {

// Zapis ca_result.txt / mc_result.txt sprzed etapu 8 (k7): strumień w trybie tekstowym, snprintf("%.1f") —
// odniesienie, z którym nowy zapis ma się zgadzać bajt w bajt (także końce wierszy CRLF na Windows).
void writeTxtReference(const std::filesystem::path& path, const Microstructure& m) {
    std::ofstream out(path);
    out << m.dims.nx << ' ' << m.dims.ny << ' ' << m.dims.nz << "\nx y z type flowId temp\n";
    std::size_t i = 0;
    char t[64];
    for (int z = 0; z < m.dims.nz; ++z) {
        for (int y = 0; y < m.dims.ny; ++y) {
            for (int x = 0; x < m.dims.nx; ++x, ++i) {
                std::snprintf(t, sizeof(t), "%.1f", static_cast<double>(m.temp[i]));
                out << x << ' ' << y << ' ' << z << ' ' << static_cast<int>(m.type[i]) << ' ' << m.flowId[i] << ' '
                    << t << '\n';
            }
        }
    }
}

void writeCrystalTxtReference(const std::filesystem::path& path, const CrystalMap& m) {
    std::ofstream out(path);
    out << m.dims.nx << ' ' << m.dims.ny << ' ' << m.dims.nz << "\nx y z crystal\n";
    std::size_t i = 0;
    for (int z = 0; z < m.dims.nz; ++z) {
        for (int y = 0; y < m.dims.ny; ++y) {
            for (int x = 0; x < m.dims.nx; ++x, ++i) {
                out << x << ' ' << y << ' ' << z << ' ' << m.crystal[i] << '\n';
            }
        }
    }
}

std::string fileBytes(const std::filesystem::path& path) {
    std::ifstream in(path, std::ios::binary);
    return std::string(std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>());
}

// Ten sam tekst co printf("%.1f", (double)v) na tej platformie?
bool sameAsPrintf(float v) {
    char ref[64];
    char got[ResultWriter::kTempChars];
    const int n = std::snprintf(ref, sizeof(ref), "%.1f", static_cast<double>(v));
    const std::size_t m = ResultWriter::formatTemp(got, v);
    return std::string(ref, static_cast<std::size_t>(n)) == std::string(got, m);
}

}  // namespace

TEST_CASE("ResultWriter::formatTemp: te same znaki co printf(\"%.1f\") (etap 8, k7)") {
    // Remisy (x,x5 dokładnie w binarnym: .25, .75 — printf zaokrągla do parzystej), wartości ujemne zaokrąglane
    // do zera („-0.0”), −0,0, typowe temperatury lawy, duże wartości i wartości obsługiwane przez snprintf.
    const float special[] = {0.0f,     -0.0f,     0.04f,      -0.04f,    0.05f,      -0.05f,   0.15f,
                             0.25f,    0.35f,     0.75f,      1.25f,     2.25f,      -0.25f,   -1.75f,
                             799.95f,  1199.75f,  1200.0f,    1.0e7f,    123456.75f, 16777215.0f,
                             3.0e7f,   9.9e13f,   1.0e14f,    3.4e38f,   -3.4e38f,   1.0e-30f, -1.0e-30f};
    for (const float v : special) {
        CAPTURE(v);
        CHECK(sameAsPrintf(v));
    }
    CHECK(sameAsPrintf(std::numeric_limits<float>::infinity()));
    CHECK(sameAsPrintf(-std::numeric_limits<float>::infinity()));
    CHECK(sameAsPrintf(std::numeric_limits<float>::quiet_NaN()));
    CHECK(sameAsPrintf(std::numeric_limits<float>::denorm_min()));

    // Siatki wartości z remisami i bez + losowe wzorce bitów (wszystkie rzędy wielkości do ~10^13).
    int bad = 0;
    for (int k = -40000; k <= 40000; ++k) {
        bad += sameAsPrintf(static_cast<float>(k) * 0.01f) ? 0 : 1;
        bad += sameAsPrintf(static_cast<float>(k) * 0.25f) ? 0 : 1;
        bad += sameAsPrintf(static_cast<float>(k) / 8.0f) ? 0 : 1;
        bad += sameAsPrintf(static_cast<float>(k) * 0.05f + 1000.0f) ? 0 : 1;
    }
    std::uint32_t r = 12345u;
    for (int k = 0; k < 200000; ++k) {
        r = r * 1664525u + 1013904223u;  // LCG — deterministycznie
        float v;
        std::memcpy(&v, &r, sizeof(v));
        if (std::isfinite(v) && std::fabs(v) < 1.0e13f) {
            bad += sameAsPrintf(v) ? 0 : 1;
        }
    }
    CHECK(bad == 0);
}

TEST_CASE("ResultWriter: ca_result.txt i mc_result.txt bajt w bajt jak zapis sprzed etapu 8 (k7)") {
    const auto dir = tempDir("io_txt_bytes");
    // Ponad 1 MB tekstu (kilka zapisów bufora), różne długości liczb, temperatury z remisami i ujemne.
    Microstructure m;
    m.resize(Dims{123, 45, 11});
    for (std::size_t i = 0; i < m.type.size(); ++i) {
        m.type[i] = static_cast<CellType>(i % 4);
        m.flowId[i] = static_cast<std::int32_t>(i % 3 == 0 ? i * 7919 : i % 13) - (i % 17 == 0 ? 5 : 0);
        m.temp[i] = static_cast<float>(i % 4801) * 0.25f - 0.75f * static_cast<float>(i % 7) +
                    (i % 29 == 0 ? 0.05f : 0.0f);
    }
    ResultWriter::writeTxt((dir / "ca_result.txt").string(), m);
    writeTxtReference(dir / "ca_ref.txt", m);
    const std::string got = fileBytes(dir / "ca_result.txt");
    CHECK(got.size() > (1u << 20));
    CHECK(got == fileBytes(dir / "ca_ref.txt"));

    CrystalMap c;
    c.dims = Dims{97, 61, 23};
    for (std::size_t i = 0; i < c.dims.cells(); ++i) {
        c.crystal.push_back(static_cast<std::int32_t>(i % 5 == 0 ? 0 : (i * 2654435761u) % 100000));
    }
    ResultWriter::writeCrystalTxt((dir / "mc_result.txt").string(), c);
    writeCrystalTxtReference(dir / "mc_ref.txt", c);
    const std::string gotMc = fileBytes(dir / "mc_result.txt");
    CHECK(gotMc.size() > (1u << 20));
    CHECK(gotMc == fileBytes(dir / "mc_ref.txt"));
}

namespace {

// Pas warstw [k0, k1) osi zewnętrznej (z; w płaszczyźnie x–y — y) jako osobna mikrostruktura (jak pas engine_mpi).
Microstructure slabOf(const Microstructure& m, int k0, int k1) {
    const bool lz = m.dims.nz > 1;
    Dims d = m.dims;
    (lz ? d.nz : d.ny) = k1 - k0;
    Microstructure s;
    s.resize(d);
    const std::size_t plane = lz ? static_cast<std::size_t>(m.dims.nx) * static_cast<std::size_t>(m.dims.ny)
                                 : static_cast<std::size_t>(m.dims.nx);
    const auto from = static_cast<std::ptrdiff_t>(static_cast<std::size_t>(k0) * plane);
    const auto to = static_cast<std::ptrdiff_t>(static_cast<std::size_t>(k1) * plane);
    std::copy(m.type.begin() + from, m.type.begin() + to, s.type.begin());
    std::copy(m.flowId.begin() + from, m.flowId.begin() + to, s.flowId.begin());
    std::copy(m.temp.begin() + from, m.temp.begin() + to, s.temp.begin());
    std::copy(m.solidStep.begin() + from, m.solidStep.begin() + to, s.solidStep.begin());
    std::copy(m.arrivalStep.begin() + from, m.arrivalStep.begin() + to, s.arrivalStep.begin());
    return s;
}

}  // namespace

TEST_CASE("ResultWriter: plik tekstowy i nagłówki z pasów (etap 11, MPI-IO) = zapis całości") {
    const auto dir = tempDir("io_slabs");
    // 3D (pasy w z, także pas jednej warstwy), przekrój x–z (pasy w z) i płaszczyzna x–y (pasy w y).
    for (const Dims d : {Dims{23, 9, 11}, Dims{31, 1, 17}, Dims{37, 41, 1}}) {
        CAPTURE(d.nx);
        Microstructure m;
        m.resize(d);
        CrystalMap c;
        c.dims = d;
        for (std::size_t i = 0; i < m.type.size(); ++i) {
            m.type[i] = static_cast<CellType>(i % 4);
            m.flowId[i] = static_cast<std::int32_t>(i % 3 == 0 ? i * 7919 : i % 13) - (i % 17 == 0 ? 5 : 0);
            m.temp[i] = static_cast<float>(i % 4801) * 0.25f - 0.75f * static_cast<float>(i % 7);
            m.solidStep[i] = static_cast<std::uint16_t>(i % 997);
            m.arrivalStep[i] = static_cast<std::uint16_t>(i % 89);
            c.crystal.push_back(static_cast<std::int32_t>(i % 5 == 0 ? 0 : (i * 2654435761u) % 100000));
        }
        ResultWriter::writeTxt((dir / "ca_result.txt").string(), m);
        ResultWriter::writeBin((dir / "ca_result.bin").string(), m);
        ResultWriter::writeCrystalTxt((dir / "mc_result.txt").string(), c);
        ResultWriter::writeCrystalBin((dir / "mc_result.bin").string(), c);
        const int layers = d.nz > 1 ? d.nz : d.ny;
        const std::vector<int> cuts = {0, 4, 5, layers};  // pasy 4, 1 i reszta warstw
        std::string txt = ResultWriter::txtHeader(d, false);
        std::string crystalTxt = ResultWriter::txtHeader(d, true);
        for (std::size_t k = 0; k + 1 < cuts.size(); ++k) {
            const Microstructure s = slabOf(m, cuts[k], cuts[k + 1]);
            ResultWriter::appendTxtRows(txt, s, d, cuts[k]);
            const std::size_t plane = s.type.size() / static_cast<std::size_t>(cuts[k + 1] - cuts[k]);
            const std::vector<std::int32_t> own(c.crystal.begin() + static_cast<std::ptrdiff_t>(cuts[k] * plane),
                                                c.crystal.begin() + static_cast<std::ptrdiff_t>(cuts[k + 1] * plane));
            ResultWriter::appendCrystalTxtRows(crystalTxt, s.dims, own.data(), d, cuts[k]);
        }
        CHECK(txt == fileBytes(dir / "ca_result.txt"));
        CHECK(crystalTxt == fileBytes(dir / "mc_result.txt"));
        const std::vector<char> h = ResultWriter::binHeader(d);
        CHECK(std::string(h.begin(), h.end()) == fileBytes(dir / "ca_result.bin").substr(0, h.size()));
        const std::vector<char> hc = ResultWriter::crystalBinHeader(d);
        CHECK(std::string(hc.begin(), hc.end()) == fileBytes(dir / "mc_result.bin").substr(0, hc.size()));
        const BinHeader bh = ResultReader::readBinHeader((dir / "ca_result.bin").string());
        CHECK(bh.dims == d);
        CHECK(bh.version == 2);
        CHECK(bh.dataOffset == h.size());
    }
    // Nagłówek wersji 1 i plik obcięty.
    const Microstructure m = sample();
    writeBinV1(dir / "v1.bin", m);
    const BinHeader v1 = ResultReader::readBinHeader((dir / "v1.bin").string());
    CHECK(v1.version == 1);
    CHECK(v1.dims == m.dims);
    const std::string bytes = fileBytes(dir / "v1.bin");
    {
        std::ofstream cut(dir / "cut.bin", std::ios::binary);
        cut.write(bytes.data(), static_cast<std::streamsize>(bytes.size() - 1));
    }
    CHECK_THROWS(ResultReader::readBinHeader((dir / "cut.bin").string()));
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
