#!/usr/bin/env python3
"""Synthesise the sound effects from the render's own cue sheet.

    python3 tools/sfx.py out/cues.json out/sfx.wav

The cues come out of src/outfit.html at build time - the same arrays the
scene draws from - so a tick cannot drift from the cut it belongs to. Timing
them by ear against the finished video would put them a frame or two off and
a UI sound a frame off its cut reads as latency.

Three voices. A soft wooden tock on each garment cut, pitched a little lower
for the bottom slot than the top so the two rows are audible apart without
anyone being told that is what they are hearing. A short dry tick on each
typed character, well under the tock. A quieter, lower tick on each backspace,
which at 26-34ms apart runs together into one burst rather than reading as
separate keys. Then a two-note resolve under the final cut, so the clip lands
rather than stopping.
"""
import json, sys
import numpy as np

SR = 48000


def env(n, attack, decay):
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-6), 0, 1)
    return a * np.exp(-t / decay)


def lowpass(x, cutoff):
    """One-pole, applied forwards and back so the transient stays centred."""
    a = np.exp(-2 * np.pi * cutoff / SR)
    for d in (1, -1):
        y = np.empty_like(x[::d]); acc = 0.0
        for i, v in enumerate(x[::d]):
            acc = (1 - a) * v + a * acc
            y[i] = acc
        x = y[::d]
    return x


def tock(f0, dur, peak, tone=0.62, bright=3200, rng=None):
    n = int(SR * dur)
    t = np.arange(n) / SR
    # a touch of downward pitch drift is what separates a struck object from a beep
    body = np.sin(2 * np.pi * (f0 * (1 - 0.18 * t / dur)) * t) * env(n, 0.0004, dur * 0.28)
    click = lowpass(rng.standard_normal(n), bright) * env(n, 0.0001, dur * 0.045)
    x = tone * body + (1 - tone) * click * 3.0
    m = np.abs(x).max()
    return x / m * peak if m > 0 else x


def chime(freqs, dur, peak, rng=None):
    n = int(SR * dur)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for i, f in enumerate(freqs):
        d = int(SR * 0.055 * i)
        e = env(n - d, 0.004, dur * 0.30)
        x[d:] += np.sin(2 * np.pi * f * t[:n - d]) * e * (0.85 ** i)
        x[d:] += np.sin(2 * np.pi * f * 2 * t[:n - d]) * e * 0.16 * (0.85 ** i)
    m = np.abs(x).max()
    return x / m * peak if m > 0 else x


def place(buf, x, t):
    i = int(round(t * SR))
    if i >= len(buf):
        return
    n = min(len(x), len(buf) - i)
    buf[i:i + n] += x[:n]


def main():
    cues = json.load(open(sys.argv[1] if len(sys.argv) > 1 else 'out/cues.json'))
    out = sys.argv[2] if len(sys.argv) > 2 else 'out/sfx.wav'
    dur = cues['duration']
    rng = np.random.default_rng(7)            # fixed, so a re-render is identical
    buf = np.zeros(int(SR * (dur + 0.6)))

    voice = {
        'top':    tock(1180, 0.085, 0.50, rng=rng),
        'bottom': tock(880,  0.095, 0.50, rng=rng),
    }
    key = tock(2350, 0.020, 0.085, tone=0.30, bright=6000, rng=rng)
    dele = tock(1650, 0.016, 0.048, tone=0.25, bright=5200, rng=rng)

    # the arrow shrinks a press-length before the garment changes, and that
    # motion is otherwise silent. A quiet click on the way down, the tock on
    # the change - the same two-part shape a real button has.
    press = tock(2050, 0.018, 0.075, tone=0.22, bright=5600, rng=rng)
    for c in cues['cuts']:
        place(buf, press, c['t'] - cues.get('pressLead', 0))
        place(buf, voice[c['row']], c['t'])
    for t in cues['keys']:
        place(buf, key, t)
    for t in cues['deletes']:
        place(buf, dele, t)

    last = cues['cuts'][-1]['t']
    place(buf, chime([659.25, 987.77], 1.5, 0.30, rng=rng), last + 0.02)

    buf = buf[:int(SR * dur)]
    buf[-int(SR * 0.05):] *= np.linspace(1, 0, int(SR * 0.05))   # no tail click
    peak = np.abs(buf).max()
    if peak > 0:
        buf *= 0.70 / peak      # -3.1 dBFS; the platforms normalise from here
    rms = float(np.sqrt((buf ** 2).mean()))

    import wave
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(buf, -1, 1) * 32767).astype('<i2').tobytes())

    print(f'  {len(cues["cuts"])} cuts + presses, {len(cues["keys"])} keys,'
          f' {len(cues["deletes"])} backspaces -> {out}')
    print(f'  peak {20*np.log10(max(np.abs(buf).max(),1e-9)):.1f} dBFS'
          f'   rms {20*np.log10(max(rms,1e-9)):.1f} dBFS')


if __name__ == '__main__':
    main()
