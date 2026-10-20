#include "io/TimingReport.hpp"

#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <system_error>

#ifdef _WIN32
#  ifndef WIN32_LEAN_AND_MEAN
#    define WIN32_LEAN_AND_MEAN
#  endif
#  ifndef NOMINMAX
#    define NOMINMAX
#  endif
#  include <windows.h>
#endif

namespace volcano {

namespace {

// Zaokrąglenie do 0.001 (czytelniejszy plik, precyzja wystarczająca).
double round3(double v) { return std::round(v * 1000.0) / 1000.0; }

// Rozmiar pliku albo suma rozmiarów plików w folderze [B]; 0, gdy nie istnieje.
std::uintmax_t sizeOnDisk(const std::filesystem::path& p) {
    namespace fs = std::filesystem;
    std::error_code ec;
    if (fs::is_directory(p, ec)) {
        std::uintmax_t sum = 0;
        for (const fs::directory_entry& e : fs::directory_iterator(p, ec)) {
            if (e.is_regular_file(ec)) {
                sum += e.file_size(ec);
            }
        }
        return sum;
    }
    const std::uintmax_t size = fs::file_size(p, ec);
    return ec ? 0 : size;
}

}  // namespace

void TimingReport::add(const std::string& section, double ms) {
    for (auto& s : sections_) {
        if (s.first == section) {
            s.second += ms;
            return;
        }
    }
    sections_.emplace_back(section, ms);
}

double TimingReport::get(const std::string& section) const {
    for (const auto& s : sections_) {
        if (s.first == section) {
            return s.second;
        }
    }
    return 0.0;
}

void TimingReport::setInfo(const std::string& key, nlohmann::ordered_json value) {
    info_[key] = std::move(value);
}

void TimingReport::addDetail(const std::string& name, double ms) {
    for (auto& d : details_) {
        if (d.first == name) {
            d.second += ms;
            return;
        }
    }
    details_.emplace_back(name, ms);
}

void TimingReport::addThreadStats(const std::string& stage, nlohmann::ordered_json stats) {
    if (!info_.contains("threadStats")) {
        info_["threadStats"] = nlohmann::ordered_json::object();
    }
    info_["threadStats"][stage] = std::move(stats);
}

void TimingReport::addFile(const std::string& path, double ms) {
    for (FileRecord& f : files_) {
        if (f.path == path) {
            f.ms += ms;
            return;
        }
    }
    files_.push_back(FileRecord{path, ms});
}

void TimingReport::recordFileSizes() {
    nlohmann::ordered_json files = nlohmann::ordered_json::object();
    for (const FileRecord& f : files_) {
        const std::string name = std::filesystem::path(f.path).filename().string();
        files[name] = {{"bytes", sizeOnDisk(f.path)}, {"writeMs", round3(f.ms)}};
    }
    setInfo("files", files);
}

void TimingReport::recordMemory(const ProcessMemory& atStart, std::size_t cells) {
    const ProcessMemory now = ProcessInfo::memory();
    const double n = cells > 0 ? static_cast<double>(cells) : 1.0;
    nlohmann::ordered_json m;
    m["method"] = now.method;
    if (now.available) {
        m["startRssBytes"] = atStart.currentRss;
        m["endRssBytes"] = now.currentRss;
        m["peakRssBytes"] = now.peakRss;
        if (now.peakPrivate > 0) {
            m["peakPrivateBytes"] = now.peakPrivate;
        }
    }
    // Model teoretyczny: duże tablice × sizeof (MemoryModel), w tym bajty na komórkę.
    nlohmann::ordered_json model;
    model["peakBytes"] = memory_.peak();
    model["peakBytesPerCell"] = round3(static_cast<double>(memory_.peak()) / n);
    // Puste tablice (np. caAux w trybie classic) pomijamy — nie wnoszą nic do zapotrzebowania.
    nlohmann::ordered_json atPeak = nlohmann::ordered_json::object();
    for (const MemoryModel::Block& b : memory_.peakBlocks()) {
        if (b.bytes > 0) {
            atPeak[b.name] = b.bytes;
        }
    }
    model["peakBlocks"] = atPeak;
    nlohmann::ordered_json blocks = nlohmann::ordered_json::object();
    for (const MemoryModel::Block& b : memory_.largest()) {
        if (b.bytes > 0) {
            blocks[b.name] = {{"bytes", b.bytes}, {"bytesPerCell", round3(static_cast<double>(b.bytes) / n)}};
        }
    }
    model["blocks"] = blocks;
    m["model"] = model;
    setInfo("memory", m);
}

nlohmann::ordered_json TimingReport::toJson() const {
    nlohmann::ordered_json j;
    j["unit"] = "ms";
    for (const auto& s : sections_) {
        j[s.first] = round3(s.second);
    }
    for (auto it = info_.begin(); it != info_.end(); ++it) {
        j[it.key()] = it.value();
    }
    if (detail_) {
        nlohmann::ordered_json d;
        d["unit"] = "ms";
        for (const auto& x : details_) {
            d[x.first] = round3(x.second);
        }
        j["detail"] = d;
    }
    return j;
}

std::string TimingReport::cpuName() {
#ifdef _WIN32
    char buf[256] = {};
    DWORD size = sizeof(buf);
    if (RegGetValueA(HKEY_LOCAL_MACHINE, "HARDWARE\\DESCRIPTION\\System\\CentralProcessor\\0",
                     "ProcessorNameString", RRF_RT_REG_SZ, nullptr, buf, &size) == ERROR_SUCCESS) {
        std::string name(buf);
        while (!name.empty() && name.back() == ' ') {
            name.pop_back();
        }
        return name;
    }
#else
    std::ifstream in("/proc/cpuinfo");
    std::string line;
    while (std::getline(in, line)) {
        if (line.rfind("model name", 0) == 0) {
            const auto colon = line.find(':');
            if (colon != std::string::npos) {
                return line.substr(colon + 2);
            }
        }
    }
#endif
    return "nieznany";
}

std::string TimingReport::compilerName() {
#if defined(_MSC_VER) && !defined(__clang__)
    return "MSVC " + std::to_string(_MSC_VER / 100) + "." + std::to_string(_MSC_VER % 100);
#elif defined(__clang__)
    return std::string("Clang ") + __clang_version__;
#elif defined(__GNUC__)
    return std::string("GCC ") + __VERSION__;
#else
    return "nieznany";
#endif
}

std::string TimingReport::buildType() {
#ifdef NDEBUG
    return "Release";
#else
    return "Debug";
#endif
}

}  // namespace volcano
