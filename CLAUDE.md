# CLAUDE.md — Instrucciones para Claude Code

Este archivo es leído automáticamente por Claude Code al abrir el proyecto.

---

## Descripción del proyecto

**MariaDB Backup Manager** — Aplicación de escritorio PyQt5 para Linux.
Gestiona y programa respaldos de bases de datos MariaDB/MySQL.

**Archivo principal:** `src/mariadb_backup_manager.py`
**Contexto técnico completo:** `docs/CONTEXT.md`

---

## Comandos útiles

```bash
# Ejecutar en desarrollo
python3 src/mariadb_backup_manager.py

# Verificar sintaxis sin ejecutar
python3 -m py_compile src/mariadb_backup_manager.py && echo "OK"

# Recompilar el .deb después de cambios
bash scripts/build_deb.sh

# Instalar el .deb generado
sudo apt install ./deb/mariadb-backup-manager_v1.0_rev12.deb

# Reinstalar (actualizar versión instalada)
sudo apt install --reinstall ./deb/mariadb-backup-manager_v1.0_rev12.deb
```

---

## Stack

- Python 3.8+ / PyQt5
- MariaDB/MySQL via `mysqldump` y `mysql` (mariadb-client / mysql-client)
- systemd para servicios de backup automático
- XDG Autostart para iniciar la app con la sesión
- Empaquetado .deb (fakeroot + dpkg-deb)

---

## Paridad con pg-backup-manager

Este proyecto es el gemelo para MariaDB del proyecto `pg-backup-manager`.
Ambos comparten la misma estructura de clases, métodos y flujo de UI.
Cuando se actualice uno, revisar si el cambio aplica al otro.

Diferencias intencionales:
- Motor de BD: `mysqldump`/`mysql` vs `pg_dump`/`psql`
- Función de prueba: `_test_mariadb_connection` vs `_test_pg_connection`
- Config JSON: `~/.config/mariadb_backup_manager.json`
- Servicios systemd: `mariadb-backup-*.service`

---

## Antes de modificar

Lee `docs/CONTEXT.md` — contiene:
- Arquitectura del código con números de línea aproximados
- Patrones usados (workers, subprocess, log, etc.)
- Convenciones de nombres de variables
- Cómo agregar nuevas pestañas
- Lista de mejoras pendientes

---

## Estilo de código

- Tema oscuro: colores definidos como constantes al inicio del archivo
- HTML inline en los QLabel para colores: `f'<span style="color:{SUCCESS}">✓</span>'`
- Workers QThread para operaciones que bloquean (backup, listado de DBs)
- Guardar referencia del worker en `self._w*` para evitar que el GC lo destruya
- Configuración persistida en JSON: `~/.config/mariadb_backup_manager.json`
