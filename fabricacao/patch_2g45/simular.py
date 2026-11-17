"""Simula a antena patch de 2,45 GHz e grava os resultados esperados em ./resultados.

Roda no openEMS Lab (o mesmo Python dos notebooks):

    python simular.py

São cinco simulações: o projeto nominal (com o diagrama de radiação) e quatro
variações. Leva de 15 a 60 minutos, conforme o computador.

Modelo:
- substrato FR-4 com perdas, do tamanho da placa;
- cobre de 35 µm com a condutividade do cobre, nas duas faces;
- porta concentrada de 50 ohm na borda da placa, entre a linha e o plano de terra.
  Ela faz o papel do SMA de borda; o plano de referência é a borda da placa;
- ar em volta e contorno absorvente (PML).

As variações mostram o efeito do que muda na prática: a permissividade do FR-4
(que o fabricante não garante em 2,4 GHz) e o desbaste do cobre pela fresa.
"""

import csv
import os
import sys
import time
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
from CSXCAD import ContinuousStructure
from CSXCAD.SmoothMeshLines import SmoothMeshLines
from openEMS import openEMS
from openEMS.physical_constants import C0, EPS0

from geometria import AQUI, Antena

F_MIN, F_MAX = 2.0, 3.0      # GHz, faixa dos resultados (igual à varredura sugerida no VNA)
F0, FC = 2.5e9, 1.0e9        # pulso gaussiano: 1,5 a 3,5 GHz
MARGEM_AR = 40.0             # mm de ar entre a placa e o contorno
RES_PLACA = 1.0              # mm, malha sobre a placa
RES_FINA = 0.35              # mm, malha na região da linha e do inset
RES_AR = C0 / 3.5e9 / 1e-3 / 20  # mm, lambda/20 na maior frequência do pulso
PASTA_RESULTADOS = AQUI / "resultados"


def pasta_simulacao(nome):
    try:  # no openEMS Lab, as simulações ficam na mesma pasta dos notebooks
        from emslab import pasta_simulacao as pasta_lab
        return pasta_lab(nome)
    except ImportError:
        pasta = Path(os.environ.get("EMSLAB_SIMULACOES", Path.home() / "openEMS-simulacoes")) / nome
        pasta.mkdir(parents=True, exist_ok=True)
        return pasta


@dataclass
class Resultado:
    nome: str
    antena: Antena
    f: np.ndarray        # GHz
    s11: np.ndarray      # complexo, referência na borda da placa
    zin: np.ndarray      # ohm
    duracao: float = 0.0
    campo: dict = field(default_factory=dict)

    @property
    def s11_db(self):
        return 20 * np.log10(np.abs(self.s11))

    def ressonancia(self):
        """Frequência (GHz) e |S11| (dB) do mínimo, com interpolação por parábola."""
        y = self.s11_db
        i = int(np.argmin(y))
        if 0 < i < len(y) - 1:
            a, b, c = y[i - 1], y[i], y[i + 1]
            k = 0.5 * (a - c) / (a - 2 * b + c)
            return float(self.f[i] + k * (self.f[1] - self.f[0])), float(b - 0.25 * (a - c) * k)
        return float(self.f[i]), float(y[i])

    def banda(self, limite=-10.0):
        """Faixa (f1, f2) em GHz onde |S11| < limite, em volta do mínimo. None se não houver."""
        y = self.s11_db
        i = int(np.argmin(y))
        if y[i] >= limite:
            return None
        j1 = i
        while j1 > 0 and y[j1 - 1] < limite:
            j1 -= 1
        j2 = i
        while j2 < len(y) - 1 and y[j2 + 1] < limite:
            j2 += 1
        f1 = np.interp(limite, [y[j1], y[j1 - 1]], [self.f[j1], self.f[j1 - 1]]) if j1 > 0 else self.f[0]
        f2 = np.interp(limite, [y[j2], y[j2 + 1]], [self.f[j2], self.f[j2 + 1]]) if j2 < len(y) - 1 else self.f[-1]
        return float(f1), float(f2)


# ==================================================================== malha

def _linhas_borda(borda, metal_do_lado, r):
    """Regra dos terços na borda de um metal fino: 1/3 da célula dentro do metal, 2/3 fora."""
    s = 1 if metal_do_lado > 0 else -1
    return [borda + s * r / 3, borda - s * 2 * r / 3]


def _suavizar(linhas, res):
    """Preenche os vãos entre as linhas dadas com células de no máximo `res` mm."""
    return np.round(SmoothMeshLines(np.unique(np.round(linhas, 6)), res, 1.3), 6)


def montar(a: Antena, campo_distante=False, max_passos=60000):
    fdtd = openEMS(NrTS=max_passos, EndCriteria=1e-4)
    fdtd.SetGaussExcite(F0, FC)
    fdtd.SetBoundaryCond(["PML_8"] * 6)

    csx = ContinuousStructure()
    fdtd.SetCSX(csx)
    malha = csx.GetGrid()
    malha.SetDeltaUnit(1e-3)

    px, py = a.placa_x / 2, a.placa_y / 2
    xl, xr, xi = a.x_patch, a.x_patch + a.L, a.x_patch + a.inset
    ya, yb = a.linha_w / 2, a.linha_w / 2 + a.gap

    # ---- materiais
    kappa = 2 * np.pi * a.f_projeto * 1e9 * EPS0 * a.er * a.tand
    fr4 = csx.AddMaterial("FR4", epsilon=a.er, kappa=kappa)
    fr4.AddBox([-px, -py, 0], [px, py, a.h], priority=0)

    cobre = dict(conductivity=5.8e7, thickness=a.cobre_um * 1e-6)
    terra = csx.AddConductingSheet("plano_de_terra", **cobre)
    terra.AddBox([-px, -py, 0], [px, py, 0], priority=10)

    topo = csx.AddConductingSheet("patch_e_linha", **cobre)
    pts = np.array(a.poligono()).T
    topo.AddPolygon(pts, norm_dir="z", elevation=a.h, priority=10)

    porta = fdtd.AddLumpedPort(1, 50, [-px, -ya, 0], [-px, ya, a.h], "z", 1.0, priority=5)

    # As linhas partem das bordas do cobre, e não de uma grade fixa: assim a malha
    # acompanha L e o resultado não pula quando a geometria muda um décimo de mm.
    r = RES_PLACA
    # ---- malha em x
    esp_x = [-px, px] + _linhas_borda(xl, +1, r) + _linhas_borda(xr, -1, r)
    fina_x = _suavizar([xi - 0.6, xi, xi + 0.6], RES_FINA)
    linhas_x = _suavizar(esp_x + list(fina_x), r)
    # ---- malha em y
    fina_y = _suavizar([-yb - 0.6, -yb, -ya, 0, ya, yb, yb + 0.6], RES_FINA)
    esp_y = [-py, py] + _linhas_borda(a.W / 2, -1, r) + _linhas_borda(-a.W / 2, +1, r)
    linhas_y = _suavizar(esp_y + list(fina_y), r)
    # ---- malha em z: 4 células no substrato
    linhas_z = np.linspace(0, a.h, 5)

    m = MARGEM_AR + 8 * RES_AR  # o PML_8 ocupa 8 células dentro do domínio
    malha.SetLines("x", np.concatenate([[-px - m], linhas_x, [px + m]]))
    malha.SetLines("y", np.concatenate([[-py - m], linhas_y, [py + m]]))
    malha.SetLines("z", np.concatenate([[-m], linhas_z, [a.h + m]]))
    malha.SmoothMeshLines("all", RES_AR, 1.3)
    # a suavização deixa erros de arredondamento (1.6000000000000014 em vez de 1.6);
    # uma folha de metal fora da linha da malha some da simulação
    for eixo in "xyz":
        malha.SetLines(eixo, np.unique(np.round(malha.GetLines(eixo), 6)))

    nf2ff = fdtd.CreateNF2FFBox() if campo_distante else None
    return fdtd, csx, porta, nf2ff


# ==================================================================== simulação

def simular(a: Antena, nome, campo_distante=False, pontos=501):
    fdtd, csx, porta, nf2ff = montar(a, campo_distante)
    pasta = pasta_simulacao(nome)
    g = csx.GetGrid()
    n = g.GetQtyLines("x") * g.GetQtyLines("y") * g.GetQtyLines("z")
    print(f"\n=== {nome}: {a}\n    {n / 1e3:.0f} mil células", flush=True)

    atual = os.getcwd()
    inicio = time.time()
    try:
        fdtd.Run(str(pasta), cleanup=True, verbose=0)
    finally:
        os.chdir(atual)
    duracao = time.time() - inicio

    f = np.linspace(F_MIN, F_MAX, pontos)
    porta.CalcPort(str(pasta), f * 1e9)
    s11 = porta.uf_ref / porta.uf_inc
    zin = porta.uf_tot / porta.if_tot
    res = Resultado(nome, a, f, s11, zin, duracao)

    if nf2ff is not None:
        res.campo = calcular_campo_distante(nf2ff, porta, pasta, res.ressonancia()[0], a.h)
    s = res.ressonancia()
    print(f"    ressonância {s[0]:.4f} GHz, |S11| = {s[1]:.1f} dB, banda -10 dB {res.banda()}, "
          f"{duracao:.0f} s", flush=True)
    return res


def calcular_campo_distante(nf2ff, porta, pasta, fres, h):
    """Diretividade, eficiência, ganho realizado e cortes do diagrama em fres (GHz).

    Atenção: o centro de fase (center) vai em metros, e não na unidade da malha.
    """
    atual = os.getcwd()
    try:
        # a potência irradiada vem da integral na esfera inteira; dois cortes não bastam
        esfera = nf2ff.CalcNF2FF(str(pasta), fres * 1e9, np.arange(0, 181, 3.0),
                                 np.arange(0, 360, 5.0), center=[0, 0, h * 1e-3],
                                 outfile="campo_esfera.h5", verbose=0)
        theta = np.arange(-180, 181, 2.0)
        cortes = nf2ff.CalcNF2FF(str(pasta), fres * 1e9, theta, np.array([0.0, 90.0]),
                                 center=[0, 0, h * 1e-3], outfile="campo_cortes.h5", verbose=0)
    finally:
        os.chdir(atual)
    porta.CalcPort(str(pasta), np.array([fres * 1e9]))
    p_inc = float(np.real(porta.P_inc[0]))
    p_acc = float(np.real(porta.P_acc[0]))
    p_rad = float(esfera.Prad[0])
    dmax = float(esfera.Dmax[0])
    # ganho realizado: inclui as perdas e o descasamento (referência: potência incidente)
    g_max = dmax * p_rad / p_inc
    e_rel = cortes.E_norm[0] / np.max(esfera.E_norm[0])
    g_real = 10 * np.log10(g_max) + 20 * np.log10(np.maximum(e_rel, 1e-6))
    return dict(f=fres, theta=theta, ganho_e=g_real[:, 0], ganho_h=g_real[:, 1],
                diretividade_dbi=10 * np.log10(dmax), eficiencia=p_rad / p_acc,
                ganho_realizado_dbi=10 * np.log10(g_max))


# ==================================================================== saída

def gravar_touchstone(res, arquivo):
    with open(arquivo, "w", encoding="ascii", newline="\n") as fh:
        fh.write(f"! S11 simulado (openEMS) da antena patch_2g45, nominal\n")
        fh.write(f"! referencia: borda da placa (entrada do SMA)\n")
        fh.write("# Hz S RI R 50\n")
        for fi, s in zip(res.f, res.s11):
            fh.write(f"{fi * 1e9:.0f} {s.real:.6f} {s.imag:.6f}\n")


def gravar_csv(res, arquivo):
    with open(arquivo, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["f_GHz", "S11_dB", "S11_re", "S11_im", "Zin_re_ohm", "Zin_im_ohm"])
        for fi, db, s, z in zip(res.f, res.s11_db, res.s11, res.zin):
            w.writerow([f"{fi:.4f}", f"{db:.3f}", f"{s.real:.5f}", f"{s.imag:.5f}",
                        f"{z.real:.2f}", f"{z.imag:.2f}"])


def gravar_variacoes_csv(resultados, arquivo):
    with open(arquivo, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["f_GHz"] + [f"S11_dB_{r.nome}" for r in resultados])
        for i, fi in enumerate(resultados[0].f):
            w.writerow([f"{fi:.4f}"] + [f"{r.s11_db[i]:.3f}" for r in resultados])


def grafico_s11(nominal, variacoes, arquivo):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 4.8))
    if variacoes:
        todas = np.array([r.s11_db for r in [nominal] + variacoes])
        ax.fill_between(nominal.f, todas.min(0), todas.max(0), color="tab:blue", alpha=0.15,
                        label="faixa esperada (variações)")
        for r in variacoes:
            ax.plot(r.f, r.s11_db, lw=0.8, ls="--", label=ROTULOS.get(r.nome, r.nome))
    ax.plot(nominal.f, nominal.s11_db, "k", lw=2, label="nominal")
    ax.axhline(-10, color="r", lw=0.8, ls=":")
    ax.axvspan(2.400, 2.4835, color="0.85", zorder=0, label="Wi-Fi 2,4 GHz")
    ax.set_xlabel("frequência (GHz)")
    ax.set_ylabel("|S11| (dB)")
    ax.set_xlim(F_MIN, F_MAX)
    ax.set_ylim(min(-35, nominal.s11_db.min() - 2), 0)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc="lower left")
    ax.set_title("Coeficiente de reflexão simulado, na entrada do SMA")
    fig.tight_layout()
    fig.savefig(arquivo, dpi=150)
    plt.close(fig)


def grafico_smith(res, arquivo):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6.2, 6.2))
    t = np.linspace(0, 2 * np.pi, 400)
    ax.plot(np.cos(t), np.sin(t), "k", lw=1)
    for rr in [0.2, 0.5, 1, 2, 5]:  # círculos de resistência constante
        c, raio = rr / (1 + rr), 1 / (1 + rr)
        ax.plot(c + raio * np.cos(t), raio * np.sin(t), color="0.75", lw=0.6)
    for xx in [0.2, 0.5, 1, 2, 5]:  # arcos de reatância constante
        for s in (1, -1):
            z = 1j * s * xx + np.logspace(-3, 3, 400)
            g = (z - 1) / (z + 1)
            ax.plot(g.real, g.imag, color="0.75", lw=0.6)
    ax.axhline(0, color="0.75", lw=0.6)
    ax.plot(res.s11.real, res.s11.imag, "tab:blue", lw=2)
    fr, _ = res.ressonancia()
    for fm in [2.3, 2.4, fr, 2.5, 2.6]:
        i = int(np.argmin(np.abs(res.f - fm)))
        ax.plot(res.s11[i].real, res.s11[i].imag, "o", color="k" if fm == fr else "tab:red", ms=4)
        ax.annotate(f"{res.f[i]:.3f}", (res.s11[i].real, res.s11[i].imag), fontsize=8,
                    xytext=(4, 4), textcoords="offset points")
    ax.set_aspect("equal")
    ax.set_xlim(-1.05, 1.05)
    ax.set_ylim(-1.05, 1.05)
    ax.axis("off")
    ax.set_title(f"S11 simulado na carta de Smith ({F_MIN:g} a {F_MAX:g} GHz, Z0 = 50 ohm)")
    fig.tight_layout()
    fig.savefig(arquivo, dpi=150)
    plt.close(fig)


def grafico_diagrama(res, arquivo):
    import matplotlib.pyplot as plt
    c = res.campo
    fig, ax = plt.subplots(subplot_kw=dict(projection="polar"), figsize=(6.2, 6.2))
    th = np.deg2rad(c["theta"])
    piso = c["ganho_realizado_dbi"] - 30
    ax.plot(th, np.maximum(c["ganho_e"], piso), label="plano E (xz)")
    ax.plot(th, np.maximum(c["ganho_h"], piso), label="plano H (yz)")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_rlim(piso, c["ganho_realizado_dbi"] + 2)
    ax.set_title(f"Ganho realizado (dBi) em {c['f']:.3f} GHz\n0° = acima da placa (+z)", fontsize=10)
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(arquivo, dpi=150)
    plt.close(fig)


def friis_s21_db(ganho_dbi, f_ghz, d_m):
    """|S21| esperado entre duas antenas iguais, alinhadas, à distância d (espaço livre)."""
    lam = C0 / (f_ghz * 1e9)
    return 2 * ganho_dbi + 20 * np.log10(lam / (4 * np.pi * d_m))


ROTULOS = {
    "er_4.2": "FR-4 com er = 4,2",
    "er_4.6": "FR-4 com er = 4,6",
    "desbaste_0.1": "fresa come 0,1 mm por borda",
    "h_1.5": "placa com 1,5 mm",
}


def variacoes(nominal: Antena):
    return [
        ("er_4.2", replace(nominal, er=4.2)),
        ("er_4.6", replace(nominal, er=4.6)),
        ("desbaste_0.1", nominal.com_desbaste(0.1)),
        ("h_1.5", replace(nominal, h=1.5)),
    ]


def resumo(nominal, outras, arquivo):
    linhas = ["# Resultados simulados: patch_2g45", "",
              f"Geometria nominal: {nominal.antena}", "",
              "Referência: borda da placa, na entrada do SMA. Faixa simulada: "
              f"{F_MIN:g} a {F_MAX:g} GHz.", "",
              "| Caso | Ressonância (GHz) | S11 mínimo (dB) | Faixa com S11 < -10 dB (GHz) | Largura (MHz) |",
              "|---|---|---|---|---|"]
    for r in [nominal] + outras:
        fr, smin = r.ressonancia()
        b = r.banda()
        faixa = f"{b[0]:.3f} a {b[1]:.3f}" if b else "não chega a -10 dB"
        largura = f"{(b[1] - b[0]) * 1e3:.0f}" if b else "-"
        linhas.append(f"| {ROTULOS.get(r.nome, r.nome)} | {fr:.3f} | {smin:.1f} | {faixa} | {largura} |")
    i = int(np.argmin(np.abs(nominal.f - nominal.ressonancia()[0])))
    z = nominal.zin[i]
    linhas += ["", f"Impedância de entrada na ressonância (nominal): {z.real:.1f} {z.imag:+.1f}j ohm."]
    c = nominal.campo
    if c:
        linhas += ["", f"## Radiação em {c['f']:.3f} GHz (nominal)", "",
                   f"- diretividade: {c['diretividade_dbi']:.1f} dBi",
                   f"- eficiência de radiação: {100 * c['eficiencia']:.0f} % "
                   "(o FR-4 tem perdas altas; num substrato de RF passaria de 80 %)",
                   f"- ganho realizado: {c['ganho_realizado_dbi']:.1f} dBi", "",
                   "## Enlace entre duas antenas iguais (|S21| no VNA de 2 portas, espaço livre)", "",
                   "| Distância (m) | S21 esperado (dB) |", "|---|---|"]
        for d in (0.5, 1.0, 1.5):
            linhas.append(f"| {d:g} | {friis_s21_db(c['ganho_realizado_dbi'], c['f'], d):.1f} |")
        linhas += ["", "Num laboratório comum, as reflexões em paredes e mesas mudam o S21 em alguns dB."]
    Path(arquivo).write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print("\n".join(linhas))


def main():
    PASTA_RESULTADOS.mkdir(exist_ok=True)
    a = Antena()
    nominal = simular(a, "patch_2g45_nominal", campo_distante=True)
    outras = [simular(v, f"patch_2g45_{n}") for n, v in variacoes(a)]
    for r, (n, _) in zip(outras, variacoes(a)):
        r.nome = n

    gravar_touchstone(nominal, PASTA_RESULTADOS / "s11_simulado.s1p")
    gravar_csv(nominal, PASTA_RESULTADOS / "s11_simulado.csv")
    grafico_s11(nominal, outras, PASTA_RESULTADOS / "s11.png")
    grafico_smith(nominal, PASTA_RESULTADOS / "smith.png")
    grafico_diagrama(nominal, PASTA_RESULTADOS / "diagrama.png")
    gravar_variacoes_csv([nominal] + outras, PASTA_RESULTADOS / "s11_variacoes.csv")
    nominal.nome = "nominal"
    resumo(nominal, outras, PASTA_RESULTADOS / "resumo.md")


if __name__ == "__main__":
    sys.exit(main())
