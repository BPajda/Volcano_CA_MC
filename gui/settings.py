"""Ustawienia GUI: położenie silnika (engine.exe), katalogi configów i wyników, adres serwera.

Kolejność (od najważniejszej):
  1. zmienne środowiskowe: VOLCANO_ENGINE (ścieżka do programu), VOLCANO_GUI_PORT, VOLCANO_GUI_WORKERS,
  2. plik gui/settings.json (opcjonalny), np. {"engine": "build/Release/engine.exe", "port": 8000, "workers": 1,
     "pinCpus": [2, 4]} (pinCpus — procesory logiczne do przypinania zadań, etap 5),
  3. auto-wykrycie programu w katalogach budowania presetów CMake (Release przed Debug).

Ścieżki względne są liczone od katalogu projektu (volcano-ca-mc). Serwer nasłuchuje wyłącznie
na 127.0.0.1 — GUI uruchamia programy i zapisuje pliki, więc nie może być dostępne z sieci.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Katalog projektu: gui/ leży bezpośrednio w volcano-ca-mc/.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SETTINGS_FILE = Path(__file__).resolve().parent / "settings.json"

HOST = "127.0.0.1"  # celowo stałe — patrz opis modułu

# Kandydaci na program silnika (względem katalogu projektu), w kolejności preferencji.
# Release przed Debug: Debug jest kilka razy wolniejszy (docs/profilowanie.md, punkt 3.4).
_EXE = ".exe" if sys.platform == "win32" else ""
ENGINE_CANDIDATES = [
    f"build/Release/engine{_EXE}",                 # preset msvc-release (Visual Studio)
    f"build-msvc-release/Release/engine{_EXE}",
    f"build-msvc-release/engine{_EXE}",
    f"build-gcc-release/bin/engine{_EXE}",         # preset gcc-release (Linux/WSL)
    f"build/bin/engine{_EXE}",
    f"build/engine{_EXE}",
    f"build/Debug/engine{_EXE}",
    f"build-gcc-debug/bin/engine{_EXE}",
]


@dataclass
class Settings:
    """Ustawienia jednej instancji GUI (testy tworzą własne, z katalogami tymczasowymi)."""

    root: Path = PROJECT_ROOT
    engine: Path | None = None          # None = silnik nie znaleziony (GUI działa, ale nie uruchomi symulacji)
    engine_source: str = "brak"         # skąd wzięto ścieżkę: env / settings.json / auto
    configs_dir: Path = PROJECT_ROOT / "configs"
    results_dir: Path = PROJECT_ROOT / "results"
    host: str = HOST
    port: int = 8000
    workers: int = 1                    # domyślna liczba równoległych zadań (zmieniana w GUI, etap 5)
    # Procesory logiczne do przypięcia procesów silnika (worker i -> pin_cpus[i mod n]). Domyślnie rdzenie P
    # i9-13900HX z pomiarów etapu 3 (logiczne 0–15 to rdzenie P z HT: 2, 4, … — co drugi, bez 0, który
    # obsługuje najwięcej przerwań). Na innym komputerze ustaw "pinCpus" w gui/settings.json.
    pin_cpus: list[int] = field(default_factory=lambda: [2, 4, 6, 8, 10, 12, 14])
    warnings: list[str] = field(default_factory=list)

    @property
    def gui_configs_dir(self) -> Path:
        """Configi utworzone z GUI: configs/gui/<id>.json."""
        return self.configs_dir / "gui"

    @property
    def gui_results_dir(self) -> Path:
        """Foldery wyników zadań z GUI: results/gui/<id>/ (+ jobs.json z listą zadań)."""
        return self.results_dir / "gui"

    @property
    def series_configs_dir(self) -> Path:
        """Serie z GUI (etap 5): configs/gui/series/<seriesId>/NN_<opis>.json + series.json."""
        return self.gui_configs_dir / "series"

    @property
    def series_results_dir(self) -> Path:
        """Wyniki serii z GUI: results/gui/series/<seriesId>/NN_<opis>/ + series.json."""
        return self.gui_results_dir / "series"

    @property
    def heightmaps_dir(self) -> Path:
        """Mapy wysokości terenu (CSV) — przykładowe i zaimportowane z GUI: configs/heightmaps/."""
        return self.configs_dir / "heightmaps"

    @property
    def jobs_file(self) -> Path:
        return self.gui_results_dir / "jobs.json"


def find_engine(root: Path) -> Path | None:
    """Pierwszy istniejący program z listy ENGINE_CANDIDATES (albo None)."""
    for rel in ENGINE_CANDIDATES:
        p = root / rel
        if p.is_file():
            return p
    return None


def _resolve(root: Path, value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else (root / p)


def load_settings(root: Path = PROJECT_ROOT, settings_file: Path | None = SETTINGS_FILE) -> Settings:
    """Ustawienia z env, gui/settings.json i auto-wykrycia (opis modułu)."""
    s = Settings(root=root, configs_dir=root / "configs", results_dir=root / "results")
    data: dict = {}
    if settings_file is not None and settings_file.is_file():
        try:
            data = json.loads(settings_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            s.warnings.append(f"Nie można wczytać {settings_file}: {e}")

    if data.get("configsDir"):
        s.configs_dir = _resolve(root, data["configsDir"])
    if data.get("resultsDir"):
        s.results_dir = _resolve(root, data["resultsDir"])
    s.port = int(os.environ.get("VOLCANO_GUI_PORT", data.get("port", 8000)))
    s.workers = max(1, int(os.environ.get("VOLCANO_GUI_WORKERS", data.get("workers", 1))))
    if isinstance(data.get("pinCpus"), list) and all(isinstance(c, int) and c >= 0 for c in data["pinCpus"]):
        s.pin_cpus = list(data["pinCpus"]) or s.pin_cpus

    env_engine = os.environ.get("VOLCANO_ENGINE")
    if env_engine:
        s.engine, s.engine_source = _resolve(root, env_engine), "zmienna VOLCANO_ENGINE"
    elif data.get("engine"):
        s.engine, s.engine_source = _resolve(root, data["engine"]), "gui/settings.json"
    else:
        s.engine, s.engine_source = find_engine(root), "auto-wykrycie"
    if s.engine is None:
        s.warnings.append("Nie znaleziono programu engine. Zbuduj silnik (cmake --build --preset msvc-release) "
                          "albo podaj ścieżkę w gui/settings.json / zmiennej VOLCANO_ENGINE.")
    elif not s.engine.is_file():
        s.warnings.append(f"Program silnika nie istnieje: {s.engine} ({s.engine_source})")
        s.engine = None
    elif "debug" in str(s.engine).lower():
        s.warnings.append(f"Używany jest build Debug ({s.engine}): symulacje będą kilka razy wolniejsze.")
    return s
