@echo off
title Maczap IntroMaker - Builder

REM -------------------------------
REM Arbeitsverzeichnis auf Projekt-Root setzen
REM -------------------------------
cd /d "%~dp0\.."

echo.
echo  ================================================
echo    Maczap IntroMaker  --  EXE Builder
echo  ================================================

REM -------------------------------
REM 1/3: Installiere Abhängigkeiten
REM -------------------------------
echo [1/3] Installiere Abhaengigkeiten...
pip install -r config\requirements.txt
if errorlevel 1 (
    echo FEHLER bei pip install!
    pause & exit /b 1
)

REM -------------------------------
REM 2/3: Erstelle EXE
REM -------------------------------
echo [2/3] Erstelle EXE (1-3 Minuten)...

python -m PyInstaller --onefile --windowed ^
  --name "IntroMaker" ^
  --distpath "dist" ^
  --workpath "build\_pyinstaller_tmp" ^
  --specpath "build" ^
  --add-data "%CD%\assets;assets" ^
  --add-data "%CD%\scripts\font_picker.py;." ^
  --add-data "%CD%\scripts\video_generator.py;." ^
  --add-data "%CD%\scripts\splash.py;." ^
  --add-data "%CD%\scripts\config_manager.py;." ^
  scripts\main.py

if errorlevel 1 (
    echo FEHLER beim Erstellen der EXE!
    pause & exit /b 1
)

REM -------------------------------
REM 3/3: Aufräumen
REM -------------------------------
echo [3/3] Aufraeumen...
if exist "build\_pyinstaller_tmp" rmdir /s /q "build\_pyinstaller_tmp"

echo.
echo  ================================================
echo   FERTIG!   dist\IntroMaker.exe
echo  ================================================
pause