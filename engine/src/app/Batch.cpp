#include "app/Batch.hpp"

#include <algorithm>
#include <cctype>
#include <cstdio>
#include <ctime>
#include <fstream>
#include <iostream>
#include <sstream>
#include <system_error>

#include "core/Timer.hpp"
#include "io/Config.hpp"
#include "json.hpp"

namespace volcano {

namespace fs = std::filesystem;

namespace {

using ojson = nlohmann::ordered_json;

// Sekcje czasu z times.json w kolejności kolumn batch_summary.csv (te same nazwy co w times.json).
const char* const kSections[] = {"readConfig", "readInput", "allocate", "terrain", "vents", "caSim", "snapshots",
                                 "save", "mcInit", "mcSim", "mcStats", "mcSave", "total"};

// Bieżąca data i czas „RRRR-MM-DD GG:MM:SS” (nagłówek engine.log).
std::string nowText() {
    char buf[32];
    const std::time_t now = std::time(nullptr);
    std::tm local{};
#ifdef _WIN32
    localtime_s(&local, &now);
#else
    localtime_r(&now, &local);
#endif
    std::strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", &local);
    return buf;
}

// Liczba z podaną liczbą miejsc po przecinku.
std::string fixed(double v, int decimals) {
    char buf[64];
    std::snprintf(buf, sizeof(buf), "%.*f", decimals, v);
    return buf;
}

// JSON z pliku albo null, gdy pliku nie ma lub jest uszkodzony.
ojson readJsonFile(const fs::path& p) {
    std::ifstream in(p);
    if (!in) {
        return nullptr;
    }
    try {
        return ojson::parse(in);
    } catch (const std::exception&) {
        return nullptr;
    }
}

// Wartość spod klucza jako tekst do CSV (liczba bez zmian, tekst bez cudzysłowów, brak = "").
std::string field(const ojson& j, const std::string& key) {
    if (!j.is_object() || !j.contains(key)) {
        return "";
    }
    const ojson& v = j[key];
    if (v.is_string()) {
        return v.get<std::string>();
    }
    if (v.is_number() || v.is_boolean()) {
        return v.dump();
    }
    return "";
}

// Rozmiar pliku wynikowego z sekcji files w times.json [B] ("" — pliku nie było).
std::string fileBytes(const ojson& times, const char* name) {
    if (!times.is_object() || !times.contains("files") || !times["files"].contains(name)) {
        return "";
    }
    return field(times["files"][name], "bytes");
}

// Pole CSV: w cudzysłowie, gdy zawiera przecinek, cudzysłów albo znak nowej linii.
std::string csvCell(const std::string& s) {
    if (s.find_first_of(",\"\n\r") == std::string::npos) {
        return s;
    }
    std::string out = "\"";
    for (char c : s) {
        if (c == '"') {
            out += '"';
        }
        out += c;
    }
    return out + '"';
}

// Ostatnia linia zaczynająca się od „Błąd” w logu silnika — opis błędu do podsumowania.
std::string lastErrorLine(const fs::path& log) {
    std::ifstream in(log);
    std::string line;
    std::string last;
    while (std::getline(in, line)) {
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        if (line.rfind("Błąd", 0) == 0) {
            last = line;
        }
    }
    return last;
}

// Ścieżka do wyświetlenia: ukośniki „/” (bez mieszania z „\”), w cudzysłowie, gdy ma spację.
std::string shown(const fs::path& p) {
    const std::string s = p.generic_u8string();
    return s.find(' ') == std::string::npos ? s : '"' + s + '"';
}

// Liczebnik z odmianą: plural(2, "przebieg", "przebiegi", "przebiegów") -> "2 przebiegi".
std::string plural(std::size_t n, const char* one, const char* few, const char* many) {
    const std::size_t d = n % 10;
    const std::size_t dd = n % 100;
    const char* word = n == 1 ? one : (d >= 2 && d <= 4 && (dd < 12 || dd > 14)) ? few : many;
    return std::to_string(n) + ' ' + word;
}

// Liczba z pola JSON (0, gdy brak) — do tabeli w konsoli.
double number(const ojson& j, const char* key) {
    return (j.is_object() && j.contains(key) && j[key].is_number()) ? j[key].get<double>() : 0.0;
}

// Tekst wyrównany do szerokości (liczy znaki UTF-8, nie bajty — nazwy configów bywają z polskimi literami).
std::string pad(const std::string& s, std::size_t width, bool right = false) {
    std::size_t chars = 0;
    for (unsigned char c : s) {
        chars += ((c & 0xC0) != 0x80) ? 1 : 0;
    }
    const std::string fill(chars < width ? width - chars : 0, ' ');
    return right ? fill + s : s + fill;
}

}  // namespace

std::vector<BatchItem> BatchRunner::collect(const fs::path& folder, const fs::path& out) {
    std::vector<BatchItem> items;
    for (const fs::directory_entry& e : fs::directory_iterator(folder)) {
        if (!e.is_regular_file()) {
            continue;
        }
        const fs::path& p = e.path();
        std::string ext = p.extension().u8string();
        std::transform(ext.begin(), ext.end(), ext.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
        const std::string stem = p.stem().u8string();
        // series.json — opis serii z generatora (nie config); _*.json — pliki pomocnicze użytkownika.
        if (ext != ".json" || stem.empty() || stem[0] == '_' || p.filename() == "series.json") {
            continue;
        }
        items.push_back(BatchItem{stem, p, out / p.stem()});
    }
    std::sort(items.begin(), items.end(), [](const BatchItem& a, const BatchItem& b) { return a.name < b.name; });
    return items;
}

BatchRunner::Runner BatchRunner::processRunner(const fs::path& exe, const std::vector<std::string>& extraArgs) {
    return [exe, extraArgs](const BatchItem& item, const fs::path& log) {
        std::vector<ChildArg> args{"--config", item.config, "--out", item.outDir};
        for (const std::string& a : extraArgs) {
            args.emplace_back(a);
        }
        {
            std::ofstream head(log, std::ios::app);
            head << "# polecenie: " << shown(exe) << " --config " << shown(item.config) << " --out "
                 << shown(item.outDir);
            for (const std::string& a : extraArgs) {
                head << ' ' << a;
            }
            head << '\n';
        }
        return ChildProcess::run(exe, args, log);
    };
}

std::vector<BatchOutcome> BatchRunner::run(const std::vector<BatchItem>& items, const Runner& runner,
                                           const fs::path& summaryCsv, std::ostream& out, ProgressReporter* progress) {
    std::vector<BatchOutcome> outcomes;
    const long long n = static_cast<long long>(items.size());
    if (progress != nullptr) {
        progress->report("batch", 0, n, true);
    }
    for (std::size_t i = 0; i < items.size(); ++i) {
        const BatchItem& it = items[i];
        std::error_code ec;
        fs::create_directories(it.outDir, ec);
        const fs::path log = it.outDir / "engine.log";
        {
            std::ofstream head(log, std::ios::trunc);
            head << "# " << nowText() << " engine --batch: " << it.name << '\n';
        }

        // Sam przebieg: osobny proces silnika (albo funkcja z testu).
        const Timer t;
        const ChildResult r = runner(it, log);
        BatchOutcome o;
        o.item = it;
        o.wallMs = t.elapsedMs();
        o.exitCode = r.exitCode;
        if (!r.started || !r.error.empty()) {
            o.error = r.error.empty() ? "przebieg nie wystartował" : r.error;
        } else if (r.exitCode != 0) {
            o.error = lastErrorLine(log);
            if (o.error.empty()) {
                o.error = "silnik zakończył się kodem " + std::to_string(r.exitCode);
            }
        }
        {
            std::ofstream tail(log, std::ios::app);
            tail << "# koniec: kod wyjścia " << o.exitCode << ", czas " << fixed(o.wallMs / 1000.0, 2) << " s\n";
        }
        outcomes.push_back(o);
        writeSummary(summaryCsv, outcomes);  // po każdym przebiegu — przerwana seria też ma podsumowanie

        std::ostringstream line;
        line << '[' << pad(std::to_string(i + 1), std::to_string(n).size(), true) << '/' << n << "] "
             << pad(it.name, 28) << ' ';
        if (o.ok()) {
            const ojson times = readJsonFile(it.outDir / "times.json");
            line << "ok    ";
            for (const char* key : {"caSim", "mcSim"}) {
                if (times.is_object() && times.contains(key)) {
                    line << key << ' ' << fixed(number(times, key), 1) << " ms  ";
                }
            }
            line << "(" << fixed(o.wallMs / 1000.0, 2) << " s)";
        } else {
            line << "BŁĄD  " << o.error;
        }
        out << line.str() << '\n' << std::flush;
        if (progress != nullptr) {
            progress->report("batch", static_cast<long long>(i + 1), n, true);
        }
    }
    return outcomes;
}

std::vector<std::string> BatchRunner::summaryColumns() {
    std::vector<std::string> cols = {"name", "status", "exitCode", "error", "mode", "nx", "ny", "nz", "cells",
                                     "grid", "neighborhood", "boundary", "seeds", "steps", "stopReason", "mcs", "Q",
                                     "domainCells"};
    for (const char* s : kSections) {
        cols.emplace_back(s);
    }
    for (const char* c : {"wallMs", "peakRssBytes", "peakPrivateBytes", "modelPeakBytes", "caResultTxtBytes",
                          "caResultBinBytes", "mcResultTxtBytes", "mcResultBinBytes", "outputBytes", "compiler", "build",
                          "config", "outDir"}) {
        cols.emplace_back(c);
    }
    return cols;
}

std::vector<std::string> BatchRunner::summaryRow(const BatchOutcome& o) {
    // Pliki wyników czytamy tylko po udanym przebiegu — po błędzie w folderze mogły zostać
    // pliki z wcześniejszego uruchomienia, które nie opisują tego przebiegu.
    const ojson times = o.ok() ? readJsonFile(o.item.outDir / "times.json") : ojson();
    const ojson cfg = o.ok() ? readJsonFile(o.item.outDir / "config_used.json") : ojson();
    const std::string mode = field(times, "mode");

    std::vector<std::string> row = {o.item.name, o.ok() ? "ok" : "error", std::to_string(o.exitCode), o.error, mode};
    for (std::size_t a = 0; a < 3; ++a) {
        const bool has = times.is_object() && times.contains("space") && times["space"].is_array() &&
                         times["space"].size() == 3;
        row.push_back(has ? times["space"][a].dump() : "");
    }
    row.push_back(field(times, "cells"));
    row.push_back(field(times, "grid"));
    row.push_back(field(times, "neighborhood"));
    row.push_back(field(times, "boundary"));
    // Liczba zarodków / kraterów ma sens tylko wtedy, gdy liczył się automat.
    const bool caRan = mode == "lava" || mode == "classic";
    row.push_back(caRan && cfg.is_object() && cfg.contains("vents") ? field(cfg["vents"], "count") : "");
    row.push_back(field(times, "steps"));
    row.push_back(field(times, "stopReason"));
    row.push_back(field(times, "mcs"));
    row.push_back(field(times, "Q"));
    row.push_back(field(times, "domainCells"));
    for (const char* s : kSections) {
        row.push_back(field(times, s));
    }
    row.push_back(fixed(o.wallMs, 3));
    const ojson mem = (times.is_object() && times.contains("memory")) ? times["memory"] : ojson();
    row.push_back(field(mem, "peakRssBytes"));
    row.push_back(field(mem, "peakPrivateBytes"));
    row.push_back(mem.is_object() && mem.contains("model") ? field(mem["model"], "peakBytes") : "");
    for (const char* f : {"ca_result.txt", "ca_result.bin", "mc_result.txt", "mc_result.bin"}) {
        row.push_back(fileBytes(times, f));
    }
    std::string total;
    if (times.is_object() && times.contains("files") && times["files"].is_object()) {
        unsigned long long sum = 0;
        const ojson& files = times["files"];
        for (auto it = files.begin(); it != files.end(); ++it) {
            const ojson& f = it.value();
            sum += f.contains("bytes") && f["bytes"].is_number_unsigned() ? f["bytes"].get<unsigned long long>() : 0ULL;
        }
        total = std::to_string(sum);
    }
    row.push_back(total);
    row.push_back(field(times, "compiler"));
    row.push_back(field(times, "build"));
    row.push_back(o.item.config.generic_u8string());
    row.push_back(o.item.outDir.generic_u8string());
    return row;
}

void BatchRunner::writeSummary(const fs::path& csv, const std::vector<BatchOutcome>& outcomes) {
    std::ofstream f(csv, std::ios::trunc);
    if (!f) {
        throw std::runtime_error("Nie można zapisać podsumowania serii: " + csv.u8string());
    }
    const std::vector<std::string> cols = summaryColumns();
    for (std::size_t i = 0; i < cols.size(); ++i) {
        f << (i ? "," : "") << cols[i];
    }
    f << '\n';
    for (const BatchOutcome& o : outcomes) {
        const std::vector<std::string> row = summaryRow(o);
        for (std::size_t i = 0; i < row.size(); ++i) {
            f << (i ? "," : "") << csvCell(row[i]);
        }
        f << '\n';
    }
}

std::string BatchRunner::describe(const std::vector<BatchOutcome>& outcomes) {
    std::size_t width = 6;
    for (const BatchOutcome& o : outcomes) {
        width = std::max(width, o.item.name.size());
    }
    std::ostringstream os;
    os << pad("config", width) << "  status  " << pad("kroki", 7, true) << pad("MCS", 7, true)
       << pad("caSim [ms]", 13, true) << pad("mcSim [ms]", 13, true) << pad("total [ms]", 13, true)
       << pad("pamięć [MiB]", 14, true) << '\n';
    std::size_t okCount = 0;
    double wall = 0.0;
    for (const BatchOutcome& o : outcomes) {
        wall += o.wallMs;
        if (!o.ok()) {
            os << pad(o.item.name, width) << "  BŁĄD\n";
            continue;
        }
        ++okCount;
        const ojson t = readJsonFile(o.item.outDir / "times.json");
        auto cell = [&t](const char* key, int decimals) {
            return (t.is_object() && t.contains(key)) ? fixed(number(t, key), decimals) : std::string("—");
        };
        double peak = 0.0;
        if (t.is_object() && t.contains("memory")) {
            peak = number(t["memory"], "peakRssBytes") / (1024.0 * 1024.0);
        }
        os << pad(o.item.name, width) << "  ok      " << pad(cell("steps", 0), 7, true) << pad(cell("mcs", 0), 7, true)
           << pad(cell("caSim", 1), 13, true) << pad(cell("mcSim", 1), 13, true) << pad(cell("total", 1), 13, true)
           << pad(peak > 0.0 ? fixed(peak, 1) : "—", 14, true) << '\n';
    }
    os << "Razem: " << plural(outcomes.size(), "przebieg", "przebiegi", "przebiegów") << ": " << okCount << " ok, "
       << (outcomes.size() - okCount) << " z błędem; czas serii " << fixed(wall / 1000.0, 2) << " s\n";
    for (const BatchOutcome& o : outcomes) {
        if (!o.ok()) {
            os << "  " << o.item.name << ": " << o.error << '\n';
        }
    }
    return os.str();
}

int BatchRunner::runFromCli(const CliOptions& opt) {
    fs::path folder(opt.batchDir);
    if (!fs::is_directory(folder)) {
        throw CliError("--batch: folder z configami nie istnieje: " + opt.batchDir);
    }
    if (folder.filename().empty()) {
        folder = folder.parent_path();  // "configs/seria/" -> nazwa folderu "seria"
    }
    const fs::path out = opt.outDir.empty() ? fs::path("results") / folder.filename() : fs::path(opt.outDir);
    const std::vector<BatchItem> items = collect(folder, out);
    if (items.empty()) {
        throw ConfigError("W folderze " + opt.batchDir + " nie ma plików konfiguracyjnych *.json "
                          "(series.json i pliki _*.json są pomijane)");
    }
    const fs::path exe = ChildProcess::selfPath();
    if (exe.empty()) {
        throw std::runtime_error("nie można ustalić ścieżki programu engine (potrzebna do uruchomienia przebiegów)");
    }
    fs::create_directories(out);

    // Opcje wspólne dla wszystkich przebiegów: --set (w tym --grid) i --timing-detail.
    std::vector<std::string> extra;
    for (const std::string& o : opt.overrides) {
        extra.push_back("--set");
        extra.push_back(o);
    }
    if (opt.timingDetail) {
        extra.push_back("--timing-detail");
    }
    ProgressReporter progress = opt.progress ? ProgressReporter(std::cout) : ProgressReporter();
    const fs::path summary = out / "batch_summary.csv";

    std::cout << "=== Seria (--batch): " << plural(items.size(), "config", "configi", "configów") << " z "
              << shown(folder) << " -> " << shown(out) << " ===\n"
              << std::flush;
    const std::vector<BatchOutcome> outcomes = run(items, processRunner(exe, extra), summary, std::cout, &progress);
    std::cout << '\n' << describe(outcomes) << "Podsumowanie   " << shown(summary) << '\n';
    const bool allOk = std::all_of(outcomes.begin(), outcomes.end(), [](const BatchOutcome& o) { return o.ok(); });
    return allOk ? 0 : 5;
}

}  // namespace volcano
