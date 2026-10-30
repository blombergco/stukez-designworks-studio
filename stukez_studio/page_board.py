"""Workshop > Place on car: import sponsor logos and tribals and put them anywhere on the car.

The board replaces the fixed sponsor boxes as the way to see a livery: drag a logo where you want it, scale and turn it,
give it the colour of Sponsor A or B, the tribal colour or any colour or gradient, add an outline, and save the board.
"""
import copy
import math
import random
import time
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QKeySequence, QPainter, QPen, QShortcut
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFileDialog, QInputDialog, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QMenu,
                               QMessageBox, QScrollArea, QSizePolicy, QVBoxLayout, QWidget)

from . import board as bd
from . import render
from . import theme as th
from .page_generator import SlotRow
from .page_gradients import slider_row
from .widgets import EmptyState, PaintSwitch, button, label

HANDLE = 8             # half the size of a scale handle, in pixels
ROTATE_GAP = 30        # how far above the item the rotate handle sits
SNAP_PX = 7


class BoardCanvas(QWidget):
    """The car on the garage floor with the items on it; items are picked, moved, scaled and turned with the mouse."""
    selectionChanged = Signal(str)
    edited = Signal()                # an item changed (moved, scaled, turned, removed)
    aboutToEdit = Signal(str)        # call before a change starts, with a tag; the owner takes an undo snapshot
    dropped = Signal(list)

    def __init__(self):
        super().__init__()
        self.board = None
        self.pl = None
        self.view = "side"
        self.selected = ""
        self.show_zones = False
        self.snap = True
        self.guides = []             # ("x"|"y", fraction) lines drawn while snapping
        self._drag = None
        self.setMinimumSize(520, 300)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAcceptDrops(True)

    # ------------------------------------------------------------------ geometry
    def car(self):
        return render.PREVIEW_CAR

    def target(self):
        """The rectangle the car view is drawn in."""
        car = self.car()
        if car is None or self.view not in car.views():
            return None
        r = QRectF(self.rect()).adjusted(22, 18, -22, -14)
        w, h = car.view_info(self.view)["size"]
        ar = w / h
        tw, th = min(r.width(), r.height() * ar), min(r.height(), r.width() / ar)
        return QRectF(r.center().x() - tw / 2, r.center().y() - th / 2, tw, th)

    def items(self):
        return [] if self.board is None else [i for i in self.board.items if i["view"] == self.view]

    def _prep(self, it, T):
        return bd.prepare(it, self.pl, self.board.root, need=it["w"] * T.width() * self.devicePixelRatioF() * 1.1)

    def current(self):
        return None if self.board is None else self.board.find(self.selected)

    def _corners(self, it, T):
        prep = self._prep(it, T)
        lw, lh = bd.item_size(it, T, prep)
        t = bd.item_transform(it, T)
        return [t.map(QPointF(sx * lw / 2, sy * lh / 2)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]

    def _rotate_handle(self, it, T):
        prep = self._prep(it, T)
        _lw, lh = bd.item_size(it, T, prep)
        return bd.item_transform(it, T).map(QPointF(0, -lh / 2 - ROTATE_GAP))

    def _handle_at(self, it, T, pt):
        """'rotate', 'corner' or '' for the point `pt` against the handles of the selected item."""
        if (self._rotate_handle(it, T) - pt).manhattanLength() <= HANDLE * 1.6:
            return "rotate"
        for c in self._corners(it, T):
            if (c - pt).manhattanLength() <= HANDLE * 1.7:
                return "corner"
        return ""

    def _item_at(self, T, pt):
        for it in reversed(self.items()):
            prep = self._prep(it, T)
            if prep.ok and bd.hit(it, T, prep, pt):
                return it
        return None

    # ------------------------------------------------------------------ painting
    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        render.draw_stage(p, r, cut=22)
        T = self.target()
        if T is None or self.pl is None:
            p.setPen(render.MUTED)
            p.setFont(render.body_font(15))
            car = self.car()
            msg = ("Choose a car in “Preview car” (top right)." if car is None else
                   f"{car.name} has no {self.view} view. Pick the view that exists, or another car.")
            p.drawText(r, Qt.AlignCenter, msg)
            return
        car = self.car()
        dpr = self.devicePixelRatioF()
        bd.paint_car(p, T, car, self.view, self.pl, dpr=dpr, plates={})
        if self.show_zones:
            self._paint_zones(p, T, car)
        if self.board is not None:
            bd.paint_items(p, T, self.board.items, self.pl, self.board.root, self.view, dpr=dpr)
        self._paint_guides(p, T)
        it = self.current()
        if it is not None and it["view"] == self.view:
            self._paint_selection(p, T, it)

    def _paint_zones(self, p, T, car):
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 90), 1, Qt.DashLine))
        f = QFont(render.body_font(11))
        p.setFont(f)
        for z, (x, y, w, h) in car.zones(self.view).items():
            r = QRectF(T.x() + x * T.width(), T.y() + y * T.height(), w * T.width(), h * T.height())
            p.drawRect(r)
            p.drawText(r.adjusted(3, 1, 0, 0), Qt.AlignLeft | Qt.AlignTop, z)

    def _paint_guides(self, p, T):
        if not self.guides:
            return
        p.setPen(QPen(render.RED, 1, Qt.DashLine))
        for axis, v in self.guides:
            if axis == "x":
                x = T.x() + v * T.width()
                p.drawLine(QPointF(x, T.top()), QPointF(x, T.bottom()))
            else:
                y = T.y() + v * T.height()
                p.drawLine(QPointF(T.left(), y), QPointF(T.right(), y))

    def _paint_selection(self, p, T, it):
        pts = self._corners(it, T)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(render.RED, 1.5))
        for a, b in zip(pts, pts[1:] + pts[:1]):
            p.drawLine(a, b)
        top = (pts[0] + pts[1]) / 2
        rot = self._rotate_handle(it, T)
        p.drawLine(top, rot)
        p.setBrush(QColor(th.BG))
        for c in pts:
            p.drawRect(QRectF(c.x() - HANDLE / 2, c.y() - HANDLE / 2, HANDLE, HANDLE))
        p.setBrush(render.RED)
        p.drawEllipse(rot, HANDLE * .75, HANDLE * .75)

    # ------------------------------------------------------------------ mouse
    def mousePressEvent(self, e):
        self.setFocus()
        T = self.target()
        if T is None or self.board is None or e.button() not in (Qt.LeftButton, Qt.RightButton):
            return
        pt = e.position()
        cur = self.current()
        if e.button() == Qt.LeftButton and cur is not None and cur["view"] == self.view:
            h = self._handle_at(cur, T, pt)
            if h:
                self._begin(h, cur, T, pt)
                return
        it = self._item_at(T, pt)
        self._select(it["id"] if it else "")
        if it is not None and e.button() == Qt.LeftButton:
            self._begin("move", it, T, pt)

    def _begin(self, mode, it, T, pt):
        self.aboutToEdit.emit(f"{mode}:{it['id']}")
        c = QPointF(T.x() + it["x"] * T.width(), T.y() + it["y"] * T.height())
        v = pt - c
        self._drag = dict(mode=mode, id=it["id"], start=QPointF(pt), x=it["x"], y=it["y"], w=it["w"], rot=it["rot"], centre=c,
                          dist=max(1.0, math.hypot(v.x(), v.y())), ang=math.degrees(math.atan2(v.y(), v.x())))

    def mouseMoveEvent(self, e):
        T = self.target()
        if T is None:
            return
        pt = e.position()
        d = self._drag
        if d is None:
            cur = self.current()
            h = self._handle_at(cur, T, pt) if cur is not None and cur["view"] == self.view and self.board else ""
            hit = self._item_at(T, pt) if not h and self.board else None
            self.setCursor(Qt.CrossCursor if h == "rotate" else Qt.SizeFDiagCursor if h == "corner" else
                           Qt.SizeAllCursor if hit else Qt.ArrowCursor)
            return
        it = self.board.find(d["id"])
        if it is None:
            return
        self.guides = []
        if d["mode"] == "move":
            dx, dy = (pt.x() - d["start"].x()) / T.width(), (pt.y() - d["start"].y()) / T.height()
            x, y = d["x"] + dx, d["y"] + dy
            if self.snap and not (e.modifiers() & Qt.AltModifier):
                tx, ty = SNAP_PX / T.width(), SNAP_PX / T.height()
                if abs(x - .5) < tx:
                    x = .5
                    self.guides.append(("x", .5))
                if abs(y - .5) < ty:
                    y = .5
                    self.guides.append(("y", .5))
            it["x"], it["y"] = round(min(1.3, max(-.3, x)), 4), round(min(1.3, max(-.3, y)), 4)
        elif d["mode"] == "corner":
            v = pt - d["centre"]
            it["w"] = round(min(2.0, max(.01, d["w"] * math.hypot(v.x(), v.y()) / d["dist"])), 4)
        else:
            v = pt - d["centre"]
            rot = d["rot"] + math.degrees(math.atan2(v.y(), v.x())) - d["ang"]
            if e.modifiers() & Qt.ShiftModifier:
                rot = round(rot / 15) * 15
            it["rot"] = round(((rot + 180) % 360) - 180, 1)
        self.update()
        self.edited.emit()

    def mouseReleaseEvent(self, _e):
        if self._drag is not None:
            self._drag = None
            self.guides = []
            self.update()
            self.edited.emit()

    def wheelEvent(self, e):
        it = self.current()
        if it is None or not (e.modifiers() & Qt.ControlModifier):
            return super().wheelEvent(e)
        self.aboutToEdit.emit(f"wheel:{it['id']}")
        it["w"] = round(min(2.0, max(.01, it["w"] * (1.05 if e.angleDelta().y() > 0 else 1 / 1.05))), 4)
        self.update()
        self.edited.emit()

    def contextMenuEvent(self, e):
        T = self.target()
        if T is None or self.board is None:
            return
        it = self._item_at(T, QPointF(e.pos()))
        self._select(it["id"] if it else "")
        if it is None:
            return
        m = QMenu(self)
        for text, fn in (("Duplicate", self.duplicate), ("Mirror", self.mirror), ("Bring to front", lambda: self.reorder(1, True)),
                         ("Send to back", lambda: self.reorder(-1, True)), ("Delete", self.delete)):
            m.addAction(text, fn)
        m.exec(e.globalPos())

    # ------------------------------------------------------------------ keys and drops
    def keyPressEvent(self, e):
        it = self.current()
        k = e.key()
        step = .01 if e.modifiers() & Qt.ShiftModifier else .002
        if it is not None and k in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down):
            self.aboutToEdit.emit(f"nudge:{it['id']}")
            dx = {Qt.Key_Left: -step, Qt.Key_Right: step}.get(k, 0)
            dy = {Qt.Key_Up: -step, Qt.Key_Down: step}.get(k, 0)
            it["x"], it["y"] = round(it["x"] + dx, 4), round(it["y"] + dy, 4)
            self.update()
            self.edited.emit()
        elif it is not None and k in (Qt.Key_Delete, Qt.Key_Backspace):
            self.delete()
        elif it is not None and k == Qt.Key_Escape:
            self._select("")
        elif it is not None and k in (Qt.Key_PageUp, Qt.Key_PageDown):
            self.reorder(1 if k == Qt.Key_PageUp else -1, bool(e.modifiers() & Qt.ControlModifier))
        elif it is not None and k == Qt.Key_D and e.modifiers() & Qt.ControlModifier:
            self.duplicate()
        else:
            super().keyPressEvent(e)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        files = [u.toLocalFile() for u in e.mimeData().urls() if Path(u.toLocalFile()).suffix.lower() in bd.IMPORT_EXT]
        if files:
            self.dropped.emit(files)
            e.acceptProposedAction()

    # ------------------------------------------------------------------ item actions (also used by the buttons)
    def _select(self, item_id):
        if item_id != self.selected:
            self.selected = item_id
            self.selectionChanged.emit(item_id)
        self.update()

    def delete(self):
        it = self.current()
        if it is None:
            return
        self.aboutToEdit.emit("delete")
        self.board.items.remove(it)
        self.selected = ""
        self.selectionChanged.emit("")
        self.update()
        self.edited.emit()

    def duplicate(self):
        it = self.current()
        if it is None:
            return
        self.aboutToEdit.emit("duplicate")
        new = copy.deepcopy(it)
        new["id"] = bd.default_item()["id"]
        new["name"] = f"{it['name']} copy".strip()
        new["x"], new["y"] = round(min(1.0, it["x"] + .03), 4), round(min(1.0, it["y"] + .03), 4)
        self.board.items.insert(self.board.items.index(it) + 1, new)
        self.selected = new["id"]
        self.selectionChanged.emit(new["id"])
        self.update()
        self.edited.emit()

    def mirror(self):
        it = self.current()
        if it is not None:
            self.aboutToEdit.emit("mirror")
            it["flip"] = not it["flip"]
            self.update()
            self.edited.emit()

    def reorder(self, direction, to_end=False):
        """Move the selected item one step (or to the very front or back) in the stack."""
        it = self.current()
        if it is None:
            return
        items = self.board.items
        i = items.index(it)
        j = (len(items) - 1 if direction > 0 else 0) if to_end else min(len(items) - 1, max(0, i + direction))
        if j == i:
            return
        self.aboutToEdit.emit("reorder")
        items.insert(j, items.pop(i))
        self.update()
        self.edited.emit()


class LibraryDialog(QDialog):
    """Pick logos from the vault's logo library by brand name."""

    def __init__(self, logos, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Logo library")
        self.resize(460, 560)
        self.search = QLineEdit(placeholderText="Search brand…")
        self.search.textChanged.connect(self._filter)
        self.list = QListWidget()
        self.list.setSelectionMode(QListWidget.ExtendedSelection)
        for name, path in logos:
            row = QListWidgetItem(name)
            row.setData(Qt.UserRole, path)
            self.list.addItem(row)
        self.list.itemDoubleClicked.connect(lambda _i: self.accept())
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(button("Cancel", slot=self.reject))
        row.addWidget(button("Place on the car", True, self.accept))
        lay = QVBoxLayout(self)
        lay.addWidget(label("The logos of your library that are on this computer (single-colour masters: they take the colour of "
                            "Sponsor A). Select one or more.", "muted", wrap=True))
        lay.addWidget(self.search)
        lay.addWidget(self.list, 1)
        lay.addLayout(row)

    def _filter(self, text):
        t = text.strip().lower()
        for i in range(self.list.count()):
            self.list.item(i).setHidden(bool(t) and t not in self.list.item(i).text().lower())

    def chosen(self):
        return [(i.text(), i.data(Qt.UserRole)) for i in self.list.selectedItems()]


class BoardTab(QWidget):
    status = Signal(str)
    layoutChanged = Signal()         # the board used by the previews changed

    def __init__(self, vault, palette_source=None):
        super().__init__()
        self.vault = vault
        self.palette_source = palette_source
        self.board = bd.Board(vault.lib)
        self._loading = False
        self._undo, self._redo = [], []
        self._last_tag, self._last_time = "", 0.0
        self._pl = bd.palette_ns({})

        self.canvas = BoardCanvas()
        self.canvas.board, self.canvas.pl = self.board, self._pl
        self.canvas.selectionChanged.connect(self._selection_changed)
        self.canvas.edited.connect(self._edited)
        self.canvas.aboutToEdit.connect(self._snapshot)
        self.canvas.dropped.connect(lambda files: self.import_files(files, "sponsor"))

        # ---- left: board, palette, add, items, the selected item
        self.source = QComboBox()
        self.source.addItem("Palette: the New project page", 0)
        for p in vault.projects():
            self.source.addItem(f"Palette: {p.id:03d}  {p.name}", p.id)
        self.source.activated.connect(self._source_picked)
        self.view_box = QComboBox()
        self.view_box.addItem("Side view", "side")
        self.view_box.addItem("Top view", "top")
        self.view_box.currentIndexChanged.connect(self._view_picked)
        self.zones_check = QCheckBox("Show sponsor zones as a guide")
        self.zones_check.toggled.connect(self._zones_toggled)
        self.snap_check = QCheckBox("Snap to the middle of the car")
        self.snap_check.setChecked(True)
        self.snap_check.toggled.connect(self._snap_toggled)

        self.boards = QComboBox()
        self.boards.activated.connect(self._board_picked)
        self.name = QLineEdit(placeholderText="Board name")
        self.name.editingFinished.connect(self._renamed)
        self.use_layout = QCheckBox("Use this board on all car previews")
        self.use_layout.setToolTip("Every preview car (Projects, New project) shows this board's logos and tribals, in the colours of its own "
                                   "palette, instead of the small sponsor plates.")
        self.use_layout.toggled.connect(self._use_layout_toggled)

        self.list = QListWidget()
        self.list.setMaximumHeight(170)
        self.list.currentItemChanged.connect(self._list_picked)
        self.empty = EmptyState("Nothing on the car yet", "Import a sponsor logo or a tribal (PNG, SVG, WebP or JPG), or drop files on the car.")
        self.empty.setMinimumHeight(150)

        self.f_name = QLineEdit(placeholderText="Name")
        self.f_name.editingFinished.connect(lambda: self._set("name", self.f_name.text().strip()))
        self.f_kind = QComboBox()
        for k, text in bd.KINDS:
            self.f_kind.addItem(text, k)
        self.f_kind.activated.connect(lambda _i: self._set("kind", self.f_kind.currentData()))
        w_size, self.s_size = slider_row("Size", 1, 100, 16, "%", lambda: self._slider("w", self.s_size.value() / 100))
        w_rot, self.s_rot = slider_row("Turn", -180, 180, 0, "°", lambda: self._slider("rot", float(self.s_rot.value())))
        w_op, self.s_op = slider_row("Opacity", 5, 100, 100, "%", lambda: self._slider("opacity", self.s_op.value() / 100))
        self.c_flip = QCheckBox("Mirror")
        self.c_flip.toggled.connect(lambda on: self._set("flip", on))
        self.f_bg = QComboBox()
        for k, text in (("auto", "Background: remove a plain one"), ("keep", "Background: keep as it is"), ("remove", "Background: remove the corner colour")):
            self.f_bg.addItem(text, k)
        self.f_bg.activated.connect(lambda _i: self._set("bg", self.f_bg.currentData()))
        self.f_colour = QComboBox()
        for k, text in bd.SOURCES:
            self.f_colour.addItem(text, k)
        self.f_colour.activated.connect(lambda _i: self._colour_mode(self.f_colour.currentData()))
        self.row_colour = SlotRow("colour", "Custom colour", True)
        self.row_colour.lock.setVisible(False)
        self.row_colour.changed.connect(lambda: self._set_in("colour", "value", self.row_colour.value()))
        self.c_outline = QCheckBox("Outline")
        self.c_outline.toggled.connect(lambda on: self._set_in("outline", "on", on))
        self.f_outline = QComboBox()
        for k, text in bd.OUTLINE_MODES:
            self.f_outline.addItem(text, k)
        self.f_outline.activated.connect(lambda _i: self._outline_mode(self.f_outline.currentData()))
        self.row_outline = SlotRow("outline", "Custom outline", True)
        self.row_outline.lock.setVisible(False)
        self.row_outline.changed.connect(lambda: self._set_in("outline", "value", self.row_outline.value()))
        w_thick, self.s_thick = slider_row("Thickness", 3, 120, 30, "", lambda: self._slider_later("size", self.s_thick.value() / 10))
        self.thick_timer = QTimer(self)
        self.thick_timer.setSingleShot(True)
        self.thick_timer.setInterval(110)
        self.thick_timer.timeout.connect(self._apply_thick)

        self.item_box = QWidget()
        ib = QVBoxLayout(self.item_box)
        ib.setContentsMargins(0, 0, 0, 0)
        ib.addWidget(self.f_name)
        ib.addWidget(self.f_kind)
        ib.addWidget(w_size)
        ib.addWidget(w_rot)
        ib.addWidget(w_op)
        ib.addWidget(self.c_flip)
        ib.addWidget(self.f_bg)
        ib.addWidget(label("Colour", "h2"))
        ib.addWidget(self.f_colour)
        ib.addWidget(self.row_colour)
        ib.addWidget(self.c_outline)
        ib.addWidget(self.f_outline)
        ib.addWidget(self.row_outline)
        ib.addWidget(w_thick)
        rowb = QHBoxLayout()
        for text, fn in (("Duplicate", self.canvas.duplicate), ("Front", lambda: self.canvas.reorder(1, True)),
                         ("Back", lambda: self.canvas.reorder(-1, True)), ("Delete", self.canvas.delete)):
            rowb.addWidget(button(text, slot=fn))
        ib.addLayout(rowb)
        ib.addWidget(button("Give every logo of this kind the same colour", slot=self.same_colour))
        self.item_box.setVisible(False)

        add = QHBoxLayout()
        add.addWidget(button("Import logos…", True, lambda: self.pick_files("sponsor")))
        add.addWidget(button("Import tribals…", slot=lambda: self.pick_files("tribal")))
        add2 = QHBoxLayout()
        add2.addWidget(button("From the logo library…", slot=self.pick_library))
        add2.addWidget(button("Add a name…", slot=self.add_text))
        top_row = QHBoxLayout()
        top_row.addWidget(self.boards, 1)
        top_row.addWidget(button("New", slot=self.new_board))
        top_row.addWidget(button("Delete", slot=self.delete_board))
        form = QVBoxLayout()
        form.setContentsMargins(0, 0, 12, 0)
        form.addWidget(label("Place logos and tribals anywhere on the car. Drag to move, the corners scale, the round handle turns "
                             "(Shift snaps to 15°), arrows nudge, Ctrl + wheel scales, Del removes, Ctrl+Z undoes.", "muted", wrap=True))
        form.addLayout(top_row)
        form.addWidget(self.name)
        form.addWidget(self.source)
        form.addWidget(self.view_box)
        form.addWidget(self.zones_check)
        form.addWidget(self.snap_check)
        form.addWidget(self.use_layout)
        form.addLayout(add)
        form.addLayout(add2)
        form.addWidget(label("On the car", "h2"))
        form.addWidget(self.list)
        form.addWidget(self.empty)
        form.addWidget(self.item_box)
        form.addStretch()
        host = QWidget()
        host.setObjectName("page")
        host.setLayout(form)
        scroll = QScrollArea()
        scroll.setWidget(host)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFixedWidth(470)

        self.paint = PaintSwitch()
        self.note = label("", "muted", wrap=True)
        acts = QHBoxLayout()
        acts.addWidget(button("Save image…", True, self.save_image))
        acts.addWidget(button("Copy image", slot=self.copy_image))
        acts.addWidget(button("Shuffle", slot=self.shuffle))
        acts.addWidget(button("Undo", slot=self.undo))
        acts.addWidget(button("Redo", slot=self.redo))
        acts.addStretch()
        right = QVBoxLayout()
        right.setContentsMargins(6, 0, 0, 0)
        right.addWidget(self.paint)
        right.addWidget(self.canvas, 1)
        right.addWidget(self.note)
        right.addLayout(acts)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 8, 0, 0)
        lay.addWidget(scroll)
        lay.addLayout(right, 1)

        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(500)
        self.save_timer.timeout.connect(self.save_now)
        for seq, fn in (("Ctrl+Z", self.undo), ("Ctrl+Y", self.redo), ("Ctrl+Shift+Z", self.redo)):
            sc = QShortcut(QKeySequence(seq), self)
            sc.setContext(Qt.WidgetWithChildrenShortcut)
            sc.activated.connect(fn)
        self._refill_boards()
        self._load_last()
        self.refresh_palette()
        self.refresh_car()

    # ------------------------------------------------------------------ the palette and the car
    def palette(self):
        return self._pl

    def refresh_palette(self):
        pid = self.board.source
        if pid:
            p = next((q for q in self.vault.projects() if q.id == pid), None)
        else:
            p = None
        if p is not None:
            self._pl = bd.palette_ns(p)
        else:
            self._pl = bd.palette_ns(dict(self.palette_source()) if self.palette_source else {})
        self.canvas.pl = self._pl
        self.canvas.update()
        self.layoutChanged.emit()

    def refresh_car(self):
        """After the preview car changed: only the views that car has can be chosen."""
        car = render.PREVIEW_CAR
        views = car.views() if car is not None else []
        for i in range(self.view_box.count()):
            self.view_box.model().item(i).setEnabled(self.view_box.itemData(i) in views or car is None)
        if views and self.canvas.view not in views:
            self.view_box.setCurrentIndex(self.view_box.findData(views[0]))
            self.canvas.view = views[0]
            self._fill_list()
        n = len(self.board.items)
        other = sum(1 for i in self.board.items if i["view"] not in views)
        self.note.setText("" if not other else f"{other} of {n} items are placed on a view this car does not have; they stay on the board.")
        self.canvas.update()

    def _refill_sources(self):
        """The projects may have changed since the tab was built (a new one was saved)."""
        want = self.board.source
        self.source.blockSignals(True)
        self.source.clear()
        self.source.addItem("Palette: the New project page", 0)
        for p in self.vault.projects():
            self.source.addItem(f"Palette: {p.id:03d}  {p.name}", p.id)
        self.source.setCurrentIndex(max(0, self.source.findData(want)))
        self.source.blockSignals(False)

    def showEvent(self, e):
        super().showEvent(e)
        if self.source.count() != len(self.vault.projects()) + 1:
            self._refill_sources()
        if not self.board.source:     # the New project page may have changed since the board was last shown
            self.refresh_palette()
        self.refresh_car()

    def _source_picked(self, _i):
        self.board.source = int(self.source.currentData() or 0)
        self.refresh_palette()
        self._changed(save=True)

    def _view_picked(self, _i):
        self.canvas.view = self.view_box.currentData()
        self.canvas.selected = ""
        self._fill_list()
        self.canvas.update()

    def _zones_toggled(self, on):
        self.canvas.show_zones = on
        self.canvas.update()

    def _snap_toggled(self, on):
        self.canvas.snap = on

    # ------------------------------------------------------------------ boards on disk
    def _refill_boards(self):
        cur = self.board.name
        self.boards.blockSignals(True)
        self.boards.clear()
        names = bd.Board.names(self.vault.lib)
        if cur not in names:
            names.insert(0, cur)
        self.boards.addItem("Open a saved board…", None)
        for n in names:
            self.boards.addItem(n, n)
        self.boards.setCurrentIndex(max(0, self.boards.findData(cur)))
        self.boards.blockSignals(False)
        self.name.setText(cur)

    def _last_file(self):
        return self.board.root / ".last"

    def _load_last(self):
        try:
            name = self._last_file().read_text(encoding="utf-8").strip()
            if name and (self.board.root / f"{name}.json").exists():
                self._open(name)
        except OSError:
            pass

    def _remember(self):
        try:
            self.board.root.mkdir(parents=True, exist_ok=True)
            self._last_file().write_text(self.board.name, encoding="utf-8")
        except OSError:
            pass

    def _open(self, name):
        try:
            b = bd.Board.load(self.vault.lib, name)
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, "Open board", f"Could not open {name}: {e}")
            return
        self.board = b
        self._undo, self._redo = [], []
        self.canvas.board = b
        self.canvas.selected = ""
        i = self.source.findData(b.source)
        self.source.setCurrentIndex(max(0, i))
        self.refresh_palette()
        self._refill_boards()
        self._fill_list()
        self._selection_changed("")
        self._remember()
        self.layoutChanged.emit()

    def _board_picked(self, _i):
        name = self.boards.currentData()
        if name and name != self.board.name:
            self.save_now()
            self._open(name)

    def new_board(self):
        self.save_now()
        names = set(bd.Board.names(self.vault.lib))
        n = 1
        while (f"Board {n}" if n > 1 else "Untitled") in names:
            n += 1
        b = bd.Board(self.vault.lib, f"Board {n}" if n > 1 else "Untitled")
        b.source = self.board.source
        self.board = b
        self._undo, self._redo = [], []
        self.canvas.board = b
        self.canvas.selected = ""
        self._refill_boards()
        self._fill_list()
        self._selection_changed("")
        self._remember()
        self.layoutChanged.emit()

    def delete_board(self):
        if not self.board.items and not self.board.path.exists():
            return
        if QMessageBox.question(self, "Delete board", f"Delete the board “{self.board.name}”? The imported logo files stay in Boards/Logos.") != QMessageBox.Yes:
            return
        self.board.delete()
        names = bd.Board.names(self.vault.lib)
        if names:
            self._open(names[0])
        else:
            self.new_board()

    def _renamed(self):
        new = bd.safe_name(self.name.text())
        if new == self.board.name:
            return
        if (self.board.root / f"{new}.json").exists():
            QMessageBox.warning(self, "Rename board", f"There is already a board called {new}.")
            self.name.setText(self.board.name)
            return
        old = self.board.path
        self.board.name = new
        self.board.save()
        if old.exists():
            old.unlink()
        self._refill_boards()
        self._remember()
        self.layoutChanged.emit()

    def save_now(self):
        self.save_timer.stop()
        if not self.board.items and not self.board.path.exists():
            return
        try:
            self.board.save()
            self._remember()
        except OSError as e:
            self.status.emit(f"Could not save the board: {e}")

    # ------------------------------------------------------------------ importing
    def pick_files(self, kind):
        exts = " ".join(f"*{e}" for e in bd.IMPORT_EXT)
        files, _ = QFileDialog.getOpenFileNames(self, "Import sponsor logos" if kind == "sponsor" else "Import tribals", "",
                                                f"Images ({exts});;All files (*)")
        if files:
            self.import_files(files, kind)

    def pick_library(self):
        logos = bd.library_logos(self.vault)
        if not logos:
            QMessageBox.information(self, "Logo library", "No logos from the library were found on this computer. Import logo files "
                                    "with “Import logos…”, or add a name with “Add a name…”.")
            return
        dlg = LibraryDialog(logos, self)
        if dlg.exec() == QDialog.Accepted and dlg.chosen():
            self._snapshot("library")
            added = []
            for name, path in dlg.chosen():
                try:
                    added.append(self.board.import_file(path, "sponsor", self.canvas.view, name=name, colour="sponsor_a"))
                except Exception as e:
                    self.status.emit(f"{name}: {e}")
            self._added(added)

    def add_text(self):
        text, ok = QInputDialog.getText(self, "Add a name", "The sponsor's name, as it should read on the car:")
        if ok and text.strip():
            self._snapshot("text")
            try:
                self._added([self.board.add_text(text, "sponsor", self.canvas.view)])
            except Exception as e:
                QMessageBox.warning(self, "Add a name", str(e))

    def _added(self, added):
        if not added:
            return
        self.canvas.selected = added[-1]["id"]
        self._fill_list()
        self._selection_changed(added[-1]["id"])
        self._changed(save=True)
        self.status.emit(f"Placed {len(added)} on the car")

    def same_colour(self):
        it = self._cur()
        if it is None:
            return
        self._snapshot("samecolour")
        n = 0
        for o in self.board.items:
            if o["kind"] == it["kind"] and o is not it:
                o["colour"] = copy.deepcopy(it["colour"])
                n += 1
        self._changed(save=True)
        self.status.emit(f"{n} other {'tribals' if it['kind'] == 'tribal' else 'logos'} now use the same colour")

    def import_files(self, files, kind="sponsor"):
        self._snapshot("import")
        added, failed = [], []
        for f in files:
            try:
                added.append(self.board.import_file(f, kind, self.canvas.view))
            except Exception as e:
                failed.append(f"{Path(f).name}: {e}")
        if added:
            self.canvas.selected = added[-1]["id"]
            self._fill_list()
            self._selection_changed(added[-1]["id"])
            self._changed(save=True)
            self.status.emit(f"Placed {len(added)} on the car")
        if failed:
            QMessageBox.warning(self, "Import", "Some files could not be placed:\n\n" + "\n".join(failed))
        return added

    # ------------------------------------------------------------------ the list and the selected item
    def _fill_list(self):
        cur = self.canvas.selected
        self.list.blockSignals(True)
        self.list.clear()
        items = self.canvas.items()
        for it in reversed(items):       # the top of the stack first
            row = QListWidgetItem(f"{it['name'] or Path(it['file']).stem}   ·   {'tribal' if it['kind'] == 'tribal' else 'logo'}")
            row.setData(Qt.UserRole, it["id"])
            self.list.addItem(row)
            if it["id"] == cur:
                self.list.setCurrentItem(row)
        self.list.blockSignals(False)
        self.list.setVisible(bool(items))
        self.empty.setVisible(not items)

    def _list_picked(self, row, _prev):
        if row is not None:
            self.canvas._select(row.data(Qt.UserRole))

    def _selection_changed(self, item_id):
        it = self.board.find(item_id) if item_id else None
        self.item_box.setVisible(it is not None)
        self._fill_list()
        if it is None:
            return
        self._loading = True
        self.f_name.setText(it["name"])
        self.f_kind.setCurrentIndex(self.f_kind.findData(it["kind"]))
        self.s_size.setValue(round(it["w"] * 100))
        self.s_rot.setValue(round(it["rot"]))
        self.s_op.setValue(round(it["opacity"] * 100))
        self.c_flip.setChecked(it["flip"])
        self.f_bg.setCurrentIndex(self.f_bg.findData(it["bg"]))
        self.f_colour.setCurrentIndex(self.f_colour.findData(it["colour"]["mode"]))
        self.row_colour.set_value(it["colour"]["value"])
        self.row_colour.setVisible(it["colour"]["mode"] == "custom")
        o = it["outline"]
        self.c_outline.setChecked(o["on"])
        self.f_outline.setCurrentIndex(self.f_outline.findData(o["mode"]))
        self.row_outline.set_value(o["value"])
        self.s_thick.setValue(round(o["size"] * 10))
        self._outline_visibility(it)
        self._loading = False

    def _outline_visibility(self, it):
        on = it["outline"]["on"]
        self.f_outline.setVisible(on)
        self.row_outline.setVisible(on and it["outline"]["mode"] == "custom")
        self.s_thick.parentWidget().setVisible(on)

    def _edited(self):
        """The canvas moved, scaled or turned something: mirror it into the controls and save."""
        it = self.canvas.current()
        if it is not None:
            self._loading = True
            self.s_size.setValue(round(it["w"] * 100))
            self.s_rot.setValue(round(it["rot"]))
            self._loading = False
        self._changed(save=True)

    def _changed(self, save=False):
        self.canvas.update()
        if save:
            self.save_timer.start()
        self.layoutChanged.emit()

    # ------------------------------------------------------------------ editing the selected item
    def _cur(self):
        return None if self._loading else self.canvas.current()

    def _set(self, key, value):
        it = self._cur()
        if it is None or it[key] == value:
            return
        self._snapshot(f"{key}:{it['id']}")
        it[key] = value
        if key in ("name", "kind"):
            self._fill_list()
        self._changed(save=True)

    def _set_in(self, group, key, value):
        it = self._cur()
        if it is None or it[group][key] == value:
            return
        self._snapshot(f"{group}.{key}:{it['id']}")
        it[group][key] = value
        if group == "outline":
            self._outline_visibility(it)
        self._changed(save=True)

    def _slider(self, key, value):
        it = self._cur()
        if it is None:
            return
        self._snapshot(f"{key}:{it['id']}")
        it[key] = value
        self._changed(save=True)

    def _slider_later(self, key, value):
        self._pending_thick = value
        self.thick_timer.start()

    def _apply_thick(self):
        it = self._cur()
        if it is not None:
            self._snapshot(f"size:{it['id']}")
            it["outline"]["size"] = round(self._pending_thick, 1)
            self._changed(save=True)

    def _colour_mode(self, mode):
        it = self._cur()
        if it is None:
            return
        self._snapshot(f"colourmode:{it['id']}")
        it["colour"]["mode"] = mode
        self.row_colour.setVisible(mode == "custom")
        if mode == "custom":
            it["colour"]["value"] = self.row_colour.value()
        self._changed(save=True)

    def _outline_mode(self, mode):
        it = self._cur()
        if it is None:
            return
        self._snapshot(f"outlinemode:{it['id']}")
        it["outline"]["mode"] = mode
        self._outline_visibility(it)
        self._changed(save=True)

    # ------------------------------------------------------------------ shuffle
    def shuffle(self):
        """Throw the items of this view into new places on the body, sizes, turns and sponsor colours: a quick way to get ideas."""
        items = self.canvas.items()
        if not items:
            self.status.emit("Place something on the car first, then shuffle")
            return
        car = render.PREVIEW_CAR
        right = car is not None and car.front_of(self.canvas.view) == "right"
        side = self.canvas.view == "side"
        # good spots on the side of a car, as seen with its front on the left: door, fender, rear quarter, hood, skirt, quarter glass
        spots = [(.52, .62), (.22, .58), (.78, .58), (.16, .50), (.5, .8), (.66, .45), (.36, .5)]
        random.shuffle(spots)
        self._snapshot("shuffle")
        sponsors = 0
        for it in items:
            if it["kind"] == "tribal":
                it["x"], it["y"] = round(random.uniform(.38, .62), 4), round(random.uniform(.5, .62), 4)
                it["w"] = round(random.uniform(.32, .55), 4)
                it["rot"] = round(random.choice([0, 0, random.uniform(-6, 6)]), 1)
                continue
            x, y = spots[sponsors % len(spots)] if side else (random.uniform(.3, .7), random.uniform(.2, .8))
            sponsors += 1
            it["x"] = round(min(1.0, max(0.0, (1 - x if right and side else x) + random.uniform(-.02, .02))), 4)
            it["y"] = round(y + random.uniform(-.02, .02), 4)
            it["w"] = round(random.uniform(.09, .2), 4)
            it["rot"] = round(random.choice([0, 0, random.uniform(-8, 8)]), 1)
            if it["colour"]["mode"] != "original":
                it["colour"]["mode"] = random.choice(["sponsor_a", "sponsor_b"])
        self._selection_changed(self.canvas.selected)
        self._changed(save=True)
        self.status.emit("Shuffled")

    # ------------------------------------------------------------------ undo
    def _snapshot(self, tag):
        """Remember the items before a change; changes with the same tag in a row (a drag, a slider) count as one."""
        now = time.monotonic()
        if tag == self._last_tag and now - self._last_time < 1.2:
            self._last_time = now
            return
        self._last_tag, self._last_time = tag, now
        self._undo.append(copy.deepcopy(self.board.items))
        del self._undo[:-80]
        self._redo.clear()

    def _restore(self, items):
        self.board.items = items
        keep = self.canvas.selected if self.board.find(self.canvas.selected) else ""
        self.canvas.selected = keep
        self._last_tag = ""
        self._fill_list()
        self._selection_changed(keep)
        self._changed(save=True)

    def undo(self):
        if not self._undo:
            return
        self._redo.append(copy.deepcopy(self.board.items))
        self._restore(self._undo.pop())

    def redo(self):
        if not self._redo:
            return
        self._undo.append(copy.deepcopy(self.board.items))
        self._restore(self._redo.pop())

    # ------------------------------------------------------------------ the layout used by the previews
    def _use_layout_toggled(self, _on):
        self.layoutChanged.emit()

    # ------------------------------------------------------------------ output
    def _scene(self, width, background):
        car = render.PREVIEW_CAR
        if car is None or self.canvas.view not in car.views():
            return None
        return bd.render_scene(car, self.canvas.view, self._pl, self.board.items, self.board.root, width, background)

    def save_image(self):
        car = render.PREVIEW_CAR
        if car is None:
            QMessageBox.information(self, "Save image", "Choose a car in “Preview car” first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save image", f"{self.board.name} - {car.name}.png", "PNG image (*.png)")
        if not path:
            return
        ask = QMessageBox.question(self, "Save image", "Keep the background transparent?\n\nYes: only the car and the logos.\nNo: on a light floor.",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        img = self._scene(2400, ask == QMessageBox.No)
        if img is None or not img.save(path):
            QMessageBox.warning(self, "Save image", "The image could not be saved.")
            return
        self.status.emit(f"Saved {Path(path).name}")

    def copy_image(self):
        img = self._scene(1800, True)
        if img is None:
            return
        QGuiApplication.clipboard().setImage(img)
        self.status.emit("Copied the image")
