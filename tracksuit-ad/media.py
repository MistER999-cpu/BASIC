"""Small ffmpeg helpers: decode whole clips to numpy, encode frames from a pipe."""
import subprocess, json
import numpy as np


def probe(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                          '-show_entries', 'stream=width,height,r_frame_rate,nb_frames',
                          '-of', 'json', path], capture_output=True, text=True).stdout
    s = json.loads(out)['streams'][0]
    num, den = map(int, s['r_frame_rate'].split('/'))
    return int(s['width']), int(s['height']), num / den, int(s.get('nb_frames', 0))


def read_frames(path, scale=None):
    """All frames of a clip as uint8 (n, h, w, 3)."""
    w, h, fps, _ = probe(path)
    vf = []
    if scale:
        w, h = scale
        vf = ['-vf', f'scale={w}:{h}:flags=lanczos']
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, *vf, '-f', 'rawvideo',
                          '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    n = len(raw) // (w * h * 3)
    return np.frombuffer(raw, np.uint8)[: n * w * h * 3].reshape(n, h, w, 3), fps
