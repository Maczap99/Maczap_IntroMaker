import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont
import os, glob

BG_DARK  = "#0F172A"
BG_MID   = "#1E293B"
BG_CARD  = "#263348"
ACCENT   = "#3B82F6"
TEXT_DIM = "#94A3B8"

FONTS_DIR = os.path.join(os.path.dirname(__file__), "assets", "fonts")


def _load_font_list():
    """Gibt Liste von (Anzeigename, Pfad) zurück — zuerst TTF/OTF aus assets/fonts."""
    fonts = []
    if os.path.isdir(FONTS_DIR):
        for ext in ("*.ttf", "*.otf", "*.TTF", "*.OTF"):
            for p in sorted(glob.glob(os.path.join(FONTS_DIR, ext))):
                name = os.path.splitext(os.path.basename(p))[0]
                fonts.append((name, p))
    # Fallback: eingebaute OpenCV-Namen
    if not fonts:
        fonts = [("Default (OpenCV)", None)]
    return fonts


def _render_preview(font_path, text="04:32", size=(320, 80)):
    """Rendert Text mit PIL-Font als CTkImage."""
    W, H = size
    img  = Image.new("RGB", (W, H), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)

    try:
        if font_path:
            pil_font = ImageFont.truetype(font_path, size=52)
        else:
            pil_font = ImageFont.load_default()
    except Exception:
        pil_font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=pil_font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (W - tw) // 2 - bbox[0]
    y = (H - th) // 2 - bbox[1]

    # Schatten
    draw.text((x + 2, y + 2), text, font=pil_font, fill=(0, 0, 0))
    # Text
    draw.text((x, y), text, font=pil_font, fill=(255, 255, 255))

    return ctk.CTkImage(img, size=(W, H))


class FontPickerWidget(ctk.CTkFrame):
    """
    Einbettbares Widget: Dropdown mit Fontnamen + Live-Vorschau.
    Gibt per `on_change(font_path_or_None)` Bescheid.
    """

    def __init__(self, parent, on_change=None, **kw):
        super().__init__(parent, fg_color=BG_CARD, corner_radius=10, **kw)
        self.on_change   = on_change
        self._font_list  = _load_font_list()
        self._font_names = [f[0] for f in self._font_list]
        self._selected   = ctk.StringVar(value=self._font_names[0])

        # Label
        ctk.CTkLabel(self, text="🔤  Schriftart", font=("Segoe UI", 13, "bold"),
                     text_color=ACCENT).pack(anchor="w", padx=14, pady=(12, 4))

        # Dropdown
        self._menu = ctk.CTkOptionMenu(
            self, variable=self._selected,
            values=self._font_names,
            width=320, font=("Segoe UI", 12),
            command=self._on_select)
        self._menu.pack(anchor="w", padx=14, pady=(0, 8))

        # Vorschau-Canvas (PIL-Bild)
        self._preview_lbl = ctk.CTkLabel(self, text="")
        self._preview_lbl.pack(padx=14, pady=(0, 12))

        self._refresh_preview()

    def _on_select(self, name):
        self._refresh_preview()
        path = self._get_path(name)
        if self.on_change:
            self.on_change(path)

    def _refresh_preview(self):
        path  = self._get_path(self._selected.get())
        img   = _render_preview(path)
        self._preview_lbl.configure(image=img, text="")
        self._preview_lbl._image = img      # Referenz halten

    def _get_path(self, name):
        for n, p in self._font_list:
            if n == name:
                return p
        return None

    def get_font_path(self):
        return self._get_path(self._selected.get())