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
    
    # Set up signal handlers for clean termination
    signal.signal(signal.SIGINT, demo.stop)
    signal.signal(signal.SIGTERM, demo.stop)
    atexit.register(demo.stop)
    
    # Run the speech-enabled demo
    try:
        demo.run_all(confManager)
    except Exception as e:
        print(f"Error running demo: {e}")
        demo.stop()
        sys.exit(1)

if __name__ == "__main__":
    runOpenCv() 