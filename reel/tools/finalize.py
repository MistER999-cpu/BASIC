#!/usr/bin/env python3
"""Loudness-normalise the sound, mux it onto the picture, write the cover.

    python3 tools/finalize.py

Outputs in export/:
  BASIC_debardeur_reel.mp4          picture + music + sticker foley
  BASIC_debardeur_reel_sfx-only.mp4 picture + foley only, to lay a licensed track under
  BASIC_debardeur_cover.jpg         Reel cover; the subject sits inside the 3:4 grid crop
"""
import json, os, re, subprocess, sys
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, 'build')
EXPORT = os.path.join(ROOT, 'export')
sys.path.insert(0, os.path.join(ROOT, 'tools'))


def loudnorm(src, dst, target=-14.0, tp=-1.5):
    """Two-pass EBU R128: measure, then apply linearly. Reels play at about -14 LUFS."""
    p = subprocess.run(['ffmpeg', '-hide_banner', '-i', src, '-af',
                        f'loudnorm=I={target}:TP={tp}:LRA=11:print_format=json', '-f', 'null', '-'],
                       capture_output=True, text=True)
    m = json.loads(re.search(r'\{[^{}]*"input_i"[^{}]*\}', p.stderr, re.S).group(0))
    af = (f'loudnorm=I={target}:TP={tp}:LRA=11:measured_I={m["input_i"]}:measured_TP={m["input_tp"]}:'
          f'measured_LRA={m["input_lra"]}:measured_thresh={m["input_thresh"]}:offset={m["target_offset"]}:'
          f'linear=true,aresample=48000')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-af', af, '-ar', '48000', dst], check=True)
    return m


def mux(video, audio, dst):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', video, '-i', audio,
                    '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k',
                    '-ar', '48000', '-shortest', '-movflags', '+faststart', dst], check=True)


def cover():
    import render
    render.init_worker()
    A = render.A
    i = int(round(11.9 * render.FPS))
    fr = render.frame_at(i).astype(np.float32) / 255
    # brand mark under the grid, inside the 3:4 crop (y 240..1680)
    logo = A.logo
    render.place(fr, logo, render.W / 2, 1545, 0.42, 0, 1.0)
    Image.fromarray((np.clip(fr, 0, 1) * 255 + 0.5).astype(np.uint8)).save(
        os.path.join(EXPORT, 'BASIC_debardeur_cover.jpg'), quality=94)


def main():
    os.makedirs(EXPORT, exist_ok=True)
    video = os.path.join(BUILD, 'video.mp4')
    full = os.path.join(BUILD, 'audio_full.wav')
    sfx = os.path.join(BUILD, 'audio_sfx.wav')
    m1 = loudnorm(os.path.join(BUILD, 'audio_full_raw.wav'), full)
    m2 = loudnorm(os.path.join(BUILD, 'audio_sfx_raw.wav'), sfx, target=-16.0)
    print('full measured', m1['input_i'], 'LUFS ->', -14, '| sfx', m2['input_i'], '->', -16)
    mux(video, full, os.path.join(EXPORT, 'BASIC_debardeur_reel.mp4'))
    mux(video, sfx, os.path.join(EXPORT, 'BASIC_debardeur_reel_sfx-only.mp4'))
    cover()
    for f in sorted(os.listdir(EXPORT)):
        print(f, os.path.getsize(os.path.join(EXPORT, f)) // 1024, 'KB')


if __name__ == '__main__':
    main()
