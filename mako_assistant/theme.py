"""Visual system for MAKO Assistant, in a Liquid Glass style.

Near-black ground lit by soft teal / blue / coral glows, glass panels with
hairline borders, and a green → cyan → blue → indigo → violet gradient for every
"selected" or primary state. Colours are tokens; `stylesheet()` renders the Qt style sheet from them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QColor, QFontDatabase, QGuiApplication, QPainter, QPainterPath, QPixmap, QRadialGradient,
)

TEAL, CORAL, PURPLE, BLUE = "#27d4b3", "#f86461", "#946eff", "#469ef6"

PALETTES: dict[str, dict[str, str]] = {
    "dark": {
        "bg": "#0a0a0c", "fg": "#f5f5f5", "muted": "rgba(245,245,245,0.56)",
        "faint": "rgba(245,245,245,0.36)", "panel": "rgba(255,255,255,0.035)",
        "panel_solid": "#131317", "panel2": "rgba(255,255,255,0.05)",
        "field": "rgba(255,255,255,0.06)", "field_hover": "rgba(255,255,255,0.09)",
        "border": "rgba(255,255,255,0.08)", "border_hover": "rgba(255,255,255,0.20)",
        "track": "rgba(255,255,255,0.14)", "popover": "#1a1a20",
        "ok": TEAL, "ok_bg": "rgba(39,212,179,0.13)", "warn": "#f2c14e",
        "warn_bg": "rgba(242,193,78,0.13)", "info": BLUE, "info_bg": "rgba(70,158,246,0.14)",
        "danger": "#ff8a87", "danger_bg": "rgba(248,100,97,0.12)", "idle_bg": "rgba(255,255,255,0.06)",
        "log_bg": "rgba(0,0,0,0.35)", "glow": "0.20",
    },
    "light": {
        "bg": "#eef0f3", "fg": "#15171c", "muted": "rgba(21,23,28,0.60)",
        "faint": "rgba(21,23,28,0.40)", "panel": "rgba(255,255,255,0.72)",
        "panel_solid": "#ffffff", "panel2": "rgba(255,255,255,0.85)",
        "field": "rgba(21,23,28,0.05)", "field_hover": "rgba(21,23,28,0.08)",
        "border": "rgba(21,23,28,0.09)", "border_hover": "rgba(21,23,28,0.22)",
        "track": "rgba(21,23,28,0.14)", "popover": "#ffffff",
        "ok": "#0f9e84", "ok_bg": "rgba(15,158,132,0.12)", "warn": "#a76d00",
        "warn_bg": "rgba(242,193,78,0.22)", "info": "#2b74d0", "info_bg": "rgba(70,158,246,0.14)",
        "danger": "#d2423f", "danger_bg": "rgba(248,100,97,0.12)", "idle_bg": "rgba(21,23,28,0.06)",
        "log_bg": "rgba(255,255,255,0.6)", "glow": "0.16",
    },
}

DISPLAY = '"Onest SemiBold", "Onest", "Noto Sans CJK TC", "Noto Sans CJK SC", sans-serif'
DISPLAY_BOLD = '"Onest", "Onest SemiBold", "Noto Sans CJK TC", "Noto Sans CJK SC", sans-serif'
BODY = '"Inter", "Noto Sans CJK TC", "Noto Sans CJK SC", "Noto Sans", sans-serif'
BODY_MEDIUM = '"Inter Medium", "Inter", "Noto Sans CJK TC", "Noto Sans CJK SC", sans-serif'
BODY_SEMIBOLD = '"Inter SemiBold", "Inter", "Noto Sans CJK TC", "Noto Sans CJK SC", sans-serif'
MONO = '"JetBrains Mono", "DejaVu Sans Mono", "Noto Sans Mono", monospace'

# Buttons, switches and selected segments: green → cyan → blue → indigo → violet.
BUTTON_STOPS = (("#22c98a", 0.0), ("#1fb8d8", 0.25), ("#3b82f6", 0.5), ("#5b5ce2", 0.75),
                ("#9b5cf0", 1.0))
BUTTON_STOPS_HOVER = (("#3dd89c", 0.0), ("#3cc8e4", 0.25), ("#5795f8", 0.5), ("#7172ea", 0.75),
                      ("#ad74f4", 1.0))


def _qss_gradient(stops) -> str:
    return ("qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            + ", ".join(f"stop:{at} {color}" for color, at in stops) + ")")


def button_gradient(x0: float, x1: float, y: float = 0.0):
    """The button gradient as a QLinearGradient for custom-painted widgets."""
    from PyQt6.QtGui import QLinearGradient
    grad = QLinearGradient(x0, y, x1, y)
    for color, at in BUTTON_STOPS:
        grad.setColorAt(at, QColor(color))
    return grad


GRADIENT = _qss_gradient(BUTTON_STOPS)
GRADIENT_HOVER = _qss_gradient(BUTTON_STOPS_HOVER)
SLIDER_FILL = f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {TEAL}, stop:1 {PURPLE})"

_mode = "dark"          # resolved: dark | light
_fonts_loaded = False


def load_fonts() -> None:
    global _fonts_loaded
    if _fonts_loaded:
        return
    for path in sorted((Path(__file__).parent / "assets" / "fonts").glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(path))
    _fonts_loaded = True


def resolve(choice: str) -> str:
    """auto → the desktop's colour scheme (dark when unknown)."""
    if choice in ("dark", "light"):
        return choice
    app = QGuiApplication.instance()
    try:
        scheme = app.styleHints().colorScheme() if app else None
        if scheme == Qt.ColorScheme.Light:
            return "light"
    except AttributeError:  # Qt < 6.5
        pass
    return "dark"


def set_mode(mode: str) -> None:
    global _mode
    _mode = mode if mode in PALETTES else "dark"


def mode() -> str:
    return _mode


def token(name: str) -> str:
    return PALETTES[_mode][name]


def qcolor(name: str) -> QColor:
    value = token(name)
    if value.startswith("rgba("):
        r, g, b, a = (float(x) for x in value[5:-1].split(","))
        return QColor(int(r), int(g), int(b), int(round(a * 255)))
    return QColor(value)


def paint_backdrop(painter: QPainter, rect: QRectF) -> None:
    """Base colour plus soft teal / blue / coral glows."""
    painter.fillRect(rect, qcolor("bg"))
    strength = float(token("glow"))
    w, h = rect.width(), rect.height()
    for (fx, fy, radius, color) in ((0.18, 0.28, 0.55, TEAL), (0.88, 0.30, 0.50, BLUE),
                                    (0.55, 1.02, 0.55, CORAL)):
        center = QPointF(rect.left() + fx * w, rect.top() + fy * h)
        gradient = QRadialGradient(center, max(w, h) * radius)
        glow = QColor(color)
        glow.setAlphaF(strength)
        gradient.setColorAt(0.0, glow)
        glow.setAlphaF(0.0)
        gradient.setColorAt(1.0, glow)
        painter.fillRect(rect, gradient)


def rounded(pixmap: QPixmap, radius: float) -> QPixmap:
    """A copy of `pixmap` with rounded corners (thumbnails)."""
    out = QPixmap(pixmap.size())
    out.setDevicePixelRatio(pixmap.devicePixelRatio())
    out.fill(Qt.GlobalColor.transparent)
    painter = QPainter(out)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    size = pixmap.deviceIndependentSize()
    path.addRoundedRect(QRectF(0, 0, size.width(), size.height()), radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, pixmap)
    painter.end()
    return out


def stylesheet(palette: Optional[dict[str, str]] = None) -> str:
    p = palette or PALETTES[_mode]
    return f"""
* {{ font-family: {BODY}; font-size: 13px; color: {p['fg']}; }}
QMainWindow, QDialog, QMessageBox {{ background: {p['bg']}; }}
QWidget#transparent, QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; }}
QToolTip {{ background: {p['popover']}; color: {p['fg']}; border: 1px solid {p['border_hover']};
    border-radius: 8px; padding: 6px 8px; }}

QLabel#wordmark {{ font-family: {DISPLAY_BOLD}; font-size: 20px; }}
QLabel#tagline, QLabel#muted, QLabel#footer {{ color: {p['muted']}; }}
QLabel#footer {{ font-size: 11px; }}
QLabel#gameTitle {{ font-family: {DISPLAY}; font-size: 16px; }}
QLabel#meta {{ color: {p['muted']}; font-size: 12px; }}
QLabel#path {{ color: {p['faint']}; font-size: 11px; font-family: {MONO}; }}
QLabel#sectionTitle {{ font-family: {DISPLAY}; font-size: 14px; }}
QLabel#panelTitle {{ font-family: {DISPLAY}; font-size: 15px; }}
QLabel#fieldLabel {{ font-family: {BODY_MEDIUM}; font-size: 13px; }}
QLabel#fieldValue {{ color: {p['muted']}; font-family: {BODY_MEDIUM}; font-size: 12px; }}
QLabel#fieldDesc {{ color: {p['muted']}; font-size: 12px; }}
QLabel#note {{ color: {p['muted']}; font-size: 12px; }}
QLabel#pending {{ color: {p['warn']}; font-family: {BODY_MEDIUM}; font-size: 12px; }}
QLabel#saved {{ color: {p['ok']}; font-family: {BODY_MEDIUM}; font-size: 12px; }}
QLabel#empty {{ color: {p['muted']}; font-size: 14px; padding: 40px; }}

QLabel#pill {{ background: {p['panel2']}; border: 1px solid {p['border']}; border-radius: 16px;
    padding: 0 14px; font-family: {BODY_MEDIUM}; font-size: 12px; }}
QLabel#chip {{ border-radius: 10px; padding: 3px 10px; font-family: {BODY_MEDIUM}; font-size: 12px; }}
QLabel#chip[tone="ok"] {{ color: {p['ok']}; background: {p['ok_bg']}; }}
QLabel#chip[tone="warn"] {{ color: {p['warn']}; background: {p['warn_bg']}; }}
QLabel#chip[tone="info"] {{ color: {p['info']}; background: {p['info_bg']}; }}
QLabel#chip[tone="idle"] {{ color: {p['muted']}; background: {p['idle_bg']}; }}
QLabel#restart {{ color: {p['warn']}; background: {p['warn_bg']}; border-radius: 8px;
    padding: 1px 7px; font-size: 11px; font-family: {BODY_MEDIUM}; }}

QFrame#card {{ background: {p['panel']}; border: 1px solid {p['border']}; border-radius: 16px; }}
QFrame#card[expanded="true"] {{ border-color: {p['border_hover']}; }}
QFrame#settings {{ background: transparent; border: none; border-top: 1px solid {p['border']};
    border-radius: 0; }}
QFrame#section {{ background: {p['panel2']}; border: 1px solid {p['border']}; border-radius: 14px; }}
QFrame#topbar, QFrame#toolbar {{ background: transparent; }}
QFrame#drawer {{ background: {p['panel']}; border: 1px solid {p['border']}; border-radius: 14px; }}
QFrame#hline {{ background: {p['border']}; max-height: 1px; min-height: 1px; border: none; }}

QPushButton {{ background: {p['field']}; border: 1px solid {p['border']}; border-radius: 17px;
    padding: 7px 16px; font-family: {BODY_MEDIUM}; min-height: 20px; }}
QPushButton:hover {{ background: {p['field_hover']}; border-color: {p['border_hover']}; }}
QPushButton:pressed {{ background: {p['border']}; }}
QPushButton:disabled {{ color: {p['faint']}; background: {p['field']}; border-color: {p['border']}; }}
QPushButton:focus {{ border-color: {p['border_hover']}; }}
QPushButton#primary {{ background: {GRADIENT}; border: none; color: white; font-family: {BODY_SEMIBOLD}; }}
QPushButton#primary:hover {{ background: {GRADIENT_HOVER}; }}
QPushButton#primary:disabled {{ background: {p['field']}; color: {p['faint']}; }}
QPushButton#danger {{ color: {p['danger']}; background: {p['danger_bg']}; border-color: transparent; }}
QPushButton#danger:hover {{ border-color: {p['danger']}; }}
QPushButton#running {{ color: {p['ok']}; background: {p['ok_bg']}; border-color: transparent; }}
QPushButton#running:disabled {{ color: {p['ok']}; background: {p['ok_bg']}; }}
QPushButton#chevron {{ border-radius: 18px; padding: 0; min-width: 36px; max-width: 36px;
    min-height: 36px; max-height: 36px; font-size: 15px; }}
QPushButton#chevron:checked {{ background: {GRADIENT}; border: none; color: white; }}
QPushButton#link {{ background: transparent; border: none; color: {p['muted']}; padding: 4px 6px; }}
QPushButton#link:hover {{ color: {p['fg']}; }}

QFrame#segment {{ background: {p['field']}; border: 1px solid {p['border']}; border-radius: 17px; }}
QPushButton#seg {{ background: transparent; border: none; border-radius: 14px; padding: 5px 10px;
    color: {p['muted']}; font-family: {BODY_MEDIUM}; font-size: 12px; min-height: 18px; }}
QPushButton#seg:hover {{ color: {p['fg']}; }}
QPushButton#seg:checked {{ background: {GRADIENT}; color: white; }}
QPushButton#seg:disabled {{ color: {p['faint']}; }}
QPushButton#seg:checked:disabled {{ background: {p['track']}; color: {p['muted']}; }}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{ background: {p['field']}; border: 1px solid {p['border']};
    border-radius: 17px; padding: 7px 14px; selection-background-color: {BLUE}; min-height: 20px; }}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover {{ border-color: {p['border_hover']}; }}
QLineEdit:focus, QSpinBox:focus {{ border-color: {TEAL}; }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox QAbstractItemView {{ background: {p['popover']}; border: 1px solid {p['border_hover']};
    border-radius: 10px; padding: 4px; selection-background-color: {p['field_hover']};
    selection-color: {p['fg']}; outline: none; }}
QSpinBox {{ padding-right: 6px; }}
QSpinBox::up-button, QSpinBox::down-button {{ width: 0; border: none; }}
QSpinBox:disabled, QLineEdit:disabled, QComboBox:disabled {{ color: {p['faint']}; }}

QSlider::groove:horizontal {{ height: 4px; background: {p['track']}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {SLIDER_FILL}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: white; border: 3px solid {BLUE}; width: 12px; height: 12px;
    margin: -7px 0; border-radius: 9px; }}
QSlider::sub-page:horizontal:disabled {{ background: {p['track']}; }}
QSlider::handle:horizontal:disabled {{ border-color: {p['track']}; }}

QCheckBox {{ spacing: 8px; }}
QPlainTextEdit {{ background: {p['log_bg']}; border: none; border-radius: 10px; padding: 6px;
    font-family: {MONO}; font-size: 12px; color: {p['muted']}; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 4px 2px; }}
QScrollBar::handle:vertical {{ background: {p['track']}; border-radius: 3px; min-height: 40px; }}
QScrollBar::handle:vertical:hover {{ background: {p['border_hover']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QStatusBar {{ background: transparent; color: {p['muted']}; }}
QMessageBox QLabel {{ font-size: 13px; }}
"""
