import json, os, sys

APP_NAME = "MaczapIntroMaker"


def _config_path() -> str:
    """Return the full path to the settings JSON file, creating its folder if needed."""
    appdata = os.environ.get("APPDATA")
    if appdata:
        folder = os.path.join(appdata, APP_NAME)
    else:
        if hasattr(sys, "_MEIPASS"):
            folder = os.path.dirname(sys.executable)
        else:
            base   = os.path.dirname(os.path.abspath(__file__))
            folder = os.path.join(base, "..", "config")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "settings.json")


DEFAULTS = {
    # UI state
    "theme":              "light",
    "language":           "de",

    # Timer
    "timer_minutes":      5,

    # Music
    "music_loop":         True,
    "music_fadeout":      True,
    "music_fade_dur":     4,

    # Video fade
    "intro_fade_enabled": True,
    "intro_fade_dur":     3,
    "outro_fade_enabled": True,
    "outro_fade_dur":     3,

    # Slider timing
    "slider_from":        4,
    "slider_until":       1,
    "img_duration":       10,
    "timer_between":      15,
    "slider_loop":        True,

    # Transitions
    "fade_duration":      1.0,

    # Font & timer color
    "font_color":         "#FFFFFF",
    "font_name":          None,

    # Background fallback color (used when no video/image is selected)
    "bg_color":           "#000000",

    # Subtitle
    "subtitle_enabled":   False,
    "subtitle_text":      "",
    "subtitle_size":      60,
    "subtitle_offset":    2,
    "subtitle_color":     "#FFFFFF",

    # Slider image fill color (used when image does not fill the 16:9 frame)
    "slider_fill_color":  "#000000",

    # Outro slide (shown after timer reaches 0)
    "outro_slide_enabled":    False,
    "outro_slide_text":       "Herzlich Willkommen",
    "outro_slide_color":      "#FFFFFF",
    "outro_slide_bg_color":   "#000000",
    "outro_slide_font_size":  120,
    "outro_slide_font_name":  None,
    "outro_slide_duration":   5,
    "outro_slide_fade_in":    1,
    "outro_slide_fade_out":   2,

    # Music behaviour during outro slide
    "music_in_outro":         False,

    # Remember last used output folder so the dialog opens there next time
    "last_output_folder":     "",
}


def load() -> dict:
    """Load settings from disk, filling missing keys with DEFAULTS."""
    path = _config_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Back-fill any keys added in newer versions
            for k, v in DEFAULTS.items():
                data.setdefault(k, v)
            return data
        except Exception:
            pass
    return dict(DEFAULTS)


def save(data: dict):
    """Persist settings dict to disk as JSON."""
    path = _config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[config_manager] Save failed: {e}")


def reset() -> dict:
    """Delete the settings file and return a fresh copy of DEFAULTS."""
    path = _config_path()
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass
    return dict(DEFAULTS)


def get_config_path() -> str:
    """Return the resolved settings file path (useful for debugging)."""
    return _config_path()