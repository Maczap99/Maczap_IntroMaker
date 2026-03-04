# 🎬 Maczap IntroMaker

> **Desktop-App zur Erstellung professioneller Countdown-Intro-Videos — mit eigenen Schriftarten, Hintergrundmusik, Bild-Slider, Abschluss-Bild und flüssigen Überblendungseffekten.**

Gebaut mit Python + PyQt5. Rendering direkt über OpenCV und PIL, mit optionalem FFmpeg-Support für Audio-Mixing.

---

## ✨ Features

- **Countdown-Timer** — konfigurierbare Dauer (1–120 Min.), zentriert mit eigener Schriftart und Farbe
- **Untertitel** — optionaler Text unterhalb des Timers mit unabhängiger Schriftgröße und Farbe
- **Hintergrund** — Video-Loop, statisches Bild oder einfaches Weiß
- **Bild-Slider** — Bilder zwischen Countdown-Abschnitten einblenden, mit konfigurierbarem Timing und Loop-Verhalten
- **Hintergrundmusik** — MP3 / WAV / OGG mit Loop und Fade-out (erfordert FFmpeg)
- **Abschluss-Bild** — optionaler Slide nach dem Timer mit eigenem Text, Schriftart, Farbe und Hintergrundbild
- **Fade-Effekte** — Fade-in aus Schwarz am Start, Fade-out zu Schwarz am Ende, Crossfade zwischen Timer und Bildern
- **Eigene Schriftarten** — beliebige `.ttf` / `.otf` Fonts aus `assets/fonts/`, mit Live-Vorschau
- **Hell- & Dunkel-Modus** — vollständiges UI-Theming mit persistenten Einstellungen
- **Mehrsprachig** — Deutsch, Englisch und Russisch, umschaltbar in den Einstellungen (gilt ab Neustart)
- **Einstellungsseite** — alle Timing-, Fade- und Slider-Parameter übersichtlich konfigurierbar

---

## 🖥️ Screenshots

> *(Eigene Screenshots hier einfügen)*

| Hauptansicht | Einstellungen |
|---|---|
| `screenshots/standard.png` | `screenshots/advanced.png` |

---

## 🚀 Schnellstart

### Voraussetzungen

- Python 3.10+
- FFmpeg (optional, für Audio-Mixing — `ffmpeg.exe` unter `assets/bin/` ablegen)

### Abhängigkeiten installieren

```bash
pip install -r config/requirements.txt
```

### Starten

```bash
cd scripts
python main.py
```

---

## 📦 EXE erstellen (Windows)

```
build\build.bat
```

Das Skript:
1. Installiert alle Abhängigkeiten via pip
2. Bündelt alles in eine einzelne `.exe` mit PyInstaller
3. Gibt die fertige Datei unter `dist\IntroMaker.exe` aus

> `assets/bin/ffmpeg.exe` muss vorhanden sein, wenn Audio-Support mit eingebunden werden soll.

---

## 📁 Projektstruktur

```
IntroMaker/
├── assets/
│   ├── bin/                # ffmpeg.exe (optional, nicht enthalten)
│   ├── fonts/              # Eigene .ttf / .otf Schriftarten
│   └── pictures/           # Icons, Logos, Splash-Bilder
├── build/
│   └── build.bat           # PyInstaller Build-Skript
├── config/
│   └── requirements.txt
├── lang/
│   ├── de.json             # Deutsch
│   ├── en.json             # Englisch
│   └── ru.json             # Russisch
├── scripts/
│   ├── main.py             # Hauptfenster & UI
│   ├── video_generator.py  # Frame-Rendering & FFmpeg-Pipeline
│   ├── font_picker.py      # Schriftart-Auswahl mit Live-Vorschau
│   ├── splash.py           # Animierter Splash-Screen
│   ├── config_manager.py   # Einstellungen laden/speichern/zurücksetzen
│   ├── lang_manager.py     # Mehrsprachigkeit (i18n)
│   └── styles.py           # Hell-/Dunkel-Theme Stylesheets
└── README.md
```

---

## ⚙️ Einstellungen

Alle Einstellungen werden automatisch zwischen Sitzungen gespeichert und können auf der **Einstellungsseite** (⚙️-Button im Header) manuell gespeichert oder zurückgesetzt werden.

| Einstellung | Beschreibung |
|---|---|
| Timer-Dauer | Gesamtlänge des Countdown-Videos (1–120 Min.) |
| Hintergrund | Videodatei, Bilddatei oder reines Weiß |
| Musik | Audiodatei mit optionalem Loop und Fade-out (erfordert FFmpeg) |
| Slider-Bilder | Bilder zwischen Countdown-Abschnitten |
| Schrift & Farben | Eigene Schriftart, Timer-Farbe, Untertitel-Farbe |
| Untertitel | Optionaler Text unter dem Timer mit Größen- und Farbsteuerung |
| Untertitel-Abstand | Extra-Abstand zwischen Timer und Untertitel in Zeilenhöhen |
| Abschluss-Bild | Slide nach dem Timer mit Text, Schriftart, Farbe und Hintergrundbild |
| Fade In / Out | Schwarzblende am Start und Ende mit konfigurierbarer Dauer |
| Slider-Timing | Wann Bilder erscheinen, wie lange, Pause dazwischen |
| Slider-Loop | Bilder bis Zonen-Ende wiederholen oder jeden einmal zeigen |
| Übergänge | Crossfade-Dauer zwischen Timer und Slider-Bildern |
| Musik-Fade-out | Dauer des Musik-Fade am Videoende |
| Sprache | Deutsch / Englisch / Russisch — wirkt ab dem nächsten Start |

Einstellungen werden gespeichert unter:
```
%APPDATA%\MaczapIntroMaker\settings.json
```

---

## 🌐 Sprachen

Die App unterstützt aktuell drei Sprachen:

| Code | Sprache |
|---|---|
| `de` | Deutsch (Standard) |
| `en` | English |
| `ru` | Русский |

Die Sprache wird in den **Einstellungen** gewählt und gilt ab dem nächsten Programmstart. Weitere Sprachen können einfach durch Ablegen einer neuen `xx.json` im `lang/`-Ordner hinzugefügt werden — sie werden automatisch erkannt.

---

## 🎵 Audio (FFmpeg)

Audio-Mixing erfordert `ffmpeg.exe` unter:

```
assets/bin/ffmpeg.exe
```

Einen statischen Build gibt es auf [ffmpeg.org](https://ffmpeg.org/download.html) oder [gyan.dev](https://www.gyan.dev/ffmpeg/builds/).

Wird FFmpeg nicht gefunden, wird das Video ohne Audio gerendert.

---

## 🛠️ Tech Stack

| Bibliothek | Zweck |
|---|---|
| `PyQt5` | UI-Framework |
| `OpenCV` (`cv2`) | Frame-Rendering & Video-Capture |
| `Pillow` (`PIL`) | Text-Rendering, Font-Handling |
| `NumPy` | Frame-Compositing |
| `FFmpeg` | Audio-Mixing (optional, extern) |
| `PyInstaller` | EXE-Bundling |

---

## 📄 Lizenz

MIT — frei verwendbar, Nennung erwünscht.