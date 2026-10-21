// Etap 10 (MPI): podział przestrzeni na pasy warstw i plan warstw brzegowych (parallel/Strip.hpp) — część bez MPI.
//   * równy podział warstw (reszta do pierwszych pasów), błąd przy liczbie pasów > liczba warstw;
//   * lawa: 17 warstw brzegowych pod pasem (pierwsza z pełnym stanem, głębsze — sam typ), 1 nad pasem; warstwy pod
//     pasem przychodzą od kilku procesów, gdy pasy są cieńsze niż 17 warstw;
//   * pierścień przy brzegu periodycznym (pierwszy i ostatni pas są sąsiadami), także dla 2 procesów;
//   * listy wysyłki nadawcy = listy odbioru odbiorcy (te same warstwy w tej samej kolejności);
//   * okno pasa w LavaCA i PottsMC: Boundary::withoutPeriodic, warstwy osi zewnętrznej w tablicach z ramką.
#include "doctest.h"

#include <vector>

#include "core/Boundary.hpp"
#include "core/Storage.hpp"
#include "parallel/Strip.hpp"

using namespace volcano;

namespace {

GhostSpec lavaSpec() {
    GhostSpec s;
    s.below.assign(17, kFieldType);
    s.below[0] = kFieldType | kFieldFlow | kFieldTemp;
    s.above.assign(1, kFieldType | kFieldFlow | kFieldTemp);
    return s;
}

GhostSpec ringSpec() {
    GhostSpec s;
    s.below.assign(1, kFieldSpin);
    s.above.assign(1, kFieldSpin);
    s.periodic = true;
    return s;
}

// Wysyłka nadawcy do odbiorcy = odbiór odbiorcy od nadawcy (globalne warstwy i pola, ta sama kolejność).
void checkConsistent(int layers, int ranks, const GhostSpec& spec) {
    std::vector<StripPlan> plans;
    for (int r = 0; r < ranks; ++r) {
        plans.push_back(planStrip(layers, ranks, r, spec));
    }
    for (int r = 0; r < ranks; ++r) {
        for (const StripPlan::Message& s : plans[static_cast<std::size_t>(r)].sends) {
            const StripPlan& dst = plans[static_cast<std::size_t>(s.peer)];
            const StripPlan::Message* match = nullptr;
            for (const StripPlan::Message& m : dst.recvs) {
                if (m.peer == r) {
                    match = &m;
                }
            }
            REQUIRE(match != nullptr);
            REQUIRE(match->layers.size() == s.layers.size());
            for (std::size_t i = 0; i < s.layers.size(); ++i) {
                CHECK(match->layers[i].global == s.layers[i].global);
                CHECK(match->layers[i].fields == s.layers[i].fields);
                // nadawca wysyła swoją warstwę własną o tym numerze globalnym
                const StripPlan& src = plans[static_cast<std::size_t>(r)];
                CHECK(s.layers[i].local == src.ownLo + (s.layers[i].global - src.lo));
                CHECK(s.layers[i].global >= src.lo);
                CHECK(s.layers[i].global < src.hi);
            }
        }
        // każda warstwa brzegowa ma nadawcę
        std::size_t received = 0;
        for (const StripPlan::Message& m : plans[static_cast<std::size_t>(r)].recvs) {
            received += m.layers.size();
        }
        CHECK(received == plans[static_cast<std::size_t>(r)].ghosts.size());
    }
}

}  // namespace

TEST_CASE("Pasy MPI: równy podział warstw") {
    CHECK(splitLayers(10, 3) == std::vector<int>{0, 4, 7, 10});
    CHECK(splitLayers(8, 8) == std::vector<int>{0, 1, 2, 3, 4, 5, 6, 7, 8});
    CHECK(splitLayers(5, 1) == std::vector<int>{0, 5});
    CHECK(splitLayers(80, 3) == std::vector<int>{0, 27, 54, 80});
    CHECK_THROWS(splitLayers(3, 4));
    CHECK_THROWS(planStrip(3, 4, 0, ringSpec()));
}

TEST_CASE("Pasy MPI: jeden proces — okno = cała przestrzeń") {
    const StripPlan p = planStrip(12, 1, 0, lavaSpec());
    CHECK(p.lo == 0);
    CHECK(p.hi == 12);
    CHECK(p.windowLo == 0);
    CHECK(p.windowLayers == 12);
    CHECK(p.ownLo == 0);
    CHECK(p.ownHi == 12);
    CHECK(p.ghosts.empty());
    CHECK(p.sends.empty());
    CHECK(p.recvs.empty());
}

TEST_CASE("Pasy MPI: lawa — 17 warstw pod pasem od kilku procesów, 1 nad pasem") {
    // 10 warstw na 4 procesy: [0,3) [3,6) [6,8) [8,10)
    const StripPlan p = planStrip(10, 4, 2, lavaSpec());
    CHECK(p.lo == 6);
    CHECK(p.hi == 8);
    CHECK(p.windowLo == 0);  // pod pasem tylko 6 warstw — do dna przestrzeni
    CHECK(p.ownLo == 6);
    CHECK(p.ownHi == 8);
    CHECK(p.windowLayers == 9);
    REQUIRE(p.ghosts.size() == 7);
    CHECK(p.ghosts[0].global == 0);
    CHECK(p.ghosts[0].fields == kFieldType);
    CHECK(p.ghosts[5].global == 5);
    CHECK(p.ghosts[5].fields == (kFieldType | kFieldFlow | kFieldTemp));  // tuż pod pasem — pełny stan
    CHECK(p.ghosts[6].global == 8);
    CHECK(p.ghosts[6].owner == 3);
    REQUIRE(p.recvs.size() == 3);  // od procesów 0, 1 i 3
    CHECK(p.recvs[0].peer == 0);
    CHECK(p.recvs[0].layers.size() == 3);
    CHECK(p.recvs[1].peer == 1);
    CHECK(p.recvs[2].peer == 3);
    // Do procesu 1 (warstwa 6 nad jego pasem) i 3 (warstwy 6, 7 pod jego pasem).
    REQUIRE(p.sends.size() == 2);
    CHECK(p.sends[0].peer == 1);
    CHECK(p.sends[0].layers.size() == 1);
    CHECK(p.sends[1].peer == 3);
    CHECK(p.sends[1].layers.size() == 2);
    CHECK(p.sends[1].layers[1].fields == (kFieldType | kFieldFlow | kFieldTemp));  // warstwa 7 tuż pod pasem 3
    // Ostatni pas nie ma warstwy nad sobą, pierwszy — pod sobą.
    CHECK(planStrip(10, 4, 3, lavaSpec()).windowLayers == 10);
    CHECK(planStrip(10, 4, 0, lavaSpec()).windowLo == 0);
    CHECK(planStrip(10, 4, 0, lavaSpec()).windowLayers == 4);
    for (int ranks : {2, 3, 4, 5, 8}) {
        CAPTURE(ranks);
        checkConsistent(45, ranks, lavaSpec());
        checkConsistent(80, ranks, lavaSpec());
    }
}

TEST_CASE("Pasy MPI: pierścień przy brzegu periodycznym") {
    // 3 warstwy na 2 procesy: [0,2) [2,3); proces 0 ma warstwę 2 pod i nad sobą (dwie kopie w oknie).
    const StripPlan p0 = planStrip(3, 2, 0, ringSpec());
    CHECK(p0.windowLo == -1);
    CHECK(p0.windowLayers == 4);
    REQUIRE(p0.ghosts.size() == 2);
    CHECK(p0.ghosts[0].global == 2);
    CHECK(p0.ghosts[1].global == 2);
    REQUIRE(p0.recvs.size() == 1);
    CHECK(p0.recvs[0].layers.size() == 2);
    const StripPlan p1 = planStrip(3, 2, 1, ringSpec());
    REQUIRE(p1.ghosts.size() == 2);
    CHECK(p1.ghosts[0].global == 1);  // pod pasem
    CHECK(p1.ghosts[1].global == 0);  // nad pasem — zawinięcie
    REQUIRE(p0.sends.size() == 1);
    CHECK(p0.sends[0].layers[0].local == 2);  // warstwa globalna 1 w oknie procesu 0
    CHECK(p0.sends[0].layers[1].local == 1);  // warstwa globalna 0
    for (int ranks : {2, 3, 4, 5, 8}) {
        CAPTURE(ranks);
        checkConsistent(8, ranks, ringSpec());
        checkConsistent(41, ranks, ringSpec());
    }
}

TEST_CASE("Pasy MPI: okno — oś bez zawijania, warstwy osi zewnętrznej w tablicach z ramką") {
    const Boundary b(BoundaryKind::Periodic, CaMode::Classic);
    const Boundary w = b.withoutPeriodic(2);
    CHECK(w.periodicX());
    CHECK(w.periodicY());
    CHECK_FALSE(w.periodicZ());
    CHECK(b.periodicZ());
    // 3D: warstwa z (z ramką x, y) jest ciągła; kolejne warstwy co layerCells().
    VectorStorage s3(Dims{4, 3, 5});
    CHECK(s3.layerCells() == 6u * 5u);
    CHECK(s3.layerStart(1) - s3.layerStart(0) == s3.layerCells());
    CHECK(s3.layerStart(0) == s3.pos(-1, -1, 0));
    // płaszczyzna x–y: warstwa = wiersz y (z ramką x)
    VectorStorage s2(Dims{4, 6, 1});
    CHECK(s2.layerCells() == 6u);
    CHECK(s2.layerStart(2) == s2.pos(-1, 2, 0));
    // przekrój x–z (ny = 1): warstwa z bez ramki w y
    VectorStorage sxz(Dims{7, 1, 4});
    CHECK(sxz.layerCells() == 9u);
    CHECK(sxz.layerStart(3) == sxz.pos(-1, 0, 3));
    CHECK(windowDims(Dims{10, 10, 30}, 7).nz == 7);
    CHECK(windowDims(Dims{10, 20, 1}, 5).ny == 5);
    CHECK(layerPlane(Dims{10, 20, 1}) == 10u);
    CHECK(layerPlane(Dims{10, 20, 3}) == 200u);
}
