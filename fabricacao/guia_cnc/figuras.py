"""Figuras esquemáticas do guia da CNC.

Usa a geometria real do sensor (../patch_2g45/geometria.py). As capturas de tela dos
programas ficam em img/ e não são geradas aqui.

    python figuras.py
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle
from shapely.geometry import Polygon as SPolygon, box
from shapely.ops import unary_union

AQUI = Path(__file__).resolve().parent
IMG = AQUI / "img"
sys.path.insert(0, str(AQUI.parent / "patch_2g45"))
from geometria import Antena  # noqa: E402

A = Antena()
DX, DY = A.placa_x / 2, A.placa_y / 2
COBRE = [(x + DX, y + DY) for x, y in A.poligono()]  # origem no canto inferior esquerdo
PLACA = box(0, 0, A.placa_x, A.placa_y)
BRUTA = (-5, -5, 60, 45)  # placa de FR-4 antes do corte: x0, y0, largura, altura
PROVA = (-3, -3)

COR_COBRE = "#c87533"
COR_FR4 = "#d9c89a"
COR_CORTE = "#1f5fa8"


def _salvar(fig, nome):
    IMG.mkdir(exist_ok=True)
    fig.savefig(IMG / nome, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print("gravado:", (IMG / nome).relative_to(AQUI))


def _base(ax, cobre_bruto=True):
    x0, y0, w, h = BRUTA
    ax.add_patch(Rectangle((x0, y0), w, h, fc=COR_COBRE if cobre_bruto else COR_FR4,
                           ec="k", lw=1, alpha=0.35 if cobre_bruto else 1))
    ax.set_aspect("equal")
    ax.set_xlim(x0 - 4, x0 + w + 4)
    ax.set_ylim(y0 - 4, y0 + h + 4)
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")


def placa_na_mesa():
    fig, ax = plt.subplots(figsize=(7.5, 5.8))
    _base(ax)
    ax.add_patch(Rectangle((0, 0), A.placa_x, A.placa_y, fc="none", ec="k", lw=1.2, ls="--"))
    ax.add_patch(Polygon(COBRE, fc=COR_COBRE, ec="#7a3f12"))
    ax.plot(0, 0, "o", color="crimson", ms=8, zorder=5)
    ax.annotate("origem X = 0, Y = 0\n(canto inferior esquerdo da antena)", (0, 0), (14, -10.5),
                fontsize=8.5, color="crimson", arrowprops=dict(arrowstyle="->", color="crimson"))
    ax.plot(*PROVA, "X", color="navy", ms=10, zorder=5)
    ax.annotate("ponto de prova do Z = 0\n(X = −3, Y = −3, no cobre da margem)", PROVA, (-9, -13),
                fontsize=8.5, color="navy", arrowprops=dict(arrowstyle="->", color="navy"))
    ax.annotate("garra da ponta de prova\nna margem", (52, 40), (36, 43), fontsize=8.5,
                arrowprops=dict(arrowstyle="->"))
    ax.plot(52, 40, "s", color="k", ms=7)
    for x in (A.placa_x / 2,):
        for y in (0, A.placa_y):
            ax.add_patch(Rectangle((x - 0.75, y - 1.5), 1.5, 3, fc="#4caf50", ec="none", zorder=4))
    ax.annotate("pontes (TB)", (A.placa_x / 2, A.placa_y), (A.placa_x / 2 + 4, A.placa_y + 4.5),
                fontsize=8.5, color="#2e7d32", arrowprops=dict(arrowstyle="->", color="#2e7d32"))
    ax.annotate("borda do SMA:\nsem ponte", (0, A.placa_y / 2), (-8.5, 26), fontsize=8.5,
                ha="center", arrowprops=dict(arrowstyle="->"))
    ax.text(A.placa_x - 1, 2.2, "contorno da antena: 45 x 32 mm (tracejado)", ha="right",
            fontsize=8.5)
    ax.set_title("Placa de FR-4 de 60 x 45 mm na mesa (vista de cima)", fontsize=10)
    ax.grid(alpha=0.2)
    ax.set_ylim(-15, 48)
    _salvar(fig, "placa_na_mesa.png")


def fresa_v():
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    ponta, ang, prof, cobre = 0.10, 30.0, 0.08, 0.035
    t = np.tan(np.radians(ang / 2))
    larg = ponta + 2 * prof * t
    # cobre e FR-4 (escala exagerada em Z para mostrar)
    ax.add_patch(Rectangle((-0.6, -0.25), 1.2, 0.25 - cobre, fc=COR_FR4, ec="none"))
    ax.add_patch(Rectangle((-0.6, -cobre), 1.2, cobre, fc=COR_COBRE, ec="none"))
    # sulco
    sulco = [(-larg / 2, 0), (larg / 2, 0), (ponta / 2, -prof), (-ponta / 2, -prof)]
    ax.add_patch(Polygon(sulco, fc="white", ec="k", lw=0.8))
    # fresa
    alt = 0.32
    fresa = [(-ponta / 2, -prof), (ponta / 2, -prof), (ponta / 2 + alt * t, -prof + alt),
             (-ponta / 2 - alt * t, -prof + alt)]
    ax.add_patch(Polygon(fresa, fc="#9e9e9e", ec="k", alpha=0.45))
    ax.annotate("", (-larg / 2, 0.03), (larg / 2, 0.03), arrowprops=dict(arrowstyle="<->"))
    ax.text(0, 0.06, f"largura do corte = {larg:.2f} mm".replace(".", ","), ha="center", fontsize=9,
            bbox=dict(fc="white", ec="none", pad=1))
    ax.annotate("", (0.33, 0), (0.33, -prof), arrowprops=dict(arrowstyle="<->"))
    ax.text(0.35, -prof / 2, f"profundidade {prof:.2f} mm".replace(".", ","), va="center", fontsize=9)
    ax.text(0, -prof - 0.02, f"ponta {ponta:.1f} mm".replace(".", ","), ha="center", va="top", fontsize=9)
    ax.text(-0.58, -cobre / 2, "cobre 35 µm", va="center", fontsize=8.5)
    ax.text(-0.58, -0.17, "FR-4", va="center", fontsize=8.5)
    ax.text(0.0, 0.19, f"fresa em V, {ang:.0f}°", ha="center", fontsize=9,
            bbox=dict(fc="white", ec="none", pad=1))
    ax.text(0.6, -0.24, "largura = ponta + 2 × profundidade × tan(ângulo / 2)", ha="right",
            fontsize=8.5, style="italic")
    ax.set_xlim(-0.6, 0.62)
    ax.set_ylim(-0.25, 0.25)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Corte da fresa em V (vista de lado, sem escala)", fontsize=10)
    _salvar(fig, "fresa_v.png")


def ponta_de_prova():
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 56)
    ax.axis("off")
    # controladora
    ax.add_patch(FancyBboxPatch((3, 30), 26, 20, boxstyle="round,pad=0.6", fc="#e3f2fd", ec="k"))
    ax.text(16, 46, "controladora\nMKS Gen v1.4", ha="center", va="top", fontsize=9)
    ax.plot([29, 33], [36, 36], "k")
    ax.plot([29, 33], [33, 33], "k")
    ax.text(27.5, 36, "PROBE", ha="right", va="center", fontsize=8)
    ax.text(27.5, 33, "GND", ha="right", va="center", fontsize=8)
    # spindle e fresa
    ax.add_patch(Rectangle((52, 34), 12, 18, fc="#bdbdbd", ec="k"))
    ax.text(58, 43, "spindle\n(desligado)", ha="center", va="center", fontsize=8)
    ax.add_patch(Polygon([(57, 34), (59, 34), (58, 21)], fc="#757575", ec="k"))
    # placa
    ax.add_patch(Rectangle((35, 12), 50, 3, fc=COR_FR4, ec="k"))
    ax.add_patch(Rectangle((35, 15), 50, 1, fc=COR_COBRE, ec="none"))
    ax.add_patch(Rectangle((30, 6), 60, 6, fc="#a1887f", ec="k"))
    ax.text(60, 9, "MDF de sacrifício", ha="center", va="center", fontsize=8)
    ax.annotate("", (58, 16.3), (58, 20.5), arrowprops=dict(arrowstyle="->", color="crimson"))
    ax.text(60, 18.5, "desce a 20 mm/min\naté tocar", fontsize=8, color="crimson", va="center")
    # fios
    ax.plot([33, 46, 46, 57.3], [36, 36, 26, 26], color="crimson", lw=1.6)
    ax.plot(57.3, 26, "s", color="crimson", ms=6)
    ax.text(45, 27, "garra na fresa", fontsize=8, color="crimson", ha="right")
    ax.plot([33, 40, 40, 80, 80], [33, 33, 25, 25, 16.3], color="k", lw=1.6)
    ax.plot(80, 16.3, "s", color="k", ms=6)
    ax.text(81.5, 21, "garra no cobre\nda margem", fontsize=8)
    ax.text(50, 1.5, "O circuito fecha no toque. O GRBL para o eixo Z e guarda a altura.",
            ha="center", fontsize=8.5)
    ax.set_title("Ligação da ponta de prova", fontsize=10)
    _salvar(fig, "ponta_de_prova.png")


def mapa_altura():
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    x0, x1, y0, y1 = -1, 46, -1, 33
    X, Y = np.meshgrid(np.linspace(x0, x1, 200), np.linspace(y0, y1, 150))
    Z = 0.0012 * (X - 20) + 0.0008 * (Y - 16) - 0.00006 * ((X - 22) ** 2 + (Y - 16) ** 2) + 0.02
    im = ax.pcolormesh(X, Y, Z * 1000, cmap="coolwarm", shading="auto")
    fig.colorbar(im, ax=ax, label="altura da placa em relação ao Z = 0 (µm)")
    ax.add_patch(Polygon(COBRE, fc="none", ec="k", lw=1))
    ax.add_patch(Rectangle((0, 0), A.placa_x, A.placa_y, fc="none", ec="k", ls="--"))
    px, py = np.meshgrid(np.linspace(x0, x1, 6), np.linspace(y0, y1, 5))
    ax.plot(px, py, "ko", ms=5)
    ax.set_aspect("equal")
    ax.set_xlim(x0 - 2, x1 + 2)
    ax.set_ylim(y0 - 2, y1 + 2)
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")
    ax.set_title("Mapa de altura: 6 x 5 pontos (os valores são um exemplo)", fontsize=10)
    _salvar(fig, "mapa_altura.png")


def caminhos():
    """Ilustração simplificada do que cada arquivo de G-code corta."""
    cobre = SPolygon(COBRE)
    v = 0.14
    iso = [cobre.buffer(v / 2 + i * 0.8 * v, join_style=2).exterior for i in range(2)]
    area = PLACA.difference(cobre.buffer(v * 1.6, join_style=2))
    grossa = area.buffer(-0.4, join_style=2)
    resto = area.difference(grossa.buffer(0.4, join_style=2))
    r = 1.0
    rec = box(-r, -r, A.placa_x + r, A.placa_y + r).exterior
    pontes = unary_union([box(A.placa_x / 2 - 0.75 - r, -5, A.placa_x / 2 + 0.75 + r, 40)])
    rec = rec.difference(pontes)

    fig, axs = plt.subplots(2, 2, figsize=(8.6, 6.8))
    titulos = ["1_isolacao.nc: fresa em V, 2 passes", "2a_remocao_08.nc: fresa de 0,8 mm",
               "2b_remocao_v.nc: fresa em V no resto", "3_recorte.nc: fresa de 2 mm, pontes TB"]
    for ax, tit in zip(axs.flat, titulos):
        _base(ax, cobre_bruto=False)
        ax.add_patch(Polygon(COBRE, fc=COR_COBRE, ec="none", alpha=0.9))
        ax.add_patch(Rectangle((0, 0), A.placa_x, A.placa_y, fc="none", ec="k", ls="--", lw=0.7))
        ax.set_title(tit, fontsize=9)
        ax.tick_params(labelsize=7)
        ax.xaxis.label.set_size(8)
        ax.yaxis.label.set_size(8)

    def linhas(ax, geo, **kw):
        geos = getattr(geo, "geoms", [geo])
        for g in geos:
            if g.is_empty:
                continue
            if g.geom_type == "Polygon":
                ax.add_patch(Polygon(np.array(g.exterior.coords), **kw))
                for i in g.interiors:
                    ax.add_patch(Polygon(np.array(i.coords), fc="white", ec="none"))
            else:
                xs, ys = g.xy
                ax.plot(xs, ys, **{k: v for k, v in kw.items() if k in ("color", "lw")})

    for e in iso:
        linhas(axs[0, 0], e, color=COR_CORTE, lw=0.9)
    linhas(axs[0, 1], grossa.buffer(0.4, join_style=2), fc=COR_CORTE, ec="none", alpha=0.45)
    linhas(axs[1, 0], resto, fc=COR_CORTE, ec="none", alpha=0.9)
    linhas(axs[1, 1], rec, color=COR_CORTE, lw=2.2)
    for ax in axs.flat:
        ax.set_xlim(-6, 51)
        ax.set_ylim(-6, 38)
    fig.suptitle("O que cada arquivo corta (ilustração simplificada; o FlatCAM calcula os caminhos reais)",
                 fontsize=9.5)
    fig.tight_layout()
    _salvar(fig, "caminhos.png")


if __name__ == "__main__":
    placa_na_mesa()
    fresa_v()
    ponta_de_prova()
    mapa_altura()
    caminhos()
