/* Generates stand-in tank-top PNG/SVGs so the pipeline is runnable before the
   real product cutouts exist. Replace assets/products/* with your own
   transparent cutouts and delete this script. */
import { writeFileSync, mkdirSync } from 'node:fs';

const COLORS = [
  ['tank-01', 'Lilac',   '#b79ae8', '#9b7ad6'],
  ['tank-02', 'Cream',   '#f2e3c2', '#e0cda4'],
  ['tank-03', 'Sage',    '#8cc06a', '#6fa64e'],
  ['tank-04', 'Rust',    '#d8763a', '#bb5c26'],
  ['tank-05', 'Magenta', '#e2559b', '#c63b80'],
  ['tank-06', 'Ink',     '#2a2f3a', '#171b23'],
  ['tank-07', 'Tan',     '#d8b48c', '#bf9770'],
  ['tank-08', 'Violet',  '#8d6fe0', '#7254c9'],
];

const BODY = `M 100 28
  C 92 74, 78 140, 62 186
  L 58 476
  C 116 491, 244 491, 302 476
  L 298 186
  C 282 140, 268 74, 260 28
  L 230 34
  C 224 72, 206 100, 180 108
  C 154 100, 136 72, 130 34 Z`;

mkdirSync('assets/products', { recursive: true });

for (const [slug, name, light, dark] of COLORS) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 520" width="360" height="520">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0"   stop-color="${light}"/>
      <stop offset=".55" stop-color="${light}"/>
      <stop offset="1"   stop-color="${dark}"/>
    </linearGradient>
    <linearGradient id="sh" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0"    stop-color="#000" stop-opacity=".16"/>
      <stop offset=".18"  stop-color="#000" stop-opacity="0"/>
      <stop offset=".78"  stop-color="#000" stop-opacity="0"/>
      <stop offset="1"    stop-color="#000" stop-opacity=".20"/>
    </linearGradient>
    <clipPath id="c"><path d="${BODY}"/></clipPath>
  </defs>
  <path d="${BODY}" fill="url(#g)"/>
  <g clip-path="url(#c)">
    <rect x="0" y="0" width="360" height="520" fill="url(#sh)"/>
    <!-- soft drape folds -->
    <path d="M126 200 C 134 300, 126 400, 118 480" stroke="#000" stroke-opacity=".08" stroke-width="13" fill="none"/>
    <path d="M234 200 C 228 300, 236 400, 242 480" stroke="#000" stroke-opacity=".08" stroke-width="13" fill="none"/>
    <path d="M180 160 C 186 290, 176 400, 180 482" stroke="#fff" stroke-opacity=".11" stroke-width="17" fill="none"/>
    <!-- ribbed hem -->
    <rect x="50" y="452" width="260" height="30" fill="#000" fill-opacity=".09"/>
  </g>
  <path d="${BODY}" fill="none" stroke="${dark}" stroke-opacity=".55" stroke-width="2.5"/>
  <!-- neck + arm binding -->
  <path d="M 130 34 C 136 72, 154 100, 180 108 C 206 100, 224 72, 230 34"
        fill="none" stroke="#fff" stroke-opacity=".32" stroke-width="5"/>
  <path d="M 100 28 C 92 74, 78 140, 62 186" fill="none" stroke="#fff" stroke-opacity=".20" stroke-width="4"/>
  <path d="M 260 28 C 268 74, 282 140, 298 186" fill="none" stroke="#fff" stroke-opacity=".20" stroke-width="4"/>
</svg>`;
  writeFileSync(`assets/products/${slug}.svg`, svg);
  console.log(`  ${slug}.svg  ${name}`);
}
console.log(`\n${COLORS.length} placeholder tank tops written to assets/products/`);
