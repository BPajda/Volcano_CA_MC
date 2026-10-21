#pragma once
// Równoległy zapis i odczyt wyników (etap 11, mpi.io = "mpiio") — każdy proces zapisuje swój pas warstw do
// wspólnego pliku, zamiast zbierać siatkę na procesie 0 (MPI_Gatherv) i zapisywać ją tam (etap 10). Pliki są bajt
// w bajt takie same jak z engine (formaty: io/ResultWriter.hpp).
//
// Pliki binarne (ca_result.bin, mc_result.bin, migawki): nagłówek + tablice pól całej przestrzeni po kolei. Pas
// warstw [lo, hi) jest w każdej tablicy ciągłym fragmentem (oś warstw jest zewnętrzna), więc proces zapisuje swój pas
// każdej tablicy pod przesunięciem nagłówek + początek tablicy + lo · (komórki warstwy) · (rozmiar elementu):
//   * widok pliku (MPI_File_set_view) = typ pochodny opisujący pas w pliku: dla każdej tablicy
//     MPI_Type_create_subarray (tablica L × (bajty warstwy), pas: warstwy [lo, hi)), tablice połączone
//     MPI_Type_create_struct z przesunięciami początków tablic; przesunięcie widoku = rozmiar nagłówka;
//   * dane w pamięci — MPI_Type_create_struct z bloków pól pasu (przesunięcia względem tablicy o najniższym adresie,
//     która jest buforem zapisu — nie MPI_BOTTOM, patrz writeStrips w MpiIo.cpp);
//   * jeden zapis zbiorowy MPI_File_write_all; nagłówek pisze proces 0 (MPI_File_write_at), rozmiar pliku ustawia
//     MPI_File_set_size (stary, dłuższy plik zostałby inaczej z „ogonem”).
// Typy plikowe i pamięciowe są z bajtów (MPI_BYTE, reprezentacja "native") — elementy pól są przepisywane bez zmian.
// Pliki tekstowe (ca_result.txt, mc_result.txt): wiersze mają zmienną długość, więc przesunięcie pasa nie wynika
// z numeru warstwy. Każdy proces formatuje swoje wiersze do pamięci (ten sam formatter co engine — ResultWriter,
// etap 8 k7), MPI_Exscan sumy długości daje przesunięcie pasa (proces 0 dokleja nagłówek przed swoimi wierszami),
// potem MPI_File_write_at_all (w porcjach < 2 GB).
// Odczyt (--mc-from): proces 0 czyta nagłówek ca_result.bin (wymiary, wersja), a każdy proces — tylko swój pas tablic
// type, solidStep i arrivalStep (MPI_File_read_at_all).
//
// Uwaga (WSL): MPI-IO tylko na ext4 (/tmp, katalog w systemie plików WSL); dysk Windows przez 9p (/mnt/<dysk>) działa,
// ale wielokrotnie wolniej (bench/results/mpi_io/POSTEP.md, punkt 0.2).

#include <mpi.h>

#include <cstdint>
#include <string>
#include <vector>

#include "core/Types.hpp"
#include "io/ResultReader.hpp"

namespace volcano {

// Czas jednego pliku na tym procesie [ms] i bajty.
struct IoTimes {
    double formatMs = 0.0;          // przygotowanie danych (tekst: formatowanie wierszy pasa)
    double ioMs = 0.0;              // MPI-IO: otwarcie, rozmiar, widok, zapis / odczyt zbiorowy, zamknięcie
    std::uint64_t fileBytes = 0;    // rozmiar pliku (zapis) / przeczytane bajty wszystkich procesów (odczyt)
    std::uint64_t ownBytes = 0;     // bajty zapisane / przeczytane przez ten proces
};

class MpiIo {
public:
    // ca_result.bin z pasów: slab — własne warstwy [lo, lo + warstwy slab) przestrzeni global.
    static IoTimes writeCaBin(MPI_Comm comm, const std::string& path, const Dims& global, int lo,
                              const Microstructure& slab);
    // ca_result.txt z pasów.
    static IoTimes writeCaTxt(MPI_Comm comm, const std::string& path, const Dims& global, int lo,
                              const Microstructure& slab);
    // mc_result.bin / mc_result.txt z pasów: own — mapa kryształów własnych warstw (wymiary slab).
    static IoTimes writeCrystalBin(MPI_Comm comm, const std::string& path, const Dims& global, int lo,
                                   const Dims& slab, const std::vector<std::int32_t>& own);
    static IoTimes writeCrystalTxt(MPI_Comm comm, const std::string& path, const Dims& global, int lo,
                                   const Dims& slab, const std::vector<std::int32_t>& own);
    // --mc-from: pas [lo, lo + warstwy slab) tablic type, solidStep i arrivalStep (od wersji 2) z ca_result.bin
    // o nagłówku h; slab musi mieć już wymiary pasa (Microstructure::resize).
    static IoTimes readCaStrip(MPI_Comm comm, const std::string& path, const BinHeader& h, int lo,
                               Microstructure& slab);
};

}  // namespace volcano
