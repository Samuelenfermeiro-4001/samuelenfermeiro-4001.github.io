"""Monta a moldura 4:5 a partir da arte nova do designer.

A arte veio com alfa de verdade, entao nao ha recorte a fazer. Duas coisas
precisam de conserto aqui:

  - a borda esquerda do desenho afina ate sumir por volta da metade da altura,
    e o miolo fica aberto para fora. Um fechamento morfologico costura essa
    linha antes de decidir onde e o vazado;
  - o lado de fora e a falha da borda sao achatados sobre o azul da campanha,
    para o arquivo baixado nao ter canto transparente nem furo na lateral.
"""
from PIL import Image, ImageFilter
from collections import Counter
import os, glob

D=os.path.expanduser("~/Downloads/")
ORIG=max(glob.glob(D+"ChatGPT Image 1 de set. de 2026, 18_*.png"), key=os.path.getmtime)
LARG,ALT=1080,1350
im=Image.open(ORIG).convert("RGBA"); W,H=im.size; px=im.load()
print("origem: %s  %dx%d"%(os.path.basename(ORIG),W,H))
assert abs(W/float(H)-0.8)<0.01, "a arte nao esta em 4:5"

c=Counter()
for y in range(0,H,3):
    for x in range(0,W,3):
        r,g,b,a=px[x,y]
        if a>240 and b>90 and b-r>50 and r<90: c[(r,g,b)]+=1
AZUL=c.most_common(1)[0][0]
print("azul da campanha: %s"%(AZUL,))

# 1) costura a borda partida
# a arte tem uma margem transparente de ~15 px em toda a volta (canto
# arredondado). Ela vira azul no fim, entao entra aqui como se fosse desenho:
# sem isso o vazado escapa por ela onde a borda esquerda esta partida.
MARGEM=18
op=Image.new("L",(W,H),0); opp=op.load()
for y in range(H):
    borda_y = y<MARGEM or y>=H-MARGEM
    for x in range(W):
        if px[x,y][3]>=100 or borda_y or x<MARGEM or x>=W-MARGEM: opp[x,y]=255
K=17
fechado=op.filter(ImageFilter.MaxFilter(K)).filter(ImageFilter.MinFilter(K))
fp=fechado.load()
costurados=sum(1 for y in range(H) for x in range(W) if fp[x,y]>128 and opp[x,y]<=128)
print("pixels costurados na borda: %d"%costurados)

# 2) vazado = o que sobra dentro da costura
v=bytearray(W*H); pilha=[(W//2,H//3)]
while pilha:
    x,y=pilha.pop()
    if v[y*W+x] or fp[x,y]>128: continue
    xi=x
    while xi>=0 and not v[y*W+xi] and fp[xi,y]<=128: xi-=1
    xi+=1
    xf=x
    while xf<W and not v[y*W+xf] and fp[xf,y]<=128: xf+=1
    xf-=1
    for xx in range(xi,xf+1): v[y*W+xx]=1
    for ny in (y-1,y+1):
        if 0<=ny<H:
            xx=xi
            while xx<=xf:
                if not v[ny*W+xx] and fp[xx,ny]<=128:
                    pilha.append((xx,ny))
                    while xx<=xf and fp[xx,ny]<=128: xx+=1
                xx+=1
assert not v[0] and not v[(H-1)*W], "o vazado ainda escapa para fora"
print("buraco: %.1f%% da arte"%(100.0*sum(v)/(W*H)))
buraco=Image.new("L",(W,H),0); bp=buraco.load()
for y in range(H):
    for x in range(W):
        if v[y*W+x]: bp[x,y]=255
buraco=buraco.filter(ImageFilter.GaussianBlur(0.8)); bp=buraco.load()

# 3) cor sobre o azul, alfa pelo vazado
out=Image.new("RGBA",(W,H)); op2=out.load()
for y in range(H):
    for x in range(W):
        r,g,b,a=px[x,y]
        f=a/255.0
        cor=(int(round(r*f+AZUL[0]*(1-f))),
             int(round(g*f+AZUL[1]*(1-f))),
             int(round(b*f+AZUL[2]*(1-f))))
        op2[x,y]=cor+(255-bp[x,y],)

fin=out.resize((LARG,ALT),Image.LANCZOS); Fp=fin.load()
minx,maxx,miny,maxy=LARG,0,ALT,0
for y in range(ALT):
    for x in range(LARG):
        if Fp[x,y][3]<128:
            minx=min(minx,x);maxx=max(maxx,x);miny=min(miny,y);maxy=max(maxy,y)
cx=(minx+maxx)//2; cy=(miny+maxy)//2; rx=(maxx-minx+1)//2; ry=(maxy-miny+1)//2
print("buraco %dx%d: cx=%d cy=%d rx=%d ry=%d"%(LARG,ALT,cx,cy,rx,ry))
fin.save("post-45.webp","WEBP",quality=90,method=6)
print("%d KB"%(os.path.getsize("post-45.webp")//1024))
for tag,cor in (("escuro",(20,24,40,255)),("solido",(230,30,60,255))):
    palco=Image.new("RGBA",(LARG,ALT),cor)
    mk=Image.new("L",(LARG,ALT)); mk.putdata([255-p[3] for p in fin.getdata()])
    palco.putalpha(mk)
    o=Image.new("RGBA",(LARG,ALT),cor); o.alpha_composite(palco); o.alpha_composite(fin)
    o.convert("RGB").resize((440,550),Image.LANCZOS).save("p45-%s.png"%tag)
