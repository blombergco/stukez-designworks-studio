"""Shared helpers for the Drift Sponsor Database tools."""
import json
import re
from pathlib import Path

DB = Path(__file__).resolve().parent.parent
VOCAB = json.loads((Path(__file__).parent / "vocab.json").read_text(encoding="utf-8"))
CATEGORIES = VOCAB["categories"]
CHASSIS = VOCAB["chassis"]
ENGINES = VOCAB["engines"]


def category_folder(cat):
    return f"{CATEGORIES.index(cat) + 1:02d} {cat}"


def slug_filename(name):
    return re.sub(r'[\\/:*?"<>|]', "-", name).strip()


def split_tokens(fits):
    return [t.strip() for t in fits.split(",") if t.strip()]


def known_token(tok):
    if tok in ("Universal", "Varies"):
        return True
    parts = tok.split("+")
    for p in parts:
        p = p.strip()
        if p in CHASSIS or p in ENGINES:
            continue
        if p in {c["family"] for c in CHASSIS.values() if c["family"]}:
            continue
        if p in {e["family"] for e in ENGINES.values() if e["family"]}:
            continue
        return False
    return True


def cell(text):
    return str(text).replace("|", "/").replace("\n", " ").strip()


def render_brand(b):
    """Render a brand dict to markdown text."""
    cats = b["categories"]
    fm = [
        "---",
        "type: brand",
        f"name: {json.dumps(b['name'], ensure_ascii=False)}",
        f"country: {json.dumps(b['country'], ensure_ascii=False)}",
        f"region: {json.dumps(b['region'])}",
        f"website: {json.dumps(b.get('website', ''))}",
        f"primary_category: {json.dumps(b['primary_category'])}",
        f"categories: {json.dumps(cats)}",
        f"confidence: {json.dumps(b.get('confidence', 'partial'))}",
        f"verified: {json.dumps(b.get('verified', ''))}",
        "tags: " + json.dumps(["drift-sponsor"] + [c.lower().replace(" ", "-") for c in cats]),
        "---",
        "",
        f"# {b['name']}",
        "",
        f"**{b['country']}** · {b['region']} · {b.get('website', '')}",
        "",
        b["summary"].strip(),
        "",
        "## Products & Fitment",
        "",
        "| Category | Product / line | Fits | Notes |",
        "|---|---|---|---|",
    ]
    for p in b["products"]:
        fm.append(f"| {cell(p['cat'])} | {cell(p['item'])} | {cell(p['fits'])} | {cell(p.get('notes', ''))} |")
    fm += ["", "## Drift scene", "", b.get("drift", "_No documented drift-scene link recorded yet._").strip(), ""]
    if b.get("notes"):
        fm += ["## Notes", "", b["notes"].strip(), ""]
    fm += ["## Sources", ""]
    for s in b.get("sources", []):
        fm.append(f"- {s}")
    fm.append("")
    return "\n".join(fm)


def parse_brand(path):
    text = Path(path).read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    meta = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        try:
            meta[k.strip()] = json.loads(v.strip())
        except json.JSONDecodeError:
            meta[k.strip()] = v.strip()
    if meta.get("type") != "brand":
        return None
    rows = []
    in_table = False
    for line in text.splitlines():
        if line.startswith("## Products & Fitment"):
            in_table = True
            continue
        if in_table and line.startswith("## "):
            break
        if in_table and line.startswith("|") and not line.startswith("|---") and "Product / line" not in line:
            cols = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cols) >= 3:
                rows.append({"cat": cols[0], "item": cols[1], "fits": cols[2], "notes": cols[3] if len(cols) > 3 else ""})
    meta["rows"] = rows
    meta["path"] = Path(path)
    return meta


def all_brands():
    out = []
    for p in sorted(DB.glob("[0-9][0-9] */*.md")):
        if p.name.startswith("_"):
            continue
        b = parse_brand(p)
        if b:
            out.append(b)
    return out


def expand_query(chassis, engine):
    """Return the set of tokens a query implies (own token + family)."""
    toks = set()
    for c in chassis:
        toks.add(c)
        fam = CHASSIS.get(c, {}).get("family")
        if fam:
            toks.add(fam)
    for e in engine:
        toks.add(e)
        fam = ENGINES.get(e, {}).get("family")
        if fam:
            toks.add(fam)
    return toks


def match_row(fits, qtoks):
    """Return 'universal' | 'match' | None for a fits string against query tokens."""
    result = None
    for tok in split_tokens(fits):
        if tok == "Universal":
            result = "universal" if result != "match" else result
            continue
        if tok == "Varies":
            result = result or "varies"
            continue
        if all(p.strip() in qtoks for p in tok.split("+")):
            return "match"
    return result
