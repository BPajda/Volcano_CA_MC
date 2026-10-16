#pragma once
// Krystalizacja zastygłej lawy — naiwny rozrost ziaren Monte Carlo (model Pottsa).
// Parametry, statystyki i opis reguł (implementacja: PottsMC.hpp/.cpp).
//
// ===== Model =====
// Każda komórka domeny ma orientację kryształu S ∈ {1..Q}. Komórki sąsiednie o tej samej
// orientacji tworzą ziarno (kryształ). Energia komórki i:
//     E_i = J · Σ_j (1 − δ(S_i, S_j)),   suma po sąsiadach j W DOMENIE (wg sąsiedztwa z configu),
// czyli J razy liczba sąsiadów o innej orientacji (energia granicy ziarna). Sąsiad spoza
// domeny (skała, powietrze, ramka absorbująca) jest pomijany — granica bazaltu ze skałą
// nie zmienia energii, więc nie wpływa na kształt kryształów.
//
// ===== Krok MCS (wersja naiwna, kroki 1–5) — PottsMC::sweep() =====
// 1 MCS = N_domena prób; próba nr a w kroku MCS t:
//   Krok 1: losowa selekcja elementu — komórka k = hashRand(seed, t, a, kSaltMcPick) mod N
//           (losowanie ZE ZWRACANIEM z listy komórek domeny);
//   (mobilność, tylko tryb basalt) z prawdopodobieństwem 1 − m_k próba jest pomijana;
//   Krok 2: energia przed zmianą E_przed = J · Σ (1 − δ(S_k, S_j));
//   Krok 3: nowa orientacja losowana z CAŁEGO zbioru 1..Q, różna od obecnej
//           (hashRand(..., kSaltMcOrient) mod (Q − 1), wartości ≥ S_k przesunięte o 1);
//   Krok 4: energia po zmianie E_po i ΔE = E_po − E_przed;
//   Krok 5: akceptacja (Metropolis): ΔE ≤ 0 -> zawsze; ΔE > 0 -> z prawdopodobieństwem
//           exp(−ΔE / kT) gdy kT > 0, w przeciwnym razie odrzucenie (dokładnie jak w wariancie naiwnym,
//           p = 1 dla ΔE ≤ 0, p = 0 dla ΔE > 0).
// Losowość wyłącznie z hashRand(seed, t, a, sól) z osobnymi solami dla wyboru komórki,
// mobilności, nowej orientacji i akceptacji — wynik zależy tylko od seeda.
// Wariant sąsiedztwa losowego (pentagonal, hexagonal) wybiera Neighborhood::variantFor
// (seed, t, globalnyIndeksKomórki) — wariant jest cechą komórki w danym kroku MCS, jak w CA.
//
// UWAGA: MC jest z natury SEKWENCYJNE — każda próba widzi wynik poprzednich (asynchroniczna
// aktualizacja), w przeciwieństwie do synchronicznego CA. Zrównoleglenie (planowany rozwój) wymaga
// podziału domeny na podzbiory niesąsiadujących komórek (szachownica) albo przetwarzania pasów.
//
// ===== Domena (mc.domain) =====
//   basalt — komórki BASALT (i ewentualnie pozostała płynna LAVA, np. krater otoczony
//            zastygłą lawą) z wyniku CA; brzeg periodyczny tylko w osiach x, y (oś z pionowa,
//            jak w CA);
//   full   — cała przestrzeń, bez terenu i bez CA (klasyczny naiwny rozrost ziaren MC);
//            brzeg periodyczny we wszystkich osiach.
// Brzegi: ramka 1 komórki. Absorbujący — ramka poza domeną. Periodyczny — ramka jest kopią
// przeciwległej warstwy i po każdej ZAAKCEPTOWANEJ zmianie komórki leżącej przy ścianie
// periodycznej odświeżamy jej kopie w ramce (PottsMC::syncFrame, do 7 kopii w narożniku 3D).
// Wybrane zamiast zawijania indeksu sąsiada, bo gorąca pętla zostaje bez rozgałęzień
// (sąsiad = indeks + stałe przesunięcie liniowe), a zmian przy brzegu jest niewiele.
//
// ===== Mobilność ze stygnięcia (mc.mobilityFromCooling, tylko basalt) =====
// Czas w stanie płynnym komórki: czas_i = solidStep − arrivalStep (z CA). Pozostała płynna
// lawa jest traktowana jak zastygła w ostatnim kroku CA (największy solidStep/arrivalStep).
// Normalizacja min–max po domenie: m_i = mobilityMin + (1 − mobilityMin) · czas_norm;
// gdy wszystkie czasy są równe — m_i = 1. Lawa, która długo była płynna (jezioro lawy
// w kraterze, okolice krateru), ma wysoką mobilność i krystalizuje w DUŻE ziarna; lawa,
// która zastygła szybko (czoło jęzora, cienka warstwa daleko od krateru), prawie się nie
// przebudowuje — zostają DROBNE ziarna. Tak jest w skałach wulkanicznych: szybko schłodzony
// brzeg wylewu lub dajki („chilled margin”) jest drobnokrystaliczny albo szklisty, a wolno
// stygnące wnętrze grubego wylewu ma duże kryształy.
//
// ===== Statystyki (co mc.statsEvery MCS, MCS 0 i ostatni) =====
//   grains        — liczba spójnych składowych komórek domeny o tej samej orientacji
//                   (union-find, Grains.hpp). Spójność: von Neumann (ściany), gdy MC używa
//                   sąsiedztwa von Neumanna; Moore (ściany, krawędzie, narożniki) dla Moore'a
//                   i sąsiedztw losowych (suma ich wariantów to Moore). Zgodnie z energią:
//                   dwie komórki należą do jednego ziarna, gdy granica między nimi nie
//                   kosztuje energii. Przy samym von Neumannie cienka warstwa bazaltu na
//                   „schodkowym” stoku (komórki stykają się tylko krawędziami) rozpadałaby
//                   się na jednokomórkowe „ziarna” niezależnie od przebiegu MC;
//   meanGrainSize — komórki domeny / liczba ziaren;
//   energy        — energia całkowita ½ · Σ_i E_i (każda para sąsiadów liczona raz);
//   acceptRate    — zaakceptowane zmiany / próby w ostatnim interwale (próby pominięte przez
//                   mobilność się nie liczą — to współczynnik akceptacji Metropolisa).
//
// OPTYMALIZACJA (planowane, celowo jeszcze nie zrobione): losowanie bez powtórzeń (permutacja),
// nowa orientacja tylko spośród sąsiadów, próby tylko dla komórek na granicy ziaren,
// jedno przejście po sąsiadach zamiast dwóch (E_przed i E_po naraz), tablica exp(−ΔE/kT).

#include <cstdint>

namespace volcano {

// Parametry algorytmu MC (wartości z sekcji "mc" configu).
struct McParams {
    std::uint64_t seed = 42;
    int Q = 50;         // liczba orientacji (stanów)
    double J = 1.0;     // energia granicy ziarna (J_gb)
    double kT = 0.0;    // „temperatura” Metropolisa; 0 = akceptacja tylko ΔE <= 0 (wariant naiwny)
};

// Statystyki stanu po danym kroku MCS (jeden wiersz mc_stats.csv).
struct McStats {
    int mcs = 0;                  // liczba wykonanych kroków MCS
    std::uint64_t grains = 0;     // liczba ziaren (spójnych składowych)
    double meanGrainSize = 0.0;   // średnia wielkość ziarna [komórki]
    double energy = 0.0;          // energia całkowita
    double acceptRate = 0.0;      // odsetek zaakceptowanych zmian w ostatnim interwale
};

}  // namespace volcano
