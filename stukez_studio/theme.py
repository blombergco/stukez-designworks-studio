"""The look of the app: three themes, set in DIN (Bahnschrift) and cut at 45 degrees.

The 45 degree cut is the one idea: it is the same cut the livery gets on the car, and it returns in the buttons, cards,
colour tiles, the navigation rail and the headings. Everything else stays quiet. The colours come from a theme
(`apply("red")`, "blue" or "carbon"): the module level names below (RED, PANEL, ...) always hold the colours of the theme in
use, so code that draws reads them as `theme.RED` at paint time and follows a theme change.
"""
# ruff: noqa: F821  (the colour names are set by apply() at import time)
import os
import tempfile
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFontDatabase, QImage, QPainter, QPalette, QPen, QPolygon, QPolygonF, QRegion
from PySide6.QtWidgets import QComboBox, QLineEdit, QWidget

# ---------------------------------------------------------------------- the themes
# accent = the signal colour, hi/dark = its light and deep shades, ember = the light edge of an accent surface, acc = its rgb for
# the transparent washes, on_accent = the text on an accent surface, bg* = the window, panel* = cards and inputs
THEMES = {
    "red": dict(
        label="Red and black", blurb="Tyre black with signal red: the studio's own look.",
        bg="#080506", bg_mid="#12070a", bg_end="#34091a", bg_deep="#050304", panel="#130a0d", panel_hi="#1c1115", raised="#26151a",
        border="#33161c", border_hi="#5e1d28", accent="#ff2e3f", accent_hi="#ff5a68", accent_dark="#a80f20", ember="#ff7a86",
        select="#7a1521", acc=(255, 46, 63), on_accent="#ffffff", ink="#f5f0f1", muted="#a8999c", disabled="#6f5d61",
        btn_top="#2b161b", btn_bot="#170b0f", btn_top_hot="#3a1a21", btn_bot_hot="#22090e", primary_end="#b3001b",
        primary_end_hot="#d4122a", off_top="#3a171d", off_bot="#2a1014", input_bg="rgba(19, 10, 13, 0.94)",
        input_focus="rgba(28, 13, 17, 0.97)", header_bg="#0e0709", header_line="#1d0c10", grid="#20100f", alt="#180d10",
        tile_hot="#1b0f13", stage_top="#2c1318", stage_bot="#0d0608", rail_mid="#0d0507", rail_end="#2a060c", mark_dark="#1a0b0f",
        th_bg="#2a1216", code_bg="#2a1216", code_fg="#ffd0a8", pre_bg="#100a0c", texture=False, nav_alpha=150),
    "blue": dict(
        label="Blue and black", blurb="Deep blue-black with electric blue and white accents.",
        bg="#04070d", bg_mid="#08101e", bg_end="#10224a", bg_deep="#03050a", panel="#0a1220", panel_hi="#111c30", raised="#18253d",
        border="#1b2a45", border_hi="#2f4b78", accent="#3d8bff", accent_hi="#7db3ff", accent_dark="#1b55b8", ember="#9cc3ff",
        select="#173a73", acc=(61, 139, 255), on_accent="#ffffff", ink="#f1f5ff", muted="#93a4c0", disabled="#566580",
        btn_top="#172640", btn_bot="#0c1424", btn_top_hot="#1f3355", btn_bot_hot="#101c33", primary_end="#1d5fd1",
        primary_end_hot="#2f78f0", off_top="#16233a", off_bot="#0f1a2c", input_bg="rgba(10, 18, 32, 0.94)",
        input_focus="rgba(15, 26, 46, 0.97)", header_bg="#070d18", header_line="#122038", grid="#101c30", alt="#0d1626",
        tile_hot="#0f1a2e", stage_top="#13213a", stage_bot="#050911", rail_mid="#060b15", rail_end="#0c2350", mark_dark="#0a1424",
        th_bg="#13213a", code_bg="#13213a", code_fg="#bcd6ff", pre_bg="#080e19", texture=False, nav_alpha=150),
    "carbon": dict(
        label="Carbon and yellow", blurb="Carbon-fibre grey with racing yellow and light accents.",
        bg="#0d0e10", bg_mid="#131417", bg_end="#1b1d21", bg_deep="#08090a", panel="#17181b", panel_hi="#202226", raised="#2a2c31",
        border="#32353b", border_hi="#575c66", accent="#ffd21f", accent_hi="#ffe566", accent_dark="#b38f00", ember="#fff0a0",
        select="#524612", acc=(255, 210, 31), on_accent="#15130a", ink="#f2f3f5", muted="#a4a8b0", disabled="#6c7079",
        btn_top="#2b2d32", btn_bot="#1a1b1e", btn_top_hot="#383b41", btn_bot_hot="#222428", primary_end="#d9ac00",
        primary_end_hot="#f0c400", off_top="#2a2c31", off_bot="#1f2023", input_bg="rgba(23, 24, 27, 0.94)",
        input_focus="rgba(32, 34, 38, 0.97)", header_bg="#0c0d0f", header_line="#232529", grid="#222428", alt="#1a1b1e",
        tile_hot="#1d1e22", stage_top="#2a2c31", stage_bot="#0c0d0f", rail_mid="#0b0c0e", rail_end="#26282d", mark_dark="#2e3036",
        th_bg="#26282d", code_bg="#26282d", code_fg="#ffe9a0", pre_bg="#0e0f11", texture=True, nav_alpha=84),
}
DEFAULT_THEME = "red"
ANIMATE = not os.environ.get("KAIZEN_NOANIM")     # the small animations (livery sweep, page fade, logo shine)
CURRENT = DEFAULT_THEME
_hooks = []     # called after a theme is applied, so modules with colours of their own can refresh them


def apply(key):
    """Make `key` the theme in use: every colour name of this module takes its value. Returns the key actually applied."""
    global CURRENT
    key = key if key in THEMES else DEFAULT_THEME
    t = THEMES[key]
    CURRENT = key
    g = globals()
    for name in ("bg", "bg_mid", "bg_end", "bg_deep", "panel", "panel_hi", "raised", "border", "border_hi", "accent", "accent_hi",
                 "accent_dark", "ember", "select", "on_accent", "ink", "muted", "disabled", "btn_top", "btn_bot", "btn_top_hot",
                 "btn_bot_hot", "primary_end", "primary_end_hot", "off_top", "off_bot", "input_bg", "input_focus", "header_bg",
                 "header_line", "grid", "alt", "tile_hot", "stage_top", "stage_bot", "rail_mid", "rail_end", "mark_dark",
                 "th_bg", "code_bg", "code_fg", "pre_bg", "texture", "nav_alpha"):
        g[name.upper()] = t[name]
    g["ACC"] = t["acc"]
    g["ACC_CSS"] = ", ".join(str(v) for v in t["acc"])
    g["RED"], g["RED_HI"], g["RED_DARK"] = t["accent"], t["accent_hi"], t["accent_dark"]      # the old names for the accent
    g["ACCENT"] = t["accent"]
    g["SELECT"] = t["select"]
    g["NOTE_CSS"] = note_css()
    for fn in _hooks:
        fn()
    return key


def on_change(fn):
    _hooks.append(fn)


def qpalette():
    """The application palette in the colours of the theme: dialogs and message boxes that the style sheet does not paint follow it."""
    pal = QPalette()
    for role, col in ((QPalette.Window, BG), (QPalette.WindowText, INK), (QPalette.Base, PANEL), (QPalette.AlternateBase, ALT),
                      (QPalette.Text, INK), (QPalette.Button, BTN_TOP), (QPalette.ButtonText, INK), (QPalette.ToolTipBase, PANEL),
                      (QPalette.ToolTipText, INK), (QPalette.Highlight, SELECT), (QPalette.HighlightedText, "#ffffff"),
                      (QPalette.PlaceholderText, MUTED), (QPalette.Link, RED_HI)):
        pal.setColor(role, QColor(col))
    pal.setColor(QPalette.Disabled, QPalette.Text, QColor(DISABLED))
    pal.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(DISABLED))
    return pal


def alpha(colour, a):
    """A colour (hex) as a QColor with an alpha."""
    c = QColor(colour)
    c.setAlpha(a)
    return c


def accent(alpha=255):
    """The accent as a QColor with an alpha."""
    return QColor(ACC[0], ACC[1], ACC[2], alpha)


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
    """The few bitmaps a stylesheet needs (tick, chevron, carbon weave); drawn here and written to a cache folder."""
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
        p.setPen(QPen(QColor(ON_ACCENT), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPolyline(QPolygonF([QPointF(3.5, 8.3), QPointF(6.6, 11.4), QPointF(12.6, 4.6)]))

    def chevron(color, points):
        def draw(p):
            p.setPen(QPen(QColor(color), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPolyline(QPolygonF([QPointF(x, y) for x, y in points]))
        return draw

    down = ((2, 4), (6, 8), (10, 4))
    right = ((4, 2), (8, 6), (4, 10))
    out = dict(tick=make(f"tick_{CURRENT}.png", 16, tick),
               chev=make("chev.png", 12, chevron("#d9c7ca", down)),
               right=make("chev_right.png", 12, chevron("#d9c7ca", right)))
    if TEXTURE:
        out["weave"] = _weave(folder)
    return out


def _weave(folder):
    """A 16 x 16 tile of 2 x 2 twill carbon fibre, light and dark strands on transparent, laid over the window colour."""
    img = QImage(16, 16, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    for y in range(16):
        for x in range(16):
            cx, cy = (x // 4) % 2, (y // 4) % 2
            u, v = (x % 4) / 3.0, (y % 4) / 3.0
            horizontal = (cx + cy) % 2 == 0
            t = v if horizontal else u
            shade = 1 - abs(t - .5) * 2            # a strand is lit along its middle
            alpha = int(10 + 34 * shade) if horizontal else int(3 + 20 * shade)
            img.setPixelColor(x, y, QColor(255, 255, 255, alpha))
    path = folder / "weave.png"
    img.save(str(path))
    return path.as_posix()


def build_qss():
    ic = _icons()
    window = (f"background-color: {BG}; background-image: url({ic['weave']});" if TEXTURE else
              f"background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {BG}, stop:0.58 {BG_MID}, stop:1 {BG_END});")
    A = ACC_CSS
    return f"""
* {{ font-family: {FONT}; font-size: 14px; color: {INK}; }}
QMainWindow, QDialog {{ {window} }}
QMainWindow > QWidget {{ background: transparent; }}
QWidget#page {{ background: transparent; }}
QToolButton#nav {{ background: transparent; border: none; }}

/* ------------------------------------------------------------ type */
QLabel#h1 {{ font-family: {HEAD}; font-size: 31px; color: #ffffff; padding-left: 30px; }}
QLabel#h2 {{ font-family: {HEAD}; font-size: 18px; color: #ffffff; }}
QLabel#muted {{ color: {MUTED}; }}
QLabel#badge {{ background: rgba({A}, 0.14); border: none; border-left: 3px solid {RED}; border-radius: 1px;
                padding: 2px 10px 2px 8px; color: #ffffff; font-size: 12px; font-weight: 600; }}

/* ------------------------------------------------------------ inputs */
QLineEdit, QPlainTextEdit, QComboBox, QSpinBox, QTextBrowser, QListView, QTreeWidget, QTableWidget, QListWidget {{
    background: {INPUT_BG}; border: 1px solid {BORDER}; border-bottom: 2px solid {BORDER_HI}; border-radius: 0;
    padding: 6px 10px; selection-background-color: {SELECT}; selection-color: #ffffff; }}
QLineEdit:hover, QComboBox:hover {{ border-color: {BORDER_HI}; }}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{ border: 1px solid {RED_DARK}; border-bottom: 2px solid {RED}; background: {INPUT_FOCUS}; }}
QLineEdit[placeholderText]:disabled {{ color: {DISABLED}; }}
QListView, QTreeWidget, QTableWidget, QListWidget {{ padding: 4px; outline: 0; }}
QComboBox {{ padding-right: 28px; }}
QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: center right; border: none; background: transparent; width: 28px; }}
QComboBox::down-arrow {{ image: url({ic['chev']}); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{ background: {PANEL}; border: 1px solid {BORDER_HI}; padding: 4px; outline: 0;
                               selection-background-color: {SELECT}; }}

/* ------------------------------------------------------------ buttons (the Studio buttons draw their own cut shape) */
QPushButton {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {BTN_TOP}, stop:1 {BTN_BOT}); border: 1px solid {BORDER_HI};
               border-radius: 3px; padding: 7px 16px; font-weight: 700; }}
QPushButton:hover {{ border: 1px solid {RED}; }}
QPushButton:pressed {{ background: {RED_DARK}; }}
QPushButton[studio="true"] {{ background: transparent; border: none; border-radius: 0; padding: 8px 20px; font-family: {HEAD};
                              font-size: 15px; font-weight: 400; min-height: 18px; }}
QPushButton[studio="true"]#primary {{ padding: 9px 34px 9px 22px; }}
QPushButton[studio="true"]#mood {{ padding: 5px 4px; font-size: 14px; min-height: 16px; }}
QPushButton:disabled {{ color: {DISABLED}; }}
QPushButton::menu-indicator {{ width: 0; }}

/* ------------------------------------------------------------ tabs */
QTabWidget::pane {{ border: none; border-top: 1px solid {BORDER}; top: -1px; }}
QTabBar {{ background: transparent; }}
QTabBar::tab {{ background: transparent; padding: 9px 20px 8px 20px; color: {MUTED}; border-bottom: 3px solid transparent;
                font-family: {HEAD}; font-size: 16px; margin-right: 2px; }}
QTabBar::tab:hover {{ color: #ffffff; background: rgba({A}, 0.08); }}
QTabBar::tab:selected {{ color: #ffffff; border-bottom: 3px solid {RED};
                         background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba({A}, 0.0), stop:1 rgba({A}, 0.18)); }}

/* ------------------------------------------------------------ tables and lists */
QHeaderView {{ background: transparent; }}
QHeaderView::section {{ background: {HEADER_BG}; border: none; border-bottom: 2px solid {BORDER_HI}; border-right: 1px solid {HEADER_LINE};
                        padding: 7px 10px; color: {MUTED}; font-family: {HEAD}; font-size: 15px; }}
QTableWidget {{ gridline-color: {GRID}; alternate-background-color: {ALT}; }}
QTableWidget::item {{ padding: 3px 6px; }}
QTableWidget::item:selected, QTableWidget::item:selected:!active, QTreeWidget::item:selected {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba({A}, 0.46), stop:1 rgba({A}, 0.12)); color: #ffffff; }}
QListWidget::item {{ padding: 7px 10px; border-left: 3px solid transparent; margin: 1px 0; }}
QListWidget::item:hover {{ background: rgba({A}, 0.10); }}
QListWidget::item:selected, QListWidget::item:selected:!active {{ border-left: 3px solid {RED}; color: #ffffff;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba({A}, 0.40), stop:1 rgba({A}, 0.05)); }}

/* ------------------------------------------------------------ scrolling */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {BORDER_HI}; border-radius: 3px; min-height: 36px; }}
QScrollBar::handle:vertical:hover, QScrollBar::handle:vertical:pressed {{ background: {RED}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {BORDER_HI}; border-radius: 3px; min-width: 36px; }}
QScrollBar::handle:horizontal:hover, QScrollBar::handle:horizontal:pressed {{ background: {RED}; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ width: 0; height: 0; background: transparent; }}
QSplitter::handle {{ background: transparent; width: 6px; }}
QSplitter::handle:hover {{ background: rgba({A}, 0.35); }}

/* ------------------------------------------------------------ chrome */
QStatusBar {{ background: {BG_DEEP}; color: {MUTED}; border-top: 1px solid {BORDER}; }}
QStatusBar::item {{ border: none; }}
QMenuBar {{ background: {BG_DEEP}; border-bottom: 1px solid {BORDER}; padding: 2px 4px; }}
QMenuBar::item {{ padding: 5px 12px; background: transparent; }}
QMenuBar::item:selected {{ background: {SELECT}; }}
QMenu {{ background: {PANEL}; border: 1px solid {BORDER_HI}; padding: 5px; }}
QMenu::item {{ padding: 7px 26px 7px 16px; border-left: 3px solid transparent; }}
QMenu::item:selected {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba({A}, 0.50), stop:1 rgba({A}, 0.10));
                        border-left: 3px solid {RED}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 8px; }}
QToolTip {{ background: {PANEL}; color: {INK}; border: 1px solid {RED}; padding: 5px 8px; }}

/* ------------------------------------------------------------ checkboxes: an accent plate with a tick */
QCheckBox {{ spacing: 9px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {BORDER_HI}; border-radius: 3px; background: {PANEL}; }}
QCheckBox::indicator:hover {{ border: 1px solid {RED}; }}
QCheckBox::indicator:checked {{ image: url({ic['tick']}); border: 1px solid {EMBER};
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {RED}, stop:1 {PRIMARY_END}); }}
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


def note_css():
    """The style sheet of the rendered notes (How to, guides, project notes) in the colours of the theme in use."""
    return f"""
body {{ color: {INK}; font-family: {BODY_FAMILY}; font-size: 15px; }}
h1 {{ font-family: {HEAD_FAMILY}; font-size: 28px; color: #ffffff; }}
h2 {{ font-family: {HEAD_FAMILY}; font-size: 21px; color: {RED_HI}; }}
h3 {{ font-family: {HEAD_FAMILY}; font-size: 17px; color: #ffffff; }}
a {{ color: {RED_HI}; text-decoration: none; }}
table {{ border-collapse: collapse; }}
th {{ background: {TH_BG}; padding: 6px 10px; text-align: left; font-family: {HEAD_FAMILY}; }}
td {{ padding: 6px 10px; border-top: 1px solid {BORDER}; }}
code {{ background: {CODE_BG}; color: {CODE_FG}; }}
pre {{ background: {PRE_BG}; color: #e8dcdf; padding: 10px; white-space: pre-wrap; }}
blockquote {{ color: {MUTED}; }}
"""


apply(DEFAULT_THEME)
