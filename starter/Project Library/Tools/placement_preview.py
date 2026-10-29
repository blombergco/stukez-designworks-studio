"""Placement preview images: one PNG per project with a side view and a top view of a generic car.

Reads the project note (palette) and the Build sheet (12-zone sponsor kit), recolours the real logo masters of
the Ash Works pack (read only, D:) to Sponsor A / B, and draws a bold text stand-in where the pack has no logo.
Nothing on D: is written. Output: `Project Library/Placement previews/NNN Name - Placement.webp` (WebP keeps the 236 images near 15 MB).

Run:  py -3 -I placement_preview.py            (all projects)
      py -3 -I placement_preview.py 1 17 43    (selected project ids)
"""
import csv
import os
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

Image.MAX_IMAGE_PIXELS = None
LIB = Path(__file__).resolve().parent.parent
PROJECTS = LIB / 'Projects'
OUT = LIB / 'Placement previews'
LOGO_CSV = LIB / 'Sponsor Logo Library' / 'ash_works_logos.csv'
SS = 2                      # supersampling of the whole canvas
W, H = 1500, 960
FONTS = r'C:\Windows\Fonts'


def font(name, size):
    return ImageFont.truetype(f'{FONTS}\\{name}', size * SS)


def hexrgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# ---------------------------------------------------------------- parsing
def hexes(line):
    return re.findall(r'#[0-9A-Fa-f]{6}', line)


def read_project(folder):
    note = folder / f'{folder.name}.md'
    fm = note.read_text(encoding='utf-8').split('---')[1]
    pal = {}
    for line in fm.splitlines():
        m = re.match(r'(\w+):\s*(.*)', line)
        if m and m.group(1) in ('base', 'tribal', 'tribal_outline', 'sponsor_a', 'sponsor_a_outline',
                                'sponsor_b', 'sponsor_b_outline'):
            pal[m.group(1)] = hexes(m.group(2))
    return pal


ROW = re.compile(r'^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*\[\[([^\]|]+)(?:\|([^\]]+))?\]\]([^|]*)\|\s*([^|]+?)\s*\|\s*(\w+)\s*\|\s*Sponsor ([AB])')


def read_kit(folder):
    sheet = folder / f'{folder.name} - Build sheet.md'
    kit = {}
    for line in sheet.read_text(encoding='utf-8').splitlines():
        m = ROW.match(line)
        if m and int(m.group(1)) not in kit:
            z = int(m.group(1))
            kit[z] = dict(zone=z, name=m.group(2), brand=(m.group(4) or m.group(3)).strip(),
                          size={'large': 1.0, 'medium': 0.8, 'small': 0.6}.get(m.group(7), 0.8),
                          fill=m.group(8))
    return kit


# ---------------------------------------------------------------- logos
def norm(s):
    for bad, good in (('Ã–', 'O'), ('Ã¶', 'o')):
        s = s.replace(bad, good)
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', s)


GENERIC = ('wheels', 'wheel', 'racing', 'performance', 'tires', 'tire', 'motorsport', 'motorsports', 'engineering',
           'suspension', 'company', 'corporation', 'corp', 'usa')


def short(brand):
    """Brand without a parenthetical note, e.g. 'Rev Style (Osaka Street Drift Team)' -> 'Rev Style'."""
    return re.sub(r'\s*\(.*?\)', '', brand).strip()


def core(brand):
    n = norm(short(brand))
    for g in GENERIC:
        if n.endswith(g) and len(n) > len(g) + 2:
            return n[:-len(g)]
    return n


MASTER_CSV = LIB / 'Sponsor Logo Library' / 'Core folders' / 'master_list.csv'
DROP_IN = LIB / 'Sponsor Logo Library' / 'Logo masters'


def load_logo_index():
    """Ash Works pack first (rows have an aspect ratio); then single-ink masters of the other core folders."""
    idx = {}
    with open(LOGO_CSV, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            idx.setdefault(core(r['brand']), []).append(r)
    with open(MASTER_CSV, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            k = core(r['entity'])
            if k in idx or r['variant'] not in ('black', 'white') or r['transparent'] != 'yes':
                continue
            if r['type'].startswith(('Own', 'Sticker')):
                continue
            px = int(r['pixels'].split('x')[0])
            if px < 1000:
                continue
            idx.setdefault(k, []).append(dict(r, aspect_ratio='', weight='', source='master', px=px))
    # drop-in folder for new masters named Brand__black__4096px.png or Brand__white__4096px.png (read only; optional)
    if DROP_IN.is_dir():
        for fp in DROP_IN.glob('*.png'):
            parts = fp.stem.split('__')
            if len(parts) >= 2 and parts[1] in ('black', 'white'):
                px = re.search(r'(\d+)px', fp.stem)
                idx.setdefault(core(parts[0].replace('_', ' ')), []).insert(0, dict(
                    variant=parts[1], px=int(px.group(1)) if px else 9999, full_path=str(fp), source='master'))
    return idx


def find_logo(brand, ratio, idx):
    rows = idx.get(core(brand))
    if not rows:
        return None
    masters = [r for r in rows if r.get('source') == 'master']
    if masters and (rows[0].get('source') == 'master'):
        # a drop-in or master-list file wins over the pack; prefer black, then the widest file
        best = max(masters, key=lambda r: (r['variant'] == 'black', r['px']))
        return best['full_path'] if os.path.exists(best['full_path']) else None
    best = min(rows, key=lambda r: abs(np.log(float(r['aspect_ratio']) / ratio)) - (0.15 if r['weight'] == 'bold' else 0))
    return best['full_path'] if os.path.exists(best['full_path']) else None


_cache = {}


def logo_alpha(path):
    if path not in _cache:
        im = Image.open(path).convert('RGBA')
        im = im.crop(im.getbbox())
        if max(im.size) > 1200:
            r = 1200 / max(im.size)
            im = im.resize((round(im.size[0] * r), round(im.size[1] * r)), Image.LANCZOS)
        _cache[path] = im.split()[3]
    return _cache[path]


# ---------------------------------------------------------------- drawing helpers
def fill_image(size, cols, vertical=False):
    w, h = size
    if len(cols) == 1:
        return Image.new('RGB', size, hexrgb(cols[0]))
    n = max(w, h) if not vertical else h
    t = np.linspace(0, 1, h if vertical else w)
    c0, c1 = np.array(hexrgb(cols[0]), float), np.array(hexrgb(cols[1]), float)
    ramp = (c0[None, :] * (1 - t[:, None]) + c1[None, :] * t[:, None]).astype('uint8')
    arr = np.repeat(ramp[:, None, :], w, axis=1) if vertical else np.repeat(ramp[None, :, :], h, axis=0)
    return Image.fromarray(arr, 'RGB')


def paint(mask, cols, outline, outline_px):
    """mask (L) -> RGBA with gradient fill and an outline of outline_px."""
    pad = outline_px + 2
    m = Image.new('L', (mask.size[0] + 2 * pad, mask.size[1] + 2 * pad), 0)
    m.paste(mask, (pad, pad))
    out = Image.new('RGBA', m.size, (0, 0, 0, 0))
    if outline_px > 0:
        grown = m.filter(ImageFilter.MaxFilter(2 * outline_px + 1))
        ol = Image.new('RGBA', m.size, hexrgb(outline) + (255,))
        ol.putalpha(grown)
        out.alpha_composite(ol)
    fl = fill_image(m.size, cols).convert('RGBA')
    fl.putalpha(m)
    out.alpha_composite(fl)
    return out


def text_mask(text, box_w, box_h):
    f = font('arialbi.ttf', 100)
    probe = ImageDraw.Draw(Image.new('L', (10, 10)))
    text = text.upper()
    bb = probe.textbbox((0, 0), text, font=f)
    m = Image.new('L', (bb[2] - bb[0] + 8, bb[3] - bb[1] + 8), 0)
    ImageDraw.Draw(m).text((4 - bb[0], 4 - bb[1]), text, font=f, fill=255)
    return m.crop(m.getbbox())


def bez(p0, c, p1, n=14):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * p1[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * p1[1]) for t in np.linspace(0, 1, n)]


def body_path():
    """The generic side-view body of Assets/sponsor-zones.svg as a polygon (original units)."""
    pts = [(70, 205), (70, 168)]
    pts += bez((70, 168), (70, 152), (90, 150))
    pts += [(160, 146)]
    pts += bez((160, 146), (205, 98), (262, 92))
    pts += [(345, 92)]
    pts += bez((345, 92), (392, 96), (428, 140))
    pts += [(505, 150)]
    pts += bez((505, 150), (540, 156), (548, 180))
    pts += [(548, 205)]
    return pts


def glass_path():
    pts = [(190, 142)]
    pts += bez((190, 142), (222, 108), (268, 104))
    pts += [(338, 104)]
    pts += bez((338, 104), (372, 108), (400, 140))
    return pts


class Canvas:
    def __init__(self, bg):
        self.im = Image.new('RGBA', (W * SS, H * SS), bg + (255,))
        self.d = ImageDraw.Draw(self.im)

    def poly(self, pts, fill=None, outline=None, width=2, gradient=None, vertical=False):
        pts = [(x * SS, y * SS) for x, y in pts]
        if gradient:
            x0, y0 = min(p[0] for p in pts), min(p[1] for p in pts)
            x1, y1 = max(p[0] for p in pts), max(p[1] for p in pts)
            box = (int(x0), int(y0), int(x1) + 1, int(y1) + 1)
            mask = Image.new('L', self.im.size, 0)
            ImageDraw.Draw(mask).polygon(pts, fill=255)
            g = fill_image((box[2] - box[0], box[3] - box[1]), gradient, vertical).convert('RGBA')
            layer = Image.new('RGBA', self.im.size, (0, 0, 0, 0))
            layer.paste(g, box[:2])
            layer.putalpha(mask)
            self.im.alpha_composite(layer)
        elif fill:
            self.d.polygon(pts, fill=fill)
        if outline:
            self.d.line(pts + [pts[0]], fill=outline, width=width * SS, joint='curve')

    def rrect(self, box, r, fill=None, outline=None, width=2, gradient=None, vertical=False):
        x0, y0, x1, y1 = [v * SS for v in box]
        if gradient:
            g = fill_image((int(x1 - x0), int(y1 - y0)), gradient, vertical).convert('RGBA')
            mask = Image.new('L', g.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle([0, 0, g.size[0] - 1, g.size[1] - 1], radius=r * SS, fill=255)
            g.putalpha(mask)
            self.im.alpha_composite(g, (int(x0), int(y0)))
        elif fill:
            self.d.rounded_rectangle([x0, y0, x1, y1], radius=r * SS, fill=fill)
        if outline:
            self.d.rounded_rectangle([x0, y0, x1, y1], radius=r * SS, outline=outline, width=width * SS)

    def text(self, xy, s, f, fill):
        self.d.text((xy[0] * SS, xy[1] * SS), s, font=f, fill=fill)

    def place(self, tile, cx, cy):
        self.im.alpha_composite(tile, (int(cx * SS - tile.size[0] / 2), int(cy * SS - tile.size[1] / 2)))


# ---------------------------------------------------------------- the picture
SIDE = lambda x, y: ((x - 60) * 2.2 + 30, (y - 80) * 2.2 + 110)
TOP = lambda x, y: ((x - 650) * 2.0 + 1190, (y - 30) * 2.0 + 110)
SIDE_S, TOP_S = 2.2, 2.0

# zone -> (cx, cy, box w, box h) in the original 900 x 520 units
SIDE_ZONES = {2: (476, 150, 56, 14), 3: (530, 188, 30, 14), 4: (462, 161, 50, 14), 5: (300, 163, 110, 24),
              6: (300, 192, 130, 12), 7: (185, 160, 60, 20), 10: (88, 190, 28, 12)}
TOP_ZONES = {1: (720, 148, 96, 18), 2: (720, 92, 76, 46), 3: (720, 52, 70, 16), 8: (720, 224, 90, 70),
             9: (720, 372, 100, 44), 10: (720, 420, 90, 14), 11: (642, 152, 16, 22), 12: (720, 298, 80, 22)}


def sponsor_tile(entry, pal, box, scale, idx, stats):
    cols = pal['sponsor_a' if entry['fill'] == 'A' else 'sponsor_b']
    ol = (pal['sponsor_a_outline' if entry['fill'] == 'A' else 'sponsor_b_outline'] or ['#000000'])[0]
    bw, bh = box[2] * scale * entry['size'], box[3] * scale * entry['size']
    if bw < 8 or bh < 6:
        return None
    path = find_logo(entry['brand'], max(bw / bh, 0.3), idx)
    if path:
        m = logo_alpha(path)
        stats['real'] += 1
    else:
        m = text_mask(short(entry['brand']), bw, bh)
        stats['text'] += 1
    r = min(bw * SS / m.size[0], bh * SS / m.size[1])
    m = m.resize((max(1, round(m.size[0] * r)), max(1, round(m.size[1] * r))), Image.LANCZOS)
    return paint(m, cols, ol, max(1, round(m.size[1] * 0.07))), bool(path)


def render(folder, idx):
    pal = read_project(folder)
    kit = read_kit(folder)
    base = pal['base']
    tribal = pal['tribal']
    t_out = (pal['tribal_outline'] or ['#000000'])[0]
    bgc = (246, 247, 251)
    c = Canvas(bgc)
    stats = {'real': 0, 'text': 0}
    used = {}

    # title
    name = folder.name
    c.text((30, 18), name, font('segoeuib.ttf', 34), (30, 34, 44, 255))
    c.text((30, 62), 'Placement preview (generic car, schematic). Real logo masters recoloured; bold text where no master exists.',
           font('segoeui.ttf', 18), (90, 98, 115, 255))
    x = 1180
    for h_ in [base[0], base[-1], tribal[0], pal['sponsor_a'][0], pal['sponsor_b'][0]]:
        c.rrect((x, 24, x + 54, 56), 6, fill=hexrgb(h_) + (255,), outline=(120, 125, 140, 255), width=1)
        x += 62

    # --- side view
    pts = [SIDE(*p) for p in body_path()]
    c.poly(pts, outline=(60, 66, 85, 255), width=3, gradient=base)
    c.poly(pts, outline=(60, 66, 85, 255), width=3)
    # tribal blade along the body
    blade = [(74, 188), (180, 172), (300, 176), (430, 166), (522, 170), (430, 186), (300, 192), (180, 192)]
    bl = [SIDE(*p) for p in blade]
    c.poly([(x_ - 0, y_ - 0) for x_, y_ in bl], fill=None, outline=hexrgb(t_out) + (255,), width=7, gradient=tribal)
    c.poly(bl, outline=hexrgb(t_out) + (255,), width=3)
    c.poly(bl, gradient=tribal)
    gl = [SIDE(*p) for p in glass_path()]
    c.poly(gl, fill=(36, 42, 58, 235), outline=(40, 44, 58, 255), width=2)
    for x1 in (232, 372):
        c.d.line([(SIDE(x1, 148)[0] * SS, SIDE(x1, 148)[1] * SS), (SIDE(x1, 200)[0] * SS, SIDE(x1, 200)[1] * SS)],
                 fill=(40, 44, 58, 255), width=2 * SS)
    for wx in (150, 448):
        cx_, cy_ = SIDE(wx, 208)
        rr = 36 * SIDE_S
        c.d.ellipse([(cx_ - rr) * SS, (cy_ - rr) * SS, (cx_ + rr) * SS, (cy_ + rr) * SS], fill=(40, 44, 58, 255))
        r2 = 20 * SIDE_S
        c.d.ellipse([(cx_ - r2) * SS, (cy_ - r2) * SS, (cx_ + r2) * SS, (cy_ + r2) * SS], fill=(150, 158, 178, 255))
    c.text((30, 480), 'side view (front is right)', font('segoeui.ttf', 16), (90, 98, 115, 255))

    # --- top view (front up)
    x0, y0 = TOP(650, 30)
    x1, y1 = TOP(790, 440)
    c.rrect((x0, y0, x1, y1), 52 * TOP_S, outline=(60, 66, 85, 255), width=3, gradient=base[::-1], vertical=True)
    c.rrect((x0, y0, x1, y1), 52 * TOP_S, outline=(60, 66, 85, 255), width=3)
    for sgn in (1, -1):    # hood blades
        bt = [TOP(720 + sgn * 62, 122), TOP(720 + sgn * 58, 72), TOP(720 + sgn * 46, 38),
              TOP(720 + sgn * 53, 74), TOP(720 + sgn * 52, 122)]
        c.poly(bt, outline=hexrgb(t_out) + (255,), width=3, gradient=tribal, vertical=True)
        c.poly(bt, outline=hexrgb(t_out) + (255,), width=3)
    for ya, yb in ((124, 178), (270, 324)):        # windshield and rear glass; the roof stays body colour
        gx0, gy0 = TOP(666, ya)
        gx1, gy1 = TOP(774, yb)
        c.rrect((gx0, gy0, gx1, gy1), 14 * TOP_S, fill=(36, 42, 58, 235), outline=(40, 44, 58, 255), width=2)
    for mx in (634, 790):
        a, b = TOP(mx, 140)
        c.rrect((a, b, a + 16 * TOP_S, b + 24 * TOP_S), 5, fill=(120, 126, 145, 255))
    c.text((1180, 940), 'top view (front is up)', font('segoeui.ttf', 16), (90, 98, 115, 255))

    # --- logos
    for zones, tf, s in ((SIDE_ZONES, SIDE, SIDE_S), (TOP_ZONES, TOP, TOP_S)):
        for z, (cx, cy, bw, bh) in zones.items():
            if z not in kit:
                continue
            res = sponsor_tile(kit[z], pal, (cx, cy, bw, bh), s, idx, stats)
            if not res:
                continue
            tile, real = res
            used[z] = real
            px, py = tf(cx, cy)
            c.place(tile, px, py)
            if z == 11:
                a, b = tf(798, 152)
                c.place(tile, a, b)

    # --- legend
    y = 548
    c.text((30, y - 36), 'Sponsor kit (from the Build sheet)', font('segoeuib.ttf', 20), (30, 34, 44, 255))
    fl, fb = font('segoeui.ttf', 19), font('segoeuib.ttf', 19)
    for z in range(1, 13):
        e = kit.get(z)
        if not e:
            continue
        row = y + (z - 1) * 33
        fc = pal['sponsor_a' if e['fill'] == 'A' else 'sponsor_b'][0]
        c.rrect((30, row + 2, 52, row + 24), 5, fill=hexrgb(fc) + (255,), outline=(120, 125, 140, 255), width=1)
        c.text((62, row), f"{z:>2}  {e['name']}", fl, (30, 34, 44, 255))
        c.text((420, row), e['brand'], fb, (30, 34, 44, 255))
        tag = 'logo master' if used.get(z) else ('text stand-in' if z in used else 'not in this view')
        c.text((860, row), tag, fl, (40, 120, 70, 255) if used.get(z) else (150, 100, 40, 255) if z in used else (140, 145, 160, 255))

    out = c.im.convert('RGB').resize((W, H), Image.LANCZOS)
    OUT.mkdir(exist_ok=True)
    out.save(OUT / f'{name} - Placement.webp', quality=90, method=6)
    return stats


def main(ids):
    idx = load_logo_index()
    folders = sorted(p for p in PROJECTS.iterdir() if p.is_dir() and (not ids or int(p.name[:3]) in ids))
    tot = {'real': 0, 'text': 0}
    for f in folders:
        s = render(f, idx)
        tot['real'] += s['real']
        tot['text'] += s['text']
    print(f'{len(folders)} previews; logo masters {tot["real"]}, text stand-ins {tot["text"]}')


if __name__ == '__main__':
    main({int(a) for a in sys.argv[1:]})
