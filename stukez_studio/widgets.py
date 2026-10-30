"""Shared widgets: the cut buttons and headings, note viewer, colour tiles, preview stage and progress helper."""
from PySide6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QDesktopServices, QGuiApplication, QLinearGradient, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (QApplication, QButtonGroup, QHBoxLayout, QLabel, QMessageBox, QProgressDialog, QPushButton, QVBoxLayout,
                               QSizePolicy, QTextBrowser, QWidget)

from . import render
from .render import chamfer_path

from .theme import ACCENT, BORDER, EMBER, INK, MUTED, NOTE_CSS, RED, RED_DARK, RED_HI  # noqa: F401


def copy_text(text):
    QGuiApplication.clipboard().setText(text)


class Heading(QLabel):
    """A page heading with the slash marks of the livery in front of it."""

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        h = self.height()
        t = min(h * .62, 26.0)
        y0 = (h - t) / 2
        p.setPen(Qt.NoPen)
        for x, w, col in ((2, 7, QColor(RED)), (13, 3.5, QColor("#ffffff"))):
            poly = QPolygonF([QPointF(x + t * .42, y0), QPointF(x + t * .42 + w, y0), QPointF(x + w, y0 + t), QPointF(x, y0 + t)])
            p.setBrush(col)
            p.drawPolygon(poly)
        p.end()
        super().paintEvent(e)


def label(text, name="", wrap=False):
    w = Heading(text) if name == "h1" else QLabel(text)
    if name:
        w.setObjectName(name)
    w.setWordWrap(wrap)
    return w


class StudioButton(QPushButton):
    """A button cut at 45 degrees (top right and bottom left), like the slash on the livery.

    Three looks by object name: plain (dark glass, red edge on hover), "primary" (red with two racing stripes) and
    "mood" (a compact toggle). Pointing at a button sweeps one light stripe across it; pressing it sinks one pixel.
    """

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setProperty("studio", True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.TabFocus)
        self.setAttribute(Qt.WA_Hover)
        self._hover = False
        self._keys = False   # focus ring only for keyboard users
        self._sweep = 1.0
        self._anim = QVariantAnimation(self, startValue=0.0, endValue=1.0, duration=520)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._set_sweep)

    def focusInEvent(self, e):
        self._keys = e.reason() in (Qt.TabFocusReason, Qt.BacktabFocusReason, Qt.ShortcutFocusReason)
        super().focusInEvent(e)

    def focusOutEvent(self, e):
        self._keys = False
        super().focusOutEvent(e)

    def _set_sweep(self, v):
        self._sweep = v
        self.update()

    def enterEvent(self, e):
        self._hover = True
        if self.isEnabled():
            self._anim.stop()
            self._anim.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self.update()
        super().leaveEvent(e)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        kind = self.objectName()
        on = self.isEnabled()
        hot = self._hover and on
        down = self.isDown() and on
        lit = kind == "primary" or (kind == "mood" and self.isChecked())
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        if down:
            r.translate(0, 1)
        c = min(r.height() * .34, 11.0)
        path = chamfer_path(r, c)
        # surface
        if lit:
            g = QLinearGradient(r.topLeft(), r.topRight())
            g.setColorAt(0, QColor(RED_HI if hot else RED))
            g.setColorAt(1, QColor("#d4122a" if hot else "#b3001b"))
            if not on:
                g.setColorAt(0, QColor("#3a171d"))
                g.setColorAt(1, QColor("#2a1014"))
        else:
            g = QLinearGradient(r.topLeft(), r.bottomLeft())
            g.setColorAt(0, QColor("#3a1a21" if hot else "#2b161b"))
            g.setColorAt(1, QColor("#22090e" if hot else "#170b0f"))
        if down:
            g = QColor(RED_DARK)
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawPath(path)
        p.save()
        p.setClipPath(path)
        if lit and on:
            # two racing stripes near the cut edge, and a light edge along the top
            p.setBrush(QColor(255, 255, 255, 70))
            for x, w in ((r.right() - 22, 3.0), (r.right() - 14, 7.0)):
                p.setBrush(QColor(255, 255, 255, 120 if w < 4 else 34))
                p.drawPolygon(QPolygonF([QPointF(x + r.height() * .5, r.top()), QPointF(x + r.height() * .5 + w, r.top()),
                                         QPointF(x + w, r.bottom()), QPointF(x, r.bottom())]))
            p.setPen(QPen(QColor(255, 255, 255, 80), 1))
            p.drawLine(QPointF(r.left() + c, r.top() + .5), QPointF(r.right() - c, r.top() + .5))
        if hot and self._sweep < 1.0:
            # one stripe of light sweeping left to right
            x = r.left() - r.height() + (r.width() + r.height() * 2) * self._sweep
            sheen = QLinearGradient(x, 0, x + r.height() * .9, 0)
            sheen.setColorAt(0, QColor(255, 255, 255, 0))
            sheen.setColorAt(.5, QColor(255, 255, 255, 70))
            sheen.setColorAt(1, QColor(255, 255, 255, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(sheen)
            p.drawPolygon(QPolygonF([QPointF(x + r.height(), r.top()), QPointF(x + r.height() * 1.9, r.top()),
                                     QPointF(x + r.height() * .9, r.bottom()), QPointF(x, r.bottom())]))
        p.restore()
        # edge
        p.setBrush(Qt.NoBrush)
        edge = QColor(EMBER) if lit else (QColor(RED) if hot or self.isChecked() else QColor("#5e1d28"))
        if not on:
            edge = QColor("#33161c")
        p.setPen(QPen(edge, 1))
        p.drawPath(path)
        if not lit and on:
            render.slash_edges(p, r, c, QColor(255, 46, 63, 255 if hot else 150), 1.5)
        if self.hasFocus() and self._keys:
            p.setPen(QPen(QColor("#ffffff"), 1.5, Qt.DashLine))
            p.drawPath(chamfer_path(r.adjusted(-1.5, -1.5, 1.5, 1.5), c))
        # text
        p.setFont(self.font())
        p.setPen(QColor("#ffffff") if on else QColor("#6f5d61"))
        pad_r = 14 if kind == "primary" else 0
        p.drawText(r.adjusted(0, 0, -pad_r, 0), Qt.AlignCenter, self.text())
        p.end()


def button(text, primary=False, slot=None):
    b = StudioButton(text)
    if primary:
        b.setObjectName("primary")
    if slot:
        b.clicked.connect(slot)
    return b


class PaintSwitch(QWidget):
    """Gradient or solid colour: how the car is painted in every preview. One state for the whole program (see MainWindow)."""
    changed = Signal(str)       # "" = the gradient (the livery cut), "base" or "tribal" = one solid colour
    MODES = (("Gradient", "", "The livery as designed: the base colour fades into the tribal colour over the car"),
             ("Solid base", "base", "The whole car in one flat colour: the base colour (the first one, if the base is a gradient)"),
             ("Solid tribals", "tribal", "The whole car in one flat colour: the tribal colour (the first one, if it is a gradient)"))

    def __init__(self, mode=""):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lay.addWidget(label("Car paint", "muted"))
        self.group = QButtonGroup(self)
        self.buttons = {}
        for text, key, tip in self.MODES:
            b = StudioButton(text)
            b.setObjectName("mood")
            b.setCheckable(True)
            b.setToolTip(tip)
            self.group.addButton(b)
            self.buttons[key] = b
            b.clicked.connect(lambda _=False, k=key: self.changed.emit(k))
            lay.addWidget(b)
        lay.addStretch()
        self.set_mode(mode)

    def set_mode(self, mode):
        self.buttons.get(mode, self.buttons[""]).setChecked(True)


class NoteView(QTextBrowser):
    """Renders vault notes; wikilinks come out as noteRequested(name)."""
    noteRequested = Signal(str)

    def __init__(self, vault):
        super().__init__()
        self.vault = vault
        self.setOpenLinks(False)
        self.document().setDefaultStyleSheet(NOTE_CSS)
        self.anchorClicked.connect(self._clicked)
        self.history = []

    def show_note(self, path, remember=True):
        if path is None or not path.exists():
            self.setHtml("<p style='color:#a8999c'>Not generated for this project yet.</p>")
            return
        if remember:
            self.history.append(path)
        self.setHtml(self.vault.note_html(path))
        self.verticalScrollBar().setValue(0)

    def back(self):
        if len(self.history) > 1:
            self.history.pop()
            self.show_note(self.history[-1], remember=False)

    def _clicked(self, url):
        if url.scheme() == "note":
            self.noteRequested.emit(url.path() if url.path() else url.toString()[5:])
        elif url.scheme() in ("http", "https"):
            QDesktopServices.openUrl(url)


class Chip(QWidget):
    """One colour: swatch, label and hex; click copies the hex code."""
    copied = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.label, self.value = "", "#000000"
        self._hover = False
        self.setAttribute(Qt.WA_Hover)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumSize(96, 86)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def set(self, label_, value):
        self.label, self.value = label_, value
        vals = value if isinstance(value, (list, tuple)) else [value]
        self.setToolTip("Click to copy " + " → ".join(vals))
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(0, 0, self.width(), 48).adjusted(.5, .5, -.5, -.5)
        if self._hover:
            r.translate(0, -2)
        shape = chamfer_path(r, 12)
        p.setPen(QPen(QColor(255, 255, 255, 90 if self._hover else 50), 1))
        p.setBrush(render.brush(r, self.value))
        p.drawPath(shape)
        render.slash_edges(p, r, 12, QColor(255, 255, 255, 110 if self._hover else 60), 1.5)
        p.setPen(QColor(INK))
        f = p.font()
        f.setFamily("Bahnschrift SemiBold Condensed")
        f.setPixelSize(15)
        p.setFont(f)
        p.drawText(QRectF(0, 53, self.width(), 18), Qt.AlignLeft, p.fontMetrics().elidedText(self.label, Qt.ElideRight, self.width()))
        f.setFamily("Bahnschrift")
        f.setPixelSize(12)
        p.setFont(f)
        p.setPen(QColor(MUTED))
        vals = self.value if isinstance(self.value, (list, tuple)) else [self.value]
        p.drawText(QRectF(0, 70, self.width(), 16), Qt.AlignLeft, " → ".join(v[1:] for v in vals) if len(vals) > 1 else vals[0])

    def enterEvent(self, e):
        self._hover = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self.update()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        vals = self.value if isinstance(self.value, (list, tuple)) else [self.value]
        copy_text(" → ".join(vals) if len(vals) > 1 else vals[0])
        self.copied.emit(self.label)


class ChipGrid(QWidget):
    """The seven colours of a palette."""
    copied = Signal(str)

    def __init__(self):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        self.chips = [Chip() for _ in range(7)]
        for c in self.chips:
            c.copied.connect(self.copied)
            lay.addWidget(c)

    def set_palette(self, d):
        d = render.pal_of(d)
        slots = [("Base", d.base), ("Tribals", d.tribal), ("Tribal outline", d.tribal_outline),
                 ("Sponsor A", d.sponsor_a), ("Sponsor A outline", d.sponsor_a_outline),
                 ("Sponsor B", d.sponsor_b), ("Sponsor B outline", d.sponsor_b_outline)]
        for chip, (lbl, v) in zip(self.chips, slots):
            chip.set(lbl, v)


class LiveryPreview(QWidget):
    def __init__(self, min_h=230, plates=True):
        super().__init__()
        self.pal = None
        self.plates = plates      # the sponsor plates on the car; the Projects page shows the bare car
        self.setMinimumHeight(min_h)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_palette(self, d):
        self.pal = d
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        render.draw_stage(p, r, cut=22)
        if self.pal is not None:
            render.draw_car(p, r.adjusted(18, 14, -18, -8), self.pal, plates=self.plates)


def run_build(parent, vault, pid, only_missing=True):
    """Build the generated notes of a project behind a progress dialog; returns the builder's result or None on error."""
    steps = vault.builder().STEPS
    dlg = QProgressDialog("Starting…", None, 0, len(steps), parent)
    dlg.setWindowTitle("Building project")
    dlg.setWindowModality(Qt.WindowModal)
    dlg.setMinimumDuration(0)
    dlg.setValue(0)

    def progress(i, step):
        dlg.setLabelText(f"{step}…")
        dlg.setValue(i)
        QApplication.processEvents()
    try:
        res = vault.builder().build_all(pid, progress, only_missing)
    except Exception as e:   # the note itself is already saved; say what failed instead of crashing
        dlg.close()
        QMessageBox.warning(parent, "Build failed", f"{type(e).__name__}: {e}")
        return None
    dlg.close()
    vault._stems = None
    return res


def pill(text):
    w = label(text, "badge")
    w.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    return w


class _Mark(QWidget):
    """The livery mark from the rail: three slanted bars, dark, red and white."""

    def __init__(self):
        super().__init__()
        self.setFixedSize(54, 36)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        for i, col in enumerate(("#2a1419", RED, "#ffffff")):
            x = 2 + i * 16
            p.setBrush(QColor(col))
            p.drawPolygon(QPolygonF([QPointF(x + 6, 0), QPointF(x + 13, 0), QPointF(x + 7, 36), QPointF(x, 36)]))
        p.end()


class EmptyState(QWidget):
    """A quiet cut panel for a list or view with nothing in it yet: the livery mark, a headline and one line of help."""

    def __init__(self, title, text, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(8)
        head = label(title, "h2")
        head.setAlignment(Qt.AlignCenter)
        note = label(text, "muted", wrap=True)
        note.setAlignment(Qt.AlignCenter)
        note.setMaximumWidth(420)
        lay.addWidget(_Mark(), 0, Qt.AlignHCenter)
        lay.addWidget(head)
        lay.addWidget(note, 0, Qt.AlignHCenter)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(.5, .5, -.5, -.5)
        p.setPen(QPen(QColor(BORDER), 1))
        p.setBrush(QColor(19, 10, 13, 120))
        p.drawPath(chamfer_path(r, 18))
        render.slash_edges(p, r, 18, QColor(RED), 2)
        p.end()
