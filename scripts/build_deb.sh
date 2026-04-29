#!/bin/bash
# build_deb.sh — Recompila el paquete .deb de MariaDB Backup Manager
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
# Fuente única de versión: src/mariadb_backup_manager.py (constantes APP_VERSION / APP_REVISION).
VERSION=$(grep -oP '^APP_VERSION\s*=\s*"\K[^"]+' "$PROJECT_DIR/src/mariadb_backup_manager.py")
REVISION=$(grep -oP '^APP_REVISION\s*=\s*"\K[^"]+' "$PROJECT_DIR/src/mariadb_backup_manager.py")
PKG_NAME="mariadb-backup-manager_v${VERSION}_rev${REVISION}"
PKG_DIR="/tmp/${PKG_NAME}"

echo "▶ Construyendo MariaDB Backup Manager v${VERSION}..."
echo "  Proyecto: $PROJECT_DIR"

if ! command -v fakeroot &>/dev/null; then
    echo "  Instalando fakeroot..."
    sudo apt-get install -y fakeroot dpkg-dev
fi

rm -rf "$PKG_DIR"

mkdir -p "$PKG_DIR/DEBIAN"
mkdir -p "$PKG_DIR/usr/lib/mariadb-backup-manager"
mkdir -p "$PKG_DIR/usr/bin"
mkdir -p "$PKG_DIR/usr/share/applications"
mkdir -p "$PKG_DIR/usr/share/doc/mariadb-backup-manager"
mkdir -p "$PKG_DIR/usr/share/pixmaps"

echo "  Copiando archivos..."
cp "$PROJECT_DIR/src/mariadb_backup_manager.py" \
   "$PKG_DIR/usr/lib/mariadb-backup-manager/mariadb_backup_manager.py"

cat > "$PKG_DIR/usr/bin/mariadb-backup-manager" << 'EOF'
#!/bin/bash
exec python3 /usr/lib/mariadb-backup-manager/mariadb_backup_manager.py "$@"
EOF

cat > "$PKG_DIR/usr/share/applications/mariadb-backup-manager.desktop" << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=MariaDB Backup Manager
GenericName=MariaDB Backup Manager
Comment=Gestiona y programa respaldos de bases de datos MariaDB
Exec=mariadb-backup-manager
Icon=mariadb-backup-manager
Terminal=false
Categories=Utility;Database;System;
Keywords=mariadb;mysql;backup;database;respaldo;
StartupNotify=true
EOF

cat > "$PKG_DIR/usr/share/pixmaps/mariadb-backup-manager.svg" << 'EOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <rect width="64" height="64" rx="12" fill="#1e1e2e"/>
  <text x="32" y="44" font-size="38" text-anchor="middle" font-family="serif">🐬</text>
</svg>
EOF

cat > "$PKG_DIR/usr/share/doc/mariadb-backup-manager/copyright" << 'EOF'
MariaDB Backup Manager — MIT License
EOF

INSTALLED_SIZE=$(du -sk --exclude=DEBIAN "$PKG_DIR" | cut -f1)

cat > "$PKG_DIR/DEBIAN/control" << EOF
Package: mariadb-backup-manager
Version: ${VERSION}.${REVISION}
Section: database
Priority: optional
Architecture: all
Installed-Size: ${INSTALLED_SIZE}
Depends: python3 (>= 3.8), python3-pyqt5, mariadb-client
Maintainer: BSG <tuxor.max@gmail.com>
Homepage: https://github.com/tuxormax/mariadb-backup-manager
Description: Gestor gráfico de respaldos para MariaDB
 Aplicación de escritorio para Linux que permite gestionar y programar
 respaldos de bases de datos MariaDB de forma visual e intuitiva.
EOF

cat > "$PKG_DIR/DEBIAN/preinst" << 'EOF'
#!/bin/bash
# Cierra cualquier instancia corriendo para permitir reemplazar archivos
pkill -f "mariadb_backup_manager.py" 2>/dev/null || true
pkill -x "mariadb-backup-manager" 2>/dev/null || true
sleep 0.3
exit 0
EOF

cat > "$PKG_DIR/DEBIAN/postinst" << 'EOF'
#!/bin/bash
set -e
chmod +x /usr/bin/mariadb-backup-manager
if ! python3 -c "import PyQt5" 2>/dev/null; then
    pip3 install PyQt5 --break-system-packages --quiet 2>/dev/null || true
fi
command -v update-desktop-database &>/dev/null && \
    update-desktop-database /usr/share/applications/ 2>/dev/null || true

# Relanzar la app para los usuarios que la tenían corriendo (preinst la mató).
# Detectamos por /home/*/.config/autostart/*.desktop para saber qué usuario la usa.
for home_dir in /home/*; do
    [ -f "$home_dir/.config/autostart/mariadb_backup_manager.desktop" ] || continue
    user=$(basename "$home_dir")
    uid=$(id -u "$user" 2>/dev/null) || continue
    display=$(ps -u "$user" -o pid= 2>/dev/null | xargs -I{} cat /proc/{}/environ 2>/dev/null \
              | tr '\0' '\n' | grep -m1 '^DISPLAY=' | cut -d= -f2)
    [ -z "$display" ] && display=":0"
    su - "$user" -c "DISPLAY=$display XDG_RUNTIME_DIR=/run/user/$uid \
        nohup /usr/bin/mariadb-backup-manager --minimized \
        > /tmp/mariadb-backup-manager-$user.log 2>&1 &" >/dev/null 2>&1 || true
done

echo "✓ MariaDB Backup Manager instalado. Si no estaba corriendo, ejecuta: mariadb-backup-manager"
exit 0
EOF

# prerm: en upgrade NO tocamos config ni servicios. En remove/purge desinstalamos
# servicios/sudoers/autostart pero NO el JSON (ese sólo se borra en `apt purge` vía postrm purge).
cat > "$PKG_DIR/DEBIAN/prerm" << 'EOF'
#!/bin/bash
set -e
# Cierra instancias corriendo antes de remover/actualizar
pkill -f "mariadb_backup_manager.py" 2>/dev/null || true
pkill -x "mariadb-backup-manager" 2>/dev/null || true
case "$1" in
    upgrade|failed-upgrade|deconfigure)
        # No tocar nada en upgrade — preservar configuración y servicios
        ;;
    remove|purge)
        for home_dir in /home/*; do
            rm -f "$home_dir/.config/autostart/mariadb_backup_manager.desktop"
        done
        systemctl disable mariadb-backup-inicio.service 2>/dev/null || true
        systemctl disable mariadb-backup-apagado.service 2>/dev/null || true
        rm -f /etc/systemd/system/mariadb-backup-inicio.service
        rm -f /etc/systemd/system/mariadb-backup-apagado.service
        rm -f /usr/local/bin/mariadb_backup.sh
        rm -f /etc/sudoers.d/mariadb-backup-manager
        systemctl daemon-reload 2>/dev/null || true
        ;;
esac
exit 0
EOF

# Solo `apt purge` borra el JSON de configuración del usuario.
cat > "$PKG_DIR/DEBIAN/postrm" << 'EOF'
#!/bin/bash
set -e
case "$1" in
    purge)
        for home_dir in /home/*; do
            rm -f "$home_dir/.config/mariadb_backup_manager.json"
        done
        ;;
esac
command -v update-desktop-database &>/dev/null && \
    update-desktop-database /usr/share/applications/ 2>/dev/null || true
exit 0
EOF

chmod 755 "$PKG_DIR/DEBIAN/preinst"
chmod 755 "$PKG_DIR/DEBIAN/postinst"
chmod 755 "$PKG_DIR/DEBIAN/prerm"
chmod 755 "$PKG_DIR/DEBIAN/postrm"
chmod 755 "$PKG_DIR/usr/bin/mariadb-backup-manager"
chmod 644 "$PKG_DIR/usr/lib/mariadb-backup-manager/mariadb_backup_manager.py"
chmod 644 "$PKG_DIR/usr/share/applications/mariadb-backup-manager.desktop"
chmod 644 "$PKG_DIR/usr/share/pixmaps/mariadb-backup-manager.svg"

echo "  Empaquetando..."
OUTPUT="$PROJECT_DIR/deb/${PKG_NAME}.deb"
fakeroot dpkg-deb --build "$PKG_DIR" "$OUTPUT"

echo ""
echo "✓ Paquete generado:"
ls -lh "$OUTPUT"
echo ""
echo "  Instalar con:"
echo "  sudo apt install $OUTPUT"
