/* Resolves a usable Chromium. Prefers the full browser over headless_shell:
   SVG-filter backdrop-filter is better supported there. */
import { chromium } from 'playwright-core';
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

function findChrome() {
  if (process.env.CHROME_PATH && existsSync(process.env.CHROME_PATH)) return process.env.CHROME_PATH;
  const root = process.env.PLAYWRIGHT_BROWSERS_PATH || '/opt/pw-browsers';
  if (!existsSync(root)) return undefined;
  const dirs = readdirSync(root)
    .filter(d => /^chromium-\d+$/.test(d))
    .sort((a, b) => +b.split('-')[1] - +a.split('-')[1]);
  for (const d of dirs) {
    const p = join(root, d, 'chrome-linux', 'chrome');
    if (existsSync(p)) return p;
  }
  return undefined;
}

export const LAUNCH_ARGS = [
  '--headless=new',
  '--force-device-scale-factor=1',
  '--force-color-profile=srgb',
  '--hide-scrollbars',
  '--disable-lcd-text',
  '--disable-gpu-vsync',
  '--allow-file-access-from-files',
  '--enable-blink-features=CSSBackdropFilter',
  '--font-render-hinting=none',
];

export function launch(extra = {}) {
  const executablePath = findChrome();
  if (!executablePath) {
    throw new Error(
      'No Chromium found. Set CHROME_PATH, or run: npx playwright install chromium'
    );
  }
  return chromium.launch({ executablePath, args: LAUNCH_ARGS, ...extra });
}

/* Product src paths in config.json are repo-relative; the scene page lives in
   src/, so rewrite them to absolute file: URLs before handing cfg to the page. */
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

export function absolutizeAssets(cfg) {
  const out = structuredClone(cfg);
  /* the lever's fitted pivot and hand track live in their own file so the
     tracking step can be re-run without touching config.json */
  if (out.lever?.file) {
    const p = resolve(out.lever.file);
    if (!existsSync(p)) throw new Error(`lever track not found: ${out.lever.file}`);
    Object.assign(out.lever, JSON.parse(readFileSync(p, 'utf8')));
  }
  out.products = out.products.map(p => {
    if (/^(file|https?|data):/.test(p.src)) return p;
    const abs = resolve(p.src);
    if (!existsSync(abs)) throw new Error(`Product asset not found: ${p.src}`);
    return { ...p, src: pathToFileURL(abs).href };
  });
  return out;
}
