#include "mc/PottsMC.hpp"

#include <cmath>
#include <stdexcept>
#include <string>
#include <utility>

#include "core/Rng.hpp"
#include "core/Timer.hpp"
#include "parallel/ThreadStats.hpp"

namespace volcano {

PottsMC::PottsMC(const Dims& dims, const McParams& params, const Neighborhood& nb, const Boundary& bc)
    : dims_(dims),
      p_(params),
      nb_(nb),
      periodic_{bc.periodicX() && dims.nx > 1, bc.periodicY() && dims.ny > 1, bc.periodicZ() && dims.nz > 1},
      frame_{dims.frameX(), dims.frameY(), dims.frameZ()},
      sx_(static_cast<std::size_t>(dims.nx + 2 * dims.frameX())),
      sy_(static_cast<std::size_t>(dims.ny + 2 * dims.frameY())),
      base_(static_cast<std::size_t>(dims.frameX()) +
            sx_ * (static_cast<std::size_t>(dims.frameY()) + sy_ * static_cast<std::size_t>(dims.frameZ()))) {
    if (p_.Q < 2) {
        throw std::invalid_argument("MC wymaga co najmniej 2 orientacji (Q >= 2)");
    }
    const std::size_t n = dims.framedCells();
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
    // Bez podziału na pasy (etap 10): okno = cała przestrzeń, wszystkie warstwy własne.
    global_ = dims;
    for (int a = 0; a < 3; ++a) {
        globalPeriodic_[a] = periodic_[a];
    }
    ownHi_ = dims.nz > 1 ? dims.nz : dims.ny;
}

void PottsMC::setStrip(const Strip& s) {
    global_ = s.global;
    const int n[3] = {s.global.nx, s.global.ny, s.global.nz};
    for (int a = 0; a < 3; ++a) {
        globalPeriodic_[a] = s.globalPeriodic[a] && n[a] > 1;
    }
    ownLo_ = s.ownLo;
    ownHi_ = s.ownHi;
    windowLo_ = s.windowLo;
    hashBase_ = s.hashBase;
    link_ = s.link;
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
    std::uint64_t g = hashBase_;  // globalIndex — pętle w kolejności pamięci (w oknie pasa: od komórki okna (0, 0, 0))
    const bool layerZ = dims_.nz > 1;
    for (int z = 0; z < dims_.nz; ++z) {
        for (int y = 0; y < dims_.ny; ++y) {
            // Etap 10: warstwy brzegowe okna nie należą do domeny okna — orientacje dostaną z wymiany.
            const int k = layerZ ? z : y;
            const bool own = k >= ownLo_ && k < ownHi_;
            for (int x = 0; x < dims_.nx; ++x, ++g) {
                const std::size_t i = frameIndex(x, y, z);
                if (!own) {
                    mask_[i] = 0;
                }
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
    colors_ = 0;
    if (checkerboard_) {
        buildColors();
    }
    sweeps_ = 0;
    attempts_ = 0;
    accepted_ = 0;
    uphill_ = 0;
}

int PottsMC::axisClass(int c, int a) const {
    const int n = a == 0 ? global_.nx : (a == 1 ? global_.ny : global_.nz);
    if (globalPeriodic_[a] && (n % 2) == 1 && c == n - 1) {
        return 2;  // ostatnia warstwa nieparzystej osi periodycznej sąsiaduje przez ramkę z warstwą 0 (też parzystą)
    }
    return c & 1;
}

int PottsMC::colorOf(int x, int y, int z) const {
    if (parityColors_) {
        return (x + y + z) & 1;
    }
    return colorIndex_[axisClass(x, 0) + 3 * axisClass(y, 1) + 9 * axisClass(z, 2)];
}

void PottsMC::buildColors() {
    // Dlaczego kolory są poprawne: dwie komórki o tej samej klasie w każdej osi różnią się w każdej osi o 0 albo o co
    // najmniej 2 (także przez ramkę periodyczną — stąd osobna klasa ostatniej warstwy nieparzystej osi), a sąsiedzi
    // Moore'a różnią się w każdej osi najwyżej o 1 i nie są tą samą komórką. Von Neumann zmienia jedną współrzędną
    // o 1, więc zmienia parzystość x + y + z — przy parzystych osiach periodycznych wystarczą 2 kolory. Sąsiedztwa
    // losowe (pentagonal, hexagonal) są podzbiorami Moore'a. Sprawdza to test_parallel.cpp na wszystkich sąsiedztwach.
    // Wymiary i periodyczność — całej przestrzeni (w oknie pasa MPI kolor zależy od położenia globalnego, etap 10).
    const int n[3] = {global_.nx, global_.ny, global_.nz};
    bool oddPeriodic = false;
    for (int a = 0; a < 3; ++a) {
        oddPeriodic = oddPeriodic || (globalPeriodic_[a] && n[a] % 2 == 1);
    }
    parityColors_ = nb_.kind() == NeighborhoodKind::VonNeumann && !oddPeriodic;
    for (int& c : colorIndex_) {
        c = -1;
    }
    if (parityColors_) {
        colors_ = 2;
    } else {
        // Klasy występujące w osi: 1 (oś o rozmiarze 1), 2 (parzystość), 3 (+ ostatnia warstwa nieparzystej osi
        // periodycznej). Kolory numerowane rosnąco wg cx + 3·cy + 9·cz.
        int classes[3];
        for (int a = 0; a < 3; ++a) {
            classes[a] = n[a] == 1 ? 1 : (globalPeriodic_[a] && n[a] % 2 == 1 ? 3 : 2);
        }
        colors_ = 0;
        for (int cz = 0; cz < classes[2]; ++cz) {
            for (int cy = 0; cy < classes[1]; ++cy) {
                for (int cx = 0; cx < classes[0]; ++cx) {
                    colorIndex_[cx + 3 * cy + 9 * cz] = colors_++;
                }
            }
        }
    }
    // Lista domeny kolor po kolorze, w kolorze warstwa po warstwie (w warstwie globalIndex rosnąco): komórki koloru c
    // w warstwie k to fragment [colorLayerStart_[c·L + k], colorLayerStart_[c·L + k + 1]). Warstwy własne okna
    // (bez podziału na pasy — wszystkie); kolor z położenia globalnego (warstwa okna + windowLo_).
    const bool layerZ = dims_.nz > 1;
    layers_ = ownHi_ - ownLo_;
    colorLayerStart_.assign(static_cast<std::size_t>(colors_ * layers_) + 1, 0);
    domainFrame_.clear();
    domainGlobal_.clear();
    for (int c = 0; c < colors_; ++c) {
        for (int k = 0; k < layers_; ++k) {
            colorLayerStart_[static_cast<std::size_t>(c * layers_ + k)] = domainFrame_.size();
            const int kw = ownLo_ + k;  // warstwa w oknie
            const int z0 = layerZ ? kw : 0;
            const int y0 = layerZ ? 0 : kw;
            const int y1 = layerZ ? dims_.ny : kw + 1;
            const int gz = layerZ ? z0 + windowLo_ : z0;  // współrzędne globalne (kolor)
            const int dy = layerZ ? 0 : windowLo_;
            for (int y = y0; y < y1; ++y) {
                std::uint64_t g = globalIndex(dims_, 0, y, z0) + hashBase_;
                for (int x = 0; x < dims_.nx; ++x, ++g) {
                    const std::size_t i = frameIndex(x, y, z0);
                    if ((mask_[i] & kInDomain) != 0 && colorOf(x, y + dy, gz) == c) {
                        domainFrame_.push_back(i);
                        domainGlobal_.push_back(g);
                    }
                }
            }
        }
    }
    colorLayerStart_.back() = domainFrame_.size();
}

void PottsMC::fillFrame() {
    const int nx = dims_.nx;
    const int ny = dims_.ny;
    const int nz = dims_.nz;
    const int fx = frame_[0];  // ramka tylko w osiach o rozmiarze > 1 (etap 8)
    const int fy = frame_[1];
    const int fz = frame_[2];
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
    for (int z = 0; z < nz && fx; ++z) {
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
    for (int z = 0; z < nz && fy; ++z) {
        for (int x = -fx; x < nx + fx; ++x) {
            if (periodic_[1]) {
                copy(frameIndex(x, -1, z), frameIndex(x, ny - 1, z));
                copy(frameIndex(x, ny, z), frameIndex(x, 0, z));
            } else {
                clear(frameIndex(x, -1, z));
                clear(frameIndex(x, ny, z));
            }
        }
    }
    for (int y = -fy; y < ny + fy && fz; ++y) {
        for (int x = -fx; x < nx + fx; ++x) {
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
    const int c[3] = {static_cast<int>(i % sx_) - frame_[0], static_cast<int>(rest % sy_) - frame_[1],
                      static_cast<int>(rest / sy_) - frame_[2]};
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

template <bool kMobility, bool kRandomNb>
std::uint64_t PottsMC::sweepTrials() {
    const std::uint64_t t = static_cast<std::uint64_t>(sweeps_);
    const std::uint64_t n = domainFrame_.size();
    const std::uint64_t otherStates = static_cast<std::uint64_t>(p_.Q - 1);
    // OPTYMALIZACJA (etap 8): stała część kaskady hashRand (seed, krok MCS) liczona raz przed pętlą; w próbie
    // jedno ogniwo numeru próby wspólne dla wszystkich jej decyzji + ogniwo soli (Rng.hpp, hashPrefix).
    const std::uint64_t prefix = hashPrefix(p_.seed, t);
    // Wskaźniki w zmiennych lokalnych: MSVC nie czyta ich wtedy z obiektu w każdej próbie.
    std::int32_t* const spin = spin_.data();
    const std::size_t* const domainFrame = domainFrame_.data();
    const std::ptrdiff_t* const offsets0 = linear_[0].data();
    const std::size_t count0 = linear_[0].size();
    std::uint64_t attempts = 0;
    std::uint64_t acceptedNow = 0;
    std::uint64_t uphill = 0;

    // 1 MCS = tyle prób, ile komórek w domenie.
    for (std::uint64_t a = 0; a < n; ++a) {
        const std::uint64_t h = hashIndex(prefix, a);  // = wspólna część hashRand(seed, t, a, ·)

        // Krok 1: losowa selekcja elementu — losowanie ZE ZWRACANIEM z listy komórek domeny.
        const std::size_t k = static_cast<std::size_t>(hashSalt(h, kSaltMcPick) % n);
        const std::size_t i = domainFrame[k];

        // Mobilność (tryb basalt): z prawdopodobieństwem 1 − m_i próba jest pomijana —
        // szybko zastygła lawa prawie nie przebudowuje kryształów.
        if constexpr (kMobility) {
            if (toUniform(hashSalt(h, kSaltMcMobility)) >= static_cast<double>(mobility_[i])) {
                continue;
            }
        }
        ++attempts;
        const std::ptrdiff_t* offsets = offsets0;
        std::size_t count = count0;
        if constexpr (kRandomNb) {
            const std::vector<std::ptrdiff_t>& v =
                linear_[static_cast<std::size_t>(nb_.variantFromPrefix(prefix, domainGlobal_[k]))];
            offsets = v.data();
            count = v.size();
        }
        const std::int32_t current = spin[i];

        // Krok 3: nowa orientacja losowana z całego zbioru 1..Q, różna od obecnej
        // (Q − 1 możliwości; wartości >= obecnej przesuwamy o 1). Nie zależy od energii, więc liczona
        // przed krokiem 2 — wtedy kroki 2 i 4 to jedno przejście po sąsiadach.
        std::int32_t proposed = 1 + static_cast<std::int32_t>(hashSalt(h, kSaltMcOrient) % otherStates);
        if (proposed >= current) {
            ++proposed;
        }

        // Krok 2 i krok 4: energia sieci otaczającej element przed zmianą E = J · Σ (1 − δ(S_i, S_j)),
        // energia po zmianie i ΔE — liczby sąsiadów „innych” w jednym przejściu (unlikeBeforeAfter).
        int unlikeBefore = 0;
        int unlikeAfter = 0;
        unlikeBeforeAfter(spin + i, current, proposed, offsets, count, unlikeBefore, unlikeAfter);
        const double energyBefore = p_.J * unlikeBefore;
        const double energyAfter = p_.J * unlikeAfter;
        const double deltaE = energyAfter - energyBefore;

        // Krok 5: akceptacja Metropolisa — ΔE <= 0 zawsze; ΔE > 0 z prawdopodobieństwem
        // exp(−ΔE/kT) (kT > 0), a dla kT = 0 nigdy (p = 0, dokładnie jak w wariancie naiwnym).
        // OPTYMALIZACJA: tablica exp(−ΔE/kT) dla możliwych ΔE = J · k.
        bool accept = deltaE <= 0.0;
        if (!accept && p_.kT > 0.0) {
            accept = toUniform(hashSalt(h, kSaltMcAccept)) < std::exp(-deltaE / p_.kT);
            uphill += accept ? 1 : 0;
        }
        if (accept) {
            spin[i] = proposed;
            ++acceptedNow;
            if ((mask_[i] & kPeriodicEdge) != 0) {
                syncFrame(i);  // kopie komórki w ramce periodycznej muszą zobaczyć zmianę
            }
        }
    }
    attempts_ += attempts;
    uphill_ += uphill;
    return acceptedNow;
}

template <bool kMobility, bool kRandomNb>
void PottsMC::colorTrials(std::uint64_t prefix, std::size_t b, std::size_t e, TrialCounts& out) {
    // Liczniki lokalne (dodawane do out na końcu): przez referencję MSVC zapisywał je do pamięci w każdej próbie.
    TrialCounts n;
    std::int32_t* const spin = spin_.data();
    const std::size_t* const domainFrame = domainFrame_.data();
    const std::uint64_t* const domainGlobal = domainGlobal_.data();
    const std::ptrdiff_t* const offsets0 = linear_[0].data();
    const std::size_t count0 = linear_[0].size();
    const std::uint64_t otherStates = static_cast<std::uint64_t>(p_.Q - 1);
    for (std::size_t j = b; j < e; ++j) {
        const std::size_t i = domainFrame[j];
        // Próba komórki o globalnym indeksie g: losowość hashRand(seed, MCS, g, sól) — nie zależy od kolejności prób.
        const std::uint64_t h = hashIndex(prefix, domainGlobal[j]);
        // Dalej kroki jak w sweepTrials (bez kroku 1 — komórkę wyznacza szachownica): mobilność, nowa orientacja,
        // energia przed i po w jednym przejściu, akceptacja Metropolisa.
        if constexpr (kMobility) {
            if (toUniform(hashSalt(h, kSaltMcMobility)) >= static_cast<double>(mobility_[i])) {
                continue;
            }
        }
        ++n.attempts;
        const std::ptrdiff_t* offsets = offsets0;
        std::size_t count = count0;
        if constexpr (kRandomNb) {
            const std::vector<std::ptrdiff_t>& v =
                linear_[static_cast<std::size_t>(nb_.variantFromPrefix(prefix, domainGlobal[j]))];
            offsets = v.data();
            count = v.size();
        }
        const std::int32_t current = spin[i];
        std::int32_t proposed = 1 + static_cast<std::int32_t>(hashSalt(h, kSaltMcOrient) % otherStates);
        if (proposed >= current) {
            ++proposed;
        }
        int unlikeBefore = 0;
        int unlikeAfter = 0;
        unlikeBeforeAfter(spin + i, current, proposed, offsets, count, unlikeBefore, unlikeAfter);
        const double deltaE = p_.J * unlikeAfter - p_.J * unlikeBefore;
        bool accept = deltaE <= 0.0;
        if (!accept && p_.kT > 0.0) {
            accept = toUniform(hashSalt(h, kSaltMcAccept)) < std::exp(-deltaE / p_.kT);
            n.uphill += accept ? 1 : 0;
        }
        if (accept) {
            spin[i] = proposed;
            ++n.accepted;
            if ((mask_[i] & kPeriodicEdge) != 0) {
                syncFrame(i);  // kopie w ramce — inne komórki ramki dla każdej komórki: bez konfliktu między wątkami
            }
        }
    }
    out.attempts += n.attempts;
    out.accepted += n.accepted;
    out.uphill += n.uphill;
}

template <bool kMobility, bool kRandomNb>
std::uint64_t PottsMC::sweepColors() {
    const std::uint64_t prefix = hashPrefix(p_.seed, static_cast<std::uint64_t>(sweeps_));
    TrialCounts total;
    StripLink* const link = link_;  // etap 10: warstwy brzegowe od sąsiednich procesów po każdym kolorze
    if (!par_.parallel()) {
        for (int c = 0; c < colors_; ++c) {
            colorTrials<kMobility, kRandomNb>(prefix, colorBegin(c), colorEnd(c), total);
            if (link != nullptr) {
                link->exchange(*this);
            }
        }
    } else {
        // Jeden region na MCS: kolor po kolorze, komórki koloru dzielone między wątki po warstwach (pasach z albo y);
        // bariera po kolorze — następny kolor czyta komórki zmienione w tym.
        const std::ptrdiff_t nl = layers_;
        const Schedule sched = par_.schedule;
        const int chunk = par_.chunk;
        ThreadStats* const ts = par_.stats;
        const double wall0 = ts != nullptr ? omp_get_wtime() : 0.0;
        std::uint64_t attempts = 0;
        std::uint64_t accepted = 0;
        std::uint64_t uphill = 0;
#ifdef _OPENMP
#  pragma omp parallel num_threads(par_.threads) reduction(+ : attempts, accepted, uphill)
#endif
        {
            const int tid = omp_get_thread_num();
            PhaseClock clock(ts, tid);
            if (ts != nullptr) {
                ts->noteCpu(tid);
            }
            TrialCounts mine;
            for (int c = 0; c < colors_; ++c) {
                const std::size_t* const start = colorLayerStart_.data() + static_cast<std::size_t>(c * layers_);
                clock.begin();
                ompFor(nl, sched, chunk, [&](std::ptrdiff_t k) {
                    colorTrials<kMobility, kRandomNb>(prefix, start[k], start[k + 1], mine);
                });
                clock.end(c);
                ompBarrier();
                if (link != nullptr) {
                    // Tryb hybrydowy (MPI + OpenMP): MPI woła tylko wątek główny (MPI_THREAD_FUNNELED), reszta czeka.
                    if (tid == 0) {
                        link->exchange(*this);
                    }
                    ompBarrier();
                }
            }
            attempts += mine.attempts;
            accepted += mine.accepted;
            uphill += mine.uphill;
        }
        if (ts != nullptr) {
            ts->addWall(omp_get_wtime() - wall0);
            ts->endStep();
        }
        total.attempts = attempts;
        total.accepted = accepted;
        total.uphill = uphill;
    }
    attempts_ += total.attempts;
    uphill_ += total.uphill;
    return total.accepted;
}

std::uint64_t PottsMC::sweep() {
    const bool useMobility = !mobility_.empty();
    std::uint64_t acceptedNow;
    if (checkerboard_) {
        if (nb_.isRandom()) {
            acceptedNow = useMobility ? sweepColors<true, true>() : sweepColors<false, true>();
        } else {
            acceptedNow = useMobility ? sweepColors<true, false>() : sweepColors<false, false>();
        }
    } else if (nb_.isRandom()) {
        acceptedNow = useMobility ? sweepTrials<true, true>() : sweepTrials<false, true>();
    } else {
        acceptedNow = useMobility ? sweepTrials<true, false>() : sweepTrials<false, false>();
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
                    domainGlobal_.capacity() * sizeof(std::uint64_t) +
                    colorLayerStart_.capacity() * sizeof(std::size_t);
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
    const std::uint64_t g = globalIndex(dims_, x, y, z) + hashBase_;
    return p_.J * unlikeNeighbors(i, s, offsetsFor(static_cast<std::uint64_t>(sweeps_), g));
}

double PottsMC::energyAt(int x, int y, int z) const { return energyIf(x, y, z, orientation(x, y, z)); }

double PottsMC::deltaEnergy(int x, int y, int z, std::int32_t s) const {
    return energyIf(x, y, z, s) - energyAt(x, y, z);
}

double PottsMC::totalEnergy() const {
    const std::uint64_t t = static_cast<std::uint64_t>(sweeps_);
    std::uint64_t unlike = 0;
    if (!nb_.isRandom()) {
        // OPTYMALIZACJA (etap 8): sąsiedztwo symetryczne (von Neumann, Moore) — każda para sąsiadów raz, przez
        // przesunięcia „do przodu” (dodatnie przesunięcie liniowe). Para (i, i+o) z sumy po wszystkich sąsiadach ma
        // odpowiednik (i+o, i) z przesunięciem −o (także przez ramkę periodyczną), więc pełna suma = 2 · suma „do
        // przodu”, a 0.5 · J · 2P == J · P bitowo (mnożenie przez 0.5 i 2 jest dokładne). Para z komórką spoza domeny
        // (orientacja 0) nie wnosi energii — jak w unlikeNeighbors. Pomiar ~2× szybszy (etap 8, k5).
        std::vector<std::ptrdiff_t> forward;
        for (const std::ptrdiff_t o : linear_[0]) {
            if (o > 0) {
                forward.push_back(o);
            }
        }
        // Bez skoków warunkowych (jak unlikeNeighbors): różnych = w domenie (S_j != 0) − tej samej orientacji (s >= 1).
        std::uint64_t inDomain = 0;
        std::uint64_t same = 0;
        if (par_.parallel()) {
            // Etap 9: komórki domeny dzielone między wątki, sumy całkowite przez redukcję (wynik ten sam).
            const std::ptrdiff_t n = static_cast<std::ptrdiff_t>(domainFrame_.size());
            const std::size_t* const domain = domainFrame_.data();
            const std::int32_t* const spins = spin_.data();
#ifdef _OPENMP
#  pragma omp parallel for schedule(static) num_threads(par_.threads) reduction(+ : inDomain, same)
#endif
            for (std::ptrdiff_t k = 0; k < n; ++k) {
                const std::int32_t* const spin = spins + domain[k];
                const std::int32_t s = *spin;
                for (const std::ptrdiff_t o : forward) {
                    const std::int32_t sj = spin[o];
                    inDomain += static_cast<std::uint64_t>(sj != 0);
                    same += static_cast<std::uint64_t>(sj == s);
                }
            }
        } else {
            for (const std::size_t i : domainFrame_) {
                const std::int32_t* const spin = spin_.data() + i;
                const std::int32_t s = *spin;
                for (const std::ptrdiff_t o : forward) {
                    const std::int32_t sj = spin[o];
                    inDomain += static_cast<std::uint64_t>(sj != 0);
                    same += static_cast<std::uint64_t>(sj == s);
                }
            }
        }
        unlike = inDomain - same;
        // Etap 10: pary „do przodu” komórek własnych — każda para raz w całej przestrzeni (para z warstwą brzegową nad
        // pasem liczy niższy pas, para z warstwą pod pasem — pas sąsiada), suma liczb całkowitych po procesach.
        if (link_ != nullptr) {
            link_->sum(&unlike, 1);
        }
        return p_.J * static_cast<double>(unlike);
    }
    if (par_.parallel()) {
        const std::ptrdiff_t n = static_cast<std::ptrdiff_t>(domainFrame_.size());
#ifdef _OPENMP
#  pragma omp parallel for schedule(static) num_threads(par_.threads) reduction(+ : unlike)
#endif
        for (std::ptrdiff_t k = 0; k < n; ++k) {
            const std::size_t i = domainFrame_[static_cast<std::size_t>(k)];
            unlike += static_cast<std::uint64_t>(
                unlikeNeighbors(i, spin_[i], offsetsFor(t, domainGlobal_[static_cast<std::size_t>(k)])));
        }
    } else {
        for (std::size_t k = 0; k < domainFrame_.size(); ++k) {
            const std::size_t i = domainFrame_[k];
            unlike += static_cast<std::uint64_t>(unlikeNeighbors(i, spin_[i], offsetsFor(t, domainGlobal_[k])));
        }
    }
    if (link_ != nullptr) {
        link_->sum(&unlike, 1);  // etap 10: suma po komórkach własnych wszystkich procesów
    }
    return 0.5 * p_.J * static_cast<double>(unlike);
}

CrystalMap PottsMC::crystals() const {
    CrystalMap m;
    m.dims = dims_;
    m.crystal.resize(dims_.cells());
    if (par_.parallel()) {
        // Etap 9: wiersze (y, z) dzielone między wątki — każdy wiersz pisze swój fragment mapy.
        const std::ptrdiff_t rows = static_cast<std::ptrdiff_t>(dims_.ny) * dims_.nz;
        std::int32_t* const out = m.crystal.data();
#ifdef _OPENMP
#  pragma omp parallel for schedule(static) num_threads(par_.threads)
#endif
        for (std::ptrdiff_t r = 0; r < rows; ++r) {
            const int y = static_cast<int>(r % dims_.ny);
            const int z = static_cast<int>(r / dims_.ny);
            std::int32_t* const row = out + static_cast<std::size_t>(r) * static_cast<std::size_t>(dims_.nx);
            const std::int32_t* const src = spin_.data() + frameIndex(0, y, z);
            for (int x = 0; x < dims_.nx; ++x) {
                row[x] = src[x];  // poza domeną 0
            }
        }
        return m;
    }
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
