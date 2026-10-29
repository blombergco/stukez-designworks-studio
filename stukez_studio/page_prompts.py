"""Prompts page: browse the Gemini prompt library and recolour any prompt with a project's palette."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QLineEdit, QPlainTextEdit, QSplitter, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)

from .widgets import ChipGrid, button, copy_text, label, pill


class PromptsPage(QWidget):
    status = Signal(str)

    GREY, GEN = "master", "generator"

    def __init__(self, vault, generator_palette):
        super().__init__()
        self.setObjectName("page")
        self.vault = vault
        self.generator_palette = generator_palette   # callable returning the generator's current palette dict
        self.item = None
        self.options = []

        self.search = QLineEdit(placeholderText="Search prompts (name, category, mood)…")
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(14)
        self.count = label("", "muted")
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(label("Prompts", "h1"))
        ll.addWidget(self.search)
        ll.addWidget(self.count)
        ll.addWidget(self.tree, 1)

        self.title = label("Choose a prompt", "h1")
        self.badges = QHBoxLayout()
        self.palette_box = QComboBox()
        self.palette_box.setEditable(True)
        self.palette_box.setInsertPolicy(QComboBox.NoInsert)
        self.palette_box.completer().setFilterMode(Qt.MatchContains)
        self.chips = ChipGrid()
        self.chips.setVisible(False)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setStyleSheet("font-family: Consolas; font-size: 13px;")
        self.text.setPlaceholderText("Pick a prompt in the list. Its text shows up here, ready to copy.")
        self.copy_btn = button("Copy prompt", True, self.copy)
        self.copy_btn.setMinimumHeight(40)
        self.meta = label("", "muted", wrap=True)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(8, 0, 0, 0)
        rl.addWidget(self.title)
        hb = QWidget()
        hb.setLayout(self.badges)
        self.badges.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(hb)
        rl.addWidget(label("Colour version", "h2"))
        rl.addWidget(self.palette_box)
        rl.addWidget(self.chips)
        rl.addWidget(self.text, 1)
        rl.addWidget(self.meta)
        rl.addWidget(self.copy_btn)

        split = QSplitter()
        split.addWidget(left)
        split.addWidget(right)
        split.setSizes([480, 1000])
        lay = QHBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 10)
        lay.addWidget(split)

        self._build_tree()
        self._fill_palettes()
        self.search.textChanged.connect(self._filter)
        self.tree.currentItemChanged.connect(lambda cur, _p: self._pick(cur))
        self.palette_box.currentIndexChanged.connect(self._render)

    # ------------------------------------------------------------------ tree
    def _build_tree(self):
        self.tree.clear()
        groups = {}
        for it in self.vault.prompts():
            groups.setdefault(it["cat"], []).append(it)
        for cat in sorted(groups):
            top = QTreeWidgetItem([f"{cat}  ({len(groups[cat])})"])
            top.setData(0, Qt.UserRole, None)
            f = top.font(0)
            f.setBold(True)
            top.setFont(0, f)
            for it in sorted(groups[cat], key=lambda x: (x.get("group", ""), x["title"].lower())):
                child = QTreeWidgetItem([(f"{it['group']}  ·  " if it.get("group") else "") + it["title"]])
                child.setData(0, Qt.UserRole, it)
                top.addChild(child)
            self.tree.addTopLevelItem(top)
        self.count.setText(f"{len(self.vault.prompts())} prompts")

    def _filter(self, text):
        words = text.lower().split()
        shown = 0
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            vis = 0
            for j in range(top.childCount()):
                c = top.child(j)
                it = c.data(0, Qt.UserRole)
                hay = f"{c.text(0)} {it['category']} {' '.join(it.get('moods', []))}".lower()
                ok = all(w in hay for w in words)
                c.setHidden(not ok)
                vis += ok
            top.setHidden(vis == 0)
            top.setExpanded(bool(words) and vis > 0)
            shown += vis
        self.count.setText(f"{shown} of {len(self.vault.prompts())} prompts")

    def _fill_palettes(self):
        self.palette_box.blockSignals(True)
        self.palette_box.clear()
        self.palette_box.addItem("Greyscale master (recolour freely)", self.GREY)
        self.palette_box.addItem("Generator palette (the one on the New project page)", self.GEN)
        for p in self.vault.projects():
            self.palette_box.addItem(f"{p.title}", p)
        self.palette_box.blockSignals(False)

    def reload(self):
        keep = self.palette_box.currentData()
        self._build_tree()
        self._fill_palettes()
        if hasattr(keep, "id"):
            self.use_project(keep)

    # ------------------------------------------------------------------ selection
    def open_prompt(self, item, project=None):
        """Select a prompt in the tree (from another page), optionally with a project's palette."""
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            for j in range(top.childCount()):
                if top.child(j).data(0, Qt.UserRole) is item or top.child(j).data(0, Qt.UserRole)["key"] == item["key"]:
                    self.search.clear()
                    top.setExpanded(True)
                    self.tree.setCurrentItem(top.child(j))
                    if project is not None:
                        self.use_project(project)
                    return

    def use_project(self, project):
        for i in range(self.palette_box.count()):
            d = self.palette_box.itemData(i)
            if hasattr(d, "id") and d.id == project.id:
                self.palette_box.setCurrentIndex(i)
                return

    def _pick(self, cur):
        it = cur.data(0, Qt.UserRole) if cur else None
        if it is None:
            return
        self.item = it
        self.title.setText(it["title"])
        while self.badges.count():
            w = self.badges.takeAt(0).widget()
            if w:
                w.hide()
                w.deleteLater()
        for t in [it["category"]] + list(it.get("moods", [])) + ([f"{it['aspect']}"] if it.get("aspect") else []):
            self.badges.addWidget(pill(t))
        self.badges.addStretch()
        # vault options are stored per prompt, so rebuild that part of the combo list
        for i in reversed(range(self.palette_box.count())):
            if str(self.palette_box.itemData(i)).startswith("opt:"):
                self.palette_box.removeItem(i)
        self.options = self.vault.vault_options(it)
        self.palette_box.blockSignals(True)
        for n, (lbl, _code) in enumerate(self.options):
            self.palette_box.insertItem(2 + n, f"Vault option {lbl}", f"opt:{n}")
        self.palette_box.blockSignals(False)
        self._render()

    def _render(self):
        if not self.item:
            return
        sel = self.palette_box.currentData()
        proj = None
        if sel == self.GREY:
            txt = self.vault.master_prompt(self.item)
        elif sel == self.GEN:
            proj = self.generator_palette()
            txt = self.vault.recoloured(self.item, proj)
        elif isinstance(sel, str) and sel.startswith("opt:"):
            txt = self.options[int(sel[4:])][1]
        else:
            proj = sel
            txt = self.vault.recoloured(self.item, sel)
        self.chips.setVisible(proj is not None)
        if proj is not None:
            self.chips.set_palette(proj)
        self.text.setPlainText(txt)
        self.meta.setText(f"{len(txt)} characters · from {self.item['path'].name}")

    def copy(self):
        copy_text(self.text.toPlainText())
        self.status.emit("Prompt copied to the clipboard")
