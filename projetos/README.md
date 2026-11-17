# Projetos

Cada pasta é um projeto completo: a geometria, a simulação no openEMS, os arquivos para a
CNC, os resultados esperados e um roteiro de fabricação e medição.

| Projeto | O que é | Etapas |
|---|---|---|
| [patch_2g45](patch_2g45) | sensor patch de 2,45 GHz para umidade em revestimento de polímero | simular, fabricar, medir no ar e sobre a amostra |

O instalador do openEMS Lab copia esta pasta para `Documentos/openEMS-notebooks/projetos`.
Uma reinstalação só copia os projetos novos e nunca apaga o trabalho do aluno.

## Como montar um projeto novo

Copie a pasta `patch_2g45` e mude os arquivos. Um projeto tem:

- `geometria.py`: as dimensões, numa fonte única, e a gravação do Gerber, do DXF e do
  desenho cotado;
- `simular.py`: as simulações no openEMS e os resultados esperados em `resultados/`;
- `comparar.py`: a comparação da medição (Touchstone) com a simulação;
- `LEIA-ME.md`: o roteiro para o aluno.

Para a fabricação e a medição, o roteiro aponta para os guias gerais:
[guia da CNC](../fabricacao/GUIA_CNC.md) e [guia do VNA](../medicao/GUIA_VNA.md).
