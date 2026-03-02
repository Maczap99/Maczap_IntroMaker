import json, os, sys

def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# Gespeichert wird neben der EXE bzw. im Projektordner
def _config_path():
    if hasattr(sys, "_MEIPASS"):
        # EXE-Modus: neben der EXE speichern
        exe_dir = os.path.dirname(sys.executable)
    else:
        # Entwicklungsmodus: im config/-Ordner
        base = os.path.dirname(os.path.abspath(__file__))
        exe_dir = os.path.join(base, "..", "config")
        os.makedirs(exe_dir, exist_ok=True)
    return os.path.join(exe_dir, "settings.json")


DEFAULTS = {
    "theme": "light",
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