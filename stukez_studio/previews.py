"""What every livery preview shows: the preview car, the board layout and the paint mode.

The painting code reads these from render and carrender. This module is the one place that sets them. After a change it
tells every widget with a preview_changed() method to repaint, so the main window does not need to know which pages
show a preview.
"""
from PySide6.QtWidgets import QApplication

from . import carrender, render


def set_car(car):
    render.set_preview_car(car)
    refresh()


def set_layout(board):
    """The board whose logos and tribals are drawn on every preview; None = the plain sponsor plates."""
    was_on = render.LAYOUT is not None
    render.LAYOUT = board
    if was_on or board is not None:
        refresh()


def set_paint(mode):
    """Gradient ("") or solid colour ("base") for every preview."""
    carrender.PAINT = mode
    refresh()


def refresh():
    """Repaint every widget that shows a preview."""
    for w in QApplication.allWidgets():
        notify = getattr(w, "preview_changed", None)
        if notify is not None:
            notify()
