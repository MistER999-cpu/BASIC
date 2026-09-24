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
