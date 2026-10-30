"""Painting helpers: palette cards for the grid, the livery car preview and PNG export."""
from types import SimpleNamespace

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QImage, QLinearGradient, QPainter, QPainterPath, QPen,
                           QRadialGradient)

from . import carrender
from .theme import body_font, head_font

PANEL = QColor("#130a0d")
INK = QColor("#f5f0f1")
MUTED = QColor("#a8999c")
RED = QColor("#ff2e3f")


# ---------------------------------------------------------------------- the cut
def chamfer_path(rect, c):
    """A rectangle with its top right and bottom left corners cut at 45 degrees: the slash of the livery."""
    r = QRectF(rect)
    c = max(0.0, min(c, r.width() / 2, r.height() / 2))
    path = QPainterPath()
    path.moveTo(r.left(), r.top())
    path.lineTo(r.right() - c, r.top())
    path.lineTo(r.right(), r.top() + c)
    path.lineTo(r.right(), r.bottom())
    path.lineTo(r.left() + c, r.bottom())
    path.lineTo(r.left(), r.bottom() - c)
    path.closeSubpath()
    return path


def slash_edges(p, rect, c, color=RED, width=2.0):
    """Light up the two cut edges of a chamfered shape."""
    r = QRectF(rect)
    p.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(r.right() - c, r.top()), QPointF(r.right(), r.top() + c))
    p.drawLine(QPointF(r.left(), r.bottom() - c), QPointF(r.left() + c, r.bottom()))


def _stage_fill(p, rect):
    """The garage floor behind a car: dark, a red light from above, faint 45 degree lines and a pool of light on the floor."""
    r = QRectF(rect)
    g = QLinearGradient(r.topLeft(), r.bottomLeft())
    g.setColorAt(0, QColor("#2c1318"))
    g.setColorAt(1, QColor("#0d0608"))
    p.fillRect(r, g)
    rg = QRadialGradient(QPointF(r.center().x(), r.top()), r.width() * .6)
    rg.setColorAt(0, QColor(255, 46, 63, 78))
    rg.setColorAt(1, QColor(255, 46, 63, 0))
    p.fillRect(r, rg)
    p.setPen(QPen(QColor(255, 255, 255, 9), 1))
    step = 26
    for i in range(int((r.width() + r.height()) / step) + 1):
        x = r.left() + i * step - r.height() * .5
        p.drawLine(QPointF(x, r.bottom()), QPointF(x + r.height(), r.top()))
    p.save()
    p.translate(r.center().x(), r.bottom() - r.height() * .1)
    p.scale(1, .17)
    R = r.width() * .46
    fg = QRadialGradient(QPointF(0, 0), R)
    fg.setColorAt(0, QColor(255, 255, 255, 30))
    fg.setColorAt(1, QColor(255, 255, 255, 0))
    p.fillRect(QRectF(-R, -R, 2 * R, 2 * R), fg)
    p.restore()


def draw_stage(p, rect, cut=16):
    """A cut-cornered stage for a livery preview."""
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    path = chamfer_path(rect, cut)
    p.setClipPath(path)
    _stage_fill(p, rect)
    p.setClipping(False)
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(255, 255, 255, 24), 1))
    p.drawPath(path)
    slash_edges(p, rect, cut)
    p.restore()


def pal_of(d):
    """Accept a Proj, a pk.Project or a plain dict."""
    return SimpleNamespace(**d) if isinstance(d, dict) else d


def brush(rect, value):
    """Solid colour, or a left-to-right gradient for a 2-colour value."""
    if isinstance(value, (list, tuple)):
        g = QLinearGradient(rect.topLeft(), rect.topRight())
        g.setColorAt(0, QColor(value[0]))
        g.setColorAt(1, QColor(value[1]))
        return QBrush(g)
    return QBrush(QColor(value))


def first(v):
    return v[0] if isinstance(v, (list, tuple)) else v


# ---------------------------------------------------------------------- the car
PLATE_SCALE = 0.4     # how big the sponsor plates are in previews, against their zone: small, so the car and its colours show
PREVIEW_CAR = None   # the car used for previews: the built-in car, or one from the Car Templates library


def set_preview_car(car):
    global PREVIEW_CAR
    PREVIEW_CAR = car


def draw_real_car(p, rect, d, car, view="side", plates=True, plate_scale=None):
    """The palette on a real car capture, fitted into rect; returns False when the car lacks that view."""
    dpr = p.device().devicePixelRatioF() if p.device() else 1.0
    src = car.view_info(view)["size"] if view in car.views() else None
    if not src:
        return False
    ar = src[0] / src[1]
    w, h = min(rect.width(), rect.height() * ar), min(rect.height(), rect.width() / ar)
    img = carrender.render(car, view, pal_of(d), int(w * dpr), plates=None if plates else {},
                           plate_scale=PLATE_SCALE if plate_scale is None else plate_scale)
    target = QRectF(rect.center().x() - w / 2, rect.center().y() - h / 2, w, h)
    p.save()
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 60))
    p.drawEllipse(QRectF(target.x() + w * .04, target.bottom() - h * .08, w * .92, h * .12))
    p.drawImage(target, img)
    p.restore()
    return True


def draw_car(p, rect, d, view="side", plates=True, plate_scale=None):
    """The palette on the preview car (the built-in car unless another one is chosen), fitted into rect."""
    if PREVIEW_CAR is not None:
        draw_real_car(p, rect, d, PREVIEW_CAR, view, plates, plate_scale)


# ---------------------------------------------------------------------- cards
def _font(px, bold=False):
    return body_font(px, bold)


def draw_chips(p, rect, d, n=4):
    d = pal_of(d)
    vals = [d.base, d.tribal, d.sponsor_a, d.sponsor_b][:n]
    gap = 5
    w = (rect.width() - gap * (len(vals) - 1)) / len(vals)
    for i, v in enumerate(vals):
        r = QRectF(rect.x() + i * (w + gap), rect.y(), w, rect.height())
        p.setPen(QPen(QColor(255, 255, 255, 46), 1))
        p.setBrush(brush(r, v))
        p.drawPath(chamfer_path(r, min(5.0, r.height() * .45)))


def draw_plate(p, rect, text):
    """A race number plate: white, cut, the number in condensed black."""
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#f5f0f1"))
    p.drawPath(chamfer_path(rect, rect.height() * .38))
    p.setPen(QColor("#0a0608"))
    p.setFont(head_font(int(rect.height() * .72)))
    p.drawText(rect.adjusted(0, 0, -rect.height() * .1, 0), Qt.AlignCenter, text)
    p.restore()


def draw_card(p, rect, d, title, subtitle, selected=False, hover=False, number=None, plates=True):
    """Grid tile: the car on its stage with the project number, then the name, the moods and four colour tiles."""
    d = pal_of(d)
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    cut = 20
    path = chamfer_path(rect, cut)
    p.setClipPath(path)
    p.fillRect(rect, QColor("#1b0f13") if hover or selected else PANEL)
    top = QRectF(rect.x(), rect.y(), rect.width(), rect.height() * .60)
    _stage_fill(p, top)
    draw_car(p, top.adjusted(10, 12, -10, -4), d, plates=plates)
    p.setPen(INK)
    p.setFont(head_font(19))
    p.drawText(QRectF(rect.x() + 14, top.bottom() + 2, rect.width() - 28, 24), Qt.AlignLeft | Qt.AlignVCenter,
               p.fontMetrics().elidedText(title, Qt.ElideRight, int(rect.width() - 28)))
    p.setPen(MUTED)
    p.setFont(_font(12))
    p.drawText(QRectF(rect.x() + 14, top.bottom() + 26, rect.width() - 28, 16), Qt.AlignLeft | Qt.AlignVCenter,
               p.fontMetrics().elidedText(subtitle, Qt.ElideRight, int(rect.width() - 28)))
    draw_chips(p, QRectF(rect.x() + 14, rect.bottom() - 28, rect.width() - 28, 14), d)
    p.setClipping(False)
    if number is not None:
        draw_plate(p, QRectF(rect.x() + 12, rect.y() + 12, 44, 20), number)
    p.setBrush(Qt.NoBrush)
    if selected:
        p.setPen(QPen(RED, 2.5))
        p.drawPath(chamfer_path(rect.adjusted(1.2, 1.2, -1.2, -1.2), cut))
    else:
        p.setPen(QPen(QColor(255, 46, 63, 120) if hover else QColor(255, 255, 255, 22), 1))
        p.drawPath(chamfer_path(rect.adjusted(.5, .5, -.5, -.5), cut))
        slash_edges(p, rect.adjusted(.5, .5, -.5, -.5), cut, QColor(255, 46, 63, 230 if hover else 130), 1.6)
    p.restore()


def render_card_image(d, title, subtitle="", concept="", width=1600, plates=True):
    """A shareable palette sheet: livery, then every colour with its hex code."""
    d = pal_of(d)
    slots = [("Base", d.base), ("Tribals", d.tribal), ("Tribal outline", d.tribal_outline),
             ("Sponsor A", d.sponsor_a), ("Sponsor A outline", d.sponsor_a_outline),
             ("Sponsor B", d.sponsor_b), ("Sponsor B outline", d.sponsor_b_outline)]
    h = int(width * .70)
    img = QImage(width, h, QImage.Format_ARGB32)
    img.fill(QColor("#080506"))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    bgl = QLinearGradient(0, 0, width, h)
    bgl.setColorAt(0, QColor("#080506"))
    bgl.setColorAt(.6, QColor("#12070a"))
    bgl.setColorAt(1, QColor("#34091a"))
    p.fillRect(QRectF(0, 0, width, h), bgl)
    m = width * .04
    p.setPen(INK)
    p.setFont(head_font(int(width * .042)))
    p.drawText(QRectF(m, m * .5, width * .7, width * .06), Qt.AlignLeft | Qt.AlignVCenter, title)
    p.setPen(MUTED)
    p.setFont(_font(int(width * .0165)))
    p.drawText(QRectF(m, m * .5 + width * .06, width - 2 * m, width * .03), Qt.AlignLeft | Qt.AlignVCenter,
               p.fontMetrics().elidedText(concept or subtitle, Qt.ElideRight, int(width - 2 * m)))
    p.setFont(head_font(int(width * .018)))
    p.setPen(INK)
    p.drawText(QRectF(width * .6, m * .5, width * .36, width * .04), Qt.AlignRight | Qt.AlignVCenter, "StukeZ Designworks")
    stage = QRectF(m, width * .15, width - 2 * m, h * .42)
    draw_stage(p, stage, cut=width * .02)
    draw_car(p, stage.adjusted(20, 14, -20, -10), d, plates=plates)
    gap = width * .012
    cw = (width - 2 * m - gap * 6) / 7
    y = stage.bottom() + width * .03
    for i, (label, v) in enumerate(slots):
        x = m + i * (cw + gap)
        r = QRectF(x, y, cw, h * .17)
        p.setPen(QPen(QColor(255, 255, 255, 60), 1.5))
        p.setBrush(brush(r, v))
        p.drawPath(chamfer_path(r, r.height() * .2))
        p.setPen(INK)
        p.setFont(head_font(int(width * .0125)))
        p.drawText(QRectF(x, r.bottom() + 6, cw, 22), Qt.AlignLeft, p.fontMetrics().elidedText(label, Qt.ElideRight, int(cw)))
        p.setPen(MUTED)
        p.setFont(_font(int(width * .0098)))
        vals = list(v) if isinstance(v, (list, tuple)) else [v]
        for j, c in enumerate(vals):
            p.drawText(QRectF(x, r.bottom() + 6 + 22 + j * 18, cw, 18), Qt.AlignLeft, c)
    p.end()
    return img
