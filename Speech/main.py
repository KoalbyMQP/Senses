import multiprocessing
from pickAndPlaceVoiceDetection import run_speech_detection
from depthai_handler import DepthAIHandler

if __name__ == "__main__":
    # Start speech detection process
    speech_process = multiprocessing.Process(target=run_speech_detection)
    speech_process.start()
    
    # Start DepthAI handler
    depthai_handler = DepthAIHandler()
    depthai_handler.create_pipeline()
    depthai_handler.run()
    
    speech_process.join()
