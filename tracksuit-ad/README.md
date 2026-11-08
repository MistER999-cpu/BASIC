# Tracksuit ad — storm edit

A 15-second, 1080×1920 Instagram ad for the mock-neck tracksuit in three
colourways (prune, chocolat, noir), in French. The structure follows the
reference ad in `assets/reference/`:
- a model on the left;
- the ghost-mannequin outfit top-right, with colour dots under it;
- a headline that builds word by word while model, outfit and active dot swap
  together on the beat.

The difference from the reference is the backdrop: a storm sky with rain and
lightning instead of a plain white page.

## Run it

```bash
pip install scipy                 # numpy and Pillow are assumed; ffmpeg on PATH
python3 prep_models.py            # key the three models -> build/cutouts/
python3 render.py preview 2.7 8.6 12.6     # stills -> out/preview/
python3 render.py full            # -> out/tracksuit_ad_base_silent.mp4
python3 audio.py                  # rain + thunder bed -> out/ambience.wav
ffmpeg -i out/tracksuit_ad_base_silent.mp4 -i out/ambience.wav \
       -c:v copy -c:a aac -b:a 192k -shortest out/tracksuit_ad_base.mp4
```

The first render keys every ghost-mannequin frame and caches the result in
`build/` (about 80 s). After that a full render takes about 90 s. Every
animation is a pure function of time, so `preview` renders any single frame
on its own.

## Assets

Media is not committed. The generated model shots, ghost clips and storm
plate stay on the machine that renders, and the third-party reference ad is
never redistributed. Put the files at these paths before running:

| File | What it is |
|---|---|
| `assets/models/M1_prune.jpg`, `M3_choco.jpg` | Hero poses on green, generated with Nano Banana 2 |
| `assets/models/M2_noir.jpg` | Hero pose on a grey sweep |
| `assets/ghosts/GHOST_*.mp4` | Ghost mannequins turning front → side → front, generated with Omni Flash; all three have identical timing |
| `assets/background/storm.mp4` | Storm plate, about 15 s; opens on a bolt |
| `assets/background/storm_lightning.jpg` | The still the storm plate was animated from |
| `assets/reference/ref1_base_layout.mp4` | The layout and pacing reference. A third-party ad, kept out of git |

## Timeline

The swaps sit on a 100 BPM grid (one beat = 0.6 s), so any 100 BPM track lines
up with the cuts.

| Time (s) | What happens |
|---|---|
| 0 – 0.7 | The model slides in from the left and the glass column from the right. The outfit card-flips in and the dots pop. The plate's own bolt is the hook. |
| 0.75 – 2.5 | `douce, / essentielle / et iconique :` builds word by word, then the three-line subline. |
| 3.0, 4.8 | Swaps: prune → chocolat → noir. On each swap the model cuts, the outfit card-turns to the new colour, and the active swatch moves. |
| 6.6 | Lightning. Card 2: grey `ensemble` turns into the bold `ensemble oversize à col montant, évidemment !` |
| 7.8, 9.0 | Faster swaps, two beats each. |
| 10.2 | A strong flash hides the cut to the end card: the three looks side by side. |
| 10.6 – 11.9 | `1 ensemble. 3 couleurs.`, `prune · chocolat · noir`, then the `disponible maintenant` pill. |

To retime the edit, change `SHOTS`, `END_CARD` and `LIGHTNING` in `render.py`,
and the `t_in` / `t_out` values in `build_texts()`.

## Keying notes

The keys are in `keying.py`. Each one compares a pixel against an estimate of
the backdrop *behind that pixel* (a clean plate built by normalised
convolution), not against a single backdrop colour. The generated studios are
vignetted and have floor shadows.

- **Green (M1, M3):** a chroma difference against the local plate, then green
  spill removal.
- **Grey sweep (M2):**
  - The backdrop is "neutral, not warm, no brighter than the sweep". White
    sneaker leather is brighter than the sweep; the suede toe and gum sole are
    warmer.
  - Shaded white leather matches the sweep exactly. To recover it, each shoe
    is filled as its convex outline, built from its unambiguous pixels and
    trimmed at the gum sole.
- **Ghost mannequins:** a solid luminance core (fabric is 100+ levels darker
  than the sweep) with a soft edge only in a 3 px band. The outfit's floor
  shadow is only 25–55 levels darker, so it never joins the core.
- The ghost loop has a small seam between its last and first frames. It is
  hidden with a 6-frame crossfade.

## Upgrading

Each layer can be replaced on its own:

- **Animated models:** for Omni Flash clips of the models, key them per frame
  as `render.py` already does for the ghosts, and replace the still in
  `draw_model`.
- **Brand:** the end card has no logo yet. Add it under the CTA in
  `render_frame`.
- **Music:** `out/ambience.wav` is a synthesised rain and thunder bed. Lay
  music over it or replace it.
- **Colour:** `DOT_RGB` holds the on-screen garment colours, measured from the
  models' torsos. The brown ghost is lifted to the sheet master in
  `load_ghosts`.
