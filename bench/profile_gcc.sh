#!/usr/bin/env bash
# Profilowanie wersji GCC (etap 3): gprof i valgrind callgrind -> bench/profiles/.
#
# Uruchamiać w WSL z katalogu volcano-ca-mc, po zbudowaniu presetów:
#   cmake --preset gcc-profile && cmake --build --preset gcc-profile -j
#   cmake --preset gcc-profile-noinline && cmake --build --preset gcc-profile-noinline -j
#   cmake --preset gcc-o2 && cmake --build --preset gcc-o2 -j
#   cmake --preset gcc-o2-noinline && cmake --build --preset gcc-o2-noinline -j
# Z Windows (Git Bash):
#   wsl -e bash -lc "bash bench/profile_gcc.sh"      (z katalogu projektu — WSL startuje w bieżącym katalogu)
#
# Warianty (jak w poleceniu etapu):
#   ca_lava_test3d   — CA lava 3D (configs/test_3d.json), 5 przebiegów zsumowanych (gprof -s),
#   ca_lava_etna3d   — CA lava 3D, większy (configs/etna_3d.json), 1 przebieg (~30 s),
#   ca_classic_100c  — CA classic 100x100x100, VN, 10 zarodków (configs/classic_ref.json), 10 przebiegów,
#   mc_full_3d       — MC full 50x50x50, Moore (configs/mc_full_3d.json) z mc.mcs = 300 (dłuższy przebieg
#                      = więcej próbek gprof; 50 MCS trwa < 1 s).
# gprof próbkuje co 10 ms — krótkie przebiegi powtarzamy i sumujemy profile.
#
# Buildy:
#   gcc-profile           -O2 -pg -g        — kod jak w Release (inline): profil „uczciwy”, ale gruby,
#   gcc-profile-noinline  -O2 -pg -g + VOLCANO_NOINLINE — kluczowe funkcje widoczne osobno (czasy zawyżone
#                                              narzutem wywołań; służy do podziału czasu między funkcje),
#   gcc-o2                -O2 -g            — callgrind (liczba instrukcji Ir, przypisanie do linii źródła),
#   gcc-o2-noinline       -O2 -g + VOLCANO_NOINLINE, bez -pg — callgrind z podziałem na funkcje
#                                              (program z -pg ginie pod valgrindem od sygnału SIGPROF).
# Callgrind spowalnia ~50x, więc dostaje mniejsze warianty (test_3d, classic_ref, mc_full_3d 50 MCS).
# Programy uruchamiamy z katalogu projektu (ścieżki configów względne), a GMON_OUT_PREFIX kieruje
# profil gprof do folderu roboczego (plik <prefiks>.<pid> zamiast gmon.out w bieżącym katalogu).

set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$(pwd)
OUT=bench/profiles
TMP=/tmp/volcano_prof
mkdir -p "$OUT" "$TMP"

# nazwa | argumenty (bez spacji w ścieżkach) | powtórzenia gprof
CASES=(
  "ca_lava_test3d|--config configs/test_3d.json --set output.format=none|5"
  "ca_lava_etna3d|--config configs/etna_3d.json --set output.format=none|1"
  "ca_classic_100c|--config configs/classic_ref.json --set output.format=none|10"
  "mc_full_3d|--config configs/mc_full_3d.json --set output.format=none --set mc.mcs=300|1"
)

# SKIP_GPROF=1 — tylko callgrind (np. po wcześniejszym przebiegu gprof).
GPROF_BUILDS="gcc-profile gcc-profile-noinline"
[ "${SKIP_GPROF:-0}" = "1" ] && GPROF_BUILDS=""
for build in $GPROF_BUILDS; do
  exe="$ROOT/build-$build/bin/engine"
  [ -x "$exe" ] || { echo "Brak $exe — zbuduj preset $build"; exit 1; }
  for c in "${CASES[@]}"; do
    IFS='|' read -r name args reps <<< "$c"
    work="$TMP/$build/$name"
    rm -rf "$work" && mkdir -p "$work"
    sums=()
    for ((r = 0; r < reps; r++)); do
      rm -f "$work"/gmon.[0-9]*
      # shellcheck disable=SC2086  # $args celowo dzielone na słowa
      GMON_OUT_PREFIX="$work/gmon" taskset -c 2 "$exe" $args --out "$work/out" > /dev/null
      mv "$work"/gmon.[0-9]* "$work/run.$r"
      sums+=("$work/run.$r")
    done
    # Kilka plików profilu podanych naraz gprof sumuje sam (gprof -s z binutils 2.38 i symbolami -g
    # kończy się błędem „somebody miscounted: ltab.len”).
    {
      echo "# gprof (profil płaski), build $build, wariant $name ($args), przebiegów: $reps"
      echo "# $(date -Iseconds), $(g++ --version | head -1)"
      gprof -b -p "$exe" "${sums[@]}"
    } > "$OUT/gprof_${build#gcc-}_${name}_flat.txt"
    {
      echo "# gprof (graf wywołań), build $build, wariant $name ($args), przebiegów: $reps"
      gprof -b -q "$exe" "${sums[@]}"
    } > "$OUT/gprof_${build#gcc-}_${name}_graph.txt"
    echo "gprof $build $name: OK"
  done
done

# --- callgrind (liczba wykonanych instrukcji Ir; --dump-instr=no zgodnie z poleceniem) ---
CG_CASES=(
  "ca_lava_test3d|--config configs/test_3d.json --set output.format=none"
  "ca_classic_100c|--config configs/classic_ref.json --set output.format=none"
  "mc_full_3d|--config configs/mc_full_3d.json --set output.format=none"
)
for build in gcc-o2 gcc-o2-noinline; do
  exe="$ROOT/build-$build/bin/engine"
  [ -x "$exe" ] || { echo "Brak $exe — zbuduj preset $build"; exit 1; }
  for c in "${CG_CASES[@]}"; do
    IFS='|' read -r name args <<< "$c"
    work="$TMP/cg_$build/$name"
    rm -rf "$work" && mkdir -p "$work"
    # shellcheck disable=SC2086
    GMON_OUT_PREFIX="$work/gmon" valgrind --tool=callgrind --dump-instr=no \
      --callgrind-out-file="$work/callgrind.out" "$exe" $args --out "$work/out" > /dev/null 2> "$work/valgrind.log"
    # Pełne raporty do plików, potem head (head na potoku + pipefail = SIGPIPE i przerwanie skryptu).
    callgrind_annotate --inclusive=no "$work/callgrind.out" > "$work/self.txt" 2> /dev/null
    callgrind_annotate --inclusive=yes "$work/callgrind.out" > "$work/incl.txt" 2> /dev/null
    {
      echo "# callgrind, build $build, wariant $name ($args)"
      echo "# $(valgrind --version), koszt = Ir (wykonane instrukcje), --dump-instr=no"
      head -n 60 "$work/self.txt"
      echo
      echo "# --- koszt włączny (funkcja + wywoływane) ---"
      head -n 45 "$work/incl.txt"
    } > "$OUT/callgrind_${build#gcc-}_${name}.txt"
    if [ "$build" = "gcc-o2" ]; then
      # Koszt przypisany do linii źródła (kod wstawiony inline widać w swoich plikach nagłówkowych).
      callgrind_annotate --auto=yes --show-percs=yes --context=1 "$work/callgrind.out" 2> /dev/null \
        > "$OUT/callgrind_${build#gcc-}_${name}_lines.txt" || true
    fi
    echo "callgrind $build $name: OK"
  done
done
echo "Raporty w $OUT"
