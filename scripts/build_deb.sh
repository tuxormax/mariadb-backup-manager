#!/bin/bash
# build_deb.sh — Recompila el paquete .deb de MariaDB Backup Manager
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VERSION="1.0"
REVISION="7"
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

cat > "$PKG_DIR/DEBIAN/control" << EOF
Package: mariadb-backup-manager
Version: ${VERSION}.${REVISION}
Section: database
Priority: optional
Architecture: all
Depends: python3 (>= 3.8), python3-pyqt5, mariadb-client
Maintainer: MariaDB Backup Manager <admin@localhost>
Description: Gestor gráfico de respaldos para MariaDB
 Aplicación de escritorio para Linux que permite gestionar y programar
 respaldos de bases de datos MariaDB de forma visual e intuitiva.
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
echo "✓ MariaDB Backup Manager instalado. Ejecuta: mariadb-backup-manager"
exit 0
EOF

cat > "$PKG_DIR/DEBIAN/prerm" << 'EOF'
#!/bin/bash
set -e
for home_dir in /home/*; do
    rm -f "$home_dir/.config/autostart/mariadb_backup_manager.desktop"
    rm -f "$home_dir/.config/mariadb_backup_manager.json"
done
systemctl disable mariadb-backup-inicio.service 2>/dev/null || true
systemctl disable mariadb-backup-apagado.service 2>/dev/null || true
rm -f /etc/systemd/system/mariadb-backup-inicio.service
rm -f /etc/systemd/system/mariadb-backup-apagado.service
rm -f /usr/local/bin/mariadb_backup.sh
rm -f /etc/sudoers.d/mariadb-backup-manager
systemctl daemon-reload 2>/dev/null || true
exit 0
EOF

cat > "$PKG_DIR/DEBIAN/postrm" << 'EOF'
#!/bin/bash
set -e
command -v update-desktop-database &>/dev/null && \
    update-desktop-database /usr/share/applications/ 2>/dev/null || true
exit 0
EOF

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
