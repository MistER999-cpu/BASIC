import numpy as np, json, os, subprocess, glob, shutil
from PIL import Image
from scipy import ndimage
FF='/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2'
picks=json.load(open('03_work/picks.json'))
TARGET_H=410; NF=48
shutil.rmtree('03_work/fig',ignore_errors=True); os.makedirs('03_work/fig')
meta={}
def bgmodel(a):                      # iterative, at quarter res then upscaled
    H,W,_=a.shape
    s=np.asarray(Image.fromarray(a.astype(np.uint8)).resize((W//4,H//4),Image.BILINEAR)).astype(np.float32)
    h,w_=s.shape[:2]
    wt=np.ones((h,w_),np.float32); wt[:,int(w_*.18):int(w_*.82)]=0.0
    for _ in range(3):
        num=np.dstack([ndimage.gaussian_filter(s[...,c]*wt,17.5) for c in range(3)])
        den=ndimage.gaussian_filter(wt,17.5)[...,None]+1e-6
        bm=num/den; wt=(np.abs(s-bm).max(2)<12).astype(np.float32)
    return np.asarray(Image.fromarray(bm.astype(np.uint8)).resize((W,H),Image.BILINEAR)).astype(np.float32)
for key,start in picks.items():
    m=key[1]
    tmp=f'03_work/tmp_{key}'; shutil.rmtree(tmp,ignore_errors=True); os.makedirs(tmp)
    subprocess.run([FF,'-y','-ss',str(start),'-i',f'02_models/model{m}/{key}.mp4','-frames:v',str(NF),
                    '-vf','scale=648:1152',f'{tmp}/%03d.png'],capture_output=True)
    fs=sorted(glob.glob(f'{tmp}/*.png'))
    a0=np.asarray(Image.open(fs[0]).convert('RGB')).astype(np.float32)
    bm=bgmodel(a0)
    alphas=[];rgbs=[]
    for f in fs:
        a=np.asarray(Image.open(f).convert('RGB')).astype(np.float32)
        d=np.abs(a-bm).max(2)
        lab,k=ndimage.label(ndimage.binary_closing(d>12,np.ones((5,5))))
        keep=set(lab[d>34]); keep.discard(0)
        fg=ndimage.binary_fill_holes(np.isin(lab,list(keep)))
        l2,k2=ndimage.label(fg)
        if k2: sz=ndimage.sum(fg,l2,range(1,k2+1)); fg=l2==(np.argmax(sz)+1)
        alphas.append(ndimage.gaussian_filter(ndimage.binary_erosion(fg,np.ones((3,3))).astype(np.float32),1.2))
        rgbs.append(a)
    A=np.array(alphas); union=A.max(0)>0.4
    ys,xs=np.where(union); y0,y1,x0,x1=ys.min(),ys.max(),xs.min(),xs.max()
    fy,fx=np.where(A[0]>0.4); h1=fy.max()-fy.min()
    k=TARGET_H/float(h1)
    ow,oh=max(1,int(round((x1-x0)*k))),max(1,int(round((y1-y0)*k)))
    for i,(a,al) in enumerate(zip(rgbs,alphas)):
        r=np.dstack([a,np.clip(al,0,1)*255]).astype(np.uint8)[y0:y1,x0:x1]
        Image.fromarray(r,'RGBA').resize((ow,oh),Image.LANCZOS).save(f'03_work/fig/{key}_{i:03d}.png')
    meta[key]={'w':ow,'h':oh}
    shutil.rmtree(tmp,ignore_errors=True)
    print(f"  {key:<10} {ow}x{oh}   (w={ow/1080*100:.1f}% of frame)")
json.dump(meta,open('03_work/fig_meta.json','w'),indent=1)
