"""Wywołania silnika C++ (engine.exe) z backendu GUI.

Backend niczego nie liczy sam — formularz budujemy z `engine --print-defaults`, config sprawdzamy
`engine --validate`, a symulację uruchamia JobManager poleceniem z `run_command()`. Dzięki temu
formularz, walidacja i uruchomienie zawsze zgadzają się z silnikiem (te same klucze, te same
komunikaty błędów po polsku).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from .settings import Settings

# Na Windows proces silnika nie otwiera okna konsoli.
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0


class EngineMissing(RuntimeError):
    """Brak programu silnika (nie zbudowany / zła ścieżka w ustawieniach)."""


class EngineClient:
    """Krótkie wywołania silnika: domyślny config i walidacja (bez symulacji)."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._defaults: dict | None = None

    def _exe(self) -> Path:
        if self.settings.engine is None:
            raise EngineMissing("Nie znaleziono programu engine — zbuduj silnik albo ustaw ścieżkę "
                                "w gui/settings.json / VOLCANO_ENGINE.")
        return self.settings.engine

    def _run(self, args: list[str], timeout: float = 30.0) -> subprocess.CompletedProcess:
        return subprocess.run([str(self._exe()), *args], cwd=self.settings.root, capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=timeout,
                              creationflags=CREATE_NO_WINDOW)

    def defaults(self) -> dict:
        """Pełny domyślny config (engine --print-defaults); wynik zapamiętany."""
        if self._defaults is None:
            p = self._run(["--print-defaults"])
            if p.returncode != 0:
                raise RuntimeError(f"engine --print-defaults: kod {p.returncode}: {p.stderr.strip()}")
            self._defaults = json.loads(p.stdout)
        return self._defaults

    def validate(self, config: dict, mc_from: Path | None = None) -> dict:
        """Walidacja configu silnikiem: {"ok": bool, "errors": [...], "warnings": [...]}.

        Config trafia do pliku tymczasowego (silnik czyta config tylko z pliku). Katalog roboczy
        silnika = katalog projektu, więc względne ścieżki (np. terrain.file) znaczą to samo co
        przy uruchomieniu zadania."""
        fd, tmp = tempfile.mkstemp(prefix="volcano_validate_", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            args = ["--validate", "--config", tmp]
            if mc_from is not None:
                args += ["--mc-from", str(mc_from)]
            p = self._run(args)
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass
        try:
            result = json.loads(p.stdout)
        except json.JSONDecodeError:
            # Błąd argumentów (kod 2) albo nieoczekiwany — komunikat ze stderr.
            msg = (p.stderr or p.stdout).strip() or f"engine --validate zakończył się kodem {p.returncode}"
            return {"ok": False, "errors": [msg], "warnings": []}
        result.setdefault("errors", [])
        result.setdefault("warnings", [])
        result["ok"] = bool(result.get("ok")) and p.returncode == 0
        return result

    def run_command(self, config_path: Path, out_dir: Path, mc_from: Path | None = None) -> list[str]:
        """Polecenie uruchomienia symulacji z raportem postępu (linie PROGRESS na stdout)."""
        cmd = [str(self._exe())]
        if mc_from is not None:
            cmd += ["--mc-from", str(mc_from)]
        cmd += ["--config", str(config_path), "--out", str(out_dir), "--progress"]
        return cmd
