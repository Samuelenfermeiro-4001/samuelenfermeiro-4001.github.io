"""Reconstroi a moldura de story a partir da arte de origem do designer."""
from PIL import Image, ImageFilter
import os, math

D=os.path.expanduser("~/Downloads/")
ORIG=D+"WhatsApp Image 2026-08-25 at 11.06.56.jpeg"
CX,CY,R=449.9,647.4,451.3           # circulo do texto em arco
AD0,AD1=math.radians(-118.06),math.radians(-117.06)   # casa do "1" errado
DELTA=math.radians(1.56)            # deslocamento ate o "7" de 437
RA,RB=437.0,466.0

im=Image.open(ORIG).convert("RGB"); W,H=im.size; px=im.load()
def amostra(fx,fy):
    x0,y0=int(math.floor(fx)),int(math.floor(fy)); dx,dy=fx-x0,fy-y0
    o=[0.0,0.0,0.0]
    for j in (0,1):
        for i in (0,1):
            w=(dx if i else 1-dx)*(dy if j else 1-dy)
            p=px[min(max(x0+i,0),W-1),min(max(y0+j,0),H-1)]
            for k in range(3): o[k]+=w*p[k]
    return o

# ---- 1) CNPJ: 68.437.165 -> 68.437.765 ----------------------------------
troca={}
import itertools
cantos=[(CX+r*math.cos(a), CY+r*math.sin(a)) for r in (RA,RB) for a in (AD0,AD1)]
BX0=int(min(c[0] for c in cantos))-3; BX1=int(max(c[0] for c in cantos))+4
BY0=int(min(c[1] for c in cantos))-3; BY1=int(max(c[1] for c in cantos))+4
for Y in range(BY0,BY1):
    for X in range(BX0,BX1):
        if not (0<=X<W and 0<=Y<H): continue
        dx=X+0.5-CX; dy=Y+0.5-CY
        rr=math.hypot(dx,dy); a=math.atan2(dy,dx)
        if not (AD0<=a<=AD1 and RA<=rr<=RB): continue
        a2=a-DELTA
        troca[(X,Y)]=tuple(int(round(v)) for v in amostra(CX+rr*math.cos(a2), CY+rr*math.sin(a2)))
for k,v in troca.items(): px[k[0],k[1]]=v
print("CNPJ: %d px trocados no arco"%len(troca))

# ---- 2) recorte ----------------------------------------------------------
def quente(p):   # o fundo do lugar da foto e levemente quente; a camisa e fria
    r,g,b=p
    return min(p)>=200 and max(p)<=253 and (r-b)>=1 and (r-g)<=6 and abs(g-b)<=6
def flood(pred):
    v=bytearray(W*H); pilha=[(W//2,H//2)]
    while pilha:
        x,y=pilha.pop()
        if v[y*W+x] or not pred(px[x,y]): continue
        xi=x
        while xi>=0 and not v[y*W+xi] and pred(px[xi,y]): xi-=1
        xi+=1
        xf=x
        while xf<W and not v[y*W+xf] and pred(px[xf,y]): xf+=1
        xf-=1
        for xx in range(xi,xf+1): v[y*W+xx]=1
        for ny in (y-1,y+1):
            if 0<=ny<H:
                xx=xi
                while xx<=xf:
                    if not v[ny*W+xx] and pred(px[xx,ny]):
                        pilha.append((xx,ny))
                        while xx<=xf and pred(px[xx,ny]): xx+=1
                    xx+=1
    return v
cru=flood(quente)
bruta=Image.new("L",(W,H),0); bp=bruta.load()
for y in range(H):
    for x in range(W):
        if cru[y*W+x]: bp[x,y]=255
bruta=bruta.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MaxFilter(5)); bp=bruta.load()
sx=sy=0; n=0
for y in range(H):
    for x in range(W):
        if bp[x,y]>128: sx+=x; sy+=y; n+=1
GX,GY=float(sx)/n,float(sy)/n

# ---- 3) borda e silhueta -------------------------------------------------
import comum
def amarelo(p): return p[0]>195 and 140<p[1]<235 and p[2]<110
def azul(p):    return p[2]>95 and p[2]-p[0]>55 and p[0]<110
def branco(p):  return min(p)>=244
raio=comum.traca_borda(px,W,H,GX,GY,amarelo,azul,branco,gap=6.0)
liso=comum.alisa(raio)
d=[abs(a-b) for a,b in zip(raio,liso)]
print("borda tracada: ondulacao media %.2f px, maxima %.2f px"%(sum(d)/len(d),max(d)))
buraco=comum.mascara_do_raio(liso,W,H,GX,GY); hp=buraco.load()
sil=bytearray(W*H)
for y in range(H):
    for x in range(W):
        if hp[x,y]>128 and bp[x,y]<=128: sil[y*W+x]=1
maior=comum.maior_pedaco(sil,W,H)
sil=bytearray(W*H)
for j in maior: sil[j]=1
bin_buraco=bytearray(W*H)
for y in range(H):
    for x in range(W):
        if hp[x,y]>128 and not sil[y*W+x]: bin_buraco[y*W+x]=1
print("silhueta do candidato: %d px"%len(maior))
# o halo que o candidato trouxe do recorte antigo puxa para o quente, como o
# fundo; a camisa dele puxa para o frio. so o halo pode ser comido.
def e_halo(p):
    r,g,b=p
    return min(p)>=200 and max(p)-min(p)<=32 and (r-b)>=1
comidos=comum.come_halo(sil,bin_buraco,px,W,H,teto=14,e_halo=e_halo)
print("halo claro removido em volta dele: %d px"%comidos)
print("sobras claras soltas removidas: %d px"%comum.limpa_sobras(sil,bin_buraco,px,W,H,k=9))
maior=comum.maior_pedaco(sil,W,H)
sil=bytearray(W*H)
for j in maior: sil[j]=1
ms=Image.new("L",(W,H),0); sp=ms.load()
for y in range(H):
    for x in range(W):
        if sil[y*W+x]: sp[x,y]=255
# fechamento tapa os furinhos que o recorte abriu dentro dele
ms=ms.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.MinFilter(9))
ms=ms.filter(ImageFilter.MedianFilter(13)); sp=ms.load()
# junta borda e silhueta ainda em preto e branco e suaviza uma vez so: duas
# bordas suaves independentes se cruzam e deixam um fio translucido no meio
# do corpo dele.
final=Image.new("L",(W,H),0); fp=final.load()
for y in range(H):
    for x in range(W):
        fp[x,y]=255 if (hp[x,y]>128 and sp[x,y]<=128) else 0
# so o vazado principal vale: pontinhos soltos viram furo na roupa dele
bin_final=bytearray(W*H); fpl=final.load()
for y in range(H):
    for x in range(W):
        if fpl[x,y]>128: bin_final[y*W+x]=1
principal=comum.maior_pedaco(bin_final,W,H)
final=Image.new("L",(W,H),0); fpl=final.load()
for j in principal: fpl[j%W,j//W]=255
final=final.filter(ImageFilter.GaussianBlur(0.8)); hp=final.load()
sp=Image.new("L",(W,H),0).load()

out=Image.new("RGBA",(W,H)); op=out.load()
minx,maxx,miny,maxy=W,0,H,0; soma=0; somax=0
for y in range(H):
    for x in range(W):
        v=hp[x,y]
        r,g,b=px[x,y]
        op[x,y]=(r,g,b,max(0,255-int(round(v))))
        if v>128:
            minx=min(minx,x);maxx=max(maxx,x);miny=min(miny,y);maxy=max(maxy,y);soma+=1;somax+=x
print("buraco: cx=%.0f cy=%.0f rx=%.0f ry=%.0f centroideX=%.0f"
      %((minx+maxx)/2.0,(miny+maxy)/2.0,(maxx-minx+1)/2.0,(maxy-miny+1)/2.0,float(somax)/soma))
out.save("story-azul.webp","WEBP",quality=90,method=6)
print("%dx%d  %d KB"%(W,H,os.path.getsize("story-azul.webp")//1024))
palco=Image.new("RGBA",(W,H),(230,30,60,255))
mm=Image.new("L",(W,H)); mm.putdata([255-p[3] for p in out.getdata()])
palco.putalpha(mm)
vis=Image.new("RGBA",(W,H),(240,243,248,255)); vis.alpha_composite(palco); vis.alpha_composite(out)
vis.convert("RGB").resize((360,640),Image.LANCZOS).save("solido-story.png")
