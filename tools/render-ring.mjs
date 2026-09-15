#!/usr/bin/env node
/* Rotating word-ring: steps the 3D scene one frame at a time in headless
   Chromium, screenshots each, then encodes to H.264.

     node tools/render-ring.mjs --config ring.config.json --out out/ring.mp4

   The spin is a pure linear function of time - no easing, no per-frame drift -
   so the type advances by exactly the same angle every frame. */
import { launch } from '../src/browser.mjs';
import { execFileSync } from 'node:child_process';
import { readFileSync, existsSync, rmSync, mkdirSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { pathToFileURL } from 'node:url';

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const has = k => args.includes(k);

const cfgPath = opt('--config', 'ring.config.json');
const cfg = JSON.parse(readFileSync(cfgPath, 'utf8'));
const OUT = opt('--out', 'out/ring.mp4');
const SUB = 'out/ring-sub';

for (const key of ['plate', 'subject']) {
  if (!cfg[key]) continue;
  const abs = resolve(cfg[key]);
  if (!existsSync(abs)) throw new Error(`${key} not found: ${cfg[key]}`);
  cfg[key] = pathToFileURL(abs).href;
}

const { width: W, height: H, fps, duration } = cfg;
const total = Math.round(duration * fps);

rmSync(SUB, { recursive: true, force: true });
mkdirSync(SUB, { recursive: true });
mkdirSync('out', { recursive: true });

console.log(`[1/3] launching Chromium at ${W}x${H}`);
const browser = await launch();
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
await page.goto(pathToFileURL(resolve('src/ring-scene.html')).href, { waitUntil: 'load' });

const geom = await page.evaluate(c => window.build(c), cfg);
console.log(`      ${geom.glyphs} glyphs, font ${geom.fontSize.toFixed(1)}px, `
          + `circumference ${geom.circumference.toFixed(0)}px`);

// every bitmap decoded before the first capture, or frame 0 ships empty
await page.evaluate(() => Promise.all(
  [...document.images].filter(i => i.src).map(i => i.decode().catch(() => {}))
));

console.log(`[2/3] rendering ${total} frames`);
for (let i = 0; i < total; i++) {
  await page.evaluate(t => window.setTime(t), i / fps);
  await page.screenshot({
    path: join(SUB, `f_${String(i).padStart(5, '0')}.jpg`),
    type: 'jpeg', quality: 96,
  });
  if (i % 15 === 0) process.stdout.write(`\r      ${i}/${total}`);
}
process.stdout.write(`\r      ${total}/${total}\n`);
await browser.close();

console.log('[3/3] encoding');
execFileSync('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y',
  '-framerate', String(fps), '-i', join(SUB, 'f_%05d.jpg'),
  '-vf', 'format=yuv420p',
  '-c:v', 'libx264', '-preset', 'slow', '-crf', String(cfg.crf ?? 17),
  '-profile:v', 'high', '-level', '4.2', '-movflags', '+faststart',
  '-r', String(fps), OUT], { stdio: ['ignore', 'inherit', 'inherit'] });

if (!has('--keep')) rmSync(SUB, { recursive: true, force: true });
console.log(`done -> ${OUT}`);
