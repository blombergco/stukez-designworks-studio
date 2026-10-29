"""Builds the generated notes of a project: design vocabulary, detail kit, build sheet with sponsor kit, placement preview.

Ported from the vault's archived generators (Project Library/Tools/Archive scripts: build_kits.py, build_sheets.py,
build_jp.py) so a project made in StukeZ Designworks Studio gets the same notes as the first 236. The data modules of the vault
(details_data, details_data2, finish_rules, dense_layout) are imported from the vault itself. Everything is written
relative to the vault passed in, and the rotation counters (which details and brands are used a lot) are read from the
notes that already exist, so a new project continues the rotation.
"""
import colorsys
import re
import sys
import zlib
from collections import Counter

import numpy, PIL.Image, PIL.ImageDraw, PIL.ImageFilter, PIL.ImageFont  # noqa: E401,F401  (placement_preview needs them)

from . import kit_rules as K
from .backend import PARTS

KIT_SIZE = 8
SLOTS = [  # zone, name, tier, preferred categories (best first)
    (1, "Windshield banner", "Tier 1", ["Lubricants and Fluids", "Tires", "Wheels", "Suspension", "Brakes"]),
    (2, "Hood", "Tier 2", ["Turbo and Supercharger", "Engine", "ECU", "Cooling", "Intake and Induction"]),
    (3, "Front bumper / lip", "Tier 2", ["Body and Aero", "Cooling", "Brakes"]),
    (4, "Front fender", "Tier 2", ["Suspension", "Steering and Angle", "Brakes"]),
    (5, "Door upper", "Tier 1", ["Wheels", "Tires", "Suspension", "Lubricants and Fluids"]),
    (6, "Door lower / side skirt", "Tier 3", ["Exhaust", "Intake and Induction", "Body and Aero"]),
    (7, "Rear quarter", "Tier 2", ["Drivetrain", "Brakes", "Exhaust"]),
    (8, "Roof", "Tier 2", ["Lubricants and Fluids", "Gauges and Electronics", "Tires"]),
    (9, "Trunk lid / wing", "Tier 2", ["Body and Aero", "Safety and Interior", "Wheels"]),
    (10, "Rear bumper", "Tier 3", ["Exhaust", "Fuel System", "Lubricants and Fluids"]),
    (11, "Mirrors", "Tier 3", ["Gauges and Electronics", "Ignition", "Injectors", "ECU"]),
    (12, "Rear and side glass", "Tier 3", ["Wraps Paint and Lighting", "Safety and Interior", "Gauges and Electronics"]),
]
SIZE = {"Tier 1": "large (about 40-60 % of the panel width)", "Tier 2": "medium (about 25-40 %)",
        "Tier 3": "small (about 10-20 %)"}
CONF = {"web-verified": 1.0, "scene-verified": 0.8, "partial": 0.6}
FILLER_ART = ("[[Sticker Shapes - Details]], [[Tape Strips - Details]], [[Paint Splatter - Details]], [[Stars - Details]], "
              "[[Speech Bubbles - Details]], [[Zigzags and Squiggles - Details]], [[Cartoon Faces - Details]], [[Hearts - Details]]")


class ProjectBuilder:
    STEPS = PARTS

    def __init__(self, vault):
        self.v, self.pk, self.co, self.dblib = vault, vault.pk, vault.co, vault.dblib
        arch = str(vault.lib / "Tools" / "Archive scripts")
        if arch not in sys.path:
            sys.path.append(arch)
        import details_data, details_data2, finish_rules, dense_layout  # vault data modules
        self.alld = details_data.DETAILS + details_data2.DETAILS2
        self.fr, self.dl = finish_rules, dense_layout
        self.titles = {d["title"] for d in self.alld}
        self._pool = None

    # ------------------------------------------------------------------ helpers
    def title(self, p):
        return f"{p.id:03d} {p.name}"

    def folder(self, p):
        return self.pk.NOTES / self.title(p)

    def note(self, p):
        return self.folder(p) / f"{self.title(p)}.md"

    def load(self, pid):
        d = next(d for d in self.pk.NOTES.iterdir() if d.is_dir() and d.name.startswith(f"{pid:03d} "))
        return self.pk.load_project(d / f"{d.name}.md")

    def missing(self, p):
        """Which generated parts a project still lacks."""
        return self.v.missing_parts(self.v._load_project(self.note(p)))

    def _mean_lum(self, v):
        cs = v if isinstance(v, tuple) else (v,)
        return sum(self.pk._luminance(c) for c in cs) / len(cs)

    def _insert_before(self, p, heading, block):
        f = self.note(p)
        t = f.read_text(encoding="utf-8")
        assert t.count(heading + "\n") == 1, f"{heading} not found once in {f.name}"
        f.write_text(t.replace(heading + "\n", block + heading + "\n", 1), encoding="utf-8", newline="\n")

    def _drop_section(self, p, heading, until):
        f = self.note(p)
        t = f.read_text(encoding="utf-8")
        t = re.sub(rf"{re.escape(heading)}\n\n.*?\n\n(?={re.escape(until)}\n)", "", t, flags=re.S)
        f.write_text(t, encoding="utf-8", newline="\n")

    # ------------------------------------------------------------------ design vocabulary
    @staticmethod
    def _hsv(h):
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
        return colorsys.rgb_to_hsv(r, g, b)

    @staticmethod
    def _circ(a, b):
        d = abs(a - b) % 360
        return min(d, 360 - d)

    @staticmethod
    def _hue_name(h):
        for lim, n in [(15, "red"), (40, "orange"), (68, "yellow"), (160, "green"), (200, "teal"), (255, "blue"),
                       (290, "violet"), (345, "magenta")]:
            if h < lim:
                return n
        return "red"

    def classify(self, p):
        cols = []
        for v in (p.base, p.tribal, p.sponsor_a, p.sponsor_b):
            cols += list(v) if isinstance(v, tuple) else [v]
        cols = list(dict.fromkeys(cols))
        chrom = [(self._hsv(c)[0] * 360, c) for c in cols if self._hsv(c)[1] >= 0.25 and self._hsv(c)[2] >= 0.08]
        neutrals = [c for c in cols if c not in [x[1] for x in chrom]]
        clusters = []
        for h in sorted(h for h, _ in chrom):
            if clusters and self._circ(clusters[-1][-1], h) <= 28:
                clusters[-1].append(h)
            else:
                clusters.append([h])
        if len(clusters) > 1 and self._circ(clusters[0][0], clusters[-1][-1]) <= 28:
            clusters[0] = clusters.pop() + clusters[0]
        centres = [sum(c) / len(c) for c in clusters]
        n = len(centres)
        if n == 0:
            scheme = "Monochromatic"
        elif n == 1:
            scheme = "Neutral with accent" if neutrals else "Monochromatic"
        elif n == 2:
            scheme = "Analogous" if self._circ(centres[0], centres[1]) < 120 else "Complementary"
        elif n == 3:
            scheme = "Triadic"
            for i in range(3):
                j, k = [x for x in range(3) if x != i]
                if (self._circ(centres[i], centres[j]) >= 130 and self._circ(centres[i], centres[k]) >= 130
                        and self._circ(centres[j], centres[k]) <= 90):
                    scheme = "Split-complementary"
            s = sorted(centres)
            if 360 - max((s[(i + 1) % 3] - s[i]) % 360 for i in range(3)) <= 100:
                scheme = "Analogous"
        else:
            scheme = "Tetradic"
        names = []
        for c in centres:
            nm = self._hue_name(c)
            if nm not in names:
                names.append(nm)
        mb, mt = self._mean_lum(p.base), self._mean_lum(p.tribal)
        if mb < 0.15 and mt > mb + 0.15:
            value = "dark base, light tribals"
        elif mb > 0.45 and mt < mb - 0.15:
            value = "light base, dark tribals"
        elif abs(mb - mt) < 0.08:
            value = "base and tribals close in value (the outline does the separating)"
        elif mb < mt:
            value = "darker base, lighter tribals"
        else:
            value = "lighter base, darker tribals"
        return scheme, names, value

    def add_vocabulary(self, p):
        if "## Design vocabulary" in self.note(p).read_text(encoding="utf-8"):
            return
        scheme, names, value = self.classify(p)
        finish = self.fr.infer_finish(p.name, p.moods)
        block = ("## Design vocabulary\n\n| Aspect | Term |\n|---|---|\n"
                 f"| Colour scheme (auto-classified from the hex codes) | [[Design glossary#{scheme}\\|{scheme}]] |\n"
                 f"| Hue families | {', '.join(names) or 'none (achromatic)'} |\n"
                 f"| Value structure | {value} |\n"
                 f"| Suggested finish (inferred) | [[Design glossary#{finish}\\|{finish}]] |\n\n")
        self._insert_before(p, "## Motifs", block)

    def finish_of(self, p):
        m = re.search(r"\| Suggested finish[^|]*\| \[\[Design glossary#([^\\|\]]+)", self.note(p).read_text(encoding="utf-8"))
        return m.group(1) if m else "Satin"

    # ------------------------------------------------------------------ detail kit
    def detail_usage(self, skip_id=None):
        use = Counter()
        for f in self.pk.NOTES.glob("*/* - Detail kit.md"):
            if skip_id is not None and f.name.startswith(f"{skip_id:03d} "):
                continue
            t = f.read_text(encoding="utf-8").split("## Layer plan", 1)[-1].split("## Prompts", 1)[0]
            use.update(re.findall(r"\[\[([^\]|]+) - Details\]\]", t))
        return use

    def select_details(self, p, usage, info):
        base = self._mean_lum(p.base)
        score, why = Counter(), {d["title"]: [] for d in self.alld}
        for d in self.alld:
            t = d["title"]
            shared = set(p.moods) & set(d["moods"])
            score[t] += 1.0 * len(shared)
            ruled = {m for m in p.moods if t in K.MOOD.get(m, [])}
            score[t] += 1.5 * len(ruled)
            allm = sorted(shared | ruled, key=lambda m: p.moods.index(m))
            if allm:
                why[t].append("mood " + "/".join(allm))
            if t in K.STYLE.get(info["style"], []):
                score[t] += 3
                why[t].append(f"style {info['style']}")
            if t in K.GROUP.get(info["group"], []):
                score[t] += 3
                why[t].append(f"theme {info['group']}")
            if t in K.FINISH.get(info["finish"], []):
                score[t] += 1.5
                why[t].append(f"finish {info['finish']}")
            if base < 0.1 and t in K.DARK:
                score[t] += 1.2
                why[t].append("dark base")
            if base > 0.45 and t in K.LIGHT:
                score[t] += 1.2
                why[t].append("light base")
            score[t] -= 0.4 * usage[t]
        chosen, per = [], Counter()
        for d in sorted(self.alld, key=lambda d: (-score[d["title"]], d["title"])):
            if per[d["group"]] >= 2:
                continue
            chosen.append(d)
            per[d["group"]] += 1
            if len(chosen) == KIT_SIZE:
                break

        def swap_in(pred):
            if any(pred(x) for x in chosen):
                return
            cand = [d for d in sorted(self.alld, key=lambda d: (-score[d["title"]], d["title"])) if pred(d) and d not in chosen]
            drop = min((x for x in chosen if not pred(x)), key=lambda x: score[x["title"]])
            chosen[chosen.index(drop)] = cand[0]

        swap_in(lambda d: d["kind"] == "overlay")
        swap_in(lambda d: d["group"] in ("Hardware and Labels", "Symbols and Icons", "Graphic Fillers"))
        chosen.sort(key=lambda d: (K.ORDER.index(d["group"]), d["title"]))
        return chosen, why

    def _master_detail(self, d):
        f = self.v.gem / "Universal Details" / d["group"] / f"{d['title']} - Details.md"
        if not f.exists():   # a workspace without the prompt library: write the prompt from the detail's own description
            return (d["desc"] + "\n\nColour treatment: strictly monochrome. Pure black ink linework plus neutral grey tones.\n\n"
                    "Detail level: 8 out of 10. Crisp, richly structured graphic work with clean consistent edges.\n\n"
                    "Isolated elements on a pure solid white background (#FFFFFF). Every element is separate with generous white "
                    "space between elements, no overlap, arranged in a loose grid, as black on white.")
        return re.search(r"```\n(.*?)\n```\n", f.read_text(encoding="utf-8"), re.S).group(1)

    def _coloured_detail(self, d, p):
        text = self._master_detail(d)
        if d["kind"] == "overlay":
            dark = min(self.pk._colours(p), key=self.pk._luminance)
            para = (f"Colour treatment: the marks are drawn in one single ink colour, {dark}, with lighter tints of that same colour "
                    "for fine detail, on the pure white background. No black, no grey and no other colour, so the layer can be set to "
                    "Multiply over the design.")
            text = text.replace("as black on white", "in a single ink colour on white").replace(
                "black marks on a pure", "marks in the single ink colour on a pure")
        else:
            para = self.co.colour_paragraph(p)
        return re.sub(r"(?m)^Colour treatment:.*$", lambda _m: para, text, count=1)

    def build_kit(self, p):
        title = self.title(p)
        info = dict(style="", group="", finish=self.finish_of(p))
        chosen, why = self.select_details(p, self.detail_usage(skip_id=p.id), info)
        sw = "\n".join(f"| `{h}` | {self.pk._swatch(h)} | {r} |" for h, r in self.co.roles(p))
        steps, prompts = [], ""
        for i, d in enumerate(chosen, 1):
            reasons = ", ".join(dict.fromkeys(why[d["title"]])) or "balance pick"
            place = ("Overlay: Multiply at 20-40 % over the finished design, masked to the edges."
                     if d["kind"] == "overlay" else K.PLACE[d["group"]])
            steps.append(f"{i}. [[{d['title']} - Details]] ({'overlay' if d['kind'] == 'overlay' else 'sheet'}) - {place} *Chosen for: {reasons}.*")
            how = ("Full-bleed overlay: Multiply over the design." if d["kind"] == "overlay"
                   else "Sheet of separate elements: cut out and place one by one.")
            prompts += (f"\n### {i}. {d['title']}\n\nFrom [[{d['title']} - Details]] ({d['group']}). Chosen for: {reasons}. "
                        f"{how}\n\n```\n{self._coloured_detail(d, p)}\n```\n")
        text = f"""---
type: project-detail-kit
project: "[[{title}]]"
tags: [detail-kit]
---

# {title} - Detail kit

Back to [[{title}]].

{len(chosen)} universal detail prompts chosen for this project's moods ({", ".join(p.moods) or "none"}){f", finish {info['finish']}" if info['finish'] else ""}. The project's hex codes are already in every prompt, so paste them straight into Gemini. The kit spans texture, support, wear and light, ordered from the bottom layer to the top; how to combine them is explained in [[Universal details guide]].

## Palette used

| Hex | Swatch | Role |
|---|---|---|
{sw}

## Layer plan (bottom to top)

{chr(10).join(steps)}

Keep accents in odd numbers and two or three sizes. Overlays go in Multiply (white drops out) and are recoloured by the single ink colour in their prompt.

## Prompts
{prompts}
Back to [[{title}]] or the [[Detail kits]] overview.
"""
        (self.folder(p) / f"{title} - Detail kit.md").write_text(text, encoding="utf-8", newline="\n")
        self._drop_section(p, "## Detail kit", "## Notes")
        self._insert_before(p, "## Notes", f"## Detail kit\n\n[[{title} - Detail kit]]: " + ", ".join(d["title"] for d in chosen) + ".\n\n")
        self._overview_row(p, chosen)
        return chosen

    def _overview_row(self, p, chosen):
        f = self.v.lib / "Detail kits.md"
        if not f.exists():
            return
        title = self.title(p)
        row = f"| {p.id:03d} | [[{title} - Detail kit\\|{p.name}]] | " + ", ".join(d["title"] for d in chosen) + " |"
        lines = [ln for ln in f.read_text(encoding="utf-8").splitlines() if not ln.startswith(f"| {p.id:03d} |")]
        last = max((i for i, ln in enumerate(lines) if re.match(r"\| \d{3} \|", ln)), default=None)
        if last is None:
            return
        lines.insert(last + 1, row)
        f.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    # ------------------------------------------------------------------ sponsors
    def pool(self):
        if self._pool is None:
            out = []
            for b in self.dblib.all_brands():
                conf = b.get("confidence")
                if conf not in CONF:
                    continue
                seen = set()
                for r in b["rows"]:
                    if r["notes"].lstrip().startswith("†"):
                        continue
                    toks = self.dblib.split_tokens(r["fits"])
                    kind = "Universal" if "Universal" in toks else "Varies" if "Varies" in toks else None
                    if not kind or (r["cat"], kind) in seen:
                        continue
                    seen.add((r["cat"], kind))
                    out.append(dict(name=b["name"], note=b["path"].stem, cat=r["cat"], item=r["item"], kind=kind,
                                    region=b.get("region", ""), country=b.get("country", ""),
                                    website=b.get("website", ""), conf=conf))
            self._pool = out
        return self._pool

    def sponsor_usage(self, skip_id=None):
        use = Counter()
        stem2name = {b["path"].stem: b["name"] for b in self.dblib.all_brands()}
        for f in self.pk.NOTES.glob("*/* - Build sheet.md"):
            if skip_id is not None and f.name.startswith(f"{skip_id:03d} "):
                continue
            sec = f.read_text(encoding="utf-8").split("## Dense layout", 1)[-1].split("**Filler art", 1)[0]
            for m in re.finditer(r"(?m)^\|[^|\n]*\|[^|\n]*\|[^|\n]*\|[^|\n]*\| \[\[([^\]|]+)\]\]", sec):
                use[stem2name.get(m.group(1), m.group(1))] += 1
        return use

    def _cr(self, a, b):
        return (max(a, b) + 0.05) / (min(a, b) + 0.05)

    def _fill_pick(self, p, i, base):
        a = p.sponsor_a[0] if isinstance(p.sponsor_a, tuple) else p.sponsor_a
        b = p.sponsor_b[0] if isinstance(p.sponsor_b, tuple) else p.sponsor_b
        pref, other = ("A", "B") if i % 2 == 0 else ("B", "A")
        lp = self.pk._luminance(a if pref == "A" else b)
        lo = self.pk._luminance(b if pref == "A" else a)
        return other if self._cr(lp, base) < 1.8 and self._cr(lo, base) > self._cr(lp, base) else pref

    def pick_sponsors(self, p, usage):
        chosen, used, regions = [], set(), Counter()
        for zone, name, tier, prefs in SLOTS:
            best, best_s = None, -1e9
            for c in self.pool():
                if c["name"] in used:
                    continue
                s = (len(prefs) - prefs.index(c["cat"])) * 0.3 if c["cat"] in prefs else -3.0
                s += CONF[c["conf"]] + (0.6 if c["kind"] == "Universal" else 0.0) - 0.35 * usage[c["name"]]
                reg = c["region"] if c["region"] in ("Japan", "USA", "Europe") else "Other"
                if reg in ("Japan", "USA", "Europe") and regions[reg] == min(regions[r] for r in ("Japan", "USA", "Europe")):
                    s += 0.5
                s += (zlib.crc32(f"{p.id}|{c['name']}|{zone}".encode()) % 1000) / 20000.0
                if s > best_s:
                    best, best_s = c, s
            used.add(best["name"])
            usage[best["name"]] += 1
            regions[best["region"]] += 1
            chosen.append((zone, name, tier, best))
        return chosen

    def pick_dense(self, p, clean, fill_clean, usage):
        by_zone = {z: (c, f) for (z, _, _, c), f in zip(clean, fill_clean)}
        prefs_by_zone = {z: prefs for z, _, _, prefs in SLOTS}
        used = {c["name"] for _, _, _, c in clean}
        base = self._mean_lum(p.base)
        out, k = [], 0
        cat_zone, cat_all = Counter(), Counter()
        for z, _, _, c in clean:
            cat_zone[(z, c["cat"])] += 1
            cat_all[c["cat"]] += 1
        for sid, zone, label, size, star, _pz, _view, _x, _y in self.dl.D:
            if star:
                c, f = by_zone[zone]
                out.append((sid, zone, label, size, True, c, f))
                continue
            prefs = ["Wheels", "Tires", "Lubricants and Fluids", "Suspension"] if sid == "5b" else prefs_by_zone[zone]
            best, best_s = None, -1e9
            for c in self.pool():
                if c["name"] in used:
                    continue
                s = (len(prefs) - prefs.index(c["cat"])) * 0.3 if c["cat"] in prefs else -0.8
                s += CONF[c["conf"]] + (0.6 if c["kind"] == "Universal" else 0.0) - 0.35 * usage[c["name"]]
                s -= 1.6 * cat_zone[(zone, c["cat"])] + 0.7 * max(0, cat_all[c["cat"]] - 1)
                s += (zlib.crc32(f"{p.id}|{c['name']}|{sid}".encode()) % 1000) / 20000.0
                if s > best_s:
                    best, best_s = c, s
            used.add(best["name"])
            usage[best["name"]] += 1
            cat_zone[(zone, best["cat"])] += 1
            cat_all[best["cat"]] += 1
            f = self._fill_pick(p, k, base)
            k += 1
            out.append((sid, zone, label, size, False, best, f))
        return out

    @staticmethod
    def _hexes(v):
        return " → ".join(f"`{c}`" for c in v) if isinstance(v, tuple) else f"`{v}`"

    def build_sheet(self, p):
        title, finish = self.title(p), self.finish_of(p)
        usage = self.sponsor_usage(skip_id=p.id)
        picks = self.pick_sponsors(p, usage)
        base = self._mean_lum(p.base)
        fills = [self._fill_pick(p, i, base) for i in range(12)]
        dense = self.pick_dense(p, picks, fills, usage)
        metallic, rough, coat, steps = self.fr.PBR[finish]
        vinyl_r = self.fr.VINYL_R[finish] + (" (same gloss as the paint, as if under the clear coat)"
                                             if finish not in ("Satin", "Matte", "Textured") else " (matches the paint)")
        sw = " ".join(self.pk._swatch(c) for c in (p.base, p.tribal, p.sponsor_a, p.sponsor_b))
        ase = f"{title}.ase"
        fillhex = lambda f: (lambda v: v[0] if isinstance(v, tuple) else v)(p.sponsor_a if f == "A" else p.sponsor_b)
        rows = []
        for (zone, zname, tier, c), f in zip(picks, fills):
            fit = "Universal fitment" if c["kind"] == "Universal" else "Varies: check fitment when the car is chosen"
            rows.append(f"| {zone} | {zname} | [[{c['note']}]] ({c['country']}) | {c['cat']} | {SIZE[tier].split(' (')[0]} | "
                        f"Sponsor {f} `{fillhex(f)}` | {fit}; {c['conf']} |")
        dense_rows = [f"| {'★ ' if star else ''}{sid} | {zone} | {label} | {size} | [[{c['note']}]] ({c['country']}) | {c['cat']} | "
                      f"Sponsor {f} `{fillhex(f)}` |" for sid, zone, label, size, star, c, f in dense]
        brands = "\n".join(f"- **{zname}:** [[{c['note']}]] - {c['item']} ({c['cat']}, {c['region']}). Site: {c['website'] or 'not recorded'}."
                           for (_z, zname, _t, c) in picks)
        text = f"""---
type: project-build-sheet
project: "[[{title}]]"
tags: [build-sheet]
---

# {title} - Build sheet

Back to [[{title}]] · [[{title} - Detail kit]] · [[{title} - Patterns]] · [[Sponsor placement guide]]

Production notes for taking this palette onto a car: swatch file, Substance 3D Painter material recipe and a 12-zone sponsor kit.

## Placement preview

![[{title} - Placement.webp]]

Generated by `Tools/placement_preview.py` from this palette and the sponsor kit below: real logo masters from the [[Ash Works Logo Pack]] where one exists, bold text stand-ins elsewhere. Schematic car, not a render.

## Swatches

{sw}

| Element | Hex |
|---|---|
| Base | {self._hexes(p.base)} |
| Tribals | {self._hexes(p.tribal)} |
| Tribal outline | {self._hexes(p.tribal_outline)} |
| Sponsor A | {self._hexes(p.sponsor_a)} / outline {self._hexes(p.sponsor_a_outline)} |
| Sponsor B | {self._hexes(p.sponsor_b)} / outline {self._hexes(p.sponsor_b_outline)} |

Adobe Swatch Exchange file: [{ase}](Swatches/{ase.replace(' ', '%20')}) (path `Project Library/Swatches/{ase}`). In Illustrator open Swatches panel > menu > Open Swatch Library > Other Library; in Photoshop use the Swatches panel menu > Import Swatches. Gradient fills (base and tribals have two colours) are stored as two separate swatches each; build the gradient from them. Master file with every project: `Project Library/Swatches/All projects.ase`.

## Materials for Substance 3D Painter

Suggested finish: [[Design glossary#{finish}|{finish}]] (from the project note). The recipe uses **only the Metallic and Roughness channels** (no clear-coat or coat channel), so the clear coat is faked with roughness; the values are starting points, tune them under your own lighting. Full explanation: [[Substance Paint Guide]].

| Element | Material | Metallic | Roughness | Clear-coat look (faked) |
|---|---|---|---|---|
| Base | {finish} | {metallic} | {rough} | {coat} |
| Tribals and their outline | Same recipe as the base, roughness about 0.03 lower so they separate from it | same | {rough} minus 0.03 | same |
| Sponsor A and B (with outlines) | Printed vinyl: no flake, no candy | 0.00 | {vinyl_r} | same as the paint |

**Layer recipe for the base**

{chr(10).join(f"{i}. {s}" for i, s in enumerate(steps, 1))}

**Setup:** put the sponsor logos in a separate folder above the paint layers, normal blend, no metallic. Work with the hex codes above (sRGB). Use the Detail kit overlays as separate wear layers (Multiply on base colour, small roughness bumps).

**Export (CarX Drift Racing Online 1 via Kino):** PNG only, 8192 x 8192 per texture set (your maximum); the livery is then baked in the game. Keep the dumped car's texture set names, colour in sRGB and Metallic and Roughness linear. Your logo masters are 8000-8192 px, so they place 1:1. Test the finish on a test car before a full livery. Details: [[Substance Paint Guide]].

## Sponsor kit (12 zones)

Twelve sponsors from the Drift Sponsor Database, one per zone of the [[Sponsor placement guide]]. They are chosen for a spread of categories and regions and rotate between projects; there is no planned platform yet, so these are brands with a drift-scene link and universal or catalogue fitment. When the project gets a car, rerun the sponsor query for that platform and swap in fitment-specific brands.

| Zone | Name | Sponsor | Category | Size | Fill | Fitment and confidence |
|---|---|---|---|---|---|---|
{chr(10).join(rows)}

Fill colours alternate along the body line and are chosen for the better contrast against the base. Rebuild each logo as one-colour vector art in the chosen fill with the sponsor outline colour.

**Brands and products**

{brands}

## Dense layout (Animal Style reference)

The loud version of the sponsor plan, after the way Drift Team Animal Style packs its cars: 36 logos with a few big marks and many small ones, a skirt strip and sticker art between the logos. The 12 primary sponsors above are marked with a star; 24 more are added. Diagram and rules: [[Sponsor placement guide#Dense layout (Animal Style reference)|Sponsor placement guide]].

| Slot | Zone | Position | Size | Sponsor | Category | Fill |
|---|---|---|---|---|---|---|
{chr(10).join(dense_rows)}

**Filler art between the logos:** {FILLER_ART}. Layer order: sticker art and fillers, then the hero graphic, then logos (5-10 % overlap with art is fine, never over another logo's name), then the smallest chrome-look marks. Sizes: L 40-60 % of the panel width, M 25-40 %, S 10-20 %, XS 5-10 %.

Back to [[{title}]].
"""
        (self.folder(p) / f"{title} - Build sheet.md").write_text(text, encoding="utf-8", newline="\n")
        self._drop_section(p, "## Build sheet", "## Notes")
        self._insert_before(p, "## Notes", f"## Build sheet\n\n[[{title} - Build sheet]]: swatches (.ase), Substance material recipe and a 12-zone sponsor kit.\n\n")
        return picks, dense

    # ------------------------------------------------------------------ placement preview
    def build_preview(self, p):
        """Run the vault's own placement_preview.py for this project. Returns (logo masters, text stand-ins)."""
        pp, idx = self.v.placement()
        stats = pp.render(self.folder(p), idx)
        return stats["real"], stats["text"]

    # ------------------------------------------------------------------ everything
    def build_all(self, pid, progress=None, only_missing=True):
        """Build every missing part of project pid; progress(step_index, text) is called before each step."""
        say = progress or (lambda *_: None)
        p = self.load(pid)
        todo = self.missing(p) if only_missing else list(self.STEPS)
        result = {"built": [], "notes": []}
        need = len(SLOTS) + sum(1 for row in self.dl.D if not row[4])   # brands the sponsor kit and dense layout use, each once
        short = len(self.pool()) < need
        for i, step in enumerate(self.STEPS):
            if step not in todo:
                continue
            if short and step in ("Build sheet and sponsor kit", "Placement preview"):
                result["notes"].append(f"Skipped the {step.lower()}: the sponsor database has {len(self.pool())} usable brands and "
                                       f"{need} are needed. Add brands to the Drift Sponsor Database, then press Build missing parts.")
                continue
            say(i, step)
            if step == "Design vocabulary":
                self.add_vocabulary(p)
            elif step == "Detail kit":
                self.add_vocabulary(p)
                self.build_kit(p)
            elif step == "Build sheet and sponsor kit":
                self.add_vocabulary(p)
                self.build_sheet(p)
            elif step == "Placement preview":
                if not (self.folder(p) / f"{self.title(p)} - Build sheet.md").exists():
                    self.add_vocabulary(p)
                    self.build_sheet(p)
                real, text = self.build_preview(p)
                result["notes"].append(f"Placement preview: {real} real logo masters, {text} text stand-ins"
                                       + ("" if real else " (no logo files were found in Sponsor Logo Library/Logo masters, so every logo is a text stand-in)"))
            result["built"].append(step)
        return result
