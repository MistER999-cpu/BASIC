# The paint-program spot

A vertical film built as a fake Windows-95 paint program: a cursor picks
garments out of a tray, drops them onto the canvas as a flat-lay, hits `enter`,
and the flat-lay is replaced by a photograph of someone wearing that look.
Four rounds, one per tank colourway. There are no camera cuts anywhere — every
edit is a UI event inside one window, which is the whole trick.

## Rebuild

```bash
npm run paint:prep     # measure the window, matte the stills, build the timeline
npm run paint          # render + encode 1080x1920 -> out/paint.mp4
npm run paint:sizes    # 9:16, 4:5 and 1:1 -> out/basic-paint-*.mp4
npm run paint:preview -- "3.7,13.4,21.6"   # stills at those times, seconds
```

`paint:prep` is only needed when the source stills in `assets/video/` change.
After that, `paint:timeline` alone is enough to re-pace the film.

## Where things are decided

| What | Where |
|---|---|
| Pacing, round structure, which garment goes where | `tools/paint/timeline.py` |
| Canvas, tray, button and palette positions | `tools/paint/measure.py` → `ui.json` |
| Cut-outs | `tools/paint/matte.py` → `assets/video/final/` |
| How the four reveals are matched to one camera | `tools/paint/reveals.py` |
| Everything that moves | `src/paint/scene.html` |
| Clicks, whoosh, static | `tools/paint/sfx.py` |

## Two things worth knowing before changing them

**Reveals are scaled on head height, not bounding box.** Fitting a cut-out by
its bounding box lets a pose with an arm held out shrink the whole figure, and
lets a half-body plate blow up to meet a full-length one. Head height does not
move with the arms and is what the eye reads as camera distance, so the scene
scales on it, hangs each figure from the crown and centres the torso rather
than the bounding box.

**The scene is a pure function of time.** `setTime(t)` fully determines the
frame — no CSS transitions, no animation state, no `Math.random`. Frame N
always renders identically, which is what makes the render resumable and the
preview trustworthy. Keep it that way: any new motion has to be derived from
`t`, and any noise has to come from the seeded `rnd()`.
