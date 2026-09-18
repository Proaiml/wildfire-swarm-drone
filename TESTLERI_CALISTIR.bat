@echo off
chcp 65001 >nul
title PyreSwarm - Kapsamlı Test Paketi
color 0B

cls
echo ===============================================================================
echo     🧪 PYRESWARM: 23 BİRİM VE ENTEGRASYON TESTİ KOŞTURULUYOR 🧪
echo ===============================================================================
echo.

set PYTHON_EXE=python
if exist "C:\Users\İlhan\AppData\Local\Programs\Python\Python311\python.exe" (
    set PYTHON_EXE="C:\Users\İlhan\AppData\Local\Programs\Python\Python311\python.exe"
) else if exist ".venv\Scripts\python.exe" (
    set PYTHON_EXE=".venv\Scripts\python.exe"
)

%PYTHON_EXE% -m pytest tests/ -v

echo.
echo ===============================================================================
echo  Tüm testler tamamlandı. Kapatmak için bir tuşa basın...
echo ===============================================================================
pause >nul
