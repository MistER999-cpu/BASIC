#!/usr/bin/env python3
"""BASIC Essentials launch reel, 24 s at 1080x1920 / 30 fps, built for Instagram.

    0-4 s    loading-glitch intro (tools/loading-intro.py, French labels)
    4-20 s   four 2x2 grid reveals (tools/grid-reveal.py timing), each with a
             frosted French text card and a push-to-white exit
    20-24 s  logo end card: tagline, the three colourways, call to action

Every section is drawn frame by frame into one encode, so nothing is
re-compressed between scenes. The soundtrack (tools/reel-audio.py) is built
from the same timeline, so every cut, glitch and pop has its sound on the frame.

    python3 tools/reel.py                       # -> out/basic-reel.mp4
    python3 tools/reel.py --stills 60,190,700   # review frames -> out/reel-fNNN.png
    python3 tools/reel.py --video-only          # skip the soundtrack

On-screen copy lives in assets/reel-copy.json.
"""
import argparse
import importlib.util
import json
import os
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"),
                                                  os.path.join(ROOT, "tools", f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


intro = _load("loading-intro")
grid = _load("grid-reveal")

W, H, FPS = 1080, 1920, 30
INTRO_F = intro.FRAMES                 # 120: 2 bars at 120 BPM
GRID_F = 120                           # 2 bars per grid
END_F = 120
INTRO_Y = (H - intro.H) // 2           # the 1080x1350 intro sits centred on white

GRIDS = [  # folder, small-tile crop focus, copy key
    ("model1-outfit1", [0.15, 0.20, 0.10, 0.0], "g1"),
    ("model2-outfit1", [0.12, 0.18, 0.08, 0.40], "g2"),
    ("model1-outfit2", [0.16, 0.10, 0.12, 0.25], "g3"),
    ("model2-outfit2", [0.12, 0.12, 0.10, 0.45], "g4"),
]
TOTAL_F = INTRO_F + len(GRIDS) * GRID_F + END_F

# grid-local frames (POP / SNAP come from grid-reveal.py)
HOLD_ZOOM = (grid.SNAP[-1], 113, 0.035)   # slow push-in on the full grid
CARD_IN, CARD_OUT = (50, 58), (104, 110)
EXIT = (113, 120)                         # push to white into the next section
INTRO_EXIT = (113, 120)

# the card sits above the grid seam: bottom-row faces start around y=1005
CARD_W, CARD_BOTTOM = 840, 988

# end-card-local frames
LOGO_IN = (3, 26)
TAG_IN = (26, 38)
SWATCHES = [40, 44, 48]
CTA_IN = (54, 66)
SWATCH_RGB = [(18, 18, 18), (246, 246, 243), (212, 180, 150)]   # noir, blanc, nude

FONTS = os.path.join(ROOT, "assets", "fonts")
SERIF = os.path.join(FONTS, "CormorantGaramond-Medium.ttf")
SERIF_IT = os.path.join(FONTS, "CormorantGaramond-MediumItalic.ttf")
SANS = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"
INK = (17, 17, 17)
MUTED = (96, 96, 96)


def ease_out(t):
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


def ease_in(t):
    t = min(max(t, 0.0), 1.0)
    return t ** 3


def smooth(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def zoom(img, s, cx=W / 2, cy=H / 2):
    """Sub-pixel zoom about (cx, cy); affine keeps slow push-ins free of jitter."""
    if abs(s - 1) < 1e-4:
        return img
    a = 1 / s
    return img.transform(img.size, Image.AFFINE, (a, 0, cx - cx * a, 0, a, cy - cy * a),
                         resample=Image.BICUBIC)


def push_to_white(img, t):
    """Exit transition: accelerating zoom with a short zoom blur, washing to white."""
    e = ease_in(t)
    s = 1 + 0.14 * e
    layers = [zoom(img, s * k) for k in (1.0, 1.015, 1.03)] if t > 0.15 else [zoom(img, s)]
    acc = np.mean([np.asarray(l, np.float32) for l in layers], axis=0)
    white = min(1.0, 0.15 + 0.85 * t ** 1.6) if t < 1 else 1.0
    acc = acc * (1 - white) + 255 * white
    return Image.fromarray(acc.clip(0, 255).astype(np.uint8))


def flash(img, box, amount):
    if amount <= 0:
        return
    x0, y0, x1, y1 = box
    region = img.crop(box)
    img.paste(Image.blend(region, Image.new("RGB", region.size, "white"), amount), (x0, y0))


# ---------------------------------------------------------------- text card

def tracked(draw, xy, text, font, fill, track):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + track


def tracked_width(draw, text, font, track):
    return sum(draw.textlength(ch, font=font) for ch in text) + track * (len(text) - 1)


class Card:
    """Frosted white card with a tracked sans kicker over a serif headline."""

    def __init__(self, kicker, lines):
        self.kicker, self.lines = kicker.upper(), lines
        self.f_kick = ImageFont.truetype(SANS, 28)
        self.f_head = ImageFont.truetype(SERIF, 70)
        self.track = 6
        probe = ImageDraw.Draw(Image.new("L", (10, 10)))
        self.kick_w = tracked_width(probe, kicker, self.f_kick, self.track)
        self.line_w = [probe.textlength(l, font=self.f_head) for l in lines]
        widest = max([self.kick_w] + self.line_w)
        if widest > CARD_W - 80:
            raise SystemExit(f"card copy too wide ({widest:.0f}px): {kicker!r} {lines!r}")
        self.line_h = 76
        self.h = 44 + 30 + 20 + self.line_h * len(lines) + 40
        self.x0 = (W - CARD_W) // 2
        self.y0 = CARD_BOTTOM - self.h
        self.mask = Image.new("L", (CARD_W, self.h), 0)
        ImageDraw.Draw(self.mask).rounded_rectangle((0, 0, CARD_W - 1, self.h - 1), radius=30, fill=255)
        sh = Image.new("L", (CARD_W + 120, self.h + 120), 0)
        ImageDraw.Draw(sh).rounded_rectangle((60, 70, 60 + CARD_W, 70 + self.h), radius=30, fill=70)
        self.shadow = sh.filter(ImageFilter.GaussianBlur(22))

    def draw(self, frame, f):
        """Composite onto an RGB frame at grid-local frame f."""
        if f < CARD_IN[0] or f >= CARD_OUT[1]:
            return frame
        if f < CARD_OUT[0]:
            p = ease_out((f - CARD_IN[0] + 1) / (CARD_IN[1] - CARD_IN[0]))
            alpha, dy = p, (1 - p) * 28
        else:
            q = smooth((f - CARD_OUT[0] + 1) / (CARD_OUT[1] - CARD_OUT[0]))
            alpha, dy = 1 - q, -14 * q
        y0 = int(round(self.y0 + dy))
        base = frame.convert("RGBA")

        # soft shadow, then frosted glass: blurred backdrop washed toward white
        shadow = Image.new("RGBA", self.shadow.size, (0, 0, 0, 0))
        shadow.putalpha(self.shadow.point(lambda v: int(v * alpha)))
        base.alpha_composite(shadow, (self.x0 - 60, y0 - 60))
        pad = 40
        box = (self.x0 - pad, y0 - pad, self.x0 + CARD_W + pad, y0 + self.h + pad)
        glass = frame.crop(box).filter(ImageFilter.GaussianBlur(24))
        glass = glass.crop((pad, pad, pad + CARD_W, pad + self.h))
        glass = Image.blend(glass, Image.new("RGB", glass.size, "white"), 0.72).convert("RGBA")
        glass.putalpha(self.mask.point(lambda v: int(v * alpha)))
        base.alpha_composite(glass, (self.x0, y0))

        # text, staggered: kicker, then each headline line rising into place
        layer = Image.new("RGBA", (CARD_W, self.h), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        steps = [CARD_IN[0] + 2 + 3 * k for k in range(1 + len(self.lines))]

        def a_for(k):
            if f >= CARD_OUT[0]:
                return alpha
            return ease_out((f - steps[k]) / 7)

        def rise(k):
            return 0 if f >= CARD_OUT[0] else (1 - a_for(k)) * 12

        ka = a_for(0)
        if ka > 0:
            tracked(d, ((CARD_W - self.kick_w) / 2, 44 + rise(0)), self.kicker, self.f_kick,
                    MUTED + (int(255 * ka),), self.track)
        for i, line in enumerate(self.lines):
            la = a_for(i + 1)
            if la > 0:
                y = 44 + 30 + 20 + i * self.line_h - 10 + rise(i + 1)
                d.text(((CARD_W - self.line_w[i]) / 2, y), line, font=self.f_head,
                       fill=INK + (int(255 * la),))
        base.alpha_composite(layer, (self.x0, y0))
        return base.convert("RGB")


# ---------------------------------------------------------------- sections

class IntroSection:
    def __init__(self, copy):
        intro.LABEL, intro.DONE = copy["intro_label"], copy["intro_done"]
        self.sharp, self.centres = intro.layout(
            os.path.join(ROOT, "assets/flatlays/set1-cami-shorts-black.jpg"),
            os.path.join(ROOT, "assets/flatlays/set2-tee-capri-black.jpg"))
        self.sprites = intro.spinner_sprites()

    def frame(self, f):
        rng = np.random.default_rng(7000 + f)
        canvas = Image.new("RGB", (W, H), "white")
        canvas.paste(Image.fromarray(intro.render_frame(f, self.sharp, self.centres, self.sprites, rng)),
                     (0, INTRO_Y))
        if f >= INTRO_EXIT[0]:
            canvas = push_to_white(canvas, (f - INTRO_EXIT[0] + 1) / (INTRO_EXIT[1] - INTRO_EXIT[0]))
        return canvas


class GridSection:
    def __init__(self, folder, focus, card):
        paths = sorted(p for p in os.listdir(os.path.join(ROOT, "assets/shoots", folder))
                       if p.lower().endswith((".jpg", ".jpeg", ".png")))
        if len(paths) != 4:
            raise SystemExit(f"{folder}: need 4 images, found {len(paths)}")
        imgs = [Image.open(os.path.join(ROOT, "assets/shoots", folder, p)).convert("RGB") for p in paths]
        self.small = [grid.cover(im, grid.TILE_W, grid.TILE_H, fy) for im, fy in zip(imgs, focus)]
        self.full = [grid.cover(im, grid.CX, grid.CY, 0.5) for im in imgs]
        self.card = card

    def frame(self, f):
        canvas = Image.new("RGB", (W, H), "white")
        for i in range(4):
            if f < grid.POP[i]:
                continue
            full = f >= grid.SNAP[i]
            x, y, w, h = grid.rects(i, full)
            canvas.paste((self.full if full else self.small)[i], (x, y))
            # a camera-flash kiss on the frame each tile lands
            since = f - (grid.SNAP[i] if full else grid.POP[i])
            amount = ([0.30, 0.10] if full else [0.55, 0.20])[since] if since < 2 else 0
            flash(canvas, (x, y, x + w, y + h), amount)
        s0, s1, depth = HOLD_ZOOM
        if f >= s0:
            canvas = zoom(canvas, 1 + depth * smooth((f - s0) / (s1 - s0)))
        canvas = self.card.draw(canvas, f)
        if f >= EXIT[0]:
            canvas = push_to_white(canvas, (f - EXIT[0] + 1) / (EXIT[1] - EXIT[0]))
        return canvas


class EndSection:
    def __init__(self, copy):
        logo = Image.open(os.path.join(ROOT, "assets/brand/basic-logo.png")).convert("RGBA")
        logo = logo.crop(logo.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox())
        lw = 660
        self.logo = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
        self.logo_xy = ((W - lw) // 2, 690)
        self.f_tag = ImageFont.truetype(SERIF_IT, 54)
        self.f_cta = ImageFont.truetype(SANS, 24)
        self.tag, self.cta = copy["end_tagline"], copy["end_cta"].upper()
        probe = ImageDraw.Draw(Image.new("L", (10, 10)))
        self.tag_w = probe.textlength(self.tag, font=self.f_tag)
        self.cta_w = tracked_width(probe, self.cta, self.f_cta, 6)
        for wdt, txt in ((self.tag_w, self.tag), (self.cta_w, self.cta)):
            if wdt > W - 160:
                raise SystemExit(f"end card copy too wide ({wdt:.0f}px): {txt!r}")
        logo_bottom = self.logo_xy[1] + self.logo.height
        self.tag_y = logo_bottom + 56
        self.sw_y = self.tag_y + 112
        self.cta_y = self.sw_y + 62

    def frame(self, f):
        canvas = Image.new("RGBA", (W, H), (255, 255, 255, 255))
        # logo: de-blurs and settles in, with a two-frame chromatic hit as it lands
        p = ease_out((f - LOGO_IN[0]) / (LOGO_IN[1] - LOGO_IN[0]))
        if p > 0:
            s = 1.06 - 0.06 * p
            lg = self.logo.resize((round(self.logo.width * s), round(self.logo.height * s)), Image.LANCZOS)
            blur = 9 * (1 - p)
            if blur > 0.3:
                lg = lg.filter(ImageFilter.GaussianBlur(blur))
            lg.putalpha(lg.getchannel("A").point(lambda v: int(v * min(1, p * 1.4))))
            cx = self.logo_xy[0] + self.logo.width / 2
            cy = self.logo_xy[1] + self.logo.height / 2
            pos = (round(cx - lg.width / 2), round(cy - lg.height / 2))
            split = {LOGO_IN[0] + 1: 9, LOGO_IN[0] + 2: 5}.get(f, 0)
            if split:
                for dx, tint in ((-split, (0, 200, 255)), (split, (255, 40, 140))):
                    ghost = Image.new("RGBA", lg.size, tint + (0,))
                    ghost.putalpha(lg.getchannel("A").point(lambda v: int(v * 0.55)))
                    canvas.alpha_composite(ghost, (pos[0] + dx, pos[1]))
            canvas.alpha_composite(lg, pos)

        text = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        td = ImageDraw.Draw(text)
        ta = ease_out((f - TAG_IN[0]) / (TAG_IN[1] - TAG_IN[0]))
        if ta > 0:
            td.text(((W - self.tag_w) / 2, self.tag_y + (1 - ta) * 16), self.tag, font=self.f_tag,
                    fill=INK + (int(255 * ta),))
        ca = ease_out((f - CTA_IN[0]) / (CTA_IN[1] - CTA_IN[0]))
        if ca > 0:
            tracked(td, ((W - self.cta_w) / 2, self.cta_y), self.cta, self.f_cta,
                    MUTED + (int(255 * ca),), 6)
        canvas.alpha_composite(text)

        d = ImageDraw.Draw(canvas)

        # the three colourways pop in one by one
        for k, (start, rgb) in enumerate(zip(SWATCHES, SWATCH_RGB)):
            t = (f - start) / 6
            if t <= 0:
                continue
            t = min(t, 1)
            pop = 1 + 0.25 * np.sin(np.pi * t) if t < 1 else 1   # overshoot then settle
            r = 17 * ease_out(t) * pop
            cx, cy = W / 2 + (k - 1) * 62, self.sw_y
            outline = (196, 196, 196) if min(rgb) > 235 else None   # only the white swatch needs an edge
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=rgb + (255,), outline=outline,
                      width=2 if outline else 0)
        return canvas.convert("RGB")


# ---------------------------------------------------------------- timeline

def build_sections(copy):
    secs = [("intro", IntroSection(copy), INTRO_F)]
    for folder, focus, key in GRIDS:
        secs.append((key, GridSection(folder, focus, Card(copy[f"{key}_kicker"], copy[f"{key}_headline"])), GRID_F))
    secs.append(("end", EndSection(copy), END_F))
    return secs


def timeline():
    """Seconds of every audible event, shared with tools/reel-audio.py."""
    t = lambda frame: frame / FPS
    ev = {
        "fps": FPS, "total": TOTAL_F / FPS, "bpm": 120,
        "intro": {
            "bursts": [(t(s), t(e + 1), amt) for s, e, amt, _ in intro.BURSTS],
            "ticks": [t(f) for f in intro.TICKS],
            "progress": [(t(f), p) for f, p in intro.PROGRESS],
            "complete": t(intro.COMPLETE),
            "reveal": (t(intro.REVEAL[0]), t(intro.REVEAL[1])),
            "exit": (t(INTRO_EXIT[0]), t(INTRO_EXIT[1])),
        },
        "grids": [],
    }
    for k in range(len(GRIDS)):
        g0 = INTRO_F + k * GRID_F
        ev["grids"].append({
            "start": t(g0),
            "pops": [t(g0 + f) for f in grid.POP],
            "snaps": [t(g0 + f) for f in grid.SNAP],
            "card_in": t(g0 + CARD_IN[0]), "card_out": t(g0 + CARD_OUT[0]),
            "exit": (t(g0 + EXIT[0]), t(g0 + EXIT[1])),
        })
    e0 = INTRO_F + len(GRIDS) * GRID_F
    ev["end"] = {
        "start": t(e0), "logo": t(e0 + LOGO_IN[0]), "tag": t(e0 + TAG_IN[0]),
        "swatches": [t(e0 + f) for f in SWATCHES], "cta": t(e0 + CTA_IN[0]),
    }
    return ev


def render_frame(secs, n):
    for name, sec, length in secs:
        if n < length:
            return sec.frame(n)
        n -= length
    raise IndexError(n)


COVER_TILES = [  # both models, both sets, all three colours
    ("model1-outfit1", "1-hero-black.jpg"), ("model2-outfit1", "1-hero-black.jpg"),
    ("model1-outfit2", "3-stride-nude.jpg"), ("model2-outfit2", "2-cube-white.jpg"),
]


def render_cover(copy, path):
    """Reel cover: 2x2 grid of both models with the logo on a frosted card, laid out
    inside the centre 1080x1440 so the 3:4 profile-grid crop loses nothing."""
    canvas = Image.new("RGB", (W, H), "white")
    top = (H - 1440) // 2                       # the 3:4 profile-grid crop
    tw, th = W // 2, 720
    for i, (folder, name) in enumerate(COVER_TILES):
        im = Image.open(os.path.join(ROOT, "assets/shoots", folder, name)).convert("RGB")
        canvas.paste(grid.cover(im, tw, th, 0.12), ((i % 2) * tw, top + (i // 2) * th))
    logo = Image.open(os.path.join(ROOT, "assets/brand/basic-logo.png")).convert("RGBA")
    logo = logo.crop(logo.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox())
    lw = 520
    logo = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    f_tag = ImageFont.truetype(SERIF_IT, 46)
    probe = ImageDraw.Draw(Image.new("L", (10, 10)))
    tag_w = probe.textlength(copy["end_tagline"], font=f_tag)
    ch = 44 + logo.height + 30 + 52 + 44
    x0, y0 = (W - CARD_W) // 2, top + th + 40 - ch     # over the seam, clear of the bottom-row faces
    pad = 40
    glass = canvas.crop((x0 - pad, y0 - pad, x0 + CARD_W + pad, y0 + ch + pad)).filter(ImageFilter.GaussianBlur(24))
    glass = Image.blend(glass.crop((pad, pad, pad + CARD_W, pad + ch)), Image.new("RGB", (CARD_W, ch), "white"), 0.78)
    mask = Image.new("L", (CARD_W, ch), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, CARD_W - 1, ch - 1), radius=30, fill=255)
    base = canvas.convert("RGBA")
    sh = Image.new("L", (CARD_W + 120, ch + 120), 0)
    ImageDraw.Draw(sh).rounded_rectangle((60, 70, 60 + CARD_W, 70 + ch), radius=30, fill=70)
    shadow = Image.new("RGBA", sh.size, (0, 0, 0, 0))
    shadow.putalpha(sh.filter(ImageFilter.GaussianBlur(22)))
    base.alpha_composite(shadow, (x0 - 60, y0 - 60))
    g = glass.convert("RGBA")
    g.putalpha(mask)
    base.alpha_composite(g, (x0, y0))
    base.alpha_composite(logo, ((W - logo.width) // 2, y0 + 44))
    text = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(text).text(((W - tag_w) / 2, y0 + 44 + logo.height + 22), copy["end_tagline"],
                              font=f_tag, fill=INK + (255,))
    base.alpha_composite(text)
    base.convert("RGB").save(path, quality=95)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "basic-reel.mp4"))
    ap.add_argument("--copy", default=os.path.join(ROOT, "assets", "reel-copy.json"))
    ap.add_argument("--stills", help="comma-separated global frame numbers to export as PNG")
    ap.add_argument("--video-only", action="store_true")
    ap.add_argument("--cover", action="store_true", help="only render the cover image")
    args = ap.parse_args()

    with open(args.copy, encoding="utf-8") as fh:
        copy = json.load(fh)
    out_dir = os.path.dirname(args.out)
    os.makedirs(out_dir, exist_ok=True)
    if args.cover:
        print(render_cover(copy, os.path.join(out_dir, "basic-reel-cover.jpg")))
        return
    secs = build_sections(copy)

    if args.stills:
        for n in map(int, args.stills.split(",")):
            path = os.path.join(out_dir, f"reel-f{n:03d}.png")
            render_frame(secs, n).save(path)
            print(path)
        return

    silent = os.path.join(out_dir, "basic-reel-video.mp4")
    ff = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
         "-c:v", "libx264", "-preset", "slow", "-crf", "15", "-profile:v", "high", "-level", "4.2",
         "-g", "60", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
         "-color_range", "tv", "-movflags", "+faststart", silent],
        stdin=subprocess.PIPE)
    for n in range(TOTAL_F):
        ff.stdin.write(render_frame(secs, n).tobytes())
    ff.stdin.close()
    if ff.wait():
        raise SystemExit("ffmpeg (video) failed")
    print(silent)
    if args.video_only:
        return

    audio = _load("reel-audio")
    wav = os.path.join(out_dir, "basic-reel-audio.wav")
    audio.render(timeline(), wav)
    audio.mux(silent, wav, args.out)
    print(args.out)


if __name__ == "__main__":
    main()
