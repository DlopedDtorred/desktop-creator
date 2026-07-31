#!/usr/bin/env bash
# Script de instalación estandarizado para Creador de Accesos Directos (.desktop)

set -e

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_TARGET="$HOME/.local/bin"
APPS_TARGET="$HOME/.local/share/applications"
DESKTOP_FILE="$APPS_TARGET/io.github.desktop_creator.desktop"

mkdir -p "$BIN_TARGET"
mkdir -p "$APPS_TARGET"

chmod +x "$APP_DIR/main.py"

# Enlace simbólico en ~/.local/bin para ejecución directa desde la terminal
ln -sf "$APP_DIR/main.py" "$BIN_TARGET/desktop-creator"

cat << EOF > "$DESKTOP_FILE"
[Desktop Entry]
Type=Application
Name=Creador .desktop
GenericName=Creador de Accesos Directos
Comment=Crea y gestiona archivos .desktop fácilmente para GNOME y Fedora
Exec=desktop-creator
Icon=application-x-executable
Terminal=false
Categories=Utility;Development;Settings;
StartupNotify=true
EOF

chmod +x "$DESKTOP_FILE"
update-desktop-database "$APPS_TARGET" 2>/dev/null || true

echo "¡Instalación completada!"
echo "El acceso directo 'Creador .desktop' ya está disponible en tu menú de aplicaciones."
