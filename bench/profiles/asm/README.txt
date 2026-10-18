Listingi asemblera PottsMC::sweep() (analiza GCC vs MSVC — docs/etap-3-profilowanie.md, punkt 2.4).
PottsMC_sweep_msvc_O2.asm   — cl /O2 /Ob2 /DNDEBUG /FAs (MSVC 19.38), fragment funkcji sweep
PottsMC_sweep_gcc_O3.s      — g++ -O3 -DNDEBUG -S (GCC 11.4), fragment funkcji sweep
PottsMC_msvc_Qvec-report.txt — /Qvec-report:2 (pętla po sąsiadach: niewektoryzowana, powód 1200)
PottsMC_gcc_fopt-info-vec.txt — -fopt-info-vec-optimized (sweep nie występuje = niewektoryzowany)
Pętla po sąsiadach: MSVC $LL41@sweep (skok je po porównaniu orientacji), GCC .L175 (setne, bez skoku).

Etap 8 (k1 — liczenie sąsiadów bez skoku warunkowego, energia przed i po w jednym przejściu):
PottsMC_unlike_msvc_O2_etap8.asm — cl /O2 /Ob2 /DNDEBUG /FAs (MSVC 19.38), pętla unlikeBeforeAfter wstawiona
  w sweepTrials<0,0>: $LL25 — trzy liczniki przez setne/sete, jedyny skok to powrót pętli (jb).
GCC 11.4 -O3 (objdump programu build-gcc-release/bin/engine, sweepTrials<false,false>): pętla po sąsiadach
  cmp/sbb (sąsiad w domenie) + 2 × sete, jedyny skok to powrót pętli (jne).
