import multiprocessing
import signal
import sys
from pickAndPlaceVoiceDetection import run_speech_detection
from depthai_handler import DepthAIHandler

def signal_handler(sig, frame):
    print("\nReceived signal to terminate...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start speech detection process
        speech_process = multiprocessing.Process(target=run_speech_detection)
        speech_process.start()
        
        # Start DepthAI handler
        depthai_handler = DepthAIHandler()
        depthai_handler.create_pipeline()
        depthai_handler.run()
        
    except KeyboardInterrupt:
        print("\nExiting program...")
    finally:
        if speech_process.is_alive():
            speech_process.terminate()
            speech_process.join()
