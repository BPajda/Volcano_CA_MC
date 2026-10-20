# Walidacja statystyczna szachownicy MC (`bench/mc_validation.py`)

Ziarna generatora: 12 (1–12); wartości po ostatnim MCS: średnia ± odchylenie (przedział ufności 95% średniej); różnica = szachownica / random − 1; |t| Welcha < 2 — różnica nieistotna na poziomie ~5%. Wykładnik n: średnia wielkość ziarna ~ MCS^n (MCS 20–100).

| Przypadek | wielkość | random | szachownica | różnica | t Welcha |
|---|---|---|---|---|---|
| 2D 200², von Neumann, kT = 0 (MCS 100) | liczba ziaren | 5 529 ± 26.7 (±16.9) | 5 436 ± 21.9 (±13.9) | -1.7% | -9.29 |
| 2D 200², von Neumann, kT = 0 (MCS 100) | średnia wielkość ziarna | 7.235 ± 0.035 (±0.022) | 7.358 ± 0.030 (±0.019) | +1.7% | +9.32 |
| 2D 200², von Neumann, kT = 0 (MCS 100) | energia | 33 226 ± 99.2 (±63.0) | 32 993 ± 82.5 (±52.4) | -0.7% | -6.25 |
| 2D 200², von Neumann, kT = 0 | wykładnik wzrostu n | 0.660 ± 0.003 | 0.660 ± 0.004 | -0.1% | -0.30 |
| 2D 200², von Neumann, kT = 0 | średni współczynnik akceptacji | 0.130 | 0.131 | +0.4% | — |
| 3D 50³, Moore, kT = 0 (MCS 100) | liczba ziaren | 3 498 ± 34.3 (±21.8) | 3 417 ± 43.8 (±27.9) | -2.3% | -5.06 |
| 3D 50³, Moore, kT = 0 (MCS 100) | średnia wielkość ziarna | 35.7 ± 0.350 (±0.222) | 36.6 ± 0.469 (±0.298) | +2.4% | +5.04 |
| 3D 50³, Moore, kT = 0 (MCS 100) | energia | 880 181 ± 1 740 (±1 106) | 876 728 ± 2 861 (±1 818) | -0.4% | -3.57 |
| 3D 50³, Moore, kT = 0 | wykładnik wzrostu n | 0.806 ± 0.005 | 0.777 ± 0.009 | -3.6% | -10.05 |
| 3D 50³, Moore, kT = 0 | średni współczynnik akceptacji | 0.056 | 0.056 | -0.7% | — |
| 2D 200², von Neumann, kT = 0,3 (MCS 100) | liczba ziaren | 10 902 ± 107 (±68.0) | 10 776 ± 93.9 (±59.7) | -1.1% | -3.04 |
| 2D 200², von Neumann, kT = 0,3 (MCS 100) | średnia wielkość ziarna | 3.670 ± 0.036 (±0.023) | 3.712 ± 0.033 (±0.021) | +1.2% | +3.03 |
| 2D 200², von Neumann, kT = 0,3 (MCS 100) | energia | 41 950 ± 199 (±126) | 41 670 ± 186 (±118) | -0.7% | -3.56 |
| 2D 200², von Neumann, kT = 0,3 | wykładnik wzrostu n | 0.405 ± 0.005 | 0.406 ± 0.007 | +0.1% | +0.21 |
| 2D 200², von Neumann, kT = 0,3 | średni współczynnik akceptacji | 0.274 | 0.273 | -0.2% | — |
