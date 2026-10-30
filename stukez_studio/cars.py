"""Car library: Substance Painter captures of a car (side, top, front, rear) stored in the vault with sponsor zones.

Each car lives in `Project Library/Car Templates/<Car>/` as cropped WebP views (full resolution, transparent
background) plus `car.json` with the orientation of the views and the 12 sponsor zones per view. Zones are fractions
of the cropped view image: [x, y, w, h], so they survive any scaling. Originals stay where they are.
"""
import json
import os
import re
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
VIEWS = ("side", "top")   # the views the app works with for now; front and rear have zone defaults but are not offered
HINTS = {"side": ("side",), "top": ("top",), "front": ("front",), "rear": ("rear", "back")}
IMAGE_EXT = (".png", ".webp", ".tga")
VIEW_WORD = re.compile(r"(?i)\b(side|top|front|rear|back)\s*(view|shot)?\b")
MARGIN = 10
ZONE_NAMES = {1: "Windshield banner", 2: "Hood", 3: "Front bumper / lip", 4: "Front fender", 5: "Door upper",
              6: "Door lower / side skirt", 7: "Rear quarter", 8: "Roof", 9: "Trunk lid / wing", 10: "Rear bumper",
              11: "Mirrors", 12: "Rear and side glass"}


# ---------------------------------------------------------------------- default zones
# centre-from-front, centre-from-top, width, height as fractions of the side silhouette (taken from the car
# of the Placement preview, front on the right there)
_SIDE = {2: (.151, .513, .117, .124), 3: (.038, .85, .063, .124), 4: (.18, .611, .105, .124), 5: (.519, .628, .23, .212),
         6: (.519, .885, .272, .106), 7: (.759, .602, .126, .177), 10: (.962, .867, .059, .106)}
# x, y, w, h as fractions of the top silhouette with the front up
_TOP = {1: (.157, .266, .686, .044), 2: (.229, .095, .543, .112), 3: (.25, .034, .5, .039), 8: (.179, .388, .643, .171),
        9: (.143, .78, .714, .107), 10: (.179, .934, .643, .034), 11: (0.0, .3, .1, .05), 12: (.214, .627, .571, .054)}
_FRONT = {1: (.2, .15, .6, .07), 2: (.2, .42, .6, .1), 3: (.18, .8, .64, .1)}
_REAR = {12: (.22, .22, .56, .1), 9: (.2, .45, .6, .1), 10: (.18, .8, .64, .1)}


def side_zones_clear_of_wheels(front_side="left"):
    """The suggested side zones with the front fender and the rear quarter lifted clear of the wheels, for cars that keep their own wheels."""
    z = default_zones("side", front_side, "down")
    for key, (cu, cv, w, h) in {"4": (.205, .50, .085, .10), "7": (.795, .45, .10, .11)}.items():
        cx = cu if front_side == "left" else 1 - cu
        z[key] = [round(cx - w / 2, 4), round(cv - h / 2, 4), w, h]
    return z


def default_zones(view, front_side="left", front_top="down"):
    out = {}
    if view == "side":
        for z, (cu, cv, w, h) in _SIDE.items():
            cx = cu if front_side == "left" else 1 - cu
            out[z] = [max(0.0, cx - w / 2), cv - h / 2, w, h]
    elif view == "top":
        for z, (x, y, w, h) in _TOP.items():
            out[z] = [x, y if front_top == "up" else 1 - y - h, w, h]
    else:
        out = {z: list(v) for z, v in (_FRONT if view == "front" else _REAR).items()}
    return {str(z): [round(v, 4) for v in box] for z, box in out.items()}


# ---------------------------------------------------------------------- image handling
def find_views(folder):
    """Guess the four view files in a folder from their names (Side View.png, Top View.png, front.png, Rear.png ...)."""
    files = [f for f in sorted(Path(folder).iterdir()) if f.suffix.lower() in IMAGE_EXT]
    found = {}
    for view in VIEWS:
        hit = next((f for f in files if any(k in f.stem.lower() for k in HINTS[view])), None)
        if hit:
            found[view] = hit
    return found


def scan_folder(root, max_depth=3):
    """Cars found in a folder tree: [{name, views: {view: Path}, folder}].

    Files are grouped per directory and per name once the view word is removed: `ER34/Sideview.png` + `ER34/Top View.png`
    is the car "ER34", `S13 side.png` + `S13 top.png` in one folder is the car "S13". Only the views the app uses are kept."""
    root = Path(root)
    groups = {}
    for dp, dns, fns in os.walk(root):
        if len(Path(dp).relative_to(root).parts) >= max_depth:
            dns[:] = []
        for fn in sorted(fns):
            p = Path(dp) / fn
            m = VIEW_WORD.search(p.stem) if p.suffix.lower() in IMAGE_EXT else None
            if not m:
                continue
            view = "rear" if m.group(1).lower() == "back" else m.group(1).lower()
            if view not in VIEWS:
                continue
            key = re.sub(r"[\s_\-]+", " ", VIEW_WORD.sub(" ", p.stem)).strip(" -_")
            groups.setdefault((dp, key), {}).setdefault(view, p)
    per_dir = {}
    for (dp, key), views in groups.items():
        per_dir.setdefault(dp, {})[key] = views
    cars = []
    for dp, keyed in per_dir.items():
        folder = Path(dp)
        parts = folder.relative_to(root).parts
        folder_name = root.name if not parts else parts[0] if len(parts) == 1 else f"{parts[-2]} - {parts[-1]}"
        complete = sum(1 for views in keyed.values() if len(views) >= 2)
        if len(keyed) > 3 and complete < 2:   # many names but hardly any with both views: the same car in many liveries
            merged = {}
            for views in keyed.values():
                for v, f in views.items():
                    merged.setdefault(v, f)
            cars.append(dict(name=folder_name, views=merged, folder=folder))
        else:
            cars += [dict(name=key or folder_name, views=views, folder=folder) for key, views in keyed.items()]
    seen = set()
    for c in sorted(cars, key=lambda c: str(c["folder"])):    # a name used twice gets its parent folder after it
        if CarLibrary.safe_name(c["name"]).lower() in seen:
            c["name"] = f"{c['name']} ({c['folder'].parent.name or c['folder'].name})"
        seen.add(CarLibrary.safe_name(c["name"]).lower())
    return sorted(cars, key=lambda c: c["name"].lower())


def crop_view(path):
    """(cropped RGBA image, offset, canvas size) of a capture; the crop keeps a small margin around the car."""
    im = Image.open(path).convert("RGBA")
    box = im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox() or (0, 0, im.width, im.height)
    x0, y0 = max(0, box[0] - MARGIN), max(0, box[1] - MARGIN)
    x1, y1 = min(im.width, box[2] + MARGIN), min(im.height, box[3] + MARGIN)
    return im.crop((x0, y0, x1, y1)), [x0, y0], [im.width, im.height]


def guess_front_side(img):
    """Which end of a side view is the front? The hood sits lower than the trunk deck, so the end with the lower top
    edge is the front. Returns 'left' or 'right'."""
    a = np.asarray(img.getchannel("A")) > 8
    w = a.shape[1]
    tops = np.where(a.any(axis=0), a.argmax(axis=0), a.shape[0])      # first opaque row per column (smaller = higher)
    k = max(2, int(w * .15))
    left, right = tops[:k][tops[:k] < a.shape[0]], tops[-k:][tops[-k:] < a.shape[0]]
    if not len(left) or not len(right):
        return "left"
    return "left" if left.mean() > right.mean() else "right"


class Car:
    def __init__(self, folder, data):
        self.folder, self.data = Path(folder), data
        self.id = self.folder.name

    # -- plain fields
    name = property(lambda s: s.data["name"])
    platform = property(lambda s: s.data.get("platform", ""))
    front_side = property(lambda s: s.data.get("front_side", "left"))
    front_top = property(lambda s: s.data.get("front_top", "down"))
    clean = property(lambda s: bool(s.data.get("clean", False)))
    glass = property(lambda s: bool(s.data.get("glass", True)))   # white areas of a clean base are windows (drawn dark)
    canvas = property(lambda s: s.data.get("canvas", [2488, 993]))

    def views(self):
        return [v for v in VIEWS if v in self.data["views"]]

    def placed(self):
        """True once the sponsor zones of any view differ from the suggestion, i.e. the car has been placed by hand."""
        return any(self.zones(v) != default_zones(v, self.front_side, self.front_top) for v in self.views())

    def _mirror_zones(self, zones, view):
        """The zones as seen after the view is turned the other way (mirrored left-right, or the top view turned 180°)."""
        out = {}
        for z, (x, y, w, h) in zones.items():
            out[z] = [1 - x - w, (1 - y - h) if view == "top" else y, w, h]
        return out

    def flip_view(self, view):
        """Turn the car the other way: the side view is mirrored, the top view rotated 180°. The stored image, its place on
        the canvas, the zones and the front direction all follow."""
        info = self.data["views"][view]
        cw, ch = self.canvas
        w, h = info["size"]
        ox, oy = info["offset"]
        img = Image.open(self.view_path(view)).convert("RGBA")
        if view == "top":
            img = img.transpose(Image.ROTATE_180)
            info["offset"] = [cw - ox - w, ch - oy - h]
            self.data["front_top"] = "up" if self.front_top == "down" else "down"
        else:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
            info["offset"] = [cw - ox - w, oy]
            self.data["front_side"] = "right" if self.front_side == "left" else "left"
        img.save(self.view_path(view), "WEBP", quality=95, method=6)
        self.set_zones(view, self._mirror_zones(self.zones(view), view))
        self.save()

    def copy_zones_from(self, other, view):
        """Take the sponsor placement of another car; mirrored if that car faces the other way."""
        zones = {z: list(b) for z, b in other.zones(view).items()}
        if other.front_of(view) != self.front_of(view):
            zones = self._mirror_zones(zones, view)
        self.set_zones(view, zones)
        self.save()

    def view_path(self, view):
        return self.folder / self.data["views"][view]["file"]

    def mask_path(self, view):
        """A grey image the size of the view where it is white on the paint: only the paint is coloured, the rest keeps its colours."""
        f = self.data["views"][view].get("mask")
        p = self.folder / f if f else None
        return p if p is not None and p.exists() else None

    def view_info(self, view):
        return self.data["views"][view]

    def zones(self, view):
        z = self.data.get("zones", {}).get(view)
        return z if z else default_zones(view, self.front_side, self.front_top)

    def set_zones(self, view, zones):
        self.data.setdefault("zones", {})[view] = {str(k): [round(float(x), 4) for x in v] for k, v in zones.items()}

    def save(self):
        (self.folder / "car.json").write_text(json.dumps(self.data, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")

    def front_of(self, view):
        return {"side": self.front_side, "top": self.front_top}.get(view, "")


BUILTIN_DIR = Path(__file__).resolve().parent / "builtin"


# the first is the default preview car; made by make_default_car.py, make_builtin_cars.py and make_builtin_illustrations.py
BUILTIN_ORDER = ("s13-silvia", "s15-raijin")


def builtin_cars():
    """The cars that ship with the program, in the order of BUILTIN_ORDER; missing ones are left out."""
    out = []
    for cid in BUILTIN_ORDER:
        f = BUILTIN_DIR / cid / "car.json"
        if f.exists():
            out.append(Car(f.parent, json.loads(f.read_text(encoding="utf-8"))))
    return out


class CarLibrary:
    def __init__(self, vault):
        self.vault = vault
        self.root = vault.lib / "Car Templates"
        self._cars = None

    def cars(self, reload=False):
        if self._cars is None or reload:
            out = []
            if self.root.exists():
                for f in sorted(self.root.glob("*/car.json")):
                    try:
                        out.append(Car(f.parent, json.loads(f.read_text(encoding="utf-8"))))
                    except (ValueError, KeyError):
                        continue
            self._cars = out
        return self._cars

    def all_cars(self):
        """Every car the previews can use: the ones that ship with the program first, then the library's."""
        return builtin_cars() + self.cars()

    def get(self, car_id):
        return next((c for c in self.cars() if c.id == car_id), None)

    @staticmethod
    def safe_name(name):
        return re.sub(r'[\\/:*?"<>|]', "-", name).strip()

    def add_car(self, name, files, platform="", front_side=None, front_top="down", clean=False, overwrite=False, index=True):
        """files: {view: path}. Crops and stores the views, returns the new Car (index=False skips the overview note)."""
        name = self.safe_name(name)
        if not name or not files:
            raise ValueError("A car needs a name and at least one view")
        folder = self.root / name
        if folder.exists() and not overwrite:
            raise FileExistsError(f"A car called {name} already exists")
        folder.mkdir(parents=True, exist_ok=True)
        data = dict(name=name, platform=platform, clean=clean, front_top=front_top, views={}, zones={})
        for view in VIEWS:
            if view not in files:
                continue
            img, offset, canvas = crop_view(files[view])
            fn = f"{name} - {view}.webp"
            img.save(folder / fn, "WEBP", quality=92, method=6)
            data["views"][view] = dict(file=fn, offset=offset, size=list(img.size))
            data["canvas"] = canvas
            if view == "side" and front_side is None:
                front_side = guess_front_side(img)
        data["front_side"] = front_side or "left"
        car = Car(folder, data)
        for view in car.views():
            car.set_zones(view, default_zones(view, car.front_side, car.front_top))
        car.save()
        self._cars = None
        if index:
            self.rebuild_index()
        return car

    def remove_car(self, car):
        import shutil
        shutil.rmtree(car.folder)
        self._cars = None
        self.rebuild_index()

    def rebuild_index(self):
        """`Car Templates.md`: an overview note for Obsidian (generated, do not edit by hand)."""
        cars = self.cars()
        lines = ["---", "tags: [car-templates]", "---", "", "# Car Templates", "",
                 "Generated by StukeZ Designworks Studio. Substance Painter captures of the cars (cropped, transparent background, "
                 "full resolution) with the sponsor zones used by the livery previews and the Illustrator templates. "
                 "Add or edit cars in the **Cars** page of the app.", "",
                 f"{len(cars)} cars.", ""]
        for c in cars:
            lines += [f"## {c.name}", "", f"Platform: {c.platform or 'not set'} · front of the side view: {c.front_side} · "
                      f"{'clean grey base' if c.clean else 'capture with an existing livery (silhouette only)'}", ""]
            lines += [f"![[{c.data['views'][v]['file']}|400]]" for v in c.views()]
            lines.append("")
        self.root.mkdir(parents=True, exist_ok=True)
        (self.vault.lib / "Car Templates.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
