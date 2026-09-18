/* Stills at chosen times, for checking layout without a full render. */
import { buildConfig, renderFrames } from '../../src/paint/render.mjs';
const times = (process.argv[2] ?? '0.9,2.4,3.4,6.2,13.9,15.0,16.4,20.6,23.0')
  .split(',').map(Number);
const cfg = buildConfig();
const { geom } = await renderFrames({ cfg, outDir: 'out/paint-preview', times });
console.log('geom', JSON.stringify(geom));
console.log('wrote', times.length, 'stills ->  out/paint-preview');
