/* Full render: frames out of Chromium, then muxed with the synthesised audio. */
import { buildConfig, renderFrames } from './render.mjs';
import { spawn } from 'node:child_process';
import { existsSync, readdirSync, rmSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';

function ffmpegPath() {
  if (process.env.FFMPEG_PATH) return process.env.FFMPEG_PATH;
  // Playwright ships a cut-down ffmpeg with no libx264, so prefer a full build
  for (const p of [
    '/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2',
    '/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg',
  ]) if (existsSync(p)) return p;
  const root = '/opt/pw-browsers';
  if (existsSync(root))
    for (const d of readdirSync(root).filter(d => d.startsWith('ffmpeg')))
      for (const f of readdirSync(join(root, d)))
        if (f.startsWith('ffmpeg')) return join(root, d, f);
  return 'ffmpeg';
}

const run = (bin, args) => new Promise((res, rej) => {
  const p = spawn(bin, args, { stdio: ['ignore', 'inherit', 'inherit'] });
  p.on('error', rej);
  p.on('close', c => c === 0 ? res() : rej(new Error(`${bin} exited ${c}`)));
});

const cfg = buildConfig();
const frames = 'out/paint-frames', outFile = 'out/paint.mp4';
rmSync(frames, { recursive: true, force: true });
mkdirSync('out', { recursive: true });

console.log(`rendering ${Math.round(cfg.output.duration * cfg.output.fps)} frames `
          + `at ${cfg.output.width}x${cfg.output.height} ...`);
const t0 = Date.now();
await renderFrames({ cfg, outDir: frames,
  onProgress: (n, tot) => process.stdout.write(`\r  ${n}/${tot}`) });
console.log(`\n  frames done in ${((Date.now() - t0) / 1000).toFixed(0)}s`);

await run(ffmpegPath(), [
  '-y', '-v', 'error', '-stats',
  '-framerate', String(cfg.output.fps), '-i', join(frames, 'f_%05d.png'),
  '-i', 'out/paint.wav',
  '-c:v', 'libx264', '-preset', 'slow', '-crf', String(cfg.output.crf),
  '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-movflags', '+faststart',
  '-c:a', 'aac', '-b:a', '192k', '-shortest', outFile,
]);
console.log('wrote', outFile);
