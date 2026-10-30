"""Reading a project note into a Proj: the concept paragraph, the vocabulary table and the palette slots.

The vault's projectkit (which parses the front matter) is replaced by a stub, so no vault is needed.
"""
import tempfile
import unittest
from pathlib import Path

from stukez_studio.backend import Proj, Vault

NOTE = """---
id: 5
name: Test Car
---

# 005 Test Car

Dark drift livery with a red stripe.

## Colour

| Colour scheme (dark) | [[Red stripe|Red]] and black |
| Hue families | red, black |
| Suggested finish (matte) | matte |
| Value structure | two dark, one light |
"""

FRONT_MATTER = dict(id=5, name="Test Car", platform="S13", status="palette", created="2026-01-01", moods=["calm"],
                    motifs=[], week=2, base="#111111", tribal=["#222222", "#333333"], tribal_outline="#444444",
                    sponsor_a="#555555", sponsor_a_outline="#666666", sponsor_b="#777777", sponsor_b_outline="#888888")


class StubProjectKit:
    @staticmethod
    def _read_fm(_path):
        return dict(FRONT_MATTER)


def loader():
    v = Vault.__new__(Vault)    # skip __init__: it needs a whole vault on disk
    v.pk = StubProjectKit
    return v


class LoadProjectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        folder = Path(self.tmp.name) / "005 Test Car"
        folder.mkdir()
        self.note = folder / "005 Test Car.md"
        self.note.write_text(NOTE, encoding="utf-8")
        self.p = loader()._load_project(self.note)

    def tearDown(self):
        self.tmp.cleanup()

    def test_front_matter_fields(self):
        self.assertEqual((self.p.id, self.p.name, self.p.week), (5, "Test Car", 2))
        self.assertEqual(self.p.title, "005 Test Car")
        self.assertEqual(self.p.tribal, ["#222222", "#333333"])
        self.assertEqual(self.p.folder, self.note.parent)

    def test_concept_is_the_first_prose_paragraph(self):
        self.assertEqual(self.p.concept, "Dark drift livery with a red stripe.")

    def test_vocabulary_table_is_read_with_wikilinks_flattened(self):
        self.assertEqual(self.p.vocab["Colour scheme"], "Red and black")
        self.assertEqual(self.p.vocab["Hue families"], "red, black")
        self.assertEqual(self.p.vocab["Suggested finish"], "matte")
        self.assertEqual(self.p.vocab["Value structure"], "two dark, one light")


class ProjColourTests(unittest.TestCase):
    def test_all_colours_skips_repeats_and_keeps_order(self):
        p = Proj(1, "A", "", "palette", "", [], [], 0, "#111111", ["#222222", "#111111"], "#222222",
                 "#333333", "#333333", "#444444", "#444444")
        self.assertEqual(p.all_colours(), ["#111111", "#222222", "#333333", "#444444"])

    def test_slots_are_in_swatch_order(self):
        p = Proj(1, "A", "", "palette", "", [], [], 0, "#111111", "#222222", "#333333",
                 "#444444", "#555555", "#666666", "#777777")
        self.assertEqual([label for label, _v, _o in p.slots()], [
            "Base", "Tribals", "Tribal outline", "Sponsor A", "Sponsor A outline", "Sponsor B", "Sponsor B outline"])


if __name__ == "__main__":
    unittest.main()
