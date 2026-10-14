"""Widgets for the UVC Studio-style interface: switch, segmented control,
chevron button, gradient wordmark, the per-game settings panel and game cards."""

from __future__ import annotations

import html
from typing import Any, Callable, Optional

from PyQt6.QtCore import (
    QEasingCurve, QPointF, QPropertyAnimation, QRectF, QSize, Qt, pyqtProperty, pyqtSignal,
)
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import (
    QAbstractButton, QButtonGroup, QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QSlider,
    QSpinBox, QVBoxLayout, QWidget,
)

from . import mako_settings as ms
from . import theme
from .i18n import tr
from .runtime import RunningGame, describe

THUMB_W, THUMB_H = 184, 86


def _label(text: str = "", name: str = "", wrap: bool = False) -> QLabel:
    label = QLabel(text)
    if name:
        label.setObjectName(name)
    label.setWordWrap(wrap)
    return label


def repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)


# ---- primitives ---------------------------------------------------------------------------------

class Switch(QAbstractButton):
    """Pill toggle: gradient track when on, sliding white knob."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._offset = 0.0
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(140)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._animate)

    def sizeHint(self) -> QSize:
        return QSize(40, 22)

    def _get_offset(self) -> float:
        return self._offset

    def _set_offset(self, value: float) -> None:
        self._offset = value
        self.update()

    offset = pyqtProperty(float, _get_offset, _set_offset)

    def _animate(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def setChecked(self, checked: bool) -> None:  # programmatic: no animation
        super().setChecked(checked)
        self._anim.stop()
        self._offset = 1.0 if checked else 0.0
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(1, 1, self.width() - 2, self.height() - 2)
        radius = r.height() / 2
        enabled = self.isEnabled()
        if self.isChecked():
            grad = theme.button_gradient(r.left(), r.right())
            p.setBrush(grad if enabled else theme.qcolor("track"))
        else:
            p.setBrush(theme.qcolor("track"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(r, radius, radius)
        knob = r.height() - 6
        x = r.left() + 3 + self._offset * (r.width() - knob - 6)
        p.setBrush(QColor(255, 255, 255, 255 if enabled else 150))
        p.drawEllipse(QRectF(x, r.top() + 3, knob, knob))


class ChevronButton(QAbstractButton):
    """Round expand / collapse button (UVC Studio panel chevron)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(38, 38)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(1, 1, self.width() - 2, self.height() - 2)
        if self.isChecked():
            grad = theme.button_gradient(r.left(), r.right())
            p.setBrush(grad)
            p.setPen(Qt.PenStyle.NoPen)
            color = QColor("white")
        else:
            p.setBrush(theme.qcolor("field_hover" if self.underMouse() else "field"))
            p.setPen(QPen(theme.qcolor("border_hover" if self.underMouse() else "border"), 1))
            color = theme.qcolor("fg")
        p.drawEllipse(r)
        c = r.center()
        d = 4.5
        pen = QPen(color, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                   Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        path = QPainterPath()
        if self.isChecked():  # pointing up: collapse
            path.moveTo(c + QPointF(-d, d / 2))
            path.lineTo(c + QPointF(0, -d / 2))
            path.lineTo(c + QPointF(d, d / 2))
        else:
            path.moveTo(c + QPointF(-d, -d / 2))
            path.lineTo(c + QPointF(0, d / 2))
            path.lineTo(c + QPointF(d, -d / 2))
        p.drawPath(path)

    def enterEvent(self, event) -> None:
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.update()
        super().leaveEvent(event)


class Segmented(QFrame):
    """Pill-shaped segmented control; the selected segment takes the gradient."""

    changed = pyqtSignal(object)

    def __init__(self, options: list[tuple[Any, str]], parent: Optional[QWidget] = None,
                 compact: bool = False) -> None:
        super().__init__(parent)
        self.setObjectName("segment")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.values: list[Any] = []
        for index, (value, label) in enumerate(options):
            button = QPushButton(label)
            button.setObjectName("seg")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            if compact:
                button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
            else:
                button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.group.addButton(button, index)
            layout.addWidget(button)
            self.values.append(value)
        self.group.idClicked.connect(lambda i: self.changed.emit(self.values[i]))

    def set_value(self, value: Any) -> None:
        for index, candidate in enumerate(self.values):
            if candidate == value and type(candidate) is type(value):
                self.group.button(index).setChecked(True)
                return
        checked = self.group.checkedButton()
        if checked is not None:  # value not offered: show nothing selected
            self.group.setExclusive(False)
            checked.setChecked(False)
            self.group.setExclusive(True)


class Wordmark(QWidget):
    """'MAKO Assistant' set in Onest with UVC Studio's teal → coral → purple gradient."""

    def __init__(self, text: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.text = text
        self.font_ = QFont("Onest")
        self.font_.setPixelSize(21)
        self.font_.setWeight(QFont.Weight.Bold)
        self.setFont(self.font_)
        self.setMinimumHeight(28)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def sizeHint(self) -> QSize:
        # The app style sheet overrides the widget font; measure the font we paint with.
        return QSize(QFontMetrics(self.font_).horizontalAdvance(self.text) + 4, 28)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        width = QFontMetrics(self.font_).horizontalAdvance(self.text)
        grad = QLinearGradient(0, 0, width, 0)
        grad.setColorAt(0.0, QColor(theme.TEAL))
        grad.setColorAt(0.55, QColor(theme.BLUE))
        grad.setColorAt(1.0, QColor(theme.CORAL))
        p.setPen(QPen(grad, 1))
        p.setFont(self.font_)
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.text)


class StatusPill(QWidget):
    """Pill with a coloured state dot; long text is elided and shown in full as a tooltip."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.text = ""
        self.tone = "ok"
        self.setFixedHeight(32)
        self.setMinimumWidth(140)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

    def set_state(self, text: str, tone: str) -> None:
        self.text, self.tone = text, tone
        self.setToolTip(text)
        self.updateGeometry()
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(self.fontMetrics().horizontalAdvance(self.text) + 50, 32)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        p.setPen(QPen(theme.qcolor("border"), 1))
        p.setBrush(theme.qcolor("panel2"))
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(theme.qcolor(self.tone))
        p.drawEllipse(QRectF(14, r.center().y() - 4, 8, 8))
        p.setPen(theme.qcolor("fg"))
        text_rect = QRectF(30, 0, self.width() - 44, self.height())
        shown = self.fontMetrics().elidedText(self.text, Qt.TextElideMode.ElideRight,
                                               int(text_rect.width()))
        p.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, shown)


class Backdrop(QWidget):
    """Central widget painting the glow background behind everything."""

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        theme.paint_backdrop(p, QRectF(self.rect()))


# ---- settings panel ----------------------------------------------------------------------------

def _format(spec: ms.Field, value: Any) -> str:
    if spec.unit == "percent":
        return f"{float(value) * 100:.0f}%"
    if spec.unit == "x":
        return f"×{float(value):.2f}"
    if spec.unit == "s":
        return f"{float(value):.1f} s"
    return str(value)


class _FieldRow(QWidget):
    """One setting: label (+ Restart chip, value), control, description."""

    def __init__(self, spec: ms.Field, on_change: Callable[[str, Any], None]) -> None:
        super().__init__()
        self.spec = spec
        self.setObjectName("transparent")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        head = QHBoxLayout()
        head.setSpacing(8)
        self.label = _label(tr(spec.label), "fieldLabel")
        head.addWidget(self.label)
        if spec.restart:
            chip = _label(tr("set_restart"), "restart")
            chip.setToolTip(tr("set_restart_tip"))
            head.addWidget(chip)
        head.addStretch(1)
        self.value_label = _label("", "fieldValue")
        self.control: QWidget
        if spec.kind == "toggle":
            self.control = Switch()
            self.control.toggled.connect(lambda checked: on_change(spec.key, bool(checked)))
            head.addWidget(self.control)
            layout.addLayout(head)
        else:
            head.addWidget(self.value_label)
            layout.addLayout(head)
            if spec.kind == "segment":
                self.control = Segmented([(v, tr(k)) for v, k in spec.options])
                self.control.changed.connect(lambda v: on_change(spec.key, v))
            elif spec.kind == "ratio":
                options = [(0, "0x")] + [(n, f"{n}x") for n in range(int(spec.minimum),
                                                                     int(spec.maximum) + 1)]
                self.control = Segmented(options)
                self.control.changed.connect(lambda v: on_change(spec.key, v))
            elif spec.kind == "slider":
                self.control = QSlider(Qt.Orientation.Horizontal)
                steps = round((spec.maximum - spec.minimum) / spec.step)
                self.control.setRange(0, steps)
                self.control.setPageStep(max(1, steps // 10))
                self.control.setCursor(Qt.CursorShape.PointingHandCursor)
                self.control.valueChanged.connect(
                    lambda i: on_change(spec.key, self._slider_value(i)))
            else:  # number
                self.control = QSpinBox()
                self.control.setRange(int(spec.minimum), int(spec.maximum))
                self.control.setSuffix(" FPS" if spec.unit == "fps" else "")
                if spec.off_at_zero:
                    self.control.setSpecialValueText(tr("set_off"))
                self.control.setFixedWidth(130)
                self.control.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
                self.control.valueChanged.connect(lambda v: on_change(spec.key, int(v)))
            layout.addWidget(self.control)
        if spec.desc:
            layout.addWidget(_label(tr(spec.desc), "fieldDesc", wrap=True))

    def _slider_value(self, index: int) -> float:
        spec = self.spec
        return round(spec.minimum + index * spec.step, 2)

    def show_value(self, values: dict) -> None:
        spec, control = self.spec, self.control
        control.blockSignals(True)
        try:
            if spec.kind == "toggle":
                control.setChecked(bool(values.get(spec.key)))
            elif spec.kind == "segment":
                control.set_value(values.get(spec.key))
            elif spec.kind == "ratio":
                current = ms.ratio_value(values, spec.key)
                control.set_value(current)
                self.value_label.setText(tr("set_off") if current == 0 else f"{current}x")
            elif spec.kind == "slider":
                value = float(values.get(spec.key, spec.minimum))
                control.setValue(round((value - spec.minimum) / spec.step))
                self.value_label.setText(_format(spec, value))
            else:
                control.setValue(int(values.get(spec.key, spec.minimum)))
        finally:
            control.blockSignals(False)


class _Section(QFrame):
    def __init__(self, section: ms.Section, on_change: Callable[[str, Any], None]) -> None:
        super().__init__()
        self.section = section
        self.setObjectName("section")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(14)
        title = QHBoxLayout()
        dot = QLabel()
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(f"background: {theme.GRADIENT}; border-radius: 5px;")
        title.addWidget(dot)
        title.addWidget(_label(tr(section.key), "sectionTitle"))
        title.addStretch(1)
        layout.addLayout(title)
        self.rows = [_FieldRow(spec, on_change) for spec in section.fields]
        for row in self.rows:
            layout.addWidget(row)


class SettingsPanel(QFrame):
    """Expandable per-game MAKO settings, applied to the game's own profile."""

    apply_requested = pyqtSignal(int, dict)
    pending_changed = pyqtSignal(int, dict)

    # Sections per column for 3, 2 and 1 columns (the panel reflows with the window width).
    LAYOUTS = {
        3: (("set_sec_fg",), ("set_sec_adaptive", "set_sec_compat"),
            ("set_sec_pacing", "set_sec_scaling")),
        2: (("set_sec_fg", "set_sec_compat"), ("set_sec_adaptive", "set_sec_pacing",
                                               "set_sec_scaling")),
        1: (("set_sec_fg", "set_sec_adaptive", "set_sec_pacing", "set_sec_scaling",
             "set_sec_compat"),),
    }

    def __init__(self, app_id: int, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.app_id = app_id
        self.setObjectName("settings")
        self.base: Optional[dict] = None
        self.pending: dict = {}
        self.profile = ""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 16, 4, 4)
        outer.setSpacing(14)

        head = QHBoxLayout()
        head.addWidget(_label(tr("set_header"), "panelTitle"))
        self.profile_chip = _label("", "chip")
        self.profile_chip.setProperty("tone", "info")
        head.addWidget(self.profile_chip)
        head.addStretch(1)
        outer.addLayout(head)
        self.note = _label(tr("set_live_note"), "note", wrap=True)
        outer.addWidget(self.note)

        self.message = _label(tr("set_loading"), "note", wrap=True)
        outer.addWidget(self.message)

        self.body = QWidget()
        self.body.setObjectName("transparent")
        self.columns = QHBoxLayout(self.body)
        self.columns.setContentsMargins(0, 0, 0, 0)
        self.columns.setSpacing(14)
        self.column_layouts: list[QVBoxLayout] = []
        for _ in range(3):
            column = QVBoxLayout()
            column.setSpacing(14)
            column.addStretch(1)
            self.columns.addLayout(column, 1)
            self.column_layouts.append(column)
        self.sections: list[_Section] = [_Section(s, self._on_change) for s in ms.SECTIONS]
        self.column_count = 0
        self.set_columns(3)
        outer.addWidget(self.body)

        foot = QHBoxLayout()
        self.state_label = _label("", "saved")
        foot.addWidget(self.state_label)
        foot.addStretch(1)
        self.revert_btn = QPushButton(tr("set_revert"))
        self.revert_btn.clicked.connect(self.revert)
        self.apply_btn = QPushButton(tr("set_apply"))
        self.apply_btn.setObjectName("primary")
        self.apply_btn.setMinimumWidth(120)
        self.apply_btn.clicked.connect(
            lambda: self.apply_requested.emit(self.app_id, dict(self.pending)))
        foot.addWidget(self.revert_btn)
        foot.addWidget(self.apply_btn)
        self.footer = QWidget()
        self.footer.setObjectName("transparent")
        self.footer.setLayout(foot)
        outer.addWidget(self.footer)
        self._show_state("loading")

    def columns_for(self, width: int) -> int:
        """The most columns whose sections fit `width` at their minimum widths."""
        by_key = {section.section.key: section.minimumSizeHint().width()
                  for section in self.sections}
        spacing = self.columns.spacing()
        for count in (3, 2, 1):
            needed = sum(max(by_key[k] for k in keys) for keys in self.LAYOUTS[count])
            if needed + spacing * (count - 1) + 8 <= width or count == 1:
                return count
        return 1

    def set_columns(self, count: int) -> None:
        count = max(1, min(3, count))
        if count == self.column_count:
            return
        self.column_count = count
        by_key = {section.section.key: section for section in self.sections}
        for column in self.column_layouts:
            for section in self.sections:
                column.removeWidget(section)
        for index, keys in enumerate(self.LAYOUTS[count]):
            column = self.column_layouts[index]
            for key in keys:
                column.insertWidget(column.count() - 1, by_key[key])
        for index in range(3):
            self.columns.setStretch(index, 1 if index < count else 0)

    # ---- state ----

    def _show_state(self, state: str) -> None:
        ready = state == "ready"
        self.body.setVisible(ready)
        self.footer.setVisible(ready)
        self.note.setVisible(ready)
        self.profile_chip.setVisible(ready)
        self.message.setVisible(not ready)
        if state == "loading":
            self.message.setText(tr("set_loading"))
        elif state == "missing":
            self.message.setText(tr("set_no_profile"))

    def set_loading(self) -> None:
        self._show_state("loading")

    def set_settings(self, settings, pending: Optional[dict] = None) -> None:
        """`settings` is a service.GameSettings or None (no profile yet)."""
        if settings is None:
            self.base = None
            self._show_state("missing")
            return
        self.base = dict(settings.values)
        self.profile = settings.profile
        self.profile_chip.setText(tr("set_profile", profile=settings.profile))
        self.pending = {k: v for k, v in (pending or {}).items() if self.base.get(k) != v}
        self._show_state("ready")
        self._refresh()

    def values(self) -> dict:
        values = dict(self.base or {})
        values.update(self.pending)
        return values

    def _on_change(self, key: str, value: Any) -> None:
        if self.base is None:
            return
        for k, v in ms.changes_for(key, value).items():
            if self.base.get(k) == v and type(self.base.get(k)) is type(v):
                self.pending.pop(k, None)
            else:
                self.pending[k] = v
        self._refresh()
        self.pending_changed.emit(self.app_id, dict(self.pending))

    def revert(self) -> None:
        self.pending.clear()
        self._refresh()
        self.pending_changed.emit(self.app_id, {})

    def _refresh(self) -> None:
        values = self.values()
        for section in self.sections:
            visible = section.section.visible(values) if section.section.visible else True
            section.setVisible(visible)
            for row in section.rows:
                spec = row.spec
                row.setVisible(spec.visible(values) if spec.visible else True)
                row.setEnabled(spec.enabled(values) if spec.enabled else True)
                row.show_value(values)
        count = len(self.pending)
        self.apply_btn.setEnabled(count > 0)
        self.revert_btn.setEnabled(count > 0)
        if count:
            self.state_label.setObjectName("pending")
            self.state_label.setText(tr("set_pending", count=count))
        else:
            self.state_label.setObjectName("saved")
            self.state_label.setText(tr("set_saved"))
        repolish(self.state_label)


# ---- game card ----------------------------------------------------------------------------------

STATUS_TONES = {"st_installed": "ok", "st_injected": "warn", "st_config_only": "info",
                "st_not_installed": "idle"}


def status_key(entry) -> str:
    if entry.has_mako and entry.profile_name:
        return "st_installed"
    if entry.has_mako:
        return "st_injected"
    if entry.profile_name:
        return "st_config_only"
    return "st_not_installed"


def runtime_html(game: Optional[RunningGame]) -> str:
    if game is None:
        return f'<span style="color:{theme.token("faint")}">—</span>'
    headline, features, notes = describe(game)
    ok, warn, muted, fg = (theme.token(k) for k in ("ok", "warn", "muted", "fg"))
    color = ok if game.mako_loaded and features else (warn if game.mako_loaded else muted)
    parts = [f'<span style="color:{color};font-weight:600">{html.escape(headline)}</span>']
    for feature in features:
        mark, tone = ("✓", ok) if feature.active else ("✗", muted)
        detail = f' <span style="color:{muted}">— {html.escape(feature.detail)}</span>' \
            if feature.detail else ""
        parts.append(f'<span style="color:{tone}">{mark}</span> '
                     f'<span style="color:{fg}">{html.escape(feature.label)}</span>{detail}')
    for note in notes:
        parts.append(f'<span style="color:{warn}">⚠ {html.escape(note)}</span>')
    return "<br>".join(parts)


class GameCard(QFrame):
    expand_toggled = pyqtSignal(int, bool)

    def __init__(self, entry, thumb: Optional[QPixmap], actions: dict[str, Callable],
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.entry = entry
        self.setObjectName("card")
        self.setProperty("expanded", False)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(0)
        row = QHBoxLayout()
        row.setSpacing(16)

        cover = QLabel()
        cover.setFixedSize(THUMB_W, THUMB_H)
        if thumb is not None:
            cover.setPixmap(thumb)
        else:
            cover.setStyleSheet(f"background: {theme.token('field')}; border-radius: 10px;")
        row.addWidget(cover, 0, Qt.AlignmentFlag.AlignTop)

        info = QVBoxLayout()
        info.setSpacing(5)
        title = _label(entry.display_name, "gameTitle", wrap=True)
        tip = entry.install_dir if entry.display_name == entry.name else \
            f"{entry.name}\n{entry.install_dir}"
        title.setToolTip(tip)
        info.addWidget(title)
        chips = QHBoxLayout()
        chips.setSpacing(8)
        key = status_key(entry)
        self.status = _label(tr(key).lstrip("●○ ").strip(), "chip")
        self.status.setProperty("tone", STATUS_TONES[key])
        self.status.setToolTip(tr("launch_options_tip",
                                  options=entry.launch_options or tr("empty")))
        chips.addWidget(self.status)
        chips.addWidget(_label(f"App ID {entry.app_id}", "meta"))
        chips.addStretch(1)
        info.addLayout(chips)
        if entry.profile_name:
            processes = ", ".join(entry.profile_processes) or "—"
            info.addWidget(_label(f"{entry.profile_name} · {processes}", "meta", wrap=True))
        paths = entry.executables
        if paths:
            path = _label(paths[0] + (f"  (+{len(paths) - 1})" if len(paths) > 1 else ""),
                          "path", wrap=True)
            path.setToolTip("\n".join(paths))
            info.addWidget(path)
        info.addStretch(1)
        row.addLayout(info, 5)

        self.live = QLabel()
        self.live.setTextFormat(Qt.TextFormat.RichText)
        self.live.setWordWrap(True)
        self.live.setMinimumWidth(170)
        self.live.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self.live, 4)

        self.actions_box = QWidget()
        self.actions_box.setObjectName("transparent")
        buttons = QHBoxLayout(self.actions_box)
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(8)
        self.launch_btn = QPushButton(tr("btn_launch"))
        self.launch_btn.setToolTip(tr("btn_launch_tip"))
        self.launch_btn.clicked.connect(lambda: actions["launch"](entry))
        buttons.addWidget(self.launch_btn)
        if entry.has_mako and not entry.profile_name:
            adopt = QPushButton(tr("btn_import"))
            adopt.setObjectName("primary")
            adopt.setToolTip(tr("btn_import_tip"))
            adopt.clicked.connect(lambda: actions["install"](entry))
            buttons.addWidget(adopt)
        if entry.has_mako:
            main = QPushButton(tr("btn_remove"))
            main.setObjectName("danger")
            main.clicked.connect(lambda: actions["uninstall"](entry))
        else:
            main = QPushButton(tr("btn_install"))
            main.setObjectName("primary")
            main.clicked.connect(lambda: actions["install"](entry))
        buttons.addWidget(main)
        self.chevron = ChevronButton()
        self.chevron.setToolTip(tr("btn_settings_tip"))
        self.chevron.toggled.connect(self._toggled)
        buttons.addWidget(self.chevron)
        self.top_row = row
        row.addWidget(self.actions_box)
        outer.addLayout(row)
        # Narrow windows: the buttons move to their own row under the game details.
        self.compact_row = QHBoxLayout()
        self.compact_row.addStretch(1)
        outer.addLayout(self.compact_row)
        self.compact = False

        self.panel: Optional[SettingsPanel] = None
        self._running = False
        self.set_runtime(None)

    def wide_width(self) -> int:
        """Width the one-row layout needs (thumbnail, details, live state, buttons)."""
        live = self.live.minimumWidth() + 16 if self.live.isVisible() or self._running else 0
        return 28 + THUMB_W + 16 + 300 + live + 16 + self.actions_box.sizeHint().width()

    def set_compact(self, compact: bool) -> None:
        if compact == self.compact:
            return
        self.compact = compact
        if compact:
            self.top_row.removeWidget(self.actions_box)
            self.compact_row.addWidget(self.actions_box)
            self.compact_row.setContentsMargins(0, 10, 0, 0)
        else:
            self.compact_row.removeWidget(self.actions_box)
            self.compact_row.setContentsMargins(0, 0, 0, 0)
            self.top_row.addWidget(self.actions_box)

    def ensure_panel(self) -> SettingsPanel:
        if self.panel is None:
            self.panel = SettingsPanel(self.entry.app_id, self)
            self.panel.setVisible(False)
            self.layout().addWidget(self.panel)
        return self.panel

    def _toggled(self, checked: bool) -> None:
        self.set_expanded(checked)
        self.expand_toggled.emit(self.entry.app_id, checked)

    def set_expanded(self, expanded: bool) -> None:
        panel = self.ensure_panel()
        panel.setVisible(expanded)
        self.layout().setSpacing(14 if expanded else 0)
        if self.chevron.isChecked() != expanded:
            self.chevron.blockSignals(True)
            self.chevron.setChecked(expanded)
            self.chevron.blockSignals(False)
        self.setProperty("expanded", expanded)
        repolish(self)

    def set_runtime(self, game: Optional[RunningGame]) -> None:
        self._running = game is not None
        self.live.setVisible(game is not None)
        self.live.setText(runtime_html(game))
        self.live.setToolTip(tr("rt_pids", pids=", ".join(map(str, sorted(game.pids))))
                             if game else "")
        running = game is not None
        self.launch_btn.setEnabled(not running)
        self.launch_btn.setText(tr("btn_running") if running else tr("btn_launch"))
        self.launch_btn.setObjectName("running" if running else "")
        repolish(self.launch_btn)
