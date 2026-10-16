#include "core/Boundary.hpp"

namespace volcano {

Boundary::Boundary(BoundaryKind kind, CaMode mode) : kind_(kind) {
    const bool periodic = (kind == BoundaryKind::Periodic);
    periodic_[0] = periodic;
    periodic_[1] = periodic;
    // Oś pionowa periodyczna tylko bez grawitacji (tryb classic) — patrz komentarz w nagłówku.
    periodic_[2] = periodic && mode == CaMode::Classic;
}

const char* Boundary::name(BoundaryKind kind) {
    return kind == BoundaryKind::Periodic ? "periodic" : "absorbing";
}

}  // namespace volcano
