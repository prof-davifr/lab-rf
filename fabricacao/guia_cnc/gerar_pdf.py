"""Gera GUIA_CNC.pdf a partir de GUIA_CNC.md.

Precisa do pacote Python `markdown` e do programa `weasyprint` (os dois são livres):

    pip install markdown weasyprint
    python gerar_pdf.py

As figuras numeradas vêm das imagens do Markdown. O texto entre colchetes vira a legenda,
e o título da imagem (entre aspas, depois do arquivo) vira a fonte. Sem título, a fonte é
"autoria própria".
"""

import html
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

import markdown
from markdown.extensions.toc import TocExtension, slugify_unicode

AQUI = Path(__file__).resolve().parent
ORIGEM = AQUI / "GUIA_CNC.md"
DESTINO = AQUI / "GUIA_CNC.pdf"
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro"]

CSS = """
@page {
  size: A4; margin: 22mm 20mm 22mm 20mm;
  @top-right { content: "Guia da fresadora CNC"; font-size: 8pt; color: #777; }
  @bottom-center { content: counter(page) " de " counter(pages); font-size: 8pt; color: #777; }
}
@page capa { @top-right { content: none; } @bottom-center { content: none; } }
html { font-family: "Noto Sans", "DejaVu Sans", sans-serif; font-size: 10pt; line-height: 1.4;
       color: #1a1a1a; }
.capa { page: capa; height: 240mm; display: flex; flex-direction: column;
        justify-content: center; text-align: center; }
.capa h1 { font-size: 24pt; margin: 0 0 8mm 0; border: none; }
.capa .sub { font-size: 12pt; color: #444; margin: 0 20mm; }
.capa .data { margin-top: 20mm; font-size: 11pt; color: #444; }
.capa img { width: 120mm; margin: 12mm auto 0 auto; }
nav.sumario { break-after: page; }
nav.sumario h2 { break-before: auto; }
nav.sumario ol { list-style: none; padding: 0; }
nav.sumario li { margin: 2.2mm 0; }
nav.sumario a { color: #1a1a1a; text-decoration: none; }
nav.sumario ol a::after { content: leader(".") target-counter(attr(href), page); }
h1, h2, h3 { color: #12355b; line-height: 1.2; }
h2 { font-size: 15pt; break-before: page; border-bottom: 1.5pt solid #12355b;
     padding-bottom: 2mm; }
h2.continua { break-before: auto; }
h3 { font-size: 11.5pt; margin-top: 6mm; break-after: avoid; }
p, li { orphans: 3; widows: 3; }
a { color: #1f5fa8; text-decoration: none; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 8.8pt; background: #f2f2f2;
       padding: 0 1pt; }
pre { background: #f2f2f2; padding: 3mm; font-size: 8.3pt; break-inside: avoid;
      white-space: pre-wrap; overflow-wrap: anywhere; }
pre code { background: none; }
table { border-collapse: collapse; width: 100%; margin: 3mm 0 4mm 0; font-size: 8.8pt;
        break-inside: auto; }
th { background: #12355b; color: white; text-align: left; }
th, td { border: 0.5pt solid #b0b0b0; padding: 1.3mm 2mm; vertical-align: top; }
tr { break-inside: avoid; }
tr:nth-child(even) td { background: #f6f8fb; }
figure { margin: 4mm 0 5mm 0; text-align: center; break-inside: avoid; }
figure img { max-width: 100%; max-height: 115mm; }
figcaption { font-size: 8.8pt; margin-top: 1.5mm; }
figcaption .fonte { display: block; color: #555; }
strong { color: #000; }
hr { display: none; }
"""


def _figuras(corpo):
    """<p><img ...></p> -> <figure> com legenda numerada e fonte."""
    n = 0

    def troca(m):
        nonlocal n
        n += 1
        atributos = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        legenda = atributos.get("alt", "")
        fonte = atributos.get("title") or "autoria própria"
        return (f'<figure><img src="{atributos["src"]}" alt="{legenda}">'
                f'<figcaption><b>Figura {n}</b> – {legenda}'
                f'<span class="fonte">Fonte: {fonte}.</span></figcaption></figure>')

    return re.sub(r"<p><img ([^>]*?)\s*/?></p>", troca, corpo)


def _recuos(texto):
    """O Python-Markdown pede 4 espaços em listas aninhadas; o GitHub aceita 2 ou 3.

    Também troca o bloco ``` dentro de uma lista por um bloco recuado, que o
    Python-Markdown aceita dentro de um item.
    """
    saida, dentro = [], None
    for linha in texto.splitlines():
        m = re.match(r"^( {2,3})```", linha)
        if dentro is None and m:
            dentro = len(m.group(1))
            saida.append("")
            continue
        if dentro is not None:
            if linha.strip() == "```":
                dentro = None
                saida.append("")
            else:
                saida.append(" " * 8 + linha[dentro:])
            continue
        m = re.match(r"^( {2,3})(\S.*)$", linha)
        if m:
            linha = " " * 4 + m.group(2)
        # item da lista de fora logo depois de um subitem: sem a linha em branco, o
        # Python-Markdown junta o item ao subitem
        if re.match(r"^(\d+\.|[-*]) ", linha) and saida and saida[-1].startswith("    "):
            saida.append("")
        saida.append(linha)
    return "\n".join(saida)


def montar_html():
    texto = ORIGEM.read_text(encoding="utf-8")
    titulo = texto.splitlines()[0].lstrip("# ").strip()
    texto = "\n".join(texto.splitlines()[1:])
    # o PDF tem sumário próprio, com páginas
    texto = re.sub(r"\n## Sumário\n.*?\n---\n", "\n", texto, flags=re.S)
    texto = texto.replace("- [ ] ", "- ☐ ")
    texto = _recuos(texto)
    # a introdução (antes da primeira seção) vai para a página do sumário
    intro, _, resto = texto.partition("\n## ")
    resto = "## " + resto

    ext = ["tables", "fenced_code", "sane_lists",
           TocExtension(slugify=slugify_unicode, toc_depth="2-2")]
    corpo = markdown.markdown(resto, extensions=ext)
    corpo = _figuras(corpo)
    intro_html = markdown.markdown(intro, extensions=["sane_lists"])

    itens = re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', corpo)
    sumario = "".join(f'<li><a href="#{i}">{t}</a></li>' for i, t in itens)
    hoje = date.today()
    capa = (f'<section class="capa"><h1>{html.escape(titulo)}</h1>'
            f'<p class="sub">Da placa de FR-4 à antena pronta para o conector, só com programas '
            f'livres: FlatCAM, bCNC e GRBL</p>'
            f'<img src="img/placa_na_mesa.png" alt="">'
            f'<p class="data">{MESES[hoje.month - 1]} de {hoje.year}</p></section>')
    nav = (f'<nav class="sumario">{intro_html}<h2 class="continua">Sumário</h2>'
           f'<ol>{sumario}</ol></nav>')
    return (f'<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">'
            f'<title>{html.escape(titulo)}</title><style>{CSS}</style></head>'
            f'<body>{capa}{nav}{corpo}</body></html>')


def main():
    weasy = shutil.which("weasyprint")
    if not weasy:
        sys.exit("weasyprint não encontrado. Instale com: pip install weasyprint")
    with tempfile.TemporaryDirectory() as tmp:
        arq = Path(tmp) / "guia.html"
        arq.write_text(montar_html(), encoding="utf-8")
        subprocess.run([weasy, "-q", "-u", AQUI.as_uri() + "/", str(arq), str(DESTINO)],
                       check=True)
    print("gravado:", DESTINO.name)


if __name__ == "__main__":
    main()
