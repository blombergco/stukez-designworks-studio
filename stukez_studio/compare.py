"""Compare two projects: their liveries on the same car, one above the other, with their colours underneath."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDialog, QHBoxLayout, QVBoxLayout, QWidget

from .widgets import ChipGrid, LiveryPreview, button, label


class _Side(QWidget):
    """One project: a box to choose it, its livery and its seven colours."""

    def __init__(self, projects, start):
        super().__init__()
        self.projects = projects
        self.box = QComboBox()
        for p in projects:
            self.box.addItem(f"{p.id:03d}  {p.name}", p)
        self.box.setCurrentIndex(max(0, min(start, len(projects) - 1)))
        self.livery = LiveryPreview(190, plates=False)
        self.chips = ChipGrid()
        self.mood = label("", "muted", wrap=True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.box)
        lay.addWidget(self.livery, 1)
        lay.addWidget(self.chips)
        lay.addWidget(self.mood)
        self.box.currentIndexChanged.connect(self.refresh)
        self.refresh()

    def project(self):
        return self.box.currentData()

    def refresh(self):
        p = self.project()
        if p is None:
            return
        self.livery.set_palette(p)
        self.chips.set_palette(p)
        self.mood.setText(", ".join(p.moods) if p.moods else "")


class CompareDialog(QDialog):
    """Two projects on the preview car, to choose between palettes. Swap puts them the other way round."""

    def __init__(self, projects, first_id=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Compare two projects")
        self.resize(1040, 740)
        i = next((n for n, p in enumerate(projects) if p.id == first_id), 0)
        self.a = _Side(projects, i)
        self.b = _Side(projects, (i + 1) % max(1, len(projects)))
        top = QHBoxLayout()
        top.addWidget(label("Compare", "h2"))
        top.addStretch()
        top.addWidget(button("Swap", slot=self.swap))
        top.addWidget(button("Close", True, self.accept))
        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(self.a, 1)
        lay.addWidget(self.b, 1)

    def swap(self):
        ia, ib = self.a.box.currentIndex(), self.b.box.currentIndex()
        self.a.box.setCurrentIndex(ib)
        self.b.box.setCurrentIndex(ia)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.accept()
        else:
            super().keyPressEvent(e)
