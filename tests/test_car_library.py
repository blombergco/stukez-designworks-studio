"""The preview car list: the cars that ship with the program, then the ones in the vault's Car Templates folder."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from stukez_studio.cars import CarLibrary, builtin_cars


class AllCarsTests(unittest.TestCase):
    def test_built_in_cars_come_first_then_the_library(self):
        with tempfile.TemporaryDirectory() as tmp:
            lib = Path(tmp) / "Project Library"
            folder = lib / "Car Templates" / "Test Car"
            folder.mkdir(parents=True)
            (folder / "car.json").write_text(json.dumps(dict(name="Test Car", views={}, zones={})), encoding="utf-8")
            cars = CarLibrary(SimpleNamespace(lib=lib)).all_cars()
        built = [c.name for c in builtin_cars()]
        self.assertEqual([c.name for c in cars], built + ["Test Car"])

    def test_no_library_folder_gives_just_the_built_in_cars(self):
        with tempfile.TemporaryDirectory() as tmp:
            cars = CarLibrary(SimpleNamespace(lib=Path(tmp))).all_cars()
        self.assertEqual([c.name for c in cars], [c.name for c in builtin_cars()])


if __name__ == "__main__":
    unittest.main()
