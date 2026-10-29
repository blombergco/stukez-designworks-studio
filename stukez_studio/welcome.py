"""The first-run dialog (create a workspace or point at an existing vault) and the licences dialog."""
from pathlib import Path

from PySide6.QtWidgets import (QCheckBox, QDialog, QFileDialog, QHBoxLayout, QLineEdit, QMessageBox, QTextBrowser, QVBoxLayout)

from . import workspace
from .backend import looks_like_vault
from .widgets import button, label


class WelcomeDialog(QDialog):
    """Shown when no workspace is known: make a new one, or use an existing vault folder."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("StukeZ Designworks Studio")
        self.setMinimumWidth(640)
        self.root = None
        self.path = QLineEdit(str(workspace.default_path()))
        self.examples = QCheckBox("Include 6 example palettes (you can delete them later)")
        self.examples.setChecked(True)
        browse = button("Browse…", slot=self._browse)
        row = QHBoxLayout()
        row.addWidget(self.path, 1)
        row.addWidget(browse)
        create = button("Create workspace", True, self._create)
        existing = button("I already have a vault folder…", slot=self._existing)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(26, 22, 26, 22)
        lay.setSpacing(10)
        lay.addWidget(label("Welcome", "h1"))
        lay.addWidget(label("Your projects, palettes, cars and notes live in one folder, called a workspace. "
                            "Choose where it goes; an empty or new folder works.", "muted", wrap=True))
        lay.addLayout(row)
        lay.addWidget(self.examples)
        lay.addWidget(create)
        lay.addSpacing(8)
        lay.addWidget(label("Moving from another computer, or using a vault that already has a Project Library?", "muted", wrap=True))
        lay.addWidget(existing)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Choose where the workspace goes", str(Path(self.path.text()).parent))
        if d:
            self.path.setText(str(Path(d) / "StukeZ Designworks Studio") if any(Path(d).iterdir()) else d)

    def _create(self):
        try:
            self.root = workspace.create(self.path.text().strip(), self.examples.isChecked())
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, "Could not create the workspace", str(e))
            return
        self.accept()

    def _existing(self):
        d = QFileDialog.getExistingDirectory(self, "Choose the vault folder (the one that contains Project Library)")
        if not d:
            return
        if looks_like_vault(d):
            self.root = Path(d)
            self.accept()
        else:
            QMessageBox.warning(self, "Not a vault", "That folder has no Project Library and Drift Sponsor Database with their Tools.")


class LicencesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Third-party licences")
        self.resize(760, 560)
        view = QTextBrowser()
        legal = workspace.app_base() / "legal"
        parts = []
        for name in ("THIRD_PARTY_NOTICES.txt", "LGPL-3.0.txt"):
            f = legal / name
            parts.append(f.read_text(encoding="utf-8", errors="replace") if f.exists() else f"({name} is missing from this installation)")
        view.setPlainText("\n\n".join(parts))
        lay = QVBoxLayout(self)
        lay.addWidget(view)
        lay.addWidget(button("Close", slot=self.accept))
