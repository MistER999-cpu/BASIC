import numpy as np, json, os
from PIL import Image
from scipy import ndimage
OUT_W,OUT_H,FPS=1080,1920,24
DUR=10.0; NFR=int(DUR*FPS)
OS=1.035; BW,BH=int(round(OUT_W*OS)),int(round(OUT_H*OS))
GROUND=int(BH*0.690)
SLOT_CX=[0.115,0.315,0.685,0.865]
SLOT_COL=['brown','cream','black','beige']
SLOT_HK=[1.00,0.975,1.02,0.99]
COLS=['brown','black','beige','cream']
NSEG=12; SEG=DUR/NSEG; XF_S=0.18; XF_M=0.30
SW=[(0,[1.35,3.10,5.45,7.20,9.05]),(1,[2.20,4.05,6.30,8.40]),
    (0,[0.95,3.55,5.05,7.85,9.40]),(1,[1.80,4.60,6.75,8.15])]   # (start model idx, switch times)

bg=np.asarray(Image.open('00_source/background.jpg').convert('RGB').resize((BW,BH),Image.LANCZOS)).astype(np.float32)
# --- tight stand cutout ---
raw=np.asarray(Image.open('00_source/background.jpg').convert('RGB')).astype(np.float32)
u=np.zeros(raw.shape[:2],bool)
for n in ('brown','black','beige'):
    p=np.asarray(Image.open(f'01_plates/plate_{n}.jpg').convert('RGB')).astype(np.float32)
    mm=ndimage.binary_opening(np.abs(p-raw).max(2)>16,np.ones((3,3)))
    l,k=ndimage.label(mm); sz=ndimage.sum(mm,l,range(1,k+1)); u|=(l==(np.argmax(sz)+1))
u=ndimage.binary_fill_holes(ndimage.binary_closing(u,np.ones((9,9))))
u=ndimage.binary_dilation(u,np.ones((5,5)))
cr=np.asarray(Image.open('01_plates/plate_cream.jpg').convert('RGB')).astype(np.float32)
gm=np.abs(cr-raw).max(2)>16
print(f"tight mask: cream garment outside = {(gm&~u).sum()/max(gm.sum(),1)*100:.2f}%")
al=np.clip(ndimage.gaussian_filter(ndimage.binary_erosion(u,np.ones((3,3))).astype(np.float32),1.2),0,1)
ys,xs=np.where(u); y0,y1,x0,x1=ys.min(),ys.max()+1,xs.min(),xs.max()+1
SC=(0.20*BW)/420.0; sw,sh=int(round((x1-x0)*SC)),int(round((y1-y0)*SC))
stands={}
for n in COLS:
    p=np.asarray(Image.open(f'01_plates/plate_{n}.jpg').convert('RGB')).astype(np.float32)
    w=ndimage.binary_erosion(u,np.ones((3,3))).astype(np.float32)
    fill=np.dstack([ndimage.gaussian_filter(p[...,c]*w,2.0) for c in range(3)])/(ndimage.gaussian_filter(w,2.0)[...,None]+1e-6)
    p=np.where((al<0.92)[...,None],fill,p)
    q=np.dstack([p,al*255]).astype(np.uint8)[y0:y1,x0:x1]
    im=np.asarray(Image.fromarray(q,'RGBA').resize((sw,sh),Image.LANCZOS)).astype(np.float32)
    stands[n]=(im[...,:3],im[...,3:4]/255.0)
SX=int(BW*0.50-sw/2); SY=GROUND-sh+2
print(f"stand {sw}x{sh} @({SX},{SY})  ground={GROUND}  canvas {BW}x{BH}")

figs={}
for k in json.load(open('03_work/fig_meta.json')):
    hk=SLOT_HK[SLOT_COL.index(k.split('_')[1])]
    seq=[]
    for i in range(48):
        im=Image.open(f'03_work/fig/{k}_{i:03d}.png').convert('RGBA')
        if abs(hk-1)>1e-6:
            im=im.resize((max(1,int(im.width*hk)),max(1,int(im.height*hk))),Image.LANCZOS)
        a=np.asarray(im).astype(np.float32); seq.append((a[...,:3],a[...,3:4]/255.0))
    figs[k]=seq

def blend(dst,rgb,a,px,py):
    h,w=a.shape[:2]
    X0,Y0=max(px,0),max(py,0); X1,Y1=min(px+w,BW),min(py+h,BH)
    if X1<=X0 or Y1<=Y0: return
    sx,sy=X0-px,Y0-py; aa=a[sy:sy+(Y1-Y0),sx:sx+(X1-X0)]
    dst[Y0:Y1,X0:X1]=dst[Y0:Y1,X0:X1]*(1-aa)+rgb[sy:sy+(Y1-Y0),sx:sx+(X1-X0)]*aa
def ramp(t,e,d): return float(np.clip((t-(e-d/2))/d,0,1))
def tri(i,n=48):
    p=i%(2*n-2); return p if p<n else 2*n-2-p
def model_at(slot,t):
    s0,sws=SW[slot]; cur=s0; out=[]
    prev=0.0
    for j,st in enumerate(sws+[1e9]):
        nxt=(s0+j+1)%2
        if t<st-XF_M/2: return [(cur,1.0)]
        if t<=st+XF_M/2:
            w=ramp(t,st,XF_M); return [(cur,1-w),(nxt,w)]
        cur=nxt
    return [(cur,1.0)]

gx=np.arange(BW)[None,:]; gy=np.arange(BH)[:,None]
VIG=0.055*np.exp(-(((gx-BW*0.5)/(sw*0.90))**2+((gy-(SY+sh*0.45))/(sh*0.66))**2))
nx=(gx-BW/2)/(BW/2); ny=(gy-BH/2)/(BH/2)
GV=np.clip(0.085*(nx**2+ny**2)**1.15,0,0.16)
os.makedirs('03_work/frames2',exist_ok=True)
rng=np.random.default_rng(7)
for fi in range(NFR):
    t=fi/FPS; fr=bg.copy()
    sh_acc=np.zeros((BH,BW),np.float32)
    for si,cx in enumerate(SLOT_CX):
        col=SLOT_COL[si]
        wmax=max(figs[f'm{m+1}_{col}'][0][1].shape[1] for m in (0,1))
        X=cx*BW
        sh_acc+=0.20*np.exp(-(((gx-X)/(wmax*0.30))**2+((gy-GROUND+3)/11.0)**2))
        sh_acc+=0.09*np.exp(-(((gx-X)/(wmax*0.72))**2+((gy-GROUND+2)/26.0)**2))
    sh_acc+=0.17*np.exp(-(((gx-BW*0.5)/(sw*0.34))**2+((gy-GROUND+2)/12.0)**2))
    sh_acc+=0.08*np.exp(-(((gx-BW*0.5)/(sw*0.80))**2+((gy-GROUND+2)/28.0)**2))
    fr*=(1-np.clip(sh_acc,0,0.34))[...,None]
    seg=[]
    for s in range(NSEG):
        a,b=s*SEG,(s+1)*SEG
        if t<a-XF_S/2 or t>b+XF_S/2: continue
        w=1.0
        if a>0: w*=ramp(t,a,XF_S)
        if b<DUR: w*=1-ramp(t,b,XF_S)
        if w>0.002: seg.append((COLS[s%4],w))
    tot=sum(w for _,w in seg) or 1.0
    for n,w in seg:
        r,a=stands[n]; blend(fr,r,a*(w/tot),SX,SY)
    for si,(cx,col) in enumerate(zip(SLOT_CX,SLOT_COL)):
        act=model_at(si,t); tot=sum(w for _,w in act) or 1.0
        for mi,w in act:
            if w<=0.002: continue
            r,a=figs[f'm{mi+1}_{col}'][tri(fi)]
            h,wd=a.shape[:2]
            blend(fr,r,a*(w/tot),int(cx*BW-wd/2),GROUND-h)
    fr*=(1-VIG)[...,None]; fr*=(1-GV)[...,None]
    fr=np.clip((fr-128.0)*1.045+128.0+2.0,0,255)
    z=1.0+0.018*(fi/max(NFR-1,1))
    cw,ch=BW/z,BH/z; cx0,cy0=(BW-cw)/2,(BH-ch)/2
    out=Image.fromarray(fr.astype(np.uint8)).resize((OUT_W,OUT_H),Image.LANCZOS,
        box=(cx0,cy0,cx0+cw,cy0+ch))
    o=np.asarray(out).astype(np.float32)
    o=np.clip(o+rng.normal(0,2.1,(OUT_H,OUT_W,1)),0,255)
    Image.fromarray(o.astype(np.uint8)).save(f'03_work/frames2/{fi:04d}.png')
    if fi%60==0: print(f"   {fi}/{NFR}")
print("done")
