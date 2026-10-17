#pragma once
// Teoretyczne zapotrzebowanie na pamięć (etap 3): rejestr dużych tablic programu.
//
// Każda duża tablica jest zgłaszana przy alokacji (rozmiar = liczba elementów × sizeof typu,
// liczony w miejscu alokacji) i przy zwolnieniu. Szczyt modelu to największa suma tablic
// żyjących jednocześnie, a peakBlocks() mówi, z czego się składał. Model pomija małe obiekty
// (config, listy kraterów, historia kroków), bufor zapisu txt (1 MB), narzut alokatora,
// kod programu i biblioteki — tę różnicę widać w raporcie po porównaniu z pomiarem
// (ProcessInfo: szczytowy zbiór roboczy / RSS).
//
// Rejestracja jest jawna (allocate/release w kodzie etapów), a nie przez własny alokator:
// gorące pętle i typy tablic zostają bez zmian, więc pomiar nie zaburza wyników ani czasów.
//
// Rozmiar siatek z ramką podają same struktury (VectorStorage::bytes, PottsMC::bytes — liczba komórek
// z ramką Dims::framedCells()). Od etapu 8 ramka jest tylko w osiach o rozmiarze > 1, więc w 2D model
// daje 2 · 13 B · (nx+2)(ny+2) zamiast 2 · 13 B · (nx+2)(ny+2) · 3 (CA classic 2D: ~91 → ~39 B/komórkę
// razem z kopią wyniku 13 B; test w test_profile.cpp).

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace volcano {

class MemoryModel {
public:
    // Blok pamięci: nazwa (np. "caGrid") i rozmiar [B].
    struct Block {
        std::string name;
        std::uint64_t bytes = 0;
    };

    // Rejestruje tablicę (lub zmienia rozmiar już zarejestrowanej o tej samej nazwie).
    void allocate(const std::string& name, std::uint64_t bytes) {
        bool found = false;
        for (Block& b : live_) {
            if (b.name == name) {
                b.bytes = bytes;
                found = true;
            }
        }
        if (!found) {
            live_.push_back(Block{name, bytes});
        }
        remember(name, bytes);
        updatePeak();
    }

    // Wyrejestrowuje tablicę (zwolnienie pamięci). Nieznana nazwa — bez zmian.
    void release(const std::string& name) {
        for (std::size_t i = 0; i < live_.size(); ++i) {
            if (live_[i].name == name) {
                live_.erase(live_.begin() + static_cast<std::ptrdiff_t>(i));
                return;
            }
        }
    }

    // Suma żyjących tablic [B].
    std::uint64_t current() const {
        std::uint64_t sum = 0;
        for (const Block& b : live_) {
            sum += b.bytes;
        }
        return sum;
    }

    // Największa suma żyjących tablic [B] i jej skład.
    std::uint64_t peak() const { return peak_; }
    const std::vector<Block>& peakBlocks() const { return peakBlocks_; }

    // Największy zarejestrowany rozmiar każdej tablicy (w kolejności pierwszej rejestracji).
    const std::vector<Block>& largest() const { return largest_; }

    bool empty() const { return largest_.empty(); }

private:
    // Zapamiętuje największy rozmiar bloku.
    void remember(const std::string& name, std::uint64_t bytes) {
        for (Block& b : largest_) {
            if (b.name == name) {
                b.bytes = std::max(b.bytes, bytes);
                return;
            }
        }
        largest_.push_back(Block{name, bytes});
    }

    // Nowy szczyt — zapamiętuje skład (>=: przy remisie późniejszy, pełniejszy skład).
    void updatePeak() {
        const std::uint64_t now = current();
        if (now >= peak_) {
            peak_ = now;
            peakBlocks_ = live_;
        }
    }

    std::vector<Block> live_;
    std::vector<Block> peakBlocks_;
    std::vector<Block> largest_;
    std::uint64_t peak_ = 0;
};

}  // namespace volcano
