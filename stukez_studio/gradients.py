"""Gradients: colour suggestions, the favourites file and the Swatch Exchange export.

A gradient follows the Project Library rule: exactly two colours, hex codes only. Next to the two colours it carries the
cut (angle, position and how much of the car it covers); the studio standard is 45 degrees over half the car.
"""
import json
import random
from dataclasses import asdict, dataclass

from . import palette as pal
from .swatch import write_file

STANDARD = dict(angle=45.0, pos=.5, span=.5)


@dataclass
class Gradient:
    name: str
    a: str
    b: str
    angle: float = STANDARD["angle"]
    pos: float = STANDARD["pos"]
    span: float = STANDARD["span"]

    def colours(self):
        return [self.a, self.b]

    def hex_line(self):
        return f"{self.a} → {self.b}"


# ---------------------------------------------------------------------- suggestions
def suggestions(a):
    """Second colours that go with `a`: [(label, hex)]."""
    h, s, l = pal.hex_hsl(a)
    lift = min(.9, l + .22) if l < .55 else max(.1, l - .22)
    return [
        ("Analogous", pal.hsl_hex(h + 28, s, l + (.1 if l < .5 else -.1))),
        ("Complement", pal.hsl_hex(h + 180, s, l)),
        ("Split complement", pal.hsl_hex(h + 150, s, l)),
        ("Triad", pal.hsl_hex(h + 120, s, l)),
        ("Lighter", pal.hsl_hex(h, s, min(.92, l + .25))),
        ("Darker", pal.hsl_hex(h, s, max(.06, l - .25))),
        ("Same hue, other energy", pal.hsl_hex(h + 8, min(1, s + .3) if s < .6 else s * .5, lift)),
    ]


def random_pair(moods=(), rng=None):
    """A fresh pair from the palette generator (the tribal colours of a generated palette), with a readable difference."""
    rng = rng or random.Random()
    best = None
    for _ in range(12):
        d = pal.generate(moods, rng=rng)
        pair = d["base"] if isinstance(d["base"], list) else [d["base"], d["tribal"][0] if isinstance(d["tribal"], list) else d["tribal"]]
        score = pal.contrast(pair[0], pair[1])
        if best is None or score > best[0]:
            best = (score, pair)
        if score >= 1.5:
            break
    return best[1]


def check(g):
    """Notes about a gradient: what the palette rules say and how far apart the two colours are."""
    notes = []
    for c in g.colours():
        if not pal.valid_hex(c):
            notes.append(f"{c} is not a valid hex code")
    if not notes:
        ratio = pal.contrast(g.a, g.b)
        if g.a.upper() == g.b.upper():
            notes.append("Both colours are the same, so there is no gradient.")
        elif ratio < 1.25:
            notes.append(f"The colours are very close ({ratio:.2f}:1); the blend will be hard to see on the car.")
    return notes


# ---------------------------------------------------------------------- favourites
class Favourites:
    """Saved gradients live in Project Library/Gradients: gradients.json (data) and Gradients.md (a note for Obsidian)."""

    def __init__(self, vault):
        self.folder = vault.lib / "Gradients"
        self.path = self.folder / "gradients.json"

    def load(self):
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return [Gradient(**{k: v for k, v in r.items() if k in Gradient.__dataclass_fields__}) for r in raw]
        except (ValueError, TypeError):
            return []

    def save(self, items):
        self.folder.mkdir(exist_ok=True)
        self.path.write_text(json.dumps([asdict(g) for g in items], indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
        self._note(items)

    def _note(self, items):
        lines = ["# Gradients", "", "Saved in StukeZ Designworks Studio (Workshop > Gradients). Two colours each, hex codes only; "
                 "the cut is the angle in degrees, where the blend is centred along the car (0 rear, 100 front) and how much of the car it covers.", "",
                 "| Name | From | To | Angle | Centre | Covers |", "| --- | --- | --- | --- | --- | --- |"]
        for g in items:
            lines.append(f"| {g.name} | `{g.a}` | `{g.b}` | {g.angle:g}° | {g.pos * 100:.0f} | {g.span * 100:.0f}% |")
        lines.append("")
        (self.folder / "Gradients.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")

    def add(self, g):
        items = [x for x in self.load() if x.name.lower() != g.name.lower()]
        items.append(g)
        self.save(items)
        return items

    def remove(self, name):
        items = [x for x in self.load() if x.name != name]
        self.save(items)
        return items


def write_ase(items, path, title="StukeZ gradients"):
    """Adobe Swatch Exchange file: two swatches per gradient (Illustrator builds the gradient from them)."""
    write_file(path, title, [(f"{g.name} {i + 1} {c}", c) for g in items for i, c in enumerate(g.colours())])
