#pragma once
// Warunki brzegowe realizowane przez wypełnienie ramki (1 komórka dookoła siatki)
// przed każdym krokiem automatu:
//
//   absorbing — ramka = VOID: nic nie wpływa ani nie wypływa, a VOID nigdy nie jest
//               lawą, więc lawa dochodząca do brzegu po prostu „znika” z modelu;
//   periodic  — ramka = kopia przeciwległej warstwy wnętrza (zawijanie torusa).
//
// W trybie lava periodyczne są TYLKO osie poziome x, y. Oś pionowa z jest zawsze
// absorbująca: przy zawinięciu w pionie lawa spadająca przez dno pojawiałaby się
// u góry mapy, co przeczy grawitacji. W trybie classic (bez grawitacji) zawijamy
// wszystkie osie, tak jak w klasycznym (referencyjnym) rozroście ziaren.

#include "core/Profile.hpp"
#include "core/Types.hpp"

namespace volcano {

class Boundary {
public:
    Boundary(BoundaryKind kind, CaMode mode);

    BoundaryKind kind() const { return kind_; }
    bool periodicX() const { return periodic_[0]; }
    bool periodicY() const { return periodic_[1]; }
    bool periodicZ() const { return periodic_[2]; }

    // Wypełnia ramkę bufora s. Kolejność osi x -> y -> z, przy czym każda kolejna
    // oś obejmuje już wypełnioną ramkę poprzednich, dzięki czemu krawędzie i narożniki
    // ramki też są poprawnie zawinięte (np. komórka (-1,-1) = (nx-1, ny-1)).
    template <class Storage>
    void apply(Storage& s) const;

    static const char* name(BoundaryKind kind);

private:
    BoundaryKind kind_;
    bool periodic_[3];  // osobno dla osi x, y, z
};

template <class Storage>
VOLCANO_NOINLINE void Boundary::apply(Storage& s) const {
    const int nx = s.nx();
    const int ny = s.ny();
    const int nz = s.nz();
    const CellState voidCell{CellType::Void, 0, 0.0f, 0, 0};

    // Ściany x = -1 i x = nx (tylko wnętrze w y i z).
    for (int z = 0; z < nz; ++z) {
        for (int y = 0; y < ny; ++y) {
            if (periodic_[0]) {
                s.setCell(-1, y, z, s.cell(nx - 1, y, z));
                s.setCell(nx, y, z, s.cell(0, y, z));
            } else {
                s.setCell(-1, y, z, voidCell);
                s.setCell(nx, y, z, voidCell);
            }
        }
    }
    // Ściany y = -1 i y = ny (x obejmuje już ramkę x).
    for (int z = 0; z < nz; ++z) {
        for (int x = -1; x <= nx; ++x) {
            if (periodic_[1]) {
                s.setCell(x, -1, z, s.cell(x, ny - 1, z));
                s.setCell(x, ny, z, s.cell(x, 0, z));
            } else {
                s.setCell(x, -1, z, voidCell);
                s.setCell(x, ny, z, voidCell);
            }
        }
    }
    // Ściany z = -1 i z = nz (x i y obejmują ramkę).
    for (int y = -1; y <= ny; ++y) {
        for (int x = -1; x <= nx; ++x) {
            if (periodic_[2]) {
                s.setCell(x, y, -1, s.cell(x, y, nz - 1));
                s.setCell(x, y, nz, s.cell(x, y, 0));
            } else {
                s.setCell(x, y, -1, voidCell);
                s.setCell(x, y, nz, voidCell);
            }
        }
    }
}

}  // namespace volcano
