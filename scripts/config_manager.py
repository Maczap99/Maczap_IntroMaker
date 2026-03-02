import json, os, sys

APP_NAME = "MaczapIntroMaker"


def _config_path() -> str:
    """
    Speichert die settings.json im AppData\Roaming Ordner des Benutzers.
    Pfad: C:\\Users\\<Name>\\AppData\\Roaming\\MaczapIntroMaker\\settings.json
    Fallback: neben der EXE / im config-Ordner (Entwicklungsmodus)
    """
    # APPDATA Umgebungsvariable (Roaming) → %APPDATA%
    appdata = os.environ.get("APPDATA")

    if appdata:
        folder = os.path.join(appdata, APP_NAME)
    else:
        # Fallback falls APPDATA nicht gesetzt ist (z.B. Linux/Mac)
        if hasattr(sys, "_MEIPASS"):
            folder = os.path.dirname(sys.executable)
        else:
            base   = os.path.dirname(os.path.abspath(__file__))
            folder = os.path.join(base, "..", "config")

    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "settings.json")


DEFAULTS = {
    # Erscheinungsbild
    "theme":            "light",

    # Timer
    "timer_minutes":    5,

    # Musik
    "music_loop":       True,
    "music_fadeout":    True,
    "music_fade_dur":   4,

    # Slider
    "slider_from":      4,
    "slider_until":     1,
    "img_duration":     10,
    "timer_between":    15,
    "slider_loop":      True,

    # Übergänge
    "fade_duration":    2.0,

    # Schrift
    "font_color":       "#FFFFFF",
    "font_name":        None,

    # Untertitel
    "subtitle_enabled": False,
    "subtitle_text":    "",
    "subtitle_size":    40,
    "subtitle_color":   "#FFFFFF",
}


def load() -> dict:
    path = _config_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Fehlende Keys mit Defaults auffüllen
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
        print(f"[config_manager] Speichern fehlgeschlagen: {e}")


def reset() -> dict:
    """Löscht die settings.json und gibt Defaults zurück."""
    path = _config_path()
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass
    return dict(DEFAULTS)


def get_config_path() -> str:
    """Gibt den vollständigen Pfad zur settings.json zurück (für Debugging)."""
    return _config_path()