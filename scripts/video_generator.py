import cv2, numpy as np, os, traceback, subprocess, shutil
from PIL import Image, ImageDraw, ImageFont


class VideoGenerator:
    def __init__(self, config, progress_cb, done_cb):
        self.cfg      = config
        self.cb       = progress_cb
        self.done     = done_cb

    def generate(self):
        try:
            self._run()
            self.done(True, "OK")
        except Exception:
            self.done(False, traceback.format_exc())

    def _run(self):
        cfg      = self.cfg
        fps      = 30
        total_sec = cfg["timer_minutes"] * 60
        out_path  = cfg["output_path"]

        # ── Hintergrund ──────────────────────────────────────────────
        bg_cap = None; bg_static = None
        w, h   = 1920, 1080

        if cfg["bg_video"]:
            bg_cap    = cv2.VideoCapture(cfg["bg_video"])
            w         = int(bg_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h         = int(bg_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            bg_total  = int(bg_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        elif cfg["bg_image"]:
            img = Image.open(cfg["bg_image"]).convert("RGB").resize((w, h))
            bg_static = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        else:
            bg_static = np.ones((h, w, 3), dtype=np.uint8) * 255

        # ── Slider-Bilder ─────────────────────────────────────────────
        slider_imgs = []
        for p in cfg.get("image_paths", []):
            try:
                img = Image.open(p).convert("RGB").resize((w, h), Image.LANCZOS)
                slider_imgs.append(cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR))
            except: pass

        slider_from  = cfg["slider_from"]  * 60
        slider_until = cfg["slider_until"] * 60
        img_dur      = cfg["img_duration"]
        fade_dur     = float(cfg["fade_duration"])

        # ── PIL-Font laden ────────────────────────────────────────────
        font_path = cfg.get("font_path")
        self._pil_fonts = {}   # size → ImageFont

        def get_pil_font(size):
            if size not in self._pil_fonts:
                try:
                    if font_path:
                        self._pil_fonts[size] = ImageFont.truetype(font_path, size)
                    else:
                        self._pil_fonts[size] = ImageFont.load_default()
                except:
                    self._pil_fonts[size] = ImageFont.load_default()
            return self._pil_fonts[size]

        # ── Output ────────────────────────────────────────────────────
        tmp_video     = out_path.replace(".mp4", "_noaudio.mp4")
        fourcc        = cv2.VideoWriter_fourcc(*"mp4v")
        writer        = cv2.VideoWriter(tmp_video, fourcc, fps, (w, h))

        total_frames  = int(total_sec * fps)
        bg_frame_idx  = 0

        for frame_idx in range(total_frames):
            time_left = total_sec - (frame_idx / fps)

            # Hintergrund
            if bg_cap:
                if bg_frame_idx >= bg_total - 1:
                    bg_cap.set(cv2.CAP_PROP_POS_FRAMES, 0); bg_frame_idx = 0
                ret, bg = bg_cap.read()
                if not ret:
                    bg_cap.set(cv2.CAP_PROP_POS_FRAMES, 0); ret, bg = bg_cap.read()
                bg_frame_idx += 1
            else:
                bg = bg_static.copy()

            # Slider-Zone?
            in_slider = (slider_imgs and slider_until < time_left <= slider_from)

            if in_slider:
                pos_in_zone = slider_from - time_left
                img_idx     = int(pos_in_zone // img_dur) % len(slider_imgs)
                pos_in_img  = pos_in_zone % img_dur
                slide       = slider_imgs[img_idx]

                if fade_dur > 0 and pos_in_img < fade_dur:
                    a = pos_in_img / fade_dur
                    frame = cv2.addWeighted(slide, a, bg, 1 - a, 0)
                elif fade_dur > 0 and pos_in_img > img_dur - fade_dur:
                    a = (img_dur - pos_in_img) / fade_dur
                    frame = cv2.addWeighted(slide, a, bg, 1 - a, 0)
                else:
                    frame = slide.copy()
            else:
                frame = bg.copy()

                # Countdown mit PIL-Font zeichnen
                frame = self._draw_timer_pil(frame, time_left, cfg, w, h, get_pil_font)

            writer.write(frame)

            # Progress alle 15 Frames
            if frame_idx % 15 == 0:
                pct = frame_idx / total_frames
                m   = int(time_left // 60); s = int(time_left % 60)
                self.cb(pct,
                        f"⏳ Rendere … {m:02d}:{s:02d}  ({int(pct*100)}%)",
                        frame_info=(frame_idx, total_frames))

        writer.release()
        if bg_cap: bg_cap.release()

        # ── Audio mischen ─────────────────────────────────────────────
        if cfg.get("music_path") and shutil.which("ffmpeg"):
            self._mix_audio(tmp_video, out_path, total_sec, cfg)
            try: os.remove(tmp_video)
            except: pass
        else:
            os.replace(tmp_video, out_path)

        self.cb(1.0, "✅ Fertig!", frame_info=(total_frames, total_frames))

    # ── TIMER MIT PIL FONT ────────────────────────────────────────────
    def _draw_timer_pil(self, frame_bgr, time_left, cfg, w, h, get_font):
        time_left = max(0, time_left)
        m = int(time_left // 60); s = int(time_left % 60)
        text = f"{m:02d}:{s:02d}"

        font_size = int(min(w, h) * 0.18)   # ~Groß & zentriert
        font      = get_font(font_size)

        # BGR → PIL
        pil_img = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
        draw    = ImageDraw.Draw(pil_img)

        bbox    = draw.textbbox((0, 0), text, font=font)
        tw, th  = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (w - tw) // 2 - bbox[0]
        y = (h - th) // 2 - bbox[1]

        # Hex-Farbe
        hx = cfg["font_color"].lstrip("#")
        r, g, b = int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)

        # Schatten
        shadow = max(3, font_size // 30)
        draw.text((x + shadow, y + shadow), text, font=font, fill=(0, 0, 0, 180))
        # Text
        draw.text((x, y), text, font=font, fill=(r, g, b))

        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    # ── AUDIO ─────────────────────────────────────────────────────────
    def _mix_audio(self, tmp_video, out_path, total_sec, cfg):
        music     = cfg["music_path"]
        loop      = cfg["music_loop"]
        fadeout   = cfg["music_fadeout"]
        fade_dur  = cfg["music_fade_dur"]
        fade_start = max(0, total_sec - fade_dur)

        af_parts = []
        if fadeout:
            af_parts.append(f"afade=t=out:st={fade_start:.2f}:d={fade_dur}")
        af_parts.append(f"atrim=0:{total_sec},asetpts=PTS-STARTPTS")
        af_str = ",".join(af_parts)

        loop_flag = ["-stream_loop", "-1"] if loop else []

        cmd = [
            "ffmpeg", "-y",
            "-i", tmp_video,
            *loop_flag, "-i", music,
            "-filter_complex", f"[1:a]{af_str}[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac",
            "-shortest", out_path
        ]
        subprocess.run(cmd, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)