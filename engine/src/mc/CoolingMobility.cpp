#include "mc/CoolingMobility.hpp"

#include <algorithm>
#include <limits>

namespace volcano {

std::vector<std::uint8_t> CoolingMobility::basaltDomain(const Microstructure& m) {
    std::vector<std::uint8_t> domain(m.type.size(), 0);
    for (std::size_t i = 0; i < m.type.size(); ++i) {
        domain[i] = (m.type[i] == CellType::Basalt || m.type[i] == CellType::Lava) ? 1 : 0;
    }
    return domain;
}

std::vector<std::uint32_t> CoolingMobility::liquidTime(const Microstructure& m,
                                                       const std::vector<std::uint8_t>& domain) {
    // Koniec CA dla lawy, która nie zastygła: największy zapisany krok.
    std::uint32_t endStep = 0;
    for (std::size_t i = 0; i < m.type.size(); ++i) {
        if (domain[i] != 0) {
            endStep = std::max<std::uint32_t>(endStep, std::max(m.solidStep[i], m.arrivalStep[i]));
        }
    }
    std::vector<std::uint32_t> time(m.type.size(), 0);
    for (std::size_t i = 0; i < m.type.size(); ++i) {
        if (domain[i] == 0) {
            continue;
        }
        const std::uint32_t solid = (m.type[i] == CellType::Basalt) ? m.solidStep[i] : endStep;
        const std::uint32_t arrival = m.arrivalStep[i];
        time[i] = solid > arrival ? solid - arrival : 0;
    }
    return time;
}

std::vector<float> CoolingMobility::fromCooling(const Microstructure& m, const std::vector<std::uint8_t>& domain,
                                                double mobilityMin) {
    const std::vector<std::uint32_t> time = liquidTime(m, domain);
    std::uint32_t tMin = std::numeric_limits<std::uint32_t>::max();
    std::uint32_t tMax = 0;
    for (std::size_t i = 0; i < time.size(); ++i) {
        if (domain[i] != 0) {
            tMin = std::min(tMin, time[i]);
            tMax = std::max(tMax, time[i]);
        }
    }
    std::vector<float> mobility(time.size(), 0.0f);
    for (std::size_t i = 0; i < time.size(); ++i) {
        if (domain[i] == 0) {
            continue;
        }
        if (tMax == tMin) {
            mobility[i] = 1.0f;  // wszystkie czasy równe — brak różnic w mobilności
            continue;
        }
        const double norm = double(time[i] - tMin) / double(tMax - tMin);
        mobility[i] = static_cast<float>(mobilityMin + (1.0 - mobilityMin) * norm);
    }
    return mobility;
}

}  // namespace volcano
