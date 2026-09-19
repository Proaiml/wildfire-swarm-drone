@echo off
cd /d "%~dp0"
title PyreSwarm - Otonom Suru Drone Gorev Kontrol Merkezi
color 0A
cls

echo ===============================================================================
echo     PYRESWARM: OTONOM YANGIN TESPIT VE 3D-PSO SURU DRONE SISTEMI
echo ===============================================================================
echo  [+] Yapay Zeka: YOLOv8 best.pt (Yangin ve Duman)
echo  [+] Planlama: Kapasite bazli sektorler ve kanit odakli PSO
echo  [+] Calisma: Simulator, gonullu pilot rehberligi, MAVLink telemetri
echo  [+] Yetenekler: Alan Kapatma Sihirbazi ve Dinamik Vatandas Katilimi
echo ===============================================================================
echo.
echo [>>] Gorev Kontrol Istasyonu (GCS) Baslatiliyor...
echo [>>] Web Arayuzu: http://localhost:8000
echo.

if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe" (
    "%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe" run.py
) else if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" run.py
) else (
    python run.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Sistem durdu. Hata Kodu: %ERRORLEVEL%
    pause
)
