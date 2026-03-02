@echo off
title Intro Maker Builder
echo.
echo  ================================================
echo    Intro Maker  --  EXE Builder
echo  ================================================

pip install -r requirements.txt

pyinstaller --onefile --windowed ^
  --name "IntroMaker" ^
  --add-data "assets;assets" ^
  --add-data "font_picker.py;." ^
  --add-data "video_generator.py;." ^
  --add-data "splash.py;." ^
  main.py

echo.
echo  FERTIG!  dist\IntroMaker.exe
pause