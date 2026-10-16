#pragma once
// Automat komórkowy spływu lawy (i klasycznego rozrostu ziaren) — szablon po
// reprezentacji siatki Storage (VectorStorage / MatrixStorage).
//
// Synchroniczny CA z podwójnym buforem: krok czyta wyłącznie cur_, pisze wyłącznie
// next_, po kroku bufory są zamieniane (swap, bez kopiowania). Każda komórka next_
// zależy tylko od cur_, więc pętla jest trywialnie równoległa (planowane OpenMP/MPI).
// Losowość pochodzi z hashRand(seed, krok, globalnyIndeks, sól) — wynik jest identyczny
// dla obu reprezentacji siatki (sprawdza to benchmark i testy).
// Reguły są opisane w CaRules.hpp.

#include <algorithm>
#include <cstdint>
#include <vector>

#include "ca/CaRules.hpp"
#include "core/Boundary.hpp"
#include "core/Neighborhood.hpp"
#include "core/Profile.hpp"
#include "core/Storage.hpp"
#include "core/Timer.hpp"
#include "core/Types.hpp"
#include "terrain/TerrainGenerator.hpp"
#include "terrain/VentPlacer.hpp"

namespace volcano {

// Czasy faz kroku [ms], sumowane po krokach — tylko przy --timing-detail (etap 3).
struct CaPhaseTimes {
    double frame = 0.0;    // wypełnienie ramki (warunki brzegowe)
    double descent = 0.0;  // przebieg D(n) — największy spadek (tylko tryb lava)
    double rules = 0.0;    // główna pętla: reguły, głosowanie, zapis next, zliczanie zmian
    double finish = 0.0;   // zamiana buforów, historia, warunek końca
};

template <class Storage>
class LavaCA {
public:
    // Alokuje oba bufory (cur, next) — cała przestrzeń AIR.
    LavaCA(const Dims& dims, const CaParams& params, const Neighborhood& nb, const Boundary& bc)
        : dims_(dims), p_(params), nb_(nb), bc_(bc), cur_(dims), next_(dims) {
        if (params.mode == CaMode::Lava) {
            descent_.assign(dims.cells(), -1);
        }
        // Poziomi sąsiedzi (oś pionowa to z) — używani przez regułę wypełniania zagłębień.
        horizontal_.push_back(Offset{-1, 0, 0});
        horizontal_.push_back(Offset{1, 0, 0});
        if (dims.ny > 1) {
            horizontal_.push_back(Offset{0, -1, 0});
            horizontal_.push_back(Offset{0, 1, 0});
        }
        // Komórki obok (dz = 0), dokąd lawa może odpłynąć, i czy sąsiedztwo ma spływ po skosie —
        // suma po wszystkich wariantach, więc wynik nie zależy od wylosowanego wariantu.
        for (int v = 0; v < nb_.variantCount(); ++v) {
            for (const Offset& o : nb_.variant(v)) {
                if (o.dz == 0) {
                    addUnique(sideOffsets_, o);
                } else if (o.dz == -1 && (o.dx != 0 || o.dy != 0)) {
                    diagonalFalls_ = true;
                }
            }
        }
    }

    // Teren: ROCK w kolumnie (x, y) dla z < h(x, y). Tylko tryb lava.
    // Liczy też poziomy przelewu niecek (reguła wypełniania zagłębień).
    void applyTerrain(const Heightmap& hm) {
        for (int y = 0; y < dims_.ny; ++y) {
            for (int x = 0; x < dims_.nx; ++x) {
                const int h = std::min(hm.at(x, y), dims_.nz);
                for (int z = 0; z < h; ++z) {
                    cur_.setType(x, y, z, CellType::Rock);
                }
            }
        }
        spill_ = TerrainGenerator::fillDepressions(hm, bc_.periodicX(), bc_.periodicY());
    }

    // Kratery / zarodki: LAVA z własnym flowId; temperatura eruptTemp (lava) lub 0 (classic).
    // Wywołać po applyTerrain — ustala też stan początkowy liczników i warunku końca.
    void placeSeeds(const std::vector<Vent>& vents) {
        const float temp = (p_.mode == CaMode::Lava) ? p_.eruptTemp : 0.0f;
        ventByFlow_.clear();
        for (const Vent& v : vents) {
            cur_.setCell(v.x, v.y, v.z, CellState{CellType::Lava, v.flowId, temp, 0, 0});
            // Szybkie rozpoznanie krateru po flowId: krater f leży w ventByFlow_[f].
            if (v.flowId >= static_cast<std::int32_t>(ventByFlow_.size())) {
                ventByFlow_.resize(static_cast<std::size_t>(v.flowId) + 1, Coord{-1, -1, -1});
            }
            ventByFlow_[static_cast<std::size_t>(v.flowId)] = Coord{v.x, v.y, v.z};
        }
        countInitialState();
    }

    // Jeden krok automatu. Zwraca true, jeśli symulacja trwa dalej.
    bool step() {
        if (finished()) {
            return false;
        }
        if (phaseTiming_) {
            stepTimed();
        } else if (p_.mode == CaMode::Lava) {
            stepLava();
        } else {
            stepClassic();
        }
        return !finished();
    }

    // Kroki aż do spełnienia warunku końca.
    void run() {
        while (step()) {
        }
    }

    bool finished() const { return stop_ != StopReason::Running; }
    StopReason stopReason() const { return stop_; }
    int steps() const { return steps_; }

    // Liczba komórek LAVA po każdym kroku (w classic: komórki należące do ziaren).
    const std::vector<std::uint64_t>& activeHistory() const { return activeHistory_; }
    // Liczba komórek zmienionych w każdym kroku (front rozrostu / stygnięcie).
    const std::vector<std::uint64_t>& changedHistory() const { return changedHistory_; }

    // Bieżący stan (bufor cur).
    const Storage& state() const { return cur_; }

    // Wynik w postaci płaskiej mikrostruktury (bez ramki).
    Microstructure result() const { return toMicrostructure(cur_); }

    // --- profil (etap 3) ---

    // Pomiar czasów faz kroku (--timing-detail): kroki idą wtedy przez stepTimed(). Domyślnie wyłączony.
    void enablePhaseTiming(bool on) { phaseTiming_ = on; }
    const CaPhaseTimes& phaseTimes() const { return phases_; }

    // Pamięć obu buforów z ramką [B] (dane komórek; MatrixStorage bez narzutu alokacji wierszy).
    std::size_t gridBytes() const { return cur_.bytes() + next_.bytes(); }
    // Pamięć tablic pomocniczych [B]: D(n) (tryb lava) i poziomy przelewu niecek.
    std::size_t auxBytes() const {
        return descent_.size() * sizeof(std::int8_t) + spill_.height.size() * sizeof(int);
    }

private:
    // Położenie komórki (do tablicy kraterów).
    struct Coord {
        int x;
        int y;
        int z;
    };

    // Czy komórka (x, y, z) z danym flowId jest kraterem (O(1) dzięki ventByFlow_).
    bool isVent(std::int32_t flowId, int x, int y, int z) const {
        if (flowId <= 0 || flowId >= static_cast<std::int32_t>(ventByFlow_.size())) {
            return false;
        }
        const Coord& v = ventByFlow_[static_cast<std::size_t>(flowId)];
        return v.x == x && v.y == y && v.z == z;
    }

    // Zawija współrzędną z ramki (-1 lub n) do wnętrza — bez kosztownego dzielenia modulo.
    static int wrap(int v, int n) { return v < 0 ? v + n : (v >= n ? v - n : v); }

    // Poziom przelewu kolumny (x, y); współrzędne z ramki periodycznej są zawijane.
    int spillAt(int x, int y) const { return spill_.at(wrap(x, dims_.nx), wrap(y, dims_.ny)); }

    // Czy lawa w komórce (x, y, z) ma podparcie, czyli może rozlewać się na boki.
    // Podparciem jest dno przestrzeni, skała, bazalt oraz płynna lawa leżąca w niecce
    // (jezioro lawy). Lawa spływająca po zboczu albo wisząca nad przepaścią NIE jest
    // podparciem — inaczej lawa rozlewałaby się poziomo „po sobie” nad powietrzem
    // i wypełniała całą przestrzeń pod sobą (patrz CaRules.hpp).
    VOLCANO_NOINLINE bool hasSupport(int x, int y, int z) const {
        if (z == 0) {
            return true;
        }
        const CellType below = cur_.type(x, y, z - 1);
        if (isSolidGround(below)) {
            return true;
        }
        return below == CellType::Lava && !spill_.empty() && z - 1 < spillAt(x, y);
    }

    // Głębokość spadku z komórki AIR (x, y, z): po ilu poziomach w dół lawa wyląduje na
    // gruncie (0 = komórka ma podparcie). -1, gdy pod spodem jest płynąca lawa (brak
    // lądowania — lawa nie piętrzy się na płynącej lawie). Głębsze urwiska liczą się jak kMaxDrop.
    VOLCANO_NOINLINE int dropDepth(int x, int y, int z) const {
        for (int d = 0; d <= kMaxDrop && z - d >= 0; ++d) {
            if (d > 0 && cur_.type(x, y, z - d) != CellType::Air) {
                return -1;
            }
            if (hasSupport(x, y, z - d)) {
                return d;
            }
        }
        return kMaxDrop;
    }

    // Największy spadek dostępny dla lawy leżącej na gruncie w (x, y, z): maksimum
    // dropDepth po sąsiednich komórkach AIR na tym samym poziomie. 0 = brak drogi w dół
    // (lawa może się rozlewać po płaskim). Lawa płynie tylko w kierunku największego
    // spadku — tak powstają jęzory zamiast wachlarza (plan projektu §3.3: „lawa woli
    // spływać w dół”; podobnie wypływ do najniższych sąsiadów w modelach SCIARA).
    VOLCANO_NOINLINE int descent(int x, int y, int z) const {
        int best = 0;
        for (const Offset& h : sideOffsets_) {
            if (cur_.type(x + h.dx, y + h.dy, z) == CellType::Air) {
                best = std::max(best, dropDepth(x + h.dx, y + h.dy, z));
            }
        }
        return best;
    }

    // Dodaje przesunięcie do listy, jeśli jeszcze go w niej nie ma.
    static void addUnique(std::vector<Offset>& list, const Offset& o) {
        for (const Offset& e : list) {
            if (e.dx == o.dx && e.dy == o.dy && e.dz == o.dz) {
                return;
            }
        }
        list.push_back(o);
    }

    // Reguła wypełniania zagłębień: czy lawa z komórki b pod c może podnieść się do c.
    // Warunki opisane w CaRules.hpp. Dodaje kandydata do głosowania.
    VOLCANO_NOINLINE void tryPonding(int x, int y, int z, CandidateVote& vote) const {
        if (spill_.empty() || z > spill_.at(x, y)) {
            return;  // c ponad poziomem przelewu niecki (albo brak terenu)
        }
        const int bz = z - 1;
        if (cur_.type(x, y, bz) != CellType::Lava) {
            return;
        }
        if (!hasSupport(x, y, bz)) {
            return;  // b nie leży na gruncie — najpierw spadnie
        }
        for (const Offset& h : horizontal_) {
            const CellType n = cur_.type(x + h.dx, y + h.dy, bz);
            if (n == CellType::Air || n == CellType::Void) {
                return;  // b może jeszcze rozlać się na boki
            }
        }
        vote.add(cur_.flowId(x, y, bz), cur_.temp(x, y, bz) - p_.coolingLateral);
    }

    // Zbiera kandydatów (lawa, która może wpłynąć do komórki AIR c) — reguła 1 z CaRules.hpp.
    VOLCANO_NOINLINE void gatherLavaCandidates(int x, int y, int z, std::uint64_t t, std::uint64_t idx,
                                               CandidateVote& vote) const {
        vote.clear();
        int cDrop = kUnknown;  // spadek z komórki c — liczony leniwie
        for (const Offset& o : nb_.offsetsFor(p_.seed, t, idx)) {
            if (o.dz < 0) {
                // Lawa się nie wspina: sąsiad poniżej nie wpływa do c.
                // Wyjątek: wypełnianie zagłębienia z komórki dokładnie pod c.
                if (p_.ponding && o.dx == 0 && o.dy == 0) {
                    tryPonding(x, y, z, vote);
                }
                continue;
            }
            const int sz = z + o.dz;
            if (cur_.type(x + o.dx, y + o.dy, sz) != CellType::Lava) {
                continue;  // (ramka absorbująca to VOID — nigdy nie jest lawą)
            }
            // Źródło z ramki periodycznej zawijamy do wnętrza (ramka jest jego kopią) —
            // dalsze sprawdzenia sięgają do sąsiadów źródła, czyli poza ramkę.
            const int sx = wrap(x + o.dx, dims_.nx);
            const int sy = wrap(y + o.dy, dims_.ny);
            float cooling;
            if (o.dz > 0 && o.dx == 0 && o.dy == 0) {
                cooling = p_.coolingFall;  // swobodny spadek pionowo — zawsze
            } else {
                // Największy spadek źródła policzony na początku kroku (-1: źródło bez podparcia).
                const int d = descent_[static_cast<std::size_t>(globalIndex(dims_, sx, sy, sz))];
                if (d < 0) {
                    continue;
                }
                if (cDrop == kUnknown) {
                    cDrop = dropDepth(x, y, z);  // liczone raz na komórkę c, tylko gdy potrzebne
                }
                if (o.dz > 0) {
                    // Spływ po skosie w dół stoku: c ma grunt pod sobą, a największy spadek
                    // dostępny dla źródła to 1 poziom.
                    if (cDrop != 0 || d != 1) {
                        continue;
                    }
                    cooling = p_.coolingFall;
                } else {
                    // Rozlewanie: c jest w kierunku największego spadku (spadek(c) == D(źródła));
                    // przy D = 0 — po płaskim. Spadek o 1 obsługuje spływ po skosie (jeśli
                    // sąsiedztwo ma przekątne).
                    if (cDrop != d || (d == 1 && diagonalFalls_)) {
                        continue;
                    }
                    cooling = p_.coolingLateral;
                }
            }
            vote.add(cur_.flowId(sx, sy, sz), cur_.temp(sx, sy, sz) - cooling);
        }
    }

    // Przed krokiem: największy spadek D(n) dla każdej komórki lawy leżącej na gruncie
    // (-1 dla pozostałych). Osobny przebieg, bo D(n) jest potrzebne wielu sąsiadom n —
    // bez tego liczylibyśmy je kilkanaście razy na krok. Czyta tylko cur_, więc w wersji równoległej
    // ten przebieg też da się zrównoleglić.
    VOLCANO_NOINLINE void computeDescent() {
        std::size_t i = 0;
        for (int z = 0; z < dims_.nz; ++z) {
            for (int y = 0; y < dims_.ny; ++y) {
                for (int x = 0; x < dims_.nx; ++x, ++i) {
                    std::int8_t d = -1;
                    if (cur_.type(x, y, z) == CellType::Lava && hasSupport(x, y, z)) {
                        d = static_cast<std::int8_t>(descent(x, y, z));
                    }
                    descent_[i] = d;
                }
            }
        }
    }

    // Liczniki jednego kroku (historia i warunek końca).
    struct StepCounts {
        std::uint64_t active = 0;   // LAVA po kroku (classic: komórki należące do ziaren)
        std::uint64_t air = 0;      // wolne komórki AIR
        std::uint64_t changed = 0;  // komórki zmienione w kroku
    };

    // Krok trybu lava: ramka -> D(n) -> reguły -> zamiana buforów.
    VOLCANO_NOINLINE void stepLava() {
        bc_.apply(cur_);
        computeDescent();
        finishStep(updateLava());
    }

    // Krok trybu classic (rozrost ziaren bez grawitacji i temperatury): ramka -> reguły -> zamiana.
    VOLCANO_NOINLINE void stepClassic() {
        bc_.apply(cur_);
        finishStep(updateClassic());
    }

    // Ten sam krok z pomiarem czasu faz (--timing-detail). Osobna ścieżka: stoper wewnątrz
    // stepLava zmieniał kod generowany przez MSVC dla głównej pętli (krok lawy wolniejszy
    // o ~10% — test A/B w profilu z etapu 3), a zwykły przebieg ma zostać punktem odniesienia.
    VOLCANO_NOINLINE void stepTimed() {
        LapTimer phase(true);
        bc_.apply(cur_);
        phase.lap(phases_.frame);
        StepCounts counts;
        if (p_.mode == CaMode::Lava) {
            computeDescent();
            phase.lap(phases_.descent);
            counts = updateLava();
        } else {
            counts = updateClassic();
        }
        phase.lap(phases_.rules);
        finishStep(counts);
        phase.lap(phases_.finish);
    }

    // Reguły lawy dla wszystkich komórek: czyta cur_, pisze next_, zlicza lawę i zmiany.
    VOLCANO_NOINLINE StepCounts updateLava() {
        const std::uint64_t t = static_cast<std::uint64_t>(steps_);
        const bool erupting = steps_ < p_.eruptionSteps;
        // Znacznik kroku dla solidStep i arrivalStep (uint16 — stąd ca.maxSteps <= 65535).
        const std::uint16_t stamp = static_cast<std::uint16_t>(std::min(steps_, 65535));
        std::uint64_t lava = 0;
        std::uint64_t air = 0;
        std::uint64_t changed = 0;
        std::uint64_t idx = 0;  // globalIndex(x, y, z) — pętle idą w kolejności pamięci
        CandidateVote vote;

        for (int z = 0; z < dims_.nz; ++z) {
            for (int y = 0; y < dims_.ny; ++y) {
                for (int x = 0; x < dims_.nx; ++x, ++idx) {
                    const CellType type = cur_.type(x, y, z);
                    if (type == CellType::Air) {
                        gatherLavaCandidates(x, y, z, t, idx, vote);
                        if (!vote.empty()) {
                            const int w = vote.winner(p_.seed, t, idx);
                            const float temp = vote.maxTemp(w);
                            if (temp >= p_.solidusTemp) {
                                next_.setCell(x, y, z,
                                              CellState{CellType::Lava, vote.flowId(w), temp, 0, stamp});
                                ++lava;
                                ++changed;
                                continue;
                            }
                        }
                        next_.setCell(x, y, z, cur_.cell(x, y, z));
                        ++air;
                    } else if (type == CellType::Lava) {
                        CellState c = cur_.cell(x, y, z);
                        const float before = c.temp;
                        if (erupting && isVent(c.flowId, x, y, z)) {
                            c.temp = p_.eruptTemp;  // krater zasilany z komina
                        } else {
                            c.temp -= p_.coolingAmbient;
                        }
                        if (c.temp < p_.solidusTemp) {
                            c.type = CellType::Basalt;
                            c.solidStep = stamp;
                            ++changed;
                        } else {
                            ++lava;
                            changed += (c.temp != before) ? 1 : 0;
                        }
                        next_.setCell(x, y, z, c);
                    } else {
                        next_.setCell(x, y, z, cur_.cell(x, y, z));  // ROCK, BASALT
                    }
                }
            }
        }
        return StepCounts{lava, air, changed};
    }

    // Reguły rozrostu klasycznego dla wszystkich komórek: czyta cur_, pisze next_.
    VOLCANO_NOINLINE StepCounts updateClassic() {
        const std::uint64_t t = static_cast<std::uint64_t>(steps_);
        const std::uint16_t stamp = static_cast<std::uint16_t>(std::min(steps_, 65535));
        std::uint64_t grains = 0;
        std::uint64_t air = 0;
        std::uint64_t changed = 0;
        std::uint64_t idx = 0;
        CandidateVote vote;

        for (int z = 0; z < dims_.nz; ++z) {
            for (int y = 0; y < dims_.ny; ++y) {
                for (int x = 0; x < dims_.nx; ++x, ++idx) {
                    const CellType type = cur_.type(x, y, z);
                    if (type == CellType::Air) {
                        vote.clear();
                        for (const Offset& o : nb_.offsetsFor(p_.seed, t, idx)) {
                            const int sx = x + o.dx;
                            const int sy = y + o.dy;
                            const int sz = z + o.dz;
                            if (cur_.type(sx, sy, sz) == CellType::Lava) {
                                vote.add(cur_.flowId(sx, sy, sz), 0.0f);
                            }
                        }
                        if (!vote.empty()) {
                            const int w = vote.winner(p_.seed, t, idx);
                            next_.setCell(x, y, z, CellState{CellType::Lava, vote.flowId(w), 0.0f, 0, stamp});
                            ++grains;
                            ++changed;
                            continue;
                        }
                        ++air;
                    } else if (type == CellType::Lava) {
                        ++grains;
                    }
                    next_.setCell(x, y, z, cur_.cell(x, y, z));
                }
            }
        }
        return StepCounts{grains, air, changed};
    }

    // Zamiana buforów, zapis historii i sprawdzenie warunku końca.
    VOLCANO_NOINLINE void finishStep(const StepCounts& c) {
        cur_.swap(next_);
        ++steps_;
        activeHistory_.push_back(c.active);
        changedHistory_.push_back(c.changed);
        if (p_.mode == CaMode::Lava && c.active == 0) {
            stop_ = StopReason::NoLava;
        } else if (p_.mode == CaMode::Classic && c.air == 0) {
            stop_ = StopReason::NoAir;
        } else if (c.changed == 0 && !nb_.isRandom()) {
            // Przy sąsiedztwie losowym krok bez zmian nie oznacza stanu końcowego —
            // w następnym kroku wylosowany wariant może sięgnąć do lawy.
            stop_ = StopReason::NoChange;
        } else if (steps_ >= p_.maxSteps) {
            stop_ = StopReason::MaxSteps;
        }
    }

    // Warunek końca przed pierwszym krokiem (np. classic bez wolnych komórek, maxSteps = 0).
    void countInitialState() {
        std::uint64_t lava = 0;
        std::uint64_t air = 0;
        for (int z = 0; z < dims_.nz; ++z) {
            for (int y = 0; y < dims_.ny; ++y) {
                for (int x = 0; x < dims_.nx; ++x) {
                    const CellType t = cur_.type(x, y, z);
                    lava += (t == CellType::Lava) ? 1 : 0;
                    air += (t == CellType::Air) ? 1 : 0;
                }
            }
        }
        stop_ = StopReason::Running;
        if (p_.mode == CaMode::Lava && lava == 0) {
            stop_ = StopReason::NoLava;
        } else if (p_.mode == CaMode::Classic && air == 0) {
            stop_ = StopReason::NoAir;
        } else if (p_.maxSteps <= 0) {
            stop_ = StopReason::MaxSteps;
        }
    }

    Dims dims_;
    CaParams p_;
    Neighborhood nb_;
    Boundary bc_;
    Storage cur_;
    Storage next_;
    std::vector<Offset> horizontal_;   // poziomi sąsiedzi (wypełnianie zagłębień)
    std::vector<Offset> sideOffsets_;  // komórki obok (ten sam poziom) — kierunki spływu
    bool diagonalFalls_ = false;       // czy sąsiedztwo pozwala spływać po skosie (dz=-1, dx/dy≠0)
    static constexpr int kMaxDrop = 16;  // urwisko głębsze niż tyle poziomów liczy się jak kMaxDrop
    static constexpr int kUnknown = -100;  // znacznik „jeszcze nie policzone”
    std::vector<std::int8_t> descent_;   // D(n) z bieżącego kroku, indeks globalIndex (bez ramki)
    Heightmap spill_;                  // poziom przelewu niecek dla każdej kolumny
    std::vector<Coord> ventByFlow_;    // położenie krateru wg flowId (indeks = flowId)
    int steps_ = 0;
    StopReason stop_ = StopReason::Running;
    std::vector<std::uint64_t> activeHistory_;
    std::vector<std::uint64_t> changedHistory_;
    bool phaseTiming_ = false;         // --timing-detail: mierzyć czasy faz kroku
    CaPhaseTimes phases_;
};

}  // namespace volcano
