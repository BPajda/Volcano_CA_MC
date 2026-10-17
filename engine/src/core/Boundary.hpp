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

    // Odświeża kopie komórki (x, y, z) wnętrza w ramce periodycznej po zmianie tej komórki — to samo, co dałoby
    // ponowne apply(), ale O(1): automat frontalny (etap 8) wypełnia ramkę raz, potem tylko zmienione komórki
    // przy ścianach periodycznych. Ramka absorbująca (VOID) się nie zmienia.
    template <class Storage>
    void syncCell(Storage& s, int x, int y, int z) const;

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
    // Ramka tylko w osiach o rozmiarze > 1 (Dims::frameX/Y/Z, etap 8) — w nieużywanej osi 2D nie ma czego wypełniać.
    const int fx = s.dims().frameX();
    const int fy = s.dims().frameY();
    const int fz = s.dims().frameZ();
    const CellState voidCell{CellType::Void, 0, 0.0f, 0, 0};

    // Ściany x = -1 i x = nx (tylko wnętrze w y i z).
    for (int z = 0; z < nz && fx; ++z) {
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
    for (int z = 0; z < nz && fy; ++z) {
        for (int x = -fx; x < nx + fx; ++x) {
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
    for (int y = -fy; y < ny + fy && fz; ++y) {
        for (int x = -fx; x < nx + fx; ++x) {
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

template <class Storage>
void Boundary::syncCell(Storage& s, int x, int y, int z) const {
    // Położenia kopii w każdej osi: sama komórka, a przy ścianie periodycznej (oś z ramką) także ramka po
    // przeciwnej stronie (x = 0 -> x = nx, x = nx-1 -> x = -1). Iloczyn tych położeń obejmuje krawędzie
    // i narożniki ramki — jak w apply(), które kopiuje osie po kolei razem z ramką poprzednich osi.
    const int c[3] = {x, y, z};
    const int n[3] = {s.nx(), s.ny(), s.nz()};
    int alt[3][3] = {};  // używane tylko pozycje < count[a]; zera — bez ostrzeżenia GCC -Wmaybe-uninitialized
    int count[3];
    bool any = false;
    for (int a = 0; a < 3; ++a) {
        alt[a][0] = c[a];
        count[a] = 1;
        if (periodic_[a] && n[a] > 1) {
            if (c[a] == 0) {
                alt[a][count[a]++] = n[a];
            }
            if (c[a] == n[a] - 1) {
                alt[a][count[a]++] = -1;
            }
        }
        any = any || count[a] > 1;
    }
    if (!any) {
        return;  // komórka nie leży przy ścianie periodycznej
    }
    const CellState v = s.cell(x, y, z);
    for (int iz = 0; iz < count[2]; ++iz) {
        for (int iy = 0; iy < count[1]; ++iy) {
            for (int ix = 0; ix < count[0]; ++ix) {
                if (ix != 0 || iy != 0 || iz != 0) {
                    s.setCell(alt[0][ix], alt[1][iy], alt[2][iz], v);
                }
            }
        }
    }
}

}  // namespace volcano
