"""Render the MAKO 助手 application icon (256x256 PNG)."""
import sys

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QGuiApplication, QImage, QLinearGradient, QPainter, QPainterPath, QPen

app = QGuiApplication(sys.argv)
size = 256
image = QImage(size, size, QImage.Format.Format_ARGB32)
image.fill(Qt.GlobalColor.transparent)
p = QPainter(image)
p.setRenderHint(QPainter.RenderHint.Antialiasing)

bg = QLinearGradient(0, 0, size, size)
bg.setColorAt(0, QColor("#2f6fed"))
bg.setColorAt(1, QColor("#7b2ff7"))
path = QPainterPath()
path.addRoundedRect(QRectF(8, 8, size - 16, size - 16), 52, 52)
p.fillPath(path, bg)

# Two "frames" with a generated frame between them: frame generation.
pen = QPen(QColor(255, 255, 255, 235), 10)
pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
p.setPen(pen)
p.drawRoundedRect(QRectF(44, 64, 70, 70), 12, 12)
p.drawRoundedRect(QRectF(142, 64, 70, 70), 12, 12)
p.setPen(QPen(QColor(255, 255, 255, 150), 8, Qt.PenStyle.DotLine))
p.drawRoundedRect(QRectF(93, 76, 70, 70), 12, 12)

font = QFont("Sans", 46)
font.setBold(True)
p.setFont(font)
p.setPen(QColor("white"))
p.drawText(QRectF(0, 150, size, 80), Qt.AlignmentFlag.AlignCenter, "MAKO")
p.end()
image.save(sys.argv[1])
