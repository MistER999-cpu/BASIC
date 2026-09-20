import numpy as np, json, os, subprocess, glob, shutil
from PIL import Image
from scipy import ndimage
FF='/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2'
picks=json.load(open('03_work/picks.json'))
TARGET_H=418; NF=48; PLATE_REF=213.5
shutil.rmtree('03_work/fig',ignore_errors=True); os.makedirs('03_work/fig')
def bgmodel(a):
    H,W,_=a.shape
    s=np.asarray(Image.fromarray(a.astype(np.uint8)).resize((W//4,H//4),Image.BILINEAR)).astype(np.float32)
    h,w_=s.shape[:2]
    wt=np.ones((h,w_),np.float32); wt[:,int(w_*.18):int(w_*.82)]=0.0
    for _ in range(3):
        num=np.dstack([ndimage.gaussian_filter(s[...,c]*wt,17.5) for c in range(3)])
        bm=num/(ndimage.gaussian_filter(wt,17.5)[...,None]+1e-6)
        wt=(np.abs(s-bm).max(2)<12).astype(np.float32)
    return np.asarray(Image.fromarray(bm.astype(np.uint8)).resize((W,H),Image.BILINEAR)).astype(np.float32)
meta={}
for key,start in picks.items():
    m=key[1]; tmp=f'03_work/tmp_{key}'
    shutil.rmtree(tmp,ignore_errors=True); os.makedirs(tmp)
    subprocess.run([FF,'-y','-ss',str(start),'-i',f'02_models/model{m}/{key}.mp4','-frames:v',str(NF),
                    '-vf','scale=648:1152',f'{tmp}/%03d.png'],capture_output=True)
    fs=sorted(glob.glob(f'{tmp}/*.png'))
    a0=np.asarray(Image.open(fs[0]).convert('RGB')).astype(np.float32)
    bm=bgmodel(a0); clip_bg=bm.mean()
    g=float(np.clip((PLATE_REF/clip_bg)**0.8,1.0,1.32))     # midtone lift, keeps blacks
    lut=(255*(np.arange(256)/255.0)**(1.0/g)).astype(np.float32)
    rgbs=[];als=[]
    for f in fs:
        a=np.asarray(Image.open(f).convert('RGB')).astype(np.float32)
        d=np.abs(a-bm).max(2); sd=bm-a
        shadowy=(sd.min(2)>-4)&(sd.max(2)<50)&((sd.max(2)-sd.min(2))<10)   # achromatic soft darkening
        maybe=ndimage.binary_closing((d>12)&~shadowy,np.ones((5,5)))
        lab,k=ndimage.label(maybe); keep=set(lab[d>45]); keep.discard(0)
        fg=ndimage.binary_fill_holes(np.isin(lab,list(keep)))
        l2,k2=ndimage.label(fg)
        if k2: sz=ndimage.sum(fg,l2,range(1,k2+1)); fg=l2==(np.argmax(sz)+1)
        core=ndimage.binary_erosion(fg,np.ones((5,5)))                      # 2 px in
        al=np.clip(ndimage.gaussian_filter(core.astype(np.float32),1.0),0,1)
        w=core.astype(np.float32)                                           # pull interior colour outward
        fill=np.dstack([ndimage.gaussian_filter(a[...,c]*w,2.0) for c in range(3)])/(ndimage.gaussian_filter(w,2.0)[...,None]+1e-6)
        edge=(al<0.92)[...,None]
        a=np.where(edge,fill,a)
        rgbs.append(np.clip(lut[np.clip(a,0,255).astype(np.uint8)],0,255)); als.append(al)
    A=np.array(als); ys,xs=np.where(A.max(0)>0.4)
    y0,y1,x0,x1=ys.min(),ys.max(),xs.min(),xs.max()
    fy,_=np.where(A[0]>0.4); k=TARGET_H/float(fy.max()-fy.min())
    ow,oh=max(1,int(round((x1-x0)*k))),max(1,int(round((y1-y0)*k)))
    for i,(r,al) in enumerate(zip(rgbs,als)):
        q=np.dstack([r,al*255]).astype(np.uint8)[y0:y1,x0:x1]
        Image.fromarray(q,'RGBA').resize((ow,oh),Image.LANCZOS).save(f'03_work/fig/{key}_{i:03d}.png')
    meta[key]={'w':ow,'h':oh}
    shutil.rmtree(tmp,ignore_errors=True)
    print(f"  {key:<10} {ow}x{oh}  clip_bg={clip_bg:.0f}  gamma={g:.3f}")
json.dump(meta,open('03_work/fig_meta.json','w'),indent=1)
