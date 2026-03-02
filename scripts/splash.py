import customtkinter as ctk
from PIL import Image
import os, threading
import sys

BG_DARK = "#0F172A"
ACCENT  = "#3B82F6"

# Hilfsfunktion für PyInstaller
def resource_path(relative_path):
    """Gibt den korrekten Pfad für PyInstaller oder normale Ausführung zurück."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# Pfad relativ zu scripts/ → assets/pictures/logo.png
LOGO_PATH = resource_path("assets/pictures/logo.png")


class SplashScreen(ctk.CTkToplevel):
    def __init__(self, on_done):
        super().__init__()
        self.on_done = on_done
        self.overrideredirect(True)
        self.configure(fg_color=BG_DARK)
        self.attributes("-topmost", True)

        W, H = 480, 340
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")

        if os.path.exists(LOGO_PATH):
            raw   = Image.open(LOGO_PATH).convert("RGBA")
            ratio = min(320 / raw.width, 200 / raw.height)
            raw   = raw.resize((int(raw.width * ratio), int(raw.height * ratio)), Image.LANCZOS)
            self._logo_img = ctk.CTkImage(raw, size=(raw.width, raw.height))
            ctk.CTkLabel(self, image=self._logo_img, text="").pack(pady=(40, 8))
        else:
            ctk.CTkLabel(self, text="🎬", font=("Segoe UI", 64)).pack(pady=(40, 8))

        ctk.CTkLabel(self, text="Intro Maker",
                     font=("Segoe UI Black", 22, "bold"), text_color="white").pack()
        ctk.CTkLabel(self, text="Wird geladen …",
                     font=("Segoe UI", 11), text_color="#64748B").pack(pady=4)

        self._canvas = ctk.CTkCanvas(self, width=48, height=48,
                                      bg=BG_DARK, highlightthickness=0)
        self._canvas.pack(pady=16)
        self._angle   = 0
        self._running = True
        self._animate()
        threading.Timer(3.0, self._finish).start()

    def _animate(self):
        if not self._running:
            return
        self._canvas.delete("all")
        cx, cy, r = 24, 24, 18
        self._canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline="#1E293B", width=4)
        self._canvas.create_arc(cx-r, cy-r, cx+r, cy+r,
                                 start=self._angle, extent=260,
                                 outline=ACCENT, width=4, style="arc")
        self._angle = (self._angle + 8) % 360
        self.after(16, self._animate)

    def _finish(self):
        self._running = False
        self.after(0, self._close)

    def _close(self):
        self.destroy()
        self.on_done()