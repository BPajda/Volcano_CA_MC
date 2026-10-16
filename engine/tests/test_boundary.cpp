// Testy warunków brzegowych: absorbujące (VOID) i periodyczne (zawijanie, także narożniki).
#include "doctest.h"

#include "core/Boundary.hpp"
#include "core/Storage.hpp"

using namespace volcano;

TEST_CASE_TEMPLATE("Brzeg absorbujący: cała ramka = VOID, wnętrze nietknięte", S, VectorStorage, MatrixStorage) {
    S s(Dims{4, 3, 5});
    s.setType(0, 0, 0, CellType::Lava);
    Boundary(BoundaryKind::Absorbing, CaMode::Lava).apply(s);
    CHECK(s.type(-1, 0, 0) == CellType::Void);
    CHECK(s.type(4, 2, 4) == CellType::Void);
    CHECK(s.type(0, -1, 0) == CellType::Void);
    CHECK(s.type(0, 0, -1) == CellType::Void);
    CHECK(s.type(-1, -1, -1) == CellType::Void);
    CHECK(s.type(4, 3, 5) == CellType::Void);
    CHECK(s.type(0, 0, 0) == CellType::Lava);
}

TEST_CASE_TEMPLATE("Brzeg periodyczny (classic): zawijanie we wszystkich osiach", S, VectorStorage, MatrixStorage) {
    S s(Dims{4, 3, 5});
    s.setFlowId(0, 0, 0, 11);  // narożnik (0,0,0)
    s.setFlowId(3, 2, 4, 22);  // przeciwległy narożnik
    s.setFlowId(3, 1, 2, 33);  // środek ściany x = nx-1
    Boundary(BoundaryKind::Periodic, CaMode::Classic).apply(s);
    // Ściany
    CHECK(s.flowId(-1, 1, 2) == 33);
    CHECK(s.flowId(4, 0, 0) == 11);
    CHECK(s.flowId(0, 3, 0) == 11);
    CHECK(s.flowId(0, 0, 5) == 11);
    // Narożniki ramki: (-1,-1,-1) = (nx-1, ny-1, nz-1), (nx,ny,nz) = (0,0,0)
    CHECK(s.flowId(-1, -1, -1) == 22);
    CHECK(s.flowId(4, 3, 5) == 11);
}

TEST_CASE_TEMPLATE("Brzeg periodyczny w trybie lava: x, y zawinięte, z zawsze VOID", S, VectorStorage, MatrixStorage) {
    S s(Dims{4, 3, 5});
    s.setType(3, 1, 2, CellType::Lava);
    s.setType(1, 1, 0, CellType::Lava);
    Boundary(BoundaryKind::Periodic, CaMode::Lava).apply(s);
    CHECK(s.type(-1, 1, 2) == CellType::Lava);
    CHECK(s.type(1, 1, 5) == CellType::Void);  // brak zawinięcia w pionie
    CHECK(s.type(1, 1, -1) == CellType::Void);
    CHECK(s.type(-1, -1, -1) == CellType::Void);
}
