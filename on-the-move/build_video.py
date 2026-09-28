"""Build the BASIC ESSENTIALS "on the move" ad.

Timeline (30 fps, every shot 9 frames = 0.30s, the reference's cut grid):

  0.0-4.5s  replica section   model, model, letter x5 spelling B A S I C
                              (full body on pure white, motion-trail ghost)
  4.5-8.1s  product section   close-up, close-up, colour card x4
                              (ivoire, sable, chocolat, noir)
  8.1-9.0s  finale            4-colour grid (model A), grid (model B), logo
  9.0-14.0s end video         endvideo/end.mp4

Audio is the reference track, extended on a 2-bar loop to cover the end
video and faded out.

Needs build/cutouts/ (run make_cutouts.py first).

Usage:  python3 build_video.py [--preview]   (--preview writes a contact
sheet of every shot instead of encoding the video)
"""
import os
import subprocess
import sys

import cv2
import numpy as np
import soundfile as sf
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")
FFMPEG = "/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2"

W, H, FPS, SHOT = 1080, 1920, 30, 9
WHITE = np.array([255, 255, 255], np.float32)

# Reference framing (measured): head top at 16.2% of frame height, person
# 67.8% of frame height, centred.
FULL_TOP, FULL_H = 0.162 * H, 0.678 * H

COLOURS = {  # tank colour, text colour on that card
    "ivoire": ((240, 234, 224), (42, 29, 22)),
    "sable": ((205, 175, 150), (42, 29, 22)),
    "chocolat": ((88, 56, 42), (243, 237, 228)),
    "noir": ((22, 21, 24), (243, 237, 228)),
}
ORDER = ["ivoire", "sable", "chocolat", "noir"]
IMAGE = {  # (model, colour) -> cutout name
    ("A", "ivoire"): "A_cream", ("B", "ivoire"): "B_cream",
    ("A", "sable"): "A_beige", ("B", "sable"): "B_beige",
    ("A", "chocolat"): "A_brown", ("B", "chocolat"): "B_brown",
    ("A", "noir"): "A_black", ("B", "noir"): "B_black",
}
INK = (29, 26, 23)


# ----------------------------------------------------------------- fonts

def _instance(src, loc, dst):
    dst = os.path.join(BUILD, dst)
    if not os.path.exists(dst):
        instancer.instantiateVariableFont(TTFont(os.path.join(HERE, "fonts", src)), loc).save(dst)
    return dst


def font(kind, size):
    path = {
        "serif_italic": lambda: _instance("CormorantGaramond-Italic.ttf", {"wght": 500}, "_cg_it500.ttf"),
        "sans": lambda: _instance("Jost.ttf", {"wght": 450}, "_jost450.ttf"),
    }[kind]()
    return ImageFont.truetype(path, size)


def draw_tracked(draw, x, y, text, fnt, fill, tracking=0.0, anchor="m"):
    """Draw text with letter spacing (tracking in em). anchor: l, m or r on
    x; y is the vertical middle of the caps."""
    widths = [draw.textlength(c, font=fnt) for c in text]
    extra = tracking * fnt.size
    total = sum(widths) + extra * (len(text) - 1)
    cx = {"l": x, "m": x - total / 2, "r": x - total}[anchor]
    for c, w in zip(text, widths):
        draw.text((cx, y), c, font=fnt, fill=fill, anchor="lm")
        cx += w + extra


# ----------------------------------------------------------------- people

class Person:
    """A cut-out model image, premultiplied RGBA float32 in source pixels."""

    def __init__(self, name):
        rgba = np.asarray(Image.open(os.path.join(BUILD, "cutouts", name + ".png")).convert("RGBA"), np.float32) / 255.0
        a = rgba[..., 3:4]
        self.src = np.concatenate([rgba[..., :3] * a, a], axis=2)
        ys, xs = np.where(rgba[..., 3] > 0.5)
        self.top, self.bot = float(ys.min()), float(ys.max())
        self.h = self.bot - self.top
        # Horizontal anchor: alpha centroid of the shoulders-to-hips band, so
        # bags and stride legs don't pull the model off centre.
        band = rgba[int(self.top + 0.12 * self.h):int(self.top + 0.45 * self.h), :, 3]
        self.cx = float((band * np.arange(band.shape[1])).sum() / band.sum())

    def layer(self, height, top_y, cx_out, anchor_frac=0.0, anchor_y=None):
        """Render so the person is `height` px tall. By default the head top
        lands on top_y; with anchor_y, the point anchor_frac down the body
        lands on anchor_y instead (used for push-ins)."""
        s = height / self.h
        if anchor_y is None:
            ty = top_y - self.top * s
        else:
            ty = anchor_y - (self.top + anchor_frac * self.h) * s
        m = np.float32([[s, 0, cx_out - self.cx * s], [0, s, ty]])
        interp = cv2.INTER_AREA if s < 1 else cv2.INTER_LANCZOS4
        out = cv2.warpAffine(self.src, m, (W, H), flags=interp, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        out = np.clip(out, 0, 1)
        return np.minimum(out, out[..., 3:4])  # keep premultiplied colour <= alpha


def trail(layer, length, direction):
    """One-sided horizontal motion trail of a premultiplied layer."""
    k = np.linspace(1.0, 0.0, length + 1, dtype=np.float32)
    k /= k.sum()
    if direction > 0:   # trail to the left of the subject (moving right)
        return cv2.filter2D(layer, -1, k[None, :], anchor=(0, 0), borderType=cv2.BORDER_CONSTANT)
    return cv2.filter2D(layer, -1, k[::-1][None, :], anchor=(length, 0), borderType=cv2.BORDER_CONSTANT)


def over(bg, layer, opacity=1.0):
    """Composite a premultiplied RGBA layer over an RGB (0-1) background."""
    return layer[..., :3] * opacity + bg * (1 - layer[..., 3:4] * opacity)


def white_bg():
    return np.ones((H, W, 3), np.float32)


def with_ghost(layers, length, direction, opacity):
    """Pure white frame, faint motion trail behind, sharp people on top."""
    img = white_bg()
    for lay in layers:
        img = over(img, trail(lay, length, direction), opacity)
    for lay in layers:
        img = over(img, lay)
    return img


def motion_look(layers, bodies, direction, blur=55, strength=0.9):
    """The reference's "on the move" smear: a trail behind each model plus a
    horizontal motion blur on the outer parts of the body (arms, trouser
    edges, shoes) while the head and the centre of the torso stay sharp.
    bodies: (cx, top, height) of each model in frame pixels."""
    sharp = with_ghost(layers, 80, direction, 0.5)
    smear = white_bg()
    for lay in layers:
        smear = over(smear, trail(lay, 70, direction), 0.5)
    for lay in layers:
        smear = over(smear, hblur(lay, blur))
    xs = np.arange(W, dtype=np.float32)[None, :]
    ys = np.arange(H, dtype=np.float32)[:, None]
    m = np.zeros((H, W), np.float32)
    for cx, top, hgt in bodies:
        scale = hgt / FULL_H
        side = np.clip((np.abs(xs - cx) - 105 * scale) / (190 * scale), 0, 1)
        head = np.clip((ys - (top + 0.15 * hgt)) / (0.06 * hgt), 0, 1)
        feet = 0.55 * np.clip((ys - (top + 0.90 * hgt)) / (0.05 * hgt), 0, 1)
        near = np.abs(xs - cx) <= np.min([np.abs(xs - b[0]) for b in bodies], axis=0)
        m = np.where(near, np.maximum(side * head, feet * head), m)
    m = cv2.GaussianBlur(m, (0, 0), 12)[..., None] * strength
    return sharp * (1 - m) + smear * m


def hblur(img, k):
    k = int(k) | 1
    return cv2.blur(img, (k, 1), borderType=cv2.BORDER_REPLICATE) if k > 1 else img


def shift_x(img, dx, fill=1.0):
    if dx == 0:
        return img
    m = np.float32([[1, 0, dx], [0, 1, 0]])
    return cv2.warpAffine(img, m, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                          borderValue=(fill, fill, fill))


def ease_out(t):
    return 1 - (1 - t) ** 3


def to_u8(img):
    return np.round(np.clip(img, 0, 1) * 255).astype(np.uint8)


def overlay_text(img, draw_fn):
    """Draw text with PIL on top of a float RGB frame."""
    pil = Image.fromarray(to_u8(img))
    draw_fn(ImageDraw.Draw(pil))
    return np.asarray(pil, np.float32) / 255.0


# ----------------------------------------------------------------- shots

PEOPLE = {}


def person(name):
    if name not in PEOPLE:
        PEOPLE[name] = Person(name)
    return PEOPLE[name]


def shot_full(name, direction):
    """Replica shot: static full body, reference framing, motion trail."""
    lay = person(name).layer(FULL_H, FULL_TOP, W / 2)
    frame = to_u8(motion_look([lay], [(W / 2, FULL_TOP, FULL_H)], direction))
    return [frame] * SHOT


def shot_duo(left, right, direction):
    """Two models side by side, slightly smaller, feet on the same line."""
    hgt = FULL_H * 0.86
    base = FULL_TOP + FULL_H
    layers = [person(left).layer(hgt, base - hgt, W * 0.29), person(right).layer(hgt, base - hgt, W * 0.71)]
    bodies = [(W * 0.29, base - hgt, hgt), (W * 0.71, base - hgt, hgt)]
    frame = to_u8(motion_look(layers, bodies, direction, blur=47))
    return [frame] * SHOT


def product_header(draw, fg=INK):
    f = font("sans", 25)
    draw_tracked(draw, 64, 70, "BASIC ESSENTIALS", f, fg, 0.32, "l")
    draw_tracked(draw, W - 64, 70, "DÉBARDEUR COL MONTANT", f, fg, 0.32, "r")


def shot_closeup(name, direction):
    """Product close-up: head to knee, whip-in on the first frames, then a
    slow push-in anchored on the tank top."""
    p = person(name)
    frames = []
    for i in range(SHOT):
        t = i / (SHOT - 1)
        zoom = 2.0 * (1 + 0.045 * ease_out(t))
        hgt = FULL_H * zoom
        # Tank sits ~25% down the body; keep it at a fixed height on screen.
        lay = p.layer(hgt, 0, W / 2, anchor_frac=0.25, anchor_y=0.095 * H + 0.25 * FULL_H * 2.0)
        img = with_ghost([lay], 90, direction, 0.14)
        whip = {0: (78, 95), 1: (22, 31)}.get(i)
        if whip:
            img = hblur(shift_x(img, direction * whip[0]), whip[1])
        frames.append(to_u8(overlay_text(img, product_header)))
    return frames


def shot_colour_card(colour, index):
    """Full-bleed card in the tank colour with the colour name."""
    bg, fg = COLOURS[colour]
    card = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(card)
    draw_tracked(d, W / 2, H / 2 - 215, "LE DÉBARDEUR COL MONTANT", font("sans", 27), fg, 0.34)
    d.text((W / 2, H / 2), colour, font=font("serif_italic", 250), fill=fg, anchor="mm")
    draw_tracked(d, W / 2, H / 2 + 200, f"0{index} / 04", font("sans", 27), fg, 0.34)
    img = np.asarray(card, np.float32) / 255.0
    frames = []
    for i in range(SHOT):
        f = img
        if i == 0:
            f = hblur(img, 75)
        elif i == 1:
            f = hblur(img, 25)
        frames.append(to_u8(f))
    return frames


def shot_grid(model):
    """All four colours on one model, popping in one cell at a time."""
    cw, ch = W / 2, H / 2
    hgt = ch * 0.74
    cells = []
    for k, colour in enumerate(ORDER):
        cx = cw * (k % 2) + cw / 2
        cy = ch * (k // 2)
        cells.append((colour, person(IMAGE[(model, colour)]).layer(hgt, cy + ch * 0.085, cx), cx, cy))
    label = font("sans", 25)
    frames = []
    for i in range(SHOT):
        img = white_bg()
        for k, (colour, lay, cx, cy) in enumerate(cells):
            age = i - 2 * k
            if age < 0:
                continue
            cell = over(white_bg(), lay)
            if age == 0:
                cell = hblur(shift_x(cell, 36 * (1 if k % 2 else -1)), 41)
            m = np.zeros((H, W, 1), np.float32)
            m[int(cy):int(cy + ch), int(cx - cw / 2):int(cx + cw / 2)] = 1
            img = cell * m + img * (1 - m)

        def labels(d, i=i):
            for k, (colour, _, cx, cy) in enumerate(cells):
                if i - 2 * k >= 0:
                    draw_tracked(d, cx, cy + ch * 0.9, colour.upper(), label, INK, 0.34)
            draw_tracked(d, W / 2, ch, "4 COLORIS", font("sans", 25), INK, 0.34)
        frames.append(to_u8(overlay_text(img, labels)))
    return frames


def shot_card(path):
    img = np.asarray(Image.open(path).convert("RGB"))
    return [img] * SHOT


def letter(name):
    return os.path.join(HERE, "logo", "cards", name + ".png")


def timeline():
    """Yield (label, frames) for each of the 30 shots."""
    A, B = "A", "B"
    # Replica section: B A S I C.
    yield "A sable", shot_full(IMAGE[(A, "sable")], 1)
    yield "B sable", shot_full(IMAGE[(B, "sable")], -1)
    yield "letter B", shot_card(letter("01_B"))
    yield "A chocolat", shot_full(IMAGE[(A, "chocolat")], -1)
    yield "B chocolat", shot_full(IMAGE[(B, "chocolat")], 1)
    yield "letter A", shot_card(letter("02_A"))
    yield "A noir", shot_full(IMAGE[(A, "noir")], 1)
    yield "B noir", shot_full(IMAGE[(B, "noir")], -1)
    yield "letter S", shot_card(letter("03_S_blur"))
    yield "A ivoire", shot_full(IMAGE[(A, "ivoire")], -1)
    yield "B ivoire", shot_full(IMAGE[(B, "ivoire")], 1)
    yield "letter I", shot_card(letter("04_I_blur"))
    yield "duo noir/ivoire", shot_duo(IMAGE[(A, "noir")], IMAGE[(B, "ivoire")], 1)
    yield "duo sable/chocolat", shot_duo(IMAGE[(B, "sable")], IMAGE[(A, "chocolat")], -1)
    yield "letter C", shot_card(letter("05_C"))
    # Product section: one colour per group.
    for n, colour in enumerate(ORDER, 1):
        yield f"A {colour} close", shot_closeup(IMAGE[(A, colour)], 1 if n % 2 else -1)
        yield f"B {colour} close", shot_closeup(IMAGE[(B, colour)], -1 if n % 2 else 1)
        yield f"card {colour}", shot_colour_card(colour, n)
    # Finale.
    yield "grid A", shot_grid(A)
    yield "grid B", shot_grid(B)
    yield "logo", shot_card(os.path.join(HERE, "logo", "cards", "99_logo.png"))


# ----------------------------------------------------------------- audio

def build_audio(duration, path):
    """Reference track, extended with its own 2-bar loop, faded out."""
    ref = os.path.join(BUILD, "audio", "ref.wav")
    if not os.path.exists(ref):
        os.makedirs(os.path.dirname(ref), exist_ok=True)
        subprocess.run([FFMPEG, "-v", "error", "-y", "-i", os.path.join(HERE, "reference", "reference.mp4"),
                        "-vn", "-c:a", "pcm_s16le", ref], check=True)
    y, sr = sf.read(ref, dtype="float32")
    loop = int(round(4.36363 * sr))         # 2 bars at ~110 BPM (measured)
    # Splice in the quiet gap just before the 8.8s hit.
    lo, hi = int(8.60 * sr), int(8.76 * sr)
    env = np.convolve(np.abs(y[lo:hi]).mean(1), np.ones(256) / 256, "same")
    splice = lo + int(np.argmin(env))
    # Every join jumps from just before the splice back one loop length; the
    # 2-bar period makes y[splice - loop] continue y[splice] seamlessly. A
    # short crossfade from the real continuation hides the edit.
    xf = int(0.012 * sr)
    ramp = np.linspace(0, 1, xf, dtype=np.float32)[:, None]
    seg = y[splice - loop:splice].copy()
    seg[:xf] = y[splice:splice + xf] * (1 - ramp) + seg[:xf] * ramp
    n = int(round(duration * sr))
    reps = int(np.ceil((n - splice) / loop))
    out = np.concatenate([y[:splice]] + [seg] * reps)[:n].copy()
    # Fade out over the last 1.6s.
    fade = int(1.6 * sr)
    out[-fade:] *= (np.cos(np.linspace(0, np.pi, fade)) * 0.5 + 0.5)[:, None].astype(np.float32)
    sf.write(path, out, sr, subtype="PCM_16")
    return splice / sr


# ----------------------------------------------------------------- main

def end_video_frames():
    cap = cv2.VideoCapture(os.path.join(HERE, "endvideo", "end.mp4"))
    while True:
        ok, f = cap.read()
        if not ok:
            break
        yield cv2.cvtColor(cv2.resize(f, (W, H)) if f.shape[:2] != (H, W) else f, cv2.COLOR_BGR2RGB)


def preview():
    thumbs = []
    for label, frames in timeline():
        for pick in (0, SHOT - 1) if label.endswith("close") or label.startswith(("grid", "card")) else (SHOT - 1,):
            t = cv2.resize(frames[pick], (216, 384), interpolation=cv2.INTER_AREA).copy()
            cv2.putText(t, label + ("" if pick else " f0"), (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
            thumbs.append(t)
    cols = 10
    while len(thumbs) % cols:
        thumbs.append(np.full((384, 216, 3), 200, np.uint8))
    sheet = np.vstack([np.hstack(thumbs[r:r + cols]) for r in range(0, len(thumbs), cols)])
    path = os.path.join(BUILD, "preview_sheet.jpg")
    cv2.imwrite(path, cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])
    print(path)


def main():
    os.makedirs(os.path.join(BUILD, "out"), exist_ok=True)
    if "--preview" in sys.argv:
        preview()
        return
    audio = os.path.join(BUILD, "audio", "music_14s.wav")
    splice = build_audio(14.0, audio)
    print(f"audio spliced at {splice:.3f}s")
    out = os.path.join(HERE, "BASIC_on_the_move.mp4")
    cmd = [FFMPEG, "-y", "-v", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", audio,
           "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "slow", "-crf", "15", "-pix_fmt", "yuv420p",
           "-profile:v", "high", "-level", "4.1", "-colorspace", "bt709", "-color_primaries", "bt709",
           "-color_trc", "bt709", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = 0
    for label, frames in timeline():
        for f in frames:
            proc.stdin.write(np.ascontiguousarray(f).tobytes())
            n += 1
        print(f"{n / FPS:5.2f}s  {label}")
    for f in end_video_frames():
        proc.stdin.write(np.ascontiguousarray(f).tobytes())
        n += 1
    proc.stdin.close()
    if proc.wait():
        raise SystemExit("ffmpeg failed")
    print(f"{n} frames -> {out}")


if __name__ == "__main__":
    main()
