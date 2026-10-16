#pragma once
// Uruchomienie programu potomnego i czekanie na jego koniec (engine --batch, etap 5).
// Wyjście programu (stdout i stderr) trafia na koniec pliku logu — tak jak w GUI (engine.log).
// Jedyny kod zależny od systemu jest w ChildProcess.cpp, w #ifdef (jak ProcessInfo):
//   Windows: CreateProcessW (wiersz poleceń w UTF-16, cytowanie wg reguł CommandLineToArgvW),
//            uchwyt logu dziedziczony jako stdout/stderr, WaitForSingleObject + GetExitCodeProcess;
//   Linux:   posix_spawn z przekierowaniem 1 i 2 do logu, waitpid.
// Ścieżki są przekazywane jako std::filesystem::path, więc znaki spoza strony kodowej systemu
// (np. polskie litery w nazwie folderu) nie giną po drodze.

#include <filesystem>
#include <string>
#include <utility>
#include <vector>

namespace volcano {

// Wynik uruchomienia programu potomnego.
struct ChildResult {
    bool started = false;  // false — programu nie dało się uruchomić (error zawiera powód)
    int exitCode = -1;     // kod wyjścia; na Linuksie proces zabity sygnałem s -> 128 + s
    std::string error;     // opis problemu (brak programu, zabity sygnałem) — pusty, gdy wszystko OK
};

// Argument programu potomnego: tekst z linii poleceń (np. "--set") albo ścieżka.
// Tekst pochodzi z argv (strona kodowa systemu) — na Windows jest zamieniany z CP_ACP, ścieżka — z path.
struct ChildArg {
    std::string text;
    std::filesystem::path path;
    bool isPath = false;

    // Konstruktory celowo bez explicit — lista argumentów pisze się wtedy jak {"--config", plik, ...}.
    ChildArg(const char* t) : text(t) {}
    ChildArg(std::string t) : text(std::move(t)) {}
    ChildArg(std::filesystem::path p) : path(std::move(p)), isPath(true) {}
};

class ChildProcess {
public:
    // Pełna ścieżka bieżącego programu (Windows: GetModuleFileNameW, Linux: /proc/self/exe).
    static std::filesystem::path selfPath();

    // Uruchamia exe z argumentami, dopisuje jego stdout i stderr na koniec pliku log
    // (plik musi dać się otworzyć do dopisywania) i czeka na zakończenie. Nie rzuca wyjątków.
    static ChildResult run(const std::filesystem::path& exe, const std::vector<ChildArg>& args,
                           const std::filesystem::path& log);

#ifdef _WIN32
    // Wiersz poleceń Windows z listy argumentów (cytowanie zgodne z CommandLineToArgvW / CRT):
    // argument ze spacją, tabulatorem lub cudzysłowem trafia w cudzysłów, a ukośniki przed
    // cudzysłowem są podwajane. Publiczne — sprawdza to test jednostkowy.
    static std::wstring quoteArg(const std::wstring& arg);
#endif
};

}  // namespace volcano
