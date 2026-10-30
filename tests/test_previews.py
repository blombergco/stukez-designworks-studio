"""The preview hub: it stores the car, layout and paint mode, and repaints every widget that has preview_changed()."""
import unittest
from types import SimpleNamespace

from PySide6.QtWidgets import QApplication, QWidget

from stukez_studio import carrender, previews, render


class Watcher(QWidget):
    def __init__(self):
        super().__init__()
        self.calls = 0

    def preview_changed(self):
        self.calls += 1


class PreviewHubTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.saved = (render.PREVIEW_CAR, render.LAYOUT, carrender.PAINT)
        self.watcher = Watcher()
        self.calls_before = 0

    def tearDown(self):
        self.watcher.deleteLater()
        render.PREVIEW_CAR, render.LAYOUT, carrender.PAINT = self.saved
        self.app.processEvents()

    def test_set_car_stores_it_and_repaints(self):
        car = SimpleNamespace(name="A")
        previews.set_car(car)
        self.assertIs(render.PREVIEW_CAR, car)
        self.assertGreaterEqual(self.watcher.calls, 1)

    def test_set_paint_stores_it_and_repaints(self):
        previews.set_paint("base")
        self.assertEqual(carrender.PAINT, "base")
        self.assertGreaterEqual(self.watcher.calls, 1)

    def test_layout_off_stays_off_without_a_repaint(self):
        render.LAYOUT = None
        previews.set_layout(None)
        self.assertEqual(self.watcher.calls, 0)

    def test_layout_on_repaints_and_switching_off_repaints_once_more(self):
        board = SimpleNamespace(items=[])
        previews.set_layout(board)
        self.assertIs(render.LAYOUT, board)
        on = self.watcher.calls
        self.assertGreaterEqual(on, 1)
        previews.set_layout(None)
        self.assertIsNone(render.LAYOUT)
        self.assertGreater(self.watcher.calls, on)

    def test_widgets_without_the_hook_are_left_alone(self):
        plain = QWidget()
        try:
            previews.refresh()     # must not raise
        finally:
            plain.deleteLater()


if __name__ == "__main__":
    unittest.main()
