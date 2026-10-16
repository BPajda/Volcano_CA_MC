// Testy obu reprezentacji siatki: ten sam interfejs, ramka, zamiana buforów.
#include "doctest.h"

#include "core/Storage.hpp"

using namespace volcano;

TEST_CASE_TEMPLATE("Storage: zapis i odczyt pól, łącznie z ramką", S, VectorStorage, MatrixStorage) {
    S s(Dims{4, 3, 2});
    CHECK(s.nx() == 4);
    CHECK(s.ny() == 3);
    CHECK(s.nz() == 2);
    CHECK(s.type(0, 0, 0) == CellType::Air);

    s.setCell(3, 2, 1, CellState{CellType::Lava, 7, 1100.5f, 12, 5});
    CHECK(s.type(3, 2, 1) == CellType::Lava);
    CHECK(s.flowId(3, 2, 1) == 7);
    CHECK(s.temp(3, 2, 1) == 1100.5f);
    CHECK(s.solidStep(3, 2, 1) == 12);
    CHECK(s.arrivalStep(3, 2, 1) == 5);
    s.setArrivalStep(3, 2, 1, 9);
    CHECK(s.cell(3, 2, 1).arrivalStep == 9);

    // Ramka: współrzędne -1 i n są dostępne i niezależne od wnętrza.
    s.setType(-1, -1, -1, CellType::Void);
    s.setType(4, 3, 2, CellType::Void);
    CHECK(s.type(-1, -1, -1) == CellType::Void);
    CHECK(s.type(4, 3, 2) == CellType::Void);
    CHECK(s.type(0, 0, 0) == CellType::Air);
    CHECK(s.type(3, 2, 1) == CellType::Lava);
}

TEST_CASE_TEMPLATE("Storage: swap zamienia bufory bez kopiowania", S, VectorStorage, MatrixStorage) {
    S a(Dims{3, 3, 3});
    S b(Dims{3, 3, 3});
    a.setFlowId(1, 1, 1, 5);
    b.setFlowId(1, 1, 1, 9);
    a.swap(b);
    CHECK(a.flowId(1, 1, 1) == 9);
    CHECK(b.flowId(1, 1, 1) == 5);
}

TEST_CASE("Storage: Microstructure w obie strony, identyczne dla vector i macierzy") {
    const Dims d{5, 1, 4};
    VectorStorage v(d);
    MatrixStorage m(d);
    for (int z = 0; z < d.nz; ++z) {
        for (int x = 0; x < d.nx; ++x) {
            const CellState c{static_cast<CellType>((x + z) % 4), x * 10 + z, float(x) - float(z),
                              static_cast<std::uint16_t>(z), static_cast<std::uint16_t>(x)};
            v.setCell(x, 0, z, c);
            m.setCell(x, 0, z, c);
        }
    }
    const Microstructure mv = toMicrostructure(v);
    const Microstructure mm = toMicrostructure(m);
    CHECK(mv.type == mm.type);
    CHECK(mv.flowId == mm.flowId);
    CHECK(mv.temp == mm.temp);
    CHECK(mv.solidStep == mm.solidStep);
    CHECK(mv.arrivalStep == mm.arrivalStep);
    CHECK(mv.flowId[mv.index(3, 0, 2)] == 32);
    CHECK(mv.arrivalStep[mv.index(3, 0, 2)] == 3);

    VectorStorage v2(d);
    loadMicrostructure(v2, mm);
    CHECK(toMicrostructure(v2).flowId == mv.flowId);
    CHECK(toMicrostructure(v2).arrivalStep == mv.arrivalStep);
}
