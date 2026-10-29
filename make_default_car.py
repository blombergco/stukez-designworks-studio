r"""Builds the built-in preview car (stukez_studio/builtin/s13-silvia/) from an illustration of a red car on black.

    py -3 make_default_car.py path\to\illustration.webp

The car is cut out of the black background (the dark tyres are kept by closing the small gaps around the wheels), and the red
paint is turned into a separate mask: the preview colours only the paint, so windows, wheels, lights and trim keep their own
colours. Anything outside the car (such as a generator's corner mark) is left out by the row limits below, which belong to
this one illustration; change them for another picture.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

OUT = Path(__file__).resolve().parent / "stukez_studio" / "builtin" / "s13-silvia"
ROWS = (650, 1300)            # the car lies in these rows of the 2000 x 2000 picture; the corner mark is below
DARK = 14                     # luminance under this is background (or tyre rubber)
CLOSE = 31                    # closing size that keeps tyres and thin dark gaps inside the car
PAD = 12
# sponsor zones in pixels of the original picture: (x, y, width, height)
ZONES = {2: (420, 964, 230, 32), 3: (146, 1066, 170, 62), 4: (560, 1029, 125, 55), 5: (724, 984, 440, 88),
         6: (662, 1150, 640, 52), 7: (1238, 940, 270, 70), 10: (1626, 1056, 210, 80)}


def lum(a):
    return a[..., 0] * .299 + a[..., 1] * .587 + a[..., 2] * .114


def closing(mask, size):
    im = Image.fromarray((mask * 255).astype(np.uint8), "L")
    return np.asarray(im.filter(ImageFilter.MaxFilter(size)).filter(ImageFilter.MinFilter(size))) > 127


def outside(mask):
    """Pixels of the background: the not-car pixels that can be reached from the border without crossing the car."""
    h, w = mask.shape
    seen = np.zeros_like(mask, bool)
    stack = [(0, x) for x in range(w)] + [(h - 1, x) for x in range(w)] + [(y, 0) for y in range(h)] + [(y, w - 1) for y in range(h)]
    free = ~mask
    # row-wise flood fill with numpy: grow from the border until nothing changes
    seen[0, :] = free[0, :]
    seen[-1, :] = free[-1, :]
    seen[:, 0] |= free[:, 0]
    seen[:, -1] |= free[:, -1]
    while True:
        p = np.pad(seen, 1)
        grown = (p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:] | seen) & free
        if (grown == seen).all():
            return seen
        seen = grown


def main(src):
    img = Image.open(src).convert("RGB")
    full = np.asarray(img).astype(np.float32)
    y0, y1 = ROWS
    a = full[y0:y1]
    fg = lum(a) >= DARK
    solid = closing(fg, CLOSE)
    silhouette = ~outside(solid)                       # the car with every hole inside it filled
    ys, xs = np.where(silhouette)
    x0, x1, yy0, yy1 = max(0, xs.min() - PAD), min(a.shape[1], xs.max() + 1 + PAD), max(0, ys.min() - PAD), min(a.shape[0], ys.max() + 1 + PAD)
    crop = lambda arr: arr[yy0:yy1, x0:x1]
    rgb, sil = crop(a), crop(silhouette)
    alpha = np.asarray(Image.fromarray((sil * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(.9))).astype(np.uint8)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    paint = ((r > 70) & (r > 1.5 * g) & (r > 1.5 * b) & sil).astype(np.uint8) * 255
    paint = np.asarray(Image.fromarray(paint, "L").filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(.8)))
    paint = np.minimum(paint, alpha)
    OUT.mkdir(parents=True, exist_ok=True)
    car = np.dstack([rgb.astype(np.uint8), alpha])
    Image.fromarray(car, "RGBA").save(OUT / "side.webp", quality=95, method=6)
    Image.fromarray(paint, "L").save(OUT / "side-mask.png", optimize=True)
    h, w = alpha.shape
    ox, oy = x0, y0 + yy0
    zones = {str(z): [round(max(0.0, (zx - ox) / w), 4), round(max(0.0, (zy - oy) / h), 4), round(zw / w, 4), round(zh / h, 4)] for z, (zx, zy, zw, zh) in ZONES.items()}
    data = {"name": "S13 Silvia (built in)", "platform": "S13", "clean": True, "glass": False, "front_side": "left", "front_top": "down",
            "canvas": [w, h], "views": {"side": {"file": "side.webp", "mask": "side-mask.png", "offset": [0, 0], "size": [w, h]}},
            "zones": {"side": zones}}
    (OUT / "car.json").write_text(json.dumps(data, indent=1), encoding="utf-8", newline="\n")
    print(f"car {w} x {h}px, paint covers {(paint > 127).mean() * 100:.0f}% of the picture, crop origin ({ox},{oy})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1])
