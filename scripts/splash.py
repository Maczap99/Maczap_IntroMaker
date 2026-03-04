import os, sys
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QApplication
from PyQt5.QtCore    import Qt, QTimer, pyqtSignal
from PyQt5.QtGui     import QPixmap, QFont, QColor, QPainter, QPainterPath


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


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
        # Slightly taller window to give the larger logo room to breathe
        self.setFixedSize(480, 320)

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

        # Inner container — rounded corners handled via QFrame stylesheet
        self._container = QFrame(self)
        self._container.setGeometry(0, 0, 480, 320)
        self._container.setStyleSheet(f"""
            QFrame {{
                background: {bg};
                border-radius: {self._RADIUS}px;
                border: 1px solid {border};
            }}
        """)

        layout = QVBoxLayout(self._container)
        layout.setContentsMargins(40, 40, 40, 32)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignCenter)

        # Logo — prefer a themed PNG, fall back to plain text
        logo_suffix = "dark" if dark else "light"
        logo_path   = resource_path(f"assets/pictures/logo_{logo_suffix}.png")
        logo_lbl    = QLabel()
        logo_lbl.setAlignment(Qt.AlignCenter)
        logo_lbl.setStyleSheet("background: transparent; border: none;")
        if os.path.exists(logo_path):
            # Scale to 180 px tall — noticeably larger than the previous 90 px
            pix = QPixmap(logo_path).scaledToHeight(180, Qt.SmoothTransformation)
            logo_lbl.setPixmap(pix)
        else:
            logo_lbl.setText("Intro Maker")
            logo_lbl.setFont(QFont("Segoe UI", 32, QFont.Bold))
            logo_lbl.setStyleSheet(
                f"color: {fg}; background: transparent; border: none;")
        layout.addWidget(logo_lbl)

        layout.addSpacing(4)

        # Loading label
        loading_lbl = QLabel("Wird geladen …")
        loading_lbl.setAlignment(Qt.AlignCenter)
        loading_lbl.setFont(QFont("Segoe UI", 11))
        loading_lbl.setStyleSheet(
            f"color: {sub}; background: transparent; border: none;")
        layout.addWidget(loading_lbl)

    # ── Painting ──────────────────────────────────────────────────────────────
    def paintEvent(self, event):
        """Fill the overall window area with full transparency so only the
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
        self.hide()
        self.finished.emit()