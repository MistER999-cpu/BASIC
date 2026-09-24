# Tank top grid ad

| File | What it is |
|---|---|
| `tank-top-grid-ad-v2.mp4` | **Current.** 1080×1920, 24 fps, 14.7 s. Printed-paper look, synced to the beat |
| `tank-top-grid-ad-v1.mp4` | First version: a straight rebuild of the reference, 8.7 s |

Each look replaces the previous one piece by piece across a 3×4 grid, in reading order.

- **Order:** A-sand → B-brown → A-cream → B-black → A-brown → B-sand → A-black → B-cream
  (models alternate; each half shows all four colours; every transition is between contrasting backdrops).
- **Paper:** each photo is a matte print on its own sheet (paper tooth lit from the side, softened blacks,
  each cut piece catching the light slightly differently), laid on a paper board. Seams are real cuts:
  small gaps with bright cut edges, stray fibres and soft shadows. Seam positions and strengths come from
  `grid_geometry.json`, measured from the reference video; faded seams stay butted.
- **Timing:** locked to the 93.2 BPM beat. Each transition flips 12 pieces over 2 beats, with the last
  piece landing on the beat, then the look holds for about a beat.
- **Audio:** `reference_audio.wav` (from the reference video), with its two-bar phrase looped on matching
  onsets and faded out after the final beat.

Re-render (e.g. after changing `ORDER` or swapping images in `../ad-images`):

```
pip install opencv-python-headless numpy soundfile imageio-ffmpeg
python3 render.py
```
