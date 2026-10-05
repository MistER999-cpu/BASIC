#!/usr/bin/env node
/* survêt fast-cut -> MP4 (or stills with --preview)

   node survet/render.mjs                          # -> out/survet.mp4
   node survet/render.mjs --preview 0.5,2,8.5,9.8  # -> out/survet-preview/*.png
   node survet/render.mjs --analyse                # print where it found the model in each shot
   node survet/render.mjs --jobs 3                 # browser pages rendering in parallel
*/
import { spawn } from 'node:child_process';
import { readFileSync, readdirSync, existsSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { launch } from '../src/browser.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, '..');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const has = k => args.includes(k);

const cfg = JSON.parse(readFileSync(opt('--config', join(HERE, 'config.json')), 'utf8'));
const OUT = opt('--out', 'out/survet.mp4');
const { width: W, height: H, fps, duration, crf } = cfg.output;
const fileUrl = p => pathToFileURL(resolve(ROOT, p)).href;

/* ---- shots: every image in shots/<colour>/, whatever it is called ------- */
const shotsDir = resolve(opt('--shots', join(HERE, 'shots')));
cfg.shots = {};
for (const colour of Object.keys(cfg.colours)) {
  const dir = join(shotsDir, colour);
  const files = existsSync(dir)
    ? readdirSync(dir).filter(f => /\.(jpe?g|png|webp)$/i.test(f)).sort()
    : [];
  if (!files.length) throw new Error(`no shots in ${dir}`);
  cfg.shots[colour] = files.map(f => ({ name: f, url: pathToFileURL(join(dir, f)).href }));
  console.log(`  ${colour.padEnd(6)} ${files.length} shots`);
}
cfg.fonts = cfg.fonts.map(f => ({ ...f, url: pathToFileURL(join(HERE, 'fonts', f.file)).href }));
cfg.end.logoUrl = fileUrl(cfg.end.logo);
cfg.end.fontUrl = pathToFileURL(join(HERE, 'fonts', cfg.end.font)).href;

/* ---- pages --------------------------------------------------------------- */
const browser = await launch();
async function openPage() {
  const page = await browser.newPage({ viewport: { width: W, height: H } });
  page.on('pageerror', e => { console.error(e); process.exitCode = 1; });
  page.on('console', m => { if (m.type() === 'error') console.error(m.text()); });
  await page.goto(pathToFileURL(join(HERE, 'scene.html')).href);
  const info = await page.evaluate(c => window.SURVET.load(c), cfg);
  return { page, info };
}
const shoot = (page, t) => page.evaluate(t => window.SURVET.draw(t), t)
  .then(() => page.screenshot({ type: 'png', clip: { x: 0, y: 0, width: W, height: H } }));

const first = await openPage();

if (has('--analyse')) {
  console.log(JSON.stringify(first.info, null, 1));
  await browser.close();
  process.exit();
}

/* ---- stills -------------------------------------------------------------- */
if (opt('--preview')) {
  const dir = 'out/survet-preview';
  mkdirSync(dir, { recursive: true });
  for (const t of opt('--preview').split(',').map(Number)) {
    const p = join(dir, `t${t.toFixed(2)}.png`);
    writeFileSync(p, await shoot(first.page, t));
    console.log(`  ${p}`);
  }
  await browser.close();
  process.exit();
}

/* ---- frames, in parallel pages ------------------------------------------ */
const N = Math.round(duration * fps);
const jobs = Math.max(1, +opt('--jobs', 3));
const frameDir = 'out/survet-frames';
rmSync(frameDir, { recursive: true, force: true });
mkdirSync(frameDir, { recursive: true });
const pages = [first.page];
for (let j = 1; j < jobs; j++) pages.push((await openPage()).page);

let done = 0;
await Promise.all(pages.map(async (page, j) => {
  for (let f = j; f < N; f += jobs) {
    writeFileSync(join(frameDir, `f_${String(f).padStart(5, '0')}.png`), await shoot(page, f / fps));
    done++;
    if (done % 10 === 0 || done === N) process.stdout.write(`\r  frame ${done}/${N}`);
  }
}));
await browser.close();
process.stdout.write('\n');

/* ---- encode -------------------------------------------------------------- */
mkdirSync(dirname(OUT), { recursive: true });
const A = cfg.audio;
const audio = A && !has('--mute') && existsSync(resolve(ROOT, A.file));
const ffArgs = [
  '-hide_banner', '-loglevel', 'error', '-y',
  '-framerate', String(fps), '-i', join(frameDir, 'f_%05d.png'),
  ...(audio ? ['-ss', String(A.start), '-t', String(duration), '-i', resolve(ROOT, A.file)] : []),
  '-map', '0:v:0',
  // a limiter keeps the drop from clipping once Instagram re-encodes it
  ...(audio ? ['-map', '1:a:0', '-c:a', 'aac', '-b:a', '256k', '-ar', '48000',
               '-af', `afade=t=in:st=0:d=${A.fadeIn},afade=t=out:st=${(duration - A.fadeOut).toFixed(3)}:d=${A.fadeOut},`
                    + 'alimiter=limit=0.89:level=false']
            : ['-an']),
  // RGB frames -> BT.709 video, tagged as such so players don't guess
  '-vf', 'scale=out_color_matrix=bt709:out_range=tv,format=yuv420p',
  '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
  '-c:v', 'libx264', '-preset', 'slow', '-crf', String(crf),
  '-profile:v', 'high', '-level', '4.2',
  '-r', String(fps), '-movflags', '+faststart',
  '-t', String(duration), OUT,
];
await new Promise((ok, fail) => spawn('ffmpeg', ffArgs, { stdio: 'inherit' })
  .on('close', code => code ? fail(new Error(`ffmpeg exited ${code}`)) : ok()));
if (!has('--keep')) rmSync(frameDir, { recursive: true, force: true });
console.log(`  -> ${OUT}${audio ? '' : ' (no audio)'}`);
