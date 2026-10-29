"""Illustrator templates from the car library: the capture on its original canvas, numbered zone guides and an SVG with layers."""
import base64
import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import carrender
from .cars import ZONE_NAMES

FONT = r"C:\Windows\Fonts\segoeuib.ttf"
ZONE_RGB = [(255, 46, 63), (255, 255, 255), (255, 159, 69), (90, 220, 170), (80, 190, 255), (242, 233, 107)]


def _font(px):
    try:
        return ImageFont.truetype(FONT, px)
    except OSError:
        return ImageFont.load_default()


def canvas_image(car, view, img=None):
    """The view pasted on its original canvas (same size as the Substance screenshot)."""
    info = car.view_info(view)
    base = Image.new("RGBA", tuple(car.canvas), (0, 0, 0, 0))
    base.paste(img or Image.open(car.view_path(view)).convert("RGBA"), tuple(info["offset"]))
    return base


def zone_boxes(car, view):
    """Zone rectangles in canvas pixels: {zone: (x, y, w, h)}."""
    info = car.view_info(view)
    ox, oy = info["offset"]
    w, h = info["size"]
    return {z: (ox + x * w, oy + y * h, zw * w, zh * h) for z, (x, y, zw, zh) in car.zones(view).items()}


def zones_image(car, view):
    img = Image.new("RGBA", tuple(car.canvas), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = _font(max(14, car.canvas[0] // 90))
    for z, (x, y, w, h) in zone_boxes(car, view).items():
        rgb = ZONE_RGB[int(z) % len(ZONE_RGB)]
        d.rounded_rectangle([x, y, x + w, y + h], radius=min(w, h) * .12, outline=rgb + (255,), width=max(3, car.canvas[0] // 700),
                            fill=rgb + (40,))
        d.text((x + 6, y + 3), f"{z} {ZONE_NAMES.get(int(z), '')}", font=f, fill=rgb + (255,))
    return img


def _png_b64(img):
    b = io.BytesIO()
    img.save(b, "PNG")
    return base64.b64encode(b.getvalue()).decode()


def _svg(car, view, proj, livery):
    cw, ch = car.canvas
    info = car.view_info(view)
    ox, oy = info["offset"]
    sw, sh = info["size"]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{cw}" height="{ch}" viewBox="0 0 {cw} {ch}">']
    parts.append('<defs>')
    swatches = []
    if proj is not None:
        for i, (label, value, _o) in enumerate(proj.slots()):
            vals = value if isinstance(value, (list, tuple)) else [value]
            if len(vals) == 2:
                parts.append(f'<linearGradient id="g{i}"><stop offset="0" stop-color="{vals[0]}"/><stop offset="1" stop-color="{vals[1]}"/></linearGradient>')
                swatches.append((label, f"url(#g{i})", " → ".join(vals)))
            else:
                swatches.append((label, vals[0], vals[0]))
    parts.append('</defs>')
    body = livery or Image.open(car.view_path(view)).convert("RGBA")
    parts.append(f'<g id="Car"><image x="{ox}" y="{oy}" width="{sw}" height="{sh}" xlink:href="data:image/png;base64,{_png_b64(body)}"/></g>')
    parts.append('<g id="Zones" fill="none" font-family="Segoe UI, Arial" font-weight="bold">')
    for z, (x, y, w, h) in zone_boxes(car, view).items():
        rgb = "#%02x%02x%02x" % ZONE_RGB[int(z) % len(ZONE_RGB)]
        fs = max(14, cw // 90)
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{min(w, h) * .12:.1f}" stroke="{rgb}" stroke-width="{max(3, cw // 700)}"/>'
                     f'<text x="{x + 6:.1f}" y="{y + fs:.1f}" font-size="{fs}" fill="{rgb}" stroke="none">{z} {ZONE_NAMES.get(int(z), "")}</text>')
    parts.append('</g>')
    if swatches:
        parts.append('<g id="Palette" font-family="Segoe UI, Arial" font-size="22">')
        sz = max(60, cw // 40)
        for i, (label, fill, txt) in enumerate(swatches):
            x = 30 + i * (sz + 150)
            parts.append(f'<rect x="{x}" y="30" width="{sz}" height="{sz}" rx="10" fill="{fill}" stroke="#808080"/>'
                         f'<text x="{x + sz + 10}" y="{30 + sz / 2 - 2}" fill="#808080" font-weight="bold">{label}</text>'
                         f'<text x="{x + sz + 10}" y="{30 + sz / 2 + 22}" fill="#808080">{txt}</text>')
        parts.append('</g>')
    parts.append('</svg>')
    return "\n".join(parts)


def export_template(car, view, folder, proj=None):
    """Write the template files of one view; returns the list of files written."""
    folder = Path(folder)
    stem = f"{car.name} - {view}"
    out = []
    livery = None
    if proj is not None:
        qi = carrender.render(car, view, proj, car.view_info(view)["size"][0])
        livery = Image.frombuffer("RGBA", (qi.width(), qi.height()), bytes(qi.constBits()), "raw", "RGBA", 0, 1)
        if livery.size != tuple(car.view_info(view)["size"]):
            livery = livery.resize(tuple(car.view_info(view)["size"]), Image.LANCZOS)
        canvas_image(car, view, livery).save(folder / f"{proj.title} - {stem} - livery.png")
        out.append(f"{proj.title} - {stem} - livery.png")
    canvas_image(car, view).save(folder / f"{stem} - template.png")
    zones_image(car, view).save(folder / f"{stem} - zones.png")
    svg_name = f"{proj.title} - {stem}.svg" if proj is not None else f"{stem}.svg"
    (folder / svg_name).write_text(_svg(car, view, proj, livery), encoding="utf-8")
    return out + [f"{stem} - template.png", f"{stem} - zones.png", svg_name]
