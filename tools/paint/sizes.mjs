/* Render and encode the spot at every delivery size. The scene contain-fits the
   window, so a squarer frame gets page colour at the sides rather than a
   sliced-off UI - no reframing or per-size layout needed. */
import { buildConfig, renderFrames } from '../../src/paint/render.mjs';
import { spawn } from 'node:child_process';
import { existsSync, rmSync } from 'node:fs';
import { join } from 'node:path';

const SIZES = { '9x16': [1080, 1920], '4x5': [1080, 1350], '1x1': [1080, 1080] };
const FF = ['/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2',
            '/usr/bin/ffmpeg'].find(existsSync) ?? 'ffmpeg';

const run = (b, a) => new Promise((res, rej) => {
  const p = spawn(b, a, { stdio: ['ignore', 'ignore', 'inherit'] });
  p.on('error', rej); p.on('close', c => c ? rej(new Error(`exit ${c}`)) : res());
});

const only = process.argv[2];
for (const [name, [w, h]] of Object.entries(SIZES)) {
  if (only && only !== 'all' && only !== name) continue;
  const cfg = buildConfig();
  cfg.output.width = w; cfg.output.height = h;
  const dir = `out/frames-${name}`, mp4 = `out/basic-paint-${name}.mp4`;
  rmSync(dir, { recursive: true, force: true });
  process.stdout.write(`${name} ${w}x${h}  `);
  const t0 = Date.now();
  await renderFrames({ cfg, outDir: dir,
    onProgress: (n, t) => process.stdout.write(`\r${name} ${w}x${h}  ${n}/${t}   `) });
  await run(FF, ['-y', '-v', 'error', '-framerate', String(cfg.output.fps),
    '-i', join(dir, 'f_%05d.png'), '-i', 'out/paint.wav',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', String(cfg.output.crf),
    '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-movflags', '+faststart',
    '-c:a', 'aac', '-b:a', '192k', '-shortest', mp4]);
  rmSync(dir, { recursive: true, force: true });   // 1.4GB a piece, not worth keeping
  console.log(`\r${name} ${w}x${h}  -> ${mp4}  (${((Date.now() - t0) / 1000).toFixed(0)}s)   `);
}
