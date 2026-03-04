import os, sys, math
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QApplication
from PyQt5.QtCore    import Qt, QTimer, pyqtSignal, QPointF
from PyQt5.QtGui     import QPixmap, QFont, QColor, QPainter, QPainterPath, QPen


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


# ── Spinner widget ─────────────────────────────────────────────────────────────
class _Spinner(QWidget):
    """A simple animated arc spinner that rotates indefinitely."""

    def __init__(self, size=32, color="#3B82F6", parent=None):
        super().__init__(parent)
        self._angle   = 0
        self._color   = QColor(color)
        self._size    = size
        self.setFixedSize(size, size)
        # Rotate 8° per tick at ~60 fps → one full revolution ≈ 0.75 s
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)  # ~60 fps

    def _tick(self):
        self._angle = (self._angle + 8) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        pen = QPen(self._color, 3, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen)

        margin = 4
        rect   = self.rect().adjusted(margin, margin, -margin, -margin)
        # Draw a 270° arc that sweeps around; the gap rotates with _angle
        painter.drawArc(rect, -self._angle * 16, -270 * 16)

    def stop(self):
        self._timer.stop()


# ── Splash screen ──────────────────────────────────────────────────────────────
class SplashScreen(QWidget):
    finished = pyqtSignal()

    # Corner radius for the rounded splash window
    _RADIUS = 20

    def __init__(self, theme="light", parent=None):
        super().__init__(parent)
        self._theme = theme

        # Frameless + translucent so we can paint our own rounded background
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.SplashScreen
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        # Extra height to comfortably fit logo + spinner
        self.setFixedSize(480, 340)

        self._build_ui()
        self._center()

        # Auto-close after 2.5 seconds
        QTimer.singleShot(2500, self._finish)

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        dark   = (self._theme == "dark")
        bg     = "#1E293B" if dark else "#FFFFFF"
        border = "#334155" if dark else "#E2E8F0"
        fg     = "#F1F5F9" if dark else "#0F172A"
        sub    = "#94A3B8" if dark else "#64748B"
        spin_c = "#3B82F6" if dark else "#2563EB"

        # Inner rounded container
        self._container = QFrame(self)
        self._container.setGeometry(0, 0, 480, 340)
        self._container.setStyleSheet(f"""
            QFrame {{
                background: {bg};
                border-radius: {self._RADIUS}px;
                border: 1px solid {border};
            }}
        """)

        layout = QVBoxLayout(self._container)
        layout.setContentsMargins(40, 36, 40, 28)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignCenter)

        # ── Logo ───────────────────────────────────────────────────────────────
        logo_suffix = "dark" if dark else "light"
        logo_path   = resource_path(f"assets/pictures/logo_{logo_suffix}.png")
        logo_lbl    = QLabel()
        logo_lbl.setAlignment(Qt.AlignCenter)
        logo_lbl.setStyleSheet("background: transparent; border: none;")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path).scaledToHeight(180, Qt.SmoothTransformation)
            logo_lbl.setPixmap(pix)
        else:
            logo_lbl.setText("Intro Maker")
            logo_lbl.setFont(QFont("Segoe UI", 32, QFont.Bold))
            logo_lbl.setStyleSheet(f"color: {fg}; background: transparent; border: none;")
        layout.addWidget(logo_lbl)

        layout.addSpacing(4)

        # ── "Loading" label ────────────────────────────────────────────────────
        loading_lbl = QLabel("Wird geladen …")
        loading_lbl.setAlignment(Qt.AlignCenter)
        loading_lbl.setFont(QFont("Segoe UI", 11))
        loading_lbl.setStyleSheet(f"color: {sub}; background: transparent; border: none;")
        layout.addWidget(loading_lbl)

        # ── FIX: animated spinner centred below the label ──────────────────────
        spinner_row = QWidget()
        spinner_row.setStyleSheet("background: transparent; border: none;")
        from PyQt5.QtWidgets import QHBoxLayout as _HBox
        sr_layout = _HBox(spinner_row)
        sr_layout.setContentsMargins(0, 0, 0, 0)
        sr_layout.setAlignment(Qt.AlignCenter)

        self._spinner = _Spinner(size=32, color=spin_c, parent=spinner_row)
        sr_layout.addWidget(self._spinner)
        layout.addWidget(spinner_row)

    # ── Painting ──────────────────────────────────────────────────────────────
    def paintEvent(self, event):
        """Fill the overall window with full transparency so only the
        rounded QFrame container is visible on screen."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _center(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width()  - self.width())  // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def _finish(self):
        self._spinner.stop()
        self.hide()
        self.finished.emit()