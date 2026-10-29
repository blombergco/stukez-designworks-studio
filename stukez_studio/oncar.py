"""Placement image on a real car: the project's palette on the capture, sponsor logos in the car's zones, legend below.

Uses the vault's own Tools/placement_preview.py for the sponsor kit and the logo masters (read only, D:), so the logos and
the text stand-ins are the same as in the generic Placement preview.
"""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen

from . import carrender
from .cars import ZONE_NAMES

BG = QColor(246, 247, 251)
INK = QColor(30, 34, 44)
MUTED = QColor(90, 98, 115)


def _font(px, bold=False):
    f = QFont("Segoe UI")
    f.setPixelSize(px)
    f.setBold(bold)
    return f


def _qimage(tile):
    """PIL RGBA -> QImage (copied, so the buffer can go away)."""
    tile = tile.convert("RGBA")
    return QImage(tile.tobytes("raw", "RGBA"), tile.width, tile.height, tile.width * 4, QImage.Format_RGBA8888).copy()


def sponsor_context(vault, proj):
    """(placement_preview, logo index, palette, sponsor kit) of a project; the kit is {} while it has no Build sheet."""
    pp, idx = vault.placement()
    try:
        kit = pp.read_kit(proj.folder)
    except FileNotFoundError:
        kit = {}
    return pp, idx, pp.read_project(proj.folder), kit


def make_tile(ctx, entry, bw, bh, stats=None):
    """(QImage, supersampling, real logo?) of one sponsor fitted into a bw x bh box, or None when the box is too small."""
    pp, idx, pal, _ = ctx
    res = pp.sponsor_tile(entry, pal, (0, 0, bw, bh), 1 / entry["size"], idx, stats if stats is not None else {"real": 0, "text": 0})
    if not res:
        return None
    tile, real = res
    return _qimage(tile), pp.SS, real


def render_placement(vault, proj, car, width=1500):
    """(QImage, stats). Raises FileNotFoundError if the project has no build sheet yet."""
    ctx = sponsor_context(vault, proj)
    pp, idx, pal, kit = ctx
    if not kit:
        raise FileNotFoundError("no build sheet")
    stats = {"real": 0, "text": 0}
    used = {}
    m = 30
    views = car.views()
    side = car.view_info("side")["size"] if "side" in views else None
    sw = width - 2 * m
    sh = int(sw * side[1] / side[0]) if side else 0
    row = [(v, 560 if v != "top" else None, 560 if v == "top" else None) for v in views if v != "side"]
    heights = [h or int(w * car.view_info(v)["size"][1] / car.view_info(v)["size"][0]) for v, w, h in row]
    rowh = max(heights) if heights else 0
    legend_h = 6 * 32 + 90
    H = 110 + sh + (rowh + 70 if row else 0) + legend_h
    img = QImage(width, H, QImage.Format_ARGB32)
    img.fill(BG)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.setPen(INK)
    p.setFont(_font(34, True))
    p.drawText(QRectF(m, 18, width - 2 * m, 44), Qt.AlignLeft | Qt.AlignVCenter, f"{proj.title} on {car.name}")
    p.setPen(MUTED)
    p.setFont(_font(17))
    p.drawText(QRectF(m, 62, width - 2 * m, 28), Qt.AlignLeft | Qt.AlignVCenter,
               "Placement preview on the real car. Real logo masters recoloured to Sponsor A / B; bold text where no master exists.")

    def draw_view(view, x, y, w, h):
        p.drawImage(QRectF(x, y, w, h), carrender.render(car, view, proj, int(w), plates={}))
        for z, (fx, fy, fw, fh) in car.zones(view).items():
            e = kit.get(int(z))
            res = make_tile(ctx, e, fw * w, fh * h, stats) if e else None
            if not res:
                continue
            tq, ss, real = res
            used[int(z)] = real
            tw, th = tq.width() / ss, tq.height() / ss
            cx, cy = x + (fx + fw / 2) * w, y + (fy + fh / 2) * h
            p.drawImage(QRectF(cx - tw / 2, cy - th / 2, tw, th), tq)
        p.setPen(MUTED)
        p.setFont(_font(15))
        front = car.front_of(view)
        p.drawText(QRectF(x, y + h + 4, max(w, 260), 22), Qt.AlignLeft,
                   f"{view} view" + (f" (front is {'at the ' + front if view == 'top' else 'on the ' + front})" if front else ""))

    y = 100
    if side:
        draw_view("side", m, y, sw, sh)
        y += sh + 34
    x = m
    for (v, w, h), hh in zip(row, heights):
        ww = w or int(hh * car.view_info(v)["size"][0] / car.view_info(v)["size"][1])
        draw_view(v, x, y, ww, hh)
        x += ww + 60
    y += (rowh + 56) if row else 0

    p.setPen(INK)
    p.setFont(_font(20, True))
    p.drawText(QRectF(m, y, 600, 28), Qt.AlignLeft, "Sponsor kit (from the Build sheet)")
    y += 38
    fl, fb = _font(17), _font(17, True)
    for z in range(1, 13):
        e = kit.get(z)
        if not e:
            continue
        col, r = divmod(z - 1, 6)
        x0, yy = m + col * (width // 2), y + r * 32
        fc = pal["sponsor_a" if e["fill"] == "A" else "sponsor_b"][0]
        p.setPen(QPen(QColor(120, 125, 140), 1))
        p.setBrush(QColor(fc))
        p.drawRoundedRect(QRectF(x0, yy + 2, 20, 20), 5, 5)
        p.setPen(INK)
        p.setFont(fl)
        p.drawText(QRectF(x0 + 30, yy, 250, 24), Qt.AlignLeft | Qt.AlignVCenter, f"{z:>2}  {ZONE_NAMES[z]}")
        p.setFont(fb)
        p.drawText(QRectF(x0 + 285, yy, 270, 24), Qt.AlignLeft | Qt.AlignVCenter, p.fontMetrics().elidedText(e["brand"], Qt.ElideRight, 260))
        tag = "logo master" if used.get(z) else ("text stand-in" if z in used else "not in a zone")
        p.setPen(QColor(40, 120, 70) if used.get(z) else QColor(150, 100, 40) if z in used else QColor(140, 145, 160))
        p.setFont(fl)
        p.drawText(QRectF(x0 + 560, yy, 170, 24), Qt.AlignLeft | Qt.AlignVCenter, tag)
    p.end()
    return img, stats
