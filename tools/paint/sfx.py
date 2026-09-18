"""Synthesise the spot's audio.

The reference film has no music at all - it is mouse clicks, one whoosh on
every enter, and a burst of static on every restart, over silence. That is the
whole mix, and it is a large part of why the thing reads as a computer rather
than an advert, so this rebuilds those three sounds rather than scoring it.
"""
import json, wave, numpy as np

SR = 48000
cfg = json.load(open('config.paint.json'))
A   = cfg['anim']
dur = cfg['output']['duration'] + 0.4
buf = np.zeros((int(dur * SR), 2))

rng = np.random.default_rng(7)

def put(sig, t, pan=0.0):
    i = int(t * SR)
    n = min(len(sig), len(buf) - i)
    if n <= 0: return
    buf[i:i + n, 0] += sig[:n] * (1 - max(0.0, pan))
    buf[i:i + n, 1] += sig[:n] * (1 + min(0.0, pan))

def env(n, a, d, p=2.0):
    e = np.ones(n); ai = int(a * SR); di = int(d * SR)
    if ai: e[:ai] = np.linspace(0, 1, ai)
    if di: e[-di:] = np.linspace(1, 0, di) ** p
    return e

def tick(level, bright=1.0):
    """A mouse switch: a tiny snap of filtered noise plus its plastic ring."""
    n = int(0.018 * SR)
    noise = rng.normal(0, 1, n) * env(n, 0.0002, 0.016, 3.2)
    t = np.arange(n) / SR
    ring = np.sin(2 * np.pi * 2300 * bright * t) * np.exp(-t * 320) * 0.5
    s = (noise * 0.7 + ring) * level
    return s / (np.abs(s).max() + 1e-9) * level

def click(t, level=0.26):
    put(tick(level), t)                       # press
    put(tick(level * 0.38, 1.15), t + 0.10)   # release

def whoosh(t, level=0.62):
    """enter: a filtered noise sweep that lands on a soft thud."""
    n = int(0.50 * SR); k = np.arange(n) / SR
    noise = rng.normal(0, 1, n)
    # sweep by resampling a lowpass cutoff via cumulative phase on a sine bed
    sweep = np.sin(2 * np.pi * np.cumsum(np.linspace(180, 1500, n)) / SR)
    body  = (noise * 0.45 + sweep * 0.55) * env(n, 0.03, 0.34, 1.6)
    thud  = np.sin(2 * np.pi * 70 * k) * np.exp(-k * 12) * 0.9
    s = body * 0.8 + thud
    put(s / np.abs(s).max() * level, t)

def glitch(t, level=0.34, d=None):
    """restart: quantised digital static, stepped so it reads as data not hiss."""
    d = d or A['glitchDur']
    n = int(d * SR)
    raw = rng.normal(0, 1, n)
    step = int(SR / 5200)                      # sample-and-hold -> crunchy
    held = np.repeat(raw[::step], step)[:n]
    if len(held) < n: held = np.pad(held, (0, n - len(held)))
    s = held * env(n, 0.004, 0.09, 1.2)
    s += np.sin(2 * np.pi * 95 * np.arange(n) / SR) * env(n, 0.002, 0.12) * 0.35
    put(s / np.abs(s).max() * level, t)

def land(t, level=0.12):
    """The soft thump of a garment settling onto the canvas, a beat after its
    click. Without it the pop reads as silent and the click feels unanswered."""
    n = int(0.09 * SR); k = np.arange(n) / SR
    s = (np.sin(2 * np.pi * 150 * k) * 0.6 + rng.normal(0, 1, n) * 0.4)
    s *= np.exp(-k * 34)
    put(s / np.abs(s).max() * level, t)

for r in cfg['rounds']:
    click(r['swatchT'], 0.22)                  # choosing the colourway
    for p in r['picks']:
        click(p['t'])
        land(p['t'] + A['popLag'] + 0.04)
    click(r['enter'], 0.30)
    whoosh(r['enter'] + A['revealLag'] - 0.06)
    click(r['heart'], 0.20)
    land(r['heart'] + 0.02, 0.09)
    click(r['restart'], 0.26)
    glitch(r['restart'])
whoosh(cfg['endcard']['t'] - 0.05, 0.30)

peak = np.abs(buf).max()
buf = buf / peak * 0.89                        # leave a little headroom
pcm = (np.clip(buf, -1, 1) * 32767).astype('<i2')
with wave.open('out/paint.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print(f'out/paint.wav  {dur:.2f}s  peak before norm {peak:.2f}')
