"""Paints a palette (base, tribals, sponsor plates) on a real car capture.

The livery is first drawn flat with Qt, then multiplied with the shading of the capture so panel lines, highlights and
shadows stay. This needs a *clean grey base* capture; for a capture that already carries a livery only the silhouette
is used (with a soft top-to-bottom shade) so the old livery never leaks into the preview.
"""
from collections import OrderedDict
from math import cos, radians, sin

import numpy as np
from PIL import Image, ImageFilter
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter, QPen

GLASS = np.array([16, 15, 26], dtype=np.float32)
_cache = OrderedDict()
_prep_cache = OrderedDict()
_images = {}
CACHE_SIZE = 240

# preview plates: which zones show a plate in the card/preview, and with which sponsor colour
PREVIEW_PLATES = {"side": {"5": "A", "4": "B", "7": "A"}, "top": {"2": "A", "8": "B", "9": "A"},
                  "front": {"2": "A", "3": "B"}, "rear": {"9": "A", "10": "B"}}


def _pil(car, view):
    key = (car.id, view, car.view_path(view).stat().st_mtime_ns)
    if key not in _images:
        _images[key] = Image.open(car.view_path(view)).convert("RGBA")
    return _images[key]


def _prep(car, view, width):
    """Silhouette, shading and glass mask of a view at one width; the same for every palette, so cached on their own."""
    key = (car.id, view, width, car.clean, car.glass, car.view_path(view).stat().st_mtime_ns)
    if key not in _prep_cache:
        src = _pil(car, view)
        h = max(1, round(src.height * width / src.width))
        alpha, shade, glass = _shade(np.asarray(src.resize((width, h), Image.LANCZOS)), car.clean, car.glass)
        _prep_cache[key] = (h, alpha, shade, glass)
        if len(_prep_cache) > 60:
            _prep_cache.popitem(last=False)
    return _prep_cache[key]


def _brush(rect, value, vertical=False):
    if isinstance(value, (list, tuple)):
        g = QLinearGradient(rect.topLeft(), rect.bottomLeft() if vertical else rect.topRight())
        g.setColorAt(0, QColor(value[0]))
        g.setColorAt(1, QColor(value[1]))
        return g
    return QColor(value)


def _first(value):
    return value[0] if isinstance(value, (list, tuple)) else value


def split_colours(d):
    """(rear, front) colours of the livery: the base at the back, the tribal colour at the front."""
    return QColor(_first(d.base)), QColor(_first(d.tribal))


CUT_DEFAULT = dict(angle=45.0, pos=.5, span=.5)   # the studio standard: 45 degrees, centred on the door, over half the car


def cut_of(d):
    """(angle, position, span) of the cut of a palette; plain palettes use the studio standard."""
    return (float(getattr(d, "cut_angle", CUT_DEFAULT["angle"])), float(getattr(d, "cut_pos", CUT_DEFAULT["pos"])),
            float(getattr(d, "cut_span", CUT_DEFAULT["span"])))


def split_gradient(rect, d, length, sx, sy, axis="x"):
    """One gradient over the car: the base behind the cut, the tribal colour in front of it.

    By default it is the studio cut: 45 degrees, centred on the middle of the door, covering half the car's length, solid
    on both sides. A palette can carry `cut_angle` (-90..90 degrees against the length of the car), `cut_pos` (0..1 along
    the car from the rear) and `cut_span` (0..1 of the length the blend covers). `length` is the car's length along
    `axis`; sx and sy (+1 or -1) point towards the front; in the side view sx is the side the car faces.
    """
    rear, front = split_colours(d)
    angle, pos, span = cut_of(d)
    th = radians(max(-89.0, min(89.0, angle)))
    if axis == "x":
        u = (sx * cos(th), sin(th))
        centre = QPointF(rect.center().x() + (pos - .5) * length * sx, rect.center().y())
    else:
        u = (sin(th), sy * cos(th))
        centre = QPointF(rect.center().x(), rect.center().y() + (pos - .5) * length * sy)
    axis_len = max(2.0, span * length * max(abs(cos(th)), .2))   # 45 degrees and span .5 give length * .354, as before
    g = QLinearGradient(centre.x() - u[0] * axis_len / 2, centre.y() - u[1] * axis_len / 2,
                        centre.x() + u[0] * axis_len / 2, centre.y() + u[1] * axis_len / 2)
    g.setColorAt(0, rear)
    g.setColorAt(1, front)
    return g


def _open(mask, size):
    """Binary opening: keeps big blobs (windows, arch interiors) and drops thin lines (panel edges)."""
    im = Image.fromarray((mask * 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.MinFilter(size)).filter(ImageFilter.MaxFilter(size))) > 127


def _shade(arr, clean, glass_on=True):
    """(alpha 0..1, shade factor, glass mask) for an RGBA uint8 array."""
    alpha = arr[..., 3].astype(np.float32) / 255
    h, w = alpha.shape
    lum = arr[..., :3].astype(np.float32) @ np.array([.299, .587, .114], np.float32)
    if not clean:
        # a capture that carries a livery: keep only its fine detail (panel lines, edges), not its paint
        blur = np.asarray(Image.fromarray(lum.astype(np.uint8)).filter(ImageFilter.GaussianBlur(max(2, w / 110))), np.float32)
        ref = float(lum[alpha > .5].mean()) if (alpha > .5).any() else 128.0
        v = np.linspace(1.08, 0.74, h, dtype=np.float32)[:, None]
        shade = np.clip(v + 0.9 * (lum - blur) / max(ref, 1.0), .4, 1.4)
        return alpha, shade, np.zeros((h, w), bool)
    opaque, white = alpha > .5, (alpha > .5) & (lum >= 236)
    if not glass_on or white.sum() > .4 * opaque.sum():   # a white base: windows can't be told from paint, so no glass
        ref = float(np.median(lum[opaque])) if opaque.any() else 200.0
        return alpha, np.clip(lum / max(ref, 1.0), .35, 1.4), np.zeros((h, w), bool)
    body = opaque & (lum < 236)
    ref = float(np.median(lum[body])) if body.any() else 128.0
    shade = np.clip(lum / max(ref, 1.0), .35, 1.55)
    return alpha, shade, _open(white, max(3, int(w / 120) | 1))


def _flat(w, h, car, view, d, plates):
    """The livery drawn flat at the size of the view, as an RGBA numpy array."""
    img = QImage(w, h, QImage.Format_RGBA8888)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    full = QRectF(0, 0, w, h)
    vertical = view != "side"
    if view == "side":   # base behind the middle of the door, tribal colour in front of it, one 45 degree gradient
        p.fillRect(full, split_gradient(full, d, w, 1 if car.front_side == "right" else -1, 1))
    elif view == "top" and w >= h:   # captured lying down: "down" is the front on the left, like the side view
        p.fillRect(full, split_gradient(full, d, w, -1 if car.front_top == "down" else 1, 1))
    elif view == "top":
        p.fillRect(full, split_gradient(full, d, h, 1, 1 if car.front_top == "down" else -1, "y"))
    else:
        p.fillRect(full, _brush(full, d.base, vertical))
    zones = car.zones(view)
    for z, which in plates.items():
        if z not in zones:
            continue
        x, y, zw, zh = zones[z]
        r = QRectF(x * w, y * h, zw * w, zh * h)
        fill, line = (d.sponsor_a, d.sponsor_a_outline) if which == "A" else (d.sponsor_b, d.sponsor_b_outline)
        p.setBrush(_brush(r, fill, vertical))
        p.setPen(QPen(QColor(line), max(2.0, min(r.width(), r.height()) * .08)))
        p.drawRoundedRect(r, r.height() * .22, r.height() * .22)
        f = QFont("Segoe UI")
        f.setBold(True)
        f.setPixelSize(max(6, int(min(r.height() * .5, r.width() * .16))))
        p.setFont(f)
        p.setPen(QColor(line))
        p.drawText(r, Qt.AlignCenter, f"SPONSOR {which}")
    p.end()
    ptr = img.constBits()
    return np.frombuffer(ptr, np.uint8).reshape(h, img.bytesPerLine() // 4, 4)[:, :w].copy()


def render(car, view, d, width, plates=None):
    """The car view in the palette `d` (Proj, pk.Project or dict-like namespace) as a QImage, `width` pixels wide."""
    if view not in car.views():
        return None
    width = max(120, int(np.ceil(width / 50) * 50))
    plates = ({} if getattr(d, "no_plates", False) else PREVIEW_PLATES.get(view, {})) if plates is None else plates
    key = (car.id, view, width, car.clean, car.glass, repr((d.base, d.tribal, d.tribal_outline, d.sponsor_a, d.sponsor_a_outline, cut_of(d),
                                                 d.sponsor_b, d.sponsor_b_outline)), repr(sorted(plates.items())),
           repr(car.zones(view)), car.front_side, car.front_top)
    if key in _cache:
        _cache.move_to_end(key)
        return _cache[key]
    h, alpha, shade, glass = _prep(car, view, width)
    flat = _flat(width, h, car, view, d, plates)[..., :3].astype(np.float32)
    rgb = np.clip(flat * shade[..., None], 0, 255)
    rgb[glass] = GLASS
    out = np.dstack([rgb, alpha * 255]).astype(np.uint8)
    qi = QImage(out.data, width, h, width * 4, QImage.Format_RGBA8888).copy()
    _cache[key] = qi
    if len(_cache) > CACHE_SIZE:
        _cache.popitem(last=False)
    return qi


def clear_cache():
    _cache.clear()
    _prep_cache.clear()
    _images.clear()
