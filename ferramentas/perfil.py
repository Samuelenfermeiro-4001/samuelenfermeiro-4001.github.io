"""Monta a moldura de perfil a partir da arte nova do designer.

Essa arte veio como PNG com alfa de verdade, entao nao ha recorte a fazer: o
trabalho e so deixar o quadro quadrado (foto de perfil e 1:1) e pintar o lado
de fora com o azul da campanha, como a Gislaine pediu, para o arquivo baixado
nao ter canto transparente.
"""
from PIL import Image
import os

ORIG=os.path.expanduser("~/Downloads/ChatGPT Image 1 de set. de 2026, 17_10_07.png")
SAIDA=1080
im=Image.open(ORIG).convert("RGBA")
W,H=im.size
L=max(W,H)
quadro=Image.new("RGBA",(L,L),(0,0,0,0))
dx,dy=(L-W)//2,(L-H)//2
quadro.paste(im,(dx,dy))
px=quadro.load()

# azul do anel, para preencher o lado de fora
from collections import Counter
c=Counter()
for y in range(0,L,3):
    for x in range(0,L,3):
        r,g,b,a=px[x,y]
        if a>240 and b>90 and b-r>50 and r<90: c[(r,g,b)]+=1
AZUL=c.most_common(1)[0][0]
print("azul da campanha: %s"%(AZUL,))

def flood(sementes):
    v=bytearray(L*L); pilha=[s for s in sementes]
    while pilha:
        x,y=pilha.pop()
        if v[y*L+x] or px[x,y][3]>=128: continue
        xi=x
        while xi>=0 and not v[y*L+xi] and px[xi,y][3]<128: xi-=1
        xi+=1
        xf=x
        while xf<L and not v[y*L+xf] and px[xf,y][3]<128: xf+=1
        xf-=1
        for xx in range(xi,xf+1): v[y*L+xx]=1
        for ny in (y-1,y+1):
            if 0<=ny<L:
                xx=xi
                while xx<=xf:
                    if not v[ny*L+xx] and px[xx,ny][3]<128:
                        pilha.append((xx,ny))
                        while xx<=xf and px[xx,ny][3]<128: xx+=1
                    xx+=1
    return v
buraco=flood([(L//2,L//2)])
fora=flood([(0,0),(L-1,0),(0,L-1),(L-1,L-1)])
assert not fora[(L//2)*L+L//2] and not buraco[0], "buraco e lado de fora se encontraram"

# tudo que nao e o buraco vai para cima do azul, opaco
n=0
for y in range(L):
    for x in range(L):
        if buraco[y*L+x]: continue
        r,g,b,a=px[x,y]
        if a==255: continue
        f=a/255.0
        px[x,y]=(int(round(r*f+AZUL[0]*(1-f))),
                 int(round(g*f+AZUL[1]*(1-f))),
                 int(round(b*f+AZUL[2]*(1-f))), 255)
        n+=1
print("pixels achatados sobre o azul: %d"%n)

fin=quadro.resize((SAIDA,SAIDA),Image.LANCZOS)
fp=fin.load()
minx,maxx,miny,maxy=SAIDA,0,SAIDA,0
for y in range(SAIDA):
    for x in range(SAIDA):
        if fp[x,y][3]<128:
            minx=min(minx,x);maxx=max(maxx,x);miny=min(miny,y);maxy=max(maxy,y)
cx=(minx+maxx)//2; cy=(miny+maxy)//2
rx=(maxx-minx+1)//2; ry=(maxy-miny+1)//2
print("buraco %d: cx=%d cy=%d rx=%d ry=%d"%(SAIDA,cx,cy,rx,ry))
fin.save("perfil-1x1.webp","WEBP",quality=90,method=6)
print("%d KB"%(os.path.getsize("perfil-1x1.webp")//1024))
for tag,cor in (("escuro",(20,24,40,255)),("solido",(230,30,60,255))):
    palco=Image.new("RGBA",(SAIDA,SAIDA),cor)
    mk=Image.new("L",(SAIDA,SAIDA)); mk.putdata([255-p[3] for p in fin.getdata()])
    palco.putalpha(mk)
    out=Image.new("RGBA",(SAIDA,SAIDA),cor); out.alpha_composite(palco); out.alpha_composite(fin)
    out.convert("RGB").resize((580,580),Image.LANCZOS).save("nv-%s.png"%tag)
