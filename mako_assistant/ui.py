"""PyQt6 user interface for MAKO Assistant (MAKO 助手), in a Liquid Glass style."""

from __future__ import annotations

import html
import sys
import time
import traceback
from datetime import datetime
from functools import cmp_to_key
from typing import Callable, Optional

from PyQt6.QtCore import (
    QCollator, QEvent, QLibraryInfo, QLocale, QObject, QRunnable, Qt, QThreadPool, QTimer, QTranslator,
    pyqtSignal,
)
from PyQt6.QtGui import QAction, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea, QVBoxLayout,
    QWidget,
)

from . import __version__, i18n, overlay, theme
from .i18n import tr
from .mako_config import DEFAULT_PROFILE_NAME
from .runtime import RunningGame, describe, detect_running
from .service import AssistantService, GameEntry, SteamMustCloseError, SyncChange
from .widgets import (
    THUMB_H, THUMB_W, Backdrop, GameCard, Segmented, StatusPill, Switch, Wordmark,
)

POLL_MS = 3000
OVERLAY_SECONDS = 10
# A game with mako-launch whose processes never load the MAKO layer.
OVERLAY_NO_MAKO_AFTER = 90

FILTER_ALL, FILTER_INSTALLED, FILTER_NOT_INSTALLED, FILTER_CONFIG_ONLY, FILTER_RUNNING = range(5)


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
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(14)
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
        ok.setObjectName("danger")
        buttons.addButton(tr("cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class MainWindow(QMainWindow):
    def __init__(self, service: Optional[AssistantService] = None,
                 entries: Optional[list[GameEntry]] = None, *, autostart: bool = True,
                 expanded: Optional[set[int]] = None,
                 pending: Optional[dict[int, dict]] = None) -> None:
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
        self._cards: dict[int, GameCard] = {}
        self._expanded: set[int] = set(expanded or ())
        # Unsaved settings edits survive a repopulate and a language switch.
        self._pending: dict[int, dict] = dict(pending or {})
        self._settings: dict[int, object] = {}    # last loaded GameSettings (or None)
        self._steam = None

        self.setWindowTitle(window_title())
        self.resize(1480, 920)
        self.setMinimumSize(1100, 640)
        central = Backdrop()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 16, 24, 14)
        root.setSpacing(14)
        root.addWidget(self._build_topbar())
        root.addWidget(self._build_toolbar())

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_host = QWidget()
        self.list_host.setObjectName("transparent")
        self.list_layout = QVBoxLayout(self.list_host)
        self.list_layout.setContentsMargins(0, 0, 6, 0)
        self.list_layout.setSpacing(12)
        self.empty_label = QLabel(tr("no_matches"))
        self.empty_label.setObjectName("empty")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.hide()
        self.list_layout.addWidget(self.empty_label)
        self.list_layout.addStretch(1)
        self.scroll.setWidget(self.list_host)
        self.scroll.viewport().installEventFilter(self)
        root.addWidget(self.scroll, 1)
        root.addWidget(self._build_drawer())
        self.statusBar().hide()

        quit_action = QAction(self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        self.addAction(quit_action)

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(POLL_MS)
        self.poll_timer.timeout.connect(self.poll_runtime)

        hints = QApplication.instance().styleHints()
        if hasattr(hints, "colorSchemeChanged"):
            hints.colorSchemeChanged.connect(lambda *_: self.apply_theme())

        self.write_log(tr("log_started", version=__version__))
        if self.entries:
            self.populate()
        if not autostart:
            return
        if self.entries:
            QTimer.singleShot(0, lambda: self.refresh(rescan=False))
        elif self.service.has_scanned:
            QTimer.singleShot(0, lambda: self.refresh(rescan=False))
        else:
            self.write_log(tr("log_first_scan"))
            QTimer.singleShot(0, lambda: self.refresh(rescan=True))
        self.poll_timer.start()
        QTimer.singleShot(0, self.poll_runtime)
        QApplication.instance().aboutToQuit.connect(self._shutdown)

    # ---- chrome -------------------------------------------------------------------------------

    def _build_topbar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("topbar")
        row = QHBoxLayout(bar)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        brand = QVBoxLayout()
        brand.setSpacing(0)
        brand.addWidget(Wordmark(tr("app_name")))
        tagline = QLabel(tr("subtitle") if tr("app_name") == "MAKO Assistant"
                         else f"MAKO Assistant · {tr('subtitle')}")
        tagline.setObjectName("tagline")
        self.tagline = tagline
        brand.addWidget(tagline)
        row.addLayout(brand)
        row.addStretch(1)
        self.steam_pill = StatusPill()
        self.steam_pill.set_state(tr("steam_unknown"), "faint")
        row.addWidget(self.steam_pill, 20, Qt.AlignmentFlag.AlignVCenter)
        row.addStretch(1)
        self.count_pill = QLabel("")
        self.count_pill.setObjectName("pill")
        self.count_pill.setFixedHeight(32)
        row.addWidget(self.count_pill, 0, Qt.AlignmentFlag.AlignVCenter)
        self.language_box = QComboBox()
        self.language_box.setToolTip(tr("language"))
        for code, native, _ in i18n.LANGUAGES:
            self.language_box.addItem(f"🌐  {native}", code)
        self.language_box.setCurrentIndex(i18n.CODES.index(i18n.current()))
        self.language_box.currentIndexChanged.connect(self.change_language)
        row.addWidget(self.language_box, 0, Qt.AlignmentFlag.AlignVCenter)
        self.rescan_btn = QPushButton(tr("rescan"))
        self.rescan_btn.setObjectName("primary")
        self.rescan_btn.setToolTip(tr("rescan_tip"))
        self.rescan_btn.clicked.connect(lambda: self.refresh(rescan=True))
        row.addWidget(self.rescan_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        return bar

    def _build_toolbar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("toolbar")
        row = QHBoxLayout(bar)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("search"))
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.apply_filter)
        row.addWidget(self.search, 1)
        self.filter = QComboBox()
        self.filter.addItems([tr("filter_all"), tr("filter_installed"),
                              tr("filter_not_installed"), tr("filter_config_only"),
                              tr("filter_running")])
        self.filter.currentIndexChanged.connect(self.apply_filter)
        row.addWidget(self.filter)
        self.theme_box = Segmented([("auto", tr("theme_auto")), ("dark", tr("theme_dark")),
                                    ("light", tr("theme_light"))], compact=True)
        self.theme_box.setToolTip(tr("theme"))
        self.theme_box.set_value(self.service.theme)
        self.theme_box.changed.connect(self.change_theme)
        row.addWidget(self.theme_box, 0, Qt.AlignmentFlag.AlignVCenter)
        self.overlay_switch = Switch()
        self.overlay_switch.setChecked(self.service.overlay_enabled)
        self.overlay_switch.toggled.connect(
            lambda checked: setattr(self.service, "overlay_enabled", checked))
        overlay_label = QLabel(tr("osd_toggle"))
        overlay_label.setToolTip(tr("osd_toggle_tip"))
        self.overlay_switch.setToolTip(tr("osd_toggle_tip"))
        row.addSpacing(6)
        row.addWidget(self.overlay_switch, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(overlay_label)
        return bar

    def _build_drawer(self) -> QWidget:
        drawer = QFrame()
        drawer.setObjectName("drawer")
        layout = QVBoxLayout(drawer)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(6)
        head = QHBoxLayout()
        self.log_toggle = QPushButton(f"▸  {tr('activity')}")
        self.log_toggle.setObjectName("link")
        self.log_toggle.setCheckable(True)
        self.log_toggle.toggled.connect(self._toggle_log)
        head.addWidget(self.log_toggle)
        self.last_line = QLabel("")
        self.last_line.setObjectName("muted")
        head.addWidget(self.last_line, 1)
        footer = QLabel(f"MAKO Assistant v{__version__}")
        footer.setObjectName("footer")
        head.addWidget(footer)
        layout.addLayout(head)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(2000)
        self.log.setFixedHeight(150)
        self.log.hide()
        layout.addWidget(self.log)
        return drawer

    def _toggle_log(self, shown: bool) -> None:
        self.log.setVisible(shown)
        self.log_toggle.setText(f"{'▾' if shown else '▸'}  {tr('activity')}")
        self.last_line.setVisible(not shown)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._reflow()

    def eventFilter(self, watched, event) -> bool:
        # The list viewport settles its width after the window's own resize event.
        if watched is self.scroll.viewport() and event.type() == QEvent.Type.Resize:
            self._reflow()
        return super().eventFilter(watched, event)

    def _reflow(self) -> None:
        """Hide the tagline and change settings columns as the window narrows."""
        self.tagline.setVisible(self.width() >= 1380)
        width = self.scroll.viewport().width() - 40   # card and panel margins
        for card in self._cards.values():
            card.set_compact(card.wide_width() > width + 34)
            if card.panel is not None:
                card.panel.set_columns(card.panel.columns_for(width))

    def _shutdown(self) -> None:
        """Let background tasks finish before Qt and Python tear down."""
        self.poll_timer.stop()
        self.pool.waitForDone(15000)

    # ---- theme & language -----------------------------------------------------------------------

    def change_theme(self, choice: str) -> None:
        self.service.theme = choice
        self.apply_theme()

    def apply_theme(self) -> None:
        theme.set_mode(theme.resolve(self.service.theme))
        QApplication.instance().setStyleSheet(theme.stylesheet())
        self.centralWidget().update()
        for card in self._cards.values():
            card.set_runtime(self.running.get(card.entry.app_id))
            card.update()

    def change_language(self, index: int) -> None:
        code = self.language_box.itemData(index)
        if code == i18n.current():
            return
        self.service.language = code
        i18n.set_language(code)
        app = QApplication.instance()
        install_translations(app)
        app.setApplicationDisplayName(tr("app_name"))
        replacement = MainWindow(self.service, self.entries, expanded=self._expanded,
                                 pending=self._pending)
        replacement.setGeometry(self.geometry())
        if self.isMaximized():
            replacement.showMaximized()
        else:
            replacement.show()
        app.main_window = replacement
        self.poll_timer.stop()
        self.close()
        self.deleteLater()

    # ---- helpers ------------------------------------------------------------------------------

    def write_log(self, text: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        lines = str(text).splitlines() or [""]
        for line in lines:
            self.log.appendPlainText(f"[{stamp}] {line}")
        self.last_line.setText(lines[0] if len(lines) == 1 else f"{lines[0]} …")

    def set_busy(self, busy: bool, message: str = "") -> None:
        self.busy = busy
        self.rescan_btn.setEnabled(not busy)
        self.language_box.setEnabled(not busy)
        self.list_host.setEnabled(not busy)
        if busy:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            if message:
                self.last_line.setText(message)
        else:
            QApplication.restoreOverrideCursor()

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

    # ---- data -------------------------------------------------------------------------------

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
            self._settings.clear()   # profiles may have changed on disk
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
            if session["shown"] or not self.overlay_switch.isChecked():
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
        color = "#27d4b3" if game.mako_loaded and features else "#f2c14e"
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
        self.steam_pill.set_state(tr(key), "ok" if live or not running else "warn")

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
                    ratio = self.devicePixelRatioF()
                    scaled = loaded.scaled(int(THUMB_W * ratio), int(THUMB_H * ratio),
                                           Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                           Qt.TransformationMode.SmoothTransformation)
                    scaled = scaled.copy((scaled.width() - int(THUMB_W * ratio)) // 2,
                                         (scaled.height() - int(THUMB_H * ratio)) // 2,
                                         int(THUMB_W * ratio), int(THUMB_H * ratio))
                    scaled.setDevicePixelRatio(ratio)
                    pixmap = theme.rounded(scaled, 10)
            self._thumbs[app_id] = pixmap
        return self._thumbs[app_id]

    def populate(self) -> None:
        for card in self._cards.values():
            self.list_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()
        collator = QCollator(QLocale(i18n.qt_suffix()))
        collator.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        collator.setNumericMode(True)
        self.entries.sort(key=cmp_to_key(lambda a, b: collator.compare(a.display_name,
                                                                        b.display_name)))
        actions = {"launch": self.launch, "install": self.install, "uninstall": self.uninstall}
        installed = 0
        for index, entry in enumerate(self.entries):
            card = GameCard(entry, self._thumb(entry.app_id), actions, self.list_host)
            card.expand_toggled.connect(self._on_expand)
            self.list_layout.insertWidget(index, card)
            self._cards[entry.app_id] = card
            installed += entry.has_mako
            if entry.app_id in self._expanded:
                card.set_expanded(True)
                self._load_settings(entry.app_id)
        self.count_pill.setText(tr("count", installed=installed, total=len(self.entries)))
        self.update_runtime()
        self._reflow()

    def update_runtime(self) -> None:
        for app_id, card in self._cards.items():
            card.set_runtime(self.running.get(app_id))
        self.apply_filter()
        self._reflow()

    def apply_filter(self) -> None:
        query = self.search.text().strip().casefold()
        mode = self.filter.currentIndex()
        shown = 0
        for entry in self.entries:
            card = self._cards.get(entry.app_id)
            if card is None:
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
            card.setVisible(visible)
            shown += visible
        self.empty_label.setVisible(bool(self._cards) and shown == 0)

    # ---- per-game settings ---------------------------------------------------------------------

    def _on_expand(self, app_id: int, expanded: bool) -> None:
        if expanded:
            self._expanded.add(app_id)
            self._load_settings(app_id)
            self._reflow()
        else:
            self._expanded.discard(app_id)

    def _load_settings(self, app_id: int) -> None:
        card = self._cards.get(app_id)
        if card is None:
            return
        panel = card.ensure_panel()
        if not getattr(panel, "_wired", False):
            panel.apply_requested.connect(self.apply_settings)
            panel.pending_changed.connect(lambda i, p: self._pending.__setitem__(i, p))
            panel._wired = True
        if app_id in self._settings:
            panel.set_settings(self._settings[app_id], self._pending.get(app_id))
            return
        panel.set_loading()
        task = _Task(self.service.game_settings, app_id)

        def done(settings):
            self._settings[app_id] = settings
            current = self._cards.get(app_id)
            if current is not None and current.panel is not None:
                current.panel.set_settings(settings, self._pending.get(app_id))

        def failed(error):
            self.write_log(tr("log_error", error=error))
            current = self._cards.get(app_id)
            if current is not None and current.panel is not None:
                current.panel.set_settings(None)

        task.signals.done.connect(done)
        task.signals.failed.connect(failed)
        self.pool.start(task)

    def apply_settings(self, app_id: int, changes: dict) -> None:
        if not changes:
            return
        entry = next((e for e in self.entries if e.app_id == app_id), None)
        name = entry.display_name if entry else str(app_id)

        def work():
            message = self.service.apply_game_settings(app_id, changes)
            return message, self.service.game_settings(app_id)

        def done(result):
            message, settings = result
            self.write_log(message)
            self._pending.pop(app_id, None)
            self._settings[app_id] = settings
            card = self._cards.get(app_id)
            if card is not None and card.panel is not None:
                card.panel.set_settings(settings, {})

        self.run_task(tr("busy_apply", name=name), work, on_done=done)

    # ---- actions -------------------------------------------------------------------------------

    def launch(self, entry: GameEntry) -> None:
        self.write_log(tr("log_launch", name=entry.display_name))
        try:
            self.service.launch_game(entry.app_id)
        except RuntimeError as error:
            self.write_log(tr("log_error", error=error))
            self.error_box(str(error))
            return
        card = self._cards.get(entry.app_id)
        if card is not None:
            card.launch_btn.setEnabled(False)  # re-enabled by polling if the game never starts
        QTimer.singleShot(1500, self.poll_runtime)

    def install(self, entry: GameEntry) -> None:
        self.write_log(tr("log_install", name=entry.display_name))
        self._settings.pop(entry.app_id, None)
        self._run_action(tr("busy_install", name=entry.display_name),
                         self.service.install, entry.app_id)

    def uninstall(self, entry: GameEntry) -> None:
        dialog = RemoveDialog(entry, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        remove_config = dialog.remove_config.isChecked()
        self.write_log(tr("log_remove_with_config" if remove_config else "log_remove",
                          name=entry.display_name))
        self._settings.pop(entry.app_id, None)
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
            try:
                result = fn(*args)
            finally:
                self.service.start_steam()  # reopen Steam even if applying failed
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


def prepare_app(app: QApplication, service: AssistantService) -> None:
    i18n.set_language(service.language)
    install_translations(app)
    app.setApplicationName("MAKO Assistant")
    app.setApplicationDisplayName(tr("app_name"))
    app.setDesktopFileName("mako-assistant")
    app.setStyle("Fusion")
    theme.load_fonts()
    theme.set_mode(theme.resolve(service.theme))
    app.setStyleSheet(theme.stylesheet())


def main() -> int:
    app = QApplication(sys.argv)
    service = AssistantService()
    prepare_app(app, service)
    app.main_window = MainWindow(service)
    app.main_window.show()
    return app.exec()
