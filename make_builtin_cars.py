r"""Builds built-in cars from rendered captures (cut out, with a transparent background): stukez_studio/builtin/<id>/.

    py -3 make_builtin_cars.py

Each capture is turned into a neutral grey base that keeps the shading: painted panels of different colours (a livery baked
into the capture) are brought to the same brightness, windows become white (the program draws them dark), and everything
else is grey. The program then paints a palette onto that base like on any clean grey capture. The wheels are not in the
captures; wheels.py draws them (vector) at the positions listed under "wheels" in car.json.

The source pictures are given below; the numbers belong to those pictures (where the windows are and where the wheels go).
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from stukez_studio.cars import crop_view, default_zones, side_zones_clear_of_wheels   # noqa: E402

OUT = HERE / "stukez_studio" / "builtin"
BODY_GREY = 150.0       # the paint ends up at this brightness; only real windows are brighter than 236

CARS = {
    "s13-origin": dict(
        name="S13 Origin kit (built in)", platform="S13", clean=True, front_side="left",
        files=dict(side="2.webp", top="3.webp"),
        # windows as boxes of the capture (x0, y0, x1, y1): white there is glass, white elsewhere is white paint
        windows=dict(side=[(740, 190, 1480, 352)], top=[(515, 80, 820, 720), (1340, 80, 1590, 720)]),
        recolour=True,
        wheels=dict(side=[(355, 360, 132), (1492, 362, 130)]),      # (centre x, centre y, tyre radius) front, rear
        default_wheel=dict(design="te37", colour="bronze"),
    ),
    "s15-raiji": dict(
        name="S15 Raiji kit (built in)", platform="S15", clean=True, front_side="left",
        files=dict(side="4.webp", top="5.webp"),
        windows=dict(side=[(700, 150, 1470, 330)], top=[(560, 60, 830, 740), (1340, 100, 1620, 700)]),
        recolour=False,
        wheels=dict(side=[(342, 385, 130), (1565, 383, 132)]),
        default_wheel=dict(design="vskf", colour="gunmetal"),
    ),
}


def _hsv(rgb):
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


def neutral_base(img, windows, recolour):
    """RGBA capture -> grey RGBA with the shading kept (see the module text)."""
    a = np.asarray(img.convert("RGBA")).astype(np.float32)
    rgb, alpha = a[..., :3], a[..., 3]
    lum = rgb @ np.array([.299, .587, .114], np.float32)
    hue, sat, _ = _hsv(rgb)
    opaque = alpha > 127
    glass = np.zeros(lum.shape, bool)
    for x0, y0, x1, y1 in windows:
        glass[y0:y1, x0:x1] = True
    glass &= opaque & (sat < .2) & (lum >= 215)
    body = opaque & ~glass
    if recolour:
        # a livery baked into the capture: bring blue and green panels to the brightness of the white paint
        white = body & (sat < .16) & (lum > 150)
        ref = float(np.median(lum[white])) if white.any() else float(np.median(lum[body]))
        out = lum.copy()
        for lo, hi in ((190, 245), (60, 110)):         # blue, then lime green
            core = body & (sat > .4) & (hue >= lo) & (hue <= hi)
            if core.sum() > 200:
                gain = ref / max(float(np.median(lum[core])), 1.0)
                # the more saturated a pixel of that hue, the more of the correction it gets: edge pixels (a mix of white
                # and blue) get part of it, so no light or dark outline is left along the panel edges
                w = np.clip((sat - .1) / .35, 0, 1) * (body & (hue >= lo) & (hue <= hi))
                out = out * (1 + w * (gain - 1))
        lum = out
    else:
        ref = float(np.median(lum[body]))
    grey = np.clip(lum / max(ref, 1.0) * BODY_GREY, 0, 228)
    grey[glass] = 255
    res = np.dstack([grey, grey, grey, alpha]).astype(np.uint8)
    return Image.fromarray(res, "RGBA")


def build(car_id, spec):
    folder = OUT / car_id
    folder.mkdir(parents=True, exist_ok=True)
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if src is None:
        sys.exit("usage: make_builtin_cars.py <folder with the car captures>")
    data = dict(name=spec["name"], platform=spec["platform"], clean=spec["clean"], glass=True, front_side=spec["front_side"],
                front_top="down", views={}, zones={})
    for view, fn in spec["files"].items():
        path = src / fn
        base = neutral_base(Image.open(path), spec["windows"][view], spec["recolour"])
        tmp = folder / f"_{view}.png"
        base.save(tmp)
        cropped, offset, canvas = crop_view(tmp)
        tmp.unlink()
        name = f"{view}.webp"
        cropped.save(folder / name, "WEBP", quality=94, method=6)
        data["views"][view] = dict(file=name, offset=offset, size=list(cropped.size))
        data["canvas"] = canvas
    for view in data["views"]:
        data["zones"][view] = side_zones_clear_of_wheels(data["front_side"]) if view == "side" else default_zones(view, data["front_side"], data["front_top"])
    side_w, side_h = data["views"]["side"]["size"]
    data["wheels"] = {"side": [[round(cx / side_w, 5), round(cy / side_h, 5), round(r / side_w, 5)] for cx, cy, r in spec["wheels"]["side"]]}
    data["default_wheel"] = spec["default_wheel"]
    old = folder / "car.json"
    if old.exists():        # keep the sponsor zones that were fitted by hand when the pictures are rebuilt
        keep = json.loads(old.read_text(encoding="utf-8"))
        if "zones" in keep:
            data["zones"] = keep["zones"]
    old.write_text(json.dumps(data, indent=1), encoding="utf-8", newline="\n")
    print(car_id, {v: i["size"] for v, i in data["views"].items()}, "canvas", data["canvas"])


if __name__ == "__main__":
    for cid, spec in CARS.items():
        build(cid, spec)
