"""Project Library toolkit: create palette/project notes and rebuild the index.

Usage (from a throwaway script):
    import sys; sys.path.insert(0, r"<vault>\\Project Library\\Tools")
    from projectkit import P, save, rebuild_index
    save(P(1, "Name", base=("#aaaaaa", "#bbbbbb"), ...))
    rebuild_index()

Rules enforced here (set by the user 2026-10-27, outlines opened up 2026-10-29):
  * Base colour: solid hex, or a gradient of exactly 2 hex colours.
  * Tribals and sponsors: solid hex, or a 2-colour gradient fill.
  * Outlines: a solid hex (the default, and every project made before 2026-10-29) or a 2-colour gradient.
"""
import json
import re
import shutil
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTES = ROOT / "Projects"
INDEX = ROOT / "Projects index.md"
HEX = re.compile(r"^#[0-9A-F]{6}$")


def _norm(v, what, allow_gradient):
    if isinstance(v, str):
        v = v.upper()
        if not HEX.match(v):
            raise ValueError(f"{what}: bad hex {v!r}")
        return v
    if allow_gradient and isinstance(v, (tuple, list)):
        if len(v) != 2:
            raise ValueError(f"{what}: gradients must have exactly 2 colours, got {len(v)}")
        return tuple(_norm(c, what, False) for c in v)
    raise ValueError(f"{what}: invalid {v!r}")


@dataclass
class Project:
    id: int
    name: str
    concept: str
    base: object
    tribal: object
    tribal_outline: object
    sponsor_a: object
    sponsor_a_outline: object
    sponsor_b: object
    sponsor_b_outline: object
    platform: str = ""
    created: str = ""
    moods: tuple = ()
    motifs: tuple = ()
    week: int = 0

    def __post_init__(self):
        self.base = _norm(self.base, "base", True)
        self.tribal = _norm(self.tribal, "tribal", True)
        self.sponsor_a = _norm(self.sponsor_a, "sponsor_a", True)
        self.sponsor_b = _norm(self.sponsor_b, "sponsor_b", True)
        self.tribal_outline = _norm(self.tribal_outline, "tribal_outline", True)
        self.sponsor_a_outline = _norm(self.sponsor_a_outline, "sponsor_a_outline", True)
        self.sponsor_b_outline = _norm(self.sponsor_b_outline, "sponsor_b_outline", True)
        self.created = self.created or date.today().isoformat()

    @property
    def filename(self):
        return f"{self.id:03d} {self.name}.md"


def P(id, name, concept, base, tribal, tribal_outline, sponsor_a, sponsor_a_outline,
      sponsor_b, sponsor_b_outline, platform="", moods=(), motifs=(), week=0):
    return Project(id, name, concept, base, tribal, tribal_outline, sponsor_a,
                   sponsor_a_outline, sponsor_b, sponsor_b_outline, platform,
                   moods=tuple(moods), motifs=tuple(motifs), week=week)


def _kind(v):
    return "Gradient" if isinstance(v, tuple) else "Solid"


def _hex(v):
    return " → ".join(f"`{c}`" for c in v) if isinstance(v, tuple) else f"`{v}`"


def _swatch(v):
    bg = f"linear-gradient(90deg,{v[0]},{v[1]})" if isinstance(v, tuple) else v
    return (f'<span style="display:inline-block;width:4em;height:1.1em;'
            f'border:1px solid #888;border-radius:3px;background:{bg}"></span>')


def _fm(v):
    return json.dumps(list(v) if isinstance(v, tuple) else v, ensure_ascii=False)


def render(p: Project) -> str:
    rows = [
        ("Base", p.base), ("Tribals", p.tribal), ("Tribal outline", p.tribal_outline),
        ("Sponsor A", p.sponsor_a), ("Sponsor A outline", p.sponsor_a_outline),
        ("Sponsor B", p.sponsor_b), ("Sponsor B outline", p.sponsor_b_outline),
    ]
    table = "\n".join(f"| {k} | {_kind(v)} | {_hex(v)} | {_swatch(v)} |" for k, v in rows)
    extra = ""
    if p.moods:
        extra += f"moods: {json.dumps(list(p.moods))}\n"
    if p.motifs:
        extra += f"motifs: {json.dumps(list(p.motifs), ensure_ascii=False)}\n"
    if p.week:
        extra += f"week: {p.week}\n"
    return f"""---
id: {p.id}
name: {json.dumps(p.name, ensure_ascii=False)}
platform: {json.dumps(p.platform, ensure_ascii=False)}
status: palette
created: {p.created}
{extra}base: {_fm(p.base)}
tribal: {_fm(p.tribal)}
tribal_outline: {_fm(p.tribal_outline)}
sponsor_a: {_fm(p.sponsor_a)}
sponsor_a_outline: {_fm(p.sponsor_a_outline)}
sponsor_b: {_fm(p.sponsor_b)}
sponsor_b_outline: {_fm(p.sponsor_b_outline)}
tags: [project]
---

# {p.id:03d} {p.name}

{p.concept}

| Element | Type | Hex | Swatch |
|---|---|---|---|
{table}

## Motifs

-

## Sponsors chosen

-

## Notes

-

Back to [[Projects index]].
"""


def project_dir(p):
    return NOTES / f"{p.id:03d} {p.name}"


def _colours(p):
    out = []
    for v in (p.base, p.tribal, p.tribal_outline, p.sponsor_a, p.sponsor_a_outline,
              p.sponsor_b, p.sponsor_b_outline):
        for c in (v if isinstance(v, tuple) else (v,)):
            if c not in out:
                out.append(c)
    return out


def _luminance(h):
    def ch(i):
        c = int(h[i:i + 2], 16) / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(1) + 0.7152 * ch(3) + 0.0722 * ch(5)


def render_patterns(p: Project) -> str:
    ramp = sorted(_colours(p), key=_luminance)
    rows = "\n".join(f"| {i} | `{c}` | {_swatch(c)} |" for i, c in enumerate(ramp, 1))
    title = f"{p.id:03d} {p.name}"
    return f"""---
type: project-patterns
project: "[[{title}]]"
tags: [patterns]
---

# {title} - Patterns

Back to [[{title}]].

The pattern prompts below are neutral greyscale, so the sets fit every project (50 patterns). Generate the grey tile in Gemini, then recolor it with this project's palette. Each pattern also has ready-made colour versions under its own heading.

## Gradient map for this project (dark to light)

| Stop | Hex | Swatch |
|---|---|---|
{rows}

Photoshop: Layer > New Adjustment Layer > Gradient Map, then place the stops evenly from dark (left) to light (right). Alternative: put the base colour as a layer above the pattern in Multiply or Overlay mode.

## Prompts

Grey masters: [[Seamless Patterns - Neutral]], [[Seamless Patterns 2 - Neutral]], [[Seamless Patterns 3 - Neutral]], [[Seamless Patterns 4 - Neutral]] and [[Seamless Patterns 5 - Neutral]] (50 patterns). The patterns that carry a ready-made colour version in this project's palette are listed under "Motifs" in [[{title}]].
"""


def write_patterns_note(p: Project):
    d = project_dir(p)
    (d / f"{p.id:03d} {p.name} - Patterns.md").write_text(render_patterns(p), encoding="utf-8", newline="\n")


def load_project(path):
    fm = _read_fm(path)
    t = lambda v: tuple(v) if isinstance(v, list) else v
    return Project(int(fm["id"]), fm["name"], "", t(fm["base"]), t(fm["tribal"]), t(fm["tribal_outline"]),
                   t(fm["sponsor_a"]), t(fm["sponsor_a_outline"]), t(fm["sponsor_b"]), t(fm["sponsor_b_outline"]),
                   platform=fm.get("platform", ""), created=str(fm.get("created", "")),
                   moods=tuple(fm.get("moods", ())), motifs=tuple(fm.get("motifs", ())),
                   week=int(fm.get("week", 0) or 0))


def save(p: Project, force=False):
    NOTES.mkdir(parents=True, exist_ok=True)
    existing = list(NOTES.glob(f"{p.id:03d} *"))
    if existing and not force:
        raise FileExistsError(f"project {p.id:03d} already exists: {[e.name for e in existing]}")
    for e in existing:
        shutil.rmtree(e) if e.is_dir() else e.unlink()
    d = project_dir(p)
    d.mkdir(parents=True)
    target = d / p.filename
    target.write_text(render(p), encoding="utf-8", newline="\n")
    write_patterns_note(p)
    return target


def _read_fm(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    fm = {}
    for line in m.group(1).splitlines():
        k, _, v = line.partition(": ")
        try:
            fm[k] = json.loads(v)
        except ValueError:
            fm[k] = v
    return fm


def next_id():
    ids = [int(f.name[:3]) for f in NOTES.iterdir() if f.is_dir()] if NOTES.exists() else []
    return max(ids, default=0) + 1


def rebuild_index():
    rows = []
    for f in sorted(NOTES.glob("*/[0-9][0-9][0-9] *.md")):
        if f.stem != f.parent.name:
            continue
        fm = _read_fm(f)
        def cell(key):
            v = fm[key]
            return _swatch(tuple(v) if isinstance(v, list) else v)
        rows.append(
            f"| {int(fm['id']):03d} | [[{f.stem}\\|{fm['name']}]] | {fm.get('platform') or ''} | "
            f"{fm['status']} | {cell('base')} | {cell('tribal')} | {cell('sponsor_a')} | {cell('sponsor_b')} |"
        )
    body = f"""---
tags: [project-index]
---

# Projects index

Generated by `Tools/projectkit.py` (`rebuild_index()`). Do not edit by hand. Rules and workflow: [[Project Library README]].

{len(rows)} projects.

| ID | Project | Platform | Status | Base | Tribals | Sponsor A | Sponsor B |
|---|---|---|---|---|---|---|---|
""" + "\n".join(rows) + "\n"
    INDEX.write_text(body, encoding="utf-8", newline="\n")
    return INDEX
