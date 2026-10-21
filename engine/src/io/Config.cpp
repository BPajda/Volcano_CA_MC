#include "io/Config.hpp"

#include <cmath>
#include <fstream>
#include <initializer_list>
#include <limits>
#include <sstream>
#include <utility>

namespace volcano {

namespace {

using ojson = nlohmann::ordered_json;

// Cudzysłowy wokół nazwy parametru w komunikatach.
std::string q(const std::string& path) { return "„" + path + "”"; }

// Dzieli ścieżkę "a.b.c" na segmenty.
std::vector<std::string> splitPath(const std::string& path) {
    std::vector<std::string> parts;
    std::stringstream ss(path);
    std::string part;
    while (std::getline(ss, part, '.')) {
        parts.push_back(part);
    }
    return parts;
}

// Zwraca wartość pod ścieżką z kropkami (po scaleniu z domyślnymi zawsze istnieje).
const ojson& field(const ojson& j, const std::string& path) {
    const ojson* cur = &j;
    for (const std::string& part : splitPath(path)) {
        if (!cur->is_object() || !cur->contains(part)) {
            throw ConfigError("Brak parametru " + q(path));
        }
        cur = &(*cur)[part];
    }
    return *cur;
}

// Liczba całkowita z zakresu [lo, hi].
long long getInteger(const ojson& j, const std::string& path, long long lo, long long hi) {
    const ojson& v = field(j, path);
    if (!v.is_number_integer() ||
        (v.is_number_unsigned() && v.get<std::uint64_t>() > static_cast<std::uint64_t>(hi))) {
        if (v.is_number_unsigned()) {
            throw ConfigError("Parametr " + q(path) + " jest za duży (maks. " + std::to_string(hi) +
                              "), podano: " + v.dump());
        }
        throw ConfigError("Parametr " + q(path) + " musi być liczbą całkowitą, podano: " + v.dump());
    }
    const long long x = v.get<long long>();
    if (x < lo || x > hi) {
        throw ConfigError("Parametr " + q(path) + " musi być z zakresu " + std::to_string(lo) + ".." +
                          std::to_string(hi) + ", podano: " + std::to_string(x));
    }
    return x;
}

int getInt(const ojson& j, const std::string& path, int lo, int hi) {
    return static_cast<int>(getInteger(j, path, lo, hi));
}

// Liczba rzeczywista z zakresu [lo, hi].
double getNumber(const ojson& j, const std::string& path, double lo, double hi) {
    const ojson& v = field(j, path);
    if (!v.is_number()) {
        throw ConfigError("Parametr " + q(path) + " musi być liczbą, podano: " + v.dump());
    }
    const double x = v.get<double>();
    if (!std::isfinite(x) || x < lo || x > hi) {
        std::ostringstream os;
        os << "Parametr " << q(path) << " musi być z zakresu " << lo << ".." << hi << ", podano: " << x;
        throw ConfigError(os.str());
    }
    return x;
}

bool getBool(const ojson& j, const std::string& path) {
    const ojson& v = field(j, path);
    if (!v.is_boolean()) {
        throw ConfigError("Parametr " + q(path) + " musi mieć wartość true lub false, podano: " + v.dump());
    }
    return v.get<bool>();
}

// Wartość wyliczeniowa z listy dozwolonych nazw.
template <class E>
E getEnum(const ojson& j, const std::string& path,
          std::initializer_list<std::pair<const char*, E>> options) {
    const ojson& v = field(j, path);
    std::string allowed;
    for (const auto& opt : options) {
        allowed += (allowed.empty() ? "" : ", ") + std::string(opt.first);
    }
    if (v.is_string()) {
        const std::string s = v.get<std::string>();
        for (const auto& opt : options) {
            if (s == opt.first) {
                return opt.second;
            }
        }
    }
    throw ConfigError("Parametr " + q(path) + " ma nieprawidłową wartość " + v.dump() +
                      "; dozwolone: " + allowed);
}

// Lista kolumn [[x, y], ...] (vents.positions): każdy element to para liczb całkowitych w zakresie
// siatki d, bez powtórzeń. Kolejność zostaje (wyznacza flowId kraterów).
std::vector<std::pair<int, int>> getColumns(const ojson& j, const std::string& path, const Dims& d) {
    const ojson& list = field(j, path);
    if (!list.is_array()) {
        throw ConfigError("Parametr " + q(path) + " musi być listą par [x, y], np. [[80, 75], [82, 70]], podano: " +
                          list.dump());
    }
    std::vector<std::pair<int, int>> out;
    for (std::size_t i = 0; i < list.size(); ++i) {
        const ojson& p = list[i];
        const std::string where = path + "[" + std::to_string(i) + "]";
        const auto isInt = [](const ojson& v) {
            return v.is_number_integer() &&
                   (!v.is_number_unsigned() || v.get<std::uint64_t>() <= static_cast<std::uint64_t>(100000));
        };
        if (!p.is_array() || p.size() != 2 || !isInt(p[0]) || !isInt(p[1])) {
            throw ConfigError("Parametr " + q(where) + " musi być parą liczb całkowitych [x, y], podano: " + p.dump());
        }
        const long long x = p[0].get<long long>();
        const long long y = p[1].get<long long>();
        if (x < 0 || x >= d.nx || y < 0 || y >= d.ny) {
            throw ConfigError("Parametr " + q(where) + " = " + p.dump() + " leży poza siatką: x musi być z zakresu 0.." +
                              std::to_string(d.nx - 1) + ", y z zakresu 0.." + std::to_string(d.ny - 1) +
                              " (space.nx = " + std::to_string(d.nx) + ", space.ny = " + std::to_string(d.ny) + ")");
        }
        int xi = static_cast<int>(x);
        int yi = static_cast<int>(y);
        for (const auto& c : out) {  // lista jest krótka — wystarczy porównanie z poprzednimi
            if (c.first == xi && c.second == yi) {
                throw ConfigError("Parametr " + q(where) + " = " + p.dump() +
                                  " powtarza kolumnę z wcześniejszego elementu listy — w jednej kolumnie może być "
                                  "najwyżej jeden krater");
            }
        }
        out.emplace_back(xi, yi);
    }
    return out;
}

}  // namespace

// ---------------------------------------------------------------------------

ojson Config::defaultsJson() {
    // Wartości domyślne zgodne z opisem w docs/uruchamianie.md. Kolejność kluczy zostaje
    // zachowana w config_used.json (ordered_json).
    return ojson::parse(R"({
      "space":        { "nx": 200, "ny": 1, "nz": 100 },
      "grid":         "vector",
      "boundary":     "absorbing",
      "neighborhood": "moore",
      "rngSeed":      42,
      "terrain": { "type": "cone", "peakHeight": 70, "baseRadius": 90,
                   "craterRadius": 6, "craterDepth": 4, "noise": 0.05, "file": null },
      "vents":   { "count": 1, "placement": "crater", "positions": [], "eruptionSteps": 300,
                   "eruptTemp": 1200 },
      "ca":      { "mode": "lava", "maxSteps": 5000, "coolingAmbient": 0.3,
                   "coolingLateral": 1.5, "coolingFall": 0.1, "solidusTemp": 800,
                   "ponding": true, "sweep": "front" },
      "mc":      { "enabled": false, "domain": "basalt", "Q": 50, "mcs": 100, "J": 1.0, "kT": 0.0,
                   "mobilityFromCooling": true, "mobilityMin": 0.05, "statsEvery": 10,
                   "snapshotsEvery": 0, "update": "random" },
      "output":  { "format": "txt", "snapshotsEvery": 0 },
      "parallel": { "threads": 1, "schedule": "static", "chunk": 0, "affinity": "none", "priority": "normal" },
      "mpi":     { "exchange": "always", "pack": "manual", "bcast": "json", "io": "gather" }
    })");
}

void Config::merge(ojson& base, const ojson& patch, const std::string& prefix) {
    for (auto it = patch.begin(); it != patch.end(); ++it) {
        const std::string& key = it.key();
        if (!key.empty() && key[0] == '_') {
            continue;  // komentarz w configu
        }
        const std::string path = prefix.empty() ? key : prefix + "." + key;
        if (!base.contains(key)) {
            std::string allowed;
            for (auto b = base.begin(); b != base.end(); ++b) {
                allowed += (allowed.empty() ? "" : ", ") + b.key();
            }
            throw ConfigError("Nieznany parametr " + q(path) + "; dozwolone w tej sekcji: " + allowed);
        }
        ojson& target = base[key];
        if (target.is_object()) {
            if (!it.value().is_object()) {
                throw ConfigError("Parametr " + q(path) + " jest sekcją — oczekiwano obiektu { ... }, podano: " +
                                  it.value().dump());
            }
            merge(target, it.value(), path);
        } else {
            target = it.value();
        }
    }
}

void Config::applyOverride(ojson& j, const std::string& keyValue) {
    const std::size_t eq = keyValue.find('=');
    if (eq == std::string::npos || eq == 0) {
        throw ConfigError("Nadpisanie musi mieć postać klucz=wartość, podano: " + keyValue);
    }
    const std::string key = keyValue.substr(0, eq);
    const std::string text = keyValue.substr(eq + 1);

    // Wartość jako JSON (liczba, true/false, null, obiekt); inaczej — zwykły tekst.
    ojson value;
    try {
        value = ojson::parse(text);
    } catch (const nlohmann::json::parse_error&) {
        value = text;
    }

    // Budujemy łatkę {"a": {"b": wartość}} i scalamy jak plik — ta sama walidacja kluczy.
    const std::vector<std::string> parts = splitPath(key);
    for (const std::string& p : parts) {
        if (p.empty()) {
            throw ConfigError("Nieprawidłowa ścieżka parametru w nadpisaniu: " + key);
        }
    }
    ojson patch = std::move(value);
    for (auto it = parts.rbegin(); it != parts.rend(); ++it) {
        ojson obj = ojson::object();
        obj[*it] = std::move(patch);
        patch = std::move(obj);
    }
    merge(j, patch, "");
}

Config Config::load(const std::string& path, const std::vector<std::string>& overrides) {
    ojson j = defaultsJson();
    bool spaceGiven = false;  // --mc-from ostrzega o konflikcie wymiarów tylko, gdy podał je użytkownik
    if (!path.empty()) {
        std::ifstream in(path);
        if (!in) {
            throw ConfigError("Nie można otworzyć pliku konfiguracyjnego: " + path);
        }
        ojson file;
        try {
            // ignore_comments = true: pozwalamy na komentarze // i /* */ w pliku.
            file = ojson::parse(in, nullptr, true, true);
        } catch (const nlohmann::json::parse_error& e) {
            throw ConfigError("Błąd składni JSON w pliku " + path + ": " + e.what());
        }
        if (!file.is_object()) {
            throw ConfigError("Plik konfiguracyjny " + path + " musi zawierać obiekt JSON { ... }");
        }
        merge(j, file, "");
        spaceGiven = file.contains("space");
    }
    for (const std::string& o : overrides) {
        applyOverride(j, o);
        spaceGiven = spaceGiven || o.rfind("space", 0) == 0;
    }
    Config c = fromJson(j);
    c.sourcePath = path;
    c.spaceFromUser = spaceGiven;
    return c;
}

Config Config::fromJson(const ojson& j) {
    Config c;

    // --- przestrzeń ---
    c.space.nx = getInt(j, "space.nx", 1, 100000);
    c.space.ny = getInt(j, "space.ny", 1, 100000);
    c.space.nz = getInt(j, "space.nz", 1, 100000);
    if (c.space.activeAxes() < 2) {
        throw ConfigError("Przestrzeń musi być 2D (dokładnie jeden wymiar równy 1) lub 3D; podano " +
                          std::to_string(c.space.nx) + " x " + std::to_string(c.space.ny) + " x " +
                          std::to_string(c.space.nz));
    }
    if (c.space.cells() > 2000000000ULL) {
        throw ConfigError("Przestrzeń ma za dużo komórek (" + std::to_string(c.space.cells()) +
                          "); maksimum to 2 000 000 000");
    }

    c.grid = getEnum<GridKind>(j, "grid", {{"vector", GridKind::Vector}, {"matrix", GridKind::Matrix}});
    c.boundary = getEnum<BoundaryKind>(
        j, "boundary", {{"absorbing", BoundaryKind::Absorbing}, {"periodic", BoundaryKind::Periodic}});
    c.neighborhood = getEnum<NeighborhoodKind>(j, "neighborhood",
                                               {{"von_neumann", NeighborhoodKind::VonNeumann},
                                                {"moore", NeighborhoodKind::Moore},
                                                {"pentagonal", NeighborhoodKind::Pentagonal},
                                                {"hexagonal", NeighborhoodKind::Hexagonal}});
    c.rngSeed = static_cast<std::uint64_t>(
        getInteger(j, "rngSeed", 0, std::numeric_limits<long long>::max()));

    // --- Monte Carlo (przed automatem: w trybie full CA i teren są pomijane) ---
    c.mc.enabled = getBool(j, "mc.enabled");
    c.mc.domain = getEnum<McDomain>(j, "mc.domain", {{"basalt", McDomain::Basalt}, {"full", McDomain::Full}});
    c.mc.Q = getInt(j, "mc.Q", 2, 1000000000);
    c.mc.mcs = getInt(j, "mc.mcs", 0, 10000000);
    c.mc.J = getNumber(j, "mc.J", 0.0, 1e6);
    if (c.mc.J <= 0.0) {
        throw ConfigError("Parametr „mc.J” (energia granicy ziarna) musi być większy od 0, podano: " +
                          field(j, "mc.J").dump());
    }
    c.mc.kT = getNumber(j, "mc.kT", 0.0, 1e6);
    c.mc.mobilityFromCooling = getBool(j, "mc.mobilityFromCooling");
    c.mc.mobilityMin = getNumber(j, "mc.mobilityMin", 0.0, 1.0);
    c.mc.statsEvery = getInt(j, "mc.statsEvery", 1, 1000000000);
    c.mc.snapshotsEvery = getInt(j, "mc.snapshotsEvery", 0, 1000000000);
    c.mc.checkerboard = getEnum<bool>(j, "mc.update", {{"random", false}, {"checkerboard", true}});
    const bool runsCa = !c.mc.fullOnly();  // czy w ogóle będzie teren i automat

    // --- automat ---
    c.ca.mode = getEnum<CaMode>(j, "ca.mode", {{"lava", CaMode::Lava}, {"classic", CaMode::Classic}});
    // solidStep zapisujemy jako uint16, stąd limit kroków 65535.
    c.ca.maxSteps = getInt(j, "ca.maxSteps", 0, 65535);
    c.ca.coolingAmbient = getNumber(j, "ca.coolingAmbient", 0.0, 1e6);
    c.ca.coolingLateral = getNumber(j, "ca.coolingLateral", 0.0, 1e6);
    c.ca.coolingFall = getNumber(j, "ca.coolingFall", 0.0, 1e6);
    c.ca.solidusTemp = getNumber(j, "ca.solidusTemp", -1e6, 1e6);
    c.ca.ponding = getBool(j, "ca.ponding");
    c.ca.frontSweep = getEnum<bool>(j, "ca.sweep", {{"front", true}, {"full", false}});

    if (runsCa && c.ca.mode == CaMode::Lava && c.space.is2D() && c.space.ny != 1) {
        throw ConfigError("W trybie lava przestrzeń 2D to przekrój pionowy x–z: wymagane ny = 1 "
                          "(podano nx = " + std::to_string(c.space.nx) + ", ny = " +
                          std::to_string(c.space.ny) + ", nz = " + std::to_string(c.space.nz) + ")");
    }
    if (c.neighborhood == NeighborhoodKind::Hexagonal && !c.space.is2D()) {
        throw ConfigError("Sąsiedztwo „hexagonal” jest zdefiniowane tylko w 2D; dla przestrzeni 3D "
                          "wybierz von_neumann, moore lub pentagonal");
    }

    // --- teren ---
    c.terrain.type = getEnum<TerrainType>(j, "terrain.type",
                                          {{"cone", TerrainType::Cone}, {"file", TerrainType::File}});
    c.terrain.peakHeight = getNumber(j, "terrain.peakHeight", 0.0, 1e6);
    c.terrain.baseRadius = getNumber(j, "terrain.baseRadius", 1e-9, 1e6);
    c.terrain.craterRadius = getNumber(j, "terrain.craterRadius", 0.0, 1e6);
    c.terrain.craterDepth = getNumber(j, "terrain.craterDepth", 0.0, 1e6);
    c.terrain.noise = getNumber(j, "terrain.noise", 0.0, 1.0);
    const ojson& file = field(j, "terrain.file");
    if (!file.is_null() && !file.is_string()) {
        throw ConfigError("Parametr „terrain.file” musi być ścieżką (tekst) albo null, podano: " + file.dump());
    }
    c.terrain.file = file.is_string() ? file.get<std::string>() : std::string();
    if (runsCa && c.ca.mode == CaMode::Lava && c.terrain.type == TerrainType::File && c.terrain.file.empty()) {
        throw ConfigError("Dla terrain.type = \"file\" trzeba podać ścieżkę w „terrain.file”");
    }

    // --- kratery / zarodki ---
    c.vents.count = getInt(j, "vents.count", 1, 100000000);
    c.vents.placement = getEnum<VentPlacement>(j, "vents.placement",
                                               {{"crater", VentPlacement::Crater},
                                                {"random", VentPlacement::Random},
                                                {"positions", VentPlacement::Positions}});
    // Kratery w zadanych kolumnach (etap 6). Lista jest sprawdzana zawsze (format, zakres, duplikaty);
    // liczba kraterów = vents.count, żeby pomyłka w jednym z dwóch pól nie przeszła po cichu.
    const std::size_t listed = getColumns(j, "vents.positions", c.space).size();
    const bool lavaCa = runsCa && c.ca.mode == CaMode::Lava;
    if (lavaCa && c.vents.placement == VentPlacement::Positions) {
        if (listed == 0) {
            throw ConfigError("vents.placement = \"positions\" wymaga listy kraterów w „vents.positions”, "
                              "np. [[80, 75]] (w GUI: kliknięcie na mapie wysokości)");
        }
        if (static_cast<std::size_t>(c.vents.count) != listed) {
            throw ConfigError("vents.count (" + std::to_string(c.vents.count) +
                              ") musi być równe liczbie kraterów w „vents.positions” (" + std::to_string(listed) +
                              ") — przy placement = \"positions\" każdy krater ma podane położenie");
        }
    } else if (lavaCa && listed > 0) {
        c.warnings.push_back("vents.positions jest ignorowane, bo vents.placement = \"" +
                             std::string(c.vents.placement == VentPlacement::Crater ? "crater" : "random") +
                             "\" (położenia losowane); kratery w zadanych miejscach: placement = \"positions\"");
    } else if (runsCa && c.ca.mode == CaMode::Classic && c.vents.placement == VentPlacement::Positions) {
        c.warnings.push_back("w trybie classic zarodki są losowane w całej przestrzeni — vents.placement = "
                             "\"positions\" i vents.positions są ignorowane");
    }
    c.vents.eruptionSteps = getInt(j, "vents.eruptionSteps", 0, 65535);
    c.vents.eruptTemp = getNumber(j, "vents.eruptTemp", -1e6, 1e6);
    if (runsCa && c.ca.mode == CaMode::Lava && c.vents.eruptTemp < c.ca.solidusTemp) {
        throw ConfigError("vents.eruptTemp musi być nie mniejsze niż ca.solidusTemp — inaczej lawa "
                          "zastygłaby od razu w kraterze");
    }
    if (runsCa && c.ca.mode == CaMode::Classic && static_cast<std::size_t>(c.vents.count) > c.space.cells()) {
        throw ConfigError("vents.count (" + std::to_string(c.vents.count) +
                          ") nie może przekraczać liczby komórek (" + std::to_string(c.space.cells()) + ")");
    }

    // --- kombinacje parametrów MC ---
    if (c.mc.enabled && c.mc.domain == McDomain::Basalt && c.ca.mode == CaMode::Classic) {
        throw ConfigError("mc.domain = \"basalt\" wymaga ca.mode = \"lava\" (w trybie classic nie ma bazaltu); "
                          "klasyczny rozrost ziaren MC to mc.domain = \"full\"");
    }
    if (c.mc.fullOnly() && c.mc.mobilityFromCooling) {
        c.warnings.push_back("mc.mobilityFromCooling dotyczy tylko mc.domain = \"basalt\" (czas stygnięcia lawy z CA) — "
                             "w trybie full jest ignorowane");
    }

    // --- wyjście ---
    c.output.format = getEnum<OutputFormat>(j, "output.format",
                                            {{"txt", OutputFormat::Txt},
                                             {"bin", OutputFormat::Bin},
                                             {"both", OutputFormat::Both},
                                             {"none", OutputFormat::None}});
    c.output.snapshotsEvery = getInt(j, "output.snapshotsEvery", 0, 65535);

    // --- równoległość (etap 9) ---
    c.parallel.threads = getInt(j, "parallel.threads", 0, 256);
    c.parallel.schedule = getEnum<Schedule>(j, "parallel.schedule",
                                            {{"static", Schedule::Static},
                                             {"dynamic", Schedule::Dynamic},
                                             {"guided", Schedule::Guided}});
    c.parallel.chunk = getInt(j, "parallel.chunk", 0, 1000000);
    c.parallel.affinity =
        getEnum<Affinity>(j, "parallel.affinity", {{"none", Affinity::None}, {"pcores", Affinity::PCores}});
    if (!openmpBuilt() && c.parallel.threads != 1) {
        c.warnings.push_back("program zbudowano bez OpenMP (VOLCANO_OPENMP=OFF) — parallel.threads = " +
                             std::to_string(c.parallel.threads) + " jest ignorowane, obliczenia w jednym wątku");
    }
    if (c.mc.enabled && !c.mc.checkerboard && c.parallel.threads != 1) {
        c.warnings.push_back("mc.update = \"random\" jest z natury sekwencyjne (każda próba widzi wynik poprzednich) — "
                             "pętla MC idzie w jednym wątku; równoległe MC: mc.update = \"checkerboard\"");
    }
    // Etap 10: priorytet procesu i wariant wymiany warstw brzegowych MPI — tylko walidacja; wartości czytają
    // highPriority() i mpiExchangeChanged() z effective (bez nowych pól struktury — układ kodu MSVC, etap 6, punkt 7).
    getEnum<bool>(j, "parallel.priority", {{"normal", false}, {"high", true}});
    getEnum<bool>(j, "mpi.exchange", {{"always", false}, {"changed", true}});
    // Etap 11: warianty typów MPI i zapisu (engine_mpi) — też tylko walidacja, odczyt przez mpiPackDatatype() itd.
    getEnum<bool>(j, "mpi.pack", {{"manual", false}, {"datatype", true}});
    getEnum<bool>(j, "mpi.bcast", {{"json", false}, {"struct", true}});
    getEnum<bool>(j, "mpi.io", {{"gather", false}, {"mpiio", true}});

    c.effective = j;
    return c;
}

std::vector<std::pair<int, int>> Config::ventColumns() const {
    return getColumns(effective, "vents.positions", space);
}

bool Config::highPriority() const {
    return getEnum<bool>(effective, "parallel.priority", {{"normal", false}, {"high", true}});
}

bool Config::mpiExchangeChanged() const {
    return getEnum<bool>(effective, "mpi.exchange", {{"always", false}, {"changed", true}});
}

bool Config::mpiPackDatatype() const {
    return getEnum<bool>(effective, "mpi.pack", {{"manual", false}, {"datatype", true}});
}

bool Config::mpiBcastStruct() const {
    return getEnum<bool>(effective, "mpi.bcast", {{"json", false}, {"struct", true}});
}

bool Config::mpiIoParallel() const {
    return getEnum<bool>(effective, "mpi.io", {{"gather", false}, {"mpiio", true}});
}

ParallelSettings Config::parallelSettings() const {
    ParallelSettings p;
    p.threads = !openmpBuilt() ? 1 : (parallel.threads == 0 ? omp_get_max_threads() : parallel.threads);
    p.schedule = parallel.schedule;
    p.chunk = parallel.chunk;
    return p;
}

const char* nameOf(GridKind g) { return g == GridKind::Matrix ? "matrix" : "vector"; }

const char* nameOf(CaMode m) { return m == CaMode::Classic ? "classic" : "lava"; }

const char* nameOf(McDomain d) { return d == McDomain::Full ? "full" : "basalt"; }

const char* nameOf(OutputFormat f) {
    switch (f) {
        case OutputFormat::Txt: return "txt";
        case OutputFormat::Bin: return "bin";
        case OutputFormat::Both: return "both";
        case OutputFormat::None: return "none";
    }
    return "?";
}

}  // namespace volcano
