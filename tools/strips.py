#!/usr/bin/env python3
"""Three-strip "sliced print" reel.

The frame is cut into three horizontal paper strips laid on a lilac-grey
table. Each strip hard-cuts on its own clock, staggered top -> middle ->
bottom, so for most of the clip the viewer sees one look's head over another
look's body over a third look's trousers. The clip opens and closes with all
three strips locked on one image.

Shots come from one folder, and the file name says what each one is:

    <colour>_<kind>_<anything>.jpg      e.g. brown_full_1.jpg, black_detail_neck.png

kinds:
    full     full-body, head near the top, feet near the bottom
    profile  full-body side view (sliced exactly like full)
    half     waist-up / three-quarter crop
    detail   macro shot - fills a single strip instead of being sliced

Full and profile shots are re-framed so every figure stands at the same
height and on the same centreline (--no-align to skip). That is what makes a
head from one shot sit on a body from another.

    python3 tools/strips.py assets/strips --out out/strips.mp4
    python3 tools/strips.py assets/strips --audio song.mp3 --step 0.2
    python3 tools/strips.py assets/strips --timeline out/strips.timeline.json   # replay an edited cut
"""
import argparse
import json
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

KINDS = ("full", "profile", "half", "detail")
SLICED = ("full", "profile", "half")
EXTS = {".jpg", ".jpeg", ".png", ".webp"}

TABLE = (214, 210, 222)        # the lilac-grey the prints lie on
INK = (22, 17, 14)             # BASIC ink, for the wordmark on light fabric
PAPER = (247, 244, 239)        # BASIC paper, for the wordmark on dark fabric
# strip bands as fractions of frame height, measured off the reference
BANDS = [(0.016, 0.343), (0.347, 0.672), (0.676, 0.992)]
FIG_TOP, FIG_BOTTOM = 0.035, 0.975   # where an aligned full-body figure stands


# ---------------------------------------------------------------- shots

def load_shots(folder):
    shots = []
    for p in sorted(Path(folder).iterdir()):
        if p.suffix.lower() not in EXTS:
            continue
        parts = p.stem.lower().split("_")
        if len(parts) < 2 or parts[1] not in KINDS:
            print(f"skip {p.name}: name it <colour>_<kind>_..., kind one of {KINDS}",
                  file=sys.stderr)
            continue
        shots.append({"id": p.stem, "path": str(p), "colour": parts[0], "kind": parts[1]})
    if not shots:
        sys.exit(f"no usable shots in {folder}")
    return shots


def backdrop_mask(rgb):
    """Foreground mask from distance to the border colour, heavily smoothed so a
    garment close to the backdrop colour does not get carved open."""
    a = np.asarray(rgb, dtype=np.float32)
    border = np.concatenate([a[:8].reshape(-1, 3), a[-8:].reshape(-1, 3),
                             a[:, :8].reshape(-1, 3), a[:, -8:].reshape(-1, 3)])
    bg = np.median(border, axis=0)
    d = np.sqrt(((a - bg) ** 2).sum(axis=2))
    d = np.asarray(Image.fromarray(np.clip(d, 0, 255).astype(np.uint8))
                   .filter(ImageFilter.BoxBlur(6)), dtype=np.float32)
    return d > max(18.0, np.percentile(d, 60) * 0.5), tuple(int(v) for v in bg)


def fit(img, W, H, align):
    """Place a source image on a WxH canvas."""
    img = img.convert("RGB")
    if align:
        small = img.copy()
        small.thumbnail((400, 400))
        mask, bg = backdrop_mask(small)
        ys, xs = np.nonzero(mask)
        if len(ys) > mask.size * 0.02:
            s = img.width / small.width
            top, bot = ys.min() * s, ys.max() * s
            cx = np.median(xs) * s
            scale = (FIG_BOTTOM - FIG_TOP) * H / max(1.0, bot - top)
            img2 = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
            canvas = Image.new("RGB", (W, H), bg)
            canvas.paste(img2, (round(W / 2 - cx * scale), round(FIG_TOP * H - top * scale)))
            return canvas
    # cover-fit, biased upward so heads survive the crop
    scale = max(W / img.width, H / img.height)
    img2 = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    x = (img2.width - W) // 2
    y = int((img2.height - H) * 0.3)
    return img2.crop((x, y, x + W, y + H))


def cover(img, w, h):
    scale = max(w / img.width, h / img.height)
    img2 = img.convert("RGB").resize((round(img.width * scale) + 1, round(img.height * scale) + 1),
                                     Image.LANCZOS)
    x, y = (img2.width - w) // 2, (img2.height - h) // 2
    return img2.crop((x, y, x + w, y + h))


# ---------------------------------------------------------------- timeline

def build_timeline(shots, duration, step, seed, order=None):
    """Events: {t, strips:[0..2], shot, wordmark}. Mirrors the reference rhythm:
    one strip cuts every `step` seconds in a top-mid-bottom cascade, now and then
    two at once, and every colourway gets its own stretch."""
    rnd = random.Random(seed)
    colours = list(dict.fromkeys(s["colour"] for s in shots))
    if order:
        unknown = [c for c in order if c not in colours]
        if unknown:
            sys.exit(f"--order names {unknown}, but the shots are {colours}")
        colours = order + [c for c in colours if c not in order]
    by = {c: [s for s in shots if s["colour"] == c] for c in colours}

    def hero(c):
        pool = [s for s in by[c] if s["kind"] == "full"] or \
               [s for s in by[c] if s["kind"] in SLICED] or by[c]
        return pool[0]

    hold_end = 1.0
    body_end = duration - hold_end
    first = hero(colours[0])
    events = [{"t": 0.0, "strips": [0, 1, 2], "shot": first["id"], "wordmark": False}]
    current = [first["id"]] * 3
    phase_len = (body_end - step) / len(colours)

    t, k = step * 2, 0
    while t < body_end - step / 2:
        colour = colours[min(int((t - step) / phase_len), len(colours) - 1)]
        strip = k % 3
        strips = [strip]
        if rnd.random() < 0.18:
            strips.append((strip + 1) % 3)
        for sidx in strips:
            pool = by[colour]
            if rnd.random() < 0.15 and len(colours) > 1:          # a stray from another colourway
                pool = by[rnd.choice([c for c in colours if c != colour])]
            allowed = [s for s in pool if s["id"] != current[sidx] and
                       (s["kind"] != "detail" or sidx == 1)]       # macros live in the middle
            if not allowed:
                allowed = [s for s in pool if s["id"] != current[sidx]] or pool
            shot = rnd.choice(allowed)
            # never let all three strips settle on one image mid-clip
            if all(current[j] == shot["id"] for j in range(3) if j != sidx):
                continue
            current[sidx] = shot["id"]
            events.append({"t": round(t, 3), "strips": [sidx], "shot": shot["id"],
                           "wordmark": sidx == 1 and shot["kind"] != "detail" and rnd.random() < 0.45})
        t += step
        k += 1

    last = hero(colours[-1])
    events.append({"t": round(body_end, 3), "strips": [0, 1, 2], "shot": last["id"], "wordmark": True})
    return {"duration": duration, "seed": seed, "step": step, "events": events}


# ---------------------------------------------------------------- render

class Renderer:
    def __init__(self, shots, W, H, align, font_path, wordmark):
        self.W, self.H = W, H
        self.shots = {s["id"]: s for s in shots}
        self.canvas = {}
        self.align = align
        self.wordmark = wordmark
        self.font = load_font(font_path, int(W * 0.155))

    def full_canvas(self, sid):
        if sid not in self.canvas:
            s = self.shots[sid]
            self.canvas[sid] = fit(Image.open(s["path"]), self.W, self.H,
                                   self.align and s["kind"] in ("full", "profile"))
        return self.canvas[sid]

    def strip_image(self, sid, band):
        s = self.shots[sid]
        y0, y1 = round(band[0] * self.H), round(band[1] * self.H)
        if s["kind"] == "detail":
            return cover(Image.open(s["path"]), self.W, y1 - y0)
        return self.full_canvas(sid).crop((0, y0, self.W, y1))

    def frame(self, state):
        W, H = self.W, self.H
        out = Image.new("RGB", (W, H), TABLE)
        shadow = Image.new("L", (W, H), 0)
        layers = []
        for i, (sid, wm, jitter) in enumerate(state):
            band = BANDS[i]
            img = self.strip_image(sid, band)
            if wm and self.wordmark:
                img = img.copy()
                d = ImageDraw.Draw(img)
                bb = d.textbbox((0, 0), self.wordmark, font=self.font)
                x = (img.width - (bb[2] - bb[0])) / 2 - bb[0]
                y = (img.height - (bb[3] - bb[1])) / 2 - bb[1]
                behind = img.crop((int(x + bb[0]), int(y + bb[1]), int(x + bb[2]), int(y + bb[3])))
                light = np.asarray(behind.convert("L"), dtype=np.float32).mean() > 115
                d.text((x, y), self.wordmark, font=self.font, fill=INK if light else PAPER)
            angle, dx, dy = jitter
            pad = 24
            sheet = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2), (0, 0, 0, 0))
            sheet.paste(img, (pad, pad))
            alpha = Image.new("L", sheet.size, 0)
            ImageDraw.Draw(alpha).rectangle((pad, pad, pad + img.width - 1, pad + img.height - 1), 255)
            sheet.putalpha(alpha)
            sheet = sheet.rotate(angle, resample=Image.BICUBIC, expand=False)
            pos = (round(dx) - pad, round(band[0] * H + dy) - pad)
            layers.append((sheet, pos))
            shadow.paste(sheet.getchannel("A").point(lambda v: v * 0.5),
                         (pos[0], pos[1] + 5), sheet.getchannel("A"))
        shadow = shadow.filter(ImageFilter.GaussianBlur(7))
        out.paste(Image.new("RGB", (W, H), (120, 112, 130)), (0, 0), shadow.point(lambda v: v * 0.55))
        for sheet, pos in layers:
            out.paste(sheet, pos, sheet)
            # a hairline of paper edge catches the light on the top of each print
            ImageDraw.Draw(out).line((0, pos[1] + 24, W, pos[1] + 24), fill=(250, 250, 252), width=2)
        return out


def load_font(path, size):
    tries = [path] if path else []
    tries += ["/usr/share/fonts/truetype/inter/Inter-Black.ttf",
              "/usr/share/fonts/opentype/inter/Inter-Black.otf",
              "C:/Windows/Fonts/arialbd.ttf", "/System/Library/Fonts/Helvetica.ttc",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    for p in tries:
        try:
            return ImageFont.truetype(p, size)
        except (OSError, TypeError):
            continue
    try:
        from matplotlib import font_manager
        return ImageFont.truetype(font_manager.findfont("Inter:black"), size)
    except Exception:
        return ImageFont.load_default()


def render(timeline, shots, args):
    W, H, fps = args.width, args.height, args.fps
    r = Renderer(shots, W, H, not args.no_align, args.font, args.wordmark)
    rnd = random.Random(timeline["seed"] + 1)
    known = {s["id"] for s in shots}
    events = sorted(timeline["events"], key=lambda e: e["t"])
    for e in events:
        if e["shot"] not in known:
            sys.exit(f"timeline names shot {e['shot']!r}, which is not in the folder")

    state = [None, None, None]
    ei, cache_key, cache = 0, None, None
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(fps), "-i", "-"]
    if args.audio:
        cmd += ["-i", args.audio, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", args.out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = round(timeline["duration"] * fps)
    for f in range(n):
        t = f / fps
        while ei < len(events) and events[ei]["t"] <= t + 1e-6:
            e = events[ei]
            for sidx in e["strips"]:
                # each re-laid print lands a touch crooked, like a hand placed it
                jit = (rnd.uniform(-0.35, 0.35), rnd.uniform(-5, 5), rnd.uniform(-2, 2))
                if len(e["strips"]) == 3:
                    jit = (rnd.uniform(-0.12, 0.12), 0, 0)
                state[sidx] = (e["shot"], bool(e.get("wordmark")) and sidx == 1, jit)
            ei += 1
        key = tuple(state)
        if key != cache_key:
            cache_key, cache = key, r.frame(state).tobytes()
        proc.stdin.write(cache)
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg failed")
    if args.cover:
        Image.frombytes("RGB", (W, H), cache).save(args.cover, quality=95)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder")
    ap.add_argument("--out", default="out/strips.mp4")
    ap.add_argument("--duration", type=float, default=8.7)
    ap.add_argument("--step", type=float, default=0.2,
                    help="seconds between strip cuts (0.2 = the reference; 60/BPM to sit on a beat)")
    ap.add_argument("--seed", type=int, default=7, help="change for a different shuffle")
    ap.add_argument("--order", help="colourway order, e.g. black,burgundy,brown (the last one closes the reel)")
    ap.add_argument("--timeline", help="replay a saved (and hand-edited) timeline json")
    ap.add_argument("--audio")
    ap.add_argument("--wordmark", default="BASIC", help='"" for none')
    ap.add_argument("--font", help="path to a .ttf/.otf for the wordmark")
    ap.add_argument("--no-align", action="store_true")
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1920)
    ap.add_argument("--fps", type=int, default=30)
    args = ap.parse_args()

    shots = load_shots(args.folder)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    if args.timeline:
        timeline = json.loads(Path(args.timeline).read_text())
    else:
        timeline = build_timeline(shots, args.duration, args.step, args.seed,
                                  args.order.split(",") if args.order else None)
        tl_path = Path(args.out).with_suffix(".timeline.json")
        tl_path.write_text(json.dumps(timeline, indent=1))
        print(f"timeline -> {tl_path}  (edit it and pass --timeline to re-cut)")
    args.cover = str(Path(args.out).with_suffix(".cover.jpg"))
    render(timeline, shots, args)
    print(f"reel -> {args.out}\ncover -> {args.cover}")


if __name__ == "__main__":
    main()
