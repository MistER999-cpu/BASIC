#!/usr/bin/env node
/* survêt fast-cut -> MP4 (or stills with --preview)

   node survet/render.mjs                         # -> out/survet.mp4
   node survet/render.mjs --preview 0.4,2,8.5,9.8 # -> out/survet-preview/*.png
   node survet/render.mjs --audio track.mp3 --audio-start 12.5
*/
import { spawn } from 'node:child_process';
import { readFileSync, readdirSync, existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { launch } from '../src/browser.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };

const cfg = JSON.parse(readFileSync(opt('--config', join(HERE, 'config.json')), 'utf8'));
const OUT = opt('--out', 'out/survet.mp4');
const { width: W, height: H, fps, duration, crf } = cfg.output;

/* ---- shots: every image in shots/<colour>/, whatever it is called ------- */
const shotsDir = resolve(opt('--shots', join(HERE, 'shots')));
cfg.shots = {};
let standins = 0, total = 0;
for (const colour of Object.keys(cfg.colours)) {
  const dir = join(shotsDir, colour);
  const files = existsSync(dir)
    ? readdirSync(dir).filter(f => /\.(jpe?g|png|webp)$/i.test(f)).sort()
    : [];
  if (!files.length) throw new Error(`no shots in ${dir}`);
  cfg.shots[colour] = files.map(f => ({ name: f, url: pathToFileURL(join(dir, f)).href }));
  standins += files.filter(f => f.startsWith('ref-')).length;
  total += files.length;
  console.log(`  ${colour.padEnd(6)} ${files.length} shot${files.length > 1 ? 's' : ''}`);
}
if (standins === total) {
  console.warn('  (stand-ins only: these are the reference photos, not the campaign shots)');
}
cfg.fonts = cfg.fonts.map(f => ({ ...f, url: pathToFileURL(join(HERE, 'fonts', f.file)).href }));

/* ---- page ---------------------------------------------------------------- */
const browser = await launch();
const page = await browser.newPage({ viewport: { width: W, height: H } });
page.on('pageerror', e => { console.error(e); process.exitCode = 1; });
await page.goto(pathToFileURL(join(HERE, 'scene.html')).href);
await page.evaluate(c => window.SURVET.load(c), cfg);

const frame = t => page.evaluate(t => window.SURVET.draw(t), t)
  .then(() => page.screenshot({ type: 'png', clip: { x: 0, y: 0, width: W, height: H } }));

/* ---- stills -------------------------------------------------------------- */
if (opt('--preview')) {
  const dir = 'out/survet-preview';
  mkdirSync(dir, { recursive: true });
  for (const t of opt('--preview').split(',').map(Number)) {
    const p = join(dir, `t${t.toFixed(2)}.png`);
    writeFileSync(p, await frame(t));
    console.log(`  ${p}`);
  }
  await browser.close();
  process.exit();
}

/* ---- video --------------------------------------------------------------- */
mkdirSync(dirname(OUT), { recursive: true });
const audio = opt('--audio');
const audioIn = audio
  ? ['-ss', opt('--audio-start', '0'), '-t', String(duration), '-i', audio]
  : [];
const audioOut = audio
  ? ['-map', '1:a:0', '-c:a', 'aac', '-b:a', '192k',
     '-af', `afade=t=out:st=${duration - 0.5}:d=0.5`]
  : ['-an'];

const ff = spawn('ffmpeg', [
  '-hide_banner', '-loglevel', 'error', '-y',
  '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'png', '-i', '-',
  ...audioIn,
  '-map', '0:v:0', ...audioOut,
  '-c:v', 'libx264', '-preset', 'slow', '-crf', String(crf),
  '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-movflags', '+faststart',
  '-t', String(duration), OUT,
], { stdio: ['pipe', 'inherit', 'inherit'] });
const done = new Promise((ok, fail) =>
  ff.on('close', code => code ? fail(new Error(`ffmpeg exited ${code}`)) : ok()));

const N = Math.round(duration * fps);
for (let f = 0; f < N; f++) {
  const png = await frame(f / fps);
  if (!ff.stdin.write(png)) await new Promise(r => ff.stdin.once('drain', r));
  process.stdout.write(`\r  frame ${f + 1}/${N}`);
}
ff.stdin.end();
await done;
await browser.close();
console.log(`\n  -> ${OUT}`);
