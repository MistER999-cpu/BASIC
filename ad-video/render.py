#!/usr/bin/env python3
"""Tank-top tile-grid ad (v2: printed paper, beat-synced, ~14.6 s).

Each photo is treated as a matte print on its own sheet of paper, cut into a
3x4 grid of pieces laid on a paper board. A new look replaces the previous one
piece by piece in reading order (left to right, top to bottom).

Grid:   seam positions and strengths come from grid_geometry.json, measured
        from the reference video (jogs and faded seams included). Strong seams
        become small gaps between pieces showing the board, with a bright cut
        edge, stray fibres and a soft shadow; faded seams stay butted.
Timing: locked to the soundtrack's 93.2 BPM beat grid. Each transition flips
        12 pieces over 2 beats with the last piece landing on the beat, then
        the finished look holds for about a beat.
Audio:  the reference audio, with its two-bar phrase looped at a quiet,
        beat-aligned join, faded out after the final beat.

Usage: python3 render.py [output.mp4]
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import soundfile as sf
from imageio_ffmpeg import get_ffmpeg_exe

HERE = Path(__file__).resolve().parent
IMAGES_DIR = HERE.parent / "ad-images"

W, H, FPS = 1080, 1920, 24
TILES = 12

IMAGES = {
    "A-sand":  "Woman_posing_in_fashion_studio_2K_20260924230705.jpg",
    "A-brown": "Woman_posing_in_brown_tank_2K_20260924230703.jpg",
    "A-black": "Woman_posing_in_black_tank_2K_20260924230707.jpg",
    "A-cream": "Woman_walking_in_editorial_shoot_2K_20260924230750.jpg",
    "B-brown": "Woman_posing_in_fashion_outfit_2K_20260924232720.jpg",
    "B-black": "Woman_posing_in_fashion_outfit_2K_20260924232730.jpg",
    "B-sand":  "Woman_posing_in_studio_fashion_2K_20260924232723.jpg",
    "B-cream": "Woman_sitting_on_wooden_stool_2K_20260924232725.jpg",
}

# Models alternate; each half shows all four colours (the second half swaps
# each pair); every transition is between contrasting backdrops.
ORDER = ["A-sand", "B-brown", "A-cream", "B-black",
         "A-brown", "B-sand", "A-black", "B-cream"]

# Beat grid of the reference audio (fitted to its onset envelope).
BEAT = 0.6435
BEAT0 = 0.090
FIRST_BEAT = 1          # first transition starts on this beat
BEATS_PER_LOOK = 3      # 2 beats of flipping + 1 beat hold
END_TAIL = 0.40         # let the final beat ring out, then fade

# Audio loop: play to LOOP_B, jump back to LOOP_A, repeat. The two points are
# matching onsets exactly two bars apart with matching spectra; the join ends
# right as the onset starts, so the incoming hit masks it.
CROSSFADE = 0.012
LOOP_A = 0.640 - CROSSFADE / 2
LOOP_B = 5.789 - CROSSFADE / 2

# Paper and print look
BOARD_RGB = (231, 226, 220)      # the paper board seen through the cuts
CUT_RGB = (244, 240, 234)        # bright core of a freshly cut paper edge
GAP_FULL = 4.4                   # gap width (px) for a full-strength seam
PRINT_TEXTURE = 0.042            # paper tooth showing through the print
BOARD_TEXTURE = 0.055
SHADOW = 0.45                    # piece shadow on the board, light from top-left
GRAIN = 1.7                      # per-exposure grain (0-255 units)


def beat(k):
    return BEAT0 + k * BEAT


# ---------------------------------------------------------------- textures

def smooth_noise(rng, scale, h=H, w=W):
    """Noise with feature size ~scale px, zero mean, unit std."""
    if scale <= 1:
        n = rng.standard_normal((h, w)).astype(np.float32)
    else:
        small = rng.standard_normal((h // scale + 3, w // scale + 3)).astype(np.float32)
        n = cv2.resize(small, (w + 3 * scale, h + 3 * scale), interpolation=cv2.INTER_CUBIC)
        n = n[scale:scale + h, scale:scale + w]
    n -= n.mean()
    return n / (n.std() + 1e-6)


def fibres(rng, count, h=H, w=W):
    """Short, slightly curved paper fibres, drawn at 2x and downsampled."""
    canvas = np.full((h * 2, w * 2), 128, np.uint8)
    for _ in range(count):
        x, y = rng.uniform(0, w * 2), rng.uniform(0, h * 2)
        ang = rng.uniform(0, math.pi)
        seg = rng.uniform(6, 26)
        tone = int(128 + rng.choice([-1, 1]) * rng.uniform(18, 60))
        for _ in range(rng.integers(2, 4)):
            ang += rng.normal(0, 0.35)
            x2, y2 = x + seg * math.cos(ang), y + seg * math.sin(ang)
            cv2.line(canvas, (int(x * 16), int(y * 16)), (int(x2 * 16), int(y2 * 16)),
                     tone, 1, cv2.LINE_AA, shift=4)
            x, y = x2, y2
    f = cv2.resize(canvas, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) - 128
    return f / (f.std() + 1e-6)


def paper_texture(seed, fibre_weight=0.55, cloud=1.0):
    """cloud scales the large blotchy paper formation; keep it low on prints so
    smooth light fabric never looks stained."""
    rng = np.random.default_rng(seed)
    t = (0.45 * cloud * smooth_noise(rng, 90) + 0.35 * cloud * smooth_noise(rng, 24)
         + 0.35 * smooth_noise(rng, 5) + 0.30 * smooth_noise(rng, 2)
         + 0.35 * cv2.GaussianBlur(smooth_noise(rng, 1), (0, 0), 0.6)
         + fibre_weight * fibres(rng, 9000))
    return t / t.std()


# ---------------------------------------------------------------- geometry

def build_geometry(geom):
    rw, rh = geom["ref_size"]
    sx, sy = W / rw, H / rh
    xs = (np.arange(W) + 0.5) / sx - 0.5
    ys = (np.arange(H) + 0.5) / sy - 0.5
    vx = {(s["row"], s["col"]): s["x"] for s in geom["vertical"]}
    hy = {(s["row"], s["col"]): s["y"] for s in geom["horizontal"]}

    X, Y = np.meshgrid(xs, ys)
    C0 = np.broadcast_to(np.digitize(xs, [160, 317]), (H, W))
    row = np.zeros((H, W), np.int32)
    for r in (1, 2, 3):
        row += Y > np.choose(C0, [hy[(r, 0)], hy[(r, 1)], hy[(r, 2)]])
    col = np.zeros((H, W), np.int32)
    for c in (1, 2):
        col += X > np.choose(row, [vx[(0, c)], vx[(1, c)], vx[(2, c)], vx[(3, c)]])
    tile = row * 3 + col

    # gap width along every seam, from its measured strength
    gap = np.zeros((H, W), np.float32)
    for s in geom["vertical"]:
        prof = np.asarray(s["opacity"], np.float32)
        yo = np.arange(math.floor(s["y0"] * sy), min(math.ceil(s["y1"] * sy), H))
        op = np.interp((yo + 0.5) / sy - 0.5 - s["y0"], np.arange(len(prof)), prof)
        xc = int(round((s["x"] + 0.5) * sx - 0.5))
        gap[yo, xc] = np.maximum(gap[yo, xc], op * GAP_FULL)
    for s in geom["horizontal"]:
        prof = np.asarray(s["opacity"], np.float32)
        xo = np.arange(math.floor(s["x0"] * sx), min(math.ceil(s["x1"] * sx), W))
        op = np.interp((xo + 0.5) / sx - 0.5 - s["x0"], np.arange(len(prof)), prof)
        yc = int(round((s["y"] + 0.5) * sy - 0.5))
        gap[yc, xo] = np.maximum(gap[yc, xo], op * GAP_FULL)
    gap = cv2.dilate(gap, np.ones((11, 11), np.uint8))
    gap = cv2.GaussianBlur(gap, (0, 0), 2.0)
    gap[gap < 1.3] = 0                                   # faint seams: pieces butt together

    # hand-cut edges: a slow wobble plus slight fraying, only where there is a gap
    rng = np.random.default_rng(7)
    wobble = np.clip(0.35 * smooth_noise(rng, 70) + 0.15 * smooth_noise(rng, 4), -0.6, 0.6)
    wobble *= np.clip((gap - 1.3) / 1.2, 0, 1)

    alphas = []
    for t in range(TILES):
        m = (tile == t).astype(np.uint8)
        d = cv2.distanceTransform(m, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
        alphas.append(np.clip(d - gap / 2 + wobble, 0, 1).astype(np.float32))
    cum = np.cumsum(np.stack(alphas), axis=0)          # pieces 0..j in reading order
    union = cum[-1]
    return tile, cum, union, gap


def build_static_layers(union, gap):
    """Board with piece shadows, and the edge light/shade/fibre overlays."""
    board = np.array(BOARD_RGB[::-1], np.float32) * (1 + BOARD_TEXTURE * paper_texture(101)[..., None])

    shifted = cv2.warpAffine(union, np.float32([[1, 0, 1.1], [0, 1, 1.7]]), (W, H),
                             borderMode=cv2.BORDER_REPLICATE)
    shadow = cv2.GaussianBlur(shifted, (0, 0), 1.5)
    board *= (1 - SHADOW * shadow)[..., None]

    # light from the top-left: top/left cut edges catch it, bottom/right edges fall off
    ub = cv2.GaussianBlur(union, (0, 0), 0.8)
    gx = cv2.Sobel(ub, cv2.CV_32F, 1, 0, ksize=3) / 4
    gy = cv2.Sobel(ub, cv2.CV_32F, 0, 1, ksize=3) / 4
    facing = gx * 0.6 + gy * 0.8
    lit = np.clip(facing * 1.6, 0, 1) * union
    shade = np.clip(-facing * 1.6, 0, 1) * union
    rim = np.clip(union - cv2.erode(union, np.ones((3, 3), np.uint8)), 0, 1)
    edge_light = np.clip(0.55 * lit + 0.30 * rim, 0, 0.8)

    # stray fibres lifting off the cut edges, bridging the gaps
    rng = np.random.default_rng(11)
    canvas = np.zeros((H * 2, W * 2), np.uint8)
    ys, xs = np.nonzero(gap > GAP_FULL * 0.45)
    for i in rng.choice(len(ys), size=min(260, len(ys)), replace=False):
        x, y = xs[i] * 2, ys[i] * 2
        ang = rng.uniform(0, 2 * math.pi)
        ln = rng.uniform(4, 14)
        cv2.line(canvas, (int(x * 16), int(y * 16)),
                 (int((x + ln * math.cos(ang)) * 16), int((y + ln * math.sin(ang)) * 16)),
                 int(rng.uniform(120, 230)), 1, cv2.LINE_AA, shift=4)
    fibre = cv2.resize(canvas, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255

    # table light: soft falloff from the top-left, gentle vignette
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    nx, ny = xx / W - 0.5, yy / H - 0.5
    light = 1 + 0.025 * (-(nx * 0.6 + ny * 0.8)) - 0.07 * (nx ** 2 + ny ** 2) * 2
    return board, edge_light[..., None], (1 - 0.22 * shade)[..., None], fibre[..., None], light[..., None]


# ---------------------------------------------------------------- prints

def load_cover(path):
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        sys.exit(f"cannot read {path}")
    h, w = img.shape[:2]
    scale = max(W / w, H / h)
    img = cv2.resize(img, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)
    y, x = (img.shape[0] - H) // 2, (img.shape[1] - W) // 2
    return img[y:y + H, x:x + W].astype(np.float32)


def paper_relief(seed):
    """Surface tooth of matte paper lit from the top-left: fine relief and
    fibres rather than tonal blotches, so fabric keeps its true look."""
    rng = np.random.default_rng(seed)
    height = (0.55 * smooth_noise(rng, 3) + 0.45 * smooth_noise(rng, 2)
              + 0.35 * cv2.GaussianBlur(smooth_noise(rng, 1), (0, 0), 0.7)
              + 0.30 * fibres(rng, 7000))
    gx = cv2.Sobel(height, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(height, cv2.CV_32F, 0, 1, ksize=3)
    relief = -(0.6 * gx + 0.8 * gy)
    relief = relief / relief.std() + 0.25 * smooth_noise(rng, 60)
    return relief / relief.std()


def make_print(img, seed, tile):
    """A matte print: paper tooth across the image, softened blacks, and each
    cut piece catching the light slightly differently."""
    rng = np.random.default_rng(seed)
    tex = paper_relief(seed)
    lum = img.mean(2, keepdims=True) / 255
    out = img * (1 + PRINT_TEXTURE * (0.45 + 0.55 * lum) * tex[..., None])
    out = out * 0.965 + 6.5                      # matte paper: ink never reaches pure black

    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    piece_light = np.ones((H, W), np.float32)
    for t in range(TILES):
        m = tile == t
        ys, xs = np.nonzero(m)
        cy, cx = ys.mean(), xs.mean()
        ang = rng.uniform(0, 2 * math.pi)
        strength = rng.uniform(0.010, 0.024)
        offset = rng.uniform(-0.008, 0.008)
        proj = ((xx - cx) * math.cos(ang) + (yy - cy) * math.sin(ang)) / 300
        piece_light[m] = (1 + offset + strength * proj)[m]
    return out * piece_light[..., None]


# ---------------------------------------------------------------- timeline

def build_timeline(n_images):
    """[(frame, imgA, imgB, j)]: pieces 0..j show imgB, the rest imgA."""
    events = [(0, 0, 0, -1)]
    for k in range(n_images - 1):
        b = beat(FIRST_BEAT + BEATS_PER_LOOK * k)
        for i in range(TILES):
            t = b + (i + 1) * BEAT / 6               # 12 pieces over 2 beats, last one on the beat
            events.append((round(t * FPS), k, k + 1, i))
    end = beat(FIRST_BEAT + BEATS_PER_LOOK * (n_images - 1)) + END_TAIL
    return events, round(end * FPS)


def build_audio(out_wav, duration, fade_from):
    y, sr = sf.read(HERE / "reference_audio.wav", dtype="float32")
    a, b = round(LOOP_A * sr), round(LOOP_B * sr)
    n = round(CROSSFADE * sr)
    t = np.linspace(0, math.pi / 2, n, dtype=np.float32)[:, None]
    want = round(duration * sr)
    out = y[:b - n // 2]
    while len(out) < want:
        fade = y[b - n // 2:b - n // 2 + n] * np.cos(t) + y[a - n // 2:a - n // 2 + n] * np.sin(t)
        out = np.concatenate([out, fade, y[a - n // 2 + n:b - n // 2]])
    out = out[:want].copy()
    f0 = round(fade_from * sr)
    k = len(out) - f0
    out[f0:] *= (0.5 + 0.5 * np.cos(np.linspace(0, math.pi, k, dtype=np.float32)))[:, None]
    sf.write(out_wav, out, sr, subtype="PCM_16")


def main():
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "tank-top-grid-ad-v2.mp4"
    geom = json.loads((HERE / "grid_geometry.json").read_text())

    print("building grid and paper...")
    tile, cum, union, gap = build_geometry(geom)
    board, edge_light, edge_shade, fibre, light = build_static_layers(union, gap)
    board_part = board * (1 - union)[..., None]
    cut_bgr = np.array(CUT_RGB[::-1], np.float32)

    print("printing images...")
    prints = [make_print(load_cover(IMAGES_DIR / IMAGES[k]), 1000 + i, tile) for i, k in enumerate(ORDER)]

    events, n_frames = build_timeline(len(prints))
    wav = out_path.with_suffix(".wav")
    last_beat = beat(FIRST_BEAT + BEATS_PER_LOOK * (len(prints) - 1))
    build_audio(wav, n_frames / FPS, last_beat + 0.05)

    ff = get_ffmpeg_exe()
    enc = subprocess.Popen([
        ff, "-v", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", str(wav),
        "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
        "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-profile:v", "high",
        "-tune", "grain",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
        "-map", "0:v", "-map", "1:a", "-shortest", "-movflags", "+faststart",
        str(out_path)], stdin=subprocess.PIPE)

    grain_rng = np.random.default_rng(3)
    ev = 0
    state_start = 0
    frame_bytes, exposure = None, None
    for f in range(n_frames):
        while ev + 1 < len(events) and events[ev + 1][0] <= f:
            ev += 1
            state_start = events[ev][0]
        # a new exposure on every change, and every 3 frames while holding (stop-motion boil)
        key = (ev, (f - state_start) // 3)
        if key != exposure:
            exposure = key
            _, ia, ib, j = events[ev]
            if j < 0:
                pieces = prints[ia] * union[..., None]
            else:
                mb = cum[j][..., None]
                pieces = prints[ib] * mb + prints[ia] * (union[..., None] - mb)
            frame = board_part + pieces
            frame = frame * edge_shade + (cut_bgr - frame) * edge_light
            frame = frame + (cut_bgr - frame) * fibre * 0.55
            gain = 1 + grain_rng.normal(0, 0.0035)
            g = cv2.GaussianBlur(grain_rng.standard_normal((H, W)).astype(np.float32), (0, 0), 0.55)
            frame = frame * light * gain + (GRAIN * 1.6) * g[..., None]
            frame_bytes = np.clip(frame + 0.5, 0, 255).astype(np.uint8).tobytes()
        enc.stdin.write(frame_bytes)
    enc.stdin.close()
    if enc.wait() != 0:
        sys.exit("ffmpeg failed")
    wav.unlink()
    print(f"{out_path} {n_frames} frames, {n_frames / FPS:.3f}s")


if __name__ == "__main__":
    main()
