import sys, os, glob
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QFrame
from PyQt5.QtGui     import QPixmap, QImage, QFont
from PyQt5.QtCore    import Qt, pyqtSignal
from PIL             import Image, ImageDraw, ImageFont


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


FONTS_DIR = resource_path("assets/fonts")


def _load_font_list():
    fonts = []
    if os.path.isdir(FONTS_DIR):
        seen = set()
        for ext in ("*.ttf", "*.otf", "*.TTF", "*.OTF"):
            for p in sorted(glob.glob(os.path.join(FONTS_DIR, ext))):
                name = os.path.splitext(os.path.basename(p))[0]
                if name not in seen:
                    fonts.append((name, p))
                    seen.add(name)
    if not fonts:
        fonts = [("Standard", None)]
    fonts.sort(key=lambda x: x[0].lower())
    return fonts


def _render_preview(font_path, theme="light", text="04:32", size=(320, 80)):
    """Render a preview image of the given text using the specified font."""
    W, H = size
    if theme == "dark":
        bg_col, text_col, shd_col = (15, 23, 42), (255, 255, 255), (0, 0, 0)
    else:
        bg_col, text_col, shd_col = (240, 245, 250), (15, 23, 42), (180, 180, 180)
    img  = Image.new("RGB", (W, H), color=bg_col)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(font_path, 52) if font_path else ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (W - tw) // 2 - bbox[0]
    y = (H - th) // 2 - bbox[1]
    draw.text((x + 2, y + 2), text, font=font, fill=shd_col)
    draw.text((x, y),         text, font=font, fill=text_col)
    data = img.tobytes("raw", "RGB")
    qi   = QImage(data, W, H, W * 3, QImage.Format_RGB888)
    return QPixmap.fromImage(qi)


class FontPickerWidget(QFrame):
    font_changed = pyqtSignal(object)

    def __init__(self, parent=None, theme="light", preview_text="04:32"):
        super().__init__(parent)
        self._font_list   = _load_font_list()
        self._theme       = theme
        # Preview text shown in the font preview image (e.g. "04:32" for timer,
        # "Beispiel" for outro slide text)
        self._preview_text = preview_text

        self.setObjectName("FontPickerWidget")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        title = QLabel("🔤  Schriftart")
        title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        title.setObjectName("sectionLabel")
        layout.addWidget(title)

        self._combo = QComboBox()
        self._combo.setFont(QFont("Segoe UI", 11))
        self._combo.setFixedWidth(320)
        for name, _ in self._font_list:
            self._combo.addItem(name)
        self._combo.currentIndexChanged.connect(self._on_change)
        layout.addWidget(self._combo)

        self._preview = QLabel()
        self._preview.setFixedSize(320, 80)
        self._preview.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._preview)

        self._refresh_preview()

    def _on_change(self, _):
        self._refresh_preview()
        self.font_changed.emit(self.get_font_path())

    def _refresh_preview(self):
        self._preview.setPixmap(
            _render_preview(self.get_font_path(), self._theme, text=self._preview_text)
        )

    def set_theme(self, theme):
        self._theme = theme
        self._refresh_preview()

    def get_font_path(self):
        idx = self._combo.currentIndex()
        return self._font_list[idx][1] if 0 <= idx < len(self._font_list) else None