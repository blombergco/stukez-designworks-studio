r"""Builds built-in preview cars from illustrations on a dark background: stukez_studio/builtin/<id>/ (side view only).

    py -3 make_builtin_illustrations.py [folder with the pictures] [car id ...]

The same procedure as make_default_car.py (the S13 Silvia): the car is cut out of the dark background, and the paint of the
body becomes a separate mask, so a preview colours only the paint while windows, wheels, lights and trim keep their own
colours. The paint is found by colour: a hue range for red and blue cars, or "silver" (grey, not too dark, outside the
windows) for the silver ones. Needs numpy, pillow and scipy (scipy only for this tool, not for the program).
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from stukez_studio.cars import side_zones_clear_of_wheels   # noqa: E402

OUT = HERE / "stukez_studio" / "builtin"
SRC = Path(os.environ["STUKEZ_CAR_MASTERS"]) if os.environ.get("STUKEZ_CAR_MASTERS") else None   # or pass the folder as argument
PAD = 12
MAXW = 2000          # a wider picture is scaled down to this, so the files stay small

# mode: which paint to look for. dark: luminance under this is background. close: closing size that keeps tyres and small
# gaps inside the car. windows: boxes (fractions x0, y0, x1, y1 of the cut-out car) that are glass in "silver" cars.
CARS = {
    "180sx-origin": dict(name="180SX Origin kit", platform="S13", file="180sx Origin kit.jpg", mode="red", dark=14, close=31),
    "e36-coupe": dict(name="E36 Coupe", platform="E36", file="E36 Coupe.jpg", mode="blue", dark=14, close=31),
    "er34-uras": dict(name="ER34 Uras bodykit", platform="ER34", file="ER34 Uras Bodykit.jpg", mode="blue", dark=14, close=31),
    "galant": dict(name="Galant", platform="Galant", file="Galant.png", mode="red", dark=34, close=21),
    "s13-bstyle": dict(name="S13 B-style", platform="S13", file="S13BSTYLE_upscaled_4x.png", mode="red", dark=14, close=41),
    "s14-dmax": dict(name="S14 D-Max kit", platform="S14", file="S14 Dmax kit.jpg", mode="silver", dark=14, close=31,
                     windows=[(.40, .09, .615, .34), (.62, .10, .76, .34)]),
    "s15-raijin": dict(name="S15 Origin Raijin kit", platform="S15", file="S15 Origin Raijin kit.jpg", mode="red", dark=14, close=31),
    "s160-junction": dict(name="S160 Junction Produce", platform="S160", file="S160_JUNCTIONPRODUCE.png", mode="red", dark=60, close=61,
                          studio=True),
    "jzx90-bnsport": dict(name="JZX90 BN Sport", platform="JZX90", file="jZX90 BNsport.jpg", mode="silver", dark=14, close=31,
                          windows=[(.405, .10, .545, .33), (.555, .10, .76, .33)]),
}


def lum(a):
    return a[..., 0] * .299 + a[..., 1] * .587 + a[..., 2] * .114


def hsv(a):
    rgb = a / 255.0
    mx, mn = rgb.max(axis=2), rgb.min(axis=2)
    d = mx - mn
    sat = d / np.maximum(mx, 1e-6)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    h = np.zeros_like(mx)
    m = d > 1e-6
    rc = m & (mx == r)
    gc = m & (mx == g) & ~rc
    bc = m & ~rc & ~gc
    h[rc] = ((g - b)[rc] / d[rc]) % 6
    h[gc] = (b - r)[gc] / d[gc] + 2
    h[bc] = (r - g)[bc] / d[bc] + 4
    return h * 60, sat, mx


def box_close(mask, size):
    st = np.ones((size, size), bool)
    return ndi.binary_closing(np.pad(mask, size), st)[size:-size, size:-size]


def biggest(mask):
    lab, n = ndi.label(mask)
    if not n:
        return mask
    sizes = ndi.sum(mask, lab, range(1, n + 1))
    return lab == (1 + int(np.argmax(sizes)))


def silhouette(a, spec):
    """The car with every hole inside it filled; the biggest blob only (a generator's corner mark is dropped)."""
    if spec.get("studio"):
        # a render on a dark grey studio floor: the car is what is coloured or bright; the tyres are brought in by the closing
        hue, sat, val = hsv(a)
        fg = ((sat > .35) & (val > .35)) | (lum(a) >= spec["dark"] + 30)
        fg = ndi.binary_opening(fg, np.ones((5, 5), bool))
    else:
        fg = lum(a) >= spec["dark"]
    solid = box_close(fg, spec["close"])
    return ndi.binary_fill_holes(biggest(ndi.binary_opening(ndi.binary_fill_holes(biggest(solid)), np.ones((7, 7), bool))))


def wheel_discs(a, sil):
    """[(cx, cy, r)] of the two wheels, from the bronze of the rims (the biggest bronze blob on each half of the car); the tyre
    reaches a bit further than the rim."""
    hue, sat, val = hsv(a)
    bronze = (hue >= 12) & (hue <= 48) & (sat > .22) & (val > .18) & (val < .85) & sil
    bronze = ndi.binary_closing(bronze, np.ones((9, 9), bool))
    w = bronze.shape[1]
    out = []
    for x0, x1 in ((0, w // 2), (w // 2, w)):
        part = np.zeros_like(bronze)
        part[:, x0:x1] = bronze[:, x0:x1]
        blob = biggest(part)
        ys, xs = np.where(blob)
        if len(xs) > 1500:
            out.append(((xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2, max(xs.max() - xs.min(), ys.max() - ys.min()) / 2 * 1.2))
    return out


def paint_mask(a, sil, spec, box):
    hue, sat, val = hsv(a)
    mode = spec["mode"]
    if mode == "red":
        m = ((hue >= 345) | (hue <= 16)) & (sat > .42) & (val > .16)
    elif mode == "blue":
        m = (hue >= 195) & (hue <= 255) & (sat > .38) & (val > .12)
    else:   # silver: grey, not too dark and not blown out
        l = lum(a)
        m = (sat < .2) & (l > 52) & (l < 240)
        h, w = m.shape
        yy, xx = np.mgrid[0:h, 0:w]
        for cx, cy, r in wheel_discs(a, sil):
            m[(xx - cx) ** 2 + (yy - cy) ** 2 < r * r] = False
        for x0, y0, x1, y1 in spec.get("windows", []):
            m[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)] = False
    m &= sil
    m = ndi.binary_opening(m, np.ones((3, 3), bool))
    # holes smaller than a highlight or a badge are paint too; the windows, wheels and lights are bigger
    lab, n = ndi.label(~m)
    if n:
        sizes = ndi.sum(~m, lab, range(1, n + 1))
        small = np.isin(lab, 1 + np.where(sizes < spec.get("hole", 260))[0]) & sil
        m |= small
    # specks that are not body panels (red hub caps, a lit part of a window) go; silver cars have more of them
    lab, n = ndi.label(m)
    sizes = ndi.sum(m, lab, range(1, n + 1))
    keep = 1 + np.where(sizes > (0.0015 if mode == "silver" else 0.002) * sil.sum())[0]
    return np.isin(lab, keep)


def build(car_id, spec, src_dir, preview=None):
    img = Image.open(src_dir / spec["file"]).convert("RGB")
    if img.width > MAXW:
        img = img.resize((MAXW, round(img.height * MAXW / img.width)), Image.LANCZOS)
    a = np.asarray(img).astype(np.float32)
    sil = silhouette(a, spec)
    ys, xs = np.where(sil)
    x0, x1 = max(0, xs.min() - PAD), min(a.shape[1], xs.max() + 1 + PAD)
    y0, y1 = max(0, ys.min() - PAD), min(a.shape[0], ys.max() + 1 + PAD)
    a, sil = a[y0:y1, x0:x1], sil[y0:y1, x0:x1]
    alpha = np.asarray(Image.fromarray((sil * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(.9))).astype(np.uint8)
    paint = paint_mask(a, sil, spec, None)
    pm = np.asarray(Image.fromarray((paint * 255).astype(np.uint8), "L").filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(.8)))
    pm = np.minimum(pm, alpha)
    h, w = alpha.shape
    folder = OUT / car_id
    folder.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.dstack([a.astype(np.uint8), alpha]), "RGBA").save(folder / "side.webp", quality=93, method=6)
    Image.fromarray(pm, "L").save(folder / "side-mask.png", optimize=True)
    data = dict(name=f"{spec['name']} (built in)", platform=spec["platform"], clean=True, glass=False, front_side="left", front_top="down",
                canvas=[w, h], views=dict(side=dict(file="side.webp", mask="side-mask.png", offset=[0, 0], size=[w, h])),
                zones=dict(side=side_zones_clear_of_wheels("left")))
    old = folder / "car.json"
    if old.exists():     # keep sponsor zones that were fitted by hand
        keep = json.loads(old.read_text(encoding="utf-8"))
        if keep.get("zones", {}).get("side") and keep.get("zones_edited"):
            data["zones"] = keep["zones"]
            data["zones_edited"] = True
    old.write_text(json.dumps(data, indent=1), encoding="utf-8", newline="\n")
    print(f"{car_id}: {w} x {h}px, paint covers {(pm > 127).mean() * 100:.0f}% of the picture ({(pm > 127).sum() / max(1, (alpha > 127).sum()) * 100:.0f}% of the car)")
    if preview is not None:      # car on pink with the paint in green, for checking
        chk = np.dstack([a, a[..., 0] * 0 + 255]).astype(np.uint8)
        bg = np.zeros((h, w, 3), np.float32)
        bg[:] = (255, 0, 200)
        al = (alpha / 255.0)[..., None]
        comp = a * al + bg * (1 - al)
        tint = comp.copy()
        tint[pm > 127] = tint[pm > 127] * .35 + np.array([0, 255, 0]) * .65
        Image.fromarray(np.vstack([comp, tint]).astype(np.uint8)).save(preview / f"{car_id}.png")


if __name__ == "__main__":
    args = sys.argv[1:]
    src = SRC
    if args and Path(args[0]).is_dir():
        src, args = Path(args[0]), args[1:]
    if src is None:
        sys.exit("usage: make_builtin_illustrations.py <folder with the masters> (or set STUKEZ_CAR_MASTERS)")
    prev = None
    if os.environ.get("CAR_PREVIEW"):
        prev = Path(os.environ["CAR_PREVIEW"])
        prev.mkdir(parents=True, exist_ok=True)
    for cid, spec in CARS.items():
        if not args or cid in args:
            build(cid, spec, src, prev)
