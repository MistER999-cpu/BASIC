/* Deterministic slot-reel renderer.
   The driver calls window.setTime(t) then screenshots — no rAF, no wall clock,
   so every frame is reproducible and a pass can be re-run identically.

   Each reel lands on its OWN target product (white / black / brown), not on a
   shared winner: the payoff here is showing the three colourways side by side. */

const S = {};

const clamp = (v,a,b) => v < a ? a : v > b ? b : v;
const inv   = (t,a,b) => clamp((t-a)/(b-a), 0, 1);

const easeInOutCubic = u => u < .5 ? 4*u*u*u : 1 - Math.pow(-2*u+2, 3)/2;

/* damped clunk as the detent catches */
const settleWobble = (dt, amp = 0.085) =>
  dt < 0 ? 0 : amp * Math.exp(-11 * dt) * Math.sin(30 * dt);

window.build = function (cfg) {
  const { width:W, height:H } = cfg.output;
  const st = document.getElementById('stage');
  st.style.width  = W + 'px';
  st.style.height = H + 'px';

  S.cfg = cfg;
  S.W = W; S.H = H;
  S.P = cfg.products;
  S.N = cfg.products.length;
  S.tl = cfg.timeline;

  if (S.N < 2) throw new Error('need at least 2 products for a slot reel');

  const R = cfg.reels.count;
  const targets = cfg.reels.targets;
  const starts  = cfg.reels.starts;
  if (!Array.isArray(targets) || targets.length !== R)
    throw new Error(`reels.targets must list ${R} product indices`);
  if (targets.some(i => !Number.isInteger(i) || i < 0 || i >= S.N))
    throw new Error(`reels.targets out of range for ${S.N} products`);

  /* ---- panel geometry ---- */
  const p = cfg.panel;
  const pw = Math.round(W * p.w), ph = Math.round(H * p.h);
  const px = Math.round(W * p.cx - pw/2), py = Math.round(H * p.cy - ph/2);
  const panel = document.getElementById('panel');
  Object.assign(panel.style, { left:px+'px', top:py+'px', width:pw+'px', height:ph+'px' });

  const k = W / 1080;                                 // scale tuning values to output
  const root = document.documentElement.style;
  root.setProperty('--rad',  Math.round(p.radius * k) + 'px');
  root.setProperty('--blur', (p.blur * k).toFixed(1) + 'px');
  root.setProperty('--sat',  p.saturate);
  root.setProperty('--bri',  p.brightness);
  root.setProperty('--tint', p.tint);
  root.setProperty('--rimw', Math.max(2, Math.round(3 * k)) + 'px');

  document.getElementById('turb')
          .setAttribute('baseFrequency', `${p.liquidFreq} ${p.liquidFreq * 1.35}`);
  document.querySelector('#liquid feDisplacementMap')
          .setAttribute('scale', p.rimDisplace * k);

  S.panel = { x:px, y:py, w:pw, h:ph };

  /* ---- reels ---- */
  const cellH   = Math.round(ph * (cfg.reels.cellHeight ?? 0.82));
  const cellPad = (ph - cellH) / 2;                   // centres the detent
  const reelsEl = document.getElementById('reels');
  reelsEl.innerHTML = '';
  S.reels = [];

  const maxLoops = Math.max(...cfg.reels.loops.map(l => Math.floor(l)));
  const REPEATS  = 3 + maxLoops + 4;                  // park + spin + peek margin

  for (let r = 0; r < R; r++) {
    const reel  = document.createElement('div');
    reel.className = 'reel';
    const strip = document.createElement('div');
    strip.className = 'strip';

    for (let i = 0; i < REPEATS * S.N; i++) {
      const cell = document.createElement('div');
      cell.className = 'cell';
      cell.style.height = cellH + 'px';
      const img = document.createElement('img');
      img.src = S.P[i % S.N].src;
      img.style.transform = `scale(${cfg.reels.cellScale})`;
      cell.appendChild(img);
      strip.appendChild(cell);
    }
    reel.appendChild(strip);
    reelsEl.appendChild(reel);

    const startIdx = starts?.[r] ?? (targets[r] + 1) % S.N;
    /* Travel must be a whole number of cells AND congruent to this reel's own
       target offset, or it stops on the wrong colour. Fractional loop counts
       silently break that, so floor to whole revolutions first. */
    const loops  = Math.max(1, Math.floor(cfg.reels.loops[r] ?? 6));
    const offset = (((targets[r] - startIdx) % S.N) + S.N) % S.N;
    const travel = loops * S.N + offset;
    if ((startIdx + travel) % S.N !== targets[r]) {
      throw new Error(`reel ${r} would stop on ${(startIdx+travel)%S.N}, not ${targets[r]}`);
    }

    S.reels.push({
      strip, cellH, cellPad, startIdx, travel,
      base: 3 * S.N,                                  // park mid-strip
      stop: S.tl.reelStops[r],
    });
  }

  S.plate = document.getElementById('plate');
  S.panelEl = panel;
  return { panel: S.panel, reels: R, cellH };
};

/* Velocity profile rather than a position ease.
   A power-law ease crawls asymptotically into its stop. With only three
   colourways that means the final colour is sitting in the window a full
   second before the beat it is supposed to land on, and the stop reads as
   nothing happening. Decaying to a minimum creep speed instead keeps the reel
   visibly turning right up to the hit, where the detent catches it dead.

   Integral of v over the spin is exactly `travel`, so the reel still lands on
   its target cell to the pixel. */
function reelPos(r, t) {
  const t0 = S.tl.spinStart, t1 = r.stop;
  if (t <= t0) return r.base + r.startIdx;
  if (t >= t1) return r.base + r.startIdx + r.travel + settleWobble(t - t1);

  const dur = t1 - t0;
  const u = (t - t0) / dur;
  const k = S.cfg.reels.decel ?? 3;
  // creep is in cells/sec; convert to cells per unit-u, and never let it
  // exceed the travel itself on a very short spin
  const vmin = Math.min((S.cfg.reels.creep ?? 4) * dur, r.travel * 0.6);
  const v0 = (r.travel - vmin) * (k + 1);
  const p = v0 * (1 - Math.pow(1 - u, k + 1)) / (k + 1) + vmin * u;
  return r.base + r.startIdx + p;
}

window.setTime = function (t) {
  const tl = S.tl;

  for (const r of S.reels) {
    const pos = reelPos(r, t);
    r.strip.style.transform =
      `translate3d(0, ${(r.cellPad - pos * r.cellH).toFixed(2)}px, 0)`;
  }

  /* panel eases in on the intro hits, then stays for the rest of the clip */
  S.panelEl.style.opacity =
    easeInOutCubic(inv(t, tl.panelIn[0], tl.panelIn[1])).toFixed(3);
};

window.setPlate = function (src) {
  return new Promise(res => {
    const img = S.plate;
    img.onload  = () => res(true);
    img.onerror = () => res(false);
    img.src = src;
  });
};
