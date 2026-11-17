#!/usr/bin/env bash
# Instala no Linux Mint 22 (ou Ubuntu 24.04) os programas livres do guia da CNC:
# FlatCAM, bCNC, LibreCAD, KiCad e, se der certo, CAMotics.
#
# Uso:
#   URL=https://raw.githubusercontent.com/prof-davifr/openEMS-lab/main
#   curl -fsSL $URL/fabricacao/guia_cnc/instalar_linux.sh | bash
#
# Pode rodar de novo: o script atualiza o que já está instalado.

set -euo pipefail

FLATCAM_DIR="$HOME/.local/share/flatcam-beta"
BIN="$HOME/.local/bin"
APPS="$HOME/.local/share/applications"
CAMOTICS_DEB="https://camotics.org/builds/release/debian-stable-64bit/camotics_1.2.0_amd64.deb"

passo() { printf '\n==> %s\n' "$*"; }

if [ "$(id -u)" -eq 0 ]; then
    echo "Rode como usuário comum, sem sudo. O script pede a senha quando precisar."
    exit 1
fi

passo "1/6 Pacotes do sistema (pede a senha)"
sudo apt-get update
sudo apt-get install -y \
    git curl python3-tk pipx librecad kicad \
    libgl1 libegl1 libxkbcommon-x11-0 libxcb-xinerama0 libxcb-cursor0 libxcb-icccm4 \
    libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-xkb1

passo "2/6 Acesso à porta USB da CNC (grupo dialout)"
if id -nG "$USER" | grep -qw dialout; then
    echo "Você já está no grupo dialout."
else
    sudo usermod -aG dialout "$USER"
    echo "Adicionado ao grupo dialout. Saia da sessão e entre de novo antes de usar o bCNC."
fi

passo "3/6 bCNC"
pipx ensurepath >/dev/null
if pipx list --short 2>/dev/null | grep -qi '^bcnc '; then
    pipx upgrade bCNC
else
    pipx install bCNC
fi

passo "4/6 FlatCAM (código-fonte, com um Python 3.10 próprio)"
mkdir -p "$BIN" "$APPS"
if ! command -v uv >/dev/null 2>&1 && [ ! -x "$BIN/uv" ]; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi
UV="$(command -v uv || echo "$BIN/uv")"
if [ -d "$FLATCAM_DIR/fonte/.git" ]; then
    git -C "$FLATCAM_DIR/fonte" pull --ff-only
else
    mkdir -p "$FLATCAM_DIR"
    git clone --depth 1 -b Beta https://bitbucket.org/jpcgt/flatcam.git "$FLATCAM_DIR/fonte"
fi
# o FlatCAM é de 2022: precisa do Python 3.10 e de versões da época das bibliotecas
"$UV" venv --allow-existing -p 3.10 "$FLATCAM_DIR/venv"
VIRTUAL_ENV="$FLATCAM_DIR/venv" "$UV" pip install \
    pyqt5 "numpy<1.24" "matplotlib<3.7" "shapely==1.8.5.post1" "vispy==0.9.6" rtree pyopengl \
    "ortools<9.5" "svg.path<6" simplejson freetype-py fontTools rasterio lxml "ezdxf<1.0" qrcode \
    "reportlab<4" "svglib<1.5" dill pyserial "Pillow<10"
cat > "$BIN/flatcam" <<EOF
#!/usr/bin/env bash
cd "$FLATCAM_DIR/fonte" && exec "$FLATCAM_DIR/venv/bin/python" FlatCAM.py "\$@"
EOF
chmod +x "$BIN/flatcam"
cat > "$APPS/flatcam.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=FlatCAM
Comment=CAM para placas de circuito
Exec=$BIN/flatcam
Icon=applications-engineering
Terminal=false
Categories=Development;Engineering;
EOF

passo "5/6 Atalho do bCNC no menu"
cat > "$APPS/bcnc.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=bCNC
Comment=Envia G-code para o GRBL
Exec=$BIN/bCNC
Icon=applications-engineering
Terminal=false
Categories=Development;Engineering;
EOF

passo "6/6 CAMotics (opcional)"
tmp="$(mktemp -d)"
if curl -fsSL -o "$tmp/camotics.deb" "$CAMOTICS_DEB" && sudo apt-get install -y "$tmp/camotics.deb"; then
    echo "CAMotics instalado."
else
    echo "AVISO: o CAMotics não instalou. Ele é opcional: confira o G-code no FlatCAM e no bCNC."
fi
rm -rf "$tmp"

printf '\nINSTALACAO OK\n'
echo "Programas: flatcam, bCNC, librecad, kicad (e camotics, se instalou)."
echo "Se o grupo dialout foi adicionado agora, saia da sessão e entre de novo."
