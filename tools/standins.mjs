/* TEMPORARY stand-ins shaped like the real product (mock neck, cut-in
   shoulder, straight hem), rendered on a grey backdrop so they double as a
   test fixture for tools/cutout.py. Delete once the real cutouts are in. */
import { launch } from '../src/browser.mjs';
import { mkdirSync } from 'node:fs';

const COLORS = [
  ['white', '#fbf8f4', '#f2ece5', '#e6ded4'],
  ['black', '#24242a', '#141419', '#0c0c10'],
  ['brown', '#7a4f33', '#5e3a24', '#4a2c1a'],
];

const BODY = `M 252 62
  C 248 96, 248 116, 252 134
  L 176 164 C 156 172, 142 188, 138 210
  C 150 250, 162 300, 172 356
  C 168 440, 166 540, 168 636 L 172 744
  C 256 760, 344 760, 428 744 L 432 636
  C 434 540, 432 440, 428 356
  C 438 300, 450 250, 462 210
  C 458 188, 444 172, 424 164 L 348 134
  C 352 116, 352 96, 348 62
  C 330 50, 270 50, 252 62 Z`;

mkdirSync('out/standin', { recursive: true });
const browser = await launch();
const page = await browser.newPage({ viewport: { width: 900, height: 900 }, deviceScaleFactor: 1 });

for (const [name, light, mid, dark] of COLORS) {
  await page.setContent(`<style>html,body{margin:0}
    .bg{width:900px;height:900px;background:#bfbcba;display:flex;align-items:center;justify-content:center}</style>
    <div class="bg">
    <svg width="640" height="853" viewBox="0 0 600 800">
      <defs>
        <linearGradient id="g" x1="0" y1="0" x2="1" y2=".25">
          <stop offset="0" stop-color="${mid}"/><stop offset=".42" stop-color="${light}"/>
          <stop offset=".78" stop-color="${mid}"/><stop offset="1" stop-color="${dark}"/>
        </linearGradient>
        <clipPath id="c"><path d="${BODY}"/></clipPath>
        <filter id="sh" x="-15%" y="-15%" width="130%" height="130%">
          <feDropShadow dx="6" dy="10" stdDeviation="14" flood-color="#000" flood-opacity=".22"/>
        </filter>
      </defs>
      <g filter="url(#sh)">
        <path d="${BODY}" fill="url(#g)"/>
        <g clip-path="url(#c)">
          <path d="M232 150 C 244 320, 236 520, 228 740" stroke="${dark}" stroke-opacity=".30" stroke-width="16" fill="none"/>
          <path d="M368 150 C 358 320, 366 520, 374 740" stroke="${dark}" stroke-opacity=".30" stroke-width="16" fill="none"/>
          <path d="M300 170 C 310 340, 292 540, 300 742" stroke="#fff" stroke-opacity=".13" stroke-width="26" fill="none"/>
          <rect x="120" y="716" width="360" height="30" fill="${dark}" fill-opacity=".22"/>
        </g>
        <!-- mock-neck collar band + opening -->
        <path d="M 252 62 C 248 96, 248 116, 252 134 L 348 134
                 C 352 116, 352 96, 348 62 Z" fill="${mid}"/>
        <ellipse cx="300" cy="66" rx="48" ry="15" fill="${dark}"/>
        <ellipse cx="300" cy="70" rx="40" ry="11" fill="#000" fill-opacity=".45"/>
        <path d="M 252 62 C 270 50, 330 50, 348 62" fill="none" stroke="#fff" stroke-opacity=".16" stroke-width="4"/>
        <!-- hem stitch -->
        <path d="M 176 736 C 258 751, 342 751, 424 736" fill="none"
              stroke="#fff" stroke-opacity=".18" stroke-width="3" stroke-dasharray="9 7"/>
      </g>
    </svg></div>`, { waitUntil: 'load' });
  await page.screenshot({ path: `out/standin/${name}.jpg`, type: 'jpeg', quality: 95 });
  console.log(`  out/standin/${name}.jpg`);
}
await browser.close();
