#pragma once
// Odczyt wyników zapisanych przez ResultWriter (txt i bin).
// Potrzebny do testów (zapis -> odczyt), do uruchamiania MC na wyniku CA z pliku
// (engine --mc-from) oraz w GUI (choć GUI czyta pliki bezpośrednio przez numpy).

#include <cstdint>
#include <string>

#include "core/Types.hpp"

namespace volcano {

// Skąd pochodzi wczytana mikrostruktura i które pola zawierał plik.
// MC potrzebuje solidStep i arrivalStep do mobilności ze stygnięcia.
struct ResultSource {
    std::string path;              // wczytany plik
    std::string format;            // "bin" albo "txt"
    std::uint32_t version = 0;     // wersja formatu bin (0 dla txt)
    bool hasSolidStep = false;     // bin v1 i v2
    bool hasArrivalStep = false;   // tylko bin v2
};

class ResultReader {
public:
    // Odczyt ca_result.txt. Pola solidStep i arrivalStep nie występują w txt — ustawiane na 0.
    static Microstructure readTxt(const std::string& path);

    // Odczyt ca_result.bin w wersji 1 lub 2 (sprawdza magic, wersję i rozmiar pliku).
    // W wersji 1 nie ma arrivalStep — przyjmowane 0. version (opcjonalnie) = wersja pliku.
    static Microstructure readBin(const std::string& path, std::uint32_t* version = nullptr);

    // Odczyt z folderu wyników: ca_result.bin, a jeśli go nie ma — ca_result.txt.
    // source (opcjonalnie) — informacja, co wczytano.
    static Microstructure readFolder(const std::string& folder, ResultSource* source = nullptr);

    // Odczyt mapy kryształów MC: mc_result.bin ("VMC1") albo mc_result.txt.
    static CrystalMap readCrystalBin(const std::string& path);
    static CrystalMap readCrystalTxt(const std::string& path);
    static CrystalMap readCrystalFolder(const std::string& folder);
};

}  // namespace volcano
