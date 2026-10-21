#include "io/ResultReader.hpp"

#include <cstring>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <stdexcept>

#include "io/ResultWriter.hpp"

namespace volcano {

namespace {

// Wczytuje tablicę surowych wartości z pliku binarnego.
template <class T>
void readArray(std::ifstream& in, std::vector<T>& v, const std::string& path) {
    in.read(reinterpret_cast<char*>(v.data()), static_cast<std::streamsize>(v.size() * sizeof(T)));
    if (!in) {
        throw std::runtime_error("Plik " + path + " jest obcięty (za mało danych)");
    }
}

// Otwiera plik tekstowy i czyta nagłówek wymiarów (linia 1) oraz nazwy kolumn (linia 2).
Dims readTxtHeader(std::ifstream& in, const std::string& path) {
    if (!in) {
        throw std::runtime_error("Nie można otworzyć pliku: " + path);
    }
    Dims d;
    if (!(in >> d.nx >> d.ny >> d.nz) || d.nx < 1 || d.ny < 1 || d.nz < 1) {
        throw std::runtime_error("Plik " + path + ": nieprawidłowy nagłówek wymiarów");
    }
    std::string header;
    std::getline(in, header);  // koniec linii wymiarów
    std::getline(in, header);  // nazwy kolumn
    return d;
}

// Sprawdza, czy współrzędne z wiersza n leżą w przestrzeni.
void checkCoords(const Dims& d, int x, int y, int z, std::size_t n, const std::string& path) {
    if (x < 0 || x >= d.nx || y < 0 || y >= d.ny || z < 0 || z >= d.nz) {
        throw std::runtime_error("Plik " + path + ": współrzędne poza przestrzenią w wierszu " +
                                 std::to_string(n + 3));
    }
}

}  // namespace

Microstructure ResultReader::readTxt(const std::string& path) {
    std::ifstream in(path);
    const Dims d = readTxtHeader(in, path);
    Microstructure m;
    m.resize(d);
    for (std::size_t n = 0; n < d.cells(); ++n) {
        int x = 0;
        int y = 0;
        int z = 0;
        int type = 0;
        std::int32_t flow = 0;
        float temp = 0.0f;
        if (!(in >> x >> y >> z >> type >> flow >> temp)) {
            throw std::runtime_error("Plik " + path + ": za mało wierszy danych (wczytano " +
                                     std::to_string(n) + " z " + std::to_string(d.cells()) + ")");
        }
        checkCoords(d, x, y, z, n, path);
        const std::size_t i = m.index(x, y, z);
        m.type[i] = static_cast<CellType>(type);
        m.flowId[i] = flow;
        m.temp[i] = temp;
    }
    return m;
}

namespace {

// Nagłówek ca_result.bin z otwartego pliku: magic, wersja, wymiary (sprawdzone).
BinHeader readVolcHeader(std::ifstream& in, const std::string& path) {
    char magic[4] = {};
    std::uint32_t version = 0;
    std::int32_t dims[3] = {};
    in.read(magic, 4);
    in.read(reinterpret_cast<char*>(&version), sizeof(version));
    in.read(reinterpret_cast<char*>(dims), sizeof(dims));
    if (!in || std::memcmp(magic, "VOLC", 4) != 0) {
        throw std::runtime_error("Plik " + path + " nie jest plikiem wyników VOLC");
    }
    if (version < 1 || version > ResultWriter::kBinVersion) {
        throw std::runtime_error("Plik " + path + ": nieobsługiwana wersja formatu " + std::to_string(version));
    }
    if (dims[0] < 1 || dims[1] < 1 || dims[2] < 1) {
        throw std::runtime_error("Plik " + path + ": nieprawidłowe wymiary");
    }
    BinHeader h;
    h.dims = Dims{dims[0], dims[1], dims[2]};
    h.version = version;
    h.dataOffset = sizeof(magic) + sizeof(version) + sizeof(dims);
    return h;
}

}  // namespace

BinHeader ResultReader::readBinHeader(const std::string& path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) {
        throw std::runtime_error("Nie można otworzyć pliku: " + path);
    }
    const BinHeader h = readVolcHeader(in, path);
    // Tablice: type (1 B), flowId (4), temp (4), solidStep (2), arrivalStep (2, od wersji 2) na komórkę.
    const std::uint64_t perCell = h.version >= 2 ? 13 : 11;
    const std::uint64_t need = h.dataOffset + perCell * static_cast<std::uint64_t>(h.dims.cells());
    in.seekg(0, std::ios::end);
    const std::streamoff size = in.tellg();
    if (size < 0 || static_cast<std::uint64_t>(size) < need) {
        throw std::runtime_error("Plik " + path + " jest obcięty (za mało danych)");
    }
    return h;
}

Microstructure ResultReader::readBin(const std::string& path, std::uint32_t* versionOut) {
    std::ifstream in(path, std::ios::binary);
    if (!in) {
        throw std::runtime_error("Nie można otworzyć pliku: " + path);
    }
    const BinHeader h = readVolcHeader(in, path);
    const std::uint32_t version = h.version;
    Microstructure m;
    m.resize(h.dims);
    readArray(in, m.type, path);
    readArray(in, m.flowId, path);
    readArray(in, m.temp, path);
    readArray(in, m.solidStep, path);
    if (version >= 2) {
        readArray(in, m.arrivalStep, path);  // w wersji 1 zostaje 0 (resize)
    }
    if (versionOut != nullptr) {
        *versionOut = version;
    }
    return m;
}

Microstructure ResultReader::readFolder(const std::string& folder, ResultSource* source) {
    const std::filesystem::path dir(folder);
    ResultSource info;
    Microstructure m;
    if (std::filesystem::exists(dir / "ca_result.bin")) {
        info.path = (dir / "ca_result.bin").string();
        info.format = "bin";
        m = readBin(info.path, &info.version);
        info.hasSolidStep = true;
        info.hasArrivalStep = info.version >= 2;
    } else {
        info.path = (dir / "ca_result.txt").string();
        info.format = "txt";
        m = readTxt(info.path);
    }
    if (source != nullptr) {
        *source = info;
    }
    return m;
}

CrystalMap ResultReader::readCrystalBin(const std::string& path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) {
        throw std::runtime_error("Nie można otworzyć pliku: " + path);
    }
    char magic[4] = {};
    std::int32_t dims[3] = {};
    in.read(magic, 4);
    in.read(reinterpret_cast<char*>(dims), sizeof(dims));
    if (!in || std::memcmp(magic, "VMC1", 4) != 0) {
        throw std::runtime_error("Plik " + path + " nie jest plikiem kryształów VMC1");
    }
    if (dims[0] < 1 || dims[1] < 1 || dims[2] < 1) {
        throw std::runtime_error("Plik " + path + ": nieprawidłowe wymiary");
    }
    CrystalMap m;
    m.dims = Dims{dims[0], dims[1], dims[2]};
    m.crystal.assign(m.dims.cells(), 0);
    readArray(in, m.crystal, path);
    return m;
}

CrystalMap ResultReader::readCrystalTxt(const std::string& path) {
    std::ifstream in(path);
    CrystalMap m;
    m.dims = readTxtHeader(in, path);
    m.crystal.assign(m.dims.cells(), 0);
    for (std::size_t n = 0; n < m.dims.cells(); ++n) {
        int x = 0;
        int y = 0;
        int z = 0;
        std::int32_t c = 0;
        if (!(in >> x >> y >> z >> c)) {
            throw std::runtime_error("Plik " + path + ": za mało wierszy danych (wczytano " +
                                     std::to_string(n) + " z " + std::to_string(m.dims.cells()) + ")");
        }
        checkCoords(m.dims, x, y, z, n, path);
        m.crystal[static_cast<std::size_t>(globalIndex(m.dims, x, y, z))] = c;
    }
    return m;
}

CrystalMap ResultReader::readCrystalFolder(const std::string& folder) {
    const std::filesystem::path dir(folder);
    if (std::filesystem::exists(dir / "mc_result.bin")) {
        return readCrystalBin((dir / "mc_result.bin").string());
    }
    return readCrystalTxt((dir / "mc_result.txt").string());
}

}  // namespace volcano
