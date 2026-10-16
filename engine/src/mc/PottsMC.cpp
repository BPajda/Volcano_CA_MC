#include "mc/PottsMC.hpp"

#include <cmath>
#include <stdexcept>
#include <string>
#include <utility>

#include "core/Rng.hpp"
#include "core/Timer.hpp"

namespace volcano {

PottsMC::PottsMC(const Dims& dims, const McParams& params, const Neighborhood& nb, const Boundary& bc)
    : dims_(dims),
      p_(params),
      nb_(nb),
      periodic_{bc.periodicX() && dims.nx > 1, bc.periodicY() && dims.ny > 1, bc.periodicZ() && dims.nz > 1},
      sx_(static_cast<std::size_t>(dims.nx) + 2),
      sy_(static_cast<std::size_t>(dims.ny) + 2) {
    if (p_.Q < 2) {
        throw std::invalid_argument("MC wymaga co najmniej 2 orientacji (Q >= 2)");
    }
    const std::size_t n = sx_ * sy_ * (static_cast<std::size_t>(dims.nz) + 2);
    spin_.assign(n, 0);
    mask_.assign(n, 0);
    // Przesunięcia liniowe: sąsiad (x+dx, y+dy, z+dz) ma indeks i + dx + sx·(dy + sy·dz).
    const std::ptrdiff_t sx = static_cast<std::ptrdiff_t>(sx_);
    const std::ptrdiff_t sy = static_cast<std::ptrdiff_t>(sy_);
    for (int v = 0; v < nb_.variantCount(); ++v) {
        std::vector<std::ptrdiff_t> lin;
        for (const Offset& o : nb_.variant(v)) {
            lin.push_back(o.dx + sx * (o.dy + sy * o.dz));
        }
        linear_.push_back(lin);
    }
}

void PottsMC::setDomainAll() {
    for (int z = 0; z < dims_.nz; ++z) {
        for (int y = 0; y < dims_.ny; ++y) {
            for (int x = 0; x < dims_.nx; ++x) {
                mask_[frameIndex(x, y, z)] = kInDomain;
            }
        }
    }
}

void PottsMC::setDomain(const std::vector<std::uint8_t>& inDomain) {
    if (inDomain.size() != dims_.cells()) {
        throw std::invalid_argument("maska domeny MC ma zły rozmiar");
    }
    std::size_t g = 0;
    for (int z = 0; z < dims_.nz; ++z) {
        for (int y = 0; y < dims_.ny; ++y) {
            for (int x = 0; x < dims_.nx; ++x, ++g) {
                mask_[frameIndex(x, y, z)] = inDomain[g] != 0 ? kInDomain : 0;
            }
        }
    }
}

void PottsMC::setMobility(const std::vector<float>& mobility) {
    if (mobility.empty()) {
        mobility_.clear();
        return;
    }
    if (mobility.size() != dims_.cells()) {
        throw std::invalid_argument("tablica mobilności MC ma zły rozmiar");
    }
    mobility_.assign(spin_.size(), 0.0f);
    std::size_t g = 0;
    for (int z = 0; z < dims_.nz; ++z) {
        for (int y = 0; y < dims_.ny; ++y) {
            for (int x = 0; x < dims_.nx; ++x, ++g) {
                mobility_[frameIndex(x, y, z)] = mobility[g];
            }
        }
    }
}

void PottsMC::initialize() {
    const std::uint64_t q = static_cast<std::uint64_t>(p_.Q);
    domainFrame_.clear();
    domainGlobal_.clear();
    std::uint64_t g = 0;  // globalIndex — pętle w kolejności pamięci
    for (int z = 0; z < dims_.nz; ++z) {
        for (int y = 0; y < dims_.ny; ++y) {
            for (int x = 0; x < dims_.nx; ++x, ++g) {
                const std::size_t i = frameIndex(x, y, z);
                if ((mask_[i] & kInDomain) == 0) {
                    spin_[i] = 0;
                    continue;
                }
                spin_[i] = 1 + static_cast<std::int32_t>(hashRand(p_.seed, 0, g, kSaltMcInit) % q);
                const bool edge = (periodic_[0] && (x == 0 || x == dims_.nx - 1)) ||
                                  (periodic_[1] && (y == 0 || y == dims_.ny - 1)) ||
                                  (periodic_[2] && (z == 0 || z == dims_.nz - 1));
                mask_[i] = static_cast<std::uint8_t>(kInDomain | (edge ? kPeriodicEdge : 0));
                domainFrame_.push_back(i);
                domainGlobal_.push_back(g);
            }
        }
    }
    fillFrame();
    sweeps_ = 0;
    attempts_ = 0;
    accepted_ = 0;
    uphill_ = 0;
}

void PottsMC::fillFrame() {
    const int nx = dims_.nx;
    const int ny = dims_.ny;
    const int nz = dims_.nz;
    // Kopia komórki src do ramki (tylko bit domeny — bit „przy ścianie” dotyczy wnętrza).
    auto copy = [this](std::size_t dst, std::size_t src) {
        spin_[dst] = spin_[src];
        mask_[dst] = static_cast<std::uint8_t>(mask_[src] & kInDomain);
    };
    auto clear = [this](std::size_t dst) {
        spin_[dst] = 0;
        mask_[dst] = 0;
    };
    // Kolejność osi x -> y -> z, każda kolejna obejmuje ramkę poprzednich (krawędzie i narożniki
    // ramki są wtedy poprawnie zawinięte) — jak Boundary::apply.
    for (int z = 0; z < nz; ++z) {
        for (int y = 0; y < ny; ++y) {
            if (periodic_[0]) {
                copy(frameIndex(-1, y, z), frameIndex(nx - 1, y, z));
                copy(frameIndex(nx, y, z), frameIndex(0, y, z));
            } else {
                clear(frameIndex(-1, y, z));
                clear(frameIndex(nx, y, z));
            }
        }
    }
    for (int z = 0; z < nz; ++z) {
        for (int x = -1; x <= nx; ++x) {
            if (periodic_[1]) {
                copy(frameIndex(x, -1, z), frameIndex(x, ny - 1, z));
                copy(frameIndex(x, ny, z), frameIndex(x, 0, z));
            } else {
                clear(frameIndex(x, -1, z));
                clear(frameIndex(x, ny, z));
            }
        }
    }
    for (int y = -1; y <= ny; ++y) {
        for (int x = -1; x <= nx; ++x) {
            if (periodic_[2]) {
                copy(frameIndex(x, y, -1), frameIndex(x, y, nz - 1));
                copy(frameIndex(x, y, nz), frameIndex(x, y, 0));
            } else {
                clear(frameIndex(x, y, -1));
                clear(frameIndex(x, y, nz));
            }
        }
    }
}

void PottsMC::syncFrame(std::size_t i) {
    // Współrzędne komórki z indeksu z ramką (rzadka operacja — tylko zmiany przy ścianie).
    const std::size_t rest = i / sx_;
    const int c[3] = {static_cast<int>(i % sx_) - 1, static_cast<int>(rest % sy_) - 1,
                      static_cast<int>(rest / sy_) - 1};
    const int n[3] = {dims_.nx, dims_.ny, dims_.nz};
    // Położenia kopii w każdej osi: sama komórka, a przy ścianie periodycznej także ramka
    // po przeciwnej stronie (x = 0 -> x = nx, x = nx-1 -> x = -1).
    int alt[3][3];
    int count[3];
    for (int a = 0; a < 3; ++a) {
        alt[a][0] = c[a];
        count[a] = 1;
        if (periodic_[a]) {
            if (c[a] == 0) {
                alt[a][count[a]++] = n[a];
            }
            if (c[a] == n[a] - 1) {
                alt[a][count[a]++] = -1;
            }
        }
    }
    for (int iz = 0; iz < count[2]; ++iz) {
        for (int iy = 0; iy < count[1]; ++iy) {
            for (int ix = 0; ix < count[0]; ++ix) {
                if (ix != 0 || iy != 0 || iz != 0) {
                    spin_[frameIndex(alt[0][ix], alt[1][iy], alt[2][iz])] = spin_[i];
                }
            }
        }
    }
}

std::uint64_t PottsMC::sweep() {
    const std::uint64_t t = static_cast<std::uint64_t>(sweeps_);
    const std::uint64_t n = domainFrame_.size();
    const std::uint64_t otherStates = static_cast<std::uint64_t>(p_.Q - 1);
    const bool useMobility = !mobility_.empty();
    std::uint64_t acceptedNow = 0;

    // 1 MCS = tyle prób, ile komórek w domenie.
    for (std::uint64_t a = 0; a < n; ++a) {
        // Krok 1: losowa selekcja elementu — losowanie ZE ZWRACANIEM z listy komórek domeny.
        // OPTYMALIZACJA: losowanie bez powtórzeń (permutacja listy) i próby tylko dla komórek na granicy ziaren.
        const std::size_t k = static_cast<std::size_t>(hashRand(p_.seed, t, a, kSaltMcPick) % n);
        const std::size_t i = domainFrame_[k];

        // Mobilność (tryb basalt): z prawdopodobieństwem 1 − m_i próba jest pomijana —
        // szybko zastygła lawa prawie nie przebudowuje kryształów.
        if (useMobility && hashUniform(p_.seed, t, a, kSaltMcMobility) >= static_cast<double>(mobility_[i])) {
            continue;
        }
        ++attempts_;
        const std::vector<std::ptrdiff_t>& offsets = offsetsFor(t, domainGlobal_[k]);
        const std::int32_t current = spin_[i];

        // Krok 2: energia sieci otaczającej element przed zmianą: E = J · Σ (1 − δ(S_i, S_j)).
        // OPTYMALIZACJA: E_przed i E_po w jednym przejściu po sąsiadach.
        const double energyBefore = p_.J * unlikeNeighbors(i, current, offsets);

        // Krok 3: nowa orientacja losowana z całego zbioru 1..Q, różna od obecnej
        // (Q − 1 możliwości; wartości >= obecnej przesuwamy o 1).
        // OPTYMALIZACJA: nowa orientacja tylko spośród orientacji sąsiadów.
        std::int32_t proposed =
            1 + static_cast<std::int32_t>(hashRand(p_.seed, t, a, kSaltMcOrient) % otherStates);
        if (proposed >= current) {
            ++proposed;
        }

        // Krok 4: energia po zmianie i zmiana energii ΔE.
        const double energyAfter = p_.J * unlikeNeighbors(i, proposed, offsets);
        const double deltaE = energyAfter - energyBefore;

        // Krok 5: akceptacja Metropolisa — ΔE <= 0 zawsze; ΔE > 0 z prawdopodobieństwem
        // exp(−ΔE/kT) (kT > 0), a dla kT = 0 nigdy (p = 0, dokładnie jak w wariancie naiwnym).
        // OPTYMALIZACJA: tablica exp(−ΔE/kT) dla możliwych ΔE = J · k.
        bool accept = deltaE <= 0.0;
        if (!accept && p_.kT > 0.0) {
            accept = hashUniform(p_.seed, t, a, kSaltMcAccept) < std::exp(-deltaE / p_.kT);
            uphill_ += accept ? 1 : 0;
        }
        if (accept) {
            spin_[i] = proposed;
            ++acceptedNow;
            if ((mask_[i] & kPeriodicEdge) != 0) {
                syncFrame(i);  // kopie komórki w ramce periodycznej muszą zobaczyć zmianę
            }
        }
    }
    accepted_ += acceptedNow;
    ++sweeps_;
    return acceptedNow;
}

McStats PottsMC::measure(GrainLabels* labels, McMeasureTimes* times) const {
    McStats s;
    s.mcs = sweeps_;
    LapTimer phase(times != nullptr);
    McMeasureTimes unused;
    McMeasureTimes& acc = (times != nullptr) ? *times : unused;
    const CrystalMap map = crystals();
    phase.lap(acc.crystals);
    GrainLabels g = Grains::label(map, mooreConnectivity(), periodic_);
    phase.lap(acc.grains);
    s.grains = g.grains;
    s.meanGrainSize = g.grains > 0 ? double(g.cells) / double(g.grains) : 0.0;
    s.energy = totalEnergy();
    phase.lap(acc.energy);
    if (labels != nullptr) {
        *labels = std::move(g);
    }
    return s;
}

std::size_t PottsMC::bytes() const {
    std::size_t b = spin_.size() * sizeof(std::int32_t) + mask_.size() * sizeof(std::uint8_t) +
                    mobility_.size() * sizeof(float) + domainFrame_.capacity() * sizeof(std::size_t) +
                    domainGlobal_.capacity() * sizeof(std::uint64_t);
    for (const std::vector<std::ptrdiff_t>& l : linear_) {
        b += l.size() * sizeof(std::ptrdiff_t);
    }
    return b;
}

void PottsMC::setOrientation(int x, int y, int z, std::int32_t s) {
    const std::size_t i = frameIndex(x, y, z);
    if ((mask_[i] & kInDomain) == 0 || s < 1 || s > p_.Q) {
        throw std::invalid_argument("setOrientation: komórka spoza domeny albo orientacja spoza 1..Q (" +
                                    std::to_string(s) + ")");
    }
    spin_[i] = s;
    if ((mask_[i] & kPeriodicEdge) != 0) {
        syncFrame(i);
    }
}

double PottsMC::energyIf(int x, int y, int z, std::int32_t s) const {
    const std::size_t i = frameIndex(x, y, z);
    const std::uint64_t g = globalIndex(dims_, x, y, z);
    return p_.J * unlikeNeighbors(i, s, offsetsFor(static_cast<std::uint64_t>(sweeps_), g));
}

double PottsMC::energyAt(int x, int y, int z) const { return energyIf(x, y, z, orientation(x, y, z)); }

double PottsMC::deltaEnergy(int x, int y, int z, std::int32_t s) const {
    return energyIf(x, y, z, s) - energyAt(x, y, z);
}

double PottsMC::totalEnergy() const {
    const std::uint64_t t = static_cast<std::uint64_t>(sweeps_);
    std::uint64_t unlike = 0;
    for (std::size_t k = 0; k < domainFrame_.size(); ++k) {
        const std::size_t i = domainFrame_[k];
        unlike += static_cast<std::uint64_t>(unlikeNeighbors(i, spin_[i], offsetsFor(t, domainGlobal_[k])));
    }
    return 0.5 * p_.J * static_cast<double>(unlike);
}

CrystalMap PottsMC::crystals() const {
    CrystalMap m;
    m.dims = dims_;
    m.crystal.resize(dims_.cells());
    std::size_t g = 0;
    for (int z = 0; z < dims_.nz; ++z) {
        for (int y = 0; y < dims_.ny; ++y) {
            for (int x = 0; x < dims_.nx; ++x, ++g) {
                m.crystal[g] = spin_[frameIndex(x, y, z)];  // poza domeną 0
            }
        }
    }
    return m;
}

}  // namespace volcano
