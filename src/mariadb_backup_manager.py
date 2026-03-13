#!/usr/bin/env python3
"""
mariadb_backup_manager.py — MariaDB Backup Manager para Linux
Requiere: PyQt5, mariadb-client (mysqldump, mysql)
"""

import sys
import os
import subprocess
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QTextEdit, QTableWidget,
    QTableWidgetItem, QTabWidget, QCheckBox, QSpinBox, QFileDialog,
    QMessageBox, QHeaderView, QFrame, QProgressBar, QDialog, QTimeEdit,
    QRadioButton, QButtonGroup, QScrollArea, QComboBox,
    QSystemTrayIcon, QMenu, QAction
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QTime
from PyQt5.QtGui import QColor, QTextCursor, QIcon, QPixmap, QPainter, QFont

# ─── Constantes ────────────────────────────────────────────────────────────────
APP_NAME     = "MariaDB Backup Manager"
CONFIG_FILE  = os.path.expanduser("~/.config/mariadb_backup_manager.json")
CURRENT_USER = os.environ.get("USER", os.environ.get("LOGNAME", "user"))

# ─── Colores ───────────────────────────────────────────────────────────────────
DARK_BG      = "#1a1a2e"
PANEL_BG     = "#222236"
INPUT_BG     = "#2a2a42"
ACCENT       = "#2ecc71"
ACCENT_HOVER = "#45d98a"
SUCCESS      = "#2ecc71"
WARNING      = "#f1c40f"
ERROR        = "#e74c3c"
TEXT         = "#ffffff"
TEXT_MUTED   = "#b0b0b0"
BORDER       = "#3a3a55"

STYLESHEET = f"""
QMainWindow, QWidget, QDialog {{
    background-color: {DARK_BG};
    color: {TEXT};
    font-family: 'Segoe UI', 'Ubuntu', sans-serif;
    font-size: 15px;
}}
QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    background: {PANEL_BG};
}}
QTabBar::tab {{
    background: {INPUT_BG};
    color: {TEXT_MUTED};
    padding: 8px 20px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}}
QTabBar::tab:selected {{ background: {ACCENT}; color: white; }}
QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    margin-top: 12px;
    padding: 14px;
    background: {PANEL_BG};
    font-weight: bold;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; color: {ACCENT}; }}
QLabel, QCheckBox, QRadioButton {{ background: transparent; }}
QGroupBox QWidget {{ background: transparent; }}
QLineEdit, QSpinBox, QComboBox {{
    background: {INPUT_BG};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 6px 10px;
    color: {TEXT};
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border: 1px solid {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox::down-arrow {{ image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 6px solid {TEXT}; }}
QComboBox QAbstractItemView {{ background: {INPUT_BG}; color: {TEXT}; border: 1px solid {BORDER}; selection-background-color: {ACCENT}; }}
QPushButton {{
    background: {ACCENT}; color: white; border: none;
    border-radius: 6px; padding: 8px 18px; font-weight: bold;
}}
QPushButton:hover {{ background: {ACCENT_HOVER}; }}
QPushButton:disabled {{ background: {BORDER}; color: {TEXT_MUTED}; }}
QPushButton#btnDanger {{ background: {ERROR}; }}
QPushButton#btnDanger:hover {{ background: #ff6e6e; }}
QPushButton#btnSuccess {{ background: #2d8a4e; }}
QPushButton#btnSuccess:hover {{ background: #3aaa62; }}
QPushButton#btnSecondary {{
    background: {INPUT_BG}; border: 1px solid {BORDER}; color: {TEXT};
}}
QPushButton#btnSecondary:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}
QTextEdit {{
    background: #12121e; border: 1px solid {BORDER}; border-radius: 6px;
    padding: 8px; color: #a6e3a1;
    font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
    font-size: 14px;
}}
QTableWidget {{
    background: {PANEL_BG}; border: 1px solid {BORDER}; border-radius: 6px;
    gridline-color: {BORDER}; alternate-background-color: {INPUT_BG};
}}
QTableWidget::item {{ padding: 6px; }}
QTableWidget::item:selected {{ background: {ACCENT}; color: white; }}
QHeaderView::section {{
    background: {INPUT_BG}; color: {TEXT_MUTED}; padding: 8px;
    border: none; border-bottom: 1px solid {BORDER}; font-weight: bold;
}}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 2px solid {BORDER}; border-radius: 3px; background: {INPUT_BG};
}}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
QProgressBar {{
    background: {INPUT_BG}; border: 1px solid {BORDER};
    border-radius: 5px; height: 12px; text-align: center;
}}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 4px; }}
QScrollBar:vertical {{ background: {INPUT_BG}; width: 8px; border-radius: 4px; }}
QScrollBar::handle:vertical {{
    background: {BORDER}; border-radius: 4px; min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{ background: {ACCENT}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QLabel#labelTitle {{ font-size: 22px; font-weight: bold; color: {ACCENT}; }}
QLabel#labelStatus {{ color: {TEXT_MUTED}; font-size: 15px; }}
QFrame#separator {{ background: {BORDER}; max-height: 1px; }}
"""


# ══════════════════════════════════════════════════════════════════════════════
# Utilidades de permisos
# ══════════════════════════════════════════════════════════════════════════════

def can_write_to(path: str) -> bool:
    p = Path(path)
    check = p
    while not check.exists():
        parent = check.parent
        if parent == check:
            return False
        check = parent
    return os.access(str(check), os.W_OK)


def prepare_directory_with_sudo(path: str, sudo_password: str):
    script = f"mkdir -p '{path}' && chown -R {CURRENT_USER}:{CURRENT_USER} '{path}' && chmod 750 '{path}'"
    try:
        proc = subprocess.run(
            ["sudo", "-S", "bash", "-c", script],
            input=sudo_password + "\n",
            capture_output=True, text=True, timeout=15
        )
        if proc.returncode == 0:
            return True, "Directorio creado y permisos asignados."
        err = proc.stderr.strip().lower()
        if "incorrect" in err or "try again" in err or "sorry" in err:
            return False, "Contraseña incorrecta."
        return False, proc.stderr.strip() or "Error desconocido."
    except subprocess.TimeoutExpired:
        return False, "Tiempo de espera agotado."
    except Exception as e:
        return False, str(e)


# ══════════════════════════════════════════════════════════════════════════════
# Diálogo: Contraseña sudo
# ══════════════════════════════════════════════════════════════════════════════

class SudoDialog(QDialog):
    def __init__(self, target_dir: str, parent=None):
        super().__init__(parent)
        self.target_dir = target_dir
        self.setWindowTitle("Permisos de administrador requeridos")
        self.setMinimumWidth(500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        title = QLabel("🔒  Permisos de administrador")
        title.setStyleSheet(f"font-size:17px; font-weight:bold; color:{ACCENT};")
        layout.addWidget(title)

        info = QLabel(
            f"El directorio que elegiste no es accesible con tu usuario normal:\n\n"
            f"  <b>{self.target_dir}</b>\n\n"
            f"Ingresa tu contraseña <b>sudo</b> para crear el directorio y asignar\n"
            f"los permisos a <b>{CURRENT_USER}</b>.\n\n"
            f"✓  Esto <b>solo se hace una vez</b>. Los respaldos futuros no necesitarán sudo."
        )
        info.setWordWrap(True)
        info.setTextFormat(Qt.RichText)
        info.setStyleSheet(
            f"color:{TEXT}; background:{INPUT_BG}; padding:14px;"
            f"border-radius:6px; border:1px solid {BORDER}; font-size:15px;"
        )
        layout.addWidget(info)

        grp = QGroupBox("Contraseña sudo")
        g = QVBoxLayout(grp)
        self.inp = QLineEdit()
        self.inp.setEchoMode(QLineEdit.Password)
        self.inp.setPlaceholderText("Contraseña de administrador...")
        self.inp.returnPressed.connect(self._apply)
        chk = QCheckBox("Mostrar contraseña")
        chk.toggled.connect(
            lambda v: self.inp.setEchoMode(QLineEdit.Normal if v else QLineEdit.Password)
        )
        self.lbl_err = QLabel("")
        self.lbl_err.setStyleSheet(f"color:{ERROR};")
        g.addWidget(self.inp); g.addWidget(chk); g.addWidget(self.lbl_err)
        layout.addWidget(grp)

        row = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("btnSecondary")
        btn_cancel.clicked.connect(self.reject)
        self.btn_ok = QPushButton("✓  Aplicar permisos")
        self.btn_ok.clicked.connect(self._apply)
        row.addWidget(btn_cancel); row.addStretch(); row.addWidget(self.btn_ok)
        layout.addLayout(row)

    def _apply(self):
        pwd = self.inp.text()
        if not pwd:
            self.lbl_err.setText("Ingresa la contraseña.")
            return
        self.btn_ok.setEnabled(False)
        self.btn_ok.setText("Aplicando...")
        QApplication.processEvents()

        ok, msg = prepare_directory_with_sudo(self.target_dir, pwd)
        if ok:
            self.accept()
        else:
            self.lbl_err.setText(f"✗  {msg}")
            self.inp.clear(); self.inp.setFocus()
            self.btn_ok.setEnabled(True)
            self.btn_ok.setText("✓  Aplicar permisos")


# ══════════════════════════════════════════════════════════════════════════════
# Wizard de primera ejecución
# ══════════════════════════════════════════════════════════════════════════════

class SetupWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} — Configuración inicial")
        self.setMinimumWidth(560)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.result_config = {}
        self._dir_verified = False
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        title = QLabel("🐬  Bienvenido a MariaDB Backup Manager")
        title.setStyleSheet(f"font-size:18px; font-weight:bold; color:{ACCENT};")
        layout.addWidget(title)

        sub = QLabel(
            "Esta es la primera vez que ejecutas la aplicación.\n"
            "Configura los parámetros básicos para comenzar.\n"
            "Podrás cambiarlos en cualquier momento desde la pestaña Conexión."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet(f"color:{TEXT_MUTED};")
        layout.addWidget(sub)

        sep = QFrame(); sep.setObjectName("separator"); sep.setFrameShape(QFrame.HLine)
        layout.addWidget(sep)

        # ── Directorio de respaldo ──────────────────────────────────────────
        grp_dir = QGroupBox("📁  Directorio de respaldo")
        g = QVBoxLayout(grp_dir)

        hint = QLabel(
            "Elige dónde se guardarán los archivos .sql.\n"
            "Si el directorio requiere privilegios especiales, se pedirá tu\n"
            "contraseña sudo <b>una sola vez</b> para configurar los permisos."
        )
        hint.setWordWrap(True)
        hint.setTextFormat(Qt.RichText)
        hint.setStyleSheet(f"color:{TEXT_MUTED}; font-size:15px;")
        g.addWidget(hint)

        row_dir = QHBoxLayout()
        self.inp_dir = QLineEdit(os.path.expanduser("~/backups/mariadb"))
        self.inp_dir.textChanged.connect(lambda _: self._reset_dir_status())
        btn_browse = QPushButton("📂  Examinar")
        btn_browse.setObjectName("btnSecondary")
        btn_browse.clicked.connect(self._browse)
        self.btn_verify = QPushButton("✓  Verificar acceso")
        self.btn_verify.setObjectName("btnSecondary")
        self.btn_verify.clicked.connect(self._verify_dir)
        row_dir.addWidget(self.inp_dir)
        row_dir.addWidget(btn_browse)
        row_dir.addWidget(self.btn_verify)
        g.addLayout(row_dir)

        self.lbl_dir_status = QLabel(
            f'<span style="color:{TEXT_MUTED}">○  Sin verificar</span>'
        )
        g.addWidget(self.lbl_dir_status)
        layout.addWidget(grp_dir)

        # ── Conexión MariaDB ─────────────────────────────────────────────
        grp_db = QGroupBox("🔌  Conexión MariaDB")
        g2 = QVBoxLayout(grp_db)

        self.inp_host = QLineEdit("localhost")
        self.inp_port = QSpinBox()
        self.inp_port.setRange(1, 65535); self.inp_port.setValue(3306)
        self.inp_user = QLineEdit("root")
        self.inp_dbpass = QLineEdit()
        self.inp_dbpass.setEchoMode(QLineEdit.Password)
        self.inp_dbpass.setPlaceholderText("(vacío si no requiere contraseña)")

        for lbl_txt, w in [
            ("Host:", self.inp_host),
            ("Puerto:", self.inp_port),
            ("Usuario:", self.inp_user),
            ("Contraseña:", self.inp_dbpass),
        ]:
            r = QHBoxLayout()
            lbl = QLabel(lbl_txt); lbl.setFixedWidth(120)
            r.addWidget(lbl); r.addWidget(w)
            g2.addLayout(r)

        chk_show = QCheckBox("Mostrar contraseña")
        chk_show.toggled.connect(
            lambda v: self.inp_dbpass.setEchoMode(
                QLineEdit.Normal if v else QLineEdit.Password
            )
        )
        g2.addWidget(chk_show)

        row_test = QHBoxLayout()
        btn_test = QPushButton("🔍  Probar conexión")
        btn_test.setObjectName("btnSecondary")
        btn_test.clicked.connect(self._test_db)
        self.lbl_db = QLabel("")
        row_test.addWidget(btn_test); row_test.addWidget(self.lbl_db)
        row_test.addStretch()
        g2.addLayout(row_test)
        layout.addWidget(grp_db)

        # ── Botones finales ─────────────────────────────────────────────────
        sep2 = QFrame(); sep2.setObjectName("separator"); sep2.setFrameShape(QFrame.HLine)
        layout.addWidget(sep2)

        btns = QHBoxLayout()
        btn_cancel = QPushButton("Salir")
        btn_cancel.setObjectName("btnSecondary")
        btn_cancel.clicked.connect(self.reject)
        self.btn_start = QPushButton("▶  Comenzar")
        self.btn_start.clicked.connect(self._finish)
        btns.addWidget(btn_cancel); btns.addStretch(); btns.addWidget(self.btn_start)
        layout.addLayout(btns)

    def _reset_dir_status(self):
        self._dir_verified = False
        self.lbl_dir_status.setText(
            f'<span style="color:{TEXT_MUTED}">○  Sin verificar</span>'
        )

    def _browse(self):
        d = QFileDialog.getExistingDirectory(
            self, "Seleccionar directorio de respaldo", self.inp_dir.text()
        )
        if d:
            self.inp_dir.setText(d)

    def _verify_dir(self):
        path = self.inp_dir.text().strip()
        if not path:
            self.lbl_dir_status.setText(
                f'<span style="color:{ERROR}">✗  Ingresa un directorio.</span>'
            )
            return

        self.btn_verify.setEnabled(False)
        self.btn_verify.setText("Verificando...")
        QApplication.processEvents()

        if can_write_to(path):
            try:
                os.makedirs(path, exist_ok=True)
                self._dir_verified = True
                self.lbl_dir_status.setText(
                    f'<span style="color:{SUCCESS}">✓  Directorio listo. '
                    f'Tienes acceso de escritura.</span>'
                )
            except Exception as e:
                self._dir_verified = False
                self.lbl_dir_status.setText(
                    f'<span style="color:{ERROR}">✗  No se pudo crear: {e}</span>'
                )
        else:
            self.lbl_dir_status.setText(
                f'<span style="color:{WARNING}">'
                f'⚠  Sin permisos. Se pedirá contraseña sudo para configurarlo...</span>'
            )
            QApplication.processEvents()
            dlg = SudoDialog(path, self)
            if dlg.exec_() == QDialog.Accepted:
                self._dir_verified = True
                self.lbl_dir_status.setText(
                    f'<span style="color:{SUCCESS}">✓  Directorio configurado. '
                    f'No se volverá a pedir sudo para este directorio.</span>'
                )
            else:
                self._dir_verified = False
                self.lbl_dir_status.setText(
                    f'<span style="color:{TEXT_MUTED}">'
                    f'○  Cancelado. Elige un directorio dentro de tu home '
                    f'(p.ej. ~/backups/mariadb) para no necesitar sudo.</span>'
                )

        self.btn_verify.setEnabled(True)
        self.btn_verify.setText("✓  Verificar acceso")

    def _test_db(self):
        self.lbl_db.setText("Conectando...")
        QApplication.processEvents()
        ok, msg = _test_mariadb_connection({
            "host": self.inp_host.text(), "port": self.inp_port.value(),
            "user": self.inp_user.text(), "password": self.inp_dbpass.text(),
        })
        color = SUCCESS if ok else ERROR
        self.lbl_db.setText(f'<span style="color:{color}">{msg}</span>')

    def _finish(self):
        path = self.inp_dir.text().strip()
        if not path:
            QMessageBox.warning(self, "Falta directorio",
                                "Indica un directorio de respaldo.")
            return

        if not self._dir_verified:
            if can_write_to(path):
                try:
                    os.makedirs(path, exist_ok=True)
                    self._dir_verified = True
                except Exception:
                    pass

        if not self._dir_verified:
            reply = QMessageBox.question(
                self, "Directorio no verificado",
                "El directorio no fue verificado.\n"
                "¿Quieres verificar y configurar los permisos ahora?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self._verify_dir()
                if not self._dir_verified:
                    return
            else:
                QMessageBox.warning(self, "Sin permisos",
                    "No se puede escribir en ese directorio.\n"
                    "Usa un directorio dentro de tu carpeta personal o verifica los permisos.")
                return

        self.result_config = {
            "host": self.inp_host.text(),
            "port": self.inp_port.value(),
            "user": self.inp_user.text(),
            "password": self.inp_dbpass.text(),
            "backup_dir": path,
            "retention_days": 7,
            "autostart_enabled": False,
            "shutdown_enabled": False,
            "first_run_done": True,
        }
        self.accept()


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _test_mariadb_connection(config: dict):
    cmd = [
        "mysql",
        "-h", config.get("host", "localhost"),
        "-P", str(config.get("port", 3306)),
        "-u", config.get("user", "root"),
        "-e", "SELECT 1;"
    ]
    if config.get("password"):
        cmd.insert(1, f"-p{config['password']}")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        if r.returncode == 0:
            return True, "✓  Conexión exitosa."
        return False, f"✗  {r.stderr.strip()}"
    except FileNotFoundError:
        return False, "✗  mysql no encontrado. Instala mariadb-client."
    except subprocess.TimeoutExpired:
        return False, "✗  Timeout al conectar."


# ══════════════════════════════════════════════════════════════════════════════
# Workers
# ══════════════════════════════════════════════════════════════════════════════

class BackupWorker(QThread):
    log_signal      = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, config, databases, backup_dir, tag="manual"):
        super().__init__()
        self.config = config; self.databases = databases
        self.backup_dir = backup_dir; self.tag = tag

    def run(self):
        os.makedirs(self.backup_dir, exist_ok=True)

        total = len(self.databases); success = 0
        for i, db in enumerate(self.databases):
            now_str  = datetime.now().strftime("%Y-%m-%d")
            hora_str = datetime.now().strftime("%H-%M")
            filename = f"{db}_{now_str}_{self.tag}_{hora_str}.sql"
            filepath = os.path.join(self.backup_dir, filename)
            self.log_signal.emit(f"⏳ Respaldando: <b>{db}</b>...")
            cmd = [
                "mysqldump",
                "-h", self.config.get("host", "localhost"),
                "-P", str(self.config.get("port", 3306)),
                "-u", self.config.get("user", "root"),
                "--no-create-info", "--skip-triggers",
                "--complete-insert", "--skip-lock-tables",
                "--set-charset", "--default-character-set=utf8mb4",
                db,
                "-r", filepath
            ]
            if self.config.get("password"):
                cmd.insert(1, f"-p{self.config['password']}")
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if r.returncode == 0:
                    size = self._hsize(os.path.getsize(filepath))
                    self.log_signal.emit(
                        f'<span style="color:{SUCCESS}">✓ {db}</span> → {filename} ({size})'
                    )
                    success += 1
                else:
                    self.log_signal.emit(
                        f'<span style="color:{ERROR}">✗ {db}: {r.stderr.strip()}</span>'
                    )
            except subprocess.TimeoutExpired:
                self.log_signal.emit(f'<span style="color:{ERROR}">✗ {db}: Timeout</span>')
            except FileNotFoundError:
                self.log_signal.emit(
                    f'<span style="color:{ERROR}">✗ mysqldump no encontrado. '
                    f'Instala: sudo apt install mariadb-client</span>'
                )
                break
            self.progress_signal.emit(int((i + 1) / total * 100))

        self.finished_signal.emit(
            success == total,
            f"Backup completado: {success}/{total} bases exitosas."
        )

    def _hsize(self, size):
        for u in ["B","KB","MB","GB"]:
            if size < 1024: return f"{size:.1f} {u}"
            size /= 1024
        return f"{size:.1f} TB"


class ListDBWorker(QThread):
    result_signal = pyqtSignal(list)
    error_signal  = pyqtSignal(str)

    def __init__(self, config):
        super().__init__(); self.config = config

    def run(self):
        cmd = [
            "mysql",
            "-h", self.config.get("host", "localhost"),
            "-P", str(self.config.get("port", 3306)),
            "-u", self.config.get("user", "root"),
            "-N", "-e",
            "SELECT schema_name FROM information_schema.schemata "
            "WHERE schema_name NOT IN ('information_schema','performance_schema',"
            "'mysql','sys') ORDER BY schema_name;"
        ]
        if self.config.get("password"):
            cmd.insert(1, f"-p{self.config['password']}")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                self.result_signal.emit(
                    [l.strip() for l in r.stdout.splitlines() if l.strip()]
                )
            else:
                self.error_signal.emit(r.stderr.strip())
        except FileNotFoundError:
            self.error_signal.emit("mysql no encontrado. Instala mariadb-client.")
        except subprocess.TimeoutExpired:
            self.error_signal.emit("Timeout al conectar.")


# ══════════════════════════════════════════════════════════════════════════════
# Ventana principal
# ══════════════════════════════════════════════════════════════════════════════

class MainWindow(QMainWindow):
    def __init__(self, start_minimized=False):
        super().__init__()
        self._start_minimized = start_minimized
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(920, 700)
        self.config = self._load_config()
        self._init_ui()
        self._init_tray()
        self._refresh_backup_list()
        self._ensure_app_autostart()
        self._update_service_status()
        QTimer.singleShot(500, self._restore_scheduled_shutdown)

    def _load_config(self):
        defaults = {
            "host": "localhost", "port": 3306,
            "user": "root", "password": "",
            "backup_dir": os.path.expanduser("~/backups/mariadb"),
            "retention_days": 7,
            "autostart_enabled": False, "shutdown_enabled": False,
            "first_run_done": False,
            "scheduled_shutdown": None,
        }
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE) as f:
                    defaults.update(json.load(f))
            except Exception:
                pass
        return defaults

    def _save_config(self):
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=2)

    def _make_tray_icon(self):
        pix = QPixmap(64, 64)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setBrush(QColor(ACCENT))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(0, 0, 64, 64, 12, 12)
        p.setPen(QColor("white"))
        p.setFont(QFont("sans-serif", 26, QFont.Bold))
        p.drawText(pix.rect(), Qt.AlignCenter, "DB")
        p.end()
        return QIcon(pix)

    def _init_tray(self):
        self._tray = QSystemTrayIcon(self._make_tray_icon(), self)
        self._tray.setToolTip(APP_NAME)
        menu = QMenu()
        act_show = QAction("Mostrar", self)
        act_show.triggered.connect(self._tray_show)
        act_quit = QAction("Salir", self)
        act_quit.triggered.connect(self._tray_quit)
        menu.addAction(act_show)
        menu.addSeparator()
        menu.addAction(act_quit)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self._tray_show()

    def _tray_show(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _tray_quit(self):
        self._tray.hide()
        QApplication.quit()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self._tray.showMessage(APP_NAME, "La app sigue ejecutándose en segundo plano.",
                               QSystemTrayIcon.Information, 2000)

    def _cleanup_old_backups(self):
        bd = self.config["backup_dir"]
        days = self.config.get("retention_days", 7)
        if not os.path.exists(bd):
            return
        cutoff = datetime.now() - timedelta(days=days)
        removed = 0
        for f in Path(bd).glob("*.sql"):
            if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                f.unlink()
                removed += 1
        if removed:
            self._log(
                f'<span style="color:{TEXT_MUTED}">🗑 Limpieza: {removed} backup(s) '
                f'mayores a {days} días eliminados.</span>'
            )

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        lay = QVBoxLayout(central)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        # Header
        hdr = QHBoxLayout()
        t = QLabel("🐬  MariaDB Backup Manager")
        t.setObjectName("labelTitle")
        self.lbl_status = QLabel("Listo")
        self.lbl_status.setObjectName("labelStatus")
        hdr.addWidget(t); hdr.addStretch(); hdr.addWidget(self.lbl_status)
        lay.addLayout(hdr)

        sep = QFrame(); sep.setObjectName("separator"); sep.setFrameShape(QFrame.HLine)
        lay.addWidget(sep)

        tabs = QTabWidget()
        tabs.addTab(self._tab_conexion(),  "🔌  Conexión")
        tabs.addTab(self._tab_backup(),    "🗄  Backup")
        tabs.addTab(self._tab_apagado(),   "⏱  Apagado")
        tabs.addTab(self._tab_historial(), "📂  Historial")
        lay.addWidget(tabs)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        lay.addWidget(self.progress)

        # Footer
        lbl_footer = QLabel("v1.0.0 r3 — Creado por: tuxor.max@gmail.com")
        lbl_footer.setAlignment(Qt.AlignCenter)
        lbl_footer.setStyleSheet(f"color:{TEXT_MUTED}; font-size:12px; padding:4px;")
        lay.addWidget(lbl_footer)

    # ── Tab Backup ───────────────────────────────────────────────────────────
    def _tab_backup(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setSpacing(12)

        grp_db = QGroupBox("Bases de datos")
        gd = QVBoxLayout(grp_db)
        ctrl = QHBoxLayout()
        self.btn_listar = QPushButton("🔄  Cargar bases de datos")
        self.btn_listar.setObjectName("btnSecondary")
        self.btn_listar.clicked.connect(self._listar_dbs)
        btn_all  = QPushButton("☑  Todas");  btn_all.setObjectName("btnSecondary")
        btn_none = QPushButton("☐  Ninguna"); btn_none.setObjectName("btnSecondary")
        btn_all.clicked.connect(lambda: self._set_all_checks(True))
        btn_none.clicked.connect(lambda: self._set_all_checks(False))
        ctrl.addWidget(self.btn_listar); ctrl.addWidget(btn_all)
        ctrl.addWidget(btn_none); ctrl.addStretch()
        gd.addLayout(ctrl)
        self.db_checks_widget = QWidget()
        self.db_checks_layout = QVBoxLayout(self.db_checks_widget)
        self.db_checks_layout.setContentsMargins(0, 4, 0, 0)
        hint = QLabel("Haz clic en 'Cargar bases de datos' para comenzar.")
        hint.setStyleSheet(f"color:{TEXT_MUTED};")
        self.db_checks_layout.addWidget(hint)
        gd.addWidget(self.db_checks_widget)
        lay.addWidget(grp_db)

        # Directorio
        grp_dir = QGroupBox("Directorio de respaldo")
        gdir = QHBoxLayout(grp_dir)
        self.inp_backup_dir = QLineEdit(self.config["backup_dir"])
        self.inp_backup_dir.textChanged.connect(
            lambda t: self.config.update({"backup_dir": t})
        )
        btn_browse = QPushButton("📁  Examinar"); btn_browse.setObjectName("btnSecondary")
        btn_browse.clicked.connect(self._browse_dir)
        self.btn_vdir = QPushButton("✓  Verificar")
        self.btn_vdir.setObjectName("btnSecondary")
        self.btn_vdir.clicked.connect(self._verify_backup_dir)
        self.lbl_dir_status = QLabel("")
        gdir.addWidget(self.inp_backup_dir); gdir.addWidget(btn_browse)
        gdir.addWidget(self.btn_vdir); gdir.addWidget(self.lbl_dir_status)
        lay.addWidget(grp_dir)

        self.btn_backup = QPushButton("▶  Iniciar Backup Manual")
        self.btn_backup.setObjectName("btnSuccess")
        self.btn_backup.setMinimumHeight(42)
        self.btn_backup.clicked.connect(self._run_backup_manual)
        lay.addWidget(self.btn_backup)

        grp_log = QGroupBox("Log")
        gl = QVBoxLayout(grp_log)
        self.log_output = QTextEdit(); self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(130)
        btn_clr = QPushButton("Limpiar"); btn_clr.setObjectName("btnSecondary")
        btn_clr.clicked.connect(self.log_output.clear)
        gl.addWidget(self.log_output); gl.addWidget(btn_clr)
        lay.addWidget(grp_log)
        return w

    # ── Tab Conexión ─────────────────────────────────────────────────────────
    def _tab_conexion(self):
        w = QWidget(); lay = QVBoxLayout(w)
        lay.setAlignment(Qt.AlignTop); lay.setSpacing(12)

        grp = QGroupBox("Credenciales de conexión")
        gf = QVBoxLayout(grp)

        def row(lbl_txt, widget):
            r = QHBoxLayout()
            lbl = QLabel(lbl_txt); lbl.setFixedWidth(130)
            r.addWidget(lbl); r.addWidget(widget); gf.addLayout(r)

        self.inp_host   = QLineEdit(self.config["host"])
        self.inp_port   = QSpinBox()
        self.inp_port.setRange(1, 65535); self.inp_port.setValue(self.config["port"])
        self.inp_user   = QLineEdit(self.config["user"])
        self.inp_dbpass = QLineEdit(self.config["password"])
        self.inp_dbpass.setEchoMode(QLineEdit.Password)
        chk = QCheckBox("Mostrar contraseña")
        chk.toggled.connect(
            lambda v: self.inp_dbpass.setEchoMode(
                QLineEdit.Normal if v else QLineEdit.Password
            )
        )
        row("Host:", self.inp_host); row("Puerto:", self.inp_port)
        row("Usuario:", self.inp_user); row("Contraseña:", self.inp_dbpass)
        gf.addWidget(chk)
        lay.addWidget(grp)

        grp2 = QGroupBox("Retención de backups")
        gr = QHBoxLayout(grp2)
        self.inp_retention = QSpinBox()
        self.inp_retention.setRange(1, 365)
        self.inp_retention.setValue(self.config["retention_days"])
        self.inp_retention.setSuffix(" días")
        gr.addWidget(QLabel("Eliminar backups mayores a:"))
        gr.addWidget(self.inp_retention); gr.addStretch()
        lay.addWidget(grp2)

        btns = QHBoxLayout()
        btn_test = QPushButton("🔍  Probar conexión")
        btn_test.setObjectName("btnSecondary")
        btn_test.clicked.connect(self._test_connection)
        btn_save = QPushButton("💾  Guardar configuración")
        btn_save.clicked.connect(self._save_connection)
        btns.addWidget(btn_test); btns.addWidget(btn_save)
        lay.addLayout(btns)
        self.lbl_conn_status = QLabel("")
        lay.addWidget(self.lbl_conn_status)
        return w

    # ── Tab Apagado ──────────────────────────────────────────────────────────
    def _tab_apagado(self):
        w = QWidget(); lay = QVBoxLayout(w)
        lay.setAlignment(Qt.AlignTop); lay.setSpacing(12)

        # ── Modo de apagado ─────────────────────────────────────────────────
        grp_modo = QGroupBox("Modo de apagado")
        gm = QVBoxLayout(grp_modo); gm.setSpacing(12)

        row_mode = QHBoxLayout()
        row_mode.addWidget(QLabel("Modo:"))
        self.cmb_shutdown_mode = QComboBox()
        self.cmb_shutdown_mode.addItem("A una hora específica", "hora")
        self.cmb_shutdown_mode.addItem("En X minutos", "mins")
        self.cmb_shutdown_mode.setFixedWidth(220)
        self.cmb_shutdown_mode.currentIndexChanged.connect(self._on_shutdown_mode_changed)
        row_mode.addWidget(self.cmb_shutdown_mode); row_mode.addStretch()
        gm.addLayout(row_mode)

        # Hora específica por día de la semana
        self.row_hora = QWidget()
        rh = QVBoxLayout(self.row_hora); rh.setContentsMargins(0, 0, 0, 0); rh.setSpacing(6)
        dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        self.inp_horas_dia = {}
        for dia in dias:
            fila = QHBoxLayout()
            lbl = QLabel(f"{dia}:")
            lbl.setFixedWidth(100)
            te = QTimeEdit()
            te.setDisplayFormat("HH:mm")
            te.setTime(QTime(18, 0))
            te.setFixedWidth(100)
            self.inp_horas_dia[dia] = te
            fila.addWidget(lbl); fila.addWidget(te); fila.addStretch()
            rh.addLayout(fila)

        # En X minutos
        self.row_mins = QWidget()
        rm = QHBoxLayout(self.row_mins); rm.setContentsMargins(0, 0, 0, 0)
        rm.addWidget(QLabel("Apagar en:"))
        self.inp_mins = QSpinBox()
        self.inp_mins.setRange(1, 480); self.inp_mins.setValue(30)
        self.inp_mins.setSuffix(" minutos")
        self.inp_mins.setFixedWidth(140)
        rm.addWidget(self.inp_mins); rm.addStretch()
        self.row_mins.setVisible(False)

        gm.addWidget(self.row_hora)
        gm.addWidget(self.row_mins)
        lay.addWidget(grp_modo)

        # ── Botones ─────────────────────────────────────────────────────────
        row_btns = QHBoxLayout()
        self.btn_schedule  = QPushButton("⏱  Programar apagado")
        self.btn_schedule.setMinimumHeight(42)
        self.btn_schedule.clicked.connect(self._schedule_shutdown)

        self.btn_cancel_sd = QPushButton("✕  Cancelar apagado")
        self.btn_cancel_sd.setObjectName("btnDanger")
        self.btn_cancel_sd.setMinimumHeight(42)
        self.btn_cancel_sd.setEnabled(False)
        self.btn_cancel_sd.clicked.connect(self._cancel_shutdown)

        row_btns.addWidget(self.btn_schedule)
        row_btns.addWidget(self.btn_cancel_sd)
        lay.addLayout(row_btns)

        # ── Panel de estado (cuenta regresiva) ──────────────────────────────
        self.grp_countdown = QGroupBox("Estado")
        gc = QVBoxLayout(self.grp_countdown)

        self.lbl_countdown_title = QLabel("Sin apagado programado")
        self.lbl_countdown_title.setStyleSheet(
            f"font-size:14px; font-weight:bold; color:{TEXT_MUTED};"
        )
        self.lbl_countdown_title.setAlignment(Qt.AlignCenter)

        self.lbl_countdown = QLabel("")
        self.lbl_countdown.setAlignment(Qt.AlignCenter)
        self.lbl_countdown.setStyleSheet(
            f"font-size:36px; font-weight:bold; color:{ACCENT}; letter-spacing:2px;"
        )

        self.lbl_shutdown_detail = QLabel("")
        self.lbl_shutdown_detail.setAlignment(Qt.AlignCenter)
        self.lbl_shutdown_detail.setStyleSheet(f"color:{TEXT_MUTED}; font-size:15px;")

        self.prog_countdown = QProgressBar()
        self.prog_countdown.setRange(0, 100)
        self.prog_countdown.setValue(0)
        self.prog_countdown.setVisible(False)

        gc.addWidget(self.lbl_countdown_title)
        gc.addWidget(self.lbl_countdown)
        gc.addWidget(self.lbl_shutdown_detail)
        gc.addSpacing(4)
        gc.addWidget(self.prog_countdown)

        self.lbl_svc = QLabel("")
        self.lbl_svc.setAlignment(Qt.AlignCenter)
        gc.addWidget(self.lbl_svc)

        lay.addWidget(self.grp_countdown)

        # Timer interno de cuenta regresiva
        self._shutdown_timer  = QTimer(self)
        self._shutdown_target = None
        self._shutdown_total  = 0
        self._shutdown_timer.timeout.connect(self._tick_countdown)

        return w

    def _on_shutdown_mode_changed(self):
        hora_mode = self.cmb_shutdown_mode.currentData() == "hora"
        self.row_hora.setVisible(hora_mode)
        self.row_mins.setVisible(not hora_mode)

    def _restore_scheduled_shutdown(self):
        sched = self.config.get("scheduled_shutdown")
        if not sched:
            return
        try:
            mins = sched.get("mins", 30)
            mode = sched.get("mode", "hora")

            if mode == "hora":
                self.cmb_shutdown_mode.setCurrentIndex(0)
                horas_dia = sched.get("horas_dia", {})
                for dia, hora_str in horas_dia.items():
                    if dia in self.inp_horas_dia:
                        h, m = map(int, hora_str.split(":"))
                        self.inp_horas_dia[dia].setTime(QTime(h, m))
            else:
                self.cmb_shutdown_mode.setCurrentIndex(1)
                self.inp_mins.setValue(mins)

            self._schedule_shutdown(auto=True)
        except Exception:
            pass

    def _services_installed(self):
        a = Path("/etc/systemd/system/mariadb-backup-inicio.service").exists()
        b = Path("/etc/systemd/system/mariadb-backup-apagado.service").exists()
        return a and b

    def _schedule_shutdown(self, auto=False):
        backup_first = True

        if not self._services_installed():
            if not auto:
                reply = QMessageBox.question(
                    self, "Servicios no instalados",
                    "Los servicios de backup automático no están instalados.\n"
                    "Se necesitan para hacer backup al encender/apagar el equipo.\n\n"
                    "¿Instalar ahora?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return
            if not self._install_services():
                return

        now = datetime.now()
        if self.cmb_shutdown_mode.currentData() == "hora":
            dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
            dia_hoy = dias[now.weekday()]
            t = self.inp_horas_dia[dia_hoy].time()
            target = now.replace(
                hour=t.hour(), minute=t.minute(), second=0, microsecond=0
            )
            if target <= now:
                target += timedelta(days=1)
            delta_mins = max(1, int((target - now).total_seconds() / 60))
            hora_str   = target.strftime("%H:%M")
            mode = "hora"
        else:
            delta_mins = self.inp_mins.value()
            target     = now + timedelta(minutes=delta_mins)
            hora_str   = target.strftime("%H:%M")
            mode = "mins"

        if not auto:
            reply = QMessageBox.question(
                self, "Confirmar apagado programado",
                f"El equipo se apagará a las <b>{hora_str}</b> "
                f"(en {delta_mins} min).\n"
                f"⚠  Se hará backup de MariaDB antes de apagar.\n\n¿Continuar?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        shutdown_mins = delta_mins

        r = subprocess.run(
            ["sudo", "-n", "shutdown", "-h", f"+{shutdown_mins}"],
            capture_output=True, text=True
        )
        if r.returncode != 0:
            tmp = "/tmp/_mdb_shutdown.sh"
            with open(tmp, "w") as f:
                f.write(f"#!/bin/bash\nshutdown -h +{shutdown_mins}\necho DONE\n")
            os.chmod(tmp, 0o755)
            r2 = subprocess.run(["pkexec", "bash", tmp],
                                capture_output=True, text=True)
            if "DONE" not in r2.stdout and r2.returncode != 0:
                if not auto:
                    QMessageBox.critical(
                        self, "Error",
                        "No se pudo programar el apagado.\n"
                        "Ejecuta manualmente:\n\n"
                        f"  sudo shutdown -h +{shutdown_mins}"
                    )
                return

        if not auto:
            horas_dia = {dia: te.time().toString("HH:mm")
                         for dia, te in self.inp_horas_dia.items()}
            self.config["scheduled_shutdown"] = {
                "mode": mode,
                "horas_dia": horas_dia if mode == "hora" else {},
                "mins": delta_mins if mode == "mins" else 0,
            }
            self._save_config()

        self._shutdown_target = target
        self._shutdown_total  = delta_mins * 60
        self._backup_before   = backup_first
        self._backup_triggered = False

        self.btn_schedule.setEnabled(False)
        self.btn_cancel_sd.setEnabled(True)
        self.prog_countdown.setVisible(True)

        self.lbl_countdown_title.setText("⏻  Apagado programado para las")
        self.lbl_countdown_title.setStyleSheet(
            f"font-size:14px; font-weight:bold; color:{WARNING};"
        )
        self.lbl_shutdown_detail.setText(
            f"Hora objetivo: {hora_str}  |  Backup automático activado"
        )

        self._shutdown_timer.start(1000)
        self._tick_countdown()

    def _tick_countdown(self):
        if self._shutdown_target is None:
            return

        now       = datetime.now()
        remaining = (self._shutdown_target - now).total_seconds()

        if remaining <= 0:
            self._shutdown_timer.stop()
            self.lbl_countdown.setText("00:00:00")
            self.lbl_countdown_title.setText("Apagando...")
            return

        if self._backup_before and not self._backup_triggered and remaining <= 120:
            self._backup_triggered = True
            dbs = self._get_selected_dbs()
            if dbs:
                self._run_backup(dbs, "apagado")
            else:
                self._log(
                    f'<span style="color:{WARNING}">⚠ Backup pre-apagado: '
                    f'carga las bases primero en la pestaña Backup.</span>'
                )

        h = int(remaining // 3600)
        m = int((remaining % 3600) // 60)
        s = int(remaining % 60)
        self.lbl_countdown.setText(f"{h:02d}:{m:02d}:{s:02d}")

        elapsed = self._shutdown_total - remaining
        pct     = int(elapsed / self._shutdown_total * 100) if self._shutdown_total else 0
        self.prog_countdown.setValue(pct)

        if remaining < 60:
            self.lbl_countdown.setStyleSheet(
                f"font-size:36px; font-weight:bold; color:{ERROR}; letter-spacing:2px;"
            )
        elif remaining < 300:
            self.lbl_countdown.setStyleSheet(
                f"font-size:36px; font-weight:bold; color:{WARNING}; letter-spacing:2px;"
            )

    def _cancel_shutdown(self):
        reply = QMessageBox.question(
            self, "Cancelar apagado",
            "¿Cancelar el apagado programado?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        r = subprocess.run(
            ["sudo", "-n", "shutdown", "-c"],
            capture_output=True, text=True
        )
        if r.returncode != 0:
            tmp = "/tmp/_mdb_cancel_sd.sh"
            with open(tmp, "w") as f:
                f.write("#!/bin/bash\nshutdown -c\necho DONE\n")
            os.chmod(tmp, 0o755)
            subprocess.run(["pkexec", "bash", tmp], capture_output=True, text=True)

        self._shutdown_timer.stop()
        self._shutdown_target  = None
        self._backup_triggered = False

        self.config["scheduled_shutdown"] = None
        self._save_config()

        self.btn_schedule.setEnabled(True)
        self.btn_cancel_sd.setEnabled(False)
        self.prog_countdown.setVisible(False)
        self.prog_countdown.setValue(0)

        self.lbl_countdown_title.setText("Apagado cancelado ✓")
        self.lbl_countdown_title.setStyleSheet(
            f"font-size:14px; font-weight:bold; color:{SUCCESS};"
        )
        self.lbl_countdown.setText("")
        self.lbl_shutdown_detail.setText("")

    # ── Tab Historial ────────────────────────────────────────────────────────
    def _tab_historial(self):
        w = QWidget(); lay = QVBoxLayout(w)
        ctrl = QHBoxLayout()
        btn_r = QPushButton("🔄  Actualizar"); btn_r.setObjectName("btnSecondary")
        btn_r.clicked.connect(self._refresh_backup_list)
        btn_o = QPushButton("📁  Abrir carpeta"); btn_o.setObjectName("btnSecondary")
        btn_o.clicked.connect(self._open_backup_dir)
        btn_d = QPushButton("🗑  Eliminar seleccionado"); btn_d.setObjectName("btnDanger")
        btn_d.clicked.connect(self._delete_selected_backup)
        self.lbl_total = QLabel("")
        self.lbl_total.setStyleSheet(f"color:{TEXT_MUTED};")
        ctrl.addWidget(btn_r); ctrl.addWidget(btn_o); ctrl.addWidget(btn_d)
        ctrl.addStretch(); ctrl.addWidget(self.lbl_total)
        lay.addLayout(ctrl)

        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(
            ["Base de datos", "Fecha / Hora", "Tipo", "Tamaño"]
        )
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for c in (1, 2, 3):
            self.tbl.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self.tbl.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        lay.addWidget(self.tbl)
        return w

    # ── Directorio ───────────────────────────────────────────────────────────
    def _browse_dir(self):
        d = QFileDialog.getExistingDirectory(
            self, "Directorio de respaldo", self.config["backup_dir"]
        )
        if d:
            self.inp_backup_dir.setText(d)
            self.config["backup_dir"] = d
            self.lbl_dir_status.setText("")

    def _verify_backup_dir(self):
        path = self.inp_backup_dir.text().strip()
        if not path:
            return
        self.btn_vdir.setEnabled(False)
        QApplication.processEvents()

        if can_write_to(path):
            os.makedirs(path, exist_ok=True)
            self.lbl_dir_status.setText(f'<span style="color:{SUCCESS}">✓  Accesible</span>')
        else:
            self.lbl_dir_status.setText(
                f'<span style="color:{WARNING}">⚠  Requiere sudo</span>'
            )
            dlg = SudoDialog(path, self)
            if dlg.exec_() == QDialog.Accepted:
                self.lbl_dir_status.setText(
                    f'<span style="color:{SUCCESS}">✓  Configurado</span>'
                )
            else:
                self.lbl_dir_status.setText(
                    f'<span style="color:{ERROR}">✗  Sin permisos</span>'
                )
        self.btn_vdir.setEnabled(True)

    # ── Bases de datos ───────────────────────────────────────────────────────
    def _listar_dbs(self):
        self.btn_listar.setEnabled(False)
        self.btn_listar.setText("Conectando...")
        self._log("Conectando al servidor MariaDB...")
        w = ListDBWorker(self.config)
        w.result_signal.connect(self._on_dbs_listed)
        w.error_signal.connect(self._on_dbs_error)
        w.finished.connect(lambda: (
            self.btn_listar.__setattr__('enabled', True) or
            self.btn_listar.setEnabled(True) or
            self.btn_listar.setText("🔄  Cargar bases de datos")
        ))
        self._wl = w; w.start()

    def _on_dbs_listed(self, dbs):
        for i in reversed(range(self.db_checks_layout.count())):
            wi = self.db_checks_layout.itemAt(i).widget()
            if wi: wi.deleteLater()
        if not dbs:
            lbl = QLabel("No se encontraron bases de datos.")
            lbl.setStyleSheet(f"color:{WARNING};")
            self.db_checks_layout.addWidget(lbl)
            return
        self._log(f'<span style="color:{SUCCESS}">✓ {len(dbs)} bases encontradas.</span>')
        for db in dbs:
            chk = QCheckBox(db); chk.setChecked(True)
            self.db_checks_layout.addWidget(chk)

    def _on_dbs_error(self, error):
        self._log(f'<span style="color:{ERROR}">✗ {error}</span>')
        QMessageBox.critical(self, "Error de conexión", error)

    def _set_all_checks(self, val):
        for i in range(self.db_checks_layout.count()):
            wi = self.db_checks_layout.itemAt(i).widget()
            if isinstance(wi, QCheckBox): wi.setChecked(val)

    def _get_selected_dbs(self):
        return [
            self.db_checks_layout.itemAt(i).widget().text()
            for i in range(self.db_checks_layout.count())
            if isinstance(self.db_checks_layout.itemAt(i).widget(), QCheckBox)
            and self.db_checks_layout.itemAt(i).widget().isChecked()
        ]

    # ── Backup ───────────────────────────────────────────────────────────────
    def _run_backup_manual(self):
        dbs = self._get_selected_dbs()
        if not dbs:
            QMessageBox.warning(self, "Sin selección",
                "Carga y selecciona al menos una base de datos.")
            return
        path = self.config["backup_dir"]
        if not can_write_to(path):
            self._log(f'<span style="color:{WARNING}">⚠ El directorio requiere permisos sudo...</span>')
            dlg = SudoDialog(path, self)
            if dlg.exec_() != QDialog.Accepted:
                self._log(f'<span style="color:{ERROR}">✗ Backup cancelado: sin permisos.</span>')
                return
        self._run_backup(dbs, "manual")

    def _run_backup(self, dbs, tag="manual"):
        self.btn_backup.setEnabled(False)
        self.progress.setVisible(True); self.progress.setValue(0)
        self._log(
            f"<b>══ Inicio de backup [{tag}] "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ══</b>"
        )
        worker = BackupWorker(self.config, dbs, self.config["backup_dir"], tag)
        worker.log_signal.connect(self._log)
        worker.progress_signal.connect(self.progress.setValue)
        worker.finished_signal.connect(self._on_backup_finished)
        self._wb = worker; worker.start()

    def _on_backup_finished(self, ok, msg):
        self.btn_backup.setEnabled(True)
        self.progress.setVisible(False)
        self._log(f'<span style="color:{SUCCESS if ok else WARNING}"><b>{msg}</b></span>')
        self.lbl_status.setText(f"Último backup: {datetime.now().strftime('%H:%M:%S')}")
        self._cleanup_old_backups()
        self._refresh_backup_list()

    def _log(self, html):
        self.log_output.append(html)
        self.log_output.moveCursor(QTextCursor.End)

    # ── Conexión ─────────────────────────────────────────────────────────────
    def _save_connection(self):
        self.config.update({
            "host": self.inp_host.text(), "port": self.inp_port.value(),
            "user": self.inp_user.text(), "password": self.inp_dbpass.text(),
            "retention_days": self.inp_retention.value(),
        })
        self._save_config()
        QMessageBox.information(self, "Guardado", "Configuración guardada.")

    def _test_connection(self):
        self.lbl_conn_status.setText("Probando conexión...")
        QApplication.processEvents()
        ok, msg = _test_mariadb_connection({
            "host": self.inp_host.text(), "port": self.inp_port.value(),
            "user": self.inp_user.text(), "password": self.inp_dbpass.text(),
        })
        self.lbl_conn_status.setText(
            f'<span style="color:{SUCCESS if ok else ERROR}">{msg}</span>'
        )

    # ── Servicios systemd ────────────────────────────────────────────────────
    def _mk_backup_sh(self):
        pwd_arg = ""
        if self.config.get("password"):
            pwd_arg = f"-p\"{self.config['password']}\""
        return (
            f"#!/bin/bash\n"
            f"BACKUP_DIR=\"{self.config['backup_dir']}\"\n"
            f"FECHA=$(date +%Y-%m-%d)\n"
            f"HORA=$(date +%H-%M)\n"
            f"DBHOST=\"{self.config.get('host','localhost')}\"\n"
            f"DBPORT=\"{self.config.get('port',3306)}\"\n"
            f"DBUSER=\"{self.config.get('user','root')}\"\n"
            f"DBPASS=\"{pwd_arg}\"\n"
            f"LOG=\"/var/log/mariadb_backup.log\"\n"
            f"RETENTION={self.config.get('retention_days',7)}\n"
            f"TAG=\"${{1:-manual}}\"\n\n"
            f"mkdir -p \"$BACKUP_DIR\"\n"
            f"echo \"[$(date)] Iniciando ($TAG)...\" >> \"$LOG\"\n"
            f"DBS=$(mysql -h \"$DBHOST\" -P \"$DBPORT\" -u \"$DBUSER\" $DBPASS -N -e \\\n"
            f"  \"SELECT schema_name FROM information_schema.schemata "
            f"WHERE schema_name NOT IN ('information_schema','performance_schema','mysql','sys');\")\n"
            f"for DB in $DBS; do\n"
            f"  DB=$(echo $DB | xargs); [ -z \"$DB\" ] && continue\n"
            f"  FILE=\"$BACKUP_DIR/${{DB}}_${{FECHA}}_${{TAG}}_${{HORA}}.sql\"\n"
            f"  mysqldump -h \"$DBHOST\" -P \"$DBPORT\" -u \"$DBUSER\" $DBPASS "
            f"--no-create-info --skip-triggers --complete-insert --skip-lock-tables "
            f"--set-charset --default-character-set=utf8mb4 \"$DB\" -r \"$FILE\"\n"
            f"  [ $? -eq 0 ] && echo \"  ✓ $DB\" >> \"$LOG\" "
            f"|| echo \"  ✗ $DB\" >> \"$LOG\"\n"
            f"done\n"
            f"find \"$BACKUP_DIR\" -name \"*.sql\" -mtime +$RETENTION -delete\n"
            f"echo \"[$(date)] Backup $TAG listo.\" >> \"$LOG\"\n"
        )

    def _install_services(self):
        t = 10
        sh = self._mk_backup_sh()
        svc_s = ("[Unit]\nDescription=Backup MariaDB al iniciar\n"
                 "After=mariadb.service mysql.service network.target\n"
                 "Wants=mariadb.service\n\n"
                 "[Service]\nType=oneshot\n"
                 "ExecStart=/usr/local/bin/mariadb_backup.sh arranque\nRemainAfterExit=yes\n\n"
                 "[Install]\nWantedBy=multi-user.target\n")
        svc_st = ("[Unit]\nDescription=Backup MariaDB antes de apagar\n"
                  "Before=shutdown.target reboot.target halt.target\n"
                  "DefaultDependencies=no\n\n"
                  "[Service]\nType=oneshot\n"
                  f"ExecStart=/usr/local/bin/mariadb_backup.sh apagado\nTimeoutStartSec={t}min\n\n"
                  "[Install]\nWantedBy=shutdown.target reboot.target halt.target\n")

        inst = f"cat > /usr/local/bin/mariadb_backup.sh << 'EOSH'\n{sh}\nEOSH\n"
        inst += "chmod +x /usr/local/bin/mariadb_backup.sh\n"
        inst += (f"cat > /etc/sudoers.d/mariadb-backup-manager << 'EOSUDO'\n"
                 f"{CURRENT_USER} ALL=(ALL) NOPASSWD: /sbin/shutdown\n"
                 f"EOSUDO\n"
                 f"chmod 440 /etc/sudoers.d/mariadb-backup-manager\n")
        inst += (f"cat > /etc/systemd/system/mariadb-backup-inicio.service << 'EOSVC'\n"
                 f"{svc_s}\nEOSVC\nsystemctl enable mariadb-backup-inicio.service\n")
        inst += (f"cat > /etc/systemd/system/mariadb-backup-apagado.service << 'EOSVC'\n"
                 f"{svc_st}\nEOSVC\nsystemctl enable mariadb-backup-apagado.service\n")
        inst += "systemctl daemon-reload\necho DONE\n"

        tmp = "/tmp/_mdb_inst.sh"
        with open(tmp, "w") as f:
            f.write(inst)
        os.chmod(tmp, 0o755)
        r = subprocess.run(["pkexec", "bash", tmp], capture_output=True, text=True)

        if "DONE" in r.stdout or r.returncode == 0:
            self.config["autostart_enabled"] = True
            self.config["shutdown_enabled"]  = True
            self._save_config(); self._update_service_status()
            QMessageBox.information(self, "✓ Instalado",
                "Servicios systemd instalados y habilitados.")
            return True
        else:
            mb = QMessageBox(self)
            mb.setWindowTitle("Instalar manualmente")
            mb.setText("No se obtuvieron permisos automáticos.\n"
                       "Ejecuta el script manualmente en terminal:")
            mb.setDetailedText(f"sudo bash << 'EOF'\n{inst}\nEOF")
            mb.exec_()
            return False

    def _uninstall_services(self):
        if QMessageBox.question(
            self, "Confirmar", "¿Desinstalar los servicios automáticos?",
            QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return
        script = ("systemctl disable mariadb-backup-inicio.service 2>/dev/null\n"
                  "systemctl disable mariadb-backup-apagado.service 2>/dev/null\n"
                  "rm -f /etc/systemd/system/mariadb-backup-inicio.service\n"
                  "rm -f /etc/systemd/system/mariadb-backup-apagado.service\n"
                  "rm -f /usr/local/bin/mariadb_backup.sh\n"
                  "rm -f /etc/sudoers.d/mariadb-backup-manager\n"
                  "systemctl daemon-reload\necho DONE\n")
        tmp = "/tmp/_mdb_uninst.sh"
        with open(tmp, "w") as f:
            f.write(script)
        os.chmod(tmp, 0o755)
        r = subprocess.run(["pkexec", "bash", tmp], capture_output=True, text=True)
        if "DONE" in r.stdout or r.returncode == 0:
            self.config["autostart_enabled"] = False
            self.config["shutdown_enabled"]  = False
            self._save_config(); self._update_service_status()
            QMessageBox.information(self, "Desinstalado", "Servicios eliminados.")

    def _autostart_path(self):
        return os.path.expanduser(
            "~/.config/autostart/mariadb_backup_manager.desktop"
        )

    def _ensure_app_autostart(self):
        path   = self._autostart_path()
        script = os.path.abspath(__file__)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        desktop = (
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=MariaDB Backup Manager\n"
            "Comment=MariaDB Backup Manager\n"
            f"Exec=python3 {script} --minimized\n"
            "Terminal=false\n"
            "Categories=Utility;Database;\n"
            "X-GNOME-Autostart-enabled=true\n"
        )
        with open(path, "w") as f:
            f.write(desktop)
        os.chmod(path, 0o644)

    def _update_service_status(self):
        a = Path("/etc/systemd/system/mariadb-backup-inicio.service").exists()
        b = Path("/etc/systemd/system/mariadb-backup-apagado.service").exists()
        parts = []
        for label, active in [("Inicio", a), ("Apagado", b)]:
            c = SUCCESS if active else TEXT_MUTED
            s = "✓" if active else "○"
            parts.append(f'<span style="color:{c}">{s} Servicio {label}</span>')
        self.lbl_svc.setText("  |  ".join(parts))

    # ── Historial ────────────────────────────────────────────────────────────
    def _refresh_backup_list(self):
        self.tbl.setRowCount(0)
        bd = self.config["backup_dir"]
        if not os.path.exists(bd):
            self.lbl_total.setText("Directorio no existe aún.")
            return
        files = sorted(
            list(Path(bd).glob("*.sql")),
            key=lambda f: f.stat().st_mtime, reverse=True
        )
        total = 0
        for f in files:
            row = self.tbl.rowCount(); self.tbl.insertRow(row)
            parts = f.stem.split("_")
            db    = parts[0] if parts else f.stem
            fecha = parts[1] if len(parts) >= 2 else "—"
            tipo  = parts[2] if len(parts) >= 3 else "—"
            hora  = parts[3] if len(parts) >= 4 else ""
            if hora:
                fecha = f"{fecha} {hora.replace('-', ':')}"
            size  = f.stat().st_size; total += size
            self.tbl.setItem(row, 0, QTableWidgetItem(db))
            self.tbl.setItem(row, 1, QTableWidgetItem(fecha))
            ti = QTableWidgetItem(tipo)
            ti.setForeground(QColor(
                {"apagado": WARNING, "arranque": SUCCESS, "inicio": SUCCESS}.get(tipo, TEXT_MUTED)
            ))
            self.tbl.setItem(row, 2, ti)
            self.tbl.setItem(row, 3, QTableWidgetItem(self._hsize(size)))
            self.tbl.item(row, 0).setData(Qt.UserRole, str(f))
        self.lbl_total.setText(
            f"{len(files)} archivos  |  Total: {self._hsize(total)}"
        )

    def _open_backup_dir(self):
        d = self.config["backup_dir"]
        os.makedirs(d, exist_ok=True)
        subprocess.Popen(["xdg-open", d])

    def _delete_selected_backup(self):
        rows = sorted(set(idx.row() for idx in self.tbl.selectedIndexes()), reverse=True)
        if not rows:
            QMessageBox.information(self, "Sin selección", "Selecciona al menos un backup.")
            return
        nombres = []
        rutas = []
        for r in rows:
            fp = self.tbl.item(r, 0).data(Qt.UserRole)
            if fp:
                rutas.append(fp)
                nombres.append(os.path.basename(fp))
        if not rutas:
            return
        msg = f"¿Eliminar {len(rutas)} archivo(s)?\n\n" + "\n".join(nombres[:10])
        if len(nombres) > 10:
            msg += f"\n... y {len(nombres) - 10} más"
        if QMessageBox.question(
            self, "Eliminar", msg, QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return
        errores = 0
        for fp in rutas:
            try:
                os.remove(fp)
            except PermissionError:
                subprocess.run(["sudo", "-n", "rm", "-f", fp],
                               capture_output=True, text=True)
                if os.path.exists(fp):
                    errores += 1
            except Exception:
                errores += 1
        if errores:
            QMessageBox.warning(self, "Advertencia",
                f"{errores} archivo(s) no se pudieron eliminar (permisos).")
        self._refresh_backup_list()

    def _hsize(self, size):
        for u in ["B", "KB", "MB", "GB"]:
            if size < 1024: return f"{size:.1f} {u}"
            size /= 1024
        return f"{size:.1f} TB"


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--minimized", action="store_true",
                        help="Iniciar minimizado (para autostart)")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyleSheet(STYLESHEET)

    if not os.path.exists(CONFIG_FILE):
        wizard = SetupWizard()
        wizard.setStyleSheet(STYLESHEET)
        if wizard.exec_() == QDialog.Accepted:
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with open(CONFIG_FILE, "w") as f:
                json.dump(wizard.result_config, f, indent=2)
        else:
            sys.exit(0)

    window = MainWindow(start_minimized=args.minimized)
    if args.minimized:
        window.showMinimized()
    else:
        window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
