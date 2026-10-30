"""The StukeZ mark: an angular S and Z on a plate that is cut at 45 degrees, like the livery.

The plate has two tones split along the same 45 degree line as the gradient on the car (the rear half darker, the front half
lighter), the letters lean forward, and the corners of the plate are cut. All colours come from the theme in use, so the mark
is red in the red theme, blue in the blue one and yellow in the carbon one.
"""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath, QPainterPathStroker, QPen, QPixmap, QPolygonF, QTransform

from . import theme as th

# the letters on a 100 x 100 plate, 11 units thick: the S is a stroked centre line with square ends, the Z one outline
_S_LINE = [(46, 27.5), (17.5, 27.5), (17.5, 50), (40.5, 50), (40.5, 72.5), (12, 72.5)]
_Z_OUT = [(54, 22), (88, 22), (88, 33), (68.5, 67), (88, 67), (88, 78), (54, 78), (54, 67), (73.5, 33), (54, 33)]
STROKE = 11.0
LEAN = -.2           # how far the letters lean forward (shear)
CUT = 24.0           # the cut corners of the plate, on the 100 unit plate


def plate_path(r, cut):
    """The plate: top right and bottom left corners cut at 45 degrees."""
    return QPolygonF([QPointF(r.left(), r.top()), QPointF(r.right() - cut, r.top()), QPointF(r.right(), r.top() + cut),
                      QPointF(r.right(), r.bottom()), QPointF(r.left() + cut, r.bottom()), QPointF(r.left(), r.bottom() - cut)])


def letters_path():
    line = QPainterPath(QPointF(*_S_LINE[0]))
    for x, y in _S_LINE[1:]:
        line.lineTo(x, y)
    stroker = QPainterPathStroker()
    stroker.setWidth(STROKE)
    stroker.setCapStyle(Qt.FlatCap)
    stroker.setJoinStyle(Qt.MiterJoin)
    path = stroker.createStroke(line)
    z = QPainterPath()
    z.addPolygon(QPolygonF([QPointF(x, y) for x, y in _Z_OUT]))
    z.closeSubpath()
    path = path.united(z)
    t = QTransform()
    t.translate(50, 50)
    t.shear(LEAN, 0)
    t.translate(-50, -50)
    return t.map(path)


def draw_mark(p, rect, plate=True, shine=None):
    """The mark fitted into `rect` (a square is best). plate=False draws the letters alone, in the accent colour.

    `shine` (0..1) sweeps one band of light across the plate, like the sheen on the buttons."""
    side = min(rect.width(), rect.height())
    r = QRectF(rect.center().x() - side / 2, rect.center().y() - side / 2, side, side)
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    p.translate(r.topLeft())
    p.scale(side / 100.0, side / 100.0)
    full = QRectF(0, 0, 100, 100)
    if plate:
        clip = QPainterPath()
        clip.addPolygon(plate_path(full, CUT))
        p.setClipPath(clip)
        # two tones, split on the 45 degree line through the middle: dark behind the cut, light in front of it
        g = QLinearGradient(0, 100, 100, 0)
        g.setColorAt(0, QColor(th.RED_DARK))
        g.setColorAt(.5, QColor(th.RED))
        g.setColorAt(1, QColor(th.RED_HI))
        p.fillRect(full, g)
        p.setPen(QPen(QColor(255, 255, 255, 215), 2.2))
        p.drawLine(QPointF(-4, 104), QPointF(104, -4))
        if shine is not None and 0 < shine < 1:
            c = -30 + shine * 260           # the band lies along x + y = c and moves towards the bottom right
            sh = QLinearGradient(QPointF(c / 2 - 22, c / 2 - 22), QPointF(c / 2 + 22, c / 2 + 22))
            sh.setColorAt(0, QColor(255, 255, 255, 0))
            sh.setColorAt(.5, QColor(255, 255, 255, 170))
            sh.setColorAt(1, QColor(255, 255, 255, 0))
            p.fillRect(full, sh)
        p.setClipping(False)
        p.setPen(QPen(QColor(th.EMBER), 1.4))
        p.setBrush(Qt.NoBrush)
        p.drawPolygon(plate_path(full.adjusted(.7, .7, -.7, -.7), CUT - .7))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(th.ON_ACCENT))
        p.drawPath(letters_path())
    else:
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(th.RED))
        p.drawPath(letters_path())
    p.restore()


def mark_pixmap(size, dpr=1.0):
    pm = QPixmap(int(size * dpr), int(size * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    draw_mark(p, QRectF(0, 0, size, size))
    p.end()
    return pm


def app_icon():
    """The window and taskbar icon in the colours of the theme in use."""
    icon = QIcon()
    for s in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(mark_pixmap(s))
    return icon


def splash_pixmap(width=560, height=300):
    """The picture shown while the program starts: the mark, the name and the theme's colours."""
    pm = QPixmap(width, height)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    g = QLinearGradient(0, 0, width, height)
    g.setColorAt(0, QColor(th.BG))
    g.setColorAt(.58, QColor(th.BG_MID))
    g.setColorAt(1, QColor(th.BG_END))
    p.fillRect(pm.rect(), g)
    # racing stripes at the foot, the same three bands as the rail
    for dy, t, col in ((0, 30, th.accent(230)), (-46, 6, QColor(255, 255, 255, 235)), (-60, 14, QColor(th.RED_DARK))):
        y0 = height - 24 + dy
        p.setPen(Qt.NoPen)
        p.setBrush(col)
        p.drawPolygon(QPolygonF([QPointF(0, y0), QPointF(width, y0 - width), QPointF(width, y0 - width + t), QPointF(0, y0 + t)]))
    draw_mark(p, QRectF(48, 52, 150, 150))
    p.setPen(QColor(th.INK))
    p.setFont(th.head_font(64))
    p.drawText(QRectF(220, 62, width - 230, 76), Qt.AlignLeft | Qt.AlignVCenter, "StukeZ")
    p.setPen(QColor(th.MUTED))
    f = th.body_font(24)
    f.setLetterSpacing(QFont.AbsoluteSpacing, 3)
    p.setFont(f)
    p.drawText(QRectF(224, 134, width - 230, 34), Qt.AlignLeft | Qt.AlignVCenter, "DESIGNWORKS")
    p.setFont(th.body_font(14))
    p.drawText(QRectF(224, 176, width - 230, 24), Qt.AlignLeft | Qt.AlignVCenter, "Starting…")
    p.setPen(QPen(QColor(th.BORDER_HI), 2))
    p.setBrush(Qt.NoBrush)
    p.drawRect(pm.rect().adjusted(1, 1, -1, -1))
    p.end()
    return pm
