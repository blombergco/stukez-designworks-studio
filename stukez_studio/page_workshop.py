"""The Workshop page: tools for making parts of a livery (logos placed on the car, gradients, logo outlines) outside a project."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from .page_board import BoardTab
from .page_gradients import GradientsTab
from .page_outlines import OutlinesTab
from .widgets import label


class WorkshopPage(QWidget):
    status = Signal(str)
    sendToProject = Signal(str, object)
    layoutChanged = Signal()

    def __init__(self, vault, palette_source=None):
        super().__init__()
        self.setObjectName("page")
        self.board = BoardTab(vault, palette_source)
        self.gradients = GradientsTab(vault)
        self.outlines = OutlinesTab(vault)
        for tab in (self.board, self.gradients, self.outlines):
            tab.status.connect(self.status)
        self.board.layoutChanged.connect(self.layoutChanged)
        self.gradients.sendToProject.connect(self.sendToProject)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.board, "Place on car")
        self.tabs.addTab(self.gradients, "Gradients")
        self.tabs.addTab(self.outlines, "Logo outlines")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 10)
        lay.addWidget(label("Workshop", "h1"))
        lay.addWidget(self.tabs, 1)
