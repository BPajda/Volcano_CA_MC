#pragma once
// Automat komórkowy spływu lawy (i klasycznego rozrostu ziaren) — szablon po
// reprezentacji siatki Storage (VectorStorage / MatrixStorage).
//
// Synchroniczny CA: nowy stan każdej komórki zależy tylko od stanu z początku kroku (cur_).
// Pełny przebieg pisze do drugiego bufora next_ i zamienia bufory (swap, bez kopiowania);
// automat frontalny zbiera zmiany na listach i stosuje je po regułach. W obu wersjach reguły
// czytają tylko cur_, więc pętla jest trywialnie równoległa (planowane OpenMP/MPI).
// Losowość pochodzi z hashRand(seed, krok, globalnyIndeks, sól) — wynik jest identyczny
// dla obu reprezentacji siatki (sprawdza to benchmark i testy).
// Reguły są opisane w CaRules.hpp.
//
// Dwa sposoby przetwarzania kroku (ca.sweep, etap 8) — wynik bitowo ten sam, łącznie z licznikami:
//   full  — pełny przebieg (wersja referencyjna): każda komórka cur_ -> next_, potem swap;
//   front — automat frontalny (domyślnie): tylko komórki, które w tym kroku MOGĄ się zmienić:
//           tryb lava — wszystkie komórki LAVA (stygną) + komórki AIR, które mają lawę wśród sąsiadów
//           (suma wszystkich wariantów sąsiedztwa, także „pod spodem” dla wypełniania zagłębień);
//           tryb classic — komórki AIR obok ziaren dodanych w poprzednim kroku + komórki AIR, które
//           były kandydatami, a nie zmieniły się (możliwe tylko przy sąsiedztwie losowym).
//           Inne komórki nie mogą się zmienić: AIR zmienia się tylko, gdy w sąsiedztwie jest lawa/ziarno,
//           ROCK i BASALT nigdy, ziarno classic nigdy. Krok czyta wyłącznie cur_ i zbiera listę zmian,
//           którą stosuje do cur_ po przetworzeniu wszystkich komórek (synchroniczność bez drugiego
//           bufora — next_ nie jest wtedy alokowany). Ramka jest wypełniana raz, potem tylko kopie
//           zmienionych komórek przy ścianach periodycznych (Boundary::syncCell). Liczniki (lawa, AIR,
//           zmiany) wychodzą z tych samych reguł, a komórki nieprzetworzone wnoszą stałe sumy.
//           Listy są trzymane osobno dla każdej warstwy (oś z; w płaszczyźnie x–y oś y): kandydatów
//           warstwy k wyznaczają tylko listy warstw k-1..k+1, reguły warstwy czytają tylko cur_
//           i piszą tylko listy tej warstwy — pod zrównoleglenie po warstwach (etap 9).
// OPTYMALIZACJA: automat frontalny zamiast pełnego przebiegu (99,99% przeszukań w lawie nic nie znajdowało).
//
// Wersja równoległa (OpenMP, etap 9; parallel.threads > 1) — podział przestrzeni na WARSTWY (oś z, w płaszczyźnie x–y
// oś y): iteracja pętli równoległej = jedna warstwa (pas jednej wartości z), harmonogram z configu dzieli warstwy
// między wątki (static bez porcji = równe ciągłe pasy warstw). Jeden region równoległy na krok, fazy rozdzielone barierami:
//   front — [D(n) lawy] | kandydaci + reguły warstwy (w jednej iteracji: kandydaci warstwy k powstają z src warstw
//           k-1..k+1, które w tej fazie się nie zmieniają) | zmiany do cur_ + kopie w ramce + nowe src;
//   full  — ramka (ściany osi po kolei) | [D(n)] | reguły: cur_ -> next_ dla wierszy warstwy.
// Każda faza pisze tylko elementy swojej warstwy (listy, znaczniki mark_, D(n) komórek lawy warstwy, komórki next_/cur_
// warstwy i ich kopie w ramce), a czyta stan z początku kroku albo wynik poprzedniej fazy (po barierze). Liczniki przez
// reduction. Wynik (siatka, liczba kroków, historia liczników, a nawet kolejność elementów list) jest więc bitowo ten
// sam dla każdej liczby wątków i każdego harmonogramu — warstwa jest zawsze liczona w całości przez jeden wątek tą samą
// funkcją. Przy 1 wątku kroki idą pętlami bez regionów OpenMP (jak w etapie 8).

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

#include "ca/CaRules.hpp"
#include "core/Boundary.hpp"
#include "core/Neighborhood.hpp"
#include "core/Profile.hpp"
#include "core/Storage.hpp"
#include "core/Timer.hpp"
#include "core/Types.hpp"
#include "parallel/Omp.hpp"
#include "parallel/ThreadStats.hpp"
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
    // Alokuje bufory — cała przestrzeń AIR: cur i next (full) albo tylko cur + znaczniki frontu (front).
    LavaCA(const Dims& dims, const CaParams& params, const Neighborhood& nb, const Boundary& bc)
        : dims_(dims),
          p_(params),
          nb_(nb),
          bc_(bc),
          cur_(dims),
          next_(params.frontSweep ? Storage() : Storage(dims)),
          front_(params.frontSweep) {
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
        // Sąsiedzi jako przesunięcia liniowe (etap 8): ta sama kolejność co w wariantach sąsiedztwa.
        for (int v = 0; v < nb_.variantCount(); ++v) {
            std::vector<NbStep> list;
            for (const Offset& o : nb_.variant(v)) {
                list.push_back(NbStep{o, cur_.linear(o)});
            }
            nbSteps_.push_back(list);
        }
        for (const Offset& o : sideOffsets_) {
            side_.push_back(NbStep{o, cur_.linear(o)});
        }
        // Oś warstw (podział na wątki, etap 9; listy automatu frontalnego): z, a w płaszczyźnie x–y (nz = 1) — y.
        layerZ_ = dims.nz > 1;
        // Automat frontalny: przesunięcia wszystkich wariantów pogrupowane wg przesunięcia w osi warstw (-1, 0, 1)
        // i znaczniki „komórka jest już na liście kandydatów”.
        if (front_) {
            layerPeriodic_ = layerZ_ ? bc_.periodicZ() : bc_.periodicY();
            std::vector<Offset> all;
            for (int v = 0; v < nb_.variantCount(); ++v) {
                for (const Offset& o : nb_.variant(v)) {
                    addUnique(all, o);
                }
            }
            for (const Offset& o : all) {
                rev_[(layerZ_ ? o.dz : o.dy) + 1].push_back(o);
            }
            mark_.assign(dims.cells(), 0);
        }
    }

    // Ustawienia równoległości (etap 9) — przed applyTerrain / placeSeeds. Domyślnie 1 wątek (kod jak w etapie 8).
    void setParallel(const ParallelSettings& par) { par_ = par; }
    const ParallelSettings& parallelSettings() const { return par_; }

    // Nazwy faz kroku w statystykach wątków (--thread-stats) — w kolejności numerów faz używanych w regionach.
    static std::vector<std::string> threadPhases(bool front, CaMode mode) {
        if (front) {
            return mode == CaMode::Lava ? std::vector<std::string>{"descent", "rules", "apply"}
                                        : std::vector<std::string>{"rules", "apply"};
        }
        return mode == CaMode::Lava ? std::vector<std::string>{"frame", "descent", "rules"}
                                    : std::vector<std::string>{"frame", "rules"};
    }

    // Teren: ROCK w kolumnie (x, y) dla z < h(x, y). Tylko tryb lava.
    // Liczy też poziomy przelewu niecek (reguła wypełniania zagłębień) — priority-flood jest sekwencyjny;
    // kolumny skały wpisują wątki (wiersz y = iteracja, każda kolumna pisze tylko swoje komórki).
    void applyTerrain(const Heightmap& hm) {
        const auto row = [&](std::ptrdiff_t yi) {
            const int y = static_cast<int>(yi);
            for (int x = 0; x < dims_.nx; ++x) {
                const int h = std::min(hm.at(x, y), dims_.nz);
                for (int z = 0; z < h; ++z) {
                    cur_.setType(x, y, z, CellType::Rock);
                }
            }
        };
        if (par_.parallel()) {
#ifdef _OPENMP
#  pragma omp parallel num_threads(par_.threads)
#endif
            ompFor(dims_.ny, Schedule::Static, 0, row);
        } else {
            for (int y = 0; y < dims_.ny; ++y) {
                row(y);
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
        } else if (front_) {
            stepFront();
        } else if (p_.mode == CaMode::Lava) {
            stepLava();
        } else {
            stepClassic();
        }
        return !finished();
    }

    // Czy krok idzie automatem frontalnym (ca.sweep = front).
    bool frontSweep() const { return front_; }

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

    // Wynik w postaci płaskiej mikrostruktury (bez ramki); kopia wierszami dzielonymi między wątki (etap 9).
    Microstructure result() const { return toMicrostructure(cur_, par_.threads); }

    // --- profil (etap 3) ---

    // Pomiar czasów faz kroku (--timing-detail): kroki idą wtedy przez stepTimed(). Domyślnie wyłączony.
    void enablePhaseTiming(bool on) { phaseTiming_ = on; }
    const CaPhaseTimes& phaseTimes() const { return phases_; }

    // Pamięć buforów z ramką [B] (dane komórek; MatrixStorage bez narzutu alokacji wierszy):
    // full — cur i next, front — tylko cur.
    std::size_t gridBytes() const { return cur_.bytes() + next_.bytes(); }
    // Pamięć tablic pomocniczych [B]: D(n) (tryb lava), poziomy przelewu niecek, znaczniki frontu.
    std::size_t auxBytes() const {
        return descent_.size() * sizeof(std::int8_t) + spill_.height.size() * sizeof(int) +
               mark_.size() * sizeof(std::uint8_t);
    }
    // Pamięć list automatu frontalnego [B] (pojemność — największy rozmiar w trakcie przebiegu).
    std::size_t frontBytes() const {
        std::size_t b = layers_.capacity() * sizeof(FrontLayer);
        for (const FrontLayer& l : layers_) {
            b += (l.src.capacity() + l.cand.capacity() + l.nextSrc.capacity()) * sizeof(Coord) +
                 l.changes.capacity() * sizeof(Change);
        }
        return b;
    }

private:
    using Pos = typename Storage::Pos;

    // Położenie komórki (do tablicy kraterów).
    struct Coord {
        int x;
        int y;
        int z;
    };

    // Sąsiad: przesunięcie (dx, dy, dz) i odpowiadające mu przesunięcie liniowe w buforze z ramką.
    // OPTYMALIZACJA (etap 8): sąsiad = pozycja + lin zamiast indeksu z (x, y, z) przy każdym odczycie.
    struct NbStep {
        Offset o;
        std::ptrdiff_t lin;
    };

    // Zmiana jednej komórki w kroku automatu frontalnego: położenie i nowy stan.
    struct Change {
        Coord c;
        CellState s;
    };

    // Listy automatu frontalnego dla jednej warstwy (wartość osi z; w płaszczyźnie x–y osi y).
    struct FrontLayer {
        std::vector<Coord> src;       // lava: komórki LAVA; classic: ziarna dodane w poprzednim kroku
        std::vector<Coord> cand;      // komórki AIR do sprawdzenia w tym kroku (bez powtórzeń — mark_)
        std::vector<Coord> nextSrc;   // src na następny krok (budowana przez reguły)
        std::vector<Change> changes;  // zmiany tego kroku (stosowane po regułach wszystkich warstw)
    };

    // Lista sąsiadów komórki idx w kroku o stałej części hasha prefix = hashPrefix(seed, krok) —
    // ten sam wariant co nb_.offsetsFor(seed, krok, idx), bez pełnej kaskady hashRand na komórkę.
    const std::vector<NbStep>& stepsFor(std::uint64_t prefix, std::uint64_t idx) const {
        return nbSteps_[static_cast<std::size_t>(nb_.variantFromPrefix(prefix, idx))];
    }

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
    VOLCANO_NOINLINE int descent(int x, int y, int z, Pos p) const {
        int best = 0;
        for (const NbStep& h : side_) {
            if (cur_.type(Storage::shifted(p, h.o, h.lin)) == CellType::Air) {
                best = std::max(best, dropDepth(x + h.o.dx, y + h.o.dy, z));
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
    // p = pozycja c w buforze, prefix = hashPrefix(seed, t) (wybór wariantu sąsiedztwa).
    VOLCANO_NOINLINE void gatherLavaCandidates(int x, int y, int z, Pos p, std::uint64_t prefix,
                                               std::uint64_t idx, CandidateVote& vote) const {
        vote.clear();
        int cDrop = kUnknown;  // spadek z komórki c — liczony leniwie
        for (const NbStep& s : stepsFor(prefix, idx)) {
            const Offset& o = s.o;
            if (o.dz < 0) {
                // Lawa się nie wspina: sąsiad poniżej nie wpływa do c.
                // Wyjątek: wypełnianie zagłębienia z komórki dokładnie pod c.
                if (p_.ponding && o.dx == 0 && o.dy == 0) {
                    tryPonding(x, y, z, vote);
                }
                continue;
            }
            if (cur_.type(Storage::shifted(p, o, s.lin)) != CellType::Lava) {
                continue;  // (ramka absorbująca to VOID — nigdy nie jest lawą)
            }
            // Dalej (rzadko — sąsiad jest lawą) współrzędne jak dotąd.
            const int sz = z + o.dz;
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

    // Liczba warstw (oś z, w płaszczyźnie x–y oś y) — iteracje pętli równoległych.
    int layerCount() const { return layerZ_ ? dims_.nz : dims_.ny; }

    // Wiersze siatki warstw [k0, k1): z ∈ [z0, z1), y ∈ [y0, y1). Wiersze idą w kolejności pamięci, więc globalIndex
    // rośnie o 1 wzdłuż x i o nx między kolejnymi wierszami.
    struct RowRange {
        int z0;
        int z1;
        int y0;
        int y1;
    };
    RowRange rowsOf(int k0, int k1) const { return layerZ_ ? RowRange{k0, k1, 0, dims_.ny} : RowRange{0, 1, k0, k1}; }

    // Stała część kroku: numer kroku t, czy trwa erupcja, znacznik solidStep / arrivalStep (uint16 — stąd
    // ca.maxSteps <= 65535) i stała część hasha hashPrefix(seed, t).
    struct StepCtx {
        std::uint64_t t;
        bool erupting;
        std::uint16_t stamp;
        std::uint64_t prefix;
    };
    StepCtx stepContext() const {
        const std::uint64_t t = static_cast<std::uint64_t>(steps_);
        return StepCtx{t, steps_ < p_.eruptionSteps, static_cast<std::uint16_t>(std::min(steps_, 65535)),
                       hashPrefix(p_.seed, t)};
    }

    // Przed krokiem: największy spadek D(n) dla każdej komórki lawy leżącej na gruncie
    // (-1 dla pozostałych) — warstwy [k0, k1). Osobny przebieg, bo D(n) jest potrzebne wielu sąsiadom n —
    // bez tego liczylibyśmy je kilkanaście razy na krok. Czyta tylko cur_, pisze D(n) komórek swoich warstw.
    VOLCANO_NOINLINE void computeDescent(int k0, int k1) {
        const RowRange r = rowsOf(k0, k1);
        std::size_t i = static_cast<std::size_t>(globalIndex(dims_, 0, r.y0, r.z0));
        for (int z = r.z0; z < r.z1; ++z) {
            for (int y = r.y0; y < r.y1; ++y) {
                Pos p = cur_.pos(0, y, z);
                for (int x = 0; x < dims_.nx; ++x, ++i, p = Storage::nextX(p)) {
                    std::int8_t d = -1;
                    if (cur_.type(p) == CellType::Lava && hasSupport(x, y, z)) {
                        d = static_cast<std::int8_t>(descent(x, y, z, p));
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

    // Krok trybu lava (pełny przebieg): ramka -> D(n) -> reguły -> zamiana buforów.
    VOLCANO_NOINLINE void stepLava() {
        if (par_.parallel()) {
            finishStep(fullStepParallel(nullptr));
            return;
        }
        bc_.apply(cur_);
        computeDescent(0, layerCount());
        CandidateVote vote;
        StepCounts c;
        updateLava(stepContext(), 0, layerCount(), vote, c);
        finishStep(c);
    }

    // Krok trybu classic (rozrost ziaren bez grawitacji i temperatury): ramka -> reguły -> zamiana.
    VOLCANO_NOINLINE void stepClassic() {
        if (par_.parallel()) {
            finishStep(fullStepParallel(nullptr));
            return;
        }
        bc_.apply(cur_);
        CandidateVote vote;
        StepCounts c;
        updateClassic(stepContext(), 0, layerCount(), vote, c);
        finishStep(c);
    }

    // Pełny przebieg w wielu wątkach (etap 9): jeden region równoległy na krok — ramka (ściany każdej osi między
    // wątkami, bariera po osi), D(n) warstw (bariera — reguły czytają D(n) sąsiadów z innych warstw), reguły warstw
    // cur_ -> next_ (każda warstwa pisze tylko swoje komórki next_). lap != nullptr — czasy faz (--timing-detail).
    VOLCANO_NOINLINE StepCounts fullStepParallel(LapTimer* lap) {
        const StepCtx ctx = stepContext();
        const std::ptrdiff_t nl = layerCount();
        const bool lavaMode = p_.mode == CaMode::Lava;
        const Schedule sched = par_.schedule;
        const int chunk = par_.chunk;
        ThreadStats* const ts = par_.stats;
        const double wall0 = ts != nullptr ? omp_get_wtime() : 0.0;
        std::uint64_t active = 0;
        std::uint64_t air = 0;
        std::uint64_t changed = 0;
#ifdef _OPENMP
#  pragma omp parallel num_threads(par_.threads) reduction(+ : active, air, changed)
#endif
        {
            const int tid = omp_get_thread_num();
            PhaseClock clock(ts, tid);
            if (ts != nullptr) {
                ts->noteCpu(tid);
            }
            int ph = 0;
            clock.begin();
            bc_.applyWith(cur_, [&](std::ptrdiff_t n, const auto& body) {
                ompFor(n, Schedule::Static, 0, body);
                ompBarrier();
            });
            clock.end(ph++);
            if (tid == 0 && lap != nullptr) {
                lap->lap(phases_.frame);
            }
            if (lavaMode) {
                clock.begin();
                ompFor(nl, sched, chunk, [&](std::ptrdiff_t k) {
                    computeDescent(static_cast<int>(k), static_cast<int>(k) + 1);
                });
                clock.end(ph++);
                ompBarrier();
                if (tid == 0 && lap != nullptr) {
                    lap->lap(phases_.descent);
                }
            }
            CandidateVote vote;
            StepCounts local;
            clock.begin();
            ompFor(nl, sched, chunk, [&](std::ptrdiff_t k) {
                if (lavaMode) {
                    updateLava(ctx, static_cast<int>(k), static_cast<int>(k) + 1, vote, local);
                } else {
                    updateClassic(ctx, static_cast<int>(k), static_cast<int>(k) + 1, vote, local);
                }
            });
            clock.end(ph);
            active += local.active;
            air += local.air;
            changed += local.changed;
        }
        if (lap != nullptr) {
            lap->lap(phases_.rules);
        }
        if (ts != nullptr) {
            ts->addWall(omp_get_wtime() - wall0);
            ts->endStep();
        }
        return StepCounts{active, air, changed};
    }

    // ===================== automat frontalny (ca.sweep = front, etap 8) =====================

    // Sumy reguł automatu frontalnego w kroku (w wersji równoległej — redukcja po wątkach).
    struct RuleSums {
        std::uint64_t stay = 0;     // lawa, która pozostała lawą
        std::uint64_t changed = 0;  // komórki zmienione
        std::uint64_t born = 0;     // nowe komórki lawy / ziarna
    };

    // Krok automatu frontalnego: D(n) dla lawy -> kandydaci i reguły (czytają cur_) -> zmiany do cur_.
    VOLCANO_NOINLINE void stepFront() {
        if (!frontReady_) {
            initFront();
        }
        finishStep(par_.parallel() ? frontStepParallel(nullptr) : frontStepSequential(nullptr));
    }

    // Przed pierwszym krokiem: ramka (raz — dalej Boundary::syncCell), listy lawy / ziaren z całej siatki
    // i sumy komórek LAVA i AIR (komórki spoza frontu wnoszą do liczników stałe wartości). Warstwy przeglądane
    // niezależnie — w wielu wątkach każda warstwa buduje tylko swoją listę src.
    VOLCANO_NOINLINE void initFront() {
        bc_.apply(cur_);
        layers_.assign(static_cast<std::size_t>(layerCount()), FrontLayer{});
        std::uint64_t lava = 0;
        std::uint64_t air = 0;
        if (par_.parallel()) {
#ifdef _OPENMP
#  pragma omp parallel num_threads(par_.threads) reduction(+ : lava, air)
#endif
            ompFor(layerCount(), Schedule::Static, 0,
                   [&](std::ptrdiff_t k) { scanLayer(static_cast<int>(k), lava, air); });
        } else {
            for (int k = 0; k < layerCount(); ++k) {
                scanLayer(k, lava, air);
            }
        }
        lavaTotal_ = lava;
        airTotal_ = air;
        frontReady_ = true;
    }

    // Lista src warstwy k (komórki LAVA w kolejności pamięci) i liczba komórek LAVA / AIR warstwy (dodawane do lavaOut,
    // airOut). Liczniki lokalne: przez referencję MSVC zapisywał je do pamięci w każdej iteracji (A/B: 3× wolniej).
    void scanLayer(int k, std::uint64_t& lavaOut, std::uint64_t& airOut) {
        FrontLayer& l = layers_[static_cast<std::size_t>(k)];
        const RowRange r = rowsOf(k, k + 1);
        std::uint64_t lava = 0;
        std::uint64_t air = 0;
        for (int z = r.z0; z < r.z1; ++z) {
            for (int y = r.y0; y < r.y1; ++y) {
                for (int x = 0; x < dims_.nx; ++x) {
                    const CellType t = cur_.type(x, y, z);
                    if (t == CellType::Lava) {
                        l.src.push_back(Coord{x, y, z});
                        ++lava;
                    } else if (t == CellType::Air) {
                        ++air;
                    }
                }
            }
        }
        lavaOut += lava;
        airOut += air;
    }

    // Krok frontalny w jednym wątku (jak w etapie 8; kandydaci i reguły warstwy w jednej pętli — kandydaci warstwy k
    // zależą tylko od src warstw k-1..k+1, których reguły nie zmieniają). lap != nullptr — czasy faz.
    VOLCANO_NOINLINE StepCounts frontStepSequential(LapTimer* lap) {
        const StepCtx ctx = stepContext();
        const int nl = static_cast<int>(layers_.size());
        const bool periodic = bc_.periodicX() || bc_.periodicY() || bc_.periodicZ();
        if (p_.mode == CaMode::Lava) {
            frontDescent(0, nl);
            if (lap != nullptr) {
                lap->lap(phases_.descent);
            }
        }
        RuleSums sums;
        CandidateVote vote;
        frontCandidatesRules(0, nl, ctx, vote, sums);
        if (lap != nullptr) {
            lap->lap(phases_.rules);
        }
        return frontCounts(sums, frontApply(0, nl, periodic));
    }

    // Krok frontalny w wielu wątkach (etap 9): jeden region na krok, warstwy dzielone między wątki wg harmonogramu.
    //   faza 1 (lava): D(n) komórek lawy warstwy — bariera, bo reguły czytają D(n) źródeł z sąsiednich warstw;
    //   faza 2: kandydaci warstwy (z src warstw k-1..k+1 — w tej fazie niezmienne) i reguły warstwy (czytają cur_,
    //           piszą listy i znaczniki tylko swojej warstwy) — bariera, bo faza 3 zmienia cur_;
    //   faza 3: zmiany warstwy do cur_ (+ kopie w ramce periodycznej — różne komórki ramki dla różnych komórek)
    //           i nowe src warstwy.
    // Liczniki przez reduction. lap != nullptr — czasy faz mierzone przez wątek 0 po barierach (--timing-detail).
    VOLCANO_NOINLINE StepCounts frontStepParallel(LapTimer* lap) {
        const StepCtx ctx = stepContext();
        const std::ptrdiff_t nl = static_cast<std::ptrdiff_t>(layers_.size());
        const bool lavaMode = p_.mode == CaMode::Lava;
        const bool periodic = bc_.periodicX() || bc_.periodicY() || bc_.periodicZ();
        const Schedule sched = par_.schedule;
        const int chunk = par_.chunk;
        ThreadStats* const ts = par_.stats;
        const double wall0 = ts != nullptr ? omp_get_wtime() : 0.0;
        std::uint64_t stay = 0;
        std::uint64_t changed = 0;
        std::uint64_t born = 0;
        std::uint64_t lava = 0;
#ifdef _OPENMP
#  pragma omp parallel num_threads(par_.threads) reduction(+ : stay, changed, born, lava)
#endif
        {
            const int tid = omp_get_thread_num();
            PhaseClock clock(ts, tid);
            if (ts != nullptr) {
                ts->noteCpu(tid);
            }
            int ph = 0;
            if (lavaMode) {
                clock.begin();
                ompFor(nl, sched, chunk, [&](std::ptrdiff_t k) {
                    frontDescent(static_cast<int>(k), static_cast<int>(k) + 1);
                });
                clock.end(ph++);
                ompBarrier();
                if (tid == 0 && lap != nullptr) {
                    lap->lap(phases_.descent);
                }
            }
            RuleSums sums;
            CandidateVote vote;
            clock.begin();
            ompFor(nl, sched, chunk, [&](std::ptrdiff_t k) {
                frontCandidatesRules(static_cast<int>(k), static_cast<int>(k) + 1, ctx, vote, sums);
            });
            clock.end(ph++);
            stay += sums.stay;
            changed += sums.changed;
            born += sums.born;
            ompBarrier();
            if (tid == 0 && lap != nullptr) {
                lap->lap(phases_.rules);
            }
            clock.begin();
            ompFor(nl, sched, chunk, [&](std::ptrdiff_t k) {
                lava += frontApply(static_cast<int>(k), static_cast<int>(k) + 1, periodic);
            });
            clock.end(ph);
        }
        if (ts != nullptr) {
            ts->addWall(omp_get_wtime() - wall0);
            ts->endStep();
        }
        RuleSums sums;
        sums.stay = stay;
        sums.changed = changed;
        sums.born = born;
        return frontCounts(sums, lava);
    }

    // Liczniki kroku jak w pełnym przebiegu (lava — lawa po kroku; classic — wszystkie ziarna; AIR — wolne komórki)
    // i nowe sumy komórek LAVA / AIR (lava = łączna długość nowych list src).
    StepCounts frontCounts(const RuleSums& s, std::uint64_t lava) {
        const bool lavaMode = p_.mode == CaMode::Lava;
        const StepCounts c{lavaMode ? s.stay + s.born : lavaTotal_ + s.born, airTotal_ - s.born, s.changed};
        lavaTotal_ = lavaMode ? lava : lavaTotal_ + s.born;
        airTotal_ -= s.born;
        return c;
    }

    // D(n) tylko dla komórek lawy warstw [k0, k1) (descent_ jest czytane wyłącznie dla źródła, które jest lawą —
    // wartości dla pozostałych komórek nie są używane, więc nie trzeba ich zerować co krok jak w computeDescent).
    // Funkcje frontu dostają zakres warstw: 1 wątek — wszystkie warstwy jednym wywołaniem (pętla po warstwach w środku,
    // jak w etapie 8 — wywołanie na każdą warstwę dawało w 2D ~5% narzutu), wiele wątków — po jednej warstwie.
    void frontDescent(int k0, int k1) {
        for (int k = k0; k < k1; ++k) {
            for (const Coord& c : layers_[static_cast<std::size_t>(k)].src) {
                const Pos p = cur_.pos(c.x, c.y, c.z);
                std::int8_t d = -1;
                if (hasSupport(c.x, c.y, c.z)) {
                    d = static_cast<std::int8_t>(descent(c.x, c.y, c.z, p));
                }
                descent_[static_cast<std::size_t>(globalIndex(dims_, c.x, c.y, c.z))] = d;
            }
        }
    }

    // Współrzędne sąsiada w odwróconym kierunku: zawinięcie w osiach periodycznych, false poza wnętrzem
    // w osiach absorbujących (tam ramka to VOID — nie wpływa na nic).
    bool insideWrapped(int& x, int& y, int& z) const {
        const auto fix = [](int& v, int n, bool periodic) {
            if (v >= 0 && v < n) {
                return true;
            }
            if (!periodic) {
                return false;
            }
            v = v < 0 ? v + n : v - n;
            return true;
        };
        return fix(x, dims_.nx, bc_.periodicX()) && fix(y, dims_.ny, bc_.periodicY()) &&
               fix(z, dims_.nz, bc_.periodicZ());
    }

    // Kandydaci warstwy k: komórki AIR c, dla których jakieś src L leży w sąsiedztwie c (L = c + o dla przesunięcia
    // o z dowolnego wariantu, więc c = L - o). Kandydaci warstwy k pochodzą tylko z src warstw k-1..k+1
    // (grupa przesunięć rev_[d] daje warstwę k z warstwy k + d) — warstwa pisze tylko własną listę
    // i własne znaczniki, więc warstwy można liczyć równolegle. Classic: lista cand zostaje z poprzedniego
    // kroku (kandydaci, którzy się nie zmienili — sąsiedztwo losowe); znaczniki pilnują braku powtórzeń.
    void frontCandidatesLayer(int k, int nl) {
        FrontLayer& dst = layers_[static_cast<std::size_t>(k)];
        for (int d = -1; d <= 1; ++d) {
            int s = k + d;
            if (s < 0 || s >= nl) {
                if (!layerPeriodic_) {
                    continue;
                }
                s = wrap(s, nl);
            }
            const std::vector<Offset>& group = rev_[d + 1];
            for (const Coord& l : layers_[static_cast<std::size_t>(s)].src) {
                for (const Offset& o : group) {
                    int x = l.x - o.dx;
                    int y = l.y - o.dy;
                    int z = l.z - o.dz;
                    if (!insideWrapped(x, y, z)) {
                        continue;
                    }
                    std::uint8_t& m = mark_[static_cast<std::size_t>(globalIndex(dims_, x, y, z))];
                    if (m != 0 || cur_.type(x, y, z) != CellType::Air) {
                        continue;
                    }
                    m = 1;
                    dst.cand.push_back(Coord{x, y, z});
                }
            }
        }
    }

    // Kandydaci i reguły warstw [k0, k1): dla każdej warstwy najpierw jej kandydaci (frontCandidatesLayer), potem
    // reguły (frontRulesLayer) — czytają tylko cur_, piszą listy zmian i nowe src warstwy oraz znaczniki jej komórek;
    // sumy dodawane do sumsOut (w wersji równoległej — sumy wątku, potem redukcja).
    void frontCandidatesRules(int k0, int k1, const StepCtx ctx, CandidateVote& vote, RuleSums& sumsOut) {
        const int nl = static_cast<int>(layers_.size());
        for (int k = k0; k < k1; ++k) {
            frontCandidatesLayer(k, nl);
            const RuleSums r = frontRulesLayer(k, ctx, vote);
            sumsOut.stay += r.stay;
            sumsOut.changed += r.changed;
            sumsOut.born += r.born;
        }
    }

    // Reguły warstwy k (te same co w updateLava / updateClassic). Liczniki — zmienne lokalne zwracane przez wartość:
    // przez referencję MSVC zapisywał je do pamięci przy każdej zmianie (push_back mógłby je zmienić) i krok przy
    // 1 wątku był o 4–5% wolniejszy.
    RuleSums frontRulesLayer(int k, const StepCtx& ctx, CandidateVote& vote) {
        std::uint64_t stay = 0;     // lawa, która pozostała lawą
        std::uint64_t changed = 0;
        std::uint64_t born = 0;     // nowe komórki lawy / ziarna
        FrontLayer& l = layers_[static_cast<std::size_t>(k)];
        l.changes.clear();
        l.nextSrc.clear();
        if (p_.mode == CaMode::Lava) {
            // Komórki lawy: krater w trakcie erupcji ma eruptTemp, reszta stygnie; poniżej solidusa — bazalt.
            for (const Coord& c : l.src) {
                CellState s = cur_.cell(cur_.pos(c.x, c.y, c.z));
                const float before = s.temp;
                if (ctx.erupting && isVent(s.flowId, c.x, c.y, c.z)) {
                    s.temp = p_.eruptTemp;
                } else {
                    s.temp -= p_.coolingAmbient;
                }
                if (s.temp < p_.solidusTemp) {
                    s.type = CellType::Basalt;
                    s.solidStep = ctx.stamp;
                    ++changed;
                    l.changes.push_back(Change{c, s});
                } else {
                    ++stay;
                    l.nextSrc.push_back(c);
                    if (s.temp != before) {
                        ++changed;
                        l.changes.push_back(Change{c, s});
                    }
                }
            }
            // Komórki AIR obok lawy: kandydaci, głosowanie, temperatura >= solidus -> lawa.
            for (const Coord& c : l.cand) {
                const std::uint64_t idx = globalIndex(dims_, c.x, c.y, c.z);
                mark_[static_cast<std::size_t>(idx)] = 0;
                gatherLavaCandidates(c.x, c.y, c.z, cur_.pos(c.x, c.y, c.z), ctx.prefix, idx, vote);
                if (!vote.empty()) {
                    const int w = vote.winner(p_.seed, ctx.t, idx);
                    const float temp = vote.maxTemp(w);
                    if (temp >= p_.solidusTemp) {
                        l.changes.push_back(
                            Change{c, CellState{CellType::Lava, vote.flowId(w), temp, 0, ctx.stamp}});
                        l.nextSrc.push_back(c);
                        ++born;
                        ++changed;
                    }
                }
            }
            l.cand.clear();
        } else {
            // Classic: AIR z sąsiadem-ziarnem dostaje najczęstszy flowId; bez zmiany zostaje kandydatem.
            std::size_t keep = 0;
            for (std::size_t i = 0; i < l.cand.size(); ++i) {
                const Coord c = l.cand[i];
                const std::uint64_t idx = globalIndex(dims_, c.x, c.y, c.z);
                const Pos p = cur_.pos(c.x, c.y, c.z);
                vote.clear();
                for (const NbStep& st : stepsFor(ctx.prefix, idx)) {
                    const Pos n = Storage::shifted(p, st.o, st.lin);
                    if (cur_.type(n) == CellType::Lava) {
                        vote.add(cur_.flowId(n), 0.0f);
                    }
                }
                if (!vote.empty()) {
                    const int w = vote.winner(p_.seed, ctx.t, idx);
                    l.changes.push_back(Change{c, CellState{CellType::Lava, vote.flowId(w), 0.0f, 0, ctx.stamp}});
                    l.nextSrc.push_back(c);
                    mark_[static_cast<std::size_t>(idx)] = 0;
                    ++born;
                    ++changed;
                } else {
                    l.cand[keep++] = c;
                }
            }
            l.cand.resize(keep);
        }
        RuleSums out;
        out.stay = stay;
        out.changed = changed;
        out.born = born;
        return out;
    }

    // Zmiany warstw [k0, k1) do cur_ (po regułach wszystkich warstw), kopie zmienionych komórek w ramce periodycznej
    // i nowe listy src. Zwraca łączną liczbę komórek nowych src.
    std::uint64_t frontApply(int k0, int k1, bool periodic) {
        std::uint64_t lava = 0;
        for (int k = k0; k < k1; ++k) {
            FrontLayer& l = layers_[static_cast<std::size_t>(k)];
            for (const Change& ch : l.changes) {
                cur_.setCell(cur_.pos(ch.c.x, ch.c.y, ch.c.z), ch.s);
                if (periodic) {
                    bc_.syncCell(cur_, ch.c.x, ch.c.y, ch.c.z);
                }
            }
            l.src.swap(l.nextSrc);
            lava += l.src.size();
        }
        return lava;
    }

    // Ten sam krok z pomiarem czasu faz (--timing-detail). Osobna ścieżka: stoper wewnątrz
    // stepLava zmieniał kod generowany przez MSVC dla głównej pętli (krok lawy wolniejszy
    // o ~10% — test A/B w profilu z etapu 3), a zwykły przebieg ma zostać punktem odniesienia.
    // W wielu wątkach fazy mierzy wątek 0 po barierach.
    VOLCANO_NOINLINE void stepTimed() {
        LapTimer phase(true);
        if (front_) {
            // Automat frontalny: ramka = wypełnienie przy pierwszym kroku, reguły = kandydaci + reguły,
            // koniec kroku = zmiany do cur_ (z kopiami w ramce periodycznej), historia, warunek końca.
            if (!frontReady_) {
                initFront();
            }
            phase.lap(phases_.frame);
            const StepCounts c = par_.parallel() ? frontStepParallel(&phase) : frontStepSequential(&phase);
            finishStep(c);
            phase.lap(phases_.finish);
            return;
        }
        StepCounts counts;
        if (par_.parallel()) {
            counts = fullStepParallel(&phase);
        } else {
            bc_.apply(cur_);
            phase.lap(phases_.frame);
            CandidateVote vote;
            if (p_.mode == CaMode::Lava) {
                computeDescent(0, layerCount());
                phase.lap(phases_.descent);
                updateLava(stepContext(), 0, layerCount(), vote, counts);
            } else {
                updateClassic(stepContext(), 0, layerCount(), vote, counts);
            }
            phase.lap(phases_.rules);
        }
        finishStep(counts);
        phase.lap(phases_.finish);
    }

    // Reguły lawy dla komórek warstw [k0, k1): czyta cur_, pisze next_, dodaje do c liczbę lawy, AIR i zmian.
    VOLCANO_NOINLINE void updateLava(const StepCtx ctx, int k0, int k1, CandidateVote& vote, StepCounts& counts) {
        std::uint64_t lava = 0;
        std::uint64_t air = 0;
        std::uint64_t changed = 0;
        const RowRange r = rowsOf(k0, k1);
        std::uint64_t idx = globalIndex(dims_, 0, r.y0, r.z0);  // pętle idą w kolejności pamięci
        for (int z = r.z0; z < r.z1; ++z) {
            for (int y = r.y0; y < r.y1; ++y) {
                Pos p = cur_.pos(0, y, z);  // pozycja (x, y, z) w obu buforach
                for (int x = 0; x < dims_.nx; ++x, ++idx, p = Storage::nextX(p)) {
                    const CellType type = cur_.type(p);
                    if (type == CellType::Air) {
                        gatherLavaCandidates(x, y, z, p, ctx.prefix, idx, vote);
                        if (!vote.empty()) {
                            const int w = vote.winner(p_.seed, ctx.t, idx);
                            const float temp = vote.maxTemp(w);
                            if (temp >= p_.solidusTemp) {
                                next_.setCell(p, CellState{CellType::Lava, vote.flowId(w), temp, 0, ctx.stamp});
                                ++lava;
                                ++changed;
                                continue;
                            }
                        }
                        next_.setCell(p, cur_.cell(p));
                        ++air;
                    } else if (type == CellType::Lava) {
                        CellState c = cur_.cell(p);
                        const float before = c.temp;
                        if (ctx.erupting && isVent(c.flowId, x, y, z)) {
                            c.temp = p_.eruptTemp;  // krater zasilany z komina
                        } else {
                            c.temp -= p_.coolingAmbient;
                        }
                        if (c.temp < p_.solidusTemp) {
                            c.type = CellType::Basalt;
                            c.solidStep = ctx.stamp;
                            ++changed;
                        } else {
                            ++lava;
                            changed += (c.temp != before) ? 1 : 0;
                        }
                        next_.setCell(p, c);
                    } else {
                        next_.setCell(p, cur_.cell(p));  // ROCK, BASALT
                    }
                }
            }
        }
        counts.active += lava;
        counts.air += air;
        counts.changed += changed;
    }

    // Reguły rozrostu klasycznego dla komórek warstw [k0, k1): czyta cur_, pisze next_.
    VOLCANO_NOINLINE void updateClassic(const StepCtx ctx, int k0, int k1, CandidateVote& vote, StepCounts& counts) {
        std::uint64_t grains = 0;
        std::uint64_t air = 0;
        std::uint64_t changed = 0;
        const RowRange r = rowsOf(k0, k1);
        std::uint64_t idx = globalIndex(dims_, 0, r.y0, r.z0);
        for (int z = r.z0; z < r.z1; ++z) {
            for (int y = r.y0; y < r.y1; ++y) {
                Pos p = cur_.pos(0, y, z);
                for (int x = 0; x < dims_.nx; ++x, ++idx, p = Storage::nextX(p)) {
                    const CellType type = cur_.type(p);
                    if (type == CellType::Air) {
                        vote.clear();
                        for (const NbStep& s : stepsFor(ctx.prefix, idx)) {
                            const Pos n = Storage::shifted(p, s.o, s.lin);
                            if (cur_.type(n) == CellType::Lava) {
                                vote.add(cur_.flowId(n), 0.0f);
                            }
                        }
                        if (!vote.empty()) {
                            const int w = vote.winner(p_.seed, ctx.t, idx);
                            next_.setCell(p, CellState{CellType::Lava, vote.flowId(w), 0.0f, 0, ctx.stamp});
                            ++grains;
                            ++changed;
                            continue;
                        }
                        ++air;
                    } else if (type == CellType::Lava) {
                        ++grains;
                    }
                    next_.setCell(p, cur_.cell(p));
                }
            }
        }
        counts.active += grains;
        counts.air += air;
        counts.changed += changed;
    }

    // Zamiana buforów (pełny przebieg; automat frontalny pisze od razu do cur_), zapis historii i warunek końca.
    VOLCANO_NOINLINE void finishStep(const StepCounts& c) {
        if (!front_) {
            cur_.swap(next_);
        }
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

    // Komórki LAVA i AIR warstw [k0, k1) (stan początkowy), dodawane do lavaOut, airOut (liczniki lokalne — jak
    // scanLayer).
    void countLayers(int k0, int k1, std::uint64_t& lavaOut, std::uint64_t& airOut) const {
        const RowRange r = rowsOf(k0, k1);
        std::uint64_t lava = 0;
        std::uint64_t air = 0;
        for (int z = r.z0; z < r.z1; ++z) {
            for (int y = r.y0; y < r.y1; ++y) {
                for (int x = 0; x < dims_.nx; ++x) {
                    const CellType t = cur_.type(x, y, z);
                    lava += (t == CellType::Lava) ? 1 : 0;
                    air += (t == CellType::Air) ? 1 : 0;
                }
            }
        }
        lavaOut += lava;
        airOut += air;
    }

    // Warunek końca przed pierwszym krokiem (np. classic bez wolnych komórek, maxSteps = 0).
    void countInitialState() {
        std::uint64_t lava = 0;
        std::uint64_t air = 0;
        if (par_.parallel()) {
#ifdef _OPENMP
#  pragma omp parallel num_threads(par_.threads) reduction(+ : lava, air)
#endif
            ompFor(layerCount(), Schedule::Static, 0, [&](std::ptrdiff_t k) {
                countLayers(static_cast<int>(k), static_cast<int>(k) + 1, lava, air);
            });
        } else {
            countLayers(0, layerCount(), lava, air);
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
    std::vector<std::vector<NbStep>> nbSteps_;  // sąsiedzi każdego wariantu z przesunięciami liniowymi
    std::vector<NbStep> side_;                // sideOffsets_ z przesunięciami liniowymi (D(n))
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
    ParallelSettings par_;             // wątki, harmonogram, statystyki wątków (etap 9)
    // --- automat frontalny ---
    bool front_ = true;                // ca.sweep = front
    bool frontReady_ = false;          // listy zbudowane (pierwszy krok)
    bool layerZ_ = true;               // oś warstw: z (3D, przekrój x–z) albo y (płaszczyzna x–y)
    bool layerPeriodic_ = false;       // czy oś warstw jest periodyczna
    std::vector<Offset> rev_[3];       // przesunięcia wszystkich wariantów wg przesunięcia w osi warstw -1/0/1
    std::vector<std::uint8_t> mark_;   // globalIndex -> 1: komórka jest na liście kandydatów
    std::vector<FrontLayer> layers_;   // listy frontu każdej warstwy
    std::uint64_t lavaTotal_ = 0;      // komórki LAVA (classic: ziarna) przed krokiem
    std::uint64_t airTotal_ = 0;       // komórki AIR przed krokiem
};

}  // namespace volcano
