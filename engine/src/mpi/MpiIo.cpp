#include "mpi/MpiIo.hpp"

#include <algorithm>
#include <climits>
#include <stdexcept>

#include "io/ResultWriter.hpp"
#include "mpi/MpiTypes.hpp"
#include "parallel/Strip.hpp"

namespace volcano {

namespace {

constexpr std::uint64_t kChunk = std::uint64_t{1} << 30;  // porcja zapisu / odczytu: liczba elementów MPI to int

// Kod błędu MPI-IO -> wyjątek z opisem (pliki MPI mają domyślnie obsługę błędów MPI_ERRORS_RETURN).
void check(int rc, const char* what, const std::string& path) {
    if (rc != MPI_SUCCESS) {
        char msg[MPI_MAX_ERROR_STRING] = {};
        int len = 0;
        MPI_Error_string(rc, msg, &len);
        throw std::runtime_error(std::string("MPI-IO (") + what + ") " + path + ": " + std::string(msg, len));
    }
}

int toInt(std::uint64_t v, const char* what) {
    if (v > static_cast<std::uint64_t>(INT_MAX)) {
        throw std::runtime_error(std::string("MPI-IO: ") + what + " ma więcej niż 2 GB — za dużo na jeden blok typu MPI");
    }
    return static_cast<int>(v);
}

int rankOf(MPI_Comm comm) {
    int r = 0;
    MPI_Comm_rank(comm, &r);
    return r;
}

// Warstwy pasa slab (oś warstw przestrzeni global: z, w płaszczyźnie x–y — y; pas jednej warstwy 3D ma nz = 1).
int stripLayers(const Dims& global, const Dims& slab) { return layerAxisZ(global) ? slab.nz : slab.ny; }

MPI_File openFile(MPI_Comm comm, const std::string& path, int mode) {
    MPI_File fh = MPI_FILE_NULL;
    check(MPI_File_open(comm, const_cast<char*>(path.c_str()), mode, MPI_INFO_NULL, &fh), "otwarcie", path);
    return fh;
}

// Zapis albo odczyt zbiorowy bytes bajtów pod przesunięciem offset, w porcjach < 2 GB (liczba porcji — maksimum po
// procesach, bo każde wywołanie _at_all jest zbiorowe; proces bez danych bierze udział z 0 bajtów).
void chunked(MPI_Comm comm, MPI_File fh, MPI_Offset offset, char* data, std::uint64_t bytes, bool write,
             const std::string& path) {
    unsigned long long rounds = (bytes + kChunk - 1) / kChunk;
    MPI_Allreduce(MPI_IN_PLACE, &rounds, 1, MPI_UNSIGNED_LONG_LONG, MPI_MAX, comm);
    for (unsigned long long k = 0; k < rounds; ++k) {
        const std::uint64_t begin = std::min<std::uint64_t>(k * kChunk, bytes);
        const int n = static_cast<int>(std::min<std::uint64_t>(kChunk, bytes - begin));
        const MPI_Offset at = offset + static_cast<MPI_Offset>(begin);
        if (write) {
            check(MPI_File_write_at_all(fh, at, data + begin, n, MPI_BYTE, MPI_STATUS_IGNORE), "zapis", path);
        } else {
            check(MPI_File_read_at_all(fh, at, data + begin, n, MPI_BYTE, MPI_STATUS_IGNORE), "odczyt", path);
        }
    }
}

// Tablica pola całej przestrzeni w pliku: dane własnych warstw tego procesu i rozmiar elementu.
struct Array {
    const void* data;
    std::size_t elem;
};

// Plik binarny = nagłówek + tablice (L warstw po plane komórek każda); proces zapisuje pas [lo, hi) każdej tablicy.
IoTimes writeStrips(MPI_Comm comm, const std::string& path, const std::vector<char>& header,
                    const std::vector<Array>& arrays, int L, std::uint64_t plane, int lo, int hi) {
    IoTimes t;
    const double t0 = MPI_Wtime();
    const int rank = rankOf(comm);
    // Widok pliku: pas w każdej tablicy (subarray L × bajty warstwy, warstwy [lo, hi)), tablice po kolei (struct).
    std::vector<MpiType> subs;
    std::vector<int> lens;
    std::vector<MPI_Aint> displs;
    std::vector<MPI_Datatype> types;
    std::uint64_t arrayStart = 0;
    for (const Array& a : arrays) {
        const int rowBytes = toInt(plane * a.elem, "warstwa tablicy");
        int sizes[2] = {L, rowBytes};
        int subsizes[2] = {hi - lo, rowBytes};
        int starts[2] = {lo, 0};
        MPI_Datatype s = MPI_DATATYPE_NULL;
        MPI_Type_create_subarray(2, sizes, subsizes, starts, MPI_ORDER_C, MPI_BYTE, &s);
        subs.emplace_back(s);
        lens.push_back(1);
        displs.push_back(static_cast<MPI_Aint>(arrayStart));
        types.push_back(s);
        arrayStart += static_cast<std::uint64_t>(L) * plane * a.elem;
    }
    MPI_Datatype ft = MPI_DATATYPE_NULL;
    MPI_Type_create_struct(static_cast<int>(arrays.size()), lens.data(), displs.data(), types.data(), &ft);
    MPI_Type_commit(&ft);
    const MpiType fileType(ft);
    // Dane w pamięci: pasy pól (osobne tablice SoA) — przesunięcia względem tablicy o najniższym adresie, która jest
    // buforem zapisu. Nie MPI_BOTTOM z adresami bezwzględnymi: MS-MPI (ROMIO) przy typie z jednym blokiem (mc_result.bin)
    // uznaje go za ciągły i czyta od samego wskaźnika bufora — od MPI_BOTTOM (adres 0) — naruszenie dostępu.
    std::vector<int> mlens;
    std::vector<MPI_Aint> mdispls;
    std::vector<MPI_Datatype> mtypes;
    std::size_t base = 0;
    for (std::size_t k = 0; k < arrays.size(); ++k) {
        MPI_Aint addr = 0;
        MPI_Get_address(const_cast<void*>(arrays[k].data), &addr);
        mlens.push_back(toInt(static_cast<std::uint64_t>(hi - lo) * plane * arrays[k].elem, "pas tablicy"));
        mdispls.push_back(addr);
        mtypes.push_back(MPI_BYTE);
        t.ownBytes += static_cast<std::uint64_t>(mlens.back());
        base = mdispls[k] < mdispls[base] ? k : base;
    }
    const MPI_Aint baseAddr = mdispls[base];
    for (MPI_Aint& d : mdispls) {
        d -= baseAddr;
    }
    void* const buffer = const_cast<void*>(arrays[base].data);
    MPI_Datatype mt = MPI_DATATYPE_NULL;
    MPI_Type_create_struct(static_cast<int>(arrays.size()), mlens.data(), mdispls.data(), mtypes.data(), &mt);
    MPI_Type_commit(&mt);
    const MpiType memType(mt);

    t.fileBytes = header.size() + arrayStart;
    MPI_File fh = openFile(comm, path, MPI_MODE_CREATE | MPI_MODE_WRONLY);
    check(MPI_File_set_size(fh, static_cast<MPI_Offset>(t.fileBytes)), "rozmiar", path);
    if (rank == 0) {
        check(MPI_File_write_at(fh, 0, const_cast<char*>(header.data()), static_cast<int>(header.size()), MPI_BYTE,
                                MPI_STATUS_IGNORE),
              "nagłówek", path);
        t.ownBytes += header.size();
    }
    check(MPI_File_set_view(fh, static_cast<MPI_Offset>(header.size()), MPI_BYTE, ft, const_cast<char*>("native"),
                            MPI_INFO_NULL),
          "widok", path);
    check(MPI_File_write_all(fh, buffer, 1, mt, MPI_STATUS_IGNORE), "zapis", path);
    check(MPI_File_close(&fh), "zamknięcie", path);
    t.ioMs = (MPI_Wtime() - t0) * 1000.0;
    return t;
}

// Plik tekstowy z części: text — tekst tego procesu (proces 0: nagłówek + jego wiersze); przesunięcie = suma długości
// tekstu procesów o mniejszym numerze (MPI_Exscan).
IoTimes writeText(MPI_Comm comm, const std::string& path, std::string& text, IoTimes t) {
    const double t0 = MPI_Wtime();
    unsigned long long len = text.size();
    unsigned long long off = 0;
    MPI_Exscan(&len, &off, 1, MPI_UNSIGNED_LONG_LONG, MPI_SUM, comm);
    if (rankOf(comm) == 0) {
        off = 0;  // wynik MPI_Exscan na procesie 0 jest nieokreślony
    }
    unsigned long long total = 0;
    MPI_Allreduce(&len, &total, 1, MPI_UNSIGNED_LONG_LONG, MPI_SUM, comm);
    MPI_File fh = openFile(comm, path, MPI_MODE_CREATE | MPI_MODE_WRONLY);
    check(MPI_File_set_size(fh, static_cast<MPI_Offset>(total)), "rozmiar", path);
    chunked(comm, fh, static_cast<MPI_Offset>(off), text.empty() ? nullptr : &text[0], len, true, path);
    check(MPI_File_close(&fh), "zamknięcie", path);
    t.ioMs = (MPI_Wtime() - t0) * 1000.0;
    t.fileBytes = total;
    t.ownBytes = len;
    return t;
}

}  // namespace

IoTimes MpiIo::writeCaBin(MPI_Comm comm, const std::string& path, const Dims& global, int lo,
                          const Microstructure& slab) {
    const std::vector<Array> arrays = {{slab.type.data(), sizeof(CellType)},
                                       {slab.flowId.data(), sizeof(std::int32_t)},
                                       {slab.temp.data(), sizeof(float)},
                                       {slab.solidStep.data(), sizeof(std::uint16_t)},
                                       {slab.arrivalStep.data(), sizeof(std::uint16_t)}};
    return writeStrips(comm, path, ResultWriter::binHeader(global), arrays, layerCountOf(global),
                       layerPlane(global), lo, lo + stripLayers(global, slab.dims));
}

IoTimes MpiIo::writeCaTxt(MPI_Comm comm, const std::string& path, const Dims& global, int lo,
                          const Microstructure& slab) {
    IoTimes t;
    const double t0 = MPI_Wtime();
    std::string text = rankOf(comm) == 0 ? ResultWriter::txtHeader(global, false) : std::string();
    ResultWriter::appendTxtRows(text, slab, global, lo);
    t.formatMs = (MPI_Wtime() - t0) * 1000.0;
    return writeText(comm, path, text, t);
}

IoTimes MpiIo::writeCrystalBin(MPI_Comm comm, const std::string& path, const Dims& global, int lo, const Dims& slab,
                               const std::vector<std::int32_t>& own) {
    const std::vector<Array> arrays = {{own.data(), sizeof(std::int32_t)}};
    return writeStrips(comm, path, ResultWriter::crystalBinHeader(global), arrays, layerCountOf(global),
                       layerPlane(global), lo, lo + stripLayers(global, slab));
}

IoTimes MpiIo::writeCrystalTxt(MPI_Comm comm, const std::string& path, const Dims& global, int lo, const Dims& slab,
                               const std::vector<std::int32_t>& own) {
    IoTimes t;
    const double t0 = MPI_Wtime();
    std::string text = rankOf(comm) == 0 ? ResultWriter::txtHeader(global, true) : std::string();
    ResultWriter::appendCrystalTxtRows(text, slab, own.data(), global, lo);
    t.formatMs = (MPI_Wtime() - t0) * 1000.0;
    return writeText(comm, path, text, t);
}

IoTimes MpiIo::readCaStrip(MPI_Comm comm, const std::string& path, const BinHeader& h, int lo, Microstructure& slab) {
    IoTimes t;
    const double t0 = MPI_Wtime();
    const std::uint64_t n = h.dims.cells();
    const std::uint64_t plane = layerPlane(h.dims);
    const std::uint64_t cells = static_cast<std::uint64_t>(stripLayers(h.dims, slab.dims)) * plane;
    const std::uint64_t first = static_cast<std::uint64_t>(lo) * plane;
    // Tablice w pliku: type (1 B), flowId (4), temp (4), solidStep (2), arrivalStep (2, od wersji 2).
    const std::uint64_t typeAt = h.dataOffset;
    const std::uint64_t solidAt = typeAt + n * (sizeof(CellType) + sizeof(std::int32_t) + sizeof(float));
    const std::uint64_t arrivalAt = solidAt + n * sizeof(std::uint16_t);
    MPI_File fh = openFile(comm, path, MPI_MODE_RDONLY);
    chunked(comm, fh, static_cast<MPI_Offset>(typeAt + first * sizeof(CellType)),
            reinterpret_cast<char*>(slab.type.data()), cells * sizeof(CellType), false, path);
    chunked(comm, fh, static_cast<MPI_Offset>(solidAt + first * sizeof(std::uint16_t)),
            reinterpret_cast<char*>(slab.solidStep.data()), cells * sizeof(std::uint16_t), false, path);
    t.ownBytes = cells * (sizeof(CellType) + sizeof(std::uint16_t));
    if (h.version >= 2) {
        chunked(comm, fh, static_cast<MPI_Offset>(arrivalAt + first * sizeof(std::uint16_t)),
                reinterpret_cast<char*>(slab.arrivalStep.data()), cells * sizeof(std::uint16_t), false, path);
        t.ownBytes += cells * sizeof(std::uint16_t);
    }
    check(MPI_File_close(&fh), "zamknięcie", path);
    unsigned long long own = t.ownBytes;
    unsigned long long all = 0;
    MPI_Allreduce(&own, &all, 1, MPI_UNSIGNED_LONG_LONG, MPI_SUM, comm);
    t.fileBytes = all;
    t.ioMs = (MPI_Wtime() - t0) * 1000.0;
    return t;
}

}  // namespace volcano
