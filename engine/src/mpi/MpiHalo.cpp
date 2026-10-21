#include "mpi/MpiHalo.hpp"

#include <algorithm>
#include <cstring>
#include <stdexcept>
#include <utility>

#include "core/Storage.hpp"
#include "mc/PottsMC.hpp"

namespace volcano {

namespace {

constexpr int kFlagTagOffset = 100;  // datatype + changed: znacznik komunikatu flag = znacznik etapu + 100

// Typ MPI elementu pola (indeks = numer bitu maski StripField): typ komórki, flowId, temperatura, solidStep,
// arrivalStep, orientacja MC.
MPI_Datatype fieldType(int f) {
    static_assert(sizeof(CellType) == 1 && sizeof(int) == 4 && sizeof(float) == 4 && sizeof(unsigned short) == 2,
                  "rozmiary pól = rozmiary typów MPI");
    switch (f) {
        case 0: return MPI_UNSIGNED_CHAR;
        case 1: return MPI_INT;
        case 2: return MPI_FLOAT;
        case 3: return MPI_UNSIGNED_SHORT;
        case 4: return MPI_UNSIGNED_SHORT;
        default: return MPI_INT;
    }
}

}  // namespace

MpiHalo::MpiHalo(MPI_Comm comm, StripPlan plan, bool changedOnly, bool datatypes, int tag)
    : comm_(comm), plan_(std::move(plan)), changedOnly_(changedOnly), datatypes_(datatypes), tag_(tag) {
    sendBuf_.resize(plan_.sends.size());
    lastSent_.resize(plan_.sends.size());
    lastValid_.assign(plan_.sends.size(), false);
    recvBuf_.resize(plan_.recvs.size());
    // datatype + changed: flagi odbierane osobno, więc odbiory flag i danych to 2 · recvs, wysyłki — 2 · sends
    requests_.resize(2 * (plan_.sends.size() + plan_.recvs.size()), MPI_REQUEST_NULL);
    flagsOut_.resize(plan_.sends.size());
    flagsIn_.resize(plan_.recvs.size());
    for (std::size_t j = 0; j < plan_.sends.size(); ++j) {
        if (plan_.sends[j].layers.size() > 64) {
            throw std::logic_error("komunikat warstw brzegowych ma więcej niż 64 warstwy (maska flag)");
        }
        flagsOut_[j].assign(plan_.sends[j].layers.size(), 0);
    }
    for (std::size_t i = 0; i < plan_.recvs.size(); ++i) {
        flagsIn_[i].assign(plan_.recvs[i].layers.size(), 0);
    }
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
        datatypes_ ? runTyped(a, &b) : run(a, &b);
    } else {
        datatypes_ ? runTyped(a, nullptr) : run(a, nullptr);
    }
}

void MpiHalo::exchange(PottsMC& mc) {
    const Layers a = of(mc);
    datatypes_ ? runTyped(a, nullptr) : run(a, nullptr);
}

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
                std::memcpy(out, src.at(f, g.local), bytes);
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
                std::memcpy(src.at(f, g.local), in, bytes);
                if (second != nullptr) {
                    std::memcpy(second->at(f, g.local), in, bytes);
                }
                in += bytes;
            }
        }
    }
    ++active_->exchanges;
    active_->haloMs += (MPI_Wtime() - t0) * 1000.0;
}

MPI_Datatype MpiHalo::messageType(const Layers& src, bool send, std::size_t index, const StripPlan::Message& m,
                                  std::uint64_t mask, int& bytes) {
    const auto key = std::make_tuple(src.key(), send, index, mask);
    const auto it = types_.find(key);
    if (it != types_.end()) {
        bytes = it->second.second;
        return it->second.first.get();
    }
    const double t0 = MPI_Wtime();
    // Bloki „warstwa pola” w kolejności warstw komunikatu, w warstwie — pól; kolejne warstwy tego samego pola leżące
    // w tablicy obok siebie łączą się w jeden blok (liczba warstw = długość bloku w typach warstwy).
    std::vector<int> lens;
    std::vector<MPI_Aint> displs;
    std::vector<MPI_Datatype> types;
    int lastField = -1;
    const unsigned char* nextAddr = nullptr;
    for (std::size_t s = 0; s < m.layers.size(); ++s) {
        if ((mask & (std::uint64_t{1} << s)) == 0) {
            continue;
        }
        const GhostLayer& g = m.layers[s];
        for (int f = 0; f < 6; ++f) {
            if ((g.fields & (1u << f)) == 0) {
                continue;
            }
            unsigned char* const addr = src.at(f, g.local);
            if (f == lastField && addr == nextAddr) {
                ++lens.back();
            } else {
                MPI_Aint a = 0;
                MPI_Get_address(addr, &a);
                lens.push_back(1);
                displs.push_back(a);
                types.push_back(layerType_[f].get());
            }
            lastField = f;
            nextAddr = addr + src.cells * src.elem[f];
        }
    }
    MPI_Datatype t = MPI_DATATYPE_NULL;
    MPI_Type_create_struct(static_cast<int>(lens.size()), lens.data(), displs.data(), types.data(), &t);
    MPI_Type_commit(&t);
    MPI_Type_size(t, &bytes);
    types_.emplace(key, std::make_pair(MpiType(t), bytes));
    ++active_->typesBuilt;
    active_->typeBuildMs += (MPI_Wtime() - t0) * 1000.0;
    return t;
}

void MpiHalo::copyLayers(const Layers& src, const Layers& second, const StripPlan::Message& m, std::uint64_t mask) {
    for (std::size_t s = 0; s < m.layers.size(); ++s) {
        if ((mask & (std::uint64_t{1} << s)) == 0) {
            continue;
        }
        const GhostLayer& g = m.layers[s];
        for (int f = 0; f < 6; ++f) {
            if ((g.fields & (1u << f)) != 0) {
                std::memcpy(second.at(f, g.local), src.at(f, g.local), src.elem[f] * src.cells);
            }
        }
    }
}

void MpiHalo::runTyped(const Layers& src, const Layers* second) {
    const double t0 = MPI_Wtime();
    if (cells_ != src.cells || layerType_[0].get() == MPI_DATATYPE_NULL) {
        // Typ warstwy każdego pola (rozmiar warstwy okna nie zmienia się w trakcie etapu).
        cells_ = src.cells;
        for (int f = 0; f < 6; ++f) {
            MPI_Datatype t = MPI_DATATYPE_NULL;
            MPI_Type_contiguous(static_cast<int>(cells_), fieldType(f), &t);
            MPI_Type_commit(&t);
            layerType_[f] = MpiType(t);
        }
    }
    const std::size_t nr = plan_.recvs.size();
    const std::size_t ns = plan_.sends.size();
    const auto all = [](std::size_t n) { return n >= 64 ? ~std::uint64_t{0} : (std::uint64_t{1} << n) - 1; };
    MPI_Request* const recvData = requests_.data();               // [0, nr)
    MPI_Request* const sendData = requests_.data() + nr;          // [nr, nr + ns)
    MPI_Request* const recvFlags = requests_.data() + nr + ns;    // [nr + ns, 2·nr + ns)
    MPI_Request* const sendFlags = requests_.data() + 2 * nr + ns;  // [2·nr + ns, 2·(nr + ns))
    std::fill(requests_.begin(), requests_.end(), MPI_REQUEST_NULL);
    int bytes = 0;
    if (!changedOnly_) {
        // "always": odbiór i wysyłka całych komunikatów typem — bez flag i bez bufora.
        for (std::size_t i = 0; i < nr; ++i) {
            const StripPlan::Message& m = plan_.recvs[i];
            const MPI_Datatype t = messageType(src, false, i, m, all(m.layers.size()), bytes);
            MPI_Irecv(MPI_BOTTOM, 1, t, m.peer, tag_, comm_, &recvData[i]);
        }
        for (std::size_t j = 0; j < ns; ++j) {
            const StripPlan::Message& m = plan_.sends[j];
            const MPI_Datatype t = messageType(src, true, j, m, all(m.layers.size()), bytes);
            MPI_Isend(MPI_BOTTOM, 1, t, m.peer, tag_, comm_, &sendData[j]);
            ++active_->messages;
            active_->bytes += static_cast<std::uint64_t>(bytes);
            active_->layersSent += m.layers.size();
        }
        MPI_Waitall(static_cast<int>(nr + ns), requests_.data(), MPI_STATUSES_IGNORE);
        if (second != nullptr) {
            for (std::size_t i = 0; i < nr; ++i) {
                copyLayers(src, *second, plan_.recvs[i], all(plan_.recvs[i].layers.size()));
            }
        }
    } else {
        // "changed": 1) odbiór flag, 2) nadawca porównuje warstwy z ostatnio wysłanymi i wysyła flagi + dane typem
        // złożonym z warstw z flagą 1, 3) odbiorca po flagach odbiera dane typem dla tej samej maski.
        for (std::size_t i = 0; i < nr; ++i) {
            const StripPlan::Message& m = plan_.recvs[i];
            MPI_Irecv(flagsIn_[i].data(), static_cast<int>(m.layers.size()), MPI_UNSIGNED_CHAR, m.peer,
                      tag_ + kFlagTagOffset, comm_, &recvFlags[i]);
        }
        for (std::size_t j = 0; j < ns; ++j) {
            const StripPlan::Message& m = plan_.sends[j];
            const std::size_t n = m.layers.size();
            std::size_t total = 0;
            for (const GhostLayer& g : m.layers) {
                for (int f = 0; f < 6; ++f) {
                    total += (g.fields & (1u << f)) != 0 ? src.elem[f] * src.cells : 0;
                }
            }
            std::vector<unsigned char>& last = lastSent_[j];
            if (last.size() != total) {
                last.assign(total, 0);
                lastValid_[j] = false;
            }
            std::uint64_t mask = 0;
            std::size_t off = 0;
            for (std::size_t s = 0; s < n; ++s) {
                const GhostLayer& g = m.layers[s];
                bool same = lastValid_[j];
                std::size_t len = 0;
                for (int f = 0; f < 6; ++f) {
                    if ((g.fields & (1u << f)) == 0) {
                        continue;
                    }
                    const std::size_t b = src.elem[f] * src.cells;
                    same = same && std::memcmp(last.data() + off + len, src.at(f, g.local), b) == 0;
                    len += b;
                }
                if (!same) {
                    // warstwa zmieniona (albo pierwsza wymiana) — kopia do pamięci ostatnio wysłanych i flaga 1
                    std::size_t o = off;
                    for (int f = 0; f < 6; ++f) {
                        if ((g.fields & (1u << f)) != 0) {
                            const std::size_t b = src.elem[f] * src.cells;
                            std::memcpy(last.data() + o, src.at(f, g.local), b);
                            o += b;
                        }
                    }
                    mask |= std::uint64_t{1} << s;
                    ++active_->layersSent;
                } else {
                    ++active_->layersSkipped;
                }
                flagsOut_[j][s] = same ? 0 : 1;
                off += len;
            }
            lastValid_[j] = true;
            MPI_Isend(flagsOut_[j].data(), static_cast<int>(n), MPI_UNSIGNED_CHAR, m.peer, tag_ + kFlagTagOffset,
                      comm_, &sendFlags[j]);
            ++active_->messages;
            active_->bytes += n;
            if (mask != 0) {
                const MPI_Datatype t = messageType(src, true, j, m, mask, bytes);
                MPI_Isend(MPI_BOTTOM, 1, t, m.peer, tag_, comm_, &sendData[j]);
                ++active_->messages;
                active_->bytes += static_cast<std::uint64_t>(bytes);
            }
        }
        MPI_Waitall(static_cast<int>(nr), recvFlags, MPI_STATUSES_IGNORE);
        std::vector<std::uint64_t> masks(nr, 0);
        for (std::size_t i = 0; i < nr; ++i) {
            const StripPlan::Message& m = plan_.recvs[i];
            for (std::size_t s = 0; s < m.layers.size(); ++s) {
                masks[i] |= flagsIn_[i][s] != 0 ? std::uint64_t{1} << s : 0;
            }
            if (masks[i] != 0) {
                const MPI_Datatype t = messageType(src, false, i, m, masks[i], bytes);
                MPI_Irecv(MPI_BOTTOM, 1, t, m.peer, tag_, comm_, &recvData[i]);
            }
        }
        MPI_Waitall(static_cast<int>(requests_.size()), requests_.data(), MPI_STATUSES_IGNORE);
        if (second != nullptr) {
            for (std::size_t i = 0; i < nr; ++i) {
                copyLayers(src, *second, plan_.recvs[i], masks[i]);
            }
        }
    }
    ++active_->exchanges;
    active_->haloMs += (MPI_Wtime() - t0) * 1000.0;
}

}  // namespace volcano
