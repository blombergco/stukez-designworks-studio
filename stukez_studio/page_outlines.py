"""Workshop > Logo outlines: one contour (a colour, or a 2-colour gradient) around a sponsor logo (or a whole folder of them)."""
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QRectF, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLineEdit, QMessageBox, QScrollArea, QVBoxLayout,
                               QWidget)

from . import outlines as ol
from . import palette as pal
from . import render
from .page_generator import ColourButton
from .page_gradients import slider_row
from .widgets import button, copy_text, label

BACKDROPS = (("Dark", "#14090c"), ("Light", "#f1ecee"), ("Mid grey", "#5a5f6b"), ("Car red", "#a80f20"))
PREVIEW_SIDE = 720     # the contour is worked out on a copy this big while you drag the sliders


class LogoStage(QWidget):
    """The logo with its outline on a backdrop; accepts a dropped image file."""
    dropped = Signal(str)

    def __init__(self):
        super().__init__()
        self.image, self.bg, self.caption = None, QColor(BACKDROPS[0][1]), "Drop a logo here, or press Choose logo"
        self.setAcceptDrops(True)
        self.setMinimumHeight(320)

    def set_image(self, pil, caption=""):
        if pil is None:
            self.image = None
        else:
            data = pil.tobytes("raw", "RGBA")
            self.image = QImage(data, pil.width, pil.height, pil.width * 4, QImage.Format_RGBA8888).copy()
        self.caption = caption or self.caption
        self.update()

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and any(u.toLocalFile().lower().endswith(ol.EXTS) for u in e.mimeData().urls()):
            e.acceptProposedAction()

    def dropEvent(self, e):
        for u in e.mimeData().urls():
            f = u.toLocalFile()
            if f.lower().endswith(ol.EXTS):
                self.dropped.emit(f)
                break

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = render.chamfer_path(r, 22)
        p.setClipPath(path)
        p.fillRect(r, self.bg)
        p.setPen(QPen(QColor(255, 255, 255, 12), 1))
        for i in range(int((r.width() + r.height()) / 26) + 1):     # the studio's 45 degree lines
            x = r.left() + i * 26 - r.height() * .5
            p.drawLine(int(x), int(r.bottom()), int(x + r.height()), int(r.top()))
        if self.image is not None:
            box = r.adjusted(28, 28, -28, -28)
            s = min(box.width() / self.image.width(), box.height() / self.image.height())
            w, h = self.image.width() * s, self.image.height() * s
            p.drawImage(QRectF(box.center().x() - w / 2, box.center().y() - h / 2, w, h), self.image)
        else:
            p.setPen(QColor("#a8999c"))
            p.drawText(r, Qt.AlignCenter, self.caption)
        p.setClipping(False)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 30), 1))
        p.drawPath(path)
        render.slash_edges(p, r, 22)


class OutlinesTab(QWidget):
    status = Signal(str)

    def __init__(self, vault):
        super().__init__()
        self.vault = vault
        self.path = None        # the logo file
        self.logo = None        # PIL image, background removed when asked
        self.raw = None
        self._busy = False
        self.timer = QTimer(self, singleShot=True, interval=110)
        self.timer.timeout.connect(self._render)

        self.file_label = label("No logo chosen yet", "muted", wrap=True)
        self.rm_bg = QCheckBox("Remove a plain background")
        self.rm_bg.setToolTip("Makes the colour of the corners transparent. Not needed for a PNG that already is transparent.")
        w_tol, self.s_tol = slider_row("Tolerance", 0, 120, 40, "", self._bg_changed)
        self.rm_bg.toggled.connect(self._bg_changed)
        self.b_col = ColourButton(ol.DEFAULT_OUTLINE)
        self.e_col = QLineEdit(ol.DEFAULT_OUTLINE, maxLength=7)
        self.e_col.setFixedWidth(90)
        self.b_col.changed.connect(lambda: (self.e_col.setText(self.b_col.hex()), self._queue()))
        self.e_col.editingFinished.connect(lambda: self._typed(self.b_col, self.e_col))
        self.grad = QCheckBox("2-colour gradient (left to right)")
        self.b_col2 = ColourButton("#F5F0F1")
        self.e_col2 = QLineEdit("#F5F0F1", maxLength=7)
        self.e_col2.setFixedWidth(90)
        self.b_col2.changed.connect(lambda: (self.e_col2.setText(self.b_col2.hex()), self._queue()))
        self.e_col2.editingFinished.connect(lambda: self._typed(self.b_col2, self.e_col2))
        self.grad.toggled.connect(self._grad_toggled)
        self.from_project = QComboBox()
        self.from_project.addItem("Colour of a project's outline…", None)
        for p in vault.projects():
            cs = p.sponsor_a_outline if isinstance(p.sponsor_a_outline, list) else [p.sponsor_a_outline]
            self.from_project.addItem(f"{p.id:03d}  {p.name}  {' → '.join(cs)}", cs)
        self.from_project.activated.connect(self._from_project)
        w_th, self.s_th = slider_row("Thickness", 0, 80, 12, " px", self._queue)
        w_gap, self.s_gap = slider_row("Gap", 0, 40, 0, " px", self._queue)
        w_join, self.s_join = slider_row("Join gaps", 0, 40, 0, " px", self._queue)
        self.round = QCheckBox("Round the corners of the contour")
        self.round.setChecked(True)
        self.round.toggled.connect(self._queue)
        self.backdrop = QComboBox()
        for n, c in BACKDROPS:
            self.backdrop.addItem(n, c)
        self.backdrop.currentIndexChanged.connect(self._backdrop)

        col = QHBoxLayout()
        col.addWidget(self.b_col)
        col.addWidget(self.e_col)
        col.addWidget(button("Auto contrast", slot=self.auto_colour))
        col.addStretch()
        col2 = QHBoxLayout()
        col2.addWidget(self.b_col2)
        col2.addWidget(self.e_col2)
        col2.addStretch()
        pick = QHBoxLayout()
        pick.addWidget(button("Choose logo…", True, self.choose))
        pick.addWidget(button("Outline a whole folder…", slot=self.batch))
        form = QVBoxLayout()
        form.setContentsMargins(0, 0, 12, 0)
        form.addLayout(pick)
        form.addWidget(self.file_label)
        form.addWidget(self.rm_bg)
        form.addWidget(w_tol)
        form.addWidget(label("Outline colour (solid, or a 2-colour gradient)", "h2"))
        form.addLayout(col)
        form.addWidget(self.grad)
        form.addLayout(col2)
        form.addWidget(self.from_project)
        form.addWidget(label("Shape", "h2"))
        form.addWidget(w_th)
        form.addWidget(w_gap)
        form.addWidget(w_join)
        form.addWidget(self.round)
        form.addWidget(label("Preview backdrop", "h2"))
        form.addWidget(self.backdrop)
        form.addStretch()
        host = QWidget()
        host.setObjectName("page")
        host.setLayout(form)
        scroll = QScrollArea()
        scroll.setWidget(host)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setFixedWidth(470)

        self.stage = LogoStage()
        self.stage.dropped.connect(self.open_file)
        self.info = label("", "muted", wrap=True)
        self.save_btn = button("Save the layers…", True, self.save)
        self.save_btn.setMinimumHeight(42)
        self.save_btn.setEnabled(False)
        right = QVBoxLayout()
        right.setContentsMargins(6, 0, 0, 0)
        right.addWidget(label("Preview", "h2"))
        right.addWidget(self.stage, 1)
        right.addWidget(self.info)
        acts = QHBoxLayout()
        acts.addWidget(button("Copy outline hex", slot=lambda: (copy_text(" → ".join(c for c in (self.b_col.hex(), self.spec().colour2) if c)),
                                                                self.status.emit("Copied the outline colour"))))
        acts.addStretch()
        right.addLayout(acts)
        right.addWidget(self.save_btn)
        self._grad_toggled(False)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 8, 0, 0)
        lay.addWidget(scroll)
        lay.addLayout(right, 1)
        self.s_tol.setEnabled(False)

    # ------------------------------------------------------------------ input
    def spec(self):
        return ol.Spec(self.b_col.hex(), self.b_col2.hex() if self.grad.isChecked() else "", self.s_th.value(), self.s_gap.value(),
                       self.s_join.value(), self.round.isChecked())

    def choose(self):
        f, _ = QFileDialog.getOpenFileName(self, "Choose a logo", "", "Images (*" + " *".join(ol.EXTS) + ")")
        if f:
            self.open_file(f)

    def open_file(self, f):
        try:
            self.raw = ol.load(f)
        except Exception as e:   # a file Pillow cannot read
            QMessageBox.warning(self, "Cannot open the logo", f"{Path(f).name}: {e}")
            return
        self.path = Path(f)
        plain = not ol.has_transparency(self.raw)
        self._busy = True
        self.rm_bg.setChecked(plain)
        self.s_tol.setEnabled(plain)
        self._busy = False
        self.file_label.setText(f"{self.path.name}  ({self.raw.width} × {self.raw.height})"
                                + ("  – no transparency found, so the plain background is removed" if plain else ""))
        self._apply_bg()
        self.auto_colour()

    def _bg_changed(self, *_):
        self.s_tol.setEnabled(self.rm_bg.isChecked())
        if not self._busy and self.raw is not None:
            self._apply_bg()

    def _apply_bg(self):
        self.logo = ol.remove_plain_background(self.raw, self.s_tol.value()) if self.rm_bg.isChecked() else self.raw
        self._queue()

    # ------------------------------------------------------------------ colour
    def _typed(self, b, e):
        h = pal.valid_hex(e.text())
        if h:
            b.set_hex(h)
            e.setText(h)
            self._queue()
        else:
            e.setText(b.hex())

    def _grad_toggled(self, on):
        self.b_col2.setVisible(on)
        self.e_col2.setVisible(on)
        self._queue()

    def _from_project(self, i):
        cs = self.from_project.itemData(i)
        if cs:
            self.b_col.set_hex(cs[0])
            self.e_col.setText(cs[0])
            self.grad.blockSignals(True)
            self.grad.setChecked(len(cs) == 2)
            self.grad.blockSignals(False)
            if len(cs) == 2:
                self.b_col2.set_hex(cs[1])
                self.e_col2.setText(cs[1])
            self._grad_toggled(len(cs) == 2)

    def auto_colour(self):
        if self.logo is None:
            return
        h = ol.suggest_colour(self.logo)
        self.b_col.set_hex(h)
        self.e_col.setText(h)
        self._queue()

    def _backdrop(self):
        from PySide6.QtGui import QColor as C
        self.stage.bg = C(self.backdrop.currentData())
        self.stage.update()

    # ------------------------------------------------------------------ rendering
    def _queue(self, *_):
        if not self._busy:
            self.timer.start()

    def _render(self):
        if self.logo is None:
            return
        sp = self.spec()
        f = min(1.0, PREVIEW_SIDE / max(self.logo.size))
        small = self.logo.resize((max(1, round(self.logo.width * f)), max(1, round(self.logo.height * f))), Image.LANCZOS) if f < 1 else self.logo
        scaled = ol.Spec(sp.colour, sp.colour2, round(sp.thickness * f), round(sp.gap * f), round(sp.join * f), sp.round_corners)
        if sp.thickness > 0 and scaled.thickness == 0:
            scaled.thickness = 1
        res = ol.make(small, scaled)
        self.stage.set_image(res["combined"])
        self.save_btn.setEnabled(True)
        self.info.setText(f"Outline {sp.colour}{' → ' + sp.colour2 if sp.colour2 else ''}, {sp.thickness} px"
                          + (f", gap {sp.gap} px" if sp.gap else "") + (f", joins gaps up to {sp.join} px" if sp.join else "")
                          + f". The saved files are {self.logo.width + 2 * (sp.gap + sp.thickness + 4)} × "
                            f"{self.logo.height + 2 * (sp.gap + sp.thickness + 4)} px.")

    # ------------------------------------------------------------------ output
    def save(self):
        if self.logo is None:
            return
        folder = QFileDialog.getExistingDirectory(self, "Save the layers in", self.path.parent.as_posix())
        if not folder:
            return
        names = ol.save(ol.make(self.logo, self.spec()), self.logo, folder, self.path.stem)
        self.status.emit(f"Saved {len(names)} files for {self.path.stem} in {folder}")

    def batch(self):
        src = QFileDialog.getExistingDirectory(self, "Choose the folder with the logos")
        if not src:
            return
        files = ol.logos_in(src)
        if not files:
            QMessageBox.information(self, "No logos found", "That folder has no PNG, WebP, JPG, TGA or BMP files.")
            return
        out = Path(src) / "outlined"
        sp = self.spec()
        tol = self.s_tol.value() if self.rm_bg.isChecked() else None
        done, failed = 0, []
        for f in files:
            try:
                ol.process_file(f, sp, out, tol)
                done += 1
            except Exception as e:
                failed.append(f"{f.name}: {e}")
        msg = f"Outlined {done} of {len(files)} logos into {out}"
        if failed:
            msg += "\n\nFailed:\n" + "\n".join(failed[:8])
            QMessageBox.warning(self, "Some logos failed", msg)
        self.status.emit(f"Outlined {done} of {len(files)} logos into {out}")
