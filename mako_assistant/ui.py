"""PyQt6 user interface for MAKO Assistant (MAKO 助手)."""

from __future__ import annotations

import html
import sys
import time
import traceback
from datetime import datetime
from functools import cmp_to_key
from typing import Callable, Optional

from PyQt6.QtCore import (
    QCollator, QLibraryInfo, QLocale, QObject, QRunnable, QSize, Qt, QThreadPool, QTimer, QTranslator,
    pyqtSignal,
)
from PyQt6.QtGui import QAction, QColor, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPlainTextEdit, QPushButton, QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget,
)

from . import __version__, i18n, overlay
from .i18n import tr
from .runtime import RunningGame, describe, detect_running
from .mako_config import DEFAULT_PROFILE_NAME
from .service import AssistantService, GameEntry, SteamMustCloseError, SyncChange

THUMB_W, THUMB_H = 138, 64
ROW_H = THUMB_H + 30
POLL_MS = 3000
OVERLAY_SECONDS = 10
# A game with mako-launch whose processes never load the MAKO layer.
OVERLAY_NO_MAKO_AFTER = 90

COL_GAME, COL_STATUS, COL_PROFILE, COL_RUNTIME, COL_PATHS, COL_ACTIONS = range(6)
FILTER_ALL, FILTER_INSTALLED, FILTER_NOT_INSTALLED, FILTER_CONFIG_ONLY, FILTER_RUNNING = range(5)

STYLE = """
QMainWindow, QDialog { background: #15171c; }
QWidget { color: #e6e8ee; font-size: 14px; }
QLabel#title { font-size: 22px; font-weight: 700; }
QLabel#subtitle { color: #9aa3b2; }
QLabel[class="pill"] { border-radius: 10px; padding: 3px 10px; background: #252a33; color: #c9d1dc; }
QLineEdit, QComboBox { background: #1f232b; border: 1px solid #323846; border-radius: 6px;
    padding: 6px 8px; }
QPushButton { background: #2a303b; border: 1px solid #3a4150; border-radius: 6px;
    padding: 7px 12px; }
QPushButton:hover { background: #343b48; }
QPushButton:disabled { color: #6b7380; background: #1f232b; }
QPushButton#primary { background: #2f6fed; border-color: #2f6fed; color: white; font-weight: 600; }
QPushButton#primary:hover { background: #4682f5; }
QPushButton#install { background: #1f8a4c; border-color: #1f8a4c; color: white; font-weight: 600; }
QPushButton#install:hover { background: #27a35b; }
QPushButton#remove { background: #3a2226; border-color: #8a3340; color: #ffb3bd; }
QPushButton#remove:hover { background: #4d2a30; }
QPushButton#launch { background: #23324d; border-color: #3b5b96; color: #cfe0ff; font-weight: 600; }
QPushButton#launch:hover { background: #2c3f61; }
QPushButton#launch:disabled { background: #1c3a2a; border-color: #2c6b48; color: #7fe0a6; }
QTableWidget { background: #1a1d23; border: 1px solid #2a2f3a; border-radius: 8px;
    gridline-color: transparent; alternate-background-color: #1d2128; }
QTableWidget::item { padding: 4px; }
QTableWidget::item:selected { background: #26324a; }
QHeaderView::section { background: #1f232b; color: #9aa3b2; border: none; padding: 6px; }
QPlainTextEdit { background: #111318; border: 1px solid #2a2f3a; border-radius: 8px;
    font-family: monospace; font-size: 12px; color: #b8c0cc; }
QCheckBox { spacing: 8px; }
"""


def window_title() -> str:
    name = tr("app_name")
    return name if name == "MAKO Assistant" else f"{name} (MAKO Assistant)"


class _Signals(QObject):
    done = pyqtSignal(object)
    failed = pyqtSignal(object)


class _Task(QRunnable):
    def __init__(self, fn: Callable, *args) -> None:
        super().__init__()
        self.fn, self.args = fn, args
        self.signals = _Signals()

    def run(self) -> None:
        try:
            result = self.fn(*self.args)
        except Exception as error:  # surfaced to the UI
            error.trace = traceback.format_exc()
            self.signals.failed.emit(error)
        else:
            self.signals.done.emit(result)


class RemoveDialog(QDialog):
    def __init__(self, entry: GameEntry, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("remove_title"))
        self.setMinimumWidth(480)
        layout = QVBoxLayout(self)
        text = QLabel(
            tr("remove_body", name=html.escape(entry.display_name))
            + "<br><code>~/.local/bin/mako-launch %command%</code><br><br>"
            + html.escape(tr("remove_keep")))
        text.setWordWrap(True)
        layout.addWidget(text)
        self.remove_config = QCheckBox(tr("remove_also"))
        if entry.profile_name:
            self.remove_config.setText(tr("remove_also_named", profile=entry.profile_name))
        else:
            self.remove_config.setEnabled(False)
            self.remove_config.setToolTip(tr("remove_no_config"))
        layout.addWidget(self.remove_config)
        buttons = QDialogButtonBox()
        ok = buttons.addButton(tr("btn_remove"), QDialogButtonBox.ButtonRole.AcceptRole)
        ok.setObjectName("remove")
        buttons.addButton(tr("cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class MainWindow(QMainWindow):
    def __init__(self, service: Optional[AssistantService] = None,
                 entries: Optional[list[GameEntry]] = None) -> None:
        super().__init__()
        self.service = service or AssistantService()
        self.pool = QThreadPool.globalInstance()
        self.entries: list[GameEntry] = list(entries or [])
        self.running: dict[int, RunningGame] = {}
        self.busy = False
        self._polling = False
        self._first_poll = True
        # app id -> {"since": monotonic seconds, "shown": bool} per game session
        self._sessions: dict[int, dict] = {}
        self._thumbs: dict[int, Optional[QPixmap]] = {}
        self._row_widgets: dict[int, tuple[QLabel, QPushButton]] = {}
        self._steam = None

        self.setWindowTitle(window_title())
        self.resize(1440, 800)
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        title = QLabel(tr("app_name"))
        title.setObjectName("title")
        subtitle = QLabel(f"MAKO Assistant · {tr('subtitle')}")
        subtitle.setObjectName("subtitle")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        header.addLayout(titles)
        header.addStretch(1)
        center = Qt.AlignmentFlag.AlignVCenter
        self.count_pill = QLabel("")
        self.count_pill.setProperty("class", "pill")
        self.steam_pill = QLabel(tr("steam_unknown"))
        self.steam_pill.setProperty("class", "pill")
        header.addWidget(self.count_pill, 0, center)
        header.addWidget(self.steam_pill, 0, center)
        self.language_box = QComboBox()
        self.language_box.setToolTip(tr("language"))
        for code, native, _ in i18n.LANGUAGES:
            self.language_box.addItem(f"🌐 {native}", code)
        self.language_box.setCurrentIndex(i18n.CODES.index(i18n.current()))
        self.language_box.currentIndexChanged.connect(self.change_language)
        header.addWidget(self.language_box, 0, center)
        self.rescan_btn = QPushButton(tr("rescan"))
        self.rescan_btn.setObjectName("primary")
        self.rescan_btn.setToolTip(tr("rescan_tip"))
        self.rescan_btn.clicked.connect(lambda: self.refresh(rescan=True))
        header.addWidget(self.rescan_btn, 0, center)
        root.addLayout(header)

        tools = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("search"))
        self.search.textChanged.connect(self.apply_filter)
        self.filter = QComboBox()
        self.filter.addItems([tr("filter_all"), tr("filter_installed"),
                              tr("filter_not_installed"), tr("filter_config_only"),
                              tr("filter_running")])
        self.filter.currentIndexChanged.connect(self.apply_filter)
        self.overlay_box = QCheckBox(tr("osd_toggle"))
        self.overlay_box.setToolTip(tr("osd_toggle_tip"))
        self.overlay_box.setChecked(self.service.overlay_enabled)
        self.overlay_box.toggled.connect(
            lambda checked: setattr(self.service, "overlay_enabled", checked))
        tools.addWidget(self.search, 1)
        tools.addWidget(self.filter)
        tools.addWidget(self.overlay_box)
        root.addLayout(tools)

        columns = (tr("col_game"), tr("col_status"), tr("col_profile"), tr("col_runtime"),
                   tr("col_paths"), tr("col_actions"))
        self.table = QTableWidget(0, len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setWordWrap(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setIconSize(QSize(THUMB_W, THUMB_H))
        self.table.verticalHeader().setDefaultSectionSize(ROW_H)
        head = self.table.horizontalHeader()
        head.setSectionResizeMode(COL_STATUS, QHeaderView.ResizeMode.ResizeToContents)
        for col, width in ((COL_GAME, 360), (COL_PROFILE, 240), (COL_PATHS, 200)):
            head.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            self.table.setColumnWidth(col, width)
        head.setSectionResizeMode(COL_RUNTIME, QHeaderView.ResizeMode.Stretch)
        head.setSectionResizeMode(COL_ACTIONS, QHeaderView.ResizeMode.Fixed)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(2000)
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.table)
        splitter.addWidget(self.log)
        splitter.setSizes([620, 130])
        root.addWidget(splitter, 1)

        quit_action = QAction(self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        self.addAction(quit_action)

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(POLL_MS)
        self.poll_timer.timeout.connect(self.poll_runtime)

        self.write_log(tr("log_started", version=__version__))
        if self.entries:
            self.populate()
            QTimer.singleShot(0, lambda: self.refresh(rescan=False))
        elif self.service.has_scanned:
            QTimer.singleShot(0, lambda: self.refresh(rescan=False))
        else:
            self.write_log(tr("log_first_scan"))
            QTimer.singleShot(0, lambda: self.refresh(rescan=True))
        self.poll_timer.start()
        QTimer.singleShot(0, self.poll_runtime)
        QApplication.instance().aboutToQuit.connect(self._shutdown)

    def _shutdown(self) -> None:
        """Let background tasks finish before Qt and Python tear down."""
        self.poll_timer.stop()
        self.pool.waitForDone(15000)

    # ---- language -------------------------------------------------------------

    def change_language(self, index: int) -> None:
        code = self.language_box.itemData(index)
        if code == i18n.current():
            return
        self.service.language = code
        i18n.set_language(code)
        app = QApplication.instance()
        install_translations(app)
        app.setApplicationDisplayName(tr("app_name"))
        replacement = MainWindow(self.service, self.entries)
        replacement.setGeometry(self.geometry())
        if self.isMaximized():
            replacement.showMaximized()
        else:
            replacement.show()
        app.main_window = replacement
        self.poll_timer.stop()
        self.close()
        self.deleteLater()

    # ---- helpers ------------------------------------------------------------

    def write_log(self, text: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        for line in str(text).splitlines() or [""]:
            self.log.appendPlainText(f"[{stamp}] {line}")

    def set_busy(self, busy: bool, message: str = "") -> None:
        self.busy = busy
        self.rescan_btn.setEnabled(not busy)
        self.language_box.setEnabled(not busy)
        self.table.setEnabled(not busy)
        if busy:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            if message:
                self.statusBar().showMessage(message)
        else:
            QApplication.restoreOverrideCursor()
            self.statusBar().clearMessage()

    def error_box(self, message: str) -> None:
        box = QMessageBox(QMessageBox.Icon.Critical, window_title(), message, parent=self)
        box.addButton(tr("ok"), QMessageBox.ButtonRole.AcceptRole)
        box.exec()

    def run_task(self, message: str, fn: Callable, *args,
                 on_done: Callable[[object], None], on_error: Optional[Callable] = None) -> None:
        self.set_busy(True, message)
        task = _Task(fn, *args)

        def done(result):
            self.set_busy(False)
            on_done(result)

        def failed(error):
            self.set_busy(False)
            if on_error is not None and on_error(error):
                return
            self.write_log(tr("log_error", error=error))
            self.error_box(str(error))

        task.signals.done.connect(done)
        task.signals.failed.connect(failed)
        self.pool.start(task)

    # ---- data -----------------------------------------------------------------

    def refresh(self, rescan: bool) -> None:
        if self.busy:
            return

        def work():
            entries, changes = self.service.scan(rescan_library=rescan)
            steam = self.service.steam()
            running = steam.is_running()
            live = running and self.service.cef.available()
            return entries, changes, running, live

        def done(result):
            entries, changes, running, live = result
            self.entries = entries
            self._update_steam_pill(running, live)
            if rescan:
                self.write_log(tr("log_scan_done", count=len(entries)))
            self._report_sync(changes)
            self.populate()

        self.run_task(tr("busy_scan") if rescan else tr("busy_load"), work, on_done=done)

    def poll_runtime(self) -> None:
        if self._polling:
            return
        self._polling = True
        task = _Task(detect_running)

        def done(result):
            self._polling = False
            self.running = result
            self._track_sessions()
            self.update_runtime()

        def failed(_error):
            self._polling = False

        task.signals.done.connect(done)
        task.signals.failed.connect(failed)
        self.pool.start(task)

    def _track_sessions(self) -> None:
        """Show the overlay once per game launch, when MAKO's state is known."""
        now = time.monotonic()
        for app_id in list(self._sessions):
            if app_id not in self.running:
                del self._sessions[app_id]  # game exited: the next launch is a new session
        entries = {e.app_id: e for e in self.entries}
        for app_id, game in self.running.items():
            # Games already running when the assistant opened are not "starting".
            session = self._sessions.setdefault(
                app_id, {"since": now, "shown": self._first_poll})
            if session["shown"] or not self.overlay_box.isChecked():
                continue
            entry = entries.get(app_id)
            mako_ready = game.mako_loaded and bool(game.contexts)
            mako_missing = (not game.mako_loaded and entry is not None and entry.has_mako
                            and now - session["since"] > OVERLAY_NO_MAKO_AFTER)
            if mako_ready or mako_missing:
                session["shown"] = True
                self._show_overlay(entry, game)
        self._first_poll = False

    def _show_overlay(self, entry: Optional[GameEntry], game: RunningGame) -> None:
        headline, features, notes = describe(game)
        color = "#4cd384" if game.mako_loaded and features else "#f2c14e"
        try:
            overlay.show({
                "title": entry.display_name if entry else f"App {game.app_id}",
                "headline": headline,
                "color": color,
                "lines": [{"label": f.label, "detail": f.detail, "active": f.active}
                          for f in features],
                "notes": notes,
                "seconds": OVERLAY_SECONDS,
            })
        except OSError as error:
            self.write_log(tr("log_error", error=error))

    def _report_sync(self, changes: list[SyncChange]) -> None:
        for change in changes:
            if change.paths_changed:
                self.write_log(tr("log_path_updated", name=change.name))
                if change.before != change.after:
                    self.write_log(tr("log_processes", before=", ".join(change.before) or "—",
                                      after=", ".join(change.after)))
                for path in change.new_paths:
                    if path not in change.old_paths:
                        self.write_log(f"    + {path}")
            if change.released:
                self.write_log(tr("cfg_released_default", processes=", ".join(change.released),
                                  default=DEFAULT_PROFILE_NAME, profile=change.profile))

    def _update_steam_pill(self, running: bool, live: bool) -> None:
        key = "steam_off" if not running else "steam_live" if live else "steam_must_close"
        self.steam_pill.setText(tr(key))

    def _thumb(self, app_id: int) -> Optional[QPixmap]:
        if app_id not in self._thumbs:
            pixmap = None
            try:
                if self._steam is None:
                    self._steam = self.service.steam()
                path = self._steam.header_image(app_id)
            except FileNotFoundError:
                path = None
            if path:
                loaded = QPixmap(str(path))
                if not loaded.isNull():
                    pixmap = loaded.scaled(THUMB_W, THUMB_H,
                                           Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                           Qt.TransformationMode.SmoothTransformation)
            self._thumbs[app_id] = pixmap
        return self._thumbs[app_id]

    @staticmethod
    def _status(entry: GameEntry) -> tuple[str, str]:
        if entry.has_mako and entry.profile_name:
            return tr("st_installed"), "#4cd384"
        if entry.has_mako:
            return tr("st_injected"), "#f2c14e"
        if entry.profile_name:
            return tr("st_config_only"), "#8fb3ff"
        return tr("st_not_installed"), "#8b93a1"

    def populate(self) -> None:
        self.table.setRowCount(0)
        self._row_widgets.clear()
        installed = 0
        collator = QCollator(QLocale(i18n.qt_suffix()))
        collator.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        collator.setNumericMode(True)
        self.entries.sort(key=cmp_to_key(lambda a, b: collator.compare(a.display_name,
                                                                        b.display_name)))
        for entry in self.entries:
            row = self.table.rowCount()
            self.table.insertRow(row)

            name_item = QTableWidgetItem(f"{entry.display_name}\nApp ID {entry.app_id}")
            name_item.setData(Qt.ItemDataRole.UserRole, entry.app_id)
            thumb = self._thumb(entry.app_id)
            if thumb:
                name_item.setIcon(QIcon(thumb))
            tooltip = entry.install_dir
            if entry.display_name != entry.name:
                tooltip = f"{entry.name}\n{tooltip}"
            name_item.setToolTip(tooltip)
            self.table.setItem(row, COL_GAME, name_item)

            label, color = self._status(entry)
            status = QTableWidgetItem(label)
            status.setForeground(QColor(color))
            status.setToolTip(tr("launch_options_tip",
                                 options=entry.launch_options or tr("empty")))
            self.table.setItem(row, COL_STATUS, status)

            profile_text = (f"{entry.profile_name}\n{', '.join(entry.profile_processes) or '—'}"
                            if entry.profile_name else "—")
            self.table.setItem(row, COL_PROFILE, QTableWidgetItem(profile_text))

            runtime_label = QLabel()
            runtime_label.setWordWrap(True)
            runtime_label.setTextFormat(Qt.TextFormat.RichText)
            runtime_label.setContentsMargins(6, 2, 6, 2)
            self.table.setCellWidget(row, COL_RUNTIME, runtime_label)

            paths = entry.executables
            path_item = QTableWidgetItem("\n".join(paths) if paths else
                                         (tr("not_detected") if entry.managed else "—"))
            path_item.setToolTip("\n".join(paths) or entry.install_dir)
            self.table.setItem(row, COL_PATHS, path_item)

            cell = QWidget()
            box = QHBoxLayout(cell)
            box.setContentsMargins(6, 4, 6, 4)
            box.setSpacing(6)
            launch = QPushButton(tr("btn_launch"))
            launch.setObjectName("launch")
            launch.setToolTip(tr("btn_launch_tip"))
            launch.clicked.connect(lambda _, e=entry: self.launch(e))
            box.addWidget(launch)
            if entry.has_mako and not entry.profile_name:
                adopt = QPushButton(tr("btn_import"))
                adopt.setObjectName("install")
                adopt.setToolTip(tr("btn_import_tip"))
                adopt.clicked.connect(lambda _, e=entry: self.install(e))
                box.addWidget(adopt)
            if entry.has_mako:
                installed += 1
                button = QPushButton(tr("btn_remove"))
                button.setObjectName("remove")
                button.clicked.connect(lambda _, e=entry: self.uninstall(e))
            else:
                button = QPushButton(tr("btn_install"))
                button.setObjectName("install")
                button.clicked.connect(lambda _, e=entry: self.install(e))
            box.addWidget(button)
            box.addStretch(1)
            self.table.setCellWidget(row, COL_ACTIONS, cell)
            self._row_widgets[entry.app_id] = (runtime_label, launch)
        self.count_pill.setText(tr("count", installed=installed, total=len(self.entries)))
        # Cell widgets are ignored by ResizeToContents; size the column from the
        # widest button row (button labels differ a lot between languages).
        widest = max((self.table.cellWidget(r, COL_ACTIONS).sizeHint().width()
                      for r in range(self.table.rowCount())), default=200)
        self.table.setColumnWidth(COL_ACTIONS, widest + 8)
        self.update_runtime()

    def update_runtime(self) -> None:
        for app_id, (label, launch) in self._row_widgets.items():
            game = self.running.get(app_id)
            launch.setEnabled(game is None)
            launch.setText(tr("btn_running") if game else tr("btn_launch"))
            if game is None:
                label.setText('<span style="color:#6b7380">—</span>')
                label.setToolTip("")
                continue
            headline, features, notes = describe(game)
            color = "#4cd384" if game.mako_loaded and features else (
                "#f2c14e" if game.mako_loaded else "#8b93a1")
            parts = [f'<b style="color:{color}">{html.escape(headline)}</b>']
            for feature in features:
                mark, tone = ("✓", "#7fe0a6") if feature.active else ("✗", "#8b93a1")
                detail = f" — {html.escape(feature.detail)}" if feature.detail else ""
                parts.append(f'<span style="color:{tone}">{mark} {html.escape(feature.label)}'
                             f'</span><span style="color:#b8c0cc">{detail}</span>')
            for note in notes:
                parts.append(f'<span style="color:#f2c14e">⚠ {html.escape(note)}</span>')
            label.setText("<br>".join(parts))
            label.setToolTip(tr("rt_pids", pids=", ".join(map(str, sorted(game.pids)))))
        self.apply_filter()

    def apply_filter(self) -> None:
        query = self.search.text().strip().casefold()
        mode = self.filter.currentIndex()
        by_id = {e.app_id: e for e in self.entries}
        for row in range(self.table.rowCount()):
            item = self.table.item(row, COL_GAME)
            entry = by_id.get(item.data(Qt.ItemDataRole.UserRole)) if item else None
            if entry is None:
                continue
            visible = not query or entry.matches(query)
            if mode == FILTER_INSTALLED:
                visible &= entry.has_mako
            elif mode == FILTER_NOT_INSTALLED:
                visible &= not entry.has_mako
            elif mode == FILTER_CONFIG_ONLY:
                visible &= bool(entry.profile_name) and not entry.has_mako
            elif mode == FILTER_RUNNING:
                visible &= entry.app_id in self.running
            self.table.setRowHidden(row, not visible)

    # ---- actions ------------------------------------------------------------

    def launch(self, entry: GameEntry) -> None:
        self.write_log(tr("log_launch", name=entry.display_name))
        try:
            self.service.launch_game(entry.app_id)
        except RuntimeError as error:
            self.write_log(tr("log_error", error=error))
            self.error_box(str(error))
            return
        _, launch = self._row_widgets.get(entry.app_id, (None, None))
        if launch is not None:
            launch.setEnabled(False)  # re-enabled by polling if the game never starts
        QTimer.singleShot(1500, self.poll_runtime)

    def install(self, entry: GameEntry) -> None:
        self.write_log(tr("log_install", name=entry.display_name))
        self._run_action(tr("busy_install", name=entry.display_name),
                         self.service.install, entry.app_id)

    def uninstall(self, entry: GameEntry) -> None:
        dialog = RemoveDialog(entry, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        remove_config = dialog.remove_config.isChecked()
        self.write_log(tr("log_remove_with_config" if remove_config else "log_remove",
                          name=entry.display_name))
        self._run_action(tr("busy_remove", name=entry.display_name),
                         self.service.uninstall, entry.app_id, remove_config)

    def _run_action(self, message: str, fn: Callable, *args) -> None:
        def done(result):
            self.write_log(result)
            self.refresh(rescan=False)

        def on_error(error):
            if isinstance(error, SteamMustCloseError):
                self._offer_steam_restart(fn, *args)
                return True
            return False

        self.run_task(message, fn, *args, on_done=done, on_error=on_error)

    def _offer_steam_restart(self, fn: Callable, *args) -> None:
        box = QMessageBox(QMessageBox.Icon.Question, window_title(), tr("steam_close_q"),
                          parent=self)
        confirm = box.addButton(tr("steam_close_confirm"), QMessageBox.ButtonRole.AcceptRole)
        box.addButton(tr("cancel"), QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is not confirm:
            self.write_log(tr("log_steam_cancel"))
            return

        def work():
            if not self.service.shutdown_steam():
                raise RuntimeError(tr("err_steam_timeout"))
            result = fn(*args)
            self.service.start_steam()
            return result + "\n" + tr("log_steam_restarted")

        def done(result):
            self.write_log(result)
            self.refresh(rescan=False)

        self.run_task(tr("busy_steam_apply"), work, on_done=done)


def install_translations(app: QApplication) -> None:
    """Translate Qt's own texts (context menus, standard dialogs) to the UI language."""
    for translator in getattr(app, "_mako_translators", []):
        app.removeTranslator(translator)
    app._mako_translators = []
    suffix = i18n.qt_suffix()
    QLocale.setDefault(QLocale(suffix))
    directories = (
        QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath),
        "/usr/share/qt6/translations",
    )
    for name in (f"qtbase_{suffix}", f"qt_{suffix}"):
        for directory in directories:
            translator = QTranslator(app)
            if translator.load(name, directory):
                app.installTranslator(translator)
                app._mako_translators.append(translator)
                break


def main() -> int:
    app = QApplication(sys.argv)
    service = AssistantService()
    i18n.set_language(service.language)
    install_translations(app)
    app.setApplicationName("MAKO Assistant")
    app.setApplicationDisplayName(tr("app_name"))
    app.setDesktopFileName("mako-assistant")
    app.setStyleSheet(STYLE)
    app.main_window = MainWindow(service)
    app.main_window.show()
    return app.exec()
