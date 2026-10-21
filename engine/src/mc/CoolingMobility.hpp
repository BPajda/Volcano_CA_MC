#pragma once
// Domena krystalizacji w trybie basalt i mobilność komórek z czasu stygnięcia lawy.
//
// Czas w stanie płynnym (z wyniku CA): czas_i = solidStep − arrivalStep. Pozostała płynna
// lawa (LAVA, np. krater otoczony zastygłą lawą) jest traktowana jak zastygła w ostatnim
// kroku CA, przybliżonym największym solidStep/arrivalStep w wyniku.
// Mobilność: normalizacja min–max po domenie, m_i = mobilityMin + (1 − mobilityMin) · czas_norm;
// gdy wszystkie czasy są równe — m_i = 1 (brak różnic, MC jak bez mobilności).
// Uzasadnienie fizyczne („chilled margin”) — McRules.hpp.

#include <cstdint>
#include <vector>

#include "core/Types.hpp"

namespace volcano {

class CoolingMobility {
public:
    // Maska domeny (kolejność globalIndex): 1 dla komórek BASALT i LAVA, 0 dla pozostałych.
    static std::vector<std::uint8_t> basaltDomain(const Microstructure& m);

    // Czas w stanie płynnym [kroki CA] komórek domeny (0 poza domeną).
    static std::vector<std::uint32_t> liquidTime(const Microstructure& m, const std::vector<std::uint8_t>& domain);

    // Mobilność komórek domeny z [mobilityMin, 1] (0 poza domeną).
    static std::vector<float> fromCooling(const Microstructure& m, const std::vector<std::uint8_t>& domain,
                                          double mobilityMin);

    // --- składniki fromCooling (etap 10: w wersji MPI każdy proces ma tylko swój pas wyniku CA, a koniec CA i zakres
    // czasów są maksimum / minimum po wszystkich procesach — MPI_Allreduce między krokami) ---

    // Koniec CA dla lawy, która nie zastygła: największy solidStep / arrivalStep komórek domeny.
    static std::uint32_t endStep(const Microstructure& m, const std::vector<std::uint8_t>& domain);
    // Czas w stanie płynnym przy podanym końcu CA.
    static std::vector<std::uint32_t> liquidTime(const Microstructure& m, const std::vector<std::uint8_t>& domain,
                                                 std::uint32_t endStep);
    // Najmniejszy i największy czas w domenie (tMin = UINT32_MAX, tMax = 0 przy pustej domenie).
    static void timeRange(const std::vector<std::uint32_t>& time, const std::vector<std::uint8_t>& domain,
                          std::uint32_t& tMin, std::uint32_t& tMax);
    // Normalizacja min–max czasów do mobilności (tMin, tMax — zakres po całej domenie).
    static std::vector<float> normalize(const std::vector<std::uint32_t>& time, const std::vector<std::uint8_t>& domain,
                                        std::uint32_t tMin, std::uint32_t tMax, double mobilityMin);
};

}  // namespace volcano
