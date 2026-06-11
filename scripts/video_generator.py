# video_generator.py
import cv2, numpy as np, os, traceback, subprocess, shutil, sys
from PIL import Image, ImageDraw, ImageFont

_STARTUPINFO = None
if sys.platform == "win32":
    _STARTUPINFO = subprocess.STARTUPINFO()
    _STARTUPINFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    _STARTUPINFO.wShowWindow = subprocess.SW_HIDE


def _get_ffmpeg() -> str | None:
    """Locate ffmpeg: bundled binary first, then system PATH."""
    if hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    else:
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    bundled = os.path.join(base, "assets", "bin", "ffmpeg.exe")
    if os.path.isfile(bundled):
        return os.path.normpath(bundled)
    return shutil.which("ffmpeg")


def _run_ffmpeg(cmd: list):
    result = subprocess.run(
        cmd, check=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        startupinfo=_STARTUPINFO
    )
    return result


def _hex_to_rgb(hex_color: str) -> tuple:
    """Convert a '#RRGGBB' hex string to an (R, G, B) integer tuple."""
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _fit_image(img_pil: Image.Image, w: int, h: int,
               fill_color_hex: str = "#000000") -> Image.Image:
    """
    Fit *img_pil* into a w x h canvas while preserving its aspect ratio.
    Any remaining area is filled with *fill_color_hex*.
    """
    r, g, b = _hex_to_rgb(fill_color_hex)
    canvas  = Image.new("RGB", (w, h), (r, g, b))
    scale   = min(w / img_pil.width, h / img_pil.height)
    new_w   = int(img_pil.width  * scale)
    new_h   = int(img_pil.height * scale)
    resized  = img_pil.resize((new_w, new_h), Image.LANCZOS)
    offset_x = (w - new_w) // 2
    offset_y = (h - new_h) // 2
    canvas.paste(resized, (offset_x, offset_y))
    return canvas


def _subtitle_layout(w: int, h: int, timer_y: int, timer_h: int,
                     sub_offset: int, sub_size: int) -> int:
    """Return the y-coordinate at which subtitle text begins."""
    base_gap  = int(min(w, h) * 0.04)
    extra_gap = sub_offset * sub_size
    return timer_y + timer_h + base_gap + extra_gap


def _smoothstep(t: float) -> float:
    """Smooth cubic easing - t is clamped to [0, 1]."""
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


class _CancelledError(Exception):
    """Raised internally when the cancel event is set during rendering."""


class VideoGenerator:
    def __init__(self, config, progress_cb, done_cb, cancel_event=None):
        self.cfg           = config
        self.cb            = progress_cb
        self.done          = done_cb
        self._cancel_event = cancel_event
        # Fortschritts-Bereich (0..1) auf den self._emit seine Werte abbildet.
        # Wird in generate() gesetzt, damit Intro und Outro sich die Leiste teilen.
        self._prog_lo = 0.0
        self._prog_hi = 1.0

    def _check_cancel(self):
        """Raise _CancelledError if the cancel event has been set."""
        if self._cancel_event and self._cancel_event.is_set():
            raise _CancelledError()

    def _emit(self, value, msg, frame_info=None):
        """Fortschritt melden, abgebildet auf den aktuellen [_prog_lo, _prog_hi]-Bereich.

        So kann das Intro z. B. 0-85 % belegen und das Outro 85-100 %,
        ohne dass die einzelnen Render-Methoden davon wissen muessen."""
        lo, hi = self._prog_lo, self._prog_hi
        self.cb(lo + (hi - lo) * value, msg, frame_info)

    # -- Gemeinsamer Video-Writer (FFmpeg-Pipe oder OpenCV-Fallback) ----------
    def _open_video_writer(self, tmp_video, w, h, fps, ffmpeg_path):
        """Open a frame sink for *tmp_video*.

        Prefers an FFmpeg rawvideo pipe (H.264, high quality); if FFmpeg is
        unavailable, falls back to OpenCV's mp4v VideoWriter.

        Returns a tuple ``(proc, write_frame, close)`` where *proc* is the
        FFmpeg subprocess (or ``None`` in the fallback case), *write_frame(f)*
        pushes a single BGR frame, and *close()* finalises the file.
        Used by both the intro render (_run) and the outro render
        (_render_outro_video) so the encoder setup lives in one place."""
        if ffmpeg_path:
            ff_cmd = [
                ffmpeg_path, "-y",
                "-f", "rawvideo", "-vcodec", "rawvideo",
                "-pix_fmt", "bgr24", "-s", f"{w}x{h}",
                "-r", str(fps), "-i", "pipe:0",
                "-c:v", "libx264", "-preset", "fast",
                "-crf", "18", "-pix_fmt", "yuv420p",
                tmp_video
            ]
            ff_proc = subprocess.Popen(
                ff_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                startupinfo=_STARTUPINFO
            )

            def write_frame(f):
                if ff_proc.poll() is not None:
                    err = ff_proc.stderr.read().decode(errors="replace")
                    raise RuntimeError(
                        f"FFmpeg exited (code {ff_proc.returncode}):\n{err}")
                try:
                    ff_proc.stdin.write(f.tobytes())
                except (BrokenPipeError, OSError):
                    err = ff_proc.stderr.read().decode(errors="replace")
                    raise RuntimeError(
                        f"FFmpeg pipe error (code {ff_proc.returncode}):\n{err}")

            def close():
                ff_proc.stdin.close()
                ff_proc.stderr.close()
                ff_proc.wait()
                if ff_proc.returncode not in (0, None):
                    raise RuntimeError(
                        f"FFmpeg closed with code {ff_proc.returncode}")

            return ff_proc, write_frame, close

        # -- Fallback: OpenCV writer --
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(tmp_video, fourcc, fps, (w, h))

        def write_frame(f):
            writer.write(f)

        def close():
            writer.release()

        return None, write_frame, close

    def generate(self):
        cfg       = self.cfg
        out_path  = cfg.get("output_path", "")
        tmp_video = out_path.replace(".mp4", "_noaudio.mp4") if out_path else ""

        # Outro-Video: nur rendern wenn aktiviert, ein Zielpfad gesetzt ist
        # UND es ueberhaupt Slider-Bilder gibt.
        outro_out = cfg.get("outro_video_output_path", "") or ""
        outro_tmp = outro_out.replace(".mp4", "_noaudio.mp4") if outro_out else ""
        do_outro  = bool(cfg.get("outro_video_enabled", False)
                         and outro_out
                         and cfg.get("image_paths"))

        try:
            # Intro belegt 0-85 % der Fortschrittsanzeige wenn ein Outro folgt,
            # sonst die vollen 0-100 %.
            self._prog_lo, self._prog_hi = 0.0, (0.85 if do_outro else 1.0)
            self._run()

            if do_outro:
                # Outro belegt die restlichen 85-100 %.
                self._prog_lo, self._prog_hi = 0.85, 1.0
                self._render_outro_video(outro_out)

            self.done(True, "OK")
        except _CancelledError:
            # Beim Abbruch alle (Zwischen-)Dateien von Intro UND Outro aufraeumen.
            for path in [tmp_video, out_path, outro_tmp, outro_out]:
                if path and os.path.isfile(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass
            self.done(False, "CANCELLED")
        except Exception:
            self.done(False, traceback.format_exc())

    # -- Main render loop (INTRO) ----------------------------------------------
    def _run(self):
        cfg       = self.cfg
        fps       = 30
        total_sec = cfg["timer_minutes"] * 60
        out_path  = cfg["output_path"]

        # -- Background ---------------------------------------------------------
        bg_cap    = None
        bg_static = None
        w, h      = 1920, 1080
        bg_total  = 0

        if cfg["bg_video"]:
            bg_cap   = cv2.VideoCapture(cfg["bg_video"])
            w        = int(bg_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h        = int(bg_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            bg_total = int(bg_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        elif cfg["bg_image"]:
            img = Image.open(cfg["bg_image"]).convert("RGB").resize((w, h))
            bg_static = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        else:
            r, g, b   = _hex_to_rgb(cfg.get("bg_color", "#000000"))
            bg_static = np.full((h, w, 3), (b, g, r), dtype=np.uint8)

        # -- Slider images ------------------------------------------------------
        slider_imgs = []
        fill_color  = cfg.get("slider_fill_color", "#000000")

        for p in cfg.get("image_paths", []):
            try:
                raw_img = Image.open(p).convert("RGB")
                fitted  = _fit_image(raw_img, w, h, fill_color)
                slider_imgs.append(cv2.cvtColor(np.array(fitted), cv2.COLOR_RGB2BGR))
            except Exception:
                pass

        # -- Settings -----------------------------------------------------------
        slider_from   = cfg["slider_from"]  * 60
        slider_until  = cfg["slider_until"] * 60
        img_dur       = float(cfg["img_duration"])
        timer_between = float(cfg.get("timer_between", 0))
        slider_loop   = cfg.get("slider_loop", True)
        fade_dur      = float(cfg["fade_duration"])

        intro_fade         = cfg.get("intro_fade_enabled", False)
        outro_slide_active = (cfg.get("outro_slide_enabled", False) and
                              cfg.get("outro_slide_text", "").strip())
        outro_fade         = cfg.get("outro_fade_enabled", False) and not outro_slide_active
        intro_fade_dur     = float(cfg.get("intro_fade_dur", 3.0))
        outro_fade_dur     = float(cfg.get("outro_fade_dur", 3.0))

        # -- Overlay / position / appearance settings --------------------------
        overlay_mode     = cfg.get("slider_timer_overlay", False)
        overlay_pos      = cfg.get("slider_timer_overlay_position", "right_bottom")
        # backward compat: old "right"/"left" keys
        if overlay_pos == "right": overlay_pos = "right_bottom"
        if overlay_pos == "left":  overlay_pos = "left_bottom"
        overlay_size_pct      = cfg.get("slider_timer_size", 6.5) / 100.0
        overlay_bg_transparent = cfg.get("slider_timer_bg_transparent", True)
        overlay_bg_color       = cfg.get("slider_timer_bg_color", "#FFFFFF")

        # -- Fonts --------------------------------------------------------------
        font_path     = cfg.get("font_path")
        sub_font_path = cfg.get("subtitle_font") or font_path
        self._pil_fonts = {}

        def get_font(path, size):
            key = (path, size)
            if key not in self._pil_fonts:
                try:
                    self._pil_fonts[key] = (
                        ImageFont.truetype(path, size) if path
                        else ImageFont.load_default()
                    )
                except Exception:
                    self._pil_fonts[key] = ImageFont.load_default()
            return self._pil_fonts[key]

        # -- Timeline -----------------------------------------------------------
        segments     = self._build_segments(
            total_sec, slider_from, slider_until,
            slider_imgs, img_dur, timer_between, slider_loop)
        total_frames = int(total_sec * fps)

        # -- Start frame sink (FFmpeg pipe or OpenCV fallback) -----------------
        tmp_video   = out_path.replace(".mp4", "_noaudio.mp4")
        ffmpeg_path = _get_ffmpeg()
        ff_proc, write_frame, _close_writer = self._open_video_writer(
            tmp_video, w, h, fps, ffmpeg_path)

        black      = np.zeros((h, w, 3), dtype=np.uint8)
        last_frame = black.copy()

        # -- Render frames ------------------------------------------------------
        bg_frame_idx = 0
        elapsed      = 0.0
        n_segs       = len(segments)

        try:
            for seg_idx, (seg_type, seg_dur) in enumerate(segments):
                seg_frames = int(seg_dur * fps)

                # Look one step ahead/behind to decide crossfade behaviour
                prev_seg      = segments[seg_idx - 1] if seg_idx > 0 else None
                next_seg      = segments[seg_idx + 1] if seg_idx < n_segs - 1 else None
                prev_is_slide = (prev_seg is not None and isinstance(prev_seg[0], int))
                next_is_slide = (next_seg is not None and isinstance(next_seg[0], int))

                for f in range(seg_frames):
                    time_left  = max(0.0, total_sec - elapsed)
                    pos_in_seg = f / fps

                    # -- Advance / loop background video ----------------------
                    if bg_cap:
                        if bg_frame_idx >= bg_total - 1:
                            bg_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            bg_frame_idx = 0
                        ret, bg = bg_cap.read()
                        if not ret:
                            bg_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            ret, bg = bg_cap.read()
                        bg_frame_idx += 1
                    else:
                        bg = bg_static.copy()

                    # -- Compose frame -----------------------------------------
                    if seg_type == "timer":
                        # Pure timer frame - always drawn normally
                        frame = self._draw_timer_and_subtitle(
                            bg.copy(), time_left, cfg, w, h,
                            get_font, font_path, sub_font_path)

                    else:
                        # -- Slide segment -----------------------------------------
                        img_idx = seg_type % len(slider_imgs)
                        slide   = slider_imgs[img_idx]

                        # Pre-compute next slide image (needed for S->S crossfade)
                        if next_is_slide:
                            next_slide = slider_imgs[next_seg[0] % len(slider_imgs)]
                        else:
                            next_slide = None

                        # Detect which fade phase we are in
                        in_fade_in  = (fade_dur > 0
                                       and not prev_is_slide
                                       and pos_in_seg < fade_dur)
                        in_fade_out = (fade_dur > 0
                                       and pos_in_seg > seg_dur - fade_dur)

                        if overlay_mode:
                            # -------------------------------------------------
                            # OVERLAY MODE
                            # Timer is always visible; it shrinks and moves to a
                            # corner while a slide is shown, then returns to
                            # centre when the slide ends.
                            #
                            # anim_t = 0.0 -> timer at centre, full size
                            # anim_t = 1.0 -> timer in corner, small
                            # -------------------------------------------------
                            if in_fade_in:
                                # Entering slide from a timer segment:
                                # slide fades in over raw background while
                                # timer simultaneously moves toward the corner.
                                a      = pos_in_seg / fade_dur
                                anim_t = a
                                base   = cv2.addWeighted(slide, a, bg, 1.0 - a, 0)

                            elif in_fade_out and next_is_slide:
                                # Leaving into another slide (timer_between=0):
                                # crossfade directly to the next slide image,
                                # timer stays pinned in the corner.
                                a      = (seg_dur - pos_in_seg) / fade_dur
                                anim_t = 1.0
                                base   = cv2.addWeighted(slide, a, next_slide, 1.0 - a, 0)

                            elif in_fade_out and not next_is_slide:
                                # Leaving to a timer segment:
                                # slide fades back out while timer grows back
                                # toward the centre.
                                a      = (seg_dur - pos_in_seg) / fade_dur
                                anim_t = a
                                base   = cv2.addWeighted(slide, a, bg, 1.0 - a, 0)

                            else:
                                # Steady state (or entering after a slide where
                                # the prev slide's fade-out already covered us):
                                anim_t = 1.0
                                base   = slide.copy()

                            frame = self._draw_timer_animated(
                                base, time_left, cfg, w, h,
                                get_font, font_path, anim_t, overlay_pos,
                                size_pct=overlay_size_pct,
                                bg_transparent=overlay_bg_transparent,
                                bg_color_hex=overlay_bg_color)

                        else:
                            # -------------------------------------------------
                            # STANDARD MODE  (slides fully cover the timer)
                            # -------------------------------------------------
                            if in_fade_in:
                                # Blend: slide fades in over a timer frame
                                a        = pos_in_seg / fade_dur
                                timer_bg = self._draw_timer_and_subtitle(
                                    bg.copy(), time_left, cfg, w, h,
                                    get_font, font_path, sub_font_path)
                                frame = cv2.addWeighted(slide, a, timer_bg, 1.0 - a, 0)

                            elif in_fade_out and next_is_slide:
                                # Direct slide->slide crossfade (timer_between=0)
                                a     = (seg_dur - pos_in_seg) / fade_dur
                                frame = cv2.addWeighted(slide, a, next_slide, 1.0 - a, 0)

                            elif in_fade_out and not next_is_slide:
                                # Slide fades out back to timer
                                a        = (seg_dur - pos_in_seg) / fade_dur
                                timer_bg = self._draw_timer_and_subtitle(
                                    bg.copy(), time_left, cfg, w, h,
                                    get_font, font_path, sub_font_path)
                                frame = cv2.addWeighted(slide, a, timer_bg, 1.0 - a, 0)

                            else:
                                # Steady state (also covers prev_is_slide fade-in
                                # which was already handled by the previous
                                # segment's fade-out)
                                frame = slide.copy()

                    # -- Global intro / outro fades ----------------------------
                    if intro_fade and elapsed < intro_fade_dur:
                        a = elapsed / intro_fade_dur
                        frame = cv2.addWeighted(frame, a, black, 1.0 - a, 0)

                    if outro_fade and elapsed > total_sec - outro_fade_dur:
                        a = (total_sec - elapsed) / outro_fade_dur
                        a = max(0.0, min(1.0, a))
                        frame = cv2.addWeighted(frame, a, black, 1.0 - a, 0)

                    write_frame(frame)
                    elapsed   += 1.0 / fps
                    last_frame = frame
                    self._check_cancel()

                    frame_idx = int(elapsed * fps)
                    if frame_idx % 15 == 0:
                        pct = elapsed / total_sec
                        m   = int(time_left // 60)
                        s   = int(time_left % 60)
                        self._emit(min(pct, 0.95),
                                   f"\u23f3 Rendering ... {m:02d}:{s:02d}  ({int(pct*100)}%)",
                                   frame_info=(frame_idx, total_frames))

            # -- Outro slide (= Abschluss-Bild, EIN Standbild im Intro) --------
            outro_enabled    = cfg.get("outro_slide_enabled", False)
            outro_text       = cfg.get("outro_slide_text", "").strip()
            outro_color      = cfg.get("outro_slide_color", "#FFFFFF")
            outro_bg_image   = cfg.get("outro_slide_bg_image")
            outro_bg_color   = cfg.get("outro_slide_bg_color", "#000000")
            outro_font_size  = int(cfg.get("outro_slide_font_size", 80))
            outro_font_path  = cfg.get("outro_slide_font") or font_path
            outro_dur        = float(cfg.get("outro_slide_duration", 5))
            outro_fade_in    = float(cfg.get("outro_slide_fade_in", 1))
            outro_fade_out   = float(cfg.get("outro_slide_fade_out", 1))

            if outro_enabled and outro_text:
                outro_base   = self._draw_outro_slide(
                    outro_text, outro_color,
                    outro_bg_image, outro_bg_color,
                    outro_font_size, outro_font_path, w, h, get_font)
                outro_frames = int(outro_dur * fps)

                for f in range(outro_frames):
                    frame = outro_base.copy()
                    t     = f / fps

                    if outro_fade_in > 0 and t < outro_fade_in:
                        a = t / outro_fade_in
                        frame = cv2.addWeighted(frame, a, last_frame, 1.0 - a, 0)

                    if outro_fade_out > 0 and t > outro_dur - outro_fade_out:
                        a = (outro_dur - t) / outro_fade_out
                        a = max(0.0, min(1.0, a))
                        frame = cv2.addWeighted(frame, a, black, 1.0 - a, 0)

                    write_frame(frame)
                    self._check_cancel()

                    if f % 15 == 0:
                        self._emit(0.95 + 0.04 * (f / outro_frames),
                                   "\U0001f5bc Outro slide ...",
                                   frame_info=(total_frames + f,
                                               total_frames + outro_frames))

        finally:
            _close_writer()
            if bg_cap:
                bg_cap.release()

        # -- Audio mix ----------------------------------------------------------
        outro_enabled_  = cfg.get("outro_slide_enabled", False)
        outro_text_set  = cfg.get("outro_slide_text", "").strip()
        music_in_outro  = cfg.get("music_in_outro", False)
        outro_dur_val   = float(cfg.get("outro_slide_duration", 5)) \
                          if (outro_enabled_ and outro_text_set) else 0.0

        full_video_dur = total_sec + outro_dur_val
        audio_total    = full_video_dur if music_in_outro else total_sec

        if cfg.get("music_path") and ffmpeg_path:
            self._emit(0.98, "\U0001f3b5 Mixing audio ...", frame_info=(total_frames, total_frames))
            self._mix_audio(tmp_video, out_path, audio_total, full_video_dur, cfg, ffmpeg_path)
            try:
                os.remove(tmp_video)
            except Exception:
                pass
        else:
            os.replace(tmp_video, out_path)

        self._emit(1.0, "\u2705 Done!", frame_info=(total_frames, total_frames))

    # -- Outro-VIDEO render (eigenstaendige zweite MP4) ------------------------
    def _render_outro_video(self, out_path):
        """Render the standalone outro video.

        Plays the chosen slider images back to back, optionally looped, with a
        crossfade between images and a fade-in/out from/to black. It contains
        NO countdown timer - only the slider images. This is saved as an
        independent MP4 next to the intro file.

        Per-image display time is reused from the slider 'img_duration'
        setting. Music (the same MP3 used by the intro) is mixed in only when
        'outro_video_use_music' is enabled."""
        cfg        = self.cfg
        fps        = 30
        w, h       = 1920, 1080
        fill_color = cfg.get("slider_fill_color", "#000000")

        # -- Slider-Bilder laden & einpassen --
        base_imgs = []
        for p in cfg.get("image_paths", []):
            try:
                raw    = Image.open(p).convert("RGB")
                fitted = _fit_image(raw, w, h, fill_color)
                base_imgs.append(cv2.cvtColor(np.array(fitted), cv2.COLOR_RGB2BGR))
            except Exception:
                pass
        if not base_imgs:
            return  # keine Bilder -> nichts zu rendern

        # -- Loop-Anzahl: loops=2 bedeutet jede Bildfolge zweimal --
        # (5 Bilder, loops=2 -> 10 Bilder werden nacheinander gezeigt)
        loops = max(1, int(cfg.get("outro_video_loops", 2)))
        imgs  = base_imgs * loops
        n     = len(imgs)

        img_dur   = float(cfg.get("img_duration", 10))       # Dauer pro Bild (vom Slider uebernommen)
        crossfade = float(cfg.get("outro_video_crossfade", 1.0))
        fade_in   = float(cfg.get("outro_video_fade_in", 2.0))
        fade_out  = float(cfg.get("outro_video_fade_out", 2.0))
        crossfade = max(0.0, min(crossfade, img_dur))        # Ueberblendung kann Bilddauer nicht ueberschreiten

        total_dur    = n * img_dur
        total_frames = int(total_dur * fps)
        black        = np.zeros((h, w, 3), dtype=np.uint8)

        tmp_video   = out_path.replace(".mp4", "_noaudio.mp4")
        ffmpeg_path = _get_ffmpeg()
        ff_proc, write_frame, _close_writer = self._open_video_writer(
            tmp_video, w, h, fps, ffmpeg_path)

        frame_no = 0
        try:
            for i in range(n):
                seg_frames = int(img_dur * fps)
                cur        = imgs[i]
                prev       = imgs[i - 1] if i > 0 else None

                for f in range(seg_frames):
                    t_in_seg = f / fps

                    # Ueberblendung vom vorherigen Bild jeweils am Slot-Anfang
                    if prev is not None and crossfade > 0 and t_in_seg < crossfade:
                        a     = t_in_seg / crossfade
                        frame = cv2.addWeighted(cur, a, prev, 1.0 - a, 0)
                    else:
                        frame = cur.copy()

                    # Globales Fade-In / Fade-Out (von / zu Schwarz)
                    gt = frame_no / fps
                    if fade_in > 0 and gt < fade_in:
                        a     = gt / fade_in
                        frame = cv2.addWeighted(frame, a, black, 1.0 - a, 0)
                    if fade_out > 0 and gt > total_dur - fade_out:
                        a     = max(0.0, min(1.0, (total_dur - gt) / fade_out))
                        frame = cv2.addWeighted(frame, a, black, 1.0 - a, 0)

                    write_frame(frame)
                    frame_no += 1
                    self._check_cancel()

                    if frame_no % 15 == 0:
                        pct = frame_no / max(1, total_frames)
                        self._emit(min(pct, 0.97),
                                   f"\U0001f3ac Outro-Video ... ({int(pct*100)}%)",
                                   frame_info=(frame_no, total_frames))
        finally:
            _close_writer()

        # -- Optional: die Intro-Musik auch im Outro verwenden --
        use_music = cfg.get("outro_video_use_music", False)
        if use_music and cfg.get("music_path") and ffmpeg_path:
            self._emit(0.98, "\U0001f3b5 Outro-Audio ...",
                       frame_info=(total_frames, total_frames))
            self._mix_audio(tmp_video, out_path, total_dur, total_dur, cfg, ffmpeg_path)
            try:
                os.remove(tmp_video)
            except Exception:
                pass
        else:
            os.replace(tmp_video, out_path)

        self._emit(1.0, "\u2705 Outro fertig!", frame_info=(total_frames, total_frames))

    # -- Timeline builder ------------------------------------------------------
    def _build_segments(self, total_sec, slider_from, slider_until,
                         slider_imgs, img_dur, timer_between, slider_loop):
        """Return a list of (segment_type, duration_seconds) pairs."""
        segs = []
        pre_timer = total_sec - slider_from
        if pre_timer > 0:
            segs.append(("timer", pre_timer))
        zone_dur = slider_from - slider_until
        if zone_dur > 0 and slider_imgs:
            segs.extend(self._build_slider_zone(
                zone_dur, slider_imgs, img_dur, timer_between, slider_loop))
        elif zone_dur > 0:
            segs.append(("timer", zone_dur))
        if slider_until > 0:
            segs.append(("timer", slider_until))
        return segs

    def _build_slider_zone(self, zone_dur, slider_imgs,
                            img_dur, timer_between, slider_loop):
        """Build the alternating image / timer segments within the slider zone.

        When timer_between == 0 the image segments are placed back-to-back with
        no timer gap between them.  The render loop detects consecutive slide
        segments (prev_is_slide / next_is_slide) and crossfades them directly.
        """
        segs  = []
        n     = len(slider_imgs)
        used  = 0.0

        if not slider_loop:
            for i in range(n):
                if used >= zone_dur:
                    break
                dur = min(img_dur, zone_dur - used)
                segs.append((i, dur))
                used += dur
                # Only insert a timer gap when timer_between > 0
                if timer_between > 0 and i < n - 1 and used < zone_dur:
                    dur_t = min(timer_between, zone_dur - used)
                    segs.append(("timer", dur_t))
                    used += dur_t
            rest = zone_dur - used
            if rest > 0.05:
                segs.append(("timer", rest))
        else:
            img_idx = 0
            while used < zone_dur - 0.05:
                remaining = zone_dur - used
                dur_img   = min(img_dur, remaining)
                segs.append((img_idx % n, dur_img))
                used += dur_img
                # Only insert a timer gap when timer_between > 0
                if timer_between > 0 and used < zone_dur - 0.05:
                    dur_t = min(timer_between, zone_dur - used)
                    segs.append(("timer", dur_t))
                    used += dur_t
                img_idx += 1
        return segs

    # -- Draw timer + subtitle (standard, centred) -----------------------------
    def _draw_timer_and_subtitle(self, frame_bgr, time_left, cfg,
                                  w, h, get_font, font_path, sub_font_path):
        """Overlay the full-size centred countdown timer (and optional subtitle)."""
        time_left = max(0, time_left)
        m         = int(time_left // 60)
        s         = int(time_left % 60)

        timer_size = int(min(w, h) * 0.18)
        timer_font = get_font(font_path, timer_size)

        pil_img = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
        draw    = ImageDraw.Draw(pil_img)

        mm_str  = f"{m:02d}"
        ss_str  = f"{s:02d}"
        col_str = ":"

        bbox_mm  = draw.textbbox((0, 0), mm_str,  font=timer_font)
        bbox_col = draw.textbbox((0, 0), col_str, font=timer_font)
        bbox_ss  = draw.textbbox((0, 0), ss_str,  font=timer_font)

        mm_w  = bbox_mm[2]  - bbox_mm[0]
        col_w = bbox_col[2] - bbox_col[0]
        ss_w  = bbox_ss[2]  - bbox_ss[0]
        th    = bbox_mm[3]  - bbox_mm[1]

        total_w = mm_w + col_w + ss_w
        start_x = (w - total_w) // 2
        mm_x    = start_x
        col_x   = start_x + mm_w
        ss_x    = start_x + mm_w + col_w

        sub_enabled      = cfg.get("subtitle_enabled", False)
        sub_lines        = []
        sub_font         = None
        sub_size         = cfg.get("subtitle_size", 40)
        sub_offset_lines = int(cfg.get("subtitle_offset", 2))

        if sub_enabled:
            raw = cfg.get("subtitle_text", "").strip()
            if raw:
                sub_font  = get_font(sub_font_path, sub_size)
                sub_lines = [ln for ln in raw.splitlines() if ln.strip()]

        line_spacing = int(min(w, h) * 0.012)
        sub_data     = []

        if sub_lines:
            for line in sub_lines:
                bbox_s = draw.textbbox((0, 0), line, font=sub_font)
                lh     = bbox_s[3] - bbox_s[1]
                sub_data.append((line, bbox_s, lh))

        timer_y = (h - th) // 2
        ty      = timer_y - bbox_mm[1]

        timer_color = _hex_to_rgb(cfg["font_color"])
        shadow      = max(3, timer_size // 30)

        draw.text((mm_x  - bbox_mm[0]  + shadow, ty + shadow), mm_str,  font=timer_font, fill=(0,0,0,180))
        draw.text((mm_x  - bbox_mm[0],            ty),          mm_str,  font=timer_font, fill=timer_color)
        draw.text((col_x - bbox_col[0] + shadow, ty + shadow), col_str, font=timer_font, fill=(0,0,0,180))
        draw.text((col_x - bbox_col[0],           ty),          col_str, font=timer_font, fill=timer_color)
        draw.text((ss_x  - bbox_ss[0]  + shadow, ty + shadow), ss_str,  font=timer_font, fill=(0,0,0,180))
        draw.text((ss_x  - bbox_ss[0],            ty),          ss_str,  font=timer_font, fill=timer_color)

        if sub_data:
            sub_color  = _hex_to_rgb(cfg.get("subtitle_color", "#FFFFFF"))
            sub_shadow = max(2, sub_size // 20)
            cur_y = _subtitle_layout(w, h, timer_y, th, sub_offset_lines, sub_size)
            for i, (line, bbox_s, lh) in enumerate(sub_data):
                lw  = bbox_s[2] - bbox_s[0]
                lx  = (w - lw) // 2 - bbox_s[0]
                ly  = cur_y - bbox_s[1]
                draw.text((lx + sub_shadow, ly + sub_shadow), line, font=sub_font, fill=(0,0,0,160))
                draw.text((lx, ly),                           line, font=sub_font, fill=sub_color)
                cur_y += lh + (line_spacing if i < len(sub_data) - 1 else 0)

        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    # -- Draw animated timer (overlay mode) ------------------------------------
    def _draw_timer_animated(self, frame_bgr, time_left, cfg,
                              w, h, get_font, font_path,
                              anim_t: float, position: str,
                              size_pct: float = 0.065,
                              bg_transparent: bool = True,
                              bg_color_hex: str = "#FFFFFF"):
        """
        Draw the countdown timer with an animated size and position.

        Parameters
        ----------
        anim_t        : float in [0, 1]
                        0 -> timer centred at full size
                        1 -> timer shrunk into the chosen corner
        position      : "right_bottom" | "left_bottom" | "right_top" | "left_top"
        size_pct      : corner timer size as fraction of min(w, h)  (e.g. 0.065)
        bg_transparent: if False, draw a coloured pill behind the corner timer
        bg_color_hex  : hex colour of that pill
        """
        time_left = max(0, time_left)
        m         = int(time_left // 60)
        s_int     = int(time_left % 60)

        ease = _smoothstep(anim_t)

        full_size   = int(min(w, h) * 0.18)
        corner_size = int(min(w, h) * size_pct)
        timer_size  = max(8, int(full_size + (corner_size - full_size) * ease))

        timer_font = get_font(font_path, timer_size)

        pil_img = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
        draw    = ImageDraw.Draw(pil_img)

        mm_str  = f"{m:02d}"
        ss_str  = f"{s_int:02d}"
        col_str = ":"

        bbox_mm  = draw.textbbox((0, 0), mm_str,  font=timer_font)
        bbox_col = draw.textbbox((0, 0), col_str, font=timer_font)
        bbox_ss  = draw.textbbox((0, 0), ss_str,  font=timer_font)

        mm_w    = bbox_mm[2]  - bbox_mm[0]
        col_w   = bbox_col[2] - bbox_col[0]
        ss_w    = bbox_ss[2]  - bbox_ss[0]
        th      = bbox_mm[3]  - bbox_mm[1]
        total_w = mm_w + col_w + ss_w

        # Centre position (anim_t=0)
        cx = (w - total_w) // 2
        cy = (h - th)      // 2

        # Corner position (anim_t=1) - 4 corners supported
        margin = int(min(w, h) * 0.035)
        if position == "left_bottom":
            corner_x = margin
            corner_y = h - th - margin
        elif position == "left_top":
            corner_x = margin
            corner_y = margin
        elif position == "right_top":
            corner_x = w - total_w - margin
            corner_y = margin
        else:  # "right_bottom" (default, also accepts old "right")
            corner_x = w - total_w - margin
            corner_y = h - th - margin

        # Interpolated position
        start_x = int(cx + (corner_x - cx) * ease)
        start_y = int(cy + (corner_y - cy) * ease)

        mm_x  = start_x
        col_x = start_x + mm_w
        ss_x  = start_x + mm_w + col_w
        ty    = start_y - bbox_mm[1]

        # -- Background pill (only when ease > 0 and not transparent) --------
        if not bg_transparent and ease > 0:
            pad_x  = max(6, timer_size // 5)
            pad_y  = max(4, timer_size // 7)
            radius = max(4, timer_size // 5)
            alpha  = int(ease * 210)   # fades in as timer moves to corner
            r, g, b = _hex_to_rgb(bg_color_hex)

            rgba    = pil_img.convert("RGBA")
            overlay = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
            d_ov    = ImageDraw.Draw(overlay)
            d_ov.rounded_rectangle(
                [start_x - pad_x,
                 start_y - pad_y,
                 start_x + total_w + pad_x,
                 start_y + th + pad_y],
                radius=radius,
                fill=(r, g, b, alpha)
            )
            pil_img = Image.alpha_composite(rgba, overlay).convert("RGB")
            draw    = ImageDraw.Draw(pil_img)

        # -- Timer text --------------------------------------------------------
        timer_color = _hex_to_rgb(cfg["font_color"])
        shadow      = max(2, timer_size // 30)

        draw.text((mm_x  - bbox_mm[0]  + shadow, ty + shadow), mm_str,  font=timer_font, fill=(0,0,0,180))
        draw.text((mm_x  - bbox_mm[0],            ty),          mm_str,  font=timer_font, fill=timer_color)
        draw.text((col_x - bbox_col[0] + shadow, ty + shadow), col_str, font=timer_font, fill=(0,0,0,180))
        draw.text((col_x - bbox_col[0],           ty),          col_str, font=timer_font, fill=timer_color)
        draw.text((ss_x  - bbox_ss[0]  + shadow, ty + shadow), ss_str,  font=timer_font, fill=(0,0,0,180))
        draw.text((ss_x  - bbox_ss[0],            ty),          ss_str,  font=timer_font, fill=timer_color)

        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    # -- Draw outro slide ------------------------------------------------------
    def _draw_outro_slide(self, text, hex_color,
                          bg_image_path, bg_hex_color,
                          font_size, font_path, w, h, get_font):
        """Render the static outro slide frame (Abschluss-Bild)."""
        if bg_image_path and os.path.isfile(bg_image_path):
            try:
                bg_pil = Image.open(bg_image_path).convert("RGB").resize(
                    (w, h), Image.LANCZOS
                )
            except Exception:
                bg_r, bg_g, bg_b = _hex_to_rgb(bg_hex_color)
                bg_pil = Image.new("RGB", (w, h), color=(bg_r, bg_g, bg_b))
        else:
            bg_r, bg_g, bg_b = _hex_to_rgb(bg_hex_color)
            bg_pil = Image.new("RGB", (w, h), color=(bg_r, bg_g, bg_b))

        draw = ImageDraw.Draw(bg_pil)
        font = get_font(font_path, font_size)

        text_color   = _hex_to_rgb(hex_color)
        lines        = [ln for ln in text.splitlines() if ln.strip()] or [text]
        line_spacing = int(font_size * 0.3)
        shadow_off   = max(2, font_size // 25)

        line_data = []
        total_h   = 0
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            lw   = bbox[2] - bbox[0]
            lh   = bbox[3] - bbox[1]
            line_data.append((line, bbox, lw, lh))
            total_h += lh
            if i < len(lines) - 1:
                total_h += line_spacing

        cur_y = (h - total_h) // 2
        for line, bbox, lw, lh in line_data:
            x = (w - lw) // 2 - bbox[0]
            y = cur_y - bbox[1]
            draw.text((x + shadow_off, y + shadow_off), line,
                      font=font, fill=(0, 0, 0, 60))
            draw.text((x, y), line, font=font, fill=text_color)
            cur_y += lh + line_spacing

        return cv2.cvtColor(np.array(bg_pil), cv2.COLOR_RGB2BGR)

    # -- Audio mix -------------------------------------------------------------
    def _mix_audio(self, tmp_video, out_path, audio_sec, video_sec, cfg, ffmpeg_path):
        """Mix background music into the video.

        Used for both the intro and the outro video; the outro reuses the same
        music settings (loop / fade-out / fade duration) as the intro."""
        music      = cfg["music_path"]
        loop       = cfg["music_loop"]
        fadeout    = cfg["music_fadeout"]
        fade_dur   = cfg["music_fade_dur"]
        fade_start = max(0, audio_sec - fade_dur)

        af_parts = []
        if fadeout:
            af_parts.append(f"afade=t=out:st={fade_start:.2f}:d={fade_dur}")
        af_parts.append(f"atrim=0:{audio_sec}")
        if video_sec > audio_sec:
            af_parts.append(f"apad=whole_dur={video_sec}")
        af_str = ",".join(af_parts) if af_parts else "anull"

        loop_flag = ["-stream_loop", "-1"] if loop else []
        cmd = [
            ffmpeg_path, "-y",
            "-i", tmp_video,
            *loop_flag,
            "-vn",
            "-i", music,
            "-filter_complex",
                f"[1:a]asetpts=PTS-STARTPTS,{af_str}[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-ac", "2",
            "-ar", "44100",
            "-shortest", out_path
        ]

        with open(os.devnull, "w") as devnull:
            subprocess.run(
                cmd, check=True,
                stdout=subprocess.DEVNULL, stderr=devnull,
                startupinfo=_STARTUPINFO
            )