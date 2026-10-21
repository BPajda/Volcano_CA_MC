#include "mpi/MpiHalo.hpp"

#include <cstring>
#include <utility>

#include "core/Storage.hpp"
#include "mc/PottsMC.hpp"

namespace volcano {

MpiHalo::MpiHalo(MPI_Comm comm, StripPlan plan, bool changedOnly, int tag)
    : comm_(comm), plan_(std::move(plan)), changedOnly_(changedOnly), tag_(tag) {
    sendBuf_.resize(plan_.sends.size());
    lastSent_.resize(plan_.sends.size());
    lastValid_.assign(plan_.sends.size(), false);
    recvBuf_.resize(plan_.recvs.size());
    requests_.resize(plan_.sends.size() + plan_.recvs.size());
}

void MpiHalo::sum(std::uint64_t* values, int n) {
    static_assert(sizeof(unsigned long long) == sizeof(std::uint64_t), "MPI_UNSIGNED_LONG_LONG = uint64");
    const double t0 = MPI_Wtime();
    MPI_Allreduce(MPI_IN_PLACE, values, n, MPI_UNSIGNED_LONG_LONG, MPI_SUM, comm_);
    active_->reduceMs += (MPI_Wtime() - t0) * 1000.0;
    ++active_->reductions;
}

MpiHalo::Layers MpiHalo::of(VectorStorage& s) {
    Layers l;
    l.field[0] = reinterpret_cast<unsigned char*>(s.typeData());
    l.field[1] = reinterpret_cast<unsigned char*>(s.flowIdData());
    l.field[2] = reinterpret_cast<unsigned char*>(s.tempData());
    l.field[3] = reinterpret_cast<unsigned char*>(s.solidStepData());
    l.field[4] = reinterpret_cast<unsigned char*>(s.arrivalStepData());
    l.elem[0] = sizeof(CellType);
    l.elem[1] = sizeof(std::int32_t);
    l.elem[2] = sizeof(float);
    l.elem[3] = sizeof(std::uint16_t);
    l.elem[4] = sizeof(std::uint16_t);
    l.start0 = s.layerStart(0);
    l.cells = s.layerCells();
    return l;
}

MpiHalo::Layers MpiHalo::of(PottsMC& mc) {
    Layers l;
    l.field[5] = reinterpret_cast<unsigned char*>(mc.spinData());
    l.elem[5] = sizeof(std::int32_t);
    l.start0 = mc.layerStart(0);
    l.cells = mc.layerCells();
    return l;
}

void MpiHalo::exchange(VectorStorage& cur, VectorStorage* next) {
    const Layers a = of(cur);
    if (next != nullptr) {
        const Layers b = of(*next);
        run(a, &b);
    } else {
        run(a, nullptr);
    }
}

void MpiHalo::exchange(PottsMC& mc) { run(of(mc), nullptr); }

std::size_t MpiHalo::segmentBytes(unsigned fields) const {
    std::size_t b = 0;
    for (int f = 0; f < 6; ++f) {
        if ((fields & (1u << f)) != 0) {
            b += elem_[f] * cells_;
        }
    }
    return b;
}

void MpiHalo::run(const Layers& src, const Layers* second) {
    const double t0 = MPI_Wtime();
    cells_ = src.cells;
    for (int f = 0; f < 6; ++f) {
        if (src.elem[f] != 0) {
            elem_[f] = src.elem[f];
        }
    }
    const std::size_t nr = plan_.recvs.size();
    const std::size_t ns = plan_.sends.size();
    // 1. Odbiory (bufor na pełne dane wszystkich warstw komunikatu — flagi mówią, które przyszły).
    for (std::size_t i = 0; i < nr; ++i) {
        const StripPlan::Message& m = plan_.recvs[i];
        std::size_t cap = m.layers.size();
        for (const GhostLayer& g : m.layers) {
            cap += segmentBytes(g.fields);
        }
        recvBuf_[i].resize(cap);
        MPI_Irecv(recvBuf_[i].data(), static_cast<int>(cap), MPI_BYTE, m.peer, tag_, comm_, &requests_[i]);
    }
    // 2. Pakowanie i wysyłka: flagi, potem dane warstw (pola po kolei, każde jednym memcpy).
    for (std::size_t j = 0; j < ns; ++j) {
        const StripPlan::Message& m = plan_.sends[j];
        const std::size_t n = m.layers.size();
        std::size_t total = 0;
        for (const GhostLayer& g : m.layers) {
            total += segmentBytes(g.fields);
        }
        std::vector<unsigned char>& buf = sendBuf_[j];
        buf.resize(n + total);
        std::vector<unsigned char>& last = lastSent_[j];
        if (changedOnly_ && last.size() != total) {
            last.assign(total, 0);
            lastValid_[j] = false;
        }
        unsigned char* out = buf.data() + n;
        std::size_t cacheOff = 0;
        for (std::size_t s = 0; s < n; ++s) {
            const GhostLayer& g = m.layers[s];
            unsigned char* const begin = out;
            for (int f = 0; f < 6; ++f) {
                if ((g.fields & (1u << f)) == 0) {
                    continue;
                }
                const std::size_t bytes = src.elem[f] * src.cells;
                const std::size_t at = (src.start0 + static_cast<std::size_t>(g.local) * src.cells) * src.elem[f];
                std::memcpy(out, src.field[f] + at, bytes);
                out += bytes;
            }
            const std::size_t len = static_cast<std::size_t>(out - begin);
            bool send = true;
            if (changedOnly_) {
                unsigned char* const cached = last.data() + cacheOff;
                if (lastValid_[j] && std::memcmp(begin, cached, len) == 0) {
                    send = false;  // warstwa bez zmian od ostatniej wysyłki — odbiorca ma ją już w oknie
                    out = begin;
                } else {
                    std::memcpy(cached, begin, len);
                }
            }
            cacheOff += len;
            buf[s] = send ? 1 : 0;
            if (send) {
                ++active_->layersSent;
            } else {
                ++active_->layersSkipped;
            }
        }
        if (changedOnly_) {
            lastValid_[j] = true;
        }
        const int size = static_cast<int>(out - buf.data());
        MPI_Isend(buf.data(), size, MPI_BYTE, m.peer, tag_, comm_, &requests_[nr + j]);
        ++active_->messages;
        active_->bytes += static_cast<std::uint64_t>(size);
    }
    MPI_Waitall(static_cast<int>(nr + ns), requests_.data(), MPI_STATUSES_IGNORE);
    // 3. Rozpakowanie warstw z flagą 1 do okna (w pełnym przebiegu automatu — do obu buforów).
    for (std::size_t i = 0; i < nr; ++i) {
        const StripPlan::Message& m = plan_.recvs[i];
        const unsigned char* const buf = recvBuf_[i].data();
        const std::size_t n = m.layers.size();
        const unsigned char* in = buf + n;
        for (std::size_t s = 0; s < n; ++s) {
            if (buf[s] == 0) {
                continue;
            }
            const GhostLayer& g = m.layers[s];
            for (int f = 0; f < 6; ++f) {
                if ((g.fields & (1u << f)) == 0) {
                    continue;
                }
                const std::size_t bytes = src.elem[f] * src.cells;
                const std::size_t at = (src.start0 + static_cast<std::size_t>(g.local) * src.cells) * src.elem[f];
                std::memcpy(src.field[f] + at, in, bytes);
                if (second != nullptr) {
                    std::memcpy(second->field[f] + at, in, bytes);
                }
                in += bytes;
            }
        }
    }
    ++active_->exchanges;
    active_->haloMs += (MPI_Wtime() - t0) * 1000.0;
}

}  // namespace volcano
