#pragma once
// Opcje silnika dla GUI (etap 4), które niczego nie symulują:
//   engine --print-defaults  — pełny domyślny config JSON; GUI buduje z niego formularz,
//                              więc formularz zawsze zgadza się z silnikiem (te same klucze i wartości);
//   engine --validate ...    — sama walidacja configu (+ --set, --mc-from) z komunikatami po polsku
//                              jako JSON: {"ok": true|false, "errors": [...], "warnings": [...]}.
// Walidacja używa dokładnie tego samego kodu co uruchomienie (Config::load), a dodatkowo sprawdza
// to, co przy uruchomieniu wyszłoby dopiero w trakcie: plik mapy wysokości i folder --mc-from.

#include <ostream>
#include <string>
#include <vector>

#include "app/Cli.hpp"
#include "json.hpp"

namespace volcano {

// Wynik walidacji configu.
struct ValidationResult {
    bool ok = true;
    std::vector<std::string> errors;    // błędy — symulacja by się nie uruchomiła
    std::vector<std::string> warnings;  // ostrzeżenia — symulacja ruszy, ale coś jest ignorowane

    // {"ok": ..., "errors": [...], "warnings": [...]}
    nlohmann::ordered_json toJson() const;
};

class ConfigCheck {
public:
    // Domyślny config (Config::defaultsJson) jako sformatowany tekst JSON z końcem linii.
    static std::string defaultsText();

    // Waliduje config z opt.configPath + opt.overrides (i opt.mcFrom, jeśli podano).
    // Nie rzuca wyjątków konfiguracji — wszystkie problemy trafiają do wyniku.
    static ValidationResult validate(const CliOptions& opt);

    // engine --validate: wypisuje wynik jako JSON na out; kod wyjścia 0 (ok) lub 1 (błąd configu,
    // jak przy zwykłym uruchomieniu).
    static int runFromCli(const CliOptions& opt, std::ostream& out);
};

}  // namespace volcano
