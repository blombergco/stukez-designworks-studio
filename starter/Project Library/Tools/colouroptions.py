"""Colour options for the Gemini prompts, generated from the Project Library.

Every greyscale prompt note in `Gemini Prompt/` (not the archive) gets a generated
"Colour options" block: the prompt again with its "Colour treatment" paragraph
replaced by the hex palette of a library project. Every project note gets a
generated list of the prompts that use its palette.

Matching: a project's front matter `motifs` (explicit picks) come first, the rest is
filled by shared `moods` (front matter of both sides) with a penalty for projects that
are already used a lot, so the choices rotate through the whole library.

Usage (from a throwaway script):
    import sys; sys.path.insert(0, r"<vault>\\Project Library\\Tools")
    from colouroptions import refresh
    refresh()

Generated regions sit between HTML comment markers and are rewritten on every run;
everything outside the markers is left alone.
"""
import re
from collections import Counter, defaultdict

import projectkit as pk

VAULT = pk.ROOT.parent
GEM = VAULT / "Gemini Prompt"
M_START, M_END = "<!-- colour-options -->", "<!-- /colour-options -->"
P_START, P_END = "<!-- motifs:auto -->", "<!-- /motifs:auto -->"
SKIP_DIRS = {"_Archive - colour versions"}
SKIP_NAMES = {"Gemini Prompt index", "Motif ideas", "Style guide", "Text and lettering plan", "Pipeline tips",
              "Design glossary", "Design glossary - Japanese", "Universal details guide", "Zoku Tribals - index"}
PATTERN_SETS = ("Seamless Patterns - Neutral", "Seamless Patterns 2 - Neutral", "Seamless Patterns 3 - Neutral", "Seamless Patterns 4 - Neutral", "Seamless Patterns 5 - Neutral")
CATEGORIES = {"Side Designs": "Side designs", "Hood Motifs": "Hood motifs", "Textures and Fill Elements": "Elements",
              "Tribal": "Tribals", "Banners": "Banners", "Cut-Ready": "Cut-ready", "Smoke and Tandem": "Smoke and tandem",
              "Mechanical": "Mechanical", "Dragon Atlas": "Dragon atlas", "Style Variants": "Style variants",
              "World Motifs": "World motifs", "Universal Details": "Universal details", "Zoku Tribals": "Zoku tribals"}
# Categories that carry their own colour versions: listed in the index but never touched by refresh().
OWN_COLOURS = {"Zoku tribals"}
CAP = {"prompt": 6, "pattern": 3}
WANT = {"prompt": 3, "pattern": 2}
LABEL = "ABCDEFGH"


# ------------------------------------------------------------------ colour roles
def _lum(h):
    return pk._luminance(h)


def _sat(h):
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    mx, mn = max(r, g, b), min(r, g, b)
    return 0 if mx == 0 else (mx - mn) / mx


def roles(p):
    """Up to five (hex, role) pairs for a project, dark to light."""
    cols = pk._colours(p)
    dark, light = min(cols, key=_lum), max(cols, key=_lum)
    rest = [c for c in cols if c not in (dark, light)]
    picked = {dark: "linework and deepest shadows", light: "highlights and the brightest planes"}
    if rest:
        accent = max(rest, key=lambda c: _sat(c) * (0.5 + _lum(c)))
        picked[accent] = "accent, used sparingly on focal details such as eyes, flames, sparks and edges"
    base = list(p.base) if isinstance(p.base, tuple) else [p.base]
    for c in base:
        if c not in picked:
            picked[c] = "midtones"
    if len(picked) < 4:
        for c in sorted(rest, key=lambda c: abs(_lum(c) - 0.3)):
            if c not in picked:
                picked[c] = "midtones"
                break
    return sorted(list(picked.items())[:5], key=lambda kv: _lum(kv[0]))


def roles2(p):
    """Two flat colours for cut-ready prompts: the darkest and the most vivid other colour."""
    cols = pk._colours(p)
    dark = min(cols, key=_lum)
    rest = [c for c in cols if c != dark]
    accent = max(rest, key=lambda c: _sat(c) * (0.5 + _lum(c)))
    return [(dark, "the main shapes"), (accent, "the second layer and the cut-out details")]


def colour_paragraph2(p):
    (a, _), (b, _) = roles2(p)
    return (f"Colour treatment: exactly two flat solid colours and nothing else: {a} for the main shapes and {b} for the "
            "second layer and the cut-out details. No gradients, no shading, no hatching, no grey, no third colour, "
            "so each colour can be cut or sprayed as its own layer.")


def colour_paragraph(p):
    parts = "; ".join(f"{h} for {r}" for h, r in roles(p))
    return ("Colour treatment: a strict limited palette. Use only these hex colours and smooth tonal "
            f"blends between neighbouring ones: {parts}. No grey, no sepia, no other hues. Keep strong "
            "tonal separation between every form so the shapes stay readable and the finished artwork "
            "matches the livery palette.")


# ------------------------------------------------------------------ loading
def load_projects():
    out = []
    for d in sorted(pk.NOTES.iterdir()):
        f = d / f"{d.name}.md"
        if not (d.is_dir() and f.exists()):
            continue
        p = pk.load_project(f)
        out.append(p)
    return out


def _fm_list(fm, key):
    v = fm.get(key, [])
    return v if isinstance(v, list) else []


def load_prompts():
    """Items that get colour options: {key, path, kind, moods, pattern_no}."""
    items = []
    for f in sorted(GEM.rglob("*.md")):
        if any(part in SKIP_DIRS for part in f.parts) or f.stem in SKIP_NAMES:
            continue
        text = f.read_text(encoding="utf-8")
        if not text.startswith("---\n") or "gemini-prompt" not in text.split("\n---", 1)[0]:
            continue
        fm = pk._read_fm(f)
        rel = f.relative_to(GEM).parts[:-1]
        if f.stem in PATTERN_SETS:
            for m in re.finditer(r"(?m)^## (\d+)\. (.+)\n(?:<!-- moods: (.*?) -->\n)?", text):
                items.append(dict(key=f"{f.stem}#{m.group(1)}. {m.group(2)}", stem=f.stem, path=f,
                                  kind="pattern", cat="Patterns", moods=(m.group(3) or "").split(),
                                  short=m.group(2)))
            continue
        cat = next((CATEGORIES[x] for x in rel if x in CATEGORIES), "Motifs")
        group = rel[1] if len(rel) > 1 else ""
        items.append(dict(key=f.stem, stem=f.stem, path=f, kind="prompt", cat=cat, group=group,
                          moods=_fm_list(fm, "moods"), short=f.stem, colours=int(fm.get("colours", 0) or 0),
                          aspect=str(fm.get("aspect_ratio", "")), layout=str(fm.get("layout", ""))))
    return items


# ------------------------------------------------------------------ matching
def select(projects, items):
    usage, chosen = Counter(), {}
    by_motif = defaultdict(list)
    for p in projects:
        for m in p.motifs:
            by_motif[m].append(p)
    for it in sorted(items, key=lambda i: i["key"]):          # phase 1: explicit picks
        ex = sorted(by_motif.get(it["key"], []), key=lambda p: (usage[p.id], p.id))[:CAP[it["kind"]]]
        chosen[it["key"]] = list(ex)
        for p in ex:
            usage[p.id] += 1
    for it in sorted(items, key=lambda i: i["key"]):          # phase 2: fill by mood
        got = chosen[it["key"]]
        while len(got) < WANT[it["kind"]]:
            pool = [p for p in projects if p not in got]
            best = max(pool, key=lambda p: (3 * len(set(p.moods) & set(it["moods"])) - 1.2 * usage[p.id], -p.id))
            got.append(best)
            usage[best.id] += 1
    pats = [i for i in items if i["kind"] == "pattern"]       # phase 3: every planned project gets a pattern
    for p in projects:
        if p.week and not any(p in chosen[i["key"]] for i in pats):
            best = max(pats, key=lambda i: (3 * len(set(p.moods) & set(i["moods"])) - 0.8 * len(chosen[i["key"]]), i["key"]))
            chosen[best["key"]].append(p)
    return chosen


# ------------------------------------------------------------------ rendering
def _title(p):
    return f"{p.id:03d} {p.name}"


def _option(p, label, prompt_text, table=True, colours=0):
    two = colours == 2
    swatches = "\n".join(f"| `{h}` | {pk._swatch(h)} | {r} |" for h, r in (roles2(p) if two else roles(p)))
    para = colour_paragraph2(p) if two else colour_paragraph(p)
    new = re.sub(r"(?m)^Colour treatment:.*$", lambda _m: para, prompt_text, count=1)
    head = f"### Option {label} - {_title(p)}\n\nPalette: [[{_title(p)}]]\n\n"
    tbl = f"| Hex | Swatch | Used for |\n|---|---|---|\n{swatches}\n\n" if table else ""
    return f"{head}{tbl}```\n{new}\n```\n"


def _block(procs, text_code, table=True, level=2, colours=0):
    opts = "\n".join(_option(p, LABEL[i], text_code, table, colours) for i, p in enumerate(procs))
    intro = ("Ready-to-paste colour versions: the prompt above with its \"Colour treatment\" paragraph "
             "replaced by the hex palette of a Project Library project, so the artwork matches that livery. "
             "The greyscale prompt stays the master for free recolouring. Generated by "
             "`Project Library/Tools/colouroptions.py`.\n")
    return f"{M_START}\n{'#' * level} Colour options\n\n{intro}\n{opts}{M_END}\n"


_CODE = re.compile(r"```\n(.*?)\n```\n", re.S)
_OLD = re.compile(re.escape(M_START) + r".*?" + re.escape(M_END) + r"\n?", re.S)


def write_prompt_note(item, procs):
    text = _OLD.sub("", item["path"].read_text(encoding="utf-8"))
    m = _CODE.search(text)
    block = _block(procs, m.group(1), colours=item.get("colours", 0))
    tail = "Back to [[Gemini Prompt index]]."
    i = text.rfind(tail)
    text = text[:i].rstrip("\n") + "\n\n" + block + "\n" + text[i:] if i != -1 else text.rstrip("\n") + "\n\n" + block
    item["path"].write_text(text, encoding="utf-8", newline="\n")


def write_pattern_set(path, items, chosen):
    text = _OLD.sub("", path.read_text(encoding="utf-8"))
    parts = re.split(r"(?m)^(?=## \d+\. )", text)
    out = [parts[0]]
    byno = {it["key"].split("#", 1)[1].split(".", 1)[0]: it for it in items if it["stem"] == path.stem}
    for sec in parts[1:]:
        no = re.match(r"## (\d+)\.", sec).group(1)
        m = _CODE.search(sec)
        block = _block(chosen[byno[no]["key"]], m.group(1), table=False, level=3)
        block = re.sub(r"### Option ([A-H]) - ", lambda o: f"#### Option {no}{o.group(1)} - ", block)
        # compact: replace the table-less option header
        sec = sec[:m.end()] + "\n" + block + "\n" + sec[m.end():]
        out.append(sec)
    path.write_text("".join(out), encoding="utf-8", newline="\n")


def _project_block(p, mine):
    cats = defaultdict(list)
    for it in mine:
        label = f"[[{it['stem']}#{it['key'].split('#', 1)[1]}|{it['short']}]]" if it["kind"] == "pattern" \
            else f"[[{it['stem']}]]"
        cats[it["cat"]].append(label)
    order = ["Motifs", "World motifs", "Universal details", "Dragon atlas", "Style variants", "Cut-ready", "Mechanical", "Smoke and tandem",
             "Side designs", "Hood motifs", "Banners", "Tribals", "Elements", "Patterns"]
    lines = [f"- **{c}:** " + ", ".join(sorted(cats[c])) for c in order if cats.get(c)]
    return (f"{P_START}\nPrompts with a ready-made colour version in this palette (generated by "
            f"`Tools/colouroptions.py`):\n\n" + "\n".join(lines) + f"\n{P_END}")


def write_project_notes(projects, items, chosen):
    mine = defaultdict(list)
    for it in items:
        for p in chosen[it["key"]]:
            mine[p.id].append(it)
    for p in projects:
        f = pk.NOTES / _title(p) / f"{_title(p)}.md"
        text = f.read_text(encoding="utf-8")
        m = re.search(r"## Motifs\n\n(.*?)\n\n## Sponsors chosen", text, re.S)
        if not m:
            continue
        body = m.group(1)
        block = _project_block(p, mine[p.id]) if mine[p.id] else ""
        if P_START in body:
            body = re.sub(re.escape(P_START) + r".*?" + re.escape(P_END), lambda _m: block, body, flags=re.S)
        elif body.strip() in ("-", ""):
            body = block or "-"
        else:
            body = body + "\n\n" + block
        text = text[:m.start(1)] + body + text[m.end(1):]
        f.write_text(text, encoding="utf-8", newline="\n")


def refresh():
    projects = load_projects()
    items = [i for i in load_prompts() if i["cat"] not in OWN_COLOURS]
    chosen = select(projects, items)
    for it in items:
        if it["kind"] == "prompt":
            write_prompt_note(it, chosen[it["key"]])
    for stem in PATTERN_SETS:
        path = next((i["path"] for i in items if i["stem"] == stem), None)
        if path:
            write_pattern_set(path, items, chosen)
    write_project_notes(projects, items, chosen)
    return len(projects), len(items)
