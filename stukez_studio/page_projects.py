"""Projects page: card grid with filters on the left, details and exports on the right."""
import os
import shutil
import tempfile

from PySide6.QtCore import (QAbstractListModel, QModelIndex, QRectF, QSize, QSortFilterProxyModel, Qt, Signal)
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
                               QListView, QListWidget, QListWidgetItem, QMenu, QMessageBox, QScrollArea,
                               QSplitter, QStyle, QStyledItemDelegate, QTabWidget, QVBoxLayout, QWidget)

from . import export, render
from .backend import write_ase
from .compare import CompareDialog
from .oncar import render_placement
from .templates import export_template
from .widgets import ChipGrid, LiveryPreview, NoteView, PaintSwitch, StudioButton, button, copy_text, label, pill, run_build


class OnCarTab(QWidget):
    """The project's palette and sponsor kit placed on the chosen preview car (rendered when the tab is opened)."""
    status = Signal(str)

    def __init__(self, vault):
        super().__init__()
        self.vault, self.proj, self.image, self.key, self.note = vault, None, None, None, ""
        self.msg = label("", "muted", wrap=True)
        self.pic = QLabel()
        self.pic.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.scroll = QScrollArea()
        self.scroll.setWidget(self.pic)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.save_btn = button("Save this image (PNG)", slot=self.save)
        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(self.msg, 1)
        top.addWidget(self.save_btn)
        lay.addLayout(top)
        lay.addWidget(self.scroll, 1)

    def set_project(self, p):
        self.proj, self.key, self.image = p, None, None

    def refresh(self):
        car, p = render.PREVIEW_CAR, self.proj
        self.save_btn.setEnabled(False)
        if p is None:
            return
        if car is None:
            self.msg.setText("Choose a car in “Preview car” (top right) to see the placement on it. Add your cars on the Cars page.")
            self.pic.clear()
            return
        sheet = p.folder / f"{p.title} - Build sheet.md"
        if not sheet.exists():
            self.msg.setText("This project has no Build sheet yet, so there is no sponsor kit to place. Use “Build missing parts” first.")
            self.pic.clear()
            return
        key = (p.id, car.id, repr(car.data.get("zones")), sheet.stat().st_mtime_ns, car.clean)
        if key != self.key:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                self.image, stats = render_placement(self.vault, p, car)
                self.key = key
                self.note = f"{stats['real']} logo masters, {stats['text']} text stand-ins"
            except Exception as e:
                self.msg.setText(f"Could not render the placement: {type(e).__name__}: {e}")
                self.image = None
                return
            finally:
                QApplication.restoreOverrideCursor()
        self.msg.setText(f"{p.title} on {car.name}: {self.note}. Move the zones on the Cars page.")
        self.save_btn.setEnabled(True)
        self._show()

    def _show(self):
        if self.image is not None:
            self.pic.setPixmap(QPixmap.fromImage(self.image).scaledToWidth(max(400, self.scroll.viewport().width() - 6),
                                                                           Qt.SmoothTransformation))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._show()

    def save(self):
        if self.image is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save placement image", f"{self.proj.title} - on {render.PREVIEW_CAR.name}.png",
                                              "PNG image (*.png)")
        if path:
            self.image.save(path)
            self.status.emit(f"Saved {os.path.basename(path)}")


class ProjectModel(QAbstractListModel):
    def __init__(self, projects):
        super().__init__()
        self.items = projects

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.items)

    def data(self, index, role=Qt.DisplayRole):
        if role in (Qt.UserRole, Qt.DisplayRole):
            return self.items[index.row()]

    def reset(self, projects):
        self.beginResetModel()
        self.items = projects
        self.endResetModel()


class ProjectFilter(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self.text, self.mood, self.platform = "", "", ""
        self.sort_by = "id"

    def filterAcceptsRow(self, row, _parent):
        p = self.sourceModel().items[row]
        if self.mood and self.mood not in p.moods:
            return False
        if self.platform == "(none)" and p.platform:
            return False
        if self.platform and self.platform != "(none)" and p.platform != self.platform:
            return False
        t = self.text.lower()
        hay = f"{p.title} {' '.join(p.moods)} {p.platform} {p.concept} {' '.join(p.vocab.values())}".lower()
        return all(w in hay for w in t.split())

    def lessThan(self, a, b):
        pa, pb = self.sourceModel().items[a.row()], self.sourceModel().items[b.row()]
        if self.sort_by == "name":
            return pa.name.lower() < pb.name.lower()
        return pa.id < pb.id


class CardDelegate(QStyledItemDelegate):
    SIZE = QSize(308, 236)

    def sizeHint(self, option, index):
        return self.SIZE

    def paint(self, painter, option, index):
        p = index.data(Qt.UserRole)
        rect = QRectF(option.rect).adjusted(6, 6, -6, -6)
        sub = (", ".join(p.moods[:3]) or "no moods") + (f"  ·  {p.platform}" if p.platform else "")
        render.draw_card(painter, rect, p, p.name, sub, selected=bool(option.state & QStyle.State_Selected), number=f"{p.id:03d}", plates=False,
                         hover=bool(option.state & QStyle.State_MouseOver))


class ProjectsPage(QWidget):
    openPrompt = Signal(object, object)   # prompt item, project
    status = Signal(str)

    def __init__(self, vault):
        super().__init__()
        self.setObjectName("page")
        self.vault = vault
        self.current = None

        # --- left: filters + grid
        self.search = QLineEdit(placeholderText="Search name, mood, colour scheme, platform…")
        self.mood = QComboBox()
        self.platform = QComboBox()
        self.sort = QComboBox()
        self.sort.addItems(["Sort: ID", "Sort: Name"])
        self.count = label("", "muted")
        self.model = ProjectModel(vault.projects())
        self.proxy = ProjectFilter()
        self.proxy.setSourceModel(self.model)
        self.proxy.sort(0)
        self.view = QListView()
        self.view.setModel(self.proxy)
        self.view.setItemDelegate(CardDelegate())
        self.view.setViewMode(QListView.IconMode)
        self.view.setResizeMode(QListView.Adjust)
        self.view.setMovement(QListView.Static)
        self.view.setUniformItemSizes(True)
        self.view.setMouseTracking(True)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.view.setFrameShape(QListView.NoFrame)
        self.view.setStyleSheet("QListView { background: transparent; border: none; }")
        self.view.selectionModel().currentChanged.connect(lambda cur, _p: self._select(cur))
        filters = QHBoxLayout()
        for w, stretch in ((self.search, 1), (self.mood, 0), (self.platform, 0), (self.sort, 0)):
            filters.addWidget(w, stretch)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(label("Projects", "h1"))
        ll.addLayout(filters)
        ll.addWidget(self.count)
        ll.addWidget(self.view, 1)

        # --- right: detail
        self.title = label("", "h1")
        self.badges = QHBoxLayout()
        self.concept = label("", "muted", wrap=True)
        self.livery = LiveryPreview(210, plates=False)
        self.paint = PaintSwitch()
        self.chips = ChipGrid()
        self.chips.copied.connect(lambda n: self.status.emit(f"Copied {n}"))
        actions = QHBoxLayout()
        for text, slot, primary in (("Export palette card (PNG)", self.export_card, True), ("Export .ase swatches", self.export_ase, False),
                                    ("Copy all hex", self.copy_hex, False), ("Open note", self.open_note, False),
                                    ("Show folder", self.show_folder, False), ("Export package (ZIP)", self.export_package, False),
                                    ("Compare…", self.compare, False)):
            actions.addWidget(button(text, primary, slot))
        self.build_btn = button("Build missing parts", slot=self.build_missing)
        self.build_btn.setToolTip("Creates the Detail kit, Build sheet with sponsor kit and Placement preview this project lacks")
        actions.addWidget(self.build_btn)
        tpl = StudioButton("Illustrator template ▾")
        tpl.setToolTip("Capture of the preview car on its original canvas, zone guides and an SVG with layers, in this project's colours")
        menu = QMenu(tpl)
        menu.aboutToShow.connect(lambda m=menu: self._fill_template_menu(m))
        tpl.setMenu(menu)
        actions.addWidget(tpl)
        actions.addStretch()
        self.tabs = QTabWidget()
        self.views = {}
        for name in ("Overview", "Build sheet", "Detail kit", "Patterns"):
            v = NoteView(vault)
            v.noteRequested.connect(self._follow)
            self.views[name] = v
            self.tabs.addTab(v, name)
        self.prompt_list = QListWidget()
        self.prompt_list.itemDoubleClicked.connect(self._prompt_open)
        self.tabs.addTab(self.prompt_list, "Prompts with this palette")
        self.on_car = OnCarTab(vault)
        self.on_car.status.connect(self.status)
        self.tabs.addTab(self.on_car, "On car")
        self.tabs.currentChanged.connect(lambda _i: self.refresh_on_car())
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(8, 0, 0, 0)
        rl.setSpacing(10)
        rl.addWidget(self.title)
        hb = QWidget()
        hb.setLayout(self.badges)
        self.badges.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(hb)
        rl.addWidget(self.concept)
        rl.addWidget(self.paint)
        rl.addWidget(self.livery)
        rl.addWidget(self.chips)
        rl.addLayout(actions)
        rl.addWidget(self.tabs, 1)

        split = QSplitter()
        split.addWidget(left)
        split.addWidget(right)
        split.setStretchFactor(0, 5)
        split.setStretchFactor(1, 6)
        split.setSizes([760, 760])
        lay = QHBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 10)
        lay.addWidget(split)

        self.search.textChanged.connect(self._refilter)
        self.mood.currentIndexChanged.connect(self._refilter)
        self.platform.currentIndexChanged.connect(self._refilter)
        self.sort.currentIndexChanged.connect(self._refilter)
        self.refill_filters()
        self._refilter()
        if self.proxy.rowCount():
            self.view.setCurrentIndex(self.proxy.index(0, 0))

    # ------------------------------------------------------------------ data
    def reload(self):
        self.model.reset(self.vault.projects(reload=True))
        self.refill_filters()
        self._refilter()

    def refill_filters(self):
        ps = self.model.items
        for combo, first, values in ((self.mood, "All moods", sorted({m for p in ps for m in p.moods})),
                                     (self.platform, "All platforms", ["(none)"] + sorted({p.platform for p in ps if p.platform}))):
            keep = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(first, "")
            for v in values:
                combo.addItem(v, v)
            i = combo.findText(keep)
            combo.setCurrentIndex(max(0, i))
            combo.blockSignals(False)

    def _refilter(self):
        f = self.proxy
        f.text, f.mood, f.platform = self.search.text(), self.mood.currentData() or "", self.platform.currentData() or ""
        f.sort_by = "name" if self.sort.currentIndex() == 1 else "id"
        f.invalidate()
        f.sort(0)
        self.count.setText(f"{f.rowCount()} of {len(self.model.items)} projects")

    def select_project(self, pid):
        self.search.clear()
        self.mood.setCurrentIndex(0)
        self.platform.setCurrentIndex(0)
        self._refilter()
        for r in range(self.proxy.rowCount()):
            idx = self.proxy.index(r, 0)
            if idx.data(Qt.UserRole).id == pid:
                self.view.setCurrentIndex(idx)
                self.view.scrollTo(idx, QAbstractItemView.PositionAtCenter)
                return

    # ------------------------------------------------------------------ detail
    def _select(self, idx):
        if not idx.isValid():
            return
        p = idx.data(Qt.UserRole)
        self.current = p
        self.title.setText(p.title)
        while self.badges.count():
            w = self.badges.takeAt(0).widget()
            if w:
                w.hide()
                w.deleteLater()
        for text in ([f"week {p.week}"] if p.week else []) + [p.status] + ([p.platform] if p.platform else []) \
                + [f"{k.lower()}: {p.vocab[k]}" for k in ("Colour scheme", "Suggested finish") if k in p.vocab] + p.moods:
            self.badges.addWidget(pill(text))
        self.badges.addStretch()
        self.concept.setText(p.concept)
        self.livery.set_palette(p)
        self.chips.set_palette(p)
        files = self.vault.project_files(p)
        missing = self.vault.missing_parts(p)
        self.build_btn.setVisible(bool(missing))
        self.build_btn.setText(f"Build missing parts ({len(missing)})")
        self.views["Overview"].history.clear()
        self.views["Overview"].show_note(p.note)
        for name in ("Build sheet", "Detail kit", "Patterns"):
            self.views[name].history.clear()
            self.views[name].show_note(files[name])
        self.prompt_list.clear()
        for it in self.vault.prompts_for_project(p):
            li = QListWidgetItem(f"{it['title']}    ·    {it['category']}")
            li.setData(Qt.UserRole, it)
            self.prompt_list.addItem(li)
        self.tabs.setTabText(4, f"Prompts with this palette ({self.prompt_list.count()})")
        self.on_car.set_project(p)
        self.refresh_on_car()

    def refresh_on_car(self):
        """Render the On car tab if it is the visible one (it takes a moment, so never in the background)."""
        if self.tabs.currentWidget() is self.on_car:
            self.on_car.refresh()
        else:
            self.on_car.key = None

    def _follow(self, name):
        path = self.vault.resolve(name)
        stems = {p.title: p for p in self.model.items}
        if name in stems:
            self.select_project(stems[name].id)
        elif path:
            self.sender().show_note(path)

    def _prompt_open(self, li):
        self.openPrompt.emit(li.data(Qt.UserRole), self.current)

    # ------------------------------------------------------------------ actions
    def compare(self):
        """Two projects on the preview car, one above the other."""
        projects = self.vault.projects()
        if len(projects) < 2:
            QMessageBox.information(self, "Compare", "You need at least two projects to compare.")
            return
        CompareDialog(projects, self.current.id if self.current else None, self).exec()

    def export_card(self):
        p = self.current
        if not p:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save palette card", f"{p.title} - Palette card.png", "PNG image (*.png)")
        if path:
            render.render_card_image(p, p.title, "", p.concept, plates=False).save(path)
            self.status.emit(f"Saved {os.path.basename(path)}")

    def export_package(self):
        p = self.current
        if not p:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save the project package", f"{p.title}.zip", "ZIP archive (*.zip)")
        if not path:
            return
        with tempfile.TemporaryDirectory() as tmp:
            card = os.path.join(tmp, f"{p.title} - Palette card.png")
            render.render_card_image(p, p.title, "", p.concept, plates=False).save(card)
            n = export.write_zip(self.vault, p, path, extra=[(card, f"{p.title}/{p.title} - Palette card.png")])
        self.status.emit(f"Saved {os.path.basename(path)} with {n} files")

    def export_ase(self):
        p = self.current
        if not p:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save swatches", f"{p.title}.ase", "Adobe Swatch Exchange (*.ase)")
        if path:
            src = self.vault.project_files(p)["ase"]
            shutil.copyfile(src, path) if src else write_ase(p, path)
            self.status.emit(f"Saved {os.path.basename(path)}")

    def copy_hex(self):
        p = self.current
        if p:
            copy_text("\n".join(f"{lbl}: " + " → ".join(v if isinstance(v, list) else [v]) for lbl, v, _ in p.slots()))
            self.status.emit("Copied all hex codes")

    def build_missing(self):
        p = self.current
        if not p:
            return
        res = run_build(self, self.vault, p.id)
        if res:
            self.reload()
            self.select_project(p.id)
            self.status.emit(f"Built {', '.join(res['built']).lower()} for {p.title}" + (f". {res['notes'][0]}" if res["notes"] else ""))

    def _fill_template_menu(self, menu):
        """Only the views the preview car has, and all of them when it has more than one."""
        menu.clear()
        car = render.PREVIEW_CAR
        views = car.views() if car is not None else []
        for view in views:
            menu.addAction(f"{view.capitalize()} view", lambda v=view: self.export_template_for(v))
        if len(views) > 1:
            menu.addAction("All views", lambda: self.export_template_for("all"))
        if not views:
            menu.addAction("Choose a preview car first").setEnabled(False)

    def export_template_for(self, view):
        car, p = render.PREVIEW_CAR, self.current
        if not p:
            return
        if car is None:
            QMessageBox.information(self, "Illustrator template", "Choose a car in “Preview car” (top right) first. "
                                    "Add your cars on the Cars page.")
            return
        d = QFileDialog.getExistingDirectory(self, "Save the Illustrator template in…")
        if not d:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            files = []
            for v in (car.views() if view == "all" else [view]):
                if v in car.views():
                    files += export_template(car, v, d, p)
        finally:
            QApplication.restoreOverrideCursor()
        self.status.emit(f"Saved {len(files)} template files for {p.title} on {car.name}")
        os.startfile(d)

    def open_note(self):
        if self.current:
            os.startfile(self.current.note)

    def show_folder(self):
        if self.current:
            os.startfile(self.current.folder)
