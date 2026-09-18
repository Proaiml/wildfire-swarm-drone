@echo off
chcp 65001 >nul
title PyreSwarm - Otonom Sürü Drone Yangın Görev Kontrol Merkezi
color 0A

cls
echo ===============================================================================
echo     🔥 PYRESWARM: OTONOM YANGIN TESPİT & 3D-PSO SÜRÜ DRONE SİSTEMİ 🔥
echo ===============================================================================
echo  [+] Yapay Zeka: YOLOv8 (best.pt - Yangın & Duman)
echo  [+] Optimizasyon: 3D-PSO (Particle Swarm Optimization) & APF Çarpışma Önleme
echo  [+] Donanım Desteği: Pixhawk / PX4 / ArduPilot MAVLink & Yüksek Doğruluklu Simülatör
echo  [+] Yetenekler: Alan Kapatma Sihirbazı & Dinamik Vatandaş Drone Entegrasyonu
echo ===============================================================================
echo.

:: Python yorumlayıcısını belirle
set PYTHON_EXE=python
if exist "C:\Users\İlhan\AppData\Local\Programs\Python\Python311\python.exe" (
    set PYTHON_EXE="C:\Users\İlhan\AppData\Local\Programs\Python\Python311\python.exe"
) else if exist ".venv\Scripts\python.exe" (
    set PYTHON_EXE=".venv\Scripts\python.exe"
)

echo [>>] Python ortamı doğrulandı: %PYTHON_EXE%
echo [>>] Görev Kontrol İstasyonu (GCS) Web Arayüzü Başlatılıyor...
echo [>>] Web Arayüzü Adresi: http://localhost:8000
echo.

:: 2 saniye sonra varsayılan tarayıcıda otomatik aç
start "" timeout /t 2 /nobreak >nul & start http://localhost:8000

:: Ana uygulamayı çalıştır
%PYTHON_EXE% run.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Sistem beklenmeyen bir hata ile durdu. Hata Kodu: %ERRORLEVEL%
    pause
)
