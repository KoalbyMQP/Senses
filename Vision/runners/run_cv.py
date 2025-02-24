import signal
import atexit
import sys
from utils.config_helper import prepareConfManager
from core.speech_demo import SpeechEnabledDemo
from depthai_sdk.managers import ArgsManager

def runOpenCv():
    args = ArgsManager.parseArgs()
    confManager = prepareConfManager(args)
    demo = SpeechEnabledDemo()
    signal.signal(signal.SIGINT, demo.stop)
    signal.signal(signal.SIGTERM, demo.stop)
    atexit.register(demo.stop)
    demo.run_all(confManager)

if __name__ == "__main__":
    runOpenCv() 