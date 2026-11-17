"""Compara o S11 medido no VNA com o simulado.

Uso (no openEMS Lab ou em qualquer Python com numpy e matplotlib):

    python comparar.py ar.s1p                          # etapa 1: antena no ar
    python comparar.py --amostra seca.s1p              # etapa 2: sobre a amostra seca
    python comparar.py --umidade seca.s1p umida.s1p    # estima a água na amostra úmida

O script lê arquivos Touchstone de 1 porta (.s1p) em qualquer formato (RI, MA ou DB;
Hz, kHz, MHz ou GHz), mostra a ressonância, o |S11| mínimo e a faixa de -10 dB de
cada curva e grava o gráfico comparar.png na pasta atual.

Na etapa 1, ele também estima a permissividade do FR-4 da sua placa pela diferença
de frequência: a ressonância do patch varia com 1/raiz(er), então
er_placa ~ er_sim * (f_sim / f_medida)^2. A conta vale se as dimensões estiverem certas.

Com --umidade, a referência é a SUA medição da amostra seca, e não a simulação. O
deslocamento medido (úmida menos seca) entra na curva de calibração simulada
(resultados/calibracao_umidade.csv) e dá a fração de água. Como as duas medições usam
a mesma placa, o erro do er do FR-4 quase se cancela.
"""

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
RESULTADOS = AQUI / "resultados"
ER_SIMULADO = 4.4


def ler_s1p(arquivo):
    """Lê um Touchstone de 1 porta. Retorna (f em GHz, S11 complexo)."""
    escala = {"HZ": 1e-9, "KHZ": 1e-6, "MHZ": 1e-3, "GHZ": 1.0}
    unidade, formato = "GHZ", "MA"
    f, s = [], []
    for linha in Path(arquivo).read_text(encoding="utf-8", errors="replace").splitlines():
        linha = linha.split("!")[0].strip()
        if not linha:
            continue
        if linha.startswith("#"):
            for p in linha[1:].upper().split():
                if p in escala:
                    unidade = p
                elif p in ("RI", "MA", "DB"):
                    formato = p
            continue
        v = [float(x) for x in linha.split()[:3]]
        if len(v) < 3:
            continue
        f.append(v[0] * escala[unidade])
        if formato == "RI":
            s.append(complex(v[1], v[2]))
        else:
            mod = 10 ** (v[1] / 20) if formato == "DB" else v[1]
            s.append(mod * np.exp(1j * np.deg2rad(v[2])))
    if not f:
        raise ValueError(f"{arquivo}: nenhum ponto lido. É um arquivo .s1p?")
    return np.array(f), np.array(s)


def analisar(f, s11):
    """Ressonância (GHz), |S11| mínimo (dB) e faixa de -10 dB (GHz) ou None."""
    db = 20 * np.log10(np.abs(s11))
    i = int(np.argmin(db))
    fres = f[i]
    if 0 < i < len(db) - 1:  # parábola pelos três pontos em volta do mínimo
        a, b, c = db[i - 1], db[i], db[i + 1]
        if a - 2 * b + c > 0:
            fres = f[i] + 0.5 * (a - c) / (a - 2 * b + c) * (f[i + 1] - f[i])
    faixa = None
    if db[i] < -10:
        j1, j2 = i, i
        while j1 > 0 and db[j1 - 1] < -10:
            j1 -= 1
        while j2 < len(db) - 1 and db[j2 + 1] < -10:
            j2 += 1
        f1 = np.interp(-10, [db[j1], db[j1 - 1]], [f[j1], f[j1 - 1]]) if j1 > 0 else f[0]
        f2 = np.interp(-10, [db[j2], db[j2 + 1]], [f[j2], f[j2 + 1]]) if j2 < len(db) - 1 else f[-1]
        faixa = (float(f1), float(f2))
    return float(fres), float(db[i]), faixa


def texto(nome, fres, smin, faixa):
    largura = f"{(faixa[1] - faixa[0]) * 1e3:.0f} MHz ({faixa[0]:.3f} a {faixa[1]:.3f} GHz)" if faixa \
        else "não chega a -10 dB"
    return f"{nome:>24}: ressonância {fres:.3f} GHz, |S11| mínimo {smin:.1f} dB, faixa -10 dB: {largura}"


def ler_calibracao():
    with open(RESULTADOS / "calibracao_umidade.csv", encoding="utf-8") as fh:
        linhas = list(csv.DictReader(fh))
    agua = np.array([float(r["agua_pct_volume"]) for r in linhas])
    desloc = np.array([float(r["delta_f0_MHz"]) for r in linhas])
    return agua, desloc


def main(argv):
    import matplotlib
    if not hasattr(sys, "ps1"):
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ap = argparse.ArgumentParser(description="Compara o S11 medido com o simulado.")
    modo = ap.add_mutually_exclusive_group()
    modo.add_argument("--amostra", action="store_true",
                      help="compara com a simulação sobre a amostra seca")
    modo.add_argument("--umidade", action="store_true",
                      help="o primeiro arquivo é a amostra seca; estima a água nos outros")
    ap.add_argument("arquivos", nargs="+", help="arquivos .s1p medidos")
    args = ap.parse_args(argv)

    fig, ax = plt.subplots(figsize=(8, 4.8))
    if args.umidade:
        if len(args.arquivos) < 2:
            ap.error("--umidade precisa da amostra seca e de pelo menos uma amostra úmida")
        agua, desloc = ler_calibracao()
        f, s = ler_s1p(args.arquivos[0])
        f_seca, smin, faixa = analisar(f, s)
        print(texto("seca (referência)", f_seca, smin, faixa))
        ax.plot(f, 20 * np.log10(np.abs(s)), "k", lw=2, label=f"seca: {Path(args.arquivos[0]).stem}")
        for arquivo in args.arquivos[1:]:
            f, s = ler_s1p(arquivo)
            fres, smin, faixa = analisar(f, s)
            nome = Path(arquivo).stem
            print(texto(nome, fres, smin, faixa))
            d = 1e3 * (fres - f_seca)
            # a curva simulada desce com a água; np.interp precisa de x crescente
            if d > 0 or d < desloc.min():
                estimativa = "fora da faixa simulada (0 a {:g} %)".format(agua.max())
            else:
                estimativa = f"cerca de {np.interp(d, desloc[::-1], agua[::-1]):.1f} % de água (volume)"
            print(f"{'':>24}  deslocamento {d:+.0f} MHz -> {estimativa}")
            ax.plot(f, 20 * np.log10(np.abs(s)), lw=1.5, label=f"medido: {nome}")
        ax.set_xlim(f[0], f[-1])
        titulo = "S11 medido: amostra seca e úmida"
    else:
        sim = RESULTADOS / ("s11_amostra_seca.s1p" if args.amostra else "s11_ar.s1p")
        fs, ss = ler_s1p(sim)
        fres_sim, smin, faixa = analisar(fs, ss)
        print(texto("simulado", fres_sim, smin, faixa))
        ax.plot(fs, 20 * np.log10(np.abs(ss)), "k", lw=2, label="simulado")
        for arquivo in args.arquivos:
            f, s = ler_s1p(arquivo)
            fres, smin, faixa = analisar(f, s)
            nome = Path(arquivo).stem
            print(texto(nome, fres, smin, faixa))
            linha = (f"{'':>24}  diferença {1e3 * (fres - fres_sim):+.0f} MHz "
                     f"({100 * (fres / fres_sim - 1):+.1f} %)")
            if not args.amostra:
                linha += f"; er estimado do FR-4: {ER_SIMULADO * (fres_sim / fres) ** 2:.2f}"
            print(linha)
            ax.plot(f, 20 * np.log10(np.abs(s)), lw=1.5, label=f"medido: {nome}")
        ax.set_xlim(fs[0], fs[-1])
        titulo = "S11 sobre a amostra seca: medido x simulado" if args.amostra \
            else "S11 no ar: medido x simulado"

    ax.axhline(-10, color="r", lw=0.8, ls=":")
    ax.set_xlabel("frequência (GHz)")
    ax.set_ylabel("|S11| (dB)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)
    ax.set_title(titulo)
    fig.tight_layout()
    fig.savefig("comparar.png", dpi=150)
    print("\nGráfico gravado em comparar.png")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
