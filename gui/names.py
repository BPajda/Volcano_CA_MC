"""Bezpieczne nazwy plików i folderów z tekstu użytkownika — wspólne dla zadań (jobs.py), serii (series.py)
i map wysokości (heightmap.py). Moduł bez zależności (używa go też tools/make_series.py)."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime

# Litery spoza ASCII zamieniane ręcznie (ł nie ma rozkładu NFKD).
_TRANSLIT = str.maketrans({"ł": "l", "Ł": "L"})


def safe_name(name: str, max_len: int = 40, fallback: str = "zadanie") -> str:
    """Nazwa nadana przez użytkownika -> fragment nazwy pliku: tylko [A-Za-z0-9_-].

    Polskie litery są transliterowane (ą -> a), separatory ścieżek, kropki i spacje zamieniane na _,
    więc wynik nigdy nie wyjdzie poza katalog (np. '..\\..\\x' -> 'x')."""
    text = unicodedata.normalize("NFKD", str(name).translate(_TRANSLIT))
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^A-Za-z0-9_-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_-")
    return text[:max_len].strip("_-") or fallback


def stamp() -> str:
    """Znacznik czasu do identyfikatorów zadań i serii: RRRRMMDD-GGMMSS."""
    return f"{datetime.now():%Y%m%d-%H%M%S}"
