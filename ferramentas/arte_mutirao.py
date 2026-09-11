"""Gera a arte do Mutirão (mutirao/arte.jpg) e a prévia do WhatsApp (mutirao/previa-whatsapp.jpg).

Parte da arte original do designer e acrescenta embaixo: "CLIQUE NA ARTE", o bloco de voto
e o botão do Instagram. Imprime as áreas clicáveis em % para colar em mutirao/index.html.
Uso: python3 ferramentas/arte_mutirao.py <arte-original.jpg>
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

RAIZ = Path(__file__).resolve().parent.parent / "mutirao"
NAVY, NAVY_ESCURO, OURO, BRANCO = (14, 42, 122), (9, 27, 84), (255, 199, 44), (255, 255, 255)
CONDENSADA = "/System/Library/Fonts/Avenir Next Condensed.ttc"
AVENIR = "/System/Library/Fonts/Avenir Next.ttc"
S = 3  # supersample para bordas lisas


def fonte(caminho, nome, tamanho):
    for i in range(30):
        try:
            f = ImageFont.truetype(caminho, tamanho, index=i)
        except OSError:
            break
        if " ".join(f.getname()).lower() == nome.lower():
            return f
    raise SystemExit(f"fonte não encontrada: {nome}")


def texto_centro(d, cx, cy, txt, f, cor):
    x0, y0, x1, y1 = f.getbbox(txt)
    d.text((cx - (x0 + x1) / 2, cy - (y0 + y1) / 2), txt, font=f, fill=cor)


def texto_meio(d, x, cy, txt, f, cor):
    _, y0, _, y1 = f.getbbox(txt)
    d.text((x, cy - (y0 + y1) / 2), txt, font=f, fill=cor)


def icone_toque(d, cx, cy, r, cor):
    d.ellipse((cx - r * .34, cy - r * .34, cx + r * .34, cy + r * .34), fill=cor)
    d.ellipse((cx - r * .66, cy - r * .66, cx + r * .66, cy + r * .66), outline=cor, width=int(r * .12))
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=cor + (120,), width=int(r * .08))


def icone_instagram(camada, x, y, diam):
    paradas = [(0, (254, 218, 117)), (.3, (250, 126, 30)), (.55, (214, 41, 118)), (.8, (150, 47, 191)), (1, (79, 91, 213))]
    g = Image.new("RGBA", (diam, diam))
    px = g.load()
    for yy in range(diam):
        for xx in range(diam):
            t = (xx + (diam - yy)) / (2 * diam)
            for (a, ca), (b, cb) in zip(paradas, paradas[1:]):
                if a <= t <= b:
                    k = (t - a) / (b - a)
                    px[xx, yy] = tuple(int(ca[i] + (cb[i] - ca[i]) * k) for i in range(3)) + (255,)
                    break
    m = Image.new("L", (diam, diam), 0)
    ImageDraw.Draw(m).ellipse((0, 0, diam - 1, diam - 1), fill=255)
    camada.paste(g, (x, y), m)
    d = ImageDraw.Draw(camada)
    q = diam * .52; qx, qy = x + (diam - q) / 2, y + (diam - q) / 2; w = int(diam * .07)
    d.rounded_rectangle((qx, qy, qx + q, qy + q), int(q * .28), outline="white", width=w)
    r = q * .23
    d.ellipse((qx + q / 2 - r, qy + q / 2 - r, qx + q / 2 + r, qy + q / 2 + r), outline="white", width=w)
    p = q * .055
    d.ellipse((qx + q * .76 - p, qy + q * .24 - p, qx + q * .76 + p, qy + q * .24 + p), fill="white")


def gerar(origem):
    arte = Image.open(origem).convert("RGB")
    W, H = arte.size
    PAINEL, FUSAO = 440, 110
    NH = H + PAINEL
    saida = Image.new("RGB", (W, NH), NAVY)
    saida.paste(arte, (0, 0))

    # degrade marinho que funde com o pé da arte
    inicio = H - FUSAO
    grad = Image.new("RGB", (1, NH)); mask = Image.new("L", (1, NH))
    for y in range(NH):
        t = max(0.0, min(1.0, (y - inicio) / (NH - inicio)))
        grad.putpixel((0, y), tuple(int(NAVY[i] + (NAVY_ESCURO[i] - NAVY[i]) * t) for i in range(3)))
        mask.putpixel((0, y), 0 if y < inicio else 255 if y >= H else int(255 * ((y - inicio) / FUSAO) ** 1.4))
    saida.paste(grad.resize((W, NH)), (0, 0), mask.resize((W, NH)))

    L = Image.new("RGBA", (W * S, PAINEL * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)

    # 1) CLIQUE NA ARTE
    f_clique = fonte(CONDENSADA, "Avenir Next Condensed Heavy", 84 * S)
    cy = 62 * S
    rotulo = "CLIQUE NA ARTE"
    larg = 70 * S + 22 * S + f_clique.getlength(rotulo)
    x = (W * S - larg) / 2
    icone_toque(d, x + 35 * S, cy, 34 * S, OURO)
    texto_meio(d, x + 92 * S, cy, rotulo, f_clique, OURO)

    # 2) VOTE 4001 | DEPUTADO FEDERAL | PSB
    bx0, by0, bx1, by1 = 44 * S, 118 * S, (W - 44) * S, 278 * S
    sombra = Image.new("RGBA", L.size, (0, 0, 0, 0))
    ImageDraw.Draw(sombra).rounded_rectangle((bx0, by0 + 8 * S, bx1, by1 + 8 * S), 30 * S, fill=(0, 0, 0, 110))
    L = Image.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(10 * S)), L)
    d = ImageDraw.Draw(L)
    d.rounded_rectangle((bx0, by0, bx1, by1), 30 * S, fill=OURO)
    f_vote = fonte(CONDENSADA, "Avenir Next Condensed Heavy", 66 * S)
    f_num = fonte(AVENIR, "Avenir Next Heavy", 138 * S)
    f_cargo = fonte(CONDENSADA, "Avenir Next Condensed Heavy", 50 * S)
    f_psb = fonte(CONDENSADA, "Avenir Next Condensed Heavy", 46 * S)
    vy = (by0 + by1) / 2
    w_vote, w_num = f_vote.getlength("VOTE"), f_num.getlength("4001")
    w_cargo = max(f_cargo.getlength("DEPUTADO"), f_cargo.getlength("FEDERAL"))
    w_psb = f_psb.getlength("PSB") + 36 * S
    total = w_vote + 22 * S + w_num + 30 * S + 5 * S + 30 * S + w_cargo + 30 * S + w_psb
    x = (W * S - total) / 2
    texto_meio(d, x, vy, "VOTE", f_vote, NAVY); x += w_vote + 22 * S
    texto_meio(d, x, vy + 4 * S, "4001", f_num, NAVY); x += w_num + 30 * S
    d.rounded_rectangle((x, vy - 48 * S, x + 5 * S, vy + 48 * S), 3 * S, fill=NAVY); x += 5 * S + 30 * S
    texto_meio(d, x, vy - 27 * S, "DEPUTADO", f_cargo, NAVY)
    texto_meio(d, x, vy + 29 * S, "FEDERAL", f_cargo, NAVY); x += w_cargo + 30 * S
    d.rounded_rectangle((x, vy - 34 * S, x + w_psb, vy + 34 * S), 34 * S, fill=NAVY)
    texto_centro(d, x + w_psb / 2, vy, "PSB", f_psb, BRANCO)

    # 3) ME SIGA NO INSTAGRAM @samuelenfermeiro
    f_bt = fonte(CONDENSADA, "Avenir Next Condensed Heavy", 54 * S)
    f_arroba = fonte(AVENIR, "Avenir Next Bold", 40 * S)
    PH, CD, PAD = 104 * S, 80 * S, 12 * S
    rot, arroba = "ME SIGA NO INSTAGRAM", "@samuelenfermeiro"
    pw = int(PAD + CD + 22 * S + f_bt.getlength(rot) + 34 * S)
    total = pw + 26 * S + f_arroba.getlength(arroba)
    px0, py0 = int((W * S - total) / 2), 318 * S
    sombra = Image.new("RGBA", L.size, (0, 0, 0, 0))
    ImageDraw.Draw(sombra).rounded_rectangle((px0, py0 + 8 * S, px0 + pw, py0 + PH + 8 * S), PH // 2, fill=(0, 0, 0, 110))
    L = Image.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(10 * S)), L)
    d = ImageDraw.Draw(L)
    d.rounded_rectangle((px0, py0, px0 + pw, py0 + PH), PH // 2, fill=BRANCO)
    icone_instagram(L, px0 + PAD, py0 + (PH - CD) // 2, CD)
    d = ImageDraw.Draw(L)
    texto_meio(d, px0 + PAD + CD + 22 * S, py0 + PH / 2, rot, f_bt, NAVY)
    texto_meio(d, px0 + pw + 26 * S, py0 + PH / 2, arroba, f_arroba, OURO)

    L = L.resize((W, PAINEL), Image.LANCZOS)
    saida.paste(L, (0, H), L)
    saida.save(RAIZ / "arte.jpg", quality=88, optimize=True, progressive=True)

    # prévia 1200x630: arte inteira no centro, chamadas grandes nas laterais
    PW, PHv, E = 1200, 630, 2
    fundo = saida.copy(); k = max(PW / fundo.width, PHv / fundo.height)
    fundo = fundo.resize((int(fundo.width * k) + 1, int(fundo.height * k) + 1), Image.LANCZOS)
    l, t = (fundo.width - PW) // 2, (fundo.height - PHv) // 2
    fundo = ImageEnhance.Brightness(fundo.crop((l, t, l + PW, t + PHv)).filter(ImageFilter.GaussianBlur(30))).enhance(.42)
    frente = saida.resize((round(W * PHv / NH), PHv), Image.LANCZOS)
    fundo.paste(frente, ((PW - frente.width) // 2, 0))
    lado = (PW - frente.width) / 2
    C = Image.new("RGBA", (PW * E, PHv * E), (0, 0, 0, 0)); d = ImageDraw.Draw(C)
    ce = lado / 2 * E
    icone_toque(d, ce, 190 * E, 44 * E, OURO)
    texto_centro(d, ce, 300 * E, "CLIQUE", fonte(CONDENSADA, "Avenir Next Condensed Heavy", 92 * E), BRANCO)
    texto_centro(d, ce, 392 * E, "NA ARTE", fonte(CONDENSADA, "Avenir Next Condensed Heavy", 92 * E), OURO)
    cd = (PW - lado / 2) * E
    texto_centro(d, cd, 196 * E, "VOTE", fonte(CONDENSADA, "Avenir Next Condensed Heavy", 58 * E), OURO)
    texto_centro(d, cd, 292 * E, "4001", fonte(AVENIR, "Avenir Next Heavy", 112 * E), BRANCO)
    texto_centro(d, cd, 382 * E, "DEPUTADO FEDERAL", fonte(CONDENSADA, "Avenir Next Condensed Heavy", 42 * E), BRANCO)
    f_p = fonte(CONDENSADA, "Avenir Next Condensed Heavy", 38 * E); wp = f_p.getlength("PSB") + 40 * E
    d.rounded_rectangle((cd - wp / 2, 428 * E, cd + wp / 2, 482 * E), 27 * E, fill=OURO)
    texto_centro(d, cd, 455 * E, "PSB", f_p, NAVY)
    C = C.resize((PW, PHv), Image.LANCZOS)
    fundo.paste(C, (0, 0), C)
    fundo.save(RAIZ / "previa-whatsapp.jpg", quality=86, optimize=True, progressive=True)

    pct = lambda v, tot: f"{100 * v / tot:.2f}%"
    print(f"arte {W}x{NH}")
    print("botao-grupo", pct(70, W), pct(448, NH), pct(470, W), pct(100, NH))
    print("qr-grupo   ", pct(74, W), pct(560, NH), pct(330, W), pct(408, NH))
    print("faixa-insta", "0%", pct(H + 300, NH), "100%", pct(PAINEL - 300, NH))
    return saida, fundo


if __name__ == "__main__":
    saida, previa = gerar(sys.argv[1])
    if len(sys.argv) > 2:
        destino = Path(sys.argv[2]); destino.mkdir(parents=True, exist_ok=True)
        saida.resize((600, round(600 * saida.height / saida.width))).save(destino / "arte.jpg", quality=85)
        previa.resize((800, 420)).save(destino / "previa.jpg", quality=85)
