#include "terrain/HeightmapLoader.hpp"

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <vector>

#include "io/Config.hpp"

namespace volcano {

namespace {

// Dzieli wiersz CSV na pola (separatory: , ; spacja tabulator).
std::vector<std::string> splitFields(const std::string& line) {
    std::vector<std::string> out;
    std::string cur;
    for (char ch : line) {
        if (ch == ',' || ch == ';' || ch == ' ' || ch == '\t' || ch == '\r') {
            if (!cur.empty()) {
                out.push_back(cur);
                cur.clear();
            }
        } else {
            cur += ch;
        }
    }
    if (!cur.empty()) {
        out.push_back(cur);
    }
    return out;
}

}  // namespace

Heightmap HeightmapLoader::loadCsv(const std::string& path, const Dims& d) {
    std::ifstream in(path);
    if (!in) {
        throw ConfigError("Nie można otworzyć pliku mapy wysokości: " + path);
    }
    Heightmap hm;
    hm.nx = d.nx;
    hm.ny = d.ny;
    hm.height.reserve(static_cast<std::size_t>(d.nx) * static_cast<std::size_t>(d.ny));

    std::string line;
    int lineNo = 0;
    int row = 0;
    while (std::getline(in, line)) {
        ++lineNo;
        const std::vector<std::string> fields = splitFields(line);
        if (fields.empty() || fields[0][0] == '#') {
            continue;
        }
        if (row >= d.ny) {
            throw ConfigError("Mapa wysokości " + path + " ma więcej wierszy danych niż ny = " +
                              std::to_string(d.ny));
        }
        if (static_cast<int>(fields.size()) != d.nx) {
            throw ConfigError("Mapa wysokości " + path + ", wiersz " + std::to_string(lineNo) + ": " +
                              std::to_string(fields.size()) + " wartości, oczekiwano nx = " +
                              std::to_string(d.nx));
        }
        for (std::size_t col = 0; col < fields.size(); ++col) {
            char* end = nullptr;
            const double h = std::strtod(fields[col].c_str(), &end);
            if (end == fields[col].c_str() || *end != '\0' || !std::isfinite(h) || h < 0.0) {
                throw ConfigError("Mapa wysokości " + path + ", wiersz " + std::to_string(lineNo) +
                                  ", kolumna " + std::to_string(col + 1) +
                                  ": oczekiwano nieujemnej liczby, jest \"" + fields[col] + "\"");
            }
            // Skała to z < h -> ceil(h) komórek, przycięte do wysokości przestrzeni.
            hm.height.push_back(std::min(static_cast<int>(std::ceil(h)), d.nz));
        }
        ++row;
    }
    if (row != d.ny) {
        throw ConfigError("Mapa wysokości " + path + " ma " + std::to_string(row) +
                          " wierszy danych, oczekiwano ny = " + std::to_string(d.ny));
    }
    return hm;
}

}  // namespace volcano
