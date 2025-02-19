from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool
import sys, traceback
from depthai_sdk import loadModule
from depthai_helpers.previews import Previews

class WorkerSignals(QObject):
    updateConfSignal = pyqtSignal(list)
    updateDownloadProgressSignal = pyqtSignal(int, int)
    updatePreviewSignal = pyqtSignal(object)
    setDataSignal = pyqtSignal(list)
    exitSignal = pyqtSignal()
    errorSignal = pyqtSignal(str)

class Worker(QRunnable):
    def __init__(self, instance, parent, conf, selectedPreview=None):
        super().__init__()
        self.running = False
        self.selectedPreview = selectedPreview
        self.instance = instance
        self.parent = parent
        self.conf = conf
        self.callback_module = loadModule(conf.args.callback)
        self.file_callbacks = {name: getattr(self.callback_module, name)
                               for name in ["shouldRun", "onNewFrame", "onShowFrame",
                                            "onNn", "onReport", "onSetup", "onTeardown", "onIter"]
                               if callable(getattr(self.callback_module, name, None))}
        self.instance.setCallbacks(**self.file_callbacks)
        self.signals = WorkerSignals()
    def run(self):
        self.running = True
        if Previews.color.name not in self.conf.args.show:
            self.conf.args.show.append(Previews.color.name)
        try:
            self.instance.run_all(self.conf)
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as ex:
            tb = ''.join(traceback.format_tb(ex.__traceback__))
            self.signals.errorSignal.emit(tb + f"{type(ex).__name__}: {ex}")

class GuiApp:
    def __init__(self, confManager, demoInstance):
        self.confManager = confManager
        self._demoInstance = demoInstance
        self.threadpool = QThreadPool()
        self.selectedPreview = self.confManager.args.show[0] if self.confManager.args.show else "color"
    def start(self):
        self.worker = Worker(self._demoInstance, parent=self, conf=self.confManager, selectedPreview=self.selectedPreview)
        self.worker.signals.updatePreviewSignal.connect(self.updatePreview)
        self.worker.signals.errorSignal.connect(self.showError)
        self.threadpool.start(self.worker)
    def updatePreview(self, frame):
        # Update the GUI with the provided frame (implementation–dependent)
        pass
    def showError(self, error):
        print(error, file=sys.stderr)
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Critical)
        msgBox.setText(error)
        msgBox.setWindowTitle("Error Occurred")
        msgBox.exec()
    def stopGui(self):
        self.worker.running = False
        self.threadpool.waitForDone(10000) 