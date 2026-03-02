import sys, os
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication
from PyQt5.QtCore    import Qt, QTimer, pyqtSignal
from PyQt5.QtGui     import QPixmap, QPainter, QColor, QPen, QFont


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


THEMES = {
    "light": {"bg": "#F1F5F9", "accent": "#2563EB", "ring_bg": "#CBD5E1"},
    "dark":  {"bg": "#0F172A", "accent": "#3B82F6", "ring_bg": "#1E293B"},
}


class _Spinner(QWidget):
    def __init__(self, accent, ring_bg, parent=None):
        super().__init__(parent)
        self.setFixedSize(52, 52)
        self._angle   = 0
        self._accent  = QColor(accent)
        self._ring_bg = QColor(ring_bg)
        self._timer   = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def _tick(self):
        self._angle = (self._angle - 8) % 360
        self.update()

    def stop(self):
        self._timer.stop()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = 18
        cx, cy = 26, 26
        pen = QPen(self._ring_bg, 4, Qt.SolidLine, Qt.RoundCap)
        p.setPen(pen)
        p.drawArc(cx - r, cy - r, r * 2, r * 2, 0, 360 * 16)
        pen2 = QPen(self._accent, 4, Qt.SolidLine, Qt.RoundCap)
        p.setPen(pen2)
        p.drawArc(cx - r, cy - r, r * 2, r * 2, self._angle * 16, 260 * 16)


class SplashScreen(QWidget):
    finished = pyqtSignal()

    def __init__(self, theme: str = "light"):
        super().__init__()
        colors = THEMES.get(theme, THEMES["light"])

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SplashScreen)
        self.setFixedSize(420, 280)
        self.setStyleSheet(f"background-color: {colors['bg']};")

        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - 420) // 2, (screen.height() - 280) // 2)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(12)
        layout.setContentsMargins(40, 30, 40, 30)

        # Logo je nach Theme (kein Text mehr)
        logo_file = "logo_light.png" if theme == "light" else "logo_dark.png"
        logo_path = resource_path(f"assets/pictures/{logo_file}")
        logo_lbl  = QLabel()
        logo_lbl.setAlignment(Qt.AlignCenter)
        logo_lbl.setStyleSheet("background: transparent;")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path)
            pix = pix.scaledToHeight(150, Qt.SmoothTransformation)
            logo_lbl.setPixmap(pix)
        else:
            logo_lbl.setText("🎬")
            logo_lbl.setFont(QFont("Segoe UI", 52))
        layout.addWidget(logo_lbl)

        # Spinner
        self._spinner = _Spinner(colors["accent"], colors["ring_bg"])
        spin_wrap = QWidget()
        spin_wrap.setStyleSheet("background: transparent;")
        sw_layout = QVBoxLayout(spin_wrap)
        sw_layout.setAlignment(Qt.AlignCenter)
        sw_layout.addWidget(self._spinner)
        layout.addWidget(spin_wrap)

        QTimer.singleShot(3000, self._finish)

    def _finish(self):
        self._spinner.stop()
        self.finished.emit()
        self.close()