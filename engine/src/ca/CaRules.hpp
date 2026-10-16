#pragma once
// Parametry i bezstanowe elementy reguł automatu komórkowego.
//
// ===== Tryb "lava" — krok t -> t+1 (czytamy tylko bufor cur, piszemy next) =====
// Pojęcia pomocnicze:
//   podparcie(k)  — pod komórką k jest ROCK/BASALT, k.z = 0 albo lawa w niecce (patrz niżej);
//   spadek(k)     — dla komórki AIR k: po ilu poziomach w dół lawa z k wyląduje na gruncie
//                   (0 = k ma podparcie); LavaCA::dropDepth,
//   D(n)          — największy spadek wśród sąsiednich komórek AIR lawy n (ten sam poziom);
//                   D = 0 oznacza, że n nie ma drogi w dół; LavaCA::descent.
// 1. Komórka AIR c zbiera kandydatów spośród sąsiadów n (wg sąsiedztwa), które są LAVA:
//    - n DOKŁADNIE NAD c          -> swobodny spadek; zawsze; stygnięcie coolingFall,
//    - n WYŻEJ PO SKOSIE           -> spływ po stoku; gdy n i c mają podparcie i D(n) = 1;
//                                     stygnięcie coolingFall,
//    - n NA TYM SAMYM POZIOMIE     -> rozlewanie; gdy n ma podparcie i spadek(c) = D(n)
//                                     (lawa płynie w kierunku największego spadku; przy D = 0
//                                     rozlewa się po płaskim, przy D >= 2 przelewa się nad
//                                     krawędź, skąd spadnie; D = 1 obsługuje spływ po skosie);
//                                     stygnięcie coolingLateral,
//    - n NIŻEJ                     -> niedozwolone (lawa się nie wspina), z wyjątkiem
//                                     „wypełniania zagłębień” (niżej).
//    Gdy są kandydaci: flowId = najczęstszy wśród kandydatów (remis -> hashRand),
//    temp = max po kandydatach z tym flowId z (temp_n - stygnięcie), arrivalStep = t
//    (krok, w którym komórka stała się lawą; kratery mają arrivalStep = 0).
//    Jeśli temp < solidusTemp, komórka zostaje AIR (lawa za zimna, by płynąć dalej).
// 2. Komórka LAVA: krater w trakcie erupcji (t < eruptionSteps) ma temp = eruptTemp;
//    pozostała lawa traci coolingAmbient; gdy temp < solidusTemp -> BASALT, solidStep = t.
//    Czas w stanie płynnym solidStep - arrivalStep wyznacza mobilność komórki w krystalizacji
//    Monte Carlo (mc/McRules.hpp): długo płynna lawa -> duże kryształy.
// 3. ROCK, BASALT: bez zmian.
// 4. Koniec: brak LAVA, brak zmian w kroku (tylko sąsiedztwa deterministyczne) albo maxSteps.
//
// ===== Dlaczego reguła 1 różni się od opisu etapu (każdą zmianę wymusił obraz wyniku) =====
// a) Podparcie. W opisie podparciem jest każda komórka LAVA. Wtedy lawa, która spadła
//    z krawędzi, podpiera komórkę nad sobą, ta rozlewa się poziomo nad powietrzem, nowa
//    komórka znów spada... — „kurtyna” wypełnia całą przestrzeń pod poziomem lawy.
//    Dlatego płynna lawa podpiera tylko w niecce (jak powierzchnia jeziora lawy).
// b) Spadanie po skosie. Zawsze dozwolone odrywa lawę od stoku bardziej stromego niż 45°
//    (w 3D po przekątnej już przy nachyleniu ~0.7): pod linią 45° rośnie klin lawy coraz
//    grubszy ku podnóżu. Dlatego po skosie lawa spływa tylko na komórkę z podparciem,
//    a z urwiska spada pionowo.
// c) Kierunek największego spadku. Gdy lawa może rozlewać się do każdej niższej komórki,
//    z krateru rozchodzi się wachlarzem i pokrywa cały stożek. Warunek „lawa woli spływać
//    w dół” jest w planie projektu (§3.3), a wypływ do najniższych sąsiadów to zasada
//    modeli SCIARA — dzięki niemu powstają jęzory wzdłuż dolin terenu.
//
// ===== Wypełnianie zagłębień (ca.ponding, rozszerzenie reguł) =====
// Same reguły 1–3 nie pozwalają lawie podnieść się ani o jedną komórkę, więc lawa
// z krateru-zagłębienia nigdy by z niego nie wypłynęła. Dlatego przed symulacją dla
// mapy wysokości liczony jest poziom przelewu każdej kolumny (fill(x,y) — algorytm
// priority-flood, TerrainGenerator::fillDepressions): do jakiej wysokości wypełniłaby
// się niecka, zanim ciecz wyleje się przez najniższy punkt krawędzi. Komórka AIR c
// bezpośrednio nad lawą b dostaje lawę z b (stygnięcie coolingLateral), gdy:
//   - c leży w niecce lub o warstwę nad nią: c.z <= fill(x,y) (warstwa fill to poziom,
//     z którego lawa przelewa się bokiem przez krawędź),
//   - b ma podparcie (nie może spaść),
//   - b nie może rozlać się na boki: żaden poziomy sąsiad b nie jest AIR ani VOID.
// Krater wypełnia się więc warstwa po warstwie, a gdy poziom sięgnie krawędzi, lawa
// przelewa się na zbocze. Na zboczu i równinie fill(x,y) = wysokość terenu, więc reguła
// tam nie działa (lawa nie piętrzy się). Pierwsza wersja z lokalnym warunkiem „obok
// ściany skalnej” podnosiła poziom wzdłuż każdego zbocza — zalewała całą mapę.
// ponding = false wyłącza tę regułę (lawa nie opuści wtedy krateru-zagłębienia).
//
// ===== Tryb "classic" — klasyczny rozrost ziaren (porównanie z referencją) =====
// Brak terenu i temperatury. Komórka AIR z sąsiadem-ziarnem (dowolny kierunek) dostaje
// najczęstszy flowId wśród sąsiadów (remis -> hashRand) i arrivalStep = t.
// Koniec: brak komórek AIR.

#include <algorithm>
#include <cassert>
#include <cstdint>
#include <limits>

#include "core/Profile.hpp"
#include "core/Rng.hpp"
#include "core/Types.hpp"

namespace volcano {

// Parametry automatu (typy jak w komórkach: temperatury jako float).
struct CaParams {
    CaMode mode = CaMode::Lava;
    std::uint64_t seed = 42;
    int maxSteps = 5000;
    int eruptionSteps = 300;
    float eruptTemp = 1200.0f;
    float solidusTemp = 800.0f;
    float coolingAmbient = 0.3f;
    float coolingLateral = 1.5f;
    float coolingFall = 0.1f;
    bool ponding = true;
};

// Powód zakończenia symulacji.
enum class StopReason { Running, NoLava, NoAir, NoChange, MaxSteps };

inline const char* describe(StopReason r) {
    switch (r) {
        case StopReason::Running: return "trwa";
        case StopReason::NoLava: return "brak płynnej lawy";
        case StopReason::NoAir: return "brak wolnych komórek (AIR)";
        case StopReason::NoChange: return "brak zmian w kroku";
        case StopReason::MaxSteps: return "osiągnięto ca.maxSteps";
    }
    return "?";
}

// Czy komórka jest stałym gruntem (skała lub zastygła lawa) — zawsze podpiera lawę.
inline bool isSolidGround(CellType t) { return t == CellType::Rock || t == CellType::Basalt; }

// Głosowanie kandydatów o flowId nowej komórki („najczęstszy sąsiad” z rozrostu ziaren).
// Zbiera głosy w małych tablicach na stosie (bez alokacji w gorącej pętli) i dla każdego
// flowId pamięta maksymalną temperaturę kandydata.
class CandidateVote {
public:
    static constexpr int kMax = 32;  // >= największe sąsiedztwo (Moore 3D = 26)

    void clear() { n_ = 0; }
    bool empty() const { return n_ == 0; }

    // Dodaje głos kandydata o danym flowId i temperaturze (już po odjęciu stygnięcia).
    VOLCANO_NOINLINE void add(std::int32_t flowId, float temp) {
        for (int i = 0; i < n_; ++i) {
            if (ids_[i] == flowId) {
                ++counts_[i];
                maxTemp_[i] = std::max(maxTemp_[i], temp);
                return;
            }
        }
        assert(n_ < kMax);
        ids_[n_] = flowId;
        counts_[n_] = 1;
        maxTemp_[n_] = temp;
        ++n_;
    }

    // Indeks zwycięzcy: najwięcej głosów; remis rozstrzyga hashRand(seed, step, cellIndex).
    // Remisujące flowId są sortowane rosnąco, więc wynik nie zależy od kolejności sąsiadów.
    VOLCANO_NOINLINE int winner(std::uint64_t seed, std::uint64_t step, std::uint64_t cellIndex) const {
        if (n_ == 1) {
            return 0;
        }
        int best = 0;
        for (int i = 0; i < n_; ++i) {
            best = std::max(best, counts_[i]);
        }
        int tied[kMax];
        int k = 0;
        for (int i = 0; i < n_; ++i) {
            if (counts_[i] == best) {
                tied[k++] = i;
            }
        }
        if (k == 1) {
            return tied[0];
        }
        std::sort(tied, tied + k, [this](int a, int b) { return ids_[a] < ids_[b]; });
        const std::uint64_t r = hashRand(seed, step, cellIndex, kSaltTieBreak);
        return tied[static_cast<int>(r % static_cast<std::uint64_t>(k))];
    }

    std::int32_t flowId(int i) const { return ids_[i]; }
    float maxTemp(int i) const { return maxTemp_[i]; }

private:
    std::int32_t ids_[kMax];
    int counts_[kMax];
    float maxTemp_[kMax];
    int n_ = 0;
};

}  // namespace volcano
