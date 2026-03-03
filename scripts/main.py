import sys, os, time
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QScrollArea, QFrame,
    QProgressBar, QTextEdit, QSizePolicy, QDialog, QStackedWidget,
    QColorDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, QTimer
from PyQt5.QtGui  import QPixmap, QFont, QColor, QIcon, QPalette

from splash          import SplashScreen
from font_picker     import FontPickerWidget
from video_generator import VideoGenerator, _get_ffmpeg
from config_manager  import load as cfg_load, save as cfg_save, reset as cfg_reset, DEFAULTS
from styles          import make_style


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


# ── ThemedDialog ───────────────────────────────────────────────────────────────
class ThemedDialog(QDialog):
    @staticmethod
    def info(parent, title, message, dark):
        ThemedDialog(parent, title, message, dark, mode="info").exec_()

    @staticmethod
    def error(parent, title, message, dark):
        ThemedDialog(parent, title, message, dark, mode="error").exec_()

    @staticmethod
    def question(parent, title, message, dark) -> bool:
        return ThemedDialog(parent, title, message, dark, mode="question").exec_() == QDialog.Accepted

    def __init__(self, parent, title, message, dark, mode="info"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(420)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        if dark:
            bg, fg, border = "#1E293B", "#F1F5F9", "#334155"
            btn_bg, btn_fg = "#3B82F6", "white"
            btn_cancel_bg, btn_cancel_fg = "#334155", "#94A3B8"
        else:
            bg, fg, border = "#FFFFFF", "#0F172A", "#E2E8F0"
            btn_bg, btn_fg = "#2563EB", "white"
            btn_cancel_bg, btn_cancel_fg = "#F1F5F9", "#64748B"
        self.setStyleSheet(f"""
            QDialog {{ background: {bg}; border-radius: 12px; }}
            QLabel  {{ color: {fg}; background: transparent; }}
            QPushButton {{ border-radius: 8px; padding: 8px 20px;
                font-size: 12px; font-weight: bold; border: none; }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 20); layout.setSpacing(16)
        hdr = QWidget(); hl = QHBoxLayout(hdr)
        hl.setContentsMargins(0,0,0,0); hl.setSpacing(12)
        icon_lbl = QLabel({"info":"✅","error":"❌","question":"↺"}.get(mode,"ℹ️"))
        icon_lbl.setFont(QFont("Segoe UI", 22))
        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title_lbl.setStyleSheet(f"color: {fg};")
        hl.addWidget(icon_lbl); hl.addWidget(title_lbl); hl.addStretch()
        layout.addWidget(hdr)
        line = QFrame(); line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background: {border}; max-height: 1px;")
        layout.addWidget(line)
        msg_lbl = QLabel(message)
        msg_lbl.setFont(QFont("Segoe UI", 11))
        msg_lbl.setWordWrap(True); msg_lbl.setStyleSheet(f"color: {fg};")
        layout.addWidget(msg_lbl)
        btn_row = QWidget(); bl = QHBoxLayout(btn_row)
        bl.setContentsMargins(0,0,0,0); bl.setSpacing(10); bl.addStretch()
        if mode == "question":
            cb = QPushButton("Abbrechen")
            cb.setStyleSheet(f"background:{btn_cancel_bg}; color:{btn_cancel_fg};")
            cb.clicked.connect(self.reject); bl.addWidget(cb)
            ok = QPushButton("Ja, zurücksetzen")
            ok.setStyleSheet("background:#EF4444; color:white;")
            ok.clicked.connect(self.accept); bl.addWidget(ok)
        else:
            ok = QPushButton("OK")
            ok.setStyleSheet(f"background:{btn_bg}; color:{btn_fg};")
            ok.setMinimumWidth(90); ok.clicked.connect(self.accept); bl.addWidget(ok)
        layout.addWidget(btn_row)


# ── StyledCheckBox ─────────────────────────────────────────────────────────────
class StyledCheckBox(QWidget):
    stateChanged = pyqtSignal(int)

    def __init__(self, text, parent=None):
        super().__init__(parent)
        self._checked = False
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0); layout.setSpacing(10)
        self._box = QPushButton()
        self._box.setFixedSize(22, 22)
        self._box.setCursor(Qt.PointingHandCursor)
        self._box.clicked.connect(self._toggle)
        self._label = QLabel(text)
        self._label.setFont(QFont("Segoe UI", 12))
        self._label.setCursor(Qt.PointingHandCursor)
        self._label.mousePressEvent = lambda _: self._toggle()
        layout.addWidget(self._box); layout.addWidget(self._label); layout.addStretch()
        self._refresh()

    def _toggle(self):
        self._checked = not self._checked
        self._refresh()
        self.stateChanged.emit(2 if self._checked else 0)

    def _refresh(self):
        if self._checked:
            self._box.setText("✕")
            self._box.setStyleSheet("""
                QPushButton { background:#3B82F6; color:white; border:none;
                    border-radius:5px; font-size:13px; font-weight:bold; }
                QPushButton:hover { background:#2563EB; }""")
        else:
            self._box.setText("")
            self._box.setStyleSheet("""
                QPushButton { background:transparent; color:transparent;
                    border:2px solid #475569; border-radius:5px; }
                QPushButton:hover { border-color:#3B82F6; }""")

    def isChecked(self):      return self._checked
    def setChecked(self, v):
        if self._checked != v:
            self._checked = v; self._refresh()

    def update_theme(self, dark):
        if not self._checked:
            border = "#475569" if dark else "#CBD5E1"
            hover  = "#3B82F6" if dark else "#2563EB"
            self._box.setStyleSheet(f"""
                QPushButton {{ background:transparent; color:transparent;
                    border:2px solid {border}; border-radius:5px; }}
                QPushButton:hover {{ border-color:{hover}; }}""")


# ── RenderWorker ───────────────────────────────────────────────────────────────
class RenderWorker(QObject):
    progress = pyqtSignal(float, str, int, int)
    finished = pyqtSignal(bool, str)

    def __init__(self, config):
        super().__init__()
        self._config = config

    def run(self):
        def cb(value, msg, frame_info=None):
            cur, total = frame_info if frame_info else (0, 0)
            self.progress.emit(value, msg, cur, total)
        gen = VideoGenerator(self._config, cb,
                             lambda ok, msg: self.finished.emit(ok, msg))
        gen.generate()


# ── Stepper ────────────────────────────────────────────────────────────────────
class Stepper(QWidget):
    def __init__(self, min_val, max_val, value, step=1, fmt="{}", parent=None):
        super().__init__(parent)
        self._min = min_val; self._max = max_val
        self._val = value;   self._step = step; self._fmt = fmt
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0); layout.setSpacing(4)
        self._dec_btn = QPushButton("−"); self._dec_btn.setObjectName("stepper")
        self._dec_btn.clicked.connect(self._dec)
        self._lbl = QLabel(fmt.format(value))
        self._lbl.setAlignment(Qt.AlignCenter)
        self._lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self._lbl.setMinimumWidth(72)
        self._inc_btn = QPushButton("+"); self._inc_btn.setObjectName("stepper")
        self._inc_btn.clicked.connect(self._inc)
        layout.addWidget(self._dec_btn); layout.addWidget(self._lbl); layout.addWidget(self._inc_btn)

    def _dec(self):
        self._val = max(self._min, round(self._val - self._step, 4))
        self._lbl.setText(self._fmt.format(self._val))

    def _inc(self):
        self._val = min(self._max, round(self._val + self._step, 4))
        self._lbl.setText(self._fmt.format(self._val))

    def value(self):        return self._val
    def set_value(self, v):
        self._val = max(self._min, min(self._max, v))
        self._lbl.setText(self._fmt.format(self._val))


# ── Helpers ────────────────────────────────────────────────────────────────────
def make_card():
    f = QFrame(); f.setObjectName("card"); return f

def sec_lbl(t):
    l = QLabel(t); l.setObjectName("sectionLabel")
    l.setFont(QFont("Segoe UI", 11, QFont.Bold)); return l

def hint_lbl(t):
    l = QLabel(t); l.setObjectName("hint")
    l.setWordWrap(True); l.setFont(QFont("Segoe UI", 10)); return l

def dim_lbl(t):
    l = QLabel(t); l.setObjectName("dim")
    l.setFont(QFont("Segoe UI", 11)); return l

def sep_line():
    """Horizontal separator line."""
    f = QFrame(); f.setFrameShape(QFrame.HLine)
    f.setObjectName("hint"); return f

def stepper_row(label, stepper, suffix=""):
    """Helper: label + stepper + optional suffix in one row."""
    w = QWidget(); l = QHBoxLayout(w)
    l.setContentsMargins(0, 4, 0, 4); l.setSpacing(10)
    lbl = dim_lbl(label); lbl.setFixedWidth(200)
    l.addWidget(lbl); l.addWidget(stepper)
    if suffix: l.addWidget(dim_lbl(suffix))
    l.addStretch()
    return w


# ── FileRow ────────────────────────────────────────────────────────────────────
class FileRow(QWidget):
    def __init__(self, btn_text, on_pick, on_clear, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,2,0,2); layout.setSpacing(6)
        self._lbl = QLabel("Nichts ausgewählt")
        self._lbl.setObjectName("pathLabel")
        self._lbl.setFont(QFont("Segoe UI", 10))
        self._lbl.setFixedHeight(28)
        self._lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        pick_btn = QPushButton(btn_text)
        pick_btn.setObjectName("secondary"); pick_btn.setFixedHeight(28)
        pick_btn.clicked.connect(on_pick)
        self._clear_btn = QPushButton("✕")
        self._clear_btn.setObjectName("iconBtn")
        self._clear_btn.setToolTip("Auswahl entfernen")
        self._clear_btn.clicked.connect(on_clear)
        self._clear_btn.setVisible(False)
        layout.addWidget(self._lbl, 1)
        layout.addWidget(pick_btn)
        layout.addWidget(self._clear_btn)

    def set_path(self, path):
        if path:
            self._lbl.setText(os.path.basename(path))
            self._clear_btn.setVisible(True)
        else:
            self._lbl.setText("Nichts ausgewählt")
            self._clear_btn.setVisible(False)


# ── Main Window ────────────────────────────────────────────────────────────────
class IntroMaker(QMainWindow):

    PAGE_SIMPLE   = 0
    PAGE_ADVANCED = 1

    def __init__(self):
        super().__init__()
        self._settings      = cfg_load()
        self._theme         = self._settings.get("theme", "light")
        self._font_color    = self._settings.get("font_color",     "#FFFFFF")
        self._sub_color     = self._settings.get("subtitle_color", "#FFFFFF")
        self._image_paths   = []
        self._render_start  = 0.0
        self._thread        = None
        self._worker        = None
        self._bg_video_path = None
        self._bg_image_path = None
        self._music_path    = None
        self._out_path      = None
        self._current_page  = self.PAGE_SIMPLE

        self.setWindowTitle("Intro Maker")
        self.setMinimumSize(960, 780)
        self.resize(1060, 920)

        icon_path = resource_path("assets/pictures/icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            QApplication.instance().setWindowIcon(QIcon(icon_path))

        self._build_shared_widgets()
        self._build_ui()
        self._restore_settings()
        self._apply_theme(self._theme, save=False)

    # ── Shared widgets (created once, used on both pages) ─────────────────────
    def _build_shared_widgets(self):
        # Timer
        self._timer_step = Stepper(1, 120, 5, step=1, fmt="{} min")

        # Background rows — two instances each due to Qt single-parent rule
        self._bg_video_row   = FileRow("🎬  Video wählen", self._pick_bg_video, self._clear_bg_video)
        self._bg_image_row   = FileRow("🖼  Bild wählen",  self._pick_bg_image, self._clear_bg_image)
        self._bg_video_row_a = FileRow("🎬  Video wählen", self._pick_bg_video, self._clear_bg_video)
        self._bg_image_row_a = FileRow("🖼  Bild wählen",  self._pick_bg_image, self._clear_bg_image)

        # Music
        self._music_row   = FileRow("🎵  Musikdatei wählen", self._pick_music, self._clear_music)
        self._music_row_a = FileRow("🎵  Musikdatei wählen", self._pick_music, self._clear_music)

        # Output
        self._out_row   = FileRow("📁  Speicherort wählen", self._pick_output, self._clear_output)
        self._out_row_a = FileRow("📁  Speicherort wählen", self._pick_output, self._clear_output)

        # Image list
        self._img_list = QTextEdit()
        self._img_list.setReadOnly(True); self._img_list.setFixedHeight(80)
        self._img_list.setPlainText("  Keine Bilder ausgewählt")

        # Font picker
        self._font_picker = FontPickerWidget(theme=self._theme)

        # Color buttons
        self._color_btn = QPushButton("  #FFFFFF  ")
        self._color_btn.setObjectName("colorBtn"); self._color_btn.setFixedHeight(32)
        self._color_btn.clicked.connect(self._pick_color)

        # Subtitle
        self._sub_chk = StyledCheckBox("Untertitel aktivieren")
        self._sub_chk.stateChanged.connect(self._toggle_subtitle)
        self._sub_edit = QTextEdit()
        self._sub_edit.setFixedHeight(70)
        self._sub_edit.setPlaceholderText("z. B. Willkommen zur Veranstaltung")
        self._sub_edit.setEnabled(False)
        self._sub_color_btn = QPushButton("  #FFFFFF  ")
        self._sub_color_btn.setObjectName("colorBtn"); self._sub_color_btn.setFixedHeight(32)
        self._sub_color_btn.setEnabled(False)
        self._sub_color_btn.clicked.connect(self._pick_sub_color)

        # ── Advanced settings widgets ──────────────────────────────────────────
        # Music
        self._music_loop_chk    = StyledCheckBox("Loop (wiederholen)")
        self._music_fadeout_chk = StyledCheckBox("Fade-out am Ende")
        self._music_loop_chk.setChecked(True); self._music_fadeout_chk.setChecked(True)
        self._music_fade_step   = Stepper(1, 30, 4, step=1, fmt="{} s")

        # Video fade
        self._intro_fade_chk  = StyledCheckBox("Fade In am Start aktivieren")
        self._intro_fade_chk.stateChanged.connect(self._toggle_intro_fade)
        self._intro_fade_step = Stepper(1, 30, 3, step=1, fmt="{} s")
        self._intro_fade_step.setEnabled(False)
        self._outro_fade_chk  = StyledCheckBox("Fade Out am Ende aktivieren")
        self._outro_fade_chk.stateChanged.connect(self._toggle_outro_fade)
        self._outro_fade_step = Stepper(1, 30, 3, step=1, fmt="{} s")
        self._outro_fade_step.setEnabled(False)

        # Slider timing
        self._slider_from_step   = Stepper(1, 120, 4,  step=1, fmt="{} min")
        self._slider_until_step  = Stepper(0, 120, 1,  step=1, fmt="{} min")
        self._img_dur_step       = Stepper(5, 120, 10, step=5, fmt="{} s")
        self._timer_between_step = Stepper(0, 120, 15, step=5, fmt="{} s")
        self._slider_loop_chk    = StyledCheckBox("Bilder wiederholen bis Slider-Ende")
        self._slider_loop_chk.setChecked(True)

        # Transitions
        self._fade_step = Stepper(0, 8, 2, step=0.5, fmt="{} s")

        # Subtitle size (advanced only)
        self._sub_size_step = Stepper(10, 120, 40, step=2, fmt="{} pt")
        self._sub_size_step.setEnabled(False)

    # ── UI build ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QWidget(); root.setObjectName("root")
        self.setCentralWidget(root)
        ml = QVBoxLayout(root)
        ml.setContentsMargins(0,0,0,0); ml.setSpacing(0)
        ml.addWidget(self._make_header())

        self._stack = QStackedWidget()
        self._stack.addWidget(self._make_simple_page())    # PAGE_SIMPLE
        self._stack.addWidget(self._make_advanced_page())  # PAGE_ADVANCED
        ml.addWidget(self._stack, 1)
        ml.addWidget(self._make_bottom())

    def _make_scroll(self, fn):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner = QWidget(); inner.setObjectName("root")
        il = QVBoxLayout(inner)
        il.setContentsMargins(0,0,8,0); il.setSpacing(10)
        fn(il); il.addStretch()
        scroll.setWidget(inner)
        return scroll

    # ── Header ─────────────────────────────────────────────────────────────────
    def _make_header(self):
        hdr = QFrame(); hdr.setObjectName("header"); hdr.setFixedHeight(72)
        layout = QHBoxLayout(hdr)
        layout.setContentsMargins(24,0,24,0); layout.setSpacing(10)
        self._header_logo_lbl = QLabel()
        self._header_logo_lbl.setStyleSheet("background: transparent;")
        layout.addWidget(self._header_logo_lbl)
        layout.addStretch()

        # Save button — only visible on advanced page
        self._save_btn = QPushButton("💾  Speichern")
        self._save_btn.setObjectName("saveBtn")
        self._save_btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self._save_btn.setFixedHeight(38)
        self._save_btn.clicked.connect(self._manual_save)
        self._save_btn.setVisible(False)
        layout.addWidget(self._save_btn)

        # Reset button — only visible on advanced page
        self._reset_btn = QPushButton("↺  Zurücksetzen")
        self._reset_btn.setObjectName("resetBtn")
        self._reset_btn.setFont(QFont("Segoe UI", 11))
        self._reset_btn.setFixedHeight(38)
        self._reset_btn.clicked.connect(self._confirm_reset)
        self._reset_btn.setVisible(False)
        layout.addWidget(self._reset_btn)

        self._mode_btn = QPushButton()
        self._mode_btn.setObjectName("themeBtn")
        self._mode_btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self._mode_btn.setFixedHeight(38)
        self._mode_btn.clicked.connect(self._toggle_mode)
        layout.addWidget(self._mode_btn)

        self._theme_btn = QPushButton()
        self._theme_btn.setObjectName("themeBtn")
        self._theme_btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self._theme_btn.setFixedHeight(38)
        self._theme_btn.clicked.connect(self._toggle_theme)
        layout.addWidget(self._theme_btn)
        return hdr

    def _update_header_logo(self):
        suffix = "dark" if self._theme == "dark" else "light"
        path   = resource_path(f"assets/pictures/logo_header_{suffix}.png")
        if os.path.exists(path):
            pix = QPixmap(path).scaledToHeight(52, Qt.SmoothTransformation)
            self._header_logo_lbl.setPixmap(pix)

    def _update_mode_btn(self):
        if self._current_page == self.PAGE_SIMPLE:
            self._mode_btn.setText("⚙️  Einstellungen")
        else:
            self._mode_btn.setText("🏠  Zurück")

    def _toggle_mode(self):
        self._current_page = self.PAGE_ADVANCED if self._current_page == self.PAGE_SIMPLE else self.PAGE_SIMPLE
        self._stack.setCurrentIndex(self._current_page)
        self._update_mode_btn()
        # Show save/reset only on the advanced page
        on_advanced = (self._current_page == self.PAGE_ADVANCED)
        self._save_btn.setVisible(on_advanced)
        self._reset_btn.setVisible(on_advanced)
        self._save_settings()

    # ── Simple page ────────────────────────────────────────────────────────────
    def _make_simple_page(self):
        page = QWidget()
        bl = QHBoxLayout(page)
        bl.setContentsMargins(20,12,20,12); bl.setSpacing(16)
        bl.addWidget(self._make_scroll(self._build_simple_left),  1)
        bl.addWidget(self._make_scroll(self._build_simple_right), 1)
        return page

    def _build_simple_left(self, layout):
        # Timer
        c = make_card(); cl = QVBoxLayout(c); cl.setContentsMargins(16,10,16,14); cl.setSpacing(6)
        cl.addWidget(sec_lbl("⏱  Timer-Dauer"))
        cl.addWidget(hint_lbl("Gesamtlänge des Countdown-Videos"))
        cl.addWidget(self._timer_step)
        layout.addWidget(c)

        # Background
        c2 = make_card(); cl2 = QVBoxLayout(c2); cl2.setContentsMargins(16,10,16,14); cl2.setSpacing(6)
        cl2.addWidget(sec_lbl("🎨  Hintergrund"))
        cl2.addWidget(hint_lbl("Video hat Vorrang vor Bild — beide optional (Standard: Weiß)"))
        cl2.addWidget(self._bg_video_row)
        cl2.addWidget(self._bg_image_row)
        layout.addWidget(c2)

        # Music
        c3 = make_card(); cl3 = QVBoxLayout(c3); cl3.setContentsMargins(16,10,16,14); cl3.setSpacing(6)
        cl3.addWidget(sec_lbl("🎵  Hintergrundmusik"))
        cl3.addWidget(hint_lbl("Optional — MP3, WAV, OGG"))
        cl3.addWidget(self._music_row)
        layout.addWidget(c3)

        # Output
        c7 = make_card(); cl7 = QVBoxLayout(c7); cl7.setContentsMargins(16,10,16,14); cl7.setSpacing(6)
        cl7.addWidget(sec_lbl("💾  Ausgabedatei"))
        cl7.addWidget(hint_lbl("Dateiname: Intro - TT.MM.JJJJ"))
        cl7.addWidget(self._out_row)
        layout.addWidget(c7)

    def _build_simple_right(self, layout):
        # Images
        c4 = make_card(); cl4 = QVBoxLayout(c4); cl4.setContentsMargins(16,10,16,14); cl4.setSpacing(6)
        cl4.addWidget(sec_lbl("🖼  Slider-Bilder"))
        cl4.addWidget(hint_lbl("Werden zwischen Countdown-Abschnitten eingeblendet"))
        br = QWidget(); brl = QHBoxLayout(br); brl.setContentsMargins(0,0,0,0); brl.setSpacing(8)
        add_btn = QPushButton("+ Bilder hinzufügen"); add_btn.setObjectName("secondary")
        add_btn.clicked.connect(self._add_images)
        clr_btn = QPushButton("Liste leeren"); clr_btn.setObjectName("secondary")
        clr_btn.clicked.connect(self._clear_images)
        brl.addWidget(add_btn); brl.addWidget(clr_btn); brl.addStretch()
        cl4.addWidget(br); cl4.addWidget(self._img_list)
        layout.addWidget(c4)

        # Font picker
        layout.addWidget(self._font_picker)

        # Font color for timer
        c6 = make_card(); cl6 = QVBoxLayout(c6); cl6.setContentsMargins(16,10,16,14); cl6.setSpacing(6)
        cl6.addWidget(sec_lbl("🎨  Schriftfarbe Timer"))
        cr_w = QWidget(); crl = QHBoxLayout(cr_w); crl.setContentsMargins(0,0,0,0); crl.setSpacing(10)
        crl.addWidget(dim_lbl("Farbe:")); crl.addWidget(self._color_btn); crl.addStretch()
        cl6.addWidget(cr_w)
        layout.addWidget(c6)

        # Subtitle
        c8 = make_card(); cl8 = QVBoxLayout(c8); cl8.setContentsMargins(16,10,16,14); cl8.setSpacing(6)
        cl8.addWidget(sec_lbl("💬  Untertitel"))
        cl8.addWidget(hint_lbl("Wird unterhalb des Timers angezeigt"))
        cl8.addWidget(self._sub_chk)
        cl8.addWidget(self._sub_edit)
        so = QWidget(); sol = QHBoxLayout(so); sol.setContentsMargins(0,0,0,0); sol.setSpacing(10)
        sol.addWidget(dim_lbl("Farbe:")); sol.addWidget(self._sub_color_btn); sol.addStretch()
        cl8.addWidget(so)
        layout.addWidget(c8)

    # ── Advanced settings page ─────────────────────────────────────────────────
    def _make_advanced_page(self):
        """Settings page: centered single column, all options stacked."""
        page = QWidget(); page.setObjectName("root")
        outer = QHBoxLayout(page)
        outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        inner = QWidget(); inner.setObjectName("root")
        vl = QVBoxLayout(inner)
        vl.setContentsMargins(0,0,0,0); vl.setSpacing(0)

        # Centered content column with max width
        center = QWidget(); center.setObjectName("root")
        center.setMaximumWidth(680)
        cl = QVBoxLayout(center)
        cl.setContentsMargins(0, 16, 0, 32); cl.setSpacing(6)

        self._build_settings_content(cl)

        vl.addWidget(center, 0, Qt.AlignHCenter)
        vl.addStretch()
        scroll.setWidget(inner)
        outer.addWidget(scroll)
        return page

    def _settings_group_header(self, icon, title):
        """Group heading in settings style."""
        lbl = QLabel(f"  {icon}  {title}")
        lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        lbl.setObjectName("sectionLabel")
        lbl.setContentsMargins(4, 18, 0, 4)
        return lbl

    def _settings_row(self, label, widget, hint=""):
        """
        One settings row: label on the left, widget on the right.
        Uses tight spacing to avoid excessive padding on WQHD screens.
        """
        row = QWidget(); row.setObjectName("card")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(16, 10, 16, 10); rl.setSpacing(12)
        left = QWidget(); ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        # Fixed, compact spacing — prevents hint label from ballooning on high-DPI
        ll.setSpacing(2)
        lbl = QLabel(label); lbl.setFont(QFont("Segoe UI", 11)); lbl.setObjectName("dim")
        ll.addWidget(lbl)
        if hint:
            h = QLabel(hint); h.setFont(QFont("Segoe UI", 9)); h.setObjectName("hint")
            # Prevent the hint label from stretching vertically
            h.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            ll.addWidget(h)
        left.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        rl.addWidget(left, 1)
        rl.addWidget(widget)
        return row

    def _settings_check_row(self, checkbox, hint=""):
        """
        One settings row containing only a checkbox (full width).
        Uses tight spacing to avoid excessive padding on WQHD screens.
        """
        row = QWidget(); row.setObjectName("card")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(16, 10, 16, 10); rl.setSpacing(0)
        left = QWidget(); ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(2)
        ll.addWidget(checkbox)
        if hint:
            h = QLabel(hint); h.setFont(QFont("Segoe UI", 9)); h.setObjectName("hint")
            h.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            ll.addWidget(h)
        left.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        rl.addWidget(left, 1)
        return row

    def _settings_divider(self):
        """Thin separator between rows of a group."""
        line = QFrame(); line.setFrameShape(QFrame.HLine)
        line.setObjectName("hint")
        line.setFixedHeight(1)
        line.setStyleSheet("margin: 0px 16px;")
        return line

    def _settings_block(self, icon, title, rows):
        """
        Builds a complete block: group header + card containing all rows.
        rows = list of widgets from _settings_row / _settings_check_row
        """
        header = self._settings_group_header(icon, title)
        card = QFrame(); card.setObjectName("card")
        cl = QVBoxLayout(card); cl.setContentsMargins(0, 0, 0, 0); cl.setSpacing(0)
        for i, row in enumerate(rows):
            row.setObjectName("card")
            row.setStyleSheet("")
            cl.addWidget(row)
            if i < len(rows) - 1:
                cl.addWidget(self._settings_divider())
        w = QWidget()
        wl = QVBoxLayout(w); wl.setContentsMargins(0, 0, 0, 8); wl.setSpacing(2)
        wl.addWidget(header)
        wl.addWidget(card)
        return w

    def _build_settings_content(self, layout):
        # ── Music ─────────────────────────────────────────────────────────────
        layout.addWidget(self._settings_block("🎵", "Musik", [
            self._settings_check_row(self._music_loop_chk),
            self._settings_check_row(self._music_fadeout_chk),
            self._settings_row("Fade-out Dauer", self._music_fade_step,
                               "Wie lange die Musik am Ende ausblendet"),
        ]))

        # ── Video fade ────────────────────────────────────────────────────────
        layout.addWidget(self._settings_block("🌑", "Video Fade In / Out", [
            self._settings_check_row(self._intro_fade_chk,
                                     "Video blendet am Start von Schwarz ein"),
            self._settings_row("Fade-In Dauer", self._intro_fade_step),
            self._settings_check_row(self._outro_fade_chk,
                                     "Video blendet am Ende zu Schwarz aus"),
            self._settings_row("Fade-Out Dauer", self._outro_fade_step),
        ]))

        # ── Slider timing ─────────────────────────────────────────────────────
        layout.addWidget(self._settings_block("🖼", "Slider-Timing", [
            self._settings_row("Slider erst ab", self._slider_from_step,
                               "Bilder einblenden wenn noch X Minuten verbleiben"),
            self._settings_row("Slider bis max.", self._slider_until_step,
                               "Keine Bilder mehr ab X verbleibenden Minuten"),
            self._settings_row("Dauer pro Bild", self._img_dur_step,
                               "Wie lange jedes Bild angezeigt wird"),
            self._settings_row("Timer zwischen Bildern", self._timer_between_step,
                               "Countdown-Pause zwischen zwei Bildern"),
            self._settings_check_row(self._slider_loop_chk,
                                     "Loop an: Bild → Timer → Bild → ...  |  Loop aus: alle Bilder einmal"),
        ]))

        # ── Transitions ───────────────────────────────────────────────────────
        layout.addWidget(self._settings_block("✨", "Übergänge", [
            self._settings_row("Bild-Fade Dauer", self._fade_step,
                               "Sanftes Ein-/Ausblenden beim Wechsel zu Bildern"),
        ]))

        # ── Subtitle ──────────────────────────────────────────────────────────
        layout.addWidget(self._settings_block("💬", "Untertitel", [
            self._settings_row("Schriftgröße", self._sub_size_step,
                               "Größe des Untertiteltextes im Video"),
        ]))

    # ── Bottom bar ─────────────────────────────────────────────────────────────
    def _make_bottom(self):
        bar = QFrame(); bar.setObjectName("bottomBar"); bar.setFixedHeight(110)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20,0,24,0); layout.setSpacing(12)
        info = QWidget(); il = QVBoxLayout(info)
        il.setContentsMargins(0,14,0,10); il.setSpacing(5)
        self._status_lbl = QLabel("Bereit")
        self._status_lbl.setObjectName("dim"); self._status_lbl.setFont(QFont("Segoe UI", 11))
        il.addWidget(self._status_lbl)
        self._progress = QProgressBar()
        self._progress.setRange(0, 1000); self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        il.addWidget(self._progress)
        det = QWidget(); dl = QHBoxLayout(det); dl.setContentsMargins(0,0,0,0); dl.setSpacing(0)
        self._frames_lbl = QLabel(""); self._frames_lbl.setObjectName("dim"); self._frames_lbl.setFont(QFont("Segoe UI", 10))
        self._eta_lbl    = QLabel(""); self._eta_lbl.setObjectName("dim");    self._eta_lbl.setFont(QFont("Segoe UI", 10))
        self._pct_lbl    = QLabel(""); self._pct_lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))
        dl.addWidget(self._frames_lbl); dl.addSpacing(20)
        dl.addWidget(self._eta_lbl);    dl.addSpacing(20)
        dl.addWidget(self._pct_lbl);    dl.addStretch()
        il.addWidget(det)
        layout.addWidget(info, 1)
        btn_col = QWidget(); bcl = QVBoxLayout(btn_col)
        bcl.setContentsMargins(0,16,0,16); bcl.setSpacing(8)
        self._create_btn = QPushButton("🎬  Video erstellen")
        self._create_btn.setObjectName("primary"); self._create_btn.setFixedSize(230, 52)
        self._create_btn.clicked.connect(self._start_render)
        self._cancel_btn = QPushButton("✕  Abbrechen")
        self._cancel_btn.setObjectName("danger"); self._cancel_btn.setFixedSize(230, 52)
        self._cancel_btn.setVisible(False); self._cancel_btn.clicked.connect(self._cancel_render)
        bcl.addWidget(self._create_btn); bcl.addWidget(self._cancel_btn)
        layout.addWidget(btn_col)
        return bar

    # ── Settings persistence ───────────────────────────────────────────────────
    def _collect_settings(self) -> dict:
        return {
            "theme":              self._theme,
            "mode":               self._current_page,
            "timer_minutes":      self._timer_step.value(),
            "music_loop":         self._music_loop_chk.isChecked(),
            "music_fadeout":      self._music_fadeout_chk.isChecked(),
            "music_fade_dur":     self._music_fade_step.value(),
            "intro_fade_enabled": self._intro_fade_chk.isChecked(),
            "intro_fade_dur":     self._intro_fade_step.value(),
            "outro_fade_enabled": self._outro_fade_chk.isChecked(),
            "outro_fade_dur":     self._outro_fade_step.value(),
            "slider_from":        self._slider_from_step.value(),
            "slider_until":       self._slider_until_step.value(),
            "img_duration":       self._img_dur_step.value(),
            "timer_between":      self._timer_between_step.value(),
            "slider_loop":        self._slider_loop_chk.isChecked(),
            "fade_duration":      self._fade_step.value(),
            "font_color":         self._font_color,
            "font_name":          self._font_picker._combo.currentText(),
            "subtitle_enabled":   self._sub_chk.isChecked(),
            "subtitle_text":      self._sub_edit.toPlainText(),
            "subtitle_size":      self._sub_size_step.value(),
            "subtitle_color":     self._sub_color,
        }

    def _restore_settings(self):
        s = self._settings
        self._current_page = s.get("mode", self.PAGE_SIMPLE)
        self._stack.setCurrentIndex(self._current_page)
        self._update_mode_btn()
        # Sync save/reset visibility with restored page
        on_advanced = (self._current_page == self.PAGE_ADVANCED)
        self._save_btn.setVisible(on_advanced)
        self._reset_btn.setVisible(on_advanced)
        self._timer_step.set_value(s.get("timer_minutes", 5))
        self._music_loop_chk.setChecked(s.get("music_loop", True))
        self._music_fadeout_chk.setChecked(s.get("music_fadeout", True))
        self._music_fade_step.set_value(s.get("music_fade_dur", 4))
        self._intro_fade_chk.setChecked(s.get("intro_fade_enabled", False))
        self._intro_fade_step.set_value(s.get("intro_fade_dur", 3))
        self._intro_fade_step.setEnabled(s.get("intro_fade_enabled", False))
        self._outro_fade_chk.setChecked(s.get("outro_fade_enabled", False))
        self._outro_fade_step.set_value(s.get("outro_fade_dur", 3))
        self._outro_fade_step.setEnabled(s.get("outro_fade_enabled", False))
        self._slider_from_step.set_value(s.get("slider_from", 4))
        self._slider_until_step.set_value(s.get("slider_until", 1))
        self._img_dur_step.set_value(s.get("img_duration", 10))
        self._timer_between_step.set_value(s.get("timer_between", 15))
        self._slider_loop_chk.setChecked(s.get("slider_loop", True))
        self._fade_step.set_value(s.get("fade_duration", 2.0))
        font_name = s.get("font_name")
        if font_name:
            idx = self._font_picker._combo.findText(font_name)
            if idx >= 0: self._font_picker._combo.setCurrentIndex(idx)
        fc = s.get("font_color", "#FFFFFF")
        self._font_color = fc
        self._update_color_btn(self._color_btn, fc)
        sub_on = s.get("subtitle_enabled", False)
        self._sub_chk.setChecked(sub_on)
        self._sub_edit.setPlainText(s.get("subtitle_text", ""))
        self._sub_size_step.set_value(s.get("subtitle_size", 40))
        self._sub_size_step.setEnabled(sub_on)
        sc = s.get("subtitle_color", "#FFFFFF")
        self._sub_color = sc
        self._update_color_btn(self._sub_color_btn, sc)
        self._sub_edit.setEnabled(sub_on)
        self._sub_color_btn.setEnabled(sub_on)

    def _save_settings(self):
        data = self._collect_settings()
        cfg_save(data); self._settings = data

    def _manual_save(self):
        self._save_settings()
        self._save_btn.setText("✓  Gespeichert")
        self._save_btn.setStyleSheet(
            "background:#16A34A; color:white; border-radius:10px;"
            "font-size:11px; font-weight:bold; padding:8px 14px; border:none;")
        QApplication.processEvents()
        QTimer.singleShot(1800, self._reset_save_btn)

    def _reset_save_btn(self):
        self._save_btn.setText("💾  Speichern")
        self._save_btn.setStyleSheet("")
        self._save_btn.setObjectName("saveBtn")
        QApplication.instance().setStyleSheet(QApplication.instance().styleSheet())

    # ── Theme ──────────────────────────────────────────────────────────────────
    def _apply_theme(self, theme, save=True):
        self._theme = theme
        QApplication.instance().setStyleSheet(make_style(theme == "dark"))
        self._theme_btn.setText("🌙  Dark Mode" if theme == "light" else "☀️  Light Mode")
        self._update_header_logo()
        accent = "#3B82F6" if theme == "dark" else "#2563EB"
        self._pct_lbl.setStyleSheet(f"color: {accent};")
        if hasattr(self, "_font_picker"):
            self._font_picker.set_theme(theme)
        dark = (theme == "dark")
        for chk in [self._music_loop_chk, self._music_fadeout_chk,
                    self._intro_fade_chk, self._outro_fade_chk,
                    self._sub_chk, self._slider_loop_chk]:
            try: chk.update_theme(dark)
            except: pass
        self._update_color_btn(self._color_btn, self._font_color)
        self._update_color_btn(self._sub_color_btn, self._sub_color)
        if save: self._save_settings()

    def _toggle_theme(self):
        self._apply_theme("dark" if self._theme == "light" else "light")

    # ── Reset ──────────────────────────────────────────────────────────────────
    def _confirm_reset(self):
        if ThemedDialog.question(self, "Einstellungen zurücksetzen",
                                  "Alle Einstellungen auf Standard zurücksetzen?\n\nDies kann nicht rückgängig gemacht werden.",
                                  dark=(self._theme == "dark")):
            self._settings = cfg_reset()
            self._restore_settings()
            self._apply_theme(self._settings.get("theme", "light"), save=False)

    # ── Color helpers ──────────────────────────────────────────────────────────
    def _update_color_btn(self, btn, hex_color):
        c      = QColor(hex_color)
        dark   = (self._theme == "dark")
        border = "rgba(255,255,255,0.3)" if dark else "rgba(0,0,0,0.2)"
        tc     = "white" if c.lightness() < 128 else "black"
        btn.setStyleSheet(
            f"background:{hex_color}; color:{tc}; border-radius:8px;"
            f"padding:4px 14px; border:1px solid {border};")
        btn.setText(f"  {hex_color.upper()}  ")

    def _open_color_dialog(self, current, title):
        dialog = QColorDialog(QColor(current), self)
        dialog.setWindowTitle(title)
        dialog.setOption(QColorDialog.DontUseNativeDialog, True)
        if self._theme == "dark":
            pal = dialog.palette()
            pal.setColor(QPalette.Window,          QColor("#1E293B"))
            pal.setColor(QPalette.WindowText,      QColor("#F1F5F9"))
            pal.setColor(QPalette.Base,            QColor("#0F172A"))
            pal.setColor(QPalette.AlternateBase,   QColor("#1E293B"))
            pal.setColor(QPalette.Text,            QColor("#F1F5F9"))
            pal.setColor(QPalette.BrightText,      QColor("#FFFFFF"))
            pal.setColor(QPalette.Button,          QColor("#334155"))
            pal.setColor(QPalette.ButtonText,      QColor("#F1F5F9"))
            pal.setColor(QPalette.ToolTipBase,     QColor("#334155"))
            pal.setColor(QPalette.ToolTipText,     QColor("#F1F5F9"))
            pal.setColor(QPalette.Highlight,       QColor("#3B82F6"))
            pal.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
            pal.setColor(QPalette.Link,            QColor("#60A5FA"))
            pal.setColor(QPalette.LinkVisited,     QColor("#818CF8"))
            dialog.setPalette(pal)
            # Force readable text on all child labels and buttons inside the dialog
            dialog.setStyleSheet("""
                QLabel       { color: #F1F5F9; }
                QLineEdit    { color: #F1F5F9; background: #0F172A;
                               border: 1px solid #475569; border-radius: 4px; padding: 2px 6px; }
                QPushButton  { color: #F1F5F9; background: #334155;
                               border: 1px solid #475569; border-radius: 6px;
                               padding: 4px 12px; }
                QPushButton:hover { background: #3B82F6; border-color: #3B82F6; }
                QSpinBox     { color: #F1F5F9; background: #0F172A;
                               border: 1px solid #475569; border-radius: 4px; }
                QComboBox    { color: #F1F5F9; background: #0F172A;
                               border: 1px solid #475569; border-radius: 4px; }
            """)
        if dialog.exec_() == QColorDialog.Accepted:
            return dialog.selectedColor().name()
        return None

    # ── File pickers ───────────────────────────────────────────────────────────
    def _pick_bg_video(self):
        p, _ = QFileDialog.getOpenFileName(self, "Hintergrundvideo", "", "Video (*.mp4 *.mov *.avi *.mkv)")
        if p:
            self._bg_video_path = p
            self._bg_video_row.set_path(p);   self._bg_image_row.setEnabled(False)
            self._bg_video_row_a.set_path(p); self._bg_image_row_a.setEnabled(False)

    def _clear_bg_video(self):
        self._bg_video_path = None
        self._bg_video_row.set_path(None);   self._bg_image_row.setEnabled(True)
        self._bg_video_row_a.set_path(None); self._bg_image_row_a.setEnabled(True)

    def _pick_bg_image(self):
        p, _ = QFileDialog.getOpenFileName(self, "Hintergrundbild", "", "Bild (*.png *.jpg *.jpeg *.bmp)")
        if p:
            self._bg_image_path = p
            self._bg_image_row.set_path(p);   self._bg_video_row.setEnabled(False)
            self._bg_image_row_a.set_path(p); self._bg_video_row_a.setEnabled(False)

    def _clear_bg_image(self):
        self._bg_image_path = None
        self._bg_image_row.set_path(None);   self._bg_video_row.setEnabled(True)
        self._bg_image_row_a.set_path(None); self._bg_video_row_a.setEnabled(True)

    def _pick_music(self):
        p, _ = QFileDialog.getOpenFileName(self, "Musikdatei", "", "Audio (*.mp3 *.wav *.ogg *.aac)")
        if p:
            self._music_path = p
            self._music_row.set_path(p)
            self._music_row_a.set_path(p)

    def _clear_music(self):
        self._music_path = None
        self._music_row.set_path(None)
        self._music_row_a.set_path(None)

    def _pick_output(self):
        default_name = datetime.now().strftime("Intro - %d.%m.%Y")
        folder = QFileDialog.getExistingDirectory(self, "Speicherordner wählen")
        if folder:
            self._out_path = os.path.join(folder, f"{default_name}.mp4")
            self._out_row.set_path(self._out_path)
            self._out_row_a.set_path(self._out_path)

    def _clear_output(self):
        self._out_path = None
        self._out_row.set_path(None)
        self._out_row_a.set_path(None)

    def _pick_color(self):
        r = self._open_color_dialog(self._font_color, "Timer Schriftfarbe")
        if r: self._font_color = r; self._update_color_btn(self._color_btn, r)

    def _pick_sub_color(self):
        r = self._open_color_dialog(self._sub_color, "Untertitel Farbe")
        if r: self._sub_color = r; self._update_color_btn(self._sub_color_btn, r)

    # ── Images ─────────────────────────────────────────────────────────────────
    def _add_images(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Bilder", "", "Bilder (*.png *.jpg *.jpeg *.bmp *.webp)")
        if paths:
            self._image_paths.extend(paths); self._refresh_imgs()

    def _clear_images(self):
        self._image_paths = []; self._refresh_imgs()

    def _refresh_imgs(self):
        txt = ("\n".join(f"  • {os.path.basename(p)}" for p in self._image_paths)
               if self._image_paths else "  Keine Bilder ausgewählt")
        self._img_list.setPlainText(txt)

    # ── Toggles ────────────────────────────────────────────────────────────────
    def _toggle_subtitle(self, state):
        on = (state == 2)
        self._sub_edit.setEnabled(on)
        self._sub_size_step.setEnabled(on)
        self._sub_color_btn.setEnabled(on)

    def _toggle_intro_fade(self, state):
        self._intro_fade_step.setEnabled(state == 2)

    def _toggle_outro_fade(self, state):
        self._outro_fade_step.setEnabled(state == 2)

    # ── Render ─────────────────────────────────────────────────────────────────
    def _start_render(self):
        if not self._out_path:
            ThemedDialog.error(self, "Fehler", "Bitte einen Speicherort wählen!",
                               dark=(self._theme == "dark"))
            return
        if self._music_path and not _get_ffmpeg():
            ThemedDialog.error(self, "FFmpeg fehlt",
                "Für Hintergrundmusik wird FFmpeg benötigt.\n\n"
                "Bitte ffmpeg.exe unter assets/bin/ ablegen.",
                dark=(self._theme == "dark"))
            return

        self._save_settings()
        sub_text = self._sub_edit.toPlainText().strip() if self._sub_chk.isChecked() else ""

        self._create_btn.setVisible(False)
        self._cancel_btn.setVisible(True)
        self._progress.setValue(0)
        self._frames_lbl.setText(""); self._eta_lbl.setText(""); self._pct_lbl.setText("")
        self._render_start = time.time()

        config = {
            "bg_video":           self._bg_video_path,
            "bg_image":           self._bg_image_path,
            "music_path":         self._music_path,
            "music_loop":         self._music_loop_chk.isChecked(),
            "music_fadeout":      self._music_fadeout_chk.isChecked(),
            "music_fade_dur":     self._music_fade_step.value(),
            "intro_fade_enabled": self._intro_fade_chk.isChecked(),
            "intro_fade_dur":     self._intro_fade_step.value(),
            "outro_fade_enabled": self._outro_fade_chk.isChecked(),
            "outro_fade_dur":     self._outro_fade_step.value(),
            "timer_minutes":      self._timer_step.value(),
            "image_paths":        list(self._image_paths),
            "img_duration":       self._img_dur_step.value(),
            "timer_between":      self._timer_between_step.value(),
            "slider_loop":        self._slider_loop_chk.isChecked(),
            "slider_from":        self._slider_from_step.value(),
            "slider_until":       self._slider_until_step.value(),
            "fade_duration":      self._fade_step.value(),
            "font_path":          self._font_picker.get_font_path(),
            "font_color":         self._font_color,
            "output_path":        self._out_path,
            "subtitle_enabled":   self._sub_chk.isChecked(),
            "subtitle_text":      sub_text,
            "subtitle_size":      self._sub_size_step.value(),
            "subtitle_color":     self._sub_color,
            "subtitle_font":      self._font_picker.get_font_path(),
        }

        self._worker = RenderWorker(config)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_done)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    def _cancel_render(self):
        if self._thread and self._thread.isRunning():
            self._thread.requestInterruption()
            self._thread.quit()
            self._thread.wait(3000)
        self._on_done(False, "Abgebrochen")

    def _on_progress(self, value, msg, cur, total):
        self._progress.setValue(int(value * 1000))
        self._status_lbl.setText(msg)
        self._pct_lbl.setText(f"{int(value * 100)}%")
        if total > 0:
            self._frames_lbl.setText(f"Frame {cur:,} / {total:,}")
        if value > 0.01:
            elapsed = time.time() - self._render_start
            eta = (elapsed / value) * (1 - value)
            m, s = divmod(int(eta), 60)
            self._eta_lbl.setText(f"⏳ ETA: {m:02d}:{s:02d}")

    def _on_done(self, ok, msg):
        self._create_btn.setVisible(True)
        self._create_btn.setEnabled(True)
        self._cancel_btn.setVisible(False)
        self._eta_lbl.setText("")
        dark = (self._theme == "dark")
        if ok:
            self._progress.setValue(1000)
            self._pct_lbl.setText("100%")
            self._status_lbl.setText("✅  Fertig!")
            ThemedDialog.info(self, "🎉 Fertig!",
                              f"Video wurde erfolgreich gespeichert:\n\n{self._out_path}", dark=dark)
        else:
            if "Abgebrochen" in msg:
                self._progress.setValue(0); self._pct_lbl.setText("")
                self._status_lbl.setText("⛔  Abgebrochen")
            else:
                self._status_lbl.setText("❌  Fehler!")
                ThemedDialog.error(self, "Fehler beim Rendern", msg[:600], dark=dark)


# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    icon_path = resource_path("assets/pictures/icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    settings = cfg_load()
    theme    = settings.get("theme", "light")
    splash   = SplashScreen(theme=theme)
    splash.show()
    window   = IntroMaker()
    splash.finished.connect(lambda: (window.show(), window.raise_(), window.activateWindow()))
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()