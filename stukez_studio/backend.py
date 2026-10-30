"""Backend: reads and writes the Kaizen Cave vault through the vault's own tools.

The vault stays the source of truth. Project notes are created with Project Library/Tools/projectkit.py,
prompt colour paragraphs come from colouroptions.py and sponsor matching from dblib.py, so the app and
Obsidian always agree on rules and data.
"""
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote, unquote

# imported here so PyInstaller bundles what the vault tools need when they are loaded at run time
import argparse, collections, dataclasses, datetime, shutil  # noqa: E401,F401

from .swatch import colours, write_ase


PARTS = ("Design vocabulary", "Detail kit", "Build sheet and sponsor kit", "Placement preview")


def looks_like_vault(p):
    p = Path(p)
    return ((p / "Project Library" / "Tools" / "projectkit.py").exists()
            and (p / "Drift Sponsor Database" / "Tools" / "dblib.py").exists())


def find_vault(saved=""):
    """Locate the Kaizen Cave section: env var, saved setting, then every parent of the program."""
    cands = [os.environ.get("KAIZEN_VAULT", ""), saved]
    here = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve()
    cands += [str(a) for a in here.parents]
    cands += [str(Path.home() / "Documents" / "Obsidian stuff" / "obsidian-hub-main" / "Obsidian Hub Main"
                  / "Kaizen Cave Main PC")]
    for c in cands:
        if c and looks_like_vault(c):
            return Path(c)
    return None


@dataclass
class Proj:
    id: int
    name: str
    platform: str
    status: str
    created: str
    moods: list
    motifs: list
    week: int
    base: object
    tribal: object
    tribal_outline: object
    sponsor_a: object
    sponsor_a_outline: object
    sponsor_b: object
    sponsor_b_outline: object
    folder: Path = None
    note: Path = None
    concept: str = ""
    vocab: dict = field(default_factory=dict)

    @property
    def title(self):
        return f"{self.id:03d} {self.name}"

    def all_colours(self):
        out = []
        for v in (self.base, self.tribal, self.tribal_outline, self.sponsor_a, self.sponsor_a_outline,
                  self.sponsor_b, self.sponsor_b_outline):
            for c in colours(v):
                if c not in out:
                    out.append(c)
        return out

    def slots(self):
        """(label, value, is_outline) in the order used by swatch files and cards."""
        return [("Base", self.base, False), ("Tribals", self.tribal, False),
                ("Tribal outline", self.tribal_outline, True), ("Sponsor A", self.sponsor_a, False),
                ("Sponsor A outline", self.sponsor_a_outline, True), ("Sponsor B", self.sponsor_b, False),
                ("Sponsor B outline", self.sponsor_b_outline, True)]


class Vault:
    def __init__(self, root):
        self.root = Path(root)
        self.lib = self.root / "Project Library"
        self.gem = self.root / "Gemini Prompt"
        self.db = self.root / "Drift Sponsor Database"
        for tools in (self.lib / "Tools", self.db / "Tools"):
            if str(tools) not in sys.path:
                sys.path.insert(0, str(tools))
        import projectkit, colouroptions, dblib  # vault tools
        self.pk, self.co, self.dblib = projectkit, colouroptions, dblib
        self._builder = None
        self._carlib = None
        self._pp = None
        self.invalidate()

    def invalidate(self):
        """Forget what was read from disk; the next call of each method reads it again."""
        self._stems = self._projects = self._prompts = self._brands = None

    # ------------------------------------------------------------------ projects
    def projects(self, reload=False):
        if self._projects is None or reload:
            out = []
            for d in sorted(self.pk.NOTES.iterdir()):
                f = d / f"{d.name}.md"
                if d.is_dir() and f.exists():
                    try:
                        out.append(self._load_project(f))
                    except (KeyError, ValueError):
                        continue
            self._projects = out
        return self._projects

    def _load_project(self, f):
        fm = self.pk._read_fm(f)
        t = lambda v: list(v) if isinstance(v, list) else v
        text = f.read_text(encoding="utf-8")
        body = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
        concept = ""
        for para in re.split(r"\n\s*\n", body):
            para = para.strip()
            if para and not para.startswith(("#", "|", "<!--", "-")):
                concept = para
                break
        vocab = {}
        for m in re.finditer(r"(?m)^\| (Colour scheme[^|]*|Hue families|Value structure|Suggested finish[^|]*|Finish[^|]*) \| (.+?) \|$", body):
            vocab[m.group(1).split(" (")[0].strip()] = re.sub(r"\[\[(?:[^\]|]*\\?\|)?([^\]]+)\]\]", r"\1", m.group(2))
        return Proj(int(fm["id"]), fm["name"], fm.get("platform", ""), fm.get("status", "palette"),
                    str(fm.get("created", "")), list(fm.get("moods", [])), list(fm.get("motifs", [])),
                    int(fm.get("week", 0) or 0), t(fm["base"]), t(fm["tribal"]), t(fm["tribal_outline"]),
                    t(fm["sponsor_a"]), t(fm["sponsor_a_outline"]), t(fm["sponsor_b"]), t(fm["sponsor_b_outline"]),
                    folder=f.parent, note=f, concept=concept, vocab=vocab)

    def project_files(self, p):
        """Extra material of a project: build sheet, detail kit, patterns, preview image, swatches."""
        d = p.folder
        pick = lambda suffix: next(iter(d.glob(f"* - {suffix}.md")), None)
        preview = self.lib / "Placement previews" / f"{p.title} - Placement.webp"
        ase = self.lib / "Swatches" / f"{p.title}.ase"
        return {"Build sheet": pick("Build sheet"), "Detail kit": pick("Detail kit"), "Patterns": pick("Patterns"),
                "Design plan": pick("Design plan"), "preview": preview if preview.exists() else None,
                "ase": ase if ase.exists() else None}

    def missing_parts(self, p):
        """Generated parts a project still lacks (see PARTS); cheap, only looks at files."""
        out = []
        if "## Design vocabulary" not in p.note.read_text(encoding="utf-8"):
            out.append(PARTS[0])
        if not (p.folder / f"{p.title} - Detail kit.md").exists():
            out.append(PARTS[1])
        if not (p.folder / f"{p.title} - Build sheet.md").exists():
            out.append(PARTS[2])
        if not (self.lib / "Placement previews" / f"{p.title} - Placement.webp").exists():
            out.append(PARTS[3])
        return out

    def builder(self):
        if self._builder is None:
            from .builder import ProjectBuilder   # imports numpy and Pillow, so only when needed
            self._builder = ProjectBuilder(self)
        return self._builder

    def cars(self):
        if self._carlib is None:
            from .cars import CarLibrary
            self._carlib = CarLibrary(self)
        return self._carlib

    def placement(self):
        """(placement_preview module, logo index): the vault's own placement renderer and its logo lookup, loaded once."""
        if self._pp is None:
            import placement_preview as pp
            self._pp = (pp, pp.load_logo_index())
        return self._pp

    def next_id(self):
        return self.pk.next_id()

    def used_names(self):
        return {p.name.lower() for p in self.projects()}

    def to_pk(self, d, pid=None):
        """Build a projectkit Project from a plain dict (the generator's output)."""
        t = lambda v: tuple(v) if isinstance(v, list) else v
        return self.pk.P(pid or self.next_id(), d["name"], d.get("concept", "") or "New palette.", t(d["base"]),
                         t(d["tribal"]), t(d["tribal_outline"]), t(d["sponsor_a"]), t(d["sponsor_a_outline"]),
                         t(d["sponsor_b"]), t(d["sponsor_b_outline"]), platform=d.get("platform", ""),
                         moods=d.get("moods", ()))

    def save_project(self, d):
        """Create the project note + patterns note with projectkit, then swatches and the index."""
        p = self.to_pk(d)
        self.pk.save(p)
        self.pk.rebuild_index()
        proj = self._load_project(self.pk.project_dir(p) / p.filename)
        ase = self.lib / "Swatches" / f"{proj.title}.ase"
        ase.parent.mkdir(exist_ok=True)
        write_ase(proj, ase)
        self.invalidate()
        return next(x for x in self.projects() if x.id == proj.id)

    # ------------------------------------------------------------------ prompts
    def prompts(self):
        if self._prompts is None:
            items = self.co.load_prompts()
            for it in items:
                it["title"] = it["short"] if it["kind"] != "pattern" else f'{it["short"]} (pattern)'
                it["category"] = it["cat"] + (f' / {it["group"]}' if it.get("group") else "")
            self._prompts = items
        return self._prompts

    def master_prompt(self, item):
        text = item["path"].read_text(encoding="utf-8").split(self.co.M_START)[0]
        if item["kind"] == "pattern":
            num = re.match(r".*#(\d+)\.", item["key"]).group(1)
            m = re.search(rf"(?ms)^## {num}\. .*?(?=^## |\Z)", text)
            text = m.group(0) if m else text
        m = re.search(r"```\n(.*?)\n```", text, re.S)
        return m.group(1).strip() if m else ""

    def recoloured(self, item, proj):
        """The master prompt with its 'Colour treatment' paragraph swapped for a palette (Proj or pk.Project)."""
        base = self.master_prompt(item)
        if isinstance(proj, dict):
            pkp = self.to_pk(dict(proj, name=proj.get("name") or "Generator palette"), 0)
        else:
            pkp = self.to_pk_from_proj(proj) if isinstance(proj, Proj) else proj
        two = item.get("colours") == 2
        para = self.co.colour_paragraph2(pkp) if two else self.co.colour_paragraph(pkp)
        new, n = re.subn(r"(?m)^Colour treatment:.*$", lambda _m: para, base, count=1)
        return new if n else f"{base}\n\n{para}"

    def to_pk_from_proj(self, p):
        d = dict(name=p.name, base=p.base, tribal=p.tribal, tribal_outline=p.tribal_outline,
                 sponsor_a=p.sponsor_a, sponsor_a_outline=p.sponsor_a_outline, sponsor_b=p.sponsor_b,
                 sponsor_b_outline=p.sponsor_b_outline, platform=p.platform, moods=p.moods)
        return self.to_pk(d, p.id)

    def vault_options(self, item):
        """The ready-made colour versions already stored in the prompt note: [(label, code)]."""
        if item["kind"] != "prompt":
            return []
        text = item["path"].read_text(encoding="utf-8")
        if self.co.M_START not in text:
            return []
        block = text.split(self.co.M_START, 1)[1].split(self.co.M_END)[0]
        return [(f"{m.group(1)} - {m.group(2).strip()}", m.group(3).strip()) for m in
                re.finditer(r"(?ms)^### Option (\w) - (.+?)\n.*?```\n(.*?)\n```", block)]

    def prompts_for_project(self, p):
        """Prompt notes that carry this project's palette (the generated list in the project note)."""
        text = p.note.read_text(encoding="utf-8")
        m = re.search(r"<!-- motifs:auto -->(.*?)<!-- /motifs:auto -->", text, re.S)
        if not m:
            return []
        names = re.findall(r"\[\[([^\]|]+)\]\]", m.group(1))
        by_stem = {}
        for it in self.prompts():
            by_stem.setdefault(it["stem"], it)
        return [by_stem[n] for n in names if n in by_stem]

    # ------------------------------------------------------------------ sponsors
    def brands(self):
        if self._brands is None:
            self._brands = self.dblib.all_brands()
        return self._brands

    def sponsor_rows(self, chassis=(), engine=(), category="", region="", text="", universal=True):
        d = self.dblib
        q = d.expand_query(chassis, engine)
        filtering = bool(chassis or engine)
        out = []
        needle = text.lower().strip()
        for b in self.brands():
            if region and b.get("region") != region:
                continue
            if needle and needle not in b["name"].lower() and not any(needle in r["item"].lower() for r in b["rows"]):
                continue
            for r in b["rows"]:
                if category and r["cat"] != category:
                    continue
                m = d.match_row(r["fits"], q) if filtering else ""
                if filtering and (m is None or (m != "match" and not universal)):
                    continue
                out.append(dict(brand=b, cat=r["cat"], item=r["item"], fits=r["fits"], notes=r["notes"],
                                match=m or ""))
        order = {"match": 0, "universal": 1, "varies": 2, "": 3}
        out.sort(key=lambda x: (self.dblib.CATEGORIES.index(x["cat"]) if x["cat"] in self.dblib.CATEGORIES else 99,
                                order[x["match"]], x["brand"]["name"].lower()))
        return out

    # ------------------------------------------------------------------ notes
    def stems(self):
        if self._stems is None:
            idx = {}
            for dp, _dn, fn in os.walk(self.root):
                if ".git" in dp or "Archive scripts" in dp:
                    continue
                for f in fn:
                    if f.endswith(".md") or f.lower().endswith((".webp", ".png", ".svg")):
                        idx.setdefault(Path(f).stem if f.endswith(".md") else f, []).append(Path(dp) / f)
            self._stems = idx
        return self._stems

    def resolve(self, name):
        name = unquote(name).split("#")[0].strip()
        hits = self.stems().get(name) or []
        return min(hits, key=lambda p: len(p.parts)) if hits else None

    def note_html(self, path):
        """Markdown note -> HTML for the in-app viewer (wikilinks become note: links, swatches become chips)."""
        import markdown
        text = Path(path).read_text(encoding="utf-8")
        text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
        text = re.sub(r"<!--.*?-->", "", text, flags=re.S)

        def img(m):
            hit = self.resolve_asset(m.group(1))
            return f'<img src="{hit.as_uri()}" width="620">' if hit else ""
        text = re.sub(r"!\[\[([^\]|]+)(?:\|[^\]]*)?\]\]", img, text)
        text = re.sub(r"!\[[^\]]*\]\(([^)]+\.(?:webp|png|jpg|svg))\)",
                      lambda m: self._md_img(Path(path), m.group(1)), text)
        text = re.sub(r"\[\[#([^\]]+)\]\]", r"\1", text)
        text = re.sub(r"\[\[([^\]|#\\]+)(?:#[^\]|\\]*)?(?:\\?\|([^\]]+))?\]\]",
                      lambda m: f"[{m.group(2) or m.group(1)}](note:{quote(m.group(1))})", text)
        text = re.sub(r'<span style="[^"]*?background:linear-gradient\(90deg,(#[0-9A-Fa-f]{6}),(#[0-9A-Fa-f]{6})\)"></span>',
                      r'<span style="background-color:\1">&nbsp;&nbsp;&nbsp;</span><span style="background-color:\2">&nbsp;&nbsp;&nbsp;</span>', text)
        text = re.sub(r'<span style="[^"]*?background:(#[0-9A-Fa-f]{6})"></span>',
                      r'<span style="background-color:\1">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>', text)
        return markdown.markdown(text, extensions=["tables", "fenced_code"])

    def _md_img(self, note, rel):
        f = (Path(note).parent / unquote(rel))
        if not f.exists():
            f = self.lib / unquote(rel)
        return f'<img src="{f.as_uri()}" width="620">' if f.exists() else ""

    def resolve_asset(self, name):
        hits = self.stems().get(unquote(name).strip()) or []
        return hits[0] if hits else None


