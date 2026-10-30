"""Vector wheels for the cars that come without them, drawn with QPainter in the same flat, inked style as the car pictures.

A 7-spoke wheel like the one on the reference car, a 6-spoke "TE37" and a 5-spoke "VS-KF". Everything is drawn from paths
and gradients at the size asked for, so the wheels are sharp at any size and the colour can be changed. The light comes
from the upper left; the deep wheels get their depth from shadow (a dark dish towards the lip, a shadow under every
spoke). These are drawn in the spirit of those wheels (the spoke shapes, the lip and the lugs); no logos.
"""
from math import cos, pi, radians, sin

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient

DESIGNS = {"ref7": "7-spoke (like the reference)", "te37": "Volk TE37 (6 spokes)", "vskf": "Work VS-KF (5 spokes)"}
# colour name -> (shade, light) of the wheel face
COLOURS = {"white": ("#b3a2c2", "#f7f2f8"), "bronze": ("#6d4f2f", "#c8a064"), "black": ("#141417", "#55555d"),
           "silver": ("#868b95", "#eceff5"), "gunmetal": ("#33353c", "#8f93a0"), "gold": ("#9a7621", "#f3d680")}
CALIPER = {"ref7": "#a63fb0", "te37": "#c8102e", "vskf": "#c8102e"}
LIP = ("#868c97", "#f3f5f9")          # the polished lip of the VS-KF
INK = QColor("#141114")


def _pt(cx, cy, r, a):
    return QPointF(cx + r * cos(a), cy + r * sin(a))


def _poly(points):
    path = QPainterPath()
    path.moveTo(points[0])
    for q in points[1:]:
        path.lineTo(q)
    path.closeSubpath()
    return path


def _straight_spoke(cx, cy, r, a, prof):
    """A straight spoke given as (distance from the centre, half width) pairs, both as fractions of the tyre radius."""
    d = QPointF(cos(a), sin(a))
    n = QPointF(-sin(a), cos(a))

    def at(rho, half):
        return QPointF(cx + d.x() * rho * r + n.x() * half * r, cy + d.y() * rho * r + n.y() * half * r)
    left = [at(rho, -h) for rho, h in prof]
    right = [at(rho, h) for rho, h in reversed(prof)]
    return _poly(left + right)


def _spoke_vskf(cx, cy, r, a0):
    """A broad, swept blade: narrow at the hub, flaring out to the rim."""
    n = 16
    left, right = [], []
    for i in range(n + 1):
        t = i / n
        rho = .13 + t * .67
        sweep = radians(11) * t ** 1.2
        half = radians(6.5 + 12.5 * t ** 1.45 + 1.6 * sin(t * pi))
        left.append(_pt(cx, cy, rho * r, a0 + sweep - half))
        right.append(_pt(cx, cy, rho * r, a0 + sweep + half))
    return _poly(left + right[::-1])


SPOKES = {"ref7": dict(count=7, start=-90 + 6, prof=[(.13, .050), (.40, .056), (.66, .074), (.76, .098), (.81, .118)]),
          "te37": dict(count=6, start=-90 + 14, prof=[(.13, .095), (.40, .105), (.66, .130), (.745, .158), (.80, .178)]),
          "vskf": dict(count=5, start=-90, prof=None)}


def draw_wheel(p, cx, cy, r, design="ref7", colour="white", caliper=None):
    """Draw one wheel with its tyre, centred on (cx, cy) with a tyre radius of r."""
    if design not in DESIGNS:
        return
    shade, light = (QColor(c) for c in COLOURS.get(colour, COLOURS["white"]))
    caliper = caliper or CALIPER[design]
    ink = max(1.2, r * .017)
    rim_r = r * (.82 if design == "vskf" else .80)
    centre = QPointF(cx, cy)
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    # tyre: black with a lighter sidewall ring, inked
    tyre = QRadialGradient(centre, r)
    tyre.setColorAt(.80, QColor("#0a0a0c"))
    tyre.setColorAt(.90, QColor("#26262b"))
    tyre.setColorAt(.97, QColor("#0e0e11"))
    p.setPen(QPen(INK, ink))
    p.setBrush(tyre)
    p.drawEllipse(centre, r, r)
    p.setPen(QPen(QColor(205, 205, 212, 150), max(1.0, r * .012)))      # a light edge, so the tyre shows against a black background
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(centre, r * .955, r * .955)
    # the barrel behind the spokes, darker towards the lip (a deep dish)
    barrel = QRadialGradient(centre, rim_r)
    barrel.setColorAt(0, QColor("#222228"))
    barrel.setColorAt(.7, QColor("#0e0e11"))
    barrel.setColorAt(1, QColor("#050506"))
    p.setPen(Qt.NoPen)
    p.setBrush(barrel)
    p.drawEllipse(centre, rim_r, rim_r)
    # brake disc and caliper
    disc = QRadialGradient(centre, r * .58)
    disc.setColorAt(.45, QColor("#2b2d33"))
    disc.setColorAt(.85, QColor("#70747e"))
    disc.setColorAt(1, QColor("#41444b"))
    p.setPen(QPen(INK, ink * .8))
    p.setBrush(disc)
    p.drawEllipse(centre, r * .58, r * .58)
    p.setPen(QPen(QColor("#1d1e22"), max(1.0, r * .011)))
    for i in range(32):
        a = i * 2 * pi / 32
        p.drawLine(_pt(cx, cy, r * .38, a), _pt(cx, cy, r * .55, a))
    cal = QPainterPath()
    a0, a1 = radians(190), radians(252)
    cal.moveTo(_pt(cx, cy, r * .50, a0))
    for k in range(13):
        cal.lineTo(_pt(cx, cy, r * .50, a0 + (a1 - a0) * k / 12))
    for k in range(13):
        cal.lineTo(_pt(cx, cy, r * .665, a1 - (a1 - a0) * k / 12))
    cal.closeSubpath()
    p.setPen(QPen(INK, ink))
    p.setBrush(QColor(caliper))
    p.drawPath(cal)
    # the spokes: a shadow under each, then the spoke itself lit from the upper left
    spec = SPOKES[design]
    start = radians(spec["start"])
    paths = []
    for i in range(spec["count"]):
        a = start + i * 2 * pi / spec["count"]
        paths.append(_spoke_vskf(cx, cy, r, a) if design == "vskf" else _straight_spoke(cx, cy, r, a, spec["prof"]))
    clip = QPainterPath()
    clip.addEllipse(centre, rim_r, rim_r)
    p.save()
    p.setClipPath(clip)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 120))
    for path in paths:
        p.translate(r * .022, r * .032)
        p.drawPath(path)
        p.translate(-r * .022, -r * .032)
    p.restore()
    face = QLinearGradient(QPointF(cx - r * .62, cy - r * .62), QPointF(cx + r * .62, cy + r * .62))
    face.setColorAt(0, light)
    face.setColorAt(1, shade)
    p.setPen(QPen(INK, ink, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(face)
    for path in paths:
        p.drawPath(path)
    # the dish: a dark ring towards the lip and a soft shade over the lower right, so the face looks deep
    p.save()
    p.setClipPath(clip)
    dish = QRadialGradient(centre, rim_r)
    dish.setColorAt(.0, QColor(0, 0, 0, 0))
    dish.setColorAt(.55, QColor(0, 0, 0, 0))
    dish.setColorAt(1, QColor(0, 0, 0, 120 if design != "ref7" else 70))
    p.setPen(Qt.NoPen)
    p.setBrush(dish)
    p.drawEllipse(centre, rim_r, rim_r)
    fall = QLinearGradient(QPointF(cx - r * .7, cy - r * .7), QPointF(cx + r * .7, cy + r * .7))
    fall.setColorAt(0, QColor(255, 255, 255, 40))
    fall.setColorAt(.5, QColor(0, 0, 0, 0))
    fall.setColorAt(1, QColor(0, 0, 0, 70))
    p.setBrush(fall)
    p.drawEllipse(centre, rim_r, rim_r)
    p.restore()
    # the lip
    if design == "vskf":
        l0, l1 = (QColor(c) for c in LIP)
        lip = QLinearGradient(QPointF(cx - rim_r, cy - rim_r), QPointF(cx + rim_r, cy + rim_r))
        lip.setColorAt(0, l1)
        lip.setColorAt(1, l0)
        width = r * .085
    else:
        lip = QLinearGradient(QPointF(cx - rim_r, cy - rim_r), QPointF(cx + rim_r, cy + rim_r))
        lip.setColorAt(0, light)
        lip.setColorAt(1, shade)
        width = r * .058
    mid = rim_r - width * .15
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(INK, width + ink * 1.7))
    p.drawEllipse(centre, mid, mid)
    p.setPen(QPen(QBrush(lip), width))
    p.drawEllipse(centre, mid, mid)
    if design == "vskf":
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#555a63"))
        for i in range(24):                                  # the bolts of the two-piece lip
            p.drawEllipse(_pt(cx, cy, mid, i * 2 * pi / 24 + .06), r * .013, r * .013)
    # the hub with five lug nuts
    hub = QRadialGradient(QPointF(cx - r * .04, cy - r * .04), r * .2)
    hub.setColorAt(0, light)
    hub.setColorAt(1, shade)
    p.setPen(QPen(INK, ink))
    p.setBrush(hub)
    p.drawEllipse(centre, r * .165, r * .165)
    for i in range(5):
        a = radians(-90 + i * 72)
        p.setPen(QPen(INK, ink * .7))
        p.setBrush(QColor("#8a8d96"))
        p.drawEllipse(_pt(cx, cy, r * .098, a), r * .030, r * .030)
    p.setPen(QPen(INK, ink * .7))
    p.setBrush(QColor("#2b2b30"))
    p.drawEllipse(centre, r * .036, r * .036)
    p.restore()
