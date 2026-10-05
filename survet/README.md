# survêt — vertical fast-cut ad

A 10 s, 1080×1920 ad for the tracksuit in its three colourways. The frame is split
into four vertical strips. Each strip whips in a new shot from above or below on a
staggered beat, so something changes roughly every 0.12 s. Over the strips, the
word **survêt** is set in a new typeface every 0.24 s, coloured in the tracksuit
colours. The ad runs sand → black → brown, then a fast cut mixing all three. It
ends on a card with one strip per colourway.

```
0.0 – 3.3   sand    strips drop in one by one, then cut every 0.48 s (staggered)
3.3 – 5.7   black   vertical wipe into the new colourway
5.7 – 8.1   brown
8.1 – 9.1   mix     all three colours, cuts every 0.17 s
9.1 – 10    end     4 strips close to 3, one colourway each; word + BASIC + swatches
```

## Render

```bash
npm install
npm run survet                                   # -> out/survet.mp4
npm run survet -- --preview 0.5,3.4,8.4,9.9      # stills -> out/survet-preview/
npm run survet -- --audio track.mp3 --audio-start 12.5   # with music
```

A full render takes a few minutes in headless Chromium. The vertical motion blur
is built up from many sub-instants for every frame of a whip. Use `--preview` to
check a change first.

## Shots

Shots go in `shots/sand/`, `shots/black/` and `shots/brown/`. Any image file
counts, whatever its name. The `ref-*` files are the product photos, cut in half,
and serve as stand-ins. Delete them once the real shots are in. A file with
`end` in its name is used for the end card. See [SHOTS.md](SHOTS.md) for the shot
list and prompts.

## Tuning (`config.json`)

- `text.mode`: `"contrast"` (default) colours the word in a different colourway
  from the strips underneath it (black over sand, sand over black and brown),
  so it stays readable. Use `"match"` to give the word the same colour as the
  section's tracksuit.
- `sections`: the start, end and cut spacing (`every`) for each part. `stagger`
  sets how far apart the strips' cuts are.
- `text.fontEvery`: how often the typeface changes. `fonts`: the list to cycle
  through, held in `fonts/` (Google Fonts, OFL/Apache).
- `framings`: zoom and crop presets that each cut picks from. They give the
  stand-ins variety. Real shots with their own close-ups need less of this.
- `cut.slide` / `cut.shutter`: whip length and motion-blur amount.
- `seed`: changes which shot and framing land where, while keeping the same
  structure.
