"""The dialogs and background threads around updates.py."""
import tempfile

from PySide6.QtCore import QObject, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QMessageBox, QProgressDialog

from . import __version__, updates


class CheckWorker(QThread):
    done = Signal(object, str)      # release info or None, error text

    def run(self):
        try:
            self.done.emit(updates.latest(), "")
        except updates.UpdateError as e:
            self.done.emit(None, str(e))


class DownloadWorker(QThread):
    progress = Signal(int, int)
    done = Signal(object, str)      # path or None, error text

    def __init__(self, info, parent=None):
        super().__init__(parent)
        self.info, self.folder = info, tempfile.mkdtemp(prefix="stukez_update_")

    def run(self):
        try:
            self.done.emit(updates.download(self.info, self.folder, lambda a, b: self.progress.emit(a, b)), "")
        except updates.UpdateError as e:
            self.done.emit(None, str(e))


class UpdateController(QObject):
    available = Signal(object)      # release info of a newer version

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self._threads = []

    def check(self, manual):
        w = CheckWorker(self)
        self._threads.append(w)
        w.done.connect(lambda info, err, w=w: self._checked(info, err, manual, w))
        if manual:
            self.window.flash("Checking for updates…")
        w.start()

    def _checked(self, info, err, manual, worker):
        self._threads.remove(worker)
        if err:
            if manual:
                QMessageBox.information(self.window, "Check for updates", err)
            return
        if not updates.is_newer(info["version"]):
            if manual:
                QMessageBox.information(self.window, "Check for updates", f"You have the latest version ({__version__}).")
            return
        self.available.emit(info)
        if manual:
            self.offer(info)

    def offer(self, info):
        notes = info["notes"][:900] + ("…" if len(info["notes"]) > 900 else "")
        text = f"Version {info['version']} is available (you have {__version__}).\n\n" + (f"What's new:\n{notes}\n\n" if notes else "")
        if not updates.can_self_update():
            if QMessageBox.question(self.window, "Update available", text + "This copy runs from source, so it does not update itself. Open the release page?") == QMessageBox.Yes:
                QDesktopServices.openUrl(QUrl(info["page"]))
            return
        if QMessageBox.question(self.window, "Update available", text + "Download and install it now? Your projects are not touched.") != QMessageBox.Yes:
            return
        dlg = QProgressDialog("Downloading the update…", "Cancel", 0, 100, self.window)
        dlg.setWindowTitle("Updating")
        dlg.setMinimumDuration(0)
        dlg.setAutoClose(False)
        worker = DownloadWorker(info, self)
        self._threads.append(worker)
        worker.progress.connect(lambda a, b: dlg.setValue(int(100 * a / b)) if b else None)
        worker.done.connect(lambda path, err, w=worker, d=dlg: self._downloaded(path, err, w, d))
        dlg.canceled.connect(worker.terminate)
        worker.start()

    def _downloaded(self, path, err, worker, dlg):
        self._threads.remove(worker)
        dlg.close()
        if err:
            QMessageBox.warning(self.window, "Update failed", err)
            return
        QMessageBox.information(self.window, "Update ready", "The installer starts now and the program closes and reopens by itself.")
        updates.install(path)
        QApplication.quit()
