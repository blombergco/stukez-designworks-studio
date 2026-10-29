"""Workshop > Gradients: design a two-colour gradient and its cut, see it on the car, keep favourites, export swatches."""
import random
from types import SimpleNamespace

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QFileDialog, QGridLayout, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QMenu, QScrollArea,
                               QSlider, QVBoxLayout, QWidget)

from . import gradients as gr
from . import palette as pal
from . import render
from .page_generator import ColourButton
from .theme import head_font
from .widgets import StudioButton, button, copy_text, label

OUTLINE = "#0C0A14"


def slider_row(text, lo, hi, value, suffix, on_change):
    """A labelled slider with its value to the right: returns (widget, slider)."""
    s = QSlider(Qt.Horizontal)
    s.setRange(lo, hi)
    s.setValue(value)
    val = label("", "muted")
    val.setFixedWidth(64)
    val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

    def moved(v):
        val.setText(f"{v}{suffix}")
        on_change()
    s.valueChanged.connect(moved)
    val.setText(f"{value}{suffix}")
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    name = label(text)
    name.setFixedWidth(78)
    lay.addWidget(name)
    lay.addWidget(s, 1)
    lay.addWidget(val)
    return w, s


class Tile(QWidget):
    """A clickable colour tile with a name (a suggestion for the second colour)."""
    clicked = Signal()

    def __init__(self, text):
        super().__init__()
        self.text, self.hex, self._hover = text, "#808080", False
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover)
        self.setMinimumSize(96, 62)

    def set_hex(self, h):
        self.hex = h
        self.setToolTip(f"{self.text}: {h}")
        self.update()

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def mousePressEvent(self, e):
        self.clicked.emit()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        if self._hover:
            r.translate(0, -2)
        sw = QRectF(r.x(), r.y(), r.width(), r.height() - 22)
        p.setPen(QPen(QColor(255, 255, 255, 90 if self._hover else 45), 1))
        p.setBrush(QColor(self.hex))
        p.drawPath(render.chamfer_path(sw, 9))
        render.slash_edges(p, sw, 9, QColor(255, 255, 255, 110 if self._hover else 60), 1.4)
        p.setFont(head_font(14))
        p.setPen(QColor("#f5f0f1"))
        p.drawText(QRectF(r.x(), sw.bottom() + 2, r.width(), 18), Qt.AlignLeft | Qt.AlignVCenter,
                   p.fontMetrics().elidedText(self.text, Qt.ElideRight, int(r.width())))


class CarStage(QWidget):
    """The gradient on the preview car, on the garage floor."""

    def __init__(self):
        super().__init__()
        self.pal = None
        self.setMinimumHeight(260)

    def set_palette(self, ns):
        self.pal = ns
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        render.draw_stage(p, r, cut=22)
        if self.pal is not None:
            render.draw_car(p, r.adjusted(18, 14, -18, -8), self.pal)


class Strip(QWidget):
    """The gradient as a bar, with its hex codes."""

    def __init__(self):
        super().__init__()
        self.a, self.b = "#1E1B2E", "#6E8B1F"
        self.setFixedHeight(66)

    def set_colours(self, a, b):
        self.a, self.b = a, b
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(0, 0, self.width(), 38).adjusted(.5, .5, -.5, -.5)
        g = QLinearGradient(r.topLeft(), r.topRight())
        g.setColorAt(0, QColor(self.a))
        g.setColorAt(1, QColor(self.b))
        p.setPen(QPen(QColor(255, 255, 255, 50), 1))
        p.setBrush(g)
        p.drawPath(render.chamfer_path(r, 12))
        render.slash_edges(p, r, 12, QColor(255, 255, 255, 70), 1.5)
        p.setFont(head_font(15))
        p.setPen(QColor("#f5f0f1"))
        p.drawText(QRectF(0, 44, self.width() / 2, 20), Qt.AlignLeft, self.a)
        p.drawText(QRectF(self.width() / 2, 44, self.width() / 2, 20), Qt.AlignRight, self.b)


def swatch_icon(a, b, w=150, h=30):
    pm = QPixmap(w, h)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    g = QLinearGradient(0, 0, w, 0)
    g.setColorAt(0, QColor(a))
    g.setColorAt(1, QColor(b))
    p.setPen(QPen(QColor(255, 255, 255, 60), 1))
    p.setBrush(g)
    p.drawPath(render.chamfer_path(QRectF(.5, .5, w - 1, h - 1), 9))
    p.end()
    return QIcon(pm)


class GradientsTab(QWidget):
    status = Signal(str)
    sendToProject = Signal(str, object)    # palette slot key, [a, b]

    def __init__(self, vault):
        super().__init__()
        self.vault = vault
        self.favs = gr.Favourites(vault)
        self._busy = False
        self.rng = random.Random()

        # --- colours
        self.name = QLineEdit(placeholderText="Name for the favourites, e.g. Plum to Lime")
        self.b_a, self.b_b = ColourButton("#1E1B2E"), ColourButton("#6E8B1F")
        self.e_a, self.e_b = QLineEdit("#1E1B2E", maxLength=7), QLineEdit("#6E8B1F", maxLength=7)
        for e in (self.e_a, self.e_b):
            e.setFixedWidth(90)
        for b, e in ((self.b_a, self.e_a), (self.b_b, self.e_b)):
            b.changed.connect(lambda b=b, e=e: (e.setText(b.hex()), self._changed()))
            e.editingFinished.connect(lambda b=b, e=e: self._typed(b, e))
        swap = button("Swap", slot=self.swap)
        row_a = QHBoxLayout()
        row_a.addWidget(label("Rear colour", "h2"), 1)
        row_a.addWidget(self.b_a)
        row_a.addWidget(self.e_a)
        row_b = QHBoxLayout()
        row_b.addWidget(label("Front colour", "h2"), 1)
        row_b.addWidget(self.b_b)
        row_b.addWidget(self.e_b)

        # --- suggestions
        self.tiles = []
        grid = QGridLayout()
        grid.setSpacing(8)
        for i, name in enumerate(("Analogous", "Complement", "Split complement", "Triad", "Lighter", "Darker", "Same hue, other energy")):
            t = Tile(name)
            t.clicked.connect(lambda t=t: self._pick_front(t.hex))
            self.tiles.append(t)
            grid.addWidget(t, i // 3, i % 3)
        rnd = button("New random pair", slot=self.random_pair)
        grid.addWidget(rnd, 2, 1, 1, 2)

        # --- the cut
        w_angle, self.s_angle = slider_row("Angle", -90, 90, 45, "°", self._changed)
        w_pos, self.s_pos = slider_row("Centre", 10, 90, 50, " %", self._changed)
        w_span, self.s_span = slider_row("Covers", 10, 100, 50, " %", self._changed)
        presets = QHBoxLayout()
        for text, ang, pos, span in (("Studio cut 45°", 45, 50, 50), ("Straight", 0, 50, 40), ("Steep", 70, 50, 60), ("Rising −45°", -45, 50, 50)):
            presets.addWidget(button(text, slot=lambda _=False, a=ang, p=pos, s=span: self.set_cut(a, p, s)))

        # --- actions
        self.save_btn = button("Save to favourites", True, self.save)
        acts = QHBoxLayout()
        acts.addWidget(button("Copy hex", slot=self.copy_hex))
        acts.addWidget(button("Export .ase swatches", slot=self.export_ase))
        acts.addStretch()

        form = QVBoxLayout()
        form.setContentsMargins(0, 0, 12, 0)
        form.addWidget(self.name)
        form.addLayout(row_a)
        form.addLayout(row_b)
        form.addWidget(swap, 0, Qt.AlignLeft)
        form.addWidget(label("Suggestions for the front colour", "h2"))
        form.addLayout(grid)
        form.addWidget(label("The cut", "h2"))
        form.addWidget(w_angle)
        form.addWidget(w_pos)
        form.addWidget(w_span)
        form.addLayout(presets)
        form.addSpacing(6)
        form.addWidget(self.save_btn)
        form.addLayout(acts)
        form.addStretch()
        host = QWidget()
        host.setObjectName("page")
        host.setLayout(form)
        scroll = QScrollArea()
        scroll.setWidget(host)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setFixedWidth(470)

        # --- preview and favourites
        self.stage = CarStage()
        self.strip = Strip()
        self.note = label("", "muted", wrap=True)
        self.list = QListWidget()
        self.list.setViewMode(QListWidget.IconMode)
        self.list.setIconSize(QSize(150, 30))
        self.list.setResizeMode(QListWidget.Adjust)
        self.list.setMovement(QListWidget.Static)
        self.list.setSpacing(6)
        self.list.setFixedHeight(150)
        self.list.itemClicked.connect(self._load_item)
        use = StudioButton("Use in New project ▾")
        use.setToolTip("Send the two colours to a slot of the New project page")
        menu = QMenu(use)
        for key, text in (("base", "Base"), ("tribal", "Tribals"), ("sponsor_a", "Sponsor A"), ("sponsor_b", "Sponsor B")):
            menu.addAction(text, lambda k=key: self.sendToProject.emit(k, [self.a(), self.b()]))
        use.setMenu(menu)
        fav_actions = QHBoxLayout()
        fav_actions.addWidget(use)
        fav_actions.addWidget(button("Delete favourite", slot=self.delete))
        fav_actions.addStretch()
        right = QVBoxLayout()
        right.setContentsMargins(6, 0, 0, 0)
        right.addWidget(label("On the car", "h2"))
        right.addWidget(self.stage, 1)
        right.addWidget(self.strip)
        right.addWidget(self.note)
        right.addWidget(label("Favourites", "h2"))
        right.addWidget(self.list)
        right.addLayout(fav_actions)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 8, 0, 0)
        lay.addWidget(scroll)
        lay.addLayout(right, 1)
        self.reload()
        self._changed()

    # ------------------------------------------------------------------ state
    def a(self):
        return self.b_a.hex()

    def b(self):
        return self.b_b.hex()

    def gradient(self):
        return gr.Gradient(self.name.text().strip() or f"{self.a()} to {self.b()}", self.a(), self.b(), float(self.s_angle.value()),
                           self.s_pos.value() / 100, self.s_span.value() / 100)

    def _typed(self, b, e):
        h = pal.valid_hex(e.text())
        if h:
            b.set_hex(h)
            e.setText(h)
            self._changed()
        else:
            e.setText(b.hex())

    def _pick_front(self, h):
        self.b_b.set_hex(h)
        self.e_b.setText(h)
        self._changed()

    def swap(self):
        a, b = self.a(), self.b()
        for btn, ed, v in ((self.b_a, self.e_a, b), (self.b_b, self.e_b, a)):
            btn.set_hex(v)
            ed.setText(v)
        self._changed()

    def random_pair(self):
        a, b = gr.random_pair((), self.rng)
        self.set_colours(a, b)

    def set_colours(self, a, b):
        for btn, ed, v in ((self.b_a, self.e_a, a), (self.b_b, self.e_b, b)):
            btn.set_hex(v)
            ed.setText(v)
        self._changed()

    def set_cut(self, angle, pos, span):
        self._busy = True
        self.s_angle.setValue(int(angle))
        self.s_pos.setValue(int(pos))
        self.s_span.setValue(int(span))
        self._busy = False
        self._changed()

    def _changed(self):
        if self._busy:
            return
        g = self.gradient()
        ns = SimpleNamespace(base=g.a, tribal=g.b, tribal_outline=OUTLINE, sponsor_a="#F5F0F1", sponsor_a_outline=OUTLINE,
                             sponsor_b="#F5F0F1", sponsor_b_outline=OUTLINE, no_plates=True,
                             cut_angle=g.angle, cut_pos=g.pos, cut_span=g.span)
        self.stage.set_palette(ns)
        self.strip.set_colours(g.a, g.b)
        for t, (_n, h) in zip(self.tiles, gr.suggestions(g.a)):
            t.set_hex(h)
        notes = gr.check(g)
        standard = (g.angle, g.pos, g.span) == (gr.STANDARD["angle"], gr.STANDARD["pos"], gr.STANDARD["span"])
        self.note.setText(" ".join(notes) if notes else
                          ("The studio cut: 45°, centred on the door, over half the car." if standard else
                           f"Cut {g.angle:g}°, centred at {g.pos * 100:.0f} % and covering {g.span * 100:.0f} % of the car."))

    # ------------------------------------------------------------------ favourites and export
    def reload(self):
        self.list.clear()
        for g in self.favs.load():
            it = QListWidgetItem(swatch_icon(g.a, g.b), g.name)
            it.setData(Qt.UserRole, g)
            it.setToolTip(f"{g.hex_line()}   {g.angle:g}°")
            self.list.addItem(it)

    def _load_item(self, it):
        g = it.data(Qt.UserRole)
        self.name.setText(g.name)
        self._busy = True
        self.s_angle.setValue(int(g.angle))
        self.s_pos.setValue(round(g.pos * 100))
        self.s_span.setValue(round(g.span * 100))
        self._busy = False
        self.set_colours(g.a, g.b)

    def save(self):
        g = self.gradient()
        if gr.check(g) and any("valid" in n for n in gr.check(g)):
            return
        self.favs.add(g)
        self.reload()
        self.status.emit(f"Saved gradient “{g.name}” in Project Library/Gradients")

    def delete(self):
        it = self.list.currentItem()
        if it:
            self.favs.remove(it.data(Qt.UserRole).name)
            self.reload()
            self.status.emit("Deleted the favourite")

    def copy_hex(self):
        g = self.gradient()
        copy_text(f"{g.a} → {g.b}  ({g.angle:g}°, centre {g.pos * 100:.0f} %, covers {g.span * 100:.0f} %)")
        self.status.emit("Copied the gradient")

    def export_ase(self):
        items = self.favs.load()
        cur = self.gradient()
        if not any(x.name == cur.name for x in items):
            items.append(cur)
        start = self.vault.lib / "Swatches" / "Gradients.ase"
        path, _ = QFileDialog.getSaveFileName(self, "Export swatches", str(start), "Adobe Swatch Exchange (*.ase)")
        if path:
            gr.write_ase(items, path)
            self.status.emit(f"Exported {len(items)} gradients to {path}")
