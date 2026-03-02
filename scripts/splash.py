import customtkinter as ctk
from PIL import Image
import os, threading, sys

def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

LOGO_PATH = resource_path("assets/pictures/logo.png")

# Farben je nach Theme
THEMES = {
    "light": {
        "bg":      "#F1F5F9",
        "accent":  "#2563EB",
        "text":    "#0F172A",
        "subtext": "#64748B",
        "ring_bg": "#E2E8F0",
    },
    "dark": {
        "bg":      "#0F172A",
        "accent":  "#3B82F6",
        "text":    "#FFFFFF",
        "subtext": "#64748B",
        "ring_bg": "#1E293B",
    },
}


class SplashScreen(ctk.CTkToplevel):
    def __init__(self, on_done):
        super().__init__()
        self.on_done = on_done

        # Theme auslesen
        mode   = ctk.get_appearance_mode().lower()   # "light" / "dark"
        colors = THEMES.get(mode, THEMES["dark"])

        self.overrideredirect(True)
        self.configure(fg_color=colors["bg"])
        self.attributes("-topmost", True)

        W, H = 480, 340
        sw   = self.winfo_screenwidth()
        sh   = self.winfo_screenheight()
        self.geometry(f"{W}x{H}+{(sw - W) // 2}+{(sh - H) // 2}")

        # Logo
        if os.path.exists(LOGO_PATH):
            try:
                raw   = Image.open(LOGO_PATH).convert("RGBA")
                ratio = min(320 / raw.width, 180 / raw.height)
                new_w = int(raw.width  * ratio)
                new_h = int(raw.height * ratio)
                raw   = raw.resize((new_w, new_h), Image.LANCZOS)
                self._logo_img = ctk.CTkImage(raw, size=(new_w, new_h))
                ctk.CTkLabel(self, image=self._logo_img, text="",
                             fg_color=colors["bg"]).pack(pady=(36, 8))
            except Exception:
                ctk.CTkLabel(self, text="🎬", font=("Segoe UI", 64),
                             fg_color=colors["bg"]).pack(pady=(36, 8))
        else:
            ctk.CTkLabel(self, text="🎬", font=("Segoe UI", 64),
                         fg_color=colors["bg"]).pack(pady=(36, 8))

        ctk.CTkLabel(self, text="Intro Maker",
                     font=("Segoe UI Black", 22, "bold"),
                     text_color=colors["text"],
                     fg_color=colors["bg"]).pack()

        ctk.CTkLabel(self, text="Wird geladen …",
                     font=("Segoe UI", 11),
                     text_color=colors["subtext"],
                     fg_color=colors["bg"]).pack(pady=4)

        # Spinner-Canvas
        self._colors = colors
        self._canvas = ctk.CTkCanvas(self, width=48, height=48,
                                      bg=colors["bg"], highlightthickness=0)
        self._canvas.pack(pady=14)
        self._angle   = 0
        self._running = True
        self._animate()
        threading.Timer(3.0, self._finish).start()

    def _animate(self):
        if not self._running:
            return
        self._canvas.delete("all")
        cx, cy, r = 24, 24, 18
        self._canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                  outline=self._colors["ring_bg"], width=4)
        self._canvas.create_arc(cx - r, cy - r, cx + r, cy + r,
                                 start=self._angle, extent=260,
                                 outline=self._colors["accent"], width=4, style="arc")
        self._angle = (self._angle + 8) % 360
        self.after(16, self._animate)

    def _finish(self):
        self._running = False
        self.after(0, self._close)

    def _close(self):
        self.destroy()
        self.on_done()