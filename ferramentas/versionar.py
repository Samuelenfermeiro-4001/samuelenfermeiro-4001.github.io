"""Recalcula a versao das artes no index.html.

O GitHub Pages manda o navegador guardar as molduras por 10 minutos e o nome do
arquivo nao muda, entao uma arte corrigida podia demorar a aparecer para quem ja
tinha aberto o app. O endereco carrega ?v=<resumo do conteudo>: quando a arte
muda, o resumo muda e o navegador busca a nova na hora.

Rodar sempre que trocar alguma moldura:  python3 ferramentas/versionar.py
"""
import hashlib, io, os, re, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTES = ["assets/molduras/perfil-1x1.webp", "assets/molduras/post-45.webp"]

h = hashlib.sha1()
for nome in ARTES:
    caminho = os.path.join(RAIZ, nome)
    if not os.path.exists(caminho):
        sys.exit("arte ausente: " + nome)
    h.update(open(caminho, "rb").read())
versao = h.hexdigest()[:8]

p = os.path.join(RAIZ, "index.html")
s = io.open(p, encoding="utf-8").read()
novo, n = re.subn(r"var VERSAO = '[0-9a-f]{8}';", "var VERSAO = '%s';" % versao, s)
if n != 1:
    sys.exit("nao encontrei a linha da versao no index.html")
if novo == s:
    print("versao ja estava correta: %s" % versao)
else:
    io.open(p, "w", encoding="utf-8").write(novo)
    print("versao atualizada para %s" % versao)
