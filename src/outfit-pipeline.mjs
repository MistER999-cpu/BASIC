#!/usr/bin/env node
/* Outfit builder: garment cutouts -> rendered frames -> MP4.

   Much shorter than src/pipeline.mjs because the reference clip has no motion
   to reproduce. Every garment change is a single-frame cut and the arrows snap
   between two sizes, so there is nothing for subframe accumulation to blur and
   no base footage to composite over - just frames, straight to H.264. */
import { execFileSync } from 'node:child_process';
import { readFileSync, existsSync, rmSync, mkdirSync } from 'node:fs';
import { renderFrames } from './render.mjs';

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const has = k => args.includes(k);

const CFG = opt('--config', 'config.outfit.json');
const OUT = opt('--out', 'out/outfit.mp4');
const cfg = JSON.parse(readFileSync(CFG, 'utf8'));
const FF = process.env.FFMPEG || 'ffmpeg';
const ff = (...a) => execFileSync(FF, ['-hide_banner', '-loglevel', 'error', '-y', ...a],
                                  { stdio: ['ignore', 'inherit', 'inherit'] });

/* The scene scales each bottom by its own waistband, so it needs the
   measurements tools/bottoms.py took at matte time. Carrying them in
   config.json instead would mean a re-matte silently disagreeing with a
   hand-edited number. */
const man = JSON.parse(readFileSync('assets/bottoms/manifest.json', 'utf8'));
const byFile = new Map(man.map(m => [m.file, m]));
cfg.bottoms = cfg.bottoms.map(b => {
  const m = byFile.get(b.src);
  if (!m) throw new Error(`${b.src} is not in assets/bottoms/manifest.json - re-run tools/bottoms.py`);
  return { ...b, w: m.w, h: m.h, waist: m.waist };
});
const tops = JSON.parse(readFileSync('assets/tops/manifest.json', 'utf8'));
const byName = new Map(tops.map(m => [m.name, m]));
cfg.tops = cfg.tops.map(t => {
  const m = byName.get(t.name);
  if (!m) throw new Error(`${t.name} is not in assets/tops/manifest.json - re-run tools/tops.py`);
  return { ...t, w: m.w, h: m.h };
});

const { width: W, height: H, fps, crf } = cfg.output;
const T = cfg.timeline;
const cuts = 2 * cfg.bottoms.length - 1;
cfg.output.duration = +(T.openHold + (cuts - 1) * T.cadence + T.closeHold).toFixed(3);

console.log(`[1/3] ${cfg.tops.length} tops x ${cfg.bottoms.length} bottoms`
          + ` -> ${cuts} cuts, ${cuts + 1} states, ${cfg.output.duration}s`);

rmSync('out/sub', { recursive: true, force: true });
mkdirSync('out', { recursive: true });
console.log(`[2/3] rendering ${Math.round(cfg.output.duration * fps)} frames at ${W}x${H}`);
const { geom } = await renderFrames({
  cfg, plateDir: 'out/__none__', outDir: 'out/sub', scene: 'src/outfit.html',
  onProgress: (n, t) => process.stdout.write(`\r      ${n}/${t} (${(100 * n / t).toFixed(0)}%)`),
});
process.stdout.write('\n');

for (const b of geom.botBoxes) {
  console.log(`      ${b.name.padEnd(24)} ${String(b.w).padStart(4)}x${String(b.h).padStart(3)}`
            + (b.clamped ? '  (clamped to maxLen)' : ''));
}
console.log(`      search text fitted at ${geom.fontPx}px`);

console.log('[3/3] encoding');
ff('-framerate', String(fps), '-i', 'out/sub/s_%06d.jpg',
   '-vf', 'format=yuv420p',
   '-c:v', 'libx264', '-preset', 'slow', '-crf', String(crf),
   '-profile:v', 'high', '-level', '4.2', '-movflags', '+faststart',
   '-an', '-r', String(fps), OUT);

console.log(`      done -> ${OUT}`);
if (!has('--keep')) rmSync('out/sub', { recursive: true, force: true });
