"""Geometria do sensor patch de 2,45 GHz com alimentação por inset, em FR-4.

Este arquivo é a fonte única das dimensões. O Gerber, o desenho cotado e a
simulação usam o mesmo polígono do cobre de cima.

Sistema de coordenadas (mm), igual ao da simulação:

    x       direção da linha de alimentação e do comprimento L do patch
    y       direção da largura W do patch
    z = 0   plano de terra (face de baixo, cobre inteiro)
    z = h   cobre de cima (patch e linha)

A placa vai de -placa_x/2 a +placa_x/2 em x e de -placa_y/2 a +placa_y/2 em y.
O conector SMA fica na borda x = -placa_x/2. No Gerber, a origem vai para o
canto inferior esquerdo da placa, como é costume.

Rodar este arquivo grava os Gerber em ./gerber e o desenho cotado em ./resultados:

    python geometria.py
"""

import zipfile
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

C0_MM_GHZ = 299.792458  # velocidade da luz em mm·GHz
AQUI = Path(__file__).resolve().parent
NOME = "patch_2g45"


@dataclass(frozen=True)
class Antena:
    """Dimensões em mm. Os valores padrão são o projeto final.

    O ajuste de L e do inset foi feito com a antena sobre a amostra seca (10 mm de
    polímero sobre metal, gap de 3 mm), que é a condição de uso do sensor. W e a
    placa são pequenos de propósito: o sensor não precisa irradiar bem.
    """

    L: float = 30.0        # comprimento do patch (define a ressonância)
    W: float = 20.0        # largura do patch
    inset: float = 13.5    # profundidade do recorte do inset, a partir da borda do patch
    gap: float = 1.0       # folga entre a linha e o patch, dentro do inset
    linha_w: float = 3.0   # largura da linha de 50 ohm
    placa_x: float = 45.0
    placa_y: float = 32.0
    margem_tras: float = 6.0   # da borda de trás do patch até a borda da placa
    # substrato
    h: float = 1.6
    er: float = 4.4
    tand: float = 0.02
    cobre_um: float = 35.0  # espessura do cobre, em micrômetros
    f_projeto: float = 2.45  # GHz

    # ---------------------------------------------------------------- posições
    @property
    def x_borda(self):
        """Borda da placa onde fica o SMA (x mínimo)."""
        return -self.placa_x / 2

    @property
    def x_patch(self):
        """Borda do patch do lado da linha."""
        return self.placa_x / 2 - self.margem_tras - self.L

    @property
    def comprimento_linha(self):
        """Da borda da placa até a borda do patch (sem contar o trecho dentro do inset)."""
        return self.x_patch - self.x_borda

    def poligono(self):
        """Contorno do cobre de cima (patch + linha), em sentido anti-horário.

        Retorna uma lista de pontos (x, y) em mm, sem repetir o primeiro ponto.
        """
        xe, xl, xr = self.x_borda, self.x_patch, self.x_patch + self.L
        xi = xl + self.inset
        a = self.linha_w / 2
        b = a + self.gap
        w = self.W / 2
        return [(xe, -a), (xi, -a), (xi, -b), (xl, -b), (xl, -w), (xr, -w),
                (xr, w), (xl, w), (xl, b), (xi, b), (xi, a), (xe, a)]

    def com_desbaste(self, d):
        """Antena com o cobre de cima recuado `d` mm em todas as bordas.

        Representa a fresa que come um pouco além da linha (d > 0). A linha fica
        mais estreita, a folga do inset fica mais larga e o patch fica menor.
        """
        r = lambda v: round(v, 4)
        return replace(self, L=r(self.L - 2 * d), W=r(self.W - 2 * d), linha_w=r(self.linha_w - 2 * d),
                       gap=r(self.gap + 2 * d), inset=r(self.inset + d),
                       margem_tras=r(self.margem_tras + d))

    def __str__(self):
        return (f"Patch {self.f_projeto} GHz: L = {self.L} mm, W = {self.W} mm, "
                f"inset = {self.inset} mm, folga = {self.gap} mm, linha = {self.linha_w} mm; "
                f"placa {self.placa_x:g} x {self.placa_y:g} mm, FR-4 {self.h} mm (er = {self.er})")


def projeto_inicial(f_ghz=2.45, er=4.4, h=1.6):
    """Ponto de partida pelas fórmulas clássicas (Balanis, cap. 14).

    A simulação corrige L e o inset. O resultado fica em Antena() (valores padrão).
    """
    lambda0 = C0_MM_GHZ / f_ghz
    W = lambda0 / 2 * np.sqrt(2 / (er + 1))
    er_ef = (er + 1) / 2 + (er - 1) / 2 / np.sqrt(1 + 12 * h / W)
    dl = 0.412 * h * ((er_ef + 0.3) * (W / h + 0.264)) / ((er_ef - 0.258) * (W / h + 0.8))
    L = lambda0 / (2 * np.sqrt(er_ef)) - 2 * dl
    # profundidade do inset para 50 ohm em FR-4 (ajuste empírico de Ramesh e Yip)
    poli = (0.001699 * er**7 + 0.13761 * er**6 - 6.1783 * er**5 + 93.187 * er**4
            - 682.69 * er**3 + 2561.9 * er**2 - 4043 * er + 6697)
    inset = 1e-4 * poli * L / 2
    # largura da linha de 50 ohm (Hammerstad, w/h > 2)
    B = 377 * np.pi / (2 * 50 * np.sqrt(er))
    linha_w = h * 2 / np.pi * (B - 1 - np.log(2 * B - 1)
                               + (er - 1) / (2 * er) * (np.log(B - 1) + 0.39 - 0.61 / er))
    return dict(L=round(L, 2), W=round(W, 2), inset=round(inset, 2), linha_w=round(linha_w, 2),
                er_ef=round(er_ef, 3))


# ==================================================================== Gerber

def _coord(v):
    """mm -> inteiro do formato 4.6 (micrômetro / 1000)."""
    return int(round(v * 1e6))


def _cabecalho(funcao, polaridade="Positive"):
    return [
        "%TF.GenerationSoftware,openEMS-lab,patch_2g45,1.0*%",
        f"%TF.FileFunction,{funcao}*%",
        f"%TF.FilePolarity,{polaridade}*%",
        "%FSLAX46Y46*%",
        "%MOMM*%",
        "%LPD*%",
        "G01*",
    ]


def _regiao(pontos, dx, dy):
    linhas = ["G36*"]
    for i, (x, y) in enumerate(list(pontos) + [pontos[0]]):
        op = "D02" if i == 0 else "D01"
        linhas.append(f"X{_coord(x + dx)}Y{_coord(y + dy)}{op}*")
    linhas.append("G37*")
    return linhas


def gravar_gerber(antena=None, pasta=None):
    """Grava cobre de cima, cobre de baixo e contorno da placa. Retorna a lista de arquivos."""
    a = antena or Antena()
    pasta = Path(pasta or AQUI / "gerber")
    pasta.mkdir(parents=True, exist_ok=True)
    dx, dy = a.placa_x / 2, a.placa_y / 2  # origem no canto inferior esquerdo
    placa = [(-dx, -dy), (dx, -dy), (dx, dy), (-dx, dy)]

    arquivos = {}
    arquivos[f"{NOME}-F_Cu.gbr"] = (_cabecalho("Copper,L1,Top") + _regiao(a.poligono(), dx, dy)
                                    + ["M02*"])
    arquivos[f"{NOME}-B_Cu.gbr"] = (_cabecalho("Copper,L2,Bot") + _regiao(placa, dx, dy)
                                    + ["M02*"])
    contorno = _cabecalho("Profile,NP") + ["%ADD10C,0.100000*%", "D10*"]
    for i, (x, y) in enumerate(placa + [placa[0]]):
        contorno.append(f"X{_coord(x + dx)}Y{_coord(y + dy)}{'D02' if i == 0 else 'D01'}*")
    arquivos[f"{NOME}-Edge_Cuts.gbr"] = contorno + ["M02*"]

    gravados = []
    for nome, linhas in arquivos.items():
        caminho = pasta / nome
        caminho.write_text("\n".join(linhas) + "\n", encoding="ascii", newline="\n")
        gravados.append(caminho)

    pacote = AQUI / f"{NOME}_gerber.zip"
    with zipfile.ZipFile(pacote, "w", zipfile.ZIP_DEFLATED) as z:
        for caminho in gravados:
            z.write(caminho, caminho.name)
    return gravados + [pacote]


# ==================================================================== desenho cotado

def desenhar(antena=None, arquivo=None):
    """Desenho do cobre de cima com as cotas, para conferir a placa depois de fresada."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon, Rectangle

    a = antena or Antena()
    fig, ax = plt.subplots(figsize=(8, 7.6))
    ax.add_patch(Rectangle((a.x_borda, -a.placa_y / 2), a.placa_x, a.placa_y,
                           facecolor="#d9c89a", edgecolor="k", lw=1))
    ax.add_patch(Polygon(a.poligono(), closed=True, facecolor="#c87533", edgecolor="#7a3f12", lw=1))

    fundo = dict(fc="white", ec="none", pad=1)

    def cota(p1, p2, texto, desloc, lado="y"):
        (x1, y1), (x2, y2) = p1, p2
        if lado == "y":  # cota horizontal, deslocada em y
            ax.annotate("", (x1, y1 + desloc), (x2, y2 + desloc),
                        arrowprops=dict(arrowstyle="<->", lw=0.8))
            ax.text((x1 + x2) / 2, y1 + desloc + 0.8, texto, ha="center", va="bottom", fontsize=9,
                    bbox=fundo)
        else:  # cota vertical, deslocada em x
            ax.annotate("", (x1 + desloc, y1), (x2 + desloc, y2),
                        arrowprops=dict(arrowstyle="<->", lw=0.8))
            ax.text(x1 + desloc + 0.8, (y1 + y2) / 2, texto, ha="left", va="center", fontsize=9,
                    rotation=90, bbox=fundo)

    xl, xr = a.x_patch, a.x_patch + a.L
    yt, yb = a.W / 2, -a.W / 2
    cota((xl, yt), (xr, yt), f"L = {a.L} mm", 3)
    cota((xr, yb), (xr, yt), f"W = {a.W} mm", 3, lado="x")
    cota((xl, yb), (xl + a.inset, yb), f"inset = {a.inset} mm", -3)
    cota((a.x_borda, a.linha_w / 2), (xl, a.linha_w / 2), f"linha {a.comprimento_linha:.1f} mm", 4)
    ax.annotate(f"largura da linha = {a.linha_w} mm\nfolga do inset = {a.gap} mm",
                (xl + a.inset / 2, -a.linha_w / 2 - a.gap / 2), (a.x_borda, -a.placa_y / 2 - 13),
                fontsize=9, arrowprops=dict(arrowstyle="->", lw=0.8))
    cota((a.x_borda, -a.placa_y / 2), (-a.x_borda, -a.placa_y / 2), f"placa {a.placa_x:g} mm", -4)
    cota((-a.x_borda, -a.placa_y / 2), (-a.x_borda, a.placa_y / 2), f"placa {a.placa_y:g} mm", 3,
         lado="x")
    ax.annotate("SMA de borda", (a.x_borda, 0), (a.x_borda - 13, 12), fontsize=9,
                arrowprops=dict(arrowstyle="->", lw=0.8))

    ax.plot(a.x_borda, -a.placa_y / 2, "ko", ms=4)
    ax.annotate("origem do Gerber (0, 0)", (a.x_borda, -a.placa_y / 2), (a.x_borda - 14, -a.placa_y / 2 - 3),
                fontsize=8)
    ax.set_xlim(a.x_borda - 15, -a.x_borda + 10)
    ax.set_ylim(-a.placa_y / 2 - 15, a.placa_y / 2 + 6)
    ax.set_aspect("equal")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_title(f"Cobre de cima (vista de cima). Embaixo: plano de terra inteiro.\n"
                 f"FR-4 {a.h} mm, cobre {a.cobre_um:g} µm")
    ax.grid(alpha=0.2)
    fig.tight_layout()
    arquivo = Path(arquivo or AQUI / "resultados" / "desenho_cotado.png")
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(arquivo, dpi=150)
    plt.close(fig)
    return arquivo


if __name__ == "__main__":
    print("Fórmulas clássicas:", projeto_inicial())
    print("Projeto final:     ", Antena())
    for caminho in gravar_gerber():
        print("gravado:", caminho.relative_to(AQUI))
    print("gravado:", desenhar().relative_to(AQUI))
