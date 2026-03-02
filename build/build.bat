@echo off
title Maczap IntroMaker - Builder
cd /d "%~dp0.."

echo.
echo  ================================================
echo    Maczap IntroMaker  --  EXE Builder
echo  ================================================
echo.

echo [1/3] Installiere Abhaengigkeiten...
pip install -r config\requirements.txt
if errorlevel 1 (
    echo FEHLER bei pip install!
    pause & exit /b 1
)

echo.
echo [2/3] Erstelle EXE (1-3 Minuten)...
pyinstaller --onefile --windowed ^
  --name "IntroMaker" ^
  --distpath "dist" ^
  --workpath "build\_pyinstaller_tmp" ^
  --specpath "build" ^
  --add-data "assets;assets" ^
  --add-data "scripts/font_picker.py;." ^
  --add-data "scripts/video_generator.py;." ^
  --add-data "scripts/splash.py;." ^
  scripts\main.py

echo.
echo [3/3] Aufraeumen...
if exist "build\_pyinstaller_tmp" rmdir /s /q "build\_pyinstaller_tmp"

echo.
echo  ================================================
echo   FERTIG!   dist\IntroMaker.exe
echo  ================================================
pause