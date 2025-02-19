import signal
import atexit
import sys
from utils.config_helper import prepareConfManager
from depthai_sdk.managers import ArgsManager
from core.demo_base import Demo
from gui.demo_gui import GuiApp
from utils.error_utils import component_check

@component_check("run_qt")
def runQt():
    args = ArgsManager.parseArgs()
    confManager = prepareConfManager(args)
    demoInstance = Demo(displayFrames=False)
    app = GuiApp(confManager, demoInstance)
    signal.signal(signal.SIGINT, app.stopGui)
    signal.signal(signal.SIGTERM, app.stopGui)
    atexit.register(app.stopGui)
    app.start()

if __name__ == "__main__":
    runQt() 