#!/usr/bin/env python3
"""Tank-top tile-grid ad.

Rebuilds the reference edit: a 3x4 grid of tiles over a 9:16 frame, where each
new photo replaces the previous one tile by tile in reading order (left to
right, top to bottom), one tile every 0.1 s with hard cuts and no holds.

The grid seams are not a perfect grid: grid_geometry.json holds every seam
segment's position and opacity measured from the reference video (478x850),
including the jogs where tiles meet and the seams that fade out.

The soundtrack is the reference audio with one bar repeated at a quiet,
beat-aligned join so it covers the longer 8-image sequence.

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
FRAMES_PER_STEP = 2.4  # 10 tile steps per second at 24 fps (3,2,3,2,2 cadence)
TILES = 12             # 3 columns x 4 rows

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

# Models alternate throughout; each half shows all four colours (the second
# half swaps each pair); every transition is between contrasting backdrops.
ORDER = ["A-sand", "B-brown", "A-cream", "B-black",
         "A-brown", "B-sand", "A-black", "B-cream"]

# Audio: play the reference up to SPLICE_B, then continue from SPLICE_A, so the
# bar between them plays twice. B - A is one bar at 93.2 BPM; A sits in a gap
# between hits. Measured with a beat grid fitted to the onset envelope.
SPLICE_A = 1.4831746
SPLICE_B = 4.0648299
CROSSFADE = 0.030


def load_cover(path):
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        sys.exit(f"cannot read {path}")
    h, w = img.shape[:2]
    scale = max(W / w, H / h)
    img = cv2.resize(img, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)
    y = (img.shape[0] - H) // 2
    x = (img.shape[1] - W) // 2
    return img[y:y + H, x:x + W].astype(np.float32)


def build_grid(geom):
    rw, rh = geom["ref_size"]
    sx, sy = W / rw, H / rh
    # reference-space coordinates of every output pixel centre
    xs = (np.arange(W) + 0.5) / sx - 0.5
    ys = (np.arange(H) + 0.5) / sy - 0.5

    vx = {(s["row"], s["col"]): s["x"] for s in geom["vertical"]}
    hy = {(s["row"], s["col"]): s["y"] for s in geom["horizontal"]}

    # tile index map: rows split by each column's horizontal seams, columns by each row's vertical seams
    col_nom = np.digitize(xs, [160, 317])
    X, Y = np.meshgrid(xs, ys)
    C0 = np.broadcast_to(col_nom, (H, W))
    row = np.zeros((H, W), np.int32)
    for r in (1, 2, 3):
        thr = np.choose(C0, [hy[(r, 0)], hy[(r, 1)], hy[(r, 2)]])
        row += (Y > thr)
    col = np.zeros((H, W), np.int32)
    for c in (1, 2):
        thr = np.choose(row, [vx[(0, c)], vx[(1, c)], vx[(2, c)], vx[(3, c)]])
        col += (X > thr)
    tile = row * 3 + col

    # seam opacity map: anti-aliased lines, each segment with its measured opacity profile
    half = geom["cross_section_fwhm_ref_px"] * sx / 2 * 0.85  # matches the reference seam's integrated brightness
    alpha = np.zeros((H, W), np.float32)
    for s in geom["vertical"]:
        prof = np.asarray(s["opacity"], np.float32)
        yo0, yo1 = math.floor(s["y0"] * sy), math.ceil(s["y1"] * sy)
        yo = np.arange(yo0, min(yo1, H))
        op = np.interp((yo + 0.5) / sy - 0.5 - s["y0"], np.arange(len(prof)), prof)
        xc = (s["x"] + 0.5) * sx - 0.5
        xo = np.arange(max(int(xc - 6), 0), min(int(xc + 7), W))
        a = np.clip(half + 0.5 - np.abs(xo - xc), 0, 1)
        blk = op[:, None] * a[None, :]
        alpha[yo[0]:yo[-1] + 1, xo[0]:xo[-1] + 1] = np.maximum(alpha[yo[0]:yo[-1] + 1, xo[0]:xo[-1] + 1], blk)
    for s in geom["horizontal"]:
        prof = np.asarray(s["opacity"], np.float32)
        xo0, xo1 = math.floor(s["x0"] * sx), math.ceil(s["x1"] * sx)
        xo = np.arange(xo0, min(xo1, W))
        op = np.interp((xo + 0.5) / sx - 0.5 - s["x0"], np.arange(len(prof)), prof)
        yc = (s["y"] + 0.5) * sy - 0.5
        yo = np.arange(max(int(yc - 6), 0), min(int(yc + 7), H))
        a = np.clip(half + 0.5 - np.abs(yo - yc), 0, 1)
        blk = a[:, None] * op[None, :]
        alpha[yo[0]:yo[-1] + 1, xo[0]:xo[-1] + 1] = np.maximum(alpha[yo[0]:yo[-1] + 1, xo[0]:xo[-1] + 1], blk)
    alpha = cv2.GaussianBlur(alpha, (0, 0), 0.6)

    seam_bgr = np.array(geom["seam_rgb"][::-1], np.float32)
    return tile, alpha[..., None], seam_bgr


def build_audio(out_wav, duration):
    y, sr = sf.read(HERE / "reference_audio.wav", dtype="float32")
    a, b = round(SPLICE_A * sr), round(SPLICE_B * sr)
    n = round(CROSSFADE * sr)
    t = np.linspace(0, math.pi / 2, n, dtype=np.float32)[:, None]
    head = y[:b - n // 2]
    fade = y[b - n // 2:b - n // 2 + n] * np.cos(t) + y[a - n // 2:a - n // 2 + n] * np.sin(t)
    tail = y[a - n // 2 + n:]
    out = np.concatenate([head, fade, tail])
    want = round(duration * sr)
    out = out[:want]
    if len(out) < want:
        out = np.pad(out, ((0, want - len(out)), (0, 0)))
    k = round(0.015 * sr)
    out[-k:] *= np.linspace(1, 0, k, dtype=np.float32)[:, None]
    sf.write(out_wav, out, sr, subtype="PCM_16")
    return len(y) + (b - a)


def main():
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "tank-top-grid-ad.mp4"
    geom = json.loads((HERE / "grid_geometry.json").read_text())
    tile, alpha, seam = build_grid(geom)
    seam_layer = alpha * seam
    keep = 1.0 - alpha

    imgs = [load_cover(IMAGES_DIR / IMAGES[k]) for k in ORDER]
    steps = 1 + (len(imgs) - 1) * TILES

    # audio decides the length: the last image holds until the music ends
    y, sr = sf.read(HERE / "reference_audio.wav", dtype="float32")
    audio_len = (len(y) + round(SPLICE_B * sr) - round(SPLICE_A * sr)) / sr
    n_frames = round(audio_len * FPS)
    last_step_frame = math.ceil((steps - 1) * FRAMES_PER_STEP)
    assert n_frames > last_step_frame, "audio shorter than the tile sequence"

    wav = out_path.with_suffix(".wav")
    build_audio(wav, n_frames / FPS)

    ff = get_ffmpeg_exe()
    enc = subprocess.Popen([
        ff, "-v", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", str(wav),
        "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
        "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
        "-map", "0:v", "-map", "1:a", "-shortest", "-movflags", "+faststart",
        str(out_path)], stdin=subprocess.PIPE)

    cache = {}
    for f in range(n_frames):
        s = 0
        while s + 1 < steps and math.ceil((s + 1) * FRAMES_PER_STEP) <= f:
            s += 1
        if s not in cache:
            cache.clear()
            if s == 0:
                base = imgs[0]
            else:
                t, j = divmod(s - 1, TILES)
                base = np.where((tile <= j)[..., None], imgs[t + 1], imgs[t])
            frame = base * keep + seam_layer
            cache[s] = np.clip(frame + 0.5, 0, 255).astype(np.uint8).tobytes()
        enc.stdin.write(cache[s])
    enc.stdin.close()
    if enc.wait() != 0:
        sys.exit("ffmpeg failed")
    wav.unlink()
    print(f"{out_path} {n_frames} frames, {n_frames / FPS:.3f}s, {steps} steps")


if __name__ == "__main__":
    main()
