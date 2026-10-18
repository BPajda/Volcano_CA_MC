# Silnik symulacji: biblioteka statyczna (cała logika) + program engine + testy.
# Podział na bibliotekę pozwala testom korzystać z tego samego kodu co program.

# ---- profil aplikacji (etap 3) ----
# VOLCANO_OPT_FLAG — nadpisuje poziom optymalizacji konfiguracji Release (presety msvc-o1,
#   gcc-o0, gcc-o2, gcc-profile*: porównanie /O1 vs /O2 i -O0/-O2/-O3). Puste = /O2 (MSVC), -O3 (GCC).
# VOLCANO_PROFILE_NOINLINE — makro VOLCANO_NOINLINE (src/core/Profile.hpp) zabrania wstawiania
#   kluczowych funkcji, żeby profiler pokazał je osobno. Tylko presety *-profile-noinline;
#   czasy z takiego buildu nie są miarodajne.
set(VOLCANO_OPT_FLAG "" CACHE STRING "Poziom optymalizacji Release (puste = /O2 lub -O3)")
option(VOLCANO_PROFILE_NOINLINE "Kluczowe funkcje bez inline (tylko do profilowania)" OFF)
if(VOLCANO_OPT_FLAG)
    set(VOLCANO_RELEASE_OPT ${VOLCANO_OPT_FLAG})
elseif(MSVC)
    set(VOLCANO_RELEASE_OPT /O2)
else()
    set(VOLCANO_RELEASE_OPT -O3)
endif()

# ---- wspólne opcje kompilacji (ostrzeżenia, kodowanie, optymalizacja) ----
add_library(volcano_options INTERFACE)
target_compile_features(volcano_options INTERFACE cxx_std_17)
if(MSVC)
    # /utf-8: źródła i komunikaty zawierają polskie znaki.
    target_compile_options(volcano_options INTERFACE
        /W4 /permissive- /utf-8 $<$<CONFIG:Release>:${VOLCANO_RELEASE_OPT}>)
else()
    # -falign-functions=64 (etap 8): każda funkcja zaczyna się na początku linii 64 B, więc położenie pętli automatu
    # i MC względem linii pamięci podręcznej nie zależy od kodu w innych plikach. Bez tego zmiana niezwiązanego pliku
    # (np. ResultWriter.cpp, +16 B kodu) przesuwała funkcje LavaCA o 16 B i zmieniała caSim o 3–25% przy identycznym
    # kodzie maszynowym (pomiar A/B w bench/results/ab/ab_k7a_gcc_*.md). Wyniki bez zmian (tylko wyrównanie kodu).
    target_compile_options(volcano_options INTERFACE
        -Wall -Wextra $<$<CONFIG:Release>:${VOLCANO_RELEASE_OPT}> $<$<CONFIG:Release>:-falign-functions=64>)
endif()
if(VOLCANO_PROFILE_NOINLINE)
    target_compile_definitions(volcano_options INTERFACE VOLCANO_PROFILE_NOINLINE)
endif()

# ---- biblioteka z całą logiką silnika ----
add_library(volcano_engine STATIC
    src/core/Neighborhood.cpp
    src/core/Boundary.cpp
    src/core/ProcessInfo.cpp
    src/core/ChildProcess.cpp
    src/terrain/TerrainGenerator.cpp
    src/terrain/HeightmapLoader.cpp
    src/terrain/VentPlacer.cpp
    src/io/Config.cpp
    src/io/ResultWriter.cpp
    src/io/ResultReader.cpp
    src/io/TimingReport.cpp
    src/mc/PottsMC.cpp
    src/mc/Grains.cpp
    src/mc/CoolingMobility.cpp
    src/app/McStage.cpp
    src/app/Simulation.cpp
    src/app/Benchmark.cpp
    src/app/Cli.cpp
    src/app/ConfigCheck.cpp
    src/app/Batch.cpp
)
target_include_directories(volcano_engine PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/src)
# Nagłówki zewnętrzne jako SYSTEM — ich ostrzeżenia nie zaśmiecają wyniku /W4.
target_include_directories(volcano_engine SYSTEM PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/third_party)
target_link_libraries(volcano_engine PUBLIC volcano_options)
if(WIN32)
    # advapi32: odczyt nazwy procesora z rejestru (TimingReport);
    # psapi: GetProcessMemoryInfo — szczytowa pamięć procesu (ProcessInfo).
    target_link_libraries(volcano_engine PUBLIC advapi32 psapi)
endif()

# ---- program wykonywalny (wersja serwerowa) ----
add_executable(engine src/main.cpp)
target_link_libraries(engine PRIVATE volcano_engine)

# ---- mikrobenchmark składników próby MC (etap 3: GCC vs MSVC) — te same flagi co silnik ----
add_executable(mc_kernels ${PROJECT_SOURCE_DIR}/bench/micro/mc_kernels.cpp)
target_link_libraries(mc_kernels PRIVATE volcano_options)
target_include_directories(mc_kernels PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src)

# ---- testy jednostkowe (doctest) ----
add_executable(engine_tests
    tests/test_main.cpp
    tests/test_cli.cpp
    tests/test_rng.cpp
    tests/test_storage.cpp
    tests/test_neighborhood.cpp
    tests/test_boundary.cpp
    tests/test_config.cpp
    tests/test_terrain.cpp
    tests/test_ca.cpp
    tests/test_front.cpp
    tests/test_io.cpp
    tests/test_mc.cpp
    tests/test_profile.cpp
    tests/test_gui_options.cpp
    tests/test_batch.cpp
    tests/test_replay.cpp
)
target_link_libraries(engine_tests PRIVATE volcano_engine)
# Test --batch (etap 5) uruchamia prawdziwy program engine jako proces potomny — testy znają jego
# ścieżkę z wyrażenia generatora (właściwa konfiguracja Release/Debug) i budują się po nim.
target_compile_definitions(engine_tests PRIVATE VOLCANO_ENGINE_EXE="$<TARGET_FILE:engine>")
add_dependencies(engine_tests engine)

add_test(NAME unit_tests COMMAND engine_tests)
# Testy dymne programu: pomoc, krótka symulacja 2D, czytelny błąd złego configu.
add_test(NAME cli_help COMMAND engine --help)
add_test(NAME cli_smoke_2d
    COMMAND engine --config ${PROJECT_SOURCE_DIR}/configs/test_2d.json
                   --out ${CMAKE_BINARY_DIR}/smoke/test_2d --set ca.maxSteps=50)
add_test(NAME cli_bad_config
    COMMAND engine --set neighborhood=octagonal --out ${CMAKE_BINARY_DIR}/smoke/bad)
set_tests_properties(cli_bad_config PROPERTIES WILL_FAIL TRUE)

# Testy dymne Monte Carlo (etap 2): MC na całej przestrzeni, CA + MC na bazalcie
# oraz samo MC na zapisanym wyniku CA (--mc-from; wymaga wyniku z poprzedniego testu).
add_test(NAME cli_smoke_mc_full
    COMMAND engine --config ${PROJECT_SOURCE_DIR}/configs/mc_full_2d.json
                   --out ${CMAKE_BINARY_DIR}/smoke/mc_full_2d --set mc.mcs=5)
add_test(NAME cli_smoke_lava_mc
    COMMAND engine --config ${PROJECT_SOURCE_DIR}/configs/lava_mc_2d.json
                   --out ${CMAKE_BINARY_DIR}/smoke/lava_mc_2d --set mc.mcs=10)
add_test(NAME cli_smoke_mc_from
    COMMAND engine --mc-from ${CMAKE_BINARY_DIR}/smoke/lava_mc_2d
                   --config ${PROJECT_SOURCE_DIR}/configs/mc_basalt.json
                   --out ${CMAKE_BINARY_DIR}/smoke/mc_from --set mc.mcs=10)
set_tests_properties(cli_smoke_lava_mc PROPERTIES FIXTURES_SETUP lava_mc_result)
set_tests_properties(cli_smoke_mc_from PROPERTIES FIXTURES_REQUIRED lava_mc_result)

# Testy dymne opcji dla GUI (etap 4): domyślny config, walidacja (dobry i zły config),
# raport postępu na stdout.
add_test(NAME cli_print_defaults COMMAND engine --print-defaults)
set_tests_properties(cli_print_defaults PROPERTIES PASS_REGULAR_EXPRESSION "\"neighborhood\": \"moore\"")
add_test(NAME cli_validate_ok
    COMMAND engine --validate --config ${PROJECT_SOURCE_DIR}/configs/test_3d.json)
set_tests_properties(cli_validate_ok PROPERTIES PASS_REGULAR_EXPRESSION "\"ok\": true")
add_test(NAME cli_validate_bad COMMAND engine --validate --set neighborhood=octagonal)
set_tests_properties(cli_validate_bad PROPERTIES WILL_FAIL TRUE)
add_test(NAME cli_smoke_progress
    COMMAND engine --config ${PROJECT_SOURCE_DIR}/configs/lava_mc_2d.json
                   --out ${CMAKE_BINARY_DIR}/smoke/progress --set mc.mcs=10 --progress)
set_tests_properties(cli_smoke_progress PROPERTIES PASS_REGULAR_EXPRESSION "PROGRESS mc 10/10")

# Test dymny serii (etap 5): folder z dwoma configami (dobry i błędny) przygotowany przy konfiguracji
# CMake -> engine --batch: kod 5 (jeden przebieg z błędem), w konsoli tabela podsumowania.
file(WRITE ${CMAKE_BINARY_DIR}/smoke/batch_in/a_ok.json
     "{ \"space\": { \"nx\": 40, \"ny\": 40, \"nz\": 1 }, \"ca\": { \"mode\": \"classic\" }, \"vents\": { \"count\": 5 }, \"output\": { \"format\": \"bin\" } }\n")
file(WRITE ${CMAKE_BINARY_DIR}/smoke/batch_in/b_zly.json "{ \"neighborhood\": \"octagonal\" }\n")
file(WRITE ${CMAKE_BINARY_DIR}/smoke/batch_in/series.json "{ \"opis\": \"pomijany przez --batch\" }\n")
add_test(NAME cli_smoke_batch
    COMMAND engine --batch ${CMAKE_BINARY_DIR}/smoke/batch_in --out ${CMAKE_BINARY_DIR}/smoke/batch_out)
set_tests_properties(cli_smoke_batch PROPERTIES PASS_REGULAR_EXPRESSION "Razem: 2 przebiegi: 1 ok, 1 z błędem")
