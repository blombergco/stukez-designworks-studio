"""StukeZ Designworks Studio main window and entry point."""
import os
import sys

from PySide6.QtCore import QRectF, QSettings, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QIcon, QKeySequence, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import (QApplication, QButtonGroup, QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QMainWindow,
                               QMessageBox, QStackedWidget, QVBoxLayout, QWidget)

from . import __channel__, __version_label__, __version__, carrender, render
from .backend import Vault, find_vault, looks_like_vault
from .cars import builtin_car
from .page_cars import CarsPage
from .page_generator import GeneratorPage
from .page_guides import GuidesPage
from .page_projects import ProjectsPage
from .page_prompts import PromptsPage
from .page_sponsors import SponsorsPage
from .page_workshop import WorkshopPage
from . import backup
from .rail import LOGO_H, NavButton, Rail
from .widgets import button
from .update_ui import UpdateController
from .welcome import LicencesDialog, WelcomeDialog
from . import updates
from . import workspace
from .theme import build_qss

PAGES = [("Projects", "projects"), ("New project", "new"), ("Cars", "cars"), ("Prompts", "prompts"), ("Sponsors", "sponsors"), ("Guides", "guides"),
         ("Workshop", "workshop")]


def app_icon():
    pm = QPixmap(256, 256)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    g = QLinearGradient(0, 0, 256, 256)
    g.setColorAt(0, QColor("#ff2e3f"))
    g.setColorAt(1, QColor("#3a0610"))
    p.setPen(Qt.NoPen)
    p.setBrush(g)
    p.drawRoundedRect(QRectF(8, 8, 240, 240), 54, 54)
    for i, c in enumerate(("#0a0608", "#ff2e3f", "#FFFFFF")):
        p.setBrush(QColor(c))
        p.drawRoundedRect(QRectF(46 + i * 62, 70, 52, 116), 16, 16)
    p.end()
    return QIcon(pm)


class MainWindow(QMainWindow):
    def __init__(self, vault, settings):
        super().__init__()
        self.vault, self.settings = vault, settings
        self.setWindowTitle(f"StukeZ Designworks Studio{' (' + __channel__ + ')' if __channel__ else ''}  ·  {vault.root.name}")
        self.setWindowIcon(app_icon())
        self.resize(1680, 980)

        self.car_box = QComboBox()
        self._restore_car()
        self.projects = ProjectsPage(vault)
        self.generator = GeneratorPage(vault)
        self.cars = CarsPage(vault)
        self.prompts = PromptsPage(vault, self.generator.palette)
        self.sponsors = SponsorsPage(vault)
        self.guides = GuidesPage(vault, lambda: {p.title: p.id for p in vault.projects()})
        self.workshop = WorkshopPage(vault)
        pages = [self.projects, self.generator, self.cars, self.prompts, self.sponsors, self.guides, self.workshop]
        self.stack = QStackedWidget()
        for p in pages:
            self.stack.addWidget(p)
            p.status.connect(self.flash)

        side = Rail()
        sl = QVBoxLayout(side)
        sl.setContentsMargins(0, LOGO_H, 0, 14)
        sl.setSpacing(2)
        self.nav = QButtonGroup(self)
        for i, (text, icon) in enumerate(PAGES):
            b = NavButton(text, icon)
            b.setToolTip(f"{text}  (Ctrl+{i + 1})")
            self.nav.addButton(b, i)
            sl.addWidget(b)
            act = QAction(text, self)
            act.setShortcut(QKeySequence(f"Ctrl+{i + 1}"))
            act.triggered.connect(lambda _=False, i=i: self.go(i))
            self.addAction(act)
        sl.addStretch()
        self.nav.idClicked.connect(self.stack.setCurrentIndex)

        central = QWidget()
        cl = QHBoxLayout(central)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)
        cl.addWidget(side)
        cl.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        self.projects.openPrompt.connect(self.open_prompt)
        self.generator.saved.connect(self.project_saved)
        self.guides.openProject.connect(self.open_project)
        self.workshop.sendToProject.connect(self.slot_from_workshop)
        self.cars.carsChanged.connect(self.cars_changed)
        self.cars.placementChanged.connect(self._repaint_previews)
        self.car_box.currentIndexChanged.connect(self._car_picked)
        self._corner = QWidget()
        cl2 = QHBoxLayout(self._corner)
        cl2.setContentsMargins(0, 0, 10, 0)
        tag = QLabel("Preview car")
        tag.setObjectName("muted")
        cl2.addWidget(tag)
        cl2.addWidget(self.car_box)
        self.menuBar().setCornerWidget(self._corner, Qt.TopRightCorner)
        self.updater = UpdateController(self)
        self.updater.available.connect(self._update_available)
        self._update_btn = None
        self._menus()
        self.go(0)
        if (updates.can_self_update() or os.environ.get("KAIZEN_UPDATE_CHECK")) and not os.environ.get("KAIZEN_SELFTEST") \
                and self.settings.value("autoUpdate", True, type=bool):
            QTimer.singleShot(4000, lambda: self.updater.check(manual=False))
        self.flash(f"{len(vault.projects())} projects · {len(vault.prompts())} prompts · {len(vault.brands())} brands")

    def _menus(self):
        m = self.menuBar().addMenu("&File")
        for text, slot, key in (("Reload from disk", self.reload, "F5"), ("Back up to GitHub…", self.back_up, "Ctrl+B"),
                                ("Open workspace folder", lambda: os.startfile(self.vault.root), ""),
                                ("Change workspace folder…", self.change_vault, ""), ("Quit", self.close, "Ctrl+Q")):
            a = QAction(text, self)
            if key:
                a.setShortcut(QKeySequence(key))
            a.triggered.connect(slot)
            m.addAction(a)
        h = self.menuBar().addMenu("&Help")
        a = QAction("About StukeZ Designworks Studio", self)
        a.triggered.connect(lambda: QMessageBox.about(
            self, "StukeZ Designworks Studio", f"<b>StukeZ Designworks Studio {__version_label__}</b><br>Design studio for drift liveries: palettes, cars, gradients and sponsor kits.<br><br>"
            f"Workspace: {self.vault.root}<br>Your notes in this folder are the source of truth; the program writes new projects as plain notes."
            + ("<br><br>This is a beta version: it is still being tested, so tell the author about anything that looks wrong. "
               "Keep a backup of your workspace." if __channel__ else "")))
        h.addAction(a)
        upd = QAction("Check for updates…", self)
        upd.triggered.connect(lambda: self.updater.check(manual=True))
        h.addAction(upd)
        auto = QAction("Check for updates at startup", self)
        auto.setCheckable(True)
        auto.setChecked(self.settings.value("autoUpdate", True, type=bool))
        auto.toggled.connect(lambda on: self.settings.setValue("autoUpdate", on))
        h.addAction(auto)
        lic = QAction("Third-party licences…", self)
        lic.triggered.connect(lambda: LicencesDialog(self).exec())
        h.addAction(lic)

    def _update_available(self, info):
        self._update_info = info
        if self._update_btn is None:
            self._update_btn = button("", True, lambda: self.updater.offer(self._update_info))
            self._update_btn.setMinimumHeight(26)
            self.statusBar().addPermanentWidget(self._update_btn)
        self._update_btn.setText(f"Update {info['version']} is available")
        self.flash(f"Version {info['version']} is available (Help > Check for updates)")

    def slot_from_workshop(self, key, value):
        self.generator.apply_slot(key, value)
        self.go(1)
        self.flash(f"Gradient {value[0]} → {value[1]} is now in the {key.replace('_', ' ')} slot of the new project")

    def back_up(self):
        ok, text = backup.status(self.vault.root)
        if not ok:
            QMessageBox.information(self, "Back up to GitHub", text)
            return
        if QMessageBox.question(self, "Back up to GitHub", f"{text}\n\nCommit the changes and push them to GitHub now?") != QMessageBox.Yes:
            return
        self.setCursor(Qt.WaitCursor)
        self.flash("Backing up to GitHub…")
        QApplication.processEvents()
        try:
            ok, log = backup.backup(self.vault.root)
        finally:
            self.unsetCursor()
        if ok:
            self.flash("Backed up to GitHub")
            QMessageBox.information(self, "Back up to GitHub", "The backup is on GitHub.\n\n" + log[-900:])
        else:
            QMessageBox.warning(self, "Backup failed", log[-1500:])

    def go(self, i):
        self.nav.button(i).setChecked(True)
        self.stack.setCurrentIndex(i)

    def flash(self, text):
        self.statusBar().showMessage(text, 6000)

    def _restore_car(self, keep=None):
        """Fill the Preview car box from the library; keep the saved choice (or `keep`) if that car still exists."""
        want = keep if keep is not None else self.settings.value("previewCar", "")
        self.car_box.blockSignals(True)
        self.car_box.clear()
        builtin = builtin_car()
        if builtin is not None:
            self.car_box.addItem(builtin.name, builtin)
        for c in self.vault.cars().cars():
            self.car_box.addItem(c.name, c)
        # the saved car if it still exists, otherwise the first entry (the built-in car)
        i = next((n for n in range(self.car_box.count()) if getattr(self.car_box.itemData(n), "id", None) == want), 0)
        self.car_box.setCurrentIndex(i)
        self.car_box.blockSignals(False)
        render.set_preview_car(self.car_box.currentData())

    def _car_picked(self, _i):
        car = self.car_box.currentData()
        render.set_preview_car(car)
        self.settings.setValue("previewCar", car.id if car else "")
        self._repaint_previews()

    def _repaint_previews(self):
        self.projects.view.viewport().update()
        self.projects.livery.update()
        self.generator.livery.update()
        self.projects.refresh_on_car()

    def cars_changed(self):
        cur = self.car_box.currentData()
        carrender.clear_cache()
        self._restore_car(cur.id if cur else "")
        self._repaint_previews()

    def open_prompt(self, item, project):
        self.go(3)
        self.prompts.open_prompt(item, project)

    def open_project(self, pid):
        self.go(0)
        self.projects.select_project(pid)

    def project_saved(self, proj):
        self.projects.reload()
        self.prompts.reload()
        self.go(0)
        self.projects.select_project(proj.id)

    def reload(self):
        self.vault._stems = self.vault._prompts = self.vault._brands = None
        self.vault.cars().cars(reload=True)
        self.cars.reload()
        self.cars_changed()
        self.projects.reload()
        self.prompts.reload()
        self.sponsors.refresh()
        self.flash("Reloaded from disk")

    def change_vault(self):
        d = QFileDialog.getExistingDirectory(self, "Choose the workspace folder", str(self.vault.root))
        if d and looks_like_vault(d):
            self.settings.setValue("vault", d)
            QMessageBox.information(self, "Workspace changed", "Restart StukeZ Designworks Studio to use the new folder.")
        elif d:
            QMessageBox.warning(self, "Not a workspace", "That folder has no Project Library and Drift Sponsor Database with their Tools.")


def choose_vault(settings):
    """The workspace to open: the saved one, or the first-run dialog. An override from the environment is not remembered."""
    via_env = bool(os.environ.get("KAIZEN_VAULT"))
    root = None
    if os.environ.get("KAIZEN_SELFTEST_CREATE"):
        # smoke test of an installed copy, as on a computer that never ran the program: make a workspace from the
        # program's own starter files, without the dialog and without looking at saved settings
        root = workspace.create(os.environ["KAIZEN_SELFTEST_CREATE"], True)
        os.environ["KAIZEN_VAULT"] = str(root)
        via_env = True
    else:
        root = find_vault(settings.value("vault", ""))
    if root is None:
        dlg = WelcomeDialog()
        if dlg.exec() != QDialog.Accepted:
            return None
        root = dlg.root
    else:
        workspace.sync_tools(root)       # an update may bring newer tools; only a marked workspace is ever changed
    if not via_env:
        settings.setValue("vault", str(root))
    return root


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("StukeZ Designworks Studio")
    app.setStyleSheet(build_qss())
    app.setWindowIcon(app_icon())
    settings = QSettings("KaizenCave", "KaizenStudio")
    root = choose_vault(settings)
    if root is None:
        return 1
    app.setOverrideCursor(Qt.WaitCursor)
    try:
        win = MainWindow(Vault(root), settings)
    finally:
        app.restoreOverrideCursor()
    win.show()
    shot = os.environ.get("KAIZEN_SELFTEST")
    if shot:   # lets a built exe prove it works: save a screenshot of the window and quit
        def selftest():
            # saving a project is only exercised against a vault chosen explicitly with KAIZEN_VAULT
            if os.environ.get("KAIZEN_SELFTEST_SAVE") and os.environ.get("KAIZEN_VAULT"):
                QMessageBox.warning = staticmethod(lambda *a, **k: open(shot + ".err", "w").write(str(a[1:])))
                win.generator.name.setText("Selftest Palette")
                win.generator.save()
            car_dir = os.environ.get("KAIZEN_SELFTEST_CAR")
            if car_dir and os.environ.get("KAIZEN_VAULT"):   # import a car, preview with it and open the On car tab
                from pathlib import Path
                from .cars import find_views, scan_folder
                car = win.vault.cars().add_car("Selftest Car", find_views(Path(car_dir)), clean=False)
                zones = dict(car.zones("side"))
                car.flip_view("side")
                car.flip_view("side")
                open(shot + ".txt", "w").write(f"scan found {len(scan_folder(Path(car_dir).parent))} cars; "
                                               f"flip twice restores zones: {car.zones('side') == zones}")
                win.cars.reload(select=car.id)
                win.cars_changed()
                win.car_box.setCurrentIndex(win.car_box.findText("Selftest Car"))
                win.projects.select_project(1)
                win.projects.tabs.setCurrentIndex(win.projects.tabs.indexOf(win.projects.on_car))
            app.processEvents()
            win.grab().save(shot)
            app.quit()
        QTimer.singleShot(2500, selftest)
    return app.exec()
