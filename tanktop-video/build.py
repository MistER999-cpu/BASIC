"""Split-cut lookbook video: two pages (hijab model left, model A right),
each page cut at the waist; top/bottom halves swap on a 4-5 frame rhythm,
alternating left/right page, like the Pull&Bear Drop #5 reference.

Usage: python3 build.py [seed]
"""
import os
import random
import subprocess
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "images")
OUT = os.path.join(HERE, "out")

FPS = 30
DURATION = 10.0
PAGE_W, PAGE_H = 675, 1080  # 5:8 page, like the reference (450x720)
SEAM = 0.575  # waist position on the page (fraction of height)
TARGET_BG = np.array([154, 140, 128], float)  # #9A8C80

# file, waistband y (source px), body center x (source px)
MODELS = {
    "A": {
        "height": 2620,  # source px covered by one page
        "looks": {
            "ivory": ("Woman_wearing_fashion_lookbook_o…_2K_20260926113040.jpg", 1556, 764),
            "chocolate": ("Keep_absolutely_everything_identical__the_2K_20260926113047.jpg", 1428, 773),
            "sand": ("Woman_posing_for_fashion_lookbook_2K_20260926113050.jpg", 1436, 769),
            "black": ("Woman_wearing_black_tank_top_2K_20260926113212.jpg", 1438, 772),
        },
    },
    "B": {
        "height": 2690,
        "looks": {
            "ivory": ("Woman_wearing_hijab_and_tank_2K_20260926114415.jpg", 1562, 769),
            "chocolate": ("Woman_wearing_hijab_and_tank_2K_20260926114417.jpg", 1500, 770),
            "sand": ("Woman_wearing_hijab_and_cardigan_2K_20260926114420.jpg", 1588, 770),
            "black": ("Woman_wearing_fashion_lookbook_o…_2K_20260926114423.jpg", 1578, 760),
        },
    },
}


def flatten_background(a):
    """Divide out the backdrop's vignette/exposure so every image sits on the
    same flat greige; fit a quadratic surface to backdrop-only regions."""
    h, w, _ = a.shape
    ys, xs = np.mgrid[0:h:8, 0:w:8]
    sel = (xs < 190) | (xs > w - 190) | (ys < 60)
    ys, xs = ys[sel], xs[sel]
    samples = a[ys, xs]
    # drop outliers (subject pixels creeping into the bands)
    med = np.median(samples, 0)
    ok = np.sqrt(((samples - med) ** 2).sum(1)) < 40
    ys, xs, samples = ys[ok], xs[ok], samples[ok]

    def basis(y, x):
        y = y / h - 0.5
        x = x / w - 0.5
        return np.stack([np.ones_like(x), x, y, x * x, y * y, x * y, y ** 3, x * x * y], -1)

    coef, *_ = np.linalg.lstsq(basis(ys, xs), samples, rcond=None)
    gy, gx = np.mgrid[0:h, 0:w].astype(float)
    field = basis(gy, gx) @ coef
    return np.clip(a * (TARGET_BG / field), 0, 255)


def make_page(model, look):
    fname, waist, cx = MODELS[model]["looks"][look]
    src_h = MODELS[model]["height"]
    src_w = src_h * PAGE_W / PAGE_H
    a = flatten_background(np.asarray(Image.open(os.path.join(IMG, fname)).convert("RGB")).astype(float))
    top = waist - SEAM * src_h
    left = cx - src_w / 2
    # pad with backdrop colour where the page reaches past the source image
    pad = 400
    canvas = np.empty((a.shape[0] + 2 * pad, a.shape[1] + 2 * pad, 3))
    canvas[:] = TARGET_BG
    canvas[pad:pad + a.shape[0], pad:pad + a.shape[1]] = a
    box = (left + pad, top + pad, left + pad + src_w, top + pad + src_h)
    assert top + src_h <= a.shape[0] + 1, f"{model}/{look}: page runs past the bottom of the photo"
    img = Image.fromarray(canvas.astype(np.uint8)).resize((PAGE_W, PAGE_H), Image.LANCZOS, box=box)
    return np.asarray(img).astype(float)


def book_shading():
    """Open-book look: soft gutter shadow in the middle, gentle page curvature."""
    x = np.arange(2 * PAGE_W, dtype=float)
    d = np.abs(x - PAGE_W)  # distance to the gutter
    gutter = 1 - 0.28 * np.exp(-(d / 14) ** 2) - 0.10 * np.exp(-(d / 60) ** 2)
    u = np.where(x < PAGE_W, x / PAGE_W, (2 * PAGE_W - x) / PAGE_W)  # 0 outer edge -> 1 gutter
    curve = 1 + 0.035 * np.sin(np.pi * np.clip(u / 0.9, 0, 1)) - 0.02 * (1 - u) ** 6
    return (gutter * curve)[None, :, None]


def schedule(seed):
    """Cut list: (frame, page, half, look). Cuts every 4/5 frames alternating
    pages; halves chosen at random; looks shuffled so all four colours rotate."""
    rng = random.Random(seed)
    looks = ["ivory", "chocolate", "sand", "black"]
    state = {p: {"top": l, "bot": b} for p, l, b in (("L", "sand", "black"), ("R", "ivory", "chocolate"))}
    initial = {p: dict(s) for p, s in state.items()}
    cuts, frame, page, gap = [], 5, "L", [4, 5]
    last_half = {"L": None, "R": None}
    while frame < DURATION * FPS:
        half = rng.choice(["top", "bot"])
        if half == last_half[page] and rng.random() < 0.5:  # avoid long runs on one half
            half = "bot" if half == "top" else "top"
        other = "bot" if half == "top" else "top"
        choices = [l for l in looks if l != state[page][half] and l != state[page][other]]
        look = rng.choice(choices)
        state[page][half] = look
        last_half[page] = half
        cuts.append((frame, page, half, look))
        frame += gap[len(cuts) % 2]
        page = "R" if page == "L" else "L"
    return initial, cuts


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    os.makedirs(OUT, exist_ok=True)
    pages = {
        (p, look): make_page(m, look)
        for p, m in (("L", "B"), ("R", "A"))
        for look in MODELS[m]["looks"]
    }
    shade = book_shading()
    seam_row = round(SEAM * PAGE_H)
    grain = np.random.default_rng(1).normal(0, 1.6, (PAGE_H, 2 * PAGE_W, 1))

    def render(state):
        frame = np.empty((PAGE_H, 2 * PAGE_W, 3))
        for i, p in enumerate(("L", "R")):
            x0 = i * PAGE_W
            frame[:seam_row, x0:x0 + PAGE_W] = pages[(p, state[p]["top"])][:seam_row]
            frame[seam_row:, x0:x0 + PAGE_W] = pages[(p, state[p]["bot"])][seam_row:]
        return np.clip(frame * shade + grain, 0, 255).astype(np.uint8)

    state, cuts = schedule(seed)
    path = os.path.join(OUT, "tanktop_splitcut_10s.mp4")
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{2 * PAGE_W}x{PAGE_H}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "slow", "-crf", "15", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", path],
        stdin=subprocess.PIPE,
    )
    ci = 0
    img = render(state)
    for f in range(int(DURATION * FPS)):
        changed = False
        while ci < len(cuts) and cuts[ci][0] == f:
            _, p, half, look = cuts[ci]
            state[p][half] = look
            ci += 1
            changed = True
        if changed:
            img = render(state)
        ff.stdin.write(img.tobytes())
    ff.stdin.close()
    ff.wait()
    print(f"{path}: {len(cuts)} cuts")


if __name__ == "__main__":
    main()
