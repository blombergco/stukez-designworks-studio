"""The Swatch Exchange writer, checked by reading the files back with a small parser."""
import struct
import tempfile
import unittest
from pathlib import Path

from stukez_studio import swatch
from stukez_studio.backend import Proj


def read_ase(path):
    """(version, [(block kind, body)]) of an .ase file; fails if the block count or the length does not add up."""
    data = Path(path).read_bytes()
    assert data[:4] == b"ASEF", "not an ASE file"
    version, _unused, count = struct.unpack(">HHI", data[4:12])
    pos, blocks = 12, []
    for _ in range(count):
        kind, length = struct.unpack(">HI", data[pos:pos + 6])
        blocks.append((kind, data[pos + 6:pos + 6 + length]))
        pos += 6 + length
    assert pos == len(data), "trailing bytes after the last block"
    return version, blocks


def read_name(body):
    """The name at the start of a block body (UTF-16 BE, length counts the terminator)."""
    n = struct.unpack(">H", body[:2])[0]
    return body[2:2 + 2 * n].decode("utf-16-be").rstrip("\0")


def swatch_entries(blocks):
    """[(name, (r, g, b))] for the colour blocks, in file order."""
    out = []
    for kind, body in blocks:
        if kind != 0x0001:
            continue
        name = read_name(body)
        rest = body[2 + 2 * (struct.unpack(">H", body[:2])[0]):]
        assert rest[:4] == b"RGB ", "colour model is not RGB"
        out.append((name, struct.unpack(">3f", rest[4:16])))
    return out


def project(**over):
    fields = dict(id=7, name="Test", platform="S13", status="palette", created="2026-01-01", moods=[], motifs=[], week=0,
                  base="#101010", tribal=["#202020", "#303030"], tribal_outline="#404040",
                  sponsor_a="#505050", sponsor_a_outline="#606060", sponsor_b="#707070", sponsor_b_outline="#808080")
    fields.update(over)
    return Proj(**fields)


class ProjectPaletteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "palette.ase"

    def tearDown(self):
        self.tmp.cleanup()

    def test_group_then_swatches_then_end(self):
        swatch.write_ase(project(), self.path)
        version, blocks = read_ase(self.path)
        self.assertEqual(version, 1)
        self.assertEqual([k for k, _ in blocks], [0xC001] + [0x0001] * 8 + [0xC002])
        self.assertEqual(read_name(blocks[0][1]), "007 Test")

    def test_names_follow_the_slot_order(self):
        swatch.write_ase(project(), self.path)
        _version, blocks = read_ase(self.path)
        self.assertEqual([n for n, _ in swatch_entries(blocks)], [
            "Base #101010", "Tribal 1 #202020", "Tribal 2 #303030", "Tribal outline #404040",
            "Sponsor A #505050", "Sponsor A outline #606060", "Sponsor B #707070", "Sponsor B outline #808080"])

    def test_colour_values_are_scaled_to_one(self):
        swatch.write_ase(project(base="#FF8000"), self.path)
        _version, blocks = read_ase(self.path)
        r, g, b = swatch_entries(blocks)[0][1]
        self.assertAlmostEqual(r, 1.0, places=6)
        self.assertAlmostEqual(g, 128 / 255, places=6)
        self.assertAlmostEqual(b, 0.0, places=6)


class WriteFileTests(unittest.TestCase):
    def test_generic_group_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "grads.ase"
            swatch.write_file(path, "StukeZ gradients", [("Red 1 #FF0000", "#FF0000"), ("Red 2 #000000", "#000000")])
            _version, blocks = read_ase(path)
            self.assertEqual(read_name(blocks[0][1]), "StukeZ gradients")
            self.assertEqual([n for n, _ in swatch_entries(blocks)], ["Red 1 #FF0000", "Red 2 #000000"])
            self.assertEqual(blocks[-1][0], 0xC002)

    def test_empty_group_is_still_a_valid_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.ase"
            swatch.write_file(path, "Empty", [])
            _version, blocks = read_ase(path)
            self.assertEqual([k for k, _ in blocks], [0xC001, 0xC002])


if __name__ == "__main__":
    unittest.main()
