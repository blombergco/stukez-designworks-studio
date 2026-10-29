"""The Workshop page: tools for making parts of a livery (gradients, logo outlines) outside a project."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from .page_gradients import GradientsTab
from .page_outlines import OutlinesTab
from .widgets import label


class WorkshopPage(QWidget):
    status = Signal(str)
    sendToProject = Signal(str, object)

    def __init__(self, vault):
        super().__init__()
        self.setObjectName("page")
        self.gradients = GradientsTab(vault)
        self.outlines = OutlinesTab(vault)
        for tab in (self.gradients, self.outlines):
            tab.status.connect(self.status)
        self.gradients.sendToProject.connect(self.sendToProject)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.gradients, "Gradients")
        self.tabs.addTab(self.outlines, "Logo outlines")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 10)
        lay.addWidget(label("Workshop", "h1"))
        lay.addWidget(self.tabs, 1)
