import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont
import os, glob
import sys

BG_DARK  = "#0F172A"
BG_CARD  = "#263348"
ACCENT   = "#3B82F6"
TEXT_DIM = "#94A3B8"

# Hilfsfunktion für PyInstaller
def resource_path(relative_path):
    """Gibt den korrekten Pfad für PyInstaller oder normale Ausführung zurück."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# Pfad zu Fonts
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = resource_path("assets/fonts")


def _load_font_list():
    fonts = []
    if os.path.isdir(FONTS_DIR):
        seen = set()  # für eindeutige Schriftarten
        for ext in ("*.ttf", "*.otf", "*.TTF", "*.OTF"):
            for p in sorted(glob.glob(os.path.join(FONTS_DIR, ext))):
                name = os.path.splitext(os.path.basename(p))[0]
                if name not in seen:
                    fonts.append((name, p))
                    seen.add(name)
    if not fonts:
        fonts = [("Standard (OpenCV)", None)]
    # alphabetisch sortieren nach Name
    fonts.sort(key=lambda x: x[0].lower())
    return fonts


def _render_preview(font_path, text="04:32", size=(320, 80)):
    W, H = size
    img  = Image.new("RGB", (W, H), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)
    try:
        pil_font = ImageFont.truetype(font_path, size=52) if font_path else ImageFont.load_default()
    except Exception:
        pil_font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=pil_font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (W - tw) // 2 - bbox[0]
    y = (H - th) // 2 - bbox[1]
    draw.text((x+2, y+2), text, font=pil_font, fill=(0, 0, 0))
    draw.text((x,   y  ), text, font=pil_font, fill=(255, 255, 255))
    return ctk.CTkImage(img, size=(W, H))


class FontPickerWidget(ctk.CTkFrame):
    def __init__(self, parent, on_change=None, **kw):
        super().__init__(parent, fg_color=BG_CARD, corner_radius=10, **kw)
        self.on_change  = on_change
        self._font_list = _load_font_list()
        self._names     = [f[0] for f in self._font_list]
        self._selected  = ctk.StringVar(value=self._names[0])

        ctk.CTkLabel(self, text="🔤  Schriftart", font=("Segoe UI", 13, "bold"),
                     text_color=ACCENT).pack(anchor="w", padx=14, pady=(12, 4))
        ctk.CTkOptionMenu(self, variable=self._selected, values=self._names,
                          width=320, font=("Segoe UI", 12),
                          command=self._on_select).pack(anchor="w", padx=14, pady=(0, 8))
        self._preview_lbl = ctk.CTkLabel(self, text="")
        self._preview_lbl.pack(padx=14, pady=(0, 12))
        self._refresh_preview()

    def _on_select(self, name):
        self._refresh_preview()
        if self.on_change:
            self.on_change(self._get_path(name))

    def _refresh_preview(self):
        img = _render_preview(self._get_path(self._selected.get()))
        self._preview_lbl.configure(image=img, text="")
        self._preview_lbl._image = img

    def _get_path(self, name):
        for n, p in self._font_list:
            if n == name:
                return p
        return None

    def get_font_path(self):
        return self._get_path(self._selected.get())