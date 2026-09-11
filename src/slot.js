/* Deterministic slot-reel renderer.
   The driver calls window.setTime(t) then screenshots — no rAF, no wall clock,
   so every frame is reproducible and a pass can be re-run identically.

   Each reel lands on its OWN target product (white / black / brown), not on a
   shared winner: the payoff here is showing the three colourways side by side. */

const S = {};

const clamp = (v,a,b) => v < a ? a : v > b ? b : v;
const inv   = (t,a,b) => clamp((t-a)/(b-a), 0, 1);

const easeInOutCubic = u => u < .5 ? 4*u*u*u : 1 - Math.pow(-2*u+2, 3)/2;

/* linear interpolation through a sampled track, clamped at both ends */
function sampleTrack(track, t, key) {
  if (t <= track[0].t) return track[0][key];
  const last = track[track.length - 1];
  if (t >= last.t) return last[key];
  let lo = 0, hi = track.length - 1;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (track[mid].t <= t) lo = mid; else hi = mid;
  }
  const a = track[lo], b = track[hi];
  const u = (t - a.t) / (b.t - a.t);
  return a[key] + (b[key] - a[key]) * u;
}

/* short decaying spike, for impacts */
const spike = (dt, dur) =>
  dt < 0 || dt > dur ? 0 : Math.pow(1 - dt / dur, 2.2);

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

  /* ---- per-reel light sweeps ---- */
  const sw = document.getElementById('sweeps');
  sw.innerHTML = '';
  S.sweeps = [];
  for (let r = 0; r < R; r++) {
    const col = document.createElement('div');
    col.className = 'sweep';
    const bar = document.createElement('i');
    col.appendChild(bar);
    sw.appendChild(col);
    S.sweeps.push(bar);
  }
  S.flash = document.getElementById('flash');

  /* ---- the mimed slot handle ---- */
  const L = cfg.lever;
  S.lever = null;
  if (L && L.hand && L.hand.length) {
    const svg = document.getElementById('lever');
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    const pv = L.pivotOverride ?? L.pivot;
    const px = pv.x * W, py = pv.y * H;
    const knobR = Math.round((L.knobR ?? 0.030) * W);

    const mount = document.getElementById('mount');
    mount.innerHTML =
      `<circle cx="${px}" cy="${py}" r="${knobR * 1.15}" fill="rgba(255,255,255,.10)"
               stroke="rgba(255,255,255,.42)" stroke-width="${Math.max(2, W/540)}"/>` +
      `<circle cx="${px}" cy="${py}" r="${knobR * 0.34}" fill="rgba(255,255,255,.30)"/>`;

    document.getElementById('rodOuter').setAttribute('stroke-width', Math.round(knobR * 0.62));
    document.getElementById('rodCore').setAttribute('stroke-width', Math.max(2, Math.round(knobR * 0.17)));
    for (const [id, r, sw2] of [['knobHalo', knobR * 1.75, 0],
                                ['knob', knobR, Math.max(2, W / 480)],
                                ['knobLip', knobR * 0.62, Math.max(1.5, W / 720)]]) {
      const el = document.getElementById(id);
      el.setAttribute('r', r);
      if (sw2) el.setAttribute('stroke-width', sw2);
    }
    S.lever = { g: document.getElementById('leverG'), px, py, knobR,
                hand: L.hand, W, H };
  }

  S.plate = document.getElementById('plate');
  S.panelEl = panel;
  return { panel: S.panel, reels: R, cellH, lever: !!S.lever };
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
  const panelAlpha = easeInOutCubic(inv(t, tl.panelIn[0], tl.panelIn[1]));

  /* --- impacts: the launch, then one per detent --- */
  const fx = S.cfg.fx ?? {};
  let flash = spike(t - tl.spinStart, fx.launchFlash ?? 0.34) * (fx.launchGain ?? 0.85);
  let shake = 0;
  S.reels.forEach((r, i) => {
    const dt = t - r.stop;
    flash = Math.max(flash, spike(dt, fx.stopFlash ?? 0.24) * (fx.stopGain ?? 0.5));
    shake += spike(dt, 0.20) * Math.sin(dt * 150) * (fx.shakePx ?? 5);
    /* light sweep runs down the cell that just landed */
    const su = inv(t, r.stop - 0.03, r.stop + (fx.sweepDur ?? 0.42));
    const bar = S.sweeps[i];
    bar.style.opacity = su > 0 && su < 1 ? (Math.sin(su * Math.PI) * 0.9).toFixed(3) : '0';
    bar.style.transform = `translateY(${(-50 + su * 190).toFixed(1)}%)`;
  });
  shake += spike(t - tl.spinStart, 0.22) * Math.sin((t - tl.spinStart) * 150) * (fx.shakePx ?? 5);

  S.flash.style.opacity = flash.toFixed(3);

  /* the glass charges while the handle is being pulled */
  const charge = S.cfg.lever
    ? easeInOutCubic(inv(t, tl.leverPull[0], tl.leverPull[1])) *
      (1 - easeInOutCubic(inv(t, tl.spinStart, tl.spinStart + 0.45)))
    : 0;
  S.panelEl.style.opacity = panelAlpha.toFixed(3);
  S.panelEl.style.transform = `translate(${shake.toFixed(2)}px, ${(shake * 0.35).toFixed(2)}px)`;
  S.panelEl.style.filter = charge > 0.002
    ? `brightness(${(1 + charge * 0.20).toFixed(3)})`
    : 'none';

  drawLever(t);
};

function drawLever(t) {
  const L = S.lever;
  if (!L) return;
  const tl = S.tl;

  /* visible from the reach until just after the handle springs back */
  const inA  = easeInOutCubic(inv(t, tl.leverIn[0], tl.leverIn[1]));
  const outA = easeInOutCubic(inv(t, tl.leverOut[0], tl.leverOut[1]));
  const a = inA * (1 - outA);
  L.g.style.opacity = a.toFixed(3);
  if (a < 0.004) return;

  /* Knob sits on the tracked hand, so the grip reads as real. The rod is drawn
     from the fitted pivot to wherever the knob is; its length varies by ~3%
     across the gesture, which is invisible on a glowing rod and much better
     than a rigid arm that drifts out of her hand. */
  let kx = sampleTrack(L.hand, t, 'x') * L.W;
  let ky = sampleTrack(L.hand, t, 'y') * L.H;

  /* after release the handle springs back up on its own, she has let go */
  const rel = inv(t, tl.leverOut[0], tl.leverOut[0] + 0.30);
  if (rel > 0) {
    const restX = sampleTrack(L.hand, tl.leverPull[0], 'x') * L.W;
    const restY = sampleTrack(L.hand, tl.leverPull[0], 'y') * L.H;
    const e = 1 - Math.pow(1 - rel, 3);
    kx += (restX - kx) * e;
    ky += (restY - ky) * e;
  }

  const d = `M ${L.px} ${L.py} L ${kx.toFixed(1)} ${ky.toFixed(1)}`;
  document.getElementById('rodOuter').setAttribute('d', d);
  document.getElementById('rodCore').setAttribute('d', d);
  for (const id of ['knob', 'knobHalo', 'knobLip']) {
    const el = document.getElementById(id);
    el.setAttribute('cx', kx.toFixed(1));
    el.setAttribute('cy', ky.toFixed(1));
  }
}

window.setPlate = function (src) {
  return new Promise(res => {
    const img = S.plate;
    img.onload  = () => res(true);
    img.onerror = () => res(false);
    img.src = src;
  });
};
