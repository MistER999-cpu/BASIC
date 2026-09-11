/* Headless check: every reel must come to rest on the winning product.
   #spec and #rim sit above the reels, so hit-test through the
   whole stack rather than taking just the topmost element. */
import { launch, absolutizeAssets } from '../src/browser.mjs';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const cfg = JSON.parse(readFileSync('config.json', 'utf8'));
const browser = await launch();
const page = await browser.newPage({
  viewport: { width: cfg.output.width, height: cfg.output.height },
});
page.on('pageerror', e => { console.error('  PAGE ERROR:', e.message); process.exitCode = 1; });

await page.goto(pathToFileURL(resolve('src/scene.html')).href, { waitUntil: 'load' });
await page.evaluate(c => window.build(c), absolutizeAssets(cfg));

const settleAt = Math.max(...cfg.timeline.reelStops) + 0.4;
await page.evaluate(t => window.setTime(t), settleAt);

const landed = await page.evaluate(() =>
  [...document.querySelectorAll('.reel')].map(reel => {
    const r = reel.getBoundingClientRect();
    const stack = document.elementsFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    const img = stack.find(el => el.tagName === 'IMG' && reel.contains(el));
    return img ? img.src.split('/').pop() : null;
  })
);

/* each reel has its own target - the payoff is the three colourways together */
const want = cfg.reels.targets.map(i => cfg.products[i].src.split('/').pop());
let ok = true;
landed.forEach((got, i) => {
  const good = got === want[i];
  ok &&= good;
  console.log(`  reel ${i}: ${good ? 'OK  ' : 'FAIL'} -> ${got ?? '(nothing)'}`
            + `${good ? '' : `   expected ${want[i]}`}`);
});
const distinct = new Set(want).size === want.length;
if (!distinct) console.log('  WARNING: targets are not all distinct');
console.log(ok
  ? `\n  verified at t=${settleAt.toFixed(2)}s: ${want.join(' / ')}`
  : `\n  MISMATCH: expected ${want.join(' / ')}`);
if (!ok) process.exitCode = 1;
await browser.close();
