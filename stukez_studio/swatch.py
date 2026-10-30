"""Adobe Swatch Exchange (.ase) files: the file format, the project palette export and the gradient export.

Depends on nothing else in the program, so the backend and the gradients page can both use it.
"""
import struct
from pathlib import Path


def colours(v):
    return list(v) if isinstance(v, (list, tuple)) else [v]


def _block(kind, body):
    return struct.pack(">HI", kind, len(body)) + body


def _name(s):
    return struct.pack(">H", len(s) + 1) + s.encode("utf-16-be") + b"\0\0"


def _swatch(name, hex_colour):
    r, g, b = (int(hex_colour[k:k + 2], 16) / 255 for k in (1, 3, 5))
    return _block(0x0001, _name(name) + b"RGB " + struct.pack(">3fH", r, g, b, 2))


def write_file(path, title, swatches):
    """A group called `title` holding the swatches, given as (name, hex colour) pairs."""
    blocks = [_block(0xC001, _name(title))]
    blocks += [_swatch(name, c) for name, c in swatches]
    blocks.append(_block(0xC002, b""))
    Path(path).write_bytes(b"ASEF" + struct.pack(">HHI", 1, 0, len(blocks)) + b"".join(blocks))


def write_ase(p, path):
    """Adobe Swatch Exchange file in the same layout as the vault's own swatch files."""
    swatches = []
    for label, value, _outline in p.slots():
        label = "Tribal" if label == "Tribals" else label
        cs = colours(value)
        for i, c in enumerate(cs):
            swatches.append(((f"{label} {i + 1}" if len(cs) > 1 else label) + f" {c}", c))
    write_file(path, p.title, swatches)
