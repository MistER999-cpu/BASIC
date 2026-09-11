/* Renders a handful of key timeline moments to out/preview/ for eyeballing. */
import { launch, absolutizeAssets } from '../src/browser.mjs';
import { readFileSync, mkdirSync, readdirSync, existsSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { pathToFileURL } from 'node:url';

const cfg = JSON.parse(readFileSync('config.json','utf8'));
const times = (process.argv[2] || '0.5,2.0,3.2,5.0,7.0,8.2,9.0,10.0,10.5,12.0,14.0')
  .split(',').map(Number);
const plateDir = 'out/plate';
const plates = existsSync(plateDir)
  ? readdirSync(plateDir).filter(f=>/\.jpe?g$/i.test(f)).sort() : [];

const { width:W, height:H, fps } = cfg.output;
mkdirSync('out/preview', { recursive:true });

const browser = await launch();
const page = await browser.newPage({ viewport:{width:W,height:H}, deviceScaleFactor:1 });
page.on('console', m => console.log('  [page]', m.text()));
page.on('pageerror', e => console.log('  [pageerror]', e.message));

await page.goto(pathToFileURL(resolve('src/scene.html')).href, { waitUntil:'load' });
await page.evaluate(c => window.build(c), absolutizeAssets(cfg));
await page.evaluate(() => Promise.all([...document.images].filter(i=>i.src).map(i=>i.decode().catch(()=>{}))));

for (const t of times) {
  if (plates.length) {
    const pi = Math.min(plates.length-1, Math.round(t*fps));
    await page.evaluate(s => window.setPlate(s), pathToFileURL(resolve(join(plateDir, plates[pi]))).href);
  }
  await page.evaluate(tt => window.setTime(tt), t);
  const name = `t${String(t.toFixed(2)).replace('.','_')}.jpg`;
  await page.screenshot({ path: join('out/preview', name), type:'jpeg', quality:92 });
  console.log('  ->', name);
}
await browser.close();
