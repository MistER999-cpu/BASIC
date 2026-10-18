#!/usr/bin/env node
/* Part 2 lookbook slide: steps src/lookbook/scene.html and encodes a
   motion-blurred MP4.

     node src/lookbook/render.mjs                        # full render
     node src/lookbook/render.mjs --stills 0.4,2.0,8.9   # quick stills to check framing

   Layers come from tools/part2_assets.py (campaign/part2/assets/). */
import { execFileSync } from 'node:child_process';
import { readFileSync, mkdirSync, rmSync } from 'node:fs';
import { resolve, join, dirname } from 'node:path';
import { pathToFileURL } from 'node:url';
import { launch } from '../browser.mjs';

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };

const W = 1080, H = 1920;
const FPS = +opt('--fps', 30), SUB = +opt('--sub', 8), DUR = +opt('--dur', 9.6);
const OUT = opt('--out', 'campaign/part2/lookbook.mp4');
const ASSETS = resolve('campaign/part2/assets');
const STILLS = opt('--stills');
// fraction of the frame interval the virtual shutter stays open: 0.5 is the
// film-standard 180-degree shutter (crisper than a full-frame smear)
const SHUTTER = +opt('--shutter', 0.5);

const manifest = JSON.parse(readFileSync(join(ASSETS, 'manifest.json'), 'utf8'));
const browser = await launch();
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
page.on('pageerror', e => { console.error('page error:', e.message); process.exitCode = 1; });
await page.goto(pathToFileURL(resolve('src/lookbook/scene.html')).href, { waitUntil: 'load' });
await page.evaluate(([m, base]) => window.build(m, base), [manifest, pathToFileURL(ASSETS).href + '/']);

if (STILLS) {
  const dir = 'out/lookbook-stills';
  mkdirSync(dir, { recursive: true });
  for (const s of STILLS.split(',').map(Number)) {
    await page.evaluate(t => window.setTime(t), s);
    await page.screenshot({ path: join(dir, `t_${s.toFixed(2)}.png`), animations: 'disabled' });
  }
  console.log(`  stills -> ${dir}/`);
} else {
  const sub = 'out/lookbook-sub';
  rmSync(sub, { recursive: true, force: true });
  mkdirSync(sub, { recursive: true });
  const total = Math.round(DUR * FPS) * SUB;
  // centre each frame's subframes on its timestamp so the blur is not lagged;
  // frame 0 is sampled exactly at t=0 so it matches part 1's last frame
  for (let i = 0; i < total; i++) {
    const f = Math.floor(i / SUB);
    const t = f === 0 ? 0 : (f + (((i % SUB) + 0.5) / SUB - 0.5) * SHUTTER) / FPS;
    await page.evaluate(tt => window.setTime(tt), t);
    await page.screenshot({ path: join(sub, `s_${String(i).padStart(6, '0')}.jpg`),
                            type: 'jpeg', quality: 95, animations: 'disabled' });
    if (i % 80 === 0) process.stdout.write(`\r  ${i}/${total}`);
  }
  process.stdout.write(`\r  ${total}/${total}\n`);
  mkdirSync(dirname(OUT), { recursive: true });
  const blur = SUB > 1 ? `tmix=frames=${SUB}:weights='${Array(SUB).fill(1).join(' ')}',` : '';
  execFileSync('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y',
    '-framerate', String(FPS * SUB), '-i', join(sub, 's_%06d.jpg'),
    '-vf', `${blur}select='not(mod(n\\,${SUB}))',setpts=N/(${FPS}*TB),format=yuv420p`,
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-profile:v', 'high',
    '-movflags', '+faststart', '-r', String(FPS), OUT], { stdio: 'inherit' });
  rmSync(sub, { recursive: true, force: true });
  console.log(`  done -> ${OUT}`);
}
await browser.close();
