# Wygląd interfejsu

Motyw „Bazalt i lawa”: kolory, motywy ciemny i jasny, paleta danych, kontrast, daltonizm, płynność.

Zmiany wyłącznie wizualne: zmieniony tylko frontend (`gui/static/**`) i jedna linia serwowania fontów w `gui/app.py`
(typ MIME `.woff2`). Silnik, reguły CA/MC, API, formaty plików, nazwy zakładek i przycisków, `id` i `data-*` zostały bez zmian.
Kolory interfejsu: `gui/static/css/style.css`, motyw: `gui/static/js/theme.js`, kolory danych: `gui/static/js/palette.js`.

## 1. Co było nie tak (przegląd przed zmianą)

Zrzuty stanu „przed”: `img/ui_przed_*.png` (8 zakładek, 1440×900, `python gui/tests/ui_shots.py --prefix ui_przed`).

| Zakładka | Co raziło |
|---|---|
| wszystkie | generyczny szaro-biały panel bez związku z tematem; zakładki w jednym rzędzie bez podziału na kroki pracy; status silnika jako sam tekst ze ścieżką; brak motywu ciemnego; `body { min-width: 1280px }`, więc przy 1280×720 ze skalowaniem 125% (1024 px CSS) strona przewijała się w poziomie o 256 px |
| Nowa symulacja | niespójne przyciski („Wartości domyślne” jako goły tekst obok obramowanych), główny przycisk **Uruchom** w niebieskim kolorze bazaltu, karty bez nagłówków (preset, nazwa zadania), szara miniatura mapy, błąd walidacji tylko jako czerwona ramka pola |
| Seria | aktywny szablon i znaczki „sparowane” w kolorze bazaltu; numeracja kroków („1.”, „2.”) w tekście nagłówka |
| Zadania | ściana jednakowych niebieskich przycisków **Pokaż wynik** i pełnych zielonych pasków (zadania gotowe dominowały nad działającymi); „gotowe” powtórzone pod paskiem; ikony statusu ze znaków Unicode; nagłówek tabeli odjeżdżał przy przewijaniu |
| Wyniki | 5–6 osobnych małych przycisków w każdym wierszu w dwóch rzędach; nagłówek tabeli nieprzyklejony |
| Porównanie | CA = niebieski, MC = pomarańczowy (kolory slotów palety, bez związku z tematem, inne niż w Czasach) |
| Podgląd 2D | **krater 1 niebieski jak woda**; powietrze i tło podglądu prawie tego samego koloru; legenda w osobnej karcie zostawia pustą kolumnę; „Eksport PNG” spada do drugiego rzędu |
| Podgląd 3D | **bazalt niebieski**; płaskie jasnoszare tło; puste kolumny (powietrze) jako biała plama pod terenem; ramka i podpisy osi czarne |
| Czasy i statystyki | wszystkie paski i wykresy w jednym niebieskim kolorze, CA i MC nieodróżnialne |

## 2. Kierunek wizualny i dlaczego taki

**Motyw ciemny (domyślny), „bazalt”:** ciepła czerń i grafit (tło `#15120f`, karty `#1f1b17`, podniesione
`#2a251f`), tekst w kolorze popiołu (`#efe8de`, drugorzędny `#a89f93`), cienkie linie podziału. Ciemne tło: lawa
i żar „świecą” na nim tak jak w nocy na prawdziwym wulkanie, a rzutnik w zaciemnionej sali nie oślepia białą plamą.

**Akcent w kolorze lawy:** gradient pomarańcz → żółty żar (`#ff5a1f` → `#ffb02e`), oszczędnie: przyciski główne
(**Uruchom**, **Uruchom serię**, **Odtwórz**), aktywna zakładka (podkreślenie z poświatą), przełączniki, suwaki,
paski postępu, znacznik zmienionego pola, znaczniki kraterów. Tekst na przycisku lawy jest ciemny (`#1b0e06`,
kontrast 6,1:1, biały miałby tylko ~3:1). Reszta interfejsu jest neutralna, żeby kolor niósł znaczenie.

**Motyw jasny, „popiół”:** pełnoprawny (rzutnik w jasnej sali, zrzuty do druku): tło `#f2ede6`, karty
`#fbf9f6`, tekst `#231b14` / `#5e554b`, ten sam akcent lawy, kolory stanów przyciemnione do kontrastu AA.

**Narzędzie naukowe, nie gra:** bez tekstur, cząsteczek i animowanych teł; ruch tylko jako krótkie przejścia
(120–180 ms), wolna poświata przycisku **Uruchom** i kręcące się ikony stanu „działa”; wszystko wyłączone przy
`prefers-reduced-motion`.

**Nagłówek:** własna ikona SVG (stożek z kraterem, strużka lawy i kropla lawy; gradient lawy; `#i-volcano`
w `index.html`, ta sama jako favicon), tytuł „Wulkan — spływ lawy (CA) i krystalizacja bazaltu (MC)”, podtytuł
z metodą („Automat komórkowy + Monte Carlo (model Pottsa)”), status silnika jako pigułka („silnik gotowy” z zieloną kropką, pełna ścieżka i katalogi w podpowiedzi),
przełącznik motywu (księżyc / słońce). Zakładki: te same nazwy, kolejność i `data-tab`, pogrupowane etykietami
i separatorami: **Przygotuj** (Nowa symulacja, Seria) · **Licz** (Zadania + licznik aktywnych) · **Analizuj** (Wyniki,
Porównanie, Podgląd 2D, Podgląd 3D, Czasy i statystyki). Przy szerokości < 1180 px etykiety grup i podtytuł się chowają.

**Komponenty** (jednolite w całym GUI): przycisk główny (lawa), drugorzędny (obrys), „duch” i niebezpieczny
(Anuluj / Anuluj serię: czerwony obrys); pola i listy z własną strzałką i fokusem w kolorze lawy; przełączniki
zamiast kwadratowych checkboxów (lista wyboru wyników w Porównaniu zostaje polem wyboru); wybór segmentowy dla
osi przekroju (x / y / z) i widoku 3D (ściany / powierzchnia / woksele); karty z nagłówkami (kroki serii jako
numerowane kółka); tabele z nagłówkiem przyklejonym w przewijanym obszarze; paski postępu w kolorze żaru (gotowe:
przygaszony zielony, błąd: czerwony); komunikaty z ikoną i kolorowym lewym brzegiem; **błąd walidacji pod polem**
(ikona + treść komunikatu silnika; lista także nad przyciskami); podpowiedź komórki w 2D jako karta z próbką koloru;
puste stany z ikoną i wskazówką („Brak wyników w `results/` — uruchom symulację w zakładce „Nowa symulacja”);
stan ładowania jako pigułka z kółkiem postępu. Ikony to proste inline SVG (`<symbol id="i-…">` w `index.html`,
w JS `icon()` z `util.js`), bez emoji. Liczby w tabelach, licznikach i legendach: cyfry o stałej szerokości.

## 3. Paleta interfejsu

| Rola (zmienna CSS) | Ciemny „bazalt” | Jasny „popiół” |
|---|---|---|
| tło strony `--bg` | `#15120f` | `#f2ede6` |
| karta `--panel` | `#1f1b17` | `#fbf9f6` |
| przycisk / pole podniesione `--raised` | `#2a251f` | `#ede7de` |
| pole formularza `--inset` | `#171410` | `#ffffff` |
| tekst `--ink` | `#efe8de` | `#231b14` |
| tekst drugorzędny `--ink-2` | `#a89f93` | `#5e554b` |
| wyciszony / wyłączony `--muted` | `#8f857a` | `#776d63` |
| lawa `--lava` → `--lava-2` | `#ff5a1f` → `#ffb02e` | jw. |
| tekst w kolorze lawy `--accent-text` | `#ff8c52` | `#b93c0b` |
| obrys fokusu klawiatury `--focus` | `#ffb02e` | `#c2410c` |
| OK / ostrzeżenie / błąd / informacja | `#5cc98f` / `#f2b33d` / `#ff7b6b` / `#8fb5e8` | `#1d7a45` / `#8a5a00` / `#c0322a` / `#2e5f9e` |
| tło podglądu 2D `--view-bg` | `#0f0d0b` | `#e9e3d9` |
| niebo 3D `--sky-top` → `--sky-bottom` | `#0a0d15` → `#2b1d15` (noc, łuna nad horyzontem) | `#c9d5df` → `#f1eadf` (mglisty dzień) |
| wykresy: CA / MC / CA+MC | `#e8682a` / `#7d68dd` / `#1f97a8` | jw. |
| wykresy: inne serie `--series-1…8` | `#3987e5 #d95926 #199e70 #c98500 #d55181 #008300 #9085e9 #e66767` | `#2a78d6 #eb6834 #1baf7a #eda100 #e87ba4 #008300 #6250d6 #e34948` |

Kolory stanów są zarezerwowane (OK / ostrzeżenie / błąd) i zawsze idą z ikoną i tekstem. Kolory CA / MC / CA+MC
sprawdzono walidatorem palety (tła kart obu motywów): przechodzą wszystkie
progi dla wszystkich par (pasmo jasności, chroma, ΔE przy proto-/deuteranopii ≥ 11,8, normalne widzenie ≥ 18,3,
kontrast ≥ 3:1); paleta `--series-*` to sprawdzona paleta referencyjna (pary sąsiednie; legenda + tabela).

## 4. Paleta naukowa (kolory komórek): `palette.js`

Te same kolory w podglądzie 2D, 3D (ściany, powierzchnia, woksele), legendach, galerii Porównania, eksporcie PNG,
klatkach PNG i filmie WebM.

| Typ / pole | Motyw ciemny | Motyw jasny | Uzasadnienie |
|---|---|---|---|
| powietrze | `#1a1613` (tło podglądu `#0f0d0b`) | `#f7f3ed` (tło `#e9e3d9`) | „nic”: kolor tła, lekko odróżniony od tła podglądu, żeby było widać granicę bloku |
| skała (teren) | `#8a7f72` | `#c8bdae` | ciepła szarość-brąz jak stary, zwietrzały teren; w rzucie z góry cieniowana wysokością (ten sam odcień, 62–112% jasności) |
| lawa płynna | `#ff6a1f` | jw. | pomarańcz-żar |
| bazalt | `#464a55` | jw. | ciemny grafit z nutą chłodu: zastygła lawa; jaśniejszy od proponowanego `#2e2f35`, żeby odróżniał się od ciemnego tła (ΔE 21) i skały (ΔE 19) |
| krater / ziarno 1–10 | `#ee7733` `#2f5fd0` `#66ccee` `#f0e442` `#9085e9` `#ccbb44` `#e8402f` `#3d7fc4` `#c39bf0` `#5b6ee1` | jw. | patrz niżej; > 10: kolor z hasha ID (bez zmian) |
| kryształ MC | hash Knutha z ID (`hashColor`, = `crystal_rgb()` z `tools/plot_slice.py`) | jw. | bez zmian, wygląda dobrze w obu motywach, kolor ziarna stały między przekrojami |
| temperatura | „żar”: `#6e1410` → `#a81d14` → `#d6361c` → `#f0641e` → `#ff9a1f` → `#ffc93c` → `#fff1b0` | jw. | ciemna czerwień = chłodniej, jasnożółty = goręcej; ta sama skala co odtwarzanie erupcji |
| czas stygnięcia | `#1b2a5c` → `#1f4a8a` → `#1f73a6` → `#239db2` → `#4cc6bc` → `#9ce9d6` | jw. | chłodna skala granat → turkus; jasny turkus = długo płynna lawa → duże kryształy MC |
| odtwarzanie „żar” | płynna lawa w skali „żar” wg temperatury w kroku; bazalt `#464a55` | jw. | bez zmian merytorycznych; bazalt ten sam co w widoku „typ komórki” (wcześniej osobny `#3b3936`) |
| mapa „Kratery na mapie” | hipsometria (bez zmian), znacznik krateru: lawa `#ff6a1f` + ciemny i jasny obrys, numer z obwódką | jw. | czytelny na zieleni nizin i na jasnych szczytach |

**Kratery / ziarna (`flowId`).** Kolejność dobrana algorytmicznie: z puli kolorów (Okabe–Ito, Paul Tol, paleta
referencyjna) odrzucono te, które przy proto- lub deuteranopii są bliżej niż ΔE 8 od skały albo bazaltu (wszystkie
zielenie i czerwienie-róże zbliżone do brązu), a następnie zachłannie dokładano kolor najdalszy od już wybranych
(minimum z ΔE przy protanopii, deuteranopii i normalnym widzeniu). Krater 1 to pomarańcz lawy (wynik z jednym kraterem
wygląda jak lawa, nie jak woda). Dla komórek na mapie każda para kraterów może się stykać, więc liczy się **każda para**
(nie tylko sąsiednie w legendzie): ΔE OKLab ×100, model Machado 2009:

| liczba kraterów | min. ΔE, protanopia / deuteranopia | min. ΔE, normalne widzenie |
|---|---|---|
| 1–3 | 22,3 | 29,0 |
| 1–5 | 13,3 | 16,8 |
| 1–6 | 8,2 | 12,2 |
| 1–7 | 7,6 | 10,4 |
| 1–10 | 4,4 | 7,0 |

Do 5 kraterów kolory są rozróżnialne parami także przy daltonizmie (próg 8), do 7 na granicy; przy większej
liczbie (i przy setkach ziaren `classic`) identyfikację zapewniają: numer w legendzie, podpowiedź komórki
(`flowId`), granice ziaren. Takiego ograniczenia nie da się obejść paletą: 8–10 kolorów nie może być parami
rozróżnialnych przy deuteranopii (zostaje praktycznie jedna oś barw niebieski–żółty).

**Eksport PNG / klatki / WebM:** w kolorach **bieżącego motywu** (tło karty, tło podglądu / niebo 3D, legenda
w kolorach tekstu motywu), więc obraz jest taki jak na ekranie. Do druku (biała strona) wystarczy przełączyć
motyw na jasny przed eksportem; ciemny eksport nadaje się do prezentacji.

## 5. Podglądy i wykresy

- **3D (three.js):** przezroczysty canvas nad gradientem nieba z CSS (`.canvas-wrap.sky`), światło półkuli
  (niebo / grunt z motywu) + kierunkowe „słońce” z NW nad wulkanem (zbocza od słońca ciemniejsze, rzeźba czytelna);
  płynna lawa w odtwarzaniu (powierzchnia i woksele) dostaje emisję w swoim kolorze (atrybut `aGlow`, `glowMaterial()`
  w `viewer3d.js`), świeci także w cieniu; ramka bloku, strzałki i podpisy osi w kolorach motywu. Logika odtwarzania
  i próbkowania danych bez zmian (zmiany tylko w kolorowaniu i materiałach).
- **2D (canvas):** tło podglądu, ramka przekroju, linie granic ziaren i podpisy osi z motywu; podpowiedź komórki
  jako karta (współrzędne w kolorze lawy, typ z próbką koloru); pasek odtwarzania jak w 3D.
- **Wykresy (Chart.js):** osie, siatka, legenda i podpowiedź z motywu (`theme.js` ustawia `Chart.defaults`); serie
  CA = lawa, MC = fiolet, CA+MC = turkus w Porównaniu i w Czasach (linie MCS w kolorze MC, płynna lawa w kolorze CA,
  paski czasu faz: symulacja CA / MC w kolorze algorytmu, reszta neutralnie). Po zmianie motywu wykresy, galeria,
  przekroje, scena 3D, miniatura mapy i mapa kraterów rysują się od nowa.
- **Kratery na mapie:** mapa hipsometryczna z cieniowaniem bez zmian; znaczniki w kolorze lawy z obrysem, numer
  z obwódką, lista kraterów z numerami w kółkach, pole „pod kursorem” jako karta.
- **Suwaki:** tor z wypełnieniem w kolorze żaru do bieżącej wartości (warstwa przekroju, krok odtwarzania,
  przewyższenie), uchwyt z obrysem lawy, w obu motywach jednakowo (natywny suwak Chrome w jasnym motywie miał
  ciemny tor). **Spacja** = Odtwórz / Pauza, gdy pasek odtwarzania jest widoczny.

## 6. Motywy, przełącznik, fonty

- Zmienne kolorów w `:root` (ciemny) i `:root[data-theme="light"]` (jasny). Atrybut `data-theme` ustawia mały skrypt
  w `<head>` przed pierwszym malowaniem (bez mignięcia): wybór z `localStorage` (`volcano.theme`, w `try/catch`),
  inaczej `prefers-color-scheme`; dopóki użytkownik nie wybierze sam, motyw idzie za zmianą ustawień systemu.
- `theme.js`: `themeColors()` (kolory z CSS dla canvasu, three.js i Chart.js), `onThemeChange()`, przełącznik
  `#theme-toggle`, zmienne `--header-h` i `--resultbar-h` (podgląd na całą wysokość okna). `palette.js` słucha zmiany
  motywu (powietrze i skała).
- Fonty lokalnie (`gui/static/vendor/fonts/`, SIL OFL 1.1, licencje i sumy SHA-256 w `vendor/README.md`):
  **Inter** (tekst) i **JetBrains Mono** (ścieżki, wartości, numer kroku), zmienna grubość, podzbiory `latin`
  i `latin-ext` (polskie litery). `gui/app.py` rejestruje typ `font/woff2`.

## 7. Układ i czytelność (rzutnik, mniejsze ekrany)

- Usunięte `min-width: 1280px`. Bez poziomego przewijania przy 1024×576 (1280×720, skalowanie 125%), 1093×614
  (1366×768, 125%), 1280×720, 1440×900 i 1920×1080, sprawdzane skryptem `ui_shots.py` (porównuje szerokość
  dokumentu z oknem). Przy < 1360 px formularz ma jedną kolumnę sekcji, przy < 1180 px chowają się etykiety grup
  zakładek, podtytuł i opis wyniku, przy < 920 px panel boczny (szacunek, legenda) schodzi pod treść.
- Podgląd 2D/3D zajmuje całą dostępną wysokość okna (siatka z wierszem `1fr` i wysokością minimalną = okno − nagłówek −
  pasek wyniku); gdy pasków jest więcej niż miejsca (bardzo niskie okno), strona przewija się w pionie, ale nic
  na siebie nie nachodzi. Przy wysokości < 760 px nagłówek, karty i paski są ciaśniejsze.
- Dostępność: kontrast tekstu ≥ 4,5:1 (punkt 9), widoczny `:focus-visible` (obrys `--focus`: żar w motywie ciemnym, ciemny pomarańcz w jasnym) na przyciskach,
  polach, zakładkach, przełącznikach i segmentach; przyciski z ikonami mają etykiety tekstowe (▲ / ▼: `aria-label`),
  pola wyszukiwania i list bez etykiety: `aria-label`.

## 8. Przed / po

| Zakładka | Przed | Po (motyw ciemny) |
|---|---|---|
| Nowa symulacja | ![](img/ui_przed_nowa_symulacja.png) | ![](img/ui_po_nowa_symulacja.png) |
| Seria | ![](img/ui_przed_seria.png) | ![](img/ui_po_seria.png) |
| Zadania | ![](img/ui_przed_zadania.png) | ![](img/ui_po_zadania.png) |
| Wyniki | ![](img/ui_przed_wyniki.png) | ![](img/ui_po_wyniki.png) |
| Porównanie | ![](img/ui_przed_porownanie.png) | ![](img/ui_po_porownanie.png) |
| Podgląd 2D | ![](img/ui_przed_podglad_2d.png) | ![](img/ui_po_podglad_2d.png) |
| Podgląd 3D | ![](img/ui_przed_podglad_3d.png) | ![](img/ui_po_podglad_3d.png) |
| Czasy i statystyki | ![](img/ui_przed_czasy.png) | ![](img/ui_po_czasy.png) |

Motyw jasny „popiół” (`img/ui_jasny_*.png`):

![](img/ui_jasny_nowa_symulacja.png)
![](img/ui_jasny_podglad_2d.png)
![](img/ui_jasny_odtwarzanie_3d.png)
![](img/ui_jasny_porownanie.png)

Błąd walidacji przy polu: ![](img/ui_po_formularz_blad.png)

Odtwarzanie erupcji Etny (krok 60, płynna lawa świeci): ![](img/ui_po_odtwarzanie_3d.png)

## 9. Wyniki kontroli

Sprawdzone 15.10.2026 (Windows 11, Chromium z Playwright 1440×900, GPU: RTX 4070 Laptop przez ANGLE/D3D11).

**Testy.** `python -m pytest gui\tests`: **100 passed** (dwa kolejne przebiegi; w pierwszym przebiegu po zmianach
1 failed: `test_pinning_to_cpu`, wyścig w istniejącym teście: zadanie 30 kroków potrafi się skończyć, zanim worker
przypnie proces, `_pin_process()` zwraca wtedy „proces mógł się już zakończyć”; kod backendu bez zmian, osobno test
przechodzi 3/3). `ctest --preset msvc-release`: **12/12** (silnik bez zmian). `python gui\tests\screenshots.py`
(motyw ciemny, całe scenariusze: interfejs, kolejka i seria, prawdziwy teren): bez błędów i ostrzeżeń konsoli JS.

**Kontrast tekstu (WCAG 2.1, AA = 4,5:1)**: `python gui\tests\palette_check.py`, kolory czytane z `style.css`:

| para | motyw ciemny | motyw jasny |
|---|---|---|
| tekst główny / karta | 14,1:1 | 16,1:1 |
| tekst główny / tło strony | 15,3:1 | 14,6:1 |
| tekst drugorzędny / karta | 6,6:1 | 6,9:1 |
| tekst drugorzędny / przycisk | 5,8:1 | 5,9:1 |
| tekst wyciszony / karta | 4,7:1 | 4,8:1 |
| tekst w kolorze lawy / karta | 7,4:1 | 5,4:1 |
| tekst na przycisku lawy (pomarańczowy / żółty koniec gradientu) | 6,1:1 / 10,3:1 | 6,1:1 / 10,3:1 |
| OK / ostrzeżenie / błąd / informacja na karcie | 8,3 / 9,2 / 6,8 / 8,1 | 5,1 / 5,6 / 5,4 / 6,2 |
| podpisy osi 2D / tło podglądu | 10,8:1 | 7,3:1 |

| obrys fokusu klawiatury / karta, przycisk (próg 3:1) | 9,4:1 / 8,3:1 | 4,9:1 / 4,2:1 |

Wszystkie pary tekstu ≥ 4,5:1. Fokus klawiatury: obrys 2 px `--focus`: w motywie ciemnym żółty żar `#ffb02e`, w jasnym
`#c2410c` (żółty żar na jasnej karcie miałby tylko 1,7:1; poprawione po tej kontroli).

**Daltonizm.** Ten sam skrypt rysuje próbki w Chromium z emulacją DevTools (`Emulation.setEmulatedVisionDeficiency`),
odczytuje kolory ze zrzutu i liczy najmniejszą odległość ΔE (OKLab ×100; ≥ 8 dobrze, 6–8 na granicy):

| widzenie | typ komórki, motyw ciemny | typ komórki, motyw jasny | kratery 1–3 | 1–5 | 1–7 | 1–10 | krater vs skała / bazalt |
|---|---|---|---|---|---|---|---|
| normalne | 19,7 (skała–bazalt) | 16,3 (powietrze–skała) | 29,0 | 16,8 | 10,4 | 7,0 | 11,8 |
| protanopia | 10,4 (skała–lawa) | 16,7 (powietrze–skała) | 27,1 | 13,2 | 11,7 | 5,4 | 8,9 |
| deuteranopia | 16,5 (skała–lawa) | 14,9 (skała–lawa) | 22,3 | 14,7 | 7,7 | 4,5 | 9,9 |
| tritanopia | 19,8 (skała–bazalt) | 16,2 (powietrze–skała) | 26,6 | 14,0 | 8,5 | 2,2 | 3,8 |
| achromatopsja | 8,0 (skała–lawa) | 11,9 (skała–lawa) | 12,2 | 2,3 | 1,6 | 1,0 | 0,3 |

![Paleta komórek w emulacji daltonizmu Chromium](img/ui_paleta_daltonizm.png)

Wnioski: cztery typy komórek są rozróżnialne przy każdym rodzaju daltonizmu, także przy całkowitym braku widzenia
barw (różnią się jasnością). Do 5 kraterów kolory są rozróżnialne przy proto- i deuteranopii (najczęstsze, ~8%
mężczyzn), do 7 na granicy; przy tritanopii (~0,01%) blisko siebie są niebieskie sloty 8 i 10 i jeden niebieski
krater względem bazaltu. Kolory kraterów nie niosą informacji samodzielnie: legenda ma numery, podpowiedź komórki
podaje `flowId`, granice ziaren można włączyć.

**Rozdzielczości.** `ui_shots.py` dla wszystkich zakładek (+ odtwarzanie 2D/3D) przy 1280×720 i 1920×1080 w obu
motywach, 1024×576 przy `device_scale_factor` 1,25 (= 1280×720 ze skalowaniem Windows 125%) i 1093×614 przy 1,25
(= 1366×768, 125%): **brak poziomego przewijania** (szerokość dokumentu = szerokość okna), brak błędów JS. Przed zmianą
przy 1024 px dokument miał 1280 px. Przy 1024×576 podgląd 3D z paskiem odtwarzania mieści się w oknie razem z linią
stanu; formularz i seria: jedna kolumna sekcji z panelem szacunku po prawej.

**Płynność odtwarzania (FPS)**: `python gui\tests\ui_shots.py --fps [--uncapped]`: odtwarzanie `etna_real`
(285 kroków) w widoku 3D, każdy krok jako osobna klatka, 1440×900. Stary i nowy frontend mierzone **na przemian**,
3 serie × 3 przebiegi (mediana z 9; w tle działało narzędzie producenta laptopa obciążające CPU, więc wartości bez limitu są zaszumione):

| widok | FPS z synchronizacją ekranu (60 Hz): przed → po | czas klatki JS [ms]: przed → po | FPS bez limitu klatek: przed → po |
|---|---|---|---|
| powierzchnia | 60,0 → 60,0 | 10,4 → 10,7 | 83,7 → 84,4 |
| woksele | 60,0 → 60,0 | 1,5 → 1,3 | 334 → 304 (−9%; zakres 288–357 → 249–326) |

Na ekranie płynność się nie zmieniła (60 FPS w obu widokach, czas klatki JS bez zmian). Test „bez limitu klatek”
(`--disable-gpu-vsync --disable-frame-rate-limit`) pokazuje zapas: powierzchnia bez zmian, woksele ~9% mniej, wciąż
5× powyżej odświeżania ekranu. Przy pierwszym pomiarze woksele spadły do ~230 FPS; ślad wydajności Chromium wskazał
5× droższą rasteryzację strony w każdej klatce. Przyczyny i poprawki (bez zmiany logiki odtwarzania):
legenda była budowana od nowa w każdej klatce (tak było już przed zmianą wyglądu, ale w nowym układzie przemalowanie panelu
kosztuje więcej); teraz `showLegend()` podmienia ją tylko przy zmianie; linia stanu: `setText()` tylko przy zmianie;
przycisk Odtwórz dostawał nowy element SVG przy każdym ruchu suwaka, teraz tylko przy zmianie stanu;
pasek odtwarzania, legenda i linia stanu mają `contain: layout paint`. Shader „żaru” i przezroczysty canvas nie
wpływały mierzalnie na wynik (sprawdzone osobno).

## 10. Co świadomie zostało bez zmian

- Silnik, reguły CA/MC, API backendu, formaty plików, logika odtwarzania i próbkowania danych.
- Nazwy zakładek, przycisków, pól (`id`, `data-*`, `name`): testy, `screenshots.py`, `run_ca_vs_mc.py` i dokumentacja
  działają bez zmian. Zmienił się tylko wygląd: przyciski z ikonami (np. „▶ Odtwórz” = ikona + „Odtwórz”,
  „+ dodaj parametr” = ikona plusa + „dodaj parametr”), checkboxy jako przełączniki, wybór osi i widoku jako segmenty.
- **`tools/plot_slice.py` i obrazki ze skryptów (wcześniejsze dokumenty: `img/test_2d_*`, `lava_mc_*`, `mc_full_*`,
  `heightmap_*`, `classic_ref_*`, `etna_3d_*` itd.) mają starą paletę** (powietrze `#fcfcfb`, skała `#c3c2b7`, lawa
  `#eb6834`, bazalt `#2a78d6`, temperatura „Oranges”) i nie są odtwarzane. Wspólny z GUI jest tylko kolor kryształu MC.
- Kolor kryształu MC (`hashColor`), mapa hipsometryczna panelu kraterów, położenie kamery 3D, układ i treść formularza.
- Wykresy `docs/img/ca_vs_mc.png`, `profile_*.png` (skrypty Pythona) bez zmian.
