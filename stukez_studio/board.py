"""Livery board: sponsor logos and tribals placed freely on a car, recoloured with the palette or any colour.

A board is a list of items; each item is an imported image with a place on one view of the car (centre and width as
fractions of the view, so it survives any scaling), a turn, a colour (the logo's own, a slot of the palette or a custom
colour/gradient) and an optional outline. Boards are saved as `Project Library/Boards/<name>.json`; imported images are
copied to `Boards/Logos/`, so a board never depends on a file outside the workspace.
"""
import json
import os
import re
import uuid
from collections import OrderedDict
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QFontMetrics, QImage, QPainter, QTransform

from . import outlines as ol
from . import palette as pal

VIEWS = ("side", "top")
KINDS = (("sponsor", "Sponsor logo"), ("tribal", "Tribal"))
SOURCES = (("original", "The logo's own colours"), ("sponsor_a", "Sponsor A"), ("sponsor_b", "Sponsor B"), ("tribal", "Tribal colour"),
           ("base", "Base colour"), ("custom", "Custom colour or gradient"))
OUTLINE_MODES = (("auto", "From the palette"), ("custom", "Custom colour or gradient"))
IMPORT_EXT = (".png", ".webp", ".jpg", ".jpeg", ".bmp", ".tga", ".svg")
SRC_MAX = 2000          # longest side a stored logo keeps
TIERS = (160, 320, 640, 1100)      # sizes the processed images are made at; the one just above what is drawn is used
OUTLINE_DEFAULT = 3.0   # outline thickness in percent of the logo's longer side
CACHE_SIZE = 160

_sources = {}
_prepared = OrderedDict()


# ---------------------------------------------------------------------- the item
def default_item(kind="sponsor", view="side", file="", name=""):
    tribal = kind == "tribal"
    return dict(id=uuid.uuid4().hex[:8], name=name, kind=kind, file=file, view=view, x=.5, y=.5, w=.16 if not tribal else .4,
                rot=0.0, flip=False, opacity=1.0, bg="auto",
                colour=dict(mode="tribal" if tribal else "original", value="#FFFFFF"),
                outline=dict(on=tribal, mode="auto", value=ol.DEFAULT_OUTLINE, size=OUTLINE_DEFAULT))


def clean_item(d):
    """An item from a file or the UI with every field present and in range."""
    base = default_item(d.get("kind", "sponsor") if d.get("kind") in dict(KINDS) else "sponsor", d.get("view", "side"), d.get("file", ""), d.get("name", ""))
    base["id"] = str(d.get("id") or base["id"])
    for k in ("x", "y", "w", "rot", "opacity"):
        try:
            base[k] = float(d.get(k, base[k]))
        except (TypeError, ValueError):
            pass
    base["x"], base["y"] = round(min(1.5, max(-.5, base["x"])), 4), round(min(1.5, max(-.5, base["y"])), 4)
    base["w"] = round(min(2.0, max(.01, base["w"])), 4)
    base["rot"] = round(((base["rot"] + 180) % 360) - 180, 1)
    base["opacity"] = round(min(1.0, max(.05, base["opacity"])), 2)
    base["flip"] = bool(d.get("flip", False))
    base["bg"] = d.get("bg") if d.get("bg") in ("auto", "keep", "remove") else "auto"
    c = d.get("colour") or {}
    if c.get("mode") in dict(SOURCES):
        base["colour"]["mode"] = c["mode"]
    base["colour"]["value"] = _clean_value(c.get("value"), base["colour"]["value"])
    o = d.get("outline") or {}
    base["outline"]["on"] = bool(o.get("on", base["outline"]["on"]))
    if o.get("mode") in dict(OUTLINE_MODES):
        base["outline"]["mode"] = o["mode"]
    base["outline"]["value"] = _clean_value(o.get("value"), base["outline"]["value"])
    try:
        base["outline"]["size"] = min(12.0, max(.3, float(o.get("size", base["outline"]["size"]))))
    except (TypeError, ValueError):
        pass
    return base


def _clean_value(v, fallback):
    cs = v if isinstance(v, (list, tuple)) else [v]
    ok = [pal.valid_hex(c) for c in cs if isinstance(c, str)]
    ok = [c for c in ok if c]
    if len(ok) >= 2:
        return ok[:2]
    return ok[0] if ok else fallback


def palette_ns(d):
    """A namespace with the seven palette slots from a dict or an object (a project, the New project page)."""
    get = (lambda k: d.get(k)) if isinstance(d, dict) else (lambda k: getattr(d, k, None))
    fall = dict(base="#1E1B2E", tribal="#6E8B1F", tribal_outline=ol.DEFAULT_OUTLINE, sponsor_a="#F5F0F1", sponsor_a_outline=ol.DEFAULT_OUTLINE,
                sponsor_b="#F5F0F1", sponsor_b_outline=ol.DEFAULT_OUTLINE)
    out = {}
    for k, v in fall.items():
        val = get(k)
        out[k] = list(val) if isinstance(val, (list, tuple)) else (val or v)
    for k in ("cut_angle", "cut_pos", "cut_span", "paint"):
        if get(k) is not None:
            out[k] = get(k)
    return SimpleNamespace(**out)


def _slot(pl, key):
    v = getattr(pl, key)
    return list(v)[:2] if isinstance(v, (list, tuple)) else v


def resolve_colour(item, pl):
    """None (keep the logo's colours), a hex or a [hex, hex] gradient."""
    c = item["colour"]
    if c["mode"] == "original":
        return None
    return c["value"] if c["mode"] == "custom" else _slot(pl, c["mode"])


def resolve_outline(item, pl):
    """None or a hex / [hex, hex] for the outline of an item."""
    o = item["outline"]
    if not o["on"]:
        return None
    if o["mode"] == "custom":
        return o["value"]
    mode = item["colour"]["mode"]
    key = {"sponsor_b": "sponsor_b_outline", "tribal": "tribal_outline"}.get(mode)
    if key is None:
        key = "tribal_outline" if item["kind"] == "tribal" else "sponsor_a_outline"
    return _slot(pl, key)


# ---------------------------------------------------------------------- image work
def _rasterize_svg(path, width=SRC_MAX):
    try:
        from PySide6.QtSvg import QSvgRenderer
    except ImportError as e:     # pragma: no cover - only if QtSvg is missing from a build
        raise ValueError("This build of the program cannot read SVG files. Save the logo as PNG instead.") from e
    r = QSvgRenderer(str(path))
    if not r.isValid():
        raise ValueError(f"{Path(path).name} is not a readable SVG file")
    size = r.defaultSize()
    if size.width() <= 0 or size.height() <= 0:
        size = r.viewBoxF().size().toSize()
    ar = size.height() / size.width() if size.width() else 1.0
    w = width
    h = max(1, round(width * ar))
    if h > width:
        h, w = width, max(1, round(width / ar))
    img = QImage(w, h, QImage.Format_RGBA8888)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    r.render(p)
    p.end()
    return Image.frombytes("RGBA", (w, h), bytes(img.constBits())[: w * h * 4]) if img.bytesPerLine() == w * 4 else \
        Image.frombuffer("RGBA", (w, h), img.constBits(), "raw", "RGBA", img.bytesPerLine(), 1).copy()


def read_image(path):
    """Any importable file as an RGBA image no bigger than SRC_MAX."""
    path = Path(path)
    if path.suffix.lower() == ".svg":
        im = _rasterize_svg(path)
    else:
        im = Image.open(path)
        im.load()
        im = im.convert("RGBA")
    if max(im.size) > SRC_MAX:
        im.thumbnail((SRC_MAX, SRC_MAX), Image.LANCZOS)
    return im


def _corners_plain(arr):
    h, w = arr.shape[:2]
    c = np.array([arr[0, 0, :3], arr[0, w - 1, :3], arr[h - 1, 0, :3], arr[h - 1, w - 1, :3]], np.float32)
    return bool(c.std(axis=0).max() < 14)


def soft_key(im, tol=40):
    """The plain background (the colour of the corners) turned transparent, with a soft edge."""
    arr = np.asarray(im).astype(np.float32)
    h, w = arr.shape[:2]
    bg = np.median(np.array([arr[0, 0, :3], arr[0, w - 1, :3], arr[h - 1, 0, :3], arr[h - 1, w - 1, :3]]), axis=0)
    dist = np.abs(arr[..., :3] - bg).max(axis=2)
    k = np.clip((dist - tol * .55) / (tol * 1.1), 0, 1)
    out = arr.copy()
    out[..., 3] = arr[..., 3] * k
    return Image.fromarray(out.astype(np.uint8), "RGBA")


def _background(im, mode):
    arr = np.asarray(im)
    if mode == "keep":
        return im
    if mode == "auto" and not (arr[..., 3].min() >= 250 and _corners_plain(arr)):
        return im
    return soft_key(im)


def trim(im, pad=1):
    box = im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    if not box:
        return im
    return im.crop((max(0, box[0] - pad), max(0, box[1] - pad), min(im.width, box[2] + pad), min(im.height, box[3] + pad)))


def _hex_rgb(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float32)


def recolour(im, colour):
    """The logo's shape in one colour, or in a gradient that rises at 45 degrees from the first colour to the second."""
    arr = np.asarray(im).copy()
    h, w = arr.shape[:2]
    if isinstance(colour, (list, tuple)):
        c0, c1 = _hex_rgb(colour[0]), _hex_rgb(colour[1])
        tx = np.linspace(0, 1, w, dtype=np.float32)[None, :]
        ty = np.linspace(1, 0, h, dtype=np.float32)[:, None]
        t = ((tx + ty) / 2)[..., None]
        arr[..., :3] = np.clip(c0 * (1 - t) + c1 * t, 0, 255).astype(np.uint8)
    else:
        arr[..., :3] = _hex_rgb(colour).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def _source(path):
    """The stored image, trimmed of empty margins, read once per file version."""
    mt = path.stat().st_mtime_ns
    hit = _sources.get(path)
    if hit is None or hit[0] != mt:
        _sources[path] = hit = (mt, read_image(path))
        if len(_sources) > 80:
            _sources.pop(next(iter(_sources)))
    return hit


class Prepared:
    """A logo ready to draw: the image with outline, and where the logo itself sits in it."""

    def __init__(self, image, content, ok=True):
        self.image = image           # QImage, RGBA
        self.content = content       # (w, h) of the logo inside the image, same unit as image.size
        self.ok = ok


def _tier(need):
    return next((t for t in TIERS if t >= need), TIERS[-1])


def prepare(item, pl, folder, need=400):
    """The item's image coloured and outlined for the palette `pl`, big enough for about `need` pixels on its longer side."""
    path = Path(folder) / item["file"]
    colour, outline = resolve_colour(item, pl), resolve_outline(item, pl)
    try:
        mt = path.stat().st_mtime_ns
        sw, sh = _source(path)[1].size
    except (OSError, ValueError):
        return MISSING
    tier = _tier(need * max(1.0, sh / max(1, sw)))      # a tall logo needs more pixels on its longer side
    key = (str(path), mt, tier, item["bg"], repr(colour), repr(outline), round(item["outline"]["size"], 2) if outline else 0)
    hit = _prepared.get(key)
    if hit is not None:
        _prepared.move_to_end(key)
        return hit
    try:
        im = _background(_source(path)[1], item["bg"])
        im = trim(im)
        if max(im.size) > tier:
            im = im.resize((max(1, round(im.width * tier / max(im.size))), max(1, round(im.height * tier / max(im.size)))), Image.LANCZOS)
        if colour is not None:
            im = recolour(im, colour)
        content = im.size
        if outline is not None:
            c1, c2 = (outline[0], outline[1]) if isinstance(outline, list) else (outline, "")
            thick = max(1, round(item["outline"]["size"] / 100 * max(im.size)))
            res = ol.make(im, ol.Spec(colour=c1, colour2=c2, thickness=thick))
            im = res["combined"]
        qi = QImage(im.tobytes("raw", "RGBA"), im.width, im.height, im.width * 4, QImage.Format_RGBA8888).copy()
        out = Prepared(qi, content)
    except Exception:    # a broken file must not take the whole board down
        out = MISSING
    _prepared[key] = out
    if len(_prepared) > CACHE_SIZE:
        _prepared.popitem(last=False)
    return out


MISSING = Prepared(QImage(), (1, 1), ok=False)


def clear_cache():
    _prepared.clear()
    _sources.clear()


# ---------------------------------------------------------------------- geometry
def item_size(item, T, prep):
    """(logo width, logo height) in pixels for the car view drawn in rectangle T."""
    lw = item["w"] * T.width()
    cw, ch = prep.content
    return lw, lw * ch / max(1, cw)


def item_transform(item, T):
    """Maps the item's own pixels (origin at its centre) to the widget: move to its place, turn, mirror."""
    t = QTransform()
    t.translate(T.x() + item["x"] * T.width(), T.y() + item["y"] * T.height())
    t.rotate(item["rot"])
    if item["flip"]:
        t.scale(-1, 1)
    return t


def hit(item, T, prep, pt):
    """Is the widget point `pt` on the item's box (the logo, without its outline)?"""
    lw, lh = item_size(item, T, prep)
    inv, ok = item_transform(item, T).inverted()
    if not ok:
        return False
    q = inv.map(QPointF(pt))
    m = 3.0
    return abs(q.x()) <= lw / 2 + m and abs(q.y()) <= lh / 2 + m


def paint_items(p, T, items, pl, folder, view, selected=None, dpr=1.0):
    """Draw the items of `view` over a car drawn in rectangle T, in list order (the last is on top)."""
    p.save()
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.setRenderHint(QPainter.Antialiasing)
    for it in items:
        if it["view"] != view:
            continue
        prep = prepare(it, pl, folder, need=it["w"] * T.width() * dpr * 1.1)
        if not prep.ok:
            continue
        lw, lh = item_size(it, T, prep)
        cw, ch = prep.content
        iw, ih = prep.image.width(), prep.image.height()
        dw, dh = lw * iw / max(1, cw), lh * ih / max(1, ch)
        p.save()
        p.setTransform(item_transform(it, T), True)
        p.setOpacity(it["opacity"])
        p.drawImage(QRectF(-dw / 2, -dh / 2, dw, dh), prep.image)
        p.restore()
    p.restore()


# ---------------------------------------------------------------------- the board on disk
def safe_name(name):
    return re.sub(r'[\\/:*?"<>|]', "-", name).strip(" .") or "Untitled"


class Board:
    def __init__(self, vault_lib, name="Untitled"):
        self.root = Path(vault_lib) / "Boards"
        self.name = safe_name(name)
        self.items = []                 # item dicts, the last one on top
        self.source = 0                 # 0 = the New project page, otherwise a project id

    @property
    def path(self):
        return self.root / f"{self.name}.json"

    @staticmethod
    def names(vault_lib):
        root = Path(vault_lib) / "Boards"
        return sorted(f.stem for f in root.glob("*.json")) if root.exists() else []

    def find(self, item_id):
        return next((it for it in self.items if it["id"] == item_id), None)

    def save(self):
        self.root.mkdir(parents=True, exist_ok=True)
        data = dict(version=1, name=self.name, source=self.source, items=self.items)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
        tmp.replace(self.path)

    @classmethod
    def load(cls, vault_lib, name):
        b = cls(vault_lib, name)
        data = json.loads(b.path.read_text(encoding="utf-8"))
        b.source = int(data.get("source", 0) or 0)
        b.items = [clean_item(d) for d in data.get("items", []) if isinstance(d, dict) and d.get("file")]
        return b

    def delete(self):
        if self.path.exists():
            self.path.unlink()

    def import_file(self, src, kind="sponsor", view="side", name=None, colour=None):
        """Copy an image into the board's Logos folder (SVG is drawn to PNG) and add it as an item; returns the item.

        `colour` is a colour source of SOURCES to start with (a logo master is one ink, so it needs one)."""
        src = Path(src)
        if src.suffix.lower() not in IMPORT_EXT:
            raise ValueError(f"{src.name}: only PNG, WebP, JPG, BMP, TGA and SVG files can be placed")
        return self._add_image(read_image(src), safe_name(src.stem), name or src.stem, kind, view, colour)

    def add_text(self, text, kind="sponsor", view="side", colour="sponsor_a"):
        """A sponsor made from a name when there is no logo: bold letters, drawn to a PNG, coloured like Sponsor A."""
        text = text.strip()
        if not text:
            raise ValueError("Type a name first")
        return self._add_image(text_image(text), "Text - " + safe_name(text)[:40], text, kind, view, colour)

    def _add_image(self, im, stem, name, kind, view, colour):
        folder = self.root / "Logos"
        folder.mkdir(parents=True, exist_ok=True)
        stem = stem[:60]
        fn = f"{stem}.png"
        n = 2
        while (folder / fn).exists():
            fn = f"{stem} {n}.png"
            n += 1
        im.save(folder / fn, "PNG")
        it = default_item(kind, view, f"Logos/{fn}", name)
        if colour in dict(SOURCES):
            it["colour"]["mode"] = colour
        n = sum(1 for o in self.items if o["view"] == view)
        it["x"], it["y"] = min(.8, .35 + .06 * (n % 6)), min(.8, .4 + .05 * (n % 6))      # not exactly on top of the last one
        self.items.append(it)
        return it

    def unused_files(self):
        used = {it["file"] for it in self.items}
        logos = self.root / "Logos"
        return [f for f in sorted(logos.glob("*.png")) if f"Logos/{f.name}" not in used] if logos.exists() else []


def text_image(text, px=260):
    """The text in heavy italic letters as a white-on-transparent RGBA image (it takes any colour on the car)."""
    fams = QFontDatabase.families()
    f = QFont(next((n for n in ("Bahnschrift", "Segoe UI Black", "Segoe UI", "Arial") if n in fams), "Arial"))
    f.setWeight(QFont.Black if "Black" in f.family() else QFont.ExtraBold)
    f.setPixelSize(px)
    f.setItalic(True)
    f.setLetterSpacing(QFont.AbsoluteSpacing, px * .02)
    fm = QFontMetrics(f)
    w, h = fm.horizontalAdvance(text) + px // 2, fm.height() + px // 4
    img = QImage(w, h, QImage.Format_RGBA8888)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    p.setFont(f)
    p.setPen(QColor("white"))
    p.drawText(img.rect(), Qt.AlignCenter, text)
    p.end()
    return trim(Image.frombuffer("RGBA", (w, h), bytes(img.constBits()), "raw", "RGBA", img.bytesPerLine(), 1).copy())


def library_logos(vault):
    """[(brand, file)] of the logos of the vault's logo library that are on this computer, one per brand, by name."""
    try:
        _pp, idx = vault.placement()
    except Exception:       # the library is optional: a workspace may have none
        return []
    out = {}
    for key, rows in idx.items():
        for r in rows:
            fp = r.get("full_path")
            if fp and os.path.exists(fp):
                out[(r.get("brand") or r.get("entity") or key).strip()] = fp
                break
    return sorted(out.items(), key=lambda kv: kv[0].lower())


def render_scene(car, view, pl, items, folder, width, background=True):
    """The car with the items on it as a QImage `width` pixels wide (the car's own transparent background if background is False)."""
    from . import carrender
    size = car.view_info(view)["size"]
    h = max(1, round(width * size[1] / size[0]))
    img = QImage(width, h, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    if background:
        p.fillRect(img.rect(), QColor("#E9E6E7"))
    p.drawImage(QRectF(0, 0, width, h), carrender.render(car, view, pl, width, plates={}))
    paint_items(p, QRectF(0, 0, width, h), items, pl, folder, view)
    p.end()
    return img
