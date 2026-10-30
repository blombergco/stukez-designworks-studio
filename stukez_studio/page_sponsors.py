"""Sponsors page: the Drift Sponsor Database, filterable by build (chassis + engine)."""
from datetime import date

from PySide6.QtCore import Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QHBoxLayout, QHeaderView, QLineEdit, QSplitter,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from .widgets import NoteView, button, copy_text, label

MATCH_TEXT = {"match": "fits your build", "universal": "universal", "varies": "check fitment", "": ""}
MATCH_COLOUR = {"match": "#7ee0a0", "universal": "#8bb8ff", "varies": "#ffcf70", "": "#a8999c"}


class SponsorsPage(QWidget):
    status = Signal(str)

    def __init__(self, vault):
        super().__init__()
        self.setObjectName("page")
        self.vault = vault
        d = vault.dblib
        self.rows = []

        self.search = QLineEdit(placeholderText="Search brand or product…")
        self.category = QComboBox()
        self.category.addItem("All categories", "")
        for c in d.CATEGORIES:
            self.category.addItem(c, c)
        self.region = QComboBox()
        self.region.addItem("All regions", "")
        for r in sorted({b.get("region", "") for b in vault.brands() if b.get("region")}):
            self.region.addItem(r, r)
        self.chassis = QComboBox()
        self.chassis.addItem("Any chassis", "")
        for k, v in d.CHASSIS.items():
            self.chassis.addItem(f"{k}  ·  {v['label']}", k)
        self.engine = QComboBox()
        self.engine.addItem("Any engine", "")
        for k, v in d.ENGINES.items():
            self.engine.addItem(f"{k}  ·  {v['label']}", k)
        self.universal = QCheckBox("Include universal and vehicle-specific brands")
        self.universal.setChecked(True)
        self.count = label("", "muted")

        top = QHBoxLayout()
        for w in (self.search, self.category, self.region):
            top.addWidget(w, 1)
        build = QHBoxLayout()
        build.addWidget(self.chassis, 1)
        build.addWidget(self.engine, 1)
        build.addWidget(self.universal)
        build.addWidget(button("Copy list", slot=self.copy_list))
        build.addWidget(button("Save as vault note", slot=self.save_note))

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Category", "Brand", "Country", "Product / line", "Fit", "Confidence"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(3, QHeaderView.Stretch)
        for col, w in enumerate((150, 190, 86, 0, 130, 124)):
            if w:
                self.table.setColumnWidth(col, w)
        self.table.currentCellChanged.connect(lambda r, _c, _pr, _pc: self._show(r))
        self.note = NoteView(vault)
        self.note.noteRequested.connect(self._follow)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(label("Sponsors", "h1"))
        ll.addLayout(top)
        ll.addLayout(build)
        ll.addWidget(self.count)
        ll.addWidget(self.table, 1)
        split = QSplitter()
        split.addWidget(left)
        split.addWidget(self.note)
        self.note.setMinimumWidth(480)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        split.setSizes([900, 700])
        lay = QHBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 10)
        lay.addWidget(split)

        for sig in (self.search.textChanged, self.category.currentIndexChanged, self.region.currentIndexChanged,
                    self.chassis.currentIndexChanged, self.engine.currentIndexChanged, self.universal.toggled):
            sig.connect(self.refresh)
        self.refresh()

    def refresh(self, *_):
        ch, en = self.chassis.currentData(), self.engine.currentData()
        self.rows = self.vault.sponsor_rows([ch] if ch else [], [en] if en else [], self.category.currentData() or "",
                                            self.region.currentData() or "", self.search.text(), self.universal.isChecked())
        self.table.setRowCount(len(self.rows))
        for i, r in enumerate(self.rows):
            b = r["brand"]
            vals = [r["cat"], b["name"], b.get("country", ""), r["item"], MATCH_TEXT[r["match"]] or r["fits"], b.get("confidence", "")]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if c == 4:
                    it.setForeground(QBrush(QColor(MATCH_COLOUR[r["match"]])))
                if "†" in r["notes"] or b.get("confidence") in ("unverified", "partial"):
                    it.setToolTip("† or low confidence: not fully verified")
                self.table.setItem(i, c, it)
        brands = {r["brand"]["name"] for r in self.rows}
        self.count.setText(f"{len(self.rows)} rows · {len(brands)} brands")
        if self.rows:
            self.table.selectRow(0)
        else:
            self.note.setHtml("")

    def _show(self, row):
        if 0 <= row < len(self.rows):
            self.note.show_note(self.rows[row]["brand"]["path"])

    def _follow(self, name):
        path = self.vault.resolve(name)
        if path:
            self.note.show_note(path)

    def _markdown(self):
        ch, en = self.chassis.currentData(), self.engine.currentData()
        title = " + ".join(x for x in (ch, en) if x) or "All"
        out = [f"# Sponsor list: {title}", "", f"_{len({r['brand']['name'] for r in self.rows})} brands matched._", ""]
        cat = None
        for r in self.rows:
            if r["cat"] != cat:
                cat = r["cat"]
                out += ["", f"## {cat}", ""]
            kind = {"match": " — _fitment-specific_", "universal": " — _universal_", "varies": " — _check fitment_", "": ""}[r["match"]]
            note = f" — {r['notes']}" if r["notes"] else ""
            out.append(f"- [[{r['brand']['name']}]] ({r['brand'].get('country', '')}): {r['item']}{kind}{note}")
        return "\n".join(out) + "\n", title

    def copy_list(self):
        copy_text(self._markdown()[0])
        self.status.emit("Sponsor list copied as markdown")

    def save_note(self):
        text, title = self._markdown()
        folder = self.vault.db / "Sponsor Lists"
        folder.mkdir(exist_ok=True)
        path = folder / f"Sponsor list - {title} ({date.today().isoformat()}).md"
        path.write_text(text, encoding="utf-8", newline="\n")
        self.status.emit(f"Saved {path.name} in Sponsor Lists")
