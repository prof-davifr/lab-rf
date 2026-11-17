# lab-rf

Material para projetar, fabricar e medir antenas e sensores de micro-ondas, feito para
alunos de iniciação científica. Tudo em português e só com programas livres.

| Etapa | O que usar | Onde está |
|---|---|---|
| **1. Simular** | o **openEMS Lab**: openEMS, Python e JupyterLab, com notebooks do básico até um sensor sobre um revestimento | [simulacao/](simulacao) |
| **2. Fabricar** | a fresadora CNC, com FlatCAM e bCNC | [guia da CNC](fabricacao/GUIA_CNC.md) ([PDF](fabricacao/GUIA_CNC.pdf)) |
| **3. Medir** | o analisador de redes vetorial (VNA) | [guia do VNA](medicao/GUIA_VNA.md) ([PDF](medicao/GUIA_VNA.pdf)) |

Os [projetos](projetos) juntam as três etapas. Cada projeto tem a geometria, a simulação, os
arquivos para a CNC, os resultados esperados e um script que compara a medição com a
simulação.

| Projeto | O que é |
|---|---|
| [patch_2g45](projetos/patch_2g45) | sensor patch de 2,45 GHz em FR-4 (45 x 32 mm) que mede a umidade num revestimento de polímero sobre metal |

## 1. Simular: instalar o openEMS Lab

O openEMS Lab instala o openEMS, um Python próprio, o JupyterLab, o pacote de apoio `emslab`,
os notebooks e os projetos, no **Windows** e no **Linux** (Mint, Ubuntu).

### Windows (uma vez)

Não precisa de permissão de administrador nem de compilar nada.

1. Abra a página do [último release](https://github.com/prof-davifr/lab-rf/releases/latest).
2. Em **Assets**, clique em **`INSTALAR.bat`** para baixar o arquivo.
   - Se o navegador avisar que o arquivo "pode ser perigoso", escolha **Manter**.
3. Dê dois cliques em `INSTALAR.bat` na pasta Downloads.
   - Se aparecer **"O Windows protegeu o computador"**, clique em **Mais informações** e depois em
     **Executar assim mesmo**. O aviso aparece porque o arquivo veio da internet.
4. Espere a mensagem **INSTALACAO OK** (de 5 a 15 minutos; o pacote tem cerca de 400 MB).

O instalador cria o atalho **openEMS Lab** na Área de Trabalho.

### Linux (uma vez)

1. Abra o **Terminal** (no Linux Mint: menu > Terminal, ou Ctrl + Alt + T).
2. Copie o comando abaixo, cole no terminal (Ctrl + Shift + V) e tecle Enter:

   ```bash
   curl -fsSL https://github.com/prof-davifr/lab-rf/releases/latest/download/instalar.sh | bash
   ```

3. Quando o instalador pedir, digite a sua senha do computador e tecle Enter.
   - A senha não aparece enquanto você digita. Isso é normal.
4. Espere a mensagem **INSTALACAO OK** (de 15 a 40 minutos: o instalador compila o openEMS).
   - Não feche o terminal. A cada minuto aparece "ainda compilando...".

O instalador cria o item **openEMS Lab** no menu de aplicativos e na Área de Trabalho.
Se o Mint perguntar se confia no atalho da Área de Trabalho, escolha **Confiar e abrir**.

### Uso diário

1. Abra o **openEMS Lab** pelo atalho na Área de Trabalho (no Linux, também pelo menu).
2. O Jupyter abre no navegador. Os notebooks e a pasta `projetos` aparecem no painel da
   esquerda.
3. **Não feche a janela do terminal** enquanto usa o Jupyter. As mensagens do openEMS aparecem nela.
4. Para encerrar: salve (Ctrl + S), feche o navegador e depois feche a janela do terminal.

### Sequência de notebooks

| Notebook | Conteúdo | Tempo |
|---|---|---|
| `00_verificar_instalacao` | confere a instalação | 1 min |
| `01_jupyter_em_10_minutos` | Jupyter, Python, numpy e gráficos | 10 min |
| `02_patch_no_ar` | primeira simulação com a API do openEMS, passo a passo | 20 min |
| `03_patch_sobre_polimero_e_metal` | o sensor sobre a amostra; comparação com o ar | 15 min |
| `04_varrer_espessura_e_permissividade` | varredura paramétrica e curva de calibração simulada | 20 min |
| `05_defeito_vazio` | vazios no revestimento e uma varredura em linha | 20 min |

Os notebooks e os projetos ficam na pasta **Documentos/openEMS-notebooks**. Uma reinstalação
nunca apaga estes arquivos: ela só copia os notebooks e os projetos novos.

### Onde ficam as coisas

| O quê | Windows | Linux |
|---|---|---|
| Programa (openEMS, Python, Jupyter) | `%LOCALAPPDATA%\openEMS-lab` | `~/.local/share/openEMS-lab` |
| Seus notebooks, projetos e figuras | `Documentos\openEMS-notebooks` | `~/Documentos/openEMS-notebooks` |
| Dados das simulações (pode apagar) | `openEMS-simulacoes` na pasta de usuário | `~/openEMS-simulacoes` |
| Registro da instalação | `%LOCALAPPDATA%\openEMS-lab-instalacao.log` | `~/.local/share/openEMS-lab-instalacao.log` |

### Sem internet no laboratório (Windows)

Copie para um pendrive, na mesma pasta, os três arquivos do release:
`INSTALAR.bat`, `openEMS-lab-windows.zip` e `openEMS-lab-windows.zip.sha256`.
No PC do laboratório, dê dois cliques em `INSTALAR.bat` dentro do pendrive. O instalador usa o
ZIP local e não baixa nada.

### Problemas

Veja [docs/problemas_comuns.md](docs/problemas_comuns.md). Para conferir a instalação:

- no Windows, dê dois cliques em `VERIFICAR.bat` dentro de `%LOCALAPPDATA%\openEMS-lab`;
- no Linux, rode `~/.local/share/openEMS-lab/verificar.sh` num terminal.

Para entender o que o openEMS calcula, leia [docs/como_funciona.md](docs/como_funciona.md).

## 2. Fabricar

O [guia da fresadora CNC](fabricacao/GUIA_CNC.md) ([PDF](fabricacao/GUIA_CNC.pdf)) mostra
como fresar uma antena em FR-4, do arquivo Gerber até a placa pronta para o conector: a
segurança, a configuração do GRBL, o G-code no FlatCAM, a ponta de prova, o mapa de altura e
a conferência da placa.

Para instalar no Linux todos os programas do guia (FlatCAM, bCNC, LibreCAD, KiCad e CAMotics):

```bash
URL=https://raw.githubusercontent.com/prof-davifr/lab-rf/main
curl -fsSL $URL/fabricacao/instalar_linux.sh | bash
```

## 3. Medir

O [guia do VNA](medicao/GUIA_VNA.md) ([PDF](medicao/GUIA_VNA.pdf)) mostra como cuidar dos
conectores, configurar a varredura, calibrar (SOL), medir o S11 de uma antena, salvar em
Touchstone e comparar com a simulação.

## Organização do repositório

```
simulacao/     openEMS Lab: instaladores, pacote emslab e notebooks
fabricacao/    guia da CNC e instalador dos programas da CNC no Linux
medicao/       guia do VNA
projetos/      antenas e sensores para simular, fabricar e medir
docs/          como funciona, problemas comuns e manutenção
```

Para manter o pacote, publicar uma versão ou gerar os PDF dos guias, veja
[docs/manutencao.md](docs/manutencao.md).

## Licença

GPL-3.0-or-later, a mesma do openEMS, que vai dentro da instalação.
O openEMS é de Thorsten Liebig e colaboradores: <https://github.com/thliebig/openEMS-Project>.
