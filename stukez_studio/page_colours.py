"""Workshop > Sponsors and outlines: change the colour or the gradient of the sponsors and of every outline, on the car."""
from types import SimpleNamespace

from PySide6.QtCore import QRectF, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from . import outlines as ol
from . import palette as pal
from . import render
from .page_generator import SlotRow
from .widgets import ChipGrid, PaintSwitch, button, copy_text, label

EDITABLE = (("sponsor_a", "Sponsor A"), ("sponsor_a_outline", "Sponsor A outline"), ("sponsor_b", "Sponsor B"),
            ("sponsor_b_outline", "Sponsor B outline"), ("tribal_outline", "Tribal outline"))
PAIRS = (("sponsor_a", "sponsor_a_outline"), ("sponsor_b", "sponsor_b_outline"))
PLATE_SCALE = .9      # the sponsor plates are drawn nearly as big as their zones here, so the outline can be judged


class Stage(QWidget):
    """The car on the garage floor with big sponsor plates."""

    def __init__(self):
        super().__init__()
        self.pal = None
        self.setMinimumHeight(270)

    def set_palette(self, ns):
        self.pal = ns
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        render.draw_stage(p, r, cut=22)
        if self.pal is not None:
            render.draw_car(p, r.adjusted(18, 14, -18, -8), self.pal, plate_scale=PLATE_SCALE, layout=False)


def mean_hex(v):
    """The colour in the middle of a solid colour or a gradient."""
    cs = v if isinstance(v, list) else [v]
    rgb = [pal.hex_to_rgb(c) for c in cs]
    return pal.rgb_to_hex(*(sum(c[i] for c in rgb) / len(rgb) for i in range(3)))


class ColoursTab(QWidget):
    status = Signal(str)
    sendPalette = Signal(object)            # {slot key: hex or [a, b]} for the five slots of this tab

    def __init__(self, vault, palette_source=None):
        super().__init__()
        self.vault = vault
        self.palette_source = palette_source      # () -> dict of the New project page
        self.fixed = {}                           # base and tribal of the palette we started from: shown, not edited here
        self._busy = False

        self.source = QComboBox()
        self.source.addItem("Start from the New project page", None)
        for p in vault.projects():
            self.source.addItem(f"Start from {p.id:03d}  {p.name}", p)
        self.source.activated.connect(self._load)
        self.rows = {}
        rows = QVBoxLayout()
        for key, text in EDITABLE:
            r = SlotRow(key, text, True)
            r.lock.setVisible(False)
            r.changed.connect(self._changed)
            self.rows[key] = r
            rows.addWidget(r)

        form = QVBoxLayout()
        form.setContentsMargins(0, 0, 12, 0)
        form.addWidget(label("Every slot is a solid colour or a 2-colour gradient: tick the gradient box to switch.", "muted", wrap=True))
        form.addWidget(self.source)
        form.addLayout(rows)
        form.addWidget(label("Quick fixes", "h2"))
        quick = QHBoxLayout()
        quick.addWidget(button("Outlines for contrast", slot=self.auto_outlines))
        quick.addWidget(button("Swap A and B", slot=self.swap))
        quick.addStretch()
        form.addLayout(quick)
        solid = QHBoxLayout()
        solid.addWidget(button("All solid", slot=self.make_solid))
        solid.addWidget(button("Sponsors as gradients", slot=self.sponsors_gradient))
        solid.addStretch()
        form.addLayout(solid)
        form.addStretch()
        host = QWidget()
        host.setObjectName("page")
        host.setLayout(form)
        scroll = QScrollArea()
        scroll.setWidget(host)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll.setFixedWidth(470)

        self.stage = Stage()
        self.paint = PaintSwitch()
        self.chips = ChipGrid()
        self.chips.copied.connect(lambda n: self.status.emit(f"Copied {n}"))
        self.note = label("", "muted", wrap=True)
        acts = QHBoxLayout()
        acts.addWidget(button("Use in New project", True, self.send))
        acts.addWidget(button("Copy hex list", slot=self.copy_hex))
        acts.addStretch()
        right = QVBoxLayout()
        right.setContentsMargins(6, 0, 0, 0)
        right.addWidget(label("On the car", "h2"))
        right.addWidget(self.paint)
        right.addWidget(self.stage, 1)
        right.addWidget(self.chips)
        right.addWidget(self.note)
        right.addLayout(acts)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 8, 0, 0)
        lay.addWidget(scroll)
        lay.addLayout(right, 1)
        self._load(0)

    # ------------------------------------------------------------------ state
    def values(self):
        d = dict(self.fixed)
        d.update({k: r.value() for k, r in self.rows.items()})
        return d

    def _load(self, i):
        src = self.source.itemData(i)
        if src is None:
            d = dict(self.palette_source()) if self.palette_source else {}
        else:
            d = {k: (list(v) if isinstance(v, (list, tuple)) else v) for k, v in
                 ((k, getattr(src, k)) for k in ("base", "tribal", "tribal_outline", "sponsor_a", "sponsor_a_outline",
                                                 "sponsor_b", "sponsor_b_outline"))}
        if not d:
            d = dict(base="#1E1B2E", tribal="#6E8B1F", tribal_outline=ol.DEFAULT_OUTLINE, sponsor_a="#F5F0F1",
                     sponsor_a_outline=ol.DEFAULT_OUTLINE, sponsor_b="#F5F0F1", sponsor_b_outline=ol.DEFAULT_OUTLINE)
        self.fixed = {k: d[k] for k in ("base", "tribal")}
        self._busy = True
        for k, r in self.rows.items():
            r.set_value(d[k])
        self._busy = False
        self._changed()

    def _changed(self):
        if self._busy:
            return
        d = self.values()
        self.stage.set_palette(SimpleNamespace(**d))
        self.chips.set_palette(d)
        problems = pal.check_rules(d)
        low = min(pal.contrast(c, o) for fill, line in PAIRS for c in _cl(d[fill]) for o in _cl(d[line]))
        if problems:
            self.note.setText("⚠ " + "; ".join(problems))
        elif low < 2.0:
            self.note.setText(f"The weakest fill against its outline is {low:.1f}:1, so a logo may be hard to read. "
                              "Try “Outlines for contrast”.")
        else:
            self.note.setText("Fills and outlines read well against each other.")

    def _set(self, key, value):
        self.rows[key].set_value(value)

    # ------------------------------------------------------------------ quick fixes
    def auto_outlines(self):
        """A dark or a light outline for each fill, whichever stands out more."""
        dark, light = ol.DEFAULT_OUTLINE, "#F5F0F1"
        d = self.values()
        self._busy = True
        for fill, line in (("sponsor_a", "sponsor_a_outline"), ("sponsor_b", "sponsor_b_outline"), ("tribal", "tribal_outline")):
            mean = mean_hex(d[fill])
            self.rows[line].set_value(dark if pal.contrast(mean, dark) >= pal.contrast(mean, light) else light)
        self._busy = False
        self._changed()

    def swap(self):
        d = self.values()
        self._busy = True
        for a, b in (("sponsor_a", "sponsor_b"), ("sponsor_a_outline", "sponsor_b_outline")):
            self.rows[a].set_value(d[b])
            self.rows[b].set_value(d[a])
        self._busy = False
        self._changed()

    def make_solid(self):
        """Every editable slot as one solid colour (its first colour)."""
        self._busy = True
        for r in self.rows.values():
            v = r.value()
            r.set_value(v[0] if isinstance(v, list) else v)
        self._busy = False
        self._changed()

    def sponsors_gradient(self):
        """A solid sponsor colour becomes a gradient to a lighter shade of itself."""
        self._busy = True
        for k in ("sponsor_a", "sponsor_b"):
            v = self.rows[k].value()
            if not isinstance(v, list):
                h, s, l = pal.hex_hsl(v)
                self.rows[k].set_value([v, pal.hsl_hex(h + 18, min(1, s + .05), min(.9, l + .16))])
        self._busy = False
        self._changed()

    # ------------------------------------------------------------------ output
    def send(self):
        d = self.values()
        self.sendPalette.emit({key: d[key] for key, _text in EDITABLE})

    def copy_hex(self):
        d = self.values()
        copy_text("\n".join(f"{t}: " + " → ".join(_cl(d[k])) for k, t in EDITABLE))
        self.status.emit("Copied the hex codes")


def _cl(v):
    return v if isinstance(v, list) else [v]
