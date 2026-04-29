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
    Fit *img_pil* into a w×h canvas while preserving its aspect ratio.

    The image is scaled down (or up) so that it fits entirely within the
    target dimensions without cropping.  Any remaining area is filled with
    *fill_color_hex* (default black).

    Parameters
    ----------
    img_pil       : PIL.Image.Image  — source image (any size / ratio)
    w, h          : int              — target canvas dimensions
    fill_color_hex: str              — hex color for letterbox/pillarbox bars

    Returns
    -------
    PIL.Image.Image — new RGB image of exactly (w, h) pixels
    """
    r, g, b = _hex_to_rgb(fill_color_hex)
    canvas  = Image.new("RGB", (w, h), (r, g, b))

    # Scale to fit while maintaining aspect ratio
    scale = min(w / img_pil.width, h / img_pil.height)
    new_w = int(img_pil.width  * scale)
    new_h = int(img_pil.height * scale)

    resized  = img_pil.resize((new_w, new_h), Image.LANCZOS)
    offset_x = (w - new_w) // 2
    offset_y = (h - new_h) // 2
    canvas.paste(resized, (offset_x, offset_y))
    return canvas


def _subtitle_layout(w: int, h: int, timer_y: int, timer_h: int,
                     sub_offset: int, sub_size: int) -> int:
    """Return the y-coordinate at which subtitle text begins.

    A single shared helper so that subtitle position is pixel-identical
    across every render path — fade frames and normal timer frames alike.

    Parameters
    ----------
    w, h        : int — frame dimensions
    timer_y     : int — top edge of the timer text block (pixels)
    timer_h     : int — pixel height of the timer text block
    sub_offset  : int — user-configured line-offset value
    sub_size    : int — subtitle font size in points (used for extra gap)

    Returns
    -------
    int — pixel y-coordinate for the first subtitle line
    """
    base_gap  = int(min(w, h) * 0.04)
    extra_gap = sub_offset * sub_size
    return timer_y + timer_h + base_gap + extra_gap


class _CancelledError(Exception):
    """Raised internally when the cancel event is set during rendering."""


class VideoGenerator:
    def __init__(self, config, progress_cb, done_cb, cancel_event=None):
        self.cfg           = config
        self.cb            = progress_cb
        self.done          = done_cb
        self._cancel_event = cancel_event

    def _check_cancel(self):
        """Raise _CancelledError if the cancel event has been set."""
        if self._cancel_event and self._cancel_event.is_set():
            raise _CancelledError()

    def generate(self):
        out_path  = self.cfg.get("output_path", "")
        tmp_video = out_path.replace(".mp4", "_noaudio.mp4") if out_path else ""
        try:
            self._run()
            self.done(True, "OK")
        except _CancelledError:
            # Remove any partially written output files so no corrupt files remain
            for path in [tmp_video, out_path]:
                if path and os.path.isfile(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass
            self.done(False, "CANCELLED")
        except Exception:
            self.done(False, traceback.format_exc())

    # ── Main render loop ──────────────────────────────────────────────────────
    def _run(self):
        cfg       = self.cfg
        fps       = 30
        total_sec = cfg["timer_minutes"] * 60
        out_path  = cfg["output_path"]

        # ── Background ────────────────────────────────────────────────────────
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
            # No background source — fill with the user-chosen color
            r, g, b   = _hex_to_rgb(cfg.get("bg_color", "#000000"))
            bg_static = np.full((h, w, 3), (b, g, r), dtype=np.uint8)

        # ── Slider images (aspect-ratio-safe with fill color) ─────────────────
        slider_imgs = []
        fill_color  = cfg.get("slider_fill_color", "#000000")

        for p in cfg.get("image_paths", []):
            try:
                raw_img = Image.open(p).convert("RGB")
                fitted  = _fit_image(raw_img, w, h, fill_color)
                slider_imgs.append(cv2.cvtColor(np.array(fitted), cv2.COLOR_RGB2BGR))
            except Exception:
                pass  # Skip unreadable images silently

        # ── Settings ──────────────────────────────────────────────────────────
        slider_from   = cfg["slider_from"]  * 60
        slider_until  = cfg["slider_until"] * 60
        img_dur       = float(cfg["img_duration"])
        timer_between = float(cfg.get("timer_between", 0))
        slider_loop   = cfg.get("slider_loop", True)
        fade_dur      = float(cfg["fade_duration"])

        # Start / end fades
        intro_fade         = cfg.get("intro_fade_enabled", False)
        # If an outro slide is active we crossfade into it instead of fading to black
        outro_slide_active = (cfg.get("outro_slide_enabled", False) and
                              cfg.get("outro_slide_text", "").strip())
        outro_fade         = cfg.get("outro_fade_enabled", False) and not outro_slide_active
        intro_fade_dur     = float(cfg.get("intro_fade_dur", 3.0))
        outro_fade_dur     = float(cfg.get("outro_fade_dur", 3.0))

        # ── Fonts ─────────────────────────────────────────────────────────────
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

        # ── Timeline ──────────────────────────────────────────────────────────
        segments     = self._build_segments(
            total_sec, slider_from, slider_until,
            slider_imgs, img_dur, timer_between, slider_loop)
        total_frames = int(total_sec * fps)

        # ── Start FFmpeg pipe process ─────────────────────────────────────────
        tmp_video   = out_path.replace(".mp4", "_noaudio.mp4")
        ffmpeg_path = _get_ffmpeg()

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
        else:
            ff_proc = None
            fourcc  = cv2.VideoWriter_fourcc(*"mp4v")
            writer  = cv2.VideoWriter(tmp_video, fourcc, fps, (w, h))
            write_frame = lambda f: writer.write(f)

        black      = np.zeros((h, w, 3), dtype=np.uint8)
        last_frame = black.copy()

        # ── Render frames ─────────────────────────────────────────────────────
        bg_frame_idx = 0
        elapsed      = 0.0

        try:
            for seg_type, seg_dur in segments:
                seg_frames = int(seg_dur * fps)

                for f in range(seg_frames):
                    time_left = max(0.0, total_sec - elapsed)

                    # Advance or loop the background video
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

                    if seg_type == "timer":
                        frame = self._draw_timer_and_subtitle(
                            bg.copy(), time_left, cfg, w, h,
                            get_font, font_path, sub_font_path)
                    else:
                        img_idx    = seg_type % len(slider_imgs)
                        slide      = slider_imgs[img_idx]
                        pos_in_seg = f / fps

                        # Crossfade slider image in/out over the timer background
                        if fade_dur > 0 and pos_in_seg < fade_dur:
                            a = pos_in_seg / fade_dur
                            timer_bg = self._draw_timer_and_subtitle(
                                bg.copy(), time_left, cfg, w, h,
                                get_font, font_path, sub_font_path)
                            frame = cv2.addWeighted(slide, a, timer_bg, 1 - a, 0)
                        elif fade_dur > 0 and pos_in_seg > seg_dur - fade_dur:
                            a = (seg_dur - pos_in_seg) / fade_dur
                            timer_bg = self._draw_timer_and_subtitle(
                                bg.copy(), time_left, cfg, w, h,
                                get_font, font_path, sub_font_path)
                            frame = cv2.addWeighted(slide, a, timer_bg, 1 - a, 0)
                        else:
                            frame = slide.copy()

                    # Global intro fade-in from black
                    if intro_fade and elapsed < intro_fade_dur:
                        a = elapsed / intro_fade_dur
                        frame = cv2.addWeighted(frame, a, black, 1 - a, 0)

                    # Global outro fade-out to black
                    if outro_fade and elapsed > total_sec - outro_fade_dur:
                        a = (total_sec - elapsed) / outro_fade_dur
                        a = max(0.0, min(1.0, a))
                        frame = cv2.addWeighted(frame, a, black, 1 - a, 0)

                    write_frame(frame)
                    elapsed   += 1.0 / fps
                    last_frame = frame
                    self._check_cancel()

                    frame_idx = int(elapsed * fps)
                    if frame_idx % 15 == 0:
                        pct = elapsed / total_sec
                        m   = int(time_left // 60)
                        s   = int(time_left % 60)
                        self.cb(min(pct, 0.95),
                                f"⏳ Rendering … {m:02d}:{s:02d}  ({int(pct*100)}%)",
                                frame_info=(frame_idx, total_frames))

            # ── Outro slide — rendered before stdin is closed ──────────────────
            outro_enabled    = cfg.get("outro_slide_enabled", False)
            outro_text       = cfg.get("outro_slide_text", "").strip()
            outro_color      = cfg.get("outro_slide_color", "#FFFFFF")
            # Background: image path takes priority over solid color
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

                    # Crossfade from last timer frame into the outro slide
                    if outro_fade_in > 0 and t < outro_fade_in:
                        a = t / outro_fade_in
                        frame = cv2.addWeighted(frame, a, last_frame, 1 - a, 0)

                    # Fade outro slide to black at the end
                    if outro_fade_out > 0 and t > outro_dur - outro_fade_out:
                        a = (outro_dur - t) / outro_fade_out
                        a = max(0.0, min(1.0, a))
                        frame = cv2.addWeighted(frame, a, black, 1 - a, 0)

                    write_frame(frame)
                    self._check_cancel()

                    if f % 15 == 0:
                        self.cb(0.95 + 0.04 * (f / outro_frames),
                                "🖼 Outro slide …",
                                frame_info=(total_frames + f,
                                            total_frames + outro_frames))

        finally:
            # Always close the pipe / writer and release the background capture
            if ff_proc:
                ff_proc.stdin.close()
                ff_proc.stderr.close()
                ff_proc.wait()
                if ff_proc.returncode not in (0, None):
                    raise RuntimeError(
                        f"FFmpeg closed with code {ff_proc.returncode}")
            else:
                writer.release()
            if bg_cap:
                bg_cap.release()

        # ── Determine audio duration ──────────────────────────────────────────
        #
        # music_in_outro=True  → music plays through the entire video incl. outro
        # music_in_outro=False → music stops at timer 0:00; outro plays silently
        outro_enabled_  = cfg.get("outro_slide_enabled", False)
        outro_text_set  = cfg.get("outro_slide_text", "").strip()
        music_in_outro  = cfg.get("music_in_outro", False)
        outro_dur_val   = float(cfg.get("outro_slide_duration", 5)) \
                          if (outro_enabled_ and outro_text_set) else 0.0

        # Full video length = timer + outro slide
        full_video_dur = total_sec + outro_dur_val

        audio_total = full_video_dur if music_in_outro else total_sec

        if cfg.get("music_path") and ffmpeg_path:
            self.cb(0.98, "🎵 Mixing audio …", frame_info=(total_frames, total_frames))
            self._mix_audio(tmp_video, out_path, audio_total, full_video_dur, cfg, ffmpeg_path)
            try:
                os.remove(tmp_video)
            except Exception:
                pass
        else:
            os.replace(tmp_video, out_path)

        self.cb(1.0, "✅ Done!", frame_info=(total_frames, total_frames))

    # ── Timeline builder ──────────────────────────────────────────────────────
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
        """Build the alternating image/timer segments within the slider zone."""
        segs  = []
        n     = len(slider_imgs)
        used  = 0.0

        if not slider_loop:
            # Play each image once in order, then fill remaining time with timer
            for i in range(n):
                if used >= zone_dur:
                    break
                dur = min(img_dur, zone_dur - used)
                segs.append((i, dur))
                used += dur
                if i < n - 1 and timer_between > 0 and used < zone_dur:
                    dur_t = min(timer_between, zone_dur - used)
                    segs.append(("timer", dur_t))
                    used += dur_t
            rest = zone_dur - used
            if rest > 0.05:
                segs.append(("timer", rest))
        else:
            # Loop images indefinitely until the zone is filled
            img_idx = 0
            while used < zone_dur - 0.05:
                remaining = zone_dur - used
                dur_img   = min(img_dur, remaining)
                segs.append((img_idx % n, dur_img))
                used += dur_img
                if timer_between > 0 and used < zone_dur - 0.05:
                    dur_t = min(timer_between, zone_dur - used)
                    segs.append(("timer", dur_t))
                    used += dur_t
                img_idx += 1
        return segs

    # ── Draw timer + subtitle ─────────────────────────────────────────────────
    def _draw_timer_and_subtitle(self, frame_bgr, time_left, cfg,
                                  w, h, get_font, font_path, sub_font_path):
        """Overlay the countdown timer (and optional subtitle) onto *frame_bgr*."""
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

        # Draw each digit group with a drop shadow for readability
        draw.text((mm_x  - bbox_mm[0]  + shadow, ty + shadow), mm_str,  font=timer_font, fill=(0,0,0,180))
        draw.text((mm_x  - bbox_mm[0],            ty),          mm_str,  font=timer_font, fill=timer_color)
        draw.text((col_x - bbox_col[0] + shadow, ty + shadow), col_str, font=timer_font, fill=(0,0,0,180))
        draw.text((col_x - bbox_col[0],           ty),          col_str, font=timer_font, fill=timer_color)
        draw.text((ss_x  - bbox_ss[0]  + shadow, ty + shadow), ss_str,  font=timer_font, fill=(0,0,0,180))
        draw.text((ss_x  - bbox_ss[0],            ty),          ss_str,  font=timer_font, fill=timer_color)

        if sub_data:
            sub_color  = _hex_to_rgb(cfg.get("subtitle_color", "#FFFFFF"))
            sub_shadow = max(2, sub_size // 20)
            # Use shared helper so subtitle y-position is consistent across all render paths
            cur_y = _subtitle_layout(w, h, timer_y, th, sub_offset_lines, sub_size)
            for i, (line, bbox_s, lh) in enumerate(sub_data):
                lw  = bbox_s[2] - bbox_s[0]
                lx  = (w - lw) // 2 - bbox_s[0]
                ly  = cur_y - bbox_s[1]
                draw.text((lx + sub_shadow, ly + sub_shadow), line, font=sub_font, fill=(0,0,0,160))
                draw.text((lx, ly),                           line, font=sub_font, fill=sub_color)
                cur_y += lh + (line_spacing if i < len(sub_data) - 1 else 0)

        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    # ── Draw outro slide ──────────────────────────────────────────────────────
    def _draw_outro_slide(self, text, hex_color,
                          bg_image_path, bg_hex_color,
                          font_size, font_path, w, h, get_font):
        """
        Render the static outro slide frame.

        Background priority:
          1. bg_image_path — valid image file → scaled to fill the frame
          2. bg_hex_color  — solid color fill when no image is provided
        """
        # Build the background canvas
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

        # Measure total text block height
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

        # Draw each line centered vertically and horizontally
        cur_y = (h - total_h) // 2
        for line, bbox, lw, lh in line_data:
            x = (w - lw) // 2 - bbox[0]
            y = cur_y - bbox[1]
            draw.text((x + shadow_off, y + shadow_off), line,
                      font=font, fill=(0, 0, 0, 60))
            draw.text((x, y), line, font=font, fill=text_color)
            cur_y += lh + line_spacing

        return cv2.cvtColor(np.array(bg_pil), cv2.COLOR_RGB2BGR)

    # ── Audio mix ─────────────────────────────────────────────────────────────
    def _mix_audio(self, tmp_video, out_path, audio_sec, video_sec, cfg, ffmpeg_path):
        """
        Mix background music into the video.

        Parameters
        ----------
        audio_sec : float
            How long the music should play.  May be shorter than the video when
            music_in_outro=False so the outro slide plays in silence.
        video_sec : float
            Full duration of the video stream (timer + outro slide).  Used to
            pad the audio track with silence so FFmpeg's -shortest flag never
            cuts the outro slide off.
        """
        music      = cfg["music_path"]
        loop       = cfg["music_loop"]
        fadeout    = cfg["music_fadeout"]
        fade_dur   = cfg["music_fade_dur"]
        fade_start = max(0, audio_sec - fade_dur)

        # Build the audio filter chain:
        # 1. Optional fade-out
        # 2. Trim music to audio_sec
        # 3. Pad with silence up to video_sec so the full video is preserved
        af_parts = []
        if fadeout:
            af_parts.append(f"afade=t=out:st={fade_start:.2f}:d={fade_dur}")
        af_parts.append(f"atrim=0:{audio_sec}")
        if video_sec > audio_sec:
            # Pad with silence so the outro slide is not cut short by -shortest
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