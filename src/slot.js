/* Deterministic slot-reel renderer.
   The driver calls window.setTime(t) then screenshots — no rAF, no wall clock,
   so every frame is reproducible and the pass can be re-run identically. */

const S = {};                         // scene state, filled by build()

const clamp  = (v,a,b) => v < a ? a : v > b ? b : v;
const inv    = (t,a,b) => clamp((t-a)/(b-a), 0, 1);
const lerp   = (a,b,u) => a + (b-a)*u;

const easeOutQuart = u => 1 - Math.pow(1-u, 4);
const easeInOutCubic = u => u < .5 ? 4*u*u*u : 1 - Math.pow(-2*u+2, 3)/2;
const easeOutCubic = u => 1 - Math.pow(1-u, 3);

/* damped clunk the reel makes as the detent catches */
function settleWobble(dt, amp = 0.085) {
  if (dt < 0) return 0;
  return amp * Math.exp(-11 * dt) * Math.sin(30 * dt);
}

window.build = function (cfg, stage) {
  const { width:W, height:H } = cfg.output;
  const st = document.getElementById('stage');
  st.style.width = W + 'px';
  st.style.height = H + 'px';

  S.cfg = cfg;
  S.W = W; S.H = H;
  S.P = cfg.products;
  S.N = cfg.products.length;
  S.win = cfg.winner;
  S.tl = cfg.timeline;

  /* ---- panel geometry ---- */
  const p = cfg.panel;
  const pw = Math.round(W * p.w), ph = Math.round(H * p.h);
  const px = Math.round(W * p.cx - pw/2), py = Math.round(H * p.cy - ph/2);
  const panel = document.getElementById('panel');
  Object.assign(panel.style, {
    left: px+'px', top: py+'px', width: pw+'px', height: ph+'px'
  });
  const rad = Math.round(p.radius * (W/1080));
  document.documentElement.style.setProperty('--rad', rad+'px');
  document.documentElement.style.setProperty('--blur', (p.blur*(W/1080)).toFixed(1)+'px');
  document.documentElement.style.setProperty('--sat',  p.saturate);
  document.documentElement.style.setProperty('--bri',  p.brightness);
  document.documentElement.style.setProperty('--tint', p.tint);
  document.documentElement.style.setProperty('--rimw', Math.max(2, Math.round(3*(W/1080)))+'px');

  const turb = document.getElementById('turb');
  turb.setAttribute('baseFrequency', `${p.liquidFreq} ${p.liquidFreq*1.35}`);
  document.querySelector('#liquid feDisplacementMap')
          .setAttribute('scale', p.rimDisplace * (W/1080));

  S.panel = { x:px, y:py, w:pw, h:ph };

  /* ---- reels: each is a tall strip of every product, repeated ---- */
  if (S.N < 2) throw new Error('need at least 2 products for a slot reel');
  const R = cfg.reels.count;
  const cellH = Math.round(ph * (cfg.reels.cellHeight ?? 0.82));
  const cellPad = (ph - cellH) / 2;                  // centres the detent in the panel
  const reelsEl = document.getElementById('reels');
  reelsEl.innerHTML = '';
  S.reels = [];

  const maxLoops = Math.max(...cfg.reels.loops.map(l => Math.floor(l)));
  const REPEATS  = 3 + maxLoops + 4;                 // park + spin + peek margin
  for (let r = 0; r < R; r++) {
    const reel = document.createElement('div');
    reel.className = 'reel';
    const strip = document.createElement('div');
    strip.className = 'strip';

    for (let k = 0; k < REPEATS * S.N; k++) {
      const prod = S.P[k % S.N];
      const cell = document.createElement('div');
      cell.className = 'cell';
      cell.style.height = cellH + 'px';
      const img = document.createElement('img');
      img.src = prod.src;
      img.style.transform = `scale(${cfg.reels.cellScale})`;
      cell.appendChild(img);
      strip.appendChild(cell);
    }
    reel.appendChild(strip);
    reelsEl.appendChild(reel);

    /* start each reel showing a different product, like the reference */
    const startIdx = (S.win + 1 + r * 3) % S.N;
    /* Travel must be a whole number of cells AND congruent to the winner
       offset mod N, or the reel stops on the wrong product. Fractional loop
       counts silently break that, so floor to whole revolutions first. */
    const loops    = Math.max(1, Math.floor(cfg.reels.loops[r] ?? 6));
    const offset   = (((S.win - startIdx) % S.N) + S.N) % S.N;
    const travel   = loops * S.N + offset;
    if ((startIdx + travel) % S.N !== S.win) {
      throw new Error(`reel ${r} would stop on ${(startIdx+travel)%S.N}, not ${S.win}`);
    }

    S.reels.push({
      strip, cellH, cellPad,
      base: 3 * S.N,                                  // park in the middle of the strip
      startIdx, travel,
      stop: S.tl.reelStops[r] ?? (7 + r)
    });
  }

  /* ---- hero ---- */
  S.heroEl = document.getElementById('hero');
  S.heroEl.querySelector('img').src = S.P[S.win].src;
  const hw = Math.round(W * (cfg.hero?.w ?? 0.46));
  const hh = Math.round(hw * (520/360));
  Object.assign(S.heroEl.style, { width:hw+'px', height:hh+'px', marginLeft:(-hw/2)+'px' });
  S.hero = { w:hw, h:hh };

  /* ---- wordmark / packshot / endcard ---- */
  const wm = document.getElementById('wordmark');
  wm.textContent = cfg.brand.wordmark;
  wm.style.fontSize = Math.round(W * 0.058) + 'px';
  wm.style.letterSpacing = (cfg.brand.wordmarkLetterSpacing) + 'em';
  wm.style.textIndent = (cfg.brand.wordmarkLetterSpacing) + 'em';

  document.querySelector('#packshot img').src = S.P[S.win].src;
  const ec = document.getElementById('endcard');
  ec.style.background = cfg.brand.endCardBg;
  const ecs = ec.querySelector('span');
  ecs.textContent = cfg.brand.wordmark;
  ecs.style.color = cfg.brand.endCardFg;
  ecs.style.fontSize = Math.round(W * 0.052) + 'px';
  ecs.style.letterSpacing = (cfg.brand.wordmarkLetterSpacing) + 'em';
  ecs.style.textIndent = (cfg.brand.wordmarkLetterSpacing) + 'em';

  S.plate = document.getElementById('plate');
  return { panel: S.panel, reels: R };
};

/* reel position in cells at time t */
function reelPos(r, t) {
  const t0 = S.tl.spinStart, t1 = r.stop;
  let u = inv(t, t0, t1);
  let p = r.travel * easeOutQuart(u);
  if (t > t1) p = r.travel + settleWobble(t - t1);
  return r.base + r.startIdx + p;
}

window.setTime = function (t) {
  const tl = S.tl, W = S.W, H = S.H;

  /* --- reels --- */
  for (const r of S.reels) {
    const pos = reelPos(r, t);
    r.strip.style.transform =
      `translate3d(0, ${(r.cellPad - pos * r.cellH).toFixed(2)}px, 0)`;
  }

  /* --- wordmark fades out as the hand arrives --- */
  const wmU = inv(t, tl.wordmarkOut[0], tl.wordmarkOut[1]);
  const wm = document.getElementById('wordmark');
  wm.style.opacity = (1 - easeInOutCubic(wmU)).toFixed(3);

  /* --- glass panel dissolves after the jackpot --- */
  const panel = document.getElementById('panel');
  const pu = inv(t, tl.panelOut[0], tl.panelOut[1]);
  const pe = easeInOutCubic(pu);
  panel.style.opacity = (1 - pe).toFixed(3);
  /* glass relaxes: blur and tint drop away as it evaporates */
  const p = S.cfg.panel;
  document.documentElement.style.setProperty('--blur', (p.blur*(W/1080)*(1-pe)).toFixed(1)+'px');
  document.documentElement.style.setProperty('--tint', (p.tint*(1-pe)).toFixed(4));

  /* --- hero: winning product grows out of the centre cell --- */
  const hu = inv(t, tl.heroIn[0], tl.heroIn[1]);
  const he = easeOutCubic(hu);
  /* start matching the centre cell exactly, end at hero size */
  const cellW = S.panel.w / S.cfg.reels.count;
  const s0 = (cellW * S.cfg.reels.cellScale) / S.hero.w;
  const scale = lerp(s0, 1, he);
  const y0 = S.panel.y + S.panel.h/2;
  const y1 = H * (S.cfg.hero?.cy ?? 0.552);
  const cy = lerp(y0, y1, he);
  /* the hero has to leave before the packshot arrives, or the two sizes
     cross-dissolve through each other and ghost */
  const heroOut = easeInOutCubic(inv(t, tl.heroOut[0], tl.heroOut[1]));
  S.heroEl.style.opacity = (hu > 0 ? 1 - heroOut : 0).toFixed(3);
  S.heroEl.style.transform =
    `translateY(${(cy - S.hero.h/2 - H/2).toFixed(2)}px) scale(${scale.toFixed(4)})`;

  /* --- packshot (white studio card) --- */
  const ps = document.getElementById('packshot');
  const psIn  = inv(t, tl.packshot[0], tl.packshot[0] + 0.30);
  const psOut = inv(t, tl.packshot[1] - 0.25, tl.packshot[1]);
  ps.style.opacity = (easeInOutCubic(psIn) * (1 - easeInOutCubic(psOut))).toFixed(3);

  /* --- end card --- */
  const ec = document.getElementById('endcard');
  ec.style.opacity = easeInOutCubic(inv(t, tl.endCard[0] - 0.25, tl.endCard[0] + 0.20)).toFixed(3);

  /* --- base plate hides once we leave live action --- */
  S.plate.style.opacity = (1 - easeInOutCubic(inv(t, tl.heroHold, tl.heroOut[1]))).toFixed(3);
  document.getElementById('stage').style.background =
    t > tl.heroHold ? '#ffffff' : '#000000';
};

window.setPlate = function (src) {
  return new Promise(res => {
    const img = S.plate;
    img.onload = () => res(true);
    img.onerror = () => res(false);
    img.src = src;
  });
};
