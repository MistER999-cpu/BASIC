"""Collage overlay: a fast-cutting 4:5 card of product photos over the base film.

    python3 collage/build.py cards      # prepare the 16 cards -> out/collage/cards/
    python3 collage/build.py plan       # print the cut list
    python3 collage/build.py render     # -> out/collage/collage.mp4

The card sits dead centre at 70% of the frame width with hard edges, no border
and no shadow, and swaps on every beat of the music. That matches the
reference edit, whose cards changed roughly every 0.46 s; this track runs at
132 BPM, so a beat is 0.455 s.

Compositing is done in ffmpeg rather than by decoding frames in Python, so the
base film never leaves its bt709 YUV path and its colours stay untouched.
"""

import json
import math
import os
import subprocess
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "..", "out", "collage")

BASE = os.path.join(ROOT, "base", "base vid.mp4")
MUSIC = os.path.join(
    ROOT, "audio",
    "YTDown.com_YouTube_Plastic-Generation-Instrumental-Version_Media_PxX8ui3HUQA_009_128k.mp3")

FPS = 24
W, H = 1080, 1920
# Reference card: 506x633 on 720x1280, i.e. 70.3% x 49.5%, centred. Kept at 4:5
# and on even pixels so the 4:2:0 chroma lines up with the card edge.
CARD_W, CARD_H = 760, 950
CARD_X, CARD_Y = (W - CARD_W) // 2, 484

# The track drops out of a one-bar silence at 36.626 s. Frame 0 lands on that
# hit, so the film opens at full energy.
MUSIC_START = 36.62
DROP = 36.626
# 132 BPM exactly: the song's three drops (36.626, 89.353, 126.626 s) sit 116
# and 82 beats apart at 60/132 s, to within 1 ms. librosa's beat tracker reads
# ~129 because the kick is syncopated; at that tempo the cuts would drift three
# frames off the beat by the end of the film.
BEAT = 60 / 132
FADE_OUT = 0.8

# Background cuts in base.mp4, in frames. A card swap within SNAP frames of one
# is moved onto it; two cuts a few frames apart read as a stutter. Two frames
# (83 ms) is as far as a swap can move before it reads as off the beat.
BASE_CUTS = [81, 132, 199, 295, 391]
SNAP = 2

# The reference keeps the model's head clear of the card: the eye goes to her
# face above it, then down to the product inside it. Three clips put her face
# behind the card, so they are scaled up about the bottom edge of the frame,
# which lifts the face while keeping the feet and collar in shot. Scale per
# clip, in cut order; 1.0 leaves a clip untouched.
#   1 white wide     chin at 26% of the height, card top at 25% -> 1.07 clears
#                    head and shoulders, feet stay below the card
#   2 white close-up eyes at 38%  -> 1.28 puts them just above the card, with
#                    room for the slow push-in that drifts them down
#   5 beige profile  lowered eye at 33% -> 1.22
REFRAME = [1.07, 1.28, 1.0, 1.0, 1.22, 1.0]

# Loop order: colour and pose both change on every swap.
ORDER = [
    "01-white-full", "02-beige-tilt", "03-brown-closeup", "04-black-crop",
    "05-white-tilt", "06-beige-closeup", "07-brown-crop", "08-black-full",
    "09-white-crop", "10-beige-full", "11-brown-tilt", "12-black-closeup",
    "13-white-closeup", "14-beige-crop", "15-brown-full", "16-black-tilt",
]
# The reference holds one card for two beats, across a background cut. Here
# the white full-body card comes round again on beat 16 and holds into the
# cut to the brown clip.
HOLD_BEAT = 16

S = os.path.join(ROOT, "cards")
ST = os.path.join(S, "studio")
# Each card: source, optional half of a side-by-side studio photo, rotation in
# degrees (the Dutch tilt), crop centre as fractions of the source, and zoom as
# a fraction of the largest 4:5 crop that fits at that rotation.
CARDS = {
    "01-white-full":    dict(src=f"{ST}/white.jpg", half="right", cx=0.50, cy=0.5),
    "02-beige-tilt":    dict(src=f"{S}/Woman_posing_in_fashion_outfit_2K_20260924110329.jpeg", rot=14, cx=0.50, cy=0.42, zoom=1.0),
    "03-brown-closeup": dict(src=f"{ST}/brown.jpg", half="left", cx=0.50, cy=0.5),
    "04-black-crop":    dict(src=f"{S}/Woman_sitting_in_studio_2K_20260924110332.jpeg", cx=0.5, cy=0.5),
    "05-white-tilt":    dict(src=f"{S}/Woman_posing_in_studio_outfit_2K_20260924110344.jpeg", rot=13, cx=0.50, cy=0.42, zoom=1.0),
    "06-beige-closeup": dict(src=f"{ST}/beige.jpg", half="left", cx=0.50, cy=0.5),
    "07-brown-crop":    dict(src=f"{S}/Woman_adjusting_mock-neck_collar_2K_20260924110335.jpeg", cx=0.5, cy=0.5),
    "08-black-full":    dict(src=f"{ST}/black.jpg", half="right", cx=0.50, cy=0.5),
    "09-white-crop":    dict(src=f"{S}/Woman_wearing_fashion_outfit_2K_20260924110345.jpeg", cx=0.5, cy=0.5),
    "10-beige-full":    dict(src=f"{ST}/beige.jpg", half="right", cx=0.50, cy=0.5),
    "11-brown-tilt":    dict(src=f"{S}/Woman_posing_in_studio_outfit_2K_20260924110426.jpeg", rot=13, cx=0.50, cy=0.38, zoom=1.0),
    "12-black-closeup": dict(src=f"{ST}/black.jpg", half="left", cx=0.50, cy=0.5),
    "13-white-closeup": dict(src=f"{ST}/white.jpg", half="left", cx=0.50, cy=0.5),
    "14-beige-crop":    dict(src=f"{S}/Woman_posing_in_fashion_outfit_2K_20260924110339.jpeg", cx=0.5, cy=0.5),
    "15-brown-full":    dict(src=f"{ST}/brown.jpg", half="right", cx=0.50, cy=0.5),
    "16-black-tilt":    dict(src=f"{S}/Woman_posing_for_fashion_photo_2K_20260924110348.jpeg", rot=14, cx=0.52, cy=0.39, zoom=1.0),
}

# The studio photos are two shots side by side with a white rule at x~995-1005.
HALVES = {"left": (0, 990), "right": (1010, 2000)}


def ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return "ffmpeg"


def crop_card(spec):
    im = cv2.imread(spec["src"])
    assert im is not None, spec["src"]
    if "half" in spec:
        x0, x1 = HALVES[spec["half"]]
        im = im[:, x0:x1]
    h, w = im.shape[:2]
    th = math.radians(spec.get("rot", 0))
    c, s = math.cos(th), math.sin(th)
    cx, cy = spec["cx"] * w, spec["cy"] * h

    def corners(cw):
        ch = cw * 5 / 4
        pts = []
        for u, v in ((-cw / 2, -ch / 2), (cw / 2, -ch / 2), (cw / 2, ch / 2), (-cw / 2, ch / 2)):
            pts.append((cx + c * u - s * v, cy + s * u + c * v))
        return pts

    def fits(cw):
        return all(0 <= x <= w - 1 and 0 <= y <= h - 1 for x, y in corners(cw))

    lo, hi = 1.0, float(w)
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if fits(mid) else (lo, mid)
    cw = lo * spec.get("zoom", 1.0)
    ch = cw * 5 / 4
    # Map card pixels back to the source through the rotation, then downscale
    # with area averaging so fine knit and denim texture does not alias.
    sw, sh = int(round(cw)), int(round(ch))
    M = np.array([[c, -s, cx - c * sw / 2 + s * sh / 2],
                  [s, c, cy - s * sw / 2 - c * sh / 2]])
    crop = cv2.warpAffine(im, M, (sw, sh), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP,
                          borderMode=cv2.BORDER_REPLICATE)
    card = cv2.resize(crop, (CARD_W, CARD_H), interpolation=cv2.INTER_AREA)
    return card, sw


def make_cards():
    os.makedirs(os.path.join(OUT, "cards"), exist_ok=True)
    thumbs = []
    for name in ORDER:
        card, sw = crop_card(CARDS[name])
        cv2.imwrite(os.path.join(OUT, "cards", name + ".png"), card)
        note = "" if sw >= CARD_W else f"  (upscaled from {sw}px)"
        print(f"{name:18s} source crop {sw}px wide{note}")
        t = cv2.resize(card, (190, 238), interpolation=cv2.INTER_AREA)
        cv2.putText(t, name[:2], (6, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        thumbs.append(t)
    sheet = np.vstack([np.hstack(thumbs[i:i + 8]) for i in (0, 8)])
    cv2.imwrite(os.path.join(OUT, "cards_sheet.jpg"), sheet)


def base_frames():
    out = subprocess.run([ffmpeg(), "-i", BASE], capture_output=True, text=True).stderr
    dur = out.split("Duration: ")[1].split(",")[0]
    hh, mm, ss = dur.split(":")
    return int(round((int(hh) * 3600 + int(mm) * 60 + float(ss)) * FPS))


def beat_grid(n_frames):
    """Beat times relative to the first frame."""
    first = DROP - MUSIC_START
    return [first + i * BEAT for i in range(int(n_frames / FPS / BEAT) + 2)], BEAT


def plan():
    n = base_frames()
    grid, period = beat_grid(n)
    cuts = [int(round(t * FPS)) for t in grid]
    cuts = [f for f in cuts if f < n]
    # Two-beat hold: drop the swap that would have ended it.
    del cuts[HOLD_BEAT + 1]
    snapped = []
    for f in cuts:
        near = [b for b in BASE_CUTS if abs(b - f) <= SNAP]
        snapped.append(near[0] if near else f)
    starts = sorted(set(snapped))
    segs = []
    for i, a in enumerate(starts):
        b = starts[i + 1] if i + 1 < len(starts) else n
        segs.append((a, b, ORDER[i % len(ORDER)]))
    return segs, n, period


def show_plan():
    segs, n, period = plan()
    print(f"{n} frames at {FPS} fps, beat {period:.4f}s ({60 / period:.1f} BPM), {len(segs)} cards")
    for a, b, name in segs:
        mark = " <- background cut" if a in BASE_CUTS else ""
        print(f"  {a / FPS:6.3f}s  {b - a:3d} frames  {name}{mark}")


def loudnorm(dur, fades):
    """Two-pass loudnorm in linear mode: one gain for the whole clip, so the
    drop keeps its punch instead of being ridden by a compressor. The source is
    mastered hot (-7.8 LUFS, peaks over 0 dBTP); -11 LUFS sits with other
    social ads and leaves headroom under -1 dBTP."""
    target = "I=-11:TP=-1:LRA=11"
    err = subprocess.run([ffmpeg(), "-hide_banner", "-ss", str(MUSIC_START), "-t", str(dur),
                          "-i", MUSIC, "-af", f"{fades},loudnorm={target}:print_format=json",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    m = json.loads(err[err.rindex("{"):err.rindex("}") + 1])
    return (f"loudnorm={target}:linear=true:measured_I={m['input_i']}:measured_TP={m['input_tp']}"
            f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}")


def render():
    segs, n, _ = plan()
    for name in ORDER:
        assert os.path.exists(os.path.join(OUT, "cards", name + ".png")), "run: build.py cards"
    cmd = [ffmpeg(), "-y", "-v", "error", "-i", BASE]
    for name in ORDER:
        cmd += ["-loop", "1", "-framerate", str(FPS), "-t", str(n / FPS + 1),
                "-i", os.path.join(OUT, "cards", name + ".png")]
    cmd += ["-ss", str(MUSIC_START), "-t", str(n / FPS), "-i", MUSIC]
    graph = []
    bounds = [0] + BASE_CUTS + [n]
    parts = []
    graph.append(f"[0:v]split={len(REFRAME)}" + "".join(f"[s{k}]" for k in range(len(REFRAME))))
    for k, z in enumerate(REFRAME):
        a, b = bounds[k], bounds[k + 1]
        chain = f"[s{k}]trim=start_frame={a}:end_frame={b},setpts=PTS-STARTPTS"
        if z != 1.0:
            zw, zh = 2 * round(W * z / 2), 2 * round(H * z / 2)
            chain += (f",scale={zw}:{zh}:flags=lanczos"
                      f",crop={W}:{H}:{(zw - W) // 2}:{zh - H}")
        # setsar=1: the base file tags a non-square SAR after scaling, and
        # concat refuses segments whose SAR differs.
        graph.append(chain + f",setsar=1[p{k}]")
        parts.append(f"[p{k}]")
    graph.append("".join(parts) + f"concat=n={len(parts)}:v=1:a=0[base]")
    for i, name in enumerate(ORDER):
        # Cards are sRGB PNGs; convert with the bt709 matrix the film uses, not
        # swscale's bt601 default, or every card shifts slightly green.
        graph.append(f"[{i + 1}:v]scale=out_color_matrix=bt709:out_range=tv,format=yuv420p[c{i}]")
    prev = "[base]"
    for i, name in enumerate(ORDER):
        ranges = [(a, b) for a, b, nm in segs if nm == name]
        if not ranges:
            continue
        en = "+".join(f"between(n,{a},{b - 1})" for a, b in ranges)
        graph.append(f"{prev}[c{i}]overlay=x={CARD_X}:y={CARD_Y}:eof_action=pass:enable='{en}'[v{i}]")
        prev = f"[v{i}]"
    graph.append(f"{prev}format=yuv420p[vout]")
    dur = n / FPS
    fades = f"afade=t=in:d=0.01,afade=t=out:st={dur - FADE_OUT:.3f}:d={FADE_OUT}"
    graph.append(f"[{len(ORDER) + 1}:a]{fades},{loudnorm(dur, fades)},aresample=48000[aout]")
    os.makedirs(OUT, exist_ok=True)
    out = os.path.join(OUT, "collage.mp4")
    cmd += ["-filter_complex", ";".join(graph), "-map", "[vout]", "-map", "[aout]",
            "-frames:v", str(n), "-r", str(FPS),
            "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
            "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-t", str(dur), out]
    subprocess.run(cmd, check=True)
    with open(os.path.join(OUT, "cutlist.json"), "w") as f:
        json.dump([{"start": a / FPS, "frames": b - a, "card": nm} for a, b, nm in segs], f, indent=1)
    print("wrote", out)


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "render"
    {"cards": make_cards, "plan": show_plan, "render": render}[step]()
