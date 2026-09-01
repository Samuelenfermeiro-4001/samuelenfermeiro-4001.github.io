"""Rotinas de recorte compartilhadas pelas duas molduras.

As artes chegam como JPEG achatado: o candidato, o anel, o faixao e o lugar da
foto vivem na mesma camada. Duas coisas dao errado quando se recorta por cor:

  1. a borda do vazado nem sempre tem limite de cor (embaixo, o vazado e o
     faixao sao brancos iguais), entao o preenchimento por semente para onde o
     ruido do JPEG mandar e a borda sai serrilhada;
  2. o candidato foi colado sobre fundo branco e carrega um halo claro em
     volta; esse halo fica opaco e aparece como uma lasca branca em volta dele
     quando a foto de quem usa o app e escura.

Aqui a borda externa e tracada raio a raio (passando por tras do candidato) e a
silhueta dele e recortada depois, com o halo comido ate encostar no cabelo.
"""
import math
from PIL import Image, ImageFilter

def escuro(p):  return min(p) < 170
def claro(p):   return min(p) >= 200 and max(p) - min(p) <= 32

def traca_borda(px, W, H, GX, GY, amarelo, azul, fio, gap, passos=3600,
                corrida=8, perto_do_aro=130):
    """Raio da borda externa em funcao do angulo, visto de (GX, GY).

    Para no arco amarelo ou no anel azul (recuando `gap`, que reproduz o
    contorno branco do desenho) e no fio claro que separa o vazado da faixa.
    O fio e o halo do candidato tem cor parecida; o que os separa e o que vem
    depois: se houver pixel escuro logo adiante, e o candidato, e o raio segue.
    """
    raio = [0.0] * passos
    for i in range(passos):
        a = 2 * math.pi * i / passos
        cs, sn = math.cos(a), math.sin(a)
        r = 8.0; achou = None
        while r < max(W, H) * 1.3:
            x = int(GX + r * cs); y = int(GY + r * sn)
            if not (0 <= x < W and 0 <= y < H):
                achou = r; break
            p = px[x, y]
            if amarelo(p) or azul(p):
                achou = r - gap; break
            if fio(p):
                # Duas armadilhas aqui. O texto do CNPJ tambem e escuro, mas em
                # tracos finos: so uma corrida longa de escuro adiante indica o
                # candidato. E a camisa branca dele parece o fio: o que separa e
                # a distancia ate o aro — a borda de verdade corre colada nele.
                seguidos = 0; candidato = False; aro = None
                for d in range(1, 420):
                    x2 = int(GX + (r + d) * cs); y2 = int(GY + (r + d) * sn)
                    if not (0 <= x2 < W and 0 <= y2 < H): break
                    q = px[x2, y2]
                    if amarelo(q) or azul(q): aro = d; break
                    if escuro(q):
                        seguidos += 1
                        if seguidos >= corrida: candidato = True; break
                    else:
                        seguidos = 0
                if not candidato and aro is not None and aro <= perto_do_aro:
                    achou = r; break
            r += 1.0
        raio[i] = achou if achou else r
    return raio

def alisa(v, k_mediana=25, k_media=10):
    m = len(v)
    med = [sorted(v[(i + j) % m] for j in range(-k_mediana, k_mediana + 1))[k_mediana]
           for i in range(m)]
    return [sum(med[(i + j) % m] for j in range(-k_media, k_media + 1)) / (2.0 * k_media + 1)
            for i in range(m)]

def mascara_do_raio(raio, W, H, GX, GY):
    passos = len(raio)
    m = Image.new("L", (W, H), 0); mp = m.load()
    for y in range(H):
        dy = y + 0.5 - GY
        for x in range(W):
            dx = x + 0.5 - GX
            a = math.atan2(dy, dx)
            if a < 0: a += 2 * math.pi
            t = a * passos / (2 * math.pi)
            i0 = int(t) % passos; i1 = (i0 + 1) % passos; f = t - int(t)
            rr = raio[i0] * (1 - f) + raio[i1] * f
            mp[x, y] = int(round(255 * max(0.0, min(1.0, rr - math.hypot(dx, dy) + 0.5))))
    return m

def maior_pedaco(mask, W, H):
    visto = bytearray(W * H); melhor = []
    for y0 in range(H):
        for x0 in range(W):
            i = y0 * W + x0
            if not mask[i] or visto[i]: continue
            pilha = [(x0, y0)]; g = []
            while pilha:
                x, y = pilha.pop(); j = y * W + x
                if visto[j] or not mask[j]: continue
                visto[j] = 1; g.append(j)
                for nx, ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                    if 0 <= nx < W and 0 <= ny < H and not visto[ny*W+nx] and mask[ny*W+nx]:
                        pilha.append((nx, ny))
            if len(g) > len(melhor): melhor = g
    return melhor

def distancia_ao_escuro(px, W, H, teto):
    """Chamfer aproximado, saturado em `teto` — so interessa o que esta perto."""
    G = teto + 1
    d = [G] * (W * H)
    for y in range(H):
        b = y * W
        for x in range(W):
            if escuro(px[x, y]): d[b + x] = 0
    for y in range(H):
        b = y * W
        for x in range(W):
            v = d[b + x]
            if x: v = min(v, d[b + x - 1] + 1)
            if y: v = min(v, d[b - W + x] + 1)
            if x and y: v = min(v, d[b - W + x - 1] + 1)
            if x < W - 1 and y: v = min(v, d[b - W + x + 1] + 1)
            d[b + x] = min(v, G)
    for y in range(H - 1, -1, -1):
        b = y * W
        for x in range(W - 1, -1, -1):
            v = d[b + x]
            if x < W - 1: v = min(v, d[b + x + 1] + 1)
            if y < H - 1: v = min(v, d[b + W + x] + 1)
            if x < W - 1 and y < H - 1: v = min(v, d[b + W + x + 1] + 1)
            if x and y < H - 1: v = min(v, d[b + W + x - 1] + 1)
            d[b + x] = min(v, G)
    return d

def come_halo(sil, buraco_bin, px, W, H, teto, e_halo=None, alcance=20):
    """Tira da silhueta o halo claro que o candidato trouxe do recorte antigo.

    So come pixel claro que esteja perto de algo escuro — assim o halo em volta
    do cabelo e do rosto some, e a camisa branca, que nao tem escuro por perto,
    fica inteira. E so ate `alcance` px para dentro da borda: sem esse limite a
    limpeza desce pelas costuras da camisa, que tambem tem escuro ao lado, e
    abre riscos finos no meio do peito dele.
    """
    e_halo = e_halo or claro
    d = distancia_ao_escuro(px, W, H, teto)
    fila = []; prof = {}
    for y in range(H):
        b = y * W
        for x in range(W):
            i = b + x
            if not sil[i]: continue
            if (x and buraco_bin[i-1]) or (x < W-1 and buraco_bin[i+1]) or \
               (y and buraco_bin[i-W]) or (y < H-1 and buraco_bin[i+W]):
                fila.append(i); prof[i] = 0
    comidos = 0; k = 0
    while k < len(fila):
        i = fila[k]; k += 1
        if not sil[i]: continue
        p = prof[i]
        if p > alcance: continue
        x = i % W; y = i // W
        if not (e_halo(px[x, y]) and d[i] <= teto): continue
        sil[i] = 0; comidos += 1
        for nx, ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if 0 <= nx < W and 0 <= ny < H:
                j = ny * W + nx
                if sil[j] and (j not in prof or prof[j] > p + 1):
                    prof[j] = p + 1; fila.append(j)
    return comidos


def limpa_sobras(sil, buraco_bin, px, W, H, k=9, alcance=30):
    """Tira as sobras claras soltas que o recorte antigo deixou junto a borda.

    A abertura so pode agir perto do buraco: no meio do corpo dele a camisa tem
    vincos e sombras que estreitam a mascara clara, e uma abertura ali abriria
    riscos de um pixel atravessando a camisa.
    """
    from PIL import Image, ImageFilter
    perto = bytearray(W * H)
    fila = [i for i in range(W * H) if buraco_bin[i]]
    dist = {i: 0 for i in fila}
    k0 = 0
    while k0 < len(fila):
        i = fila[k0]; k0 += 1
        d = dist[i]
        if d >= alcance: continue
        x = i % W; y = i // W
        for nx, ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if 0 <= nx < W and 0 <= ny < H:
                j = ny * W + nx
                if j not in dist:
                    dist[j] = d + 1
                    if sil[j]: perto[j] = 1
                    fila.append(j)
    claro_img = Image.new("L", (W, H), 0); cp = claro_img.load()
    for y in range(H):
        b = y * W
        for x in range(W):
            if sil[b + x]:
                p = px[x, y]
                if min(p) >= 210 and max(p) - min(p) <= 35: cp[x, y] = 255
    aberto = claro_img.filter(ImageFilter.MinFilter(k)).filter(ImageFilter.MaxFilter(k))
    ap = aberto.load(); tirados = 0
    for y in range(H):
        b = y * W
        for x in range(W):
            i = b + x
            if sil[i] and perto[i] and cp[x, y] and not ap[x, y]:
                sil[i] = 0; tirados += 1
    return tirados
