#include "io/ResultWriter.hpp"

#include <charconv>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <stdexcept>

namespace volcano {

namespace {

// Otwiera plik do zapisu albo zgłasza błąd z nazwą pliku.
std::ofstream openOut(const std::string& path, bool binary) {
    std::ofstream out(path, binary ? std::ios::binary : std::ios::out);
    if (!out) {
        throw std::runtime_error("Nie można utworzyć pliku: " + path);
    }
    return out;
}

// Zapisuje tablicę wartości w postaci surowych bajtów.
template <class T>
void writeArray(std::ofstream& out, const std::vector<T>& v) {
    out.write(reinterpret_cast<const char*>(v.data()), static_cast<std::streamsize>(v.size() * sizeof(T)));
}

// OPTYMALIZACJA (etap 8, k7): zapis plików tekstowych wyników (ca_result.txt, mc_result.txt) bez strumieni
// i printf — znaki dopisywane wskaźnikiem do bufora ~1 MB (bez sprawdzania rozmiaru przy każdym znaku), liczby
// całkowite przez to_chars, temperatura własnym formatowaniem (ResultWriter::formatTemp), wspólny fragment
// wiersza „ y z ” liczony raz na wiersz siatki. Plik otwarty binarnie, koniec wiersza dopisywany jawnie:
// na Windows "\r\n" — te same bajty, które dawał tryb tekstowy (biblioteka C zamieniała '\n' na "\r\n",
// kopiując cały bufor), w Linuksie "\n". Format i zawartość plików bez zmian (bajt w bajt, test w test_io.cpp).
#ifdef _WIN32
constexpr char kEol[] = "\r\n";
#else
constexpr char kEol[] = "\n";
#endif
constexpr std::size_t kEolLen = sizeof(kEol) - 1;
constexpr std::ptrdiff_t kFlushAt = 1 << 20;  // ~1 MB
constexpr std::size_t kMaxLine = 256;         // najdłuższy wiersz (liczby int32 + temperatura) z zapasem

// Dopisuje liczbę całkowitą (to_chars — bez locale i bez alokacji); zwraca pozycję za ostatnim znakiem.
char* putInt(char* p, long long v) { return std::to_chars(p, p + 24, v).ptr; }

char* putText(char* p, const char* s, std::size_t n) {
    std::memcpy(p, s, n);
    return p + n;
}

char* putEol(char* p) { return putText(p, kEol, kEolLen); }

// Bufor wiersza pliku tekstowego: dopisywanie wskaźnikiem, zapis do pliku po przekroczeniu kFlushAt
// (bufor ma kFlushAt + kMaxLine bajtów, więc jeden wiersz zawsze się mieści).
class LineBuffer {
public:
    explicit LineBuffer(std::ofstream& out) : out_(out), buf_(static_cast<std::size_t>(kFlushAt) + kMaxLine) {}

    char* begin() { return buf_.data(); }

    // Po dopisaniu wiersza (p = pozycja za nim): zapis do pliku, jeśli bufor jest pełny.
    char* commit(char* p) {
        if (p - buf_.data() >= kFlushAt) {
            return flush(p);
        }
        return p;
    }

    char* flush(char* p) {
        out_.write(buf_.data(), static_cast<std::streamsize>(p - buf_.data()));
        return buf_.data();
    }

private:
    std::ofstream& out_;
    std::vector<char> buf_;
};

// Nagłówek „nx ny nz” + wiersz z nazwami kolumn.
char* putHeader(char* p, const Dims& d, const char* columns) {
    p = putInt(p, d.nx);
    *p++ = ' ';
    p = putInt(p, d.ny);
    *p++ = ' ';
    p = putInt(p, d.nz);
    p = putEol(p);
    p = putText(p, columns, std::strlen(columns));
    return putEol(p);
}

// Fragment wiersza „ y z ” (ze spacjami po obu stronach) — wspólny dla całego wiersza siatki; zwraca długość.
std::size_t rowSuffix(char* out, int y, int z) {
    char* p = out;
    *p++ = ' ';
    p = putInt(p, y);
    *p++ = ' ';
    p = putInt(p, z);
    *p++ = ' ';
    return static_cast<std::size_t>(p - out);
}

}  // namespace

std::size_t ResultWriter::formatTemp(char* out, float v) {
    // printf("%.1f") zaokrągla DOKŁADNĄ wartość dziesiętną liczby do 1 miejsca po przecinku (remis — do parzystej:
    // glibc, biblioteka C Windows od Windows 10 2004). Iloczyn v·10 jest w double dokładny (mantysa float 24 bity
    // × 10 → najwyżej 27 bitów), więc zaokrąglenie t = v·10 do całkowitej w domyślnym trybie (do najbliższej,
    // remis do parzystej — std::nearbyint) daje te same cyfry. Minus jak w printf: także dla −0,0 i wartości ujemnych
    // zaokrąglonych do zera („-0.0”). NaN, nieskończoność i ogromne wartości (|t| ≥ 10^15) — przez snprintf.
    const double t = static_cast<double>(v) * 10.0;
    if (!(std::fabs(t) < 1e15)) {
        return static_cast<std::size_t>(std::snprintf(out, kTempChars, "%.1f", static_cast<double>(v)));
    }
    char* p = out;
    if (std::signbit(v)) {
        *p++ = '-';
    }
    const auto n = static_cast<unsigned long long>(std::fabs(std::nearbyint(t)));
    p = std::to_chars(p, p + 24, n / 10).ptr;
    *p++ = '.';
    *p++ = static_cast<char>('0' + n % 10);
    return static_cast<std::size_t>(p - out);
}

void ResultWriter::writeTxt(const std::string& path, const Microstructure& m) {
    std::ofstream out = openOut(path, true);
    const Dims& d = m.dims;
    LineBuffer buf(out);
    char* p = putHeader(buf.begin(), d, "x y z type flowId temp");

    std::size_t i = 0;
    char yz[32];
    for (int z = 0; z < d.nz; ++z) {
        for (int y = 0; y < d.ny; ++y) {
            const std::size_t yzLen = rowSuffix(yz, y, z);
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
    if (!out) {
        throw std::runtime_error("Błąd zapisu pliku: " + path);
    }
}

void ResultWriter::writeBin(const std::string& path, const Microstructure& m) {
    std::ofstream out = openOut(path, true);
    const std::vector<char> header = binHeader(m.dims);
    out.write(header.data(), static_cast<std::streamsize>(header.size()));
    writeArray(out, m.type);
    writeArray(out, m.flowId);
    writeArray(out, m.temp);
    writeArray(out, m.solidStep);
    writeArray(out, m.arrivalStep);
    if (!out) {
        throw std::runtime_error("Błąd zapisu pliku: " + path);
    }
}

void ResultWriter::writeCrystalTxt(const std::string& path, const CrystalMap& m) {
    std::ofstream out = openOut(path, true);
    const Dims& d = m.dims;
    LineBuffer buf(out);
    char* p = putHeader(buf.begin(), d, "x y z crystal");

    std::size_t i = 0;
    char yz[32];
    for (int z = 0; z < d.nz; ++z) {
        for (int y = 0; y < d.ny; ++y) {
            const std::size_t yzLen = rowSuffix(yz, y, z);
            for (int x = 0; x < d.nx; ++x, ++i) {
                p = putInt(p, x);
                p = putText(p, yz, yzLen);
                p = putInt(p, m.crystal[i]);
                p = buf.commit(putEol(p));
            }
        }
    }
    buf.flush(p);
    if (!out) {
        throw std::runtime_error("Błąd zapisu pliku: " + path);
    }
}

void ResultWriter::writeCrystalBin(const std::string& path, const CrystalMap& m) {
    std::ofstream out = openOut(path, true);
    const std::vector<char> header = crystalBinHeader(m.dims);
    out.write(header.data(), static_cast<std::streamsize>(header.size()));
    writeArray(out, m.crystal);
    if (!out) {
        throw std::runtime_error("Błąd zapisu pliku: " + path);
    }
}

std::vector<char> ResultWriter::binHeader(const Dims& d) {
    const char magic[4] = {'V', 'O', 'L', 'C'};
    const std::uint32_t version = kBinVersion;
    const std::int32_t dims[3] = {d.nx, d.ny, d.nz};
    std::vector<char> h(sizeof(magic) + sizeof(version) + sizeof(dims));
    std::memcpy(h.data(), magic, sizeof(magic));
    std::memcpy(h.data() + sizeof(magic), &version, sizeof(version));
    std::memcpy(h.data() + sizeof(magic) + sizeof(version), dims, sizeof(dims));
    return h;
}

std::vector<char> ResultWriter::crystalBinHeader(const Dims& d) {
    const char magic[4] = {'V', 'M', 'C', '1'};
    const std::int32_t dims[3] = {d.nx, d.ny, d.nz};
    std::vector<char> h(sizeof(magic) + sizeof(dims));
    std::memcpy(h.data(), magic, sizeof(magic));
    std::memcpy(h.data() + sizeof(magic), dims, sizeof(dims));
    return h;
}

void ResultWriter::writeMcStatsCsv(const std::string& path, const std::vector<McStats>& history) {
    std::ofstream out = openOut(path, false);
    out << "mcs,grains,meanGrainSize,energy,acceptRate\n";
    char line[160];
    for (const McStats& s : history) {
        std::snprintf(line, sizeof(line), "%d,%llu,%.4f,%.3f,%.6f\n", s.mcs,
                      static_cast<unsigned long long>(s.grains), s.meanGrainSize, s.energy, s.acceptRate);
        out << line;
    }
    if (!out) {
        throw std::runtime_error("Błąd zapisu pliku: " + path);
    }
}

void ResultWriter::writeJson(const std::string& path, const nlohmann::ordered_json& j) {
    std::ofstream out = openOut(path, false);
    out << j.dump(2) << '\n';
    if (!out) {
        throw std::runtime_error("Błąd zapisu pliku: " + path);
    }
}

}  // namespace volcano
