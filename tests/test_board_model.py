"""The livery board's item model: defaults, clean-up of saved items, colour and outline resolution, files and geometry."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from PIL import Image
from PySide6.QtCore import QPointF, QRectF

from stukez_studio import board as bd


class DefaultItemTests(unittest.TestCase):
    def test_sponsor_logo_keeps_its_own_colours_and_no_outline(self):
        it = bd.default_item("sponsor")
        self.assertEqual(it["colour"]["mode"], "original")
        self.assertFalse(it["outline"]["on"])
        self.assertEqual(it["w"], 0.16)

    def test_tribal_takes_the_tribal_colour_with_an_outline(self):
        it = bd.default_item("tribal")
        self.assertEqual(it["colour"]["mode"], "tribal")
        self.assertTrue(it["outline"]["on"])
        self.assertEqual(it["w"], 0.4)

    def test_every_item_gets_its_own_id(self):
        self.assertNotEqual(bd.default_item()["id"], bd.default_item()["id"])


class CleanItemTests(unittest.TestCase):
    def test_unknown_kind_falls_back_to_sponsor(self):
        self.assertEqual(bd.clean_item({"kind": "banana"})["kind"], "sponsor")

    def test_positions_and_sizes_are_clamped(self):
        it = bd.clean_item({"x": 9, "y": -9, "w": 50, "opacity": 0})
        self.assertEqual((it["x"], it["y"]), (1.5, -0.5))
        self.assertEqual(it["w"], 2.0)
        self.assertEqual(it["opacity"], 0.05)
        self.assertEqual(bd.clean_item({"w": 0})["w"], 0.01)

    def test_rotation_wraps_into_minus_180_to_180(self):
        self.assertEqual(bd.clean_item({"rot": 370})["rot"], 10.0)
        self.assertEqual(bd.clean_item({"rot": 540})["rot"], -180.0)

    def test_invalid_hex_keeps_the_default_colour(self):
        it = bd.clean_item({"colour": {"mode": "custom", "value": "nope"}})
        self.assertEqual(it["colour"]["value"], "#FFFFFF")

    def test_hex_without_hash_is_accepted_and_uppercased(self):
        it = bd.clean_item({"colour": {"mode": "custom", "value": "ff8800"}})
        self.assertEqual(it["colour"]["value"], "#FF8800")

    def test_gradient_keeps_two_colours(self):
        it = bd.clean_item({"colour": {"mode": "custom", "value": ["#ff0000", "#0000ff", "#00ff00"]}})
        self.assertEqual(it["colour"]["value"], ["#FF0000", "#0000FF"])

    def test_unknown_modes_are_ignored(self):
        it = bd.clean_item({"colour": {"mode": "bogus"}, "bg": "bogus", "outline": {"mode": "bogus"}})
        self.assertEqual(it["colour"]["mode"], "original")
        self.assertEqual(it["bg"], "auto")
        self.assertEqual(it["outline"]["mode"], "auto")

    def test_outline_size_is_clamped(self):
        self.assertEqual(bd.clean_item({"outline": {"size": 50}})["outline"]["size"], 12.0)

    def test_saved_id_is_kept(self):
        self.assertEqual(bd.clean_item({"id": "abc123"})["id"], "abc123")


class PaletteNamespaceTests(unittest.TestCase):
    def test_missing_slots_get_fallbacks(self):
        pl = bd.palette_ns({"base": "#111111"})
        self.assertEqual(pl.base, "#111111")
        self.assertEqual(pl.tribal, "#6E8B1F")

    def test_lists_are_copied_as_lists(self):
        pl = bd.palette_ns(SimpleNamespace(base=None, tribal=("#aaaaaa", "#bbbbbb")))
        self.assertEqual(pl.tribal, ["#aaaaaa", "#bbbbbb"])

    def test_cut_settings_only_appear_when_given(self):
        self.assertFalse(hasattr(bd.palette_ns({}), "cut_angle"))
        self.assertEqual(bd.palette_ns({"cut_angle": 30}).cut_angle, 30)


class ResolveTests(unittest.TestCase):
    PL = bd.palette_ns({"base": "#111111", "sponsor_a": "#222222", "sponsor_a_outline": "#333333",
                        "sponsor_b": ["#444444", "#555555", "#666666"], "sponsor_b_outline": "#777777",
                        "tribal": "#888888", "tribal_outline": "#999999"})

    def test_original_colour_resolves_to_none(self):
        self.assertIsNone(bd.resolve_colour(bd.default_item("sponsor"), self.PL))

    def test_palette_slot_resolves_to_its_value(self):
        it = bd.default_item("sponsor")
        it["colour"]["mode"] = "sponsor_a"
        self.assertEqual(bd.resolve_colour(it, self.PL), "#222222")

    def test_gradient_slot_keeps_two_colours(self):
        it = bd.default_item("sponsor")
        it["colour"]["mode"] = "sponsor_b"
        self.assertEqual(bd.resolve_colour(it, self.PL), ["#444444", "#555555"])

    def test_custom_colour_is_used_as_given(self):
        it = bd.default_item("sponsor")
        it["colour"] = dict(mode="custom", value="#ABCDEF")
        self.assertEqual(bd.resolve_colour(it, self.PL), "#ABCDEF")

    def test_outline_is_off_unless_switched_on(self):
        self.assertIsNone(bd.resolve_outline(bd.default_item("sponsor"), self.PL))

    def test_auto_outline_follows_the_logo_colour_slot(self):
        it = bd.default_item("sponsor")
        it["outline"]["on"] = True
        it["colour"]["mode"] = "sponsor_b"
        self.assertEqual(bd.resolve_outline(it, self.PL), "#777777")

    def test_auto_outline_for_a_tribal_is_the_tribal_outline(self):
        it = bd.default_item("tribal")
        self.assertEqual(bd.resolve_outline(it, self.PL), "#999999")

    def test_custom_outline_is_used_as_given(self):
        it = bd.default_item("sponsor")
        it["outline"] = dict(on=True, mode="custom", value="#010203", size=3.0)
        self.assertEqual(bd.resolve_outline(it, self.PL), "#010203")


class BoardFileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.lib = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_safe_name_replaces_characters_windows_forbids(self):
        self.assertEqual(bd.safe_name('a/b:c*d'), "a-b-c-d")
        self.assertEqual(bd.safe_name(" .. "), "Untitled")

    def test_save_and_load_round_trip(self):
        b = bd.Board(self.lib, "My Car")
        b.source = 3
        b.items.append(bd.default_item("tribal", "top", "Logos/x.png", "X"))
        b.save()
        self.assertEqual(bd.Board.names(self.lib), ["My Car"])
        loaded = bd.Board.load(self.lib, "My Car")
        self.assertEqual(loaded.source, 3)
        self.assertEqual([i["id"] for i in loaded.items], [i["id"] for i in b.items])
        self.assertEqual(loaded.items[0]["view"], "top")

    def test_load_skips_items_without_a_file(self):
        b = bd.Board(self.lib, "Broken")
        b.root.mkdir(parents=True)
        b.path.write_text(json.dumps({"items": [{"name": "no file"}, {"file": "Logos/a.png"}]}), encoding="utf-8")
        self.assertEqual(len(bd.Board.load(self.lib, "Broken").items), 1)

    def test_import_copies_the_image_and_numbers_repeats(self):
        src_dir = self.lib / "incoming"
        src_dir.mkdir()
        src = src_dir / "logo.png"
        Image.new("RGBA", (20, 10), (255, 0, 0, 255)).save(src)
        b = bd.Board(self.lib, "Car")
        first = b.import_file(src)
        second = b.import_file(src)
        self.assertEqual(first["file"], "Logos/logo.png")
        self.assertEqual(second["file"], "Logos/logo 2.png")
        self.assertTrue((b.root / "Logos" / "logo 2.png").exists())

    def test_unused_files_lists_logos_no_item_points_to(self):
        src = self.lib / "logo.png"
        Image.new("RGBA", (4, 4), (0, 0, 0, 255)).save(src)
        b = bd.Board(self.lib, "Car")
        it = b.import_file(src)
        self.assertEqual(b.unused_files(), [])
        b.items.remove(it)
        self.assertEqual([f.name for f in b.unused_files()], ["logo.png"])

    def test_unsupported_file_type_is_refused(self):
        with self.assertRaises(ValueError):
            bd.Board(self.lib, "Car").import_file(self.lib / "notes.txt")

    def test_empty_text_is_refused(self):
        with self.assertRaises(ValueError):
            bd.Board(self.lib, "Car").add_text("   ")


class GeometryTests(unittest.TestCase):
    T = QRectF(0, 0, 200, 100)
    PREP = SimpleNamespace(content=(100, 50))   # a logo 100 x 50 pixels, so its shape is 2 : 1

    def item(self, **over):
        it = bd.default_item("sponsor")
        it.update(x=0.5, y=0.5, w=0.5, rot=0.0, flip=False)
        it.update(over)
        return it

    def test_centre_of_the_item_maps_to_its_place(self):
        p = bd.item_transform(self.item(), self.T).map(QPointF(0, 0))
        self.assertAlmostEqual(p.x(), 100)
        self.assertAlmostEqual(p.y(), 50)

    def test_hit_inside_the_logo(self):
        self.assertTrue(bd.hit(self.item(), self.T, self.PREP, QPointF(100, 50)))

    def test_hit_stops_at_the_edge_plus_margin(self):
        it = self.item()
        self.assertTrue(bd.hit(it, self.T, self.PREP, QPointF(152, 50)))
        self.assertFalse(bd.hit(it, self.T, self.PREP, QPointF(154, 50)))

    def test_rotated_logo_is_hit_along_its_new_axis(self):
        it = self.item(rot=90.0)
        # turned a quarter: the logo is now 50 wide and 100 tall on screen
        self.assertTrue(bd.hit(it, self.T, self.PREP, QPointF(100, 90)))
        self.assertFalse(bd.hit(it, self.T, self.PREP, QPointF(140, 50)))


if __name__ == "__main__":
    unittest.main()
