"""Workspaces: the folder a user works in.

A workspace is a small vault with the same folders as the author's vault, made from the starter that ships inside the
app (tools, data modules, a few example palettes, empty logo indexes). The app and the vault tools therefore work the
same way for everyone. A workspace carries a marker file; the app only ever updates the tools of a folder that has the
marker, so a hand-made vault such as the author's own is never touched.
"""
import json
import shutil
import sys
from datetime import date
from pathlib import Path

from . import __version__

MARKER = ".stukez-workspace.json"
SCHEMA = 1
TOOL_DIRS = ("Project Library/Tools", "Drift Sponsor Database/Tools")
EMPTY_DIRS = ("Project Library/Projects", "Project Library/Swatches", "Project Library/Placement previews",
              "Project Library/Car Templates", "Project Library/Gradients", "Project Library/Sponsor Logo Library/Core folders",
              "Project Library/Sponsor Logo Library/Logo masters", "Gemini Prompt")
LOGO_README = """Put your sponsor logo files here (PNG with a transparent background, 1000 pixels or wider).

Name them  Brand__black__4096px.png  or  Brand__white__4096px.png
(two underscores around the colour; the number is the width in pixels).
The Placement preview and the On car view then use them for that brand.
"""


def app_base():
    """The folder the program's own files (starter, legal) live in: the install folder, or the source folder."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def starter_dir():
    return app_base() / "starter"


def default_path():
    return Path.home() / "Documents" / "StukeZ Designworks Studio"


def is_workspace(root):
    return (Path(root) / MARKER).exists()


def _copy_tree(src, dst, overwrite, skip=lambda rel: False):
    n = 0
    for f in src.rglob("*"):
        if not f.is_file():
            continue
        rel = f.relative_to(src)
        if skip(rel.as_posix()):
            continue
        target = dst / rel
        if target.exists() and not overwrite:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(f, target)
        n += 1
    return n


def create(path, examples=True):
    """Make a new workspace at `path` (an empty or missing folder). Returns the path."""
    root = Path(path)
    src = starter_dir()
    if not (src / "VERSION").exists():
        raise FileNotFoundError(f"The program's starter files are missing ({src}). Reinstall the program.")
    if root.exists() and any(root.iterdir()) and not is_workspace(root):
        raise ValueError(f"{root} is not empty. Choose an empty folder, or a new one.")
    root.mkdir(parents=True, exist_ok=True)
    for d in EMPTY_DIRS:
        (root / d).mkdir(parents=True, exist_ok=True)
    skip = (lambda rel: rel == "VERSION") if examples else (lambda rel: rel == "VERSION" or rel.startswith("Project Library/Projects/") or rel.endswith(".ase"))
    _copy_tree(src, root, overwrite=False, skip=skip)
    vocab = json.loads((root / "Drift Sponsor Database/Tools/vocab.json").read_text(encoding="utf-8"))
    for i, cat in enumerate(vocab["categories"], 1):
        (root / "Drift Sponsor Database" / f"{i:02d} {cat}").mkdir(exist_ok=True)
    (root / "Project Library/Sponsor Logo Library/Logo masters/README.txt").write_text(LOGO_README, encoding="utf-8")
    (root / MARKER).write_text(json.dumps({"schema": SCHEMA, "created": date.today().isoformat(), "tools_version": (src / "VERSION").read_text().strip(),
                                           "app": __version__}, indent=1), encoding="utf-8")
    return root


def sync_tools(root):
    """After an update: bring the tools of a workspace up to the version that ships with the app. True if anything changed."""
    root = Path(root)
    if not is_workspace(root):
        return False
    src = starter_dir()
    if not (src / "VERSION").exists():
        return False
    marker = json.loads((root / MARKER).read_text(encoding="utf-8"))
    new = (src / "VERSION").read_text().strip()
    if marker.get("tools_version") == new:
        return False
    for d in TOOL_DIRS:
        _copy_tree(src / d, root / d, overwrite=True)
    marker.update(tools_version=new, app=__version__)
    (root / MARKER).write_text(json.dumps(marker, indent=1), encoding="utf-8")
    return True
