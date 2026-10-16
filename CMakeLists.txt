# Główny plik CMake projektu „Symulacja erupcji wulkanu — CA lawy + MC krystalizacji”.
# Buduje silnik (część serwerowa, bez GUI) i testy jednostkowe.
cmake_minimum_required(VERSION 3.20)

project(VolcanoCaMc
    VERSION 0.1.0
    DESCRIPTION "Symulacja splywu lawy (automat komorkowy) i krystalizacji (Monte Carlo)"
    LANGUAGES CXX)

# Standard C++17 bez rozszerzeń kompilatora (kod ma się budować MSVC i GCC/Clang).
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Domyślnie Release — pomiary czasu mają sens tylko w wersji zoptymalizowanej.
# Generatory wielokonfiguracyjne (Visual Studio) wybierają konfigurację przy budowaniu.
get_property(VOLCANO_MULTI_CONFIG GLOBAL PROPERTY GENERATOR_IS_MULTI_CONFIG)
if(NOT VOLCANO_MULTI_CONFIG AND NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Typ budowania" FORCE)
endif()

# Położenie plików wykonywalnych:
# Visual Studio -> build/Release/engine.exe (generator dopisuje katalog konfiguracji),
# Makefile -> build-gcc-release/bin/engine. Przy generatorze jednokonfiguracyjnym nie
# można użyć samego katalogu budowania: plik „engine” kolidowałby z podkatalogiem engine/
# (add_subdirectory) — linker zgłasza wtedy „cannot open output file”.
if(VOLCANO_MULTI_CONFIG)
    set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR})
else()
    set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
endif()

enable_testing()
add_subdirectory(engine)
