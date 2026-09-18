@echo off
title PyreSwarm - Otonom Suru Drone Gorev Kontrol Merkezi
color 0A
cls

echo ===============================================================================
echo     PYRESWARM: OTONOM YANGIN TESPIT VE 3D-PSO SURU DRONE SISTEMI
echo ===============================================================================
echo  [+] Yapay Zeka: YOLOv8 best.pt (Yangin ve Duman)
echo  [+] Optimizasyon: 3D-PSO ve APF Carpisma Onleme
echo  [+] Donanim Destegi: Pixhawk, PX4, ArduPilot MAVLink ve Simulator
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
