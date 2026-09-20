import numpy as np, os, glob
from PIL import Image, ImageDraw, ImageFont
W,H=1080,1920
F='03_work/fonts'
ROM=f'{F}/bodoni-moda-latin-400-normal.ttf'
ITA=f'{F}/bodoni-moda-latin-400-italic.ttf'
def tracked(draw,xy,txt,font,track,fill=(0,0,0,255),anchor_cx=True):
    ws=[draw.textlength(c,font=font) for c in txt]
    tot=sum(ws)+track*(len(txt)-1)
    x=xy[0]-tot/2 if anchor_cx else xy[0]
    for c,w in zip(txt,ws):
        draw.text((x,xy[1]),c,font=font,fill=fill,anchor='ls'); x+=w+track
    return tot
def fit(path,txt,target,track_frac):
    lo,hi=20,400
    for _ in range(40):
        mid=(lo+hi)/2
        f=ImageFont.truetype(path,int(mid))
        d=ImageDraw.Draw(Image.new('RGBA',(10,10)))
        w=sum(d.textlength(c,font=f) for c in txt)+track_frac*mid*(len(txt)-1)
        if w<target: lo=mid
        else: hi=mid
    return ImageFont.truetype(path,int(lo)), track_frac*lo

ov=Image.new('RGBA',(W,H),(0,0,0,0)); dr=ImageDraw.Draw(ov)
# logo
lg=Image.open('03_work/logo.png').convert('RGBA')
lw=int(W*0.320); lh=int(round(lw*lg.height/lg.width))
lg=lg.resize((lw,lh),Image.LANCZOS)
ly=int(H*0.058)
ov.alpha_composite(lg,((W-lw)//2,ly))
# headline + footer
f1,t1=fit(ROM,"Un seul pack",int(W*0.615),0.012)
f2,t2=fit(ITA,"plusieurs looks",int(W*0.660),0.004)
tracked(dr,(W/2,int(H*0.253)),"Un seul pack",f1,t1)
tracked(dr,(W/2,int(H*0.836)),"plusieurs looks",f2,t2)
ov.save('03_work/overlay.png')
print(f"logo {lw}x{lh} at y={ly} ({ly/H*100:.1f}%-{(ly+lh)/H*100:.1f}%)")
print(f"headline size={f1.size}  baseline {0.253*100:.1f}%")
print(f"footer   size={f2.size}  baseline {0.836*100:.1f}%")

O=np.asarray(ov).astype(np.float32); oa=O[...,3:4]/255.0; org=O[...,:3]
os.makedirs('03_work/final',exist_ok=True)
fs=sorted(glob.glob('03_work/frames2/*.png'))
for i,f in enumerate(fs):
    a=np.asarray(Image.open(f).convert('RGB')).astype(np.float32)
    Image.fromarray(np.clip(a*(1-oa)+org*oa,0,255).astype(np.uint8)).save(f'03_work/final/{i:04d}.png')
print(f"composited {len(fs)} frames")
