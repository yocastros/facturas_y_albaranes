#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  Instalador del Sistema de Facturas y Albaranes
#  Compatible con: Ubuntu/Debian · Fedora/CentOS/RHEL
# ═══════════════════════════════════════════════════════════

set -e

AZUL='\033[0;34m'
VERDE='\033[0;32m'
ROJO='\033[0;31m'
AMARILLO='\033[1;33m'
NC='\033[0m'

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${AZUL}"
echo "═══════════════════════════════════════════════════"
echo "  Sistema de Gestión de Facturas y Albaranes v1.0"
echo "  Instalador Linux"
echo "═══════════════════════════════════════════════════"
echo -e "${NC}"

# ── Detectar distribución ──────────────────────────────────
detectar_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$ID"
    elif command -v apt-get &>/dev/null; then
        echo "debian"
    elif command -v dnf &>/dev/null; then
        echo "fedora"
    elif command -v yum &>/dev/null; then
        echo "centos"
    else
        echo "unknown"
    fi
}

DISTRO=$(detectar_distro)
echo -e "${AMARILLO}Sistema detectado: $DISTRO${NC}"

# ── Instalar dependencias del sistema ─────────────────────
instalar_sistema() {
    echo -e "\n${AZUL}[1/5] Instalando dependencias del sistema...${NC}"

    case "$DISTRO" in
        ubuntu|debian|linuxmint|pop)
            sudo apt-get update -q
            sudo apt-get install -y \
                python3 python3-pip python3-tk \
                tesseract-ocr tesseract-ocr-spa \
                poppler-utils \
                libgl1-mesa-glx libglib2.0-0
            ;;
        fedora)
            sudo dnf install -y \
                python3 python3-pip python3-tkinter \
                tesseract tesseract-langpack-spa \
                poppler-utils \
                mesa-libGL glib2
            ;;
        centos|rhel)
            sudo yum install -y epel-release
            sudo yum install -y \
                python3 python3-pip python3-tkinter \
                tesseract tesseract-langpack-spa \
                poppler-utils
            ;;
        *)
            echo -e "${AMARILLO}Distro no reconocida. Intentando con apt-get...${NC}"
            sudo apt-get update -q
            sudo apt-get install -y python3 python3-pip python3-tk \
                tesseract-ocr tesseract-ocr-spa poppler-utils
            ;;
    esac

    echo -e "${VERDE}✓ Dependencias del sistema instaladas${NC}"
}

# ── Instalar dependencias Python ──────────────────────────
instalar_python() {
    echo -e "\n${AZUL}[2/5] Instalando dependencias Python...${NC}"
    cd "$DIR/backend"
    pip3 install -r requirements.txt --quiet
    pip3 install pystray pillow --quiet
    echo -e "${VERDE}✓ Dependencias Python instaladas${NC}"
}

# ── Verificar instalación ─────────────────────────────────
verificar() {
    echo -e "\n${AZUL}[3/5] Verificando instalación...${NC}"
    local errores=0

    if command -v tesseract &>/dev/null; then
        echo -e "${VERDE}✓ Tesseract: $(tesseract --version 2>&1 | head -1)${NC}"
    else
        echo -e "${ROJO}✗ Tesseract no encontrado${NC}"
        errores=$((errores+1))
    fi

    if command -v pdftoppm &>/dev/null; then
        echo -e "${VERDE}✓ Poppler: OK${NC}"
    else
        echo -e "${ROJO}✗ Poppler no encontrado${NC}"
        errores=$((errores+1))
    fi

    if python3 -c "import flask" 2>/dev/null; then
        echo -e "${VERDE}✓ Flask: OK${NC}"
    else
        echo -e "${ROJO}✗ Flask no instalado${NC}"
        errores=$((errores+1))
    fi

    if [ $errores -gt 0 ]; then
        echo -e "${ROJO}Hay $errores error(es). Revisa los mensajes anteriores.${NC}"
        exit 1
    fi
}

# ── Crear acceso directo ──────────────────────────────────
crear_acceso() {
    echo -e "\n${AZUL}[4/5] Creando acceso directo...${NC}"

    # Script lanzador
    cat > "$DIR/facturas.sh" << EOF
#!/bin/bash
cd "$DIR"
python3 start.py
EOF
    chmod +x "$DIR/facturas.sh"

    # Entrada en el menú de aplicaciones (.desktop)
    DESKTOP_FILE="$HOME/.local/share/applications/facturas-albaranes.desktop"
    mkdir -p "$HOME/.local/share/applications"
    cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Facturas y Albaranes
Comment=Sistema de Gestión de Facturas y Albaranes
Exec=$DIR/facturas.sh
Icon=$DIR/frontend/favicon.ico
Terminal=false
Categories=Office;Finance;
EOF
    chmod +x "$DESKTOP_FILE"

    # Copiar al escritorio si existe
    if [ -d "$HOME/Desktop" ]; then
        cp "$DESKTOP_FILE" "$HOME/Desktop/Facturas y Albaranes.desktop"
        chmod +x "$HOME/Desktop/Facturas y Albaranes.desktop"
        echo -e "${VERDE}✓ Acceso directo creado en el escritorio${NC}"
    elif [ -d "$HOME/Escritorio" ]; then
        cp "$DESKTOP_FILE" "$HOME/Escritorio/Facturas y Albaranes.desktop"
        chmod +x "$HOME/Escritorio/Facturas y Albaranes.desktop"
        echo -e "${VERDE}✓ Acceso directo creado en el escritorio${NC}"
    fi

    echo -e "${VERDE}✓ Añadido al menú de aplicaciones${NC}"
}

# ── Finalizar ─────────────────────────────────────────────
finalizar() {
    echo -e "\n${AZUL}[5/5] Instalación completada${NC}"
    echo -e "${VERDE}"
    echo "═══════════════════════════════════════════════════"
    echo "  ¡Instalación completada con éxito!"
    echo ""
    echo "  Para arrancar el sistema:"
    echo "  → Doble clic en el icono del escritorio"
    echo "  → O ejecuta: python3 $DIR/start.py"
    echo "═══════════════════════════════════════════════════"
    echo -e "${NC}"
}

# ── Ejecución principal ───────────────────────────────────
instalar_sistema
instalar_python
verificar
crear_acceso
finalizar
