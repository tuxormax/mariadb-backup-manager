# Checklist de regresiones — mariadb-backup-manager

**OBLIGATORIO**: leer este archivo antes de modificar `src/mariadb_backup_manager.py` y verificar cada ítem después del cambio. Si arreglas un bug nuevo, agrégalo al final con su revisión.

Mantén paridad con `pg-backup-manager/docs/REGRESSIONS.md` — son apps gemelas.

---

## Comportamientos críticos a NO romper

### Log y estado al iniciar
- [ ] **Al arrancar la app**, en el panel Log aparece el estado de:
  - Servicio systemd `mariadb-backup-inicio` (instalado / no instalado)
  - Servicio systemd `mariadb-backup-apagado` (instalado / no instalado)
  - Regla sudoers `/etc/sudoers.d/mariadb-backup-manager` (instalada / no)
  - Apagado programado (sí + hora del día actual, o "no hay")
  - *Verificar:* función `_log_startup_status()` llamada desde `__init__`. *(rev16)*
- [ ] La pestaña **Apagado** muestra labels con el estado de los dos servicios systemd (verde ✓ / rojo ✗).
  - *Verificar:* `_update_service_status()`.
- [ ] La pestaña Apagado muestra la hora programada de hoy si existe `scheduled_shutdown`.
  - *Verificar:* `_update_today_schedule()`.

### Persistencia de configuración
- [ ] El archivo `~/.config/mariadb_backup_manager.json` guarda: `host`, `port`, `user`, `password`, `backup_dir`, `retention_days`, `scheduled_shutdown` (con `horas_dia`), `selected_dbs`, `autostart_enabled`, `shutdown_enabled`. *(rev16 agrega `selected_dbs`)*
- [ ] Las bases seleccionadas en la UI se persisten en `selected_dbs` y se restauran al cargar las bases del servidor. Primera carga (selected_dbs=None) marca todas. *(rev16)*
- [ ] El `prerm` del .deb **NO borra** el JSON de configuración en `upgrade` ni en `remove`. Solo `apt purge` lo borra (vía `postrm purge`). Reinstalar conserva configuración. *(rev16)*
- [ ] El `prerm` solo desinstala servicios systemd, sudoers y autostart en `remove|purge`, no en `upgrade`. *(rev16)*

### Backup
- [ ] Backup manual: si no hay bases marcadas, muestra `QMessageBox.warning("Sin selección")` y no procede.
- [ ] Backup pre-apagado: si no hay bases marcadas en la UI, lista automáticamente todas las bases del servidor (excluyendo `information_schema`/`performance_schema`/`mysql`/`sys`) y las respalda antes de apagar. **No** apagar sin backup. *(rev16)*
- [ ] El backup usa `mysqldump` con las opciones definidas en `BackupWorker`.
- [ ] Limpieza de backups viejos: archivos > `retention_days` se eliminan tras cada backup exitoso.
- [ ] Eliminación múltiple de backups en pestaña Historial: soporta multi-selección.
- [ ] Nombres de archivo: `db_fecha_tag_hora.sql`.
- [ ] No hay backup duplicado al apagar (solo se ejecuta una vez la cadena backup→apagado). *(commit 2fadc09)*

### Apagado programado
- [ ] Botón "Programar apagado" pide confirmación con la hora exacta y delta en minutos.
- [ ] Si la regla sudoers NO existe, antes de programar se ofrece instalar servicios. *(rev16)*
- [ ] La programación se persiste en `~/.config/mariadb_backup_manager.json` y se restaura al arrancar la app.
- [ ] Cancelar apagado pide confirmación y borra `scheduled_shutdown` del config.
- [ ] Cuenta regresiva en pestaña Apagado: muestra **hora de apagado** (no countdown). *(commit eb38346)*
- [ ] Sin texto duplicado en el estado de apagado. *(commits 13f30c9, fa40948)*
- [ ] Días de la semana en 2 columnas (Lun-Vie | Sáb-Dom). *(commit 8fef9ea)*

### Ejecución de apagado (`_do_shutdown_now`)
- [ ] Intenta `sudo -n shutdown -h now` primero. Si rc==0 → marca config como apagado en curso y retorna. *(rev16)*
- [ ] Cada paso del intento de apagado se registra en el log con su error real (rc + stderr). *(rev16)*
- [ ] Si `sudo -n` falla y la regla sudoers no existe, intenta instalar servicios y reintenta. *(rev16)*
- [ ] Si todos los intentos fallan: **NO** borra `scheduled_shutdown`, muestra `QMessageBox` con la causa, conserva la programación para reintento manual. *(rev16)*
- [ ] El apagado solo se ejecuta DESPUÉS de que termine el backup (encadenado por `_shutdown_pending` + `_on_backup_finished`).

### Servicios systemd / sudoers
- [ ] Botón "Instalar / Actualizar servicios systemd" crea: `/usr/local/bin/mariadb_backup.sh`, los dos `.service`, y `/etc/sudoers.d/mariadb-backup-manager` con `NOPASSWD: /sbin/shutdown` para el usuario actual.
- [ ] Botón "Desinstalar servicios" elimina los 4 archivos.
- [ ] El `prerm` del .deb hace la misma limpieza al desinstalar el paquete (solo en remove/purge).
- [ ] El servicio `mariadb-backup-apagado.service` corre `mariadb_backup.sh apagado` antes de `shutdown.target`.

### Tray / autostart / cierre
- [ ] La app inicia minimizada al tray cuando se arranca con `--minimized`. *(commit 2fadc09)*
- [ ] Cerrar la ventana NO sale; minimiza al tray.
- [ ] Salir del tray pide contraseña. *(commit 13f30c9)*
- [ ] Autostart `.desktop` se crea/actualiza siempre al arrancar la app (`_ensure_app_autostart`).

### UI
- [ ] Tema oscuro, constantes de color al inicio del archivo.
- [ ] **Layout responsive de horas por día**: usar `FlowLayout` (no `QHBoxLayout` con 2 columnas fijas), las celdas se reacomodan a 2/3/4 columnas según el ancho. La pestaña Apagado va dentro de un `QScrollArea` para ventanas chicas. *(rev17)*
  - *Verificar:* clase `FlowLayout` (top del archivo) + `_tab_apagado()` envuelve todo en `QScrollArea`.
- [ ] **NUNCA usar 2 columnas fijas (Lun-Vie | Sáb-Dom)**: en pantallas chicas la columna izquierda colapsa y los campos se solapan verticalmente. Usar siempre `FlowLayout` + `cell.setFixedHeight(42)` + `cell.setMinimumWidth(220)`. *(regresión recurrente — rev17)*
- [ ] El QTimeEdit dentro del time picker tiene padding interno mínimo (`padding: 0px; padding-left: 4px; padding-right: 4px;`). *(rev17)*
- [ ] Campos de hora (cada día) usan el patrón `[−] [HH:MM] [+]`: botón menos a la izquierda, valor centrado, botón más a la derecha. Botones internos del QTimeEdit deshabilitados. Cada click cambia ±30 minutos. *(commit 8c16364)*
  - *Verificar:* helper `_make_time_edit()`.
- [ ] Campos de hora por día tienen ancho suficiente.

### Empaquetado
- [ ] **Fuente única de versión**: las constantes `APP_VERSION` y `APP_REVISION` en `src/mariadb_backup_manager.py` son la única fuente. El footer (`lbl_footer`) las usa con f-string. `scripts/build_deb.sh` las extrae con `grep -oP`. **Bumpear solo en el .py** — el .deb y el footer toman valor automáticamente. *(rev17)*
- [ ] `scripts/build_deb.sh`: nombre `mariadb-backup-manager_v${VERSION}_rev${REVISION}.deb`.
- [ ] `control` lleva `Maintainer: BSG`, `Installed-Size`, `Homepage`. *(commit f18e120)*
- [ ] `Depends`: python3 ≥ 3.8, python3-pyqt5, mariadb-client.
- [ ] El `preinst` mata el proceso corriendo antes de reemplazar archivos. *(commit 8c16364)*
- [ ] El `postinst` relanza la app para los usuarios que la tenían corriendo (detectados por su autostart `.desktop`). *(rev16)*

---

## Cómo extender este checklist

Cuando arregles un bug nuevo:
1. Agrégalo en la sección correspondiente con `- [ ] descripción *(revN)*`.
2. Indica dónde verificar (`*Verificar:* función_o_línea`).
3. Si la corrección aplica también a `pg-backup-manager`, replícala allá.
