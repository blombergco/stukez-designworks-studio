"""Project cards for the Projects grid: one picture per project, drawn on a background thread.

The window thread never draws a card. A card that is not ready yet shows a plain placeholder, and the picture arrives a moment
later. Cards are queued in the background as soon as the page is shown, the cards on screen first, so a scroll never waits for
a card to be drawn. Memory is limited to a share of the computer's RAM, so a small PC keeps working too."""
import collections
import threading
from collections import OrderedDict

from PySide6.QtCore import QObject, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QStyle, QStyledItemDelegate

from . import render
from . import theme as th

CARD_SIZE = QSize(308, 236)
CARD_MAX_SCALE = 1.25    # card pictures are kept at most at this scale (a 200 % screen gets them 1.25x, not 2x: 40 % less memory)


def card_memory_budget():
    """Memory for card pictures: 3 % of the computer's RAM, between 32 and 128 MB, so a small PC is not starved."""
    total = 4 * 1024 ** 3                       # when the RAM cannot be read, assume 4 GB
    try:
        import ctypes

        class MemoryStatus(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong), ("total_phys", ctypes.c_ulonglong),
                        ("avail_phys", ctypes.c_ulonglong), ("total_page", ctypes.c_ulonglong), ("avail_page", ctypes.c_ulonglong),
                        ("total_virtual", ctypes.c_ulonglong), ("avail_virtual", ctypes.c_ulonglong), ("avail_ext", ctypes.c_ulonglong)]
        st = MemoryStatus()
        st.length = ctypes.sizeof(MemoryStatus)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st)):
            total = st.total_phys
    except Exception:       # not Windows, or no ctypes: keep the default
        pass
    mb = total / (1024 * 1024) * 0.03
    return int(min(128, max(32, mb)) * 1024 * 1024)


def picture_scale(dpr):
    """The resolution a card picture is kept at: the screen's, but no more than CARD_MAX_SCALE."""
    return min(dpr, CARD_MAX_SCALE)


def preview_state():
    """Everything outside the project that changes how a card looks: the preview car, its zones and the board's logos."""
    car, layout = render.PREVIEW_CAR, render.LAYOUT
    car_key = None if car is None else (car.id, repr(car.data))
    layout_key = None if layout is None else (id(layout), repr(layout.items))
    return car_key, layout_key


def draw_card_image(p, w, h, scale):
    """The plain card (no selection, no hover) as an image. Runs on the background thread: it touches no widget."""
    img = QImage(round(w * scale), round(h * scale), QImage.Format_ARGB32_Premultiplied)
    img.setDevicePixelRatio(scale)
    img.fill(Qt.transparent)
    cp = QPainter(img)
    rect = QRectF(0, 0, w, h).adjusted(6, 6, -6, -6)
    sub = (", ".join(p.moods[:3]) or "no moods") + (f"  ·  {p.platform}" if p.platform else "")
    render.draw_card(cp, rect, p, p.name, sub, number=f"{p.id:03d}", plates=False)
    cp.end()
    return img


class _Worker(QObject):
    """One background thread that draws queued cards. Urgent jobs (cards on screen) go before the rest."""
    done = Signal(object, object, object)   # project id, state, image

    def __init__(self):
        super().__init__()
        self._jobs = collections.deque()    # (project id, project, state, w, h, scale)
        self._cond = threading.Condition()
        self._failed = set()                # states that could not be drawn: not tried again
        threading.Thread(target=self._run, name="card-pictures", daemon=True).start()

    def submit(self, job, urgent):
        pid = job[0]
        with self._cond:
            queued = any(j[0] == pid for j in self._jobs)
            if queued and not urgent:
                return
            rest = [j for j in self._jobs if j[0] != pid]
            if urgent:
                self._jobs = collections.deque([job] + rest)
            else:
                self._jobs = collections.deque(rest + [job])
            self._cond.notify()

    def cancel_all(self):
        with self._cond:
            self._jobs.clear()

    def _run(self):
        while True:
            with self._cond:
                while not self._jobs:
                    self._cond.wait()
                pid, p, state, w, h, scale = self._jobs.popleft()
            if state in self._failed:
                continue
            try:
                img = draw_card_image(p, w, h, scale)
            except Exception:     # one broken project must not stop the others
                self._failed.add(state)
                continue
            self.done.emit(pid, state, img)


class CardDelegate(QStyledItemDelegate):
    """Paints the project cards from one picture per project. Pictures come from the background thread."""
    SIZE = CARD_SIZE
    more = Signal()         # pictures arrived: the view should repaint soon

    def __init__(self):
        super().__init__()
        self._cards = OrderedDict()     # project id -> (state, picture)
        self._bytes = 0
        self.budget = card_memory_budget()
        self._gen = 0                   # the theme generation: a new theme makes every picture stale
        self._pending = {}              # project id -> the state it is being drawn for
        self._asked = False
        self._worker = _Worker()
        self._worker.done.connect(self._received)
        th.on_change(self._theme_changed)

    def sizeHint(self, option, index):
        return self.SIZE

    def _theme_changed(self):
        self._gen += 1
        self._cards.clear()
        self._bytes = 0
        self._pending.clear()
        self._worker.cancel_all()

    def _state(self, p, w, h, dpr):
        return (repr(p), w, h, dpr, self._gen, preview_state())    # the project is a dataclass: its repr holds every field

    def _store(self, pid, state, pic):
        old = self._cards.pop(pid, None)
        if old is not None:
            self._bytes -= old[1].width() * old[1].height() * 4
        self._cards[pid] = (state, pic)
        self._bytes += pic.width() * pic.height() * 4
        while self._bytes > self.budget and len(self._cards) > 1:
            _, (_, gone) = self._cards.popitem(last=False)
            self._bytes -= gone.width() * gone.height() * 4

    def _received(self, pid, state, img):
        if state[4] != self._gen:       # drawn for a theme that is gone
            return
        if self._pending.get(pid) == state:
            del self._pending[pid]
        pic = QPixmap.fromImage(img)
        pic.setDevicePixelRatio(img.devicePixelRatio())
        self._store(pid, state, pic)
        self._ask()

    def request(self, p, state, urgent=False):
        self._pending[p.id] = state
        self._worker.submit((p.id, p, state, state[1], state[2], picture_scale(state[3])), urgent)

    def warm(self, projects, w, h, dpr):
        """Queue every card that is not ready yet, in list order, as far as the memory budget has room for."""
        scale = picture_scale(dpr)
        one = round(w * scale) * round(h * scale) * 4
        room = max(0, (self.budget - self._bytes) // one)
        for p in projects:
            if room <= 0:
                break
            state = self._state(p, w, h, dpr)
            hit = self._cards.get(p.id)
            if (hit is not None and hit[0] == state) or self._pending.get(p.id) == state:
                continue
            self.request(p, state)
            room -= 1

    def build_now(self, projects, w, h, dpr, progress=None):
        """Draw every card that is not ready, on this thread, and wait for it. Used at start-up while the splash shows: the window
        then opens with all its cards, and nothing competes with the window thread afterwards. `progress(done, total)` is optional."""
        scale = picture_scale(dpr)
        one = round(w * scale) * round(h * scale) * 4
        total = len(projects)
        for i, p in enumerate(projects, 1):
            state = self._state(p, w, h, dpr)
            hit = self._cards.get(p.id)
            if not (hit is not None and hit[0] == state):
                if self._bytes + one > self.budget:
                    break
                img = draw_card_image(p, w, h, scale)
                pic = QPixmap.fromImage(img)
                pic.setDevicePixelRatio(img.devicePixelRatio())
                self._store(p.id, state, pic)
            if progress is not None:
                progress(i, total)

    def _placeholder(self, painter, rect, hover):
        r = QRectF(rect).adjusted(6, 6, -6, -6)
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillPath(render.chamfer_path(r, 20), QColor(th.TILE_HOT) if hover else render.PANEL)
        painter.restore()

    def _ask(self):
        if not self._asked:
            self._asked = True
            QTimer.singleShot(16, self._emit_more)

    def _emit_more(self):
        self._asked = False
        self.more.emit()

    def _overlay(self, painter, rect, selected, hover):
        """Selection and hover are drawn on top of the cached card: a pointer moving over the grid then costs no redraw."""
        if not (selected or hover):
            return
        r = QRectF(rect).adjusted(6, 6, -6, -6)
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        if selected:
            painter.fillPath(render.chamfer_path(r, 20), th.accent(34))
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(render.RED, 2.5))
            painter.drawPath(render.chamfer_path(r.adjusted(1.2, 1.2, -1.2, -1.2), 20))
        else:
            painter.fillPath(render.chamfer_path(r, 20), th.accent(22))
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(th.accent(120), 1))
            painter.drawPath(render.chamfer_path(r.adjusted(.5, .5, -.5, -.5), 20))
            render.slash_edges(painter, r.adjusted(.5, .5, -.5, -.5), 20, th.accent(230), 1.6)
        painter.restore()

    def paint(self, painter, option, index):
        p = index.data(Qt.UserRole)
        selected = bool(option.state & QStyle.State_Selected)
        hover = bool(option.state & QStyle.State_MouseOver)
        dpr = painter.device().devicePixelRatioF()
        w, h = option.rect.width(), option.rect.height()
        state = self._state(p, w, h, dpr)
        hit = self._cards.get(p.id)
        if hit is not None and hit[0] == state:
            self._cards.move_to_end(p.id)
            painter.save()
            painter.setRenderHint(QPainter.SmoothPixmapTransform)    # a picture kept below the screen's scale is smoothed up
            painter.drawPixmap(option.rect.topLeft(), hit[1])
            painter.restore()
        else:
            self.request(p, state, urgent=True)     # the window thread only ever shows a placeholder
            self._placeholder(painter, option.rect, hover)
        self._overlay(painter, option.rect, selected, hover)
