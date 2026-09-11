/* Renders a neutral studio plate (backdrop + torso) so the pipeline has
   something with real tonal variation to refract when no base video exists. */
import { launch } from '../src/browser.mjs';
import { readFileSync, mkdirSync } from 'node:fs';

const cfg = JSON.parse(readFileSync('config.json', 'utf8'));
const { width: W, height: H } = cfg.output;
const out = process.argv[2] || 'out/plate.png';
mkdirSync('out', { recursive: true });

const html = `<style>
  html,body{margin:0;background:#000}
  .w{position:relative;width:${W}px;height:${H}px;overflow:hidden;
     background:radial-gradient(120% 90% at 50% 28%, #e8e6e1 0%, #d3d0ca 52%, #b9b6af 100%);}
  .floor{position:absolute;left:0;right:0;bottom:0;height:26%;
     background:linear-gradient(180deg,rgba(0,0,0,0),rgba(0,0,0,.10));}
  svg{position:absolute;left:50%;top:16%;transform:translateX(-50%)}
</style>
<div class="w"><div class="floor"></div>
<svg width="${Math.round(W*0.62)}" height="${Math.round(H*0.78)}" viewBox="0 0 620 1500">
  <defs>
    <linearGradient id="sk" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#c9a68c"/><stop offset=".45" stop-color="#e6c3a6"/>
      <stop offset="1" stop-color="#bd9a80"/>
    </linearGradient>
    <linearGradient id="gm" x1="0" y1="0" x2="1" y2=".4">
      <stop offset="0" stop-color="#1b2733"/><stop offset=".5" stop-color="#2c3b4b"/>
      <stop offset="1" stop-color="#16202b"/>
    </linearGradient>
    <filter id="s"><feGaussianBlur stdDeviation="3"/></filter>
  </defs>
  <g filter="url(#s)">
    <ellipse cx="310" cy="150" rx="104" ry="132" fill="url(#sk)"/>
    <rect x="272" y="252" width="76" height="90" fill="#cfa98d"/>
    <path d="M120 350 C 210 306, 410 306, 500 350
             L 545 700 C 548 900, 540 1100, 534 1290
             L 86 1290 C 80 1100, 72 900, 75 700 Z" fill="url(#gm)"/>
    <path d="M120 350 C 96 520, 84 700, 86 900 L 30 900 C 26 690, 52 500, 96 366 Z" fill="url(#gm)"/>
    <path d="M500 350 C 524 520, 536 700, 534 900 L 590 900 C 594 690, 568 500, 524 366 Z" fill="url(#gm)"/>
    <path d="M240 352 C 268 420, 352 420, 380 352" fill="none" stroke="#0d1620" stroke-width="10" opacity=".55"/>
  </g>
</svg></div>`;

const browser = await launch();
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
await page.setContent(html, { waitUntil: 'load' });
await page.screenshot({ path: out, type: 'png' });
await browser.close();
console.log('  studio plate ->', out);
