"""Split-cut lookbook video: two pages (hijab model left, model A right),
each page cut at the waist, like the Pull&Bear Drop #5 reference.

Each page rolls through the looks: the next look's bottom half comes in,
then its top half follows and completes it. Cuts land every 4-5 frames and
alternate pages, so the order criss-crosses: left-bottom, right-top,
left-top, right-bottom, ...

The spread is 16:9 (1920x1080). The main output is that spread rotated
90 degrees counter-clockwise into a 9:16 (1080x1920) file, like the
reference; an upright copy is written for checking.

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
FRAMES = 300  # 10 s
CUTS = 68  # 34 per page = 17 look changes each, so the video loops seamlessly
PAGE_W, PAGE_H = 960, 1080  # two pages side by side = 1920x1080 (16:9)
SEAM = 0.575  # waist position on the page (fraction of height)
TARGET_BG = np.array([154, 140, 128], float)  # #9A8C80
LOOKS = ["ivory", "chocolate", "sand", "black"]

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
    same flat greige; fit a smooth surface to backdrop-only regions."""
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
    h, w, _ = a.shape
    top = waist - SEAM * src_h
    left = cx - src_w / 2
    assert top + src_h <= h + 1, f"{model}/{look}: page runs past the bottom of the photo"

    # The page is wider than the photo: extend it with the backdrop colour,
    # feathering the photo's edges so the join can't be seen.
    feather = 90
    ramp_x = np.clip(np.minimum(np.arange(w), w - 1 - np.arange(w)) / feather, 0, 1)
    ramp_y = np.clip(np.arange(h) / feather, 0, 1)  # top only: the page ends inside the photo
    alpha = (ramp_y[:, None] * ramp_x[None, :])[..., None]
    a = a * alpha + TARGET_BG * (1 - alpha)

    pad = 800
    canvas = np.empty((h + 2 * pad, w + 2 * pad, 3))
    canvas[:] = TARGET_BG
    canvas[pad:pad + h, pad:pad + w] = a
    box = (left + pad, top + pad, left + pad + src_w, top + pad + src_h)
    img = Image.fromarray(canvas.round().astype(np.uint8)).resize((PAGE_W, PAGE_H), Image.LANCZOS, box=box)
    return np.asarray(img).astype(float)


def book_shading():
    """Open-book look: soft gutter shadow in the middle, gentle page curvature."""
    x = np.arange(2 * PAGE_W, dtype=float)
    d = np.abs(x - PAGE_W)  # distance to the gutter
    gutter = 1 - 0.28 * np.exp(-(d / 14) ** 2) - 0.10 * np.exp(-(d / 60) ** 2)
    u = np.where(x < PAGE_W, x / PAGE_W, (2 * PAGE_W - x) / PAGE_W)  # 0 outer edge -> 1 gutter
    curve = 1 + 0.035 * np.sin(np.pi * np.clip(u / 0.9, 0, 1)) - 0.02 * (1 - u) ** 6
    return (gutter * curve)[None, :, None]


def cut_frames():
    """Cut times on the reference's 4/5-frame rhythm, spread so the gap from
    the last cut back round to the first also fits the rhythm (clean loop)."""
    fives = FRAMES - 4 * CUTS  # number of 5-frame gaps, spread evenly
    gaps = [5 if (i + 1) * fives // CUTS > i * fives // CUTS else 4 for i in range(CUTS)]
    assert gaps[-1] == 5  # last cut -> wrap -> first cut
    frames, t = [], 4
    for g in gaps:
        frames.append(t)
        t += g
    assert frames[-1] < FRAMES and t == FRAMES + 4
    return frames


def look_sequences(seed):
    """One cyclic order of looks per page (17 changes each). A look never
    comes back within two changes, both pages never show the same colour at
    the same time, and every colour gets equal screen time (4-5 each)."""
    n = CUTS // 4
    rng = random.Random(seed)
    L, R = [], []

    def ok(k, wrap):
        # indices are cyclic; only check pairs that are already assigned
        def g(seq, i):
            i %= n
            return seq[i] if i < len(seq) else None

        checks = [
            (g(L, k), g(L, k - 1)), (g(L, k), g(L, k - 2)),
            (g(R, k), g(R, k - 1)), (g(R, k), g(R, k - 2)),
            (g(L, k), g(R, k)),  # both pages on a full look together
            (g(R, k), g(L, k - 1)),  # right leads with R[k] while left shows L[k-1]
        ]
        if wrap:
            checks += [(L[0], L[-1]), (L[0], L[-2]), (L[1], L[-1]),
                       (R[0], R[-1]), (R[0], R[-2]), (R[1], R[-1]), (R[0], L[-1])]
        return all(a is None or b is None or a != b for a, b in checks)

    def balanced(seq):
        return max(seq.count(v) for v in LOOKS) <= -(-n // len(LOOKS))

    def solve(k):
        if k == n:
            return ok(0, True)
        for v in rng.sample(LOOKS, len(LOOKS)):
            L.append(v)
            if balanced(L):
                for u in rng.sample(LOOKS, len(LOOKS)):
                    R.append(u)
                    if balanced(R) and ok(k, False) and solve(k + 1):
                        return True
                    R.pop()
            L.pop()
        return False

    assert solve(0), "no valid look order"
    return L, R


def schedule(seed):
    """Initial page state and cut list [(frame, page, half, look)].

    Left page starts on a full look and goes bottom-then-top for each new
    look. Right page starts halfway through a change (its next look's bottom
    already in) so its first cut is the top: this gives the reference's
    criss-cross order while both pages follow bottom-then-top."""
    L, R = look_sequences(seed)
    n = len(L)
    state = {"L": {"top": L[0], "bot": L[0]}, "R": {"top": R[0], "bot": R[1]}}
    cuts = []
    for i, f in enumerate(cut_frames()):
        j = i // 2  # this page's cut number
        if i % 2 == 0:  # left: bottom leads, top follows
            half = "bot" if j % 2 == 0 else "top"
            look = L[(j // 2 + 1) % n]
            cuts.append((f, "L", half, look))
        else:  # right: top completes the look already started, then next bottom
            half = "top" if j % 2 == 0 else "bot"
            look = R[(j // 2 + 1) % n] if half == "top" else R[(j // 2 + 2) % n]
            cuts.append((f, "R", half, look))
    return state, cuts


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    os.makedirs(OUT, exist_ok=True)
    pages = {
        (p, look): make_page(m, look)
        for p, m in (("L", "B"), ("R", "A"))
        for look in LOOKS
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
    start = {p: dict(s) for p, s in state.items()}
    rotated = os.path.join(OUT, "tanktop_splitcut_9x16.mp4")
    upright = os.path.join(OUT, "tanktop_splitcut_16x9_upright.mp4")
    enc = ["-c:v", "libx264", "-preset", "slow", "-crf", "15", "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{2 * PAGE_W}x{PAGE_H}", "-r", str(FPS), "-i", "-",
         "-filter_complex", "[0]split[u][r0];[r0]transpose=2[r]",
         "-map", "[r]", *enc, rotated, "-map", "[u]", *enc, upright],
        stdin=subprocess.PIPE,
    )
    ci = 0
    img = render(state)
    for f in range(FRAMES):
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
    assert state == start, "loop does not close"
    for f, p, half, look in cuts:
        print(f"{f:3d}  {p}-{half:3s} -> {look}")
    print(f"{rotated}\n{upright}\n{len(cuts)} cuts")


if __name__ == "__main__":
    main()
