/* Rewrites config.json's product list from whatever is in assets/products/.
   Drop your tank-top cutouts in there (PNG with alpha, or SVG) and run:
     node tools/scan-products.mjs [dir]                                      */
import { readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const dir = process.argv[2] || 'assets/products';
const files = readdirSync(dir)
  .filter(f => /\.(png|svg|webp|jpe?g)$/i.test(f))
  .sort();

if (files.length < 2) {
  console.error(`Need at least 2 product images in ${dir}, found ${files.length}.`);
  process.exit(1);
}

const title = s => s.replace(/[-_]+/g, ' ').replace(/\b\w/g, c => c.toUpperCase()).trim();
const cfg = JSON.parse(readFileSync('config.json', 'utf8'));
cfg.products = files.map(f => ({
  src: join(dir, f),
  name: title(f.replace(/\.\w+$/, '').replace(/^tank[-_ ]?0?/i, '')) || f,
}));
if (cfg.winner >= cfg.products.length) cfg.winner = 0;

writeFileSync('config.json', JSON.stringify(cfg, null, 2));
console.log(`${files.length} products written to config.json:`);
cfg.products.forEach((p, i) =>
  console.log(`  [${i}]${i === cfg.winner ? ' *' : '  '} ${p.src}`));
console.log(`\nwinner = [${cfg.winner}] ${cfg.products[cfg.winner].name}` +
            `  (change with: node src/pipeline.mjs --winner N)`);
