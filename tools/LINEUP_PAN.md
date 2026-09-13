# lineup_pan.py

Joins N short model clips into one continuous left-to-right camera move, in the
style of a fashion-lookbook lineup.

## How it works

Every clip is laid out side by side on a very wide virtual canvas. The seams
between neighbouring clips are feathered across flat wall, where a dissolve is
invisible. A 9:16 window is then craned across that canvas at constant speed.

The part that makes it read as one take: each clip is **delayed** so it is
actually playing during the seconds its model is on screen, and freeze-padded
before and after. The freeze is off-screen, so nobody sees it.

## Measured from the reference

| | reference | `--style slow` | `--style punchy` |
|---|---|---|---|
| pan speed | 0.108 screen-widths/s | 0.122 | 0.243 |
| model centre-to-centre | ~6.0 s | ~6.2 s | ~3.1 s |
| time a model is on screen | ~13.5 s | 12.0 s | 6.0 s |
| total, 8 models | — | ~44 s | ~23 s |

A model is on screen far longer than they are the hero, which is why a 6 s clip
cannot cover a reference-speed pan on its own. `--style slow` gets the extra
seconds by ping-ponging each clip (forward, then reverse); `--style punchy`
instead pans twice as fast so one pass is enough.

## Usage

```bash
pip install imageio-ffmpeg pillow numpy     # only if ffmpeg isn't on PATH

# editorial, reference speed
python3 tools/lineup_pan.py clips/*.mp4 -o lineup.mp4 --style slow --match

# short social cut
python3 tools/lineup_pan.py clips/*.mp4 -o lineup.mp4 --style punchy --match
```

Clips are consumed in the order given, which is their left-to-right screen
order — so name them `01.mp4 … 08.mp4`.

## Preparing real clips

Generated clips rarely arrive ready to tile. Two problems show up every time,
and both have a flag:

**Wall lighting disagrees between clips.** Each clip carries its own horizontal
falloff, and the directions often oppose each other — one brightens to the
right, the next darkens. Tiled, that puts a bright centre against a dark edge
and draws a hard vertical seam down the backdrop. `--flatten` samples the wall
above the models' heads, fits a curve per channel, and divides it out,
normalising everything to one shared flat level. It fixes gradient, exposure
and colour cast at once, and supersedes `--match`. Use it by default.

**A clip opens with the model still walking into position.** In a lineup every
model has to sit at the same distance, so a clip whose model grows 10-17% over
its run will visibly swell as it crosses frame. Measure where the scale settles,
drop that much off the head with `--trim`, and the remainder is retimed back up
to a common length so trimming one clip does not force the whole pan to hurry.

```bash
python3 tools/lineup_pan.py clips/*.mp4 -o lineup.mp4 \
    --style slow --flatten --trim 0,1.0,0,1.75 \
    --model-width 0.62 --spacing 0.82
```

Measure `--model-width` off your own clips rather than trusting the default —
a model holding a jacket out, or standing with elbows out, is much wider than a
plain standing pose, and spacing has to open up to keep the blend seam off them.

## Options worth knowing

- `--flatten` — the one to reach for. See above.
- `--match` — weaker alternative to `--flatten`: matches each clip's overall
  wall tone to the first clip's, but cannot fix a gradient.
- `--trim` — seconds to drop off the head of each clip, comma separated, one
  value per clip.
- `--smooth` — optical-flow interpolation when retiming a trimmed clip back up
  to length. Slower, but no judder.
- `--spacing` (default `0.75`) — gap between model centres in screen widths.
  Lower packs models closer but pushes the feathered seam onto the model; the
  script warns when that happens.
- `--model-width` (default `0.46`) — how much of the frame the model fills.
  Drives both the spacing guard and the timing. Measure it off one of your own
  clips if the framing differs.
- `--phase` (default `0.25`) — where the ping-pong turnaround falls in a
  model's time on screen. At `0` it lands dead centre, which is exactly where a
  model un-doing their own motion is most visible.
- `--ease` — eases the move in and out instead of holding constant speed.
- `--duration` — force a total length. Only ever slows the pan down; the script
  clamps and warns if you ask for faster than the clips can cover.

## Preparing the source clips

The technique only disappears if the clips agree with each other:

- identical framing — same head height, same feet height, model centred
- identical wall, floor and lighting
- static or near-static camera in each clip (any built-in camera move fights
  the pan)
- subtle idle motion only; big gestures expose the ping-pong reversal
