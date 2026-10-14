#!/usr/bin/env python3
"""2x2 grid reveal: four shots pop in one by one as a small grid on white,
then each tile snaps out to fill its quarter of the 9:16 frame, and the full
grid holds. Hard cuts only; timing and geometry are measured from the
reference clip (720x1280, scaled 1.5x here).

    python3 tools/grid-reveal.py assets/shoots/model1-outfit1   # -> out/model1-outfit1.mp4
    python3 tools/grid-reveal.py a.jpg b.jpg c.jpg d.jpg --out out/x.mp4 --seconds 3.5

Order is reading order: top-left, top-right, bottom-left, bottom-right. A
folder is read in filename order. Each tile is cover-fitted into its current
rectangle, so the snap out reads as the photo uncropping, not zooming.
"""
import argparse
import glob
import os
import subprocess

from PIL import Image

W, H, FPS = 1080, 1920, 30
CX, CY = W // 2, H // 2
TILE_W, TILE_H = 480, 375    # small-grid tile; the grid meets at the frame centre

POP = [4, 8, 12, 17]          # frame each tile appears in the small grid
SNAP = [32, 37, 42, 46]       # frame each tile fills its quarter

# vertical focus per tile (0 top .. 1 bottom) for the small landscape crop,
# so faces stay in shot; the full quarter is 9:16 and barely crops
FOCUS = [0.15, 0.20, 0.10, 0.0]


def cover(img, w, h, focus_y):
    s = max(w / img.width, h / img.height)
    rw, rh = round(img.width * s), round(img.height * s)
    big = img.resize((rw, rh), Image.LANCZOS)
    x = (rw - w) // 2
    y = round((rh - h) * focus_y)
    return big.crop((x, y, x + w, y + h))


def rects(i, full):
    """Tile i's rectangle, anchored on the frame centre like the reference."""
    right, bottom = i % 2, i // 2
    w, h = (CX, CY) if full else (TILE_W, TILE_H)
    x = CX if right else CX - w
    y = CY if bottom else CY - h
    return x, y, w, h


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+", help="a folder of 4 images, or 4 image paths")
    ap.add_argument("--out")
    ap.add_argument("--seconds", type=float, default=3.5)
    args = ap.parse_args()

    paths = args.inputs
    if len(paths) == 1 and os.path.isdir(paths[0]):
        paths = sorted(p for p in glob.glob(os.path.join(paths[0], "*"))
                       if p.lower().endswith((".jpg", ".jpeg", ".png", ".webp")))
    if len(paths) != 4:
        raise SystemExit(f"need exactly 4 images, got {len(paths)}")
    name = os.path.basename(os.path.normpath(args.inputs[0])) if len(args.inputs) == 1 else "grid-reveal"
    out = args.out or os.path.join(root, "out", f"{name}.mp4")
    os.makedirs(os.path.dirname(out), exist_ok=True)

    imgs = [Image.open(p).convert("RGB") for p in paths]
    small = [cover(im, TILE_W, TILE_H, f) for im, f in zip(imgs, FOCUS)]
    full = [cover(im, CX, CY, 0.5) for im in imgs]

    frames = round(args.seconds * FPS)
    ff = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", out],
        stdin=subprocess.PIPE)
    last, cached = None, None
    for f in range(frames):
        state = tuple(2 if f >= SNAP[i] else 1 if f >= POP[i] else 0 for i in range(4))
        if state != last:
            canvas = Image.new("RGB", (W, H), "white")
            for i, s in enumerate(state):
                if s:
                    x, y, _, _ = rects(i, s == 2)
                    canvas.paste((full if s == 2 else small)[i], (x, y))
            cached, last = canvas.tobytes(), state
        ff.stdin.write(cached)
    ff.stdin.close()
    if ff.wait():
        raise SystemExit("ffmpeg failed")
    print(out)


if __name__ == "__main__":
    main()
