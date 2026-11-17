"""Figuras do guia do VNA.

Usa o S11 simulado do sensor (../projetos/patch_2g45/resultados).

    python figuras.py
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

AQUI = Path(__file__).resolve().parent
IMG = AQUI / "img"
PROJETO = AQUI.parent / "projetos" / "patch_2g45"
sys.path.insert(0, str(PROJETO))
from comparar import analisar, ler_s1p  # noqa: E402


def _salvar(fig, nome):
    IMG.mkdir(exist_ok=True)
    fig.savefig(IMG / nome, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print("gravado:", (IMG / nome).relative_to(AQUI))


def _virgula(v, casas):
    return f"{v:.{casas}f}".replace(".", ",")


def s11_lido():
    f, s = ler_s1p(PROJETO / "resultados" / "s11_amostra_seca.s1p")
    db = 20 * np.log10(np.abs(s))
    fres, smin, (f1, f2) = analisar(f, s)
    fig, ax = plt.subplots(figsize=(7.5, 4.3))
    ax.plot(f, db, color="#1f5fa8", lw=2)
    ax.axhline(-10, color="crimson", lw=1, ls="--")
    ax.text(f[0] + 0.01, -9.4, "−10 dB: 10 % da potência volta", color="crimson", fontsize=8.5)
    ax.plot(fres, smin, "ko")
    ax.annotate(f"ressonância: {_virgula(fres, 3)} GHz\nS11 mínimo: {_virgula(smin, 1).replace('-', '−')} dB",
                (fres, smin), (fres + 0.12, smin + 1), fontsize=9,
                arrowprops=dict(arrowstyle="->"))
    ax.annotate("", (f1, -12.5), (f2, -12.5), arrowprops=dict(arrowstyle="<->", color="#2e7d32"))
    ax.text(f2 + 0.03, -12.5,
            f"faixa abaixo de −10 dB:\n{_virgula(f1, 3)} a {_virgula(f2, 3)} GHz",
            fontsize=8.5, color="#2e7d32", va="center")
    ax.set_xlabel("frequência (GHz)")
    ax.set_ylabel("|S11| (dB)")
    ax.set_xlim(f[0], f[-1])
    ax.grid(alpha=0.3)
    ax.set_title("Como ler o |S11| (exemplo: sensor sobre a amostra seca, simulado)", fontsize=10)
    _salvar(fig, "s11_lido.png")


def _grade_smith(ax):
    ax.add_patch(Circle((0, 0), 1, fill=False, lw=1.2))
    for r in (0.2, 0.5, 1, 2, 5):
        ax.add_patch(Circle((r / (1 + r), 0), 1 / (1 + r), fill=False, lw=0.5, color="0.6"))
    t = np.linspace(0, 2 * np.pi, 400)
    for x in (0.2, 0.5, 1, 2, 5):
        for sinal in (1, -1):
            cx, cy, raio = 1, sinal / x, 1 / x
            px, py = cx + raio * np.cos(t), cy + raio * np.sin(t)
            dentro = px ** 2 + py ** 2 <= 1.0001
            px, py = np.where(dentro, px, np.nan), np.where(dentro, py, np.nan)
            ax.plot(px, py, lw=0.5, color="0.6")
    ax.plot([-1, 1], [0, 0], lw=0.5, color="0.6")
    ax.set_aspect("equal")
    ax.set_xlim(-1.15, 1.15)
    ax.set_ylim(-1.15, 1.15)
    ax.axis("off")


def smith():
    fig, ax = plt.subplots(figsize=(6.2, 6.2))
    _grade_smith(ax)
    for nome, (x, y), cor, ha in [("curto\n(0 Ω)", (-1, 0), "crimson", "right"),
                                  ("aberto\n(∞)", (1, 0), "crimson", "left"),
                                  ("carga\n50 Ω", (0, 0), "crimson", "center")]:
        ax.plot(x, y, "o", color=cor, ms=8, zorder=5)
        dx = {"right": -0.05, "left": 0.05, "center": 0}[ha]
        dy = -0.17 if ha == "center" else 0.0
        ax.text(x + dx, y + dy, nome, ha=ha, va="center", fontsize=9, color=cor)
    f, s = ler_s1p(PROJETO / "resultados" / "s11_amostra_seca.s1p")
    ax.plot(s.real, s.imag, color="#1f5fa8", lw=2)
    fres, smin, _ = analisar(f, s)
    i = int(np.argmin(np.abs(f - fres)))
    ax.plot(s[i].real, s[i].imag, "o", color="#1f5fa8")
    ax.annotate("sensor: a curva passa\nperto do centro na\nressonância", (s[i].real, s[i].imag),
                (0.25, 0.55), fontsize=8.5, color="#1f5fa8",
                arrowprops=dict(arrowstyle="->", color="#1f5fa8"))
    ax.text(0, 1.08, "metade de cima: indutivo", ha="center", fontsize=8.5, color="0.35")
    ax.text(0, -1.1, "metade de baixo: capacitivo", ha="center", fontsize=8.5, color="0.35")
    ax.set_title("Carta de Smith: os padrões da calibração e o sensor", fontsize=10)
    _salvar(fig, "smith.png")


def calibracao():
    fig, ax = plt.subplots(figsize=(7.8, 3.6))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 44)
    ax.axis("off")
    ax.add_patch(FancyBboxPatch((2, 14), 20, 18, boxstyle="round,pad=0.6", fc="#e3f2fd", ec="k"))
    ax.text(12, 26, "VNA", ha="center", fontsize=11, weight="bold")
    ax.text(12, 19.5, "porta 1", ha="center", fontsize=8.5)
    ax.plot([22.6, 24], [17, 17], "k", lw=3)
    xs = np.linspace(24, 52, 60)
    ax.plot(xs, 17 + 2.5 * np.sin((xs - 24) / 28 * 2 * np.pi), color="#424242", lw=3)
    ax.text(38, 22, "cabo", ha="center", fontsize=9)
    ax.add_patch(Rectangle((52, 15.5), 3, 3, fc="#bdbdbd", ec="k"))
    ax.plot([55, 55], [5, 40], color="crimson", lw=1.5, ls="--")
    ax.text(55, 41.5, "plano de referência", ha="center", fontsize=9, color="crimson")
    ax.text(55, 2, "a calibração leva a medição até aqui", ha="center", fontsize=8.5,
            color="crimson")
    padroes = [("aberto", 33), ("curto", 25), ("carga 50 Ω", 17)]
    for nome, y in padroes:
        ax.add_patch(FancyBboxPatch((62, y - 2.5), 14, 5, boxstyle="round,pad=0.3", fc="#fff3e0",
                                    ec="k"))
        ax.text(69, y, nome, ha="center", va="center", fontsize=8.5)
        ax.annotate("", (61.5, y), (55.6, 17), arrowprops=dict(arrowstyle="->", lw=0.8))
    ax.text(69, 39, "1. calibração (SOL)", ha="center", fontsize=9, weight="bold")
    ax.annotate("", (83, 17), (78, 17), arrowprops=dict(arrowstyle="->", lw=1.2))
    ax.add_patch(Rectangle((84, 12), 13, 10, fc="#d9c89a", ec="k"))
    ax.add_patch(Rectangle((86.5, 14), 8, 6, fc="#c87533", ec="none"))
    ax.text(90.5, 9, "2. antena", ha="center", fontsize=9, weight="bold")
    ax.set_title("Calibração na ponta do cabo: depois, só a antena muda", fontsize=10)
    _salvar(fig, "calibracao.png")


if __name__ == "__main__":
    s11_lido()
    smith()
    calibracao()
