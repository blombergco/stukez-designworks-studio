"""Assembles starter/ (what a new workspace is made from) and legal/ (third-party notices) before a release build.

    py -3 make_starter.py [path to the vault]

starter/ holds the vault's own tools and data modules (so the app does not need the author's vault), a few example
palettes, and empty logo indexes. Nothing personal is copied: the author's drive paths are replaced, brand notes,
logos, prompts and car captures stay out. Commit the result; CI builds the installer from it.
"""
import os
import re
import shutil
import sys
from importlib.metadata import distribution
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from stukez_studio.backend import find_vault   # noqa: E402

TOOLS = {
    "Project Library/Tools": ["projectkit.py", "colouroptions.py", "placement_preview.py"],
    "Project Library/Tools/Archive scripts": ["details_data.py", "details_data2.py", "finish_rules.py", "dense_layout.py"],
    "Drift Sponsor Database/Tools": ["dblib.py", "vocab.json"],
}
EXAMPLE_IDS = (1, 2, 3, 4, 5, 6)      # the example palettes that come with a new workspace
CSV_HEADERS = {                       # the logo indexes start empty; only the header row is kept
    "Project Library/Sponsor Logo Library/ash_works_logos.csv": None,
    "Project Library/Sponsor Logo Library/Core folders/master_list.csv": None,
}
DROP_IN_PATTERN = re.compile(r"^DROP_IN = Path\(r'[^']*'\)$", re.M)   # a hard-coded drive path in the vault's placement_preview.py
DROP_IN_NEW = "DROP_IN = LIB / 'Sponsor Logo Library' / 'Logo masters'"
NOTICE_PACKAGES = ("PySide6", "shiboken6", "pillow", "numpy", "markdown")


def starter(vault):
    out = HERE / "starter"
    if out.exists():
        shutil.rmtree(out)
    for folder, names in TOOLS.items():
        (out / folder).mkdir(parents=True)
        for n in names:
            shutil.copyfile(vault / folder / n, out / folder / n)
    pp = out / "Project Library/Tools/placement_preview.py"
    text = pp.read_text(encoding="utf-8")
    assert DROP_IN_PATTERN.search(text), "placement_preview.py changed: update make_starter.py"
    pp.write_text(DROP_IN_PATTERN.sub(DROP_IN_NEW, text), encoding="utf-8", newline="\n")
    for rel in CSV_HEADERS:
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        with open(vault / rel, encoding="utf-8-sig") as f:
            dst.write_text(f.readline().rstrip("\r\n") + "\n", encoding="utf-8", newline="\n")
    lib = vault / "Project Library"
    n = 0
    for pid in EXAMPLE_IDS:
        folder = next(d for d in (lib / "Projects").iterdir() if d.name.startswith(f"{pid:03d} "))
        note = folder / f"{folder.name}.md"
        dst = out / "Project Library/Projects" / folder.name
        dst.mkdir(parents=True)
        shutil.copyfile(note, dst / note.name)
        ase = lib / "Swatches" / f"{folder.name}.ase"
        if ase.exists():
            (out / "Project Library/Swatches").mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ase, out / "Project Library/Swatches" / ase.name)
        n += 1
    from stukez_studio import __version__
    (out / "VERSION").write_text(__version__ + "\n", encoding="utf-8")
    print(f"starter/: {sum(1 for _ in out.rglob('*') if _.is_file())} files, {n} example palettes, version {__version__}")


def notices():
    """legal/THIRD_PARTY_NOTICES.txt: the licences of what the app ships, with their licence files where the package has them."""
    legal = HERE / "legal"
    legal.mkdir(exist_ok=True)
    lines = ["StukeZ Designworks Studio uses these open source packages.", ""]
    for name in NOTICE_PACKAGES:
        d = distribution(name)
        lic = d.metadata.get("License-Expression") or d.metadata.get("License") or "see package"
        lines += [f"{d.metadata['Name']} {d.version}", f"  Licence: {lic}", f"  Home: {d.metadata.get('Home-page') or d.metadata.get('Project-URL') or ''}", ""]
    lines += ["Qt for Python (PySide6) is used under the GNU Lesser General Public License v3 (legal/LGPL-3.0.txt). The program is",
              "installed as a folder with the Qt libraries as separate files, so they can be replaced by a modified version.",
              "Source code of Qt for Python: https://code.qt.io/cgit/pyside/pyside-setup.git/", ""]
    for name in ("pillow", "numpy", "markdown"):
        d = distribution(name)
        for f in d.files or []:
            if f.name.upper().startswith(("LICENSE", "LICENCE")) and "licenses" in f.parts and len(f.parts) <= 3:
                lines += ["=" * 78, f"{d.metadata['Name']} - {f.name}", "=" * 78, d.locate_file(f).read_text(encoding="utf-8", errors="replace"), ""]
                break
    (legal / "THIRD_PARTY_NOTICES.txt").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"legal/THIRD_PARTY_NOTICES.txt written; LGPL text present: {(legal / 'LGPL-3.0.txt').exists()}")


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else find_vault(os.environ.get("KAIZEN_VAULT", ""))
    if root is None:
        sys.exit("Could not find the vault; pass its path.")
    starter(root)
    notices()
