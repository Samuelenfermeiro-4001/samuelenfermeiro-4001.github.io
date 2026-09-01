"""Auditoria das molduras do aplicativo Samuel Enfermeiro.

Verifica, em cada arte publicada:
  1. Buraco unico e conexo (sem bolsoes de placeholder esquecidos)
  2. Sem furos no corpo do candidato (transparencia onde deveria haver arte)
  3. Sem sobra de placeholder encostada no buraco
  4. Qualidade fotografica: banding/posterizacao na pele
  5. Borda do buraco limpa (sem franja clara)
"""
import os, sys, math
from collections import Counter
from PIL import Image

RAIZ = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "molduras")
MOLDURAS = [
    ("perfil-1x1.webp", "Foto de perfil 1:1"),
    ("post-45.webp",    "Post 4:5"),
]

def componentes(mask, W, H, minimo=200):
    """Componentes conexos de uma mascara booleana (lista de bytes)."""
    visto = bytearray(W * H)
    achados = []
    for sy in range(0, H, 2):
        for sx in range(0, W, 2):
            i = sy * W + sx
            if not mask[i] or visto[i]:
                continue
            n = 0
            pilha = [(sx, sy)]
            caixa = [W, 0, H, 0]
            while pilha:
                x, y = pilha.pop()
                j = y * W + x
                if visto[j] or not mask[j]:
                    continue
                xi = x
                while xi >= 0 and not visto[y*W+xi] and mask[y*W+xi]:
                    xi -= 1
                xi += 1
                xf = x
                while xf < W and not visto[y*W+xf] and mask[y*W+xf]:
                    xf += 1
                xf -= 1
                for xx in range(xi, xf + 1):
                    visto[y*W+xx] = 1
                n += xf - xi + 1
                caixa[0] = min(caixa[0], xi); caixa[1] = max(caixa[1], xf)
                caixa[2] = min(caixa[2], y);  caixa[3] = max(caixa[3], y)
                for ny in (y-1, y+1):
                    if 0 <= ny < H:
                        xx = xi
                        while xx <= xf:
                            if not visto[ny*W+xx] and mask[ny*W+xx]:
                                pilha.append((xx, ny))
                                while xx <= xf and mask[ny*W+xx]:
                                    xx += 1
                            xx += 1
            if n >= minimo:
                achados.append((n, tuple(caixa)))
    achados.sort(reverse=True)
    return achados

def auditar(caminho, rotulo):
    im = Image.open(caminho).convert("RGBA")
    W, H = im.size
    px = im.load()
    total = W * H
    achados = []

    vazado = bytearray(total)
    opaco  = bytearray(total)
    for y in range(H):
        base = y * W
        for x in range(W):
            a = px[x, y][3]
            if a < 24:   vazado[base+x] = 1
            elif a > 231: opaco[base+x] = 1

    n_vaz = sum(vazado)

    # 1) buraco unico
    comps = componentes(vazado, W, H, minimo=400)
    if not comps:
        achados.append(("GRAVE", "nenhuma area vazada — a foto nao teria onde entrar"))
    elif len(comps) > 1:
        # o corpo do candidato pode dividir o buraco em duas partes legitimas.
        # so acusa quando a area extra e pequena demais para caber uma foto.
        pequenas = [c for c in comps[1:] if c[0] < 8000]
        if pequenas:
            achados.append(("ATENCAO",
                "%d area(s) vazada(s) pequenas demais (%d px) — provavel furo na arte"
                % (len(pequenas), sum(c[0] for c in pequenas))))

    # 2) furos dentro da arte: vazado pequeno e isolado
    soltos = [c for c in comps[1:] if c[0] < n_vaz * 0.02]
    if soltos:
        achados.append(("ATENCAO", "%d furos pequenos na arte (possivel recorte comendo o candidato)" % len(soltos)))

    # 3) sobra de placeholder: pixels opacos quase-neutros colados no buraco
    sobra = 0
    for y in range(1, H-1):
        for x in range(1, W-1):
            i = y*W+x
            if not opaco[i]:
                continue
            if not (vazado[i-1] or vazado[i+1] or vazado[i-W] or vazado[i+W]):
                continue
            r, g, b, _ = px[x, y]
            neutro = abs(r-g) < 12 and abs(g-b) < 12
            if neutro and (r < 30 or 195 < r < 245):
                sobra += 1
    if sobra > 400:
        achados.append(("ATENCAO", "%d px de placeholder encostados na borda do buraco" % sobra))

    # 4) qualidade fotografica: cores unicas na area do candidato
    cores = Counter()
    amostra = 0
    for y in range(0, H, 2):
        for x in range(0, W, 2):
            i = y*W+x
            if not opaco[i]:
                continue
            r, g, b, _ = px[x, y]
            # tons de pele/cabelo: fora do azul e do amarelo da marca
            if 25 < r < 235 and abs(r-g) > 8 and r > b:
                cores[(r//2, g//2, b//2)] += 1
                amostra += 1
    unicas = len(cores)
    if amostra > 3000 and unicas < 900:
        achados.append(("ATENCAO",
            "poucas cores na pele (%d tons em %d px) — sinal de manchas/posterizacao" % (unicas, amostra)))

    # 5) franja clara na borda do buraco
    franja = 0
    for y in range(1, H-1):
        for x in range(1, W-1):
            i = y*W+x
            if not opaco[i]:
                continue
            if not (vazado[i-1] or vazado[i+1] or vazado[i-W] or vazado[i+W]):
                continue
            r, g, b, _ = px[x, y]
            if r > 238 and g > 238 and b > 238:
                franja += 1
    if franja > 900:
        achados.append(("ATENCAO", "%d px quase brancos na borda do buraco (possivel franja)" % franja))

    return {
        "rotulo": rotulo,
        "dim": "%dx%d" % (W, H),
        "kb": os.path.getsize(caminho)//1024,
        "vazado_pct": 100.0*n_vaz/total,
        "areas_vazadas": len(comps),
        "tons_pele": unicas,
        "sobra_borda": sobra,
        "franja": franja,
        "achados": achados,
    }

print("=" * 74)
print("AUDITORIA DAS MOLDURAS")
print("=" * 74)
problemas = 0
for arq, rotulo in MOLDURAS:
    caminho = os.path.join(RAIZ, arq)
    if not os.path.exists(caminho):
        print("\n%-22s AUSENTE" % rotulo); problemas += 1; continue
    r = auditar(caminho, rotulo)
    print("\n%s  (%s, %d KB)" % (r["rotulo"], r["dim"], r["kb"]))
    print("   buraco ocupa %.1f%% da arte, em %d area(s)" % (r["vazado_pct"], r["areas_vazadas"]))
    print("   tons distintos na pele: %d" % r["tons_pele"])
    print("   placeholder na borda: %d px | franja clara: %d px" % (r["sobra_borda"], r["franja"]))
    if not r["achados"]:
        print("   -> SEM PROBLEMAS")
    for nivel, msg in r["achados"]:
        print("   -> %s: %s" % (nivel, msg))
        problemas += 1

print("\n" + "=" * 74)
print("RESULTADO: %s" % ("nenhum problema encontrado" if problemas == 0
                         else "%d ponto(s) para revisar" % problemas))
print("=" * 74)
