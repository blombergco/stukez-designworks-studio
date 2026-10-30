"""The look of the app: tyre black, signal red and paper white, set in DIN (Bahnschrift) and cut at 45 degrees.

The 45 degree cut is the one idea: it is the same cut the livery gets on the car, and it returns in the buttons, cards,
colour tiles, the navigation rail and the headings. Everything else stays quiet.
"""
import tempfile
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFontDatabase, QImage, QPainter, QPen, QPolygon, QPolygonF, QRegion
from PySide6.QtWidgets import QComboBox, QLineEdit, QWidget

BG = "#080506"          # tyre black (a hair of red)
BG_DEEP = "#050304"     # rail, menu and status bar
PANEL = "#130a0d"       # cards, inputs, tables
PANEL_HI = "#1c1115"
RAISED = "#26151a"
BORDER = "#33161c"
BORDER_HI = "#5e1d28"
RED = "#ff2e3f"
RED_HI = "#ff5a68"
RED_DARK = "#a80f20"
EMBER = "#ff7a86"       # the light edge of a red surface
SELECT = "#7a1521"
INK = "#f5f0f1"         # paper white
MUTED = "#a8999c"       # chalk
ACCENT = RED

# DIN: the type of number plates and road signs. One family; the width carries the hierarchy.
FONT = '"Bahnschrift", "Segoe UI"'
HEAD = '"Bahnschrift SemiBold Condensed", "Bahnschrift SemiBold", "Segoe UI Semibold"'
HEAD_FAMILY = "Bahnschrift SemiBold Condensed"
BODY_FAMILY = "Bahnschrift"


def head_font(px, fallback_bold=True):
    """The condensed headline face at a pixel size (falls back to bold Segoe UI when Bahnschrift is missing)."""
    from PySide6.QtGui import QFont
    f = QFont(HEAD_FAMILY if HEAD_FAMILY in QFontDatabase.families() else "Segoe UI")
    f.setPixelSize(px)
    if HEAD_FAMILY not in QFontDatabase.families():
        f.setBold(fallback_bold)
    return f


def body_font(px, bold=False):
    from PySide6.QtGui import QFont
    f = QFont(BODY_FAMILY if BODY_FAMILY in QFontDatabase.families() else "Segoe UI")
    f.setPixelSize(px)
    f.setBold(bold)
    return f


def _icons():
    """The few bitmaps a stylesheet needs (tick, chevron); drawn here and written to a cache folder."""
    folder = Path(tempfile.gettempdir()) / "stukez_studio_ui"
    folder.mkdir(exist_ok=True)

    def make(name, size, draw):
        s = 4   # drawn at 4x and let Qt scale down: smooth edges on any display
        img = QImage(size * s, size * s, QImage.Format_ARGB32)
        img.fill(Qt.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.Antialiasing)
        p.scale(s, s)
        draw(p)
        p.end()
        path = folder / name
        img.save(str(path))
        return path.as_posix()

    def tick(p):
        p.setPen(QPen(QColor("#ffffff"), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPolyline(QPolygonF([QPointF(3.5, 8.3), QPointF(6.6, 11.4), QPointF(12.6, 4.6)]))

    def chevron(color, points):
        def draw(p):
            p.setPen(QPen(QColor(color), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPolyline(QPolygonF([QPointF(x, y) for x, y in points]))
        return draw

    down = ((2, 4), (6, 8), (10, 4))
    right = ((4, 2), (8, 6), (4, 10))
    return dict(tick=make("tick.png", 16, tick),
                chev=make("chev.png", 12, chevron("#d9c7ca", down)),
                right=make("chev_right.png", 12, chevron("#d9c7ca", right)))


def build_qss():
    ic = _icons()
    return f"""
* {{ font-family: {FONT}; font-size: 14px; color: {INK}; }}
QMainWindow, QDialog {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {BG}, stop:0.58 #12070a, stop:1 #34091a); }}
QMainWindow > QWidget {{ background: transparent; }}
QWidget#page {{ background: transparent; }}
QToolButton#nav {{ background: transparent; border: none; }}

/* ------------------------------------------------------------ type */
QLabel#h1 {{ font-family: {HEAD}; font-size: 31px; color: #ffffff; padding-left: 30px; }}
QLabel#h2 {{ font-family: {HEAD}; font-size: 18px; color: #ffffff; }}
QLabel#muted {{ color: {MUTED}; }}
QLabel#badge {{ background: rgba(255, 46, 63, 0.14); border: none; border-left: 3px solid {RED}; border-radius: 1px;
                padding: 2px 10px 2px 8px; color: #ffffff; font-size: 12px; font-weight: 600; }}

/* ------------------------------------------------------------ inputs */
QLineEdit, QPlainTextEdit, QComboBox, QSpinBox, QTextBrowser, QListView, QTreeWidget, QTableWidget, QListWidget {{
    background: rgba(19, 10, 13, 0.94); border: 1px solid {BORDER}; border-bottom: 2px solid {BORDER_HI}; border-radius: 0;
    padding: 6px 10px; selection-background-color: {SELECT}; selection-color: #ffffff; }}
QLineEdit:hover, QComboBox:hover {{ border-color: {BORDER_HI}; }}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{ border: 1px solid {RED_DARK}; border-bottom: 2px solid {RED}; background: rgba(28, 13, 17, 0.97); }}
QLineEdit[placeholderText]:disabled {{ color: #6f5d61; }}
QListView, QTreeWidget, QTableWidget, QListWidget {{ padding: 4px; outline: 0; }}
QComboBox {{ padding-right: 28px; }}
QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: center right; border: none; background: transparent; width: 28px; }}
QComboBox::down-arrow {{ image: url({ic['chev']}); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{ background: {PANEL}; border: 1px solid {BORDER_HI}; padding: 4px; outline: 0;
                               selection-background-color: {SELECT}; }}

/* ------------------------------------------------------------ buttons (the Studio buttons draw their own cut shape) */
QPushButton {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2b161b, stop:1 #170b0f); border: 1px solid {BORDER_HI};
               border-radius: 3px; padding: 7px 16px; font-weight: 700; }}
QPushButton:hover {{ border: 1px solid {RED}; }}
QPushButton:pressed {{ background: {RED_DARK}; }}
QPushButton[studio="true"] {{ background: transparent; border: none; border-radius: 0; padding: 8px 20px; font-family: {HEAD};
                              font-size: 15px; font-weight: 400; min-height: 18px; }}
QPushButton[studio="true"]#primary {{ padding: 9px 34px 9px 22px; }}
QPushButton[studio="true"]#mood {{ padding: 5px 4px; font-size: 14px; min-height: 16px; }}
QPushButton:disabled {{ color: #6f5d61; }}
QPushButton::menu-indicator {{ width: 0; }}

/* ------------------------------------------------------------ tabs */
QTabWidget::pane {{ border: none; border-top: 1px solid {BORDER}; top: -1px; }}
QTabBar {{ background: transparent; }}
QTabBar::tab {{ background: transparent; padding: 9px 20px 8px 20px; color: {MUTED}; border-bottom: 3px solid transparent;
                font-family: {HEAD}; font-size: 16px; margin-right: 2px; }}
QTabBar::tab:hover {{ color: #ffffff; background: rgba(255, 46, 63, 0.08); }}
QTabBar::tab:selected {{ color: #ffffff; border-bottom: 3px solid {RED};
                         background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(255, 46, 63, 0.0), stop:1 rgba(255, 46, 63, 0.18)); }}

/* ------------------------------------------------------------ tables and lists */
QHeaderView {{ background: transparent; }}
QHeaderView::section {{ background: #0e0709; border: none; border-bottom: 2px solid {BORDER_HI}; border-right: 1px solid #1d0c10;
                        padding: 7px 10px; color: {MUTED}; font-family: {HEAD}; font-size: 15px; }}
QTableWidget {{ gridline-color: #20100f; alternate-background-color: #180d10; }}
QTableWidget::item {{ padding: 3px 6px; }}
QTableWidget::item:selected, QTableWidget::item:selected:!active, QTreeWidget::item:selected {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(255, 46, 63, 0.46), stop:1 rgba(255, 46, 63, 0.12)); color: #ffffff; }}
QListWidget::item {{ padding: 7px 10px; border-left: 3px solid transparent; margin: 1px 0; }}
QListWidget::item:hover {{ background: rgba(255, 46, 63, 0.10); }}
QListWidget::item:selected, QListWidget::item:selected:!active {{ border-left: 3px solid {RED}; color: #ffffff;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(255, 46, 63, 0.40), stop:1 rgba(255, 46, 63, 0.05)); }}

/* ------------------------------------------------------------ scrolling */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {BORDER_HI}; border-radius: 3px; min-height: 36px; }}
QScrollBar::handle:vertical:hover, QScrollBar::handle:vertical:pressed {{ background: {RED}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {BORDER_HI}; border-radius: 3px; min-width: 36px; }}
QScrollBar::handle:horizontal:hover, QScrollBar::handle:horizontal:pressed {{ background: {RED}; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ width: 0; height: 0; background: transparent; }}
QSplitter::handle {{ background: transparent; width: 6px; }}
QSplitter::handle:hover {{ background: rgba(255, 46, 63, 0.35); }}

/* ------------------------------------------------------------ chrome */
QStatusBar {{ background: {BG_DEEP}; color: {MUTED}; border-top: 1px solid {BORDER}; }}
QStatusBar::item {{ border: none; }}
QMenuBar {{ background: {BG_DEEP}; border-bottom: 1px solid {BORDER}; padding: 2px 4px; }}
QMenuBar::item {{ padding: 5px 12px; background: transparent; }}
QMenuBar::item:selected {{ background: {SELECT}; }}
QMenu {{ background: {PANEL}; border: 1px solid {BORDER_HI}; padding: 5px; }}
QMenu::item {{ padding: 7px 26px 7px 16px; border-left: 3px solid transparent; }}
QMenu::item:selected {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(255, 46, 63, 0.50), stop:1 rgba(255, 46, 63, 0.10));
                        border-left: 3px solid {RED}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 8px; }}
QToolTip {{ background: {PANEL}; color: {INK}; border: 1px solid {RED}; padding: 5px 8px; }}

/* ------------------------------------------------------------ checkboxes: a red plate with a white tick */
QCheckBox {{ spacing: 9px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {BORDER_HI}; border-radius: 3px; background: {PANEL}; }}
QCheckBox::indicator:hover {{ border: 1px solid {RED}; }}
QCheckBox::indicator:checked {{ image: url({ic['tick']}); border: 1px solid {EMBER};
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {RED}, stop:1 #b3001b); }}
QSlider::groove:horizontal {{ height: 4px; background: {BORDER_HI}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {RED_DARK}, stop:1 {RED}); border-radius: 2px; }}
QSlider::handle:horizontal {{ background: #ffffff; border: 2px solid {RED}; width: 12px; height: 12px; margin: -7px 0; border-radius: 8px; }}
QSlider::handle:horizontal:hover {{ background: {EMBER}; }}
QProgressBar {{ border: 1px solid {BORDER_HI}; border-radius: 3px; background: {PANEL}; text-align: center; min-height: 16px; }}
QProgressBar::chunk {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {RED_DARK}, stop:1 {RED}); border-radius: 2px; }}
QScrollArea {{ background: transparent; border: none; }}

/* tree: the open and closed chevrons are the cut-plate arrows, the category rows read as headings */
QTreeWidget::branch {{ background: transparent; }}
QTreeWidget::branch:has-children:!has-siblings:closed, QTreeWidget::branch:closed:has-children:has-siblings {{ image: url({ic['right']}); }}
QTreeWidget::branch:open:has-children:!has-siblings, QTreeWidget::branch:open:has-children:has-siblings {{ image: url({ic['chev']}); }}
QTreeWidget::item {{ padding: 4px 4px; }}
"""


class _CutEdges(QWidget):
    """The two cut edges of an input, drawn over it: a stylesheet cannot draw a 45 degree corner."""

    def __init__(self, host):
        super().__init__(host)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, _e):
        from . import render   # render imports this module, so the import waits until a widget paints
        host = self.parent()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        col = QColor(RED) if host.hasFocus() else QColor(BORDER_HI if host.underMouse() else BORDER)
        render.slash_edges(p, QRectF(self.rect()).adjusted(.5, .5, -.5, -.5), host.property("cutSize"), col, 1.4)
        p.end()


class CutFrames(QObject):
    """Cuts the top right and bottom left corners of every line edit and combo box, like the Studio buttons.

    Each input gets a mask (the corners are clipped away) and a transparent child that draws the two cut edges on top.
    A line edit inside an editable combo box is left alone: the combo box itself is cut.
    """

    def eventFilter(self, obj, e):
        if not isinstance(obj, (QLineEdit, QComboBox)) or (isinstance(obj, QLineEdit) and isinstance(obj.parent(), QComboBox)):
            return False
        t = e.type()
        if t == QEvent.Polish and obj.property("cutSize") is None:
            obj.setProperty("cutSize", 0.0)
            _CutEdges(obj)
        elif t == QEvent.Resize and obj.property("cutSize") is not None:
            w, h = obj.width(), obj.height()
            c = round(min(h * .3, 9.0))
            obj.setProperty("cutSize", float(c))
            obj.setMask(QRegion(QPolygon([QPoint(0, 0), QPoint(w - c, 0), QPoint(w, c), QPoint(w, h), QPoint(c, h), QPoint(0, h - c)])))
            edges = obj.findChild(_CutEdges)
            edges.setGeometry(obj.rect())
            edges.raise_()
        elif t in (QEvent.FocusIn, QEvent.FocusOut, QEvent.Enter, QEvent.Leave) and obj.property("cutSize") is not None:
            obj.findChild(_CutEdges).update()
        return False


def install_cut_frames(app):
    """Call once after the stylesheet is set: every line edit and combo box in the program gets the cut."""
    cut = CutFrames(app)
    app.installEventFilter(cut)
    return cut


NOTE_CSS = f"""
body {{ color: {INK}; font-family: {BODY_FAMILY}; font-size: 15px; }}
h1 {{ font-family: {HEAD_FAMILY}; font-size: 28px; color: #ffffff; }}
h2 {{ font-family: {HEAD_FAMILY}; font-size: 21px; color: {RED_HI}; }}
h3 {{ font-family: {HEAD_FAMILY}; font-size: 17px; color: #ffffff; }}
a {{ color: {RED_HI}; text-decoration: none; }}
table {{ border-collapse: collapse; }}
th {{ background: #2a1216; padding: 6px 10px; text-align: left; font-family: {HEAD_FAMILY}; }}
td {{ padding: 6px 10px; border-top: 1px solid {BORDER}; }}
code {{ background: #2a1216; color: #ffd0a8; }}
pre {{ background: #100a0c; color: #e8dcdf; padding: 10px; white-space: pre-wrap; }}
blockquote {{ color: {MUTED}; }}
"""

