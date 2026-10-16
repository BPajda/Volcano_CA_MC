#pragma once
// Makro VOLCANO_NOINLINE — wyłącznie do profilowania (etap 3).
//
// W buildzie Release kompilator wstawia (inline) małe funkcje i metody szablonów do pętli
// kroku, więc profiler (gprof, callgrind, Visual Studio) widzi prawie cały czas w jednej
// funkcji (stepLava, sweep). W presetach profilowania z opcją CMake
// VOLCANO_PROFILE_NOINLINE=ON (np. gcc-profile-noinline) makro zabrania wstawiania kluczowych
// funkcji, żeby profil pokazał je osobno. Koszt: dodatkowe wywołania — czasy takiego buildu
// NIE są miarodajne, służy tylko do podziału czasu między funkcje.
// W normalnym buildzie makro jest puste i generowany kod się nie zmienia.

#if defined(VOLCANO_PROFILE_NOINLINE)
#  if defined(_MSC_VER)
#    define VOLCANO_NOINLINE __declspec(noinline)
#  else
#    define VOLCANO_NOINLINE __attribute__((noinline))
#  endif
#else
#  define VOLCANO_NOINLINE
#endif
