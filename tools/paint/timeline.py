"""Generate the shot list.

Pacing is expressed as relative gaps rather than absolute stamps so the whole
film can be tightened or loosened in one place; absolute times are derived.
The four brand chips are painted into the palette's bottom-left cells - the
Win95 palette has no brown or beige, so matching a colourway to an existing
swatch lands on salmon or navy. Authoring our own four is honest and says
"four colourways" before any model appears.
"""
import json, cv2, numpy as np

ui = json.load(open('tools/paint/ui.json'))
rev = json.load(open('tools/paint/reveals.json'))

# the palette's lower row, left to right; first four cells become brand chips
sw = sorted(ui['swatches'], key=lambda r: (r[1], r[0]))
ymid = (min(s[1] for s in sw) + max(s[1] for s in sw)) / 2
lower = sorted([s for s in sw if s[1] > ymid], key=lambda r: r[0])
brand = lower[:4]

TANK = {'beige': '#C3A793', 'white': '#EBE4E8', 'black': '#252327', 'brown': '#533429'}

ROUNDS = [
  dict(key='beige', reveal='reveal-beige', gap=0.62,
       picks=[('tank-beige','top'), ('trousers-flares','legs'), ('trainers-cream','feet')]),
  dict(key='white', reveal='reveal-white', gap=0.58,
       picks=[('tank-white','top'), ('trousers-pinstripe','legs'), ('trainers-grey','feet')]),
  dict(key='black', reveal='reveal-black', gap=0.52, revealFit='crop',
       picks=[('tank-black','topUnder'), ('trousers-charcoal','legs'),
              ('jacket-bomber','jacket'), ('boots-black','feet'), ('cuff-gold','wrist')]),
  dict(key='brown', reveal='reveal-brown', gap=0.50,
       picks=[('tank-brown','topUnder'), ('trousers-barrel','legs'),
              ('jacket-suede','jacket'), ('loafers-tan','feet'), ('belt-braided','belt')]),
]
SCALE = {'boots-black': 1.45, 'loafers-tan': 1.20, 'trainers-grey': 1.15, 'cuff-gold': 0.85}

LEAD, ENTER_GAP, HEART_GAP, REST_GAP, TAIL = 0.50, 0.72, 0.90, 0.80, 0.43

t, out = 0.20, []
for i, R in enumerate(ROUNDS):
    swatch_t = t
    picks = [{'item': it, 'place': pl, 't': round(t + LEAD + k * R['gap'], 2),
              **({'s': SCALE[it]} if it in SCALE else {})}
             for k, (it, pl) in enumerate(R['picks'])]
    enter = round(picks[-1]['t'] + ENTER_GAP, 2)
    heart = round(enter + HEART_GAP, 2)
    rest  = round(heart + REST_GAP, 2)
    r = {'key': R['key'], 'reveal': R['reveal'], 'tint': TANK[R['key']],
         'swatch': i, 'swatchT': round(swatch_t, 2), 'picks': picks,
         'enter': enter, 'heart': heart, 'restart': rest}
    if 'revealFit' in R: r['revealFit'] = R['revealFit']
    out.append(r)
    t = round(rest + 0.25 + TAIL, 2)

endcard = round(t + 0.25, 2)
cfg = json.load(open('config.paint.json'))
cfg['rounds'] = out
cfg['brandSwatches'] = [[int(v) for v in b] for b in brand]
cfg['brandColours'] = [TANK[R['key']] for R in ROUNDS]
cfg['endcard'] = {'t': endcard, 'text': 'BASIC', 'h': 0.062,
                  'items': [f'tank-{k}' for k in ('beige', 'white', 'black', 'brown')]}
cfg['revealMetrics'] = rev
cfg['anim'].update({'cursorLead': 0.22, 'pressDur': 0.10, 'popLag': 0.32,
                    'popDur': 0.42, 'glitchDur': 0.25, 'scrollDur': 0.28,
                    'headTarget': 0.142, 'pushIn': 0.018})
cfg['output']['duration'] = round(endcard + 1.95, 2)
json.dump(cfg, open('config.paint.json', 'w'), indent=2)

for r in out:
    ts = ' '.join('%5.2f' % p['t'] for p in r['picks'])
    print(f"{r['key']:6s} swatch {r['swatchT']:5.2f}  picks {ts}"
          f"   enter {r['enter']:5.2f}  heart {r['heart']:5.2f}  restart {r['restart']:5.2f}")
print(f"endcard {endcard}   duration {cfg['output']['duration']}s")
