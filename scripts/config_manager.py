import json, os, sys

APP_NAME = "MaczapIntroMaker"


def _config_path() -> str:
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
    "mode":               0,           # 0 = simple page, 1 = advanced page

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
    "img_duration":       15,
    "timer_between":      15,
    "slider_loop":        True,

    # Transitions
    "fade_duration":      2.0,

    # Font & timer color
    "font_color":         "#FFFFFF",
    "font_name":          None,

    # Subtitle
    "subtitle_enabled":   False,
    "subtitle_text":      "",
    "subtitle_size":      40,
    "subtitle_offset":    2,           # extra line-heights of gap below timer
    "subtitle_color":     "#FFFFFF",
}


def load() -> dict:
    path = _config_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Fill in any keys added in newer versions
            for k, v in DEFAULTS.items():
                data.setdefault(k, v)
            return data
        except Exception:
            pass
    return dict(DEFAULTS)


def save(data: dict):
    path = _config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[config_manager] Save failed: {e}")


def reset() -> dict:
    path = _config_path()
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass
    return dict(DEFAULTS)


def get_config_path() -> str:
    return _config_path()