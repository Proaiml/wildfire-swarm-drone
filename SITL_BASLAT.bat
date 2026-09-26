@echo off
cd /d "%~dp0"
title PyreSwarm - ArduPilot SITL surusu (test)
echo ===============================================================================
echo   GERCEK ARDUPILOT UCUS KODU (SITL) ILE SURU TESTI
echo   Gercek drone kullanmadan once hub'i burada deneyin.
echo ===============================================================================
set COUNT=%1
if "%COUNT%"=="" set COUNT=3
docker info >nul 2>&1
if errorlevel 1 (
  echo [!] Docker calismiyor. Docker Desktop'i acip tekrar deneyin.
  pause
  exit /b 1
)
docker image inspect pyreswarm-sitl >nul 2>&1
if errorlevel 1 (
  echo [>>] SITL imaji ilk kez derleniyor ^(10-20 dakika surer, bir kez yapilir^)...
  docker build -t pyreswarm-sitl tools\sitl || (pause & exit /b 1)
)
docker rm -f pyreswarm-sitl >nul 2>&1
docker run -d --name pyreswarm-sitl -p 5760-5800:5760-5800 -e COUNT=%COUNT% pyreswarm-sitl
echo.
echo [OK] %COUNT% ArduCopter SITL calisiyor. Hub'da: + Ekle ^> MAVLink otopilot
echo      Baglanti: tcp:127.0.0.1:5760 , tcp:127.0.0.1:5770 , tcp:127.0.0.1:5780 ...
echo      Tatbikat icin "Tatbikat sentetik kamerasi" kutusunu isaretleyin.
echo      Durdurmak icin: docker rm -f pyreswarm-sitl
pause
