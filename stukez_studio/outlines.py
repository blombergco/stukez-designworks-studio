"""Outlines for sponsor logos: a single-colour contour around any logo, as separate layers.

The Project Library rule is that every outline is one colour, so a logo is given one contour in one hex colour. The result
comes as three layers (the contour on its own, the contour with the logo on top, and a solid cut plate) plus a layered SVG
for Illustrator. Contours are pixel based: for a true vector contour use Offset Path on the plate in Illustrator.
"""
import base64
import io
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from . import palette as pal

EXTS = (".png", ".webp", ".jpg", ".jpeg", ".tga", ".bmp")
WORK = 1600           # longest side the contour is worked out at; bigger logos get the contour scaled up smoothly
DEFAULT_OUTLINE = "#0C0A14"


@dataclass
class Spec:
    colour: str = DEFAULT_OUTLINE
    thickness: int = 12     # pixels of the original logo
    gap: int = 0            # clear space between the logo and the contour
    join: int = 0           # bridge gaps up to this size, so letters become one shape
    round_corners: bool = True


# ---------------------------------------------------------------------- loading
def load(path):
    img = Image.open(path)
    img.load()
    return img.convert("RGBA")


def has_transparency(img):
    a = np.asarray(img)[..., 3]
    return bool((a < 250).any())


def remove_plain_background(img, tolerance=40):
    """Make the background transparent: the colour of the corners, within `tolerance` (0..255 per channel sum / 3)."""
    arr = np.asarray(img).astype(np.int16).copy()
    h, w = arr.shape[:2]
    corners = np.array([arr[0, 0, :3], arr[0, w - 1, :3], arr[h - 1, 0, :3], arr[h - 1, w - 1, :3]])
    bg = np.median(corners, axis=0)
    dist = np.abs(arr[..., :3] - bg).sum(axis=2) / 3
    arr[..., 3] = np.where(dist <= tolerance, 0, arr[..., 3])
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def dominant_colour(img):
    """Average colour of the opaque pixels of a logo (what the outline has to stand out from)."""
    a = np.asarray(img)
    m = a[..., 3] > 127
    if not m.any():
        return "#808080"
    r, g, b = (float(a[..., i][m].mean()) for i in range(3))
    return pal.rgb_to_hex(r, g, b)


def suggest_colour(img):
    """The outline colour that reads best against the logo: the studio's dark outline, or white."""
    d = dominant_colour(img)
    dark, light = DEFAULT_OUTLINE, "#F5F0F1"
    return dark if pal.contrast(d, dark) >= pal.contrast(d, light) else light


# ---------------------------------------------------------------------- morphology
def dilate(mask, r):
    """Grow a boolean mask by r pixels (an octagon: alternating square and cross steps)."""
    m = mask
    for i in range(int(r)):
        p = np.pad(m, 1)
        if i % 2 == 0:
            m = (p[:-2, :-2] | p[:-2, 1:-1] | p[:-2, 2:] | p[1:-1, :-2] | p[1:-1, 1:-1] | p[1:-1, 2:] | p[2:, :-2] | p[2:, 1:-1] | p[2:, 2:])
        else:
            m = p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:] | p[1:-1, 1:-1]
    return m


def erode(mask, r):
    return ~dilate(~mask, r)


def _smooth(mask, radius):
    """Round off the corners of a mask: blur it and cut it at the half way line."""
    if radius <= 0:
        return mask
    im = Image.fromarray((mask * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(radius))
    return np.asarray(im) > 127


# ---------------------------------------------------------------------- the contour
def _alpha_from_mask(mask, size):
    """Antialiased 0..255 alpha of a boolean mask, scaled to `size` (w, h) when the contour was worked out smaller."""
    im = Image.fromarray((mask * 255).astype(np.uint8), "L")
    if im.size != size:
        im = im.resize(size, Image.BICUBIC)
    arr = np.asarray(im.filter(ImageFilter.GaussianBlur(.7))).astype(np.float32)
    return np.clip((arr - 127.5) * 3 + 127.5, 0, 255).astype(np.uint8)


def make(img, spec):
    """Return dict(outline, combined, plate, size): RGBA images the size of the logo plus room for the contour."""
    reach = spec.gap + spec.thickness
    pad = reach + 4
    w0, h0 = img.size
    canvas = Image.new("RGBA", (w0 + 2 * pad, h0 + 2 * pad), (0, 0, 0, 0))
    canvas.paste(img, (pad, pad))
    W, H = canvas.size
    f = min(1.0, WORK / max(W, H))
    small = canvas.resize((max(1, round(W * f)), max(1, round(H * f))), Image.LANCZOS) if f < 1 else canvas
    m = np.asarray(small)[..., 3] > 127
    gap, thick, join = (round(v * f) for v in (spec.gap, spec.thickness, spec.join))
    thick = max(1, thick) if spec.thickness > 0 else 0
    if join:
        m = erode(dilate(m, join), join)
    outer = dilate(m, gap + thick)
    inner = dilate(m, gap) if gap else m
    if spec.round_corners:
        outer = _smooth(outer, max(.0, thick * .22))
    ring = outer & ~inner
    rgb = tuple(int(spec.colour[i:i + 2], 16) for i in (1, 3, 5))
    out = np.zeros((H, W, 4), np.uint8)
    out[..., :3] = rgb
    out[..., 3] = _alpha_from_mask(ring, (W, H))
    outline = Image.fromarray(out, "RGBA")
    plate = np.zeros((H, W, 4), np.uint8)
    plate[..., :3] = rgb
    plate[..., 3] = _alpha_from_mask(outer, (W, H))
    combined = Image.alpha_composite(outline, canvas)
    return dict(outline=outline, combined=combined, plate=Image.fromarray(plate, "RGBA"), size=(W, H))


# ---------------------------------------------------------------------- output
def _b64(im):
    b = io.BytesIO()
    im.save(b, "PNG")
    return base64.b64encode(b.getvalue()).decode()


def svg_layers(result, logo):
    """A layered SVG: Cut plate, Outline and Logo as separate groups (each an embedded PNG) for Illustrator."""
    w, h = result["size"]
    pad = (w - logo.width) // 2
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{w}" height="{h}" viewBox="0 0 {w} {h}">\n'
            f'<g id="Cut plate"><image width="{w}" height="{h}" xlink:href="data:image/png;base64,{_b64(result["plate"])}"/></g>\n'
            f'<g id="Outline"><image width="{w}" height="{h}" xlink:href="data:image/png;base64,{_b64(result["outline"])}"/></g>\n'
            f'<g id="Logo"><image x="{pad}" y="{pad}" width="{logo.width}" height="{logo.height}" xlink:href="data:image/png;base64,{_b64(logo)}"/></g>\n'
            '</svg>\n')


def save(result, logo, folder, stem):
    """Write the layers next to each other; returns the file names."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    names = [f"{stem} - outlined.png", f"{stem} - outline only.png", f"{stem} - cut plate.png", f"{stem} - layers.svg"]
    result["combined"].save(folder / names[0])
    result["outline"].save(folder / names[1])
    result["plate"].save(folder / names[2])
    (folder / names[3]).write_text(svg_layers(result, logo), encoding="utf-8")
    return names


def process_file(path, spec, folder, remove_bg=None):
    """Outline one logo file and save it; `remove_bg` is a tolerance (or None to keep the pixels as they are)."""
    logo = load(path)
    if remove_bg is not None:
        logo = remove_plain_background(logo, remove_bg)
    return save(make(logo, spec), logo, folder, Path(path).stem)


def logos_in(folder):
    return sorted(f for f in Path(folder).iterdir() if f.suffix.lower() in EXTS and not f.stem.endswith((" - outlined", " - outline only", " - cut plate")))
