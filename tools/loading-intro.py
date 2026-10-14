#!/usr/bin/env python3
"""Glitch "loading" intro: two blurred flat-lay sets, spinners and a progress
bar; glitch bursts tear the sharp product through, then the load completes and
the outfits land sharp.

    python3 tools/loading-intro.py                      # -> out/loading-intro.mp4
    python3 tools/loading-intro.py --top a.jpg --bottom b.jpg --out out/x.mp4
    python3 tools/loading-intro.py --stills 20,45,100   # PNG frames for review

Flat-lays are expected on a white background; each is cropped to its content
and both are drawn at the same scale so the sets stay in proportion.
"""
import argparse
import os
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1350, 30
FRAMES = 4 * FPS

BLUE = (111, 155, 203)       # bar fill + label, from the reference clip
NAVY = (46, 58, 85)          # bar outline
FONT = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
LABEL, DONE = "LOADING", "COMPLETE"   # loader text; tools/reel.py swaps in French

# progress keyframes (frame, percent): stalls and jumps read as a real download
PROGRESS = [(0, 0), (8, 4), (17, 19), (24, 23), (38, 36), (46, 57), (60, 64),
            (66, 73), (78, 79), (86, 95), (93, 100)]
COMPLETE = 93                # bar hits 100 %
REVEAL = (97, 103)           # final tear-through; clean from REVEAL[1]

# glitch bursts: (start, end, strength 0-1, share of rows torn sharp)
BURSTS = [(18, 22, 0.55, 0.35), (41, 46, 0.75, 0.55), (63, 66, 0.6, 0.45),
          (80, 85, 0.9, 0.7)]
TICKS = [11, 30, 54, 72, 89]  # single-frame micro hits between bursts

SLOT_H = 560                 # height of each set's slot
TOP_Y, BOTTOM_Y = 40, 750    # slot tops; the loader sits between them


def content_box(img, pad=40):
    a = np.asarray(img.convert("L"))
    ys, xs = np.where(a < 235)
    return (max(xs.min() - pad, 0), max(ys.min() - pad, 0),
            min(xs.max() + pad, img.width), min(ys.max() + pad, img.height))


def garment_centres(img, box):
    """Centre of each garment (left/right halves of the content box)."""
    a = np.asarray(img.convert("L")) < 200
    x0, y0, x1, y1 = box
    mid = (x0 + x1) // 2
    out = []
    for lo, hi in ((x0, mid), (mid, x1)):
        ys, xs = np.where(a[y0:y1, lo:hi])
        out.append(((xs.min() + xs.max()) / 2 + lo, (ys.min() + ys.max()) / 2 + y0))
    return out


def layout(top_path, bottom_path):
    imgs = [Image.open(p).convert("RGB") for p in (top_path, bottom_path)]
    boxes = [content_box(im) for im in imgs]
    # one scale for both so the garments keep their real proportions
    scale = min(min(SLOT_H / (b[3] - b[1]), (W - 60) / (b[2] - b[0])) for b in boxes)
    canvas = Image.new("RGB", (W, H), "white")
    spinners = []
    for im, box, slot_y in zip(imgs, boxes, (TOP_Y, BOTTOM_Y)):
        crop = im.crop(box)
        cw, ch = round(crop.width * scale), round(crop.height * scale)
        ox, oy = (W - cw) // 2, slot_y + (SLOT_H - ch) // 2
        canvas.paste(crop.resize((cw, ch), Image.LANCZOS), (ox, oy))
        for cx, cy in garment_centres(im, box):
            spinners.append((ox + (cx - box[0]) * scale, oy + (cy - box[1]) * scale))
    return canvas, spinners


def spinner_sprites(n=12, size=190, ring=64, dot=12, ss=4):
    """One sprite per head position; head dots solid, tail fading out."""
    sprites = []
    for head in range(n):
        im = Image.new("RGBA", (size * ss, size * ss), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        c = size * ss / 2
        for i in range(n):
            age = (head - i) % n
            alpha = int(255 * max(0.28, 1 - age / 4.5))
            shade = 255 if age < 3 else 228
            ang = 2 * np.pi * i / n - np.pi / 2
            x, y = c + ring * ss * np.cos(ang), c + ring * ss * np.sin(ang)
            r = dot * ss
            d.ellipse((x - r, y - r, x + r, y + r), fill=(shade, shade, shade, alpha))
        sprites.append(im.resize((size, size), Image.LANCZOS))
    return sprites


def progress_at(f):
    for (f0, p0), (f1, p1) in zip(PROGRESS, PROGRESS[1:]):
        if f0 <= f <= f1:
            t = (f - f0) / (f1 - f0)
            return p0 + (p1 - p0) * (t * t * (3 - 2 * t))
    return 100.0


def draw_loader(base, pct, f, alpha=1.0, dx=0):
    """Label + progress bar centred between the two sets."""
    ss = 3
    bw, bh = 500, 54
    lw, lh = 560, 130
    layer = Image.new("RGBA", (lw * ss, lh * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    font = ImageFont.truetype(FONT, 44 * ss)

    if f >= COMPLETE:
        word, dots = DONE, ""
    else:
        word, dots = LABEL, " " + "." * ((f // 6) % 4)
    track = 4 * ss
    widths = [d.textlength(ch, font=font) for ch in word]
    word_w = sum(widths) + track * (len(word) - 1)
    x = (lw * ss - word_w) / 2         # centre the word only: dots never shift it
    for ch, cw in zip(word, widths):
        d.text((x, 0), ch, font=font, fill=BLUE)
        x += cw + track
    d.text((x, 0), dots, font=font, fill=BLUE)

    bx, by = (lw - bw) // 2 * ss, 70 * ss
    d.rounded_rectangle((bx, by, bx + bw * ss, by + bh * ss), radius=bh * ss // 2,
                        outline=NAVY, width=6 * ss, fill=(255, 255, 255, 255))
    inset = 12 * ss
    inner_w = bw * ss - 2 * inset
    inner_h = bh * ss - 2 * inset
    fill_w = max(inner_h, inner_w * pct / 100)
    if pct > 0.5:
        d.rounded_rectangle((bx + inset, by + inset, bx + inset + fill_w, by + inset + inner_h),
                            radius=inner_h // 2, fill=BLUE)

    layer = layer.resize((lw, lh), Image.LANCZOS)
    if alpha < 1:
        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
    base.alpha_composite(layer, ((W - lw) // 2 + dx, (TOP_Y + SLOT_H + BOTTOM_Y) // 2 - 62))


def tear_rows(blur, sharp, reveal, amt, rng):
    """Swap random horizontal bands of the blurred frame for shifted sharp ones."""
    out = blur.copy()
    y = 0
    while y < H:
        h = int(rng.integers(8, 80))
        if rng.random() < reveal:
            dx = int(rng.normal(0, 26 * amt))
            out[y:y + h] = np.roll(sharp[y:y + h], dx, axis=1)
        y += h
    return out


def glitch_fx(img, amt, rng):
    out = img.copy()
    # displaced blocks
    for _ in range(int(2 + 7 * amt)):
        bh, bw = int(rng.integers(6, 60)), int(rng.integers(80, 520))
        y0, x0 = int(rng.integers(0, H - bh)), int(rng.integers(0, W - bw))
        sx = int(np.clip(x0 + rng.normal(0, 60 * amt), 0, W - bw))
        out[y0:y0 + bh, x0:x0 + bw] = img[y0:y0 + bh, sx:sx + bw]
    # chromatic split
    d = int(3 + 16 * amt)
    out[..., 0] = np.roll(out[..., 0], d, axis=1)
    out[..., 2] = np.roll(np.roll(out[..., 2], -d, axis=1), int(rng.integers(-3, 4)), axis=0)
    out = out.astype(np.float32)
    # tinted scan bars
    for _ in range(int(rng.integers(1, 3 + 3 * amt))):
        y0, h = int(rng.integers(0, H)), int(rng.integers(1, 5))
        tint = np.array([(0, 255, 255), (255, 0, 200), (20, 20, 20)][rng.integers(0, 3)], np.float32)
        out[y0:y0 + h] = out[y0:y0 + h] * 0.45 + tint * 0.55
    out[::3] *= 1 - 0.07 * amt          # scanlines
    out += rng.normal(0, 4 * amt, (H, W, 1)).astype(np.float32)
    return np.clip(out, 0, 255).astype(np.uint8)


def burst_at(f):
    for s, e, amt, rev in BURSTS:
        if s <= f <= e:
            t = (f - s) / max(e - s, 1)
            env = np.sin(np.pi * (0.15 + 0.7 * t))      # peaks mid-burst
            return amt * (0.6 + 0.4 * env), rev * (0.5 + 0.5 * env)
    return None


def settle(img, f):
    """Ease the sharp reveal from a slight push-in back to 1:1."""
    t = min(max((f - REVEAL[0]) / (FRAMES - 1 - REVEAL[0]), 0), 1)
    s = 1 + 0.045 * (1 - t) ** 3
    if s <= 1.0005:
        return img
    big = img.resize((round(W * s), round(H * s)), Image.LANCZOS)
    x, y = (big.width - W) // 2, (big.height - H) // 2
    return big.crop((x, y, x + W, y + H))


def render_frame(f, sharp, centres, sprites, rng):
    pct = progress_at(f)
    if f >= REVEAL[1]:
        return np.asarray(settle(sharp, f))

    radius = 30 - 12 * pct / 100            # blur thins as the load progresses
    blur = sharp.filter(ImageFilter.GaussianBlur(radius))
    blur = Image.blend(blur, Image.new("RGB", (W, H), "white"), 0.12).convert("RGBA")
    head = (f // 2) % len(sprites)
    for cx, cy in centres:
        sp = sprites[head]
        blur.alpha_composite(sp, (int(cx - sp.width / 2), int(cy - sp.height / 2)))

    sharp_now = sharp if f < REVEAL[0] else settle(sharp, f)
    blur_np, sharp_np = np.asarray(blur.convert("RGB")), np.asarray(sharp_now)

    amt, reveal = None, 0.0
    burst = burst_at(f)
    if burst:
        amt, reveal = burst
    elif REVEAL[0] <= f < REVEAL[1]:
        t = (f - REVEAL[0]) / (REVEAL[1] - REVEAL[0])
        amt, reveal = 1.0 - 0.35 * t, 0.55 + 0.45 * t
    elif f in TICKS:
        amt = 0.3

    frame = tear_rows(blur_np, sharp_np, reveal, amt, rng) if reveal else blur_np
    frame = Image.fromarray(frame).convert("RGBA")

    ui_alpha = min(1.0, f / 4 + 0.25)
    if f >= REVEAL[0]:
        ui_alpha = max(0.0, 1 - (f - REVEAL[0] + 1) / (REVEAL[1] - REVEAL[0]))
    dx = int(rng.normal(0, 10 * amt)) if amt else 0
    if ui_alpha > 0:
        draw_loader(frame, pct, f, ui_alpha, dx)

    out = np.asarray(frame.convert("RGB"))
    return glitch_fx(out, amt, rng) if amt else out


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", default=os.path.join(root, "assets/flatlays/set1-cami-shorts-black.jpg"))
    ap.add_argument("--bottom", default=os.path.join(root, "assets/flatlays/set2-tee-capri-black.jpg"))
    ap.add_argument("--out", default=os.path.join(root, "out/loading-intro.mp4"))
    ap.add_argument("--stills", help="comma-separated frame numbers to export as PNG instead")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    sharp, centres = layout(args.top, args.bottom)
    sprites = spinner_sprites()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    if args.stills:
        for f in map(int, args.stills.split(",")):
            rng = np.random.default_rng(args.seed * 1000 + f)
            path = os.path.splitext(args.out)[0] + f"-f{f:03d}.png"
            Image.fromarray(render_frame(f, sharp, centres, sprites, rng)).save(path)
            print(path)
        return

    ff = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "slow", "-crf", "15", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", args.out],
        stdin=subprocess.PIPE)
    for f in range(FRAMES):
        rng = np.random.default_rng(args.seed * 1000 + f)
        ff.stdin.write(render_frame(f, sharp, centres, sprites, rng).tobytes())
    ff.stdin.close()
    if ff.wait():
        raise SystemExit("ffmpeg failed")
    print(args.out)


if __name__ == "__main__":
    main()
