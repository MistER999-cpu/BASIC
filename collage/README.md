# Collage overlay

A fast-cutting 4:5 card of product photos composited over the background film,
centred on the frame, in the style of the reference edit.

## Where the assets go

| Folder | What goes in it |
|---|---|
| `collage/base/` | The background film, named `base.mp4` (9:16 vertical) |
| `collage/cards/` | The 16 card images, named by their place in the loop (below) |
| `collage/audio/` | Optional: a separate music track, named `music.mp3` or `music.wav`. Leave empty to keep the film's own audio |

## Card names

Name each card by its slot in the loop. Colour and pose both change on every swap.

| File | Card |
|---|---|
| `01-white-full.jpg` | White, full body |
| `02-beige-tilt.jpg` | Beige, Dutch tilt |
| `03-brown-closeup.jpg` | Brown, close-up |
| `04-black-crop.jpg` | Black, headless crop |
| `05-white-tilt.jpg` | White, Dutch tilt |
| `06-beige-closeup.jpg` | Beige, close-up |
| `07-brown-crop.jpg` | Brown, headless crop |
| `08-black-full.jpg` | Black, full body |
| `09-white-crop.jpg` | White, headless crop |
| `10-beige-full.jpg` | Beige, full body |
| `11-brown-tilt.jpg` | Brown, Dutch tilt |
| `12-black-closeup.jpg` | Black, close-up |
| `13-white-closeup.jpg` | White, close-up |
| `14-beige-crop.jpg` | Beige, headless crop |
| `15-brown-full.jpg` | Brown, full body |
| `16-black-tilt.jpg` | Black, Dutch tilt |

`.png` or `.jpeg` are fine too. Cards do not need to be cropped to 4:5
beforehand; they are centre-cropped to fit the card when the edit is rendered.

## Render

The finished cut is `collage/export/collage.mp4`. To rebuild it:

```bash
pip install opencv-python-headless imageio-ffmpeg
python3 collage/build.py cards     # crop the 16 cards -> out/collage/cards/
python3 collage/build.py plan      # print the cut list
python3 collage/build.py render    # -> out/collage/collage.mp4
```

`build.py` maps each card to its source in `CARDS`: the eight new images in
`collage/cards/`, and the eight studio shots cropped from the side-by-side
photos in `collage/cards/studio/`. The Dutch-tilt cards are rotated 13-14° in
the direction each pose already leans, since the generated images came out
nearly level.

What the edit does, and why:

- **Card:** 760x950 (4:5), dead centre, 70% of the frame width, hard edges.
  Same proportions as the reference.
- **Cuts on the beat:** the track is 132 BPM (the three drops sit exactly 116
  and 82 beats apart), so a card lasts one beat, 0.455 s, matching the
  reference's ~0.46 s. The film opens on the drop at 36.63 s of the song.
- **One two-beat hold** on the white full-body card, ending on the cut to the
  brown clip, as the reference holds one card across a background cut.
- **Swaps near a background cut snap onto it** (within 2 frames), so the two
  layers never cut a few frames apart.
- **Faces clear the card:** clips 1, 2 and 5 are scaled up about the bottom
  edge (`REFRAME`) so her head sits above the card, as in the reference.
- **Colour:** composited in ffmpeg on the bt709 path, so neither the film nor
  the cards shift colour. Audio is loudness-matched to -11 LUFS, -1 dBTP.
