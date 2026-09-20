import numpy as np, json, os, subprocess
from PIL import Image
OUT_W,OUT_H,FPS = 1080,1920,24
DUR=16.0; NFR=int(DUR*FPS)
GROUND=int(OUT_H*0.690)
SLOT_CX=[0.11,0.31,0.69,0.88]
SLOT_COL=['brown','cream','black','beige']      # colourway per slot
STAND_SEQ=[('brown',0,2),('black',2,6),('beige',6,10),('cream',10,14),('brown',14,16)]
MODEL_BLOCKS=[('1',0,4),('2',4,8),('1',8,12),('2',12,16)]
XF_M, XF_S = 0.8, 0.7
STAGGER=[0.0,0.30,0.60,0.90]

bg=np.asarray(Image.open('00_source/background.jpg').convert('RGB').resize((OUT_W,OUT_H),Image.LANCZOS)).astype(np.float32)
mask=np.load('03_work/stand_mask.npy'); alpha=np.load('03_work/stand_alpha.npy')
ys,xs=np.where(mask); y0,y1,x0,x1=ys.min(),ys.max()+1,xs.min(),xs.max()+1
SC=(0.20*OUT_W)/420.0
sw,sh=int(round((x1-x0)*SC)),int(round((y1-y0)*SC))
stands={}
for n in ('brown','black','beige','cream'):
    p=np.asarray(Image.open(f'01_plates/plate_{n}.jpg').convert('RGB')).astype(np.float32)
    r=np.dstack([p,np.clip(alpha,0,1)*255]).astype(np.uint8)[y0:y1,x0:x1]
    im=Image.fromarray(r,'RGBA').resize((sw,sh),Image.LANCZOS)
    a=np.asarray(im).astype(np.float32)
    stands[n]=(a[...,:3],a[...,3:4]/255.0)
SX=int(OUT_W*0.50-sw/2); SY=GROUND-sh+2
print(f"stand {sw}x{sh} at ({SX},{SY})  ground={GROUND}")

figs={}; fmeta=json.load(open('03_work/fig_meta.json'))
plate_ref=bg[int(OUT_H*.62):int(OUT_H*.76)].mean()
for k in fmeta:
    seq=[]
    for i in range(48):
        a=np.asarray(Image.open(f'03_work/fig/{k}_{i:03d}.png').convert('RGBA')).astype(np.float32)
        seq.append((a[...,:3],a[...,3:4]/255.0))
    # gentle exposure match to the plate
    r,al=seq[0]; m=al[...,0]>0.5
    gain=np.clip(1.0+0.45*((plate_ref/max(r[m].mean(),1))-1.0),0.94,1.10)
    figs[k]=[(np.clip(r*gain,0,255),al) for r,al in seq]
    print(f"  {k:<10} gain={gain:.3f}")

def blend(dst,rgb,al,px,py):
    h,w=al.shape[:2]
    x0,y0=max(px,0),max(py,0); x1,y1=min(px+w,OUT_W),min(py+h,OUT_H)
    if x1<=x0 or y1<=y0: return
    sx,sy=x0-px,y0-py
    a=al[sy:sy+(y1-y0), sx:sx+(x1-x0)]
    dst[y0:y1,x0:x1]=dst[y0:y1,x0:x1]*(1-a)+rgb[sy:sy+(y1-y0), sx:sx+(x1-x0)]*a

def ramp(t,edge,d):
    return float(np.clip((t-(edge-d/2))/d,0,1))
def tri(i,n=48):
    p=i%(2*n-2); return p if p<n else 2*n-2-p

os.makedirs('03_work/frames',exist_ok=True)
sh_y=np.arange(OUT_H)[:,None]; sh_x=np.arange(OUT_W)[None,:]
VIG=0.065*np.exp(-(((sh_x-OUT_W*0.5)/(sw*0.85))**2+((sh_y-(SY+sh*0.45))/(sh*0.62))**2))
for fi in range(NFR):
    t=fi/FPS
    fr=bg.copy()
    # contact shadows
    shadow=np.zeros((OUT_H,OUT_W),np.float32)
    for si,cx in enumerate(SLOT_CX):
        X=int(cx*OUT_W); rw,rh=95.0,17.0
        shadow+=0.13*np.exp(-(((sh_x-X)/rw)**2+((sh_y-GROUND+4)/rh)**2))
    X=int(OUT_W*0.5)
    shadow+=0.11*np.exp(-(((sh_x-X)/(sw*0.42))**2+((sh_y-GROUND+3)/15.0)**2))
    fr*= (1-np.clip(shadow,0,0.30))[...,None]
    fr*= (1-VIG)[...,None]
    # stand with colour crossfades
    layers=[]
    for n,a,b in STAND_SEQ:
        w=1.0
        if t<a-XF_S/2 or t>b+XF_S/2: continue
        if a>0: w*=ramp(t,a,XF_S)
        if b<DUR: w*=1-ramp(t,b,XF_S)
        if w>0.002: layers.append((n,w))
    tot=sum(w for _,w in layers) or 1.0
    for n,w in layers:
        rgb,al=stands[n]; blend(fr,rgb,al*(w/tot),SX,SY)
    # figures
    for si,(cx,col) in enumerate(zip(SLOT_CX,SLOT_COL)):
        st=STAGGER[si]
        act=[]
        for mm,a,b in MODEL_BLOCKS:
            a2,b2=a+st,b+st
            if t<a2-XF_M/2 or t>b2+XF_M/2: continue
            w=1.0
            if a2>0: w*=ramp(t,a2,XF_M)
            if b2<DUR: w*=1-ramp(t,b2,XF_M)
            if w>0.002: act.append((mm,w))
        if not act: act=[('1',1.0)]
        tot=sum(w for _,w in act) or 1.0
        for mm,w in act:
            seq=figs[f'm{mm}_{col}']; rgb,al=seq[tri(fi)]
            h,wd=al.shape[:2]
            blend(fr,rgb,al*(w/tot),int(cx*OUT_W-wd/2),GROUND-h)
    Image.fromarray(np.clip(fr,0,255).astype(np.uint8)).save(f'03_work/frames/{fi:04d}.png')
    if fi%48==0: print(f"   frame {fi}/{NFR}")
print("frames done")
