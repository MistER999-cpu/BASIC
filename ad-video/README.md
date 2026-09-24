# Tank top grid ad

`tank-top-grid-ad.mp4`: 1080×1920, 24 fps, 8.7 s, AAC audio.

A rebuild of the reference tile-grid transition. Each photo replaces the previous one
tile by tile across a 3×4 grid, in reading order, one tile every 0.1 s.

- **Order:** A-sand → B-brown → A-cream → B-black → A-brown → B-sand → A-black → B-cream
  (models alternate; each half shows all four colours; every transition is between contrasting backdrops).
- **Grid:** `grid_geometry.json` holds every seam segment's position and opacity, measured from the
  reference video, including the small jogs and the faded seams.
- **Audio:** `reference_audio.wav` (taken from the reference video) with one bar repeated at a quiet,
  beat-aligned join, so it covers the 8 images.

Re-render (e.g. after changing `ORDER` or swapping images in `../ad-images`):

```
pip install opencv-python-headless numpy soundfile imageio-ffmpeg
python3 render.py
```
