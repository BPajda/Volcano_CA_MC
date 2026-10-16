#pragma once
// Wczytanie mapy wysokości terenu z pliku CSV (terrain.type = "file").
//
// Format: ny wierszy x nx kolumn; wiersz nr k to y = k, kolumna nr i to x = i.
// Wartość = wysokość terenu w komórkach (może być ułamkowa — skała to z < h).
// Separatory: przecinek, średnik, spacja lub tabulator. Wiersze puste i zaczynające
// się od '#' są pomijane.

#include <string>

#include "core/Types.hpp"
#include "terrain/TerrainGenerator.hpp"

namespace volcano {

class HeightmapLoader {
public:
    // Wczytuje mapę i sprawdza zgodność z wymiarami d. Rzuca ConfigError z numerem
    // wiersza/kolumny przy błędach formatu.
    static Heightmap loadCsv(const std::string& path, const Dims& d);
};

}  // namespace volcano
