"""Writes assets/icon.ico from the app's own painted icon (run by build_exe.ps1)."""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from PIL import Image

from stukez_studio.main import app_icon

here = Path(__file__).resolve().parent
(here / "assets").mkdir(exist_ok=True)
app = QApplication(sys.argv)
png = here / "assets" / "icon.png"
app_icon().pixmap(256, 256).save(str(png))
Image.open(png).save(here / "assets" / "icon.ico", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
print("icon written")
