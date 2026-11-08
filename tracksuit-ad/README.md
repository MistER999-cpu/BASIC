# BASIC Essentials — tracksuit ad (v2)

A 20-second, 1080×1920 Instagram ad in French for the mock-neck tracksuit in
three colourways, Bordeaux, Chocolat and Noir. Each colourway gets its own
segment and appears once. The ad is set in a storm: rain, mist, lightning and
water on glass.

The layout follows the reference ad:
- the model on the left;
- in a frosted-glass column on the right: the ghost-mannequin outfit, the
  colour swatches and the copy.

## Run it

```bash
pip install scipy                 # numpy and Pillow are assumed; ffmpeg on PATH
python3 prep_models.py            # key the three models -> build/cutouts/
python3 render.py preview 3.6 8.4 12.6 16.6 19.2   # stills -> out/preview/
python3 render.py full            # -> out/basic_ad_silent.mp4      (~3 min)
python3 audio.py                  # -> out/soundtrack.wav           (~5 s)
ffmpeg -i out/basic_ad_silent.mp4 -i out/soundtrack.wav -map 0:v -map 1:a \
       -c:v copy -af "loudnorm=I=-14:TP=-1.5:LRA=11" -ar 48000 \
       -c:a aac -b:a 192k -shortest -movflags +faststart out/basic_ad_v2.mp4
```

The final step normalises the audio to −14 LUFS, the loudness Instagram plays
at. The first render keys every ghost-mannequin frame and caches the result in
`build/`. Every animation is a pure function of time, so `preview` renders any
single frame on its own.

## Timeline and copy

| Time (s) | Section | On screen |
|---|---|---|
| 0 – 1.8 | Cold open | The storm opens on a strike. The BASIC logo forms out of the flash, is swept with light, and ESSENTIALS unfolds from the centre. Then `L’ENSEMBLE D’HIVER`. The logo flies into the header as the layout slides in. |
| 1.8 – 6.6 | Bordeaux | `01 · L’ENSEMBLE` / *Bordeaux* / un rouge profond, chaleureux et élégant. / sweat col montant oversize et pantalon large assorti. |
| 6.6 – 10.8 | Chocolat | `02 · LA MATIÈRE` / *Chocolat* / un brun doux et gourmand, comme un chocolat chaud. / molleton épais et doux, finition mate. |
| 10.8 – 15.0 | Noir | `03 · LA COUPE` / *Noir* / intemporel, il se porte avec tout. / col montant, épaules tombantes, ourlet arrondi. |
| 15.0 – 17.4 | Lineup | The three looks together, then *Un ensemble. Trois couleurs.* and `BORDEAUX · CHOCOLAT · NOIR`. |
| 17.4 – 20.0 | Slate | The scene blurs back, then the logo, `L’ENSEMBLE D’HIVER` and the `disponible maintenant` pill. |

The copy and timing live in `SEGMENTS` at the top of `render.py`. The fabric
line describes what the product shots show: thick, soft fleece with a matte
finish. Replace it with the real composition when it is confirmed.

## Effects

- **Lightning.** The strikes on the cuts carry the bolt into open sky, a
  bloom, a flash veil, a chromatic split, camera shake, and a rim light on the
  models. Faint flickers between the cuts are distant weather.
- **Rain.** Two procedural layers: fine rain behind everything, and a few
  out-of-focus streaks in front.
- **Mist.** Two drifting fractal layers around the models' feet.
- **Glass.** The column is frosted from the live plate behind it, with a
  sheen, a fine frost texture, still water beads and drops that run down in
  stick-slip motion.
- **Outfit.** Each ghost-mannequin clip plays its own front → side → front
  turn once. Between colourways the outfit does a 3D card turn.
- **Models.** Each model enters with motion blur, slowly pushes in, and
  settles after each cut.
- **Swatches.** The selected swatch gets a gapped ring and a ripple.
- **Text.** The colour names reveal letter by letter. The colour lines come
  into focus. The labels type out.
- **Storm plate.** The plate is slowed with frame blending to span all 20 s.
- **Finish.** A vignette and film grain over the whole frame.

## Sound (`audio.py`, all synthesised)

- **Rain.** Pink noise rolled off above about 2.6 kHz, so it stays soft on the
  ear.
- **Pad.** A warm, low-passed chord bed that changes with each section.
- **Thunder.** A rounded crack and a long rolling rumble after each strike.
- **Effects.** Whooshes on moves, low impacts on cuts, a reverse swell into
  each strike, a shimmer on each logo sweep, a riser into the lineup, soft
  pops on the swatches and quiet ticks on the typed labels.

Every cue is placed from the constants in `render.py`, so retiming the picture
retimes the sound.

## Assets (not committed)

The media stays on the machine that renders it and is git-ignored. Put the
files here:

| File | What it is |
|---|---|
| `assets/models/M1_bordeaux.jpg`, `M3_chocolat.jpg` | Hero poses on green (Nano Banana 2) |
| `assets/models/M2_noir.jpg` | Hero pose on a grey sweep |
| `assets/ghosts/GHOST_{bordeaux,chocolat,noir}.mp4` | Ghost-mannequin turns (Omni Flash); all three have identical timing |
| `assets/background/storm.mp4` | The storm plate. It opens on a bolt. |
| `assets/brand/basic_logo.png` | The BASIC Essentials logo, black on transparent |

Fonts: Inter, installed on the system, and Playfair Display, in `fonts/`
under the SIL Open Font License.

## Keying notes

The keys are in `keying.py`. Each one compares a pixel against an estimate of
the backdrop *behind that pixel* (a clean plate built by normalised
convolution), not against a single backdrop colour.

- **Green:** a chroma difference against the local plate, then green spill
  removal.
- **Grey sweep:**
  - The backdrop is "neutral, not warm, no brighter than the sweep".
  - Shaded white sneaker leather matches the sweep exactly. To recover it,
    each shoe is filled as its convex outline, trimmed at the gum sole.
- **Ghost mannequins:** a solid luminance core with a soft edge only in a thin
  band, so the outfit's floor shadow never keys in.

## Upgrading

- **Animated models:** key Omni Flash clips of the models per frame, as
  `load_ghosts` already does for the ghosts, and swap them in for the stills
  in `model_sprite`.
- **Music:** lay music over `out/soundtrack.wav`, or replace it.
