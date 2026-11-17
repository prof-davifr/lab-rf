"""Simula o sensor patch de 2,45 GHz e grava os resultados esperados em ./resultados.

Roda no openEMS Lab (o mesmo Python dos notebooks):

    python simular.py

São 12 simulações, em duas etapas. Leva de 30 a 90 minutos, conforme o computador.

Etapa 1, antena no ar: o projeto nominal e três variações de fabricação (er do
FR-4 de 4,2 e 4,6 e a fresa que come 0,1 mm por borda). Serve para validar a placa.

Etapa 2, antena sobre a amostra: o patch fica voltado para um revestimento de
10 mm de polímero (er = 4, tand = 0,01) sobre metal, com 3 mm de ar entre os dois,
como nos notebooks 03 a 05. A água no polímero vai de 0 a 10 % do volume. Duas
simulações extras mostram o efeito de um gap de 2 ou 4 mm.

Modelo:
- substrato FR-4 com perdas, do tamanho da placa;
- cobre de 35 µm com a condutividade do cobre, nas duas faces;
- porta concentrada de 50 ohm na borda da placa, entre a linha e o plano de terra.
  Ela faz o papel do SMA de borda; o plano de referência é a borda da placa;
- amostra: polímero e metal começam na borda do SMA e vão até o contorno;
- ar em volta e contorno absorvente (PML).
"""

import csv
import os
import sys
import time
import unicodedata
from dataclasses import dataclass, replace
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
    amostra: "Amostra" = None

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


# ==================================================================== amostra

def agua_debye(f_ghz, temperatura=25.0):
    """Permissividade complexa da água pura (modelo de Debye), na convenção e' - j e''.

    Valores a 25 °C (Kaatze, 1989); a 2,45 GHz dá cerca de 77 - 9j.
    """
    es, einf, tau = 78.36, 5.16, 8.27e-12
    return einf + (es - einf) / (1 + 1j * 2 * np.pi * f_ghz * 1e9 * tau)


@dataclass(frozen=True)
class Amostra:
    """Revestimento de polímero sobre metal, na frente do patch (medidas em mm).

    A água entra como fração de volume (0,05 = 5 %), misturada ao polímero pelo
    modelo CRIM: raiz(e_mistura) = (1 - v) raiz(e_polímero) + v raiz(e_água).
    O CRIM supõe a água espalhada no polímero, sem bolsas.
    """

    espessura: float = 10.0  # polímero
    gap: float = 3.0         # ar entre o patch e o polímero
    er: float = 4.0          # polímero seco
    tand: float = 0.01
    agua: float = 0.0        # fração de volume de água

    def permissividade(self, f_ghz=2.45):
        """Permissividade complexa (e' - j e'') do polímero com a água."""
        ep = self.er * (1 - 1j * self.tand)
        raiz = (1 - self.agua) * np.sqrt(ep) + self.agua * np.sqrt(agua_debye(f_ghz))
        return complex(raiz ** 2)

    def __str__(self):
        e = self.permissividade()
        return (f"amostra: {self.espessura:g} mm de polímero (er = {self.er:g}, tand = {self.tand:g}) "
                f"com {100 * self.agua:g} % de água -> er = {e.real:.2f}, tand = {-e.imag / e.real:.3f}; "
                f"gap {self.gap:g} mm")


# ==================================================================== malha

def _linhas_borda(borda, metal_do_lado, r):
    """Regra dos terços na borda de um metal fino: 1/3 da célula dentro do metal, 2/3 fora."""
    s = 1 if metal_do_lado > 0 else -1
    return [borda + s * r / 3, borda - s * 2 * r / 3]


def _suavizar(linhas, res):
    """Preenche os vãos entre as linhas dadas com células de no máximo `res` mm."""
    return np.round(SmoothMeshLines(np.unique(np.round(linhas, 6)), res, 1.3), 6)


def montar(a: Antena, amostra: Amostra = None, max_passos=60000):
    """Monta a simulação. Com uma amostra, o patch fica voltado para ela.

    A amostra (polímero e metal) começa na borda do SMA e vai até o contorno nos
    outros lados: no laboratório, a placa de amostra não pode passar por baixo do SMA.
    """
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
    linhas_z = list(np.linspace(0, a.h, 5))
    m = MARGEM_AR + 8 * RES_AR  # o PML_8 ocupa 8 células dentro do domínio

    if amostra is not None:
        z_pol = a.h + amostra.gap
        z_met = z_pol + amostra.espessura
        e = amostra.permissividade(a.f_projeto)
        pol = csx.AddMaterial("polimero", epsilon=e.real,
                              kappa=2 * np.pi * a.f_projeto * 1e9 * EPS0 * (-e.imag))
        pol.AddBox([-px, -py - m, z_pol], [px + m, py + m, z_met], priority=1)
        metal = csx.AddMetal("metal_da_amostra")
        metal.AddBox([-px, -py - m, z_met], [px + m, py + m, z_met], priority=10)
        n = int(np.ceil(amostra.espessura / 1.0)) + 1  # células de até 1 mm no polímero
        linhas_z += list(np.linspace(z_pol, z_met, max(n, 4)))
        linhas_z = list(_suavizar(linhas_z, 0.6))

    malha.SetLines("x", np.concatenate([[-px - m], linhas_x, [px + m]]))
    malha.SetLines("y", np.concatenate([[-py - m], linhas_y, [py + m]]))
    malha.SetLines("z", np.concatenate([[-m], linhas_z, [linhas_z[-1] + m]]))
    malha.SmoothMeshLines("all", RES_AR, 1.3)
    # a suavização deixa erros de arredondamento (1.6000000000000014 em vez de 1.6);
    # uma folha de metal fora da linha da malha some da simulação
    for eixo in "xyz":
        malha.SetLines(eixo, np.unique(np.round(malha.GetLines(eixo), 6)))
    return fdtd, csx, porta


# ==================================================================== simulação

def simular(a: Antena, nome, amostra: Amostra = None, pontos=501):
    fdtd, csx, porta = montar(a, amostra)
    pasta = pasta_simulacao(nome)
    g = csx.GetGrid()
    n = g.GetQtyLines("x") * g.GetQtyLines("y") * g.GetQtyLines("z")
    print(f"\n=== {nome}: {a}\n    {amostra or 'antena no ar'}\n    {n / 1e3:.0f} mil células",
          flush=True)

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
    res = Resultado(nome, a, f, s11, zin, duracao, amostra=amostra)
    s = res.ressonancia()
    print(f"    ressonância {s[0]:.4f} GHz, |S11| = {s[1]:.1f} dB, banda -10 dB {res.banda()}, "
          f"{duracao:.0f} s", flush=True)
    return res


# ==================================================================== saída

def gravar_touchstone(res, arquivo, descricao):
    # o Touchstone é ASCII: tira os acentos do comentário
    descricao = unicodedata.normalize("NFKD", descricao).encode("ascii", "ignore").decode()
    with open(arquivo, "w", encoding="ascii", newline="\n") as fh:
        fh.write(f"! S11 simulado (openEMS) da antena patch_2g45: {descricao}\n")
        fh.write("! referencia: borda da placa (entrada do SMA)\n")
        fh.write("# Hz S RI R 50\n")
        for fi, s in zip(res.f, res.s11):
            fh.write(f"{fi * 1e9:.0f} {s.real:.6f} {s.imag:.6f}\n")


def gravar_csv(res, arquivo):
    with open(arquivo, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["f_GHz", "S11_dB", "S11_re", "S11_im", "Zin_re_ohm", "Zin_im_ohm"])
        for fi, db, s, z in zip(res.f, res.s11_db, res.s11, res.zin):
            w.writerow([f"{fi:.4f}", f"{db:.3f}", f"{s.real:.5f}", f"{s.imag:.5f}",
                        f"{z.real:.2f}", f"{z.imag:.2f}"])


def gravar_curvas_csv(resultados, arquivo):
    with open(arquivo, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["f_GHz"] + [f"S11_dB_{r.nome}" for r in resultados])
        for i, fi in enumerate(resultados[0].f):
            w.writerow([f"{fi:.4f}"] + [f"{r.s11_db[i]:.3f}" for r in resultados])


def _eixos_s11(ax, titulo, ymin):
    ax.axhline(-10, color="r", lw=0.8, ls=":")
    ax.axvspan(2.400, 2.4835, color="0.88", zorder=0, label="faixa ISM de 2,4 GHz")
    ax.set_xlabel("frequência (GHz)")
    ax.set_ylabel("|S11| (dB)")
    ax.set_xlim(F_MIN, F_MAX)
    ax.set_ylim(min(-35, ymin - 2), 0)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc="lower left")
    ax.set_title(titulo)


def grafico_ar(nominal, variacoes, arquivo):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 4.8))
    todas = np.array([r.s11_db for r in [nominal] + variacoes])
    ax.fill_between(nominal.f, todas.min(0), todas.max(0), color="tab:blue", alpha=0.15,
                    label="faixa esperada (variações)")
    for r in variacoes:
        ax.plot(r.f, r.s11_db, lw=0.8, ls="--", label=ROTULOS.get(r.nome, r.nome))
    ax.plot(nominal.f, nominal.s11_db, "k", lw=2, label="nominal")
    _eixos_s11(ax, "Etapa 1: antena no ar (S11 na entrada do SMA)", todas.min())
    fig.tight_layout()
    fig.savefig(arquivo, dpi=150)
    plt.close(fig)


def grafico_umidade(umidade, gaps, arquivo):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 4.8))
    cores = plt.cm.viridis_r(np.linspace(0.1, 0.95, len(umidade)))
    for r, c in zip(umidade, cores):
        ax.plot(r.f, r.s11_db, color=c, lw=2 if r.amostra.agua == 0 else 1.3,
                label=f"{100 * r.amostra.agua:g} % de água")
    for r, ls in zip(gaps, (":", "--")):
        ax.plot(r.f, r.s11_db, color="0.4", lw=1, ls=ls,
                label=f"seca, gap de {r.amostra.gap:g} mm")
    ymin = min(r.s11_db.min() for r in umidade + gaps)
    _eixos_s11(ax, "Etapa 2: antena sobre o revestimento (10 mm de polímero sobre metal, gap 3 mm)",
               ymin)
    fig.tight_layout()
    fig.savefig(arquivo, dpi=150)
    plt.close(fig)


def grafico_calibracao(umidade, arquivo):
    import matplotlib.pyplot as plt
    agua = np.array([100 * r.amostra.agua for r in umidade])
    f0 = np.array([r.ressonancia()[0] for r in umidade])
    smin = np.array([r.ressonancia()[1] for r in umidade])
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    ax[0].plot(agua, 1e3 * (f0 - f0[0]), "o-")
    ax[0].set_ylabel("deslocamento da ressonância (MHz)")
    ax[0].set_title("A parte real da permissividade (e')")
    ax[1].plot(agua, smin, "o-", color="tab:red")
    ax[1].set_ylabel("|S11| mínimo (dB)")
    ax[1].set_title("As perdas (e'')")
    for a in ax:
        a.set_xlabel("água no polímero (% do volume)")
        a.grid(alpha=0.3)
    fig.suptitle("Curvas de calibração simuladas (a referência é a amostra seca)")
    fig.tight_layout()
    fig.savefig(arquivo, dpi=150)
    plt.close(fig)


def grafico_smith(res, arquivo, titulo):
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
    for df in [-0.1, -0.05, 0, 0.05, 0.1]:
        i = int(np.argmin(np.abs(res.f - fr - df)))
        ax.plot(res.s11[i].real, res.s11[i].imag, "o", color="k" if df == 0 else "tab:red", ms=4)
        ax.annotate(f"{res.f[i]:.3f}", (res.s11[i].real, res.s11[i].imag), fontsize=8,
                    xytext=(4, 4), textcoords="offset points")
    ax.set_aspect("equal")
    ax.set_xlim(-1.05, 1.05)
    ax.set_ylim(-1.05, 1.05)
    ax.axis("off")
    ax.set_title(f"{titulo}\n(S11 de {F_MIN:g} a {F_MAX:g} GHz, Z0 = 50 ohm, frequências em GHz)")
    fig.tight_layout()
    fig.savefig(arquivo, dpi=150)
    plt.close(fig)


def gravar_calibracao_csv(umidade, arquivo):
    f_seca = umidade[0].ressonancia()[0]
    with open(arquivo, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["agua_pct_volume", "er_polimero", "tand_polimero", "f0_GHz", "delta_f0_MHz",
                    "S11_min_dB", "banda_10dB_MHz"])
        for r in umidade:
            e = r.amostra.permissividade()
            fr, smin = r.ressonancia()
            b = r.banda()
            w.writerow([f"{100 * r.amostra.agua:g}", f"{e.real:.3f}", f"{-e.imag / e.real:.4f}",
                        f"{fr:.4f}", f"{1e3 * (fr - f_seca):.1f}", f"{smin:.2f}",
                        f"{1e3 * (b[1] - b[0]):.0f}" if b else ""])


ROTULOS = {
    "er_4.2": "FR-4 com er = 4,2",
    "er_4.6": "FR-4 com er = 4,6",
    "desbaste_0.1": "fresa come 0,1 mm por borda",
}

AGUA = [0.0, 0.02, 0.04, 0.06, 0.08, 0.10]  # fração de volume de água no polímero
GAPS = [2.0, 4.0]                            # mm, para ver o efeito de um espaçador errado


def variacoes(nominal: Antena):
    return [
        ("er_4.2", replace(nominal, er=4.2)),
        ("er_4.6", replace(nominal, er=4.6)),
        ("desbaste_0.1", nominal.com_desbaste(0.1)),
    ]


def _linha_tabela(rotulo, r, ref=None):
    fr, smin = r.ressonancia()
    b = r.banda()
    faixa = f"{b[0]:.3f} a {b[1]:.3f}" if b else "não chega a -10 dB"
    largura = f"{(b[1] - b[0]) * 1e3:.0f}" if b else "-"
    desloc = f" | {1e3 * (fr - ref):+.0f}" if ref is not None else ""
    return f"| {rotulo} | {fr:.3f}{desloc} | {smin:.1f} | {faixa} | {largura} |"


def resumo(ar, var_ar, umidade, gaps, arquivo):
    seca = umidade[0]
    f_seca = seca.ressonancia()[0]
    linhas = ["# Resultados simulados: patch_2g45", "",
              f"Antena: {ar.antena}", "",
              "Referência: borda da placa, na entrada do SMA. Faixa simulada: "
              f"{F_MIN:g} a {F_MAX:g} GHz.", "",
              "## Etapa 1: antena no ar", "",
              "| Caso | Ressonância (GHz) | S11 mínimo (dB) | Faixa com S11 < -10 dB (GHz) | Largura (MHz) |",
              "|---|---|---|---|---|"]
    linhas.append(_linha_tabela("nominal", ar))
    linhas += [_linha_tabela(ROTULOS[r.nome], r) for r in var_ar]
    linhas += ["", "## Etapa 2: antena sobre o revestimento", "",
               f"Amostra seca: {seca.amostra}.", "",
               "| Água no polímero | er / tand do polímero | Ressonância (GHz) | Deslocamento (MHz) "
               "| S11 mínimo (dB) | Faixa com S11 < -10 dB (GHz) | Largura (MHz) |",
               "|---|---|---|---|---|---|---|"]
    for r in umidade:
        e = r.amostra.permissividade()
        rot = f"{100 * r.amostra.agua:g} % | {e.real:.2f} / {-e.imag / e.real:.3f}"
        linhas.append(_linha_tabela(rot, r, f_seca))
    linhas += ["", "Efeito do gap (amostra seca):", "",
               "| Gap | Ressonância (GHz) | Deslocamento (MHz) | S11 mínimo (dB) "
               "| Faixa com S11 < -10 dB (GHz) | Largura (MHz) |", "|---|---|---|---|---|---|"]
    for r in gaps:
        linhas.append(_linha_tabela(f"{r.amostra.gap:g} mm", r, f_seca))
    Path(arquivo).write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print("\n".join(linhas))


def main():
    PASTA_RESULTADOS.mkdir(exist_ok=True)
    a = Antena()
    seca = Amostra()

    ar = simular(a, "patch_2g45_ar")
    ar.nome = "ar"
    var_ar = []
    for n, v in variacoes(a):
        var_ar.append(simular(v, f"patch_2g45_ar_{n}"))
        var_ar[-1].nome = n
    umidade = []
    for v in AGUA:
        umidade.append(simular(a, f"patch_2g45_agua_{100 * v:g}pct", amostra=replace(seca, agua=v)))
        umidade[-1].nome = f"agua_{100 * v:g}pct"
    gaps = []
    for g in GAPS:
        gaps.append(simular(a, f"patch_2g45_seca_gap_{g:g}mm", amostra=replace(seca, gap=g)))
        gaps[-1].nome = f"seca_gap_{g:g}mm"

    R = PASTA_RESULTADOS
    gravar_touchstone(ar, R / "s11_ar.s1p", "antena no ar")
    gravar_touchstone(umidade[0], R / "s11_amostra_seca.s1p", str(seca))
    gravar_csv(ar, R / "s11_ar.csv")
    gravar_curvas_csv([ar] + var_ar, R / "s11_ar_variacoes.csv")
    gravar_curvas_csv(umidade + gaps, R / "s11_amostra.csv")
    gravar_calibracao_csv(umidade, R / "calibracao_umidade.csv")
    grafico_ar(ar, var_ar, R / "s11_ar.png")
    grafico_smith(ar, R / "smith_ar.png", "Antena no ar")
    grafico_smith(umidade[0], R / "smith_amostra_seca.png", "Antena sobre a amostra seca")
    grafico_umidade(umidade, gaps, R / "s11_amostra.png")
    grafico_calibracao(umidade, R / "calibracao_umidade.png")
    resumo(ar, var_ar, umidade, gaps, R / "resumo.md")


if __name__ == "__main__":
    sys.exit(main())
