/* Frame driver for the paint-program spot. Steps scene.html to an exact time
   and screenshots it, so a render is reproducible frame for frame. */
import { launch } from '../browser.mjs';
import { readFileSync, mkdirSync, readdirSync, existsSync } from 'node:fs';
import { resolve, join, basename, extname } from 'node:path';
import { pathToFileURL } from 'node:url';

/* PNG header: width and height are the two big-endian u32 after the IHDR tag. */
function pngSize(p) {
  const b = readFileSync(p);
  return [b.readUInt32BE(16), b.readUInt32BE(20)];
}

function collect(dir) {
  const src = {}, size = {};
  for (const f of readdirSync(dir).filter(f => extname(f) === '.png')) {
    const k = basename(f, '.png');
    src[k] = pathToFileURL(resolve(join(dir, f))).href;
    size[k] = pngSize(join(dir, f));
  }
  return { src, size };
}

export function buildConfig(cfgPath = 'config.paint.json') {
  const cfg = JSON.parse(readFileSync(cfgPath, 'utf8'));
  const items = collect(cfg.items), reveals = collect(cfg.reveals);
  cfg.uiGeom = JSON.parse(readFileSync('tools/paint/ui.json', 'utf8'));
  cfg.uiSrc = pathToFileURL(resolve(cfg.uiGeom.src)).href;
  cfg.cursorSrc = pathToFileURL(resolve(join(cfg.ui, 'cursor-rest.png'))).href;
  cfg.itemSrc = items.src;   cfg.itemSize = items.size;
  cfg.revealSrc = reveals.src; cfg.revealSize = reveals.size;

  const missing = [];
  for (const k of cfg.displayOrder) if (!cfg.itemSrc[k]) missing.push(k);
  for (const r of cfg.rounds) if (!cfg.revealSrc[r.reveal]) missing.push(r.reveal);
  if (missing.length) throw new Error('missing assets: ' + missing.join(', '));
  return cfg;
}

export async function renderFrames({ cfg, outDir, times = null, onProgress }) {
  const { width: W, height: H, fps, duration } = cfg.output;
  mkdirSync(outDir, { recursive: true });

  const browser = await launch();
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  page.on('pageerror', e => { throw e; });
  await page.goto(pathToFileURL(resolve('src/paint/scene.html')).href, { waitUntil: 'load' });
  const geom = await page.evaluate(c => window.build(c), cfg);
  await page.evaluate(() => Promise.all(
    [...document.images].filter(i => i.src).map(i => i.decode().catch(() => {}))));

  const list = times ?? Array.from({ length: Math.round(duration * fps) }, (_, i) => i / fps);
  for (let i = 0; i < list.length; i++) {
    await page.evaluate(t => window.setTime(t), list[i]);
    await page.screenshot({
      path: join(outDir, `f_${String(i).padStart(5, '0')}.png`),
      type: 'png', animations: 'disabled',
    });
    if ((i + 1) % 25 === 0 || i === list.length - 1) onProgress?.(i + 1, list.length);
  }
  await browser.close();
  return { frames: list.length, geom };
}
