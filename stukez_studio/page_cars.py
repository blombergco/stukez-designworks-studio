"""Cars page: the car library with a zone editor, folder import and the dialog that adds one car."""
import os
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                               QHBoxLayout, QHeaderView, QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox,
                               QProgressDialog, QSizePolicy, QSplitter, QTabBar, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from . import theme as th
from . import carrender
from .cars import VIEWS, ZONE_NAMES, default_zones, find_views, scan_folder
from .oncar import make_tile, sponsor_context
from .templates import ZONE_RGB, export_template
from .widgets import button, label

VIEW_TEXT = {"side": "Side view", "top": "Top view"}


class AddCarDialog(QDialog):
    def __init__(self, lib, parent=None):
        super().__init__(parent)
        self.lib = lib
        self.setWindowTitle("Add a car")
        self.setMinimumWidth(640)
        self.name = QLineEdit(placeholderText="e.g. S13 or ER34 Silver")
        self.platform = QLineEdit(placeholderText="optional, e.g. S13")
        self.files = {}
        form = QFormLayout()
        form.addRow("Name", self.name)
        form.addRow("Platform", self.platform)
        form.addRow("", button("Pick the folder with the captures…", slot=self._pick_folder))
        for view in VIEWS:
            row = QHBoxLayout()
            edit = QLineEdit(placeholderText=f"{view} view (PNG with transparent background)")
            row.addWidget(edit, 1)
            row.addWidget(button("Browse…", slot=lambda _=False, v=view: self._browse(v)))
            self.files[view] = edit
            form.addRow(VIEW_TEXT[view], row)
        self.front_side = QComboBox()
        self.front_side.addItem("Detect automatically", None)
        self.front_side.addItem("Front is on the left", "left")
        self.front_side.addItem("Front is on the right", "right")
        self.front_top = QComboBox()
        self.front_top.addItem("Front is at the bottom", "down")
        self.front_top.addItem("Front is at the top", "up")
        self.clean = QCheckBox("These are clean grey bases (no livery on the car)")
        form.addRow("Side view faces", self.front_side)
        form.addRow("Top view faces", self.front_top)
        form.addRow("", self.clean)
        hint = label("Clean grey bases give the best result: every panel one mid-grey in Substance Painter, glass left white. "
                     "Captures that already carry a livery work too, but only their silhouette and panel lines are used. The "
                     "originals are never changed: cropped copies go into the vault. You can flip a car later on the Cars page.",
                     "muted", wrap=True)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(hint)
        lay.addWidget(buttons)
        self.car = None

    def _pick_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Folder with the captures")
        if not d:
            return
        if not self.name.text().strip():
            self.name.setText(Path(d).name)
        for view, f in find_views(d).items():
            self.files[view].setText(str(f))

    def _browse(self, view):
        f, _ = QFileDialog.getOpenFileName(self, f"{view} view", "", "Images (*.png *.webp *.tga)")
        if f:
            self.files[view].setText(f)

    def _accept(self):
        files = {v: e.text().strip() for v, e in self.files.items() if e.text().strip()}
        bad = [v for v, f in files.items() if not Path(f).is_file()]
        if not self.name.text().strip() or not files or bad:
            QMessageBox.warning(self, "Add a car", "Give the car a name and point at existing image files." +
                                (f" Not found: {', '.join(bad)}." if bad else ""))
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.car = self.lib.add_car(self.name.text(), files, self.platform.text().strip(), self.front_side.currentData(),
                                        self.front_top.currentData(), self.clean.isChecked())
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, "Could not add the car", f"{type(e).__name__}: {e}")
            return
        QApplication.restoreOverrideCursor()
        self.accept()


class ImportFolderDialog(QDialog):
    """Pick a folder; every car found in it (side and top captures) can be ticked and imported in one go."""

    def __init__(self, lib, parent=None):
        super().__init__(parent)
        self.lib = lib
        self.imported = []
        self.setWindowTitle("Import a folder of cars")
        self.resize(900, 560)
        self.path = QLineEdit(placeholderText="Folder that contains your car captures (subfolders are searched)")
        self.path.returnPressed.connect(self.scan)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Import", "Name (editable)", "Views found", "Where"])
        self.table.verticalHeader().setVisible(False)
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.Stretch)
        self.clean = QCheckBox("These are clean grey bases (no livery on the cars)")
        self.info = label("Files are recognised by the words side and top in their names (Sideview.png, S13 top.png …). "
                          "One folder can hold many cars when every name has both a side and a top file; a folder of single-view "
                          "variants of one car counts as one car. Cars that already exist are left unticked.",
                          "muted", wrap=True)
        self.go = button("Import the ticked cars", True, self.run)
        self.go.setEnabled(False)
        top = QHBoxLayout()
        top.addWidget(self.path, 1)
        top.addWidget(button("Browse…", slot=self.browse))
        top.addWidget(button("Scan", slot=self.scan))
        sel = QHBoxLayout()
        sel.addWidget(button("Tick all", slot=lambda: self._tick(True)))
        sel.addWidget(button("Tick none", slot=lambda: self._tick(False)))
        sel.addStretch()
        sel.addWidget(self.clean)
        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(self.info)
        lay.addWidget(self.table, 1)
        lay.addLayout(sel)
        bottom = QHBoxLayout()
        bottom.addStretch()
        bottom.addWidget(button("Close", slot=self.reject))
        bottom.addWidget(self.go)
        lay.addLayout(bottom)
        self.found = []

    def browse(self):
        d = QFileDialog.getExistingDirectory(self, "Folder with car captures", self.path.text())
        if d:
            self.path.setText(d)
            self.scan()

    def scan(self):
        root = Path(self.path.text().strip())
        if not root.is_dir():
            QMessageBox.warning(self, "Import", "That folder does not exist.")
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.found = scan_folder(root)
        finally:
            QApplication.restoreOverrideCursor()
        existing = {c.name.lower() for c in self.lib.cars(reload=True)}
        self.table.setRowCount(len(self.found))
        for i, c in enumerate(self.found):
            have = self.lib.safe_name(c["name"]).lower() in existing
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk.setCheckState(Qt.Unchecked if have else Qt.Checked)
            name = QTableWidgetItem(c["name"])
            views = QTableWidgetItem("   ".join(f"{VIEW_TEXT[v].split()[0]} ✓" for v in VIEWS if v in c["views"]) + ("   (already in the library)" if have else ""))
            views.setFlags(Qt.ItemIsEnabled)
            where = QTableWidgetItem(str(c["folder"]))
            where.setFlags(Qt.ItemIsEnabled)
            for col, it in enumerate((chk, name, views, where)):
                self.table.setItem(i, col, it)
        self.go.setEnabled(bool(self.found))
        self.info.setText(f"{len(self.found)} cars found." if self.found else
                          "No cars found: the file names need the words side or top (Sideview.png, S13 top.png …).")

    def _tick(self, on):
        for i in range(self.table.rowCount()):
            self.table.item(i, 0).setCheckState(Qt.Checked if on else Qt.Unchecked)

    def run(self):
        todo = [(i, self.found[i]) for i in range(self.table.rowCount()) if self.table.item(i, 0).checkState() == Qt.Checked]
        if not todo:
            return
        dlg = QProgressDialog("Importing…", "Stop", 0, len(todo), self)
        dlg.setWindowTitle("Importing cars")
        dlg.setWindowModality(Qt.WindowModal)
        dlg.setMinimumDuration(0)
        errors = []
        for n, (row, c) in enumerate(todo):
            if dlg.wasCanceled():
                break
            name = self.table.item(row, 1).text().strip() or c["name"]
            dlg.setLabelText(f"{name}  ({n + 1} of {len(todo)})")
            dlg.setValue(n)
            QApplication.processEvents()
            try:
                self.imported.append(self.lib.add_car(name, c["views"], clean=self.clean.isChecked(), index=False))
            except Exception as e:
                errors.append(f"{name}: {e}")
        dlg.setValue(len(todo))
        self.lib.rebuild_index()
        if errors:
            QMessageBox.warning(self, "Some cars were skipped", "\n".join(errors[:12]))
        self.accept()


class ZoneEditor(QWidget):
    """One view of a car with its sponsor zones; drag a zone to move it, drag its dot to resize, right-click to add/delete."""
    changed = Signal()

    def __init__(self, vault):
        super().__init__()
        self.vault = vault
        self.car, self.view, self.pal, self.show_sponsors = None, "side", None, True
        self.sel, self.drag = None, None
        self._ctx, self._ctx_id, self._tiles = None, None, {}
        self.setMinimumHeight(320)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_view(self, car, view, pal=None):
        self.car, self.view, self.pal = car, view, pal
        self.sel = None
        self.update()

    def _image_rect(self):
        info = self.car.view_info(self.view)
        ar = info["size"][0] / info["size"][1]
        w, h = min(self.width() - 20, (self.height() - 20) * ar), min(self.height() - 20, (self.width() - 20) / ar)
        return QRectF((self.width() - w) / 2, (self.height() - h) / 2, w, h)

    @staticmethod
    def _zone_rect(box, ir):
        return QRectF(ir.x() + box[0] * ir.width(), ir.y() + box[1] * ir.height(), box[2] * ir.width(), box[3] * ir.height())

    def _sponsor_tiles(self, p, ir):
        """The sponsor logos of the chosen project drawn into the zones, so a placement can be judged as it will look."""
        if self.pal is None or not self.show_sponsors:
            return
        if self._ctx is None or self._ctx_id != self.pal.id:
            self._ctx, self._ctx_id, self._tiles = sponsor_context(self.vault, self.pal), self.pal.id, {}
        kit = self._ctx[3]
        for z, box in self.car.zones(self.view).items():
            e = kit.get(int(z))
            if not e:
                continue
            r = self._zone_rect(box, ir)
            key = (z, round(r.width()), round(r.height()))
            if key not in self._tiles:
                self._tiles[key] = make_tile(self._ctx, e, r.width(), r.height())
            t = self._tiles[key]
            if t:
                qi, ss, _real = t
                tw, th = qi.width() / ss, qi.height() / ss
                p.drawImage(QRectF(r.center().x() - tw / 2, r.center().y() - th / 2, tw, th), qi)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(th.PANEL))
        if self.car is None or self.view not in self.car.views():
            p.setPen(QColor(th.MUTED))
            p.drawText(self.rect(), Qt.AlignCenter, "This car has no capture of this view")
            return
        ir = self._image_rect()
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        if self.pal is not None:
            img = carrender.render(self.car, self.view, self.pal, int(ir.width() * self.devicePixelRatioF()), plates={})
        else:
            img = QImage(str(self.car.view_path(self.view)))
        p.drawImage(ir, img)
        self._sponsor_tiles(p, ir)
        p.setFont(th.body_font(12, bold=True))
        for z, box in self.car.zones(self.view).items():
            r = self._zone_rect(box, ir)
            rgb = QColor(*ZONE_RGB[int(z) % len(ZONE_RGB)])
            fill = QColor(rgb)
            fill.setAlpha(80 if z == self.sel else (0 if self.pal is not None and self.show_sponsors else 40))
            p.setBrush(fill)
            p.setPen(QPen(rgb, 3 if z == self.sel else 2))
            p.drawRoundedRect(r, 5, 5)
            text = f"{z}" if r.width() < 70 else f"{z} {ZONE_NAMES.get(int(z), '')}"
            tr = r.adjusted(3, 2, -2, -2)
            text = p.fontMetrics().elidedText(text, Qt.ElideRight, max(0, int(tr.width())))   # never past the zone's box
            p.setPen(QColor(0, 0, 0, 170))
            p.drawText(tr.translated(1, 1), Qt.AlignLeft | Qt.AlignTop, text)
            p.setPen(QColor("#ffffff"))
            p.drawText(tr, Qt.AlignLeft | Qt.AlignTop, text)
            if z == self.sel:
                p.setBrush(rgb)
                p.setPen(Qt.NoPen)
                p.drawEllipse(QPointF(r.right(), r.bottom()), 6, 6)

    def _hit(self, pos):
        ir = self._image_rect()
        for z, box in reversed(list(self.car.zones(self.view).items())):
            r = self._zone_rect(box, ir)
            if z == self.sel and (QPointF(r.right(), r.bottom()) - pos).manhattanLength() <= 16:
                return z, "resize"
            if r.contains(pos):
                return z, "move"
        return None, None

    def mousePressEvent(self, e):
        if self.car is None or self.view not in self.car.views():
            return
        z, mode = self._hit(e.position())
        if e.button() == Qt.RightButton:
            self._menu(e, z)
            return
        self.sel = z
        if z:
            self.drag = (z, mode, e.position(), list(self.car.zones(self.view)[z]), self._image_rect())
        self.update()

    def mouseMoveEvent(self, e):
        if self.car is None or self.view not in self.car.views():
            return
        if not self.drag:
            _z, mode = self._hit(e.position())
            self.setCursor(Qt.SizeFDiagCursor if mode == "resize" else Qt.SizeAllCursor if mode else Qt.ArrowCursor)
            return
        z, mode, start, box, ir = self.drag
        dx, dy = (e.position().x() - start.x()) / ir.width(), (e.position().y() - start.y()) / ir.height()
        x, y, w, h = box
        if mode == "move":
            x, y = min(max(0.0, x + dx), 1 - w), min(max(0.0, y + dy), 1 - h)
        else:
            w, h = min(max(0.01, w + dx), 1 - x), min(max(0.01, h + dy), 1 - y)
        zones = dict(self.car.zones(self.view))
        zones[z] = [x, y, w, h]
        self.car.set_zones(self.view, zones)
        self.update()

    def mouseReleaseEvent(self, _e):
        if self.drag:
            self.drag = None
            self._save()

    def _save(self):
        self.car.save()
        self.changed.emit()
        self.update()

    def _menu(self, e, z):
        m = QMenu(self)
        if z:
            m.addAction(f"Delete zone {z}", lambda: self.delete_zone(z))
        missing = [k for k in ZONE_NAMES if str(k) not in self.car.zones(self.view)]
        if missing:
            add = m.addMenu("Add zone")
            for k in missing:
                add.addAction(f"{k} {ZONE_NAMES[k]}", lambda k=k: self.add_zone(k))
        m.exec(e.globalPosition().toPoint())

    def delete_zone(self, z):
        zones = dict(self.car.zones(self.view))
        zones.pop(z, None)
        self.car.set_zones(self.view, zones)
        self.sel = None
        self._save()

    def add_zone(self, k):
        zones = dict(self.car.zones(self.view))
        zones[str(k)] = [0.4, 0.4, 0.2, 0.1]
        self.car.set_zones(self.view, zones)
        self.sel = str(k)
        self._save()

    def reset(self):
        self.car.set_zones(self.view, default_zones(self.view, self.car.front_side, self.car.front_top))
        self._save()


class CarsPage(QWidget):
    status = Signal(str)
    carsChanged = Signal()        # cars added, removed, flipped or their settings changed
    placementChanged = Signal()   # only the sponsor zones moved

    def __init__(self, vault):
        super().__init__()
        self.setObjectName("page")
        self.vault = vault
        self.lib = vault.cars()
        self.car = None

        self.list = QListWidget()
        self.list.currentItemChanged.connect(lambda cur, _p: self._select(cur.data(Qt.UserRole) if cur else None))
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(label("Cars", "h1"))
        ll.addWidget(button("Add a car…", True, self.add_car))
        ll.addWidget(button("Import a folder of cars…", slot=self.import_folder))
        ll.addWidget(self.list, 1)
        ll.addWidget(button("Remove selected car", slot=self.remove_car))
        left.setMaximumWidth(320)

        self.title = label("Add a car to get started", "h1")
        self.info = label("", "muted", wrap=True)
        self.platform = QLineEdit(placeholderText="Platform")
        self.front_side = QComboBox()
        self.front_side.addItem("Side view faces left", "left")
        self.front_side.addItem("Side view faces right", "right")
        self.front_top = QComboBox()
        self.front_top.addItem("Top view: front at the bottom", "down")
        self.front_top.addItem("Top view: front at the top", "up")
        self.clean = QCheckBox("Clean grey base")
        self.glass = QCheckBox("White areas are windows")
        self.glass.setToolTip("On a clean base, white areas (windows, arch interiors) are drawn dark. Turn off for a white car.")
        meta = QHBoxLayout()
        for w in (self.platform, self.front_side, self.front_top, self.clean, self.glass):
            meta.addWidget(w)
        meta.addStretch()
        for sig in (self.platform.editingFinished, self.front_side.activated, self.front_top.activated, self.clean.clicked,
                    self.glass.clicked):
            sig.connect(self._save_meta)

        self.tabs = QTabBar()
        for v in VIEWS:
            self.tabs.addTab(VIEW_TEXT[v])
        self.tabs.currentChanged.connect(self._view_changed)
        self.editor = ZoneEditor(vault)
        self.editor.changed.connect(self._zones_changed)

        self.palette_box = QComboBox()
        self.palette_box.setEditable(True)
        self.palette_box.setInsertPolicy(QComboBox.NoInsert)
        self.palette_box.completer().setFilterMode(Qt.MatchContains)
        self.palette_box.addItem("Show the capture as it is", None)
        for p in vault.projects():
            self.palette_box.addItem(f"Paint it as {p.title}", p)
        self.palette_box.currentIndexChanged.connect(self._view_changed)
        self.sponsors_check = QCheckBox("Show the sponsors")
        self.sponsors_check.setChecked(True)
        self.sponsors_check.toggled.connect(self._sponsors_toggled)
        row1 = QHBoxLayout()
        row1.addWidget(self.palette_box, 1)
        row1.addWidget(self.sponsors_check)
        self.flip_btn = button("Flip the car", slot=self.flip)
        self.copy_box = QComboBox()
        self.copy_box.setMinimumWidth(200)
        self.copy_box.activated.connect(self.copy_from)
        row2 = QHBoxLayout()
        row2.addWidget(self.flip_btn)
        row2.addWidget(self.copy_box)
        row2.addWidget(button("Reset zones", slot=self.editor.reset))
        row2.addStretch()
        row2.addWidget(button("Export Illustrator template…", True, self.export))
        self.saved = label("", "muted", wrap=True)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(8, 0, 0, 0)
        rl.addWidget(self.title)
        rl.addWidget(self.info)
        rl.addLayout(meta)
        rl.addWidget(self.tabs)
        rl.addWidget(self.editor, 1)
        rl.addLayout(row1)
        rl.addLayout(row2)
        rl.addWidget(self.saved)
        split = QSplitter()
        split.addWidget(left)
        split.addWidget(right)
        split.setStretchFactor(1, 1)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 10)
        lay.addWidget(split)
        self.reload()

    # ------------------------------------------------------------------ data
    def reload(self, select=None):
        keep = select or (self.car.id if self.car else None)
        self.list.blockSignals(True)
        self.list.clear()
        for c in self.lib.cars():
            it = QListWidgetItem()
            it.setData(Qt.UserRole, c)
            self._label(it, c)
            self.list.addItem(it)
        self.list.blockSignals(False)
        row = next((i for i in range(self.list.count()) if self.list.item(i).data(Qt.UserRole).id == keep), 0)
        if self.list.count():
            self.list.setCurrentRow(row)
        else:
            self._select(None)

    @staticmethod
    def _label(item, c):
        item.setText(c.name + (f"   ·   {c.platform}" if c.platform and c.platform != c.name else "") +
                     ("      ✓ placed" if c.placed() else ""))

    def _select(self, car):
        self.car = car
        for w in (self.platform, self.front_side, self.front_top, self.clean, self.glass, self.tabs, self.editor,
                  self.palette_box, self.sponsors_check, self.flip_btn, self.copy_box):
            w.setEnabled(car is not None and bool(car.views()))
        if car is None or not car.views():
            self.title.setText(car.name if car else "Add a car to get started")
            self.info.setText("Use “Add a car…” or “Import a folder of cars…” and point at the Side and Top captures from "
                              "Substance Painter." if car is None else "This car has no side or top capture.")
            self.editor.set_view(None, "side")
            self.saved.setText("")
            return
        self.title.setText(car.name)
        self.info.setText(f"{len(car.views())} views · stored in Project Library/Car Templates/{car.name}")
        self.platform.setText(car.platform)
        self.front_side.setCurrentIndex(self.front_side.findData(car.front_side))
        self.front_top.setCurrentIndex(self.front_top.findData(car.front_top))
        self.clean.setChecked(car.clean)
        self.glass.setChecked(car.glass)
        for i, v in enumerate(VIEWS):
            self.tabs.setTabEnabled(i, v in car.views())
        if VIEWS[max(0, self.tabs.currentIndex())] not in car.views():
            self.tabs.setCurrentIndex(VIEWS.index(car.views()[0]))
        self.copy_box.blockSignals(True)
        self.copy_box.clear()
        self.copy_box.addItem("Copy the placement from another car…", None)
        for c in self.lib.cars():
            if c.id != car.id and c.views():
                self.copy_box.addItem(c.name, c)
        self.copy_box.blockSignals(False)
        self._view_changed()

    def _view_changed(self, *_):
        if self.car is None or not self.car.views():
            return
        view = VIEWS[max(0, self.tabs.currentIndex())]
        self.editor.set_view(self.car, view, self.palette_box.currentData())
        self.flip_btn.setText("Flip the car (mirror left ↔ right)" if view == "side" else "Turn the car 180°")
        self.saved.setText("The placement is saved automatically for this car and view. Pick a project above to see its sponsors "
                           "in the zones while you place them.")

    def _sponsors_toggled(self, on):
        self.editor.show_sponsors = on
        self.editor.update()

    def _zones_changed(self):
        it = self.list.currentItem()
        if it:
            self._label(it, self.car)
        self.saved.setText(f"✓ Placement saved for {self.car.name}, {VIEW_TEXT[self.editor.view].lower()}.")
        self.status.emit(f"Placement saved for {self.car.name}")
        self.placementChanged.emit()

    def _save_meta(self, *_):
        c = self.car
        if c is None:
            return
        c.data.update(platform=self.platform.text().strip(), front_side=self.front_side.currentData(),
                      front_top=self.front_top.currentData(), clean=self.clean.isChecked(), glass=self.glass.isChecked())
        c.save()
        self.lib.rebuild_index()
        carrender.clear_cache()
        self.editor.update()
        self.carsChanged.emit()
        self.status.emit(f"Saved {c.name}")

    # ------------------------------------------------------------------ actions
    def add_car(self):
        dlg = AddCarDialog(self.lib, self)
        if dlg.exec() and dlg.car:
            self.reload(select=dlg.car.id)
            self.carsChanged.emit()
            self.status.emit(f"Added {dlg.car.name} ({len(dlg.car.views())} views)")

    def import_folder(self):
        dlg = ImportFolderDialog(self.lib, self)
        dlg.exec()
        if dlg.imported:
            self.reload(select=dlg.imported[0].id)
            self.carsChanged.emit()
            self.status.emit(f"Imported {len(dlg.imported)} cars")

    def remove_car(self):
        c = self.car
        if c and QMessageBox.question(self, "Remove car", f"Remove {c.name} from the library? The original captures are not touched.") \
                == QMessageBox.Yes:
            self.lib.remove_car(c)
            self.car = None
            self.reload()
            self.carsChanged.emit()

    def flip(self):
        c, view = self.car, VIEWS[self.tabs.currentIndex()]
        if not c or view not in c.views():
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            c.flip_view(view)
            carrender.clear_cache()
        finally:
            QApplication.restoreOverrideCursor()
        self.lib.rebuild_index()
        self._select(c)
        self.carsChanged.emit()
        self.status.emit(f"{c.name}: the {view} view now faces the other way (zones followed)")

    def copy_from(self, _i):
        other, c = self.copy_box.currentData(), self.car
        view = VIEWS[self.tabs.currentIndex()]
        if other is None or c is None or view not in other.views():
            self.copy_box.setCurrentIndex(0)
            return
        c.copy_zones_from(other, view)
        self.copy_box.setCurrentIndex(0)
        self.editor.update()
        self._zones_changed()
        self.status.emit(f"Copied the {view} placement from {other.name} to {c.name}")

    def export(self):
        c = self.car
        if not c:
            return
        d = QFileDialog.getExistingDirectory(self, "Save the Illustrator template in…")
        if not d:
            return
        view = VIEWS[self.tabs.currentIndex()]
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            files = export_template(c, view, d, self.palette_box.currentData())
        finally:
            QApplication.restoreOverrideCursor()
        self.status.emit(f"Saved {len(files)} files for the {view} view in {d}")
        os.startfile(d)
