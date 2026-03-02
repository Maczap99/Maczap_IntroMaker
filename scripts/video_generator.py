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

    # ── HAUPT-RENDER ──────────────────────────────────────────────────
    def _run(self):
        cfg       = self.cfg
        fps       = 30
        total_sec = cfg["timer_minutes"] * 60
        out_path  = cfg["output_path"]

        # ── Hintergrund ───────────────────────────────────────────────
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

        # ── Slider-Bilder laden ───────────────────────────────────────
        slider_imgs = []
        for p in cfg.get("image_paths", []):
            try:
                img = Image.open(p).convert("RGB").resize((w, h), Image.LANCZOS)
                slider_imgs.append(cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR))
            except:
                pass

        # ── Einstellungen ─────────────────────────────────────────────
        slider_from    = cfg["slider_from"]  * 60   # Sek: Slider beginnt
        slider_until   = cfg["slider_until"] * 60   # Sek: Slider endet
        img_dur        = float(cfg["img_duration"])  # Sek pro Bild
        timer_between  = float(cfg.get("timer_between", 0))  # Sek Timer zwischen Bildern
        slider_loop    = cfg.get("slider_loop", True)
        fade_dur       = float(cfg["fade_duration"])

        # ── Fonts ─────────────────────────────────────────────────────
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

        # ── Zeitplan berechnen ────────────────────────────────────────
        # Wir bauen einen Plan: Liste von Segmenten mit (typ, dauer_in_sek)
        # Typ: "timer" oder index in slider_imgs
        # Die reale Zeit (time_left) läuft immer weiter — unabhängig vom Segment
        segments = self._build_segments(
            total_sec, slider_from, slider_until,
            slider_imgs, img_dur, timer_between, slider_loop)

        total_frames = int(total_sec * fps)

        # ── Output ────────────────────────────────────────────────────
        tmp_video    = out_path.replace(".mp4", "_noaudio.mp4")
        fourcc       = cv2.VideoWriter_fourcc(*"mp4v")
        writer       = cv2.VideoWriter(tmp_video, fourcc, fps, (w, h))
        bg_frame_idx = 0

        elapsed = 0.0   # Sekunden ab Videostart

        for seg_type, seg_dur in segments:
            seg_frames = int(seg_dur * fps)

            for f in range(seg_frames):
                time_left = max(0.0, total_sec - elapsed)

                # Hintergrund
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
                    frame = bg.copy()
                    frame = self._draw_timer_and_subtitle(
                        frame, time_left, cfg, w, h, get_font, font_path, sub_font_path)

                else:
                    # Bild-Segment: seg_type ist der Index in slider_imgs
                    img_idx = seg_type % len(slider_imgs)
                    slide   = slider_imgs[img_idx]
                    pos_in_seg = f / fps   # Position innerhalb dieses Segments

                    # Fade-in
                    if fade_dur > 0 and pos_in_seg < fade_dur:
                        a = pos_in_seg / fade_dur
                        frame = cv2.addWeighted(slide, a, bg, 1 - a, 0)
                    # Fade-out
                    elif fade_dur > 0 and pos_in_seg > seg_dur - fade_dur:
                        a = (seg_dur - pos_in_seg) / fade_dur
                        frame = cv2.addWeighted(slide, a, bg, 1 - a, 0)
                    else:
                        frame = slide.copy()

                writer.write(frame)
                elapsed += 1.0 / fps

                frame_idx = int(elapsed * fps)
                if frame_idx % 15 == 0:
                    pct = elapsed / total_sec
                    m   = int(time_left // 60)
                    s   = int(time_left % 60)
                    self.cb(min(pct, 1.0),
                            f"⏳ Rendere … {m:02d}:{s:02d}  ({int(pct*100)}%)",
                            frame_info=(frame_idx, total_frames))

        writer.release()
        if bg_cap:
            bg_cap.release()

        # ── Audio ─────────────────────────────────────────────────────
        if cfg.get("music_path") and shutil.which("ffmpeg"):
            self._mix_audio(tmp_video, out_path, total_sec, cfg)
            try:
                os.remove(tmp_video)
            except:
                pass
        else:
            os.replace(tmp_video, out_path)

        self.cb(1.0, "✅ Fertig!", frame_info=(total_frames, total_frames))

    # ── ZEITPLAN BUILDER ──────────────────────────────────────────────
    def _build_segments(self, total_sec, slider_from, slider_until,
                         slider_imgs, img_dur, timer_between, slider_loop):
        """
        Gibt eine Liste von (typ, dauer) zurück.
        typ = "timer"  → Countdown anzeigen
        typ = int      → Bild-Index anzeigen

        Zeitachse (time_left läuft rückwärts):
          total_sec → slider_from : Timer
          slider_from → slider_until : Slider-Zone
          slider_until → 0           : Timer

        Innerhalb der Slider-Zone:
          Loop=False: alle Bilder einmal, dazwischen timer_between Sek Timer
          Loop=True:  Bild → timer_between Timer → nächstes Bild → ... bis Zone voll
        """
        segs = []

        # Phase 1: Timer von Start bis slider_from
        pre_timer = total_sec - slider_from
        if pre_timer > 0:
            segs.append(("timer", pre_timer))

        # Phase 2: Slider-Zone
        zone_dur = slider_from - slider_until
        if zone_dur > 0 and slider_imgs:
            slider_segs = self._build_slider_zone(
                zone_dur, slider_imgs, img_dur, timer_between, slider_loop)
            segs.extend(slider_segs)
        elif zone_dur > 0:
            # Keine Bilder → einfach Timer
            segs.append(("timer", zone_dur))

        # Phase 3: Timer von slider_until bis 0
        if slider_until > 0:
            segs.append(("timer", slider_until))

        return segs

    def _build_slider_zone(self, zone_dur, slider_imgs,
                            img_dur, timer_between, slider_loop):
        """Baut die Segmente innerhalb der Slider-Zone."""
        segs  = []
        n     = len(slider_imgs)
        used  = 0.0   # bereits verplante Sekunden

        if not slider_loop:
            # ── Loop=False: alle Bilder genau einmal ──────────────────
            for i in range(n):
                if used >= zone_dur:
                    break
                # Bild
                dur = min(img_dur, zone_dur - used)
                segs.append((i, dur))
                used += dur
                # Timer zwischen Bildern (außer nach dem letzten)
                if i < n - 1 and timer_between > 0 and used < zone_dur:
                    dur_t = min(timer_between, zone_dur - used)
                    segs.append(("timer", dur_t))
                    used += dur_t
            # Restzeit als Timer
            rest = zone_dur - used
            if rest > 0.05:
                segs.append(("timer", rest))

        else:
            # ── Loop=True: Bild → Timer → Bild → Timer → ... ──────────
            # Runde: img_dur + timer_between Sek
            cycle = img_dur + timer_between
            img_idx = 0
            while used < zone_dur - 0.05:
                remaining = zone_dur - used

                # Bild
                dur_img = min(img_dur, remaining)
                segs.append((img_idx % n, dur_img))
                used += dur_img

                # Timer zwischen Bildern
                if timer_between > 0 and used < zone_dur - 0.05:
                    dur_t = min(timer_between, zone_dur - used)
                    segs.append(("timer", dur_t))
                    used += dur_t

                img_idx += 1

        return segs

    # ── TIMER + UNTERTITEL ZEICHNEN ───────────────────────────────────
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

        sub_enabled = cfg.get("subtitle_enabled", False)
        sub_lines   = []

        if sub_enabled:
            raw = cfg.get("subtitle_text", "").strip()
            if raw:
                sub_size = cfg.get("subtitle_size", 40)
                sub_font = get_font(sub_font_path, sub_size)
                sub_lines = [ln for ln in raw.splitlines() if ln.strip()]

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

    # ── AUDIO ─────────────────────────────────────────────────────────
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