import cv2, numpy as np
W,H=1080,1920
PAL={'cream':(210,221,242),'sand':(170,193,214),'clay':(120,147,194),
     'khaki':(110,172,178),'taupe':(106,130,155),'slate':(129,119,100),
     'peri':(227,185,169),'sky':(235,193,138),'dusty':(177,154,128),'base':(232,233,233)}
def plate(name,bands,ylo,yhi):
    img=np.full((H,W,3),PAL['base'],np.uint8); n=len(bands)
    for i,cname in enumerate(bands):
        y0=int(ylo+(yhi-ylo)*i/n); y1=int(ylo+(yhi-ylo)*(i+1)/n)
        cv2.rectangle(img,(0,y0),(W,y1),PAL[cname],-1)
    img=cv2.warpAffine(img,cv2.getRotationMatrix2D((W/2,H/2),15,1.3),(W,H),borderMode=cv2.BORDER_REPLICATE)
    cv2.imwrite(f"assets/_test/bg/{name}",cv2.GaussianBlur(img,(0,0),45))
plate("bg1.png",['cream','clay','khaki','sand','taupe'],int(H*.52),int(H*.95))
plate("bg2.png",['slate','peri','sky','dusty','khaki'],int(H*.18),int(H*.72))
plate("bg3.png",['slate','dusty','khaki','sand','clay'],int(H*.25),int(H*.85))
plate("bg4.png",['clay','khaki','taupe','slate','peri'],int(H*.35),int(H*.90))

def figure(name,label,tone,mode):
    """realistic proportions: far = full body, near = head-to-thigh crop"""
    cw,ch=1080,1990
    img=np.full((ch,cw,3),(60,180,60),np.uint8); cx=cw//2
    if mode=="far":                       # slim full figure, head to feet
        hw=int(cw*.085)
        cv2.circle(img,(cx,int(ch*.07)),hw,tone,-1)
        cv2.rectangle(img,(cx-int(cw*.085),int(ch*.12)),(cx+int(cw*.085),int(ch*.46)),tone,-1)
        cv2.rectangle(img,(cx-int(cw*.075),int(ch*.46)),(cx-int(cw*.008),int(ch*.96)),tone,-1)
        cv2.rectangle(img,(cx+int(cw*.008),int(ch*.46)),(cx+int(cw*.075),int(ch*.96)),tone,-1)
        cv2.rectangle(img,(cx-int(cw*.115),int(ch*.14)),(cx-int(cw*.085),int(ch*.45)),tone,-1)
        cv2.rectangle(img,(cx+int(cw*.085),int(ch*.14)),(cx+int(cw*.115),int(ch*.45)),tone,-1)
        sc=0.8
    else:                                  # head near top, body to bottom edge
        cv2.circle(img,(cx,int(ch*.10)),int(cw*.115),tone,-1)
        cv2.rectangle(img,(cx-int(cw*.175),int(ch*.20)),(cx+int(cw*.175),ch),tone,-1)
        cv2.rectangle(img,(cx-int(cw*.245),int(ch*.24)),(cx-int(cw*.175),int(ch*.78)),tone,-1)
        cv2.rectangle(img,(cx+int(cw*.175),int(ch*.24)),(cx+int(cw*.245),int(ch*.78)),tone,-1)
        sc=1.3
    for i,t in enumerate(label.split()):
        cv2.putText(img,t,(cx-int(cw*.10),int(ch*.36)+i*int(52*sc)),
                    cv2.FONT_HERSHEY_SIMPLEX,sc*0.75,(255,255,255),2)
    cv2.imwrite(f"assets/_test/models/{name}",img)
T={'black':(38,38,40),'brown':(52,74,102),'ivory':(226,233,241),'beige':(150,183,212)}
for n,l,t,m in [("A_near_black.png","A NEAR BLACK",T['black'],"near"),
                ("A_near_brown.png","A NEAR BROWN",T['brown'],"near"),
                ("B_near_ivory.png","B NEAR IVORY",T['ivory'],"near"),
                ("B_near_black.png","B NEAR BLACK",T['black'],"near"),
                ("A_far_beige.png","A FAR BEIGE",T['beige'],"far"),
                ("A_far_ivory.png","A FAR IVORY",T['ivory'],"far"),
                ("B_far_brown.png","B FAR BROWN",T['brown'],"far"),
                ("B_far_beige.png","B FAR BEIGE",T['beige'],"far")]:
    figure(n,l,t,m)
print("placeholders rebuilt")
