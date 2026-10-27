#include "app/ConfigCheck.hpp"

#include <exception>
#include <filesystem>

#include "app/Simulation.hpp"
#include "io/Config.hpp"

namespace volcano {

namespace fs = std::filesystem;

namespace {

// Sprawdzenia dla --mc-from, które przy uruchomieniu wyszłyby dopiero po starcie
// (Simulation::runMcFrom, ResultReader::readFolder).
void checkMcFrom(Config cfg, const std::string& folder, ValidationResult& r) {
    if (cfg.mc.domain != McDomain::Basalt) {
        r.errors.push_back(std::string("--mc-from krystalizuje wynik CA z pliku, więc wymaga mc.domain = \"basalt\" "
                                       "(podano \"") + nameOf(cfg.mc.domain) + "\")");
    }
    if (!cfg.mc.enabled) {
        r.warnings.push_back("mc.enabled = false, a w trybie --mc-from Monte Carlo jest uruchamiane zawsze");
    }
    const fs::path dir(folder);
    if (!fs::is_directory(dir)) {
        r.errors.push_back("Folder wyniku CA (--mc-from) nie istnieje: " + folder);
    } else if (!fs::exists(dir / "ca_result.bin") && !fs::exists(dir / "ca_result.txt")) {
        r.errors.push_back("W folderze " + folder + " nie ma ca_result.bin ani ca_result.txt");
    }
}

}  // namespace

nlohmann::ordered_json ValidationResult::toJson() const {
    nlohmann::ordered_json j;
    j["ok"] = ok;
    j["errors"] = errors;
    j["warnings"] = warnings;
    return j;
}

std::string ConfigCheck::defaultsText() { return Config::defaultsJson().dump(2) + '\n'; }

ValidationResult ConfigCheck::validate(const CliOptions& opt) {
    ValidationResult r;
    try {
        const Config cfg = Config::load(opt.configPath, opt.overrides);
        r.warnings = cfg.warnings;
        if (!opt.mcFrom.empty()) {
            checkMcFrom(cfg, opt.mcFrom, r);
        } else if (!cfg.mc.fullOnly() && cfg.ca.mode == CaMode::Lava && cfg.terrain.type == TerrainType::File) {
            // Mapa wysokości jest czytana dopiero przy starcie symulacji — tu sprawdzamy plik i jego format
            // (ten sam kod, ta sama ścieżka względem configu). Brak pliku / zły format -> ConfigError.
            (void)Simulation::buildTerrain(cfg);
        }
    } catch (const std::exception& e) {
        // ConfigError (zła wartość, nieznany klucz, składnia JSON, brak pliku) albo inny błąd odczytu.
        r.errors.push_back(e.what());
    }
    r.ok = r.errors.empty();
    return r;
}

int ConfigCheck::runFromCli(const CliOptions& opt, std::ostream& out) {
    const ValidationResult r = validate(opt);
    // replace: ścieżka z argv w stronie kodowej systemu (nie UTF-8) nie może przerwać wypisania wyniku.
    out << r.toJson().dump(2, ' ', false, nlohmann::json::error_handler_t::replace) << '\n';
    return r.ok ? 0 : 1;
}

}  // namespace volcano
