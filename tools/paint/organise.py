"""Give the matted stills stable slugs and record what belongs to which round."""
import glob, os, shutil, json, re

SLUG = {
    'Black_braided':        'belt-braided',
    'Black_leather_ankle':  'boots-black',
    'Brown_workwear':       'trousers-barrel',
    'Charcoal_grey_wide':   'trousers-charcoal',
    'Charcoal_pinstripe':   'jacket-bomber',
    'Gold_cuff':            'cuff-gold',
    'Grey_retro_trainers':  'trainers-grey',
    'Pinstripe_tailored':   'trousers-pinstripe',
    'Retro_trainers_disp':  'trainers-cream',
    'Suede_cropped':        'jacket-suede',
    'Suede_penny':          'loafers-tan',
    'Suede_trousers':       'trousers-flares',
    'Woman_modeling_layered_fashion_a': 'reveal-black',
    'Woman_modeling_layered_fashion_o': 'reveal-brown',
    'Woman_posing':         'reveal-white',
    'Woman_walking':        'reveal-beige',
}

def norm(src, dst):
    os.makedirs(dst, exist_ok=True)
    done = {}
    for p in sorted(glob.glob(f'{src}/*.png')):
        b = os.path.basename(p)
        hit = next((v for k, v in SLUG.items() if b.startswith(k)), None)
        if not hit:
            print(f'  ?? unmapped: {b}'); continue
        shutil.copy(p, f'{dst}/{hit}.png')
        done[hit] = f'{dst}/{hit}.png'
        print(f'  {hit:20s} <- {b[:44]}')
    return done

print('items');   items   = norm('assets/video/cut/items',   'assets/video/final/items')
print('reveals'); reveals = norm('assets/video/cut/reveals', 'assets/video/final/reveals')
missing = [v for v in SLUG.values() if v not in {**items, **reveals}]
print('missing:', missing or 'none')
json.dump({'items': items, 'reveals': reveals}, open('tools/paint/assets.json', 'w'), indent=1)
