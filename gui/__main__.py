"""Start GUI: `python -m gui` (z katalogu volcano-ca-mc) -> serwer na http://127.0.0.1:8000 + przeglądarka.

Opcje: --port N (domyślnie 8000 albo z gui/settings.json / VOLCANO_GUI_PORT), --no-browser.
Serwer słucha wyłącznie na 127.0.0.1 (patrz gui/settings.py). Zatrzymanie: Ctrl+C w oknie konsoli.
"""

from __future__ import annotations

import argparse
import socket
import sys
import threading
import webbrowser


def main() -> int:
    try:
        import uvicorn
    except ImportError:
        print("Brak pakietów GUI. Zainstaluj je poleceniem:\n    python -m pip install -r gui/requirements.txt")
        return 1
    from .app import create_app
    from .settings import load_settings

    settings = load_settings()
    parser = argparse.ArgumentParser(prog="python -m gui", description="GUI symulacji wulkanu (CA + MC)")
    parser.add_argument("--port", type=int, default=settings.port, help="port HTTP (domyślnie %(default)s)")
    parser.add_argument("--no-browser", action="store_true", help="nie otwieraj przeglądarki")
    args = parser.parse_args()
    settings.port = args.port

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex((settings.host, settings.port)) == 0:
            url = f"http://{settings.host}:{settings.port}/"
            print(f"Port {settings.port} jest zajęty — GUI już działa? Otwieram {url}\n"
                  f"(inny port: python -m gui --port 8001)")
            if not args.no_browser:
                webbrowser.open(url)
            return 1

    url = f"http://{settings.host}:{settings.port}/"
    print(f"GUI symulacji wulkanu: {url}  (Ctrl+C — zatrzymanie)")
    print(f"Silnik: {settings.engine or 'NIE ZNALEZIONO'} ({settings.engine_source})")
    for w in settings.warnings:
        print(f"Ostrzeżenie: {w}")
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
