// Etap 11 (engine_mpi, mpi.io = "mpiio"): tekst plików wyników (ca_result.txt, mc_result.txt) z pasów warstw —
// nagłówek i wiersze pasa jako napis, który proces zapisuje przez MPI-IO pod swoim przesunięciem (mpi/MpiIo.cpp).
// Te same znaki co ResultWriter::writeTxt / writeCrystalTxt: temperatura przez ResultWriter::formatTemp (formatter
// z etapu 8, k7), liczby całkowite przez std::to_chars, koniec wiersza jak w ResultWriter.cpp. Zgodność bajtową
// z całym plikiem sprawdza test_io.cpp (pasy sklejone = writeTxt / writeCrystalTxt), a pliki MPI-IO — test_mpi.cpp.
//
// Osobny plik, a nie ResultWriter.cpp: te same pętle w jednym pliku z writeTxt zmieniały decyzje MSVC o wstawianiu
// funkcji pomocniczych i writeTxt programu engine był o 8–9% wolniejszy (ca_result.txt 1000²: 63 -> 69 ms; dziennik
// bench/results/mpi_io/POSTEP.md). Drobne funkcje znaków są tu więc skopiowane; engine (bez MPI-IO) tego pliku nie
// dołącza — biblioteka statyczna bierze tylko używane pliki obiektowe.

#include <charconv>
#include <cstring>

#include "io/ResultWriter.hpp"

namespace volcano {

namespace {

#ifdef _WIN32
constexpr char kEol[] = "\r\n";  // jak w ResultWriter.cpp: na Windows te same bajty co tryb tekstowy
#else
constexpr char kEol[] = "\n";
#endif
constexpr std::size_t kEolLen = sizeof(kEol) - 1;
constexpr std::ptrdiff_t kFlushAt = 1 << 20;  // ~1 MB
constexpr std::size_t kMaxLine = 256;         // najdłuższy wiersz z zapasem

char* putInt(char* p, long long v) { return std::to_chars(p, p + 24, v).ptr; }

char* putText(char* p, const char* s, std::size_t n) {
    std::memcpy(p, s, n);
    return p + n;
}

char* putEol(char* p) { return putText(p, kEol, kEolLen); }

// Fragment wiersza „ y z ” — wspólny dla całego wiersza siatki; zwraca długość.
std::size_t rowSuffix(char* out, int y, int z) {
    char* p = out;
    *p++ = ' ';
    p = putInt(p, y);
    *p++ = ' ';
    p = putInt(p, z);
    *p++ = ' ';
    return static_cast<std::size_t>(p - out);
}

// Bufor wiersza dopisywany do napisu po przekroczeniu kFlushAt (jak LineBuffer w ResultWriter.cpp dla pliku).
class TextBuffer {
public:
    explicit TextBuffer(std::string& out) : out_(out), buf_(static_cast<std::size_t>(kFlushAt) + kMaxLine) {}

    char* begin() { return buf_.data(); }

    char* commit(char* p) {
        if (p - buf_.data() >= kFlushAt) {
            return flush(p);
        }
        return p;
    }

    char* flush(char* p) {
        out_.append(buf_.data(), static_cast<std::size_t>(p - buf_.data()));
        return buf_.data();
    }

private:
    std::string& out_;
    std::vector<char> buf_;
};

}  // namespace

std::string ResultWriter::txtHeader(const Dims& d, bool crystal) {
    char buf[kMaxLine];
    char* p = putInt(buf, d.nx);
    *p++ = ' ';
    p = putInt(p, d.ny);
    *p++ = ' ';
    p = putInt(p, d.nz);
    p = putEol(p);
    const char* columns = crystal ? "x y z crystal" : "x y z type flowId temp";
    p = putText(p, columns, std::strlen(columns));
    p = putEol(p);
    return std::string(buf, static_cast<std::size_t>(p - buf));
}

void ResultWriter::appendTxtRows(std::string& out, const Microstructure& m, const Dims& global, int layer0) {
    const Dims& d = m.dims;
    const bool axisZ = global.nz > 1;  // oś warstw (parallel/Strip.hpp): z, w płaszczyźnie x–y — y
    const int yShift = axisZ ? 0 : layer0;
    const int zShift = axisZ ? layer0 : 0;
    out.reserve(out.size() + d.cells() * 24);  // typowy wiersz ma ~20 znaków
    TextBuffer buf(out);
    char* p = buf.begin();
    std::size_t i = 0;
    char yz[32];
    for (int z = 0; z < d.nz; ++z) {
        for (int y = 0; y < d.ny; ++y) {
            const std::size_t yzLen = rowSuffix(yz, y + yShift, z + zShift);
            for (int x = 0; x < d.nx; ++x, ++i) {
                p = putInt(p, x);
                p = putText(p, yz, yzLen);
                p = putInt(p, static_cast<int>(m.type[i]));
                *p++ = ' ';
                p = putInt(p, m.flowId[i]);
                *p++ = ' ';
                p += formatTemp(p, m.temp[i]);
                p = buf.commit(putEol(p));
            }
        }
    }
    buf.flush(p);
}

void ResultWriter::appendCrystalTxtRows(std::string& out, const Dims& d, const std::int32_t* crystal,
                                        const Dims& global, int layer0) {
    const bool axisZ = global.nz > 1;
    const int yShift = axisZ ? 0 : layer0;
    const int zShift = axisZ ? layer0 : 0;
    out.reserve(out.size() + d.cells() * 16);
    TextBuffer buf(out);
    char* p = buf.begin();
    std::size_t i = 0;
    char yz[32];
    for (int z = 0; z < d.nz; ++z) {
        for (int y = 0; y < d.ny; ++y) {
            const std::size_t yzLen = rowSuffix(yz, y + yShift, z + zShift);
            for (int x = 0; x < d.nx; ++x, ++i) {
                p = putInt(p, x);
                p = putText(p, yz, yzLen);
                p = putInt(p, crystal[i]);
                p = buf.commit(putEol(p));
            }
        }
    }
    buf.flush(p);
}

}  // namespace volcano
