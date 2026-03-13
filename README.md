# MariaDB Backup Manager

Aplicación de escritorio PyQt5 para Linux que gestiona y programa respaldos
de bases de datos MariaDB de forma gráfica.

---

## Stack técnico

- **Lenguaje:** Python 3.8+
- **GUI:** PyQt5 (tema oscuro personalizado)
- **Base de datos:** MariaDB (via `mysqldump`, `mysql`)
- **Automatización:** systemd services + XDG Autostart (.desktop)
- **Empaquetado:** .deb (Debian/Ubuntu/Linux Mint)

---

## Estructura del proyecto

```
mariadb-backup-manager/
├── src/
│   └── mariadb_backup_manager.py     ← Código fuente principal (todo en un archivo)
├── deb/
│   └── mariadb-backup-manager_v1.0_rev2.deb   ← Paquete listo para instalar
├── scripts/
│   └── build_deb.sh             ← Script para recompilar el .deb
└── docs/
    └── CONTEXT.md               ← Contexto técnico para modificaciones
```

---

## Instalación rápida

```bash
sudo apt install ./deb/mariadb-backup-manager_v1.0_rev2.deb
mariadb-backup-manager
```

## Dependencias del sistema

```bash
sudo apt install python3-pyqt5 mariadb-client
```

---

## Ejecutar en desarrollo (sin instalar)

```bash
python3 src/mariadb_backup_manager.py
```

---

## Recompilar el .deb después de modificar

```bash
bash scripts/build_deb.sh
```

---

## Desinstalar

```bash
sudo apt remove mariadb-backup-manager        # conserva config
sudo apt purge mariadb-backup-manager         # elimina todo
```

---

## Archivo de configuración

Se guarda automáticamente en:
```
~/.config/mariadb_backup_manager.json
```

Campos:
```json
{
  "host": "localhost",
  "port": 3306,
  "user": "root",
  "password": "",
  "backup_dir": "~/backups/mariadb",
  "retention_days": 7,
  "autostart_enabled": false,
  "shutdown_enabled": false,
  "first_run_done": true
}
```

---

## Servicios systemd que instala la app

| Servicio | Archivo | Función |
|---|---|---|
| mariadb-backup-inicio | `/etc/systemd/system/mariadb-backup-inicio.service` | Backup al encender |
| mariadb-backup-apagado | `/etc/systemd/system/mariadb-backup-apagado.service` | Backup al apagar |
| Script bash | `/usr/local/bin/mariadb_backup.sh` | Ejecuta los mysqldump |

El servicio de apagado usa `Before=shutdown.target` — el equipo espera
a que termine el backup antes de apagarse.

## Autostart de la app

Crea: `~/.config/autostart/mariadb_backup_manager.desktop`
Método: XDG Autostart (funciona en GNOME, KDE, XFCE, Cinnamon, MATE).
No requiere sudo.
