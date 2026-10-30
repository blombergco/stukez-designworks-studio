"""The navigation rail: wordmark, hand-drawn page icons, and a racing stripe along the bottom."""
from PySide6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QToolButton, QWidget

from . import __channel__
from .logo import draw_mark
from .render import chamfer_path
from . import theme as th
from .theme import body_font, head_font

RAIL_W = 96
LOGO_H = 132


def _poly(*pts):
    return QPolygonF([QPointF(x, y) for x, y in pts])


def draw_icon(p, key, line, accent):
    """Page icons in a 28 x 28 box: drawn from lines, one red accent each."""
    p.setBrush(Qt.NoBrush)
    pen = QPen(line, 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    if key == "projects":        # four swatches
        for i, (x, y) in enumerate(((3, 3), (16, 3), (3, 16), (16, 16))):
            r = QRectF(x, y, 9, 9)
            if i == 1:
                p.setPen(Qt.NoPen)
                p.setBrush(accent)
                p.drawPath(chamfer_path(r, 3))
                p.setBrush(Qt.NoBrush)
                p.setPen(pen)
            else:
                p.drawPath(chamfer_path(r, 3))
    elif key == "new":           # a cut plate with a plus
        p.drawPath(chamfer_path(QRectF(3, 3, 22, 22), 7))
        p.setPen(QPen(accent, 2.2, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(14, 9), QPointF(14, 19))
        p.drawLine(QPointF(9, 14), QPointF(19, 14))
    elif key == "cars":          # a coupe from the side
        path = QPainterPath()
        path.moveTo(2.5, 19)
        path.lineTo(3, 15.5)
        path.cubicTo(3.5, 14, 6, 13.5, 8, 13)
        path.lineTo(11, 9)
        path.cubicTo(13, 7.6, 19, 7.6, 21.5, 11)
        path.lineTo(25, 14)
        path.lineTo(25.5, 19)
        p.drawPath(path)
        p.drawLine(QPointF(2.5, 19), QPointF(5, 19))
        p.drawLine(QPointF(11.5, 19), QPointF(16.5, 19))
        p.drawLine(QPointF(23, 19), QPointF(25.5, 19))
        p.setPen(QPen(accent, 2.0))
        p.drawEllipse(QPointF(8.2, 19.2), 2.8, 2.8)
        p.drawEllipse(QPointF(19.8, 19.2), 2.8, 2.8)
    elif key == "prompts":       # lines of text with a cut
        p.drawLine(QPointF(4, 7), QPointF(24, 7))
        p.drawLine(QPointF(4, 14), QPointF(17, 14))
        p.drawLine(QPointF(4, 21), QPointF(21, 21))
        p.setPen(QPen(accent, 2.4, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(22, 11), QPointF(25, 17))
    elif key == "sponsors":      # a cut badge with a bar
        p.drawPath(chamfer_path(QRectF(3, 5, 22, 18), 7))
        p.setPen(QPen(accent, 2.4, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(9, 14), QPointF(19, 14))
        p.setPen(pen)
        p.drawLine(QPointF(9, 18.5), QPointF(15, 18.5))
    elif key == "workshop":      # two sliders
        p.drawLine(QPointF(3, 9), QPointF(25, 9))
        p.drawLine(QPointF(3, 19), QPointF(25, 19))
        p.setPen(Qt.NoPen)
        p.setBrush(accent)
        p.drawPath(chamfer_path(QRectF(8, 4.5, 8, 9), 3))
        p.setBrush(QColor(line))
        p.drawPath(chamfer_path(QRectF(14, 14.5, 8, 9), 3))
    elif key == "howto":         # a cut plate with a question mark
        p.drawPath(chamfer_path(QRectF(3, 3, 22, 22), 7))
        q = QPainterPath()
        q.moveTo(10.5, 11.5)
        q.cubicTo(10.5, 6.5, 18, 6.5, 17.5, 11)
        q.cubicTo(17.3, 13.8, 14, 13.8, 14, 17)
        p.setPen(QPen(accent, 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPath(q)
        p.drawPoint(QPointF(14, 20.5))
    elif key == "guides":        # an open book
        p.drawPolyline(_poly((14, 8), (6, 5.5), (3.5, 5.5), (3.5, 21.5), (6, 21.5), (14, 24)))
        p.drawPolyline(_poly((14, 8), (22, 5.5), (24.5, 5.5), (24.5, 21.5), (22, 21.5), (14, 24)))
        p.setPen(QPen(accent, 2.0, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(14, 8), QPointF(14, 24))


class NavButton(QToolButton):
    def __init__(self, text, icon_key, parent=None):
        super().__init__(parent)
        self.setObjectName("nav")
        self.setText(text)
        self.icon_key = icon_key
        self.setCheckable(True)
        self.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.setFixedSize(RAIL_W, 76)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        on, hot = self.isChecked(), self.underMouse()
        r = QRectF(self.rect()).adjusted(0, 0, -6, 0)
        if on or hot:
            c = 16
            g = QLinearGradient(r.topLeft(), r.topRight())
            if on:
                g.setColorAt(0, th.accent(th.NAV_ALPHA))
                g.setColorAt(1, th.accent(28))
            else:
                g.setColorAt(0, th.accent(46))
                g.setColorAt(1, th.accent(6))
            p.setPen(Qt.NoPen)
            p.setBrush(g)
            p.drawPath(chamfer_path(r, c))
        if on:
            p.setBrush(QColor("#ffffff"))
            p.drawRect(QRectF(0, 6, 3, r.height() - 12))
        p.save()
        p.translate(r.center().x() - 14 - 2, 11)
        draw_icon(p, self.icon_key, QColor("#ffffff") if on else (QColor("#f0d8dc") if hot else QColor("#b9a9ac")),
                  QColor(th.EMBER) if on else QColor(th.RED))
        p.restore()
        p.setFont(head_font(15))
        p.setPen(QColor("#ffffff") if on else (QColor("#f0d8dc") if hot else QColor(th.MUTED)))
        p.drawText(QRectF(0, 46, r.width() - 2, 24), Qt.AlignHCenter | Qt.AlignTop, self.text())
        p.end()


class Rail(QWidget):
    """The left rail: wordmark on top, page buttons, and the livery stripe at the bottom."""

    def __init__(self):
        super().__init__()
        self.setObjectName("side")
        self.setFixedWidth(RAIL_W)
        self.setMouseTracking(True)
        self._shine = None
        self._anim = QVariantAnimation(self, startValue=0.0, endValue=1.0, duration=900)
        self._anim.setEasingCurve(QEasingCurve.InOutSine)
        self._anim.valueChanged.connect(self._shone)
        self._anim.finished.connect(lambda: self._shone(None))

    def _shone(self, v):
        self._shine = v
        self.update(0, 0, self.width(), LOGO_H)

    def shine(self):
        """One band of light across the mark (also when the pointer comes over it)."""
        if th.ANIMATE and self._anim.state() != QVariantAnimation.Running:
            self._anim.start()

    def mouseMoveEvent(self, e):
        if e.position().y() < LOGO_H:
            self.shine()
        super().mouseMoveEvent(e)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        g = QLinearGradient(0, 0, 0, h)
        g.setColorAt(0, QColor(th.BG_DEEP))
        g.setColorAt(.6, QColor(th.RAIL_MID))
        g.setColorAt(1, QColor(th.RAIL_END))
        p.fillRect(self.rect(), g)
        # the racing stripe: three bands at 45 degrees across the foot of the rail
        for dy, t, col in ((0, 26, th.accent(230)), (-40, 5, QColor(255, 255, 255, 235)), (-52, 12, QColor(th.RED_DARK))):
            y0 = h - 30 + dy
            p.setPen(Qt.NoPen)
            p.setBrush(col)
            p.drawPolygon(_poly((0, y0 + 0), (w, y0 - w), (w, y0 - w + t), (0, y0 + t)))
        p.setPen(QPen(QColor(th.BORDER), 1))
        p.drawLine(w - 1, 0, w - 1, h)
        # the mark: the S and Z plate, then the name
        cx = w / 2 - 1
        draw_mark(p, QRectF(cx - 24, 14, 48, 48), shine=self._shine)
        p.setFont(head_font(21))
        p.setPen(QColor(th.INK))
        p.drawText(QRectF(0, 66, w - 2, 26), Qt.AlignHCenter | Qt.AlignVCenter, "StukeZ")
        p.setFont(body_font(11))
        p.setPen(QColor(th.MUTED))
        p.drawText(QRectF(0, 90, w - 2, 16), Qt.AlignHCenter | Qt.AlignVCenter, "Designworks")
        if __channel__:
            tag = QRectF(cx - 17, 110, 36, 15)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(th.RED))
            p.drawPath(chamfer_path(tag, 5))
            p.setFont(head_font(13))
            p.setPen(QColor(th.ON_ACCENT))
            p.drawText(tag, Qt.AlignCenter, __channel__)
        p.end()
