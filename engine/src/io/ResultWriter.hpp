#pragma once
// Zapis wyników symulacji („mikrostruktura końcowa”).
//
// ca_result.txt — format tekstowy (bez solidStep i arrivalStep):
//     nx ny nz
//     x y z type flowId temp
//     0 0 0 1 0 0.0
//     ...              (wszystkie komórki; x najszybciej, potem y, potem z; temp z 1 miejscem po przecinku)
//
// ca_result.bin — format binarny (little-endian, bez ramki), szybszy i ~5x mniejszy:
//     char[4]  magic = "VOLC"
//     uint32   version = 2
//     int32    nx, ny, nz
//     uint8    type[N]         N = nx*ny*nz, indeks x + nx*(y + ny*z)
//     int32    flowId[N]
//     float32  temp[N]
//     uint16   solidStep[N]    krok zastygnięcia
//     uint16   arrivalStep[N]  krok, w którym komórka stała się lawą (od wersji 2; w wersji 1
//                              tej tablicy nie ma — ResultReader przyjmuje wtedy 0)
// Czas w stanie płynnym solidStep − arrivalStep to wejście mobilności MC (mc/McRules.hpp).
//
// mc_result.txt — mapa kryształów po krystalizacji Monte Carlo:
//     nx ny nz
//     x y z crystal
//     ...              (wszystkie komórki, kolejność jak wyżej; crystal = 0 poza domeną MC)
//
// mc_result.bin — binarnie (little-endian):
//     char[4]  magic = "VMC1"   (wersja formatu w magicu)
//     int32    nx, ny, nz
//     int32    crystal[N]
//
// mc_stats.csv — przebieg MC: mcs,grains,meanGrainSize,energy,acceptRate

#include <string>
#include <vector>

#include "core/Types.hpp"
#include "json.hpp"
#include "mc/McRules.hpp"

namespace volcano {

class ResultWriter {
public:
    static constexpr std::uint32_t kBinVersion = 2;
    static constexpr int kTempChars = 64;  // miejsce na temperaturę w formatTemp (z zapasem na snprintf)

    // Zapis tekstowy, buforowany (jeden zapis na ~1 MB danych, bez strumieni i printf — etap 8, k7).
    static void writeTxt(const std::string& path, const Microstructure& m);

    // Temperatura jako tekst z 1 miejscem po przecinku — te same znaki co printf("%.1f", (double)v), bez printf.
    // Pisze do out (co najmniej kTempChars bajtów; za tekstem może zostać '\0'); zwraca liczbę znaków.
    static std::size_t formatTemp(char* out, float v);

    // Zapis binarny — surowe tablice po nagłówku.
    static void writeBin(const std::string& path, const Microstructure& m);

    // Mapa kryształów MC: tekstowo (mc_result.txt) i binarnie (mc_result.bin).
    static void writeCrystalTxt(const std::string& path, const CrystalMap& m);
    static void writeCrystalBin(const std::string& path, const CrystalMap& m);

    // Przebieg MC (mc_stats.csv) — jeden wiersz na pomiar statystyk.
    static void writeMcStatsCsv(const std::string& path, const std::vector<McStats>& history);

    // Zapis dowolnego JSON z wcięciami (config_used.json, times.json, stats.json ...).
    static void writeJson(const std::string& path, const nlohmann::ordered_json& j);
};

}  // namespace volcano
