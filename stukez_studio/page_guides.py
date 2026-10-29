"""Guides page: glossaries, placement and paint guides, year plan and the other reference notes."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QSplitter, QVBoxLayout, QWidget)

from .theme import head_font
from .widgets import NoteView, button, label

GUIDES = [
    ("Design", ["Design glossary", "Design glossary - Japanese", "Style guide", "Text and lettering plan", "Pipeline tips",
                "Motif ideas", "Universal details guide", "Detail kits"]),
    ("Livery production", ["Sponsor placement guide", "Substance Paint Guide", "Test Car Guide", "Palette of the day",
                           "Year plan", "Roadmap", "Project Library README", "Projects index"]),
    ("Logos", ["Ash Works Logo Pack", "Master Logo List", "Standard Line-up - Quality Check", "Missing Logos",
               "Core Folders Overview", "Generated Masters", "StukeZ Designworks - Brand kit"]),
    ("Sponsor database", ["Home", "README"]),
]


class GuidesPage(QWidget):
    openProject = Signal(int)
    status = Signal(str)

    def __init__(self, vault, project_titles):
        super().__init__()
        self.setObjectName("page")
        self.vault = vault
        self.project_titles = project_titles   # callable: {title: id}

        self.search = QLineEdit(placeholderText="Filter guides…")
        self.list = QListWidget()
        self.view = NoteView(vault)
        self.view.noteRequested.connect(self.follow)
        self.back_btn = button("← Back", slot=self.view.back)
        self.title = label("Guides", "h1")

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(label("Guides", "h1"))
        ll.addWidget(self.search)
        ll.addWidget(self.list, 1)
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(8, 0, 0, 0)
        bar = QHBoxLayout()
        bar.addWidget(self.back_btn)
        bar.addStretch()
        rl.addLayout(bar)
        rl.addWidget(self.view, 1)
        split = QSplitter()
        split.addWidget(left)
        split.addWidget(right)
        split.setSizes([340, 1200])
        lay = QHBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 10)
        lay.addWidget(split)

        self._fill()
        self.search.textChanged.connect(self._filter)
        self.list.currentItemChanged.connect(lambda cur, _p: cur and cur.data(Qt.UserRole) and self._open(cur.data(Qt.UserRole)))
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.UserRole):
                self.list.setCurrentRow(i)
                break

    def _fill(self):
        self.list.clear()
        for group, names in GUIDES:
            head = QListWidgetItem(group)
            head.setFlags(Qt.NoItemFlags)
            head.setFont(head_font(18))
            head.setForeground(QColor("#ff5a68"))
            self.list.addItem(head)
            for n in names:
                path = self._guide_path(group, n)
                if path and path.exists():
                    it = QListWidgetItem(n)
                    it.setData(Qt.UserRole, path)
                    self.list.addItem(it)

    def _guide_path(self, group, name):
        if group == "Sponsor database":
            return {"README": self.vault.db / "README.md", "Home": self.vault.db / "Home.md"}.get(name)
        hits = self.vault.stems().get(name) or []
        return min(hits, key=lambda p: len(p.parts)) if hits else None

    def _filter(self, text):
        t = text.lower()
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it.data(Qt.UserRole):
                it.setHidden(t not in it.text().lower())

    def _open(self, path):
        self.view.history.clear()
        self.view.show_note(path)

    def follow(self, name):
        titles = self.project_titles()
        if name in titles:
            self.openProject.emit(titles[name])
            return
        path = self.vault.resolve(name)
        if path:
            self.view.show_note(path)
