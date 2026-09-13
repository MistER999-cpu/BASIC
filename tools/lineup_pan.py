#!/usr/bin/env python3
"""
lineup_pan.py -- Join N short model clips into ONE continuous left-to-right
camera move, in the style of a fashion-lookbook lineup.

Idea: every clip is laid out side by side on a very wide virtual canvas, the
seams between them are feathered over flat wall, and a 9:16 window is then
craned across that canvas at constant speed. Each clip is delayed so that it is
actually *playing* during the seconds it is on screen, and freeze-padded before
and after (off-screen, so the freeze is invisible).

Usage:
    python3 lineup_pan.py clips/*.mp4 -o out.mp4
    python3 lineup_pan.py clips/*.mp4 -o out.mp4 --style punchy
    python3 lineup_pan.py clips/*.mp4 -o out.mp4 --spacing 0.8 --duration 30
"""

import argparse, os, shutil, subprocess, sys, tempfile


def find_ffmpeg():
    for c in ("ffmpeg", shutil.which("ffmpeg")):
        if c and shutil.which(c):
            return shutil.which(c)
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        sys.exit("ffmpeg not found. Install it, or: pip install imageio-ffmpeg")


FFMPEG = find_ffmpeg()


def probe_duration(path):
    out = subprocess.run([FFMPEG, "-i", path], capture_output=True, text=True).stderr
    for line in out.splitlines():
        if "Duration:" in line:
            hms = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = hms.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    return None


def make_ramp(path, width, height, feather):
    """Full-frame alpha mask: 0 at the left edge ramping to 1 over `feather` px.

    Used to dissolve each clip into the one to its left, across flat wall.
    """
    from PIL import Image
    import numpy as np
    x = np.ones(width, dtype=np.float32)
    r = np.linspace(0.0, 1.0, max(feather, 1), dtype=np.float32)
    x[:feather] = r * r * (3 - 2 * r)            # smoothstep, no visible banding
    Image.fromarray(
        (np.tile(x, (height, 1)) * 255).astype("uint8"), mode="L"
    ).save(path)


def pingpong_prepass(clips, tmp, W, H, FPS, crf, preset, phase):
    """Render forward+reverse copies to disk, rotated by `phase`.

    The reverse filter buffers a whole clip in memory; doing all eight inside
    one graph needs ~12GB, so each is baked separately first.

    Without the rotation the forward/reverse turnaround falls exactly halfway
    through a model's time on screen -- i.e. dead centre frame, where a model
    visibly un-doing their own motion is most obvious. Rotating the loop moves
    both turnarounds out towards the edges. The wrap itself is seamless: the
    ping-pong begins and ends on the same frame.
    """
    out = []
    for i, c in enumerate(clips):
        p = os.path.join(tmp, f"pp{i}.mp4")
        print(f"    ping-pong {i + 1}/{len(clips)} ...", flush=True)
        r = (probe_duration(c) or 6.0) * 2 * phase
        pre = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
               f"crop={W}:{H},fps={FPS},setsar=1,setpts=PTS-STARTPTS,split[a][b];"
               f"[b]reverse,setpts=PTS-STARTPTS[rv];[a][rv]concat=n=2:v=1:a=0")
        if r > 0.01:
            fc = (pre + "[pp];[pp]split[p1][p2];"
                  f"[p1]trim=start={r:.4f},setpts=PTS-STARTPTS[x];"
                  f"[p2]trim=end={r:.4f},setpts=PTS-STARTPTS[y];"
                  "[x][y]concat=n=2:v=1:a=0[v]")
        else:
            fc = pre + "[v]"
        subprocess.run(
            [FFMPEG, "-y", "-loglevel", "error", "-i", c, "-filter_complex", fc,
             "-map", "[v]", "-c:v", "libx264", "-preset", preset,
             "-crf", str(max(crf - 3, 12)), "-pix_fmt", "yuv420p", "-an", p],
            check=True)
        out.append(p)
    return out


def build(args):
    clips = args.clips
    n = len(clips)
    W, H, FPS = args.width, args.height, args.fps

    # --- geometry -----------------------------------------------------------
    S = int(round(args.spacing * W))             # spacing between model centres
    overlap = W - S                              # feathered seam width
    if overlap < 8:
        sys.exit(f"--spacing {args.spacing} leaves no overlap to feather; use < 0.98")
    # The feathered seam must land on empty wall, never across a model.
    edge = (1.0 - args.model_width) / 2.0
    if (1.0 - args.spacing) > edge + 1e-6:
        print(f"  ! --spacing {args.spacing} puts the {overlap}px seam across the model "
              f"(needs >= {1 - edge:.2f} at --model-width {args.model_width}); "
              f"models will ghost through each other.", file=sys.stderr)

    # How wide the model actually is inside its own frame. Everything outside
    # this is wall, and wall may be frozen without anyone noticing.
    mw = args.model_width * W

    src = min(probe_duration(c) or args.clip_len for c in clips)
    pingpong = args.style == "slow"
    avail = src * 2 if pingpong else src         # usable seconds per clip

    # Speed is set by the slowest thing we must satisfy: each model has to stay
    # on screen no longer than its clip can cover.
    v_max = (W + mw) / avail                     # px/s
    if args.duration:
        v = (n - 1) * S / args.duration
        if v < v_max * 0.999:
            pass                                 # slower than needed: fine
        else:
            print(f"  ! --duration {args.duration}s needs {v:.0f} px/s but clips "
                  f"only cover {v_max:.0f} px/s; clamping.", file=sys.stderr)
            v = v_max
    else:
        v = v_max

    total = ((n - 1) * S) / v + 2 * args.hold
    canvas_w = (n - 1) * S + W

    print(f"  clips        : {n} x {src:.2f}s"
          f"{'  (ping-ponged to %.2fs)' % avail if pingpong else ''}")
    print(f"  output       : {W}x{H} @ {FPS}fps, {total:.1f}s")
    print(f"  canvas       : {canvas_w}px wide, spacing {S}px, feather {overlap}px")
    print(f"  pan speed    : {v:.1f} px/s  ({v / W:.3f} screen-widths/s)")
    print(f"  per model    : {S / v:.2f}s centre-to-centre, {(W + mw) / v:.2f}s on screen")

    # --- prepass + masks ----------------------------------------------------
    tmp = tempfile.mkdtemp(prefix="lineup_")
    if pingpong:
        print("  baking ping-pong copies (keeps peak memory sane)...")
        clips = pingpong_prepass(clips, tmp, W, H, FPS, args.crf, args.preset,
                                 args.phase)
    ramp = os.path.join(tmp, "ramp.png")
    make_ramp(ramp, W, H, overlap)

    # --- filtergraph --------------------------------------------------------
    # one ramp copy per feathered seam (every clip but the first)
    fg = [f"[{n}:v]format=gray,scale={W}:{H},split={n - 1}"
          + "".join(f"[rp{i}]" for i in range(1, n))]

    for i, _ in enumerate(clips):
        lbl = f"c{i}"
        f = (f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
             f"crop={W}:{H},fps={FPS},setsar=1,format=rgba,setpts=PTS-STARTPTS")
        if args.match and i > 0:
            f += f",colorchannelmixer=rr={args.gains[i][0]}:gg={args.gains[i][1]}:bb={args.gains[i][2]}"
        fg.append(f + f"[{lbl}]")

        # Delay so the clip is live exactly while its model crosses the window,
        # cloning the first/last frame outside that span.
        t_in = max(0.0, (i * S - (W + mw) / 2) / v + args.hold)
        tail = max(0.0, total - t_in - avail) + 1.0
        fg.append(f"[{lbl}]tpad=start_duration={t_in:.4f}:start_mode=clone:"
                  f"stop_duration={tail:.4f}:stop_mode=clone[{lbl}t]")
        lbl = f"{lbl}t"

        # Feather the left edge of every clip but the first.
        if i > 0:
            fg.append(f"[{lbl}][rp{i}]alphamerge[{lbl}m]")
            lbl = f"{lbl}m"
        fg.append(f"[{lbl}]null[t{i}]")

    fg.append(f"color=c={args.bg}:s={canvas_w}x{H}:r={FPS}:d={total:.3f},format=rgba[base]")
    prev = "base"
    for i in range(n):
        out = f"ov{i}"
        fg.append(f"[{prev}][t{i}]overlay=x={i * S}:y=0:shortest=0:format=auto[{out}]")
        prev = out

    # Crane the window across the canvas.
    hold, T = args.hold, total
    if args.ease:
        p = (f"(t-{hold})/{max(T - 2 * hold, 0.001)}")
        prog = f"clip({p},0,1)"
        xexpr = f"({canvas_w}-{W})*({prog}*{prog}*(3-2*{prog}))"
    else:
        xexpr = f"clip({v}*(t-{hold}),0,{canvas_w - W})"

    # commas inside the expression must be escaped or ffmpeg splits the args
    fg.append(f"[{prev}]crop={W}:{H}:x='{xexpr.replace(',', chr(92) + ',')}':y=0,"
              f"format=yuv420p[v]")

    cmd = [FFMPEG, "-y"]
    for c in clips:
        cmd += ["-i", c]
    cmd += ["-loop", "1", "-i", ramp]
    cmd += ["-filter_complex", ";".join(fg),
            "-map", "[v]", "-t", f"{total:.3f}",
            "-c:v", "libx264", "-preset", args.preset, "-crf", str(args.crf),
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", args.out]
    return cmd, tmp


def measure_gains(clips, W, H):
    """Match each clip's wall tone to the first clip's."""
    import numpy as np
    from PIL import Image
    tmp = tempfile.mkdtemp(prefix="gains_")
    means = []
    for i, c in enumerate(clips):
        p = os.path.join(tmp, f"{i}.png")
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-ss", "0.3", "-i", c,
                        "-frames:v", "1", "-vf", "scale=160:-1", p], check=True)
        a = np.asarray(Image.open(p).convert("RGB"), dtype=np.float32)
        # top band = wall, above the models' heads
        means.append(a[: max(a.shape[0] // 8, 1)].reshape(-1, 3).mean(0))
    ref = means[0]
    return [tuple(round(float(ref[k] / max(m[k], 1e-3)), 4) for k in range(3)) for m in means]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("clips", nargs="+", help="clips in left-to-right screen order")
    ap.add_argument("-o", "--out", default="lineup.mp4")
    ap.add_argument("--style", choices=["slow", "punchy"], default="slow",
                    help="slow = ping-pong each clip, reference-speed pan (long). "
                         "punchy = each clip plays once, ~2x faster pan (short).")
    ap.add_argument("--spacing", type=float, default=0.75,
                    help="gap between model centres, in screen widths (default 0.75)")
    ap.add_argument("--model-width", type=float, default=0.46,
                    help="how much of the frame width the model occupies (default 0.46)")
    ap.add_argument("--duration", type=float, default=None,
                    help="force total length in seconds (slower only)")
    ap.add_argument("--hold", type=float, default=0.6,
                    help="still beat at the head and tail (default 0.6s)")
    ap.add_argument("--phase", type=float, default=0.25,
                    help="where the ping-pong turnaround sits in a model's time "
                         "on screen, 0-0.5 (default 0.25; 0 puts it dead centre)")
    ap.add_argument("--ease", action="store_true",
                    help="ease the move in and out instead of constant speed")
    ap.add_argument("--match", action="store_true",
                    help="colour-match every clip's wall to the first clip")
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1920)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--clip-len", type=float, default=6.0)
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--preset", default="medium")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    args.bg = "0xEDEAE4"
    args.gains = [(1, 1, 1)] * len(args.clips)
    if args.match:
        print("  matching wall tone across clips...")
        args.gains = measure_gains(args.clips, args.width, args.height)
        for c, g in zip(args.clips, args.gains):
            print(f"    {os.path.basename(c):28s} gain r={g[0]} g={g[1]} b={g[2]}")

    cmd, tmp = build(args)
    if args.dry_run:
        print("\n" + " ".join(f"'{a}'" if " " in a or ";" in a else a for a in cmd))
        return
    print("  rendering...")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-4000:], file=sys.stderr)
        sys.exit("ffmpeg failed")
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"  done -> {args.out}")


if __name__ == "__main__":
    main()
