# Manutenção: como o pacote é feito

O fluxo [`.github/workflows/pacote.yml`](../.github/workflows/pacote.yml) tem três jobs.

O job `windows` roda num Windows do GitHub Actions e:

1. baixa o ZIP oficial do openEMS para Windows (versão e SHA256 fixos no início do arquivo);
2. instala um Python 3.13 portátil (python-build-standalone, pelo `uv`) e as bibliotecas;
3. instala as wheels do openEMS que vêm no ZIP oficial e o pacote `emslab`;
4. copia os notebooks e a pasta `projetos/` para dentro do pacote;
5. monta `openEMS-lab-windows.zip`;
6. testa o `INSTALAR.bat` numa conta com espaço e acento no nome, confere se os projetos
   foram para `Documentos` e executa os notebooks 00 a 03;
7. guarda o ZIP como artefato do job.

O pacote do Windows é portátil: o Python não tem caminhos absolutos, e os atalhos usam `python -m`.

O job `linux` roda o `simulacao/instalar.sh` num contêiner do Linux Mint 22.3, como um usuário comum
com sudo, e executa os notebooks 00 a 03.

No Linux não há binário oficial do openEMS, e o pacote do Debian é de 2019. Por isso, o
`instalar.sh` compila o openEMS no computador do aluno com os scripts do próprio openEMS
(`scripts/install_deps.sh` e `update_openEMS.sh`). A compilação vai direto para
`~/.local/share/openEMS-lab`, porque o venv e as bibliotecas guardam o caminho completo.

O job `release`, numa tag `v*`, fixa a tag no `simulacao/instalar.sh` e publica o release com
`INSTALAR.bat`, o ZIP, o SHA256 e o `instalar.sh`.

## Publicar uma nova versão

```bash
git tag v0.2.0
git push origin v0.2.0
```

## Trocar a versão do openEMS

- Windows: mude `OPENEMS_TAG`, `OPENEMS_ZIP` e `OPENEMS_SHA256` no fluxo. As wheels do ZIP têm de
  existir para a versão do Python em `PYTHON_VERSION` (a v0.37.0-rc3 tem cp313 e cp314).
- Linux: mude `OPENEMS_TAG` no início do `simulacao/instalar.sh`.

## Testar o instalador do Linux num Linux Mint limpo

```bash
docker run --rm -it -v "$PWD":/repo:ro linuxmintd/mint22.3-amd64 bash -c '
  apt-get update && apt-get install -y sudo
  useradd -m aluno && echo "aluno ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/aluno
  cp -r /repo /home/aluno/lab && chown -R aluno: /home/aluno/lab
  sudo -u aluno -H env EMSLAB_TESTE=1 EMSLAB_SEM_JANELA=1 bash /home/aluno/lab/simulacao/instalar.sh'
```

## Desenvolver o `emslab` no Linux

```bash
pip install -e simulacao/emslab
export CSXCAD_INSTALL_PATH=$HOME/opt/openEMS OPENEMS_INSTALL_PATH=$HOME/opt/openEMS
python -c "import emslab; emslab.verificar()"
```

## Gerar os PDF dos guias

Os guias são escritos em Markdown. Depois de mudar um guia, gere o PDF de novo:

```bash
pip install markdown weasyprint
python fabricacao/figuras.py       # figuras do guia da CNC
python medicao/figuras.py          # figuras do guia do VNA
python docs/gerar_pdf.py fabricacao/GUIA_CNC.md medicao/GUIA_VNA.md
```

As figuras usam o `numpy`, o `matplotlib` e o `shapely`, e a geometria e os resultados de
`projetos/patch_2g45`.

## Estrutura

```
README.md                       visão geral: simular, fabricar e medir
simulacao/                      o openEMS Lab (instalação, notebooks e pacote emslab)
  INSTALAR.bat                  instalador do Windows (também vai no release)
  instalar.sh                   instalador do Linux (também vai no release)
  pacote/                       arquivos que vão para dentro da instalação
    ABRIR.bat, VERIFICAR.bat    Windows
    abrir.sh, verificar.sh      Linux
    LEIA-ME.txt                 leia-me da pasta instalada
    scripts/abrir.py            copia os notebooks e projetos, cria o atalho e abre o JupyterLab
    scripts/ambiente.bat        variáveis de ambiente do openEMS (Windows)
    scripts/ambiente.sh         variáveis de ambiente do openEMS (Linux)
  emslab/                       pacote Python de apoio (geometria, simulação, gráficos)
  notebooks/                    notebooks em português
fabricacao/                     guia da fresadora CNC (MD e PDF), figuras e instalar_linux.sh
medicao/                        guia do VNA (MD e PDF) e figuras
projetos/                       antenas e sensores para simular, fabricar e medir
  patch_2g45/                   sensor de umidade de 2,45 GHz
docs/                           como funciona, problemas comuns, manutenção, gerar_pdf.py
```
