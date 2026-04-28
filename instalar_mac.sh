#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  Instalador del Sistema de Facturas y Albaranes
#  Compatible con: macOS 11+ (Intel y Apple Silicon)
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
echo "  Instalador macOS"
echo "═══════════════════════════════════════════════════"
echo -e "${NC}"

# ── Detectar arquitectura ─────────────────────────────────
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
    echo -e "${AMARILLO}Apple Silicon (M1/M2/M3) detectado${NC}"
    BREW_PREFIX="/opt/homebrew"
else
    echo -e "${AMARILLO}Intel Mac detectado${NC}"
    BREW_PREFIX="/usr/local"
fi

# ── Instalar Homebrew si no está ─────────────────────────
instalar_brew() {
    echo -e "\n${AZUL}[1/5] Verificando Homebrew...${NC}"
    if ! command -v brew &>/dev/null; then
        echo "Homebrew no encontrado. Instalando..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        # Añadir al PATH para Apple Silicon
        if [ "$ARCH" = "arm64" ]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
    fi
    echo -e "${VERDE}✓ Homebrew: $(brew --version | head -1)${NC}"
}

# ── Instalar dependencias del sistema ─────────────────────
instalar_sistema() {
    echo -e "\n${AZUL}[2/5] Instalando Tesseract y Poppler...${NC}"
    brew install tesseract tesseract-lang poppler
    echo -e "${VERDE}✓ Tesseract y Poppler instalados${NC}"
}

# ── Instalar Python si no está ────────────────────────────
instalar_python_deps() {
    echo -e "\n${AZUL}[3/5] Instalando dependencias Python...${NC}"

    # Asegurar que pip está disponible
    if ! command -v pip3 &>/dev/null; then
        brew install python3
    fi

    cd "$DIR/backend"
    pip3 install -r requirements.txt --quiet
    pip3 install pystray pillow --quiet
    echo -e "${VERDE}✓ Dependencias Python instaladas${NC}"
}

# ── Verificar instalación ─────────────────────────────────
verificar() {
    echo -e "\n${AZUL}[4/5] Verificando instalación...${NC}"
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
        echo -e "${ROJO}Hay $errores error(es).${NC}"
        exit 1
    fi
}

# ── Crear app en el Dock / Aplicaciones ──────────────────
crear_acceso() {
    echo -e "\n${AZUL}[5/5] Creando acceso directo...${NC}"

    APP_DIR="$DIR/FacturasAlbaranes.app"
    CONTENTS="$APP_DIR/Contents"
    MACOS="$CONTENTS/MacOS"
    RESOURCES="$CONTENTS/Resources"

    mkdir -p "$MACOS" "$RESOURCES"

    # Script ejecutable de la app
    cat > "$MACOS/FacturasAlbaranes" << APPEOF
#!/bin/bash
# Añadir Homebrew al PATH
export PATH="$BREW_PREFIX/bin:\$PATH"
export PYTHONIOENCODING=utf-8
cd "$DIR"
python3 "$DIR/start.py"
APPEOF
    chmod +x "$MACOS/FacturasAlbaranes"

    # Info.plist
    cat > "$CONTENTS/Info.plist" << PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>Facturas y Albaranes</string>
    <key>CFBundleDisplayName</key>
    <string>Facturas y Albaranes</string>
    <key>CFBundleIdentifier</key>
    <string>es.esenex.facturas-albaranes</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleExecutable</key>
    <string>FacturasAlbaranes</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSUIElement</key>
    <true/>
</dict>
</plist>
PLISTEOF

    # Copiar al escritorio
    DESKTOP="$HOME/Desktop"
    [ -d "$HOME/Escritorio" ] && DESKTOP="$HOME/Escritorio"
    cp -r "$APP_DIR" "$DESKTOP/"

    echo -e "${VERDE}✓ App creada en: $APP_DIR${NC}"
    echo -e "${VERDE}✓ Acceso directo en el escritorio${NC}"

    echo -e "${VERDE}"
    echo "═══════════════════════════════════════════════════"
    echo "  Instalacion completada!"
    echo ""
    echo "  Doble clic en 'Facturas y Albaranes' en el"
    echo "  escritorio para arrancar el sistema."
    echo ""
    echo "  Si macOS bloquea la app la primera vez:"
    echo "  Ajustes > Privacidad y seguridad > Abrir igualmente"
    echo "═══════════════════════════════════════════════════"
    echo -e "${NC}"
}

# ── Ejecución principal ───────────────────────────────────
instalar_brew
instalar_sistema
instalar_python_deps
verificar
crear_acceso
