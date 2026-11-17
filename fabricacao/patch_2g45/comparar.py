"""Compara o S11 medido no VNA com o simulado.

Uso (no openEMS Lab ou em qualquer Python com numpy e matplotlib):

    python comparar.py medido.s1p
    python comparar.py medido.s1p outra_placa.s1p

O script lê arquivos Touchstone de 1 porta (.s1p) em qualquer formato (RI, MA ou DB;
Hz, kHz, MHz ou GHz), mostra a ressonância, o |S11| mínimo e a faixa de -10 dB de
cada curva e grava o gráfico comparar.png na pasta atual.

Também estima a permissividade do FR-4 da sua placa pela diferença de frequência:
a ressonância do patch varia com 1/raiz(er), então er_placa ~ er_sim * (f_sim / f_medida)^2.
A conta é aproximada. Ela vale se as dimensões da placa estiverem certas (confira com o
paquímetro antes).
"""

import sys
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
SIMULADO = AQUI / "resultados" / "s11_simulado.s1p"
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
            partes = linha[1:].upper().split()
            for p in partes:
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


def main(arquivos):
    import matplotlib
    if not hasattr(sys, "ps1"):
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if not arquivos:
        print(__doc__)
        return 1
    fs, ss = ler_s1p(SIMULADO)
    fres_sim, smin, faixa = analisar(fs, ss)
    print(texto("simulado", fres_sim, smin, faixa))

    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot(fs, 20 * np.log10(np.abs(ss)), "k", lw=2, label="simulado")
    for arquivo in arquivos:
        f, s = ler_s1p(arquivo)
        fres, smin, faixa = analisar(f, s)
        nome = Path(arquivo).stem
        print(texto(nome, fres, smin, faixa))
        er = ER_SIMULADO * (fres_sim / fres) ** 2
        print(f"{'':>24}  diferença {1e3 * (fres - fres_sim):+.0f} MHz "
              f"({100 * (fres / fres_sim - 1):+.1f} %); er estimado do FR-4: {er:.2f}")
        ax.plot(f, 20 * np.log10(np.abs(s)), lw=1.5, label=f"medido: {nome}")
    ax.axhline(-10, color="r", lw=0.8, ls=":")
    ax.set_xlabel("frequência (GHz)")
    ax.set_ylabel("|S11| (dB)")
    ax.set_xlim(fs[0], fs[-1])
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)
    ax.set_title("S11: medido x simulado")
    fig.tight_layout()
    fig.savefig("comparar.png", dpi=150)
    print("\nGráfico gravado em comparar.png")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
