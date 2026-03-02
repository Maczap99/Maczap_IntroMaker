# Maczap_IntroMaker# 🎬 Maczap IntroMaker

Erstelle professionelle Countdown-Intros mit Hintergrundvideo, Musik,
Bilder-Slider und individuellen Schriftarten — direkt als MP4 exportiert.

---

## 📁 Projektstruktur
```
Maczap_IntroMaker/
├── assets/
│   ├── fonts/          → TTF/OTF Schriftarten (werden automatisch geladen)
│   └── pictures/       → logo.png (Splash Screen)
├── scripts/
│   ├── main.py         → Hauptprogramm & GUI
│   ├── video_generator.py → Video-Rendering Engine
│   ├── font_picker.py  → Font-Auswahl Widget
│   └── splash.py       → Splash Screen
├── build/
│   └── build.bat       → EXE bauen (Doppelklick)
├── config/
│   └── requirements.txt
├── dist/               → fertige EXE (nach Build)
├── README.md
└── .gitignore
```

---

## ⚙️ Voraussetzungen

| Tool | Version | Download |
|------|---------|----------|
| Python | 3.11+ | https://python.org |
| FFmpeg | 7.x+ | `winget install ffmpeg` oder https://www.gyan.dev/ffmpeg/builds/ |

> **Wichtig:** Bei Python-Installation "Add Python to PATH" anhaken!

---

## 🚀 Installation & Start

### Programm testen (ohne EXE)
```cmd
cd S:\Projekte\Maczap_IntroMaker
pip install -r config\requirements.txt
python scripts\main.py
```

### EXE bauen
`build\build.bat` doppelklicken → EXE erscheint in `dist\IntroMaker.exe`

---

## 🎬 Funktionen

- **Hintergrund** — Video (MP4, MOV …) oder Bild (JPG, PNG) oder einfach Weiß
- **Countdown-Timer** — frei wählbare Dauer (1–120 Minuten), zentriert & groß
- **Schriftarten** — alle TTF/OTF aus `assets/fonts/` mit Live-Vorschau
- **Bilder-Slider** — Bilder werden zwischen Countdown-Abschnitten eingeblendet
- **Fade-Übergänge** — sanfte Überblendungen zwischen Timer und Bildern
- **Hintergrundmusik** — MP3/WAV/OGG mit Loop und automatischem Fade-out
- **Fortschrittsanzeige** — Echtzeit-Fortschrittsbalken mit ETA und Frame-Zähler

---

## 🎵 FFmpeg (für Musik)

FFmpeg wird für das Einbetten von Hintergrundmusik benötigt.
Ohne FFmpeg funktioniert alles — nur ohne Ton.
```powershell
winget install ffmpeg
```

---

## 📝 Lizenz

Privates Projekt — alle Rechte vorbehalten.