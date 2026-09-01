"""Monta as molduras a partir das artes do designer, que vem com alfa de verdade.

Nao ha recorte a fazer: o vazado e a silhueta do candidato ja vem no arquivo.
O que o script faz e:

  1. costurar a borda do desenho quando ela vem partida (na arte 4:5 a lateral
     esquerda afina ate sumir por volta da metade da altura);
  2. descobrir o lado de fora — o que esta ligado a beirada do arquivo — e
     achatar so ele sobre o azul da campanha, para o arquivo baixado nao ter
     canto transparente;
  3. deixar TODO o resto do transparente como vazado. Isso inclui os vaos entre
     os dedos da mao dele, que sao buraco e nao moldura: pintar esses vaos de
     azul era o que fazia a mao parecer recortada.
"""
from PIL import Image, ImageFilter
from collections import Counter
import os, sys

def azul_da_campanha(px, W, H):
    c = Counter()
    for y in range(0, H, 3):
        for x in range(0, W, 3):
            r, g, b, a = px[x, y]
            if a > 240 and b > 90 and b - r > 50 and r < 90: c[(r, g, b)] += 1
    return c.most_common(1)[0][0]

def monta(origem, saida, larg, alt, anel=None, costura=None):
    im = Image.open(origem).convert("RGBA")
    W, H = im.size
    px = im.load()
    AZUL = azul_da_campanha(px, W, H)

    # 1) opacidade com a borda costurada, para o lado de fora nao invadir o
    #    miolo onde o desenho vem partido
    op = Image.new("L", (W, H), 0); opp = op.load()
    for y in range(H):
        for x in range(W):
            if px[x, y][3] >= 128: opp[x, y] = 255
    # a costura so entra quando o desenho vem com a borda partida; costurar sem
    # necessidade fecharia pedacos legitimos do lado de fora.
    if costura:
        op = op.filter(ImageFilter.MaxFilter(costura)).filter(ImageFilter.MinFilter(costura))
    fp = op.load()

    # 2) lado de fora: o transparente ligado a beirada do arquivo. Quando a
    #    moldura tem so uma margem fina de canto arredondado (e o desenho vem
    #    com falha na borda), `anel` prende essa busca a faixa da beirada.
    # semear a beirada inteira, e nao so os quatro cantos: no desenho 1:1 o
    # arco amarelo encosta no topo e separa um pedaco do lado de fora, que
    # senao seria confundido com vazado.
    fora = bytearray(W * H)
    pilha = ([(x, 0) for x in range(W)] + [(x, H-1) for x in range(W)] +
             [(0, y) for y in range(H)] + [(W-1, y) for y in range(H)])
    def livre(x, y):
        if fp[x, y] > 128: return False
        if anel is None: return True
        return x < anel or y < anel or x >= W - anel or y >= H - anel
    while pilha:
        x, y = pilha.pop()
        if fora[y*W+x] or not livre(x, y): continue
        xi = x
        while xi >= 0 and not fora[y*W+xi] and livre(xi, y): xi -= 1
        xi += 1
        xf = x
        while xf < W and not fora[y*W+xf] and livre(xf, y): xf += 1
        xf -= 1
        for xx in range(xi, xf+1): fora[y*W+xx] = 1
        for ny in (y-1, y+1):
            if 0 <= ny < H:
                xx = xi
                while xx <= xf:
                    if not fora[ny*W+xx] and livre(xx, ny):
                        pilha.append((xx, ny))
                        while xx <= xf and livre(xx, ny): xx += 1
                    xx += 1
    if fora[(H//3)*W + W//2]:
        sys.exit("o lado de fora invadiu o miolo: a borda continua aberta")

    # 3) vazado = todo o transparente que nao e o lado de fora (inclui os vaos
    #    entre os dedos)
    buraco = Image.new("L", (W, H), 0); bp = buraco.load()
    n = 0
    for y in range(H):
        for x in range(W):
            if px[x, y][3] < 128 and not fora[y*W+x]:
                bp[x, y] = 255; n += 1
    print("  vazado: %.1f%% da arte" % (100.0*n/(W*H)))
    buraco = buraco.filter(ImageFilter.GaussianBlur(0.8)); bp = buraco.load()

    out = Image.new("RGBA", (W, H)); op2 = out.load()
    for y in range(H):
        for x in range(W):
            r, g, b, a = px[x, y]
            f = a / 255.0
            op2[x, y] = (int(round(r*f + AZUL[0]*(1-f))),
                         int(round(g*f + AZUL[1]*(1-f))),
                         int(round(b*f + AZUL[2]*(1-f))),
                         255 - bp[x, y])
    fin = out.resize((larg, alt), Image.LANCZOS); Fp = fin.load()
    # A geometria sai do vazado PRINCIPAL, nao de todo o transparente: os vaos
    # entre os dedos tambem sao vazado, mas obrigar a foto a cobri-los faria a
    # foto crescer demais. Neles aparece o fundo claro, como na arte original.
    mask = bytearray(larg * alt)
    for y in range(alt):
        for x in range(larg):
            if Fp[x, y][3] < 128: mask[y*larg+x] = 1
    visto = bytearray(larg * alt); melhor = []
    for y0 in range(alt):
        for x0 in range(larg):
            i = y0*larg + x0
            if not mask[i] or visto[i]: continue
            pilha = [(x0, y0)]; g = []
            while pilha:
                x, y = pilha.pop(); j = y*larg + x
                if visto[j] or not mask[j]: continue
                visto[j] = 1; g.append(j)
                for nx, ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                    if 0 <= nx < larg and 0 <= ny < alt and not visto[ny*larg+nx] and mask[ny*larg+nx]:
                        pilha.append((nx, ny))
            if len(g) > len(melhor): melhor = g
    minx = min(j % larg for j in melhor); maxx = max(j % larg for j in melhor)
    miny = min(j // larg for j in melhor); maxy = max(j // larg for j in melhor)
    print("  vazado principal: %d px de %d transparentes" % (len(melhor), sum(mask)))
    cx = (minx+maxx)//2; cy = (miny+maxy)//2
    rx = (maxx-minx+1)//2; ry = (maxy-miny+1)//2
    print("  cx=%d cy=%d rx=%d ry=%d" % (cx, cy, rx, ry))
    fin.save(saida, "WEBP", quality=90, method=6)
    print("  %s  %dx%d  %d KB" % (saida, larg, alt, os.path.getsize(saida)//1024))
    return fin

if __name__ == "__main__":
    import glob
    D = os.path.expanduser("~/Downloads/")
    print("perfil 1:1")
    monta(max(glob.glob(D+"ChatGPT Image 1 de set. de 2026, 17_*.png"), key=os.path.getmtime),
          "perfil-1x1.webp", 1080, 1080)   # cantos largos: componente inteiro
    print("post 4:5")
    monta(max(glob.glob(D+"ChatGPT Image 1 de set. de 2026, 18_*.png"), key=os.path.getmtime),
          "post-45.webp", 1080, 1350, anel=26, costura=17)  # margem fina e borda partida
