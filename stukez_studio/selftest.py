"""Self-test hooks for a built copy of the program. Normal runs never use them.

KAIZEN_SELFTEST=<png path>        after the window opens, save a screenshot there and quit
KAIZEN_SELFTEST_SAVE=1            also save a test palette (only with KAIZEN_VAULT, so the real workspace is never touched)
KAIZEN_SELFTEST_CAR=<folder>      import the cars in that folder, preview one and open the On car tab (needs KAIZEN_VAULT)
KAIZEN_SELFTEST_CREATE=<folder>   make a workspace from the program's own starter files there, without the dialog
"""
import os
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox

from . import workspace
from .cars import find_views, scan_folder


def create_workspace():
    """The workspace for a smoke test of an installed copy, as on a computer that never ran the program.

    It is made from the starter files, and KAIZEN_VAULT is set to it, so the program opens it."""
    root = workspace.create(os.environ["KAIZEN_SELFTEST_CREATE"], True)
    os.environ["KAIZEN_VAULT"] = str(root)
    return root


def arm(app, win, shot):
    """Run the checks a little after the window opened, save the window to `shot`, then quit."""
    QTimer.singleShot(2500, lambda: _run(app, win, shot))


def _run(app, win, shot):
    if os.environ.get("KAIZEN_SELFTEST_SAVE") and os.environ.get("KAIZEN_VAULT"):
        def failed(*args, **_kw):
            Path(shot + ".err").write_text(str(args[1:]), encoding="utf-8")
        QMessageBox.warning = staticmethod(failed)
        win.generator.name.setText("Selftest Palette")
        win.generator.save()
    car_dir = os.environ.get("KAIZEN_SELFTEST_CAR")
    if car_dir and os.environ.get("KAIZEN_VAULT"):
        car = win.vault.cars().add_car("Selftest Car", find_views(Path(car_dir)), clean=False)
        zones = dict(car.zones("side"))
        car.flip_view("side")
        car.flip_view("side")
        Path(shot + ".txt").write_text(
            f"scan found {len(scan_folder(Path(car_dir).parent))} cars; "
            f"flip twice restores zones: {car.zones('side') == zones}", encoding="utf-8")
        win.cars.reload(select=car.id)
        win.cars_changed()
        win.car_box.setCurrentIndex(win.car_box.findText("Selftest Car"))
        win.projects.select_project(1)
        win.projects.tabs.setCurrentIndex(win.projects.tabs.indexOf(win.projects.on_car))
    app.processEvents()
    win.grab().save(shot)
    app.quit()
