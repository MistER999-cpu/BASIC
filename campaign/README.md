# Campaign video — working notes

Analysis and source material for the BASIC video. Generation tools: Nano Banana
2.1 (images) and Omni 1.1 Flash (video). No prompts yet — this file holds what
we know, so the prompt pack can be written once all outfit sets are in.

**Status:** tank and set 1 in; waiting for set 2.

## Brand

- Name: BASIC — logo lockup reads `BASIC` / `ESSENTIALS`, black on transparent.
- Line: "The essentials, considered." Eleven styles, muted palette (bone, sand,
  oat, clay, ink). Quiet and editorial rather than trend-driven.
- [`brand/logo.png`](brand/logo.png) — 643×388 RGBA. Soft at full-screen; ask
  for an SVG or a larger export before final render.

## References

Neither is an AI-generated video. Both are 2D compositing: cut-out stills on
layers, moved by keyframes. That means AI makes the assets and the motion is
built in an editor, which keeps the garments exactly as they are.

### A — the folder ([`A-folder.mp4`](references/A-folder.mp4))

5.4s, 720×900 (4:5), 30fps, no audio, white background.
[Contact sheet](references/A-folder-contact-sheet.png).

| Time | What happens |
|---|---|
| 0.0–1.0s | Pink Mac-style folder, label "cosy fall essentials", under a Notes card "FILE → FAVES" (comment-for-template CTA). Cursor glides in, clicks ~0.8s. |
| 1.2–2.5s | Seven products emerge **from behind** the folder (folder is the top layer, so it masks them), fan out staggered, overshoot and settle in a ring. |
| 2.5–5.4s | Static hold. |

Keep: click → burst → settle rhythm; the folder masking the items as they exit.
Drop: the 3s hold (built for screenshots) — about 1s in a video.

### B — the slide ([`B-slide.mp4`](references/B-slide.mp4))

9.9s, 720×1280 (9:16), 60fps, with music.
[Contact sheet](references/B-slide-contact-sheet.png).

One continuous horizontal pan across a single wide panorama:

- Background: real meadow photo, washed-out cream sky, soft overcast light.
- Three full-body model cut-outs standing in the grass, mixed poses (front-on,
  walking, hand on hip).
- Oversized watercolour flowers as foreground layers between the models. Each
  flower repeats the print on the tee beside it — the decoration echoes the
  product.

| Time | What happens |
|---|---|
| 0–0.75s | Hold on model 1 |
| ~2.0s | Eases past model 2 |
| 3.25–3.9s | Settles on model 3, landing on the 3.73s beat |
| 4.25s | Brand name enters on the strongest beat in the track |
| 4.25–9.9s | Pan decelerates onto empty sky, brand name + two butterflies, hold |

The pan eases in and out at each model rather than moving at constant speed.

Audio onsets (`tools/onsets.py`): 0.36, 0.52, 0.69, **1.83**, 3.17, **3.73**,
3.88, **4.25** (strongest), 6.63, 7.87, 9.03s.

## Concept so far (not locked)

About 13s, 9:16. Folder burst → push into the folder → horizontal slide across
the looks → logo on empty sky.

- Folder in brand colours (sand, darker tab, ink label) instead of pink; drawn
  as vector in Figma/Canva rather than generated.
- Slide background: hazy overcast meadow, to match the flat studio light of the
  look photos (golden hour would read as pasted on).
- Foreground decoration tied to each look's colourway instead of a print.
- Slide order light → dark, ending on black next to the black logo.

## Items

### Tank — high mock-neck sleeveless, four colourways

Same model in all four: early 20s, shoulder-length dark brown curly hair,
centre part, olive skin, brown eyes, no-makeup look. Taupe studio backdrop,
flat frontal light, cropped at mid-thigh, identical front-on pose.

| File | Tank | Styled with |
|---|---|---|
| [`1-cream-grey-pinstripe.jpg`](looks/tank/1-cream-grey-pinstripe.jpg) | Cream / ecru | Grey pinstripe pleated wide-leg trousers |
| [`2-beige-brown-suede.jpg`](looks/tank/2-beige-brown-suede.jpg) | Beige | Brown suede five-pocket trousers |
| [`3-brown-raw-denim.jpg`](looks/tank/3-brown-raw-denim.jpg) | Brown | Raw indigo denim, tan leather belt, gold cuff, gold hoops |
| [`4-black-black-pinstripe.jpg`](looks/tank/4-black-black-pinstripe.jpg) | Black | Black pinstripe high-waist straight trousers |

Matted flat-lays of all four colourways already exist in
[`assets/products/`](../assets/products) — usable for the folder burst.

Open points:

- Cropped at mid-thigh — the slide needs full-length figures with shoes.
- Same pose ×4 — repetitive in a pan; the reference varies poses.
- "White" reads cream here but cooler in the flat-lay `white.png`. Which is true?
- Only the brown look carries accessories. Intentional?
- Taupe backdrop is close to the beige and brown tanks, which makes cut-outs
  bleed at the edges.

### Set 1 — cami crop top + bike shorts

Matching two-piece in a matte cotton-stretch jersey: cropped cami with thin
spaghetti straps and a soft V/scoop neck, high-rise bike shorts ending
mid-thigh with a centre-front seam. Three colourways: white, beige, black.

Two models:

- **Model A** — shoulder-length dark curly hair, olive skin, brown eyes. Reads
  as the tank model, but smiling and slightly softer in the face; check the
  likeness holds before mixing her across items.
- **Model B** — long straight auburn-brown hair, centre part, fair skin, curvier
  build.

All five: full length, head to toe, barefoot, same pose (weight on one leg,
feet lightly crossed, hands relaxed at the thighs), soft smile. Flat cool
light-grey backdrop, about rgb(168,168,170) — not the tank's warm taupe.

| File | Colour | Model |
|---|---|---|
| [`1-white-model-a.jpg`](looks/set-1/1-white-model-a.jpg) | White | A |
| [`2-beige-model-a.jpg`](looks/set-1/2-beige-model-a.jpg) | Beige | A |
| [`3-black-model-a.jpg`](looks/set-1/3-black-model-a.jpg) | Black | A |
| [`4-beige-model-b.jpg`](looks/set-1/4-beige-model-b.jpg) | Beige | B |
| [`5-black-model-b.jpg`](looks/set-1/5-black-model-b.jpg) | Black | B |

Open points:

- Already full length with feet in frame — ready for the slide as they are,
  unlike the tank looks.
- Barefoot here, while the tank looks will need shoes. Pick one rule for the
  whole video.
- Same pose ×5, as with the tank — the slide wants variation.
- No white on Model B. Intentional, or still to come?
- Beige sits close to both models' skin tones; at slide scale it can read as
  bare skin. Worth weighing against a contrasting background or decoration.
- Grey backdrop contrasts well with all three colours, so cut-outs should be
  clean — except white against grey at the strap edges, which is the closest
  pair.
- Cool grey here vs warm taupe for the tank: once cut out this no longer
  matters, but the two sets were lit slightly differently (this one cooler).

### Set 2

_Pending._

## Still needed

- Outfit set 2
- Music track (all timing goes on its beats)
- Final folder contents
- CTA wording, if any
- Logo as SVG or a larger PNG
