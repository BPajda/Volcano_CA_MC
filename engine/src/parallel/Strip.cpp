#include "parallel/Strip.hpp"

#include <stdexcept>
#include <string>

namespace volcano {

std::vector<int> splitLayers(int layers, int parts) {
    if (parts < 1 || parts > layers) {
        throw std::invalid_argument("podział " + std::to_string(layers) + " warstw na " + std::to_string(parts) +
                                    " części: wymagane 1 <= części <= warstwy");
    }
    std::vector<int> lo(static_cast<std::size_t>(parts) + 1, 0);
    const int base = layers / parts;
    const int rest = layers % parts;
    for (int r = 0; r <= parts; ++r) {
        lo[static_cast<std::size_t>(r)] = r * base + (r < rest ? r : rest);
    }
    return lo;  // część r: [lo[r], lo[r + 1]); lo[parts] = layers
}

namespace {

// Właściciel globalnej warstwy g (0 <= g < L) przy podziale lo.
int ownerOf(const std::vector<int>& lo, int g) {
    int r = 0;
    while (lo[static_cast<std::size_t>(r) + 1] <= g) {
        ++r;
    }
    return r;
}

// Warstwy brzegowe procesu rank (bez list wysyłki) — wspólne dla planu własnego i planów sąsiadów.
StripPlan ghostsOf(int layers, int ranks, int rank, const std::vector<int>& lo, const GhostSpec& spec) {
    StripPlan p;
    p.layers = layers;
    p.ranks = ranks;
    p.rank = rank;
    p.lo = lo[static_cast<std::size_t>(rank)];
    p.hi = lo[static_cast<std::size_t>(rank) + 1];
    int below = 0;
    int above = 0;
    if (ranks > 1) {
        // Bez pierścienia: tylko istniejące warstwy (pierwszy pas nie ma warstw pod sobą, ostatni — nad sobą).
        // Pierścień: zawsze pełna liczba, numery zawinięte modulo L.
        below = static_cast<int>(spec.below.size());
        above = static_cast<int>(spec.above.size());
        if (!spec.periodic) {
            below = below < p.lo ? below : p.lo;
            above = above < layers - p.hi ? above : layers - p.hi;
        }
    }
    p.windowLo = p.lo - below;
    p.ownLo = below;
    p.ownHi = below + (p.hi - p.lo);
    p.windowLayers = p.ownHi + above;
    const auto wrap = [layers](int g) { return g < 0 ? g + layers : (g >= layers ? g - layers : g); };
    for (int d = below; d >= 1; --d) {
        const int g = wrap(p.lo - d);
        p.ghosts.push_back(GhostLayer{p.ownLo - d, g, ownerOf(lo, g), spec.below[static_cast<std::size_t>(d) - 1]});
    }
    for (int d = 1; d <= above; ++d) {
        const int g = wrap(p.hi - 1 + d);
        p.ghosts.push_back(GhostLayer{p.ownHi - 1 + d, g, ownerOf(lo, g), spec.above[static_cast<std::size_t>(d) - 1]});
    }
    return p;
}

}  // namespace

StripPlan planStrip(int layers, int ranks, int rank, const GhostSpec& spec) {
    if (ranks > layers) {
        throw std::invalid_argument("więcej procesów (" + std::to_string(ranks) + ") niż warstw przestrzeni (" +
                                    std::to_string(layers) + ")");
    }
    const std::vector<int> lo = splitLayers(layers, ranks);
    StripPlan plan = ghostsOf(layers, ranks, rank, lo, spec);
    if (spec.periodic && ranks > 1) {
        // Przy pierścieniu warstwa brzegowa jest zawsze warstwą innego procesu (każdy pas ma co najmniej 1 warstwę,
        // a pasów jest >= 2), ale ta sama warstwa może wystąpić w oknie dwa razy (np. 2 procesy: pod i nad pasem).
        for (const GhostLayer& g : plan.ghosts) {
            if (g.owner == rank) {
                throw std::logic_error("warstwa brzegowa należy do własnego pasu");
            }
        }
    }
    // Odbiór: warstwy brzegowe pogrupowane wg właściciela, w kolejności okna.
    for (int peer = 0; peer < ranks; ++peer) {
        StripPlan::Message m;
        m.peer = peer;
        for (const GhostLayer& g : plan.ghosts) {
            if (g.owner == peer) {
                m.layers.push_back(g);
            }
        }
        if (!m.layers.empty()) {
            plan.recvs.push_back(m);
        }
    }
    // Wysyłka: warstwy własne, których potrzebują inni, w kolejności okna odbiorcy (ta sama kolejność co jego odbiór).
    for (int peer = 0; peer < ranks; ++peer) {
        if (peer == rank) {
            continue;
        }
        const StripPlan other = ghostsOf(layers, ranks, peer, lo, spec);
        StripPlan::Message m;
        m.peer = peer;
        for (const GhostLayer& g : other.ghosts) {
            if (g.owner == rank) {
                GhostLayer s = g;
                s.local = plan.ownLo + (g.global - plan.lo);  // ta warstwa w oknie nadawcy
                m.layers.push_back(s);
            }
        }
        if (!m.layers.empty()) {
            plan.sends.push_back(m);
        }
    }
    return plan;
}

}  // namespace volcano
