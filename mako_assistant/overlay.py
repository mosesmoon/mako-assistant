"""On-screen watermark: the live MAKO features of a game that just started.

Runs as its own short-lived process (``python -m mako_assistant.overlay JSON``)
so it can use the X11 (XWayland) platform even when the main window is a
native Wayland client: Wayland gives ordinary clients no way to stack above
a fullscreen game, while an X11 override-redirect window is always kept on
top. The window never takes focus and ignores input, so it cannot steal
keyboard or mouse from the game.

Payload: {"title", "headline", "color", "lines": [{"label", "detail",
"active"}], "notes": [...], "seconds"}
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

MARGIN = 28
FADE_MS = 600


def show(payload: dict) -> None:
    """Start the overlay process; returns immediately."""
    env = dict(os.environ)
    if env.get("DISPLAY"):
        env["QT_QPA_PLATFORM"] = "xcb"
    subprocess.Popen(
        [sys.executable, "-m", "mako_assistant.overlay", json.dumps(payload, ensure_ascii=False)],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
    )


def _html(payload: dict) -> str:
    from html import escape

    color = payload.get("color") or "#4cd384"
    parts = [
        f'<div style="font-size:13px; color:#9aa3b2; letter-spacing:1px;">MAKO</div>',
        f'<div style="font-size:17px; font-weight:700; color:#ffffff;">'
        f'{escape(payload.get("title", ""))}</div>',
        f'<div style="font-size:14px; font-weight:600; color:{color}; margin-top:4px;">'
        f'{escape(payload.get("headline", ""))}</div>',
    ]
    for line in payload.get("lines", []):
        mark, tone = ("✓", "#7fe0a6") if line.get("active") else ("✗", "#8b93a1")
        detail = line.get("detail")
        detail_html = (f'<span style="color:#d5dae3;"> — {escape(detail)}</span>'
                       if detail else "")
        parts.append(f'<div style="font-size:14px; margin-top:3px;">'
                     f'<span style="color:{tone};">{mark} {escape(line.get("label", ""))}</span>'
                     f'{detail_html}</div>')
    for note in payload.get("notes", []):
        parts.append(f'<div style="font-size:13px; color:#f2c14e; margin-top:3px;">'
                     f'⚠ {escape(note)}</div>')
    return "".join(parts)


def main(argv: list[str]) -> int:
    from PyQt6.QtCore import QPropertyAnimation, Qt, QTimer
    from PyQt6.QtGui import QGuiApplication
    from PyQt6.QtWidgets import QApplication, QFrame, QLabel, QVBoxLayout, QWidget

    payload = json.loads(argv[1]) if len(argv) > 1 else {}
    app = QApplication(argv[:1])
    app.setApplicationName("MAKO Assistant Overlay")

    window = QWidget()
    flags = (Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint
             | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus
             | Qt.WindowType.WindowTransparentForInput)
    if QGuiApplication.platformName() == "xcb":
        flags |= Qt.WindowType.X11BypassWindowManagerHint
    window.setWindowFlags(flags)
    window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    window.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    window.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    card = QFrame(window)
    card.setObjectName("card")  # QLabel is a QFrame too: scope the border to the card
    card.setStyleSheet("#card { background: rgba(16, 18, 24, 215); border-radius: 14px;"
                       " border: 1px solid rgba(120, 140, 180, 90); }")
    inner = QVBoxLayout(card)
    inner.setContentsMargins(18, 14, 18, 14)
    label = QLabel(_html(payload))
    label.setTextFormat(Qt.TextFormat.RichText)
    label.setStyleSheet("color: #e6e8ee; background: transparent; border: none;")
    label.setMaximumWidth(520)
    label.setWordWrap(True)
    inner.addWidget(label)
    outer = QVBoxLayout(window)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.addWidget(card)
    window.adjustSize()

    screen = QGuiApplication.primaryScreen().availableGeometry()
    window.move(screen.right() - window.width() - MARGIN,
                screen.bottom() - window.height() - MARGIN)

    window.setWindowOpacity(0.0)
    window.show()
    fade_in = QPropertyAnimation(window, b"windowOpacity")
    fade_in.setDuration(FADE_MS)
    fade_in.setEndValue(0.95)
    fade_in.start()

    fade_out = QPropertyAnimation(window, b"windowOpacity")
    fade_out.setDuration(FADE_MS)
    fade_out.setEndValue(0.0)
    fade_out.finished.connect(app.quit)
    seconds = float(payload.get("seconds", 10))
    QTimer.singleShot(int(seconds * 1000), fade_out.start)
    QTimer.singleShot(int(seconds * 1000) + FADE_MS + 2000, app.quit)  # safety net
    return app.exec()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
