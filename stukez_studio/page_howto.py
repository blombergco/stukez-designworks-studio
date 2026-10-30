"""How to: a short, plain explanation of how the program works, one topic at a time. Links like page:1 jump to a page."""
import markdown
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QListWidget, QTextBrowser, QVBoxLayout, QWidget

from .theme import NOTE_CSS
from .widgets import label

# (title, markdown). Page numbers for page:N links follow the order of main.PAGES: 0 Projects, 1 New project, 2 Cars,
# 3 Prompts, 4 Sponsors, 5 Guides, 6 Workshop, 7 How to.
TOPICS = [
    ("Start here", """
# Start here

StukeZ Designworks Studio turns a colour idea into a livery plan. You pick the colours, see them on a real car, and the
program writes everything down as notes in your workspace folder, so nothing is locked inside the program.

## The route from idea to livery

| Step | What you do | Where |
|---|---|---|
| 1 | Make a palette: let the generator suggest one, or set the seven colours by hand. | [New project](page:1) |
| 2 | Look at it on a car. Switch the car, and switch between gradient and solid paint. | Any preview |
| 3 | Fine-tune the sponsor and outline colours, build a gradient, outline a logo. | [Workshop](page:6) |
| 4 | Save. The program writes the project note, the swatches, a detail kit, a build sheet and a placement preview. | [New project](page:1) |
| 5 | Open the project, check the real sponsor logos on your car, export for Illustrator or Substance Painter. | [Projects](page:0) |

## The seven colours of a palette

Every livery is described by seven colours. Each one is a **solid colour** or a **two-colour gradient**.

| Colour | What it paints |
|---|---|
| Base | The paint of the car. |
| Tribals | The graphic shapes over the base. On the preview car it is the colour at the front. |
| Tribal outline | The line around the tribals. |
| Sponsor A and Sponsor B | The fill of the sponsor logos. Logos alternate between A and B along the body. |
| Sponsor A outline and Sponsor B outline | The line around each sponsor logo. |

Hex codes (like `#6E8B1F`) are the only way colours are stored, so they paste straight into Illustrator and Substance Painter.
"""),
    ("Projects", """
# Projects

Every saved palette is a **project**: a card with a car in its colours and four colour chips.

* **Find one.** Search by name, mood, colour scheme or platform. Filter by mood or platform. Sort by number or name.
* **Open one.** Click a card. The right side shows the car, all seven colours (click a chip to copy its hex code) and tabs
  for the project note, build sheet, detail kit, patterns and the prompts that carry this palette.
* **Gradient or solid.** The *Car paint* switch above the car has three buttons. *Gradient* shows the livery as designed.
  *Solid base* and *Solid tribals* paint the whole car in one flat colour (the first colour, if that slot is a gradient).
  It only changes the preview: the project keeps all its colours.
* **On car.** The real sponsor logos placed in the sponsor zones of the car you picked, in this project's colours.
  Save the picture as PNG.
* **Export.** Palette card (PNG), `.ase` swatches, all hex codes, a ZIP package, or an Illustrator template of the car.

If a project lacks its detail kit, build sheet or placement preview, press *Build missing parts*. Nothing that already
exists is overwritten.
"""),
    ("New project", """
# New project

1. **Name it.** Two English words, for example *Wasabi Eclipse*. *Suggest name* makes one from the colours.
2. **Pick moods and a scheme** (or neither for a surprise), then press *Generate palette* (`Ctrl+G`) as often as you like.
3. **Change anything by hand.** Each of the seven colours has a colour button and a hex box. Tick *2-colour gradient* to give
   a slot a second colour. This works for every slot, outlines too.
4. **Lock what you like.** A locked colour stays when you generate again.
5. **Read the note under the preview.** It warns when two colours that must be readable together (a fill and its outline,
   tribals and base) are too close.
6. **Save.** Tick *Also build the Detail kit...* to get the whole set of notes in one go.

The *Car paint* switch above the preview works here too, and *Export card (PNG)* makes a shareable palette sheet.
"""),
    ("Cars", """
# Cars

The car on every preview is your **Preview car**: the box in the top right corner.

* **Built in.** Twelve cars come with the program: S13 Silvia, S13 B-style, S13 Origin kit, 180SX Origin kit, S14 D-Max kit,
  S15 Origin Raijin kit, S15 Raiji kit, ER34 Uras, JZX90 BN Sport, Galant, E36 Coupe and the S160 Junction Produce.
* **Wheels.** Two of them come without wheels. For those, the two boxes next to the car choose the wheel (TE37, VS-KF) and
  its colour. The other cars keep the wheels in their picture.
* **Your own cars.** On the [Cars](page:2) page, *Add a car* takes one car (side and top captures), and *Import a folder of
  cars* finds many at once. Your cars appear in the same box.
* **Sponsor zones.** Each view has twelve zones where sponsors go. Drag a zone to move it, drag its dot to resize, right-click
  to add or delete. The placement is saved with the car.

Only the paint of the car takes the livery. Windows, wheels and lights keep their own colours.
"""),
    ("Workshop", """
# Workshop

Small tools for making one part of a livery, outside a project. Open them from [Workshop](page:6).

## Gradients

Pick a rear and a front colour, get suggestions for the front colour (analogous, complement, triad, lighter, darker), and set
the cut: its angle, where its centre is and how much of the car it covers. The studio standard is 45 degrees, centred on the
door, over half the car. Keep favourites, export them as `.ase`, or send the pair to any slot of a new project.

## Sponsors and outlines

Change the colour of Sponsor A, Sponsor B and their outlines, and see them on big plates on the car.

* Every slot is solid or a gradient: tick *2-colour gradient* to switch.
* *Start from* loads the New project page or any saved project.
* *Outlines for contrast* picks a dark or a light outline for each fill. *Sponsors as gradients* turns solid sponsors into
  gradients. *All solid* does the opposite. *Swap A and B* swaps the two sponsors.
* *Use in New project* sends the five colours to the New project page.

## Logo outlines

Draws a contour around a logo, in one colour or a two-colour gradient. Set thickness, gap and how far to join letters, then
save the outlined logo, the outline alone, a cut plate and a layered SVG. *Outline a whole folder* does many logos at once.
"""),
    ("Prompts, Sponsors, Guides", """
# Prompts, Sponsors and Guides

## Prompts

All the image prompts, sorted by category. Pick a colour version (grey master, the palette on the New project page, any
project, or the ready-made options) and press *Copy prompt*.

## Sponsors

The sponsor database, filtered by chassis, engine, category and region. Each brand is colour-coded as fitting your build,
universal, or needing a fitment check. *Copy list* or *Save as vault note* keeps the result.

## Guides

The reference notes of the vault: glossaries, style guide, placement and paint guides, the year plan. Links between notes
work, and a link to a project opens it.
"""),
    ("Files, backup, updates", """
# Files, backup and updates

Everything you make is stored as ordinary Markdown notes in your **workspace folder**, which also opens in Obsidian. The
program never keeps your work anywhere else.

* **Changed a note in Obsidian?** Press `F5` to reload.
* **Back up.** *File > Back up to GitHub* (`Ctrl+B`) commits and pushes the folder to your own private repository.
* **Updates.** *Help > Check for updates* looks for a newer version and checks it before installing.
* **Move the workspace.** *File > Change workspace folder*.

## Keyboard shortcuts

| Keys | Does |
|---|---|
| `Ctrl+1` to `Ctrl+8` | Switch page |
| `Ctrl+G` | Generate a palette |
| `F5` | Reload from disk |
| `Ctrl+B` | Back up to GitHub |
| `Ctrl+Q` | Quit |

The program is in beta. If something looks wrong, keep a backup of your workspace and tell the author what you saw.
"""),
]


class HowToPage(QWidget):
    openPage = Signal(int)
    status = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("page")
        self.topics = QListWidget()
        self.topics.addItems([t for t, _ in TOPICS])
        self.topics.setFixedWidth(250)
        self.view = QTextBrowser()
        self.view.setOpenLinks(False)
        self.view.document().setDefaultStyleSheet(NOTE_CSS)
        self.view.anchorClicked.connect(self._link)
        self.topics.currentRowChanged.connect(self._show)
        left = QVBoxLayout()
        left.addWidget(label("How to", "h1"))
        left.addWidget(self.topics, 1)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 10)
        lay.addLayout(left)
        lay.addWidget(self.view, 1)
        self.topics.setCurrentRow(0)

    def _show(self, i):
        if i < 0:
            return
        self.view.setHtml(markdown.markdown(TOPICS[i][1], extensions=["tables"]))
        self.view.verticalScrollBar().setValue(0)

    def _link(self, url):
        if url.scheme() == "page":
            self.openPage.emit(int(url.toString()[5:]))
