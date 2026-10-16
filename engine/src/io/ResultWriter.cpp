#include "io/ResultWriter.hpp"

#include <charconv>
#include <cstdio>
#include <fstream>
#include <stdexcept>

namespace volcano {

namespace {

// Otwiera plik do zapisu albo zgłasza błąd z nazwą pliku.
std::ofstream openOut(const std::string& path, bool binary) {
    std::ofstream out(path, binary ? std::ios::binary : std::ios::out);
    if (!out) {
        throw std::runtime_error("Nie można utworzyć pliku: " + path);
    }
    return out;
}

// Dopisuje liczbę całkowitą do bufora (to_chars — bez locale i bez alokacji).
void appendInt(std::string& buf, long long v) {
    char tmp[24];
    const auto res = std::to_chars(tmp, tmp + sizeof(tmp), v);
    buf.append(tmp, res.ptr);
}

// Zapisuje tablicę wartości w postaci surowych bajtów.
template <class T>
void writeArray(std::ofstream& out, const std::vector<T>& v) {
    out.write(reinterpret_cast<const char*>(v.data()), static_cast<std::streamsize>(v.size() * sizeof(T)));
}

}  // namespace

void ResultWriter::writeTxt(const std::string& path, const Microstructure& m) {
    std::ofstream out = openOut(path, false);
    const Dims& d = m.dims;
    std::string buf;
    const std::size_t flushAt = 1 << 20;  // ~1 MB
    buf.reserve(flushAt + 256);

    appendInt(buf, d.nx);
    buf += ' ';
    appendInt(buf, d.ny);
    buf += ' ';
    appendInt(buf, d.nz);
    buf += "\nx y z type flowId temp\n";

    std::size_t i = 0;
    char tempText[32];
    for (int z = 0; z < d.nz; ++z) {
        for (int y = 0; y < d.ny; ++y) {
            for (int x = 0; x < d.nx; ++x, ++i) {
                appendInt(buf, x);
                buf += ' ';
                appendInt(buf, y);
                buf += ' ';
                appendInt(buf, z);
                buf += ' ';
                appendInt(buf, static_cast<int>(m.type[i]));
                buf += ' ';
                appendInt(buf, m.flowId[i]);
                buf += ' ';
                const int len = std::snprintf(tempText, sizeof(tempText), "%.1f", static_cast<double>(m.temp[i]));
                buf.append(tempText, static_cast<std::size_t>(len));
                buf += '\n';
                if (buf.size() >= flushAt) {
                    out.write(buf.data(), static_cast<std::streamsize>(buf.size()));
                    buf.clear();
                }
            }
        }
    }
    out.write(buf.data(), static_cast<std::streamsize>(buf.size()));
    if (!out) {
        throw std::runtime_error("Błąd zapisu pliku: " + path);
    }
}

void ResultWriter::writeBin(const std::string& path, const Microstructure& m) {
    std::ofstream out = openOut(path, true);
    const char magic[4] = {'V', 'O', 'L', 'C'};
    const std::uint32_t version = kBinVersion;
    const std::int32_t dims[3] = {m.dims.nx, m.dims.ny, m.dims.nz};
    out.write(magic, 4);
    out.write(reinterpret_cast<const char*>(&version), sizeof(version));
    out.write(reinterpret_cast<const char*>(dims), sizeof(dims));
    writeArray(out, m.type);
    writeArray(out, m.flowId);
    writeArray(out, m.temp);
    writeArray(out, m.solidStep);
    writeArray(out, m.arrivalStep);
    if (!out) {
        throw std::runtime_error("Błąd zapisu pliku: " + path);
    }
}

void ResultWriter::writeCrystalTxt(const std::string& path, const CrystalMap& m) {
    std::ofstream out = openOut(path, false);
    const Dims& d = m.dims;
    std::string buf;
    const std::size_t flushAt = 1 << 20;  // ~1 MB
    buf.reserve(flushAt + 64);

    appendInt(buf, d.nx);
    buf += ' ';
    appendInt(buf, d.ny);
    buf += ' ';
    appendInt(buf, d.nz);
    buf += "\nx y z crystal\n";

    std::size_t i = 0;
    for (int z = 0; z < d.nz; ++z) {
        for (int y = 0; y < d.ny; ++y) {
            for (int x = 0; x < d.nx; ++x, ++i) {
                appendInt(buf, x);
                buf += ' ';
                appendInt(buf, y);
                buf += ' ';
                appendInt(buf, z);
                buf += ' ';
                appendInt(buf, m.crystal[i]);
                buf += '\n';
                if (buf.size() >= flushAt) {
                    out.write(buf.data(), static_cast<std::streamsize>(buf.size()));
                    buf.clear();
                }
            }
        }
    }
    out.write(buf.data(), static_cast<std::streamsize>(buf.size()));
    if (!out) {
        throw std::runtime_error("Błąd zapisu pliku: " + path);
    }
}

void ResultWriter::writeCrystalBin(const std::string& path, const CrystalMap& m) {
    std::ofstream out = openOut(path, true);
    const char magic[4] = {'V', 'M', 'C', '1'};
    const std::int32_t dims[3] = {m.dims.nx, m.dims.ny, m.dims.nz};
    out.write(magic, 4);
    out.write(reinterpret_cast<const char*>(dims), sizeof(dims));
    writeArray(out, m.crystal);
    if (!out) {
        throw std::runtime_error("Błąd zapisu pliku: " + path);
    }
}

void ResultWriter::writeMcStatsCsv(const std::string& path, const std::vector<McStats>& history) {
    std::ofstream out = openOut(path, false);
    out << "mcs,grains,meanGrainSize,energy,acceptRate\n";
    char line[160];
    for (const McStats& s : history) {
        std::snprintf(line, sizeof(line), "%d,%llu,%.4f,%.3f,%.6f\n", s.mcs,
                      static_cast<unsigned long long>(s.grains), s.meanGrainSize, s.energy, s.acceptRate);
        out << line;
    }
    if (!out) {
        throw std::runtime_error("Błąd zapisu pliku: " + path);
    }
}

void ResultWriter::writeJson(const std::string& path, const nlohmann::ordered_json& j) {
    std::ofstream out = openOut(path, false);
    out << j.dump(2) << '\n';
    if (!out) {
        throw std::runtime_error("Błąd zapisu pliku: " + path);
    }
}

}  // namespace volcano
