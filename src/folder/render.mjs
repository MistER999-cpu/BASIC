#!/usr/bin/env node
/* Folder burst: steps src/folder/scene.html and encodes a motion-blurred MP4.

     node src/folder/render.mjs                         # full render
     node src/folder/render.mjs --stills 0.3,1.2,2.9    # quick stills to check framing

   Layers come from tools/folder_assets.py (campaign/folder/assets/). */
import { execFileSync } from 'node:child_process';
import { readFileSync, mkdirSync, rmSync } from 'node:fs';
import { resolve, join, dirname } from 'node:path';
import { pathToFileURL } from 'node:url';
import { launch } from '../browser.mjs';

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };

const W = 1080, H = 1920;
const FPS = +opt('--fps', 30), SUB = +opt('--sub', 8), DUR = +opt('--dur', 5.0);
const OUT = opt('--out', 'campaign/folder/folder-burst.mp4');
const ASSETS = resolve('campaign/folder/assets');
const STILLS = opt('--stills');

const manifest = JSON.parse(readFileSync(join(ASSETS, 'manifest.json'), 'utf8'));
const browser = await launch();
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
await page.goto(pathToFileURL(resolve('src/folder/scene.html')).href, { waitUntil: 'load' });
await page.evaluate(([m, base]) => window.build(m, base), [manifest, pathToFileURL(ASSETS).href + '/']);

if (STILLS) {
  const dir = 'out/folder-stills';
  mkdirSync(dir, { recursive: true });
  for (const s of STILLS.split(',').map(Number)) {
    await page.evaluate(t => window.setTime(t), s);
    await page.screenshot({ path: join(dir, `t_${s.toFixed(2)}.png`), animations: 'disabled' });
  }
  console.log(`  stills -> ${dir}/`);
} else {
  const sub = 'out/folder-sub';
  rmSync(sub, { recursive: true, force: true });
  mkdirSync(sub, { recursive: true });
  const total = Math.round(DUR * FPS) * SUB;
  // centre each frame's subframes on its timestamp so the blur is not lagged
  for (let i = 0; i < total; i++) {
    const t = (Math.floor(i / SUB) + ((i % SUB) + 0.5) / SUB - 0.5) / FPS;
    await page.evaluate(tt => window.setTime(tt), t);
    await page.screenshot({ path: join(sub, `s_${String(i).padStart(6, '0')}.jpg`),
                            type: 'jpeg', quality: 95, animations: 'disabled' });
    if (i % 60 === 0) process.stdout.write(`\r  ${i}/${total}`);
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
