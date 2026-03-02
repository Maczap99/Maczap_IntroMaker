import customtkinter as ctk
from tkinter import filedialog, messagebox, colorchooser
from PIL import Image
import threading, os, time, sys
from video_generator import VideoGenerator
from splash import SplashScreen
from font_picker import FontPickerWidget
from config_manager import load as cfg_load, save as cfg_save

ACCENT   = "#3B82F6"
BG_DARK  = "#0F172A"
BG_MID   = "#1E293B"
BG_CARD  = "#263348"
TEXT_DIM = "#94A3B8"

ACCENT_L  = "#2563EB"
BG_DARK_L = "#F1F5F9"
BG_MID_L  = "#E2E8F0"
BG_CARD_L = "#FFFFFF"
TEXT_DIM_L = "#64748B"


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def card(parent, **kw):
    return ctk.CTkFrame(parent, fg_color=(BG_CARD_L, BG_CARD), corner_radius=12, **kw)


def section_label(parent, text):
    ctk.CTkLabel(parent, text=text, font=("Segoe UI", 13, "bold"),
                 text_color=(ACCENT_L, ACCENT)).pack(anchor="w", padx=16, pady=(14, 4))


def hint(parent, text):
    ctk.CTkLabel(parent, text=text, font=("Segoe UI", 11),
                 text_color=(TEXT_DIM_L, TEXT_DIM)).pack(anchor="w", padx=16, pady=(0, 8))


class Stepper(ctk.CTkFrame):
    def __init__(self, parent, variable, min_val, max_val, step=1,
                 width=60, fmt="{}", **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        self._var  = variable
        self._min  = min_val
        self._max  = max_val
        self._step = step
        self._fmt  = fmt
        ctk.CTkButton(self, text="−", width=30, height=30, corner_radius=6,
                      command=self._dec).pack(side="left")
        self._lbl = ctk.CTkLabel(self, text=fmt.format(variable.get()),
                                  font=("Segoe UI", 13, "bold"), width=width)
        self._lbl.pack(side="left")
        ctk.CTkButton(self, text="+", width=30, height=30, corner_radius=6,
                      command=self._inc).pack(side="left")

    def _dec(self):
        v = max(self._min, round(self._var.get() - self._step, 4))
        self._var.set(v); self._lbl.configure(text=self._fmt.format(v))

    def _inc(self):
        v = min(self._max, round(self._var.get() + self._step, 4))
        self._var.set(v); self._lbl.configure(text=self._fmt.format(v))


class IntroMaker(ctk.CTk):
    def __init__(self):
        self._settings = cfg_load()
        theme = self._settings.get("theme", "light")
        ctk.set_appearance_mode(theme)
        ctk.set_default_color_theme("blue")

        super().__init__()
        self.withdraw()
        self.title("Intro Maker")
        self.geometry("1020x920")
        self.minsize(920, 780)
        self.configure(fg_color=(BG_DARK_L, BG_DARK))

        # ── Fenster-Performance: kein Live-Redraw beim Verschieben ────
        self.resizable(True, True)

        # State
        self.bg_video_path  = ctk.StringVar()
        self.bg_image_path  = ctk.StringVar()
        self.music_path     = ctk.StringVar()
        self.out_path       = ctk.StringVar()
        self.image_paths    = []
        self.font_color     = "#FFFFFF"
        self.subtitle_color = "#FFFFFF"

        self.timer_min        = ctk.IntVar(value=5)
        self.slider_from      = ctk.IntVar(value=4)
        self.slider_until     = ctk.IntVar(value=1)
        self.img_duration     = ctk.IntVar(value=20)
        self.fade_duration    = ctk.DoubleVar(value=2.0)
        self.music_loop       = ctk.BooleanVar(value=True)
        self.music_fadeout    = ctk.BooleanVar(value=True)
        self.music_fade_dur   = ctk.IntVar(value=4)
        self.subtitle_enabled = ctk.BooleanVar(value=False)
        self.subtitle_text    = ctk.StringVar(value="")
        self.subtitle_size    = ctk.IntVar(value=40)

        self._theme_var = ctk.StringVar(value=theme)

        self._build_ui()
        self.after(100, self._show_splash)

    # ── SPLASH ────────────────────────────────────────────────────────
    def _show_splash(self):
        SplashScreen(on_done=self._after_splash)

    def _after_splash(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    # ── UI ────────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Header ────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=(BG_MID_L, BG_MID), corner_radius=0, height=72)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        # Logo (logo_header.png)
        logo_path = resource_path("assets/pictures/logo_header.png")
        if os.path.exists(logo_path):
            try:
                raw   = Image.open(logo_path).convert("RGBA")
                ratio = min(220 / raw.width, 52 / raw.height)
                new_w = int(raw.width  * ratio)
                new_h = int(raw.height * ratio)
                raw   = raw.resize((new_w, new_h), Image.LANCZOS)
                self._header_logo = ctk.CTkImage(raw, size=(new_w, new_h))
                ctk.CTkLabel(hdr, image=self._header_logo, text="",
                             fg_color="transparent").pack(side="left", padx=20, pady=10)
            except Exception:
                pass

        # Theme-Toggle rechts
        theme_frame = ctk.CTkFrame(hdr, fg_color="transparent")
        theme_frame.pack(side="right", padx=20)
        ctk.CTkLabel(theme_frame, text="☀️", font=("Segoe UI", 16)).pack(side="left", padx=(0, 4))
        self._theme_switch = ctk.CTkSwitch(
            theme_frame, text="", variable=self._theme_var,
            onvalue="dark", offvalue="light", width=46,
            command=self._toggle_theme)
        self._theme_switch.pack(side="left")
        if self._theme_var.get() == "dark":
            self._theme_switch.select()
        else:
            self._theme_switch.deselect()
        ctk.CTkLabel(theme_frame, text="🌙", font=("Segoe UI", 16)).pack(side="left", padx=(4, 0))

        # Body
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=12)

        left  = ctk.CTkScrollableFrame(body, fg_color="transparent", width=480)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        right = ctk.CTkScrollableFrame(body, fg_color="transparent", width=460)
        right.pack(side="right", fill="both", expand=True, padx=(8, 0))

        self._col_left(left)
        self._col_right(right)
        self._build_bottom()

    # ── THEME TOGGLE ──────────────────────────────────────────────────
    def _toggle_theme(self):
        new_theme = self._theme_var.get()
        ctk.set_appearance_mode(new_theme)
        self._settings["theme"] = new_theme
        cfg_save(self._settings)
        # Font-Vorschau neu rendern damit Hintergrundfarbe stimmt
        if hasattr(self, "font_picker"):
            self.font_picker.refresh_preview_theme()

    # ── LINKE SPALTE ──────────────────────────────────────────────────
    def _col_left(self, p):
        # Timer
        c = card(p); c.pack(fill="x", pady=(0, 10))
        section_label(c, "⏱  Timer-Dauer")
        hint(c, "Gesamtlänge des Countdown-Videos")
        row = ctk.CTkFrame(c, fg_color="transparent")
        row.pack(padx=16, pady=(0, 14))
        Stepper(row, self.timer_min, 1, 120, step=1, width=60, fmt="{} min").pack(side="left")

        # Hintergrund
        c2 = card(p); c2.pack(fill="x", pady=(0, 10))
        section_label(c2, "🎨  Hintergrund")
        hint(c2, "Video hat Vorrang vor Bild — beide optional (Standard: Weiß)")
        self._file_row(c2, "🎬  Video wählen", self.bg_video_path,
                       [("Video", "*.mp4 *.mov *.avi *.mkv")], self._pick_bg_video)
        self._file_row(c2, "🖼  Bild wählen", self.bg_image_path,
                       [("Bild", "*.png *.jpg *.jpeg *.bmp")], self._pick_bg_image)
        ctk.CTkFrame(c2, fg_color="transparent", height=6).pack()

        # Musik
        c3 = card(p); c3.pack(fill="x", pady=(0, 10))
        section_label(c3, "🎵  Hintergrundmusik")
        hint(c3, "Optional — MP3, WAV, OGG")
        self._file_row(c3, "🎵  Musikdatei wählen", self.music_path,
                       [("Audio", "*.mp3 *.wav *.ogg *.aac")], self._pick_music)
        opt = ctk.CTkFrame(c3, fg_color="transparent")
        opt.pack(fill="x", padx=16, pady=(4, 4))
        ctk.CTkSwitch(opt, text="Loop (wiederholen)", variable=self.music_loop,
                      font=("Segoe UI", 12)).pack(side="left", padx=(0, 20))
        ctk.CTkSwitch(opt, text="Fade-out am Ende", variable=self.music_fadeout,
                      font=("Segoe UI", 12)).pack(side="left")
        fade = ctk.CTkFrame(c3, fg_color="transparent")
        fade.pack(fill="x", padx=16, pady=(4, 14))
        ctk.CTkLabel(fade, text="Fade-out Dauer:", font=("Segoe UI", 12),
                     text_color=(TEXT_DIM_L, TEXT_DIM)).pack(side="left", padx=(0, 10))
        Stepper(fade, self.music_fade_dur, 1, 30, step=1, width=50, fmt="{} s").pack(side="left")

        # Ausgabe
        c7 = card(p); c7.pack(fill="x", pady=(0, 10))
        section_label(c7, "💾  Ausgabedatei")
        self._file_row(c7, "📁  Speicherort wählen", self.out_path, [], self._pick_output, save=True)
        ctk.CTkFrame(c7, fg_color="transparent", height=6).pack()

    # ── RECHTE SPALTE ─────────────────────────────────────────────────
    def _col_right(self, p):
        # Slider-Bilder
        c4 = card(p); c4.pack(fill="x", pady=(0, 10))
        section_label(c4, "🖼  Slider-Bilder")
        hint(c4, "Werden zwischen Countdown-Abschnitten eingeblendet")
        btn_row = ctk.CTkFrame(c4, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 6))
        ctk.CTkButton(btn_row, text="+ Bilder hinzufügen", width=180,
                      command=self._add_images).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_row, text="Liste leeren", width=120,
                      fg_color=("#CBD5E1", "#374151"), hover_color=("#94A3B8", "#4B5563"),
                      command=self._clear_images).pack(side="left")
        self.img_list_box = ctk.CTkTextbox(c4, height=80, font=("Segoe UI", 11),
                                            fg_color=("#E2E8F0", "#1a2535"), state="disabled")
        self.img_list_box.pack(fill="x", padx=16, pady=(0, 8))
        for label, var, fmt in [
            ("Slider erst ab:",  self.slider_from,  "{} min"),
            ("Slider bis max.:", self.slider_until, "{} min"),
            ("Dauer pro Bild:",  self.img_duration, "{} s"),
        ]:
            r = ctk.CTkFrame(c4, fg_color="transparent")
            r.pack(fill="x", padx=16, pady=3)
            ctk.CTkLabel(r, text=label, font=("Segoe UI", 12),
                         text_color=(TEXT_DIM_L, TEXT_DIM),
                         width=130, anchor="w").pack(side="left")
            Stepper(r, var, 1 if "bis" not in label else 0,
                    120, step=1, width=55, fmt=fmt).pack(side="left")
            ctk.CTkLabel(r, text="verbleibend" if "min" in fmt else "",
                         font=("Segoe UI", 11),
                         text_color=(TEXT_DIM_L, TEXT_DIM)).pack(side="left", padx=6)
        ctk.CTkFrame(c4, fg_color="transparent", height=6).pack()

        # Übergänge
        c5 = card(p); c5.pack(fill="x", pady=(0, 10))
        section_label(c5, "✨  Übergänge")
        fr = ctk.CTkFrame(c5, fg_color="transparent")
        fr.pack(fill="x", padx=16, pady=(0, 14))
        ctk.CTkLabel(fr, text="Fade-Dauer:", font=("Segoe UI", 12),
                     text_color=(TEXT_DIM_L, TEXT_DIM), width=100).pack(side="left")
        Stepper(fr, self.fade_duration, 0, 8, step=0.5, width=60, fmt="{} s").pack(side="left")

        # Font-Picker
        self.font_picker = FontPickerWidget(p, on_change=None)
        self.font_picker.pack(fill="x", pady=(0, 10))

        # Schriftfarbe Timer
        c6 = card(p); c6.pack(fill="x", pady=(0, 10))
        section_label(c6, "🎨  Schriftfarbe Timer")
        cr = ctk.CTkFrame(c6, fg_color="transparent")
        cr.pack(fill="x", padx=16, pady=(0, 14))
        ctk.CTkLabel(cr, text="Farbe:", font=("Segoe UI", 12),
                     text_color=(TEXT_DIM_L, TEXT_DIM)).pack(side="left", padx=(0, 12))
        self.color_btn = ctk.CTkButton(cr, text="  #FFFFFF  ",
                                        fg_color="#FFFFFF", text_color="#000000",
                                        hover_color="#DDDDDD", width=130,
                                        command=self._pick_color)
        self.color_btn.pack(side="left")

        # ── Untertitel ────────────────────────────────────────────────
        c8 = card(p); c8.pack(fill="x", pady=(0, 10))
        section_label(c8, "💬  Untertitel")
        hint(c8, "Wird unterhalb des Timers im Video angezeigt")

        sw_row = ctk.CTkFrame(c8, fg_color="transparent")
        sw_row.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkSwitch(sw_row, text="Untertitel aktivieren",
                      variable=self.subtitle_enabled,
                      font=("Segoe UI", 12),
                      command=self._toggle_subtitle).pack(side="left")

        # Einzige große Textbox
        self._subtitle_frame = ctk.CTkFrame(c8, fg_color="transparent")
        self._subtitle_frame.pack(fill="x", padx=16, pady=(0, 4))

        self._subtitle_entry = ctk.CTkTextbox(
            self._subtitle_frame,
            height=70,
            font=("Segoe UI", 13),
            fg_color=("#E2E8F0", "#1a2535"),
            wrap="word")
        self._subtitle_entry.pack(fill="x", pady=(0, 6))
        self._subtitle_entry.insert("1.0", "")

        # Optionen-Zeile unter der Textbox
        opt_row = ctk.CTkFrame(self._subtitle_frame, fg_color="transparent")
        opt_row.pack(fill="x", pady=(2, 0))
        ctk.CTkLabel(opt_row, text="Schriftgröße:", font=("Segoe UI", 12),
                     text_color=(TEXT_DIM_L, TEXT_DIM)).pack(side="left", padx=(0, 8))
        Stepper(opt_row, self.subtitle_size, 10, 120, step=2,
                width=50, fmt="{} pt").pack(side="left", padx=(0, 20))
        ctk.CTkLabel(opt_row, text="Farbe:", font=("Segoe UI", 12),
                     text_color=(TEXT_DIM_L, TEXT_DIM)).pack(side="left", padx=(0, 8))
        self.subtitle_color_btn = ctk.CTkButton(
            opt_row, text="  #FFFFFF  ",
            fg_color="#FFFFFF", text_color="#000000",
            hover_color="#DDDDDD", width=120,
            command=self._pick_subtitle_color)
        self.subtitle_color_btn.pack(side="left")

        ctk.CTkFrame(c8, fg_color="transparent", height=10).pack()
        # Initial deaktiviert
        self._set_subtitle_state("disabled")

    # ── BOTTOM BAR ────────────────────────────────────────────────────
    def _build_bottom(self):
        bar = ctk.CTkFrame(self, fg_color=(BG_MID_L, BG_MID), corner_radius=0, height=110)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        info = ctk.CTkFrame(bar, fg_color="transparent")
        info.pack(side="left", padx=20, fill="y")
        self.status_label = ctk.CTkLabel(info, text="Bereit", font=("Segoe UI", 12),
                                          text_color=(TEXT_DIM_L, TEXT_DIM))
        self.status_label.pack(anchor="w", pady=(14, 2))
        self.progress = ctk.CTkProgressBar(info, width=650, height=12, corner_radius=6,
                                            progress_color=(ACCENT_L, ACCENT))
        self.progress.pack(anchor="w")
        self.progress.set(0)
        det = ctk.CTkFrame(info, fg_color="transparent")
        det.pack(anchor="w", pady=(4, 0))
        self.frames_label = ctk.CTkLabel(det, text="", font=("Segoe UI", 10),
                                          text_color="#475569")
        self.frames_label.pack(side="left", padx=(0, 20))
        self.eta_label = ctk.CTkLabel(det, text="", font=("Segoe UI", 10),
                                       text_color="#475569")
        self.eta_label.pack(side="left")
        self.pct_label = ctk.CTkLabel(det, text="", font=("Segoe UI Bold", 11, "bold"),
                                       text_color=(ACCENT_L, ACCENT))
        self.pct_label.pack(side="left", padx=(20, 0))

        self.create_btn = ctk.CTkButton(bar, text="🎬  Video erstellen",
                                         font=("Segoe UI", 15, "bold"),
                                         height=52, width=230, corner_radius=10,
                                         fg_color=(ACCENT_L, ACCENT),
                                         hover_color="#1D4ED8",
                                         command=self._start)
        self.create_btn.pack(side="right", padx=24, pady=28)

    # ── FILE ROW ──────────────────────────────────────────────────────
    def _file_row(self, parent, btn_text, var, filetypes, cmd, save=False):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 8))
        lbl = ctk.CTkLabel(row, text=var.get() or "Nichts ausgewählt",
                            font=("Segoe UI", 11), text_color=(TEXT_DIM_L, TEXT_DIM),
                            fg_color=("#E2E8F0", "#1a2535"), corner_radius=6,
                            width=260, height=28, anchor="w")
        lbl.pack(side="left", padx=(0, 8))
        var.trace_add("write", lambda *_: lbl.configure(
            text=os.path.basename(var.get()) if var.get() else "Nichts ausgewählt"))
        ctk.CTkButton(row, text=btn_text, width=190, height=28,
                      fg_color=("#CBD5E1", "#374151"),
                      hover_color=("#94A3B8", "#4B5563"),
                      command=cmd).pack(side="left")

    # ── SUBTITLE TOGGLE ───────────────────────────────────────────────
    def _toggle_subtitle(self):
        state = "normal" if self.subtitle_enabled.get() else "disabled"
        self._set_subtitle_state(state)

    def _set_subtitle_state(self, state):
        try:
            self._subtitle_entry.configure(state=state)
        except Exception:
            pass
        for widget in self._subtitle_frame.winfo_children():
            if widget == self._subtitle_entry:
                continue
            try:
                widget.configure(state=state)
            except Exception:
                pass
            for child in widget.winfo_children():
                try:
                    child.configure(state=state)
                except Exception:
                    pass

    # ── FILE PICKERS ──────────────────────────────────────────────────
    def _pick_bg_video(self):
        p = filedialog.askopenfilename(filetypes=[("Video", "*.mp4 *.mov *.avi *.mkv")])
        if p: self.bg_video_path.set(p)

    def _pick_bg_image(self):
        p = filedialog.askopenfilename(filetypes=[("Bild", "*.png *.jpg *.jpeg *.bmp")])
        if p: self.bg_image_path.set(p)

    def _pick_music(self):
        p = filedialog.askopenfilename(filetypes=[("Audio", "*.mp3 *.wav *.ogg *.aac")])
        if p: self.music_path.set(p)

    def _pick_output(self):
        p = filedialog.asksaveasfilename(defaultextension=".mp4",
                                          filetypes=[("MP4", "*.mp4")],
                                          initialfile="intro_output.mp4")
        if p: self.out_path.set(p)

    def _pick_color(self):
        c = colorchooser.askcolor(color=self.font_color, title="Timer Schriftfarbe")
        if c[1]:
            self.font_color = c[1]
            light = self._is_light(c[1])
            self.color_btn.configure(fg_color=c[1], text=f"  {c[1].upper()}  ",
                                      text_color="black" if light else "white",
                                      hover_color="#CCCCCC" if light else "#333333")

    def _pick_subtitle_color(self):
        c = colorchooser.askcolor(color=self.subtitle_color, title="Untertitel Farbe")
        if c[1]:
            self.subtitle_color = c[1]
            light = self._is_light(c[1])
            self.subtitle_color_btn.configure(fg_color=c[1], text=f"  {c[1].upper()}  ",
                                               text_color="black" if light else "white",
                                               hover_color="#CCCCCC" if light else "#333333")

    def _is_light(self, h):
        h = h.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return (r * 299 + g * 587 + b * 114) / 1000 > 128

    def _add_images(self):
        paths = filedialog.askopenfilenames(
            filetypes=[("Bilder", "*.png *.jpg *.jpeg *.bmp *.webp")])
        if paths:
            self.image_paths.extend(paths)
            self._refresh_images()

    def _clear_images(self):
        self.image_paths = []
        self._refresh_images()

    def _refresh_images(self):
        self.img_list_box.configure(state="normal")
        self.img_list_box.delete("1.0", "end")
        if self.image_paths:
            for p in self.image_paths:
                self.img_list_box.insert("end", f"  • {os.path.basename(p)}\n")
        else:
            self.img_list_box.insert("end", "  Keine Bilder ausgewählt")
        self.img_list_box.configure(state="disabled")

    # ── GENERIERUNG ───────────────────────────────────────────────────
    def _start(self):
        if not self.out_path.get():
            messagebox.showerror("Fehler", "Bitte einen Speicherort wählen!")
            return

        # Untertitel-Text aus Textbox lesen
        sub_text = ""
        if self.subtitle_enabled.get():
            sub_text = self._subtitle_entry.get("1.0", "end").strip()

        self.create_btn.configure(state="disabled", text="⏳  Wird gerendert …")
        self.progress.set(0)
        self.frames_label.configure(text="")
        self.eta_label.configure(text="")
        self.pct_label.configure(text="")
        self._render_start_time = time.time()

        config = {
            "bg_video":         self.bg_video_path.get() or None,
            "bg_image":         self.bg_image_path.get() or None,
            "music_path":       self.music_path.get() or None,
            "music_loop":       self.music_loop.get(),
            "music_fadeout":    self.music_fadeout.get(),
            "music_fade_dur":   self.music_fade_dur.get(),
            "timer_minutes":    self.timer_min.get(),
            "image_paths":      list(self.image_paths),
            "img_duration":     self.img_duration.get(),
            "slider_from":      self.slider_from.get(),
            "slider_until":     self.slider_until.get(),
            "fade_duration":    self.fade_duration.get(),
            "font_path":        self.font_picker.get_font_path(),
            "font_color":       self.font_color,
            "output_path":      self.out_path.get(),
            "subtitle_enabled": self.subtitle_enabled.get(),
            "subtitle_text":    sub_text,
            "subtitle_size":    self.subtitle_size.get(),
            "subtitle_color":   self.subtitle_color,
            "subtitle_font":    self.font_picker.get_font_path(),
        }

        gen = VideoGenerator(config, self._on_progress, self._on_done)
        threading.Thread(target=gen.generate, daemon=True).start()

    def _on_progress(self, value, msg, frame_info=None):
        self.progress.set(value)
        self.status_label.configure(text=msg)
        self.pct_label.configure(text=f"{int(value * 100)}%")
        if frame_info:
            cur, total = frame_info
            self.frames_label.configure(text=f"Frame {cur:,} / {total:,}")
        if value > 0.01:
            elapsed = time.time() - self._render_start_time
            eta_sec = (elapsed / value) * (1 - value)
            m, s    = divmod(int(eta_sec), 60)
            self.eta_label.configure(text=f"⏳ ETA: {m:02d}:{s:02d}")

    def _on_done(self, ok, msg):
        self.create_btn.configure(state="normal", text="🎬  Video erstellen")
        self.eta_label.configure(text="")
        if ok:
            self.progress.set(1.0)
            self.pct_label.configure(text="100%")
            self.status_label.configure(text="✅  Fertig!")
            messagebox.showinfo("🎉 Fertig!", f"Video gespeichert:\n{self.out_path.get()}")
        else:
            self.status_label.configure(text="❌  Fehler!")
            messagebox.showerror("Fehler beim Rendern", msg[:800])


if __name__ == "__main__":
    app = IntroMaker()
    app.mainloop()