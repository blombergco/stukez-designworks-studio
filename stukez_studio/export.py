"""Export package: everything the vault holds about one project in a single ZIP."""
import zipfile
from pathlib import Path


def project_files(vault, p):
    """[(file, name inside the zip)] for a project: its notes, swatches, placement preview and sponsor logos folder."""
    lib = vault.lib
    found = []
    folder = lib / "Projects" / p.title
    if folder.exists():
        for f in sorted(folder.rglob("*")):
            if f.is_file():
                found.append((f, f"{p.title}/{f.relative_to(folder).as_posix()}"))
    for extra, sub in ((lib / "Swatches" / f"{p.title}.ase", "Swatches"), (lib / "Placement previews" / f"{p.title} - Placement.webp", "Placement")):
        if extra.exists():
            found.append((extra, f"{p.title}/{sub}/{extra.name}"))
    return found


def write_zip(vault, p, path, extra=()):
    """Write the package; `extra` are more (file, zip name) pairs, such as a freshly exported palette card."""
    files = project_files(vault, p) + list(extra)
    seen = set()
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for f, name in files:
            if name in seen:
                continue
            seen.add(name)
            z.write(f, name)
        z.writestr(f"{p.title}/README.txt", f"{p.title}\n\nExported from StukeZ Designworks Studio.\nFiles: {len(seen)}\n")
    return len(seen)
