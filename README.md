# 🎬 Maczap IntroMaker

> **A desktop app for creating professional countdown intro videos — with custom fonts, background music, image sliders, and smooth fade effects.**

Built with Python + PyQt5. Renders directly via OpenCV and PIL, with optional FFmpeg support for audio mixing.

---

## ✨ Features

- **Countdown Timer** — configurable duration (1–120 min), centered on screen with custom font and color
- **Subtitle** — optional text displayed below the timer, with independent font size and color
- **Background** — use a video loop, a static image, or plain white
- **Image Slider** — display images between countdown segments, with configurable timing and loop behavior
- **Background Music** — MP3 / WAV / OGG support, with optional loop and fade-out (requires FFmpeg)
- **Fade Effects** — smooth fade-in from black at the start, fade-out to black at the end, and crossfade transitions between timer and images
- **Custom Fonts** — pick any `.ttf` / `.otf` font from the `assets/fonts/` folder, with live preview
- **Light & Dark Mode** — full UI theming with persistent settings
- **Advanced Settings Page** — configure all timing, fade, and slider parameters in a clean settings view

---

## 🖥️ Screenshots

> *(Add your own screenshots here)*

| Standard View | Advanced Settings |
|---|---|
| `screenshots/standard.png` | `screenshots/advanced.png` |

---

## 🚀 Getting Started

### Requirements

- Python 3.10+
- FFmpeg (optional, required for audio mixing — place `ffmpeg.exe` under `assets/bin/`)

### Install dependencies

```bash
pip install -r config/requirements.txt
```

### Run

```bash
cd scripts
python main.py
```

---

## 📦 Build EXE (Windows)

Run the included build script:

```
build\build.bat
```

This will:
1. Install all dependencies via pip
2. Bundle everything into a single `.exe` using PyInstaller
3. Output to `dist\IntroMaker.exe`

> Make sure `assets/bin/ffmpeg.exe` is present before building if you want audio support bundled.

---

## 📁 Project Structure

```
IntroMaker/
├── assets/
│   ├── bin/            # ffmpeg.exe (optional, not included)
│   ├── fonts/          # Custom .ttf / .otf fonts
│   └── pictures/       # Icons, logos, splash images
├── build/
│   └── build.bat       # PyInstaller build script
├── config/
│   └── requirements.txt
├── scripts/
│   ├── main.py             # Main window & UI
│   ├── video_generator.py  # Frame rendering & FFmpeg pipeline
│   ├── font_picker.py      # Font selection widget with live preview
│   ├── splash.py           # Animated splash screen
│   ├── config_manager.py   # Settings load/save/reset (stored in %APPDATA%)
│   └── styles.py           # Light/dark theme stylesheets
└── README.md
```

---

## ⚙️ Configuration

All settings are saved automatically between sessions. You can also manually save or reset them from the **Advanced Settings** page (⚙️ button in the header).

| Setting | Description |
|---|---|
| Timer Duration | Total length of the countdown video (1–120 min) |
| Background | Video file, image file, or plain white |
| Music | Audio file with optional loop + fade-out (requires FFmpeg) |
| Slider Images | Images shown between countdown segments |
| Font & Colors | Custom font, timer color, subtitle color |
| Subtitle | Optional text below the timer with size and color control |
| Subtitle Offset | Extra distance between timer and subtitle in line-heights |
| Fade In / Out | Configurable black fade at video start and end, with duration |
| Slider Timing | When to show images, how long each is shown, pause between |
| Slider Loop | Repeat images until the slider zone ends, or show each once |
| Transitions | Crossfade duration between timer and slider images |
| Music Fade-out | Duration of the music fade at the end of the video |

Settings are saved automatically to `%APPDATA%\MaczapIntroMaker\settings.json` and restored on next launch. You can also manually save or reset from the **Advanced Settings** page.

---

## 🎵 Audio (FFmpeg)

Audio mixing requires `ffmpeg.exe` to be placed at:

```
assets/bin/ffmpeg.exe
```

You can download a static build from [ffmpeg.org](https://ffmpeg.org/download.html) or [gyan.dev](https://www.gyan.dev/ffmpeg/builds/).

If FFmpeg is not found, the video will be rendered without audio.

---

## 🛠️ Tech Stack

| Library | Purpose |
|---|---|
| `PyQt5` | UI framework |
| `OpenCV` (`cv2`) | Frame writing & video capture |
| `Pillow` (`PIL`) | Text rendering, font handling |
| `NumPy` | Frame compositing |
| `FFmpeg` | Audio mixing (optional, external) |
| `PyInstaller` | EXE bundling |

---

## 📄 License

MIT — do whatever you want, attribution appreciated.