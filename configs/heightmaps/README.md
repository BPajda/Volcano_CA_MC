# Mapy wysokości terenu (`terrain.type = "file"`)

Format czytany przez silnik (`engine/src/terrain/HeightmapLoader.cpp`): **ny wierszy × nx wartości**, wiersz k to y = k
(y = 0 — południe), kolumna i to x = i (x = 0 — zachód); wartość = wysokość terenu w komórkach (może być ułamkowa,
skała to z < h); separatory `,` `;` spacja, tabulator; wiersze zaczynające się od `#` są pomijane.
Ścieżka w configu: `configs/heightmaps/<nazwa>.csv` (względem katalogu projektu). Obraz `<nazwa>.png` — podgląd
w odcieniach szarości (biel = najwyżej, północ u góry).

| Mapa | Siatka | Skąd | Preset |
|---|---|---|---|
| `kaldera_wylom` | 100 × 100 (nz 45) | sztuczna — `tools/make_heightmaps.py` | `heightmap_kaldera.json` |
| `kanion` | 100 × 100 (nz 45) | sztuczna — `tools/make_heightmaps.py` | `heightmap_kanion.json` |
| `podwojny_wulkan` | 100 × 100 (nz 45) | sztuczna — `tools/make_heightmaps.py` | `heightmap_podwojny.json` |
| `etna` | 160 × 160 (nz 70), ~234 m/komórkę, 55 m w pionie | **prawdziwy teren** — `tools/fetch_dem.py` (2026-10-13) | `etna_real.json`, `etna_real_boczna.json` |
| `wezuwiusz` | 140 × 140 (nz 50), ~79 m/komórkę, 29 m w pionie | **prawdziwy teren** — `tools/fetch_dem.py` (2026-10-13) | `wezuwiusz_real.json` |

Mapy z prawdziwego terenu mają plik metadanych `<nazwa>.json` (bbox, zoom, kafelki, data pobrania, metry na komórkę
w poziomie i w pionie, przewyższenie, min/max wysokości, wzór komórka ↔ szerokość/długość geograficzna) — GUI pokazuje
z niego szer./dł. i wysokość w metrach pod kursorem. Odtworzenie / inny obszar:

```powershell
python tools\fetch_dem.py --name etna --bbox 37.58 14.80 37.92 15.22 --zoom 11 --nx 160 --ny 160 --nz 70 --description "Etna (Sycylia)"
python tools\fetch_dem.py --name wezuwiusz --bbox 40.77 14.36 40.87 14.49 --zoom 12 --nx 140 --ny 140 --nz 50 --description "Wezuwiusz z Monte Somma (Kampania)"
python tools\latlon_to_grid.py etna 37.751 14.993        # (szer., dł.) -> kolumna (x, y)
```

Opis metody i wyników: [docs/etap-6-prawdziwe-wulkany.md](../../docs/etap-6-prawdziwe-wulkany.md).

## Źródło danych i przypisanie (wymagane)

Mapy `etna` i `wezuwiusz` powstały z **AWS Terrain Tiles** (Tilezen / Mapzen „Terrain Tiles”, kafelki Terrarium PNG,
`https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png`), przepróbkowanych i przeskalowanych do
siatki symulacji. Dane łączą zbiory wielu dostawców; wymagane przypisanie wg dokumentacji Terrain Tiles
(<https://github.com/tilezen/joerd/blob/master/docs/attribution.md>):

```
* ArcticDEM terrain data DEM(s) were created from DigitalGlobe, Inc., imagery and
  funded under National Science Foundation awards 1043681, 1559691, and 1542736;
* Australia terrain data © Commonwealth of Australia (Geoscience Australia) 2017;
* Austria terrain data © offene Daten Österreichs – Digitales Geländemodell (DGM)
  Österreich;
* Canada terrain data contains information licensed under the Open Government
  Licence – Canada;
* Europe terrain data produced using Copernicus data and information funded by the
  European Union - EU-DEM layers;
* Global ETOPO1 terrain data U.S. National Oceanic and Atmospheric Administration
* Mexico terrain data source: INEGI, Continental relief, 2016;
* New Zealand terrain data Copyright 2011 Crown copyright (c) Land Information New
  Zealand and the New Zealand Government (All rights reserved);
* Norway terrain data © Kartverket;
* United Kingdom terrain data © Environment Agency copyright and/or database right
  2015. All rights reserved;
* United States 3DEP (formerly NED) and global GMTED2010 and SRTM terrain data
  courtesy of the U.S. Geological Survey.
```

Dla obszarów Etny i Wezuwiusza dane pochodzą przede wszystkim z SRTM (U.S. Geological Survey) i EU-DEM (Copernicus,
Unia Europejska); morze — ETOPO1 (NOAA). Mapy są danymi pochodnymi (wygładzone, przepróbkowane do 234 m / 79 m na komórkę,
wysokości przeliczone na komórki z przewyższeniem ×4,2 / ×2,7) — nie nadają się do celów innych niż ilustracja symulacji.
