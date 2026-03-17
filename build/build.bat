@echo off
title Maczap IntroMaker - Builder
cd /d "%~dp0\.."
echo.
echo  ================================================
echo    Maczap IntroMaker  --  EXE Builder (PyQt5)
echo  ================================================
echo [1/3] Installiere Abhaengigkeiten...
pip install -r config\requirements.txt
if errorlevel 1 ( echo FEHLER bei pip install! & pause & exit /b 1 )
echo [2/3] Erstelle EXE...
python -m PyInstaller --onefile --windowed ^
  --name "IntroMaker" ^
  --icon "%CD%\assets\pictures\favicon.ico" ^
  --distpath "dist" ^
  --workpath "build\_pyinstaller_tmp" ^
  --specpath "build" ^
  --add-data "%CD%\assets;assets" ^
  --add-data "%CD%\lang;lang" ^
  --hidden-import "PyQt5.QtMultimedia" ^
  --hidden-import "PyQt5.QtMultimediaWidgets" ^
  scripts\main.py
if errorlevel 1 ( echo FEHLER beim Build! & pause & exit /b 1 )
echo [3/3] Aufraeumen...
if exist "build\_pyinstaller_tmp" rmdir /s /q "build\_pyinstaller_tmp"
echo.
echo  ================================================
echo   FERTIG!   dist\IntroMaker.exe
echo  ================================================
pause