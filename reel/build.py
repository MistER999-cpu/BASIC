#!/usr/bin/env python3
"""
BASIC — parallax reel builder.

Replicates the measured geometry of the reference clip: two flat cut-out layers
scrolling horizontally at different constant speeds over a scrolling plate.
No 3D camera, no easing, no zoom, no cuts. Loops exactly at NFRAMES.

    python3 build.py            # renders out/v1.mp4 from assets/
    python3 build.py --test     # renders out/v1_placeholder.mp4 from assets/_test/
"""
import cv2, numpy as np, os, subprocess, sys

# ---------------------------------------------------------------- spec
W, H, FPS, NFRAMES = 1080, 1920, 30, 450          # 15.0 s

# Layer speeds are chosen so each strip's travel over the loop equals its own
# width exactly: 4 background plates and 4 slots per layer, parallax held at the
# reference's measured near:far ratio of 4:3.
BG_STRIP   = 4 * W                                 # 4320
FAR_STRIP  = 4 * W                                 # 4320  (4 slots @ 1080)
NEAR_STRIP = 4 * 1440                              # 5760  (4 slots @ 1440)
BG_V   = BG_STRIP   / NFRAMES                      # 9.60 px/frame
FAR_V  = FAR_STRIP  / NFRAMES                      # 9.60
NEAR_V = NEAR_STRIP / NFRAMES                      # 12.80  -> 4:3 parallax
NEAR_SPACING, FAR_SPACING = NEAR_STRIP // 4, FAR_STRIP // 4

FAR_HEAD_Y, FAR_FEET_Y = 298, 1613                 # 15.5% / 84% of frame height
FAR_FIG_H = FAR_FEET_Y - FAR_HEAD_Y                # 1315 px
NEAR_TOP_Y = -58                                   # crown clipped off the top edge
# Near figures are anchored to a fixed crown-to-thigh height so every one sits at
# the same anatomical scale regardless of how wide its pose is. NEAR_FIG_H is set
# so the widest pose still lands inside NEAR_MAX_W — the near model's hands must
# stay within the frame when she is centred on her beat.
NEAR_FIG_H = 1820
NEAR_MAX_W = 0.95 * W                              # safety cap
NEAR_TAIL  = 0.38                                  # fraction of the figure stretched
BG_BLUR    = 10                                    # extra softening on the plate
# The assembled plate's empty field lands ~6 levels under the reference's #E9E9E8;
# a small gain brings the field onto it and nudges the band into the reference range.
BG_GAIN    = 1.026
BG_OVERLAP = 180                                   # cross-dissolve width per seam

ROOT = os.path.dirname(os.path.abspath(__file__))
TEST = "--test" in sys.argv
SUB  = "assets/_test" if TEST else "assets"
EXT  = ".png" if TEST else ".jpeg"
BG   = lambda n: os.path.join(ROOT, SUB, "bg", n + EXT)
MOD  = lambda n: os.path.join(ROOT, SUB, "models", n + EXT)
OUT  = "out/v1_placeholder.mp4" if TEST else "out/v1.mp4"

# plate order = the colour wave: low band -> rising -> held high -> descending
BG_ORDER = ["bg1", "bg2", "bg3", "bg4"]

# beat order: a hero centres every 1.875 s, alternating near/far.
# Colour never repeats between neighbouring beats; the two unavoidable
# same-model adjacencies both land on a far shot whose head is turned down.
NEAR_SLOTS = ["A_near_black", "B_near_ivory", "B_near_black", "A_near_brown"]
FAR_SLOTS  = ["B_far_brown",  "A_far_beige",  "A_far_ivory",  "B_far_beige"]
NEAR_PHASE, FAR_PHASE = 864, 1323

# ---------------------------------------------------------------- green key
def key_green(bgr, lo=6.0, hi=45.0, despill=0.0):
    """Chroma key + full despill.

    lo/hi and a full green clamp were chosen by measuring residual green in the
    soft alpha band across the set — they take A_far_ivory's edge from +6.8 to
    +3.6 and remove the dark outline the looser settings left on light garments.
    Nothing in the wardrobe is green, so clamping green entirely is safe.
    """
    f = bgr.astype(np.float32)
    b, g, r = f[..., 0], f[..., 1], f[..., 2]
    d = g - np.maximum(r, b)                        # green dominance
    a = 1.0 - np.clip((d - lo) / (hi - lo), 0, 1)   # green -> 0, subject -> 1
    a = cv2.GaussianBlur(a, (0, 0), 1.0)
    cap = np.maximum(r, b)
    g2 = np.where(g > cap, cap + (g - cap) * despill, g)
    return np.clip(np.dstack([b, g2, r, a * 255.0]), 0, 255).astype(np.uint8)

def fix_edge_colour(rgba):
    """Rebuild colour in the soft alpha band from the nearest opaque pixel.

    Despill darkens semi-transparent edge pixels (they are part green, and the
    green gets clamped), which leaves a thin dark outline once the figure is
    composited. Replacing the band's colour with its nearest solid neighbour's
    keeps the anti-aliasing but removes the fringe.
    """
    solid = rgba[..., 3] > 200
    if not solid.any() or solid.all():
        return rgba
    inv = (~solid).astype(np.uint8)
    _, lab = cv2.distanceTransformWithLabels(inv, cv2.DIST_L2, 3,
                                             labelType=cv2.DIST_LABEL_PIXEL)
    zy, zx = np.nonzero(inv == 0)                 # solid pixels, raster order
    nearest = rgba[..., :3][zy[lab - 1], zx[lab - 1]]
    rgba[..., :3] = np.where(solid[..., None], rgba[..., :3], nearest)
    return rgba

def largest_subject(alpha):
    m = (alpha > 24).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    if n <= 1:
        return m.astype(bool)
    k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    return lab == k

def load_cutout(name):
    path = MOD(name)
    raw = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if raw is None:
        raise FileNotFoundError(path)
    rgba = raw if raw.shape[2] == 4 else key_green(raw)
    keep = largest_subject(rgba[..., 3])
    rgba[..., 3] = np.where(keep, rgba[..., 3], 0)
    rgba = fix_edge_colour(rgba)
    ys, xs = np.where(rgba[..., 3] > 24)
    if len(ys) == 0:
        raise ValueError(f"nothing survived the key in {path}")
    return rgba, (xs.min(), ys.min(), xs.max(), ys.max())

# ---------------------------------------------------------------- layers
def build_bg():
    """Four plates cross-dissolved into one wrapping strip."""
    ov = BG_OVERLAP
    pw = W + ov
    acc = np.zeros((H, BG_STRIP, 3), np.float32)
    wgt = np.zeros((1, BG_STRIP), np.float32)
    ramp = np.ones(pw, np.float32)
    ramp[:ov]  = np.linspace(0, 1, ov)
    ramp[-ov:] = np.linspace(1, 0, ov)
    for k, n in enumerate(BG_ORDER):
        p = cv2.imread(BG(n))
        if p is None:
            raise FileNotFoundError(BG(n))
        p = cv2.resize(p, (pw, H), interpolation=cv2.INTER_AREA).astype(np.float32)
        xs = (k * W - ov // 2 + np.arange(pw)) % BG_STRIP
        np.add.at(acc, (slice(None), xs), p * ramp[None, :, None])
        np.add.at(wgt, (0, xs), ramp)
    strip = (acc / np.maximum(wgt[..., None], 1e-6)).astype(np.uint8)
    strip = np.clip(strip.astype(np.float32) * BG_GAIN, 0, 255).astype(np.uint8)
    return cv2.GaussianBlur(strip, (0, 0), BG_BLUR)

def place(strip, rgba, bbox, cx, mode):
    x0, y0, x1, y1 = bbox
    fig = rgba[y0:y1 + 1, x0:x1 + 1]
    fh, fw = fig.shape[:2]
    if mode == "far":
        s, top = FAR_FIG_H / fh, FAR_HEAD_Y
    else:
        s, top = min(NEAR_FIG_H / fh, NEAR_MAX_W / fw), NEAR_TOP_Y
    nw, nh = max(1, round(fw * s)), max(1, round(fh * s))
    fig = cv2.resize(fig, (nw, nh), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
    if mode == "near" and top + nh < H:
        # stretch the trouser band down to the frame edge. Every near shot ends in
        # trousers, whose vertical fall takes the stretch without showing a seam.
        need = H - (top + nh)
        bh = int(nh * NEAR_TAIL)
        fig = np.vstack([fig[:-bh], cv2.resize(fig[-bh:], (nw, bh + need),
                                               interpolation=cv2.INTER_LINEAR)])
        nh += need
    left = round(cx - nw / 2)
    ys0, ys1 = max(0, top), min(H, top + nh)
    src = fig[ys0 - top:ys1 - top]
    xs = (left + np.arange(nw)) % strip.shape[1]
    a = src[..., 3:4].astype(np.float32) / 255.0
    dst = strip[ys0:ys1][:, xs]
    strip[ys0:ys1, xs, :3] = (src[..., :3] * a + dst[..., :3] * (1 - a)).astype(np.uint8)
    strip[ys0:ys1, xs, 3]  = np.maximum(dst[..., 3], src[..., 3])
    return nw, nh

def build_layer(slots, strip_w, spacing, mode, phase):
    strip = np.zeros((H, strip_w, 4), np.uint8)
    for k, name in enumerate(slots):
        rgba, bbox = load_cutout(name)
        cx = (phase + k * spacing) % strip_w
        nw, nh = place(strip, rgba, bbox, cx, mode)
        print(f"  {name:14s} -> strip x={cx:5d}  {nw}x{nh}px  ({100*nw/W:.0f}% frame width)")
    return strip

def window(img, off, w):
    off = int(round(off)) % img.shape[1]
    if off + w <= img.shape[1]:
        return img[:, off:off + w]
    return np.hstack([img[:, off:], img[:, :off + w - img.shape[1]]])

# ---------------------------------------------------------------- render
def main():
    print(f"spec: {W}x{H} {FPS}fps {NFRAMES}f = {NFRAMES/FPS:.2f}s")
    print(f"      near {NEAR_V:.2f}px/f strip {NEAR_STRIP} | far {FAR_V:.2f} strip {FAR_STRIP} "
          f"| bg {BG_V:.2f} strip {BG_STRIP} | parallax {NEAR_V/FAR_V:.4f}")
    print("background…"); bg = build_bg()
    print("far layer…");  far  = build_layer(FAR_SLOTS,  FAR_STRIP,  FAR_SPACING,  "far",  FAR_PHASE)
    print("near layer…"); near = build_layer(NEAR_SLOTS, NEAR_STRIP, NEAR_SPACING, "near", NEAR_PHASE)

    raw = os.path.join(ROOT, "out/_raw.mp4")
    os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
    vw = cv2.VideoWriter(raw, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    print(f"rendering {NFRAMES} frames…")
    for i in range(NFRAMES):
        frame = window(bg, BG_V * i, W).astype(np.float32)
        for layer, v in ((far, FAR_V), (near, NEAR_V)):
            win = window(layer, v * i, W)
            a = win[..., 3:4].astype(np.float32) / 255.0
            frame = win[..., :3].astype(np.float32) * a + frame * (1 - a)
        vw.write(frame.astype(np.uint8))
    vw.release()

    final = os.path.join(ROOT, OUT)
    try:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-c:v", "libx264",
                        "-crf", "17", "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart", final], check=True)
        os.remove(raw)
    except Exception:
        os.replace(raw, final)
        print("  (ffmpeg not found — kept the mp4v render)")
    print(f"\ndone -> {final}")

if __name__ == "__main__":
    main()
