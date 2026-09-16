#!/usr/bin/env python3
"""
BASIC — parallax reel builder.
Replicates the measured geometry of the reference: two flat cut-out layers
scrolling horizontally at different constant speeds over a scrolling plate.
No 3D, no easing, no zoom. Loops exactly at 480 frames.

Drop 4 background plates + 8 model shots into assets/ and run:  python3 build.py
"""
import cv2, numpy as np, os, subprocess, sys

# ---------------------------------------------------------------- measured spec
W, H, FPS, NFRAMES = 1080, 1920, 30, 480          # 16.0 s
NEAR_V, FAR_V, BG_V = 12.0, 9.0, 9.0              # px/frame, all negative-x
NEAR_STRIP = int(NEAR_V * NFRAMES)                # 5760 = 4 slots x 1440
FAR_STRIP  = int(FAR_V  * NFRAMES)                # 4320 = 4 slots x 1080
BG_STRIP   = int(BG_V   * NFRAMES)                # 4320 = 4 plates x 1080
NEAR_SPACING, FAR_SPACING = NEAR_STRIP // 4, FAR_STRIP // 4

FAR_HEAD_Y, FAR_FEET_Y = 298, 1613                # 15.5% / 84% of frame height
FAR_FIG_H = FAR_FEET_Y - FAR_HEAD_Y               # 1315 px
NEAR_MIN_W = int(0.70 * W)                        # 70% of frame width
NEAR_TOP_Y = -58                                  # crown clips off the top edge
BG_BLUR = 11                                      # extra softening on the plate

ROOT = os.path.dirname(os.path.abspath(__file__))
# --test renders against the synthetic placeholders in assets/_test/
SUB = "assets/_test" if "--test" in sys.argv else "assets"
BG  = lambda n: os.path.join(ROOT, SUB, "bg", n)
MOD = lambda n: os.path.join(ROOT, SUB, "models", n)
OUT = "out/v1_placeholder.mp4" if "--test" in sys.argv else "out/v1.mp4"

# order established from edge/band-height matching
BG_ORDER = ["bg4.png", "bg2.png", "bg3.png", "bg1.png"]

# beat order: alternates near/far every 2.0 s, alternates model where possible
NEAR_SLOTS = ["A_near_black.png", "B_near_ivory.png", "B_near_black.png", "A_near_brown.png"]
FAR_SLOTS  = ["B_far_brown.png",  "A_far_beige.png",  "A_far_ivory.png",  "B_far_beige.png"]

# ---------------------------------------------------------------- green key
def key_green(bgr, lo=12.0, hi=55.0):
    """Chroma key + despill. Returns BGRA uint8."""
    f = bgr.astype(np.float32)
    b, g, r = f[..., 0], f[..., 1], f[..., 2]
    d = g - np.maximum(r, b)                       # green dominance
    a = 1.0 - np.clip((d - lo) / (hi - lo), 0, 1)  # green -> 0, subject -> 1
    a = cv2.GaussianBlur(a, (0, 0), 1.0)
    # despill: clamp green channel to the warmer of the other two
    cap = np.maximum(r, b)
    g2 = np.where(g > cap, cap + (g - cap) * 0.15, g)
    out = np.dstack([b, g2, r, a * 255.0])
    return np.clip(out, 0, 255).astype(np.uint8)

def largest_subject(alpha):
    """Keep only the biggest connected blob — drops stray keyed specks."""
    m = (alpha > 24).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    if n <= 1:
        return m.astype(bool)
    k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    return lab == k

def load_cutout(path):
    """Load a model shot; key it if it still has a green backdrop."""
    raw = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if raw is None:
        raise FileNotFoundError(path)
    if raw.shape[2] == 4:
        rgba = raw
    else:
        rgba = key_green(raw)
    keep = largest_subject(rgba[..., 3])
    rgba[..., 3] = np.where(keep, rgba[..., 3], 0)
    ys, xs = np.where(rgba[..., 3] > 24)
    if len(ys) == 0:
        raise ValueError(f"nothing survived the key in {path}")
    return rgba, (xs.min(), ys.min(), xs.max(), ys.max())

def place(strip, rgba, bbox, cx, mode):
    x0, y0, x1, y1 = bbox
    fig = rgba[y0:y1 + 1, x0:x1 + 1]
    fh, fw = fig.shape[:2]
    if mode == "far":
        s = FAR_FIG_H / fh
        top = FAR_HEAD_Y
    else:
        # scale so the figure covers the frame vertically, crown clipped off the
        # top edge and body running off the bottom — the reference's near framing.
        s = (H - NEAR_TOP_Y) / fh
        top = NEAR_TOP_Y
        if fw * s > 0.92 * W:
            print(f"    ! near figure would be {100*fw*s/W:.0f}% of frame width — "
                  f"source is too wide/short for this crop")
    nw, nh = max(1, int(round(fw * s))), max(1, int(round(fh * s)))
    fig = cv2.resize(fig, (nw, nh), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
    left = int(round(cx - nw / 2))
    # wrapped alpha-over onto the strip
    for col in range(nw):
        sx = (left + col) % strip.shape[1]
        ys0, ys1 = max(0, top), min(H, top + nh)
        if ys1 <= ys0:
            continue
        src = fig[ys0 - top:ys1 - top, col]
        a = (src[:, 3:4].astype(np.float32) / 255.0)
        dst = strip[ys0:ys1, sx]
        dst[:, :3] = (src[:, :3].astype(np.float32) * a + dst[:, :3].astype(np.float32) * (1 - a)).astype(np.uint8)
        dst[:, 3] = np.maximum(dst[:, 3], src[:, 3])

def build_bg():
    plates = []
    for n in BG_ORDER:
        p = cv2.imread(BG(n))
        if p is None:
            raise FileNotFoundError(BG(n))
        plates.append(cv2.resize(p, (W, H), interpolation=cv2.INTER_AREA))
    strip = np.hstack(plates)
    # feather each seam, including the wrap seam
    ov = 90
    for k in range(4):
        x = k * W
        for i in range(-ov, ov):
            t = (i + ov) / (2 * ov)
            a = (x + i) % BG_STRIP
            bcol = strip[:, (x - 1) % BG_STRIP].astype(np.float32)
            strip[:, a] = (strip[:, a].astype(np.float32) * t + bcol * (1 - t)).astype(np.uint8)
    return cv2.GaussianBlur(strip, (0, 0), BG_BLUR)

def build_layer(slots, strip_w, spacing, mode, phase):
    strip = np.zeros((H, strip_w, 4), np.uint8)
    for k, name in enumerate(slots):
        rgba, bbox = load_cutout(MOD(name))
        place(strip, rgba, bbox, (phase + k * spacing) % strip_w, mode)
        print(f"  placed {name:22s} at strip x={int((phase+k*spacing)%strip_w)}")
    return strip

def window(img, off, w):
    off = int(off) % img.shape[1]
    if off + w <= img.shape[1]:
        return img[:, off:off + w]
    return np.hstack([img[:, off:], img[:, :off + w - img.shape[1]]])

def main():
    print("background strip…")
    bg = build_bg()
    print("far layer…")
    far = build_layer(FAR_SLOTS, FAR_STRIP, FAR_SPACING, "far", 1323)
    print("near layer…")
    near = build_layer(NEAR_SLOTS, NEAR_STRIP, NEAR_SPACING, "near", 864)

    raw = os.path.join(ROOT, "out/_raw.mp4")
    vw = cv2.VideoWriter(raw, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    print(f"rendering {NFRAMES} frames…")
    for i in range(NFRAMES):
        frame = window(bg, BG_V * i, W).copy()
        for layer, v in ((far, FAR_V), (near, NEAR_V)):
            win = window(layer, v * i, W)
            a = win[..., 3:4].astype(np.float32) / 255.0
            frame = (win[..., :3].astype(np.float32) * a +
                     frame.astype(np.float32) * (1 - a)).astype(np.uint8)
        vw.write(frame)
    vw.release()

    final = os.path.join(ROOT, OUT)
    try:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw,
                        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", final],
                       check=True)
        os.remove(raw)
    except Exception:
        # no ffmpeg: keep the mp4v render, just under the right name
        os.replace(raw, final)
        print("  (ffmpeg not found — kept the mp4v render; re-encode for delivery)")
    print(f"\ndone -> {final}")

if __name__ == "__main__":
    main()
