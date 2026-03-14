# 🎬 Maczap IntroMaker

> **Desktop-App zur Erstellung professioneller Countdown-Intro-Videos — mit eigenen Schriftarten, Hintergrundmusik, Bild-Slider, Abschluss-Bild und flüssigen Überblendungseffekten.**

Gebaut mit Python + PyQt5. Rendering direkt über OpenCV und PIL, mit optionalem FFmpeg-Support für Audio-Mixing.

---

## ✨ Features

- **Countdown-Timer** — konfigurierbare Dauer (1–120 Min.), zentriert mit eigener Schriftart und Farbe
- **Untertitel** — optionaler Text unterhalb des Timers mit unabhängiger Schriftgröße, Farbe und Abstand
- **Hintergrund** — Video-Loop, statisches Bild oder konfigurierbare Fallback-Farbe (Standard: Schwarz)
- **Bild-Slider** — Bilder und PDFs zwischen Countdown-Abschnitten einblenden, mit konfigurierbarem Timing, Loop-Verhalten und Füllfarbe für nicht-16:9-Formate
- **Hintergrundmusik** — MP3 / WAV / OGG mit Loop und Fade-out (erfordert FFmpeg)
- **Abschluss-Bild** — optionaler Slide nach dem Timer mit eigenem Text, Schriftart, Farbe und Hintergrundbild
- **Fade-Effekte** — Fade-in aus Schwarz am Start, Fade-out zu Schwarz am Ende, Crossfade zwischen Timer und Bildern
- **Eigene Schriftarten** — beliebige `.ttf` / `.otf` Fonts aus `assets/fonts/`, mit Live-Vorschau
- **Echtzeit-Vorschau** — generiert einen Vorschau-Frame mit Hintergrund, Schriftart und Farbe vor dem Rendern
- **Render abbrechen** — laufendes Rendering jederzeit abbrechbar; unfertige Dateien werden automatisch gelöscht
- **Hardware-Encoding** — automatische Erkennung von NVIDIA (`h264_nvenc`) und AMD (`h264_amf`); fällt auf `libx264` zurück wenn keine GPU verfügbar ist
- **Töne** — optionale Audio-Benachrichtigung bei erfolgreichem Abschluss oder Fehler
- **Hell- & Dunkel-Modus** — vollständiges UI-Theming mit persistenten Einstellungen
- **Mehrsprachig** — Deutsch, Englisch und Russisch, umschaltbar in den Einstellungen
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
│   ├── pictures/           # Icons, Logos, Splash-Bilder
│   └── sounds/             # success.mp3, error.mp3 (optional)
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
| Hintergrund | Videodatei, Bilddatei oder Fallback-Farbe (Standard: Schwarz) |
| Musik | Audiodatei mit optionalem Loop und Fade-out (erfordert FFmpeg) |
| Slider-Bilder | Bilder und PDFs zwischen Countdown-Abschnitten |
| Füllfarbe (Slider) | Farbe der Balken bei nicht-16:9-Bildern (z. B. Hochformat) |
| Schrift & Farben | Eigene Schriftart, Timer-Farbe, Untertitel-Farbe |
| Untertitel | Optionaler Text unter dem Timer mit Größen- und Farbsteuerung |
| Untertitel-Abstand | Extra-Abstand zwischen Timer und Untertitel in Zeilenhöhen |
| Abschluss-Bild | Slide nach dem Timer mit Text, Schriftart, Farbe und Hintergrundbild |
| Fade In / Out | Schwarzblende am Start und Ende mit konfigurierbarer Dauer |
| Slider-Timing | Wann Bilder erscheinen, wie lange, Pause dazwischen |
| Slider-Loop | Bilder bis Zonen-Ende wiederholen oder jeden einmal zeigen |
| Übergänge | Crossfade-Dauer zwischen Timer und Slider-Bildern |
| Musik im Abschluss-Bild | Musik läuft bis Videoende oder endet mit Timer 0:00 |
| Musik-Fade-out | Dauer des Musik-Fade am Videoende |
| Töne | Audio-Benachrichtigung bei Abschluss oder Fehler |
| Sprache | Deutsch / Englisch / Russisch — wirkt sofort |

Einstellungen werden gespeichert unter:
```
%APPDATA%\MaczapIntroMaker\settings.json
```

---

## 🔍 Vorschau

Vor dem Rendern kann ein Vorschau-Frame generiert werden, der Hintergrund, Schriftart, Farbe und Untertitel exakt so zeigt wie das fertige Video — bei fester Uhrzeit 04:32. Die Vorschau aktualisiert sich automatisch (600 ms Debounce) wenn Hintergrund, Schrift oder Farbe geändert wird, oder manuell per Button.

---

## 📄 PDF-Support

Slider-Bilder können auch als PDF ausgewählt werden. Jede Seite wird automatisch als Einzelbild übernommen. Erfordert **PyMuPDF**:

```bash
pip install PyMuPDF
```

---

## 🌐 Sprachen

Die App unterstützt aktuell drei Sprachen:

| Code | Sprache |
|---|---|
| `de` | Deutsch (Standard) |
| `en` | English |
| `ru` | Русский |

Die Sprache wird in den **Einstellungen** gewählt und gilt sofort. Weitere Sprachen können einfach durch Ablegen einer neuen `xx.json` im `lang/`-Ordner hinzugefügt werden — sie werden automatisch erkannt.

---

## 🎵 Audio (FFmpeg)

Audio-Mixing erfordert `ffmpeg.exe` unter:

```
assets/bin/ffmpeg.exe
```

Einen statischen Build gibt es auf [ffmpeg.org](https://ffmpeg.org/download.html) oder [gyan.dev](https://www.gyan.dev/ffmpeg/builds/).

Wird FFmpeg nicht gefunden, wird das Video ohne Audio gerendert.

---

## ⚡ Hardware-Encoding

Beim Rendern erkennt die App automatisch verfügbare Hardware-Encoder und wählt den schnellsten:

| Encoder | Voraussetzung |
|---|---|
| `h264_nvenc` | NVIDIA-GPU mit NVENC-Support |
| `h264_amf` | AMD-GPU mit AMF-Support |
| `libx264` | CPU-Fallback, immer verfügbar |

Die Erkennung läuft einmalig beim ersten Render und wird für die Sitzung gecacht. Es ist keine Konfiguration nötig.

---

## 🔔 Töne

Die App spielt optionale Benachrichtigungsgeräusche ab, wenn das Rendering abgeschlossen ist oder ein Fehler aufgetreten ist. Die Sounds können in den Einstellungen deaktiviert werden.

Erwartet werden folgende Dateien unter `assets/sounds/`:

```
assets/sounds/success.mp3
assets/sounds/error.mp3
```

Fehlen die Dateien, läuft die App ohne Töne — es gibt keine Fehlermeldung.

---

## 🛠️ Tech Stack

| Bibliothek | Zweck |
|---|---|
| `PyQt5` | UI-Framework |
| `OpenCV` (`cv2`) | Frame-Rendering & Video-Capture |
| `Pillow` (`PIL`) | Text-Rendering, Font-Handling |
| `NumPy` | Frame-Compositing |
| `FFmpeg` | Audio-Mixing (optional, extern) |
| `PyMuPDF` (`fitz`) | PDF-zu-Bild-Konvertierung (optional) |
| `PyInstaller` | EXE-Bundling |

---

## 📄 Lizenz

MIT — frei verwendbar, Nennung erwünscht.