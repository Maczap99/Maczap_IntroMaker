import cv2, numpy as np, os, traceback, subprocess, shutil
from PIL import Image, ImageDraw, ImageFont


class VideoGenerator:
    def __init__(self, config, progress_cb, done_cb):
        self.cfg  = config
        self.cb   = progress_cb
        self.done = done_cb

    def generate(self):
        try:
            self._run()
            self.done(True, "OK")
        except Exception:
            self.done(False, traceback.format_exc())

    def _run(self):
        cfg       = self.cfg
        fps       = 30
        total_sec = cfg["timer_minutes"] * 60
        out_path  = cfg["output_path"]

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
            bg_static = np.ones((h, w, 3), dtype=np.uint8) * 255

        slider_imgs = []
        for p in cfg.get("image_paths", []):
            try:
                img = Image.open(p).convert("RGB").resize((w, h), Image.LANCZOS)
                slider_imgs.append(cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR))
            except:
                pass

        slider_from  = cfg["slider_from"]  * 60
        slider_until = cfg["slider_until"] * 60
        img_dur      = cfg["img_duration"]
        fade_dur     = float(cfg["fade_duration"])

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
                except:
                    self._pil_fonts[key] = ImageFont.load_default()
            return self._pil_fonts[key]

        tmp_video    = out_path.replace(".mp4", "_noaudio.mp4")
        fourcc       = cv2.VideoWriter_fourcc(*"mp4v")
        writer       = cv2.VideoWriter(tmp_video, fourcc, fps, (w, h))
        total_frames = int(total_sec * fps)
        bg_frame_idx = 0

        for frame_idx in range(total_frames):
            time_left = total_sec - (frame_idx / fps)

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
                frame = self._draw_timer_and_subtitle(
                    frame, time_left, cfg, w, h, get_font, font_path, sub_font_path)

            writer.write(frame)

            if frame_idx % 15 == 0:
                pct = frame_idx / total_frames
                m   = int(time_left // 60)
                s   = int(time_left % 60)
                self.cb(pct, f"⏳ Rendere … {m:02d}:{s:02d}  ({int(pct * 100)}%)",
                        frame_info=(frame_idx, total_frames))

        writer.release()
        if bg_cap:
            bg_cap.release()

        if cfg.get("music_path") and shutil.which("ffmpeg"):
            self._mix_audio(tmp_video, out_path, total_sec, cfg)
            try:
                os.remove(tmp_video)
            except:
                pass
        else:
            os.replace(tmp_video, out_path)

        self.cb(1.0, "✅ Fertig!", frame_info=(total_frames, total_frames))

    def _draw_timer_and_subtitle(self, frame_bgr, time_left, cfg,
                                  w, h, get_font, font_path, sub_font_path):
        time_left  = max(0, time_left)
        m          = int(time_left // 60)
        s          = int(time_left % 60)
        timer_text = f"{m:02d}:{s:02d}"

        timer_size = int(min(w, h) * 0.18)
        timer_font = get_font(font_path, timer_size)

        pil_img = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
        draw    = ImageDraw.Draw(pil_img)

        bbox_t = draw.textbbox((0, 0), timer_text, font=timer_font)
        tw     = bbox_t[2] - bbox_t[0]
        th     = bbox_t[3] - bbox_t[1]

        # Untertitel: mehrzeiliger Text aus Textbox (Zeilenumbrüche erhalten)
        sub_enabled = cfg.get("subtitle_enabled", False)
        sub_lines   = []

        if sub_enabled:
            raw_text = cfg.get("subtitle_text", "").strip()
            if raw_text:
                sub_size = cfg.get("subtitle_size", 40)
                sub_font = get_font(sub_font_path, sub_size)
                # Zeilenumbrüche aus der Textbox beibehalten
                sub_lines = [ln for ln in raw_text.splitlines() if ln.strip()]

        gap          = int(min(w, h) * 0.03)
        line_spacing = int(min(w, h) * 0.012)

        total_height = th
        sub_data     = []

        if sub_lines:
            total_height += gap
            for i, line in enumerate(sub_lines):
                bbox_s = draw.textbbox((0, 0), line, font=sub_font)
                lh     = bbox_s[3] - bbox_s[1]
                sub_data.append((line, bbox_s, lh))
                total_height += lh
                if i < len(sub_lines) - 1:
                    total_height += line_spacing

        start_y = (h - total_height) // 2

        # Timer-Farbe
        hx_t        = cfg["font_color"].lstrip("#")
        rt, gt, bt  = int(hx_t[0:2], 16), int(hx_t[2:4], 16), int(hx_t[4:6], 16)
        timer_color = (rt, gt, bt)

        tx     = (w - tw) // 2 - bbox_t[0]
        ty     = start_y - bbox_t[1]
        shadow = max(3, timer_size // 30)
        draw.text((tx + shadow, ty + shadow), timer_text, font=timer_font, fill=(0, 0, 0, 180))
        draw.text((tx, ty), timer_text, font=timer_font, fill=timer_color)

        if sub_data:
            hx_s       = cfg.get("subtitle_color", "#FFFFFF").lstrip("#")
            rs, gs, bs = int(hx_s[0:2], 16), int(hx_s[2:4], 16), int(hx_s[4:6], 16)
            sub_color  = (rs, gs, bs)
            sub_shadow = max(2, sub_size // 20)

            cur_y = start_y + th + gap
            for i, (line, bbox_s, lh) in enumerate(sub_data):
                lw  = bbox_s[2] - bbox_s[0]
                lx  = (w - lw) // 2 - bbox_s[0]
                ly  = cur_y - bbox_s[1]
                draw.text((lx + sub_shadow, ly + sub_shadow),
                          line, font=sub_font, fill=(0, 0, 0, 160))
                draw.text((lx, ly), line, font=sub_font, fill=sub_color)
                cur_y += lh + (line_spacing if i < len(sub_data) - 1 else 0)

        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    def _mix_audio(self, tmp_video, out_path, total_sec, cfg):
        music      = cfg["music_path"]
        loop       = cfg["music_loop"]
        fadeout    = cfg["music_fadeout"]
        fade_dur   = cfg["music_fade_dur"]
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