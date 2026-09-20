/* Playwright frame driver: steps the scene deterministically and screenshots
   each subframe. Accumulation motion blur happens later, in ffmpeg. */
import { launch, absolutizeAssets } from './browser.mjs';
import { readFileSync, mkdirSync, existsSync, readdirSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { pathToFileURL } from 'node:url';

export async function renderFrames({ cfg, plateDir, outDir, onProgress, scene = 'src/scene.html' }) {
  const { width:W, height:H, fps, subframes, duration } = cfg.output;
  mkdirSync(outDir, { recursive: true });

  const plates = existsSync(plateDir)
    ? readdirSync(plateDir).filter(f => /\.(jpe?g|png)$/i.test(f)).sort()
    : [];

  const browser = await launch();
  const page = await browser.newPage({
    viewport: { width: W, height: H },
    deviceScaleFactor: 1,
  });

  await page.goto(pathToFileURL(resolve(scene)).href, { waitUntil: 'load' });
  const geom = await page.evaluate(c => window.build(c, null), absolutizeAssets(cfg));

  // make sure every product image has decoded before the first capture
  await page.evaluate(() => Promise.all(
    [...document.images].filter(i => i.src).map(i => i.decode().catch(() => {}))
  ));

  const totalOut = Math.round(duration * fps);
  const totalSub = totalOut * subframes;
  const subDt    = 1 / (fps * subframes);

  let n = 0;
  for (let i = 0; i < totalSub; i++) {
    const t = i * subDt;

    if (plates.length) {
      // nearest plate frame for this instant
      const pi = Math.min(plates.length - 1, Math.round(t * fps));
      await page.evaluate(
        src => window.setPlate(src),
        pathToFileURL(resolve(join(plateDir, plates[pi]))).href
      );
    }

    await page.evaluate(tt => window.setTime(tt), t);
    await page.screenshot({
      path: join(outDir, `s_${String(i).padStart(6, '0')}.jpg`),
      type: 'jpeg',
      quality: 94,
      animations: 'disabled',
    });

    if (++n % 30 === 0 || i === totalSub - 1) onProgress?.(n, totalSub);
  }

  await browser.close();
  return { frames: totalSub, geom };
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const cfg = JSON.parse(readFileSync('config.json', 'utf8'));
  const r = await renderFrames({
    cfg,
    plateDir: 'out/plate',
    outDir: 'out/sub',
    onProgress: (n, t) =>
      process.stdout.write(`\r  rendering ${n}/${t} subframes (${(100*n/t).toFixed(0)}%)`),
  });
  console.log(`\n  done: ${r.frames} subframes`);
}
