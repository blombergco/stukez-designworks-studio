"""New project page: pick a name and colours by hand or let the generator suggest a palette."""
import os
import random

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QFileDialog, QGridLayout, QHBoxLayout, QLineEdit,
                               QMessageBox, QPlainTextEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget)

from . import palette as pal
from . import render
from .widgets import ChipGrid, LiveryPreview, PaintSwitch, StudioButton, button, copy_text, label, run_build

SLOTS = [("base", "Base", True), ("tribal", "Tribals", True), ("tribal_outline", "Tribal outline", True),
         ("sponsor_a", "Sponsor A", True), ("sponsor_a_outline", "Sponsor A outline", True),
         ("sponsor_b", "Sponsor B", True), ("sponsor_b_outline", "Sponsor B outline", True)]


class ColourButton(QPushButton):
    changed = Signal()

    def __init__(self, hex_="#808080"):
        super().__init__()
        self.setFixedSize(34, 28)
        self.set_hex(hex_)
        self.clicked.connect(self._pick)

    def hex(self):
        return self._hex

    def set_hex(self, h):
        self._hex = h
        self.setStyleSheet(f"QPushButton {{ background: {h}; border: 1px solid #6a3a42; border-radius: 4px; padding: 0; }}")

    def _pick(self):
        c = QColorDialog.getColor(QColor(self._hex), self, "Pick colour")
        if c.isValid():
            self.set_hex(c.name().upper())
            self.changed.emit()


class SlotRow(QWidget):
    changed = Signal()

    def __init__(self, key, text, can_gradient):
        super().__init__()
        self.key, self.can_gradient = key, can_gradient
        self.lock = QCheckBox("lock")
        self.lock.setToolTip("Keep this colour when generating")
        self.grad = QCheckBox("2-colour gradient")
        self.b1, self.b2 = ColourButton(), ColourButton()
        self.e1, self.e2 = QLineEdit(maxLength=7), QLineEdit(maxLength=7)
        for e in (self.e1, self.e2):
            e.setFixedWidth(84)
        for b, e in ((self.b1, self.e1), (self.b2, self.e2)):
            b.changed.connect(lambda b=b, e=e: (e.setText(b.hex()), self.changed.emit()))
            e.editingFinished.connect(lambda b=b, e=e: self._typed(b, e))
        top = QHBoxLayout()
        top.addWidget(label(text, "h2"))
        top.addStretch()
        if can_gradient:
            top.addWidget(self.grad)
        top.addWidget(self.lock)
        row = QHBoxLayout()
        row.addWidget(self.b1)
        row.addWidget(self.e1)
        row.addSpacing(8)
        row.addWidget(self.b2)
        row.addWidget(self.e2)
        row.addStretch()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 4)
        lay.setSpacing(3)
        lay.addLayout(top)
        lay.addLayout(row)
        self.grad.toggled.connect(self._grad_changed)
        self._grad_changed(False, emit=False)

    def _typed(self, b, e):
        h = pal.valid_hex(e.text())
        if h:
            b.set_hex(h)
            e.setText(h)
            self.changed.emit()
        else:
            e.setText(b.hex())

    def _grad_changed(self, on, emit=True):
        self.b2.setVisible(on)
        self.e2.setVisible(on)
        if emit:
            self.changed.emit()

    def value(self):
        return [self.b1.hex(), self.b2.hex()] if self.grad.isChecked() and self.can_gradient else self.b1.hex()

    def set_value(self, v):
        cs = v if isinstance(v, list) else [v]
        self.grad.blockSignals(True)
        self.grad.setChecked(len(cs) == 2 and self.can_gradient)
        self.grad.blockSignals(False)
        self._grad_changed(len(cs) == 2 and self.can_gradient, emit=False)
        self.b1.set_hex(cs[0])
        self.e1.setText(cs[0])
        if len(cs) == 2:
            self.b2.set_hex(cs[1])
            self.e2.setText(cs[1])


class GeneratorPage(QWidget):
    saved = Signal(object)
    status = Signal(str)
    palette_changed = Signal(object)

    def __init__(self, vault):
        super().__init__()
        self.setObjectName("page")
        self.vault = vault
        self.rng = random.Random()
        self.seed_hue = None
        self._busy = False

        # --- controls
        self.name = QLineEdit(placeholderText="Project name, two English words (e.g. Wasabi Eclipse)")
        self.suggest = button("Suggest name", slot=self.suggest_name)
        self.moods = {}
        mood_grid = QGridLayout()
        mood_grid.setSpacing(5)
        for i, m in enumerate(pal.MOODS):
            b = StudioButton(m)
            b.setObjectName("mood")
            b.setCheckable(True)
            mood_grid.addWidget(b, i // 5, i % 5)
            self.moods[m] = b
        self.scheme = QComboBox()
        self.scheme.addItems(pal.SCHEMES)
        self.seed_btn = ColourButton("#808080")
        self.seed_use = QCheckBox("Start from this colour")
        self.seed_btn.changed.connect(lambda: self.seed_use.setChecked(True))
        gen = button("Generate palette   (Ctrl+G)", True, self.generate)
        gen.setMinimumHeight(40)
        self.rows = {}
        rows_lay = QVBoxLayout()
        for key, text, grad in SLOTS:
            r = SlotRow(key, text, grad)
            r.changed.connect(self._edited)
            self.rows[key] = r
            rows_lay.addWidget(r)
        self.platform = QLineEdit(placeholderText="Platform (optional, e.g. S13, JZX90)")
        self.concept = QPlainTextEdit(placeholderText="Short description of the palette")
        self.concept.setFixedHeight(64)

        form = QVBoxLayout()
        form.setSpacing(8)
        form.addWidget(label("New project", "h1"))
        form.addWidget(label("Name", "h2"))
        nr = QHBoxLayout()
        nr.addWidget(self.name, 1)
        nr.addWidget(self.suggest)
        form.addLayout(nr)
        form.addWidget(label("Mood (pick none for a surprise)", "h2"))
        form.addLayout(mood_grid)
        sr = QHBoxLayout()
        sr.addWidget(label("Scheme"))
        sr.addWidget(self.scheme, 1)
        form.addLayout(sr)
        seed = QHBoxLayout()
        seed.addWidget(self.seed_btn)
        seed.addWidget(self.seed_use)
        seed.addStretch()
        form.addLayout(seed)
        form.addWidget(gen)
        form.addWidget(label("Colours (hex codes only, every slot is a solid colour or a 2-colour gradient)", "h2"))
        form.addLayout(rows_lay)
        form.addWidget(label("Platform and concept", "h2"))
        form.addWidget(self.platform)
        form.addWidget(self.concept)
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

        # --- preview
        self.livery = LiveryPreview(300)
        self.paint = PaintSwitch()
        self.chips = ChipGrid()
        self.chips.copied.connect(lambda n: self.status.emit(f"Copied {n}"))
        self.problem = label("", "muted", wrap=True)
        self.save_btn = button("", True, self.save)
        self.save_btn.setMinimumHeight(42)
        self.build_check = QCheckBox("Also build the Detail kit, Build sheet with sponsor kit and Placement preview")
        self.build_check.setChecked(True)
        actions = QHBoxLayout()
        actions.addWidget(button("Export card (PNG)", slot=self.export_card))
        actions.addWidget(button("Copy hex list", slot=self.copy_hex))
        actions.addWidget(button("Make a surprise", slot=self.surprise))
        actions.addStretch()
        right = QVBoxLayout()
        right.setContentsMargins(10, 0, 0, 0)
        right.addWidget(label("Preview", "h2"))
        right.addWidget(self.paint)
        right.addWidget(self.livery, 1)
        right.addWidget(self.chips)
        right.addWidget(self.problem)
        right.addLayout(actions)
        right.addWidget(self.build_check)
        right.addWidget(self.save_btn)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 10)
        lay.addWidget(scroll)
        lay.addLayout(right, 1)
        self._auto_name = False
        self.name.textChanged.connect(self._refresh_save)
        self.name.textEdited.connect(lambda _t: setattr(self, "_auto_name", False))
        QShortcut(QKeySequence(Qt.CTRL | Qt.Key_G), self, activated=self.generate)
        self.surprise()

    # ------------------------------------------------------------------ state
    def apply_slot(self, key, value):
        """Set one slot (base, tribal, sponsor_a, sponsor_b) from outside, e.g. a gradient from the Workshop."""
        self.rows[key].set_value(value)
        self._edited()

    def selected_moods(self):
        return [m for m, b in self.moods.items() if b.isChecked()]

    def palette(self):
        d = {k: r.value() for k, r in self.rows.items()}
        d.update(name=self.name.text().strip(), platform=self.platform.text().strip(), moods=self.selected_moods(),
                 concept=self.concept.toPlainText().strip())
        return d

    def _apply(self, d, only_unlocked=True):
        self._busy = True
        for k, r in self.rows.items():
            if not (only_unlocked and r.lock.isChecked()):
                r.set_value(d[k])
        self._busy = False
        self._edited()

    def _edited(self):
        if self._busy:
            return
        d = self.palette()
        self.livery.set_palette(d)
        self.chips.set_palette(d)
        problems = pal.check_rules(d)
        low = pal.quality(d)
        if problems:
            self.problem.setText("⚠ " + "; ".join(problems))
        elif low < 2.0:
            self.problem.setText(f"Contrast note: the weakest fill/outline or tribal/base pair is {low:.1f}:1, "
                                 "so parts of the livery may be hard to read. Fine if intentional.")
        else:
            self.problem.setText("Follows the Project Library palette rules.")
        self.palette_changed.emit(d)
        self._refresh_save()

    def _refresh_save(self):
        name = self.name.text().strip()
        nid = self.vault.next_id()
        taken = name.lower() in self.vault.used_names()
        self.save_btn.setEnabled(bool(name) and not pal.check_rules(self.palette()) and not taken)
        self.save_btn.setText(f"Save to vault as {nid:03d} {name}" if name else "Enter a name to save")
        if taken:
            self.save_btn.setText(f"A project called “{name}” already exists")

    # ------------------------------------------------------------------ actions
    def generate(self):
        seed = QColor(self.seed_btn.hex()).hueF() * 360 if self.seed_use.isChecked() else None
        d = pal.generate(self.selected_moods(), self.scheme.currentText(), seed, self.rng)
        self._apply(d)
        if not self.name.text().strip() or self._auto_name:
            self.suggest_name()
        self._auto_describe()

    def surprise(self):
        for b in self.moods.values():
            b.setChecked(False)
        for m in self.rng.sample(list(pal.MOODS), self.rng.choice([1, 2])):
            self.moods[m].setChecked(True)
        for r in self.rows.values():
            r.lock.setChecked(False)
        self.name.clear()
        self.generate()

    def suggest_name(self):
        self.name.setText(pal.suggest_name(self.palette(), self.selected_moods(), self.vault.used_names(), self.rng))
        self._auto_name = True

    def _auto_describe(self):
        d = self.palette()
        word = lambda v: pal.nearest_colour_word([v[0] if isinstance(v, list) else v]).lower()
        base = word(d["base"][-1] if isinstance(d["base"], list) else d["base"])
        first = word(d["base"][0] if isinstance(d["base"], list) else d["base"])
        base_txt = f"{first.capitalize()} fading into {base}" if isinstance(d["base"], list) and first != base else f"{base.capitalize()} base"
        self.concept.setPlainText(f"{base_txt}, with {word(d['tribal'])} tribals and {word(d['sponsor_a'])} and "
                                  f"{word(d['sponsor_b'])} sponsor accents.")

    def copy_hex(self):
        d = self.palette()
        copy_text("\n".join(f"{lbl}: " + " → ".join(v if isinstance(v, list) else [v])
                            for lbl, v in ((t, d[k]) for k, t, _ in SLOTS)))
        self.status.emit("Copied all hex codes")

    def export_card(self):
        d = self.palette()
        title = d["name"] or "New palette"
        path, _ = QFileDialog.getSaveFileName(self, "Save palette card", f"{title} - Palette card.png", "PNG image (*.png)")
        if path:
            render.render_card_image(d, title, "", d["concept"]).save(path)
            self.status.emit(f"Saved {os.path.basename(path)}")

    def save(self):
        d = self.palette()
        try:
            proj = self.vault.save_project(d)
        except Exception as e:  # projectkit validates every rule; show its message as is
            QMessageBox.warning(self, "Could not save", str(e))
            return
        msg = f"Saved {proj.title} to the vault"
        if self.build_check.isChecked():
            res = run_build(self, self.vault, proj.id)
            if not res:
                msg += " (the extra notes could not be built, use Build missing parts)"
            else:
                msg += " with " + ", ".join(s.lower() for s in res["built"]) if res["built"] else ""
                if res["notes"] and "Skipped" in res["notes"][0]:
                    msg += f". {res['notes'][0]}"
        self.status.emit(msg)
        self.saved.emit(proj)
        self.name.clear()
        self.surprise()
