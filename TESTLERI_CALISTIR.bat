@echo off
cd /d "%~dp0"
title PyreSwarm - Kapsamli Test Paketi
color 0B
cls

echo ===============================================================================
echo     PYRESWARM: BIRIM, ENTEGRASYON VE HUB REGRESYON TESTLERI
echo ===============================================================================
echo.

if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe" (
    "%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe" -m pytest tests/ -v
) else if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m pytest tests/ -v
) else (
    python -m pytest tests/ -v
)

echo.
echo ===============================================================================
echo  Tum testler tamamlandi. Kapatmak icin bir tusa basin...
echo ===============================================================================
pause >nul
