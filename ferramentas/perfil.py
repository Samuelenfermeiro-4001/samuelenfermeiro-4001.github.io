"""Reconstroi a moldura 1:1 a partir da arte de origem do designer.

Tres coisas acontecem aqui:
  1. o CNPJ vem errado na arte (58.437.765); o digito e corrigido transplantando
     o proprio "6" da mesma linha, deslocado ao longo do arco;
  2. o miolo e vazado por preenchimento a partir do centro;
  3. a borda do vazado e alisada — a arte veio de JPEG e a linha fina que separa
     o miolo da faixa branca fica ruidosa, deixando dentes na borda.
"""
from PIL import Image, ImageFilter
import os, math

D=os.path.expanduser("~/Downloads/")
ORIG=D+"WhatsApp Image 2026-08-27 at 11.39.34.jpeg"
AZUL=(2,42,156)
CX,CY,R=625.0,550.3,528.5          # circulo do texto em arco
A0=math.radians(-190); R0=468.0; R1=588.0
SW=int(round(R*(math.radians(10)-A0))); SH=int(round(R1-R0))
DX,DY=121,2                        # deslocamento do "6" ate a casa do "5"
CAIXA_SAMUEL=(690,250)             # a partir daqui o alisamento e leve

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

# ---- 1) CNPJ -------------------------------------------------------------
def tinta(p): return p[2]>60 and p[2]-p[0]>35 and p[0]<125 and p[1]<125
ink=bytearray(SW*SH)
for sy in range(SH):
    rr=R0+sy
    for sx in range(SW):
        a=A0+(sx+0.5)/R
        if tinta(amostra(CX+rr*math.cos(a), CY+rr*math.sin(a))): ink[sy*SW+sx]=1
def componente(x0,y0):
    v=bytearray(SW*SH); pilha=[(x0,y0)]; saida=set()
    while pilha:
        x,y=pilha.pop(); j=y*SW+x
        if v[j] or not ink[j]: continue
        v[j]=1; saida.add((x,y))
        for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if 0<=nx<SW and 0<=ny<SH and not v[ny*SW+nx] and ink[ny*SW+nx]: pilha.append((nx,ny))
    return saida
def semente(x0,x1,y0,y1):
    for y in range(y0,y1+1):
        for x in range(x0,x1+1):
            if ink[y*SW+x]: return (x,y)
    raise SystemExit("glifo nao encontrado")
c5=componente(*semente(805,822,16,37))
c6=componente(*semente(927,942,18,39))
def dilata(s,k):
    o=set()
    for x,y in s:
        for j in range(-k,k+1):
            for i in range(-k,k+1):
                if i*i+j*j<=k*k+1: o.add((x+i,y+j))
    return o
outros=set()
for y in range(SH):
    for x in range(SW):
        if ink[y*SW+x] and (x,y) not in c5 and (x,y) not in c6: outros.add((x,y))
proibido=dilata(outros,1)
m5=dilata(c5,2)-proibido; m6=dilata(c6,2)-proibido
print("CNPJ: %d px do '5' apagados, %d px do '6' colados"%(len(m5),len(m6)))
alvo=m5|{(x-DX,y-DY) for x,y in m6}
xs=[p[0] for p in alvo]; ys=[p[1] for p in alvo]
px0,px1,py0,py1=W,0,H,0
for sx in (min(xs)-2,max(xs)+2):
    for sy in (min(ys)-2,max(ys)+2):
        a=A0+(sx+0.5)/R; rr=R0+sy
        X=CX+rr*math.cos(a); Y=CY+rr*math.sin(a)
        px0=min(px0,int(X)-3); px1=max(px1,int(X)+4)
        py0=min(py0,int(Y)-3); py1=max(py1,int(Y)+4)
np_=im.load()
troca={}
for Y in range(py0,py1):
    for X in range(px0,px1):
        dx=X+0.5-CX; dy=Y+0.5-CY
        rr=math.hypot(dx,dy); a=math.atan2(dy,dx)
        while a<A0: a+=2*math.pi
        sx=int(round((a-A0)*R-0.5)); sy=int(round(rr-R0))
        if (sx+DX,sy+DY) in m6:
            a2=a+DX/R; r2=rr+DY
            troca[(X,Y)]=tuple(int(round(v)) for v in amostra(CX+r2*math.cos(a2), CY+r2*math.sin(a2)))
        elif (sx,sy) in m5:
            troca[(X,Y)]=(255,255,255)
for k,v in troca.items(): np_[k[0],k[1]]=v

# ---- 2) vazado -----------------------------------------------------------
def branco(p,t=248): return p[0]>=t and p[1]>=t and p[2]>=t
def flood(sementes,pred):
    v=bytearray(W*H); pilha=list(sementes)
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
dentro=flood([(W//2,H//2)],branco)
fora=flood([(0,0),(W-1,0),(0,H-1),(W-1,H-1)],lambda p: min(p)>=170)
assert not fora[(H//2)*W+W//2] and not dentro[0], "os preenchimentos se encontraram"

def como_imagem(v):
    m=Image.new("L",(W,H),0); mp=m.load()
    for y in range(H):
        for x in range(W):
            if v[y*W+x]: mp[x,y]=255
    return m

# ---- 3) borda e silhueta -------------------------------------------------
import comum
bruta=como_imagem(dentro).filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MaxFilter(5))
bp=bruta.load()
sx=sy=0; n=0
for y in range(H):
    for x in range(W):
        if bp[x,y]>128: sx+=x; sy+=y; n+=1
GX,GY=float(sx)/n,float(sy)/n
def amarelo(p): return p[0]>195 and 140<p[1]<235 and p[2]<110
def azul(p):    return p[2]>95 and p[2]-p[0]>55 and p[0]<110
def fio(p):     return 150<=min(p)<248 and max(p)-min(p)<=22
raio=comum.traca_borda(px,W,H,GX,GY,amarelo,azul,fio,gap=7.0)
liso=comum.alisa(raio)
d=[abs(a-b) for a,b in zip(raio,liso)]
print("borda tracada: ondulacao media %.2f px, maxima %.2f px"%(sum(d)/len(d),max(d)))
buraco=comum.mascara_do_raio(liso,W,H,GX,GY); hp=buraco.load()
bin_buraco=bytearray(W*H); sil=bytearray(W*H)
for y in range(H):
    for x in range(W):
        if hp[x,y]>128:
            if bp[x,y]>128: bin_buraco[y*W+x]=1
            else: sil[y*W+x]=1
def fundo_exato(p): return min(p)>=253
resgatados=0
for y in range(H):
    for x in range(W):
        i=y*W+x
        if sil[i] and fundo_exato(px[x,y]): sil[i]=0; resgatados+=1
print("bolsoes recuperados: %d px"%resgatados)
maior=comum.maior_pedaco(sil,W,H)
sil=bytearray(W*H)
for j in maior: sil[j]=1
for y in range(H):
    for x in range(W):
        if hp[x,y]>128 and not sil[y*W+x]: bin_buraco[y*W+x]=1
print("silhueta do candidato: %d px"%len(maior))
comidos=comum.come_halo(sil,bin_buraco,px,W,H,teto=18)
print("halo claro removido em volta dele: %d px"%comidos)
print("sobras claras soltas removidas: %d px"%comum.limpa_sobras(sil,px,W,H,k=9))
maior=comum.maior_pedaco(sil,W,H)
sil=bytearray(W*H)
for j in maior: sil[j]=1
ms=Image.new("L",(W,H),0); sp=ms.load()
for y in range(H):
    for x in range(W):
        if sil[y*W+x]: sp[x,y]=255
# fechamento tapa os furinhos que o recorte abriu dentro dele
ms=ms.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.MinFilter(9))
ms=ms.filter(ImageFilter.MedianFilter(3)).filter(ImageFilter.GaussianBlur(0.8)); sp=ms.load()
final=Image.new("L",(W,H),0); fp=final.load()
for y in range(H):
    for x in range(W):
        fp[x,y]=int(round(hp[x,y]*(1.0-sp[x,y]/255.0)))
final=final.filter(ImageFilter.GaussianBlur(0.7)); fp=final.load()
mf=como_imagem(fora).filter(ImageFilter.GaussianBlur(1.0)).load()

# ---- 4) saida ------------------------------------------------------------
out=Image.new("RGBA",(W,H)); op=out.load()
minx,maxx,miny,maxy=W,0,H,0; soma=0; somax=0
for y in range(H):
    for x in range(W):
        r,g,b=px[x,y]
        t=mf[x,y]/255.0
        if t>0.004:
            r=max(0,min(255,int(round(r+t*(AZUL[0]-255)))))
            g=max(0,min(255,int(round(g+t*(AZUL[1]-255)))))
            b=max(0,min(255,int(round(b+t*(AZUL[2]-255)))))
        d=fp[x,y]
        op[x,y]=(r,g,b,max(0,255-d))
        if d>128:
            minx=min(minx,x);maxx=max(maxx,x);miny=min(miny,y);maxy=max(maxy,y);soma+=1;somax+=x
e=1080.0/W
print("buraco 1080: cx=%.0f cy=%.0f rx=%.0f ry=%.0f centroideX=%.0f"
      %(((minx+maxx)/2)*e,((miny+maxy)/2)*e,((maxx-minx+1)/2)*e,((maxy-miny+1)/2)*e,(float(somax)/soma)*e))
fin=out.resize((1080,1080),Image.LANCZOS)
fin.save("perfil-1x1.webp","WEBP",quality=90,method=6)
print("%d KB"%(os.path.getsize("perfil-1x1.webp")//1024))
v=Image.new("RGB",(1080,1080),(255,0,255)); v.paste(fin,(0,0),fin)
v.crop((40,380,340,760)).resize((600,760),Image.LANCZOS).save("z-alfa-esq.png")
v.crop((0,0,1080,1080)).resize((420,420)).save("z-todo.png")
