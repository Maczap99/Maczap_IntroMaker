import customtkinter as ctk
from PIL import Image, ImageTk
import os, math, time, threading

BG_DARK = "#0F172A"
ACCENT  = "#3B82F6"


class SplashScreen(ctk.CTkToplevel):
    """Zeigt logo.png 3 Sekunden mit animiertem Ladekreis."""

    LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "pictures", "logo.png")

    def __init__(self, on_done):
        super().__init__()
        self.on_done = on_done
        self.overrideredirect(True)          # kein Fensterrahmen
        self.configure(fg_color=BG_DARK)
        self.attributes("-topmost", True)

        W, H = 480, 340
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")

        # ── Logo ──────────────────────────────────────────────────────
        if os.path.exists(self.LOGO_PATH):
            raw   = Image.open(self.LOGO_PATH).convert("RGBA")
            ratio = min(320 / raw.width, 200 / raw.height)
            raw   = raw.resize((int(raw.width * ratio), int(raw.height * ratio)), Image.LANCZOS)
            self._logo_img = ctk.CTkImage(raw, size=(raw.width, raw.height))
            ctk.CTkLabel(self, image=self._logo_img, text="").pack(pady=(40, 8))
        else:
            ctk.CTkLabel(self, text="🎬", font=("Segoe UI", 64)).pack(pady=(40, 8))

        ctk.CTkLabel(self, text="Intro Maker",
                     font=("Segoe UI Black", 22, "bold"),
                     text_color="white").pack()
        ctk.CTkLabel(self, text="Wird geladen …",
                     font=("Segoe UI", 11), text_color="#64748B").pack(pady=4)

        # ── Canvas für Spinner ────────────────────────────────────────
        self._canvas = ctk.CTkCanvas(self, width=48, height=48,
                                      bg=BG_DARK, highlightthickness=0)
        self._canvas.pack(pady=16)

        self._angle   = 0
        self._running = True
        self._animate()

        # Timer: nach 3 s Splash schließen
        threading.Timer(3.0, self._finish).start()

    # ── Spinner-Animation ─────────────────────────────────────────────
    def _animate(self):
        if not self._running:
            return
        self._canvas.delete("all")
        cx, cy, r = 24, 24, 18
        # Hintergrundkreis
        self._canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                  outline="#1E293B", width=4)
        # Bogen
        start = self._angle
        self._canvas.create_arc(cx - r, cy - r, cx + r, cy + r,
                                  start=start, extent=260,
                                  outline=ACCENT, width=4, style="arc")
        self._angle = (self._angle + 8) % 360
        self.after(16, self._animate)     # ~60 fps

    def _finish(self):
        self._running = False
        self.after(0, self._close)

    def _close(self):
        self.destroy()
        self.on_done()