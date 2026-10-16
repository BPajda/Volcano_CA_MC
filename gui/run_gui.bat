@echo off
rem Start GUI symulacji wulkanu (podwojne klikniecie). Serwer: http://127.0.0.1:8000 (tylko ten komputer).
rem Pierwsze uruchomienie: python -m pip install -r gui\requirements.txt
cd /d "%~dp0.."
python -c "import fastapi, uvicorn, numpy, PIL" 2>nul
if errorlevel 1 (
    echo Instaluje pakiety GUI: fastapi, uvicorn, numpy, pillow ...
    python -m pip install --user -r gui\requirements.txt
)
python -m gui %*
if errorlevel 1 pause
