#!/usr/bin/env node
/* base video -> plate frames -> rendered subframes -> motion-blurred MP4 */
import { execFileSync } from 'node:child_process';
import { readFileSync, existsSync, rmSync, mkdirSync } from 'node:fs';
import { renderFrames } from './render.mjs';

const args = process.argv.slice(2);
const opt  = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i+1] : d; };
const has  = k => args.includes(k);

const cfg = JSON.parse(readFileSync(opt('--config', 'config.json'), 'utf8'));
if (opt('--base'))     cfg.base.video     = opt('--base');
if (opt('--targets')) cfg.reels.targets = opt('--targets').split(',').map(Number);
if (opt('--starts'))  cfg.reels.starts  = opt('--starts').split(',').map(Number);
const OUT = opt('--out', 'out/final.mp4');
const ff  = (...a) => execFileSync('ffmpeg', ['-hide_banner','-loglevel','error','-y',...a],
                                   { stdio: ['ignore','inherit','inherit'] });

const { width:W, height:H, fps, subframes, duration, crf } = cfg.output;

/* Placeholders must never reach a render unnoticed - they look plausible at
   reel size and that is exactly how a stand-in ships by mistake. */
if (existsSync('assets/products/.STANDIN')) {
  console.warn('\n  ####################################################################');
  console.warn('  #  PLACEHOLDER PRODUCTS - these are NOT the real garments.         #');
  console.warn('  #  Replace them:  python3 tools/cutout.py --outdir assets/products #');
  console.warn('  #      white=<file> black=<file> brown=<file>                      #');
  console.warn('  ####################################################################\n');
  if (!has('--allow-standins')) {
    throw new Error('refusing to render with placeholder products; pass --allow-standins to override');
  }
}

/* ---- 1. base plate ------------------------------------------------------ */
rmSync('out/plate', { recursive: true, force: true });
mkdirSync('out/plate', { recursive: true });
const hasBase = existsSync(cfg.base.video);

if (hasBase) {
  console.log(`[1/4] extracting plate frames from ${cfg.base.video}`);
  ff('-i', cfg.base.video, '-vf',
     `fps=${fps},scale=${W}:${H}:force_original_aspect_ratio=increase,crop=${W}:${H}`,
     '-q:v','2','-frames:v', String(Math.round(duration*fps)), 'out/plate/p_%05d.jpg');
} else {
  console.log(`[1/4] no base video at ${cfg.base.video} - generating a studio plate`);
  execFileSync('node', ['tools/make-plate.mjs', 'out/plate.png'], { stdio: 'inherit' });
  // gentle push-in so the fallback plate is not dead static
  ff('-loop', '1', '-i', 'out/plate.png', '-t', String(duration), '-r', String(fps),
     '-vf', `scale=${Math.round(W*1.06)}:-1,`
          + `zoompan=z='min(zoom+0.00035,1.06)':d=1:s=${W}x${H}:fps=${fps},`
          + `format=yuv420p`,
     '-q:v', '2', 'out/plate/p_%05d.jpg');
}

/* ---- 2. render ---------------------------------------------------------- */
console.log(`[2/4] rendering ${Math.round(duration*fps)}x${subframes} subframes at ${W}x${H}`);
rmSync('out/sub', { recursive: true, force: true });
await renderFrames({
  cfg, plateDir: 'out/plate', outDir: 'out/sub',
  onProgress: (n, t) => process.stdout.write(`\r      ${n}/${t} (${(100*n/t).toFixed(0)}%)`),
});
process.stdout.write('\n');

/* ---- 3. motion blur + encode ------------------------------------------- */
console.log(`[3/4] accumulating ${subframes}-subframe motion blur and encoding`);
const blur = subframes > 1
  ? `tmix=frames=${subframes}:weights='${Array(subframes).fill(1).join(' ')}',fps=${fps},`
  : '';
const audioIn = hasBase ? ['-i', cfg.base.video] : [];
const audioMap = hasBase
  ? ['-map','1:a:0?','-c:a','aac','-b:a','192k','-shortest']
  : ['-an'];

ff('-framerate', String(fps*subframes), '-i', 'out/sub/s_%06d.jpg',
   ...audioIn,
   '-vf', `${blur}format=yuv420p`,
   '-map','0:v:0', ...audioMap,
   '-c:v','libx264','-preset','slow','-crf',String(crf),
   '-profile:v','high','-level','4.2','-movflags','+faststart',
   '-r', String(fps), OUT);

/* ---- 4. report ---------------------------------------------------------- */
console.log(`[4/4] done -> ${OUT}`);
if (!has('--keep')) rmSync('out/sub', { recursive: true, force: true });
