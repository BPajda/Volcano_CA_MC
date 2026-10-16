#pragma once
// Benchmark reprezentacji siatki: płaski std::vector vs macierz vector<vector<vector>>.
//
// Dla każdego przypadku ta sama symulacja jest uruchamiana na VectorStorage i na
// MatrixStorage (naprzemiennie, `repeats` razy; wynik = mediana czasu caSim), a wyniki
// obu wersji są porównywane komórka po komórce (type, flowId, temp, solidStep, arrivalStep —
// bitowo).
// Tabela w konsoli ma kolumny tabeli porównawczej (+ kolumna „tryb”), pełne dane
// trafiają do benchmark.csv, a informacje o sprzęcie do benchmark_meta.json.

#include <cstddef>
#include <string>
#include <vector>

#include "app/Cli.hpp"
#include "io/Config.hpp"

namespace volcano {

// Jeden przypadek testowy: etykieta siatki + pełna konfiguracja.
struct BenchmarkCase {
    std::string label;  // np. "10x10x10", "100x100", "200x1x100"
    Config config;
};

// Wiersz tabeli wyników.
struct BenchmarkRow {
    std::string label;
    std::size_t cells = 0;
    int grains = 0;
    int steps = 0;
    double vectorMs = 0.0;   // mediana caSim
    double matrixMs = 0.0;   // mediana caSim
    bool match = false;      // identyczne wyniki obu reprezentacji
    std::string mode;          // kolumna „tryb”: tryb/sąsiedztwo, np. "classic/vn", "lava/moore"
    std::string neighborhood;
    std::string boundary;

    double ratio() const { return vectorMs > 0.0 ? matrixMs / vectorMs : 0.0; }
};

class Benchmark {
public:
    // Przypadki domyślne; quick = bez przypadków >= 1 mln komórek.
    static std::vector<BenchmarkCase> defaultCases(bool quick);

    // Uruchamia jeden przypadek na obu reprezentacjach i porównuje wyniki.
    static BenchmarkRow runCase(const BenchmarkCase& c, int repeats);

    // Tryb --benchmark: wszystkie przypadki, tabela w konsoli, benchmark.csv.
    static int runFromCli(const CliOptions& opt);

    // Nagłówek i wiersz tabeli porównawczej (kolumny jak w tabeli referencyjnej).
    static std::string tableHeader();
    static std::string tableRow(const BenchmarkRow& r);
};

}  // namespace volcano
